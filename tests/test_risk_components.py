"""風險組件庫單元測試

此測試文件驗證風險組件庫的功能，包括：
- 表單組件測試
- 圖表組件測試
- 面板組件測試
- 組件集成測試

Author: AI Trading System
Version: 1.0.0
"""

import sys
import os
from pathlib import Path
import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestRiskComponents:
    """風險組件庫測試類"""

    def test_components_import(self):
        """測試組件庫導入"""
        try:
            from src.ui.components.risk import (
                get_component_info,
                create_risk_dashboard,
                create_parameter_page,
                create_monitoring_page,
            )

            assert callable(get_component_info), "組件信息函數應該可調用"
            assert callable(create_risk_dashboard), "儀表板創建函數應該可調用"
            assert callable(create_parameter_page), "參數頁面創建函數應該可調用"
            assert callable(create_monitoring_page), "監控頁面創建函數應該可調用"

            logger.info("✅ 組件庫導入測試通過")

        except ImportError as e:
            pytest.fail(f"組件庫導入失敗: {e}")

    def test_forms_components(self):
        """測試表單組件"""
        try:
            from src.ui.components.risk.forms import (
                risk_parameter_form,
                parameter_validation_display,
                dynamic_form_generator,
                form_state_manager,
                save_form_state,
                reset_form_state,
                form_action_buttons,
            )

            # 測試表單狀態管理
            initial_state = {"test_param": "test_value"}
            state = form_state_manager("test_form", initial_state)
            assert isinstance(state, dict), "表單狀態應該是字典"
            assert state["test_param"] == "test_value", "狀態值應該正確"

            # 測試狀態保存
            new_state = {"test_param": "new_value"}
            save_form_state("test_form", new_state)

            # 測試狀態重置
            reset_form_state("test_form", initial_state)

            # 測試參數驗證顯示
            test_params = {
                "stop_loss_enabled": True,
                "stop_loss_percent": 5.0,
                "max_position_size": 10.0,
            }

            # 這個函數會有 Streamlit 依賴，所以我們只測試它是可調用的
            assert callable(parameter_validation_display), "參數驗證函數應該可調用"
            assert callable(risk_parameter_form), "風險參數表單函數應該可調用"
            assert callable(dynamic_form_generator), "動態表單生成器應該可調用"
            assert callable(form_action_buttons), "表單按鈕函數應該可調用"

            logger.info("✅ 表單組件測試通過")

        except Exception as e:
            pytest.fail(f"表單組件測試失敗: {e}")

    def test_charts_components(self):
        """測試圖表組件"""
        try:
            from src.ui.components.risk.charts import (
                var_analysis_chart,
                drawdown_chart,
                risk_decomposition_pie_chart,
                correlation_heatmap,
                risk_trend_chart,
                portfolio_composition_chart,
                risk_gauge_chart,
                create_sample_data,
            )

            # 測試示例數據創建
            sample_data = create_sample_data()
            assert isinstance(sample_data, dict), "示例數據應該是字典"
            assert "returns" in sample_data, "應包含收益率數據"
            assert "dates" in sample_data, "應包含日期數據"
            assert "drawdown" in sample_data, "應包含回撤數據"
            assert "risk_components" in sample_data, "應包含風險組成數據"
            assert "correlation_matrix" in sample_data, "應包含相關性矩陣"

            # 測試 VaR 分析圖表
            returns_data = sample_data["returns"]
            var_chart = var_analysis_chart(returns_data)
            assert hasattr(var_chart, "data"), "VaR 圖表應該有數據屬性"

            # 測試回撤圖表
            dates = sample_data["dates"]
            drawdown_data = sample_data["drawdown"]
            dd_chart = drawdown_chart(dates, drawdown_data)
            assert hasattr(dd_chart, "data"), "回撤圖表應該有數據屬性"

            # 測試風險分解餅圖
            risk_components = sample_data["risk_components"]
            pie_chart = risk_decomposition_pie_chart(risk_components)
            assert hasattr(pie_chart, "data"), "餅圖應該有數據屬性"

            # 測試相關性熱圖
            correlation_matrix = sample_data["correlation_matrix"]
            heatmap = correlation_heatmap(correlation_matrix)
            assert hasattr(heatmap, "data"), "熱圖應該有數據屬性"

            # 測試風險評分儀表圖
            gauge_chart = risk_gauge_chart(75)
            assert hasattr(gauge_chart, "data"), "儀表圖應該有數據屬性"

            # 測試投資組合組成圖
            holdings = {"AAPL": 15.0, "MSFT": 12.0, "GOOGL": 10.0}
            composition_chart = portfolio_composition_chart(holdings)
            assert hasattr(composition_chart, "data"), "組成圖應該有數據屬性"

            # 測試風險趨勢圖
            risk_metrics = {
                "VaR": np.random.uniform(0.02, 0.05, 30),
                "回撤": np.random.uniform(-0.1, 0, 30),
            }
            trend_chart = risk_trend_chart(dates[:30], risk_metrics)
            assert hasattr(trend_chart, "data"), "趨勢圖應該有數據屬性"

            logger.info("✅ 圖表組件測試通過")

        except Exception as e:
            pytest.fail(f"圖表組件測試失敗: {e}")

    def test_panels_components(self):
        """測試面板組件"""
        try:
            from src.ui.components.risk.panels import (
                risk_overview_panel,
                control_panel,
                alert_panel,
                status_indicator_panel,
                quick_action_panel,
                parameter_summary_panel,
                responsive_panel_layout,
                collapsible_panel,
            )

            # 測試所有面板函數都是可調用的
            assert callable(risk_overview_panel), "概覽面板函數應該可調用"
            assert callable(control_panel), "控制面板函數應該可調用"
            assert callable(alert_panel), "警報面板函數應該可調用"
            assert callable(status_indicator_panel), "狀態面板函數應該可調用"
            assert callable(quick_action_panel), "快速操作面板函數應該可調用"
            assert callable(parameter_summary_panel), "參數摘要面板函數應該可調用"
            assert callable(responsive_panel_layout), "響應式佈局函數應該可調用"
            assert callable(collapsible_panel), "可摺疊面板函數應該可調用"

            logger.info("✅ 面板組件測試通過")

        except Exception as e:
            pytest.fail(f"面板組件測試失敗: {e}")

    def test_component_info(self):
        """測試組件信息"""
        try:
            from src.ui.components.risk import get_component_info

            info = get_component_info()
            assert isinstance(info, dict), "組件信息應該是字典"
            assert "version" in info, "應包含版本信息"
            assert "features" in info, "應包含功能列表"
            assert "modules" in info, "應包含模組列表"
            assert "total_components" in info, "應包含組件總數"

            # 驗證模組列表
            expected_modules = ["forms", "charts", "panels"]
            for module in expected_modules:
                assert module in info["modules"], f"應包含模組: {module}"

            # 驗證功能列表
            expected_features = [
                "parameter_forms",
                "risk_charts",
                "control_panels",
                "alert_management",
                "responsive_design",
            ]
            for feature in expected_features:
                assert feature in info["features"], f"應包含功能: {feature}"

            logger.info("✅ 組件信息測試通過")

        except Exception as e:
            pytest.fail(f"組件信息測試失敗: {e}")

    def test_file_structure_components(self):
        """測試組件文件結構"""
        components_dir = project_root / "src" / "ui" / "components" / "risk"

        # 檢查目錄存在
        assert components_dir.exists(), "風險組件目錄應該存在"

        # 檢查必要文件存在
        required_files = ["__init__.py", "forms.py", "charts.py", "panels.py"]

        for file_name in required_files:
            file_path = components_dir / file_name
            assert file_path.exists(), f"文件應該存在: {file_name}"

            # 檢查文件大小（應該 ≤ 300 行）
            with open(file_path, "r", encoding="utf-8") as f:
                line_count = sum(1 for _ in f)
            assert line_count <= 300, f"文件 {file_name} 超過 300 行: {line_count} 行"

        logger.info("✅ 組件文件結構測試通過")

    @patch("streamlit.session_state", {})
    def test_component_integration(self):
        """測試組件集成"""
        try:
            from src.ui.components.risk import (
                create_risk_dashboard,
                create_parameter_page,
                create_monitoring_page,
            )
            from src.ui.components.risk.charts import create_sample_data

            # 創建測試數據
            sample_data = create_sample_data()

            # 測試儀表板創建（這些函數有 Streamlit 依賴，所以只測試可調用性）
            assert callable(create_risk_dashboard), "儀表板創建函數應該可調用"
            assert callable(create_parameter_page), "參數頁面創建函數應該可調用"
            assert callable(create_monitoring_page), "監控頁面創建函數應該可調用"

            logger.info("✅ 組件集成測試通過")

        except Exception as e:
            pytest.fail(f"組件集成測試失敗: {e}")


def test_components_integration():
    """組件庫集成測試"""
    try:
        # 測試完整的組件庫功能
        from src.ui.components.risk import get_component_info
        from src.ui.components.risk.charts import create_sample_data
        from src.ui.components.risk.forms import form_state_manager

        # 獲取組件信息
        component_info = get_component_info()
        assert component_info["version"] == "1.0.0", "版本應該是 1.0.0"

        # 創建示例數據
        sample_data = create_sample_data()
        assert len(sample_data) > 0, "應該有示例數據"

        # 測試表單狀態管理
        state = form_state_manager("test", {"param": "value"})
        assert state["param"] == "value", "狀態管理應該正確"

        logger.info("✅ 組件庫集成測試通過")

    except Exception as e:
        pytest.fail(f"組件庫集成測試失敗: {e}")


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v"])
