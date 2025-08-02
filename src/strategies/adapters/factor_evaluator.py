# -*- coding: utf-8 -*-
"""因子評估工具

此模組提供全面的因子有效性評估、相關性分析和選擇工具，包括：
- 因子有效性評估指標 (IC, IR, Sharpe Ratio, 最大回撤等)
- 因子相關性分析和去重機制
- 因子穩定性測試和時間序列分析
- 因子組合優化和權重分配
- 因子績效回測和風險評估

主要功能：
- 多維度因子評估指標計算
- 因子間相關性和多重共線性檢測
- 時間序列穩定性分析
- 因子選擇和組合優化算法
- 回測驗證和風險評估

Example:
    >>> evaluator = FactorEvaluator()
    >>> metrics = evaluator.evaluate_factor_effectiveness(factors, returns)
    >>> selected = evaluator.select_factors(factors, returns, method='ic')
"""

import logging
import warnings
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression

# 設定日誌
logger = logging.getLogger(__name__)

# 抑制警告
warnings.filterwarnings('ignore', category=RuntimeWarning)


class FactorEvaluator:
    """因子評估工具
    
    提供全面的因子評估、選擇和分析功能。
    
    Attributes:
        config: 評估配置參數
        
    Example:
        >>> evaluator = FactorEvaluator({
        ...     'ic_method': 'pearson',
        ...     'lookback_periods': [20, 60, 252],
        ...     'significance_level': 0.05
        ... })
        >>> metrics = evaluator.evaluate_factors(factors, returns)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化因子評估工具
        
        Args:
            config: 配置參數
                - ic_method: IC 計算方法 ('pearson', 'spearman', 'kendall')
                - lookback_periods: 回看期間列表
                - significance_level: 顯著性水平
                - min_periods: 最小期間數
        """
        self.config = config or {}
        
        # 基本配置
        self.ic_method = self.config.get('ic_method', 'pearson')
        self.lookback_periods = self.config.get('lookback_periods', [20, 60, 252])
        self.significance_level = self.config.get('significance_level', 0.05)
        self.min_periods = self.config.get('min_periods', 20)
        
        # 評估指標配置
        self.evaluation_metrics = self.config.get('evaluation_metrics', [
            'ic', 'ic_ir', 'rank_ic', 'sharpe_ratio', 'max_drawdown',
            'win_rate', 'stability', 'turnover'
        ])
        
        logger.info("因子評估工具初始化完成")
    
    def evaluate_factor_effectiveness(self,
                                    factors: pd.DataFrame,
                                    returns: pd.Series,
                                    **kwargs) -> Dict[str, Dict[str, float]]:
        """評估因子有效性
        
        Args:
            factors: 因子數據框架
            returns: 目標收益率序列
            **kwargs: 其他參數
            
        Returns:
            因子評估結果字典
        """
        try:
            # 數據對齊
            factors_aligned, returns_aligned = self._align_data(factors, returns)
            
            if len(factors_aligned) < self.min_periods:
                raise ValueError(f"數據長度不足，需要至少 {self.min_periods} 個觀測值")
            
            results = {}
            
            for factor_name in factors_aligned.columns:
                factor_series = factors_aligned[factor_name]
                
                # 跳過全為 NaN 的因子
                if factor_series.isna().all():
                    logger.warning(f"因子 {factor_name} 全為 NaN，跳過評估")
                    continue
                
                factor_metrics = {}
                
                # 計算各項評估指標
                if 'ic' in self.evaluation_metrics:
                    factor_metrics.update(self._calculate_ic_metrics(factor_series, returns_aligned))
                
                if 'sharpe_ratio' in self.evaluation_metrics:
                    factor_metrics['sharpe_ratio'] = self._calculate_factor_sharpe(factor_series, returns_aligned)
                
                if 'max_drawdown' in self.evaluation_metrics:
                    factor_metrics['max_drawdown'] = self._calculate_max_drawdown(factor_series, returns_aligned)
                
                if 'win_rate' in self.evaluation_metrics:
                    factor_metrics['win_rate'] = self._calculate_win_rate(factor_series, returns_aligned)
                
                if 'stability' in self.evaluation_metrics:
                    factor_metrics['stability'] = self._calculate_stability(factor_series, returns_aligned)
                
                if 'turnover' in self.evaluation_metrics:
                    factor_metrics['turnover'] = self._calculate_turnover(factor_series)
                
                results[factor_name] = factor_metrics
            
            logger.info(f"完成 {len(results)} 個因子的有效性評估")
            return results
            
        except Exception as e:
            logger.error(f"因子有效性評估失敗: {e}")
            raise RuntimeError(f"因子有效性評估失敗: {e}") from e
    
    def _align_data(self, factors: pd.DataFrame, returns: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
        """對齊因子和收益率數據"""
        # 找到共同的索引
        common_index = factors.index.intersection(returns.index)
        
        if len(common_index) == 0:
            raise ValueError("因子和收益率數據沒有共同的索引")
        
        # 對齊數據
        factors_aligned = factors.loc[common_index]
        returns_aligned = returns.loc[common_index]
        
        # 移除包含 NaN 的行
        valid_mask = ~(factors_aligned.isna().all(axis=1) | returns_aligned.isna())
        factors_aligned = factors_aligned[valid_mask]
        returns_aligned = returns_aligned[valid_mask]
        
        return factors_aligned, returns_aligned
    
    def _calculate_ic_metrics(self, factor: pd.Series, returns: pd.Series) -> Dict[str, float]:
        """計算 IC 相關指標"""
        metrics = {}
        
        try:
            # 移除 NaN 值
            valid_mask = ~(factor.isna() | returns.isna())
            factor_clean = factor[valid_mask]
            returns_clean = returns[valid_mask]
            
            if len(factor_clean) < self.min_periods:
                return {'ic': np.nan, 'ic_ir': np.nan, 'rank_ic': np.nan}
            
            # 計算 IC (Information Coefficient)
            if self.ic_method == 'pearson':
                ic, p_value = stats.pearsonr(factor_clean, returns_clean)
            elif self.ic_method == 'spearman':
                ic, p_value = stats.spearmanr(factor_clean, returns_clean)
            elif self.ic_method == 'kendall':
                ic, p_value = stats.kendalltau(factor_clean, returns_clean)
            else:
                ic, p_value = stats.pearsonr(factor_clean, returns_clean)
            
            metrics['ic'] = ic if not np.isnan(ic) else 0.0
            metrics['ic_pvalue'] = p_value if not np.isnan(p_value) else 1.0
            
            # 計算 Rank IC
            factor_rank = factor_clean.rank()
            returns_rank = returns_clean.rank()
            rank_ic, _ = stats.pearsonr(factor_rank, returns_rank)
            metrics['rank_ic'] = rank_ic if not np.isnan(rank_ic) else 0.0
            
            # 計算滾動 IC 和 IR
            rolling_ics = []
            for period in self.lookback_periods:
                if len(factor_clean) >= period:
                    rolling_ic = self._calculate_rolling_ic(factor_clean, returns_clean, period)
                    rolling_ics.extend(rolling_ic.dropna().tolist())
            
            if rolling_ics:
                ic_mean = np.mean(rolling_ics)
                ic_std = np.std(rolling_ics)
                metrics['ic_mean'] = ic_mean
                metrics['ic_std'] = ic_std
                metrics['ic_ir'] = ic_mean / ic_std if ic_std > 0 else 0.0
            else:
                metrics['ic_ir'] = 0.0
            
        except Exception as e:
            logger.warning(f"IC 指標計算失敗: {e}")
            metrics = {'ic': 0.0, 'ic_ir': 0.0, 'rank_ic': 0.0}
        
        return metrics
    
    def _calculate_rolling_ic(self, factor: pd.Series, returns: pd.Series, window: int) -> pd.Series:
        """計算滾動 IC"""
        def rolling_corr(x, y):
            if len(x) < 2 or len(y) < 2:
                return np.nan
            try:
                if self.ic_method == 'pearson':
                    corr, _ = stats.pearsonr(x, y)
                elif self.ic_method == 'spearman':
                    corr, _ = stats.spearmanr(x, y)
                else:
                    corr, _ = stats.pearsonr(x, y)
                return corr
            except:
                return np.nan
        
        # 使用滾動窗口計算相關性
        rolling_ic = pd.Series(index=factor.index, dtype=float)
        
        for i in range(window - 1, len(factor)):
            factor_window = factor.iloc[i - window + 1:i + 1]
            returns_window = returns.iloc[i - window + 1:i + 1]
            
            # 移除 NaN 值
            valid_mask = ~(factor_window.isna() | returns_window.isna())
            if valid_mask.sum() >= 2:
                ic = rolling_corr(factor_window[valid_mask], returns_window[valid_mask])
                rolling_ic.iloc[i] = ic
        
        return rolling_ic
    
    def _calculate_factor_sharpe(self, factor: pd.Series, returns: pd.Series) -> float:
        """計算因子夏普比率"""
        try:
            # 構建因子策略收益
            factor_returns = self._build_factor_strategy_returns(factor, returns)
            
            if len(factor_returns) == 0 or factor_returns.std() == 0:
                return 0.0
            
            # 計算夏普比率 (假設無風險利率為0)
            sharpe = factor_returns.mean() / factor_returns.std() * np.sqrt(252)
            return sharpe if not np.isnan(sharpe) else 0.0
            
        except Exception as e:
            logger.warning(f"夏普比率計算失敗: {e}")
            return 0.0
    
    def _build_factor_strategy_returns(self, factor: pd.Series, returns: pd.Series) -> pd.Series:
        """構建因子策略收益"""
        # 簡化的因子策略：根據因子值排名進行多空配置
        valid_mask = ~(factor.isna() | returns.isna())
        factor_clean = factor[valid_mask]
        returns_clean = returns[valid_mask]
        
        if len(factor_clean) == 0:
            return pd.Series(dtype=float)
        
        # 計算因子排名
        factor_rank = factor_clean.rank(pct=True)
        
        # 構建策略權重 (top 30% 做多，bottom 30% 做空)
        weights = pd.Series(0.0, index=factor_rank.index)
        weights[factor_rank >= 0.7] = 1.0   # 做多
        weights[factor_rank <= 0.3] = -1.0  # 做空
        
        # 計算策略收益
        strategy_returns = weights * returns_clean
        
        return strategy_returns
    
    def _calculate_max_drawdown(self, factor: pd.Series, returns: pd.Series) -> float:
        """計算最大回撤"""
        try:
            factor_returns = self._build_factor_strategy_returns(factor, returns)
            
            if len(factor_returns) == 0:
                return 0.0
            
            # 計算累積收益
            cumulative_returns = (1 + factor_returns).cumprod()
            
            # 計算回撤
            rolling_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - rolling_max) / rolling_max
            
            max_drawdown = drawdown.min()
            return max_drawdown if not np.isnan(max_drawdown) else 0.0
            
        except Exception as e:
            logger.warning(f"最大回撤計算失敗: {e}")
            return 0.0
    
    def _calculate_win_rate(self, factor: pd.Series, returns: pd.Series) -> float:
        """計算勝率"""
        try:
            factor_returns = self._build_factor_strategy_returns(factor, returns)
            
            if len(factor_returns) == 0:
                return 0.0
            
            win_rate = (factor_returns > 0).mean()
            return win_rate if not np.isnan(win_rate) else 0.0
            
        except Exception as e:
            logger.warning(f"勝率計算失敗: {e}")
            return 0.0
    
    def _calculate_stability(self, factor: pd.Series, returns: pd.Series) -> float:
        """計算因子穩定性"""
        try:
            # 計算不同時期的 IC
            ic_values = []
            
            # 分段計算 IC
            segment_length = max(60, len(factor) // 4)  # 至少60個觀測值，或總長度的1/4
            
            for i in range(0, len(factor) - segment_length + 1, segment_length // 2):
                end_idx = min(i + segment_length, len(factor))
                factor_segment = factor.iloc[i:end_idx]
                returns_segment = returns.iloc[i:end_idx]
                
                # 移除 NaN 值
                valid_mask = ~(factor_segment.isna() | returns_segment.isna())
                if valid_mask.sum() >= 10:  # 至少10個有效觀測值
                    factor_clean = factor_segment[valid_mask]
                    returns_clean = returns_segment[valid_mask]
                    
                    ic, _ = stats.pearsonr(factor_clean, returns_clean)
                    if not np.isnan(ic):
                        ic_values.append(ic)
            
            if len(ic_values) < 2:
                return 0.0
            
            # 穩定性 = 1 - IC標準差/|IC均值|
            ic_mean = np.mean(ic_values)
            ic_std = np.std(ic_values)
            
            if abs(ic_mean) > 0:
                stability = 1 - ic_std / abs(ic_mean)
                return max(0.0, min(1.0, stability))  # 限制在 [0, 1] 範圍內
            else:
                return 0.0
                
        except Exception as e:
            logger.warning(f"穩定性計算失敗: {e}")
            return 0.0
    
    def _calculate_turnover(self, factor: pd.Series) -> float:
        """計算因子換手率"""
        try:
            # 計算因子排名
            factor_rank = factor.rank(pct=True)
            
            # 計算排名變化
            rank_changes = factor_rank.diff().abs()
            
            # 平均換手率
            turnover = rank_changes.mean()
            return turnover if not np.isnan(turnover) else 0.0
            
        except Exception as e:
            logger.warning(f"換手率計算失敗: {e}")
            return 0.0
    
    def analyze_factor_correlation(self, factors: pd.DataFrame, 
                                 threshold: float = 0.8) -> Dict[str, Any]:
        """分析因子相關性
        
        Args:
            factors: 因子數據框架
            threshold: 相關性閾值
            
        Returns:
            相關性分析結果
        """
        try:
            # 移除全為 NaN 的因子
            factors_clean = factors.dropna(axis=1, how='all')
            
            if factors_clean.empty:
                return {'correlation_matrix': pd.DataFrame(), 'high_corr_pairs': []}
            
            # 計算相關性矩陣
            correlation_matrix = factors_clean.corr()
            
            # 找出高相關性因子對
            high_corr_pairs = []
            for i in range(len(correlation_matrix.columns)):
                for j in range(i + 1, len(correlation_matrix.columns)):
                    corr_value = correlation_matrix.iloc[i, j]
                    if abs(corr_value) >= threshold:
                        high_corr_pairs.append({
                            'factor1': correlation_matrix.columns[i],
                            'factor2': correlation_matrix.columns[j],
                            'correlation': corr_value
                        })
            
            # 按相關性絕對值排序
            high_corr_pairs.sort(key=lambda x: abs(x['correlation']), reverse=True)
            
            logger.info(f"發現 {len(high_corr_pairs)} 對高相關性因子 (閾值: {threshold})")
            
            return {
                'correlation_matrix': correlation_matrix,
                'high_corr_pairs': high_corr_pairs,
                'threshold': threshold,
                'summary': {
                    'total_factors': len(factors_clean.columns),
                    'high_corr_pairs_count': len(high_corr_pairs),
                    'avg_correlation': correlation_matrix.abs().mean().mean()
                }
            }
            
        except Exception as e:
            logger.error(f"因子相關性分析失敗: {e}")
            raise RuntimeError(f"因子相關性分析失敗: {e}") from e
    
    def select_factors(self,
                      factors: pd.DataFrame,
                      returns: pd.Series,
                      method: str = 'ic',
                      n_factors: int = 20,
                      **kwargs) -> List[str]:
        """選擇因子
        
        Args:
            factors: 因子數據框架
            returns: 目標收益率
            method: 選擇方法 ('ic', 'ic_ir', 'sharpe', 'mutual_info', 'f_test')
            n_factors: 選擇的因子數量
            **kwargs: 其他參數
            
        Returns:
            選擇的因子名稱列表
        """
        try:
            if method in ['ic', 'ic_ir', 'sharpe']:
                # 基於評估指標選擇
                evaluation_results = self.evaluate_factor_effectiveness(factors, returns)
                
                # 按指標排序
                factor_scores = []
                for factor_name, metrics in evaluation_results.items():
                    score = metrics.get(method, 0.0)
                    if not np.isnan(score):
                        factor_scores.append((factor_name, abs(score)))  # 使用絕對值
                
                # 排序並選擇前 n 個
                factor_scores.sort(key=lambda x: x[1], reverse=True)
                selected_factors = [name for name, score in factor_scores[:n_factors]]
                
            elif method == 'mutual_info':
                # 基於互信息選擇
                factors_aligned, returns_aligned = self._align_data(factors, returns)
                factors_filled = factors_aligned.fillna(0)
                
                selector = SelectKBest(score_func=mutual_info_regression, k=n_factors)
                selector.fit(factors_filled, returns_aligned)
                
                selected_indices = selector.get_support(indices=True)
                selected_factors = factors_aligned.columns[selected_indices].tolist()
                
            elif method == 'f_test':
                # 基於 F 檢驗選擇
                factors_aligned, returns_aligned = self._align_data(factors, returns)
                factors_filled = factors_aligned.fillna(0)
                
                selector = SelectKBest(score_func=f_regression, k=n_factors)
                selector.fit(factors_filled, returns_aligned)
                
                selected_indices = selector.get_support(indices=True)
                selected_factors = factors_aligned.columns[selected_indices].tolist()
                
            else:
                raise ValueError(f"不支援的選擇方法: {method}")
            
            logger.info(f"使用 {method} 方法選擇了 {len(selected_factors)} 個因子")
            return selected_factors
            
        except Exception as e:
            logger.error(f"因子選擇失敗: {e}")
            raise RuntimeError(f"因子選擇失敗: {e}") from e
    
    def remove_redundant_factors(self,
                                factors: pd.DataFrame,
                                returns: pd.Series,
                                correlation_threshold: float = 0.8,
                                selection_method: str = 'ic') -> List[str]:
        """移除冗餘因子
        
        Args:
            factors: 因子數據框架
            returns: 目標收益率
            correlation_threshold: 相關性閾值
            selection_method: 選擇方法
            
        Returns:
            去重後的因子名稱列表
        """
        try:
            # 分析相關性
            corr_analysis = self.analyze_factor_correlation(factors, correlation_threshold)
            high_corr_pairs = corr_analysis['high_corr_pairs']
            
            if not high_corr_pairs:
                return factors.columns.tolist()
            
            # 評估因子有效性
            evaluation_results = self.evaluate_factor_effectiveness(factors, returns)
            
            # 構建因子評分字典
            factor_scores = {}
            for factor_name, metrics in evaluation_results.items():
                score = metrics.get(selection_method, 0.0)
                factor_scores[factor_name] = abs(score) if not np.isnan(score) else 0.0
            
            # 去重邏輯：對於高相關的因子對，保留評分更高的因子
            factors_to_remove = set()
            
            for pair in high_corr_pairs:
                factor1, factor2 = pair['factor1'], pair['factor2']
                
                # 如果其中一個已經被標記移除，跳過
                if factor1 in factors_to_remove or factor2 in factors_to_remove:
                    continue
                
                # 比較評分，移除評分較低的因子
                score1 = factor_scores.get(factor1, 0.0)
                score2 = factor_scores.get(factor2, 0.0)
                
                if score1 >= score2:
                    factors_to_remove.add(factor2)
                else:
                    factors_to_remove.add(factor1)
            
            # 返回保留的因子
            remaining_factors = [f for f in factors.columns if f not in factors_to_remove]
            
            logger.info(f"移除了 {len(factors_to_remove)} 個冗餘因子，保留 {len(remaining_factors)} 個因子")
            return remaining_factors
            
        except Exception as e:
            logger.error(f"冗餘因子移除失敗: {e}")
            raise RuntimeError(f"冗餘因子移除失敗: {e}") from e
    
    def analyze_factor_stability(self,
                                factors: pd.DataFrame,
                                returns: pd.Series,
                                window_size: int = 252,
                                step_size: int = 63) -> Dict[str, Dict[str, Any]]:
        """分析因子穩定性

        Args:
            factors: 因子數據框架
            returns: 目標收益率
            window_size: 分析窗口大小（交易日）
            step_size: 步長（交易日）

        Returns:
            因子穩定性分析結果
        """
        try:
            factors_aligned, returns_aligned = self._align_data(factors, returns)

            if len(factors_aligned) < window_size * 2:
                raise ValueError(f"數據長度不足，需要至少 {window_size * 2} 個觀測值")

            stability_results = {}

            for factor_name in factors_aligned.columns:
                factor_series = factors_aligned[factor_name]

                if factor_series.isna().all():
                    continue

                # 滾動窗口分析
                rolling_metrics = self._rolling_window_analysis(
                    factor_series, returns_aligned, window_size, step_size
                )

                # 時間序列分析
                time_series_analysis = self._time_series_analysis(
                    factor_series, returns_aligned
                )

                # 衰減檢測
                decay_analysis = self._decay_analysis(
                    factor_series, returns_aligned
                )

                stability_results[factor_name] = {
                    'rolling_metrics': rolling_metrics,
                    'time_series_analysis': time_series_analysis,
                    'decay_analysis': decay_analysis,
                    'overall_stability_score': self._calculate_stability_score(
                        rolling_metrics, time_series_analysis, decay_analysis
                    )
                }

            logger.info(f"完成 {len(stability_results)} 個因子的穩定性分析")
            return stability_results

        except Exception as e:
            logger.error(f"因子穩定性分析失敗: {e}")
            raise RuntimeError(f"因子穩定性分析失敗: {e}") from e

    def _rolling_window_analysis(self, factor: pd.Series, returns: pd.Series,
                                window_size: int, step_size: int) -> Dict[str, Any]:
        """滾動窗口分析"""
        ic_values = []
        sharpe_values = []
        periods = []

        for start_idx in range(0, len(factor) - window_size + 1, step_size):
            end_idx = start_idx + window_size

            factor_window = factor.iloc[start_idx:end_idx]
            returns_window = returns.iloc[start_idx:end_idx]

            # 移除 NaN 值
            valid_mask = ~(factor_window.isna() | returns_window.isna())
            if valid_mask.sum() < self.min_periods:
                continue

            factor_clean = factor_window[valid_mask]
            returns_clean = returns_window[valid_mask]

            # 計算 IC
            try:
                if self.ic_method == 'pearson':
                    ic, _ = stats.pearsonr(factor_clean, returns_clean)
                elif self.ic_method == 'spearman':
                    ic, _ = stats.spearmanr(factor_clean, returns_clean)
                else:
                    ic, _ = stats.pearsonr(factor_clean, returns_clean)

                if not np.isnan(ic):
                    ic_values.append(ic)

                    # 計算該窗口的夏普比率
                    factor_returns = self._build_factor_strategy_returns(factor_clean, returns_clean)
                    if len(factor_returns) > 0 and factor_returns.std() > 0:
                        sharpe = factor_returns.mean() / factor_returns.std() * np.sqrt(252)
                        sharpe_values.append(sharpe)
                    else:
                        sharpe_values.append(0.0)

                    periods.append(factor.index[start_idx])

            except Exception as e:
                logger.debug(f"滾動窗口計算失敗: {e}")
                continue

        if not ic_values:
            return {
                'ic_mean': 0.0,
                'ic_std': 0.0,
                'ic_stability': 0.0,
                'sharpe_mean': 0.0,
                'sharpe_std': 0.0,
                'periods_analyzed': 0
            }

        ic_mean = np.mean(ic_values)
        ic_std = np.std(ic_values)
        ic_stability = 1 - (ic_std / abs(ic_mean)) if abs(ic_mean) > 0 else 0.0

        return {
            'ic_values': ic_values,
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'ic_stability': max(0.0, min(1.0, ic_stability)),
            'sharpe_values': sharpe_values,
            'sharpe_mean': np.mean(sharpe_values),
            'sharpe_std': np.std(sharpe_values),
            'periods': periods,
            'periods_analyzed': len(ic_values)
        }

    def _time_series_analysis(self, factor: pd.Series, returns: pd.Series) -> Dict[str, Any]:
        """時間序列分析"""
        try:
            from scipy import signal
            from statsmodels.tsa.stattools import adfuller
            from statsmodels.stats.diagnostic import acorr_ljungbox

            # 計算滾動 IC
            rolling_ic = self._calculate_rolling_ic(factor, returns, 60)  # 60天滾動窗口
            rolling_ic_clean = rolling_ic.dropna()

            if len(rolling_ic_clean) < 10:
                return {'error': '數據不足進行時間序列分析'}

            # 平穩性檢驗 (ADF test)
            try:
                adf_result = adfuller(rolling_ic_clean)
                is_stationary = adf_result[1] < 0.05  # p-value < 0.05 表示平穩
            except:
                is_stationary = False

            # 自相關檢驗
            try:
                ljung_box = acorr_ljungbox(rolling_ic_clean, lags=10, return_df=True)
                has_autocorr = (ljung_box['lb_pvalue'] < 0.05).any()
            except:
                has_autocorr = False

            # 趨勢分析
            time_index = np.arange(len(rolling_ic_clean))
            try:
                slope, intercept, r_value, p_value, std_err = stats.linregress(time_index, rolling_ic_clean)
                has_trend = p_value < 0.05
                trend_direction = 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
            except:
                slope, r_value, p_value = 0, 0, 1
                has_trend = False
                trend_direction = 'stable'

            # 週期性分析
            try:
                # 使用 FFT 檢測週期性
                fft = np.fft.fft(rolling_ic_clean - rolling_ic_clean.mean())
                freqs = np.fft.fftfreq(len(rolling_ic_clean))
                power = np.abs(fft) ** 2

                # 找到最強的頻率成分
                dominant_freq_idx = np.argmax(power[1:len(power)//2]) + 1
                dominant_period = 1 / abs(freqs[dominant_freq_idx]) if freqs[dominant_freq_idx] != 0 else 0

                # 檢查是否有顯著的週期性
                has_seasonality = power[dominant_freq_idx] > np.mean(power) * 3
            except:
                dominant_period = 0
                has_seasonality = False

            return {
                'is_stationary': is_stationary,
                'adf_pvalue': adf_result[1] if 'adf_result' in locals() else 1.0,
                'has_autocorr': has_autocorr,
                'has_trend': has_trend,
                'trend_direction': trend_direction,
                'trend_slope': slope,
                'trend_r_squared': r_value ** 2,
                'trend_pvalue': p_value,
                'has_seasonality': has_seasonality,
                'dominant_period': dominant_period,
                'rolling_ic_mean': rolling_ic_clean.mean(),
                'rolling_ic_std': rolling_ic_clean.std()
            }

        except ImportError:
            logger.warning("缺少時間序列分析依賴庫 (scipy, statsmodels)")
            return {'error': '缺少必要的依賴庫'}
        except Exception as e:
            logger.error(f"時間序列分析失敗: {e}")
            return {'error': str(e)}

    def _decay_analysis(self, factor: pd.Series, returns: pd.Series) -> Dict[str, Any]:
        """衰減分析"""
        try:
            # 計算不同持有期的 IC
            holding_periods = [1, 5, 10, 20, 60]  # 1天、1週、2週、1月、3月
            ic_by_period = {}

            for period in holding_periods:
                if len(factor) <= period:
                    continue

                # 計算前瞻收益
                forward_returns = returns.shift(-period)

                # 對齊數據
                valid_mask = ~(factor.isna() | forward_returns.isna())
                if valid_mask.sum() < self.min_periods:
                    continue

                factor_clean = factor[valid_mask]
                forward_returns_clean = forward_returns[valid_mask]

                # 計算 IC
                try:
                    ic, p_value = stats.pearsonr(factor_clean, forward_returns_clean)
                    if not np.isnan(ic):
                        ic_by_period[period] = {
                            'ic': ic,
                            'abs_ic': abs(ic),
                            'p_value': p_value,
                            'significant': p_value < self.significance_level
                        }
                except:
                    continue

            if not ic_by_period:
                return {'error': '無法計算衰減分析'}

            # 分析衰減模式
            periods = sorted(ic_by_period.keys())
            ic_values = [ic_by_period[p]['abs_ic'] for p in periods]

            # 計算衰減率
            if len(ic_values) >= 2:
                # 使用指數衰減模型擬合
                try:
                    from scipy.optimize import curve_fit

                    def exp_decay(x, a, b):
                        return a * np.exp(-b * x)

                    popt, _ = curve_fit(exp_decay, periods, ic_values, maxfev=1000)
                    decay_rate = popt[1]
                    half_life = np.log(2) / decay_rate if decay_rate > 0 else np.inf

                except:
                    # 簡單線性衰減
                    slope, _, _, _, _ = stats.linregress(periods, ic_values)
                    decay_rate = -slope
                    half_life = ic_values[0] / (2 * abs(slope)) if slope != 0 else np.inf
            else:
                decay_rate = 0
                half_life = np.inf

            # 計算衰減穩定性
            ic_1d = ic_by_period.get(1, {}).get('abs_ic', 0)
            ic_20d = ic_by_period.get(20, {}).get('abs_ic', 0)

            if ic_1d > 0:
                decay_stability = ic_20d / ic_1d
            else:
                decay_stability = 0

            return {
                'ic_by_period': ic_by_period,
                'decay_rate': decay_rate,
                'half_life_days': half_life,
                'decay_stability': decay_stability,
                'optimal_holding_period': max(ic_by_period.keys(),
                                            key=lambda k: ic_by_period[k]['abs_ic']) if ic_by_period else 1
            }

        except Exception as e:
            logger.error(f"衰減分析失敗: {e}")
            return {'error': str(e)}

    def _calculate_stability_score(self, rolling_metrics: Dict,
                                 time_series_analysis: Dict,
                                 decay_analysis: Dict) -> float:
        """計算綜合穩定性評分"""
        try:
            score = 0.0
            weight_sum = 0.0

            # IC 穩定性 (權重: 0.4)
            if 'ic_stability' in rolling_metrics:
                score += rolling_metrics['ic_stability'] * 0.4
                weight_sum += 0.4

            # 時間序列穩定性 (權重: 0.3)
            if 'error' not in time_series_analysis:
                ts_score = 0.0

                # 平穩性
                if time_series_analysis.get('is_stationary', False):
                    ts_score += 0.3

                # 無顯著趨勢
                if not time_series_analysis.get('has_trend', True):
                    ts_score += 0.4

                # 無強自相關
                if not time_series_analysis.get('has_autocorr', True):
                    ts_score += 0.3

                score += ts_score * 0.3
                weight_sum += 0.3

            # 衰減穩定性 (權重: 0.3)
            if 'error' not in decay_analysis:
                decay_score = min(1.0, decay_analysis.get('decay_stability', 0))
                score += decay_score * 0.3
                weight_sum += 0.3

            # 標準化評分
            if weight_sum > 0:
                score = score / weight_sum

            return max(0.0, min(1.0, score))

        except Exception as e:
            logger.error(f"穩定性評分計算失敗: {e}")
            return 0.0

    def get_evaluator_info(self) -> Dict[str, Any]:
        """獲取評估工具資訊

        Returns:
            評估工具詳細資訊
        """
        return {
            'evaluator_name': 'FactorEvaluator',
            'version': '1.0.0',
            'config': self.config,
            'ic_method': self.ic_method,
            'lookback_periods': self.lookback_periods,
            'evaluation_metrics': self.evaluation_metrics,
            'significance_level': self.significance_level,
            'min_periods': self.min_periods,
            'supported_analyses': [
                'factor_effectiveness',
                'factor_correlation',
                'factor_selection',
                'factor_stability',
                'time_series_analysis',
                'decay_analysis'
            ]
        }
