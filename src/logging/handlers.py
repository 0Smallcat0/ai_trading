"""
日誌處理器模組

此模組提供各種日誌處理器，用於處理日誌記錄。
"""

import json
import logging
import os
import queue
import threading
import time
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

import requests

# 定義常量
DEFAULT_ELASTICSEARCH_URL = "http://localhost:9200"
DEFAULT_LOGSTASH_URL = "http://localhost:5044"
DEFAULT_LOKI_URL = "http://localhost:3100/loki/api/v1/push"


class AsyncHandler(logging.Handler):
    """異步處理器基類"""

    def __init__(self, level=logging.NOTSET, max_queue_size=1000):
        """
        初始化處理器

        Args:
            level: 日誌級別
            max_queue_size: 最大隊列大小
        """
        super().__init__(level)
        self.queue = queue.Queue(maxsize=max_queue_size)
        self.thread = None
        self.running = False
        self.flush_interval = 0.1  # 刷新間隔（秒）

    def emit(self, record):
        """
        發送記錄

        Args:
            record: 日誌記錄
        """
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            self.handleError(record)

        # 確保處理線程正在運行
        self._ensure_thread_running()

    def _ensure_thread_running(self):
        """確保處理線程正在運行"""
        if self.thread is None or not self.thread.is_alive():
            self.running = True
            self.thread = threading.Thread(target=self._process_queue)
            self.thread.daemon = True
            self.thread.start()

    def _process_queue(self):
        """處理隊列"""
        while self.running:
            try:
                # 獲取記錄
                record = self.queue.get(block=True, timeout=self.flush_interval)
                self._process_record(record)
                self.queue.task_done()
            except queue.Empty:
                # 隊列為空，繼續等待
                pass
            except Exception:
                # 處理異常
                self.handleError(record if "record" in locals() else None)

    def _process_record(self, record):
        """
        處理記錄

        Args:
            record: 日誌記錄
        """
        raise NotImplementedError("子類必須實現此方法")

    def close(self):
        """關閉處理器"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        self.queue = None
        super().close()


class ElasticsearchHandler(AsyncHandler):
    """Elasticsearch處理器"""

    def __init__(
        self,
        host=DEFAULT_ELASTICSEARCH_URL,
        index_name="trading-logs",
        level=logging.INFO,
        max_queue_size=1000,
        auth=None,
        timeout=5,
    ):
        """
        初始化處理器

        Args:
            host: Elasticsearch主機
            index_name: 索引名稱
            level: 日誌級別
            max_queue_size: 最大隊列大小
            auth: 認證信息，格式為(username, password)
            timeout: 超時時間（秒）
        """
        super().__init__(level, max_queue_size)
        self.host = host
        self.index_name = index_name
        self.auth = auth
        self.timeout = timeout
        self.session = requests.Session()
        if auth:
            self.session.auth = auth

    def _process_record(self, record):
        """
        處理記錄

        Args:
            record: 日誌記錄
        """
        # 格式化記錄
        message = self.format(record)

        # 構建URL
        url = f"{self.host}/{self.index_name}/_doc"

        # 發送記錄
        try:
            response = self.session.post(
                url,
                data=message,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except Exception:
            self.handleError(record)


class LogstashHandler(AsyncHandler):
    """Logstash處理器"""

    def __init__(
        self,
        host=DEFAULT_LOGSTASH_URL,
        level=logging.INFO,
        max_queue_size=1000,
        timeout=5,
    ):
        """
        初始化處理器

        Args:
            host: Logstash主機
            level: 日誌級別
            max_queue_size: 最大隊列大小
            timeout: 超時時間（秒）
        """
        super().__init__(level, max_queue_size)
        self.host = host
        self.timeout = timeout
        self.session = requests.Session()

    def _process_record(self, record):
        """
        處理記錄

        Args:
            record: 日誌記錄
        """
        # 格式化記錄
        message = self.format(record)

        # 發送記錄
        try:
            response = self.session.post(
                self.host,
                data=message,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except Exception:
            self.handleError(record)


class LokiHandler(AsyncHandler):
    """Loki處理器"""

    def __init__(
        self,
        host=DEFAULT_LOKI_URL,
        level=logging.INFO,
        max_queue_size=1000,
        timeout=5,
        batch_size=100,
        batch_interval=1.0,
    ):
        """
        初始化處理器

        Args:
            host: Loki主機
            level: 日誌級別
            max_queue_size: 最大隊列大小
            timeout: 超時時間（秒）
            batch_size: 批次大小
            batch_interval: 批次間隔（秒）
        """
        super().__init__(level, max_queue_size)
        self.host = host
        self.timeout = timeout
        self.session = requests.Session()
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.batch = []
        self.last_batch_time = time.time()

    def _process_record(self, record):
        """
        處理記錄

        Args:
            record: 日誌記錄
        """
        # 格式化記錄
        message = self.format(record)

        # 添加到批次
        self.batch.append(message)

        # 檢查是否需要發送批次
        if (
            len(self.batch) >= self.batch_size
            or time.time() - self.last_batch_time >= self.batch_interval
        ):
            self._send_batch()

    def _send_batch(self):
        """發送批次"""
        if not self.batch:
            return

        # 合併批次
        batch_data = self._merge_batch()

        # 發送批次
        try:
            response = self.session.post(
                self.host,
                data=batch_data,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except Exception:
            # 處理異常
            self.handleError(None)

        # 清空批次
        self.batch = []
        self.last_batch_time = time.time()

    def _merge_batch(self):
        """
        合併批次

        Returns:
            str: 合併後的批次數據
        """
        # 解析批次
        streams = {}
        for message in self.batch:
            try:
                data = json.loads(message)
                for stream in data.get("streams", []):
                    stream_key = json.dumps(stream.get("stream", {}), sort_keys=True)
                    if stream_key not in streams:
                        streams[stream_key] = {
                            "stream": stream.get("stream", {}),
                            "values": [],
                        }
                    streams[stream_key]["values"].extend(stream.get("values", []))
            except Exception:
                # 處理異常
                self.handleError(None)

        # 構建合併後的批次數據
        merged_data = {"streams": list(streams.values())}
        return json.dumps(merged_data)

    def close(self):
        """關閉處理器"""
        # 發送剩餘的批次
        if self.batch:
            self._send_batch()
        super().close()


class EnhancedRotatingFileHandler(RotatingFileHandler):
    """增強的輪換文件處理器"""

    def __init__(
        self,
        filename,
        mode="a",
        maxBytes=0,
        backupCount=0,
        encoding=None,
        delay=False,
        errors=None,
        compress=False,
        compress_mode="gzip",
    ):
        """
        初始化處理器

        Args:
            filename: 文件名
            mode: 模式
            maxBytes: 最大字節數
            backupCount: 備份數量
            encoding: 編碼
            delay: 是否延遲
            errors: 錯誤處理
            compress: 是否壓縮
            compress_mode: 壓縮模式
        """
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay, errors)
        self.compress = compress
        self.compress_mode = compress_mode

    def doRollover(self):
        """執行輪換"""
        # 執行基本輪換
        super().doRollover()

        # 壓縮舊文件
        if self.compress and self.backupCount > 0:
            for i in range(1, self.backupCount + 1):
                source = f"{self.baseFilename}.{i}"
                target = f"{source}.{self.compress_mode}"

                if os.path.exists(source):
                    self._compress_file(source, target)
                    try:
                        os.remove(source)
                    except Exception:
                        pass

    def _compress_file(self, source, target):
        """
        壓縮文件

        Args:
            source: 源文件
            target: 目標文件
        """
        if self.compress_mode == "gzip":
            import gzip

            with open(source, "rb") as f_in:
                with gzip.open(target, "wb") as f_out:
                    f_out.writelines(f_in)
        elif self.compress_mode == "bz2":
            import bz2

            with open(source, "rb") as f_in:
                with bz2.open(target, "wb") as f_out:
                    f_out.writelines(f_in)
        elif self.compress_mode == "zip":
            import zipfile

            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as f_out:
                f_out.write(source, os.path.basename(source))
        else:
            raise ValueError(f"不支持的壓縮模式: {self.compress_mode}")


class EnhancedTimedRotatingFileHandler(TimedRotatingFileHandler):
    """增強的定時輪換文件處理器"""

    def __init__(
        self,
        filename,
        when="h",
        interval=1,
        backupCount=0,
        encoding=None,
        delay=False,
        utc=False,
        atTime=None,
        errors=None,
        compress=False,
        compress_mode="gzip",
    ):
        """
        初始化處理器

        Args:
            filename: 文件名
            when: 輪換時間單位
            interval: 輪換間隔
            backupCount: 備份數量
            encoding: 編碼
            delay: 是否延遲
            utc: 是否使用UTC時間
            atTime: 輪換時間
            errors: 錯誤處理
            compress: 是否壓縮
            compress_mode: 壓縮模式
        """
        super().__init__(
            filename, when, interval, backupCount, encoding, delay, utc, atTime, errors
        )
        self.compress = compress
        self.compress_mode = compress_mode

    def doRollover(self):
        """執行輪換"""
        # 獲取舊文件名
        if self.backupCount > 0:
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename(f"{self.baseFilename}.{i}")
                dfn = self.rotation_filename(f"{self.baseFilename}.{i + 1}")
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
            dfn = self.rotation_filename(f"{self.baseFilename}.1")
            if os.path.exists(dfn):
                os.remove(dfn)
            self.rotate(self.baseFilename, dfn)
            if self.compress:
                self._compress_file(dfn, f"{dfn}.{self.compress_mode}")
                try:
                    os.remove(dfn)
                except Exception:
                    pass

        if not self.delay:
            self.stream = self._open()

    def _compress_file(self, source, target):
        """
        壓縮文件

        Args:
            source: 源文件
            target: 目標文件
        """
        if self.compress_mode == "gzip":
            import gzip

            with open(source, "rb") as f_in:
                with gzip.open(target, "wb") as f_out:
                    f_out.writelines(f_in)
        elif self.compress_mode == "bz2":
            import bz2

            with open(source, "rb") as f_in:
                with bz2.open(target, "wb") as f_out:
                    f_out.writelines(f_in)
        elif self.compress_mode == "zip":
            import zipfile

            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as f_out:
                f_out.write(source, os.path.basename(source))
        else:
            raise ValueError(f"不支持的壓縮模式: {self.compress_mode}")
