# -*- coding: utf-8 -*-
"""
執行性能分析和優化腳本

此腳本用於執行系統性能分析和優化。
主要功能：
- 執行系統性能分析
- 識別性能瓶頸
- 優化系統性能
- 生成性能報告
"""

import argparse
import os
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.config import RESULTS_DIR
from src.core.logger import get_logger
from src.maintenance.performance_optimizer import PerformanceOptimizer
from src.maintenance.system_profiler import SystemProfiler
from src.models.model_optimizer import ModelOptimizer

# 設定日誌
logger = get_logger("performance_profiling")


def run_profiling(args):
    """
    執行性能分析

    Args:
        args: 命令行參數
    """
    logger.info("開始執行性能分析")

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
        bottlenecks = profiler.identify_bottlenecks()
        logger.info(f"識別到的瓶頸: {bottlenecks}")

    # 生成報告
    report_path = profiler.generate_report()
    logger.info(f"性能報告已生成: {report_path}")

    return profiler


def optimize_performance(args, profiler=None):
    """
    優化系統性能

    Args:
        args: 命令行參數
        profiler: 系統性能分析器，如果為 None，則創建新的分析器
    """
    logger.info("開始優化系統性能")

    # 如果沒有提供分析器，則創建新的分析器
    if profiler is None:
        profiler = SystemProfiler(args.output_dir)
        bottlenecks = profiler.identify_bottlenecks()
    else:
        bottlenecks = profiler.profiling_results.get("bottlenecks", {})

    # 創建性能優化器
    optimizer = PerformanceOptimizer()

    # 優化瓶頸
    optimization_results = optimizer.optimize(bottlenecks)
    logger.info(f"優化結果: {optimization_results}")

    # 如果需要優化模型
    if args.optimize_model:
        optimize_models(args)

    return optimization_results


def optimize_models(args):
    """
    優化模型性能

    Args:
        args: 命令行參數
    """
    logger.info("開始優化模型性能")

    # 創建模型優化器
    model_optimizer = ModelOptimizer()

    # 檢查 ONNX 是否可用
    if (
        not hasattr(model_optimizer, "ONNX_AVAILABLE")
        or not model_optimizer.ONNX_AVAILABLE
    ):
        logger.warning("ONNX 相關套件未安裝，無法使用 ONNX 優化功能")
        return

    # 獲取模型列表
    try:
        from src.models.model_factory import create_model, list_models

        models = list_models()
    except (ImportError, AttributeError):
        logger.warning("無法獲取模型列表，將使用預設模型")
        models = ["lstm", "gru", "transformer"]

    # 優化每個模型
    for model_name in models:
        try:
            # 創建模型
            model = create_model(model_name)

            # 創建測試資料
            import numpy as np

            test_data = np.random.random((100, 10)).astype(np.float32)
            input_shape = (1, 10)

            # 轉換為 ONNX
            onnx_path = model_optimizer.convert_to_onnx(model, model_name, input_shape)

            # 比較性能
            performance_results = model_optimizer.compare_performance(
                model, onnx_path, test_data
            )

            logger.info(f"模型 {model_name} 優化結果:")
            logger.info(f"原始模型執行時間: {performance_results['original']}")
            logger.info(f"ONNX 模型執行時間: {performance_results['onnx']}")
            logger.info(f"加速比: {performance_results['speedup']}")

        except Exception as e:
            logger.error(f"優化模型 {model_name} 時發生錯誤: {e}")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="系統性能分析和優化工具")
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
    parser.add_argument("--optimize", action="store_true", help="優化系統性能")
    parser.add_argument("--optimize-model", action="store_true", help="優化模型性能")
    parser.add_argument("--all", action="store_true", help="執行所有分析和優化")
    args = parser.parse_args()

    # 設定輸出目錄
    if args.output_dir is None:
        args.output_dir = os.path.join(RESULTS_DIR, "profiling")
    os.makedirs(args.output_dir, exist_ok=True)

    # 執行性能分析
    profiler = None
    if (
        args.all
        or args.profile_main
        or args.profile_data
        or args.profile_model
        or args.identify_bottlenecks
    ):
        profiler = run_profiling(args)

    # 執行性能優化
    if args.all or args.optimize or args.optimize_model:
        optimize_performance(args, profiler)


if __name__ == "__main__":
    main()
