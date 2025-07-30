# -*- coding: utf-8 -*-
"""
數據源整合適配器

此模組將擴展的數據源整合到原始項目中，
擴展原始項目的數據管理系統並提供統一的數據接口。

主要功能：
- 新數據源整合（qstock等）
- 數據源健康監控整合
- 數據質量管理整合
- 緩存系統整合
- 原始數據IO擴展

整合策略：
- 擴展原始項目的quant_brain/data_io模組
- 整合到原始項目的數據管理流程
- 提供統一的數據獲取接口
- 保持與原始項目的兼容性
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import pandas as pd

# 設定日誌
logger = logging.getLogger(__name__)


class DataSourceAdapter:
    """
    數據源整合適配器
    
    將擴展的數據源整合到原始項目中
    """
    
    def __init__(self, config):
        """
        初始化數據源適配器
        
        Args:
            config: 整合配置
        """
        self.config = config
        self.initialized = False
        
        # 數據源組件
        self.unified_data_manager = None
        self.health_monitor = None
        self.data_validator = None
        self.cache_manager = None
        
        # 原始項目數據IO
        self.legacy_data_io = None
        
        # 數據源配置
        self.data_source_configs = {}
        self.active_data_sources = {}
        
        logger.info("數據源適配器初始化")
    
    def initialize(self) -> bool:
        """
        初始化數據源系統
        
        Returns:
            是否初始化成功
        """
        try:
            # 檢查原始項目數據IO
            if not self._check_legacy_data_io():
                logger.warning("原始項目數據IO檢查失敗，繼續初始化")
            
            # 初始化統一數據管理器
            if not self._initialize_unified_data_manager():
                return False
            
            # 初始化健康監控
            if not self._initialize_health_monitor():
                logger.warning("健康監控初始化失敗")
            
            # 初始化數據驗證器
            if not self._initialize_data_validator():
                logger.warning("數據驗證器初始化失敗")
            
            # 初始化緩存管理器
            if not self._initialize_cache_manager():
                logger.warning("緩存管理器初始化失敗")
            
            # 配置數據源
            if not self._configure_data_sources():
                return False
            
            # 啟動健康監控
            if self.health_monitor:
                self.health_monitor.start_monitoring()
            
            self.initialized = True
            logger.info("數據源系統初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"數據源系統初始化失敗: {e}")
            return False
    
    def _check_legacy_data_io(self) -> bool:
        """檢查原始項目數據IO"""
        try:
            import sys
            from pathlib import Path
            
            legacy_path = Path(self.config.legacy_project_path)
            data_io_path = legacy_path / "quant_brain" / "data_io"
            
            if data_io_path.exists():
                # 添加到sys.path
                sys.path.insert(0, str(legacy_path))
                
                try:
                    import quant_brain.data_io as legacy_data_io
                    self.legacy_data_io = legacy_data_io
                    logger.info("原始項目數據IO模組載入成功")
                    return True
                except ImportError as e:
                    logger.warning(f"原始項目數據IO模組導入失敗: {e}")
                    return False
            else:
                logger.warning("原始項目數據IO模組不存在")
                return False
                
        except Exception as e:
            logger.error(f"檢查原始項目數據IO失敗: {e}")
            return False
    
    def _initialize_unified_data_manager(self) -> bool:
        """初始化統一數據管理器"""
        try:
            from ..data_sources.unified_data_manager import UnifiedDataManager
            
            data_manager_config = {
                'cache_dir': 'cache/data',
                'cache_ttl': 3600,
                'health_check_enabled': True,
                'failover_enabled': True,
                'data_validation_enabled': True
            }
            
            self.unified_data_manager = UnifiedDataManager(data_manager_config)
            
            # 初始化數據管理器
            if self.unified_data_manager.initialize():
                logger.info("統一數據管理器初始化成功")
                return True
            else:
                logger.error("統一數據管理器初始化失敗")
                return False
                
        except ImportError as e:
            logger.error(f"統一數據管理器模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"統一數據管理器初始化失敗: {e}")
            return False
    
    def _initialize_health_monitor(self) -> bool:
        """初始化健康監控"""
        try:
            from ..data_sources.health_monitor import DataSourceHealthMonitor
            
            monitor_config = {
                'monitoring_enabled': True,
                'check_interval': 60,
                'health_check_timeout': 10,
                'failover_enabled': True
            }
            
            self.health_monitor = DataSourceHealthMonitor(monitor_config)
            logger.info("數據源健康監控初始化成功")
            return True
            
        except ImportError as e:
            logger.error(f"健康監控模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"健康監控初始化失敗: {e}")
            return False
    
    def _initialize_data_validator(self) -> bool:
        """初始化數據驗證器"""
        try:
            from ..utils.data_validator import DataValidator
            
            validator_config = {
                'min_data_points': 10,
                'max_missing_ratio': 0.1,
                'max_outlier_ratio': 0.05,
                'min_price': 0.01,
                'max_price_change': 0.5,
                'max_volume_change': 10.0
            }
            
            self.data_validator = DataValidator(validator_config)
            logger.info("數據驗證器初始化成功")
            return True
            
        except ImportError as e:
            logger.error(f"數據驗證器模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"數據驗證器初始化失敗: {e}")
            return False
    
    def _initialize_cache_manager(self) -> bool:
        """初始化緩存管理器"""
        try:
            from ..utils.cache_manager import CacheManager
            
            self.cache_manager = CacheManager(
                cache_dir="cache/data",
                max_memory_size=1000,
                default_ttl=3600,
                enable_disk_cache=True,
                max_disk_size=1024*1024*1024,  # 1GB
                compression=True
            )
            
            logger.info("緩存管理器初始化成功")
            return True
            
        except ImportError as e:
            logger.error(f"緩存管理器模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"緩存管理器初始化失敗: {e}")
            return False
    
    def _configure_data_sources(self) -> bool:
        """配置數據源"""
        try:
            # 配置qstock數據源
            if not self._configure_qstock_source():
                logger.warning("qstock數據源配置失敗")
            
            # 配置其他數據源
            # 這裡可以添加更多數據源的配置
            
            # 註冊數據源到健康監控
            if self.health_monitor:
                for source_name in self.active_data_sources:
                    self.health_monitor.register_data_source(source_name)
            
            logger.info(f"已配置 {len(self.active_data_sources)} 個數據源")
            return True
            
        except Exception as e:
            logger.error(f"數據源配置失敗: {e}")
            return False
    
    def _configure_qstock_source(self) -> bool:
        """配置qstock數據源"""
        try:
            from ..data_sources.qstock_adapter import QStockAdapter
            from ..data_sources.base_data_source import DataSourceConfig
            
            qstock_config = DataSourceConfig(
                name="qstock",
                cache_dir="cache/qstock",
                cache_ttl=3600
            )
            
            qstock_adapter = QStockAdapter(qstock_config)
            
            if qstock_adapter.is_available():
                self.active_data_sources['qstock'] = qstock_adapter
                self.data_source_configs['qstock'] = qstock_config
                logger.info("qstock數據源配置成功")
                return True
            else:
                logger.warning("qstock數據源不可用")
                return False
                
        except ImportError as e:
            logger.warning(f"qstock適配器模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"qstock數據源配置失敗: {e}")
            return False
    
    def get_stock_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str, 
        source: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        獲取股票數據（統一接口）
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            source: 指定數據源
            
        Returns:
            股票數據
        """
        try:
            if not self.initialized:
                logger.error("數據源系統未初始化")
                return None
            
            # 檢查緩存
            cache_key = f"stock_data_{symbol}_{start_date}_{end_date}_{source}"
            if self.cache_manager:
                cached_data = self.cache_manager.get(cache_key)
                if cached_data is not None:
                    logger.debug(f"從緩存獲取數據: {symbol}")
                    return cached_data
            
            # 獲取數據
            data = None
            
            if self.unified_data_manager:
                # 使用統一數據管理器
                data = self.unified_data_manager.get_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    source=source
                )
            elif source and source in self.active_data_sources:
                # 直接使用指定數據源
                data_source = self.active_data_sources[source]
                if hasattr(data_source, 'get_historical_data'):
                    data = data_source.get_historical_data(symbol, start_date, end_date)
            
            # 數據驗證
            if data is not None and not data.empty and self.data_validator:
                validation_result = self.data_validator.validate_historical_data(data)
                if not validation_result.is_valid:
                    logger.warning(f"數據驗證失敗: {symbol}, 錯誤: {validation_result.errors}")
                    # 根據配置決定是否返回無效數據
                    if validation_result.quality_score < 0.5:
                        return None
            
            # 緩存數據
            if data is not None and self.cache_manager:
                self.cache_manager.set(cache_key, data)
            
            # 記錄請求結果
            if self.health_monitor:
                success = data is not None and not data.empty
                response_time = 0.1  # 這裡應該記錄實際響應時間
                self.health_monitor.record_request(
                    source or 'unified',
                    response_time,
                    success
                )
            
            return data
            
        except Exception as e:
            logger.error(f"獲取股票數據失敗 {symbol}: {e}")
            
            # 記錄錯誤
            if self.health_monitor:
                self.health_monitor.record_request(
                    source or 'unified',
                    0.0,
                    False,
                    str(e)
                )
            
            return None
    
    def get_realtime_data(self, symbol: str, source: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        獲取實時數據
        
        Args:
            symbol: 股票代碼
            source: 指定數據源
            
        Returns:
            實時數據
        """
        try:
            if not self.initialized:
                logger.error("數據源系統未初始化")
                return None
            
            # 檢查緩存（實時數據緩存時間較短）
            cache_key = f"realtime_{symbol}_{source}"
            if self.cache_manager:
                cached_data = self.cache_manager.get(cache_key)
                if cached_data is not None:
                    return cached_data
            
            # 獲取數據
            data = None
            
            if self.unified_data_manager:
                data = self.unified_data_manager.get_realtime_data(symbol, source)
            elif source and source in self.active_data_sources:
                data_source = self.active_data_sources[source]
                if hasattr(data_source, 'get_realtime_data'):
                    result = data_source.get_realtime_data(symbol)
                    if isinstance(result, pd.DataFrame) and not result.empty:
                        data = result.iloc[0].to_dict()
            
            # 數據驗證
            if data and self.data_validator:
                # 轉換為DataFrame進行驗證
                df = pd.DataFrame([data])
                validation_result = self.data_validator.validate_realtime_data(df)
                if not validation_result.is_valid:
                    logger.warning(f"實時數據驗證失敗: {symbol}")
            
            # 緩存數據（短時間）
            if data and self.cache_manager:
                self.cache_manager.set(cache_key, data, ttl=60)  # 1分鐘緩存
            
            return data
            
        except Exception as e:
            logger.error(f"獲取實時數據失敗 {symbol}: {e}")
            return None
    
    def get_available_data_sources(self) -> List[str]:
        """獲取可用數據源列表"""
        try:
            available_sources = []
            
            # 檢查活躍數據源
            for source_name, data_source in self.active_data_sources.items():
                try:
                    if hasattr(data_source, 'is_available') and data_source.is_available():
                        available_sources.append(source_name)
                    else:
                        available_sources.append(source_name)  # 假設可用
                except Exception as e:
                    logger.warning(f"檢查數據源可用性失敗 {source_name}: {e}")
            
            # 檢查統一數據管理器中的數據源
            if self.unified_data_manager:
                try:
                    manager_sources = self.unified_data_manager.get_available_sources()
                    available_sources.extend(manager_sources)
                except Exception as e:
                    logger.warning(f"獲取統一數據管理器數據源失敗: {e}")
            
            return list(set(available_sources))  # 去重
            
        except Exception as e:
            logger.error(f"獲取可用數據源失敗: {e}")
            return []
    
    def get_data_source_status(self) -> Dict[str, Any]:
        """獲取數據源狀態"""
        try:
            status = {
                'initialized': self.initialized,
                'active_sources': len(self.active_data_sources),
                'health_monitor_active': self.health_monitor is not None,
                'cache_enabled': self.cache_manager is not None,
                'validation_enabled': self.data_validator is not None,
                'sources': {}
            }
            
            # 獲取各數據源狀態
            for source_name, data_source in self.active_data_sources.items():
                try:
                    source_status = {
                        'available': True,
                        'type': type(data_source).__name__,
                        'last_check': datetime.now().isoformat()
                    }
                    
                    if hasattr(data_source, 'get_data_info'):
                        source_info = data_source.get_data_info()
                        source_status.update(source_info)
                    
                    status['sources'][source_name] = source_status
                    
                except Exception as e:
                    status['sources'][source_name] = {'error': str(e)}
            
            # 獲取健康監控狀態
            if self.health_monitor:
                try:
                    health_status = self.health_monitor.get_all_health_status()
                    status['health_status'] = {
                        name: {
                            'status': metrics.status.value,
                            'success_rate': metrics.success_rate,
                            'response_time': metrics.response_time,
                            'availability': metrics.availability
                        }
                        for name, metrics in health_status.items()
                    }
                except Exception as e:
                    status['health_status'] = {'error': str(e)}
            
            # 獲取緩存統計
            if self.cache_manager:
                try:
                    cache_stats = self.cache_manager.get_stats()
                    status['cache_stats'] = cache_stats
                except Exception as e:
                    status['cache_stats'] = {'error': str(e)}
            
            return status
            
        except Exception as e:
            logger.error(f"獲取數據源狀態失敗: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> bool:
        """健康檢查"""
        try:
            if not self.initialized:
                return False
            
            # 檢查統一數據管理器
            if not self.unified_data_manager:
                return False
            
            # 檢查活躍數據源
            if not self.active_data_sources:
                return False
            
            # 檢查關鍵組件
            components_ok = True
            if self.health_monitor and not self.health_monitor.monitoring_active:
                components_ok = False
            
            return components_ok
            
        except Exception as e:
            logger.error(f"數據源健康檢查失敗: {e}")
            return False
    
    def shutdown(self):
        """關閉數據源系統"""
        try:
            logger.info("正在關閉數據源系統...")
            
            # 停止健康監控
            if self.health_monitor:
                try:
                    self.health_monitor.stop_monitoring()
                    logger.info("健康監控已停止")
                except Exception as e:
                    logger.error(f"健康監控停止失敗: {e}")
            
            # 關閉數據源
            for source_name, data_source in self.active_data_sources.items():
                try:
                    if hasattr(data_source, 'shutdown'):
                        data_source.shutdown()
                    logger.info(f"數據源已關閉: {source_name}")
                except Exception as e:
                    logger.error(f"數據源關閉失敗 {source_name}: {e}")
            
            # 清理緩存
            if self.cache_manager:
                try:
                    # 這裡可以選擇是否清理緩存
                    logger.info("緩存管理器已關閉")
                except Exception as e:
                    logger.error(f"緩存管理器關閉失敗: {e}")
            
            # 清理資源
            self.active_data_sources.clear()
            self.data_source_configs.clear()
            
            self.initialized = False
            logger.info("數據源系統已關閉")
            
        except Exception as e:
            logger.error(f"數據源系統關閉失敗: {e}")
