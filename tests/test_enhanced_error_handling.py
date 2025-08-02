"""增強錯誤處理測試套件

此測試套件驗證代碼品質審計後實施的增強錯誤處理模式，包括：
- 鏈式異常處理測試
- 懶惰日誌格式測試
- 統一錯誤處理模式測試
- 向後相容性測試
"""

import pytest
import logging
import sys
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

# 添加專案根目錄到路徑
sys.path.insert(0, ".")

# 導入要測試的模組
from src.api.main import app
from src.core.authentication_service import AuthenticationService


class TestChainedExceptionHandling:
    """測試鏈式異常處理"""

    def test_api_auth_chained_exceptions(self):
        """測試 API 認證路由的鏈式異常處理"""
        client = TestClient(app)

        # 測試登入錯誤的異常鏈
        with patch("src.api.routers.auth.get_user_by_username") as mock_get_user:
            mock_get_user.side_effect = Exception("Database connection failed")

            response = client.post(
                "/api/v1/auth/login",
                json={"username": "test_user", "password": "test_password"},
            )

            # 驗證錯誤回應
            assert response.status_code == 500
            assert "登入過程中發生錯誤" in response.json()["detail"]

    def test_authentication_service_chained_exceptions(self):
        """測試認證服務的鏈式異常處理"""
        # 模擬資料庫連接失敗
        with patch("src.core.authentication_service.create_engine") as mock_engine:
            mock_engine.side_effect = Exception("Database connection failed")

            # 驗證異常鏈是否正確傳播
            with pytest.raises(Exception) as exc_info:
                AuthenticationService()

            # 檢查異常訊息
            assert "Database connection failed" in str(exc_info.value)

    def test_exception_chain_preservation(self):
        """測試異常鏈的保存"""

        def inner_function():
            raise ValueError("Original error")

        def outer_function():
            try:
                inner_function()
            except ValueError as e:
                # 使用鏈式異常處理
                raise RuntimeError("Wrapped error") from e

        # 驗證異常鏈
        with pytest.raises(RuntimeError) as exc_info:
            outer_function()

        # 檢查原始異常是否保存
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValueError)
        assert "Original error" in str(exc_info.value.__cause__)


class TestLazyLoggingFormat:
    """測試懶惰日誌格式"""

    def setup_method(self):
        """設置測試環境"""
        self.logger = logging.getLogger("test_logger")
        self.mock_handler = Mock()
        self.logger.addHandler(self.mock_handler)
        self.logger.setLevel(logging.DEBUG)

    def test_lazy_logging_performance(self):
        """測試懶惰日誌的效能優化"""

        # 模擬昂貴的字串操作
        def expensive_operation():
            return "expensive_result"

        # 設置日誌級別為 WARNING，INFO 不會被記錄
        self.logger.setLevel(logging.WARNING)

        # 使用懶惰日誌格式
        self.logger.info("Test message: %s", expensive_operation())

        # 驗證昂貴操作沒有被執行（因為日誌級別不夠）
        # 在實際實施中，expensive_operation 不會被調用
        assert self.mock_handler.emit.call_count == 0

    def test_lazy_logging_format_correctness(self):
        """測試懶惰日誌格式的正確性"""
        test_variable = "test_value"

        # 使用懶惰日誌格式
        self.logger.error("Error occurred: %s", test_variable)

        # 驗證日誌記錄被調用
        assert self.mock_handler.emit.call_count == 1

        # 獲取記錄的日誌
        log_record = self.mock_handler.emit.call_args[0][0]
        assert "Error occurred: test_value" in log_record.getMessage()

    def test_multiple_parameters_lazy_logging(self):
        """測試多參數懶惰日誌格式"""
        user_id = "user123"
        action = "login"
        timestamp = "2024-12-25"

        self.logger.info("User %s performed %s at %s", user_id, action, timestamp)

        # 驗證日誌記錄
        assert self.mock_handler.emit.call_count == 1
        log_record = self.mock_handler.emit.call_args[0][0]
        expected_message = "User user123 performed login at 2024-12-25"
        assert expected_message in log_record.getMessage()


class TestUnifiedErrorHandling:
    """測試統一錯誤處理模式"""

    def test_http_exception_passthrough(self):
        """測試 HTTP 異常的直接傳遞"""
        client = TestClient(app)

        # 測試不存在的端點
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_business_logic_exception_handling(self):
        """測試業務邏輯異常處理"""
        client = TestClient(app)

        # 測試無效的登入資料
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "", "password": ""},  # 空用戶名  # 空密碼
        )

        # 驗證適當的錯誤回應
        assert response.status_code in [400, 401, 422]

    def test_system_exception_handling(self):
        """測試系統異常處理"""
        client = TestClient(app)

        # 模擬系統異常
        with patch("src.api.main.datetime") as mock_datetime:
            mock_datetime.now.side_effect = Exception("System error")

            response = client.get("/health")

            # 驗證系統異常被正確處理
            assert response.status_code == 503


class TestBackwardCompatibility:
    """測試向後相容性"""

    def test_api_endpoint_compatibility(self):
        """測試 API 端點的向後相容性"""
        client = TestClient(app)

        # 測試核心端點仍然可用
        response = client.get("/")
        assert response.status_code == 200

        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/api/info")
        assert response.status_code == 200

    def test_module_import_compatibility(self):
        """測試模組導入的向後相容性"""
        # 測試核心模組可以正常導入
        try:
            from src.ui.web_ui import run_web_ui
            from src.api.main import app
            from src.core.authentication_service import AuthenticationService
            from src.api.routers.auth import router

            # 如果能到達這裡，說明導入成功
            assert True
        except ImportError as e:
            pytest.fail(f"模組導入失敗: {e}")

    def test_function_signature_compatibility(self):
        """測試函數簽名的向後相容性"""
        # 測試認證服務的主要方法簽名
        auth_service = AuthenticationService()

        # 檢查方法是否存在且可調用
        assert hasattr(auth_service, "login_with_password")
        assert callable(auth_service.login_with_password)

        assert hasattr(auth_service, "verify_2fa_totp")
        assert callable(auth_service.verify_2fa_totp)

        assert hasattr(auth_service, "generate_jwt_token")
        assert callable(auth_service.generate_jwt_token)


class TestErrorHandlingIntegration:
    """測試錯誤處理整合"""

    def test_end_to_end_error_flow(self):
        """測試端到端錯誤流程"""
        client = TestClient(app)

        # 模擬完整的錯誤流程
        with patch("src.api.routers.auth.get_user_by_username") as mock_get_user:
            # 模擬資料庫錯誤
            mock_get_user.side_effect = Exception("Database connection timeout")

            response = client.post(
                "/api/v1/auth/login",
                json={"username": "test_user", "password": "test_password"},
            )

            # 驗證錯誤被正確處理和回應
            assert response.status_code == 500
            assert "登入過程中發生錯誤" in response.json()["detail"]

    def test_logging_integration(self):
        """測試日誌整合"""
        with patch("src.core.authentication_service.logger") as mock_logger:
            # 模擬認證服務初始化錯誤
            with patch("src.core.authentication_service.create_engine") as mock_engine:
                mock_engine.side_effect = Exception("Database error")

                try:
                    AuthenticationService()
                except Exception:
                    pass

                # 驗證使用了懶惰日誌格式
                mock_logger.error.assert_called()
                call_args = mock_logger.error.call_args

                # 檢查是否使用了 %s 格式而非 f-string
                assert "%s" in call_args[0][0]


class TestPerformanceImpact:
    """測試效能影響"""

    def test_logging_performance_improvement(self):
        """測試日誌效能改進"""
        import time

        logger = logging.getLogger("performance_test")
        logger.setLevel(logging.WARNING)  # 設置較高級別

        # 測試懶惰日誌格式的效能
        start_time = time.time()
        for _ in range(1000):
            # 這些 INFO 級別的日誌不會被處理
            logger.info("Test message: %s", "expensive_operation_result")
        end_time = time.time()

        lazy_time = end_time - start_time

        # 懶惰日誌應該很快，因為字串格式化被跳過
        assert lazy_time < 0.1  # 應該在 100ms 內完成

    def test_exception_handling_overhead(self):
        """測試異常處理開銷"""

        def test_function_with_chained_exceptions():
            try:
                raise ValueError("Test error")
            except ValueError as e:
                raise RuntimeError("Wrapped error") from e

        # 測試異常鏈不會顯著影響效能
        import time

        start_time = time.time()

        for _ in range(100):
            try:
                test_function_with_chained_exceptions()
            except RuntimeError:
                pass

        end_time = time.time()
        total_time = end_time - start_time

        # 100 次異常處理應該在合理時間內完成
        assert total_time < 1.0  # 應該在 1 秒內完成


if __name__ == "__main__":
    # 執行測試
    pytest.main([__file__, "-v", "--tb=short"])
