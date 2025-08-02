# -*- coding: utf-8 -*-
"""因子績效回測器

此模組提供因子策略的歷史回測、風險評估和績效分析功能，
支援單因子和多因子組合的回測驗證。

主要功能：
- 因子策略歷史回測
- 風險評估和指標計算
- 績效分析和歸因
- 分層回測和IC分析
- 多因子組合回測
- 基準比較和超額收益分析

支援的回測方法：
- 分層回測 (Layered Backtesting)
- IC 回測 (Information Coefficient)
- 多空組合回測 (Long-Short Portfolio)
- 等權重組合回測 (Equal Weight Portfolio)
- 市值加權回測 (Market Cap Weighted)

Example:
    >>> from src.strategies.adapters.factor_backtester import FactorBacktester
    >>> backtester = FactorBacktester()
    >>> 
    >>> # 單因子回測
    >>> results = backtester.backtest_single_factor(
    ...     factor_data, price_data, method='layered'
    ... )
    >>> 
    >>> # 多因子組合回測
    >>> portfolio_results = backtester.backtest_factor_portfolio(
    ...     factors, weights, price_data
    ... )
"""

import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
from scipy import stats

# 設定日誌
logger = logging.getLogger(__name__)

# 抑制警告
warnings.filterwarnings('ignore', category=RuntimeWarning)


class FactorBacktester:
    """因子績效回測器
    
    提供全面的因子策略回測和風險評估功能。
    
    Attributes:
        config: 回測配置
        
    Example:
        >>> backtester = FactorBacktester({
        ...     'layers': 5,
        ...     'rebalance_freq': 'monthly',
        ...     'transaction_cost': 0.002
        ... })
        >>> results = backtester.backtest_single_factor(factor, prices)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化因子回測器
        
        Args:
            config: 配置參數
                - layers: 分層數量
                - rebalance_freq: 調倉頻率
                - transaction_cost: 交易成本
                - benchmark: 基準指數
        """
        self.config = config or {}
        
        # 基本配置
        self.layers = self.config.get('layers', 5)
        self.rebalance_freq = self.config.get('rebalance_freq', 'monthly')
        self.transaction_cost = self.config.get('transaction_cost', 0.002)
        self.benchmark = self.config.get('benchmark', None)
        
        # 回測配置
        self.min_periods = self.config.get('min_periods', 20)
        self.max_weight = self.config.get('max_weight', 0.1)
        self.risk_free_rate = self.config.get('risk_free_rate', 0.03)
        
        logger.info("因子績效回測器初始化完成")
    
    def backtest_single_factor(self,
                              factor_data: pd.DataFrame,
                              price_data: pd.DataFrame,
                              method: str = 'layered',
                              **kwargs) -> Dict[str, Any]:
        """單因子回測
        
        Args:
            factor_data: 因子數據 (日期 x 股票)
            price_data: 價格數據 (日期 x 股票)
            method: 回測方法
            **kwargs: 其他參數
            
        Returns:
            回測結果
        """
        try:
            # 數據對齊和預處理
            factor_aligned, price_aligned = self._align_data(factor_data, price_data)
            
            if factor_aligned.empty or price_aligned.empty:
                raise ValueError("沒有有效的對齊數據")
            
            # 根據方法選擇回測策略
            if method == 'layered':
                results = self._layered_backtest(factor_aligned, price_aligned, **kwargs)
            elif method == 'ic_analysis':
                results = self._ic_backtest(factor_aligned, price_aligned, **kwargs)
            elif method == 'long_short':
                results = self._long_short_backtest(factor_aligned, price_aligned, **kwargs)
            elif method == 'equal_weight':
                results = self._equal_weight_backtest(factor_aligned, price_aligned, **kwargs)
            else:
                raise ValueError(f"不支援的回測方法: {method}")
            
            # 添加風險評估
            results['risk_metrics'] = self._calculate_risk_metrics(results)
            
            # 添加基準比較
            if self.benchmark is not None:
                results['benchmark_comparison'] = self._benchmark_comparison(results)
            
            logger.info(f"單因子回測完成，方法: {method}")
            return results
            
        except Exception as e:
            logger.error(f"單因子回測失敗: {e}")
            raise RuntimeError(f"單因子回測失敗: {e}") from e
    
    def backtest_factor_portfolio(self,
                                 factors: pd.DataFrame,
                                 weights: pd.Series,
                                 price_data: pd.DataFrame,
                                 **kwargs) -> Dict[str, Any]:
        """多因子組合回測
        
        Args:
            factors: 因子數據
            weights: 因子權重
            price_data: 價格數據
            **kwargs: 其他參數
            
        Returns:
            組合回測結果
        """
        try:
            # 構建組合因子
            composite_factor = self._build_composite_factor(factors, weights)
            
            # 執行回測
            results = self.backtest_single_factor(
                composite_factor, price_data, method='long_short', **kwargs
            )
            
            # 添加因子貢獻分析
            results['factor_contribution'] = self._analyze_factor_contribution(
                factors, weights, price_data
            )
            
            # 添加權重分析
            results['weight_analysis'] = {
                'factor_weights': weights,
                'weight_concentration': self._calculate_weight_concentration(weights),
                'effective_factors': (weights.abs() > 0.01).sum()
            }
            
            logger.info(f"多因子組合回測完成，因子數: {len(weights)}")
            return results
            
        except Exception as e:
            logger.error(f"多因子組合回測失敗: {e}")
            raise RuntimeError(f"多因子組合回測失敗: {e}") from e
    
    def _align_data(self, factor_data: pd.DataFrame, 
                   price_data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """對齊因子和價格數據"""
        # 找到共同的日期和股票
        common_dates = factor_data.index.intersection(price_data.index)
        common_stocks = factor_data.columns.intersection(price_data.columns)
        
        if len(common_dates) == 0:
            raise ValueError("因子和價格數據沒有共同的日期")
        
        if len(common_stocks) == 0:
            raise ValueError("因子和價格數據沒有共同的股票")
        
        # 對齊數據
        factor_aligned = factor_data.loc[common_dates, common_stocks]
        price_aligned = price_data.loc[common_dates, common_stocks]
        
        # 計算收益率
        returns = price_aligned.pct_change().dropna()
        
        # 確保因子和收益率對齊
        common_dates_final = factor_aligned.index.intersection(returns.index)
        factor_final = factor_aligned.loc[common_dates_final]
        returns_final = returns.loc[common_dates_final]
        
        return factor_final, returns_final
    
    def _layered_backtest(self, factor_data: pd.DataFrame, 
                         returns_data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """分層回測"""
        layers = kwargs.get('layers', self.layers)
        
        # 存儲每層的收益
        layer_returns = {f'layer_{i+1}': [] for i in range(layers)}
        layer_positions = {f'layer_{i+1}': [] for i in range(layers)}
        
        for date in factor_data.index:
            if date not in returns_data.index:
                continue
            
            factor_values = factor_data.loc[date].dropna()
            
            if len(factor_values) < layers:
                continue
            
            # 按因子值分層
            factor_sorted = factor_values.sort_values()
            layer_size = len(factor_sorted) // layers
            
            for i in range(layers):
                start_idx = i * layer_size
                end_idx = (i + 1) * layer_size if i < layers - 1 else len(factor_sorted)
                
                layer_stocks = factor_sorted.iloc[start_idx:end_idx].index
                
                # 計算該層的等權重收益
                if date in returns_data.index:
                    layer_return = returns_data.loc[date, layer_stocks].mean()
                    layer_returns[f'layer_{i+1}'].append(layer_return)
                    layer_positions[f'layer_{i+1}'].append(len(layer_stocks))
        
        # 轉換為 DataFrame
        layer_returns_df = pd.DataFrame(layer_returns, index=factor_data.index[:len(layer_returns['layer_1'])])
        
        # 計算累積收益
        cumulative_returns = (1 + layer_returns_df).cumprod()
        
        # 計算多空組合收益 (最高層 - 最低層)
        long_short_returns = layer_returns_df[f'layer_{layers}'] - layer_returns_df['layer_1']
        long_short_cumulative = (1 + long_short_returns).cumprod()
        
        return {
            'method': 'layered',
            'layer_returns': layer_returns_df,
            'cumulative_returns': cumulative_returns,
            'long_short_returns': long_short_returns,
            'long_short_cumulative': long_short_cumulative,
            'layer_positions': layer_positions,
            'performance_summary': self._calculate_performance_summary(layer_returns_df, long_short_returns)
        }
    
    def _ic_backtest(self, factor_data: pd.DataFrame, 
                    returns_data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """IC 分析回測"""
        ic_values = []
        rank_ic_values = []
        dates = []
        
        for date in factor_data.index[:-1]:  # 排除最後一天
            next_date_idx = factor_data.index.get_loc(date) + 1
            if next_date_idx >= len(factor_data.index):
                continue
            
            next_date = factor_data.index[next_date_idx]
            
            if next_date not in returns_data.index:
                continue
            
            factor_values = factor_data.loc[date].dropna()
            next_returns = returns_data.loc[next_date]
            
            # 找到共同的股票
            common_stocks = factor_values.index.intersection(next_returns.index)
            if len(common_stocks) < self.min_periods:
                continue
            
            factor_common = factor_values[common_stocks]
            returns_common = next_returns[common_stocks]
            
            # 計算 IC
            ic, _ = stats.pearsonr(factor_common, returns_common)
            
            # 計算 Rank IC
            factor_rank = factor_common.rank()
            returns_rank = returns_common.rank()
            rank_ic, _ = stats.pearsonr(factor_rank, returns_rank)
            
            if not np.isnan(ic) and not np.isnan(rank_ic):
                ic_values.append(ic)
                rank_ic_values.append(rank_ic)
                dates.append(date)
        
        # 創建 IC 時間序列
        ic_series = pd.Series(ic_values, index=dates)
        rank_ic_series = pd.Series(rank_ic_values, index=dates)
        
        # 計算 IC 統計
        ic_stats = {
            'ic_mean': ic_series.mean(),
            'ic_std': ic_series.std(),
            'ic_ir': ic_series.mean() / ic_series.std() if ic_series.std() > 0 else 0,
            'ic_win_rate': (ic_series > 0).mean(),
            'rank_ic_mean': rank_ic_series.mean(),
            'rank_ic_std': rank_ic_series.std(),
            'rank_ic_ir': rank_ic_series.mean() / rank_ic_series.std() if rank_ic_series.std() > 0 else 0
        }
        
        return {
            'method': 'ic_analysis',
            'ic_series': ic_series,
            'rank_ic_series': rank_ic_series,
            'ic_stats': ic_stats,
            'cumulative_ic': ic_series.cumsum(),
            'rolling_ic_mean': ic_series.rolling(20).mean(),
            'rolling_ic_std': ic_series.rolling(20).std()
        }
    
    def _long_short_backtest(self, factor_data: pd.DataFrame, 
                            returns_data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """多空組合回測"""
        long_pct = kwargs.get('long_pct', 0.3)  # 做多比例
        short_pct = kwargs.get('short_pct', 0.3)  # 做空比例
        
        portfolio_returns = []
        long_returns = []
        short_returns = []
        positions = []
        
        for date in factor_data.index:
            if date not in returns_data.index:
                continue
            
            factor_values = factor_data.loc[date].dropna()
            
            if len(factor_values) < 20:  # 最少需要20隻股票
                continue
            
            # 按因子值排序
            factor_sorted = factor_values.sort_values(ascending=False)
            
            # 選擇做多和做空的股票
            n_stocks = len(factor_sorted)
            n_long = int(n_stocks * long_pct)
            n_short = int(n_stocks * short_pct)
            
            long_stocks = factor_sorted.head(n_long).index
            short_stocks = factor_sorted.tail(n_short).index
            
            # 計算收益
            if date in returns_data.index:
                long_return = returns_data.loc[date, long_stocks].mean()
                short_return = returns_data.loc[date, short_stocks].mean()
                
                # 多空組合收益 (做多 - 做空)
                portfolio_return = long_return - short_return
                
                portfolio_returns.append(portfolio_return)
                long_returns.append(long_return)
                short_returns.append(short_return)
                positions.append({
                    'long_stocks': len(long_stocks),
                    'short_stocks': len(short_stocks),
                    'long_names': long_stocks.tolist(),
                    'short_names': short_stocks.tolist()
                })
        
        # 轉換為時間序列
        portfolio_returns_series = pd.Series(portfolio_returns, index=factor_data.index[:len(portfolio_returns)])
        long_returns_series = pd.Series(long_returns, index=factor_data.index[:len(long_returns)])
        short_returns_series = pd.Series(short_returns, index=factor_data.index[:len(short_returns)])
        
        # 計算累積收益
        cumulative_returns = (1 + portfolio_returns_series).cumprod()
        long_cumulative = (1 + long_returns_series).cumprod()
        short_cumulative = (1 + short_returns_series).cumprod()
        
        return {
            'method': 'long_short',
            'portfolio_returns': portfolio_returns_series,
            'long_returns': long_returns_series,
            'short_returns': short_returns_series,
            'cumulative_returns': cumulative_returns,
            'long_cumulative': long_cumulative,
            'short_cumulative': short_cumulative,
            'positions': positions,
            'performance_summary': self._calculate_performance_summary(
                pd.DataFrame({'portfolio': portfolio_returns_series}), 
                portfolio_returns_series
            )
        }
    
    def _equal_weight_backtest(self, factor_data: pd.DataFrame, 
                              returns_data: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """等權重組合回測"""
        top_pct = kwargs.get('top_pct', 0.2)  # 選擇前20%的股票
        
        portfolio_returns = []
        positions = []
        
        for date in factor_data.index:
            if date not in returns_data.index:
                continue
            
            factor_values = factor_data.loc[date].dropna()
            
            if len(factor_values) < 10:
                continue
            
            # 選擇因子值最高的股票
            n_select = max(1, int(len(factor_values) * top_pct))
            top_stocks = factor_values.nlargest(n_select).index
            
            # 計算等權重收益
            if date in returns_data.index:
                portfolio_return = returns_data.loc[date, top_stocks].mean()
                portfolio_returns.append(portfolio_return)
                positions.append({
                    'selected_stocks': len(top_stocks),
                    'stock_names': top_stocks.tolist()
                })
        
        # 轉換為時間序列
        portfolio_returns_series = pd.Series(portfolio_returns, index=factor_data.index[:len(portfolio_returns)])
        
        # 計算累積收益
        cumulative_returns = (1 + portfolio_returns_series).cumprod()
        
        return {
            'method': 'equal_weight',
            'portfolio_returns': portfolio_returns_series,
            'cumulative_returns': cumulative_returns,
            'positions': positions,
            'performance_summary': self._calculate_performance_summary(
                pd.DataFrame({'portfolio': portfolio_returns_series}), 
                portfolio_returns_series
            )
        }
    
    def _calculate_performance_summary(self, returns_df: pd.DataFrame, 
                                     main_strategy: pd.Series) -> Dict[str, Any]:
        """計算績效摘要"""
        try:
            # 基本統計
            total_return = (1 + main_strategy).prod() - 1
            annualized_return = (1 + main_strategy.mean()) ** 252 - 1
            volatility = main_strategy.std() * np.sqrt(252)
            
            # 夏普比率
            sharpe_ratio = (annualized_return - self.risk_free_rate) / volatility if volatility > 0 else 0
            
            # 最大回撤
            cumulative = (1 + main_strategy).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdown = (cumulative - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # 勝率
            win_rate = (main_strategy > 0).mean()
            
            # 卡瑪比率 (Calmar Ratio)
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # 索提諾比率 (Sortino Ratio)
            downside_returns = main_strategy[main_strategy < 0]
            downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
            sortino_ratio = (annualized_return - self.risk_free_rate) / downside_std if downside_std > 0 else 0
            
            return {
                'total_return': total_return,
                'annualized_return': annualized_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'calmar_ratio': calmar_ratio,
                'sortino_ratio': sortino_ratio,
                'win_rate': win_rate,
                'total_trades': len(main_strategy),
                'avg_return': main_strategy.mean(),
                'std_return': main_strategy.std(),
                'skewness': main_strategy.skew(),
                'kurtosis': main_strategy.kurtosis()
            }
            
        except Exception as e:
            logger.error(f"績效摘要計算失敗: {e}")
            return {}
    
    def _calculate_risk_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """計算風險指標"""
        try:
            if 'portfolio_returns' in results:
                returns = results['portfolio_returns']
            elif 'long_short_returns' in results:
                returns = results['long_short_returns']
            else:
                return {}
            
            # VaR 計算
            var_95 = returns.quantile(0.05)
            var_99 = returns.quantile(0.01)
            
            # CVaR 計算
            cvar_95 = returns[returns <= var_95].mean()
            cvar_99 = returns[returns <= var_99].mean()
            
            # 最大連續虧損
            cumulative = (1 + returns).cumprod()
            drawdown_periods = []
            in_drawdown = False
            drawdown_start = None
            
            for i, (date, value) in enumerate(cumulative.items()):
                if i == 0:
                    peak = value
                    continue
                
                if value > peak:
                    if in_drawdown:
                        drawdown_periods.append(i - drawdown_start)
                        in_drawdown = False
                    peak = value
                elif not in_drawdown:
                    in_drawdown = True
                    drawdown_start = i
            
            max_drawdown_duration = max(drawdown_periods) if drawdown_periods else 0
            
            return {
                'var_95': var_95,
                'var_99': var_99,
                'cvar_95': cvar_95,
                'cvar_99': cvar_99,
                'max_drawdown_duration': max_drawdown_duration,
                'downside_deviation': returns[returns < 0].std() if (returns < 0).any() else 0,
                'upside_deviation': returns[returns > 0].std() if (returns > 0).any() else 0
            }
            
        except Exception as e:
            logger.error(f"風險指標計算失敗: {e}")
            return {}
    
    def _build_composite_factor(self, factors: pd.DataFrame, 
                               weights: pd.Series) -> pd.DataFrame:
        """構建組合因子"""
        # 確保權重和因子對齊
        common_factors = factors.columns.intersection(weights.index)
        
        if len(common_factors) == 0:
            raise ValueError("因子和權重沒有共同的因子名稱")
        
        factors_aligned = factors[common_factors]
        weights_aligned = weights[common_factors]
        
        # 計算組合因子
        composite_factor = (factors_aligned * weights_aligned).sum(axis=1)
        
        return pd.DataFrame({'composite_factor': composite_factor})
    
    def _analyze_factor_contribution(self, factors: pd.DataFrame, 
                                   weights: pd.Series, 
                                   price_data: pd.DataFrame) -> Dict[str, Any]:
        """分析因子貢獻"""
        try:
            contributions = {}
            
            for factor_name in factors.columns:
                if factor_name in weights.index:
                    # 單因子回測
                    single_factor_data = pd.DataFrame({factor_name: factors[factor_name]})
                    single_result = self.backtest_single_factor(
                        single_factor_data, price_data, method='long_short'
                    )
                    
                    # 計算加權貢獻
                    weight = weights[factor_name]
                    contribution = single_result['performance_summary']['annualized_return'] * weight
                    
                    contributions[factor_name] = {
                        'weight': weight,
                        'individual_return': single_result['performance_summary']['annualized_return'],
                        'contribution': contribution,
                        'sharpe_ratio': single_result['performance_summary']['sharpe_ratio']
                    }
            
            return contributions
            
        except Exception as e:
            logger.error(f"因子貢獻分析失敗: {e}")
            return {}
    
    def _calculate_weight_concentration(self, weights: pd.Series) -> Dict[str, float]:
        """計算權重集中度"""
        abs_weights = weights.abs()
        
        return {
            'herfindahl_index': (abs_weights ** 2).sum(),
            'max_weight': abs_weights.max(),
            'top3_weight_sum': abs_weights.nlargest(3).sum(),
            'effective_number': 1 / (abs_weights ** 2).sum() if (abs_weights ** 2).sum() > 0 else 0
        }
    
    def _benchmark_comparison(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """基準比較分析"""
        # 這裡可以添加與基準指數的比較邏輯
        # 暫時返回空字典
        return {}
    
    def get_backtester_info(self) -> Dict[str, Any]:
        """獲取回測器資訊
        
        Returns:
            回測器詳細資訊
        """
        return {
            'backtester_name': 'FactorBacktester',
            'version': '1.0.0',
            'config': self.config,
            'supported_methods': [
                'layered',
                'ic_analysis',
                'long_short',
                'equal_weight'
            ],
            'supported_metrics': [
                'total_return',
                'annualized_return',
                'sharpe_ratio',
                'max_drawdown',
                'calmar_ratio',
                'sortino_ratio',
                'var',
                'cvar'
            ]
        }
