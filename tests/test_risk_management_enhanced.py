"""增強版風險管理模組單元測試

此測試文件驗證增強版風險管理模組的功能，包括：
- 響應式設計功能
- 增強版參數設定
- 數據服務層
- 智能功能測試

Author: AI Trading System
Version: 1.0.0
"""

import sys
import os
from pathlib import Path
import pytest
from unittest.mock import Mock, patch
import json

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

# 設置日誌
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestRiskManagementEnhanced:
    """增強版風險管理模組測試類"""

    def test_enhanced_module_import(self):
        """測試增強版模組導入"""
        try:
            from src.ui.pages.risk_management_enhanced import (
                show,
                get_enhanced_module_info,
                show_enhanced_parameters,
            )
            
            assert callable(show), "增強版 show 函數應該可調用"
            assert callable(get_enhanced_module_info), "增強版模組信息函數應該可調用"
            assert callable(show_enhanced_parameters), "增強版參數函數應該可調用"
            
            logger.info("✅ 增強版模組導入測試通過")
            
        except ImportError as e:
            pytest.fail(f"增強版模組導入失敗: {e}")

    def test_data_services_module(self):
        """測試數據服務模組"""
        try:
            from src.ui.pages.risk_management_enhanced.data_services import (
                load_risk_parameters,
                save_risk_parameters,
                load_risk_indicators,
                load_control_status,
                load_risk_alerts,
                export_risk_parameters,
                import_risk_parameters,
                calculate_risk_score,
                get_risk_level,
                format_currency,
                format_percentage,
                validate_parameters,
            )
            
            # 測試參數載入
            params = load_risk_parameters()
            assert isinstance(params, dict), "載入的參數應該是字典"
            assert len(params) > 0, "應該有參數內容"
            
            # 測試參數保存
            test_params = {"test_param": "test_value"}
            result = save_risk_parameters(test_params)
            assert isinstance(result, bool), "保存結果應該是布林值"
            
            # 測試風險指標載入
            indicators = load_risk_indicators()
            assert isinstance(indicators, dict), "風險指標應該是字典"
            assert "portfolio_value" in indicators, "應包含投資組合價值"
            
            # 測試控制狀態載入
            control_status = load_control_status()
            assert isinstance(control_status, dict), "控制狀態應該是字典"
            assert "master_switch" in control_status, "應包含主開關狀態"
            
            # 測試警報載入
            alerts = load_risk_alerts()
            assert isinstance(alerts, list), "警報應該是列表"
            
            # 測試參數匯出/匯入
            export_data = export_risk_parameters(test_params)
            assert isinstance(export_data, str), "匯出數據應該是字符串"
            
            imported_params = import_risk_parameters(export_data)
            assert isinstance(imported_params, dict), "匯入參數應該是字典"
            assert imported_params["test_param"] == "test_value", "匯入的參數應該正確"
            
            # 測試風險評分計算
            test_indicators = {
                "current_drawdown": -5.0,
                "var_95_1day": 20000,
                "portfolio_value": 1000000,
                "volatility": 15.0,
                "largest_position_weight": 12.0
            }
            risk_score = calculate_risk_score(test_indicators)
            assert isinstance(risk_score, int), "風險評分應該是整數"
            assert 0 <= risk_score <= 100, "風險評分應該在 0-100 之間"
            
            # 測試風險等級
            risk_level, risk_color = get_risk_level(risk_score)
            assert isinstance(risk_level, str), "風險等級應該是字符串"
            assert isinstance(risk_color, str), "風險顏色應該是字符串"
            
            # 測試格式化函數
            currency_str = format_currency(1234567.89)
            assert currency_str == "$1,234,568", f"貨幣格式化錯誤: {currency_str}"
            
            percentage_str = format_percentage(0.0525)
            assert percentage_str == "5.25%", f"百分比格式化錯誤: {percentage_str}"
            
            # 測試參數驗證
            valid_params = {
                "stop_loss_enabled": True,
                "stop_loss_percent": 5.0,
                "max_position_size": 10.0
            }
            errors = validate_parameters(valid_params)
            assert isinstance(errors, list), "驗證結果應該是列表"
            
            logger.info("✅ 數據服務模組測試通過")
            
        except Exception as e:
            pytest.fail(f"數據服務模組測試失敗: {e}")

    def test_parameters_enhanced_module(self):
        """測試增強版參數模組"""
        try:
            from src.ui.pages.risk_management_enhanced.parameters_enhanced import (
                show_enhanced_parameters,
            )
            
            assert callable(show_enhanced_parameters), "增強版參數函數應該可調用"
            
            logger.info("✅ 增強版參數模組測試通過")
            
        except ImportError as e:
            pytest.fail(f"增強版參數模組導入失敗: {e}")

    def test_enhanced_module_info(self):
        """測試增強版模組信息"""
        try:
            from src.ui.pages.risk_management_enhanced import get_enhanced_module_info
            
            info = get_enhanced_module_info()
            assert isinstance(info, dict), "增強版模組信息應該是字典"
            assert "version" in info, "應包含版本信息"
            assert "devices" in info, "應包含支援設備列表"
            assert "features" in info, "應包含功能列表"
            assert "submodules" in info, "應包含子模組列表"
            
            # 驗證支援設備
            expected_devices = ["desktop", "tablet", "mobile"]
            for device in expected_devices:
                assert device in info["devices"], f"應支援設備: {device}"
            
            # 驗證增強功能
            expected_features = [
                "responsive_design",
                "real_time_validation", 
                "smart_alerts",
                "intelligent_scoring"
            ]
            for feature in expected_features:
                assert feature in info["features"], f"應包含功能: {feature}"
            
            logger.info("✅ 增強版模組信息測試通過")
            
        except Exception as e:
            pytest.fail(f"增強版模組信息測試失敗: {e}")

    def test_json_import_export(self):
        """測試 JSON 匯入匯出功能"""
        try:
            from src.ui.pages.risk_management_enhanced.data_services import (
                export_risk_parameters,
                import_risk_parameters,
            )
            
            # 測試數據
            test_params = {
                "stop_loss_enabled": True,
                "stop_loss_percent": 5.0,
                "take_profit_enabled": True,
                "take_profit_percent": 10.0,
                "max_position_size": 15.0
            }
            
            # 測試匯出
            exported_json = export_risk_parameters(test_params)
            assert isinstance(exported_json, str), "匯出結果應該是字符串"
            
            # 驗證 JSON 格式
            parsed_data = json.loads(exported_json)
            assert "export_time" in parsed_data, "應包含匯出時間"
            assert "version" in parsed_data, "應包含版本信息"
            assert "parameters" in parsed_data, "應包含參數數據"
            
            # 測試匯入
            imported_params = import_risk_parameters(exported_json)
            assert isinstance(imported_params, dict), "匯入結果應該是字典"
            
            # 驗證匯入的參數正確性
            for key, value in test_params.items():
                assert imported_params[key] == value, f"參數 {key} 匯入錯誤"
            
            # 測試無效 JSON 匯入
            invalid_json = '{"invalid": "format"}'
            result = import_risk_parameters(invalid_json)
            assert result is None, "無效 JSON 應該返回 None"
            
            logger.info("✅ JSON 匯入匯出測試通過")
            
        except Exception as e:
            pytest.fail(f"JSON 匯入匯出測試失敗: {e}")

    def test_risk_scoring_algorithm(self):
        """測試風險評分算法"""
        try:
            from src.ui.pages.risk_management_enhanced.data_services import (
                calculate_risk_score,
                get_risk_level,
            )
            
            # 測試低風險情況
            low_risk_indicators = {
                "current_drawdown": -2.0,  # 小回撤
                "var_95_1day": 10000,      # 低 VaR
                "portfolio_value": 1000000,
                "volatility": 10.0,        # 低波動率
                "largest_position_weight": 8.0  # 低集中度
            }
            
            low_risk_score = calculate_risk_score(low_risk_indicators)
            low_risk_level, low_risk_color = get_risk_level(low_risk_score)
            
            assert low_risk_score >= 80, f"低風險評分應該 ≥80: {low_risk_score}"
            assert low_risk_level == "低風險", f"應該是低風險: {low_risk_level}"
            assert low_risk_color == "🟢", f"應該是綠色: {low_risk_color}"
            
            # 測試高風險情況
            high_risk_indicators = {
                "current_drawdown": -20.0,  # 大回撤
                "var_95_1day": 80000,       # 高 VaR
                "portfolio_value": 1000000,
                "volatility": 35.0,         # 高波動率
                "largest_position_weight": 25.0  # 高集中度
            }
            
            high_risk_score = calculate_risk_score(high_risk_indicators)
            high_risk_level, high_risk_color = get_risk_level(high_risk_score)
            
            assert high_risk_score <= 40, f"高風險評分應該 ≤40: {high_risk_score}"
            assert high_risk_level in ["高風險", "極高風險"], f"應該是高風險: {high_risk_level}"
            assert high_risk_color in ["🟠", "🔴"], f"應該是橙色或紅色: {high_risk_color}"
            
            logger.info("✅ 風險評分算法測試通過")
            
        except Exception as e:
            pytest.fail(f"風險評分算法測試失敗: {e}")

    def test_file_structure_enhanced(self):
        """測試增強版文件結構"""
        enhanced_dir = project_root / "src" / "ui" / "pages" / "risk_management_enhanced"
        
        # 檢查目錄存在
        assert enhanced_dir.exists(), "增強版風險管理目錄應該存在"
        
        # 檢查必要文件存在
        required_files = [
            "__init__.py",
            "parameters_enhanced.py",
            "data_services.py"
        ]
        
        for file_name in required_files:
            file_path = enhanced_dir / file_name
            assert file_path.exists(), f"文件應該存在: {file_name}"
            
            # 檢查文件大小（應該 ≤ 300 行）
            with open(file_path, 'r', encoding='utf-8') as f:
                line_count = sum(1 for _ in f)
            assert line_count <= 300, f"文件 {file_name} 超過 300 行: {line_count} 行"
        
        logger.info("✅ 增強版文件結構測試通過")


def test_enhanced_integration():
    """增強版集成測試"""
    try:
        # 測試完整的增強版模組功能
        from src.ui.pages.risk_management_enhanced import show, get_enhanced_module_info
        from src.ui.pages.risk_management_enhanced.data_services import (
            load_risk_parameters,
            calculate_risk_score,
            load_risk_indicators
        )
        
        # 獲取增強版模組信息
        module_info = get_enhanced_module_info()
        assert module_info["version"] == "1.0.0", "版本應該是 1.0.0"
        
        # 測試數據流
        params = load_risk_parameters()
        indicators = load_risk_indicators()
        risk_score = calculate_risk_score(indicators)
        
        assert isinstance(params, dict), "參數應該是字典"
        assert isinstance(indicators, dict), "指標應該是字典"
        assert isinstance(risk_score, int), "風險評分應該是整數"
        
        logger.info("✅ 增強版集成測試通過")
        
    except Exception as e:
        pytest.fail(f"增強版集成測試失敗: {e}")


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v"])
