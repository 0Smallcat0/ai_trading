"""
服務管理系統測試

測試統一服務管理架構的功能。
"""

import unittest
import time
from unittest.mock import Mock, patch

from src.core.services import (
    BaseService,
    ServiceRegistry,
    ServiceManager,
    UIServiceClient,
    get_service_manager,
    get_ui_client
)
from src.core.services.base_service import ServiceStatus, MockService


class TestServiceManagement(unittest.TestCase):
    """服務管理系統測試類"""
    
    def setUp(self):
        """測試前準備"""
        self.registry = ServiceRegistry()
        self.manager = ServiceManager()
        self.ui_client = UIServiceClient(self.manager)
    
    def test_base_service(self):
        """測試基礎服務類"""
        # 創建模擬服務
        service = MockService("test_service", "1.0.0")
        
        # 驗證基本屬性
        self.assertEqual(service.name, "test_service")
        self.assertEqual(service.version, "1.0.0")
        self.assertEqual(service.status, ServiceStatus.RUNNING)
        
        # 測試健康檢查
        health = service.health_check()
        self.assertIsInstance(health, dict)
        self.assertTrue(health["healthy"])
        self.assertEqual(health["service"], "test_service")
        
        # 測試狀態獲取
        status = service.get_status()
        self.assertIsInstance(status, dict)
        self.assertEqual(status["name"], "test_service")
        self.assertEqual(status["version"], "1.0.0")
        
        # 測試指標獲取
        metrics = service.get_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn("requests_total", metrics)
        
        # 測試服務控制
        self.assertTrue(service.is_running())
        self.assertTrue(service.is_healthy())
        
        # 測試停止和啟動
        self.assertTrue(service.stop())
        self.assertEqual(service.status, ServiceStatus.STOPPED)
        self.assertFalse(service.is_running())
        
        self.assertTrue(service.start())
        self.assertEqual(service.status, ServiceStatus.RUNNING)
        self.assertTrue(service.is_running())
        
        # 測試重啟
        self.assertTrue(service.restart())
        self.assertTrue(service.is_running())
    
    def test_service_registry(self):
        """測試服務註冊器"""
        # 創建測試服務
        service1 = MockService("service1", "1.0.0")
        service2 = MockService("service2", "1.0.0")
        
        # 測試服務註冊
        self.assertTrue(self.registry.register(service1))
        self.assertTrue(self.registry.register(service2))
        
        # 測試重複註冊
        self.assertFalse(self.registry.register(service1))
        
        # 測試服務獲取
        retrieved_service = self.registry.get_service("service1")
        self.assertEqual(retrieved_service, service1)
        
        # 測試服務列表
        services = self.registry.list_services()
        self.assertIn("service1", services)
        self.assertIn("service2", services)
        
        # 測試服務狀態
        status = self.registry.get_service_status("service1")
        self.assertIsInstance(status, dict)
        self.assertEqual(status["name"], "service1")
        
        # 測試健康檢查
        health = self.registry.get_service_health("service1")
        self.assertIsInstance(health, dict)
        self.assertTrue(health["healthy"])
        
        # 測試所有健康檢查
        all_health = self.registry.get_all_health()
        self.assertIsInstance(all_health, dict)
        self.assertIn("service1", all_health)
        self.assertIn("service2", all_health)
        
        # 測試服務控制
        self.assertTrue(self.registry.start_service("service1"))
        self.assertTrue(self.registry.stop_service("service1"))
        self.assertTrue(self.registry.restart_service("service1"))
        
        # 測試服務解除註冊
        self.assertTrue(self.registry.unregister("service1"))
        self.assertIsNone(self.registry.get_service("service1"))
        
        # 測試不存在的服務
        self.assertIsNone(self.registry.get_service("nonexistent"))
        self.assertFalse(self.registry.start_service("nonexistent"))
    
    def test_service_dependencies(self):
        """測試服務依賴管理"""
        # 創建測試服務
        service_a = MockService("service_a", "1.0.0")
        service_b = MockService("service_b", "1.0.0")
        service_c = MockService("service_c", "1.0.0")
        
        # 註冊服務
        self.registry.register(service_a)
        self.registry.register(service_b)
        self.registry.register(service_c)
        
        # 測試添加依賴
        self.assertTrue(self.registry.add_dependency("service_b", "service_a"))
        self.assertTrue(self.registry.add_dependency("service_c", "service_b"))
        
        # 測試獲取依賴
        deps_b = self.registry.get_dependencies("service_b")
        self.assertIn("service_a", deps_b)
        
        # 測試獲取所有依賴
        all_deps_c = self.registry.get_all_dependencies("service_c")
        self.assertIn("service_a", all_deps_c)
        self.assertIn("service_b", all_deps_c)
        
        # 測試循環依賴檢測
        self.assertFalse(self.registry.add_dependency("service_a", "service_c"))
        
        # 測試移除依賴
        self.assertTrue(self.registry.remove_dependency("service_b", "service_a"))
        deps_b_after = self.registry.get_dependencies("service_b")
        self.assertNotIn("service_a", deps_b_after)
    
    def test_service_manager(self):
        """測試服務管理器"""
        # 測試服務註冊
        service = MockService("test_service", "1.0.0")
        self.assertTrue(self.manager.register_service(service))
        
        # 測試服務獲取
        retrieved_service = self.manager.get_service("test_service")
        self.assertEqual(retrieved_service, service)
        
        # 測試服務列表
        services = self.manager.list_services()
        self.assertIn("test_service", services)
        
        # 測試系統狀態
        system_status = self.manager.get_system_status()
        self.assertIsInstance(system_status, dict)
        self.assertIn("total_services", system_status)
        self.assertIn("healthy_services", system_status)
        
        # 測試服務控制
        self.assertTrue(self.manager.start_service("test_service"))
        self.assertTrue(self.manager.stop_service("test_service"))
        self.assertTrue(self.manager.restart_service("test_service"))
        
        # 測試解除註冊
        self.assertTrue(self.manager.unregister_service("test_service"))
        self.assertIsNone(self.manager.get_service("test_service"))
    
    def test_ui_service_client(self):
        """測試 UI 服務客戶端"""
        # 測試系統狀態獲取
        system_status = self.ui_client.get_system_status()
        self.assertIsInstance(system_status, dict)
        
        # 測試可用服務列表
        services = self.ui_client.list_available_services()
        self.assertIsInstance(services, list)
        
        # 測試可用功能
        features = self.ui_client.get_available_features()
        self.assertIsInstance(features, dict)
        self.assertIn("authentication", features)
        self.assertIn("backtest", features)
        
        # 測試服務可用性檢查
        # 由於沒有實際的服務，大部分應該返回 False
        self.assertFalse(self.ui_client.is_service_available("NonexistentService"))
    
    def test_global_service_manager(self):
        """測試全局服務管理器"""
        # 測試獲取全局服務管理器
        manager1 = get_service_manager()
        manager2 = get_service_manager()
        
        # 應該返回同一個實例
        self.assertEqual(manager1, manager2)
        
        # 測試獲取 UI 客戶端
        client1 = get_ui_client()
        client2 = get_ui_client()
        
        # 應該返回同一個實例
        self.assertEqual(client1, client2)
    
    def test_service_type_registration(self):
        """測試服務類型註冊"""
        # 測試註冊服務類型
        service = self.registry.register_type(MockService, "typed_service", version="2.0.0")
        
        self.assertIsInstance(service, MockService)
        self.assertEqual(service.name, "typed_service")
        self.assertEqual(service.version, "2.0.0")
        
        # 驗證服務已註冊
        retrieved_service = self.registry.get_service("typed_service")
        self.assertEqual(retrieved_service, service)
    
    def test_service_monitoring(self):
        """測試服務監控"""
        # 創建測試服務
        service = MockService("monitored_service", "1.0.0")
        self.manager.register_service(service)
        
        # 啟動監控（短間隔用於測試）
        self.manager.start_monitoring(interval=1)
        
        # 等待一小段時間讓監控運行
        time.sleep(0.1)
        
        # 停止監控
        self.manager.stop_monitoring()
        
        # 驗證監控狀態
        system_status = self.manager.get_system_status()
        self.assertFalse(system_status["monitoring_enabled"])
    
    def test_error_handling(self):
        """測試錯誤處理"""
        # 測試不存在的服務
        self.assertIsNone(self.ui_client.get_backtest_status("nonexistent_id"))
        self.assertEqual(self.ui_client.list_backtests(), [])
        
        # 測試服務不可用時的行為
        self.assertFalse(self.ui_client.authenticate_user("user", "pass"))
        self.assertIsNone(self.ui_client.start_backtest({}))
        self.assertIsNone(self.ui_client.get_risk_metrics())
    
    def tearDown(self):
        """測試後清理"""
        # 停止所有服務
        if hasattr(self, 'manager'):
            self.manager.shutdown()


if __name__ == '__main__':
    unittest.main()
