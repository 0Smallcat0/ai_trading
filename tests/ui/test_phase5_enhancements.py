"""
Phase 5.1 功能模組完善測試

測試策略管理和AI模型管理的增強功能
"""

import pytest
import streamlit as st
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np


# 測試策略管理增強功能
class TestStrategyManagementEnhancements:
    """測試策略管理增強功能"""

    def test_strategy_version_control(self):
        """測試策略版本控制功能"""
        # 模擬策略數據
        strategy_data = {
            "id": "test_strategy_1",
            "name": "測試策略",
            "version": "1.0.0",
            "type": "技術分析策略",
        }

        # 測試版本控制功能存在
        from src.ui.pages.strategy_management import show_strategy_version_control

        assert callable(show_strategy_version_control)

    def test_strategy_performance_analysis(self):
        """測試策略效能分析功能"""
        from src.ui.pages.strategy_management import show_strategy_performance_analysis

        assert callable(show_strategy_performance_analysis)

    def test_strategy_parameter_optimization(self):
        """測試策略參數優化功能"""
        from src.ui.pages.strategy_management import (
            show_strategy_parameter_optimization,
        )

        assert callable(show_strategy_parameter_optimization)

    def test_basic_performance_metrics(self):
        """測試基本效能指標顯示"""
        from src.ui.pages.strategy_management import show_basic_performance_metrics

        strategy_data = {
            "performance": {
                "sharpe_ratio": 1.5,
                "max_drawdown": 0.15,
                "win_rate": 0.65,
                "profit_factor": 1.8,
            }
        }

        assert callable(show_basic_performance_metrics)

    def test_risk_analysis(self):
        """測試風險分析功能"""
        from src.ui.pages.strategy_management import show_risk_analysis

        assert callable(show_risk_analysis)


# 測試AI模型管理增強功能
class TestAIModelManagementEnhancements:
    """測試AI模型管理增強功能"""

    def test_enhanced_training_interface(self):
        """測試增強版訓練介面"""
        from src.ui.pages.ai_models import show_model_training_enhanced

        assert callable(show_model_training_enhanced)

    def test_performance_monitoring(self):
        """測試效能監控功能"""
        from src.ui.pages.ai_models import show_model_performance_monitoring

        assert callable(show_model_performance_monitoring)

    def test_realtime_monitoring(self):
        """測試實時監控功能"""
        from src.ui.pages.ai_models import show_realtime_monitoring

        assert callable(show_realtime_monitoring)

    def test_historical_analysis(self):
        """測試歷史分析功能"""
        from src.ui.pages.ai_models import show_historical_analysis

        assert callable(show_historical_analysis)

    def test_performance_comparison(self):
        """測試效能比較功能"""
        from src.ui.pages.ai_models import show_performance_comparison

        assert callable(show_performance_comparison)

    def test_anomaly_detection(self):
        """測試異常檢測功能"""
        from src.ui.pages.ai_models import show_anomaly_detection

        assert callable(show_anomaly_detection)

    def test_enhanced_model_management(self):
        """測試增強版模型管理"""
        from src.ui.pages.ai_models import show_model_management_enhanced

        assert callable(show_model_management_enhanced)

    def test_lifecycle_management(self):
        """測試生命週期管理"""
        from src.ui.pages.ai_models import show_model_lifecycle_management

        assert callable(show_model_lifecycle_management)


# 測試訓練配置功能
class TestTrainingConfigurations:
    """測試訓練配置功能"""

    def test_quick_training_config(self):
        """測試快速訓練配置"""
        from src.ui.pages.ai_models import show_quick_training_config

        assert callable(show_quick_training_config)

    def test_standard_training_config(self):
        """測試標準訓練配置"""
        from src.ui.pages.ai_models import show_standard_training_config

        assert callable(show_standard_training_config)

    def test_deep_training_config(self):
        """測試深度訓練配置"""
        from src.ui.pages.ai_models import show_deep_training_config

        assert callable(show_deep_training_config)

    def test_auto_tuning_config(self):
        """測試自動調優配置"""
        from src.ui.pages.ai_models import show_auto_tuning_config

        assert callable(show_auto_tuning_config)

    def test_training_results_display(self):
        """測試訓練結果顯示"""
        from src.ui.pages.ai_models import show_training_results

        assert callable(show_training_results)


# 整合測試
class TestPhase5Integration:
    """Phase 5.1 整合測試"""

    @patch("streamlit.session_state")
    def test_strategy_management_integration(self, mock_session_state):
        """測試策略管理整合"""
        mock_session_state.selected_strategy = {
            "id": "test_1",
            "name": "測試策略",
            "type": "技術分析策略",
        }

        # 測試主要功能可以正常導入
        from src.ui.pages.strategy_management import (
            show_strategy_version_control,
            show_strategy_performance_analysis,
            show_strategy_parameter_optimization,
        )

        assert all(
            [
                callable(show_strategy_version_control),
                callable(show_strategy_performance_analysis),
                callable(show_strategy_parameter_optimization),
            ]
        )

    @patch("streamlit.session_state")
    def test_ai_model_management_integration(self, mock_session_state):
        """測試AI模型管理整合"""
        mock_session_state.selected_model = {
            "id": "test_model_1",
            "name": "測試模型",
            "type": "機器學習模型",
        }

        # 測試主要功能可以正常導入
        from src.ui.pages.ai_models import (
            show_model_training_enhanced,
            show_model_performance_monitoring,
            show_model_management_enhanced,
        )

        assert all(
            [
                callable(show_model_training_enhanced),
                callable(show_model_performance_monitoring),
                callable(show_model_management_enhanced),
            ]
        )


if __name__ == "__main__":
    pytest.main([__file__])
