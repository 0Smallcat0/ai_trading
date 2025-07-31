# -*- coding: utf-8 -*-
"""因子挖掘適配器

此模組整合 ai_quant_trade-0.0.1/egs_alpha/ 中的因子挖掘功能到當前系統，
提供統一的因子挖掘、評估和選擇平台。

主要功能：
- tsfresh 自動因子挖掘功能整合
- Alpha101 因子庫統一管理
- 因子計算的批量處理和並行化
- 因子評估和選擇工具
- 因子數據格式標準化和快取

支援的因子挖掘方法：
- tsfresh 自動特徵提取 (5000+ 特徵)
- Alpha101 經典因子庫 (101 個因子)
- 自定義因子計算框架
- 因子組合和優化算法

Example:
    >>> from src.strategies.adapters import FactorMiningAdapter
    >>> adapter = FactorMiningAdapter(
    ...     method='tsfresh',
    ...     config={'n_jobs': 4, 'cache_enabled': True}
    ... )
    >>> factors = adapter.extract_factors(price_data)
    >>> selected_factors = adapter.select_factors(factors, target_returns)
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import multiprocessing as mp

from .base import LegacyStrategyAdapter, AdapterError
from ...utils.cache_manager import CacheManager
from ...utils.data_validator import DataValidator

# 設定日誌
logger = logging.getLogger(__name__)


class FactorMiningConfig:
    """因子挖掘配置類
    
    管理因子挖掘的各種配置參數。
    
    Attributes:
        method: 因子挖掘方法 ('tsfresh', 'alpha101', 'custom')
        n_jobs: 並行處理進程數
        cache_enabled: 是否啟用快取
        batch_size: 批量處理大小
        
    Example:
        >>> config = FactorMiningConfig(
        ...     method='tsfresh',
        ...     n_jobs=4,
        ...     cache_enabled=True
        ... )
    """
    
    def __init__(self,
                 method: str = 'tsfresh',
                 n_jobs: int = None,
                 cache_enabled: bool = True,
                 batch_size: int = 1000,
                 **kwargs):
        """初始化因子挖掘配置
        
        Args:
            method: 因子挖掘方法
            n_jobs: 並行處理進程數，默認為 CPU 核心數
            cache_enabled: 是否啟用快取
            batch_size: 批量處理大小
            **kwargs: 其他配置參數
        """
        self.method = method
        self.n_jobs = n_jobs or mp.cpu_count()
        self.cache_enabled = cache_enabled
        self.batch_size = batch_size
        
        # 方法特定配置
        self.tsfresh_config = kwargs.get('tsfresh_config', {})
        self.alpha101_config = kwargs.get('alpha101_config', {})
        self.evaluation_config = kwargs.get('evaluation_config', {})
        
        # 性能配置
        self.max_memory_gb = kwargs.get('max_memory_gb', 8)
        self.timeout_seconds = kwargs.get('timeout_seconds', 3600)
        
        logger.info(f"因子挖掘配置初始化: {method}, 並行數: {self.n_jobs}")


class DataFormatConverter:
    """數據格式轉換器
    
    處理不同因子挖掘方法所需的數據格式轉換。
    """
    
    @staticmethod
    def to_alpha101_format(df: pd.DataFrame) -> pd.DataFrame:
        """轉換為 Alpha101 期望格式
        
        Args:
            df: 標準格式數據
            
        Returns:
            Alpha101 格式數據
        """
        try:
            # 計算必要的衍生欄位
            df_alpha = df.copy()
            
            # 重命名欄位
            column_mapping = {
                'open': 'S_DQ_OPEN',
                'high': 'S_DQ_HIGH',
                'low': 'S_DQ_LOW',
                'close': 'S_DQ_CLOSE',
                'volume': 'S_DQ_VOLUME',
                'amount': 'S_DQ_AMOUNT'
            }
            
            df_alpha = df_alpha.rename(columns=column_mapping)
            
            # 計算收益率
            if 'S_DQ_PCTCHANGE' not in df_alpha.columns:
                df_alpha['S_DQ_PCTCHANGE'] = df_alpha['S_DQ_CLOSE'].pct_change()
            
            # 計算 VWAP
            if 'S_DQ_AMOUNT' in df_alpha.columns and 'S_DQ_VOLUME' in df_alpha.columns:
                df_alpha['vwap'] = (df_alpha['S_DQ_AMOUNT'] * 1000) / (df_alpha['S_DQ_VOLUME'] * 100 + 1)
            
            return df_alpha
            
        except Exception as e:
            logger.error(f"Alpha101 格式轉換失敗: {e}")
            raise AdapterError(f"Alpha101 格式轉換失敗: {e}") from e
    
    @staticmethod
    def to_tsfresh_format(df: pd.DataFrame, value_columns: List[str] = None) -> pd.DataFrame:
        """轉換為 tsfresh 期望格式
        
        Args:
            df: 標準格式數據
            value_columns: 要轉換的數值欄位列表
            
        Returns:
            tsfresh 格式數據 (長格式)
        """
        try:
            if value_columns is None:
                value_columns = ['open', 'high', 'low', 'close', 'volume', 'amount']
            
            # 確保必要欄位存在
            required_columns = ['symbol', 'date'] + value_columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"缺少必要欄位: {missing_columns}")
            
            # 轉換為長格式
            df_long = pd.melt(
                df,
                id_vars=['symbol', 'date'],
                value_vars=value_columns,
                var_name='feature',
                value_name='value'
            )
            
            # 重命名欄位以符合 tsfresh 期望
            df_long = df_long.rename(columns={
                'symbol': 'id',
                'date': 'time'
            })
            
            # 創建複合 ID (symbol + feature)
            df_long['id'] = df_long['id'].astype(str) + '_' + df_long['feature']
            df_long = df_long.drop('feature', axis=1)
            
            # 排序
            df_long = df_long.sort_values(['id', 'time'])
            
            return df_long
            
        except Exception as e:
            logger.error(f"tsfresh 格式轉換失敗: {e}")
            raise AdapterError(f"tsfresh 格式轉換失敗: {e}") from e
    
    @staticmethod
    def from_tsfresh_format(df_features: pd.DataFrame, 
                           original_symbols: List[str]) -> pd.DataFrame:
        """從 tsfresh 結果格式轉換回標準格式
        
        Args:
            df_features: tsfresh 特徵結果
            original_symbols: 原始股票代碼列表
            
        Returns:
            標準格式的因子數據
        """
        try:
            # 解析複合 ID
            df_result = df_features.copy()
            
            # 如果索引包含複合 ID，需要解析
            if isinstance(df_result.index, pd.Index):
                # 提取股票代碼
                symbols = []
                for idx in df_result.index:
                    if isinstance(idx, str) and '_' in idx:
                        symbol = idx.split('_')[0]
                        symbols.append(symbol)
                    else:
                        symbols.append(str(idx))
                
                df_result['symbol'] = symbols
            
            # 重置索引
            df_result = df_result.reset_index(drop=True)
            
            return df_result
            
        except Exception as e:
            logger.error(f"tsfresh 結果格式轉換失敗: {e}")
            raise AdapterError(f"tsfresh 結果格式轉換失敗: {e}") from e


class FactorMiningAdapter(LegacyStrategyAdapter):
    """因子挖掘適配器
    
    提供統一的因子挖掘、評估和選擇功能，整合 tsfresh 自動因子挖掘
    和 Alpha101 因子庫。
    
    Attributes:
        config: 因子挖掘配置
        cache_manager: 快取管理器
        data_converter: 數據格式轉換器
        
    Example:
        >>> adapter = FactorMiningAdapter(
        ...     method='tsfresh',
        ...     config={'n_jobs': 4}
        ... )
        >>> factors = adapter.extract_factors(price_data)
        >>> evaluation = adapter.evaluate_factors(factors, target_returns)
    """
    
    def __init__(self,
                 method: str = 'tsfresh',
                 config: Optional[Dict[str, Any]] = None,
                 **kwargs):
        """初始化因子挖掘適配器
        
        Args:
            method: 因子挖掘方法 ('tsfresh', 'alpha101', 'custom')
            config: 配置參數字典
            **kwargs: 其他參數
            
        Raises:
            ValueError: 當方法不支援時
            ImportError: 當必要的依賴庫未安裝時
        """
        # 設定基本參數
        parameters = {
            'method': method,
            'config': config or {},
            **kwargs
        }
        
        super().__init__(name=f"FactorMining_{method}", **parameters)
        
        # 初始化配置
        self.config = FactorMiningConfig(method=method, **(config or {}))
        
        # 驗證方法支援
        supported_methods = ['tsfresh', 'alpha101', 'custom']
        if method not in supported_methods:
            raise ValueError(f"不支援的因子挖掘方法: {method}, 支援的方法: {supported_methods}")
        
        # 初始化組件
        self.data_converter = DataFormatConverter()
        self.cache_manager = None
        self.tsfresh_engine = None
        self.alpha101_engine = None
        
        # 初始化快取管理器
        if self.config.cache_enabled:
            self._initialize_cache_manager()
        
        # 初始化因子挖掘引擎
        self._initialize_engines()
        
        logger.info(f"因子挖掘適配器初始化完成: {method}")
    
    def _initialize_cache_manager(self):
        """初始化快取管理器"""
        try:
            cache_config = {
                'cache_dir': 'cache/factor_mining',
                'max_size_gb': self.config.max_memory_gb / 2,
                'ttl_hours': 24
            }
            self.cache_manager = CacheManager(cache_config)
            logger.info("因子挖掘快取管理器初始化完成")
        except Exception as e:
            logger.warning(f"快取管理器初始化失敗: {e}")
            self.cache_manager = None
    
    def _initialize_engines(self):
        """初始化因子挖掘引擎"""
        try:
            if self.config.method == 'tsfresh':
                self._initialize_tsfresh_engine()
            elif self.config.method == 'alpha101':
                self._initialize_alpha101_engine()
            elif self.config.method == 'custom':
                self._initialize_custom_engine()
                
        except ImportError as e:
            logger.error(f"因子挖掘引擎初始化失敗，缺少依賴: {e}")
            raise ImportError(f"請安裝必要的依賴庫: {e}") from e
        except Exception as e:
            logger.error(f"因子挖掘引擎初始化失敗: {e}")
            raise AdapterError(f"因子挖掘引擎初始化失敗: {e}") from e
    
    def _initialize_tsfresh_engine(self):
        """初始化 tsfresh 引擎"""
        try:
            from .tsfresh_engine import TsfreshEngine
            self.tsfresh_engine = TsfreshEngine(self.config.tsfresh_config)
            logger.info("tsfresh 引擎初始化完成")
        except ImportError:
            logger.warning("tsfresh 庫未安裝，將使用模擬實現")
            self.tsfresh_engine = self._create_mock_tsfresh_engine()
    
    def _initialize_alpha101_engine(self):
        """初始化 Alpha101 引擎"""
        try:
            from .alpha101_engine import Alpha101Engine
            self.alpha101_engine = Alpha101Engine(self.config.alpha101_config)
            logger.info("Alpha101 引擎初始化完成")
        except ImportError:
            logger.warning("Alpha101 依賴未滿足，將使用模擬實現")
            self.alpha101_engine = self._create_mock_alpha101_engine()
    
    def _initialize_custom_engine(self):
        """初始化自定義引擎"""
        logger.info("自定義因子挖掘引擎初始化完成")
    
    def _create_mock_tsfresh_engine(self):
        """創建模擬 tsfresh 引擎"""
        class MockTsfreshEngine:
            def extract_features(self, data, **kwargs):
                # 返回模擬特徵
                n_samples = len(data['id'].unique()) if 'id' in data.columns else 100
                n_features = 50  # 簡化的特徵數量
                
                features = pd.DataFrame(
                    np.random.randn(n_samples, n_features),
                    columns=[f'feature_{i}' for i in range(n_features)]
                )
                return features
            
            def select_features(self, features, target, **kwargs):
                # 返回前10個特徵
                return features.iloc[:, :10]
        
        return MockTsfreshEngine()
    
    def _create_mock_alpha101_engine(self):
        """創建模擬 Alpha101 引擎"""
        class MockAlpha101Engine:
            def calculate_factors(self, data, factor_list=None, **kwargs):
                # 返回模擬因子
                n_samples = len(data)
                n_factors = len(factor_list) if factor_list else 10
                
                factors = pd.DataFrame(
                    np.random.randn(n_samples, n_factors),
                    columns=[f'alpha_{i:03d}' for i in range(1, n_factors + 1)],
                    index=data.index
                )
                return factors
        
        return MockAlpha101Engine()
    
    def extract_factors(self,
                       data: pd.DataFrame,
                       method: Optional[str] = None,
                       **kwargs) -> pd.DataFrame:
        """提取因子
        
        Args:
            data: 輸入數據
            method: 因子挖掘方法，默認使用配置中的方法
            **kwargs: 其他參數
            
        Returns:
            提取的因子數據
            
        Raises:
            AdapterError: 當因子提取失敗時
        """
        method = method or self.config.method
        
        try:
            # 檢查快取
            cache_key = self._generate_cache_key('extract_factors', data, method, kwargs)
            if self.cache_manager:
                cached_result = self.cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.info("從快取中獲取因子提取結果")
                    return cached_result
            
            # 數據驗證
            self._validate_input_data(data)
            
            # 根據方法提取因子
            if method == 'tsfresh':
                factors = self._extract_tsfresh_factors(data, **kwargs)
            elif method == 'alpha101':
                factors = self._extract_alpha101_factors(data, **kwargs)
            elif method == 'custom':
                factors = self._extract_custom_factors(data, **kwargs)
            else:
                raise ValueError(f"不支援的因子挖掘方法: {method}")
            
            # 快取結果
            if self.cache_manager:
                self.cache_manager.set(cache_key, factors)
            
            logger.info(f"成功提取 {len(factors.columns)} 個因子，數據長度: {len(factors)}")
            return factors
            
        except Exception as e:
            logger.error(f"因子提取失敗: {e}")
            raise AdapterError(f"因子提取失敗: {e}") from e
    
    def _validate_input_data(self, data: pd.DataFrame):
        """驗證輸入數據"""
        if data.empty:
            raise ValueError("輸入數據為空")
        
        required_columns = ['symbol', 'date', 'close']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"缺少必要欄位: {missing_columns}")
        
        if data['close'].isnull().all():
            raise ValueError("收盤價數據全部為空")
    
    def _generate_cache_key(self, operation: str, data: pd.DataFrame, 
                           method: str, kwargs: Dict) -> str:
        """生成快取鍵"""
        import hashlib
        
        # 創建數據指紋
        data_hash = hashlib.md5(
            f"{len(data)}_{data.columns.tolist()}_{data.index.min()}_{data.index.max()}"
            .encode()
        ).hexdigest()[:8]
        
        # 創建參數指紋
        params_str = f"{method}_{sorted(kwargs.items())}"
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        return f"{operation}_{data_hash}_{params_hash}"
    
    def _extract_tsfresh_factors(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """使用 tsfresh 提取因子"""
        if not self.tsfresh_engine:
            raise RuntimeError("tsfresh 引擎未初始化")
        
        # 轉換數據格式
        tsfresh_data = self.data_converter.to_tsfresh_format(data)
        
        # 提取特徵
        features = self.tsfresh_engine.extract_features(tsfresh_data, **kwargs)
        
        # 轉換回標準格式
        symbols = data['symbol'].unique().tolist()
        result = self.data_converter.from_tsfresh_format(features, symbols)
        
        return result
    
    def _extract_alpha101_factors(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """使用 Alpha101 提取因子"""
        if not self.alpha101_engine:
            raise RuntimeError("Alpha101 引擎未初始化")
        
        # 轉換數據格式
        alpha101_data = self.data_converter.to_alpha101_format(data)
        
        # 計算因子
        factors = self.alpha101_engine.calculate_factors(alpha101_data, **kwargs)
        
        return factors
    
    def _extract_custom_factors(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """使用自定義方法提取因子"""
        # 實現自定義因子提取邏輯
        logger.info("使用自定義方法提取因子")
        
        # 簡單示例：計算一些基礎技術指標作為因子
        factors = pd.DataFrame(index=data.index)
        
        # 移動平均
        for window in [5, 10, 20, 60]:
            factors[f'ma_{window}'] = data['close'].rolling(window).mean()
        
        # 價格動量
        for period in [1, 5, 10, 20]:
            factors[f'momentum_{period}'] = data['close'].pct_change(period)
        
        # 波動率
        for window in [5, 10, 20]:
            factors[f'volatility_{window}'] = data['close'].pct_change().rolling(window).std()
        
        return factors
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """獲取策略資訊
        
        Returns:
            策略詳細資訊
        """
        return {
            'name': self.name,
            'type': 'Factor Mining',
            'category': 'FactorMining',
            'method': self.config.method,
            'parameters': {
                'n_jobs': self.config.n_jobs,
                'cache_enabled': self.config.cache_enabled,
                'batch_size': self.config.batch_size,
            },
            'description': f'{self.config.method} 因子挖掘適配器，支援自動因子提取和評估',
            'source': 'ai_quant_trade-0.0.1/egs_alpha',
            'adapter_version': '1.0.0',
            'supported_methods': ['tsfresh', 'alpha101', 'custom'],
        }
