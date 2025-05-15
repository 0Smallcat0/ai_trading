# -*- coding: utf-8 -*-
"""
執行策略調整腳本

此腳本用於執行策略重新回測和參數調整。
主要功能：
- 根據市場變化重新回測策略
- 調整策略參數以提高性能
- 記錄和比較優化前後的結果
- 生成策略優化報告
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.config import LOG_LEVEL, RESULTS_DIR
from src.maintenance.strategy_rebacktester import StrategyRebacktester
from src.maintenance.strategy_tuner import StrategyTuner
from src.utils.utils import ensure_dir

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


def parse_args():
    """解析命令行參數"""
    parser = argparse.ArgumentParser(description="執行策略調整")

    # 策略相關參數
    parser.add_argument("--strategy", type=str, required=True, help="策略名稱")
    parser.add_argument("--params-file", type=str, help="策略參數檔案路徑")

    # 回測相關參數
    parser.add_argument("--start-date", type=str, help="回測開始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="回測結束日期 (YYYY-MM-DD)")
    parser.add_argument(
        "--reference-period", type=int, default=90, help="市場變化參考期間（天數）"
    )

    # 優化相關參數
    parser.add_argument("--optimize", action="store_true", help="是否優化策略參數")
    parser.add_argument("--param-grid-file", type=str, help="參數網格檔案路徑")
    parser.add_argument(
        "--optimization-metric", type=str, default="sharpe_ratio", help="優化指標"
    )

    # 邏輯調整相關參數
    parser.add_argument("--adjust-logic", action="store_true", help="是否調整策略邏輯")
    parser.add_argument("--adjustments-file", type=str, help="邏輯調整檔案路徑")

    # 機器學習相關參數
    parser.add_argument("--ml-strategy", action="store_true", help="是否為機器學習策略")
    parser.add_argument("--model-type", type=str, help="模型類型")
    parser.add_argument("--features-file", type=str, help="特徵資料檔案路徑")
    parser.add_argument("--target-file", type=str, help="目標資料檔案路徑")
    parser.add_argument("--test-size", type=float, default=0.3, help="測試集比例")
    parser.add_argument("--scoring", type=str, default="f1", help="評分指標")

    # 輸出相關參數
    parser.add_argument("--output-dir", type=str, help="輸出目錄")
    parser.add_argument("--generate-report", action="store_true", help="是否生成報告")

    return parser.parse_args()


def load_json_file(file_path):
    """載入 JSON 檔案"""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"載入 JSON 檔案 {file_path} 時發生錯誤: {e}")
        return {}


def load_data_file(file_path):
    """載入資料檔案"""
    try:
        import pandas as pd

        return pd.read_csv(file_path, index_col=0)
    except Exception as e:
        logger.error(f"載入資料檔案 {file_path} 時發生錯誤: {e}")
        return None


def run_rebacktest(args):
    """執行策略重新回測"""
    # 創建策略重新回測器
    rebacktester = StrategyRebacktester(args.output_dir)

    # 解析日期
    start_date = (
        datetime.strptime(args.start_date, "%Y-%m-%d") if args.start_date else None
    )
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d") if args.end_date else None

    # 載入策略參數
    if args.params_file:
        strategy_params = load_json_file(args.params_file)
    else:
        # 使用預設參數
        if args.strategy == "moving_average_crossover":
            strategy_params = {"short_window": 20, "long_window": 50}
        elif args.strategy == "rsi":
            strategy_params = {"rsi_period": 14, "overbought": 70, "oversold": 30}
        elif args.strategy == "bollinger_bands":
            strategy_params = {"window": 20, "num_std": 2}
        elif args.strategy == "ml_strategy":
            strategy_params = {
                "model_type": "random_forest",
                "n_estimators": 100,
                "max_depth": 5,
            }
        else:
            strategy_params = {}

    # 分析市場變化
    market_changes = rebacktester.analyze_market_changes(
        start_date, end_date, args.reference_period
    )
    logger.info(f"市場變化分析結果: {market_changes}")

    # 重新回測策略
    results = rebacktester.rebacktest_strategy(
        args.strategy, strategy_params, start_date, end_date
    )
    logger.info(f"重新回測結果: {results}")

    return rebacktester


def run_optimization(args, rebacktester=None):
    """執行策略參數優化"""
    # 創建策略調整器
    tuner = StrategyTuner(args.output_dir)

    # 解析日期
    start_date = (
        datetime.strptime(args.start_date, "%Y-%m-%d") if args.start_date else None
    )
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d") if args.end_date else None

    # 載入策略參數
    if args.params_file:
        current_params = load_json_file(args.params_file)
    else:
        # 使用預設參數
        if args.strategy == "moving_average_crossover":
            current_params = {"short_window": 20, "long_window": 50}
        elif args.strategy == "rsi":
            current_params = {"rsi_period": 14, "overbought": 70, "oversold": 30}
        elif args.strategy == "bollinger_bands":
            current_params = {"window": 20, "num_std": 2}
        elif args.strategy == "ml_strategy":
            current_params = {
                "model_type": "random_forest",
                "n_estimators": 100,
                "max_depth": 5,
            }
        else:
            current_params = {}

    # 載入參數網格
    if args.param_grid_file:
        param_grid = load_json_file(args.param_grid_file)
    else:
        # 使用預設參數網格
        if args.strategy == "moving_average_crossover":
            param_grid = {
                "short_window": [5, 10, 15, 20, 25],
                "long_window": [30, 40, 50, 60, 70],
            }
        elif args.strategy == "rsi":
            param_grid = {
                "rsi_period": [7, 14, 21],
                "overbought": [65, 70, 75, 80],
                "oversold": [20, 25, 30, 35],
            }
        elif args.strategy == "bollinger_bands":
            param_grid = {
                "window": [10, 20, 30],
                "num_std": [1.5, 2.0, 2.5],
            }
        elif args.strategy == "ml_strategy":
            param_grid = {
                "n_estimators": [50, 100, 200],
                "max_depth": [3, 5, 7, 10],
                "min_samples_split": [2, 5, 10],
            }
        else:
            param_grid = {}

    # 執行參數優化
    if args.ml_strategy:
        # 載入特徵和目標資料
        features_df = load_data_file(args.features_file)
        target_df = load_data_file(args.target_file)

        if features_df is None or target_df is None:
            logger.error("無法載入特徵或目標資料")
            return None

        # 執行機器學習策略調整
        results = tuner.tune_ml_strategy(
            args.strategy,
            args.model_type,
            current_params,
            param_grid,
            features_df,
            target_df,
            args.test_size,
            args.scoring,
        )
    else:
        # 執行一般策略參數調整
        results = tuner.tune_strategy_parameters(
            args.strategy,
            current_params,
            param_grid,
            start_date,
            end_date,
            args.optimization_metric,
        )

    logger.info(f"參數優化結果: {results}")

    # 生成版本歷史報告
    if args.generate_report:
        report_path = tuner.generate_version_history_report(args.strategy)
        logger.info(f"版本歷史報告已生成: {report_path}")

    return tuner


def run_logic_adjustment(args, tuner=None):
    """執行策略邏輯調整"""
    # 創建策略調整器（如果尚未創建）
    if tuner is None:
        tuner = StrategyTuner(args.output_dir)

    # 解析日期
    start_date = (
        datetime.strptime(args.start_date, "%Y-%m-%d") if args.start_date else None
    )
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d") if args.end_date else None

    # 載入策略邏輯
    if args.params_file:
        current_logic = load_json_file(args.params_file)
    else:
        # 使用預設邏輯
        if args.strategy == "moving_average_crossover":
            current_logic = {
                "short_window": 20,
                "long_window": 50,
                "signal_threshold": 0,
            }
        elif args.strategy == "rsi":
            current_logic = {
                "rsi_period": 14,
                "overbought": 70,
                "oversold": 30,
                "use_divergence": False,
            }
        elif args.strategy == "bollinger_bands":
            current_logic = {"window": 20, "num_std": 2, "use_volume": False}
        else:
            current_logic = {}

    # 載入邏輯調整
    if args.adjustments_file:
        adjustments = load_json_file(args.adjustments_file)
    else:
        # 使用預設調整
        if args.strategy == "moving_average_crossover":
            adjustments = {"signal_threshold": 0.01}
        elif args.strategy == "rsi":
            adjustments = {"use_divergence": True}
        elif args.strategy == "bollinger_bands":
            adjustments = {"use_volume": True}
        else:
            adjustments = {}

    # 執行邏輯調整
    results = tuner.adjust_strategy_logic(
        args.strategy, current_logic, adjustments, start_date, end_date
    )

    logger.info(f"邏輯調整結果: {results}")

    # 生成版本歷史報告
    if args.generate_report:
        report_path = tuner.generate_version_history_report(args.strategy)
        logger.info(f"版本歷史報告已生成: {report_path}")

    return tuner


def main():
    """主函數"""
    # 解析命令行參數
    args = parse_args()

    # 設定輸出目錄
    if args.output_dir is None:
        args.output_dir = os.path.join(RESULTS_DIR, "strategy_adjustment")
    ensure_dir(args.output_dir)

    # 執行策略重新回測
    rebacktester = run_rebacktest(args)

    # 執行策略參數優化
    if args.optimize:
        tuner = run_optimization(args, rebacktester)

    # 執行策略邏輯調整
    if args.adjust_logic:
        tuner = run_logic_adjustment(args, tuner if args.optimize else None)


if __name__ == "__main__":
    main()
