"""報表視覺化服務單元測試

此模組測試報表視覺化服務的各種功能，包括圖表生成、數據處理和錯誤處理。
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
    return pd.DataFrame({
        'date': dates,
        'symbol': ['AAPL'] * 30,
        'price': np.random.uniform(100, 200, 30),
        'volume': np.random.randint(1000, 10000, 30),
        'returns': np.random.normal(0.001, 0.02, 30),
        'pnl': np.random.normal(100, 500, 30)
    })


@pytest.fixture
def sample_portfolio_data():
    """提供測試用的投資組合數據"""
    return pd.DataFrame({
        'symbol': ['AAPL', 'GOOGL', 'MSFT', 'TSLA'],
        'weight': [0.3, 0.25, 0.25, 0.2],
        'value': [30000, 25000, 25000, 20000],
        'returns': [0.05, 0.03, 0.04, 0.08]
    })


class TestReportVisualizationServiceInit:
    """測試報表視覺化服務初始化"""

    def test_service_initialization(self, visualization_service):
        """測試服務初始化"""
        assert visualization_service is not None
        assert hasattr(visualization_service, 'session_factory')

    def test_service_initialization_with_invalid_db(self):
        """測試無效資料庫連接的初始化"""
        with patch('src.core.report_visualization_service.create_engine') as mock_engine:
            mock_engine.side_effect = Exception("資料庫連接失敗")

            with pytest.raises(Exception):
                ReportVisualizationService()


class TestCumulativeReturnChart:
    """測試累積報酬圖表生成"""

    def test_generate_cumulative_return_chart_plotly(self, visualization_service, sample_trading_data):
        """測試 Plotly 累積報酬圖表生成"""
        # 準備數據格式
        data = {
            'data': sample_trading_data.to_dict('records')
        }
        # 添加必要的欄位
        for record in data['data']:
            record['execution_time'] = record['date']
            record['cumulative_pnl'] = np.random.uniform(-1000, 1000)

        fig = visualization_service.generate_cumulative_return_chart(
            data,
            chart_type='plotly'
        )

        assert fig is not None
        assert hasattr(fig, 'data')

    def test_generate_cumulative_return_chart_matplotlib(self, visualization_service, sample_trading_data):
        """測試 Matplotlib 累積報酬圖表生成"""
        # 準備數據格式
        data = {
            'data': sample_trading_data.to_dict('records')
        }
        # 添加必要的欄位
        for record in data['data']:
            record['execution_time'] = record['date']
            record['cumulative_pnl'] = np.random.uniform(-1000, 1000)

        fig = visualization_service.generate_cumulative_return_chart(
            data,
            chart_type='matplotlib'
        )

        assert fig is not None

    def test_generate_cumulative_return_chart_empty_data(self, visualization_service):
        """測試空數據的累積報酬圖表生成"""
        empty_data = {'data': []}

        result = visualization_service.generate_cumulative_return_chart(empty_data)

        assert result is None

    def test_generate_cumulative_return_chart_invalid_data(self, visualization_service):
        """測試無效數據的累積報酬圖表生成"""
        invalid_data = {}

        result = visualization_service.generate_cumulative_return_chart(invalid_data)

        assert result is None


class TestDrawdownChart:
    """測試回撤圖表生成"""

    def test_generate_drawdown_chart_plotly(self, visualization_service, sample_trading_data):
        """測試 Plotly 回撤圖表生成"""
        # 準備數據格式
        data = {
            'data': sample_trading_data.to_dict('records')
        }
        # 添加必要的欄位
        for record in data['data']:
            record['execution_time'] = record['date']
            record['cumulative_pnl'] = np.random.uniform(-1000, 1000)

        fig = visualization_service.generate_drawdown_chart(
            data,
            chart_type='plotly'
        )

        assert fig is not None
        assert hasattr(fig, 'data')

    def test_generate_drawdown_chart_matplotlib(self, visualization_service, sample_trading_data):
        """測試 Matplotlib 回撤圖表生成"""
        # 準備數據格式
        data = {
            'data': sample_trading_data.to_dict('records')
        }
        # 添加必要的欄位
        for record in data['data']:
            record['execution_time'] = record['date']
            record['cumulative_pnl'] = np.random.uniform(-1000, 1000)

        fig = visualization_service.generate_drawdown_chart(
            data,
            chart_type='matplotlib'
        )

        assert fig is not None

    def test_generate_drawdown_chart_empty_data(self, visualization_service):
        """測試空數據的回撤圖表生成"""
        empty_data = {'data': []}

        result = visualization_service.generate_drawdown_chart(empty_data)

        assert result is None


class TestPieChartGeneration:
    """測試圓餅圖生成"""

    def test_generate_pie_chart_plotly(self, visualization_service, sample_portfolio_data):
        """測試 Plotly 圓餅圖生成"""
        fig = visualization_service.generate_pie_chart(
            sample_portfolio_data,
            values_col='value',
            names_col='symbol',
            chart_type='plotly'
        )

        assert fig is not None
        assert hasattr(fig, 'data')
        assert len(fig.data) > 0

    def test_generate_pie_chart_matplotlib(self, visualization_service, sample_portfolio_data):
        """測試 Matplotlib 圓餅圖生成"""
        fig = visualization_service.generate_pie_chart(
            sample_portfolio_data,
            values_col='value',
            names_col='symbol',
            chart_type='matplotlib'
        )

        assert fig is not None

    def test_generate_pie_chart_empty_data(self, visualization_service):
        """測試空數據的圓餅圖生成"""
        empty_data = pd.DataFrame()

        result = visualization_service.generate_pie_chart(
            empty_data,
            values_col='value',
            names_col='symbol'
        )

        assert result is None


class TestHeatmapGeneration:
    """測試熱力圖生成"""

    def test_generate_monthly_performance_heatmap_plotly(self, visualization_service, sample_trading_data):
        """測試 Plotly 月度績效熱力圖生成"""
        fig = visualization_service.generate_monthly_performance_heatmap(
            sample_trading_data,
            chart_type='plotly'
        )

        assert fig is not None
        assert hasattr(fig, 'data')

    def test_generate_monthly_performance_heatmap_matplotlib(self, visualization_service, sample_trading_data):
        """測試 Matplotlib 月度績效熱力圖生成"""
        fig = visualization_service.generate_monthly_performance_heatmap(
            sample_trading_data,
            chart_type='matplotlib'
        )

        assert fig is not None

    def test_generate_parameter_sensitivity_heatmap(self, visualization_service):
        """測試參數敏感度熱力圖生成"""
        param_results = {
            'param1_values': [10, 20, 30],
            'param2_values': [0.1, 0.2, 0.3],
            'performance_matrix': [[100, 110, 120], [105, 115, 125], [110, 120, 130]]
        }

        fig = visualization_service.generate_parameter_sensitivity_heatmap(
            param_results,
            chart_type='plotly'
        )

        assert fig is not None


class TestStrategyComparisonChart:
    """測試策略比較圖表"""

    def test_generate_strategy_comparison_chart(self, visualization_service):
        """測試策略比較圖表生成"""
        strategy_data = pd.DataFrame({
            'strategy': ['Strategy A', 'Strategy B', 'Strategy C'],
            'returns': [0.15, 0.12, 0.18],
            'sharpe_ratio': [1.2, 1.0, 1.5],
            'max_drawdown': [-0.05, -0.08, -0.04]
        })

        fig = visualization_service.generate_strategy_comparison_chart(
            strategy_data,
            chart_type='plotly'
        )

        assert fig is not None


class TestExportFunctionality:
    """測試匯出功能"""

    @patch('src.core.report_visualization_service.Path')
    def test_export_report_json(self, mock_path, visualization_service):
        """測試 JSON 格式報表匯出"""
        mock_path.return_value.mkdir = Mock()
        mock_path.return_value.stat.return_value.st_size = 1024

        report_data = {'test': 'data'}

        with patch('builtins.open', create=True) as mock_open:
            with patch('json.dump') as mock_json_dump:
                success, message, filepath = visualization_service.export_report(
                    report_data,
                    export_format='json'
                )

                assert success is True
                assert 'json' in message
                mock_json_dump.assert_called_once()

    @patch('src.core.report_visualization_service.Path')
    def test_export_report_csv(self, mock_path, visualization_service):
        """測試 CSV 格式報表匯出"""
        mock_path.return_value.mkdir = Mock()
        mock_path.return_value.stat.return_value.st_size = 1024

        report_data = {'data': [{'col1': 1, 'col2': 2}]}

        with patch('pandas.DataFrame.to_csv') as mock_to_csv:
            success, message, filepath = visualization_service.export_report(
                report_data,
                export_format='csv'
            )

            assert success is True
            assert 'csv' in message.lower()
            mock_to_csv.assert_called_once()

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


class TestErrorHandling:
    """測試錯誤處理機制"""

    def test_exception_chaining_in_line_chart(self, visualization_service):
        """測試折線圖生成中的異常鏈接"""
        with patch('src.core.report_visualization_service.px.line') as mock_line:
            mock_line.side_effect = Exception("Plotly 錯誤")

            result = visualization_service.generate_line_chart(
                pd.DataFrame({'x': [1, 2], 'y': [1, 2]}),
                x_col='x',
                y_col='y'
            )

            assert result is None

    def test_exception_chaining_in_export(self, visualization_service):
        """測試匯出功能中的異常鏈接"""
        with patch('builtins.open', side_effect=Exception("檔案錯誤")):
            success, message, filepath = visualization_service.export_report(
                {'test': 'data'},
                export_format='json'
            )

            assert success is False
            assert '匯出失敗' in message
            assert filepath is None


class TestCacheFunctionality:
    """測試快取功能"""

    def test_cleanup_cache(self, visualization_service):
        """測試快取清理"""
        with patch.object(visualization_service, 'session_factory') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.delete.return_value = 5

            success, message = visualization_service.cleanup_cache(max_age_hours=24)

            assert success is True
            assert '5' in message


class TestChartConfigManagement:
    """測試圖表配置管理"""

    def test_save_chart_config(self, visualization_service):
        """測試保存圖表配置"""
        config_data = {
            'style': {'theme': 'dark'},
            'colors': {'primary': 'blue'}
        }

        with patch.object(visualization_service, 'session_factory') as mock_session:
            mock_session.return_value.__enter__.return_value.add = Mock()
            mock_session.return_value.__enter__.return_value.commit = Mock()

            success, message = visualization_service.save_chart_config(
                config_name='test_config',
                chart_type='line',
                config_data=config_data
            )

            assert success is True
            assert 'test_config' in message

    def test_get_chart_configs(self, visualization_service):
        """測試獲取圖表配置"""
        with patch.object(visualization_service, 'session_factory') as mock_session:
            mock_config = Mock()
            mock_config.config_id = 'test_id'
            mock_config.config_name = 'test_config'
            mock_config.chart_type = 'line'
            mock_config.created_by = 'user'
            mock_config.created_at.isoformat.return_value = '2023-01-01T00:00:00'
            mock_config.usage_count = 5

            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_config]

            configs = visualization_service.get_chart_configs(chart_type='line')

            assert len(configs) == 1
            assert configs[0]['config_name'] == 'test_config'


class TestDataValidation:
    """測試數據驗證"""

    def test_validate_data_columns(self, visualization_service):
        """測試數據欄位驗證"""
        # 這個測試假設服務有數據驗證方法
        valid_data = pd.DataFrame({'date': [1, 2], 'price': [100, 110]})
        invalid_data = pd.DataFrame({'wrong_col': [1, 2]})

        # 測試有效數據
        result = visualization_service.generate_line_chart(
            valid_data,
            x_col='date',
            y_col='price'
        )
        assert result is not None

        # 測試無效數據
        result = visualization_service.generate_line_chart(
            invalid_data,
            x_col='date',
            y_col='price'
        )
        assert result is None

    def test_data_type_validation(self, visualization_service):
        """測試數據類型驗證"""
        # 測試非 DataFrame 輸入
        invalid_input = "not a dataframe"

        result = visualization_service.generate_line_chart(
            invalid_input,
            x_col='date',
            y_col='price'
        )

        assert result is None
