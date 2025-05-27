"""報表視覺化服務簡化測試

此模組測試報表視覺化服務的核心功能。
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, Mock

from src.core.report_visualization_service import ReportVisualizationService


@pytest.fixture
def visualization_service():
    """提供報表視覺化服務實例"""
    return ReportVisualizationService()


@pytest.fixture
def sample_trading_data():
    """提供測試用的交易數據"""
    dates = pd.date_range('2023-01-01', periods=30, freq='D')
    return {
        'data': [
            {
                'execution_time': date.isoformat(),
                'symbol': 'AAPL',
                'cumulative_pnl': np.random.uniform(-1000, 1000),
                'net_amount': np.random.uniform(-100, 100)
            }
            for date in dates
        ]
    }


class TestServiceInitialization:
    """測試服務初始化"""

    def test_service_initialization(self, visualization_service):
        """測試服務初始化"""
        assert visualization_service is not None
        assert hasattr(visualization_service, 'session_factory')
        assert hasattr(visualization_service, 'engine')

    def test_service_attributes(self, visualization_service):
        """測試服務屬性"""
        assert visualization_service.cache_enabled is True
        assert visualization_service.default_cache_duration == 300
        assert 'plotly' in visualization_service.default_chart_config
        assert 'matplotlib' in visualization_service.default_chart_config


class TestCumulativeReturnChart:
    """測試累積報酬圖表"""

    def test_generate_cumulative_return_chart_plotly(self, visualization_service, sample_trading_data):
        """測試 Plotly 累積報酬圖表"""
        fig = visualization_service.generate_cumulative_return_chart(
            sample_trading_data, 
            chart_type='plotly'
        )
        
        assert fig is not None
        assert hasattr(fig, 'data')

    def test_generate_cumulative_return_chart_matplotlib(self, visualization_service, sample_trading_data):
        """測試 Matplotlib 累積報酬圖表"""
        fig = visualization_service.generate_cumulative_return_chart(
            sample_trading_data, 
            chart_type='matplotlib'
        )
        
        assert fig is not None

    def test_generate_cumulative_return_chart_empty_data(self, visualization_service):
        """測試空數據處理"""
        empty_data = {'data': []}
        
        result = visualization_service.generate_cumulative_return_chart(empty_data)
        
        assert result is None


class TestDrawdownChart:
    """測試回撤圖表"""

    def test_generate_drawdown_chart_plotly(self, visualization_service, sample_trading_data):
        """測試 Plotly 回撤圖表"""
        fig = visualization_service.generate_drawdown_chart(
            sample_trading_data, 
            chart_type='plotly'
        )
        
        assert fig is not None
        assert hasattr(fig, 'data')

    def test_generate_drawdown_chart_matplotlib(self, visualization_service, sample_trading_data):
        """測試 Matplotlib 回撤圖表"""
        fig = visualization_service.generate_drawdown_chart(
            sample_trading_data, 
            chart_type='matplotlib'
        )
        
        assert fig is not None

    def test_generate_drawdown_chart_empty_data(self, visualization_service):
        """測試空數據處理"""
        empty_data = {'data': []}
        
        result = visualization_service.generate_drawdown_chart(empty_data)
        
        assert result is None


class TestPerformanceDashboard:
    """測試績效儀表板"""

    def test_generate_performance_dashboard(self, visualization_service):
        """測試績效儀表板生成"""
        metrics = {
            'total_pnl': 1000,
            'win_rate': 65.5,
            'profit_factor': 1.5,
            'sharpe_ratio': 1.2,
            'max_drawdown': -500,
            'total_trades': 100
        }
        
        fig = visualization_service.generate_performance_dashboard(metrics)
        
        assert fig is not None
        assert hasattr(fig, 'data')

    def test_generate_performance_dashboard_empty_metrics(self, visualization_service):
        """測試空指標處理"""
        empty_metrics = {}
        
        fig = visualization_service.generate_performance_dashboard(empty_metrics)
        
        assert fig is not None


class TestMonthlyHeatmap:
    """測試月度熱力圖"""

    def test_generate_monthly_heatmap_plotly(self, visualization_service, sample_trading_data):
        """測試 Plotly 月度熱力圖"""
        fig = visualization_service.generate_monthly_heatmap(
            sample_trading_data, 
            chart_type='plotly'
        )
        
        assert fig is not None

    def test_generate_monthly_heatmap_matplotlib(self, visualization_service, sample_trading_data):
        """測試 Matplotlib 月度熱力圖"""
        fig = visualization_service.generate_monthly_heatmap(
            sample_trading_data, 
            chart_type='matplotlib'
        )
        
        assert fig is not None


class TestParameterSensitivityHeatmap:
    """測試參數敏感度熱力圖"""

    def test_generate_parameter_sensitivity_heatmap(self, visualization_service):
        """測試參數敏感度熱力圖"""
        param_results = {
            'param1_values': [10, 20, 30],
            'param2_values': [0.1, 0.2, 0.3],
            'performance_matrix': [[100, 110, 120], [105, 115, 125], [110, 120, 130]]
        }
        
        fig = visualization_service.generate_parameter_sensitivity_heatmap(param_results)
        
        assert fig is not None


class TestDataRetrieval:
    """測試數據檢索"""

    @patch.object(ReportVisualizationService, 'session_factory')
    def test_get_trading_performance_data(self, mock_session, visualization_service):
        """測試獲取交易績效數據"""
        # 模擬資料庫查詢結果
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        result = visualization_service.get_trading_performance_data()
        
        assert isinstance(result, dict)
        assert 'message' in result or 'data' in result

    @patch.object(ReportVisualizationService, 'session_factory')
    def test_get_trade_details_data(self, mock_session, visualization_service):
        """測試獲取交易明細數據"""
        # 模擬資料庫查詢結果
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        result = visualization_service.get_trade_details_data()
        
        assert isinstance(result, dict)


class TestExportFunctionality:
    """測試匯出功能"""

    def test_export_report_unsupported_format(self, visualization_service):
        """測試不支援的匯出格式"""
        report_data = {'test': 'data'}
        
        success, message, filepath = visualization_service.export_report(
            report_data, 
            export_format='unsupported'
        )
        
        assert success is False
        assert '不支援' in message
        assert filepath is None


class TestCacheFunctionality:
    """測試快取功能"""

    @patch.object(ReportVisualizationService, 'session_factory')
    def test_cleanup_cache(self, mock_session, visualization_service):
        """測試快取清理"""
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.delete.return_value = 5
        
        success, message = visualization_service.cleanup_cache(max_age_hours=24)
        
        assert success is True
        assert '5' in message


class TestChartConfigManagement:
    """測試圖表配置管理"""

    @patch.object(ReportVisualizationService, 'session_factory')
    def test_save_chart_config(self, mock_session, visualization_service):
        """測試保存圖表配置"""
        config_data = {
            'style': {'theme': 'dark'},
            'colors': {'primary': 'blue'}
        }
        
        mock_session.return_value.__enter__.return_value.add = Mock()
        mock_session.return_value.__enter__.return_value.commit = Mock()
        
        success, message = visualization_service.save_chart_config(
            config_name='test_config',
            chart_type='line',
            config_data=config_data
        )
        
        assert success is True
        assert 'test_config' in message

    @patch.object(ReportVisualizationService, 'session_factory')
    def test_get_chart_configs(self, mock_session, visualization_service):
        """測試獲取圖表配置"""
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        configs = visualization_service.get_chart_configs(chart_type='line')
        
        assert isinstance(configs, list)


class TestErrorHandling:
    """測試錯誤處理"""

    def test_invalid_data_handling(self, visualization_service):
        """測試無效數據處理"""
        invalid_data = {}
        
        result = visualization_service.generate_cumulative_return_chart(invalid_data)
        
        assert result is None

    def test_exception_handling_in_performance_metrics(self, visualization_service):
        """測試績效指標計算中的異常處理"""
        # 測試空 DataFrame
        empty_df = pd.DataFrame()
        
        metrics = visualization_service._calculate_performance_metrics(empty_df)
        
        assert isinstance(metrics, dict)
        assert len(metrics) == 0
