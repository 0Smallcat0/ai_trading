# -*- coding: utf-8 -*-
"""市場看盤適配器

此模組整合 ai_quant_trade-0.0.1/egs_aide/看盤神器/ 中的看盤工具功能到當前系統，
提供統一的市場監控和輔助操盤平台。

主要功能：
- Excel 看盤功能的統一封裝
- 實時行情數據獲取和顯示
- 自定義看盤面板配置和管理
- 數據導出和報表生成
- 預警系統和通知機制

支援的看盤功能：
- 自選股實時監控
- 概念板塊漲幅榜
- 龍虎榜數據展示
- 漲停板股票池
- 市場快訊和新聞

Example:
    >>> from src.strategies.adapters import MarketWatchAdapter
    >>> adapter = MarketWatchAdapter(
    ...     config={'refresh_interval': 5, 'data_source': 'qstock'}
    ... )
    >>> realtime_data = adapter.get_realtime_data('custom_stocks', ['000001', '000002'])
    >>> adapter.start_monitoring(['000001', '000002'])
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading

from .base import LegacyStrategyAdapter, AdapterError
from ...utils.cache_manager import CacheManager
from ...utils.data_validator import DataValidator

# 設定日誌
logger = logging.getLogger(__name__)


class MarketWatchConfig:
    """市場看盤配置類
    
    管理看盤工具的各種配置參數。
    
    Attributes:
        data_source: 數據源名稱
        refresh_interval: 刷新間隔（秒）
        enable_alerts: 是否啟用預警
        export_format: 導出格式
        
    Example:
        >>> config = MarketWatchConfig(
        ...     data_source='qstock',
        ...     refresh_interval=5,
        ...     enable_alerts=True
        ... )
    """
    
    def __init__(self,
                 data_source: str = 'qstock',
                 refresh_interval: int = 5,
                 enable_alerts: bool = True,
                 export_format: str = 'excel',
                 **kwargs):
        """初始化市場看盤配置
        
        Args:
            data_source: 數據源名稱
            refresh_interval: 刷新間隔（秒）
            enable_alerts: 是否啟用預警
            export_format: 導出格式
            **kwargs: 其他配置參數
        """
        self.data_source = data_source
        self.refresh_interval = refresh_interval
        self.enable_alerts = enable_alerts
        self.export_format = export_format
        
        # 看盤面板配置
        self.panel_config = kwargs.get('panel_config', {
            'show_custom_stocks': True,
            'show_concept_ranking': True,
            'show_billboard': True,
            'show_limit_up': True
        })
        
        # 預警配置
        self.alert_config = kwargs.get('alert_config', {
            'price_change_threshold': 0.05,  # 5% 價格變動預警
            'volume_spike_threshold': 2.0,   # 成交量異常倍數
            'enable_sound_alert': False
        })
        
        # 數據源配置
        self.qstock_config = kwargs.get('qstock_config', {
            'timeout': 10,
            'retry_count': 3,
            'cache_enabled': True
        })
        
        logger.info(f"市場看盤配置初始化: {data_source}, 刷新間隔: {refresh_interval}秒")


class MarketWatchDataManager:
    """市場看盤數據管理器

    負責市場看盤實時數據的獲取、處理和緩存管理。
    """
    
    def __init__(self, config: MarketWatchConfig):
        """初始化市場看盤數據管理器

        Args:
            config: 看盤配置
        """
        self.config = config
        self.cache_manager = None
        self.data_sources = {}
        self.last_update_time = {}
        
        # 初始化緩存管理器
        if config.qstock_config.get('cache_enabled', True):
            self._initialize_cache_manager()
        
        # 初始化數據源
        self._initialize_data_sources()
        
        logger.info("市場看盤數據管理器初始化完成")
    
    def _initialize_cache_manager(self):
        """初始化緩存管理器"""
        try:
            cache_config = {
                'cache_dir': 'cache/market_watch',
                'max_size_gb': 1,
                'ttl_seconds': self.config.refresh_interval * 2  # 緩存時間為刷新間隔的2倍
            }
            self.cache_manager = CacheManager(cache_config)
            logger.info("市場看盤緩存管理器初始化完成")
        except Exception as e:
            logger.warning(f"緩存管理器初始化失敗: {e}")
            self.cache_manager = None
    
    def _initialize_data_sources(self):
        """初始化數據源"""
        try:
            if self.config.data_source == 'qstock':
                self._initialize_qstock()
            # 可以添加其他數據源的初始化
            
        except ImportError as e:
            logger.error(f"數據源初始化失敗，缺少依賴: {e}")
            raise ImportError(f"請安裝必要的依賴庫: {e}") from e
        except Exception as e:
            logger.error(f"數據源初始化失敗: {e}")
            raise AdapterError(f"數據源初始化失敗: {e}") from e
    
    def _initialize_qstock(self):
        """初始化 qstock 數據源"""
        try:
            import qstock as qs
            self.qstock = qs
            self.data_sources['qstock'] = qs
            logger.info("qstock 數據源初始化完成")
        except ImportError:
            logger.warning("qstock 庫未安裝，將使用模擬數據")
            self.qstock = self._create_mock_qstock()
            self.data_sources['qstock'] = self.qstock
    
    def _create_mock_qstock(self):
        """創建模擬 qstock 數據源"""
        class MockQstock:
            def realtime_data(self, code):
                """模擬實時數據"""
                if isinstance(code, list):
                    data = []
                    for c in code:
                        data.append({
                            '代碼': c,
                            '名稱': f'股票{c}',
                            '最新': np.random.uniform(10, 100),
                            '漲幅': np.random.uniform(-0.1, 0.1),
                            '時間': datetime.now().strftime('%H:%M:%S')
                        })
                    return pd.DataFrame(data)
                elif code == '概念板块':
                    # 模擬概念板塊數據
                    concepts = ['人工智能', '新能源', '半導體', '醫藥', '軍工']
                    data = []
                    for concept in concepts:
                        data.append({
                            '板塊名稱': concept,
                            '漲幅': np.random.uniform(-0.05, 0.15),
                            '領漲股': f'{concept}龍頭',
                            '成交額': np.random.uniform(1e8, 1e10)
                        })
                    return pd.DataFrame(data)
                else:
                    return pd.DataFrame()
            
            def stock_billboard(self):
                """模擬龍虎榜數據"""
                data = []
                for i in range(10):
                    data.append({
                        '代碼': f'00000{i}',
                        '名稱': f'龍虎股{i}',
                        '漲幅': np.random.uniform(0.05, 0.2),
                        '成交額': np.random.uniform(1e8, 1e9),
                        '上榜原因': '日漲幅偏離值達7%'
                    })
                return pd.DataFrame(data)
            
            def stock_zt_pool(self):
                """模擬漲停板數據"""
                data = []
                for i in range(20):
                    data.append({
                        '代碼': f'30000{i}',
                        '名稱': f'漲停股{i}',
                        '最新價': np.random.uniform(10, 50),
                        '漲幅': 0.10,
                        '封板時間': f'{9 + i//10}:{30 + i%10:02d}',
                        '封板資金': np.random.uniform(1e6, 1e8)
                    })
                return pd.DataFrame(data)
        
        return MockQstock()
    
    def get_realtime_data(self, data_type: str, symbols: Optional[List[str]] = None) -> pd.DataFrame:
        """獲取實時數據
        
        Args:
            data_type: 數據類型 ('custom_stocks', 'concept_ranking', 'billboard', 'limit_up')
            symbols: 股票代碼列表（僅對 custom_stocks 有效）
            
        Returns:
            實時數據 DataFrame
        """
        try:
            # 檢查緩存
            cache_key = f"{data_type}_{symbols if symbols else 'all'}"
            if self.cache_manager:
                cached_data = self.cache_manager.get(cache_key)
                if cached_data is not None:
                    logger.debug(f"從緩存獲取 {data_type} 數據")
                    return cached_data
            
            # 獲取數據
            data = None
            
            if data_type == 'custom_stocks' and symbols:
                data = self._get_custom_stocks_data(symbols)
            elif data_type == 'concept_ranking':
                data = self._get_concept_ranking_data()
            elif data_type == 'billboard':
                data = self._get_billboard_data()
            elif data_type == 'limit_up':
                data = self._get_limit_up_data()
            else:
                raise ValueError(f"不支援的數據類型: {data_type}")
            
            # 緩存數據
            if self.cache_manager and data is not None:
                self.cache_manager.set(cache_key, data)
            
            # 更新最後更新時間
            self.last_update_time[data_type] = datetime.now()
            
            return data if data is not None else pd.DataFrame()
            
        except Exception as e:
            logger.error(f"獲取實時數據失敗 ({data_type}): {e}")
            return pd.DataFrame()
    
    def _get_custom_stocks_data(self, symbols: List[str]) -> pd.DataFrame:
        """獲取自選股數據"""
        if not symbols:
            return pd.DataFrame()
        
        # 移除股票代碼後綴（如 .SZ, .SH）
        clean_symbols = [symbol.split('.')[0] for symbol in symbols]
        
        try:
            df = self.qstock.realtime_data(code=clean_symbols)
            if not df.empty:
                # 標準化列名
                column_mapping = {
                    '最新': '現價(元)',
                    '漲幅': '漲跌幅',
                    '時間': '刷新時間'
                }
                df = df.rename(columns=column_mapping)
                
                # 添加額外信息
                df['更新時間'] = datetime.now().strftime('%H:%M:%S')
                
            return df
        except Exception as e:
            logger.error(f"獲取自選股數據失敗: {e}")
            return pd.DataFrame()
    
    def _get_concept_ranking_data(self) -> pd.DataFrame:
        """獲取概念板塊漲幅榜數據"""
        try:
            df = self.qstock.realtime_data('概念板块')
            if not df.empty:
                # 按漲幅排序
                if '漲幅' in df.columns:
                    df = df.sort_values('漲幅', ascending=False)
                
                # 添加排名
                df['排名'] = range(1, len(df) + 1)
                
            return df
        except Exception as e:
            logger.error(f"獲取概念板塊數據失敗: {e}")
            return pd.DataFrame()
    
    def _get_billboard_data(self) -> pd.DataFrame:
        """獲取龍虎榜數據"""
        try:
            df = self.qstock.stock_billboard()
            if not df.empty:
                # 添加更新時間
                df['數據時間'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
            return df
        except Exception as e:
            logger.error(f"獲取龍虎榜數據失敗: {e}")
            return pd.DataFrame()
    
    def _get_limit_up_data(self) -> pd.DataFrame:
        """獲取漲停板數據"""
        try:
            df = self.qstock.stock_zt_pool()
            if not df.empty:
                # 按封板時間排序
                if '封板時間' in df.columns:
                    df = df.sort_values('封板時間')
                
                # 添加序號
                df['序號'] = range(1, len(df) + 1)
                
            return df
        except Exception as e:
            logger.error(f"獲取漲停板數據失敗: {e}")
            return pd.DataFrame()
    
    def get_last_update_time(self, data_type: str) -> Optional[datetime]:
        """獲取最後更新時間
        
        Args:
            data_type: 數據類型
            
        Returns:
            最後更新時間
        """
        return self.last_update_time.get(data_type)


class MarketWatchAdapter(LegacyStrategyAdapter):
    """市場看盤適配器
    
    提供統一的市場監控和輔助操盤功能，整合原有 Excel 看盤工具的功能
    到 Web 界面。
    
    Attributes:
        config: 看盤配置
        data_manager: 實時數據管理器
        monitoring_active: 監控狀態
        
    Example:
        >>> adapter = MarketWatchAdapter(
        ...     config={'data_source': 'qstock', 'refresh_interval': 5}
        ... )
        >>> data = adapter.get_realtime_data('custom_stocks', ['000001', '000002'])
        >>> adapter.start_monitoring(['000001', '000002'])
    """
    
    def __init__(self,
                 config: Optional[Dict[str, Any]] = None,
                 **kwargs):
        """初始化市場看盤適配器
        
        Args:
            config: 配置參數字典
            **kwargs: 其他參數
        """
        # 設定基本參數
        parameters = {
            'config': config or {},
            **kwargs
        }
        
        super().__init__(name="MarketWatch", **parameters)
        
        # 初始化配置
        self.config = MarketWatchConfig(**(config or {}))
        
        # 初始化組件
        self.data_manager = MarketWatchDataManager(self.config)
        self.monitoring_active = False
        self.monitoring_thread = None
        self.monitoring_callback = None
        
        # 監控數據存儲
        self.monitored_symbols = []
        self.alert_history = []
        
        logger.info("市場看盤適配器初始化完成")
    
    def get_realtime_data(self,
                         data_type: str,
                         symbols: Optional[List[str]] = None) -> pd.DataFrame:
        """獲取實時數據
        
        Args:
            data_type: 數據類型
            symbols: 股票代碼列表
            
        Returns:
            實時數據 DataFrame
        """
        try:
            return self.data_manager.get_realtime_data(data_type, symbols)
        except Exception as e:
            logger.error(f"獲取實時數據失敗: {e}")
            raise AdapterError(f"獲取實時數據失敗: {e}") from e
    
    def start_monitoring(self,
                        symbols: List[str],
                        callback: Optional[Callable] = None):
        """開始監控
        
        Args:
            symbols: 要監控的股票代碼列表
            callback: 數據更新回調函數
        """
        if self.monitoring_active:
            logger.warning("監控已在運行中")
            return
        
        self.monitored_symbols = symbols
        self.monitoring_callback = callback
        self.monitoring_active = True
        
        # 啟動監控線程
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        
        logger.info(f"開始監控 {len(symbols)} 隻股票")
    
    def stop_monitoring(self):
        """停止監控"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        logger.info("監控已停止")
    
    def _monitoring_loop(self):
        """監控循環"""
        while self.monitoring_active:
            try:
                # 獲取實時數據
                data = self.get_realtime_data('custom_stocks', self.monitored_symbols)
                
                # 檢查預警條件
                if self.config.enable_alerts:
                    self._check_alerts(data)
                
                # 調用回調函數
                if self.monitoring_callback and not data.empty:
                    self.monitoring_callback(data)
                
                # 等待下次刷新
                time.sleep(self.config.refresh_interval)
                
            except Exception as e:
                logger.error(f"監控循環錯誤: {e}")
                time.sleep(self.config.refresh_interval)
    
    def _check_alerts(self, data: pd.DataFrame):
        """檢查預警條件"""
        if data.empty:
            return
        
        threshold = self.config.alert_config['price_change_threshold']
        
        for _, row in data.iterrows():
            if '漲跌幅' in row and abs(row['漲跌幅']) > threshold:
                alert = {
                    'time': datetime.now(),
                    'symbol': row.get('代碼', 'Unknown'),
                    'name': row.get('名稱', 'Unknown'),
                    'change': row['漲跌幅'],
                    'price': row.get('現價(元)', 0),
                    'type': 'price_alert'
                }
                
                self.alert_history.append(alert)
                logger.info(f"價格預警: {alert['name']} ({alert['symbol']}) 漲跌幅 {alert['change']:.2%}")
    
    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """獲取預警歷史
        
        Args:
            limit: 返回記錄數限制
            
        Returns:
            預警歷史列表
        """
        return self.alert_history[-limit:] if self.alert_history else []
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """獲取策略資訊
        
        Returns:
            策略詳細資訊
        """
        return {
            'name': self.name,
            'type': 'Market Watch',
            'category': 'MarketWatch',
            'data_source': self.config.data_source,
            'parameters': {
                'refresh_interval': self.config.refresh_interval,
                'enable_alerts': self.config.enable_alerts,
                'export_format': self.config.export_format,
            },
            'description': '市場看盤適配器，提供實時行情監控和輔助操盤功能',
            'source': 'ai_quant_trade-0.0.1/egs_aide/看盤神器',
            'adapter_version': '1.0.0',
            'supported_data_types': ['custom_stocks', 'concept_ranking', 'billboard', 'limit_up'],
            'monitoring_status': {
                'active': self.monitoring_active,
                'monitored_symbols': len(self.monitored_symbols),
                'alert_count': len(self.alert_history)
            }
        }

    # 實現抽象方法
    def _load_legacy_strategy(self) -> None:
        """載入原始策略（市場看盤不需要策略載入）"""
        # 市場看盤適配器不需要載入特定策略
        pass

    def _convert_parameters(self, **parameters: Any) -> Dict[str, Any]:
        """轉換策略參數格式（市場看盤使用配置而非策略參數）"""
        # 將通用參數轉換為市場看盤配置格式
        converted = {}

        # 映射常用參數
        if 'symbols' in parameters:
            converted['custom_stocks'] = parameters['symbols']
        if 'refresh_interval' in parameters:
            converted['refresh_interval'] = parameters['refresh_interval']
        if 'enable_alerts' in parameters:
            converted['enable_alerts'] = parameters['enable_alerts']

        # 保留其他參數
        for key, value in parameters.items():
            if key not in ['symbols', 'refresh_interval', 'enable_alerts']:
                converted[key] = value

        return converted

    def _execute_legacy_strategy(self, data: pd.DataFrame, **parameters: Any) -> Any:
        """執行原始策略（市場看盤返回實時數據）"""
        # 市場看盤不執行策略，而是返回實時市場數據
        try:
            # 轉換參數
            config = self._convert_parameters(**parameters)

            # 根據數據類型返回相應的市場數據
            if 'data_type' in config:
                return self.get_realtime_data(config['data_type'], config.get('symbols', []))
            else:
                # 默認返回自選股數據
                symbols = config.get('custom_stocks', [])
                if symbols:
                    return self.get_realtime_data('custom_stocks', symbols)
                else:
                    return pd.DataFrame()
        except Exception as e:
            logger.error(f"執行市場看盤數據獲取失敗: {e}")
            return pd.DataFrame()

    def _convert_results(self, legacy_results: Any, data: pd.DataFrame) -> pd.DataFrame:
        """轉換策略結果格式（將市場數據轉換為標準格式）"""
        try:
            if isinstance(legacy_results, pd.DataFrame):
                # 如果已經是DataFrame，直接返回
                return legacy_results
            elif isinstance(legacy_results, dict):
                # 如果是字典，轉換為DataFrame
                return pd.DataFrame([legacy_results])
            elif isinstance(legacy_results, list):
                # 如果是列表，轉換為DataFrame
                return pd.DataFrame(legacy_results)
            else:
                # 其他類型，返回空DataFrame
                logger.warning(f"未知的結果類型: {type(legacy_results)}")
                return pd.DataFrame()
        except Exception as e:
            logger.error(f"轉換市場看盤結果失敗: {e}")
            return pd.DataFrame()
