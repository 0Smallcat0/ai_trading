#!/usr/bin/env python3
"""
特徵工程服務測試腳本

此腳本用於測試特徵工程服務層的基本功能，包括：
- 特徵工程服務初始化
- 特徵計算功能
- 特徵查詢功能
- 特徵處理功能
- UI 組件功能
"""

import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta

# 設置日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_feature_engineering_service():
    """測試特徵工程服務"""
    logger.info("開始測試特徵工程服務...")

    try:
        from src.core.feature_engineering_service import FeatureEngineeringService

        # 初始化服務
        service = FeatureEngineeringService()
        logger.info("✅ 特徵工程服務初始化成功")

        # 測試獲取可用特徵
        available_features = service.get_available_features()
        logger.info(f"✅ 獲取可用特徵成功: {len(available_features)} 種類型")

        # 測試特徵計算
        task_id = service.start_feature_calculation(
            feature_type="technical",
            stock_ids=["2330.TW", "AAPL"],
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
            indicators=["RSI", "MACD"],
        )
        logger.info(f"✅ 特徵計算任務啟動成功: {task_id}")

        # 等待任務完成
        import time

        max_wait = 10
        wait_count = 0

        while wait_count < max_wait:
            task_status = service.get_task_status(task_id)
            if task_status.get("status") in ["completed", "failed"]:
                break
            time.sleep(1)
            wait_count += 1

        final_status = service.get_task_status(task_id)
        logger.info(f"✅ 任務狀態: {final_status.get('status')}")

        # 測試特徵查詢
        features_df = service.query_features(
            feature_type="technical", stock_ids=["2330.TW"], limit=10
        )
        logger.info(f"✅ 特徵查詢成功: {len(features_df)} 筆記錄")

        # 測試特徵統計
        if not features_df.empty:
            feature_name = features_df["feature_name"].iloc[0]
            stats = service.get_feature_statistics(feature_name)
            logger.info(f"✅ 特徵統計成功: {feature_name}")

        logger.info("✅ 特徵工程服務測試完成")
        return True

    except Exception as e:
        logger.error(f"❌ 特徵工程服務測試失敗: {e}")
        return False


def test_feature_processing():
    """測試特徵處理功能"""
    logger.info("開始測試特徵處理功能...")

    try:
        from src.core.feature_engineering_service import FeatureEngineeringService

        service = FeatureEngineeringService()

        # 創建測試數據
        np.random.seed(42)
        test_data = pd.DataFrame(
            {
                "feature1": np.random.randn(100),
                "feature2": np.random.randn(100) * 10 + 50,
                "feature3": np.random.randn(100) * 5 + 20,
                "target": np.random.randn(100),
            }
        )

        # 測試標準化
        standardized_data, scaler_params = service.standardize_features(
            test_data,
            method="standard",
            feature_columns=["feature1", "feature2", "feature3"],
        )
        logger.info("✅ 特徵標準化測試成功")

        # 測試特徵選擇
        selected_data, selected_features = service.select_features(
            test_data, target_column="target", method="f_regression", k=2
        )
        logger.info(f"✅ 特徵選擇測試成功: 選擇了 {len(selected_features)} 個特徵")

        # 測試降維
        reduced_data, reduction_params = service.reduce_dimensions(
            test_data,
            method="pca",
            n_components=2,
            feature_columns=["feature1", "feature2", "feature3"],
        )
        logger.info("✅ 降維處理測試成功")

        # 測試異常值檢測
        outlier_data, outlier_indices = service.detect_outliers(
            test_data, feature_column="feature1", method="iqr"
        )
        logger.info(f"✅ 異常值檢測測試成功: 檢測到 {len(outlier_indices)} 個異常值")

        logger.info("✅ 特徵處理功能測試完成")
        return True

    except Exception as e:
        logger.error(f"❌ 特徵處理功能測試失敗: {e}")
        return False


def test_feature_components():
    """測試特徵工程 UI 組件"""
    logger.info("開始測試特徵工程 UI 組件...")

    try:
        from src.ui.components.feature_components import (
            show_feature_card,
            show_calculation_progress,
            show_feature_statistics_chart,
        )

        logger.info("✅ 特徵工程 UI 組件導入成功")

        # 測試特徵卡片數據結構
        feature_info = {
            "name": "RSI",
            "full_name": "相對強弱指標",
            "category": "動量指標",
            "description": "測試描述",
            "parameters": {"window": 14},
            "calculation_cost": "低",
        }

        # 測試任務狀態數據結構
        task_status = {
            "status": "completed",
            "progress": 100,
            "message": "計算完成",
            "processed_records": 100,
            "error_records": 0,
        }

        # 測試統計數據結構
        stats = {
            "count": 100,
            "mean": 50.5,
            "std": 15.2,
            "min": 10.0,
            "max": 90.0,
            "median": 52.0,
        }

        logger.info("✅ 特徵工程 UI 組件測試完成")
        return True

    except Exception as e:
        logger.error(f"❌ 特徵工程 UI 組件測試失敗: {e}")
        return False


def test_feature_engineering_page():
    """測試特徵工程頁面"""
    logger.info("開始測試特徵工程頁面...")

    try:
        from src.ui.pages.feature_engineering import (
            show_available_features,
            show_feature_calculation,
            get_stock_list,
            get_feature_service,
        )

        logger.info("✅ 特徵工程頁面模組導入成功")

        # 測試股票列表
        stocks = get_stock_list()
        logger.info(f"✅ 股票列表獲取成功: {len(stocks)} 檔股票")

        # 測試特徵服務
        feature_service = get_feature_service()
        logger.info("✅ 特徵服務獲取成功")

        logger.info("✅ 特徵工程頁面測試完成")
        return True

    except Exception as e:
        logger.error(f"❌ 特徵工程頁面測試失敗: {e}")
        return False


def test_database_operations():
    """測試資料庫操作"""
    logger.info("開始測試資料庫操作...")

    try:
        from src.core.feature_engineering_service import FeatureEngineeringService

        service = FeatureEngineeringService()

        # 測試操作日誌查詢
        logs_df = service.get_operation_logs(limit=10)
        logger.info(f"✅ 操作日誌查詢成功: {len(logs_df)} 筆記錄")

        logger.info("✅ 資料庫操作測試完成")
        return True

    except Exception as e:
        logger.error(f"❌ 資料庫操作測試失敗: {e}")
        return False


def test_configuration():
    """測試配置"""
    logger.info("開始測試配置...")

    try:
        # 檢查配置檔案
        config_files = [
            "src/config.py",
            "pyproject.toml",
        ]

        for config_file in config_files:
            config_path = project_root / config_file
            if config_path.exists():
                logger.info(f"✅ 配置檔案存在: {config_file}")
            else:
                logger.warning(f"⚠️ 配置檔案不存在: {config_file}")

        # 檢查資料目錄
        data_dirs = [
            "data",
            "logs",
            "models",
        ]

        for data_dir in data_dirs:
            dir_path = project_root / data_dir
            if dir_path.exists():
                logger.info(f"✅ 資料目錄存在: {data_dir}")
            else:
                logger.warning(f"⚠️ 資料目錄不存在: {data_dir}")

        logger.info("✅ 配置測試完成")
        return True

    except Exception as e:
        logger.error(f"❌ 配置測試失敗: {e}")
        return False


def main():
    """主函數"""
    logger.info("🚀 開始特徵工程服務測試")
    logger.info("=" * 50)

    test_results = []

    # 執行各項測試
    tests = [
        ("配置測試", test_configuration),
        ("特徵工程服務測試", test_feature_engineering_service),
        ("特徵處理功能測試", test_feature_processing),
        ("特徵工程 UI 組件測試", test_feature_components),
        ("特徵工程頁面測試", test_feature_engineering_page),
        ("資料庫操作測試", test_database_operations),
    ]

    for test_name, test_func in tests:
        logger.info(f"\n📋 執行 {test_name}...")
        logger.info("-" * 30)

        try:
            result = test_func()
            test_results.append((test_name, result))

            if result:
                logger.info(f"✅ {test_name} 通過")
            else:
                logger.error(f"❌ {test_name} 失敗")

        except Exception as e:
            logger.error(f"❌ {test_name} 執行時發生錯誤: {e}")
            test_results.append((test_name, False))

    # 顯示測試結果摘要
    logger.info("\n" + "=" * 50)
    logger.info("📊 測試結果摘要")
    logger.info("=" * 50)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1

    logger.info(f"\n總計: {passed}/{total} 項測試通過")

    if passed == total:
        logger.info("🎉 所有測試都通過了！")
        return 0
    else:
        logger.warning(f"⚠️ 有 {total - passed} 項測試失敗")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
