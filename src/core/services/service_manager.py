"""
服務管理器模組

服務管理器職責分工：
- ServiceManager: 通用服務管理器 (本檔案)
- PortfolioService: 投資組合服務管理 (src/services/portfolio_service/__init__.py)
- MockBackendServices: 模擬後端服務管理 (src/ui/mock_backend_services.py)
詳見：docs/開發者指南/服務管理器使用指南.md

提供統一的服務管理功能，包括：
- 服務生命週期管理
- 服務健康監控
- 服務配置管理
- 服務依賴管理
"""

import logging
import threading
import time
from typing import Dict, List, Any, Optional, Type

from .base_service import BaseService, ServiceStatus
from .service_registry import ServiceRegistry


class ServiceManager:
    """服務管理器
    
    統一管理系統中的所有服務，提供服務的註冊、發現、
    生命週期管理和健康監控功能。
    
    Attributes:
        registry: 服務註冊器
        logger: 日誌記錄器
    """
    
    def __init__(self):
        """初始化服務管理器"""
        self.registry = ServiceRegistry()
        self.logger = logging.getLogger("service.manager")
        self._monitoring_thread = None
        self._monitoring_enabled = False
        self._monitoring_interval = 30  # 秒
        self._lock = threading.RLock()
        
        # 初始化核心服務
        self._initialize_core_services()
        
        self.logger.info("服務管理器已初始化")
    
    def _initialize_core_services(self) -> None:
        """初始化核心服務"""
        try:
            # 嘗試註冊現有的核心服務
            from ..auth_service import AuthenticationService
            
            # 註冊認證服務
            auth_service = AuthenticationService()
            self.registry.register(auth_service)
            
            # 嘗試註冊回測服務
            try:
                from ..backtest import BacktestService
                backtest_service = BacktestService()
                self.registry.register(backtest_service)
            except ImportError:
                self.logger.warning("回測服務不可用")
            
            # 嘗試註冊其他核心服務
            self._register_additional_services()
            
        except Exception as e:
            self.logger.error(f"初始化核心服務失敗: {e}")
    
    def _register_additional_services(self) -> None:
        """註冊額外的服務"""
        # 這裡可以添加其他服務的註冊邏輯
        pass
    
    def register_service(self, service: BaseService) -> bool:
        """註冊服務
        
        Args:
            service: 要註冊的服務
            
        Returns:
            bool: 是否成功註冊
        """
        return self.registry.register(service)
    
    def register_service_type(self, service_type: Type[BaseService], name: Optional[str] = None, **kwargs) -> Optional[BaseService]:
        """註冊服務類型
        
        Args:
            service_type: 服務類型
            name: 服務名稱
            **kwargs: 服務構造參數
            
        Returns:
            Optional[BaseService]: 註冊的服務實例
        """
        try:
            return self.registry.register_type(service_type, name, **kwargs)
        except Exception as e:
            self.logger.error(f"註冊服務類型失敗: {e}")
            return None
    
    def unregister_service(self, service_name: str) -> bool:
        """解除註冊服務
        
        Args:
            service_name: 服務名稱
            
        Returns:
            bool: 是否成功解除註冊
        """
        return self.registry.unregister(service_name)
    
    def get_service(self, service_name: str) -> Optional[BaseService]:
        """獲取服務
        
        Args:
            service_name: 服務名稱
            
        Returns:
            Optional[BaseService]: 服務實例
        """
        return self.registry.get_service(service_name)
    
    def list_services(self) -> List[str]:
        """列出所有服務
        
        Returns:
            List[str]: 服務名稱列表
        """
        return self.registry.list_services()
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """獲取服務狀態
        
        Args:
            service_name: 服務名稱
            
        Returns:
            Optional[Dict[str, Any]]: 服務狀態
        """
        return self.registry.get_service_status(service_name)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """獲取所有服務狀態
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有服務狀態
        """
        status = {}
        for service_name in self.list_services():
            status[service_name] = self.get_service_status(service_name)
        return status
    
    def get_service_health(self, service_name: str) -> Optional[Dict[str, Any]]:
        """獲取服務健康狀態
        
        Args:
            service_name: 服務名稱
            
        Returns:
            Optional[Dict[str, Any]]: 服務健康狀態
        """
        return self.registry.get_service_health(service_name)
    
    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """獲取所有服務健康狀態
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有服務健康狀態
        """
        return self.registry.get_all_health()
    
    def start_service(self, service_name: str) -> bool:
        """啟動服務
        
        Args:
            service_name: 服務名稱
            
        Returns:
            bool: 是否成功啟動
        """
        return self.registry.start_service(service_name)
    
    def stop_service(self, service_name: str) -> bool:
        """停止服務
        
        Args:
            service_name: 服務名稱
            
        Returns:
            bool: 是否成功停止
        """
        return self.registry.stop_service(service_name)
    
    def restart_service(self, service_name: str) -> bool:
        """重啟服務
        
        Args:
            service_name: 服務名稱
            
        Returns:
            bool: 是否成功重啟
        """
        return self.registry.restart_service(service_name)
    
    def start_all_services(self) -> Dict[str, bool]:
        """啟動所有服務
        
        Returns:
            Dict[str, bool]: 服務啟動結果
        """
        return self.registry.start_all()
    
    def stop_all_services(self) -> Dict[str, bool]:
        """停止所有服務
        
        Returns:
            Dict[str, bool]: 服務停止結果
        """
        return self.registry.stop_all()
    
    def add_dependency(self, service_name: str, dependency_name: str) -> bool:
        """添加服務依賴
        
        Args:
            service_name: 服務名稱
            dependency_name: 依賴的服務名稱
            
        Returns:
            bool: 是否成功添加依賴
        """
        return self.registry.add_dependency(service_name, dependency_name)
    
    def remove_dependency(self, service_name: str, dependency_name: str) -> bool:
        """移除服務依賴
        
        Args:
            service_name: 服務名稱
            dependency_name: 依賴的服務名稱
            
        Returns:
            bool: 是否成功移除依賴
        """
        return self.registry.remove_dependency(service_name, dependency_name)
    
    def start_monitoring(self, interval: int = 30) -> None:
        """啟動服務監控
        
        Args:
            interval: 監控間隔（秒）
        """
        with self._lock:
            if self._monitoring_enabled:
                self.logger.warning("服務監控已經啟動")
                return
            
            self._monitoring_interval = interval
            self._monitoring_enabled = True
            self._monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self._monitoring_thread.start()
            
            self.logger.info(f"服務監控已啟動，間隔 {interval} 秒")
    
    def stop_monitoring(self) -> None:
        """停止服務監控"""
        with self._lock:
            if not self._monitoring_enabled:
                self.logger.warning("服務監控未啟動")
                return
            
            self._monitoring_enabled = False
            if self._monitoring_thread:
                self._monitoring_thread.join(timeout=5)
            
            self.logger.info("服務監控已停止")
    
    def _monitoring_loop(self) -> None:
        """監控循環"""
        while self._monitoring_enabled:
            try:
                self._check_services_health()
                time.sleep(self._monitoring_interval)
            except Exception as e:
                self.logger.error(f"服務監控錯誤: {e}")
                time.sleep(5)  # 錯誤時短暫等待
    
    def _check_services_health(self) -> None:
        """檢查所有服務健康狀態"""
        health_status = self.get_all_health()
        
        for service_name, health in health_status.items():
            if not health.get("healthy", False):
                self.logger.warning(f"服務 {service_name} 不健康: {health}")
                
                # 嘗試重啟不健康的服務
                service = self.get_service(service_name)
                if service and service.status == ServiceStatus.ERROR:
                    self.logger.info(f"嘗試重啟服務 {service_name}")
                    self.restart_service(service_name)
    
    def get_system_status(self) -> Dict[str, Any]:
        """獲取系統整體狀態
        
        Returns:
            Dict[str, Any]: 系統狀態
        """
        services = self.list_services()
        health_status = self.get_all_health()
        
        healthy_count = sum(1 for h in health_status.values() if h.get("healthy", False))
        total_count = len(services)
        
        return {
            "total_services": total_count,
            "healthy_services": healthy_count,
            "unhealthy_services": total_count - healthy_count,
            "system_healthy": healthy_count == total_count,
            "monitoring_enabled": self._monitoring_enabled,
            "monitoring_interval": self._monitoring_interval,
            "services": health_status
        }
    
    def shutdown(self) -> None:
        """關閉服務管理器"""
        self.logger.info("正在關閉服務管理器...")
        
        # 停止監控
        self.stop_monitoring()
        
        # 停止所有服務
        self.stop_all_services()
        
        self.logger.info("服務管理器已關閉")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown()
