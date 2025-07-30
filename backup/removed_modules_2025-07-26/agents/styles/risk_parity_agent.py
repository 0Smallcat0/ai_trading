# -*- coding: utf-8 -*-
"""
風險平價代理模組

此模組實現基於風險預算的投資組合代理。

投資哲學：
- 基於風險貢獻的資產配置
- 分散化投資
- 風險預算管理
- 動態再平衡

主要功能：
- 風險平價權重計算
- 風險貢獻分析
- 投資組合優化
- 動態再平衡策略
- 風險預算管理
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from scipy.optimize import minimize
import warnings

from ..base import TradingAgent, AgentDecision, InvestmentStyle, RiskPreference

# 設定日誌
logger = logging.getLogger(__name__)

# 忽略優化警告
warnings.filterwarnings('ignore', category=RuntimeWarning)


class RiskParityAgent(TradingAgent):
    """
    風險平價代理。
    
    基於風險預算進行投資組合管理，包括：
    - 風險平價權重計算
    - 風險貢獻分析
    - 協方差矩陣估計
    - 動態再平衡
    - 風險預算約束
    
    Attributes:
        lookback_period (int): 風險估計回望期間
        rebalance_frequency (int): 再平衡頻率
        risk_budget (Dict[str, float]): 風險預算分配
        min_weight (float): 最小權重約束
        max_weight (float): 最大權重約束
        volatility_target (float): 目標波動率
        correlation_threshold (float): 相關性閾值
        risk_tolerance (float): 風險容忍度
    """
    
    def __init__(
        self,
        name: str = "RiskParityAgent",
        lookback_period: int = 60,
        rebalance_frequency: int = 20,
        risk_budget: Optional[Dict[str, float]] = None,
        min_weight: float = 0.05,
        max_weight: float = 0.4,
        volatility_target: float = 0.12,
        correlation_threshold: float = 0.8,
        risk_tolerance: float = 0.15,
        **parameters: Any
    ) -> None:
        """
        初始化風險平價代理。
        
        Args:
            name: 代理名稱
            lookback_period: 風險估計回望期間
            rebalance_frequency: 再平衡頻率（天數）
            risk_budget: 風險預算分配字典
            min_weight: 最小權重約束
            max_weight: 最大權重約束
            volatility_target: 目標波動率（年化）
            correlation_threshold: 相關性閾值
            risk_tolerance: 風險容忍度
            **parameters: 其他策略參數
        """
        super().__init__(
            name=name,
            investment_style=InvestmentStyle.RISK_PARITY,
            risk_preference=RiskPreference.MODERATE,
            max_position_size=0.4,  # 風險平價可能集中在某些資產
            **parameters
        )
        
        # 風險平價參數
        self.lookback_period = lookback_period
        self.rebalance_frequency = rebalance_frequency
        self.risk_budget = risk_budget or {}
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.volatility_target = volatility_target
        self.correlation_threshold = correlation_threshold
        self.risk_tolerance = risk_tolerance
        
        # 投資組合追蹤
        self.current_weights: Dict[str, float] = {}
        self.target_weights: Dict[str, float] = {}
        self.risk_contributions: Dict[str, float] = {}
        self.last_rebalance: Optional[datetime] = None
        self.covariance_matrix: Optional[np.ndarray] = None
        self.asset_list: List[str] = []
        
        logger.info(f"初始化風險平價代理: {name}")
    
    def make_decision(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """
        基於風險平價分析生成投資決策。
        
        Args:
            data: 市場數據，包含多個資產的價格數據
            market_context: 市場上下文信息
            
        Returns:
            AgentDecision: 投資決策
        """
        try:
            symbol = market_context.get('symbol', 'UNKNOWN') if market_context else 'UNKNOWN'
            portfolio_assets = market_context.get('portfolio_assets', []) if market_context else []
            
            # 檢查數據完整性
            if not self._validate_data(data, portfolio_assets):
                return self._create_hold_decision(symbol, "數據不完整或資產不足")
            
            # 檢查是否需要再平衡
            if not self._should_rebalance():
                return self._create_hold_decision(symbol, "未到再平衡時間")
            
            # 準備資產數據
            asset_returns = self._prepare_asset_data(data, portfolio_assets)
            
            # 估計風險模型
            risk_model = self._estimate_risk_model(asset_returns)
            
            # 計算風險平價權重
            risk_parity_weights = self._calculate_risk_parity_weights(risk_model)
            
            # 分析當前配置
            portfolio_analysis = self._analyze_current_portfolio(risk_parity_weights, risk_model)
            
            # 生成再平衡決策
            decision = self._generate_rebalance_decision(
                symbol, risk_parity_weights, portfolio_analysis
            )
            
            # 更新內部狀態
            self._update_portfolio_state(risk_parity_weights, risk_model)
            
            return decision
            
        except Exception as e:
            logger.error(f"風險平價決策生成失敗: {e}")
            return self._create_hold_decision(symbol, f"決策生成錯誤: {e}")
    
    def _validate_data(self, data: pd.DataFrame, portfolio_assets: List[str]) -> bool:
        """驗證數據完整性"""
        if len(data) < self.lookback_period:
            logger.warning(f"數據不足，需要至少{self.lookback_period}個週期")
            return False
        
        # 檢查資產數量
        if len(portfolio_assets) < 2:
            # 嘗試從數據欄位推斷資產
            price_columns = [col for col in data.columns if 'close' in col.lower() or 'price' in col.lower()]
            if len(price_columns) < 2:
                logger.warning("需要至少兩個資產進行風險平價配置")
                return False
            portfolio_assets = [col.replace('_close', '').replace('close_', '') for col in price_columns]
        
        self.asset_list = portfolio_assets
        return True
    
    def _should_rebalance(self) -> bool:
        """檢查是否需要再平衡"""
        if self.last_rebalance is None:
            return True
        
        days_since_rebalance = (datetime.now() - self.last_rebalance).days
        return days_since_rebalance >= self.rebalance_frequency
    
    def _prepare_asset_data(self, data: pd.DataFrame, portfolio_assets: List[str]) -> pd.DataFrame:
        """準備資產數據"""
        asset_prices = {}
        
        for asset in portfolio_assets:
            price_series = self._get_price_series(asset, data)
            if price_series is not None:
                asset_prices[asset] = price_series
        
        # 創建價格數據框
        price_df = pd.DataFrame(asset_prices)
        
        # 計算收益率
        returns_df = price_df.pct_change().dropna()
        
        return returns_df
    
    def _get_price_series(self, asset: str, data: pd.DataFrame) -> Optional[pd.Series]:
        """獲取資產價格序列"""
        possible_columns = [
            f'{asset}_close',
            f'close_{asset}',
            f'{asset}',
            asset.upper(),
            asset.lower()
        ]
        
        for col in possible_columns:
            if col in data.columns:
                return data[col]
        
        return None
    
    def _estimate_risk_model(self, returns: pd.DataFrame) -> Dict[str, Any]:
        """估計風險模型"""
        # 計算協方差矩陣
        cov_matrix = returns.cov().values
        
        # 計算相關性矩陣
        corr_matrix = returns.corr().values
        
        # 計算波動率
        volatilities = returns.std().values
        
        # 計算預期收益率（簡化使用歷史平均）
        expected_returns = returns.mean().values
        
        return {
            'covariance_matrix': cov_matrix,
            'correlation_matrix': corr_matrix,
            'volatilities': volatilities,
            'expected_returns': expected_returns,
            'asset_names': list(returns.columns)
        }
    
    def _calculate_risk_parity_weights(self, risk_model: Dict[str, Any]) -> Dict[str, float]:
        """計算風險平價權重"""
        cov_matrix = risk_model['covariance_matrix']
        asset_names = risk_model['asset_names']
        n_assets = len(asset_names)
        
        # 目標風險貢獻（等風險貢獻）
        target_risk_contrib = np.ones(n_assets) / n_assets
        
        # 如果有自定義風險預算，使用自定義分配
        if self.risk_budget:
            for i, asset in enumerate(asset_names):
                if asset in self.risk_budget:
                    target_risk_contrib[i] = self.risk_budget[asset]
        
        # 標準化風險預算
        target_risk_contrib = target_risk_contrib / target_risk_contrib.sum()
        
        # 優化權重
        optimal_weights = self._optimize_risk_parity_weights(cov_matrix, target_risk_contrib)
        
        # 轉換為字典格式
        weights_dict = {}
        for i, asset in enumerate(asset_names):
            weights_dict[asset] = optimal_weights[i]
        
        return weights_dict
    
    def _optimize_risk_parity_weights(
        self,
        cov_matrix: np.ndarray,
        target_risk_contrib: np.ndarray
    ) -> np.ndarray:
        """優化風險平價權重"""
        n_assets = len(target_risk_contrib)
        
        # 目標函數：最小化風險貢獻與目標的差異
        def objective(weights):
            weights = np.array(weights)
            portfolio_vol = np.sqrt(weights.T @ cov_matrix @ weights)
            
            if portfolio_vol == 0:
                return 1e6
            
            # 計算風險貢獻
            marginal_contrib = cov_matrix @ weights
            risk_contrib = weights * marginal_contrib / portfolio_vol
            
            # 標準化風險貢獻
            risk_contrib = risk_contrib / risk_contrib.sum()
            
            # 計算與目標的差異
            error = np.sum((risk_contrib - target_risk_contrib) ** 2)
            
            return error
        
        # 約束條件
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}  # 權重和為1
        ]
        
        # 邊界條件
        bounds = [(self.min_weight, self.max_weight) for _ in range(n_assets)]
        
        # 初始猜測（等權重）
        x0 = np.ones(n_assets) / n_assets
        
        # 優化
        try:
            result = minimize(
                objective,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000}
            )
            
            if result.success:
                return result.x
            else:
                logger.warning("風險平價優化失敗，使用等權重")
                return x0
                
        except Exception as e:
            logger.warning(f"風險平價優化錯誤: {e}，使用等權重")
            return x0

    def _analyze_current_portfolio(
        self,
        target_weights: Dict[str, float],
        risk_model: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析當前投資組合"""
        # 計算目標投資組合的風險指標
        weights_array = np.array(list(target_weights.values()))
        cov_matrix = risk_model['covariance_matrix']

        # 投資組合波動率
        portfolio_vol = np.sqrt(weights_array.T @ cov_matrix @ weights_array)

        # 風險貢獻
        marginal_contrib = cov_matrix @ weights_array
        risk_contributions = weights_array * marginal_contrib / portfolio_vol if portfolio_vol > 0 else np.zeros_like(weights_array)

        # 轉換為字典
        risk_contrib_dict = {}
        for i, asset in enumerate(target_weights.keys()):
            risk_contrib_dict[asset] = risk_contributions[i]

        # 分散化比率
        diversification_ratio = self._calculate_diversification_ratio(weights_array, risk_model)

        # 與當前權重的差異
        weight_changes = {}
        for asset, target_weight in target_weights.items():
            current_weight = self.current_weights.get(asset, 0.0)
            weight_changes[asset] = target_weight - current_weight

        return {
            'target_weights': target_weights,
            'portfolio_volatility': portfolio_vol,
            'risk_contributions': risk_contrib_dict,
            'diversification_ratio': diversification_ratio,
            'weight_changes': weight_changes,
            'max_weight_change': max(abs(change) for change in weight_changes.values()) if weight_changes else 0
        }

    def _calculate_diversification_ratio(
        self,
        weights: np.ndarray,
        risk_model: Dict[str, Any]
    ) -> float:
        """計算分散化比率"""
        try:
            volatilities = risk_model['volatilities']
            cov_matrix = risk_model['covariance_matrix']

            # 加權平均波動率
            weighted_avg_vol = np.sum(weights * volatilities)

            # 投資組合波動率
            portfolio_vol = np.sqrt(weights.T @ cov_matrix @ weights)

            # 分散化比率
            if portfolio_vol > 0:
                diversification_ratio = weighted_avg_vol / portfolio_vol
            else:
                diversification_ratio = 1.0

            return diversification_ratio

        except Exception as e:
            logger.warning(f"分散化比率計算失敗: {e}")
            return 1.0

    def _generate_rebalance_decision(
        self,
        symbol: str,
        target_weights: Dict[str, float],
        portfolio_analysis: Dict[str, Any]
    ) -> AgentDecision:
        """生成再平衡決策"""
        current_time = datetime.now()

        # 檢查是否需要顯著調整
        max_weight_change = portfolio_analysis['max_weight_change']

        if max_weight_change < 0.02:  # 權重變化小於2%
            return self._create_hold_decision(symbol, "權重變化較小，無需再平衡")

        # 確定對當前symbol的操作
        target_weight = target_weights.get(symbol, 0.0)
        current_weight = self.current_weights.get(symbol, 0.0)
        weight_change = target_weight - current_weight

        if weight_change > 0.01:  # 增加權重
            action = 1
            confidence = min(0.8, abs(weight_change) * 10)
            reasoning = self._generate_increase_reasoning(symbol, target_weight, weight_change, portfolio_analysis)
        elif weight_change < -0.01:  # 減少權重
            action = -1
            confidence = min(0.8, abs(weight_change) * 10)
            reasoning = self._generate_decrease_reasoning(symbol, target_weight, weight_change, portfolio_analysis)
        else:  # 權重變化很小
            action = 0
            confidence = 0.6
            reasoning = f"風險平價權重調整：{symbol}目標權重{target_weight:.1%}，變化較小"

        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=current_time,
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            expected_return=self._estimate_risk_parity_return(portfolio_analysis),
            risk_assessment=self._assess_portfolio_risk(portfolio_analysis),
            position_size=target_weight,
            metadata={
                'target_weight': target_weight,
                'current_weight': current_weight,
                'weight_change': weight_change,
                'portfolio_volatility': portfolio_analysis['portfolio_volatility'],
                'diversification_ratio': portfolio_analysis['diversification_ratio'],
                'risk_contribution': portfolio_analysis['risk_contributions'].get(symbol, 0.0),
                'is_rebalance': True
            }
        )

    def _generate_increase_reasoning(
        self,
        symbol: str,
        target_weight: float,
        weight_change: float,
        portfolio_analysis: Dict[str, Any]
    ) -> str:
        """生成增加權重推理"""
        risk_contrib = portfolio_analysis['risk_contributions'].get(symbol, 0.0)
        return (f"風險平價再平衡：增加{symbol}權重至{target_weight:.1%}（+{weight_change:.1%}），"
                f"目標風險貢獻{risk_contrib:.1%}")

    def _generate_decrease_reasoning(
        self,
        symbol: str,
        target_weight: float,
        weight_change: float,
        portfolio_analysis: Dict[str, Any]
    ) -> str:
        """生成減少權重推理"""
        risk_contrib = portfolio_analysis['risk_contributions'].get(symbol, 0.0)
        return (f"風險平價再平衡：減少{symbol}權重至{target_weight:.1%}（{weight_change:.1%}），"
                f"目標風險貢獻{risk_contrib:.1%}")

    def _update_portfolio_state(
        self,
        target_weights: Dict[str, float],
        risk_model: Dict[str, Any]
    ) -> None:
        """更新投資組合狀態"""
        self.target_weights = target_weights.copy()
        self.covariance_matrix = risk_model['covariance_matrix']
        self.last_rebalance = datetime.now()

        # 計算風險貢獻
        weights_array = np.array(list(target_weights.values()))
        portfolio_vol = np.sqrt(weights_array.T @ self.covariance_matrix @ weights_array)

        if portfolio_vol > 0:
            marginal_contrib = self.covariance_matrix @ weights_array
            risk_contributions = weights_array * marginal_contrib / portfolio_vol

            self.risk_contributions = {}
            for i, asset in enumerate(target_weights.keys()):
                self.risk_contributions[asset] = risk_contributions[i]

    def _create_hold_decision(self, symbol: str, reason: str) -> AgentDecision:
        """創建持有決策"""
        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            symbol=symbol,
            action=0,
            confidence=0.6,
            reasoning=reason,
            expected_return=0.0,
            risk_assessment=0.3,  # 風險平價風險較低
            position_size=self.current_weights.get(symbol, 0.0)
        )

    def _estimate_risk_parity_return(self, portfolio_analysis: Dict[str, Any]) -> float:
        """估算風險平價收益率"""
        # 基於分散化比率和目標波動率估算收益率
        diversification_ratio = portfolio_analysis['diversification_ratio']
        portfolio_vol = portfolio_analysis['portfolio_volatility']

        # 風險平價通常提供穩定的風險調整收益
        base_return = 0.06  # 基準6%年化收益率

        # 分散化獎勵
        diversification_bonus = (diversification_ratio - 1.0) * 0.02

        # 波動率調整
        vol_adjustment = (self.volatility_target - portfolio_vol) * 0.5

        expected_return = base_return + diversification_bonus + vol_adjustment

        return max(0.0, min(expected_return, 0.12))  # 0-12%範圍

    def _assess_portfolio_risk(self, portfolio_analysis: Dict[str, Any]) -> float:
        """評估投資組合風險"""
        portfolio_vol = portfolio_analysis['portfolio_volatility']
        diversification_ratio = portfolio_analysis['diversification_ratio']

        # 基於波動率的風險評估
        vol_risk = min(portfolio_vol / self.volatility_target, 1.0)

        # 分散化風險（分散化比率越低，風險越高）
        diversification_risk = max(0.0, 2.0 - diversification_ratio) / 2.0

        # 綜合風險評估
        overall_risk = (vol_risk * 0.7 + diversification_risk * 0.3)

        return min(overall_risk, 1.0)

    def get_investment_philosophy(self) -> str:
        """獲取投資哲學描述"""
        return (
            "風險平價哲學：基於風險貢獻的資產配置，追求風險分散和穩定收益。"
            f"目標波動率：{self.volatility_target:.1%}，再平衡頻率：{self.rebalance_frequency}天，"
            f"權重約束：{self.min_weight:.1%}-{self.max_weight:.1%}。"
            "策略特點：風險分散、動態平衡、穩健配置。"
        )

    def get_current_weights(self) -> Dict[str, float]:
        """獲取當前權重"""
        return self.current_weights.copy()

    def get_target_weights(self) -> Dict[str, float]:
        """獲取目標權重"""
        return self.target_weights.copy()

    def get_risk_contributions(self) -> Dict[str, float]:
        """獲取風險貢獻"""
        return self.risk_contributions.copy()

    def update_current_weights(self, weights: Dict[str, float]) -> None:
        """更新當前權重"""
        self.current_weights = weights.copy()
        logger.info("更新風險平價代理當前權重")

    def set_risk_budget(self, risk_budget: Dict[str, float]) -> None:
        """設置風險預算"""
        # 標準化風險預算
        total_budget = sum(risk_budget.values())
        if total_budget > 0:
            self.risk_budget = {asset: budget/total_budget for asset, budget in risk_budget.items()}
            logger.info(f"更新風險預算: {self.risk_budget}")

    def __str__(self) -> str:
        """字符串表示"""
        return f"RiskParityAgent(assets={len(self.current_weights)})"
