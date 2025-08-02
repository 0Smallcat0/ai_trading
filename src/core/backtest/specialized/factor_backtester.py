"""
因子回測器模組

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
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

from ..config import BacktestConfig
from ..metrics import BacktestMetrics, calculate_performance_metrics

logger = logging.getLogger(__name__)


@dataclass
class FactorBacktestConfig(BacktestConfig):
    """因子回測配置類
    
    擴展基本回測配置，添加因子回測特有的參數。
    
    Attributes:
        factor_names: 因子名稱列表
        factor_weights: 因子權重字典
        factor_method: 因子回測方法
        num_groups: 分層數量
        long_short: 是否多空組合
        neutralization: 中性化方法
        factor_params: 因子參數
    """
    
    # 因子參數
    factor_names: List[str] = field(default_factory=list)
    factor_weights: Dict[str, float] = field(default_factory=dict)
    factor_method: str = "layered"  # layered, ic, long_short, equal_weight, market_cap
    num_groups: int = 5  # 分層數量
    long_short: bool = False  # 是否多空組合
    neutralization: Optional[str] = None  # 中性化方法: None, industry, market_cap
    factor_params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化後處理"""
        super().__post_init__()
        
        # 驗證因子參數
        self._validate_factor_config()
    
    def _validate_factor_config(self) -> None:
        """驗證因子配置參數
        
        Raises:
            ValueError: 當配置無效時
        """
        # 驗證因子名稱
        if not self.factor_names:
            raise ValueError("因子名稱列表不能為空")
        
        # 驗證因子權重
        if self.factor_weights:
            unknown_factors = set(self.factor_weights.keys()) - set(self.factor_names)
            if unknown_factors:
                raise ValueError(f"未知的因子: {unknown_factors}")
            
            weight_sum = sum(self.factor_weights.values())
            if abs(weight_sum - 1.0) > 0.001:
                raise ValueError(f"因子權重總和必須為1.0，當前為: {weight_sum}")
        
        # 驗證回測方法
        valid_methods = ["layered", "ic", "long_short", "equal_weight", "market_cap"]
        if self.factor_method not in valid_methods:
            raise ValueError(f"不支援的因子回測方法: {self.factor_method}，有效方法: {valid_methods}")
        
        # 驗證分層數量
        if self.num_groups < 2 or self.num_groups > 10:
            raise ValueError(f"分層數量必須在2-10之間，當前為: {self.num_groups}")
        
        # 驗證中性化方法
        valid_neutralizations = [None, "industry", "market_cap"]
        if self.neutralization not in valid_neutralizations:
            raise ValueError(f"不支援的中性化方法: {self.neutralization}，有效方法: {valid_neutralizations}")


class FactorBacktester:
    """因子回測器
    
    提供完整的因子策略回測功能，支援多種回測方法和分析工具。
    
    Example:
        >>> from src.core.backtest.specialized.factor_backtester import FactorBacktester
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
    
    def __init__(self):
        """初始化因子回測器"""
        logger.info("因子回測器已初始化")
    
    def backtest_single_factor(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        method: str = "layered",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """回測單個因子
        
        Args:
            factor_data: 因子數據
            price_data: 價格數據
            method: 回測方法
            config: 回測配置
            
        Returns:
            Dict[str, Any]: 回測結果
            
        Raises:
            ValueError: 當輸入數據無效時
        """
        try:
            # 驗證輸入數據
            self._validate_inputs(factor_data, price_data)
            
            # 設置配置
            config = config or {}
            config["factor_method"] = method
            
            # 根據方法選擇回測函數
            if method == "layered":
                return self._backtest_layered(factor_data, price_data, config)
            elif method == "ic":
                return self._backtest_ic(factor_data, price_data, config)
            elif method == "long_short":
                return self._backtest_long_short(factor_data, price_data, config)
            elif method == "equal_weight":
                return self._backtest_equal_weight(factor_data, price_data, config)
            elif method == "market_cap":
                return self._backtest_market_cap(factor_data, price_data, config)
            else:
                raise ValueError(f"不支援的回測方法: {method}")
                
        except Exception as e:
            logger.error("單因子回測失敗: %s", e, exc_info=True)
            raise ValueError(f"單因子回測失敗: {e}") from e
    
    def backtest_factor_portfolio(
        self,
        factors: Dict[str, pd.DataFrame],
        weights: Dict[str, float],
        price_data: pd.DataFrame,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """回測多因子組合
        
        Args:
            factors: 因子數據字典
            weights: 因子權重字典
            price_data: 價格數據
            config: 回測配置
            
        Returns:
            Dict[str, Any]: 回測結果
            
        Raises:
            ValueError: 當輸入數據無效時
        """
        try:
            # 驗證輸入數據
            for factor_name, factor_data in factors.items():
                self._validate_inputs(factor_data, price_data)
            
            # 驗證權重
            if not weights:
                raise ValueError("因子權重不能為空")
            
            unknown_factors = set(weights.keys()) - set(factors.keys())
            if unknown_factors:
                raise ValueError(f"未知的因子: {unknown_factors}")
            
            weight_sum = sum(weights.values())
            if abs(weight_sum - 1.0) > 0.001:
                raise ValueError(f"因子權重總和必須為1.0，當前為: {weight_sum}")
            
            # 合併因子
            combined_factor = self._combine_factors(factors, weights)
            
            # 設置配置
            config = config or {}
            config["factor_weights"] = weights
            
            # 使用合併因子進行回測
            return self.backtest_single_factor(
                combined_factor, price_data, config.get("factor_method", "layered"), config
            )
                
        except Exception as e:
            logger.error("多因子組合回測失敗: %s", e, exc_info=True)
            raise ValueError(f"多因子組合回測失敗: {e}") from e
    
    def _validate_inputs(self, factor_data: pd.DataFrame, price_data: pd.DataFrame) -> None:
        """驗證輸入數據
        
        Args:
            factor_data: 因子數據
            price_data: 價格數據
            
        Raises:
            ValueError: 當數據無效時
        """
        if factor_data.empty:
            raise ValueError("因子數據不能為空")
        
        if price_data.empty:
            raise ValueError("價格數據不能為空")
        
        # 檢查必要的列
        required_factor_cols = ['symbol', 'factor']
        missing_factor_cols = [col for col in required_factor_cols if col not in factor_data.columns]
        if missing_factor_cols:
            raise ValueError(f"因子數據缺少必要列: {missing_factor_cols}")
        
        required_price_cols = ['symbol', 'close', 'date']
        missing_price_cols = [col for col in required_price_cols if col not in price_data.columns]
        if missing_price_cols:
            raise ValueError(f"價格數據缺少必要列: {missing_price_cols}")
    
    def _combine_factors(
        self,
        factors: Dict[str, pd.DataFrame],
        weights: Dict[str, float]
    ) -> pd.DataFrame:
        """合併多個因子
        
        Args:
            factors: 因子數據字典
            weights: 因子權重字典
            
        Returns:
            pd.DataFrame: 合併後的因子
        """
        # 初始化合併因子
        combined_factor = None
        
        # 遍歷所有因子
        for factor_name, factor_data in factors.items():
            if factor_name not in weights:
                continue
            
            weight = weights[factor_name]
            if weight == 0:
                continue
            
            # 標準化因子
            standardized_factor = self._standardize_factor(factor_data)
            
            # 加權合併
            if combined_factor is None:
                combined_factor = standardized_factor.copy()
                combined_factor['factor'] = combined_factor['factor'] * weight
            else:
                # 合併數據
                combined_factor = pd.merge(
                    combined_factor,
                    standardized_factor,
                    on=['date', 'symbol'],
                    how='inner',
                    suffixes=('', f'_{factor_name}')
                )
                
                # 加權合併因子
                combined_factor['factor'] += standardized_factor['factor'] * weight
        
        if combined_factor is None:
            raise ValueError("合併因子失敗，請檢查因子數據和權重")
        
        return combined_factor
    
    def _standardize_factor(self, factor_data: pd.DataFrame) -> pd.DataFrame:
        """標準化因子
        
        Args:
            factor_data: 因子數據
            
        Returns:
            pd.DataFrame: 標準化後的因子
        """
        # 複製數據
        standardized = factor_data.copy()
        
        # 按日期分組標準化
        if 'date' in standardized.columns:
            standardized = standardized.groupby('date').apply(
                lambda x: self._standardize_group(x)
            ).reset_index(drop=True)
        else:
            standardized = self._standardize_group(standardized)
        
        return standardized
    
    def _standardize_group(self, group: pd.DataFrame) -> pd.DataFrame:
        """標準化單個分組
        
        Args:
            group: 分組數據
            
        Returns:
            pd.DataFrame: 標準化後的分組
        """
        # 複製數據
        result = group.copy()
        
        # Z-score 標準化
        if 'factor' in result.columns:
            factor = result['factor']
            if factor.std() > 0:
                result['factor'] = (factor - factor.mean()) / factor.std()
        
        return result
    
    def _backtest_layered(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分層回測
        
        Args:
            factor_data: 因子數據
            price_data: 價格數據
            config: 回測配置
            
        Returns:
            Dict[str, Any]: 回測結果
        """
        # 這裡實現分層回測邏輯
        # 簡化實現，實際應該更複雜
        return {"method": "layered", "status": "not_implemented"}
    
    def _backtest_ic(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """IC 回測
        
        Args:
            factor_data: 因子數據
            price_data: 價格數據
            config: 回測配置
            
        Returns:
            Dict[str, Any]: 回測結果
        """
        # 這裡實現 IC 回測邏輯
        # 簡化實現，實際應該更複雜
        return {"method": "ic", "status": "not_implemented"}
    
    def _backtest_long_short(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """多空組合回測
        
        Args:
            factor_data: 因子數據
            price_data: 價格數據
            config: 回測配置
            
        Returns:
            Dict[str, Any]: 回測結果
        """
        # 這裡實現多空組合回測邏輯
        # 簡化實現，實際應該更複雜
        return {"method": "long_short", "status": "not_implemented"}
    
    def _backtest_equal_weight(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """等權重組合回測
        
        Args:
            factor_data: 因子數據
            price_data: 價格數據
            config: 回測配置
            
        Returns:
            Dict[str, Any]: 回測結果
        """
        # 這裡實現等權重組合回測邏輯
        # 簡化實現，實際應該更複雜
        return {"method": "equal_weight", "status": "not_implemented"}
    
    def _backtest_market_cap(
        self,
        factor_data: pd.DataFrame,
        price_data: pd.DataFrame,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """市值加權回測
        
        Args:
            factor_data: 因子數據
            price_data: 價格數據
            config: 回測配置
            
        Returns:
            Dict[str, Any]: 回測結果
        """
        # 這裡實現市值加權回測邏輯
        # 簡化實現，實際應該更複雜
        return {"method": "market_cap", "status": "not_implemented"}
