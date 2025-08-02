# -*- coding: utf-8 -*-
"""
統一數據管理器

⚠️ 重要通知：此模組已棄用 ⚠️

遷移指南：
- UnifiedDataManager → 使用 DataCollectionSystem
- 智能資料源選擇 → 使用 CollectorManager.get_best_collector()
- 性能統計 → 使用 CollectorManager.update_performance_stats()

新架構位置：
- src.data_sources.data_collection_system.DataCollectionSystem
- src.data_sources.collector_manager.CollectorManager

此模組提供統一的數據管理接口，整合現有項目和原始項目的數據處理能力。

主要功能：
- 多數據源統一管理
- 數據源自動切換和容錯
- 數據質量檢查和清洗
- 實時和歷史數據統一接口
- 數據緩存和存儲管理
- 數據源性能監控

整合特色：
- 兼容原始項目的數據接口
- 支持新的多代理數據需求
- 提供統一的數據格式
- 智能數據源選擇和切換
"""

import warnings

import logging
import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 導入現有數據源
from .data_collector import DataCollector
from .yahoo_adapter import YahooAdapter
from .broker_adapter import BrokerAdapter, MockBrokerAdapter
from .twse_crawler import TWSECrawler
from .news_sentiment_collector import NewsSentimentCollector
from .data_collection_system import DataCollectionSystem

# 導入原始項目數據源適配器
from .legacy_adapters import LegacyDataSourceManager

# 導入新增數據源適配器
from .qstock_adapter import QStockAdapter
from .data_source_router import DataSourceRouter

# 設定日誌
logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """數據源類型枚舉"""
    YAHOO = "yahoo"
    TWSE = "twse"
    BROKER = "broker"
    NEWS = "news"
    QSTOCK = "qstock"
    LEGACY_TUSHARE = "legacy_tushare"
    LEGACY_WIND = "legacy_wind"
    LEGACY_BAOSTOCK = "legacy_baostock"
    # 新增數據源類型
    TUSHARE = "tushare"
    BAOSTOCK = "baostock"


class DataType(Enum):
    """數據類型枚舉"""
    PRICE = "price"              # 價格數據
    VOLUME = "volume"            # 成交量數據
    FUNDAMENTAL = "fundamental"   # 基本面數據
    NEWS = "news"                # 新聞數據
    SENTIMENT = "sentiment"      # 情緒數據
    TECHNICAL = "technical"      # 技術指標數據


@dataclass
class DataRequest:
    """數據請求結構"""
    symbols: List[str]
    data_type: DataType
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    frequency: str = "1d"  # 1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M
    fields: Optional[List[str]] = None
    source_preference: Optional[List[DataSourceType]] = None
    real_time: bool = False


@dataclass
class DataResponse:
    """數據響應結構"""
    data: pd.DataFrame
    source: DataSourceType
    request: DataRequest
    timestamp: datetime
    quality_score: float
    metadata: Dict[str, Any]


class UnifiedDataManager:
    """
    統一數據管理器
    
    整合多個數據源，提供統一的數據獲取接口，
    支持自動容錯、數據質量檢查和智能源選擇。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, lazy_init: bool = True):
        """
        初始化統一數據管理器

        ⚠️ 已棄用：請使用新的模組化架構

        Args:
            config: 配置參數
            lazy_init: 是否使用懶加載初始化（提升性能）
        """
        warnings.warn(
            "UnifiedDataManager 已棄用，請使用新的模組化架構：\n"
            "from src.data_sources import DataCollectionSystem\n"
            "system = DataCollectionSystem()\n"
            "詳見：docs/開發者指南/配置管理器使用指南.md",
            DeprecationWarning,
            stacklevel=2
        )
        self.config = config or {}
        self.lazy_init = lazy_init

        # 初始化數據源
        self.data_sources = {}
        self._initialized_sources = set()  # 追蹤已初始化的數據源

        if not lazy_init:
            # 立即初始化所有數據源（舊行為）
            self._initialize_data_sources()
        else:
            # 懶加載模式：只初始化關鍵數據源
            self._initialize_critical_sources()

        # 初始化原始項目數據源管理器
        self.legacy_manager = None  # 先設置為 None
        try:
            legacy_config = self.config.get('legacy_sources', {})
            self.legacy_manager = LegacyDataSourceManager(legacy_config)
            logger.info("原始數據源管理器初始化成功")
        except Exception as e:
            logger.warning(f"原始數據源管理器初始化失敗: {e}")
            self.legacy_manager = None

        # 數據緩存
        self.cache = {}
        self.cache_ttl = self.config.get('cache_ttl', 300)  # 5分鐘
        
        # 性能統計
        self.source_performance = {source: {'success': 0, 'failure': 0, 'avg_time': 0.0} 
                                 for source in DataSourceType}
        
        # 線程池
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # 實時數據流
        self.real_time_streams = {}
        self.stream_callbacks = {}

        # 初始化數據源路由器
        self.router = None
        self._initialize_router()

        logger.info("統一數據管理器初始化完成")

    def _initialize_critical_sources(self):
        """初始化關鍵數據源（懶加載模式）"""
        try:
            # 只初始化最基本的數據源，其他按需加載
            self.data_sources[DataSourceType.BROKER] = MockBrokerAdapter()
            self._initialized_sources.add(DataSourceType.BROKER)

            logger.info("關鍵數據源初始化完成（懶加載模式）")
        except Exception as e:
            logger.error(f"關鍵數據源初始化失敗: {e}")

    def _ensure_source_initialized(self, source_type: DataSourceType, timeout: float = 3.0):
        """確保指定數據源已初始化（懶加載）

        Args:
            source_type: 數據源類型
            timeout: 初始化超時時間（秒）
        """
        if source_type in self._initialized_sources:
            return

        import time
        start_time = time.time()

        try:
            if source_type == DataSourceType.YAHOO:
                self.data_sources[source_type] = YahooAdapter()
            elif source_type == DataSourceType.TWSE:
                self.data_sources[source_type] = TWSECrawler()
            elif source_type == DataSourceType.NEWS:
                self.data_sources[source_type] = NewsSentimentCollector()
            elif source_type == DataSourceType.QSTOCK:
                self._initialize_qstock_adapter()
            elif source_type == DataSourceType.TUSHARE:
                self._initialize_tushare_adapter()
            elif source_type == DataSourceType.BAOSTOCK:
                self._initialize_baostock_adapter()

            self._initialized_sources.add(source_type)

            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.warning(f"數據源 {source_type} 初始化耗時 {elapsed:.2f}s，超過預期 {timeout}s")
            else:
                logger.debug(f"數據源 {source_type} 初始化完成，耗時 {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"數據源 {source_type} 初始化失敗: {e}")
            # 不要讓單個數據源的失敗影響整個系統

    def _initialize_data_sources(self):
        """初始化數據源"""
        try:
            # 初始化現有數據源
            self.data_sources[DataSourceType.YAHOO] = YahooAdapter()
            self.data_sources[DataSourceType.TWSE] = TWSECrawler()
            self.data_sources[DataSourceType.BROKER] = MockBrokerAdapter()
            self.data_sources[DataSourceType.NEWS] = NewsSentimentCollector()

            # 初始化 QStock 數據源
            self._initialize_qstock_adapter()

            # 初始化新增的專用數據源適配器
            self._initialize_tushare_adapter()
            self._initialize_baostock_adapter()

            # 初始化原始項目數據源（通過適配器）
            self._initialize_legacy_sources()

            logger.info(f"初始化了 {len(self.data_sources)} 個數據源")

        except Exception as e:
            logger.error(f"數據源初始化失敗: {e}")
            # 確保至少有基本的數據源可用
            if not self.data_sources:
                logger.info("創建基本模擬數據源")
                self.data_sources[DataSourceType.BROKER] = MockBrokerAdapter()

    def _initialize_qstock_adapter(self):
        """初始化 QStock 適配器"""
        import time
        start_time = time.time()
        timeout = 3.0  # 3秒超時

        try:
            from .base_data_source import DataSourceConfig
            qstock_config = DataSourceConfig(
                name="qstock",
                cache_dir=self.config.get('cache_dir', 'cache'),
                cache_ttl=self.config.get('cache_ttl', 3600)
            )

            # 檢查是否超時
            if time.time() - start_time > timeout:
                logger.warning("qstock數據源初始化超時，跳過")
                return

            self.data_sources[DataSourceType.QSTOCK] = QStockAdapter(qstock_config)
            elapsed = time.time() - start_time
            logger.info(f"qstock數據源初始化成功，耗時 {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - start_time
            logger.warning(f"qstock數據源初始化失敗 (耗時 {elapsed:.2f}s): {e}")

    def _initialize_tushare_adapter(self):
        """初始化 Tushare Pro 適配器"""
        try:
            from .tushare_adapter import TushareAdapter
            from .base_data_source import DataSourceConfig

            tushare_config = DataSourceConfig(
                name="tushare",
                cache_dir=self.config.get('cache_dir', 'cache/tushare'),
                cache_ttl=self.config.get('cache_ttl', 3600),
                credentials=self.config.get('tushare', {}),
                api_limits=self.config.get('tushare_limits', {
                    'daily_calls': 10000,
                    'min_interval': 0.1
                })
            )

            adapter = TushareAdapter(tushare_config)
            if adapter.is_available():
                self.data_sources[DataSourceType.TUSHARE] = adapter
                logger.info("Tushare Pro 數據源初始化成功")
            else:
                logger.warning("Tushare Pro 數據源不可用")

        except ImportError as e:
            logger.warning(f"Tushare 適配器模組導入失敗: {e}")
        except Exception as e:
            logger.warning(f"Tushare 數據源初始化失敗: {e}")

    def _initialize_baostock_adapter(self):
        """初始化 BaoStock 適配器"""
        try:
            from .baostock_adapter import BaoStockAdapter
            from .base_data_source import DataSourceConfig

            baostock_config = DataSourceConfig(
                name="baostock",
                cache_dir=self.config.get('cache_dir', 'cache/baostock'),
                cache_ttl=self.config.get('cache_ttl', 3600),
                api_limits=self.config.get('baostock_limits', {
                    'min_interval': 0.5
                })
            )

            adapter = BaoStockAdapter(baostock_config)
            if adapter.is_available():
                self.data_sources[DataSourceType.BAOSTOCK] = adapter
                logger.info("BaoStock 數據源初始化成功")
            else:
                logger.warning("BaoStock 數據源不可用")

        except ImportError as e:
            logger.warning(f"BaoStock 適配器模組導入失敗: {e}")
        except Exception as e:
            logger.warning(f"BaoStock 數據源初始化失敗: {e}")

    def _initialize_legacy_sources(self):
        """初始化原始項目數據源"""
        try:
            if self.legacy_manager is None:
                logger.warning("原始數據源管理器未初始化，跳過原始數據源初始化")
                return

            available_legacy_sources = self.legacy_manager.get_available_sources()
            for source in available_legacy_sources:
                if source == 'tushare':
                    self.data_sources[DataSourceType.LEGACY_TUSHARE] = self.legacy_manager
                elif source == 'wind':
                    self.data_sources[DataSourceType.LEGACY_WIND] = self.legacy_manager
                elif source == 'baostock':
                    self.data_sources[DataSourceType.LEGACY_BAOSTOCK] = self.legacy_manager

            logger.info(f"可用的原始數據源: {available_legacy_sources}")
        except Exception as e:
            logger.warning(f"原始數據源初始化失敗: {e}")

    def _initialize_router(self):
        """初始化數據源路由器"""
        try:
            # 過濾出可用的適配器
            available_adapters = {}
            for source_type, adapter in self.data_sources.items():
                if hasattr(adapter, 'is_available') and adapter.is_available():
                    available_adapters[source_type.value] = adapter
                elif not hasattr(adapter, 'is_available'):
                    # 對於沒有 is_available 方法的適配器，假設可用
                    available_adapters[source_type.value] = adapter

            if available_adapters:
                self.router = DataSourceRouter(available_adapters)
                logger.info(f"數據源路由器初始化完成，管理 {len(available_adapters)} 個數據源")
            else:
                logger.warning("沒有可用的數據源，路由器未初始化")

        except Exception as e:
            logger.error(f"數據源路由器初始化失敗: {e}")
            self.router = None
    
    async def get_data(self, request: DataRequest) -> DataResponse:
        """
        獲取數據的主要接口
        
        Args:
            request: 數據請求
            
        Returns:
            DataResponse: 數據響應
        """
        try:
            # 檢查緩存
            cache_key = self._generate_cache_key(request)
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if self._is_cache_valid(cached_data):
                    logger.debug(f"從緩存返回數據: {cache_key}")
                    return cached_data
            
            # 選擇數據源
            data_sources = self._select_data_sources(request)
            
            # 並行嘗試多個數據源
            response = await self._fetch_from_sources(request, data_sources)
            
            # 數據質量檢查
            response = self._validate_data_quality(response)
            
            # 緩存數據
            self.cache[cache_key] = response
            
            # 更新性能統計
            self._update_performance_stats(response.source, True, 0.0)
            
            return response
            
        except Exception as e:
            logger.error(f"獲取數據失敗: {e}")
            raise
    
    def _select_data_sources(self, request: DataRequest) -> List[DataSourceType]:
        """選擇合適的數據源"""
        if request.source_preference:
            return request.source_preference
        
        # 根據數據類型和符號選擇數據源
        sources = []
        
        if request.data_type == DataType.PRICE:
            # 價格數據優先級
            sources = [DataSourceType.YAHOO, DataSourceType.TWSE, DataSourceType.BROKER]
        elif request.data_type == DataType.NEWS:
            sources = [DataSourceType.NEWS]
        elif request.data_type == DataType.FUNDAMENTAL:
            sources = [DataSourceType.TWSE, DataSourceType.YAHOO]
        else:
            sources = list(self.data_sources.keys())
        
        # 根據性能排序
        sources.sort(key=lambda x: self._get_source_score(x), reverse=True)
        
        return sources
    
    def _get_source_score(self, source: DataSourceType) -> float:
        """計算數據源評分"""
        stats = self.source_performance[source]
        total_requests = stats['success'] + stats['failure']
        
        if total_requests == 0:
            return 0.5  # 默認評分
        
        success_rate = stats['success'] / total_requests
        speed_score = max(0, 1 - stats['avg_time'] / 10)  # 10秒為基準
        
        return success_rate * 0.7 + speed_score * 0.3
    
    async def _fetch_from_sources(
        self, 
        request: DataRequest, 
        sources: List[DataSourceType]
    ) -> DataResponse:
        """從數據源獲取數據"""
        
        for source in sources:
            try:
                start_time = datetime.now()
                
                # 調用對應的數據源
                data = await self._fetch_from_source(source, request)
                
                if data is not None and not data.empty:
                    fetch_time = (datetime.now() - start_time).total_seconds()
                    
                    response = DataResponse(
                        data=data,
                        source=source,
                        request=request,
                        timestamp=datetime.now(),
                        quality_score=self._calculate_quality_score(data),
                        metadata={'fetch_time': fetch_time}
                    )
                    
                    self._update_performance_stats(source, True, fetch_time)
                    return response
                
            except Exception as e:
                logger.warning(f"數據源 {source.value} 獲取失敗: {e}")
                self._update_performance_stats(source, False, 0.0)
                continue
        
        raise Exception("所有數據源都無法獲取數據")
    
    async def _fetch_from_source(
        self, 
        source: DataSourceType, 
        request: DataRequest
    ) -> Optional[pd.DataFrame]:
        """從特定數據源獲取數據"""
        
        if source not in self.data_sources:
            return None
        
        data_source = self.data_sources[source]
        
        try:
            if source == DataSourceType.YAHOO:
                return await self._fetch_yahoo_data(data_source, request)
            elif source == DataSourceType.TWSE:
                return await self._fetch_twse_data(data_source, request)
            elif source == DataSourceType.BROKER:
                return await self._fetch_broker_data(data_source, request)
            elif source == DataSourceType.NEWS:
                return await self._fetch_news_data(data_source, request)
            # TODO: 添加原始項目數據源的獲取邏輯
            else:
                logger.warning(f"未實現的數據源: {source.value}")
                return None
                
        except Exception as e:
            logger.error(f"從 {source.value} 獲取數據失敗: {e}")
            return None
    
    async def _fetch_yahoo_data(self, source, request: DataRequest) -> pd.DataFrame:
        """從Yahoo獲取數據"""
        # 這裡需要根據實際的YahooAdapter接口實現
        # 目前提供模擬實現
        
        if request.data_type == DataType.PRICE:
            # 模擬價格數據
            dates = pd.date_range(
                start=request.start_date or datetime.now() - timedelta(days=30),
                end=request.end_date or datetime.now(),
                freq='D'
            )
            
            data = pd.DataFrame({
                'symbol': request.symbols[0] if request.symbols else 'AAPL',
                'date': dates,
                'open': np.random.uniform(100, 200, len(dates)),
                'high': np.random.uniform(100, 200, len(dates)),
                'low': np.random.uniform(100, 200, len(dates)),
                'close': np.random.uniform(100, 200, len(dates)),
                'volume': np.random.randint(1000000, 10000000, len(dates))
            })
            
            return data
        
        return pd.DataFrame()
    
    async def _fetch_twse_data(self, source, request: DataRequest) -> pd.DataFrame:
        """從台灣證交所獲取數據"""
        # 根據實際的TWSECrawler接口實現
        return pd.DataFrame()
    
    async def _fetch_broker_data(self, source, request: DataRequest) -> pd.DataFrame:
        """從券商獲取數據"""
        # 根據實際的BrokerAdapter接口實現
        return pd.DataFrame()
    
    async def _fetch_news_data(self, source, request: DataRequest) -> pd.DataFrame:
        """從新聞源獲取數據"""
        # 根據實際的NewsSentimentCollector接口實現
        return pd.DataFrame()
    
    def _calculate_quality_score(self, data: pd.DataFrame) -> float:
        """計算數據質量評分"""
        if data.empty:
            return 0.0
        
        # 基本質量檢查
        completeness = 1 - data.isnull().sum().sum() / (data.shape[0] * data.shape[1])
        
        # 數據一致性檢查
        consistency = 1.0  # 簡化實現
        
        # 時效性檢查
        timeliness = 1.0  # 簡化實現
        
        return (completeness * 0.5 + consistency * 0.3 + timeliness * 0.2)
    
    def _validate_data_quality(self, response: DataResponse) -> DataResponse:
        """驗證數據質量"""
        if response.quality_score < 0.7:
            logger.warning(f"數據質量較低: {response.quality_score:.2f}")
        
        return response
    
    def _generate_cache_key(self, request: DataRequest) -> str:
        """生成緩存鍵"""
        key_parts = [
            str(request.symbols),
            request.data_type.value,
            str(request.start_date),
            str(request.end_date),
            request.frequency
        ]
        return "|".join(key_parts)
    
    def _is_cache_valid(self, cached_data: DataResponse) -> bool:
        """檢查緩存是否有效"""
        age = (datetime.now() - cached_data.timestamp).total_seconds()
        return age < self.cache_ttl
    
    def _update_performance_stats(
        self, 
        source: DataSourceType, 
        success: bool, 
        fetch_time: float
    ):
        """更新性能統計"""
        stats = self.source_performance[source]
        
        if success:
            stats['success'] += 1
            # 更新平均時間
            total_success = stats['success']
            stats['avg_time'] = (stats['avg_time'] * (total_success - 1) + fetch_time) / total_success
        else:
            stats['failure'] += 1
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """獲取性能統計"""
        return {
            'source_performance': self.source_performance,
            'cache_size': len(self.cache),
            'cache_hit_rate': 0.0  # TODO: 實現緩存命中率統計
        }
    
    def clear_cache(self):
        """清理緩存"""
        self.cache.clear()
        logger.info("數據緩存已清理")

    def get_available_sources(self) -> List[str]:
        """獲取可用的數據源列表

        Returns:
            List[str]: 可用數據源名稱列表
        """
        available_sources = []

        # 檢查現有數據源
        for source_type, source in self.data_sources.items():
            if source is not None:
                available_sources.append(source_type.value)

        # 檢查路由器中的數據源
        if hasattr(self, 'router') and self.router:
            router_sources = list(self.router.adapters.keys())
            available_sources.extend(router_sources)

        # 去重並排序
        available_sources = sorted(list(set(available_sources)))

        logger.info(f"發現 {len(available_sources)} 個可用數據源: {available_sources}")
        return available_sources

    def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """獲取數據源狀態信息

        Returns:
            Dict[str, Dict[str, Any]]: 數據源狀態信息
        """
        status = {}

        for source_type, source in self.data_sources.items():
            source_name = source_type.value
            if source is not None:
                try:
                    # 嘗試檢查數據源是否可用
                    if hasattr(source, 'is_available'):
                        is_available = source.is_available()
                    else:
                        is_available = True  # 假設可用

                    status[source_name] = {
                        "available": is_available,
                        "type": type(source).__name__,
                        "status": "正常" if is_available else "不可用"
                    }
                except Exception as e:
                    status[source_name] = {
                        "available": False,
                        "type": type(source).__name__,
                        "status": f"錯誤: {str(e)}"
                    }
            else:
                status[source_name] = {
                    "available": False,
                    "type": "未初始化",
                    "status": "未配置"
                }

        return status

    def __del__(self):
        """析構函數"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
