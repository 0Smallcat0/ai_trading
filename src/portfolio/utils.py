"""投資組合工具函數模組

此模組提供投資組合管理中常用的工具函數，包括：
- 資料處理和格式轉換
- 權重正規化和驗證
- 模擬資料生成
- 投資組合比較和排名
- 其他輔助函數

這些函數可以被其他投資組合模組使用。
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime

import numpy as np
import pandas as pd

# 設定日誌
logger = logging.getLogger(__name__)


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """正規化權重，確保總和為1

    Args:
        weights: 權重字典

    Returns:
        正規化後的權重字典
    """
    if not weights:
        return {}

    total_weight = sum(weights.values())
    if total_weight == 0:
        # 如果總權重為0，返回等權重
        equal_weight = 1.0 / len(weights)
        return {stock: equal_weight for stock in weights.keys()}

    return {stock: weight / total_weight for stock, weight in weights.items()}


def validate_weights(weights: Dict[str, float], tolerance: float = 1e-6) -> bool:
    """驗證權重是否有效

    Args:
        weights: 權重字典
        tolerance: 容忍誤差

    Returns:
        是否有效
    """
    if not weights:
        return False

    # 檢查權重是否為非負數
    if any(weight < 0 for weight in weights.values()):
        return False

    # 檢查權重總和是否接近1
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > tolerance:
        return False

    return True


def generate_mock_returns(
    stocks: List[str],
    start_date: datetime,
    end_date: datetime,
    annual_return: float = 0.08,
    annual_volatility: float = 0.2,
    correlation: float = 0.3,
) -> pd.DataFrame:
    """生成模擬收益率資料

    Args:
        stocks: 股票代碼列表
        start_date: 開始日期
        end_date: 結束日期
        annual_return: 年化收益率
        annual_volatility: 年化波動率
        correlation: 股票間相關性

    Returns:
        模擬收益率資料框
    """
    if not stocks:
        return pd.DataFrame()

    try:
        # 生成日期範圍
        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        n_days = len(dates)
        n_stocks = len(stocks)

        # 生成相關矩陣
        corr_matrix = np.full((n_stocks, n_stocks), correlation)
        np.fill_diagonal(corr_matrix, 1.0)

        # 生成隨機收益率
        daily_return = annual_return / 252
        daily_volatility = annual_volatility / np.sqrt(252)

        # 使用多變量正態分佈生成相關的收益率
        returns = np.random.multivariate_normal(
            mean=[daily_return] * n_stocks,
            cov=corr_matrix * (daily_volatility**2),
            size=n_days,
        )

        # 創建 DataFrame
        returns_df = pd.DataFrame(returns, index=dates, columns=stocks)

        return returns_df

    except Exception as e:
        logger.error(f"生成模擬資料錯誤: {e}")
        return pd.DataFrame()


def generate_mock_prices(
    stocks: List[str],
    start_date: datetime,
    end_date: datetime,
    initial_price: float = 100.0,
    annual_return: float = 0.08,
    annual_volatility: float = 0.2,
    correlation: float = 0.3,
) -> pd.DataFrame:
    """生成模擬價格資料

    Args:
        stocks: 股票代碼列表
        start_date: 開始日期
        end_date: 結束日期
        initial_price: 初始價格
        annual_return: 年化收益率
        annual_volatility: 年化波動率
        correlation: 股票間相關性

    Returns:
        模擬價格資料框（MultiIndex格式）
    """
    if not stocks:
        return pd.DataFrame()

    try:
        # 生成收益率
        returns_df = generate_mock_returns(
            stocks, start_date, end_date, annual_return, annual_volatility, correlation
        )

        if returns_df.empty:
            return pd.DataFrame()

        # 計算價格
        prices_data = []
        for stock in stocks:
            stock_returns = returns_df[stock]
            stock_prices = [initial_price]

            for ret in stock_returns:
                new_price = stock_prices[-1] * (1 + ret)
                stock_prices.append(new_price)

            # 移除第一個初始價格，保持與日期對應
            stock_prices = stock_prices[1:]

            for i, (date, price) in enumerate(zip(returns_df.index, stock_prices)):
                prices_data.append(
                    {"stock": stock, "date": date, "close": price, "收盤價": price}
                )

        # 創建 MultiIndex DataFrame
        prices_df = pd.DataFrame(prices_data)
        prices_df = prices_df.set_index(["stock", "date"])

        return prices_df

    except Exception as e:
        logger.error(f"生成模擬價格資料錯誤: {e}")
        return pd.DataFrame()


def rebalance_weights(
    current_weights: Dict[str, float],
    target_weights: Dict[str, float],
    rebalance_threshold: float = 0.05,
) -> Tuple[Dict[str, float], bool]:
    """檢查是否需要再平衡並計算新權重

    Args:
        current_weights: 當前權重
        target_weights: 目標權重
        rebalance_threshold: 再平衡閾值

    Returns:
        (新權重, 是否需要再平衡)
    """
    if not current_weights or not target_weights:
        return target_weights, True

    try:
        # 檢查是否需要再平衡
        need_rebalance = False

        # 獲取所有股票
        all_stocks = set(current_weights.keys()) | set(target_weights.keys())

        for stock in all_stocks:
            current_weight = current_weights.get(stock, 0.0)
            target_weight = target_weights.get(stock, 0.0)

            if abs(current_weight - target_weight) > rebalance_threshold:
                need_rebalance = True
                break

        if need_rebalance:
            return normalize_weights(target_weights), True
        else:
            return current_weights, False

    except Exception as e:
        logger.error(f"再平衡檢查錯誤: {e}")
        return target_weights, True


def calculate_portfolio_metrics_summary(
    portfolios_performance: Dict[str, Dict[str, Any]]
) -> pd.DataFrame:
    """計算多個投資組合的績效摘要

    Args:
        portfolios_performance: 投資組合績效字典

    Returns:
        績效摘要 DataFrame
    """
    if not portfolios_performance:
        return pd.DataFrame()

    try:
        summary_data = []

        for portfolio_name, performance in portfolios_performance.items():
            if not performance:
                continue

            summary = {
                "投資組合": portfolio_name,
                "年化收益率": performance.get("annual_return", 0),
                "年化波動率": performance.get("annual_volatility", 0),
                "夏普比率": performance.get("sharpe_ratio", 0),
                "最大回撤": performance.get("max_drawdown", 0),
                "Sortino比率": performance.get("sortino_ratio", 0),
                "Calmar比率": performance.get("calmar_ratio", 0),
                "VaR(5%)": performance.get("var_5", 0),
                "CVaR(5%)": performance.get("cvar_5", 0),
            }

            # 如果有基準比較指標
            if "beta" in performance:
                summary["Beta"] = performance["beta"]
            if "alpha" in performance:
                summary["Alpha"] = performance["alpha"]
            if "information_ratio" in performance:
                summary["資訊比率"] = performance["information_ratio"]

            summary_data.append(summary)

        return pd.DataFrame(summary_data)

    except Exception as e:
        logger.error(f"績效摘要計算錯誤: {e}")
        return pd.DataFrame()


def rank_portfolios(
    portfolios_performance: Dict[str, Dict[str, Any]],
    ranking_metric: str = "sharpe_ratio",
    ascending: bool = False,
) -> pd.DataFrame:
    """對投資組合進行排名

    Args:
        portfolios_performance: 投資組合績效字典
        ranking_metric: 排名指標
        ascending: 是否升序排列

    Returns:
        排名結果 DataFrame
    """
    if not portfolios_performance:
        return pd.DataFrame()

    try:
        summary_df = calculate_portfolio_metrics_summary(portfolios_performance)

        if summary_df.empty:
            return pd.DataFrame()

        # 根據指標排名
        metric_mapping = {
            "sharpe_ratio": "夏普比率",
            "annual_return": "年化收益率",
            "sortino_ratio": "Sortino比率",
            "calmar_ratio": "Calmar比率",
            "information_ratio": "資訊比率",
        }

        sort_column = metric_mapping.get(ranking_metric, ranking_metric)

        if sort_column in summary_df.columns:
            ranked_df = summary_df.sort_values(sort_column, ascending=ascending)
            ranked_df["排名"] = range(1, len(ranked_df) + 1)

            # 重新排列欄位，將排名放在前面
            cols = ["排名"] + [col for col in ranked_df.columns if col != "排名"]
            ranked_df = ranked_df[cols]

            return ranked_df
        else:
            logger.warning(f"排名指標 '{sort_column}' 不存在")
            return summary_df

    except Exception as e:
        logger.error(f"投資組合排名錯誤: {e}")
        return pd.DataFrame()


def convert_weights_to_dataframe(
    weights_dict: Dict[str, Dict[str, float]], fill_missing: bool = True
) -> pd.DataFrame:
    """將權重字典轉換為 DataFrame

    Args:
        weights_dict: 權重字典，格式為 {date: {stock: weight}}
        fill_missing: 是否填充缺失值

    Returns:
        權重 DataFrame
    """
    if not weights_dict:
        return pd.DataFrame()

    try:
        weights_df = pd.DataFrame(weights_dict).T

        if fill_missing:
            weights_df = weights_df.fillna(0.0)

        return weights_df

    except Exception as e:
        logger.error(f"權重轉換錯誤: {e}")
        return pd.DataFrame()


def simulate_portfolios_comparison(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    portfolio_types: List[str] = None,
    initial_capital: float = 1000000,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    rebalance_freq: str = "M",
) -> Dict[str, Any]:
    """模擬並比較不同投資組合策略的表現

    Args:
        signals: 交易訊號
        prices: 價格資料
        portfolio_types: 要比較的投資組合類型列表
        initial_capital: 初始資金
        start_date: 開始日期
        end_date: 結束日期
        rebalance_freq: 再平衡頻率

    Returns:
        比較結果字典
    """
    if portfolio_types is None:
        portfolio_types = [
            "equal_weight",
            "mean_variance",
            "risk_parity",
            "max_sharpe",
            "min_variance",
        ]

    try:
        # 這裡應該導入並使用具體的投資組合策略類別
        # 由於循環導入問題，這裡只返回模擬結果結構

        results = {
            "portfolios": {},
            "summary": pd.DataFrame(),
            "ranking": pd.DataFrame(),
            "comparison_chart": None,
        }

        logger.info(f"模擬 {len(portfolio_types)} 個投資組合策略")

        return results

    except Exception as e:
        logger.error(f"投資組合比較模擬錯誤: {e}")
        return {}
