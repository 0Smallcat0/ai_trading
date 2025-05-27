"""
分散化管理模組

此模組實現了投資組合分散化管理和風險平價策略。
"""

from typing import Dict, List

import numpy as np
import pandas as pd

from src.core.logger import logger


class DiversificationManager:
    """
    分散化管理器

    管理投資組合的分散化，包括股票數量、行業分布和相關性等。
    """

    def __init__(self, min_stocks: int = 5, max_correlation: float = 0.7):
        """
        初始化分散化管理器

        Args:
            min_stocks: 最小股票數量
            max_correlation: 最大相關性
        """
        self.min_stocks = max(min_stocks, 1)
        self.max_correlation = min(max(max_correlation, 0.0), 1.0)

        logger.info(
            "初始化分散化管理器: 最小股票數量 %s, 最大相關性 %s",
            self.min_stocks,
            self.max_correlation,
        )

    def check_diversification(self, portfolio: Dict[str, float]) -> bool:
        """
        檢查分散化

        Args:
            portfolio: 投資組合，股票代碼到權重的映射

        Returns:
            bool: 是否符合分散化要求
        """
        # 檢查股票數量
        if len(portfolio) < self.min_stocks:
            logger.warning(
                "投資組合股票數量 %s 少於最小要求 %s",
                len(portfolio),
                self.min_stocks,
            )
            return False

        return True

    def suggest_diversification(
        self, portfolio: Dict[str, float], candidates: List[str]
    ) -> List[str]:
        """
        建議分散化

        Args:
            portfolio: 投資組合，股票代碼到權重的映射
            candidates: 候選股票列表

        Returns:
            List[str]: 建議添加的股票列表
        """
        # 檢查是否需要添加股票
        if len(portfolio) >= self.min_stocks:
            return []

        # 計算需要添加的股票數量
        to_add = self.min_stocks - len(portfolio)

        # 從候選列表中選擇
        suggestions = candidates[:to_add]

        logger.info("建議添加 %s 支股票以增加分散化: %s", len(suggestions), suggestions)

        return suggestions

    def calculate_diversification_ratio(self, portfolio_weights: Dict[str, float]) -> float:
        """
        計算分散化比率

        Args:
            portfolio_weights: 投資組合權重

        Returns:
            float: 分散化比率，範圍 0-1，越高越分散
        """
        if not portfolio_weights:
            return 0.0

        # 計算有效股票數量（Effective Number of Stocks）
        weights = list(portfolio_weights.values())
        sum_squared_weights = sum(w * w for w in weights)
        
        if sum_squared_weights == 0:
            return 0.0
            
        effective_stocks = 1 / sum_squared_weights
        max_effective_stocks = len(weights)
        
        # 標準化到 0-1 範圍
        if max_effective_stocks <= 1:
            return 1.0
            
        return (effective_stocks - 1) / (max_effective_stocks - 1)

    def get_concentration_metrics(self, portfolio_weights: Dict[str, float]) -> Dict[str, float]:
        """
        獲取集中度指標

        Args:
            portfolio_weights: 投資組合權重

        Returns:
            Dict[str, float]: 集中度指標
        """
        if not portfolio_weights:
            return {
                "herfindahl_index": 0.0,
                "effective_stocks": 0.0,
                "max_weight": 0.0,
                "top_5_concentration": 0.0,
                "diversification_ratio": 0.0,
            }

        weights = list(portfolio_weights.values())
        
        # 赫芬達爾指數
        herfindahl_index = sum(w * w for w in weights)
        
        # 有效股票數量
        effective_stocks = 1 / herfindahl_index if herfindahl_index > 0 else 0
        
        # 最大權重
        max_weight = max(weights) if weights else 0.0
        
        # 前5大持股集中度
        sorted_weights = sorted(weights, reverse=True)
        top_5_concentration = sum(sorted_weights[:5])
        
        # 分散化比率
        diversification_ratio = self.calculate_diversification_ratio(portfolio_weights)

        return {
            "herfindahl_index": herfindahl_index,
            "effective_stocks": effective_stocks,
            "max_weight": max_weight,
            "top_5_concentration": top_5_concentration,
            "diversification_ratio": diversification_ratio,
        }

    def optimize_diversification(
        self, current_weights: Dict[str, float], target_stocks: int
    ) -> Dict[str, float]:
        """
        優化分散化

        Args:
            current_weights: 當前權重
            target_stocks: 目標股票數量

        Returns:
            Dict[str, float]: 優化後的權重
        """
        if not current_weights or target_stocks <= 0:
            return current_weights

        # 如果當前股票數量已經達到目標，返回等權重分配
        if len(current_weights) >= target_stocks:
            equal_weight = 1.0 / len(current_weights)
            return {symbol: equal_weight for symbol in current_weights}

        # 如果需要更多股票，建議等權重分配現有股票
        equal_weight = 1.0 / len(current_weights)
        optimized_weights = {symbol: equal_weight for symbol in current_weights}

        logger.info(
            "優化分散化: 當前 %s 支股票，目標 %s 支股票",
            len(current_weights),
            target_stocks,
        )

        return optimized_weights


class RiskParityStrategy:
    """
    風險平價策略

    根據風險貢獻平衡投資組合權重。
    """

    def __init__(self, price_data: Dict[str, pd.DataFrame], lookback_period: int = 252):
        """
        初始化風險平價策略

        Args:
            price_data: 價格資料，股票代碼到價格資料的映射
            lookback_period: 回顧期間
        """
        self.price_data = price_data
        self.lookback_period = lookback_period

        logger.info(
            "初始化風險平價策略: 股票數量 %s, 回顧期間 %s",
            len(price_data),
            lookback_period,
        )

    def calculate_weights(self) -> Dict[str, float]:
        """
        計算風險平價權重

        Returns:
            Dict[str, float]: 股票代碼到權重的映射
        """
        # 提取收益率
        returns = {}
        for symbol, data in self.price_data.items():
            if "close" in data.columns:
                # 使用最近的數據
                recent_data = (
                    data.iloc[-self.lookback_period :]
                    if len(data) > self.lookback_period
                    else data
                )
                returns[symbol] = recent_data["close"].pct_change().dropna()

        # 創建收益率 DataFrame
        returns_df = pd.DataFrame(returns)

        # 計算協方差矩陣
        cov_matrix = returns_df.cov()

        # 計算波動率
        volatilities = np.sqrt(np.diag(cov_matrix))

        # 避免除零錯誤
        volatilities = np.where(volatilities == 0, 1e-8, volatilities)

        # 計算風險平價權重
        weights = 1 / volatilities
        weights = weights / np.sum(weights)

        # 轉換為字典
        weight_dict = {
            symbol: weight for symbol, weight in zip(returns.keys(), weights)
        }

        return weight_dict

    def calculate_risk_contributions(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        計算風險貢獻

        Args:
            weights: 投資組合權重

        Returns:
            Dict[str, float]: 風險貢獻
        """
        # 提取收益率
        returns = {}
        for symbol, data in self.price_data.items():
            if symbol in weights and "close" in data.columns:
                recent_data = (
                    data.iloc[-self.lookback_period :]
                    if len(data) > self.lookback_period
                    else data
                )
                returns[symbol] = recent_data["close"].pct_change().dropna()

        if not returns:
            return {symbol: 0.0 for symbol in weights}

        # 創建收益率 DataFrame
        returns_df = pd.DataFrame(returns)

        # 計算協方差矩陣
        cov_matrix = returns_df.cov()

        # 轉換權重為 numpy 數組
        symbols = list(weights.keys())
        weight_array = np.array([weights[symbol] for symbol in symbols])

        # 計算投資組合方差
        portfolio_variance = np.dot(weight_array, np.dot(cov_matrix.values, weight_array))

        # 計算邊際風險貢獻
        marginal_contributions = np.dot(cov_matrix.values, weight_array)

        # 計算風險貢獻
        risk_contributions = weight_array * marginal_contributions

        # 標準化風險貢獻
        if portfolio_variance > 0:
            risk_contributions = risk_contributions / portfolio_variance
        else:
            risk_contributions = np.zeros_like(risk_contributions)

        # 轉換為字典
        return {symbol: contrib for symbol, contrib in zip(symbols, risk_contributions)}

    def update_price_data(self, symbol: str, data: pd.DataFrame) -> None:
        """
        更新價格資料

        Args:
            symbol: 股票代碼
            data: 價格資料
        """
        self.price_data[symbol] = data

        logger.info("更新價格資料: %s", symbol)

    def get_risk_parity_metrics(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        獲取風險平價指標

        Args:
            weights: 投資組合權重

        Returns:
            Dict[str, float]: 風險平價指標
        """
        risk_contributions = self.calculate_risk_contributions(weights)
        
        if not risk_contributions:
            return {
                "risk_concentration": 0.0,
                "max_risk_contribution": 0.0,
                "min_risk_contribution": 0.0,
                "risk_parity_score": 0.0,
            }

        contributions = list(risk_contributions.values())
        
        # 風險集中度（使用赫芬達爾指數）
        risk_concentration = sum(c * c for c in contributions)
        
        # 最大和最小風險貢獻
        max_risk_contribution = max(contributions) if contributions else 0.0
        min_risk_contribution = min(contributions) if contributions else 0.0
        
        # 風險平價得分（越接近1越好）
        target_contribution = 1.0 / len(contributions) if contributions else 0.0
        deviations = [abs(c - target_contribution) for c in contributions]
        risk_parity_score = 1.0 - (sum(deviations) / len(deviations)) if deviations else 0.0

        return {
            "risk_concentration": risk_concentration,
            "max_risk_contribution": max_risk_contribution,
            "min_risk_contribution": min_risk_contribution,
            "risk_parity_score": max(0.0, risk_parity_score),
        }
