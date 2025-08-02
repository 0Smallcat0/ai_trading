"""
投資組合管理系統測試腳本

此腳本用於測試投資組合管理系統的基本功能
"""

import sys
import os
from datetime import datetime, timedelta

# 添加項目根目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.portfolio_service import PortfolioService, Portfolio, PortfolioHolding


def test_portfolio_service():
    """測試投資組合服務"""
    print("🧪 開始測試投資組合服務...")

    # 初始化服務
    service = PortfolioService()
    print("✅ 投資組合服務初始化成功")

    # 測試獲取可用股票
    stocks = service.get_available_stocks()
    print(f"✅ 獲取到 {len(stocks)} 個可用股票")

    # 創建測試投資組合
    print("\n🧪 測試創建投資組合...")

    holdings_data = [
        {
            "symbol": "2330.TW",
            "name": "台積電",
            "quantity": 1000,
            "price": 500.0,
            "sector": "半導體",
            "exchange": "TWSE",
        },
        {
            "symbol": "2317.TW",
            "name": "鴻海",
            "quantity": 5000,
            "price": 100.0,
            "sector": "電子零組件",
            "exchange": "TWSE",
        },
        {
            "symbol": "AAPL",
            "name": "蘋果",
            "quantity": 1000,
            "price": 150.0,
            "sector": "科技",
            "exchange": "NASDAQ",
        },
    ]

    portfolio_id = service.create_portfolio(
        name="測試投資組合", description="用於測試的投資組合", holdings=holdings_data
    )

    print(f"✅ 投資組合已創建，ID: {portfolio_id}")

    # 測試獲取投資組合
    print("\n🧪 測試獲取投資組合...")

    portfolio = service.get_portfolio(portfolio_id)
    if portfolio:
        print(f"✅ 成功獲取投資組合: {portfolio.name}")
        print(f"   總市值: {portfolio.total_value:,.0f}")
        print(f"   持倉數量: {len(portfolio.holdings)}")

        for holding in portfolio.holdings:
            print(f"   - {holding.symbol}: {holding.weight:.2%}")
    else:
        print("❌ 無法獲取投資組合")
        return

    # 測試績效指標計算
    print("\n🧪 測試績效指標計算...")

    metrics = service.calculate_portfolio_metrics(portfolio)
    print(f"✅ 績效指標計算完成")
    print(f"   年化報酬率: {metrics['annual_return']:.2%}")
    print(f"   年化波動率: {metrics['volatility']:.2%}")
    print(f"   夏普比率: {metrics['sharpe_ratio']:.2f}")
    print(f"   最大回撤: {metrics['max_drawdown']:.2%}")

    # 測試權重調整
    print("\n🧪 測試權重調整...")

    new_weights = {"2330.TW": 0.5, "2317.TW": 0.3, "AAPL": 0.2}

    success = service.update_portfolio_weights(
        portfolio_id, new_weights, "測試權重調整"
    )
    if success:
        print("✅ 權重調整成功")

        # 重新獲取投資組合檢查權重
        updated_portfolio = service.get_portfolio(portfolio_id)
        print("   調整後權重:")
        for holding in updated_portfolio.holdings:
            print(f"   - {holding.symbol}: {holding.weight:.2%}")
    else:
        print("❌ 權重調整失敗")

    # 測試最佳化演算法
    print("\n🧪 測試最佳化演算法...")

    symbols = portfolio.get_symbols()

    # 等權重配置
    equal_weights = service.optimize_equal_weight(symbols)
    print(f"✅ 等權重配置: {equal_weights}")

    # 風險平衡配置
    try:
        risk_parity_weights = service.optimize_risk_parity(symbols)
        print(f"✅ 風險平衡配置: {risk_parity_weights}")
    except Exception as e:
        print(f"⚠️ 風險平衡配置失敗: {e}")

    # 最小變異數配置
    try:
        min_var_weights = service.optimize_minimum_variance(symbols)
        print(f"✅ 最小變異數配置: {min_var_weights}")
    except Exception as e:
        print(f"⚠️ 最小變異數配置失敗: {e}")

    # 最大夏普比率配置
    try:
        max_sharpe_weights = service.optimize_maximum_sharpe(symbols)
        print(f"✅ 最大夏普比率配置: {max_sharpe_weights}")
    except Exception as e:
        print(f"⚠️ 最大夏普比率配置失敗: {e}")

    # 測試配置建議
    print("\n🧪 測試配置建議...")

    suggestion_saved = service.save_optimization_suggestion(
        portfolio_id, "等權重配置", equal_weights
    )

    if suggestion_saved:
        print("✅ 配置建議已保存")

        suggestions = service.get_optimization_suggestions(portfolio_id)
        print(f"✅ 獲取到 {len(suggestions)} 個配置建議")

        for suggestion in suggestions:
            print(
                f"   - {suggestion['suggestion_type']}: 夏普比率 {suggestion['sharpe_ratio']:.2f}"
            )
    else:
        print("❌ 保存配置建議失敗")

    # 測試投資組合複製
    print("\n🧪 測試投資組合複製...")

    copied_id = service.copy_portfolio(portfolio_id, "測試投資組合 (副本)")
    if copied_id:
        print(f"✅ 投資組合已複製，新ID: {copied_id}")
    else:
        print("❌ 投資組合複製失敗")

    # 測試投資組合比較
    print("\n🧪 測試投資組合比較...")

    if copied_id:
        comparison_data = service.compare_portfolios([portfolio_id, copied_id])

        if comparison_data.get("portfolios"):
            print(f"✅ 投資組合比較完成")
            print(f"   比較了 {len(comparison_data['portfolios'])} 個投資組合")

            if comparison_data.get("correlation_matrix"):
                print("✅ 相關性分析完成")
        else:
            print("❌ 投資組合比較失敗")

    # 測試匯出功能
    print("\n🧪 測試匯出功能...")

    # JSON 匯出
    json_data = service.export_portfolio_data(portfolio_id, "json")
    if json_data:
        print("✅ JSON 匯出成功")

    # CSV 匯出
    csv_data = service.export_portfolio_data(portfolio_id, "csv")
    if csv_data:
        print("✅ CSV 匯出成功")

    # Excel 匯出
    try:
        excel_data = service.export_portfolio_data(portfolio_id, "excel")
        if excel_data:
            print("✅ Excel 匯出成功")
    except Exception as e:
        print(f"⚠️ Excel 匯出失敗: {e}")

    # 測試投資組合列表
    print("\n🧪 測試投資組合列表...")

    portfolio_list = service.get_portfolio_list()
    print(f"✅ 獲取到 {len(portfolio_list)} 個投資組合")

    for p in portfolio_list:
        print(
            f"   - {p['name']}: 市值 {p['total_value']:,.0f}, 持倉 {p['holdings_count']}"
        )

    # 測試調整歷史
    print("\n🧪 測試調整歷史...")

    history = service.get_adjustment_history(portfolio_id)
    print(f"✅ 獲取到 {len(history)} 筆調整歷史")

    for h in history:
        print(f"   - {h['adjustment_type']}: {h['reason']}")

    print("\n🎉 投資組合管理系統測試完成！")


def test_database_connection():
    """測試資料庫連接"""
    print("🧪 測試資料庫連接...")

    try:
        service = PortfolioService()
        # 嘗試獲取投資組合列表來測試資料庫連接
        portfolio_list = service.get_portfolio_list(limit=1)
        print("✅ 資料庫連接正常")
        return True
    except Exception as e:
        print(f"❌ 資料庫連接失敗: {str(e)}")
        return False


def test_optimization_algorithms():
    """測試最佳化演算法"""
    print("\n🧪 測試最佳化演算法...")

    service = PortfolioService()
    symbols = ["2330.TW", "2317.TW", "AAPL", "MSFT"]

    print(f"測試股票: {symbols}")

    # 測試各種最佳化方法
    algorithms = [
        ("等權重配置", service.optimize_equal_weight),
        ("風險平衡配置", service.optimize_risk_parity),
        ("最小變異數配置", service.optimize_minimum_variance),
        ("最大夏普比率配置", service.optimize_maximum_sharpe),
    ]

    for name, algorithm in algorithms:
        try:
            if name == "均值變異數最佳化":
                weights = algorithm(symbols, 0.1)  # 10% 目標報酬率
            else:
                weights = algorithm(symbols)

            total_weight = sum(weights.values())
            print(f"✅ {name}: 權重總和 {total_weight:.3f}")

            for symbol, weight in weights.items():
                print(f"   - {symbol}: {weight:.3f}")

        except Exception as e:
            print(f"❌ {name} 失敗: {e}")


if __name__ == "__main__":
    print("🚀 開始投資組合管理系統測試")
    print("=" * 50)

    # 測試資料庫連接
    if test_database_connection():
        # 測試最佳化演算法
        test_optimization_algorithms()

        # 測試投資組合服務
        test_portfolio_service()
    else:
        print("❌ 資料庫連接失敗，跳過其他測試")

    print("=" * 50)
    print("🏁 測試結束")
