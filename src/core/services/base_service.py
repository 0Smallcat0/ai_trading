"""
基礎服務類

定義所有服務的基礎接口和通用功能。
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum


class ServiceStatus(Enum):
    """服務狀態枚舉"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class BaseService(ABC):
    """基礎服務類
    
    所有服務都應該繼承此類，提供統一的接口和功能。
    
    Attributes:
        name: 服務名稱
        version: 服務版本
        status: 服務狀態
        logger: 日誌記錄器
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        """初始化基礎服務
        
        Args:
            name: 服務名稱
            version: 服務版本
        """
        self.name = name
        self.version = version
        self.status = ServiceStatus.INITIALIZING
        self.logger = logging.getLogger(f"service.{name}")
        self._start_time = None
        self._error_count = 0
        self._last_error = None
        
        # 初始化服務
        try:
            self._initialize()
            self.status = ServiceStatus.RUNNING
            self._start_time = time.time()
            self.logger.info(f"服務 {self.name} 初始化成功")
        except Exception as e:
            self.status = ServiceStatus.ERROR
            self._last_error = str(e)
            self.logger.error(f"服務 {self.name} 初始化失敗: {e}")
            raise
    
    @abstractmethod
    def _initialize(self) -> None:
        """初始化服務（子類實現）
        
        Raises:
            NotImplementedError: 子類必須實現此方法
        """
        pass
    
    def health_check(self) -> Dict[str, Any]:
        """健康檢查
        
        Returns:
            Dict[str, Any]: 健康狀態信息
        """
        try:
            # 執行具體的健康檢查
            health_data = self._health_check()
            
            return {
                "service": self.name,
                "status": self.status.value,
                "healthy": self.status == ServiceStatus.RUNNING,
                "uptime": time.time() - self._start_time if self._start_time else 0,
                "error_count": self._error_count,
                "last_error": self._last_error,
                "details": health_data
            }
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            self.logger.error(f"健康檢查失敗: {e}")
            
            return {
                "service": self.name,
                "status": ServiceStatus.ERROR.value,
                "healthy": False,
                "error": str(e)
            }
    
    def _health_check(self) -> Dict[str, Any]:
        """具體的健康檢查邏輯（子類可重寫）
        
        Returns:
            Dict[str, Any]: 健康檢查詳細信息
        """
        return {"message": "服務運行正常"}
    
    def get_status(self) -> Dict[str, Any]:
        """獲取服務狀態
        
        Returns:
            Dict[str, Any]: 服務狀態信息
        """
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "start_time": self._start_time,
            "uptime": time.time() - self._start_time if self._start_time else 0,
            "error_count": self._error_count,
            "last_error": self._last_error
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """獲取服務指標（子類可重寫）
        
        Returns:
            Dict[str, Any]: 服務指標
        """
        return {
            "requests_total": 0,
            "requests_per_second": 0,
            "average_response_time": 0,
            "error_rate": 0
        }
    
    def start(self) -> bool:
        """啟動服務
        
        Returns:
            bool: 是否成功啟動
        """
        try:
            if self.status == ServiceStatus.RUNNING:
                self.logger.warning(f"服務 {self.name} 已經在運行")
                return True
            
            self.status = ServiceStatus.INITIALIZING
            self._start()
            self.status = ServiceStatus.RUNNING
            self._start_time = time.time()
            
            self.logger.info(f"服務 {self.name} 啟動成功")
            return True
            
        except Exception as e:
            self.status = ServiceStatus.ERROR
            self._last_error = str(e)
            self._error_count += 1
            self.logger.error(f"服務 {self.name} 啟動失敗: {e}")
            return False
    
    def stop(self) -> bool:
        """停止服務
        
        Returns:
            bool: 是否成功停止
        """
        try:
            if self.status == ServiceStatus.STOPPED:
                self.logger.warning(f"服務 {self.name} 已經停止")
                return True
            
            self.status = ServiceStatus.STOPPING
            self._stop()
            self.status = ServiceStatus.STOPPED
            
            self.logger.info(f"服務 {self.name} 停止成功")
            return True
            
        except Exception as e:
            self.status = ServiceStatus.ERROR
            self._last_error = str(e)
            self._error_count += 1
            self.logger.error(f"服務 {self.name} 停止失敗: {e}")
            return False
    
    def restart(self) -> bool:
        """重啟服務
        
        Returns:
            bool: 是否成功重啟
        """
        self.logger.info(f"重啟服務 {self.name}")
        return self.stop() and self.start()
    
    def _start(self) -> None:
        """啟動服務的具體邏輯（子類可重寫）"""
        pass
    
    def _stop(self) -> None:
        """停止服務的具體邏輯（子類可重寫）"""
        pass
    
    def is_healthy(self) -> bool:
        """檢查服務是否健康
        
        Returns:
            bool: 服務是否健康
        """
        return self.status == ServiceStatus.RUNNING
    
    def is_running(self) -> bool:
        """檢查服務是否運行中
        
        Returns:
            bool: 服務是否運行中
        """
        return self.status == ServiceStatus.RUNNING
    
    def get_uptime(self) -> float:
        """獲取服務運行時間
        
        Returns:
            float: 運行時間（秒）
        """
        if self._start_time is None:
            return 0
        return time.time() - self._start_time
    
    def reset_error_count(self) -> None:
        """重置錯誤計數"""
        self._error_count = 0
        self._last_error = None
        self.logger.info(f"服務 {self.name} 錯誤計數已重置")
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Service({self.name}, {self.version}, {self.status.value})"
    
    def __repr__(self) -> str:
        """詳細字符串表示"""
        return (f"Service(name='{self.name}', version='{self.version}', "
                f"status='{self.status.value}', uptime={self.get_uptime():.1f}s)")


class MockService(BaseService):
    """模擬服務類（用於測試）"""
    
    def __init__(self, name: str = "mock_service", version: str = "1.0.0"):
        super().__init__(name, version)
    
    def _initialize(self) -> None:
        """初始化模擬服務"""
        self.logger.info("模擬服務初始化")
    
    def _health_check(self) -> Dict[str, Any]:
        """模擬健康檢查"""
        return {
            "message": "模擬服務運行正常",
            "mock_data": True
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """模擬指標"""
        return {
            "requests_total": 100,
            "requests_per_second": 10,
            "average_response_time": 0.1,
            "error_rate": 0.01
        }
