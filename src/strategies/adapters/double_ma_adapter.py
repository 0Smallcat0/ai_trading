# -*- coding: utf-8 -*-
"""
雙移動平均線策略適配器

此模組將 ai_quant_trade-0.0.1 中的雙移動平均線策略適配到當前系統。
遵循零修改原則，保持原始策略代碼完全不變。

主要功能：
- 適配 double_ma_timing 函數
- 提供標準 Strategy 接口
- 處理數據格式轉換
- 統一錯誤處理和日誌記錄

策略原理：
- 當短期移動平均線向上穿越長期移動平均線時產生買入訊號
- 當短期移動平均線向下穿越長期移動平均線時產生賣出訊號

Example:
    >>> adapter = DoubleMaAdapter(short_window=5, long_window=20)
    >>> signals = adapter.generate_signals(price_data)
    >>> metrics = adapter.evaluate(price_data, signals)
"""

import logging
import sys
import os
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

# 添加 ai_quant_trade-0.0.1 到路徑
current_dir = os.path.dirname(os.path.abspath(__file__))
legacy_project_path = os.path.join(current_dir, '..', '..', '..', 'ai_quant_trade-0.0.1')
if os.path.exists(legacy_project_path):
    sys.path.insert(0, legacy_project_path)

from .base import LegacyStrategyAdapter, StrategyWrapper, AdapterError
from ...strategy.base import ParameterError

# 設定日誌
logger = logging.getLogger(__name__)


class DoubleMaAdapter(LegacyStrategyAdapter):
    """
    雙移動平均線策略適配器。
    
    將 ai_quant_trade-0.0.1 中的 double_ma_timing 策略適配到當前系統。
    
    策略邏輯：
    1. 計算短期和長期移動平均線
    2. 當短期MA向上穿越長期MA時產生買入訊號
    3. 當短期MA向下穿越長期MA時產生賣出訊號
    
    Attributes:
        short_window (int): 短期移動平均線窗口大小
        long_window (int): 長期移動平均線窗口大小
        
    Example:
        >>> adapter = DoubleMaAdapter(short_window=5, long_window=20)
        >>> signals = adapter.generate_signals(price_data)
        >>> print(f"生成 {len(signals)} 個交易訊號")
    """
    
    def __init__(self, short_window: int = 5, long_window: int = 20, **kwargs) -> None:
        """
        初始化雙移動平均線策略適配器。
        
        Args:
            short_window: 短期移動平均線窗口大小，默認5
            long_window: 長期移動平均線窗口大小，默認20
            **kwargs: 其他策略參數
            
        Raises:
            ParameterError: 當參數不合法時
        """
        # 設定默認參數
        parameters = {
            'short_window': short_window,
            'long_window': long_window,
            **kwargs
        }
        
        super().__init__(name="DoubleMaStrategy", **parameters)
        
        # 提取參數
        self.short_window = self.parameters['short_window']
        self.long_window = self.parameters['long_window']
        
        logger.info(f"雙移動平均線策略適配器初始化完成，短期窗口: {self.short_window}, 長期窗口: {self.long_window}")
    
    def _validate_parameters(self) -> None:
        """
        驗證策略參數。
        
        Raises:
            ParameterError: 當參數不合法時
        """
        super()._validate_parameters()
        
        short_window = self.parameters.get('short_window', 5)
        long_window = self.parameters.get('long_window', 20)
        
        if not isinstance(short_window, int) or short_window <= 0:
            raise ParameterError(f"短期窗口必須為正整數，當前值: {short_window}")
        
        if not isinstance(long_window, int) or long_window <= 0:
            raise ParameterError(f"長期窗口必須為正整數，當前值: {long_window}")
        
        if short_window >= long_window:
            raise ParameterError(f"短期窗口 ({short_window}) 必須小於長期窗口 ({long_window})")
    
    def _load_legacy_strategy(self) -> None:
        """
        載入原始雙移動平均線策略。
        
        從 ai_quant_trade-0.0.1 項目中導入 double_ma_timing 函數。
        """
        try:
            # 嘗試導入原始策略函數
            from quant_brain.rules.timing_ctrl.moving_average import double_ma_timing
            
            # 創建策略包裝器
            self.strategy_wrapper = StrategyWrapper(
                strategy_func=double_ma_timing,
                strategy_name="double_ma_timing"
            )
            
            self.legacy_strategy = double_ma_timing
            logger.info("成功載入原始雙移動平均線策略")
            
        except ImportError as e:
            # 如果無法導入原始策略，使用本地實現
            logger.warning(f"無法導入原始策略，使用本地實現: {e}")
            self._create_local_implementation()
    
    def _create_local_implementation(self) -> None:
        """
        創建本地策略實現。
        
        當無法導入原始策略時，提供本地實現作為備選方案。
        """
        def local_double_ma_timing(ma_short: float, ma_long: float, hold: bool) -> str:
            """
            本地雙移動平均線時機控制實現。
            
            Args:
                ma_short: 短期移動平均值
                ma_long: 長期移動平均值
                hold: 是否持有倉位
                
            Returns:
                交易類型 ('buy', 'sell', 或 '')
            """
            trade_type = ''
            if ma_short >= ma_long and not hold:
                trade_type = 'buy'
            elif ma_short < ma_long and hold:
                trade_type = 'sell'
            return trade_type
        
        self.strategy_wrapper = StrategyWrapper(
            strategy_func=local_double_ma_timing,
            strategy_name="local_double_ma_timing"
        )
        
        self.legacy_strategy = local_double_ma_timing
        logger.info("創建本地雙移動平均線策略實現")
    
    def _convert_parameters(self, **parameters: Any) -> Dict[str, Any]:
        """
        轉換策略參數格式。
        
        原始策略不需要參數轉換，移動平均線計算在適配器中完成。
        
        Args:
            **parameters: 當前系統參數格式
            
        Returns:
            原始策略期望的參數格式
        """
        return {
            'short_window': parameters.get('short_window', self.short_window),
            'long_window': parameters.get('long_window', self.long_window),
        }
    
    def _execute_legacy_strategy(self, data: pd.DataFrame, **parameters: Any) -> pd.DataFrame:
        """
        執行原始策略。
        
        Args:
            data: 輸入數據
            **parameters: 策略參數
            
        Returns:
            包含交易決策的數據框架
        """
        try:
            # 計算移動平均線
            short_window = parameters.get('short_window', self.short_window)
            long_window = parameters.get('long_window', self.long_window)
            
            price_series = data['close'].astype(float)
            short_ma = price_series.rolling(window=short_window).mean()
            long_ma = price_series.rolling(window=long_window).mean()
            
            # 創建結果數據框架
            results = pd.DataFrame(index=data.index)
            results['short_ma'] = short_ma
            results['long_ma'] = long_ma
            results['trade_type'] = ''
            
            # 模擬持倉狀態
            hold = False
            
            # 逐行執行策略決策
            for i in range(len(data)):
                if pd.isna(short_ma.iloc[i]) or pd.isna(long_ma.iloc[i]):
                    continue
                
                # 執行原始策略
                trade_type = self.strategy_wrapper.execute(
                    ma_short=short_ma.iloc[i],
                    ma_long=long_ma.iloc[i],
                    hold=hold
                )
                
                results.iloc[i, results.columns.get_loc('trade_type')] = trade_type
                
                # 更新持倉狀態
                if trade_type == 'buy':
                    hold = True
                elif trade_type == 'sell':
                    hold = False
            
            logger.debug(f"策略執行完成，處理 {len(data)} 筆數據")
            return results
            
        except Exception as e:
            logger.error(f"執行原始策略失敗: {e}")
            raise AdapterError(f"執行原始策略失敗: {e}") from e
    
    def _convert_results(self, legacy_results: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
        """
        轉換策略結果格式。
        
        將原始策略結果轉換為當前系統期望的格式。
        
        Args:
            legacy_results: 原始策略結果
            data: 輸入數據
            
        Returns:
            當前系統期望的結果格式
        """
        try:
            # 創建標準訊號格式
            signals = pd.DataFrame(index=data.index)
            
            # 初始化訊號欄位
            signals['signal'] = 0.0
            signals['buy_signal'] = 0
            signals['sell_signal'] = 0
            
            # 轉換交易類型為標準訊號
            for i in range(len(legacy_results)):
                trade_type = legacy_results.iloc[i]['trade_type']
                
                if trade_type == 'buy':
                    signals.iloc[i, signals.columns.get_loc('signal')] = 1.0
                    signals.iloc[i, signals.columns.get_loc('buy_signal')] = 1
                elif trade_type == 'sell':
                    signals.iloc[i, signals.columns.get_loc('signal')] = -1.0
                    signals.iloc[i, signals.columns.get_loc('sell_signal')] = 1
            
            # 添加移動平均線數據供分析使用
            if 'short_ma' in legacy_results.columns:
                signals['short_ma'] = legacy_results['short_ma']
            if 'long_ma' in legacy_results.columns:
                signals['long_ma'] = legacy_results['long_ma']
            
            logger.debug(f"結果轉換完成，生成 {len(signals)} 個訊號")
            return signals
            
        except Exception as e:
            logger.error(f"結果轉換失敗: {e}")
            raise AdapterError(f"結果轉換失敗: {e}") from e
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        獲取策略資訊。
        
        Returns:
            策略詳細資訊
        """
        info = {
            'name': self.name,
            'type': 'Technical Analysis',
            'category': 'Moving Average',
            'parameters': {
                'short_window': self.short_window,
                'long_window': self.long_window,
            },
            'description': '雙移動平均線交叉策略，當短期MA向上穿越長期MA時買入，向下穿越時賣出',
            'source': 'ai_quant_trade-0.0.1',
            'adapter_version': '1.0.0',
        }
        
        if self.strategy_wrapper:
            info['execution_stats'] = {
                'execution_count': self.strategy_wrapper.execution_count,
                'error_count': self.strategy_wrapper.error_count,
                'success_rate': self.strategy_wrapper.success_rate,
            }
        
        return info
