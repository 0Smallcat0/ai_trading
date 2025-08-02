# -*- coding: utf-8 -*-
"""BaoStock 數據源適配器

此模組整合 BaoStock 免費數據源到現有的數據源架構中，
提供統一的數據接口和格式標準化。

主要功能：
- BaoStock API 封裝和適配
- 數據格式標準化
- 錯誤處理和重試機制
- 數據質量檢查
- 緩存和性能優化

支援的數據類型：
- A股歷史K線數據
- 財務報表數據
- 分紅配股數據
- 基本面數據

特點：
- 完全免費使用
- 無需註冊和認證
- 主要支援A股市場
- 數據更新頻率為T+1

Example:
    >>> from src.data_sources.base_data_source import DataSourceConfig
    >>> config = DataSourceConfig(name="baostock")
    >>> adapter = BaoStockAdapter(config)
    >>> df = await adapter.get_daily_data('sh.600000', '2023-01-01', '2023-12-31')
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import pandas as pd
import numpy as np

from .base_data_source import BaseDataSource, DataSourceConfig
from ..utils.data_validator import DataValidator
from ..utils.cache_manager import CacheManager

# 設定日誌
logger = logging.getLogger(__name__)


class BaoStockAdapter(BaseDataSource):
    """BaoStock 數據源適配器
    
    提供 BaoStock API 的統一接口，包括數據格式標準化、
    錯誤處理等功能。
    
    Attributes:
        bs: BaoStock API 實例
        login_status: 登錄狀態
        last_request_time: 最後請求時間
        
    Example:
        >>> config = DataSourceConfig(name="baostock")
        >>> adapter = BaoStockAdapter(config)
        >>> data = await adapter.get_daily_data('sh.600000', '2023-01-01', '2023-12-31')
    """
    
    def __init__(self, config: DataSourceConfig):
        """初始化 BaoStock 適配器

        Args:
            config: 數據源配置

        Raises:
            ImportError: 當 baostock 模組未安裝時
        """
        super().__init__(config)

        # 使用連接管理器
        from .baostock_connection_manager import get_baostock_connection_manager
        self.connection_manager = get_baostock_connection_manager()
        self.last_request_time = 0
        self.min_interval = config.api_limits.get('min_interval', 0.5)  # 最小請求間隔

        # 檢查模組可用性（不進行實際連接）
        if not self.connection_manager.is_module_available():
            raise ImportError("請安裝 baostock: pip install baostock")
        
        # 數據格式映射
        self.column_mapping = {
            'code': 'symbol',
            'date': 'date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'amount': 'amount',
            'pctChg': 'pct_change',
            'preclose': 'pre_close',
            'turn': 'turnover',
            'tradestatus': 'trade_status',
            'peTTM': 'pe_ttm',
            'pbMRQ': 'pb_mrq',
            'psTTM': 'ps_ttm'
        }
        
        logger.info(f"BaoStock適配器初始化完成，可用性: {self.is_available()}")

    def _setup_connection(self):
        """設定連接（實現 BaseDataSource 抽象方法）"""
        # 使用連接管理器，無需在此處建立連接
        # 連接將在需要時懶加載
        pass

    def is_available(self) -> bool:
        """檢查數據源是否可用

        Returns:
            數據源是否可用
        """
        return self.connection_manager.is_module_available()
    
    async def connect(self) -> bool:
        """連接到數據源（使用連接管理器）

        Returns:
            連接是否成功
        """
        if not self.is_available():
            return False

        try:
            # 使用連接管理器獲取連接
            bs = await self.connection_manager.get_connection()
            return bs is not None

        except Exception as e:
            logger.error(f"BaoStock 連接失敗: {e}")
            return False

    async def disconnect(self):
        """斷開連接（由連接管理器管理）"""
        # 連接由管理器統一管理，無需手動斷開
        pass
    
    async def get_daily_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str,
        **kwargs
    ) -> pd.DataFrame:
        """獲取日線數據
        
        Args:
            symbol: 股票代碼 (如 'sh.600000')
            start_date: 開始日期 (格式: 'YYYY-MM-DD')
            end_date: 結束日期 (格式: 'YYYY-MM-DD')
            **kwargs: 其他參數
                - adjustflag: 復權類型 ('1':前復權, '2':後復權, '3':不復權)
                - frequency: 數據頻率 ('d':日, 'w':週, 'm':月)
            
        Returns:
            標準化的日線數據
            
        Raises:
            RuntimeError: 當 API 調用失敗時
        """
        if not self.is_available():
            raise RuntimeError("BaoStock 數據源不可用")

        # 使用連接管理器獲取連接
        bs = await self.connection_manager.get_connection()
        if not bs:
            raise RuntimeError("無法建立 BaoStock 連接")
        
        # 控制請求頻率
        await self._rate_limit()
        
        try:
            # 設定參數
            adjustflag = kwargs.get('adjustflag', '3')  # 默認不復權
            frequency = kwargs.get('frequency', 'd')    # 默認日線
            
            # 設定要獲取的欄位
            fields = self._get_fields()
            
            # 調用 BaoStock API
            rs = bs.query_history_k_data_plus(
                symbol,
                fields,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag=adjustflag
            )
            
            # 檢查查詢結果
            if rs.error_code != '0':
                raise RuntimeError(f"BaoStock 查詢失敗: {rs.error_msg}")
            
            # 轉換為 DataFrame
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                logger.warning(f"未獲取到數據: {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 數據格式標準化
            standardized_df = self._standardize_data_format(df)
            
            # 數據質量檢查
            quality_score = self._check_data_quality(standardized_df)
            logger.debug(f"數據質量評分: {quality_score:.2f}")
            
            logger.info(f"成功獲取 {symbol} 日線數據，共 {len(standardized_df)} 條記錄")
            return standardized_df
            
        except Exception as e:
            logger.error(f"獲取日線數據失敗 {symbol}: {e}")
            raise RuntimeError(f"獲取日線數據失敗: {e}") from e
    
    async def get_realtime_data(self, symbols: List[str]) -> pd.DataFrame:
        """獲取實時數據
        
        Note:
            BaoStock 不提供實時數據，此方法返回空 DataFrame
            
        Args:
            symbols: 股票代碼列表
            
        Returns:
            空的 DataFrame
        """
        logger.warning("BaoStock 不支援實時數據")
        return pd.DataFrame()
    
    async def get_stock_basic(self, date: str = None) -> pd.DataFrame:
        """獲取股票基本信息
        
        Args:
            date: 查詢日期 (格式: 'YYYY-MM-DD')，默認為當前日期
            
        Returns:
            股票基本信息
        """
        # 使用連接管理器獲取連接
        bs = await self.connection_manager.get_connection()
        if not bs:
            raise RuntimeError("無法建立 BaoStock 連接")

        try:
            if date is None:
                date = datetime.now().strftime('%Y-%m-%d')

            rs = bs.query_all_stock(day=date)
            
            if rs.error_code != '0':
                raise RuntimeError(f"查詢股票基本信息失敗: {rs.error_msg}")
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if data_list:
                df = pd.DataFrame(data_list, columns=rs.fields)
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"獲取股票基本信息失敗: {e}")
            raise RuntimeError(f"獲取股票基本信息失敗: {e}") from e
    
    def _get_fields(self) -> str:
        """獲取查詢欄位
        
        Returns:
            欄位字符串
        """
        return ("date,code,open,high,low,close,preclose,volume,amount,"
                "adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,"
                "pcfNcfTTM,isST")
    
    async def _rate_limit(self):
        """控制請求頻率"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _standardize_data_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """標準化數據格式
        
        Args:
            df: 原始數據
            
        Returns:
            標準化後的數據
        """
        if df.empty:
            return df
        
        # 重命名欄位
        standardized_df = df.rename(columns=self.column_mapping)
        
        # 數據類型轉換
        if 'date' in standardized_df.columns:
            standardized_df['date'] = pd.to_datetime(standardized_df['date'])
        
        # 數值欄位轉換
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount', 
                          'pct_change', 'pre_close', 'turnover', 'pe_ttm', 'pb_mrq', 'ps_ttm']
        for col in numeric_columns:
            if col in standardized_df.columns:
                standardized_df[col] = pd.to_numeric(standardized_df[col], errors='coerce')
        
        # 處理特殊欄位
        if 'trade_status' in standardized_df.columns:
            # 交易狀態：1-正常交易, 0-停牌
            standardized_df['trade_status'] = pd.to_numeric(standardized_df['trade_status'], errors='coerce')
        
        # 排序
        if 'date' in standardized_df.columns:
            standardized_df = standardized_df.sort_values('date')
        
        return standardized_df
    
    def _check_data_quality(self, df: pd.DataFrame) -> float:
        """檢查數據質量
        
        Args:
            df: 數據框架
            
        Returns:
            質量評分 (0-1)
        """
        if df.empty:
            return 0.0
        
        quality_score = 1.0
        
        # 檢查缺失值
        missing_ratio = df.isnull().sum().sum() / (df.shape[0] * df.shape[1])
        quality_score -= missing_ratio * 0.3
        
        # 檢查價格邏輯
        if all(col in df.columns for col in ['high', 'low', 'open', 'close']):
            invalid_price = ((df['high'] < df['low']) | 
                           (df['open'] > df['high']) | (df['open'] < df['low']) |
                           (df['close'] > df['high']) | (df['close'] < df['low'])).sum()
            quality_score -= (invalid_price / len(df)) * 0.4
        
        # 檢查交易狀態
        if 'trade_status' in df.columns:
            # 停牌數據過多會影響質量
            suspended_ratio = (df['trade_status'] == 0).sum() / len(df)
            quality_score -= suspended_ratio * 0.2
        
        # 檢查數據連續性
        if 'date' in df.columns and len(df) > 1:
            date_gaps = (df['date'].diff().dt.days > 7).sum()  # 超過7天的間隔
            quality_score -= (date_gaps / len(df)) * 0.1
        
        return max(0.0, quality_score)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """獲取使用統計
        
        Returns:
            使用統計信息
        """
        return {
            'adapter_name': self.name,
            'is_available': self.is_available(),
            'login_status': self.login_status,
            'min_interval': self.min_interval,
            'last_request_time': self.last_request_time,
            'supported_markets': ['A股'],
            'data_types': ['歷史K線', '基本信息', '財務數據'],
            'cost': '免費'
        }

    def get_historical_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        **kwargs
    ) -> pd.DataFrame:
        """獲取歷史數據（實現 BaseDataSource 抽象方法）

        這是同步版本的 get_daily_data 包裝器

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            **kwargs: 其他參數

        Returns:
            歷史數據 DataFrame
        """
        import asyncio

        # 如果已經在事件循環中，直接調用同步版本
        try:
            loop = asyncio.get_running_loop()
            # 在已有事件循環中，使用 run_in_executor
            return loop.run_until_complete(
                self.get_daily_data(symbol, start_date, end_date, **kwargs)
            )
        except RuntimeError:
            # 沒有事件循環，創建新的
            return asyncio.run(
                self.get_daily_data(symbol, start_date, end_date, **kwargs)
            )

    def __del__(self):
        """析構函數，確保登出"""
        if hasattr(self, 'bs') and hasattr(self, 'login_status') and self.login_status:
            try:
                self.bs.logout()
            except:
                pass
