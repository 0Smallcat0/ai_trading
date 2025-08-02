# -*- coding: utf-8 -*-
"""
系統性能分析模組

此模組負責分析系統各組件的性能，識別瓶頸，並提供優化建議。
主要功能：
- 分析主流程性能
- 分析資料處理性能
- 分析模型推論性能
- 生成性能報告
"""

import argparse
import os
import time
from datetime import datetime
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import RESULTS_DIR
from src.core import (
    data_ingest,
    executor,
    features,
    main,
    portfolio,
    risk_control,
    signal_gen,
)
from src.core.logger import get_logger
from src.maintenance.performance_optimizer import PerformanceOptimizer
from src.models import inference_pipeline
from src.utils.profiler import FunctionProfiler, IOProfiler, MemoryProfiler

# 設定日誌
logger = get_logger("system_profiler")


class SystemProfiler:
    """系統性能分析器"""

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化系統性能分析器

        Args:
            output_dir: 輸出目錄，如果為 None，則使用 RESULTS_DIR/profiling
        """
        self.output_dir = output_dir or os.path.join(RESULTS_DIR, "profiling")
        os.makedirs(self.output_dir, exist_ok=True)

        # 創建分析器
        self.function_profiler = FunctionProfiler(self.output_dir)
        self.memory_profiler = MemoryProfiler(self.output_dir)
        self.io_profiler = IOProfiler(self.output_dir)
        self.performance_optimizer = PerformanceOptimizer()

        # 性能結果
        self.profiling_results = {}

    def profile_main_flow(self, mode: str = "backtest"):
        """
        分析主流程性能

        Args:
            mode: 執行模式，可選值：'backtest', 'paper', 'live'
        """
        logger.info(f"開始分析主流程性能，模式: {mode}")

        # 設定參數
        args = argparse.Namespace()
        args.mode = mode
        args.config = None
        args.start_date = "2022-01-01"
        args.end_date = "2022-12-31"
        args.strategy = "momentum"
        args.portfolio = "equal_weight"
        args.initial_capital = 1000000
        args.transaction_cost = 0.001
        args.slippage = 0.0005
        args.tax = 0.003
        args.interval = 60
        args.update_data = False

        # 分析初始化系統
        init_system = self.function_profiler.profile()(main.init_system)
        config = init_system(args)

        # 根據模式分析不同流程
        if mode == "backtest":
            # 分析回測模式
            run_backtest_mode = self.function_profiler.profile()(main.run_backtest_mode)
            results, report = run_backtest_mode(config)

            # 記錄結果
            self.profiling_results["main_flow"] = {
                "mode": mode,
                "results": report,
            }
        elif mode == "paper":
            # 分析模擬交易模式（只執行一次循環）
            # 修改 run_paper_mode 函數以便測試
            original_run_paper_mode = main.run_paper_mode

            def test_run_paper_mode(config):
                """測試用的模擬交易模式函數"""
                logger.info("開始模擬交易模式")

                # 載入資料
                logger.info("載入資料")
                data_ingest.load_data()

                # 更新資料
                logger.info("更新資料")
                data_ingest.update_data()

                # 計算特徵
                logger.info("計算特徵")
                features_data = features.compute_features()

                # 生成訊號
                logger.info("生成訊號")
                signals = signal_gen.generate_signals(
                    features_data,
                    config["strategy"]["name"],
                    **config["strategy"]["params"],
                )

                # 最佳化投資組合
                logger.info("最佳化投資組合")
                weights = portfolio.optimize(
                    signals,
                    config["portfolio"]["name"],
                    **config["portfolio"]["params"],
                )

                # 風險控制
                logger.info("風險控制")
                portfolio_value = config["backtest"]["initial_capital"]
                filtered_signals = risk_control.filter_signals(
                    signals,
                    portfolio_value,
                    max_position_size=config["risk_control"]["max_position_size"],
                    max_portfolio_risk=config["risk_control"]["max_portfolio_risk"],
                    stop_loss_pct=config["risk_control"]["stop_loss"],
                    stop_profit_pct=config["risk_control"]["stop_profit"],
                )

                # 執行訂單
                logger.info("執行訂單")
                orders = executor.generate_orders(filtered_signals, weights)

                return {
                    "signals": signals,
                    "weights": weights,
                    "filtered_signals": filtered_signals,
                    "orders": orders,
                }

            # 替換函數
            main.run_paper_mode = self.function_profiler.profile()(test_run_paper_mode)

            # 執行測試
            results = main.run_paper_mode(config)

            # 還原函數
            main.run_paper_mode = original_run_paper_mode

            # 記錄結果
            self.profiling_results["main_flow"] = {
                "mode": mode,
                "results": results,
            }

        logger.info("主流程性能分析完成")

    def profile_data_processing(self):
        """分析資料處理性能"""
        logger.info("開始分析資料處理性能")

        # 分析資料載入
        load_data = self.function_profiler.profile()(data_ingest.load_data)
        load_data_memory = self.memory_profiler.profile()(data_ingest.load_data)
        load_data_io = self.io_profiler.profile()(data_ingest.load_data)

        # 執行分析
        load_data()
        _ = load_data_memory()
        _ = load_data_io()

        # 分析特徵計算
        compute_features = self.function_profiler.profile()(features.compute_features)
        compute_features_memory = self.memory_profiler.profile()(
            features.compute_features
        )

        # 執行分析
        compute_features()
        _ = compute_features_memory()

        logger.info("資料處理性能分析完成")

    def profile_model_inference(self):
        """分析模型推論性能"""
        logger.info("開始分析模型推論性能")

        # 創建測試資料
        test_data = pd.DataFrame(
            np.random.random((1000, 10)), columns=[f"feature_{i}" for i in range(10)]
        )

        # 分析單次推論
        try:
            # 獲取模型
            from src.models.model_factory import create_model

            model = create_model("lstm")

            # 創建推論管道
            pipeline = inference_pipeline.InferencePipeline(model=model)

            # 分析推論性能
            predict = self.function_profiler.profile()(pipeline.predict)
            predict_memory = self.memory_profiler.profile()(pipeline.predict)

            # 執行分析
            _ = predict(test_data)
            _ = predict_memory(test_data)

            # 分析批次推論
            batch_predict = self.function_profiler.profile()(pipeline.batch_predict)

            # 執行分析
            _ = batch_predict(test_data, batch_size=100)

            # 測試不同批次大小
            batch_sizes = [10, 50, 100, 200, 500]
            batch_results = {}

            for batch_size in batch_sizes:
                start_time = time.time()
                _ = pipeline.batch_predict(test_data, batch_size=batch_size)
                end_time = time.time()
                batch_results[batch_size] = end_time - start_time

            # 記錄結果
            self.profiling_results["model_inference"] = {
                "batch_results": batch_results,
            }

            # 繪製批次大小與執行時間的關係圖
            plt.figure(figsize=(10, 6))
            plt.plot(
                list(batch_results.keys()), list(batch_results.values()), marker="o"
            )
            plt.xlabel("Batch Size")
            plt.ylabel("Execution Time (s)")
            plt.title("Model Inference Performance by Batch Size")
            plt.grid(True)
            plt.savefig(os.path.join(self.output_dir, "batch_size_performance.png"))

        except Exception as e:
            logger.error(f"模型推論性能分析時發生錯誤: {e}")

        logger.info("模型推論性能分析完成")

    def identify_bottlenecks(self):
        """識別系統瓶頸"""
        logger.info("開始識別系統瓶頸")

        # 使用性能優化器識別瓶頸
        bottlenecks = self.performance_optimizer.identify_bottlenecks()

        # 記錄結果
        self.profiling_results["bottlenecks"] = bottlenecks

        logger.info("系統瓶頸識別完成")

        return bottlenecks

    def generate_report(self):
        """生成性能報告"""
        logger.info("開始生成性能報告")

        # 報告時間戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 報告檔案路徑
        report_path = os.path.join(
            self.output_dir, f"performance_report_{timestamp}.md"
        )

        # 生成報告內容
        report_content = f"""# 系統性能分析報告

## 生成時間
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 主流程性能分析

"""

        # 添加主流程分析結果
        if "main_flow" in self.profiling_results:
            report_content += (
                f"### 執行模式: {self.profiling_results['main_flow']['mode']}\n\n"
            )

            # 添加函數分析結果
            for func_name, result in self.function_profiler.profiling_results.items():
                if "main" in func_name:
                    report_content += f"#### 函數: {func_name}\n"
                    report_content += f"- 分析檔案: {result['filepath']}\n"
                    report_content += f"- 時間戳: {result['timestamp']}\n\n"

        # 添加資料處理分析結果
        report_content += """## 資料處理性能分析

"""
        for func_name, result in self.function_profiler.profiling_results.items():
            if "load_data" in func_name or "compute_features" in func_name:
                report_content += f"### 函數: {func_name}\n"
                report_content += f"- 分析檔案: {result['filepath']}\n"
                report_content += f"- 時間戳: {result['timestamp']}\n\n"

        # 添加模型推論分析結果
        report_content += """## 模型推論性能分析

"""
        if "model_inference" in self.profiling_results:
            report_content += "### 批次大小性能比較\n\n"
            report_content += "| 批次大小 | 執行時間 (秒) |\n"
            report_content += "|----------|---------------|\n"

            for batch_size, execution_time in self.profiling_results["model_inference"][
                "batch_results"
            ].items():
                report_content += f"| {batch_size} | {execution_time:.6f} |\n"

            report_content += "\n![批次大小性能圖](batch_size_performance.png)\n\n"

        # 添加瓶頸分析結果
        report_content += """## 系統瓶頸分析

"""
        if "bottlenecks" in self.profiling_results:
            bottlenecks = self.profiling_results["bottlenecks"]

            for category, items in bottlenecks.items():
                report_content += f"### {category.capitalize()} 瓶頸\n\n"

                if isinstance(items, dict):
                    for name, details in items.items():
                        report_content += f"#### {name}\n"
                        for key, value in details.items():
                            report_content += f"- {key}: {value}\n"
                        report_content += "\n"

        # 添加優化建議
        report_content += """## 優化建議

### 資料處理優化
- 考慮使用資料分區策略減少載入時間
- 實施增量更新機制
- 優化特徵計算，考慮使用 Dask 或 Ray 進行分散式處理

### 模型推論優化
- 使用批次推論提高吞吐量
- 考慮將模型轉換為 ONNX 格式以提高推論速度
- 實施模型量化以減少記憶體使用

### 系統資源優化
- 監控並限制記憶體使用
- 優化 I/O 操作，減少磁碟讀寫
- 考慮使用快取機制減少重複計算
"""

        # 寫入報告檔案
        with open(report_path, "w") as f:
            f.write(report_content)

        logger.info(f"性能報告已生成: {report_path}")

        return report_path


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="系統性能分析工具")
    parser.add_argument(
        "--mode",
        type=str,
        default="backtest",
        choices=["backtest", "paper", "live"],
        help="執行模式",
    )
    parser.add_argument("--output-dir", type=str, default=None, help="輸出目錄")
    parser.add_argument("--profile-main", action="store_true", help="分析主流程性能")
    parser.add_argument("--profile-data", action="store_true", help="分析資料處理性能")
    parser.add_argument("--profile-model", action="store_true", help="分析模型推論性能")
    parser.add_argument(
        "--identify-bottlenecks", action="store_true", help="識別系統瓶頸"
    )
    parser.add_argument("--all", action="store_true", help="執行所有分析")
    args = parser.parse_args()

    # 創建系統性能分析器
    profiler = SystemProfiler(args.output_dir)

    # 執行分析
    if args.all or args.profile_main:
        profiler.profile_main_flow(args.mode)

    if args.all or args.profile_data:
        profiler.profile_data_processing()

    if args.all or args.profile_model:
        profiler.profile_model_inference()

    if args.all or args.identify_bottlenecks:
        profiler.identify_bottlenecks()

    # 生成報告
    profiler.generate_report()


if __name__ == "__main__":
    main()
