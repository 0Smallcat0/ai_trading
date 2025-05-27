"""風險管理模組化結構單元測試

此測試文件驗證重構後的風險管理模組的功能完整性，包括：
- 模組導入測試
- 函數功能測試
- 錯誤處理測試
- API 向後兼容性測試

Author: AI Trading System
Version: 1.0.0
"""

import sys
import os
from pathlib import Path
import pytest
from unittest.mock import Mock, patch

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestRiskManagementModular:
    """風險管理模組化結構測試類"""

    def test_main_module_import(self):
        """測試主模組導入"""
        try:
            from src.ui.pages.risk_management import (
                show,
                get_module_info,
                show_risk_parameters,
                show_risk_indicators,
                show_risk_controls,
                show_risk_alerts,
            )

            assert callable(show), "show 函數應該可調用"
            assert callable(get_module_info), "get_module_info 函數應該可調用"
            assert callable(show_risk_parameters), "show_risk_parameters 函數應該可調用"
            assert callable(show_risk_indicators), "show_risk_indicators 函數應該可調用"
            assert callable(show_risk_controls), "show_risk_controls 函數應該可調用"
            assert callable(show_risk_alerts), "show_risk_alerts 函數應該可調用"

            logger.info("✅ 主模組導入測試通過")

        except ImportError as e:
            pytest.fail(f"主模組導入失敗: {e}")

    def test_utils_module_functions(self):
        """測試工具模組函數"""
        try:
            from src.ui.pages.risk_management.utils import (
                get_risk_management_service,
                get_default_risk_parameters,
                get_mock_risk_metrics,
                get_mock_risk_events,
                format_currency,
                format_percentage,
                validate_risk_parameters,
            )

            # 測試預設參數獲取
            default_params = get_default_risk_parameters()
            assert isinstance(default_params, dict), "預設參數應該是字典"
            assert "stop_loss_enabled" in default_params, "應包含停損設定"
            assert "max_position_size" in default_params, "應包含最大部位設定"

            # 測試模擬數據生成
            mock_metrics = get_mock_risk_metrics()
            assert isinstance(mock_metrics, dict), "模擬指標應該是字典"
            assert "portfolio_value" in mock_metrics, "應包含投資組合價值"

            mock_events = get_mock_risk_events()
            assert hasattr(mock_events, "shape"), "模擬事件應該是 DataFrame"
            assert mock_events.shape[0] > 0, "應包含事件記錄"

            # 測試格式化函數
            currency_str = format_currency(1234567.89)
            assert currency_str == "$1,234,568", f"貨幣格式化錯誤: {currency_str}"

            percentage_str = format_percentage(0.0525)
            assert percentage_str == "5.25%", f"百分比格式化錯誤: {percentage_str}"

            # 測試參數驗證
            valid_params = {
                "stop_loss_percent": 5.0,
                "max_position_size": 10.0,
                "max_portfolio_risk": 2.0,
            }
            errors = validate_risk_parameters(valid_params)
            assert len(errors) == 0, f"有效參數不應有錯誤: {errors}"

            invalid_params = {"stop_loss_percent": -1.0}
            errors = validate_risk_parameters(invalid_params)
            assert len(errors) > 0, "無效參數應該有錯誤"

            logger.info("✅ 工具模組函數測試通過")

        except Exception as e:
            pytest.fail(f"工具模組測試失敗: {e}")

    def test_parameters_module(self):
        """測試參數模組"""
        try:
            from src.ui.pages.risk_management.parameters import show_risk_parameters

            assert callable(show_risk_parameters), "參數設定函數應該可調用"

            logger.info("✅ 參數模組測試通過")

        except ImportError as e:
            pytest.fail(f"參數模組導入失敗: {e}")

    def test_indicators_module(self):
        """測試指標模組"""
        try:
            from src.ui.pages.risk_management.indicators import (
                show_risk_indicators,
                show_risk_summary,
            )

            assert callable(show_risk_indicators), "指標顯示函數應該可調用"
            assert callable(show_risk_summary), "指標摘要函數應該可調用"

            logger.info("✅ 指標模組測試通過")

        except ImportError as e:
            pytest.fail(f"指標模組導入失敗: {e}")

    def test_controls_module(self):
        """測試控制模組"""
        try:
            from src.ui.pages.risk_management.controls import show_risk_controls

            assert callable(show_risk_controls), "控制面板函數應該可調用"

            logger.info("✅ 控制模組測試通過")

        except ImportError as e:
            pytest.fail(f"控制模組導入失敗: {e}")

    def test_alerts_module(self):
        """測試警報模組"""
        try:
            from src.ui.pages.risk_management.alerts import (
                show_risk_alerts,
                get_alert_summary,
            )

            assert callable(show_risk_alerts), "警報顯示函數應該可調用"
            assert callable(get_alert_summary), "警報摘要函數應該可調用"

            # 測試警報摘要
            alert_summary = get_alert_summary()
            assert isinstance(alert_summary, dict), "警報摘要應該是字典"
            assert "total_alerts" in alert_summary, "應包含總警報數"

            logger.info("✅ 警報模組測試通過")

        except ImportError as e:
            pytest.fail(f"警報模組導入失敗: {e}")

    def test_module_info(self):
        """測試模組信息"""
        try:
            from src.ui.pages.risk_management import get_module_info

            info = get_module_info()
            assert isinstance(info, dict), "模組信息應該是字典"
            assert "version" in info, "應包含版本信息"
            assert "features" in info, "應包含功能列表"
            assert "submodules" in info, "應包含子模組列表"

            # 驗證子模組列表
            expected_submodules = [
                "parameters",
                "indicators",
                "controls",
                "alerts",
                "utils",
            ]
            for submodule in expected_submodules:
                assert submodule in info["submodules"], f"應包含子模組: {submodule}"

            logger.info("✅ 模組信息測試通過")

        except Exception as e:
            pytest.fail(f"模組信息測試失敗: {e}")

    def test_error_handling(self):
        """測試錯誤處理"""
        try:
            from src.ui.pages.risk_management.utils import validate_risk_parameters

            # 測試類型錯誤
            with pytest.raises(TypeError):
                validate_risk_parameters("not_a_dict")

            # 測試格式化函數的錯誤處理
            from src.ui.pages.risk_management.utils import format_percentage

            with pytest.raises(ValueError):
                format_percentage(0.05, -1)  # 負數小數位數

            logger.info("✅ 錯誤處理測試通過")

        except Exception as e:
            pytest.fail(f"錯誤處理測試失敗: {e}")

    @patch("streamlit.session_state", {})
    def test_backward_compatibility(self):
        """測試向後兼容性"""
        try:
            # 測試原始 API 仍然可用
            from src.ui.pages.risk_management import show as new_show

            # 確保函數可調用（不會拋出異常）
            assert callable(new_show), "新的 show 函數應該可調用"

            logger.info("✅ 向後兼容性測試通過")

        except Exception as e:
            pytest.fail(f"向後兼容性測試失敗: {e}")

    def test_file_structure(self):
        """測試文件結構完整性"""
        risk_management_dir = project_root / "src" / "ui" / "pages" / "risk_management"

        # 檢查目錄存在
        assert risk_management_dir.exists(), "風險管理目錄應該存在"

        # 檢查必要文件存在
        required_files = [
            "__init__.py",
            "parameters.py",
            "indicators.py",
            "controls.py",
            "alerts.py",
            "utils.py",
        ]

        for file_name in required_files:
            file_path = risk_management_dir / file_name
            assert file_path.exists(), f"文件應該存在: {file_name}"

            # 檢查文件大小（應該 ≤ 300 行）
            with open(file_path, "r", encoding="utf-8") as f:
                line_count = sum(1 for _ in f)
            assert line_count <= 300, f"文件 {file_name} 超過 300 行: {line_count} 行"

        logger.info("✅ 文件結構測試通過")


def test_integration():
    """集成測試"""
    try:
        # 測試完整的模組導入和基本功能
        from src.ui.pages.risk_management import show, get_module_info
        from src.ui.pages.risk_management.utils import get_default_risk_parameters

        # 獲取模組信息
        module_info = get_module_info()
        assert module_info["version"] == "1.0.0", "版本應該是 1.0.0"

        # 獲取預設參數
        default_params = get_default_risk_parameters()
        assert len(default_params) > 0, "應該有預設參數"

        logger.info("✅ 集成測試通過")

    except Exception as e:
        pytest.fail(f"集成測試失敗: {e}")


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v"])
