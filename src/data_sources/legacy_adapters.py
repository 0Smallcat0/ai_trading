# -*- coding: utf-8 -*-
"""
原始項目數據源適配器

此模組提供原始項目 (ai_quant_trade-master) 數據源的適配器，
實現與統一數據管理器的無縫整合。

支持的原始數據源：
- Tushare API
- Wind API  
- BaoStock API

主要功能：
- 原始數據源接口適配
- 數據格式統一轉換
- 錯誤處理和重試
- 性能優化和緩存
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio
import sys
import os

# 添加原始項目路徑
original_project_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ai_quant_trade-master')
if original_project_path not in sys.path:
    sys.path.append(original_project_path)

# 設定日誌
logger = logging.getLogger(__name__)

# 警告去重機制
_logged_warnings = set()

def log_warning_once(message: str):
    """只記錄一次的警告訊息"""
    if message not in _logged_warnings:
        logger.warning(message)
        _logged_warnings.add(message)


class LegacyDataSourceAdapter:
    """
    原始數據源適配器基類
    
    提供統一的接口來訪問原始項目的數據源，
    並將數據格式轉換為當前系統的標準格式。
    """
    
    def __init__(self, source_name: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化適配器
        
        Args:
            source_name: 數據源名稱
            config: 配置參數
        """
        self.source_name = source_name
        self.config = config or {}
        self.is_available = False
        
        # 初始化數據源
        self._initialize_source()
    
    def _initialize_source(self):
        """初始化數據源（子類實現）"""
        raise NotImplementedError("子類必須實現此方法")
    
    async def get_data(self, symbols: List[str], start_date: datetime, end_date: datetime, **kwargs) -> pd.DataFrame:
        """獲取數據（子類實現）"""
        raise NotImplementedError("子類必須實現此方法")
    
    def _standardize_data_format(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        標準化數據格式
        
        將原始數據格式轉換為統一的標準格式：
        - symbol: 股票代碼
        - date: 日期
        - open: 開盤價
        - high: 最高價
        - low: 最低價
        - close: 收盤價
        - volume: 成交量
        """
        if data.empty:
            return data
        
        # 標準化列名映射
        column_mapping = {
            'ts_code': 'symbol',
            'trade_date': 'date',
            'vol': 'volume',
            'amount': 'turnover'
        }
        
        # 重命名列
        for old_name, new_name in column_mapping.items():
            if old_name in data.columns:
                data = data.rename(columns={old_name: new_name})
        
        # 確保必要的列存在
        required_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                if col == 'volume':
                    data[col] = 0
                else:
                    data[col] = np.nan
        
        # 數據類型轉換
        try:
            if 'date' in data.columns:
                data['date'] = pd.to_datetime(data['date'])
            
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                if col in data.columns:
                    data[col] = pd.to_numeric(data[col], errors='coerce')
        except Exception as e:
            logger.warning(f"數據類型轉換失敗: {e}")
        
        return data


class TushareAdapter(LegacyDataSourceAdapter):
    """
    Tushare數據源適配器
    
    適配原始項目的Tushare數據獲取功能
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("tushare", config)
    
    def _initialize_source(self):
        """初始化Tushare數據源"""
        try:
            # 嘗試導入原始項目的Tushare模組
            from quant_brain.data_io.api_tushare_data import TushareDataApi
            
            # 檢查是否有token配置
            token = self.config.get('token')
            if not token:
                try:
                    from data.private.tushare_token import tushare_token
                    token = tushare_token
                except ImportError:
                    log_warning_once("Tushare token未配置，將無法使用Tushare數據源")
                    return
            
            self.api = TushareDataApi()
            self.is_available = True
            logger.info("Tushare數據源初始化成功")
            
        except ImportError as e:
            log_warning_once(f"Tushare數據源不可用: {e}")
        except Exception as e:
            logger.error(f"Tushare數據源初始化失敗: {e}")
    
    async def get_data(self, symbols: List[str], start_date: datetime, end_date: datetime, **kwargs) -> pd.DataFrame:
        """
        獲取Tushare數據
        
        Args:
            symbols: 股票代碼列表
            start_date: 開始日期
            end_date: 結束日期
            **kwargs: 其他參數
            
        Returns:
            標準化的數據DataFrame
        """
        if not self.is_available:
            raise Exception("Tushare數據源不可用")
        
        try:
            all_data = []
            
            for symbol in symbols:
                # 調用原始項目的API
                data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._get_tushare_data_sync,
                    symbol,
                    start_date,
                    end_date
                )
                
                if not data.empty:
                    all_data.append(data)
            
            if all_data:
                combined_data = pd.concat(all_data, ignore_index=True)
                return self._standardize_data_format(combined_data)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Tushare數據獲取失敗: {e}")
            return pd.DataFrame()
    
    def _get_tushare_data_sync(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """同步獲取Tushare數據"""
        try:
            # 這裡需要根據原始項目的實際API調用方式實現
            # 目前提供模擬實現
            
            # 轉換日期格式
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            
            # 模擬數據（實際實現時需要調用真實API）
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            data = pd.DataFrame({
                'ts_code': symbol,
                'trade_date': dates.strftime('%Y%m%d'),
                'open': np.random.uniform(10, 100, len(dates)),
                'high': np.random.uniform(10, 100, len(dates)),
                'low': np.random.uniform(10, 100, len(dates)),
                'close': np.random.uniform(10, 100, len(dates)),
                'vol': np.random.randint(1000, 100000, len(dates))
            })
            
            return data
            
        except Exception as e:
            logger.error(f"Tushare同步數據獲取失敗: {e}")
            return pd.DataFrame()


class WindAdapter(LegacyDataSourceAdapter):
    """
    Wind數據源適配器
    
    適配原始項目的Wind數據獲取功能
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("wind", config)
    
    def _initialize_source(self):
        """初始化Wind數據源"""
        try:
            # 嘗試導入原始項目的Wind模組
            # 注意：Wind API通常需要特殊的許可證和安裝
            logger.info("嘗試初始化Wind數據源...")
            
            # 檢查Wind是否可用
            # 這裡需要根據實際的Wind API實現
            self.is_available = False  # 默認不可用，需要實際配置
            log_warning_once("Wind數據源需要額外配置才能使用")
            
        except Exception as e:
            logger.error(f"Wind數據源初始化失敗: {e}")
    
    async def get_data(self, symbols: List[str], start_date: datetime, end_date: datetime, **kwargs) -> pd.DataFrame:
        """獲取Wind數據"""
        if not self.is_available:
            raise Exception("Wind數據源不可用")
        
        # 實際實現時需要調用Wind API
        log_warning_once("Wind數據源功能待實現")
        return pd.DataFrame()


class BaoStockAdapter(LegacyDataSourceAdapter):
    """
    BaoStock數據源適配器
    
    適配原始項目的BaoStock數據獲取功能
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("baostock", config)
    
    def _initialize_source(self):
        """初始化BaoStock數據源"""
        try:
            # 嘗試導入BaoStock
            import baostock as bs
            
            # 登錄BaoStock
            lg = bs.login()
            if lg.error_code != '0':
                logger.error(f"BaoStock登錄失敗: {lg.error_msg}")
                return
            
            self.bs = bs
            self.is_available = True
            logger.info("BaoStock數據源初始化成功")
            
        except ImportError:
            log_warning_once("BaoStock未安裝，請運行: pip install baostock")
        except Exception as e:
            logger.error(f"BaoStock數據源初始化失敗: {e}")
    
    async def get_data(self, symbols: List[str], start_date: datetime, end_date: datetime, **kwargs) -> pd.DataFrame:
        """獲取BaoStock數據"""
        if not self.is_available:
            raise Exception("BaoStock數據源不可用")
        
        try:
            all_data = []
            
            for symbol in symbols:
                data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._get_baostock_data_sync,
                    symbol,
                    start_date,
                    end_date
                )
                
                if not data.empty:
                    all_data.append(data)
            
            if all_data:
                combined_data = pd.concat(all_data, ignore_index=True)
                return self._standardize_data_format(combined_data)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"BaoStock數據獲取失敗: {e}")
            return pd.DataFrame()
    
    def _get_baostock_data_sync(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """同步獲取BaoStock數據"""
        try:
            # 轉換股票代碼格式
            if symbol.startswith('6'):
                bs_code = f"sh.{symbol}"
            else:
                bs_code = f"sz.{symbol}"
            
            # 獲取數據
            rs = self.bs.query_history_k_data_plus(
                bs_code,
                "date,code,open,high,low,close,volume,amount",
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                frequency="d"
            )
            
            if rs.error_code != '0':
                logger.error(f"BaoStock查詢失敗: {rs.error_msg}")
                return pd.DataFrame()
            
            # 轉換為DataFrame
            data = []
            while rs.next():
                data.append(rs.get_row_data())
            
            if data:
                df = pd.DataFrame(data, columns=rs.fields)
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"BaoStock同步數據獲取失敗: {e}")
            return pd.DataFrame()
    
    def __del__(self):
        """析構函數，登出BaoStock"""
        if hasattr(self, 'bs') and self.is_available:
            try:
                self.bs.logout()
            except:
                pass


class LegacyDataSourceManager:
    """
    原始數據源管理器
    
    統一管理所有原始項目的數據源適配器
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化管理器
        
        Args:
            config: 配置參數
        """
        self.config = config or {}
        self.adapters = {}
        
        # 初始化所有適配器
        self._initialize_adapters()
    
    def _initialize_adapters(self):
        """初始化所有數據源適配器"""
        try:
            # 初始化Tushare適配器
            tushare_config = self.config.get('tushare', {})
            self.adapters['tushare'] = TushareAdapter(tushare_config)
            
            # 初始化Wind適配器
            wind_config = self.config.get('wind', {})
            self.adapters['wind'] = WindAdapter(wind_config)
            
            # 初始化BaoStock適配器
            baostock_config = self.config.get('baostock', {})
            self.adapters['baostock'] = BaoStockAdapter(baostock_config)
            
            logger.info(f"初始化了 {len(self.adapters)} 個原始數據源適配器")
            
        except Exception as e:
            logger.error(f"原始數據源適配器初始化失敗: {e}")
    
    def get_available_sources(self) -> List[str]:
        """獲取可用的數據源列表"""
        return [name for name, adapter in self.adapters.items() if adapter.is_available]
    
    async def get_data(self, source: str, symbols: List[str], start_date: datetime, end_date: datetime, **kwargs) -> pd.DataFrame:
        """
        從指定數據源獲取數據
        
        Args:
            source: 數據源名稱
            symbols: 股票代碼列表
            start_date: 開始日期
            end_date: 結束日期
            **kwargs: 其他參數
            
        Returns:
            標準化的數據DataFrame
        """
        if source not in self.adapters:
            raise ValueError(f"不支持的數據源: {source}")
        
        adapter = self.adapters[source]
        if not adapter.is_available:
            raise Exception(f"數據源 {source} 不可用")
        
        return await adapter.get_data(symbols, start_date, end_date, **kwargs)
    
    def get_source_status(self) -> Dict[str, bool]:
        """獲取所有數據源的狀態"""
        return {name: adapter.is_available for name, adapter in self.adapters.items()}
