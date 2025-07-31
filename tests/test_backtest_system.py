"""
回測系統測試腳本

此腳本用於測試回測系統的基本功能
"""

import sys
import os
from datetime import datetime, timedelta

# 添加項目根目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.backtest_service import BacktestService, BacktestConfig


def test_backtest_service():
    """測試回測服務"""
    print("🧪 開始測試回測服務...")

    # 初始化服務
    service = BacktestService()
    print("✅ 回測服務初始化成功")

    # 測試獲取策略列表
    strategies = service.get_available_strategies()
    print(f"✅ 獲取到 {len(strategies)} 個策略")

    # 測試獲取股票列表
    stocks = service.get_available_stocks()
    print(f"✅ 獲取到 {len(stocks)} 個股票")

    # 創建測試配置
    config = BacktestConfig(
        strategy_id="ma_cross",
        strategy_name="移動平均線交叉策略",
        symbols=["2330.TW", "2317.TW"],
        start_date=datetime.now() - timedelta(days=365),
        end_date=datetime.now() - timedelta(days=1),
        initial_capital=1000000,
        commission=0.001425,
        slippage=0.001,
        tax=0.003,
        max_position_size=0.2,
        stop_loss=0.05,
        take_profit=0.1,
    )

    # 驗證配置
    is_valid, error_msg = service.validate_backtest_config(config)
    if is_valid:
        print("✅ 回測配置驗證通過")
    else:
        print(f"❌ 回測配置驗證失敗: {error_msg}")
        return

    # 啟動回測
    try:
        backtest_id = service.start_backtest(config)
        print(f"✅ 回測已啟動，ID: {backtest_id}")

        # 等待回測完成
        import time

        max_wait = 60  # 最多等待60秒
        waited = 0

        while waited < max_wait:
            status = service.get_backtest_status(backtest_id)
            print(
                f"📊 回測狀態: {status['status']} - {status['message']} ({status['progress']:.1f}%)"
            )

            if status["status"] in ["completed", "failed", "cancelled"]:
                break

            time.sleep(2)
            waited += 2

        # 檢查最終狀態
        final_status = service.get_backtest_status(backtest_id)

        if final_status["status"] == "completed":
            print("✅ 回測完成")

            # 獲取結果
            results = service.get_backtest_results(backtest_id)
            if results:
                print("✅ 成功獲取回測結果")

                metrics = results.get("metrics", {})
                print(f"📊 總報酬率: {metrics.get('total_return', 0):.2f}%")
                print(f"📊 夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
                print(f"📊 最大回撤: {metrics.get('max_drawdown', 0):.2f}%")
                print(f"📊 勝率: {metrics.get('win_rate', 0):.1f}%")
                print(f"📊 總交易次數: {metrics.get('total_trades', 0)}")

                # 測試匯出功能
                print("\n🧪 測試匯出功能...")

                # 測試 JSON 匯出
                json_data = service.export_results(backtest_id, "json")
                if json_data:
                    print("✅ JSON 匯出成功")

                # 測試 CSV 匯出
                csv_data = service.export_results(backtest_id, "csv")
                if csv_data:
                    print("✅ CSV 匯出成功")

                # 測試 HTML 匯出
                html_data = service.export_results(backtest_id, "html")
                if html_data:
                    print("✅ HTML 匯出成功")

            else:
                print("❌ 無法獲取回測結果")

        elif final_status["status"] == "failed":
            print(f"❌ 回測失敗: {final_status['message']}")

        else:
            print(f"⚠️ 回測未完成，狀態: {final_status['status']}")

    except Exception as e:
        print(f"❌ 回測執行失敗: {str(e)}")

    # 測試回測列表
    print("\n🧪 測試回測列表...")
    backtest_list = service.get_backtest_list(limit=10)
    print(f"✅ 獲取到 {len(backtest_list)} 個回測記錄")

    print("\n🎉 回測系統測試完成！")


def test_database_connection():
    """測試資料庫連接"""
    print("🧪 測試資料庫連接...")

    try:
        service = BacktestService()
        # 嘗試獲取回測列表來測試資料庫連接
        backtest_list = service.get_backtest_list(limit=1)
        print("✅ 資料庫連接正常")
        return True
    except Exception as e:
        print(f"❌ 資料庫連接失敗: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 開始回測系統測試")
    print("=" * 50)

    # 測試資料庫連接
    if test_database_connection():
        # 測試回測服務
        test_backtest_service()
    else:
        print("❌ 資料庫連接失敗，跳過其他測試")

    print("=" * 50)
    print("🏁 測試結束")
