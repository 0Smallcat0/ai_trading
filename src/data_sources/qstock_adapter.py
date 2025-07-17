# -*- coding: utf-8 -*-
"""
qstock數據源適配器

此模組整合qstock數據獲取工具到現有的數據源架構中，
提供統一的數據接口和格式標準化。

主要功能：
- qstock API封裝和適配
- 數據格式標準化
- 錯誤處理和重試機制
- 數據質量檢查
- 緩存和性能優化

支援的數據類型：
- 實時行情數據
- 歷史K線數據
- 財務報表數據
- 資金流向數據
- 宏觀經濟數據
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import time
import warnings
from functools import wraps

from .base_data_source import BaseDataSource, DataSourceConfig
from ..utils.data_validator import DataValidator
from ..utils.cache_manager import CacheManager

# 設定日誌
logger = logging.getLogger(__name__)

# 抑制qstock的警告
warnings.filterwarnings('ignore')


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """重試裝飾器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"函數 {func.__name__} 重試 {max_retries} 次後仍然失敗: {e}")
                        raise
                    else:
                        logger.warning(f"函數 {func.__name__} 第 {attempt + 1} 次嘗試失敗: {e}，{delay}秒後重試")
                        time.sleep(delay)
            return None
        return wrapper
    return decorator


class QStockAdapter(BaseDataSource):
    """
    qstock數據源適配器
    
    整合qstock數據獲取功能到統一的數據源接口
    """
    
    def __init__(self, config: DataSourceConfig):
        """
        初始化qstock適配器
        
        Args:
            config: 數據源配置
        """
        super().__init__(config)
        
        self.source_name = "qstock"
        self.description = "qstock金融數據源"
        
        # 嘗試導入qstock
        self.qstock_available = self._import_qstock()
        
        # 數據驗證器
        self.validator = DataValidator()
        
        # 緩存管理器
        self.cache_manager = CacheManager(
            cache_dir=config.cache_dir,
            cache_ttl=config.cache_ttl
        )
        
        # 支援的市場和數據類型
        self.supported_markets = [
            '沪深A', '沪A', '深A', '北A', '创业板', '科创板',
            '美股', '港股', '期货', 'ETF', 'LOF', '可转债'
        ]
        
        self.supported_data_types = [
            'realtime', 'historical', 'intraday', 'financial',
            'money_flow', 'macro', 'news', 'index_member'
        ]
        
        logger.info(f"qstock適配器初始化完成，可用性: {self.qstock_available}")
    
    def _import_qstock(self) -> bool:
        """導入qstock模組"""
        try:
            import qstock as qs
            self.qs = qs
            logger.info("qstock模組導入成功")
            return True
        except ImportError as e:
            logger.warning(f"qstock模組導入失敗: {e}")
            logger.info("請使用 'pip install qstock' 安裝qstock")
            self.qs = None
            return False
    
    def is_available(self) -> bool:
        """檢查數據源是否可用"""
        return self.qstock_available
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def get_realtime_data(self, symbols: Union[str, List[str]], market: str = '沪深A') -> pd.DataFrame:
        """
        獲取實時行情數據
        
        Args:
            symbols: 股票代碼或代碼列表
            market: 市場類型
            
        Returns:
            實時行情數據
        """
        if not self.qstock_available:
            raise RuntimeError("qstock不可用")
        
        try:
            # 檢查緩存
            cache_key = f"realtime_{market}_{symbols}"
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # 獲取數據
            if isinstance(symbols, str):
                if symbols == 'all':
                    # 獲取整個市場數據
                    data = self.qs.realtime_data(market=market)
                else:
                    # 獲取單個股票數據
                    data = self.qs.realtime_data(code=symbols)
            else:
                # 獲取多個股票數據
                data = self.qs.realtime_data(code=symbols)
            
            if data is None or data.empty:
                logger.warning(f"未獲取到實時數據: {symbols}")
                return pd.DataFrame()
            
            # 數據標準化
            standardized_data = self._standardize_realtime_data(data)
            
            # 數據驗證
            if self.validator.validate_realtime_data(standardized_data):
                # 緩存數據（實時數據緩存時間較短）
                self.cache_manager.set(cache_key, standardized_data, ttl=60)  # 1分鐘緩存
                return standardized_data
            else:
                logger.warning("實時數據驗證失敗")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"獲取實時數據失敗: {e}")
            raise
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def get_historical_data(
        self, 
        symbols: Union[str, List[str]], 
        start_date: str = '20200101',
        end_date: Optional[str] = None,
        frequency: str = 'd',
        adjust: str = 'qfq'
    ) -> pd.DataFrame:
        """
        獲取歷史K線數據
        
        Args:
            symbols: 股票代碼或代碼列表
            start_date: 開始日期
            end_date: 結束日期
            frequency: 數據頻率 ('d', '5', '15', '30', '60')
            adjust: 復權類型 ('qfq', 'hfq', 'none')
            
        Returns:
            歷史K線數據
        """
        if not self.qstock_available:
            raise RuntimeError("qstock不可用")
        
        try:
            # 檢查緩存
            cache_key = f"historical_{symbols}_{start_date}_{end_date}_{frequency}_{adjust}"
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # 轉換復權類型
            fqt_map = {'none': 0, 'qfq': 1, 'hfq': 2}
            fqt = fqt_map.get(adjust, 1)
            
            # 轉換頻率
            freq_map = {'d': 101, '5': 5, '15': 15, '30': 30, '60': 60}
            freq = freq_map.get(frequency, 101)
            
            # 獲取數據
            if isinstance(symbols, str):
                data = self.qs.get_data(
                    code_list=symbols,
                    start=start_date,
                    end=end_date,
                    freq=freq,
                    fqt=fqt
                )
            else:
                data = self.qs.get_data(
                    code_list=symbols,
                    start=start_date,
                    end=end_date,
                    freq=freq,
                    fqt=fqt
                )
            
            if data is None or data.empty:
                logger.warning(f"未獲取到歷史數據: {symbols}")
                return pd.DataFrame()
            
            # 數據標準化
            standardized_data = self._standardize_historical_data(data)
            
            # 數據驗證
            if self.validator.validate_historical_data(standardized_data):
                # 緩存數據
                self.cache_manager.set(cache_key, standardized_data)
                return standardized_data
            else:
                logger.warning("歷史數據驗證失敗")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"獲取歷史數據失敗: {e}")
            raise
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def get_financial_data(self, symbols: Union[str, List[str]], report_type: str = '业绩报表') -> pd.DataFrame:
        """
        獲取財務數據
        
        Args:
            symbols: 股票代碼或代碼列表
            report_type: 報表類型
            
        Returns:
            財務數據
        """
        if not self.qstock_available:
            raise RuntimeError("qstock不可用")
        
        try:
            # 檢查緩存
            cache_key = f"financial_{symbols}_{report_type}"
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # 獲取財務數據
            if isinstance(symbols, str):
                # 獲取基本財務指標
                data = self.qs.stock_basics(symbols)
            else:
                data = self.qs.stock_basics(symbols)
            
            if data is None or data.empty:
                logger.warning(f"未獲取到財務數據: {symbols}")
                return pd.DataFrame()
            
            # 數據標準化
            standardized_data = self._standardize_financial_data(data)
            
            # 緩存數據
            self.cache_manager.set(cache_key, standardized_data)
            return standardized_data
            
        except Exception as e:
            logger.error(f"獲取財務數據失敗: {e}")
            raise
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def get_money_flow_data(self, symbols: Union[str, List[str]], days: List[int] = [5, 10, 20]) -> pd.DataFrame:
        """
        獲取資金流向數據
        
        Args:
            symbols: 股票代碼或代碼列表
            days: 統計天數
            
        Returns:
            資金流向數據
        """
        if not self.qstock_available:
            raise RuntimeError("qstock不可用")
        
        try:
            # 檢查緩存
            cache_key = f"money_flow_{symbols}_{days}"
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # 獲取資金流向數據
            if isinstance(symbols, str):
                data = self.qs.stock_money(symbols, ndays=days)
            else:
                # 對於多個股票，需要逐個獲取
                all_data = []
                for symbol in symbols:
                    try:
                        symbol_data = self.qs.stock_money(symbol, ndays=days)
                        if symbol_data is not None and not symbol_data.empty:
                            symbol_data['symbol'] = symbol
                            all_data.append(symbol_data)
                    except Exception as e:
                        logger.warning(f"獲取 {symbol} 資金流向數據失敗: {e}")
                
                if all_data:
                    data = pd.concat(all_data, ignore_index=True)
                else:
                    data = pd.DataFrame()
            
            if data is None or data.empty:
                logger.warning(f"未獲取到資金流向數據: {symbols}")
                return pd.DataFrame()
            
            # 數據標準化
            standardized_data = self._standardize_money_flow_data(data)
            
            # 緩存數據
            self.cache_manager.set(cache_key, standardized_data)
            return standardized_data
            
        except Exception as e:
            logger.error(f"獲取資金流向數據失敗: {e}")
            raise
    
    def _standardize_realtime_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """標準化實時數據格式"""
        try:
            # 重命名列名為標準格式
            column_mapping = {
                '代码': 'symbol',
                '名称': 'name',
                '最新': 'price',
                '涨跌': 'change',
                '涨幅': 'change_pct',
                '成交量': 'volume',
                '成交额': 'amount',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '昨收': 'prev_close',
                '换手率': 'turnover_rate',
                '市盈率': 'pe_ratio',
                '市净率': 'pb_ratio'
            }
            
            # 重命名存在的列
            existing_columns = {k: v for k, v in column_mapping.items() if k in data.columns}
            standardized_data = data.rename(columns=existing_columns)
            
            # 添加時間戳
            standardized_data['timestamp'] = datetime.now()
            standardized_data['source'] = 'qstock'
            
            # 數據類型轉換
            numeric_columns = ['price', 'change', 'change_pct', 'volume', 'amount', 
                             'open', 'high', 'low', 'prev_close', 'turnover_rate', 
                             'pe_ratio', 'pb_ratio']
            
            for col in numeric_columns:
                if col in standardized_data.columns:
                    standardized_data[col] = pd.to_numeric(standardized_data[col], errors='coerce')
            
            return standardized_data
            
        except Exception as e:
            logger.error(f"實時數據標準化失敗: {e}")
            return data
    
    def _standardize_historical_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """標準化歷史數據格式"""
        try:
            # qstock歷史數據通常已經是標準格式
            standardized_data = data.copy()
            
            # 確保列名為英文
            column_mapping = {
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'vol': 'volume',
                'turnover': 'amount',
                'turnover_rate': 'turnover_rate'
            }
            
            # 重命名存在的列
            existing_columns = {k: v for k, v in column_mapping.items() if k in data.columns}
            standardized_data = standardized_data.rename(columns=existing_columns)
            
            # 確保索引為日期格式
            if not isinstance(standardized_data.index, pd.DatetimeIndex):
                standardized_data.index = pd.to_datetime(standardized_data.index)
            
            # 添加元數據
            standardized_data['source'] = 'qstock'
            
            # 數據類型轉換
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount', 'turnover_rate']
            for col in numeric_columns:
                if col in standardized_data.columns:
                    standardized_data[col] = pd.to_numeric(standardized_data[col], errors='coerce')
            
            return standardized_data
            
        except Exception as e:
            logger.error(f"歷史數據標準化失敗: {e}")
            return data
    
    def _standardize_financial_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """標準化財務數據格式"""
        try:
            # 重命名列名為標準格式
            column_mapping = {
                '代码': 'symbol',
                '名称': 'name',
                '净利润': 'net_profit',
                '总市值': 'market_cap',
                '流通市值': 'float_market_cap',
                '所处行业': 'industry',
                '市盈率': 'pe_ratio',
                '市净率': 'pb_ratio',
                'ROE': 'roe',
                '毛利率': 'gross_margin',
                '净利率': 'net_margin'
            }
            
            # 重命名存在的列
            existing_columns = {k: v for k, v in column_mapping.items() if k in data.columns}
            standardized_data = data.rename(columns=existing_columns)
            
            # 添加時間戳
            standardized_data['update_time'] = datetime.now()
            standardized_data['source'] = 'qstock'
            
            # 數據類型轉換
            numeric_columns = ['net_profit', 'market_cap', 'float_market_cap', 
                             'pe_ratio', 'pb_ratio', 'roe', 'gross_margin', 'net_margin']
            
            for col in numeric_columns:
                if col in standardized_data.columns:
                    standardized_data[col] = pd.to_numeric(standardized_data[col], errors='coerce')
            
            return standardized_data
            
        except Exception as e:
            logger.error(f"財務數據標準化失敗: {e}")
            return data
    
    def _standardize_money_flow_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """標準化資金流向數據格式"""
        try:
            # 添加時間戳和來源
            standardized_data = data.copy()
            standardized_data['update_time'] = datetime.now()
            standardized_data['source'] = 'qstock'
            
            return standardized_data
            
        except Exception as e:
            logger.error(f"資金流向數據標準化失敗: {e}")
            return data
    
    def get_supported_symbols(self, market: str = '沪深A') -> List[str]:
        """獲取支援的股票代碼列表"""
        if not self.qstock_available:
            return []
        
        try:
            # 獲取市場所有股票
            data = self.get_realtime_data('all', market)
            if not data.empty and 'symbol' in data.columns:
                return data['symbol'].tolist()
            else:
                return []
        except Exception as e:
            logger.error(f"獲取支援股票列表失敗: {e}")
            return []
    
    def get_data_info(self) -> Dict[str, Any]:
        """獲取數據源信息"""
        return {
            'name': self.source_name,
            'description': self.description,
            'available': self.qstock_available,
            'supported_markets': self.supported_markets,
            'supported_data_types': self.supported_data_types,
            'features': [
                '實時行情數據',
                '歷史K線數據',
                '財務報表數據',
                '資金流向數據',
                '宏觀經濟數據',
                '新聞資訊數據'
            ],
            'update_frequency': {
                'realtime': '實時',
                'historical': '日更新',
                'financial': '季度更新',
                'money_flow': '日更新'
            }
        }
