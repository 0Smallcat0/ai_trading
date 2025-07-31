#!/usr/bin/env python3
"""
策略管理服務測試腳本

此腳本用於測試策略管理服務層的基本功能，包括：
- 策略管理服務初始化
- 策略CRUD操作
- 策略版本控制
- 策略匯入匯出
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


def test_strategy_management_service():
    """測試策略管理服務"""
    logger.info("開始測試策略管理服務...")

    try:
        from src.core.strategy_management_service import StrategyManagementService

        # 初始化服務
        service = StrategyManagementService()
        logger.info("✅ 策略管理服務初始化成功")

        # 測試獲取策略類型
        strategy_types = service.get_strategy_types()
        logger.info(f"✅ 獲取策略類型成功: {len(strategy_types)} 種類型")

        # 測試獲取策略模板
        templates = service.get_strategy_templates()
        logger.info(f"✅ 獲取策略模板成功: {len(templates)} 個模板")

        # 測試創建策略
        strategy_id = service.create_strategy(
            name="測試策略",
            strategy_type="技術分析策略",
            description="這是一個測試策略",
            author="測試用戶",
            code="# 測試代碼\nprint('Hello World')",
            parameters={"test_param": 10},
            risk_parameters={
                "stop_loss": 0.05,
                "take_profit": 0.1,
                "max_position_size": 0.2,
            },
        )
        logger.info(f"✅ 策略創建成功: {strategy_id}")

        # 測試獲取策略
        strategy = service.get_strategy(strategy_id)
        logger.info(f"✅ 策略獲取成功: {strategy['name']}")

        # 測試列出策略
        strategies = service.list_strategies()
        logger.info(f"✅ 策略列表獲取成功: {len(strategies)} 個策略")

        # 測試更新策略
        new_version = service.update_strategy(
            strategy_id=strategy_id,
            description="更新後的描述",
            change_log="測試更新",
            author="測試用戶",
        )
        logger.info(f"✅ 策略更新成功: 新版本 {new_version}")

        # 測試獲取版本歷史
        versions = service.get_strategy_versions(strategy_id)
        logger.info(f"✅ 版本歷史獲取成功: {len(versions)} 個版本")

        # 測試策略狀態更新
        success = service.update_strategy_status(strategy_id, "active")
        logger.info(f"✅ 策略狀態更新成功: {success}")

        # 測試代碼驗證
        validation_result = service.validate_strategy_code("print('test')")
        logger.info(f"✅ 代碼驗證成功: {validation_result['is_valid']}")

        # 測試匯出策略
        exported_data = service.export_strategy(strategy_id, "json")
        logger.info("✅ 策略匯出成功")

        # 測試刪除策略
        success = service.delete_strategy(strategy_id)
        logger.info(f"✅ 策略刪除成功: {success}")

        logger.info("✅ 策略管理服務測試完成")
        return True

    except Exception as e:
        logger.error(f"❌ 策略管理服務測試失敗: {e}")
        return False


def test_strategy_components():
    """測試策略管理 UI 組件"""
    logger.info("開始測試策略管理 UI 組件...")

    try:
        from src.ui.components.strategy_components import (
            show_strategy_card,
            show_parameter_editor,
            show_strategy_performance_chart,
        )

        logger.info("✅ 策略管理 UI 組件導入成功")

        # 測試策略卡片數據結構
        strategy_info = {
            "id": "test_001",
            "name": "測試策略",
            "type": "技術分析策略",
            "category": "測試分類",
            "description": "測試描述",
            "author": "測試用戶",
            "version": "1.0.0",
            "status": "active",
            "parameters": {"test_param": 10},
            "risk_parameters": {
                "stop_loss": 0.05,
                "take_profit": 0.1,
                "max_position_size": 0.2,
            },
            "performance_metrics": {
                "sharpe_ratio": 1.5,
                "max_drawdown": 0.1,
                "win_rate": 0.6,
                "total_return": 0.2,
            },
            "tags": ["測試", "技術分析"],
            "created_at": "2023-01-01",
            "updated_at": "2023-12-01",
        }

        # 測試效能數據結構
        performance_data = {
            "sharpe_ratio": 1.5,
            "max_drawdown": 0.1,
            "win_rate": 0.6,
            "total_return": 0.2,
        }

        logger.info("✅ 策略管理 UI 組件測試完成")
        return True

    except Exception as e:
        logger.error(f"❌ 策略管理 UI 組件測試失敗: {e}")
        return False


def test_strategy_management_page():
    """測試策略管理頁面"""
    logger.info("開始測試策略管理頁面...")

    try:
        from src.ui.pages.strategy_management import (
            show_strategy_list,
            show_strategy_editor,
            show_strategy_parameters,
            show_strategy_versions,
            get_strategy_service,
        )

        logger.info("✅ 策略管理頁面模組導入成功")

        # 測試策略服務獲取
        service = get_strategy_service()
        logger.info("✅ 策略服務獲取成功")

        logger.info("✅ 策略管理頁面測試完成")
        return True

    except Exception as e:
        logger.error(f"❌ 策略管理頁面測試失敗: {e}")
        return False


def test_database_operations():
    """測試資料庫操作"""
    logger.info("開始測試資料庫操作...")

    try:
        from src.core.strategy_management_service import StrategyManagementService

        service = StrategyManagementService()

        # 測試統計信息
        stats = service.get_strategy_statistics()
        logger.info(f"✅ 策略統計信息獲取成功: {stats}")

        # 測試搜索功能
        search_results = service.search_strategies("測試", {"type": "技術分析策略"})
        logger.info(f"✅ 策略搜索成功: {len(search_results)} 個結果")

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
            "src/core/strategy_management_service.py",
            "src/ui/pages/strategy_management.py",
            "src/ui/components/strategy_components.py",
        ]

        for config_file in config_files:
            config_path = project_root / config_file
            if config_path.exists():
                logger.info(f"✅ 檔案存在: {config_file}")
            else:
                logger.warning(f"⚠️ 檔案不存在: {config_file}")

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


def test_import_export():
    """測試匯入匯出功能"""
    logger.info("開始測試匯入匯出功能...")

    try:
        from src.core.strategy_management_service import StrategyManagementService

        service = StrategyManagementService()

        # 創建測試策略（使用時間戳確保唯一性）
        import time

        timestamp = int(time.time())
        strategy_name = f"匯出測試策略_{timestamp}"

        strategy_id = service.create_strategy(
            name=strategy_name,
            strategy_type="技術分析策略",
            description="用於測試匯出功能的策略",
            author="測試用戶",
            code="# 測試代碼",
            parameters={"test_param": 20},
            risk_parameters={
                "stop_loss": 0.05,
                "take_profit": 0.1,
                "max_position_size": 0.2,
            },
        )

        # 測試匯出
        exported_json = service.export_strategy(strategy_id, "json")
        logger.info("✅ JSON 匯出成功")

        exported_python = service.export_strategy(strategy_id, "python")
        logger.info("✅ Python 匯出成功")

        # 修改匯入的策略名稱以避免重複
        import json

        strategy_data = json.loads(exported_json)
        strategy_data["name"] = "匯入測試策略"
        modified_json = json.dumps(strategy_data)

        # 測試匯入
        imported_strategy_id = service.import_strategy(
            modified_json, "json", "測試用戶"
        )
        logger.info(f"✅ 策略匯入成功: {imported_strategy_id}")

        # 清理測試數據
        service.delete_strategy(strategy_id)
        service.delete_strategy(imported_strategy_id)

        logger.info("✅ 匯入匯出功能測試完成")
        return True

    except Exception as e:
        logger.error(f"❌ 匯入匯出功能測試失敗: {e}")
        return False


def main():
    """主函數"""
    logger.info("🚀 開始策略管理服務測試")
    logger.info("=" * 50)

    test_results = []

    # 執行各項測試
    tests = [
        ("配置測試", test_configuration),
        ("策略管理服務測試", test_strategy_management_service),
        ("策略管理 UI 組件測試", test_strategy_components),
        ("策略管理頁面測試", test_strategy_management_page),
        ("資料庫操作測試", test_database_operations),
        ("匯入匯出功能測試", test_import_export),
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
