"""等權重投資組合策略模組

此模組實現等權重投資組合策略，這是最簡單的投資組合配置方法。

主要功能：
- 等權重配置所有選中的股票
- 簡單的風險分散
- 不需要複雜的最佳化計算
"""

from typing import Dict, Optional, Any
import logging

import numpy as np
import pandas as pd

from .core import Portfolio

# 設定日誌
logger = logging.getLogger(__name__)


class EqualWeightPortfolio(Portfolio):
    """等權重投資組合
    
    將資金平均分配給所有選中的股票，是最簡單的投資組合策略。
    適合初學者或希望簡單分散風險的投資者。
    """

    def __init__(self, **kwargs):
        """初始化等權重投資組合
        
        Args:
            **kwargs: 傳遞給父類的參數
        """
        super().__init__(name="EqualWeight", **kwargs)

    def optimize(
        self, signals: pd.DataFrame, price_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """等權重最佳化
        
        將資金平均分配給所有有買入訊號的股票。

        Args:
            signals: 交易訊號 DataFrame
            price_df: 價格資料（此策略不使用）

        Returns:
            等權重配置字典 {股票代號: 權重}
            
        Example:
            >>> portfolio = EqualWeightPortfolio()
            >>> signals = pd.DataFrame({'signal': [1, 1, 0]}, 
            ...                       index=['AAPL', 'GOOGL', 'MSFT'])
            >>> weights = portfolio.optimize(signals)
            >>> print(weights)
            {'AAPL': 0.5, 'GOOGL': 0.5}
        """
        try:
            # 獲取有買入訊號的股票
            buy_signals = signals[signals.get("signal", signals.get("buy_signal", 0)) > 0]

            if buy_signals.empty:
                logger.info("沒有買入訊號，返回空權重")
                return {}

            # 獲取股票列表
            if isinstance(buy_signals.index, pd.MultiIndex):
                stocks = buy_signals.index.get_level_values(0).unique().tolist()
            else:
                stocks = buy_signals.index.tolist()

            if not stocks:
                logger.warning("無法從訊號中提取股票列表")
                return {}

            # 等權重分配
            weight = 1.0 / len(stocks)
            weights = {stock: weight for stock in stocks}
            
            logger.info(f"等權重配置完成，共 {len(stocks)} 隻股票，每隻權重 {weight:.4f}")
            return weights
            
        except Exception as e:
            logger.error(f"等權重最佳化失敗: {e}")
            return {}

    def evaluate(
        self, weights: Dict[str, float], price_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """評估等權重投資組合表現

        Args:
            weights: 投資組合權重
            price_df: 價格資料

        Returns:
            評估結果字典，包含各種績效指標
        """
        if not weights:
            logger.warning("權重為空，無法評估")
            return {}

        try:
            # 確定價格欄位
            price_col = "close" if "close" in price_df.columns else "收盤價"
            
            if price_col not in price_df.columns:
                logger.error("價格資料中找不到收盤價欄位")
                return {}

            # 計算投資組合收益率
            portfolio_returns = self._calculate_portfolio_returns(weights, price_df, price_col)
            
            if portfolio_returns.empty:
                logger.warning("無法計算投資組合收益率")
                return {}

            # 計算績效指標
            performance_metrics = self._calculate_performance_metrics(portfolio_returns)
            
            # 添加策略特定資訊
            performance_metrics.update({
                "strategy": "EqualWeight",
                "num_stocks": len(weights),
                "weights": weights,
            })
            
            logger.info("等權重投資組合評估完成")
            return performance_metrics
            
        except Exception as e:
            logger.error(f"等權重投資組合評估失敗: {e}")
            return {}

    def _calculate_portfolio_returns(
        self, weights: Dict[str, float], price_df: pd.DataFrame, price_col: str
    ) -> pd.Series:
        """計算投資組合收益率
        
        Args:
            weights: 投資組合權重
            price_df: 價格資料
            price_col: 價格欄位名稱
            
        Returns:
            投資組合收益率時間序列
        """
        try:
            # 計算個股收益率
            stock_returns = {}
            
            for stock, weight in weights.items():
                if isinstance(price_df.index, pd.MultiIndex):
                    # 多層索引（日期, 股票）
                    stock_prices = price_df.xs(stock, level=1)[price_col]
                else:
                    # 單層索引，假設每列是一隻股票
                    if stock in price_df.columns:
                        stock_prices = price_df[stock]
                    else:
                        logger.warning(f"找不到股票 {stock} 的價格資料")
                        continue
                
                # 計算收益率
                stock_return = stock_prices.pct_change().dropna()
                stock_returns[stock] = stock_return * weight

            if not stock_returns:
                logger.error("無法計算任何股票的收益率")
                return pd.Series()

            # 合併所有股票的收益率
            returns_df = pd.DataFrame(stock_returns)
            portfolio_returns = returns_df.sum(axis=1)
            
            return portfolio_returns
            
        except Exception as e:
            logger.error(f"計算投資組合收益率失敗: {e}")
            return pd.Series()

    def _calculate_performance_metrics(self, returns: pd.Series) -> Dict[str, Any]:
        """計算績效指標
        
        Args:
            returns: 收益率時間序列
            
        Returns:
            績效指標字典
        """
        try:
            if returns.empty:
                return {}

            # 基本統計
            total_return = (1 + returns).prod() - 1
            annual_return = returns.mean() * 252
            annual_volatility = returns.std() * np.sqrt(252)
            
            # 夏普比率（假設無風險利率為 0）
            sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
            
            # 最大回撤
            cumulative_returns = (1 + returns).cumprod()
            max_drawdown = (cumulative_returns / cumulative_returns.cummax() - 1).min()
            
            # 勝率
            win_rate = (returns > 0).mean()
            
            # VaR（95% 信心水準）
            var_95 = returns.quantile(0.05)
            
            return {
                "total_return": total_return,
                "annual_return": annual_return,
                "annual_volatility": annual_volatility,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "win_rate": win_rate,
                "var_95": var_95,
                "num_periods": len(returns),
                "start_date": returns.index[0] if len(returns) > 0 else None,
                "end_date": returns.index[-1] if len(returns) > 0 else None,
            }
            
        except Exception as e:
            logger.error(f"計算績效指標失敗: {e}")
            return {}

    def rebalance(
        self, target_weights: Dict[str, float], current_prices: Dict[str, float]
    ) -> Dict[str, float]:
        """重新平衡到等權重
        
        Args:
            target_weights: 目標權重（會被忽略，強制等權重）
            current_prices: 當前價格
            
        Returns:
            等權重配置
        """
        # 等權重策略忽略目標權重，強制等權重
        stocks = list(current_prices.keys())
        if not stocks:
            return {}
            
        weight = 1.0 / len(stocks)
        return {stock: weight for stock in stocks}

    def get_strategy_info(self) -> Dict[str, Any]:
        """獲取策略資訊
        
        Returns:
            策略資訊字典
        """
        return {
            "name": "等權重投資組合",
            "description": "將資金平均分配給所有選中的股票",
            "advantages": [
                "簡單易懂",
                "不需要複雜計算",
                "天然分散風險",
                "避免過度集中"
            ],
            "disadvantages": [
                "忽略股票品質差異",
                "可能配置到劣質股票",
                "無法根據風險調整權重"
            ],
            "suitable_for": [
                "投資新手",
                "希望簡單分散的投資者",
                "作為基準策略"
            ]
        }
