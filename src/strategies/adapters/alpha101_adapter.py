# -*- coding: utf-8 -*-
"""
Alpha101 因子庫適配器

此模組將 ai_quant_trade-0.0.1 中的 Alpha101 因子庫適配到當前系統。
Alpha101 是 WorldQuant 開發的 101 個量化因子集合。

主要功能：
- 適配 Alpha101 因子計算函數
- 提供因子選擇和組合功能
- 基於因子值生成交易訊號
- 支援多因子策略構建

因子特色：
- 101 個經過驗證的量化因子
- 涵蓋價格、成交量、技術指標等多個維度
- 適用於股票、期貨等多種資產類別
- 支援因子組合和權重分配

Example:
    >>> adapter = Alpha101Adapter(factors=['alpha001', 'alpha002'], weights=[0.6, 0.4])
    >>> signals = adapter.generate_signals(price_data)
    >>> factor_values = adapter.calculate_factors(price_data)
"""

import logging
import sys
import os
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np

# 添加 ai_quant_trade-0.0.1 到路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
legacy_project_path = os.path.join(current_dir, '..', '..', '..', 'ai_quant_trade-0.0.1')
if os.path.exists(legacy_project_path):
    sys.path.insert(0, legacy_project_path)

from .base import LegacyStrategyAdapter, StrategyWrapper, AdapterError, DataConversionError
from ...strategy.base import ParameterError

# 設定日誌
logger = logging.getLogger(__name__)


class Alpha101Adapter(LegacyStrategyAdapter):
    """
    Alpha101 因子庫適配器。
    
    將 ai_quant_trade-0.0.1 中的 Alpha101 因子庫適配到當前系統，
    提供因子計算和基於因子的交易訊號生成功能。
    
    主要功能：
    1. 計算指定的 Alpha101 因子
    2. 支援多因子組合和權重分配
    3. 基於因子值生成交易訊號
    4. 提供因子分析和評估工具
    
    Attributes:
        factors (List[str]): 選擇的因子列表
        weights (List[float]): 因子權重列表
        signal_threshold (float): 訊號生成閾值
        
    Example:
        >>> adapter = Alpha101Adapter(
        ...     factors=['alpha001', 'alpha002', 'alpha003'],
        ...     weights=[0.5, 0.3, 0.2],
        ...     signal_threshold=0.02
        ... )
        >>> signals = adapter.generate_signals(price_data)
    """
    
    # 可用的 Alpha101 因子列表 (部分)
    AVAILABLE_FACTORS = [
        'alpha001', 'alpha002', 'alpha003', 'alpha004', 'alpha005',
        'alpha006', 'alpha007', 'alpha008', 'alpha009', 'alpha010',
        # 可以根據需要添加更多因子
    ]
    
    def __init__(self, 
                 factors: List[str] = None,
                 weights: List[float] = None,
                 signal_threshold: float = 0.02,
                 **kwargs) -> None:
        """
        初始化 Alpha101 因子庫適配器。
        
        Args:
            factors: 選擇的因子列表，默認使用前3個因子
            weights: 因子權重列表，默認等權重
            signal_threshold: 訊號生成閾值，默認0.02
            **kwargs: 其他策略參數
            
        Raises:
            ParameterError: 當參數不合法時
        """
        # 設定默認參數
        if factors is None:
            factors = ['alpha001', 'alpha002', 'alpha003']
        
        if weights is None:
            weights = [1.0 / len(factors)] * len(factors)
        
        parameters = {
            'factors': factors,
            'weights': weights,
            'signal_threshold': signal_threshold,
            **kwargs
        }
        
        super().__init__(name="Alpha101Strategy", **parameters)
        
        # 提取參數
        self.factors = self.parameters['factors']
        self.weights = self.parameters['weights']
        self.signal_threshold = self.parameters['signal_threshold']
        
        # 因子計算函數映射
        self.factor_functions = {}
        
        logger.info(f"Alpha101 因子庫適配器初始化完成，使用因子: {self.factors}")
    
    def _validate_parameters(self) -> None:
        """
        驗證策略參數。
        
        Raises:
            ParameterError: 當參數不合法時
        """
        super()._validate_parameters()
        
        factors = self.parameters.get('factors', [])
        weights = self.parameters.get('weights', [])
        signal_threshold = self.parameters.get('signal_threshold', 0.02)
        
        if not isinstance(factors, list) or len(factors) == 0:
            raise ParameterError(f"因子列表必須為非空列表，當前值: {factors}")
        
        if not isinstance(weights, list) or len(weights) != len(factors):
            raise ParameterError(f"權重列表長度必須與因子列表相同，因子數: {len(factors)}, 權重數: {len(weights)}")
        
        if not all(isinstance(w, (int, float)) and w >= 0 for w in weights):
            raise ParameterError(f"所有權重必須為非負數，當前值: {weights}")
        
        if abs(sum(weights) - 1.0) > 1e-6:
            raise ParameterError(f"權重總和必須為1，當前總和: {sum(weights)}")
        
        if not isinstance(signal_threshold, (int, float)) or signal_threshold <= 0:
            raise ParameterError(f"訊號閾值必須為正數，當前值: {signal_threshold}")
        
        # 檢查因子是否可用
        unavailable_factors = [f for f in factors if f not in self.AVAILABLE_FACTORS]
        if unavailable_factors:
            logger.warning(f"以下因子暫未實現: {unavailable_factors}")
    
    def _load_legacy_strategy(self) -> None:
        """
        載入原始 Alpha101 因子庫。
        
        從 ai_quant_trade-0.0.1 項目中導入 Alpha101 因子計算函數。
        """
        try:
            # 嘗試導入原始因子庫
            self._import_alpha101_functions()
            logger.info("成功載入原始 Alpha101 因子庫")
            
        except ImportError as e:
            # 如果無法導入原始因子庫，使用本地實現
            logger.warning(f"無法導入原始因子庫，使用本地實現: {e}")
            self._create_local_implementations()
    
    def _import_alpha101_functions(self) -> None:
        """
        導入原始 Alpha101 因子計算函數。
        """
        try:
            # 嘗試導入 Alpha101 模組 (文件名以數字開頭，需要特殊處理)
            import importlib.util
            alpha_module_path = os.path.join(legacy_project_path, 'egs_alpha', 'alpha_libs', 'alpha101', '101Alpha_code_1.py')

            if os.path.exists(alpha_module_path):
                spec = importlib.util.spec_from_file_location("alpha101_module", alpha_module_path)
                alpha_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(alpha_module)
            
                # 創建因子函數映射
                self.factor_functions = {
                    'alpha001': getattr(alpha_module, 'alpha001', None),
                    'alpha002': getattr(alpha_module, 'alpha002', None),
                    'alpha003': getattr(alpha_module, 'alpha003', None),
                    # 可以根據需要添加更多因子映射
                }

                # 過濾掉 None 值
                self.factor_functions = {k: v for k, v in self.factor_functions.items() if v is not None}
            else:
                raise ImportError("Alpha101 模組文件不存在")
            
            # 為每個因子創建包裝器
            for factor_name, factor_func in self.factor_functions.items():
                self.factor_functions[factor_name] = StrategyWrapper(
                    strategy_func=factor_func,
                    strategy_name=factor_name
                )
            
        except ImportError:
            raise ImportError("無法導入 Alpha101 因子庫")
    
    def _create_local_implementations(self) -> None:
        """
        創建本地因子實現。
        
        當無法導入原始因子庫時，提供簡化的本地實現。
        """
        def local_alpha001(close, returns, volume):
            """Alpha001 本地實現：基於收益率和成交量的因子"""
            try:
                # 簡化實現：收益率與成交量變化的相關性
                volume_change = volume.pct_change()
                correlation = returns.rolling(20).corr(volume_change)
                return correlation.fillna(0)
            except Exception:
                return pd.Series(0, index=close.index)
        
        def local_alpha002(close, returns, volume):
            """Alpha002 本地實現：基於價格動量的因子"""
            try:
                # 簡化實現：價格動量指標
                momentum = returns.rolling(10).sum()
                return momentum.fillna(0)
            except Exception:
                return pd.Series(0, index=close.index)
        
        def local_alpha003(close, returns, volume):
            """Alpha003 本地實現：基於波動率的因子"""
            try:
                # 簡化實現：滾動波動率
                volatility = returns.rolling(20).std()
                return -volatility.fillna(0)  # 負號表示低波動率偏好
            except Exception:
                return pd.Series(0, index=close.index)
        
        # 創建本地因子函數映射
        local_functions = {
            'alpha001': local_alpha001,
            'alpha002': local_alpha002,
            'alpha003': local_alpha003,
        }
        
        # 為每個因子創建包裝器
        self.factor_functions = {}
        for factor_name, factor_func in local_functions.items():
            self.factor_functions[factor_name] = StrategyWrapper(
                strategy_func=factor_func,
                strategy_name=f"local_{factor_name}"
            )
        
        logger.info("創建本地 Alpha101 因子實現")
    
    def _convert_parameters(self, **parameters: Any) -> Dict[str, Any]:
        """
        轉換策略參數格式。
        
        Args:
            **parameters: 當前系統參數格式
            
        Returns:
            原始策略期望的參數格式
        """
        return {
            'factors': parameters.get('factors', self.factors),
            'weights': parameters.get('weights', self.weights),
            'signal_threshold': parameters.get('signal_threshold', self.signal_threshold),
        }
    
    def _execute_legacy_strategy(self, data: pd.DataFrame, **parameters: Any) -> Dict[str, pd.Series]:
        """
        執行原始策略 - 計算因子值。
        
        Args:
            data: 輸入數據
            **parameters: 策略參數
            
        Returns:
            包含各因子計算結果的字典
        """
        try:
            factors = parameters.get('factors', self.factors)
            
            # 準備因子計算所需的數據
            close = data['close']
            returns = close.pct_change()
            volume = data.get('volume', pd.Series(1, index=data.index))
            
            # 計算各個因子
            factor_results = {}
            for factor_name in factors:
                if factor_name in self.factor_functions:
                    try:
                        factor_value = self.factor_functions[factor_name].execute(
                            close=close,
                            returns=returns,
                            volume=volume
                        )
                        factor_results[factor_name] = factor_value
                        logger.debug(f"成功計算因子 {factor_name}")
                    except Exception as e:
                        logger.error(f"計算因子 {factor_name} 失敗: {e}")
                        factor_results[factor_name] = pd.Series(0, index=data.index)
                else:
                    logger.warning(f"因子 {factor_name} 未實現，使用零值")
                    factor_results[factor_name] = pd.Series(0, index=data.index)
            
            logger.debug(f"因子計算完成，計算了 {len(factor_results)} 個因子")
            return factor_results
            
        except Exception as e:
            logger.error(f"執行因子計算失敗: {e}")
            raise AdapterError(f"執行因子計算失敗: {e}") from e
    
    def _convert_results(self, legacy_results: Dict[str, pd.Series], data: pd.DataFrame) -> pd.DataFrame:
        """
        轉換策略結果格式 - 基於因子值生成交易訊號。
        
        Args:
            legacy_results: 因子計算結果
            data: 輸入數據
            
        Returns:
            當前系統期望的訊號格式
        """
        try:
            # 創建標準訊號格式
            signals = pd.DataFrame(index=data.index)
            
            # 計算組合因子值
            combined_factor = pd.Series(0, index=data.index)
            for i, factor_name in enumerate(self.factors):
                if factor_name in legacy_results:
                    factor_value = legacy_results[factor_name]
                    weight = self.weights[i]
                    combined_factor += weight * factor_value.fillna(0)
            
            # 標準化因子值
            combined_factor = (combined_factor - combined_factor.mean()) / combined_factor.std().clip(lower=1e-8)
            
            # 基於因子值生成訊號
            signals['signal'] = 0.0
            signals['buy_signal'] = 0
            signals['sell_signal'] = 0
            
            # 使用閾值生成訊號
            buy_condition = combined_factor > self.signal_threshold
            sell_condition = combined_factor < -self.signal_threshold
            
            signals.loc[buy_condition, 'signal'] = 1.0
            signals.loc[buy_condition, 'buy_signal'] = 1
            signals.loc[sell_condition, 'signal'] = -1.0
            signals.loc[sell_condition, 'sell_signal'] = 1
            
            # 添加因子值供分析使用
            signals['combined_factor'] = combined_factor
            for factor_name, factor_value in legacy_results.items():
                signals[f'factor_{factor_name}'] = factor_value
            
            logger.debug(f"訊號生成完成，買入訊號: {signals['buy_signal'].sum()}, 賣出訊號: {signals['sell_signal'].sum()}")
            return signals
            
        except Exception as e:
            logger.error(f"結果轉換失敗: {e}")
            raise AdapterError(f"結果轉換失敗: {e}") from e
    
    def calculate_factors(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        計算因子值。
        
        Args:
            data: 輸入數據
            
        Returns:
            各因子的計算結果
        """
        try:
            # 轉換數據格式
            legacy_data = self.data_converter.convert_to_legacy_format(data)
            
            # 轉換參數格式
            legacy_parameters = self._convert_parameters(**self.parameters)
            
            # 執行因子計算
            factor_results = self._execute_legacy_strategy(legacy_data, **legacy_parameters)
            
            return factor_results
            
        except Exception as e:
            logger.error(f"因子計算失敗: {e}")
            raise AdapterError(f"因子計算失敗: {e}") from e
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        獲取策略資訊。
        
        Returns:
            策略詳細資訊
        """
        info = {
            'name': self.name,
            'type': 'Factor-based',
            'category': 'Alpha101',
            'parameters': {
                'factors': self.factors,
                'weights': self.weights,
                'signal_threshold': self.signal_threshold,
            },
            'description': 'Alpha101 因子庫策略，基於多個量化因子生成交易訊號',
            'source': 'ai_quant_trade-0.0.1',
            'adapter_version': '1.0.0',
            'available_factors': len(self.AVAILABLE_FACTORS),
        }
        
        # 添加因子執行統計
        if self.factor_functions:
            factor_stats = {}
            for factor_name, wrapper in self.factor_functions.items():
                if isinstance(wrapper, StrategyWrapper):
                    factor_stats[factor_name] = {
                        'execution_count': wrapper.execution_count,
                        'error_count': wrapper.error_count,
                        'success_rate': wrapper.success_rate,
                    }
            info['factor_execution_stats'] = factor_stats
        
        return info
