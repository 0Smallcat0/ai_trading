"""投資組合管理模組

此模組提供完整的投資組合管理功能，包括：
- 基礎投資組合類別和異常處理
- 各種投資組合策略實現
- 投資組合最佳化演算法
- 績效評估和風險分析
- 工具函數和輔助功能

主要類別：
- Portfolio: 投資組合基類
- EqualWeightPortfolio: 等權重投資組合
- MeanVariancePortfolio: 均值變異數投資組合
- RiskParityPortfolio: 風險平價投資組合
- MaxSharpePortfolio: 最大夏普比率投資組合
- MinVariancePortfolio: 最小變異數投資組合

主要函數：
- equal_weight: 等權重配置
- mean_variance_optimization: 均值變異數最佳化
- risk_parity_optimization: 風險平價最佳化
- calculate_portfolio_returns: 計算投資組合收益率
- calculate_comprehensive_metrics: 計算綜合績效指標

為了保持向後相容性，所有原始的類別和函數都可以直接從此模組導入。
"""

# 導入基礎類別和異常
from .base import (
    Portfolio,
    PortfolioOptimizationError,
    DependencyError
)

# 導入投資組合策略
from .strategies import (
    EqualWeightPortfolio,
    MeanVariancePortfolio,
    RiskParityPortfolio,
    MaxSharpePortfolio,
    MinVariancePortfolio
)

# 導入最佳化函數
from .optimization import (
    equal_weight,
    kelly_weight,
    momentum_weight,
    mean_variance_optimization,
    minimum_variance_optimization,
    maximum_sharpe_optimization,
    risk_parity_optimization
)

# 導入評估函數
from .evaluation import (
    calculate_portfolio_returns,
    calculate_var,
    calculate_cvar,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_information_ratio,
    calculate_beta,
    calculate_alpha,
    calculate_comprehensive_metrics,
    plot_portfolio_performance
)

# 導入工具函數
from .utils import (
    normalize_weights,
    validate_weights,
    generate_mock_returns,
    generate_mock_prices,
    rebalance_weights,
    calculate_portfolio_metrics_summary,
    rank_portfolios,
    convert_weights_to_dataframe,
    simulate_portfolios_comparison
)

# 導入投資組合服務（向後相容性）
try:
    import sys
    import os
    # 添加 services 路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    services_dir = os.path.join(os.path.dirname(current_dir), 'services')
    if services_dir not in sys.path:
        sys.path.insert(0, services_dir)

    from portfolio_service import PortfolioService
except ImportError:
    try:
        # 嘗試相對導入
        from services.portfolio_service import PortfolioService
    except ImportError:
        # 如果無法導入，提供一個警告但不中斷
        import warnings
        warnings.warn(
            "無法導入 PortfolioService，請確認 services.portfolio_service 模組存在",
            ImportWarning
        )
        PortfolioService = None


# 為了向後相容性，保留原始的函數名稱
def simulate_portfolios(
    signals,
    prices,
    portfolio_types=None,
    initial_capital=1000000,
    start_date=None,
    end_date=None,
    rebalance_freq="M",
    show_plot=True
):
    """模擬並比較不同投資組合策略的表現（向後相容函數）

    Args:
        signals: 交易訊號
        prices: 價格資料
        portfolio_types: 要比較的投資組合類型列表
        initial_capital: 初始資金
        start_date: 開始日期
        end_date: 結束日期
        rebalance_freq: 再平衡頻率
        show_plot: 是否顯示圖表

    Returns:
        比較結果字典
    """
    if portfolio_types is None:
        portfolio_types = [
            "equal_weight",
            "mean_variance",
            "risk_parity",
            "max_sharpe",
            "min_variance"
        ]

    # 創建投資組合實例
    portfolios = {}

    for portfolio_type in portfolio_types:
        if portfolio_type == "equal_weight":
            portfolios[portfolio_type] = EqualWeightPortfolio(initial_capital=initial_capital)
        elif portfolio_type == "mean_variance":
            portfolios[portfolio_type] = MeanVariancePortfolio(initial_capital=initial_capital)
        elif portfolio_type == "risk_parity":
            portfolios[portfolio_type] = RiskParityPortfolio(initial_capital=initial_capital)
        elif portfolio_type == "max_sharpe":
            portfolios[portfolio_type] = MaxSharpePortfolio(initial_capital=initial_capital)
        elif portfolio_type == "min_variance":
            portfolios[portfolio_type] = MinVariancePortfolio(initial_capital=initial_capital)

    # 模擬每個投資組合
    results = {}
    for name, portfolio in portfolios.items():
        try:
            result = portfolio.simulate(
                signals=signals,
                price_df=prices,
                start_date=start_date,
                end_date=end_date,
                rebalance_freq=rebalance_freq
            )
            results[name] = result
        except Exception as e:
            print(f"模擬 {name} 投資組合時發生錯誤: {e}")
            continue

    # 如果需要顯示圖表
    if show_plot and results:
        try:
            import matplotlib.pyplot as plt

            plt.figure(figsize=(12, 8))

            for name, result in results.items():
                if 'performance' in result and 'equity_curve' in result['performance']:
                    equity_curve = result['performance']['equity_curve']
                    plt.plot(equity_curve.index, equity_curve.values, label=name)

            plt.title("投資組合績效比較")
            plt.xlabel("日期")
            plt.ylabel("投資組合價值")
            plt.legend()
            plt.grid(True)
            plt.show()

        except ImportError:
            print("matplotlib 不可用，無法繪製圖表")
        except Exception as e:
            print(f"繪製圖表時發生錯誤: {e}")

    return results


# 向後相容性：保留原始的評估函數名稱
def evaluate_portfolio(weights, prices):
    """評估投資組合表現（向後相容函數）"""
    return calculate_portfolio_returns(weights, prices)


# 模組版本資訊
__version__ = "2.0.0"
__author__ = "AI Trading System"

# 公開的 API
__all__ = [
    # 基礎類別
    "Portfolio",
    "PortfolioOptimizationError",
    "DependencyError",

    # 策略類別
    "EqualWeightPortfolio",
    "MeanVariancePortfolio",
    "RiskParityPortfolio",
    "MaxSharpePortfolio",
    "MinVariancePortfolio",

    # 最佳化函數
    "equal_weight",
    "kelly_weight",
    "momentum_weight",
    "mean_variance_optimization",
    "minimum_variance_optimization",
    "maximum_sharpe_optimization",
    "risk_parity_optimization",

    # 評估函數
    "calculate_portfolio_returns",
    "calculate_var",
    "calculate_cvar",
    "calculate_sortino_ratio",
    "calculate_calmar_ratio",
    "calculate_information_ratio",
    "calculate_beta",
    "calculate_alpha",
    "calculate_comprehensive_metrics",
    "plot_portfolio_performance",

    # 工具函數
    "normalize_weights",
    "validate_weights",
    "generate_mock_returns",
    "generate_mock_prices",
    "rebalance_weights",
    "calculate_portfolio_metrics_summary",
    "rank_portfolios",
    "convert_weights_to_dataframe",
    "simulate_portfolios_comparison",

    # 向後相容函數
    "simulate_portfolios",
    "evaluate_portfolio",

    # 服務類別
    "PortfolioService"
]
