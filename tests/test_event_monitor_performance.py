"""
事件監控系統效能測試

測試事件監控系統的效能、記憶體使用和併發處理能力
"""

import gc
import threading
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import psutil

from src.core.event_monitor import EventMonitor, MonitorConfig, MonitorConstants


class TestEventMonitorPerformance(unittest.TestCase):
    """事件監控系統效能測試"""

    def setUp(self):
        """設置測試環境"""
        # 創建測試配置
        self.config = MonitorConfig(
            price_threshold=0.05,
            volume_threshold=2.0,
            check_interval=1,  # 1秒間隔用於測試
            news_sources=["http://test.com"],
            notification_channels=["log"],
            use_event_engine=False,  # 簡化測試
        )

        # 創建測試資料
        self.test_price_data = self._create_test_price_data()
        self.test_volume_data = self._create_test_volume_data()

        # 創建監控器
        self.monitor = EventMonitor(
            config=self.config,
            price_df=self.test_price_data,
            volume_df=self.test_volume_data,
        )

    def _create_test_price_data(self) -> pd.DataFrame:
        """創建測試價格資料"""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        stocks = ["2330", "2317", "2454"]

        data = {}
        for stock in stocks:
            # 創建有異常的價格資料
            prices = [100.0]
            for i in range(1, 100):
                if i == 98:  # 在最後第二天創建異常，確保有前一天資料比較
                    change = 0.1 if stock == "2330" else 0.01  # 2330有10%異常變化
                else:
                    change = 0.001  # 正常小幅變化
                prices.append(prices[-1] * (1 + change))
            data[stock] = prices

        return pd.DataFrame(data, index=dates)

    def _create_test_volume_data(self) -> pd.DataFrame:
        """創建測試成交量資料"""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        stocks = ["2330", "2317", "2454"]

        data = {}
        for stock in stocks:
            # 創建有異常的成交量資料
            volumes = [1000000]
            for i in range(1, 100):
                if i == 98:  # 在最後第二天創建異常，確保有足夠歷史資料
                    multiplier = 3.0 if stock == "2317" else 1.01  # 2317有3倍異常
                else:
                    multiplier = 1.001  # 正常小幅變化
                volumes.append(int(volumes[-1] * multiplier))
            data[stock] = volumes

        return pd.DataFrame(data, index=dates)

    def test_memory_usage(self):
        """測試記憶體使用"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # 模擬大量事件處理
        for i in range(1000):
            self.monitor.events.append(
                {
                    "id": i,
                    "type": "test",
                    "data": f"test_data_{i}" * 100,  # 創建較大的資料
                }
            )

        # 觸發記憶體管理
        self.monitor._manage_memory()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # 記憶體增長應該在合理範圍內（小於50MB）
        self.assertLess(
            memory_increase,
            50 * 1024 * 1024,
            f"記憶體增長過多: {memory_increase / 1024 / 1024:.2f} MB",
        )

        # 檢查事件數量是否被限制
        self.assertLessEqual(
            len(self.monitor.events), MonitorConstants.MAX_EVENTS_IN_MEMORY
        )

    def test_price_anomaly_detection_performance(self):
        """測試價格異常檢測效能"""
        start_time = time.time()

        # 執行多次價格異常檢測
        for _ in range(100):
            self.monitor._check_price_anomaly()

        end_time = time.time()
        execution_time = end_time - start_time

        # 100次檢測應該在1秒內完成
        self.assertLess(
            execution_time, 1.0, f"價格異常檢測效能不佳: {execution_time:.3f}秒"
        )

        # 檢查是否檢測到異常
        anomaly_events = [
            e
            for e in self.monitor.events
            if hasattr(e, "event_type") and "ANOMALY" in str(e.event_type)
        ]
        self.assertGreater(len(anomaly_events), 0, "應該檢測到價格異常")

    def test_volume_anomaly_detection_performance(self):
        """測試成交量異常檢測效能"""
        start_time = time.time()

        # 執行多次成交量異常檢測
        for _ in range(100):
            self.monitor._check_volume_anomaly()

        end_time = time.time()
        execution_time = end_time - start_time

        # 100次檢測應該在1秒內完成
        self.assertLess(
            execution_time, 1.0, f"成交量異常檢測效能不佳: {execution_time:.3f}秒"
        )

        # 檢查是否檢測到異常
        anomaly_events = [
            e
            for e in self.monitor.events
            if hasattr(e, "event_type") and "ANOMALY" in str(e.event_type)
        ]
        self.assertGreater(len(anomaly_events), 0, "應該檢測到成交量異常")

    @patch("requests.get")
    def test_news_fetching_performance(self, mock_get):
        """測試新聞獲取效能"""
        # 模擬新聞回應
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <div class="news-item">
                    <h3><a href="/test">測試新聞標題 2330</a></h3>
                    <time datetime="2024-01-01T10:00:00">2024-01-01</time>
                    <p class="summary">測試摘要</p>
                </div>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        start_time = time.time()

        # 執行多次新聞檢查
        for _ in range(10):
            self.monitor._check_news()

        end_time = time.time()
        execution_time = end_time - start_time

        # 10次新聞檢查應該在5秒內完成
        self.assertLess(
            execution_time, 5.0, f"新聞檢查效能不佳: {execution_time:.3f}秒"
        )

    def test_concurrent_monitoring(self):
        """測試併發監控"""
        results = []
        errors = []

        def monitor_worker():
            """監控工作執行緒"""
            try:
                for _ in range(10):
                    self.monitor._check_price_anomaly()
                    self.monitor._check_volume_anomaly()
                    time.sleep(0.01)  # 短暫延遲
                results.append("success")
            except Exception as e:
                errors.append(str(e))

        # 創建多個執行緒
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=monitor_worker)
            threads.append(thread)

        # 啟動所有執行緒
        start_time = time.time()
        for thread in threads:
            thread.start()

        # 等待所有執行緒完成
        for thread in threads:
            thread.join(timeout=10)

        end_time = time.time()
        execution_time = end_time - start_time

        # 檢查結果
        self.assertEqual(len(results), 5, f"併發執行失敗，錯誤: {errors}")
        self.assertLess(
            execution_time, 5.0, f"併發監控效能不佳: {execution_time:.3f}秒"
        )
        self.assertEqual(len(errors), 0, f"併發執行出現錯誤: {errors}")

    def test_garbage_collection_effectiveness(self):
        """測試垃圾回收效果"""
        # 創建大量物件
        large_objects = []
        for i in range(1000):
            large_objects.append([i] * 1000)

        # 記錄初始記憶體
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # 刪除物件並觸發垃圾回收
        del large_objects
        gc.collect()

        # 記錄垃圾回收後記憶體
        after_gc_memory = process.memory_info().rss

        # 記憶體應該有所減少
        memory_freed = initial_memory - after_gc_memory
        self.assertGreaterEqual(memory_freed, 0, "垃圾回收應該釋放記憶體")

    def test_event_processing_latency(self):
        """測試事件處理延遲"""
        latencies = []

        for _ in range(100):
            start_time = time.time()

            # 模擬事件處理
            self.monitor._check_price_anomaly()

            end_time = time.time()
            latency = (end_time - start_time) * 1000  # 轉換為毫秒
            latencies.append(latency)

        # 計算統計資料
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        # 檢查延遲要求
        self.assertLess(avg_latency, 50, f"平均延遲過高: {avg_latency:.2f}ms")
        self.assertLess(p95_latency, 100, f"95th百分位延遲過高: {p95_latency:.2f}ms")
        self.assertLess(max_latency, 200, f"最大延遲過高: {max_latency:.2f}ms")

    def tearDown(self):
        """清理測試環境"""
        if self.monitor.running:
            self.monitor.stop()

        # 強制垃圾回收
        gc.collect()


if __name__ == "__main__":
    unittest.main()
