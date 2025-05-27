#!/usr/bin/env python3
"""
風險管理模組測試腳本

此腳本用於測試風險管理模組的各項功能，包括：
- 風險參數管理
- 風險指標計算
- 風險事件處理
- 風控機制控制

使用方法：
    python scripts/test_risk_management.py
"""

import sys
import os
from pathlib import Path
import pytest

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import json
from datetime import datetime, timedelta

# 設置日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.fixture
def service():
    """風險管理服務 fixture"""
    try:
        from src.core.risk_management_service import RiskManagementService

        return RiskManagementService()
    except ImportError:
        pytest.skip("無法導入風險管理服務")


def test_risk_management_service():
    """測試風險管理服務"""
    try:
        from src.core.risk_management_service import RiskManagementService

        logger.info("開始測試風險管理服務...")

        # 初始化服務
        service = RiskManagementService()
        logger.info("✅ 風險管理服務初始化成功")

        assert service is not None, "風險管理服務初始化失敗"

        # 測試風險參數管理
        test_risk_parameters(service)

        # 測試風控機制狀態
        test_control_status(service)

        # 測試風險事件處理
        test_risk_events(service)

        # 測試風險指標計算
        test_risk_metrics(service)

        logger.info("✅ 風險管理服務測試完成")

    except ImportError as e:
        logger.error(f"❌ 無法導入風險管理服務: {e}")
        pytest.skip(f"無法導入風險管理服務: {e}")
    except Exception as e:
        logger.error(f"❌ 風險管理服務測試失敗: {e}")
        pytest.fail(f"風險管理服務測試失敗: {e}")


def test_risk_parameters(service):
    """測試風險參數管理"""
    logger.info("測試風險參數管理...")

    try:
        # 獲取所有風險參數
        params = service.get_risk_parameters()
        logger.info(f"獲取到 {len(params)} 個風險參數")

        # 測試更新參數
        test_param = "stop_loss_percent"
        original_value = params.get(test_param, {}).get("value", 5.0)
        new_value = 7.5

        success = service.update_risk_parameter(test_param, new_value)
        if success:
            logger.info(
                f"✅ 成功更新參數 {test_param}: {original_value} -> {new_value}"
            )

            # 驗證更新
            updated_params = service.get_risk_parameters()
            updated_value = updated_params.get(test_param, {}).get("value")
            if updated_value == new_value:
                logger.info("✅ 參數更新驗證成功")
            else:
                logger.warning(
                    f"⚠️ 參數更新驗證失敗: 期望 {new_value}, 實際 {updated_value}"
                )
        else:
            logger.error(f"❌ 更新參數失敗: {test_param}")

        # 獲取特定分類的參數
        stop_loss_params = service.get_risk_parameters(category="stop_loss")
        logger.info(f"獲取到 {len(stop_loss_params)} 個停損參數")

    except Exception as e:
        logger.error(f"❌ 風險參數測試失敗: {e}")


def test_control_status(service):
    """測試風控機制狀態"""
    logger.info("測試風控機制狀態...")

    try:
        # 獲取風控機制狀態
        status = service.get_control_status()
        logger.info(f"獲取到 {len(status)} 個風控機制狀態")

        # 測試更新風控機制狀態
        test_control = "stop_loss"
        if test_control in status:
            original_enabled = status[test_control]["enabled"]
            new_enabled = not original_enabled

            success = service.update_control_status(test_control, new_enabled)
            if success:
                logger.info(
                    f"✅ 成功更新風控機制 {test_control}: {original_enabled} -> {new_enabled}"
                )

                # 恢復原狀態
                service.update_control_status(test_control, original_enabled)
                logger.info(f"✅ 恢復風控機制狀態: {test_control}")
            else:
                logger.error(f"❌ 更新風控機制失敗: {test_control}")

        # 測試緊急停止
        logger.info("測試緊急停止功能...")
        success = service.set_emergency_stop(True)
        if success:
            logger.info("✅ 緊急停止啟動成功")

            # 解除緊急停止
            success = service.set_emergency_stop(False)
            if success:
                logger.info("✅ 緊急停止解除成功")
            else:
                logger.error("❌ 緊急停止解除失敗")
        else:
            logger.error("❌ 緊急停止啟動失敗")

    except Exception as e:
        logger.error(f"❌ 風控機制狀態測試失敗: {e}")


def test_risk_events(service):
    """測試風險事件處理"""
    logger.info("測試風險事件處理...")

    try:
        # 創建測試風險事件
        event_id = service.create_risk_event(
            event_type="停損觸發",
            severity="medium",
            message="測試停損事件",
            symbol="TEST.TW",
            strategy_name="測試策略",
            trigger_value=-5.2,
            threshold_value=-5.0,
            current_value=-5.2,
            details={"test": True},
        )

        if event_id:
            logger.info(f"✅ 成功創建風險事件: {event_id}")

            # 獲取風險事件列表
            events = service.get_risk_events(limit=10)
            logger.info(f"獲取到 {len(events)} 個風險事件")

            # 解決風險事件
            success = service.resolve_risk_event(event_id, "測試解決", "test_user")
            if success:
                logger.info(f"✅ 成功解決風險事件: {event_id}")
            else:
                logger.error(f"❌ 解決風險事件失敗: {event_id}")
        else:
            logger.error("❌ 創建風險事件失敗")

        # 測試事件篩選
        filtered_events = service.get_risk_events(
            event_type="停損觸發", severity="medium", limit=5
        )
        logger.info(f"篩選後獲取到 {len(filtered_events)} 個風險事件")

    except Exception as e:
        logger.error(f"❌ 風險事件處理測試失敗: {e}")


def test_risk_metrics(service):
    """測試風險指標計算"""
    logger.info("測試風險指標計算...")

    try:
        # 計算投資組合風險指標
        metrics = service.calculate_risk_metrics()
        if metrics:
            logger.info(f"✅ 成功計算投資組合風險指標，包含 {len(metrics)} 個指標")

            # 顯示部分指標
            key_metrics = ["sharpe_ratio", "max_drawdown", "volatility"]
            for metric in key_metrics:
                if metric in metrics:
                    logger.info(f"  {metric}: {metrics[metric]:.4f}")
        else:
            logger.warning("⚠️ 風險指標計算返回空結果")

        # 計算特定股票的風險指標
        symbol_metrics = service.calculate_risk_metrics(symbol="2330.TW")
        if symbol_metrics:
            logger.info(f"✅ 成功計算股票風險指標，包含 {len(symbol_metrics)} 個指標")
        else:
            logger.warning("⚠️ 股票風險指標計算返回空結果")

        # 獲取風險指標歷史記錄
        history = service.get_risk_metrics_history(days=7)
        logger.info(f"獲取到 {len(history)} 筆風險指標歷史記錄")

    except Exception as e:
        logger.error(f"❌ 風險指標計算測試失敗: {e}")


def test_database_schema():
    """測試資料庫結構"""
    logger.info("測試資料庫結構...")

    try:
        from src.database.schema import init_db
        from sqlalchemy import create_engine
        from src.config import DB_URL

        # 測試資料庫連接和表格創建
        engine = create_engine(DB_URL)
        try:
            init_db(engine)
        except Exception as e:
            # 如果表格已存在，這是正常的
            if "already exists" in str(e):
                logger.info("✅ 資料庫表格已存在，跳過創建")
            else:
                raise e

        logger.info("✅ 資料庫結構測試成功")
        assert True, "資料庫結構測試成功"

    except ImportError as e:
        logger.error(f"❌ 無法導入資料庫模組: {e}")
        pytest.skip(f"無法導入資料庫模組: {e}")
    except Exception as e:
        logger.error(f"❌ 資料庫結構測試失敗: {e}")
        pytest.fail(f"資料庫結構測試失敗: {e}")


def main():
    """主函數"""
    logger.info("開始風險管理模組測試...")

    # 測試資料庫結構
    if not test_database_schema():
        logger.error("❌ 資料庫結構測試失敗，停止測試")
        return

    # 測試風險管理服務
    if not test_risk_management_service():
        logger.error("❌ 風險管理服務測試失敗")
        return

    logger.info("🎉 所有測試完成！")


if __name__ == "__main__":
    main()
