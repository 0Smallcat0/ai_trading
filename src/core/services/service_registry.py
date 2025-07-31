"""
服務註冊器模組

提供服務註冊和發現功能，支援：
- 服務註冊和解除註冊
- 服務查詢和發現
- 服務依賴管理
- 服務生命週期管理
"""

import logging
import threading
from typing import Dict, List, Any, Optional, Type, Set

from .base_service import BaseService, ServiceStatus


class ServiceRegistry:
    """服務註冊器
    
    管理系統中所有服務的註冊和發現。
    
    Attributes:
        services: 註冊的服務字典
        logger: 日誌記錄器
    """
    
    def __init__(self):
        """初始化服務註冊器"""
        self.services: Dict[str, BaseService] = {}
        self.logger = logging.getLogger("service.registry")
        self._lock = threading.RLock()
        self._dependencies: Dict[str, Set[str]] = {}  # 服務依賴關係
        self._service_types: Dict[str, Type[BaseService]] = {}  # 服務類型
        
        self.logger.info("服務註冊器已初始化")
    
    def register(self, service: BaseService) -> bool:
        """註冊服務
        
        Args:
            service: 要註冊的服務
            
        Returns:
            bool: 是否成功註冊
            
        Raises:
            ValueError: 當服務名稱已存在時
        """
        with self._lock:
            service_name = service.name
            
            if service_name in self.services:
                self.logger.warning(f"服務 {service_name} 已經註冊")
                return False
            
            self.services[service_name] = service
            self._service_types[service_name] = type(service)
            self.logger.info(f"服務 {service_name} 註冊成功")
            return True
    
    def register_type(self, service_type: Type[BaseService], name: Optional[str] = None, **kwargs) -> BaseService:
        """註冊服務類型並實例化
        
        Args:
            service_type: 服務類型
            name: 服務名稱（可選）
            **kwargs: 傳遞給服務構造函數的參數
            
        Returns:
            BaseService: 實例化的服務
            
        Raises:
            ValueError: 當服務名稱已存在時
        """
        with self._lock:
            # 如果沒有指定名稱，使用類名
            if name is None:
                name = service_type.__name__
            
            if name in self.services:
                self.logger.warning(f"服務 {name} 已經註冊")
                return self.services[name]
            
            # 實例化服務
            service = service_type(name=name, **kwargs)
            
            # 註冊服務
            self.services[name] = service
            self._service_types[name] = service_type
            self.logger.info(f"服務類型 {service_type.__name__} 註冊為 {name}")
            return service
    
    def unregister(self, service_name: str) -> bool:
        """解除註冊服務
        
        Args:
            service_name: 服務名稱
            
        Returns:
            bool: 是否成功解除註冊
        """
        with self._lock:
            if service_name not in self.services:
                self.logger.warning(f"服務 {service_name} 未註冊")
                return False
            
            # 檢查依賴關係
            dependent_services = self._get_dependent_services(service_name)
            if dependent_services:
                self.logger.error(f"無法解除註冊服務 {service_name}，以下服務依賴它: {dependent_services}")
                return False
            
            # 停止服務
            service = self.services[service_name]
            if service.is_running():
                service.stop()
            
            # 解除註冊
            del self.services[service_name]
            if service_name in self._service_types:
                del self._service_types[service_name]
            if service_name in self._dependencies:
                del self._dependencies[service_name]
            
            # 清理其他服務的依賴
            for deps in self._dependencies.values():
                if service_name in deps:
                    deps.remove(service_name)
            
            self.logger.info(f"服務 {service_name} 解除註冊成功")
            return True
    
    def get_service(self, service_name: str) -> Optional[BaseService]:
        """獲取服務
        
        Args:
            service_name: 服務名稱
            
        Returns:
            Optional[BaseService]: 服務實例，如果不存在則返回 None
        """
        return self.services.get(service_name)
    
    def get_services(self) -> Dict[str, BaseService]:
        """獲取所有服務
        
        Returns:
            Dict[str, BaseService]: 服務字典
        """
        return self.services.copy()
    
    def list_services(self) -> List[str]:
        """列出所有服務名稱
        
        Returns:
            List[str]: 服務名稱列表
        """
        return list(self.services.keys())
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """獲取服務狀態
        
        Args:
            service_name: 服務名稱
            
        Returns:
            Optional[Dict[str, Any]]: 服務狀態，如果不存在則返回 None
        """
        service = self.get_service(service_name)
        if service is None:
            return None
        return service.get_status()
    
    def get_service_health(self, service_name: str) -> Optional[Dict[str, Any]]:
        """獲取服務健康狀態
        
        Args:
            service_name: 服務名稱
            
        Returns:
            Optional[Dict[str, Any]]: 服務健康狀態，如果不存在則返回 None
        """
        service = self.get_service(service_name)
        if service is None:
            return None
        return service.health_check()
    
    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """獲取所有服務的健康狀態
        
        Returns:
            Dict[str, Dict[str, Any]]: 服務健康狀態字典
        """
        health = {}
        for name, service in self.services.items():
            health[name] = service.health_check()
        return health
    
    def start_service(self, service_name: str) -> bool:
        """啟動服務
        
        Args:
            service_name: 服務名稱
            
        Returns:
            bool: 是否成功啟動
        """
        service = self.get_service(service_name)
        if service is None:
            self.logger.warning(f"服務 {service_name} 未註冊")
            return False
        return service.start()
    
    def stop_service(self, service_name: str) -> bool:
        """停止服務
        
        Args:
            service_name: 服務名稱
            
        Returns:
            bool: 是否成功停止
        """
        service = self.get_service(service_name)
        if service is None:
            self.logger.warning(f"服務 {service_name} 未註冊")
            return False
        return service.stop()
    
    def restart_service(self, service_name: str) -> bool:
        """重啟服務
        
        Args:
            service_name: 服務名稱
            
        Returns:
            bool: 是否成功重啟
        """
        service = self.get_service(service_name)
        if service is None:
            self.logger.warning(f"服務 {service_name} 未註冊")
            return False
        return service.restart()
    
    def start_all(self) -> Dict[str, bool]:
        """啟動所有服務
        
        Returns:
            Dict[str, bool]: 服務啟動結果
        """
        results = {}
        # 按照依賴順序啟動
        for name in self._get_startup_order():
            results[name] = self.start_service(name)
        return results
    
    def stop_all(self) -> Dict[str, bool]:
        """停止所有服務
        
        Returns:
            Dict[str, bool]: 服務停止結果
        """
        results = {}
        # 按照依賴順序的反向停止
        for name in reversed(self._get_startup_order()):
            results[name] = self.stop_service(name)
        return results
    
    def add_dependency(self, service_name: str, dependency_name: str) -> bool:
        """添加服務依賴
        
        Args:
            service_name: 服務名稱
            dependency_name: 依賴的服務名稱
            
        Returns:
            bool: 是否成功添加依賴
            
        Raises:
            ValueError: 當服務不存在時
            ValueError: 當依賴關係形成循環時
        """
        with self._lock:
            if service_name not in self.services:
                self.logger.error(f"服務 {service_name} 未註冊")
                return False
            
            if dependency_name not in self.services:
                self.logger.error(f"依賴服務 {dependency_name} 未註冊")
                return False
            
            # 初始化依賴集合
            if service_name not in self._dependencies:
                self._dependencies[service_name] = set()
            
            # 檢查循環依賴
            if self._would_create_cycle(service_name, dependency_name):
                self.logger.error(f"添加依賴 {service_name} -> {dependency_name} 會形成循環依賴")
                return False
            
            # 添加依賴
            self._dependencies[service_name].add(dependency_name)
            self.logger.info(f"添加依賴 {service_name} -> {dependency_name}")
            return True
    
    def remove_dependency(self, service_name: str, dependency_name: str) -> bool:
        """移除服務依賴
        
        Args:
            service_name: 服務名稱
            dependency_name: 依賴的服務名稱
            
        Returns:
            bool: 是否成功移除依賴
        """
        with self._lock:
            if service_name not in self._dependencies:
                return False
            
            if dependency_name not in self._dependencies[service_name]:
                return False
            
            self._dependencies[service_name].remove(dependency_name)
            self.logger.info(f"移除依賴 {service_name} -> {dependency_name}")
            return True
    
    def get_dependencies(self, service_name: str) -> Set[str]:
        """獲取服務的直接依賴
        
        Args:
            service_name: 服務名稱
            
        Returns:
            Set[str]: 依賴的服務名稱集合
        """
        return self._dependencies.get(service_name, set()).copy()
    
    def get_all_dependencies(self, service_name: str) -> Set[str]:
        """獲取服務的所有依賴（包括間接依賴）
        
        Args:
            service_name: 服務名稱
            
        Returns:
            Set[str]: 所有依賴的服務名稱集合
        """
        result = set()
        self._collect_dependencies(service_name, result)
        return result
    
    def _collect_dependencies(self, service_name: str, result: Set[str]) -> None:
        """收集服務的所有依賴
        
        Args:
            service_name: 服務名稱
            result: 結果集合
        """
        direct_deps = self.get_dependencies(service_name)
        for dep in direct_deps:
            if dep not in result:
                result.add(dep)
                self._collect_dependencies(dep, result)
    
    def _get_dependent_services(self, service_name: str) -> List[str]:
        """獲取依賴於指定服務的所有服務
        
        Args:
            service_name: 服務名稱
            
        Returns:
            List[str]: 依賴於該服務的服務名稱列表
        """
        dependent_services = []
        for name, deps in self._dependencies.items():
            if service_name in deps:
                dependent_services.append(name)
        return dependent_services
    
    def _would_create_cycle(self, service_name: str, dependency_name: str) -> bool:
        """檢查添加依賴是否會形成循環
        
        Args:
            service_name: 服務名稱
            dependency_name: 依賴的服務名稱
            
        Returns:
            bool: 是否會形成循環
        """
        # 如果依賴服務依賴於當前服務，則會形成循環
        if service_name == dependency_name:
            return True
        
        # 檢查依賴服務的所有依賴
        deps = self.get_all_dependencies(dependency_name)
        return service_name in deps
    
    def _get_startup_order(self) -> List[str]:
        """獲取服務啟動順序
        
        Returns:
            List[str]: 服務啟動順序列表
        """
        # 使用拓撲排序
        result = []
        visited = set()
        temp = set()
        
        def visit(node):
            if node in temp:
                raise ValueError(f"檢測到循環依賴: {node}")
            if node in visited:
                return
            
            temp.add(node)
            for dep in self.get_dependencies(node):
                visit(dep)
            temp.remove(node)
            visited.add(node)
            result.append(node)
        
        for service in self.services:
            if service not in visited:
                visit(service)
        
        return result
