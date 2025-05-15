# -*- coding: utf-8 -*-
"""
性能和壓力測試腳本

此腳本用於執行系統的性能和壓力測試，包括：
- 基準性能測試
- 高負載壓力測試
- 長時間穩定性測試
- 並發請求測試
- 資源使用監控

使用方法:
    python -m src.scripts.run_performance_tests [options]

選項:
    --benchmark: 執行基準性能測試
    --stress: 執行高負載壓力測試
    --stability: 執行長時間穩定性測試
    --concurrency: 執行並發請求測試
    --monitor: 監控資源使用
    --all: 執行所有測試
    --output-dir: 指定輸出目錄
    --duration: 測試持續時間（秒）
    --concurrency-level: 並發級別
"""

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import psutil

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.config import RESULTS_DIR
from src.core.logger import get_logger
from src.maintenance.system_profiler import SystemProfiler
from src.utils.profiler import FunctionProfiler, IOProfiler, MemoryProfiler

# 設定日誌
logger = get_logger("performance_tests")


class PerformanceTest:
    """性能測試基類"""

    def __init__(self, output_dir: str, duration: int = 60):
        """
        初始化性能測試

        Args:
            output_dir: 輸出目錄
            duration: 測試持續時間（秒）
        """
        self.output_dir = output_dir
        self.duration = duration
        self.results = {}
        self.start_time = None
        self.end_time = None

        # 創建分析器
        self.function_profiler = FunctionProfiler(output_dir)
        self.memory_profiler = MemoryProfiler(output_dir)
        self.io_profiler = IOProfiler(output_dir)
        self.system_profiler = SystemProfiler(output_dir)

    def setup(self):
        """設置測試環境"""
        logger.info(f"設置 {self.__class__.__name__} 測試環境")

    def teardown(self):
        """清理測試環境"""
        logger.info(f"清理 {self.__class__.__name__} 測試環境")

    def run(self):
        """執行測試"""
        logger.info(f"開始執行 {self.__class__.__name__}")

        self.setup()

        self.start_time = datetime.now()
        self._run_test()
        self.end_time = datetime.now()

        self.teardown()

        # 計算測試時間
        test_duration = (self.end_time - self.start_time).total_seconds()
        self.results["duration"] = test_duration

        logger.info(f"{self.__class__.__name__} 執行完成，耗時 {test_duration:.2f} 秒")

        return self.results

    def _run_test(self):
        """執行具體測試，由子類實現"""
        raise NotImplementedError("子類必須實現 _run_test 方法")

    def save_results(self):
        """保存測試結果"""
        if not self.results:
            logger.warning(f"{self.__class__.__name__} 沒有結果可保存")
            return

        # 保存結果為 JSON
        result_path = os.path.join(
            self.output_dir, f"{self.__class__.__name__}_results.json"
        )
        with open(result_path, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"{self.__class__.__name__} 結果已保存至 {result_path}")

        # 生成圖表
        self._generate_charts()

    def _generate_charts(self):
        """生成圖表，由子類實現"""


class BenchmarkTest(PerformanceTest):
    """基準性能測試"""

    def _run_test(self):
        """執行基準性能測試"""
        logger.info("執行基準性能測試")

        # 測試數據處理性能
        self._test_data_processing()

        # 測試模型推論性能
        self._test_model_inference()

        # 測試信號生成性能
        self._test_signal_generation()

        # 測試回測性能
        self._test_backtest()

    def _test_data_processing(self):
        """測試數據處理性能"""
        logger.info("測試數據處理性能")

        # 使用系統分析器分析數據處理性能
        self.system_profiler.profile_data_processing()

        # 獲取分析結果
        data_processing_results = self.system_profiler.profiling_results.get(
            "data_processing", {}
        )

        self.results["data_processing"] = data_processing_results

    def _test_model_inference(self):
        """測試模型推論性能"""
        logger.info("測試模型推論性能")

        # 使用系統分析器分析模型推論性能
        self.system_profiler.profile_model_inference()

        # 獲取分析結果
        model_inference_results = self.system_profiler.profiling_results.get(
            "model_inference", {}
        )

        self.results["model_inference"] = model_inference_results

    def _test_signal_generation(self):
        """測試信號生成性能"""
        logger.info("測試信號生成性能")

        # 使用函數分析器分析信號生成性能
        from src.core.signal_gen import SignalGenerator

        # 創建信號生成器
        signal_generator = SignalGenerator()

        # 使用函數分析器分析 generate_signals 方法
        generate_signals = self.function_profiler.profile()(
            signal_generator.generate_signals
        )

        # 執行信號生成
        try:
            generate_signals()
        except Exception as e:
            logger.error(f"執行信號生成時發生錯誤: {e}")

        # 獲取分析結果
        signal_generation_results = self.function_profiler.profiling_results.get(
            "generate_signals", {}
        )

        self.results["signal_generation"] = signal_generation_results

    def _test_backtest(self):
        """測試回測性能"""
        logger.info("測試回測性能")

        # 使用函數分析器分析回測性能
        from src.core.backtest import run_backtest

        # 使用函數分析器分析 run_backtest 函數
        profiled_run_backtest = self.function_profiler.profile()(run_backtest)

        # 執行回測
        try:
            profiled_run_backtest()
        except Exception as e:
            logger.error(f"執行回測時發生錯誤: {e}")

        # 獲取分析結果
        backtest_results = self.function_profiler.profiling_results.get(
            "run_backtest", {}
        )

        self.results["backtest"] = backtest_results

    def _generate_charts(self):
        """生成基準性能測試圖表"""
        logger.info("生成基準性能測試圖表")

        # 創建圖表目錄
        charts_dir = os.path.join(self.output_dir, "benchmark_charts")
        os.makedirs(charts_dir, exist_ok=True)

        # 生成數據處理性能圖表
        if "data_processing" in self.results:
            self._generate_data_processing_chart(charts_dir)

        # 生成模型推論性能圖表
        if "model_inference" in self.results:
            self._generate_model_inference_chart(charts_dir)

        # 生成信號生成性能圖表
        if "signal_generation" in self.results:
            self._generate_signal_generation_chart(charts_dir)

        # 生成回測性能圖表
        if "backtest" in self.results:
            self._generate_backtest_chart(charts_dir)

    def _generate_data_processing_chart(self, charts_dir):
        """生成數據處理性能圖表"""
        # 實現數據處理性能圖表生成邏輯

    def _generate_model_inference_chart(self, charts_dir):
        """生成模型推論性能圖表"""
        # 實現模型推論性能圖表生成邏輯

    def _generate_signal_generation_chart(self, charts_dir):
        """生成信號生成性能圖表"""
        # 實現信號生成性能圖表生成邏輯

    def _generate_backtest_chart(self, charts_dir):
        """生成回測性能圖表"""
        # 實現回測性能圖表生成邏輯


class StressTest(PerformanceTest):
    """高負載壓力測試"""

    def __init__(
        self, output_dir: str, duration: int = 300, concurrency_level: int = 10
    ):
        """
        初始化高負載壓力測試

        Args:
            output_dir: 輸出目錄
            duration: 測試持續時間（秒）
            concurrency_level: 並發級別
        """
        super().__init__(output_dir, duration)
        self.concurrency_level = concurrency_level
        self.resource_usage = []
        self.stop_event = threading.Event()

    def _run_test(self):
        """執行高負載壓力測試"""
        logger.info(
            f"執行高負載壓力測試，並發級別: {self.concurrency_level}，持續時間: {self.duration} 秒"
        )

        # 啟動資源監控線程
        monitor_thread = threading.Thread(target=self._monitor_resources)
        monitor_thread.start()

        # 啟動工作線程
        threads = []
        for i in range(self.concurrency_level):
            thread = threading.Thread(target=self._worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待測試完成
        start_time = time.time()
        while time.time() - start_time < self.duration:
            time.sleep(1)

        # 停止所有線程
        self.stop_event.set()

        # 等待所有線程完成
        for thread in threads:
            thread.join()

        # 等待監控線程完成
        monitor_thread.join()

        # 計算結果
        self._calculate_results()

    def _worker(self, worker_id):
        """工作線程"""
        logger.info(f"工作線程 {worker_id} 啟動")

        # 執行任務直到收到停止信號
        while not self.stop_event.is_set():
            try:
                # 執行高負載任務
                self._execute_high_load_task(worker_id)
            except Exception as e:
                logger.error(f"工作線程 {worker_id} 執行任務時發生錯誤: {e}")

        logger.info(f"工作線程 {worker_id} 停止")

    def _execute_high_load_task(self, worker_id):
        """執行高負載任務"""
        # 這裡可以根據需要實現具體的高負載任務
        # 例如：處理大量數據、執行複雜計算等

        # 模擬高負載任務
        time.sleep(0.1)  # 避免 CPU 使用率過高

    def _monitor_resources(self):
        """監控資源使用"""
        logger.info("資源監控線程啟動")

        # 監控資源使用直到收到停止信號
        while not self.stop_event.is_set():
            try:
                # 獲取 CPU 使用率
                cpu_percent = psutil.cpu_percent(interval=1)

                # 獲取內存使用率
                memory_info = psutil.virtual_memory()
                memory_percent = memory_info.percent

                # 獲取磁盤 I/O
                disk_io = psutil.disk_io_counters()

                # 獲取網絡 I/O
                net_io = psutil.net_io_counters()

                # 記錄資源使用
                self.resource_usage.append(
                    {
                        "timestamp": time.time(),
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory_percent,
                        "disk_read_bytes": disk_io.read_bytes,
                        "disk_write_bytes": disk_io.write_bytes,
                        "net_bytes_sent": net_io.bytes_sent,
                        "net_bytes_recv": net_io.bytes_recv,
                    }
                )
            except Exception as e:
                logger.error(f"監控資源使用時發生錯誤: {e}")

        logger.info("資源監控線程停止")

    def _calculate_results(self):
        """計算測試結果"""
        if not self.resource_usage:
            logger.warning("沒有資源使用數據")
            return

        # 轉換為 DataFrame
        df = pd.DataFrame(self.resource_usage)

        # 計算統計數據
        stats = {
            "cpu_percent": {
                "min": df["cpu_percent"].min(),
                "max": df["cpu_percent"].max(),
                "mean": df["cpu_percent"].mean(),
                "median": df["cpu_percent"].median(),
                "std": df["cpu_percent"].std(),
            },
            "memory_percent": {
                "min": df["memory_percent"].min(),
                "max": df["memory_percent"].max(),
                "mean": df["memory_percent"].mean(),
                "median": df["memory_percent"].median(),
                "std": df["memory_percent"].std(),
            },
        }

        # 計算磁盤 I/O 速率
        if len(df) > 1:
            df["disk_read_rate"] = df["disk_read_bytes"].diff() / df["timestamp"].diff()
            df["disk_write_rate"] = (
                df["disk_write_bytes"].diff() / df["timestamp"].diff()
            )
            df["net_send_rate"] = df["net_bytes_sent"].diff() / df["timestamp"].diff()
            df["net_recv_rate"] = df["net_bytes_recv"].diff() / df["timestamp"].diff()

            stats["disk_io"] = {
                "read_rate": {
                    "min": df["disk_read_rate"].min(),
                    "max": df["disk_read_rate"].max(),
                    "mean": df["disk_read_rate"].mean(),
                    "median": df["disk_read_rate"].median(),
                    "std": df["disk_read_rate"].std(),
                },
                "write_rate": {
                    "min": df["disk_write_rate"].min(),
                    "max": df["disk_write_rate"].max(),
                    "mean": df["disk_write_rate"].mean(),
                    "median": df["disk_write_rate"].median(),
                    "std": df["disk_write_rate"].std(),
                },
            }

            stats["net_io"] = {
                "send_rate": {
                    "min": df["net_send_rate"].min(),
                    "max": df["net_send_rate"].max(),
                    "mean": df["net_send_rate"].mean(),
                    "median": df["net_send_rate"].median(),
                    "std": df["net_send_rate"].std(),
                },
                "recv_rate": {
                    "min": df["net_recv_rate"].min(),
                    "max": df["net_recv_rate"].max(),
                    "mean": df["net_recv_rate"].mean(),
                    "median": df["net_recv_rate"].median(),
                    "std": df["net_recv_rate"].std(),
                },
            }

        # 保存原始數據
        self.results["resource_usage"] = self.resource_usage

        # 保存統計數據
        self.results["stats"] = stats

        # 保存測試參數
        self.results["parameters"] = {
            "duration": self.duration,
            "concurrency_level": self.concurrency_level,
        }

    def _generate_charts(self):
        """生成高負載壓力測試圖表"""
        logger.info("生成高負載壓力測試圖表")

        if not self.resource_usage:
            logger.warning("沒有資源使用數據，無法生成圖表")
            return

        # 創建圖表目錄
        charts_dir = os.path.join(self.output_dir, "stress_test_charts")
        os.makedirs(charts_dir, exist_ok=True)

        # 轉換為 DataFrame
        df = pd.DataFrame(self.resource_usage)

        # 轉換時間戳為相對時間（秒）
        df["relative_time"] = df["timestamp"] - df["timestamp"].iloc[0]

        # 生成 CPU 使用率圖表
        plt.figure(figsize=(10, 6))
        plt.plot(df["relative_time"], df["cpu_percent"])
        plt.xlabel("Time (seconds)")
        plt.ylabel("CPU Usage (%)")
        plt.title("CPU Usage During Stress Test")
        plt.grid(True)
        plt.savefig(os.path.join(charts_dir, "cpu_usage.png"))
        plt.close()

        # 生成內存使用率圖表
        plt.figure(figsize=(10, 6))
        plt.plot(df["relative_time"], df["memory_percent"])
        plt.xlabel("Time (seconds)")
        plt.ylabel("Memory Usage (%)")
        plt.title("Memory Usage During Stress Test")
        plt.grid(True)
        plt.savefig(os.path.join(charts_dir, "memory_usage.png"))
        plt.close()

        # 計算並生成磁盤 I/O 速率圖表
        if len(df) > 1:
            df["disk_read_rate"] = df["disk_read_bytes"].diff() / df["timestamp"].diff()
            df["disk_write_rate"] = (
                df["disk_write_bytes"].diff() / df["timestamp"].diff()
            )

            plt.figure(figsize=(10, 6))
            plt.plot(df["relative_time"][1:], df["disk_read_rate"][1:], label="Read")
            plt.plot(df["relative_time"][1:], df["disk_write_rate"][1:], label="Write")
            plt.xlabel("Time (seconds)")
            plt.ylabel("Disk I/O Rate (bytes/s)")
            plt.title("Disk I/O Rate During Stress Test")
            plt.legend()
            plt.grid(True)
            plt.savefig(os.path.join(charts_dir, "disk_io_rate.png"))
            plt.close()

            # 計算並生成網絡 I/O 速率圖表
            df["net_send_rate"] = df["net_bytes_sent"].diff() / df["timestamp"].diff()
            df["net_recv_rate"] = df["net_bytes_recv"].diff() / df["timestamp"].diff()

            plt.figure(figsize=(10, 6))
            plt.plot(df["relative_time"][1:], df["net_send_rate"][1:], label="Send")
            plt.plot(df["relative_time"][1:], df["net_recv_rate"][1:], label="Receive")
            plt.xlabel("Time (seconds)")
            plt.ylabel("Network I/O Rate (bytes/s)")
            plt.title("Network I/O Rate During Stress Test")
            plt.legend()
            plt.grid(True)
            plt.savefig(os.path.join(charts_dir, "network_io_rate.png"))
            plt.close()


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="性能和壓力測試腳本")
    parser.add_argument("--benchmark", action="store_true", help="執行基準性能測試")
    parser.add_argument("--stress", action="store_true", help="執行高負載壓力測試")
    parser.add_argument("--stability", action="store_true", help="執行長時間穩定性測試")
    parser.add_argument("--concurrency", action="store_true", help="執行並發請求測試")
    parser.add_argument("--monitor", action="store_true", help="監控資源使用")
    parser.add_argument("--all", action="store_true", help="執行所有測試")
    parser.add_argument("--output-dir", type=str, default=None, help="指定輸出目錄")
    parser.add_argument("--duration", type=int, default=60, help="測試持續時間（秒）")
    parser.add_argument("--concurrency-level", type=int, default=10, help="並發級別")

    args = parser.parse_args()

    # 如果沒有指定任何測試，則執行所有測試
    if not any(
        [
            args.benchmark,
            args.stress,
            args.stability,
            args.concurrency,
            args.monitor,
            args.all,
        ]
    ):
        args.all = True

    # 如果指定了 --all，則執行所有測試
    if args.all:
        args.benchmark = True
        args.stress = True
        args.stability = True
        args.concurrency = True
        args.monitor = True

    # 設置輸出目錄
    if args.output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output_dir = os.path.join(RESULTS_DIR, f"performance_tests_{timestamp}")

    os.makedirs(args.output_dir, exist_ok=True)

    # 執行測試
    if args.benchmark:
        benchmark_test = BenchmarkTest(args.output_dir, args.duration)
        benchmark_test.run()
        benchmark_test.save_results()

    if args.stress:
        stress_test = StressTest(args.output_dir, args.duration, args.concurrency_level)
        stress_test.run()
        stress_test.save_results()

    # 其他測試可以根據需要添加

    logger.info(f"所有測試結果已保存至: {args.output_dir}")


if __name__ == "__main__":
    main()
