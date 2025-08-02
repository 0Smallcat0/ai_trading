# -*- coding: utf-8 -*-
"""因子組合優化器

此模組提供因子組合優化、權重分配和投資組合構建功能，
基於現代投資組合理論和機器學習方法實現最優因子組合。

主要功能：
- 因子組合優化算法
- 權重分配策略
- 風險平價模型
- 最大化夏普比率優化
- 最小化風險優化
- 因子投資組合構建

支援的優化方法：
- 均值方差優化 (Mean-Variance Optimization)
- 風險平價 (Risk Parity)
- 等權重 (Equal Weight)
- IC 加權 (IC Weighted)
- 最大分散化 (Maximum Diversification)
- 最小相關性 (Minimum Correlation)

Example:
    >>> from src.strategies.adapters.factor_optimizer import FactorOptimizer
    >>> optimizer = FactorOptimizer()
    >>> 
    >>> # 優化因子權重
    >>> weights = optimizer.optimize_factor_weights(
    ...     factors, returns, method='sharpe_ratio'
    ... )
    >>> 
    >>> # 構建投資組合
    >>> portfolio = optimizer.build_portfolio(factors, weights, returns)
"""

import logging
import warnings
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
from scipy import optimize
from sklearn.covariance import LedoitWolf
from sklearn.preprocessing import StandardScaler

# 設定日誌
logger = logging.getLogger(__name__)

# 抑制警告
warnings.filterwarnings('ignore', category=RuntimeWarning)


class FactorOptimizer:
    """因子組合優化器
    
    提供多種因子組合優化算法和權重分配策略。
    
    Attributes:
        config: 優化器配置
        
    Example:
        >>> optimizer = FactorOptimizer({
        ...     'risk_free_rate': 0.03,
        ...     'max_weight': 0.3,
        ...     'min_weight': 0.01
        ... })
        >>> weights = optimizer.optimize_factor_weights(factors, returns)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化因子組合優化器
        
        Args:
            config: 配置參數
                - risk_free_rate: 無風險利率
                - max_weight: 最大權重限制
                - min_weight: 最小權重限制
                - lookback_window: 回看窗口
        """
        self.config = config or {}
        
        # 基本配置
        self.risk_free_rate = self.config.get('risk_free_rate', 0.03)
        self.max_weight = self.config.get('max_weight', 0.5)
        self.min_weight = self.config.get('min_weight', 0.0)
        self.lookback_window = self.config.get('lookback_window', 252)
        
        # 優化配置
        self.regularization = self.config.get('regularization', 0.01)
        self.max_iterations = self.config.get('max_iterations', 1000)
        self.tolerance = self.config.get('tolerance', 1e-6)
        
        logger.info("因子組合優化器初始化完成")
    
    def optimize_factor_weights(self,
                               factors: pd.DataFrame,
                               returns: pd.Series,
                               method: str = 'sharpe_ratio',
                               constraints: Optional[Dict[str, Any]] = None) -> pd.Series:
        """優化因子權重
        
        Args:
            factors: 因子數據框架
            returns: 目標收益率
            method: 優化方法
            constraints: 額外約束條件
            
        Returns:
            優化後的因子權重
        """
        try:
            # 數據預處理
            factors_clean, returns_clean = self._preprocess_data(factors, returns)
            
            if factors_clean.empty:
                raise ValueError("沒有有效的因子數據")
            
            # 根據方法選擇優化算法
            if method == 'sharpe_ratio':
                weights = self._optimize_sharpe_ratio(factors_clean, returns_clean, constraints)
            elif method == 'min_variance':
                weights = self._optimize_min_variance(factors_clean, returns_clean, constraints)
            elif method == 'risk_parity':
                weights = self._optimize_risk_parity(factors_clean, returns_clean, constraints)
            elif method == 'equal_weight':
                weights = self._equal_weight(factors_clean)
            elif method == 'ic_weighted':
                weights = self._ic_weighted(factors_clean, returns_clean)
            elif method == 'max_diversification':
                weights = self._optimize_max_diversification(factors_clean, returns_clean, constraints)
            else:
                raise ValueError(f"不支援的優化方法: {method}")
            
            logger.info(f"使用 {method} 方法優化 {len(weights)} 個因子權重")
            return weights
            
        except Exception as e:
            logger.error(f"因子權重優化失敗: {e}")
            raise RuntimeError(f"因子權重優化失敗: {e}") from e
    
    def _preprocess_data(self, factors: pd.DataFrame, 
                        returns: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
        """數據預處理"""
        # 對齊數據
        common_index = factors.index.intersection(returns.index)
        if len(common_index) == 0:
            raise ValueError("因子和收益率數據沒有共同的索引")
        
        factors_aligned = factors.loc[common_index]
        returns_aligned = returns.loc[common_index]
        
        # 移除全為 NaN 的因子
        factors_clean = factors_aligned.dropna(axis=1, how='all')
        
        # 移除包含 NaN 的行
        valid_mask = ~(factors_clean.isna().any(axis=1) | returns_aligned.isna())
        factors_clean = factors_clean[valid_mask]
        returns_clean = returns_aligned[valid_mask]
        
        # 標準化因子
        scaler = StandardScaler()
        factors_scaled = pd.DataFrame(
            scaler.fit_transform(factors_clean),
            index=factors_clean.index,
            columns=factors_clean.columns
        )
        
        return factors_scaled, returns_clean
    
    def _optimize_sharpe_ratio(self, factors: pd.DataFrame, returns: pd.Series,
                              constraints: Optional[Dict[str, Any]] = None) -> pd.Series:
        """最大化夏普比率優化"""
        try:
            # 計算因子收益
            factor_returns = self._calculate_factor_returns(factors, returns)
            
            # 計算協方差矩陣
            cov_matrix = self._calculate_covariance_matrix(factor_returns)
            
            # 計算期望收益
            expected_returns = factor_returns.mean()
            
            n_factors = len(expected_returns)
            
            # 目標函數：最大化夏普比率 = 最小化 -夏普比率
            def objective(weights):
                portfolio_return = np.dot(weights, expected_returns)
                portfolio_risk = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
                
                if portfolio_risk == 0:
                    return -np.inf
                
                sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_risk
                return -sharpe_ratio  # 最小化負夏普比率
            
            # 約束條件
            constraints_list = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}  # 權重和為1
            ]
            
            # 添加自定義約束
            if constraints:
                constraints_list.extend(self._build_constraints(constraints, n_factors))
            
            # 邊界條件
            bounds = [(self.min_weight, self.max_weight) for _ in range(n_factors)]
            
            # 初始權重
            initial_weights = np.ones(n_factors) / n_factors
            
            # 優化
            result = optimize.minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints_list,
                options={'maxiter': self.max_iterations, 'ftol': self.tolerance}
            )
            
            if not result.success:
                logger.warning(f"夏普比率優化未收斂: {result.message}")
                # 使用等權重作為備選
                return self._equal_weight(factors)
            
            weights = pd.Series(result.x, index=factors.columns)
            return weights
            
        except Exception as e:
            logger.error(f"夏普比率優化失敗: {e}")
            return self._equal_weight(factors)
    
    def _optimize_min_variance(self, factors: pd.DataFrame, returns: pd.Series,
                              constraints: Optional[Dict[str, Any]] = None) -> pd.Series:
        """最小方差優化"""
        try:
            # 計算因子收益
            factor_returns = self._calculate_factor_returns(factors, returns)
            
            # 計算協方差矩陣
            cov_matrix = self._calculate_covariance_matrix(factor_returns)
            
            n_factors = len(factor_returns.columns)
            
            # 目標函數：最小化投資組合方差
            def objective(weights):
                return np.dot(weights, np.dot(cov_matrix, weights))
            
            # 約束條件
            constraints_list = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
            ]
            
            if constraints:
                constraints_list.extend(self._build_constraints(constraints, n_factors))
            
            # 邊界條件
            bounds = [(self.min_weight, self.max_weight) for _ in range(n_factors)]
            
            # 初始權重
            initial_weights = np.ones(n_factors) / n_factors
            
            # 優化
            result = optimize.minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints_list,
                options={'maxiter': self.max_iterations, 'ftol': self.tolerance}
            )
            
            if not result.success:
                logger.warning(f"最小方差優化未收斂: {result.message}")
                return self._equal_weight(factors)
            
            weights = pd.Series(result.x, index=factors.columns)
            return weights
            
        except Exception as e:
            logger.error(f"最小方差優化失敗: {e}")
            return self._equal_weight(factors)
    
    def _optimize_risk_parity(self, factors: pd.DataFrame, returns: pd.Series,
                             constraints: Optional[Dict[str, Any]] = None) -> pd.Series:
        """風險平價優化"""
        try:
            # 計算因子收益
            factor_returns = self._calculate_factor_returns(factors, returns)
            
            # 計算協方差矩陣
            cov_matrix = self._calculate_covariance_matrix(factor_returns)
            
            n_factors = len(factor_returns.columns)
            
            # 目標函數：最小化風險貢獻的差異
            def objective(weights):
                portfolio_var = np.dot(weights, np.dot(cov_matrix, weights))
                marginal_contrib = np.dot(cov_matrix, weights)
                contrib = weights * marginal_contrib / portfolio_var
                
                # 目標風險貢獻（等權重）
                target_contrib = np.ones(n_factors) / n_factors
                
                # 最小化風險貢獻與目標的差異
                return np.sum((contrib - target_contrib) ** 2)
            
            # 約束條件
            constraints_list = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
            ]
            
            if constraints:
                constraints_list.extend(self._build_constraints(constraints, n_factors))
            
            # 邊界條件
            bounds = [(self.min_weight, self.max_weight) for _ in range(n_factors)]
            
            # 初始權重（使用方差倒數加權）
            diag_var = np.diag(cov_matrix)
            initial_weights = (1 / diag_var) / np.sum(1 / diag_var)
            
            # 優化
            result = optimize.minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints_list,
                options={'maxiter': self.max_iterations, 'ftol': self.tolerance}
            )
            
            if not result.success:
                logger.warning(f"風險平價優化未收斂: {result.message}")
                return self._equal_weight(factors)
            
            weights = pd.Series(result.x, index=factors.columns)
            return weights
            
        except Exception as e:
            logger.error(f"風險平價優化失敗: {e}")
            return self._equal_weight(factors)
    
    def _equal_weight(self, factors: pd.DataFrame) -> pd.Series:
        """等權重分配"""
        n_factors = len(factors.columns)
        weights = pd.Series(1.0 / n_factors, index=factors.columns)
        return weights
    
    def _ic_weighted(self, factors: pd.DataFrame, returns: pd.Series) -> pd.Series:
        """基於 IC 的權重分配"""
        try:
            from scipy import stats
            
            ic_values = []
            
            for factor_name in factors.columns:
                factor_series = factors[factor_name]
                
                # 計算 IC
                valid_mask = ~(factor_series.isna() | returns.isna())
                if valid_mask.sum() < 10:
                    ic_values.append(0.0)
                    continue
                
                factor_clean = factor_series[valid_mask]
                returns_clean = returns[valid_mask]
                
                ic, _ = stats.pearsonr(factor_clean, returns_clean)
                ic_values.append(abs(ic) if not np.isnan(ic) else 0.0)
            
            # 標準化權重
            ic_array = np.array(ic_values)
            if ic_array.sum() == 0:
                return self._equal_weight(factors)
            
            weights = ic_array / ic_array.sum()
            return pd.Series(weights, index=factors.columns)
            
        except Exception as e:
            logger.error(f"IC 加權失敗: {e}")
            return self._equal_weight(factors)
    
    def _optimize_max_diversification(self, factors: pd.DataFrame, returns: pd.Series,
                                    constraints: Optional[Dict[str, Any]] = None) -> pd.Series:
        """最大分散化優化"""
        try:
            # 計算因子收益
            factor_returns = self._calculate_factor_returns(factors, returns)
            
            # 計算協方差矩陣和標準差
            cov_matrix = self._calculate_covariance_matrix(factor_returns)
            volatilities = np.sqrt(np.diag(cov_matrix))
            
            n_factors = len(factor_returns.columns)
            
            # 目標函數：最大化分散化比率
            def objective(weights):
                weighted_avg_vol = np.dot(weights, volatilities)
                portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
                
                if portfolio_vol == 0:
                    return -np.inf
                
                diversification_ratio = weighted_avg_vol / portfolio_vol
                return -diversification_ratio  # 最小化負分散化比率
            
            # 約束條件
            constraints_list = [
                {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
            ]
            
            if constraints:
                constraints_list.extend(self._build_constraints(constraints, n_factors))
            
            # 邊界條件
            bounds = [(self.min_weight, self.max_weight) for _ in range(n_factors)]
            
            # 初始權重
            initial_weights = np.ones(n_factors) / n_factors
            
            # 優化
            result = optimize.minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints_list,
                options={'maxiter': self.max_iterations, 'ftol': self.tolerance}
            )
            
            if not result.success:
                logger.warning(f"最大分散化優化未收斂: {result.message}")
                return self._equal_weight(factors)
            
            weights = pd.Series(result.x, index=factors.columns)
            return weights
            
        except Exception as e:
            logger.error(f"最大分散化優化失敗: {e}")
            return self._equal_weight(factors)
    
    def _calculate_factor_returns(self, factors: pd.DataFrame, 
                                 returns: pd.Series) -> pd.DataFrame:
        """計算因子收益"""
        factor_returns = pd.DataFrame(index=factors.index, columns=factors.columns)
        
        for factor_name in factors.columns:
            factor_series = factors[factor_name]
            
            # 構建因子策略收益
            factor_rank = factor_series.rank(pct=True)
            
            # 簡化的因子策略：top 30% 做多，bottom 30% 做空
            weights = pd.Series(0.0, index=factor_rank.index)
            weights[factor_rank >= 0.7] = 1.0
            weights[factor_rank <= 0.3] = -1.0
            
            # 計算因子收益
            factor_returns[factor_name] = weights * returns
        
        return factor_returns.fillna(0)
    
    def _calculate_covariance_matrix(self, returns: pd.DataFrame) -> np.ndarray:
        """計算協方差矩陣"""
        try:
            # 使用 Ledoit-Wolf 收縮估計器
            lw = LedoitWolf()
            cov_matrix = lw.fit(returns.fillna(0)).covariance_
            
            # 添加正則化項以確保正定性
            cov_matrix += np.eye(cov_matrix.shape[0]) * self.regularization
            
            return cov_matrix
            
        except Exception as e:
            logger.warning(f"協方差矩陣計算失敗，使用樣本協方差: {e}")
            cov_matrix = returns.cov().values
            cov_matrix += np.eye(cov_matrix.shape[0]) * self.regularization
            return cov_matrix
    
    def _build_constraints(self, constraints: Dict[str, Any], 
                          n_factors: int) -> List[Dict[str, Any]]:
        """構建約束條件"""
        constraints_list = []
        
        # 組別約束
        if 'group_constraints' in constraints:
            for group_name, group_info in constraints['group_constraints'].items():
                indices = group_info['indices']
                max_weight = group_info.get('max_weight', 1.0)
                min_weight = group_info.get('min_weight', 0.0)
                
                # 最大權重約束
                constraints_list.append({
                    'type': 'ineq',
                    'fun': lambda w, idx=indices: max_weight - np.sum(w[idx])
                })
                
                # 最小權重約束
                constraints_list.append({
                    'type': 'ineq',
                    'fun': lambda w, idx=indices: np.sum(w[idx]) - min_weight
                })
        
        # 換手率約束
        if 'turnover_constraint' in constraints:
            previous_weights = constraints['turnover_constraint']['previous_weights']
            max_turnover = constraints['turnover_constraint']['max_turnover']
            
            constraints_list.append({
                'type': 'ineq',
                'fun': lambda w: max_turnover - np.sum(np.abs(w - previous_weights))
            })
        
        return constraints_list
    
    def build_portfolio(self, factors: pd.DataFrame, weights: pd.Series,
                       returns: pd.Series) -> Dict[str, Any]:
        """構建因子投資組合
        
        Args:
            factors: 因子數據
            weights: 因子權重
            returns: 目標收益率
            
        Returns:
            投資組合信息
        """
        try:
            # 計算組合因子
            composite_factor = (factors * weights).sum(axis=1)
            
            # 計算組合收益
            factor_rank = composite_factor.rank(pct=True)
            
            # 構建投資組合權重
            portfolio_weights = pd.Series(0.0, index=factor_rank.index)
            portfolio_weights[factor_rank >= 0.7] = 1.0
            portfolio_weights[factor_rank <= 0.3] = -1.0
            
            # 標準化權重
            long_weight = portfolio_weights[portfolio_weights > 0].sum()
            short_weight = abs(portfolio_weights[portfolio_weights < 0].sum())
            
            if long_weight > 0:
                portfolio_weights[portfolio_weights > 0] /= long_weight
            if short_weight > 0:
                portfolio_weights[portfolio_weights < 0] /= short_weight
            
            # 計算投資組合收益
            portfolio_returns = portfolio_weights * returns
            
            # 計算績效指標
            total_return = (1 + portfolio_returns).prod() - 1
            annualized_return = (1 + portfolio_returns.mean()) ** 252 - 1
            volatility = portfolio_returns.std() * np.sqrt(252)
            sharpe_ratio = (annualized_return - self.risk_free_rate) / volatility if volatility > 0 else 0
            
            # 計算最大回撤
            cumulative_returns = (1 + portfolio_returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            return {
                'factor_weights': weights,
                'composite_factor': composite_factor,
                'portfolio_weights': portfolio_weights,
                'portfolio_returns': portfolio_returns,
                'performance': {
                    'total_return': total_return,
                    'annualized_return': annualized_return,
                    'volatility': volatility,
                    'sharpe_ratio': sharpe_ratio,
                    'max_drawdown': max_drawdown,
                    'win_rate': (portfolio_returns > 0).mean()
                }
            }
            
        except Exception as e:
            logger.error(f"投資組合構建失敗: {e}")
            raise RuntimeError(f"投資組合構建失敗: {e}") from e
    
    def get_optimizer_info(self) -> Dict[str, Any]:
        """獲取優化器資訊
        
        Returns:
            優化器詳細資訊
        """
        return {
            'optimizer_name': 'FactorOptimizer',
            'version': '1.0.0',
            'config': self.config,
            'supported_methods': [
                'sharpe_ratio',
                'min_variance',
                'risk_parity',
                'equal_weight',
                'ic_weighted',
                'max_diversification'
            ],
            'constraints_support': [
                'weight_bounds',
                'group_constraints',
                'turnover_constraint'
            ]
        }
