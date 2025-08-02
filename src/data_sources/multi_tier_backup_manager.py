# -*- coding: utf-8 -*-
"""
多層備援機制管理器

此模組實現數據源驗證報告改進建議中的多層備援機制，
為關鍵數據建立備援註冊表，實施優先級排序和自動切換邏輯。

主要功能：
- 多層備援數據源管理
- 優先級排序和自動切換
- 智能故障檢測和恢復
- 數據源健康監控
- 統一故障轉移接口

Example:
    基本使用：
    ```python
    from src.data_sources.multi_tier_backup_manager import MultiTierBackupManager
    
    manager = MultiTierBackupManager()
    data = manager.get_data_with_fallback('技術面', 'yahoo_adjusted_price', symbol='2330.TW')
    ```

Note:
    此模組專門解決數據源驗證報告中提到的數據源不穩定問題，
    實現自動切換到可靠來源（如Yahoo Finance API）的機制。
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict

import pandas as pd

# 設定日誌
logger = logging.getLogger(__name__)


class DataSourceStatus(Enum):
    """數據源狀態枚舉"""
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"
    MAINTENANCE = "maintenance"


class FailoverStrategy(Enum):
    """故障轉移策略枚舉"""
    IMMEDIATE = "immediate"  # 立即切換
    RETRY_THEN_SWITCH = "retry_then_switch"  # 重試後切換
    CIRCUIT_BREAKER = "circuit_breaker"  # 熔斷器模式


@dataclass
class DataSourceConfig:
    """數據源配置"""
    name: str
    priority: int  # 優先級（數字越小優先級越高）
    crawler_class: str
    method_name: str
    success_rate_threshold: float = 0.8  # 成功率閾值
    response_time_threshold: float = 30.0  # 響應時間閾值（秒）
    max_retries: int = 3
    retry_delay: float = 2.0
    circuit_breaker_threshold: int = 5  # 熔斷器閾值
    circuit_breaker_timeout: int = 300  # 熔斷器超時（秒）
    health_check_interval: int = 60  # 健康檢查間隔（秒）
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataSourceMetrics:
    """數據源指標"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    consecutive_failures: int = 0
    status: DataSourceStatus = DataSourceStatus.ACTIVE
    circuit_breaker_open_until: Optional[datetime] = None


class MultiTierBackupManager:
    """
    多層備援機制管理器
    
    提供數據源的多層備援、自動故障轉移和健康監控功能。
    """
    
    def __init__(self):
        """初始化多層備援管理器"""
        self.backup_registry: Dict[str, Dict[str, List[DataSourceConfig]]] = defaultdict(lambda: defaultdict(list))
        self.metrics: Dict[str, DataSourceMetrics] = {}
        self.lock = threading.RLock()
        self.health_check_thread = None
        self.is_running = False
        
        # 初始化備援配置
        self._initialize_backup_configs()
        
    def _initialize_backup_configs(self) -> None:
        """初始化備援配置"""
        # 技術面數據備援配置
        self.register_backup_source(
            category='技術面',
            data_type='股價數據',
            config=DataSourceConfig(
                name='yahoo_finance_primary',
                priority=1,
                crawler_class='VerifiedCrawler',
                method_name='crawl_yahoo_adjusted_price',
                success_rate_threshold=0.95,
                metadata={'source': 'Yahoo Finance API', 'reliability': 'high'}
            )
        )
        
        self.register_backup_source(
            category='技術面',
            data_type='股價數據',
            config=DataSourceConfig(
                name='twse_api_backup',
                priority=2,
                crawler_class='VerifiedCrawler',
                method_name='crawl_twse_backtest_index',
                success_rate_threshold=0.85,
                metadata={'source': 'TWSE OpenAPI', 'reliability': 'medium'}
            )
        )
        
        # 基本面數據備援配置
        self.register_backup_source(
            category='基本面',
            data_type='企業資訊',
            config=DataSourceConfig(
                name='gov_platform_primary',
                priority=1,
                crawler_class='VerifiedCrawler',
                method_name='crawl_gov_company_info',
                success_rate_threshold=0.8,
                metadata={'source': '政府開放平台', 'reliability': 'medium'}
            )
        )
        
        self.register_backup_source(
            category='基本面',
            data_type='企業資訊',
            config=DataSourceConfig(
                name='finmind_backup',
                priority=2,
                crawler_class='VerifiedCrawler',
                method_name='crawl_finmind_financial_data',
                success_rate_threshold=0.7,
                metadata={'source': 'FinMind API', 'reliability': 'low'}
            )
        )
        
        # 籌碼面數據備援配置
        self.register_backup_source(
            category='籌碼面',
            data_type='券商交易',
            config=DataSourceConfig(
                name='twse_broker_primary',
                priority=1,
                crawler_class='VerifiedCrawler',
                method_name='crawl_twse_broker_trading',
                success_rate_threshold=0.9,
                metadata={'source': 'TWSE JSON', 'reliability': 'high'}
            )
        )
        
        self.register_backup_source(
            category='籌碼面',
            data_type='外資持股',
            config=DataSourceConfig(
                name='twse_foreign_primary',
                priority=1,
                crawler_class='VerifiedCrawler',
                method_name='crawl_twse_foreign_holding',
                success_rate_threshold=0.9,
                metadata={'source': 'TWSE JSON', 'reliability': 'high'}
            )
        )
        
        logger.info("✅ 備援配置初始化完成")
        
    def register_backup_source(self, category: str, data_type: str, config: DataSourceConfig) -> None:
        """
        註冊備援數據源
        
        Args:
            category: 數據分類（如'技術面'、'基本面'）
            data_type: 數據類型（如'股價數據'、'企業資訊'）
            config: 數據源配置
        """
        with self.lock:
            self.backup_registry[category][data_type].append(config)
            # 按優先級排序
            self.backup_registry[category][data_type].sort(key=lambda x: x.priority)
            
            # 初始化指標
            source_key = f"{category}_{data_type}_{config.name}"
            if source_key not in self.metrics:
                self.metrics[source_key] = DataSourceMetrics()
                
            logger.info(f"註冊備援數據源: {category}/{data_type}/{config.name} (優先級: {config.priority})")
            
    def get_data_with_fallback(self, category: str, data_type: str, **kwargs) -> pd.DataFrame:
        """
        使用故障轉移機制獲取數據
        
        Args:
            category: 數據分類
            data_type: 數據類型
            **kwargs: 傳遞給爬蟲方法的參數
            
        Returns:
            pd.DataFrame: 獲取的數據
        """
        if category not in self.backup_registry or data_type not in self.backup_registry[category]:
            logger.warning(f"未找到備援配置: {category}/{data_type}")
            return pd.DataFrame()
            
        sources = self.backup_registry[category][data_type]
        
        for config in sources:
            source_key = f"{category}_{data_type}_{config.name}"
            metrics = self.metrics[source_key]
            
            # 檢查熔斷器狀態
            if self._is_circuit_breaker_open(metrics, config):
                logger.warning(f"熔斷器開啟，跳過數據源: {config.name}")
                continue
                
            # 嘗試獲取數據
            result = self._fetch_data_from_source(config, metrics, **kwargs)
            
            if not result.empty:
                logger.info(f"✅ 成功從 {config.name} 獲取數據: {len(result)} 筆記錄")
                self._update_success_metrics(metrics)
                return result
            else:
                logger.warning(f"⚠️ 數據源 {config.name} 返回空數據")
                self._update_failure_metrics(metrics, config)
                
        logger.error(f"❌ 所有備援數據源均失敗: {category}/{data_type}")
        return pd.DataFrame()
        
    def _fetch_data_from_source(self, config: DataSourceConfig, metrics: DataSourceMetrics, **kwargs) -> pd.DataFrame:
        """
        從指定數據源獲取數據
        
        Args:
            config: 數據源配置
            metrics: 數據源指標
            **kwargs: 參數
            
        Returns:
            pd.DataFrame: 獲取的數據
        """
        start_time = time.time()
        
        try:
            # 動態導入和調用
            if config.crawler_class == 'VerifiedCrawler':
                from .verified_crawler import VerifiedCrawler
                crawler = VerifiedCrawler()
            elif config.crawler_class == 'ComprehensiveCrawler':
                from .comprehensive_crawler import ComprehensiveCrawler
                crawler = ComprehensiveCrawler()
            else:
                logger.error(f"未知的爬蟲類別: {config.crawler_class}")
                return pd.DataFrame()
                
            method = getattr(crawler, config.method_name)
            
            # 執行重試邏輯
            for attempt in range(config.max_retries):
                try:
                    result = method(**kwargs)
                    
                    # 更新響應時間
                    response_time = time.time() - start_time
                    metrics.avg_response_time = (metrics.avg_response_time * metrics.total_requests + response_time) / (metrics.total_requests + 1)
                    
                    if not result.empty:
                        return result
                        
                except Exception as e:
                    logger.warning(f"嘗試 {attempt + 1}/{config.max_retries} 失敗: {e}")
                    if attempt < config.max_retries - 1:
                        time.sleep(config.retry_delay)
                        
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"數據源 {config.name} 執行失敗: {e}")
            return pd.DataFrame()
            
    def _is_circuit_breaker_open(self, metrics: DataSourceMetrics, config: DataSourceConfig) -> bool:
        """
        檢查熔斷器是否開啟
        
        Args:
            metrics: 數據源指標
            config: 數據源配置
            
        Returns:
            bool: 熔斷器是否開啟
        """
        # 檢查熔斷器超時
        if metrics.circuit_breaker_open_until:
            if datetime.now() < metrics.circuit_breaker_open_until:
                return True
            else:
                # 重置熔斷器
                metrics.circuit_breaker_open_until = None
                metrics.consecutive_failures = 0
                metrics.status = DataSourceStatus.ACTIVE
                logger.info(f"熔斷器重置: {config.name}")
                
        # 檢查是否需要開啟熔斷器
        if metrics.consecutive_failures >= config.circuit_breaker_threshold:
            metrics.circuit_breaker_open_until = datetime.now() + timedelta(seconds=config.circuit_breaker_timeout)
            metrics.status = DataSourceStatus.FAILED
            logger.warning(f"熔斷器開啟: {config.name} (連續失敗 {metrics.consecutive_failures} 次)")
            return True
            
        return False
        
    def _update_success_metrics(self, metrics: DataSourceMetrics) -> None:
        """更新成功指標"""
        with self.lock:
            metrics.total_requests += 1
            metrics.successful_requests += 1
            metrics.last_success_time = datetime.now()
            metrics.consecutive_failures = 0
            
            # 更新狀態
            success_rate = metrics.successful_requests / metrics.total_requests
            if success_rate >= 0.9:
                metrics.status = DataSourceStatus.ACTIVE
            elif success_rate >= 0.7:
                metrics.status = DataSourceStatus.DEGRADED
            else:
                metrics.status = DataSourceStatus.FAILED
                
    def _update_failure_metrics(self, metrics: DataSourceMetrics, config: DataSourceConfig) -> None:
        """更新失敗指標"""
        with self.lock:
            metrics.total_requests += 1
            metrics.failed_requests += 1
            metrics.last_failure_time = datetime.now()
            metrics.consecutive_failures += 1
            
            # 更新狀態
            success_rate = metrics.successful_requests / metrics.total_requests if metrics.total_requests > 0 else 0
            if success_rate < 0.5:
                metrics.status = DataSourceStatus.FAILED
            elif success_rate < 0.8:
                metrics.status = DataSourceStatus.DEGRADED
                
    def get_health_report(self) -> Dict[str, Any]:
        """
        獲取健康報告
        
        Returns:
            Dict[str, Any]: 健康報告
        """
        with self.lock:
            report = {
                'timestamp': datetime.now().isoformat(),
                'total_sources': len(self.metrics),
                'sources_by_status': defaultdict(int),
                'sources_detail': {}
            }
            
            for source_key, metrics in self.metrics.items():
                status = metrics.status.value
                report['sources_by_status'][status] += 1
                
                success_rate = metrics.successful_requests / metrics.total_requests if metrics.total_requests > 0 else 0
                
                report['sources_detail'][source_key] = {
                    'status': status,
                    'success_rate': round(success_rate, 3),
                    'total_requests': metrics.total_requests,
                    'avg_response_time': round(metrics.avg_response_time, 2),
                    'consecutive_failures': metrics.consecutive_failures,
                    'last_success': metrics.last_success_time.isoformat() if metrics.last_success_time else None,
                    'last_failure': metrics.last_failure_time.isoformat() if metrics.last_failure_time else None
                }
                
            return dict(report)
            
    def start_health_monitoring(self) -> None:
        """啟動健康監控"""
        if self.is_running:
            logger.warning("健康監控已在運行中")
            return
            
        self.is_running = True
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
        logger.info("✅ 健康監控已啟動")
        
    def stop_health_monitoring(self) -> None:
        """停止健康監控"""
        self.is_running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
        logger.info("✅ 健康監控已停止")
        
    def _health_check_loop(self) -> None:
        """健康檢查循環"""
        while self.is_running:
            try:
                self._perform_health_checks()
                time.sleep(60)  # 每分鐘檢查一次
            except Exception as e:
                logger.error(f"健康檢查失敗: {e}")
                time.sleep(60)
                
    def _perform_health_checks(self) -> None:
        """執行健康檢查"""
        logger.debug("執行健康檢查...")
        
        # 這裡可以實現主動健康檢查邏輯
        # 例如：定期測試數據源可用性、清理過期指標等
        
        with self.lock:
            for source_key, metrics in self.metrics.items():
                # 如果長時間沒有請求，重置一些指標
                if metrics.last_success_time and (datetime.now() - metrics.last_success_time).days > 7:
                    metrics.consecutive_failures = 0
                    if metrics.status == DataSourceStatus.FAILED:
                        metrics.status = DataSourceStatus.DEGRADED
