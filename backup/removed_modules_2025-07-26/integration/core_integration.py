# -*- coding: utf-8 -*-
"""
核心系統整合器

此模組提供統一的系統整合管理，協調所有增強功能與原始項目的整合。
作為整合層的核心組件，負責初始化、配置管理、功能路由和狀態監控。

主要功能：
- 統一的整合管理
- 功能模組初始化
- 配置管理和驗證
- 狀態監控和健康檢查
- 錯誤處理和恢復

整合策略：
- 適配器模式實現
- 依賴注入管理
- 事件驅動架構
- 插件化擴展
"""

import logging
import os
import sys
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import threading
import importlib
from pathlib import Path

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class IntegrationConfig:
    """整合配置數據類"""
    # 原始項目配置
    legacy_project_path: str = "ai_quant_trade-0.0.1"
    legacy_project_enabled: bool = True
    
    # 功能模組配置
    multi_agent_enabled: bool = True
    llm_strategy_enabled: bool = True
    reinforcement_learning_enabled: bool = True
    knowledge_system_enabled: bool = True
    data_sources_enabled: bool = True
    
    # 整合配置
    integration_mode: str = "full"  # full, partial, minimal
    compatibility_mode: bool = True
    auto_migration: bool = False
    
    # 性能配置
    max_concurrent_operations: int = 10
    timeout_seconds: int = 30
    retry_attempts: int = 3
    
    # 日誌配置
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # 監控配置
    health_check_interval: int = 60
    metrics_enabled: bool = True
    
    # 自定義配置
    custom_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrationStatus:
    """整合狀態數據類"""
    component_name: str
    status: str  # initializing, active, error, disabled
    last_update: datetime
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)


class SystemIntegrator:
    """
    系統整合器
    
    統一管理所有增強功能與原始項目的整合
    """
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        """
        初始化系統整合器
        
        Args:
            config: 整合配置
        """
        self.config = config or IntegrationConfig()
        
        # 整合狀態管理
        self.integration_status: Dict[str, IntegrationStatus] = {}
        self.adapters: Dict[str, Any] = {}
        self.initialized_components: List[str] = []
        
        # 線程安全
        self.lock = threading.RLock()
        
        # 事件處理
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # 健康檢查
        self.health_check_thread = None
        self.health_check_active = False
        
        # 初始化日誌
        self._setup_logging()
        
        logger.info("系統整合器初始化完成")
    
    def initialize(self) -> bool:
        """
        初始化整合系統
        
        Returns:
            是否初始化成功
        """
        try:
            logger.info("開始初始化系統整合...")
            
            # 檢查原始項目
            if not self._check_legacy_project():
                logger.error("原始項目檢查失敗")
                return False
            
            # 初始化核心組件
            if not self._initialize_core_components():
                logger.error("核心組件初始化失敗")
                return False
            
            # 初始化功能適配器
            if not self._initialize_feature_adapters():
                logger.error("功能適配器初始化失敗")
                return False
            
            # 啟動健康檢查
            if self.config.metrics_enabled:
                self._start_health_monitoring()
            
            # 觸發初始化完成事件
            self._trigger_event('integration_initialized')
            
            logger.info("系統整合初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"系統整合初始化失敗: {e}")
            return False
    
    def _check_legacy_project(self) -> bool:
        """檢查原始項目"""
        try:
            legacy_path = Path(self.config.legacy_project_path)
            
            if not legacy_path.exists():
                logger.error(f"原始項目路徑不存在: {legacy_path}")
                return False
            
            # 檢查關鍵目錄
            required_dirs = ['quant_brain', 'tools', 'docs']
            for dir_name in required_dirs:
                if not (legacy_path / dir_name).exists():
                    logger.warning(f"原始項目缺少目錄: {dir_name}")
            
            # 更新狀態
            self._update_status('legacy_project', 'active', "原始項目檢查通過")
            
            logger.info("原始項目檢查通過")
            return True
            
        except Exception as e:
            logger.error(f"原始項目檢查失敗: {e}")
            self._update_status('legacy_project', 'error', str(e))
            return False
    
    def _initialize_core_components(self) -> bool:
        """初始化核心組件"""
        try:
            # 初始化配置管理器
            if not self._initialize_config_manager():
                return False
            
            # 初始化原始項目適配器
            if not self._initialize_legacy_adapter():
                return False
            
            # 初始化接口橋樑
            if not self._initialize_interface_bridge():
                return False
            
            logger.info("核心組件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"核心組件初始化失敗: {e}")
            return False
    
    def _initialize_feature_adapters(self) -> bool:
        """初始化功能適配器"""
        try:
            adapters_config = {
                'multi_agent': self.config.multi_agent_enabled,
                'llm_strategy': self.config.llm_strategy_enabled,
                'reinforcement_learning': self.config.reinforcement_learning_enabled,
                'knowledge_system': self.config.knowledge_system_enabled,
                'data_sources': self.config.data_sources_enabled
            }
            
            for adapter_name, enabled in adapters_config.items():
                if enabled:
                    if self._initialize_adapter(adapter_name):
                        logger.info(f"{adapter_name} 適配器初始化成功")
                    else:
                        logger.warning(f"{adapter_name} 適配器初始化失敗")
            
            logger.info("功能適配器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"功能適配器初始化失敗: {e}")
            return False
    
    def _initialize_adapter(self, adapter_name: str) -> bool:
        """初始化單個適配器"""
        try:
            self._update_status(adapter_name, 'initializing', "正在初始化適配器")
            
            # 動態導入適配器
            adapter_module_map = {
                'multi_agent': 'agents_integration.MultiAgentSystemAdapter',
                'llm_strategy': 'llm_integration.LLMStrategyAdapter',
                'reinforcement_learning': 'rl_integration.ReinforcementLearningAdapter',
                'knowledge_system': 'knowledge_integration.KnowledgeSystemAdapter',
                'data_sources': 'data_integration.DataSourceAdapter'
            }
            
            if adapter_name not in adapter_module_map:
                logger.error(f"未知的適配器: {adapter_name}")
                return False
            
            module_path = adapter_module_map[adapter_name]
            module_name, class_name = module_path.rsplit('.', 1)
            
            try:
                module = importlib.import_module(f'.{module_name}', package='src.integration')
                adapter_class = getattr(module, class_name)
                
                # 創建適配器實例
                adapter_instance = adapter_class(self.config)
                
                # 初始化適配器
                if hasattr(adapter_instance, 'initialize'):
                    if adapter_instance.initialize():
                        self.adapters[adapter_name] = adapter_instance
                        self.initialized_components.append(adapter_name)
                        self._update_status(adapter_name, 'active', "適配器初始化成功")
                        return True
                    else:
                        self._update_status(adapter_name, 'error', "適配器初始化失敗")
                        return False
                else:
                    self.adapters[adapter_name] = adapter_instance
                    self.initialized_components.append(adapter_name)
                    self._update_status(adapter_name, 'active', "適配器創建成功")
                    return True
                    
            except ImportError as e:
                logger.warning(f"適配器模組導入失敗 {adapter_name}: {e}")
                self._update_status(adapter_name, 'disabled', f"模組不可用: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"適配器初始化失敗 {adapter_name}: {e}")
            self._update_status(adapter_name, 'error', str(e))
            return False
    
    def _initialize_config_manager(self) -> bool:
        """初始化配置管理器"""
        try:
            from .config_manager import IntegrationConfigManager
            self.config_manager = IntegrationConfigManager(self.config)
            self._update_status('config_manager', 'active', "配置管理器初始化成功")
            return True
        except Exception as e:
            logger.error(f"配置管理器初始化失敗: {e}")
            self._update_status('config_manager', 'error', str(e))
            return False
    
    def _initialize_legacy_adapter(self) -> bool:
        """初始化原始項目適配器"""
        try:
            from .legacy_adapter import LegacyProjectAdapter
            self.legacy_adapter = LegacyProjectAdapter(self.config)
            self._update_status('legacy_adapter', 'active', "原始項目適配器初始化成功")
            return True
        except Exception as e:
            logger.error(f"原始項目適配器初始化失敗: {e}")
            self._update_status('legacy_adapter', 'error', str(e))
            return False
    
    def _initialize_interface_bridge(self) -> bool:
        """初始化接口橋樑"""
        try:
            from .interface_bridge import InterfaceBridge
            self.interface_bridge = InterfaceBridge(self.config)
            self._update_status('interface_bridge', 'active', "接口橋樑初始化成功")
            return True
        except Exception as e:
            logger.error(f"接口橋樑初始化失敗: {e}")
            self._update_status('interface_bridge', 'error', str(e))
            return False
    
    def _update_status(self, component: str, status: str, message: str = ""):
        """更新組件狀態"""
        with self.lock:
            self.integration_status[component] = IntegrationStatus(
                component_name=component,
                status=status,
                last_update=datetime.now(),
                error_message=message if status == 'error' else None
            )
    
    def _setup_logging(self):
        """設置日誌"""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        if self.config.log_file:
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setLevel(log_level)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    
    def _start_health_monitoring(self):
        """啟動健康監控"""
        if self.health_check_active:
            return
        
        self.health_check_active = True
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
        logger.info("健康監控已啟動")
    
    def _health_check_loop(self):
        """健康檢查循環"""
        import time
        
        while self.health_check_active:
            try:
                self._perform_health_check()
                time.sleep(self.config.health_check_interval)
            except Exception as e:
                logger.error(f"健康檢查失敗: {e}")
                time.sleep(self.config.health_check_interval)
    
    def _perform_health_check(self):
        """執行健康檢查"""
        for component_name, adapter in self.adapters.items():
            try:
                if hasattr(adapter, 'health_check'):
                    is_healthy = adapter.health_check()
                    if is_healthy:
                        self._update_status(component_name, 'active', "健康檢查通過")
                    else:
                        self._update_status(component_name, 'error', "健康檢查失敗")
            except Exception as e:
                logger.error(f"組件健康檢查失敗 {component_name}: {e}")
                self._update_status(component_name, 'error', str(e))
    
    def _trigger_event(self, event_name: str, data: Any = None):
        """觸發事件"""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    handler(data)
                except Exception as e:
                    logger.error(f"事件處理器執行失敗 {event_name}: {e}")
    
    def register_event_handler(self, event_name: str, handler: Callable):
        """註冊事件處理器"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    def get_adapter(self, adapter_name: str) -> Optional[Any]:
        """獲取適配器實例"""
        return self.adapters.get(adapter_name)
    
    def get_integration_status(self) -> Dict[str, IntegrationStatus]:
        """獲取整合狀態"""
        with self.lock:
            return self.integration_status.copy()
    
    def shutdown(self):
        """關閉整合系統"""
        logger.info("正在關閉系統整合...")
        
        # 停止健康監控
        self.health_check_active = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
        
        # 關閉適配器
        for adapter_name, adapter in self.adapters.items():
            try:
                if hasattr(adapter, 'shutdown'):
                    adapter.shutdown()
                logger.info(f"適配器已關閉: {adapter_name}")
            except Exception as e:
                logger.error(f"適配器關閉失敗 {adapter_name}: {e}")
        
        # 觸發關閉事件
        self._trigger_event('integration_shutdown')
        
        logger.info("系統整合已關閉")
