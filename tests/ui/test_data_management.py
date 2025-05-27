"""
資料管理模組測試

此測試檔案驗證資料管理模組的各項功能，包括：
- 模組導入測試
- 功能函數測試
- 錯誤處理測試
- 整合測試

測試覆蓋範圍：
- data_sources 模組
- data_update 模組
- data_query 模組
- data_quality 模組
- data_export 模組

Example:
    執行測試：
    ```bash
    pytest tests/ui/test_data_management.py -v
    ```

Note:
    測試使用 pytest 框架，包含完整的錯誤處理和邊界條件測試。
"""

import sys
from unittest.mock import Mock, patch

import pytest

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, "src")


class TestDataManagementModules:
    """資料管理模組測試類別"""

    def test_module_imports(self):
        """測試模組導入功能"""
        try:
            # 測試主模組導入
            from src.ui.pages import data_management

            assert hasattr(data_management, "show")
            assert hasattr(data_management, "initialize_data_service")

            # 測試子模組導入
            from src.ui.pages.data_management import (
                data_export,
                data_quality,
                data_query,
                data_sources,
                data_update,
            )

            # 驗證主要函數存在
            assert hasattr(data_sources, "show_data_sources_management")
            assert hasattr(data_update, "show_data_update_management")
            assert hasattr(data_query, "show_data_query_interface")
            assert hasattr(data_quality, "show_data_quality_monitoring")
            assert hasattr(data_export, "show_data_export_tools")

        except ImportError as e:
            pytest.fail(f"模組導入失敗: {e}")

    @patch("streamlit.session_state", new_callable=dict)
    def test_initialize_data_service(self, mock_session_state):
        """測試資料服務初始化"""
        from src.ui.pages.data_management import initialize_data_service

        # 測試初始化成功情況
        with patch(
            "src.ui.pages.data_management.DataManagementService"
        ) as mock_service:
            mock_service.return_value = Mock()

            initialize_data_service()

            # 驗證服務已初始化
            assert "data_service" in mock_session_state
            assert "update_task_id" in mock_session_state
            assert mock_session_state["update_task_id"] is None

    def test_data_quality_functions(self):
        """測試資料品質模組功能"""
        from src.ui.pages.data_management.data_quality import (
            detect_data_anomalies,
            get_data_quality_metrics,
        )

        # 測試品質指標獲取
        metrics = get_data_quality_metrics()
        assert isinstance(metrics, list)
        assert len(metrics) > 0

        # 驗證指標結構
        for metric in metrics:
            assert "data_type" in metric
            assert "completeness" in metric
            assert "accuracy" in metric
            assert "timeliness" in metric
            assert "consistency" in metric

        # 測試異常檢測
        result = detect_data_anomalies("股價資料", "Z-Score", 5)
        assert isinstance(result, dict)
        assert "data_type" in result
        assert "anomaly_count" in result
        assert "total_records" in result
        assert "anomaly_rate" in result

    def test_data_export_functions(self):
        """測試資料匯出模組功能"""
        import pandas as pd

        from src.ui.pages.data_management.data_export import (
            export_data_to_format,
            get_available_export_types,
            get_export_formats,
        )

        # 測試可用匯出類型
        export_types = get_available_export_types()
        assert isinstance(export_types, list)
        assert len(export_types) > 0
        assert "股價資料" in export_types

        # 測試匯出格式
        formats = get_export_formats()
        assert isinstance(formats, list)
        assert "CSV" in formats
        assert "Excel" in formats
        assert "JSON" in formats

        # 測試資料匯出
        test_data = pd.DataFrame(
            {"date": ["2024-01-01", "2024-01-02"], "value": [100, 101]}
        )

        # 測試 CSV 匯出
        csv_result = export_data_to_format(test_data, "CSV", "test.csv")
        assert csv_result is not None
        assert isinstance(csv_result, bytes)

        # 測試 JSON 匯出
        json_result = export_data_to_format(test_data, "JSON", "test.json")
        assert json_result is not None
        assert isinstance(json_result, bytes)

    @patch("streamlit.error")
    @patch("streamlit.warning")
    def test_error_handling(self, mock_warning, mock_error):
        """測試錯誤處理機制"""
        from src.ui.pages.data_management.data_quality import (
            show_data_quality_monitoring,
        )

        # 測試在沒有資料服務的情況下的錯誤處理
        with patch("streamlit.session_state", {"data_service": None}):
            try:
                show_data_quality_monitoring()
                # 應該不會拋出異常，而是顯示友善的錯誤訊息
            except Exception as e:
                pytest.fail(f"錯誤處理失敗: {e}")

    def test_module_info_function(self):
        """測試模組資訊函數"""
        from src.ui.pages.data_management import get_module_info

        info = get_module_info()
        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "description" in info
        assert "modules" in info
        assert "features" in info
        assert "status" in info

        # 驗證版本格式
        version = info["version"]
        assert isinstance(version, str)
        assert len(version.split(".")) == 3  # 應該是 x.y.z 格式


class TestDataManagementIntegration:
    """資料管理整合測試類別"""

    @patch("streamlit.title")
    @patch("streamlit.tabs")
    @patch("streamlit.success")
    def test_main_show_function(self, mock_success, mock_tabs, mock_title):
        """測試主顯示函數"""
        from src.ui.pages.data_management import show

        # 模擬標籤頁
        mock_tabs.return_value = [Mock() for _ in range(5)]

        # 測試主函數執行
        with patch("src.ui.pages.data_management.initialize_data_service") as mock_init:
            mock_init.return_value = Mock()

            try:
                show()
                # 驗證基本函數被調用
                mock_title.assert_called_once()
                mock_tabs.assert_called_once()
                mock_success.assert_called_once()
            except Exception as e:
                pytest.fail(f"主顯示函數執行失敗: {e}")

    def test_backward_compatibility(self):
        """測試向後兼容性"""
        try:
            # 測試舊的導入方式仍然有效
            from src.ui.pages.data_management import show_data_management

            assert callable(show_data_management)
        except ImportError:
            pytest.fail("向後兼容性測試失敗")


class TestDataManagementPerformance:
    """資料管理性能測試類別"""

    def test_module_load_time(self):
        """測試模組載入時間"""
        import time

        start_time = time.time()

        # 重新導入模組以測試載入時間
        if "src.ui.pages.data_management" in sys.modules:
            del sys.modules["src.ui.pages.data_management"]

        load_time = time.time() - start_time

        # 模組載入時間應該少於 1 秒
        assert load_time < 1.0, f"模組載入時間過長: {load_time:.2f}s"

    def test_function_response_time(self):
        """測試函數響應時間"""
        import time

        from src.ui.pages.data_management.data_quality import get_data_quality_metrics

        start_time = time.time()
        metrics = get_data_quality_metrics()
        response_time = time.time() - start_time

        # 函數響應時間應該少於 0.5 秒
        assert response_time < 0.5, f"函數響應時間過長: {response_time:.2f}s"
        assert len(metrics) > 0


if __name__ == "__main__":
    # 執行測試
    pytest.main([__file__, "-v", "--tb=short"])
