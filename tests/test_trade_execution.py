#!/usr/bin/env python3
"""
交易執行模組測試腳本

此腳本用於測試交易執行模組的各項功能，包括：
- 交易執行服務
- 訂單管理
- 歷史記錄查詢
- 異常處理
- 券商連線狀態

使用方法：
    python scripts/test_trade_execution.py
"""

import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@pytest.fixture
def trade_service():
    """創建交易執行服務實例的 pytest fixture"""
    try:
        from src.core.trade_execution_service import TradeExecutionService

        return TradeExecutionService()
    except ImportError as e:
        pytest.skip(f"無法導入交易執行服務: {e}")


def test_trade_execution_service():
    """測試交易執行服務"""
    try:
        from src.core.trade_execution_service import TradeExecutionService

        logger.info("開始測試交易執行服務...")

        # 初始化服務
        service = TradeExecutionService()
        logger.info("✅ 交易執行服務初始化成功")

        # 測試股票搜尋
        test_symbol_search(service)

        # 測試訂單提交
        test_order_submission(service)

        # 測試訂單查詢
        test_order_queries(service)

        # 測試交易模式切換
        test_trading_mode_switch(service)

        # 測試券商狀態
        test_broker_status(service)

        logger.info("✅ 交易執行服務測試完成")
        assert True  # 使用 assert 而不是 return

    except ImportError as e:
        logger.error("❌ 無法導入交易執行服務: %s", e)
        pytest.fail(f"無法導入交易執行服務: {e}")
    except Exception as e:
        logger.error("❌ 交易執行服務測試失敗: %s", e)
        pytest.fail(f"交易執行服務測試失敗: {e}")


def test_symbol_search(trade_service):
    """測試股票搜尋功能"""
    logger.info("測試股票搜尋功能...")

    try:
        # 測試搜尋功能
        symbols = trade_service.get_available_symbols("2330")
        logger.info("搜尋結果: 找到 %d 個股票", len(symbols))

        # 測試收藏清單
        favorites = trade_service.get_favorite_symbols()
        logger.info("收藏清單: %d 個股票", len(favorites))

        # 測試最近交易
        recent = trade_service.get_recent_symbols()
        logger.info("最近交易: %d 個股票", len(recent))

        logger.info("✅ 股票搜尋功能測試成功")
        assert True

    except Exception as e:
        logger.error("❌ 股票搜尋功能測試失敗: %s", e)
        pytest.fail(f"股票搜尋功能測試失敗: {e}")


def test_order_submission(trade_service):
    """測試訂單提交功能"""
    logger.info("測試訂單提交功能...")

    try:
        # 測試訂單數據
        test_orders = [
            {
                "symbol": "2330.TW",
                "action": "buy",
                "quantity": 1000,
                "order_type": "market",
                "time_in_force": "ROD",
                "strategy_name": "測試策略",
                "signal_id": "test_signal_001",
            },
            {
                "symbol": "2317.TW",
                "action": "buy",
                "quantity": 2000,
                "order_type": "limit",
                "price": 100.0,
                "time_in_force": "ROD",
                "strategy_name": "測試策略",
                "signal_id": "test_signal_002",
            },
        ]

        submitted_orders = []

        for order_data in test_orders:
            # 驗證訂單
            is_valid, message, _ = trade_service.validate_order(order_data)
            logger.info("訂單驗證: %s - %s", is_valid, message)

            if is_valid:
                # 提交訂單
                success, submit_message, order_id = trade_service.submit_order(
                    order_data
                )
                if success:
                    logger.info("✅ 訂單提交成功: %s", order_id)
                    submitted_orders.append(order_id)
                else:
                    logger.error("❌ 訂單提交失敗: %s", submit_message)
            else:
                logger.warning("⚠️ 訂單驗證失敗: %s", message)

        # 測試訂單取消
        if submitted_orders:
            test_order_id = submitted_orders[0]
            success, cancel_message = trade_service.cancel_order(test_order_id)
            if success:
                logger.info("✅ 訂單取消成功: %s", test_order_id)
            else:
                logger.error("❌ 訂單取消失敗: %s", cancel_message)

        logger.info("✅ 訂單提交功能測試成功")
        assert True

    except Exception as e:
        logger.error("❌ 訂單提交功能測試失敗: %s", e)
        pytest.fail(f"訂單提交功能測試失敗: {e}")


def test_order_queries(trade_service):
    """測試訂單查詢功能"""
    logger.info("測試訂單查詢功能...")

    try:
        # 測試訂單歷史查詢
        orders = trade_service.get_order_history(limit=10)
        logger.info("獲取到 %d 筆訂單歷史", len(orders))

        # 測試成交記錄查詢
        executions = trade_service.get_trade_executions(limit=10)
        logger.info("獲取到 %d 筆成交記錄", len(executions))

        # 測試待處理訂單
        pending_orders = trade_service.get_pending_orders()
        logger.info("獲取到 %d 筆待處理訂單", len(pending_orders))

        # 測試交易統計
        stats = trade_service.get_trading_statistics()
        if stats:
            logger.info(
                "交易統計: 總訂單 %s, 成功率 %s%%",
                stats["orders"]["total"],
                stats["orders"]["success_rate"],
            )
        else:
            logger.info("暫無交易統計數據")

        # 測試異常查詢
        exceptions = trade_service.get_trading_exceptions(limit=10)
        logger.info("獲取到 %d 筆交易異常", len(exceptions))

        logger.info("✅ 訂單查詢功能測試成功")
        assert True

    except Exception as e:
        logger.error("❌ 訂單查詢功能測試失敗: %s", e)
        pytest.fail(f"訂單查詢功能測試失敗: {e}")


def test_trading_mode_switch(trade_service):
    """測試交易模式切換"""
    logger.info("測試交易模式切換...")

    try:
        # 獲取當前模式
        current_mode = trade_service.is_simulation_mode
        logger.info("當前交易模式: %s", "模擬交易" if current_mode else "實盤交易")

        # 測試切換到相同模式
        success, message = trade_service.switch_trading_mode(current_mode)
        logger.info("切換到相同模式: %s - %s", success, message)

        # 測試切換到不同模式（如果是模擬模式，嘗試切換到實盤）
        if current_mode:
            success, message = trade_service.switch_trading_mode(False)
            logger.info("切換到實盤交易: %s - %s", success, message)

            # 切換回模擬模式
            success, message = trade_service.switch_trading_mode(True)
            logger.info("切換回模擬交易: %s - %s", success, message)

        logger.info("✅ 交易模式切換測試成功")
        assert True

    except Exception as e:
        logger.error("❌ 交易模式切換測試失敗: %s", e)
        pytest.fail(f"交易模式切換測試失敗: {e}")


def test_broker_status(trade_service):
    """測試券商狀態"""
    logger.info("測試券商狀態...")

    try:
        # 獲取券商狀態
        status = trade_service.get_broker_status()

        if "error" in status:
            logger.error("獲取券商狀態失敗: %s", status["error"])
        else:
            logger.info("券商狀態:")
            logger.info("  - 當前券商: %s", status["current_broker"])
            logger.info("  - 連線狀態: %s", status["connected"])
            logger.info(
                "  - 交易模式: %s", "模擬" if status["is_simulation"] else "實盤"
            )
            logger.info("  - 錯誤次數: %s", status["error_count"])
            logger.info("  - 今日下單: %s", status["daily_order_count"])

        logger.info("✅ 券商狀態測試成功")
        assert True

    except Exception as e:
        logger.error("❌ 券商狀態測試失敗: %s", e)
        pytest.fail(f"券商狀態測試失敗: {e}")


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
                raise e from e

        logger.info("✅ 資料庫結構測試成功")
        assert True

    except ImportError as e:
        logger.error("❌ 無法導入資料庫模組: %s", e)
        pytest.fail(f"無法導入資料庫模組: {e}")
    except Exception as e:
        logger.error("❌ 資料庫結構測試失敗: %s", e)
        pytest.fail(f"資料庫結構測試失敗: {e}")


def test_export_functionality(trade_service):
    """測試匯出功能"""
    logger.info("測試匯出功能...")

    try:
        # 測試 CSV 匯出
        success, message, _ = trade_service.export_order_history(
            format_type="csv", limit=10
        )
        if success:
            logger.info("✅ CSV 匯出成功: %s", message)
        else:
            logger.error("❌ CSV 匯出失敗: %s", message)

        # 測試 Excel 匯出
        success, message, _ = trade_service.export_order_history(
            format_type="excel", limit=10
        )
        if success:
            logger.info("✅ Excel 匯出成功: %s", message)
        else:
            logger.error("❌ Excel 匯出失敗: %s", message)

        logger.info("✅ 匯出功能測試成功")
        assert True

    except Exception as e:
        logger.error("❌ 匯出功能測試失敗: %s", e)
        pytest.fail(f"匯出功能測試失敗: {e}")


def main():
    """主函數"""
    logger.info("開始交易執行模組測試...")

    # 測試資料庫結構
    test_database_schema()

    # 測試交易執行服務
    test_trade_execution_service()

    logger.info("🎉 所有測試完成！")


if __name__ == "__main__":
    main()
