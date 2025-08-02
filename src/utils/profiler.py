# -*- coding: utf-8 -*-
"""
性能分析工具模組

此模組提供用於分析和優化系統性能的工具。
主要功能：
- 函數執行時間分析
- 記憶體使用分析
- CPU 使用分析
- I/O 操作分析
- 模型推論性能分析
"""

import argparse
import cProfile
import functools
import inspect
import io
import os
import pstats
import time
import tracemalloc
from datetime import datetime
from typing import Callable, Optional, TypeVar

import psutil

from src.config import RESULTS_DIR
from src.core.logger import get_logger

# 設定日誌
logger = get_logger("profiler")

# 類型變量
T = TypeVar("T")


class FunctionProfiler:
    """函數性能分析器"""

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化函數性能分析器

        Args:
            output_dir: 輸出目錄，如果為 None，則使用 RESULTS_DIR/profiling
        """
        self.output_dir = output_dir or os.path.join(RESULTS_DIR, "profiling")
        os.makedirs(self.output_dir, exist_ok=True)
        self.profiling_results = {}

    def profile(
        self,
        sort_by: str = "cumulative",
        lines_to_print: int = 20,
        strip_dirs: bool = True,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        函數性能分析裝飾器

        Args:
            sort_by: 排序方式，可選值：'cumulative', 'time', 'calls'
            lines_to_print: 輸出的行數
            strip_dirs: 是否去除目錄路徑

        Returns:
            Callable: 裝飾器
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            """
            decorator

            Args:
                func:

            Returns:
                Callable[...]:
            """

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                """
                wrapper

                """
                profiler = cProfile.Profile()
                # 啟動分析器
                profiler.enable()
                # 執行函數
                result = func(*args, **kwargs)
                # 停止分析器
                profiler.disable()
                # 創建輸出流
                s = io.StringIO()
                # 創建統計對象
                ps = pstats.Stats(profiler, stream=s).sort_stats(sort_by)
                # 如果需要去除目錄路徑
                if strip_dirs:
                    ps.strip_dirs()
                # 輸出統計信息
                ps.print_stats(lines_to_print)
                # 獲取輸出
                output = s.getvalue()
                # 記錄結果
                func_name = func.__name__
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{func_name}_{timestamp}.prof"
                filepath = os.path.join(self.output_dir, filename)
                # 保存分析結果
                with open(filepath, "w") as f:
                    f.write(output)
                # 記錄到日誌
                logger.info(f"函數 {func_name} 的性能分析結果已保存至 {filepath}")
                # 保存到結果字典
                self.profiling_results[func_name] = {
                    "timestamp": timestamp,
                    "filepath": filepath,
                    "output": output,
                }
                return result

            return wrapper

        return decorator


class MemoryProfiler:
    """記憶體使用分析器"""

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化記憶體使用分析器

        Args:
            output_dir: 輸出目錄，如果為 None，則使用 RESULTS_DIR/profiling
        """
        self.output_dir = output_dir or os.path.join(RESULTS_DIR, "profiling")
        os.makedirs(self.output_dir, exist_ok=True)
        self.profiling_results = {}

    def profile(
        self, top_n: int = 20
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        記憶體使用分析裝飾器

        Args:
            top_n: 輸出的前 N 個記憶體分配

        Returns:
            Callable: 裝飾器
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            """
            decorator

            Args:
                func:

            Returns:
                Callable[...]:
            """

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                """
                wrapper

                """
                tracemalloc.start()
                # 執行函數
                result = func(*args, **kwargs)
                # 獲取當前記憶體快照
                snapshot = tracemalloc.take_snapshot()
                # 停止記憶體追蹤
                tracemalloc.stop()
                # 按大小排序統計信息
                top_stats = snapshot.statistics("lineno")
                # 創建輸出流
                s = io.StringIO()
                s.write(f"記憶體使用 Top {top_n}:\n")
                for i, stat in enumerate(top_stats[:top_n], 1):
                    s.write(f"#{i}: {stat}\n")
                # 獲取輸出
                output = s.getvalue()
                # 記錄結果
                func_name = func.__name__
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{func_name}_memory_{timestamp}.txt"
                filepath = os.path.join(self.output_dir, filename)
                # 保存分析結果
                with open(filepath, "w") as f:
                    f.write(output)
                # 記錄到日誌
                logger.info(f"函數 {func_name} 的記憶體使用分析結果已保存至 {filepath}")
                # 保存到結果字典
                self.profiling_results[func_name] = {
                    "timestamp": timestamp,
                    "filepath": filepath,
                    "output": output,
                }
                return result

            return wrapper

        return decorator


class IOProfiler:
    """I/O 操作分析器"""

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化 I/O 操作分析器

        Args:
            output_dir: 輸出目錄，如果為 None，則使用 RESULTS_DIR/profiling
        """
        self.output_dir = output_dir or os.path.join(RESULTS_DIR, "profiling")
        os.makedirs(self.output_dir, exist_ok=True)
        self.profiling_results = {}

    def profile(self) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        I/O 操作分析裝飾器

        Returns:
            Callable: 裝飾器
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            """
            decorator

            Args:
                func:

            Returns:
                Callable[...]:
            """

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                """
                wrapper

                """
                process = psutil.Process(os.getpid())
                # 獲取初始 I/O 計數
                io_before = process.io_counters()
                # 記錄開始時間
                start_time = time.time()
                # 執行函數
                result = func(*args, **kwargs)
                # 記錄結束時間
                end_time = time.time()
                # 獲取結束 I/O 計數
                io_after = process.io_counters()
                # 計算 I/O 差異
                io_diff = {
                    "read_count": io_after.read_count - io_before.read_count,
                    "write_count": io_after.write_count - io_before.write_count,
                    "read_bytes": io_after.read_bytes - io_before.read_bytes,
                    "write_bytes": io_after.write_bytes - io_before.write_bytes,
                    "execution_time": end_time - start_time,
                }
                # 創建輸出流
                s = io.StringIO()
                s.write(f"I/O 操作分析結果:\n")
                s.write(f"執行時間: {io_diff['execution_time']:.6f} 秒\n")
                s.write(f"讀取次數: {io_diff['read_count']}\n")
                s.write(f"寫入次數: {io_diff['write_count']}\n")
                s.write(f"讀取字節: {io_diff['read_bytes']} 字節\n")
                s.write(f"寫入字節: {io_diff['write_bytes']} 字節\n")
                # 獲取輸出
                output = s.getvalue()
                # 記錄結果
                func_name = func.__name__
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{func_name}_io_{timestamp}.txt"
                filepath = os.path.join(self.output_dir, filename)
                # 保存分析結果
                with open(filepath, "w") as f:
                    f.write(output)
                # 記錄到日誌
                logger.info(f"函數 {func_name} 的 I/O 操作分析結果已保存至 {filepath}")
                # 保存到結果字典
                self.profiling_results[func_name] = {
                    "timestamp": timestamp,
                    "filepath": filepath,
                    "output": output,
                    "data": io_diff,
                }
                return result

            return wrapper

        return decorator


def analyze_module(module_name: str, output_dir: Optional[str] = None):
    """
    分析模組性能

    Args:
        module_name: 模組名稱
        output_dir: 輸出目錄，如果為 None，則使用 RESULTS_DIR/profiling
    """
    output_dir = output_dir or os.path.join(RESULTS_DIR, "profiling")
    os.makedirs(output_dir, exist_ok=True)

    # 導入模組
    try:
        module = __import__(module_name, fromlist=["*"])
    except ImportError:
        logger.error(f"無法導入模組 {module_name}")
        return

    # 創建分析器
    profiler = cProfile.Profile()
    # 啟動分析器
    profiler.enable()

    # 執行模組中的所有函數
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and obj.__module__ == module_name:
            try:
                logger.info(f"分析函數 {name}")
                # 執行函數
                obj()
            except Exception as e:
                logger.error(f"執行函數 {name} 時發生錯誤: {e}")

    # 停止分析器
    profiler.disable()
    # 創建輸出流
    s = io.StringIO()
    # 創建統計對象
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    # 去除目錄路徑
    ps.strip_dirs()
    # 輸出統計信息
    ps.print_stats(30)
    # 獲取輸出
    output = s.getvalue()
    # 記錄結果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{module_name.replace('.', '_')}_{timestamp}.prof"
    filepath = os.path.join(output_dir, filename)
    # 保存分析結果
    with open(filepath, "w") as f:
        f.write(output)
    # 記錄到日誌
    logger.info(f"模組 {module_name} 的性能分析結果已保存至 {filepath}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="性能分析工具")
    parser.add_argument("--analyze-module", type=str, help="分析指定模組的性能")
    parser.add_argument("--output-dir", type=str, default=None, help="輸出目錄")
    args = parser.parse_args()

    if args.analyze_module:
        analyze_module(args.analyze_module, args.output_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
