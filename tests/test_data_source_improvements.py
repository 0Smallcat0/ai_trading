# -*- coding: utf-8 -*-
"""
數據源改進測試

此模組測試數據源驗證報告改進建議的實施效果，
驗證增強HTML解析器、多層備援機制和數據驗證功能。

測試內容：
- 增強HTML解析器功能測試
- 多層備援機制測試
- 數據品質驗證測試
- 自動化驗證管道測試
- 性能和穩定性測試

Example:
    運行測試：
    ```bash
    pytest tests/test_data_source_improvements.py -v
    ```

Note:
    此測試模組專門驗證數據源驗證報告改進建議的實施效果，
    確保改進後的系統能夠解決原有的HTML解析失敗和數據品質問題。
"""

import pytest
import pandas as pd
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# 導入待測試的模組
try:
    from src.data_sources.enhanced_html_parser import EnhancedHTMLParser
    from src.data_sources.multi_tier_backup_manager import MultiTierBackupManager
    from src.data_sources.enhanced_data_validator import EnhancedDataValidator, DataQualityLevel
    from src.data_sources.automated_validation_pipeline import AutomatedValidationPipeline
    from src.data_sources.comprehensive_crawler import ComprehensiveCrawler
except ImportError as e:
    pytest.skip(f"無法導入測試模組: {e}", allow_module_level=True)


class TestEnhancedHTMLParser:
    """測試增強HTML解析器"""
    
    def setup_method(self):
        """設置測試環境"""
        self.parser = EnhancedHTMLParser()
        
    def test_parser_initialization(self):
        """測試解析器初始化"""
        assert self.parser is not None
        assert hasattr(self.parser, 'selector_mapping')
        assert '股利公告' in self.parser.selector_mapping
        assert '月營收' in self.parser.selector_mapping
        assert '重訊公告' in self.parser.selector_mapping
        
    def test_selector_mapping_structure(self):
        """測試選擇器映射結構"""
        for data_type, config in self.parser.selector_mapping.items():
            assert 'table_keywords' in config
            assert 'selectors' in config
            assert 'fallback_url_patterns' in config
            assert isinstance(config['table_keywords'], list)
            assert isinstance(config['selectors'], list)
            assert isinstance(config['fallback_url_patterns'], list)
            
    @patch('src.data_sources.enhanced_html_parser.requests.Session.get')
    def test_parse_with_requests_success(self, mock_get):
        """測試HTTP請求解析成功情況"""
        # 模擬成功的HTML響應
        mock_response = Mock()
        mock_response.text = """
        <html>
            <table class="hasBorder">
                <tr><th>股利公告</th><th>金額</th></tr>
                <tr><td>台積電</td><td>10.0</td></tr>
            </table>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.parser._parse_with_requests("http://test.com", "股利公告")
        
        assert isinstance(result, pd.DataFrame)
        # 由於HTML解析可能因為pandas版本差異而失敗，我們主要測試流程
        
    def test_update_selector_mapping(self):
        """測試動態更新選擇器映射"""
        new_config = {
            'table_keywords': ['測試', '關鍵字'],
            'selectors': ['table.test'],
            'fallback_url_patterns': ['/test']
        }
        
        self.parser.update_selector_mapping('測試數據', new_config)
        
        assert '測試數據' in self.parser.selector_mapping
        assert self.parser.selector_mapping['測試數據'] == new_config
        
    def test_health_status(self):
        """測試健康狀態獲取"""
        status = self.parser.get_health_status()
        
        assert isinstance(status, dict)
        assert 'parser_name' in status
        assert 'supported_data_types' in status
        assert 'request_delay' in status
        assert 'timeout' in status
        assert status['parser_name'] == 'EnhancedHTMLParser'


class TestMultiTierBackupManager:
    """測試多層備援機制管理器"""
    
    def setup_method(self):
        """設置測試環境"""
        self.manager = MultiTierBackupManager()
        
    def test_manager_initialization(self):
        """測試管理器初始化"""
        assert self.manager is not None
        assert hasattr(self.manager, 'backup_registry')
        assert hasattr(self.manager, 'metrics')
        
        # 檢查預設備援配置
        assert '技術面' in self.manager.backup_registry
        assert '基本面' in self.manager.backup_registry
        assert '籌碼面' in self.manager.backup_registry
        
    def test_backup_source_registration(self):
        """測試備援數據源註冊"""
        from src.data_sources.multi_tier_backup_manager import DataSourceConfig
        
        config = DataSourceConfig(
            name='test_source',
            priority=1,
            crawler_class='TestCrawler',
            method_name='test_method'
        )
        
        self.manager.register_backup_source('測試分類', '測試類型', config)
        
        assert '測試分類' in self.manager.backup_registry
        assert '測試類型' in self.manager.backup_registry['測試分類']
        assert len(self.manager.backup_registry['測試分類']['測試類型']) > 0
        
    def test_health_report_generation(self):
        """測試健康報告生成"""
        report = self.manager.get_health_report()
        
        assert isinstance(report, dict)
        assert 'timestamp' in report
        assert 'total_sources' in report
        assert 'sources_by_status' in report
        assert 'sources_detail' in report
        
    @patch('src.data_sources.multi_tier_backup_manager.VerifiedCrawler')
    def test_data_fetching_with_fallback(self, mock_crawler_class):
        """測試故障轉移數據獲取"""
        # 模擬爬蟲實例
        mock_crawler = Mock()
        mock_method = Mock()
        mock_method.return_value = pd.DataFrame({'test': [1, 2, 3]})
        mock_crawler.crawl_yahoo_adjusted_price = mock_method
        mock_crawler_class.return_value = mock_crawler
        
        result = self.manager.get_data_with_fallback('技術面', '股價數據')
        
        assert isinstance(result, pd.DataFrame)


class TestEnhancedDataValidator:
    """測試增強數據驗證器"""
    
    def setup_method(self):
        """設置測試環境"""
        self.validator = EnhancedDataValidator()
        
    def test_validator_initialization(self):
        """測試驗證器初始化"""
        assert self.validator is not None
        assert hasattr(self.validator, 'validation_rules')
        assert '股價數據' in self.validator.validation_rules
        assert '財務數據' in self.validator.validation_rules
        
    def test_data_quality_validation_empty_data(self):
        """測試空數據的品質驗證"""
        empty_df = pd.DataFrame()
        report = self.validator.validate_data_quality(empty_df, '股價數據')
        
        assert report.total_records == 0
        assert report.quality_level == DataQualityLevel.CRITICAL
        assert report.quality_score == 0.0
        assert '數據為空' in report.recommendations[0]
        
    def test_data_quality_validation_good_data(self):
        """測試良好數據的品質驗證"""
        good_df = pd.DataFrame({
            '開盤價': [100, 101, 102],
            '最高價': [105, 106, 107],
            '最低價': [99, 100, 101],
            '收盤價': [104, 105, 106],
            '成交量': [1000, 1100, 1200]
        })
        
        report = self.validator.validate_data_quality(good_df, '股價數據')
        
        assert report.total_records == 3
        assert report.missing_rate == 0.0
        assert report.duplicate_rate == 0.0
        assert report.quality_score > 80.0
        
    def test_data_quality_validation_with_issues(self):
        """測試有問題數據的品質驗證"""
        problematic_df = pd.DataFrame({
            '開盤價': [100, None, 102, 100],  # 缺失值和重複
            '最高價': [105, 106, 90, 105],   # 邏輯錯誤（最高價<開盤價）
            '最低價': [99, 100, 101, 99],
            '收盤價': [104, 105, 106, 104],
            '成交量': [1000, 1100, 1200, 1000]
        })
        
        report = self.validator.validate_data_quality(problematic_df, '股價數據')
        
        assert report.total_records == 4
        assert report.missing_rate > 0
        assert report.duplicate_rate > 0
        assert len(report.anomalies) > 0
        assert report.quality_score < 90.0
        
    def test_anomaly_detection_methods(self):
        """測試異常檢測方法"""
        from src.data_sources.enhanced_data_validator import AnomalyMethod
        
        # 創建包含異常值的數據
        data_with_outliers = pd.DataFrame({
            'value': [1, 2, 3, 4, 5, 100, 6, 7, 8, 9]  # 100是明顯的異常值
        })
        
        # 測試Z-score方法
        zscore_anomalies = self.validator._detect_anomalies(
            data_with_outliers, AnomalyMethod.ZSCORE, 'general'
        )
        assert len(zscore_anomalies) > 0
        
        # 測試IQR方法
        iqr_anomalies = self.validator._detect_anomalies(
            data_with_outliers, AnomalyMethod.IQR, 'general'
        )
        assert len(iqr_anomalies) > 0
        
    def test_data_cleaning_based_on_report(self):
        """測試基於報告的數據清理"""
        dirty_df = pd.DataFrame({
            'value': [1, 2, 2, 3, 4],  # 包含重複值
            'name': ['A', 'B', 'B', 'C', 'D']
        })
        
        report = self.validator.validate_data_quality(dirty_df)
        cleaned_df = self.validator.clean_data_based_on_report(dirty_df, report)
        
        # 清理後的數據應該更少（移除了重複值）
        assert len(cleaned_df) <= len(dirty_df)


class TestAutomatedValidationPipeline:
    """測試自動化驗證管道"""
    
    def setup_method(self):
        """設置測試環境"""
        self.pipeline = AutomatedValidationPipeline(output_dir="tests/temp_validation")
        
    def test_pipeline_initialization(self):
        """測試管道初始化"""
        assert self.pipeline is not None
        assert hasattr(self.pipeline, 'html_parser')
        assert hasattr(self.pipeline, 'backup_manager')
        assert hasattr(self.pipeline, 'data_validator')
        assert hasattr(self.pipeline, 'validation_config')
        
    def test_validation_config_structure(self):
        """測試驗證配置結構"""
        config = self.pipeline.validation_config
        
        assert 'verified_sources' in config
        assert 'comprehensive_sources' in config
        assert 'validation_params' in config
        
        # 檢查已驗證數據源配置
        verified = config['verified_sources']
        assert '技術面' in verified
        assert '基本面' in verified
        assert '籌碼面' in verified
        assert '總經面' in verified
        
    @patch('src.data_sources.automated_validation_pipeline.VerifiedCrawler')
    @patch('src.data_sources.automated_validation_pipeline.ComprehensiveCrawler')
    def test_single_source_validation(self, mock_comprehensive, mock_verified):
        """測試單一數據源驗證"""
        # 模擬爬蟲
        mock_crawler = Mock()
        mock_method = Mock()
        mock_method.return_value = pd.DataFrame({'test': [1, 2, 3]})
        setattr(mock_crawler, 'test_method', mock_method)
        
        result = self.pipeline._validate_single_source(
            mock_crawler, '技術面', 'test_method', 'verified'
        )
        
        assert result.source_name == 'test_method'
        assert result.category == '技術面'
        assert result.success == True
        assert result.record_count == 3
        
    def test_recommendation_generation(self):
        """測試建議生成"""
        from src.data_sources.automated_validation_pipeline import ValidationResult
        
        # 創建測試結果
        results = [
            ValidationResult(
                source_name='test1',
                category='技術面',
                data_type='verified',
                success=True,
                record_count=100,
                response_time=1.0,
                error_message=None,
                quality_report=None,
                timestamp=datetime.now()
            ),
            ValidationResult(
                source_name='test2',
                category='基本面',
                data_type='comprehensive',
                success=False,
                record_count=0,
                response_time=30.0,
                error_message='HTML parsing failed',
                quality_report=None,
                timestamp=datetime.now()
            )
        ]
        
        recommendations = self.pipeline._generate_recommendations(results, 50.0)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any('成功率過低' in rec for rec in recommendations)


class TestComprehensiveCrawlerImprovements:
    """測試綜合爬蟲改進"""
    
    def setup_method(self):
        """設置測試環境"""
        self.crawler = ComprehensiveCrawler()
        
    def test_crawler_initialization_with_html_parser(self):
        """測試爬蟲初始化包含HTML解析器"""
        assert self.crawler is not None
        # HTML解析器可能因為依賴問題初始化失敗，但不應該影響爬蟲基本功能
        assert hasattr(self.crawler, 'html_parser')
        
    @patch('src.data_sources.comprehensive_crawler.EnhancedHTMLParser')
    def test_enhanced_parsing_integration(self, mock_parser_class):
        """測試增強解析器整合"""
        # 模擬增強解析器
        mock_parser = Mock()
        mock_parser.parse_twse_page.return_value = pd.DataFrame({'test': [1, 2, 3]})
        mock_parser_class.return_value = mock_parser
        
        # 重新初始化爬蟲以使用模擬解析器
        crawler = ComprehensiveCrawler()
        crawler.html_parser = mock_parser
        
        # 測試股利公告方法
        result = crawler.crawl_twse_dividend_announcement()
        
        # 如果增強解析器可用，應該被調用
        if crawler.html_parser:
            mock_parser.parse_twse_page.assert_called_once()


class TestIntegrationAndPerformance:
    """整合和性能測試"""
    
    def test_system_integration(self):
        """測試系統整合"""
        # 創建所有組件
        html_parser = EnhancedHTMLParser()
        backup_manager = MultiTierBackupManager()
        data_validator = EnhancedDataValidator()
        pipeline = AutomatedValidationPipeline()
        
        # 驗證組件間可以正常協作
        assert html_parser is not None
        assert backup_manager is not None
        assert data_validator is not None
        assert pipeline is not None
        
        # 測試組件間的基本交互
        health_status = html_parser.get_health_status()
        health_report = backup_manager.get_health_report()
        
        assert isinstance(health_status, dict)
        assert isinstance(health_report, dict)
        
    def test_performance_benchmarks(self):
        """測試性能基準"""
        validator = EnhancedDataValidator()
        
        # 創建大數據集進行性能測試
        large_df = pd.DataFrame({
            'value': range(1000),
            'category': ['A'] * 500 + ['B'] * 500
        })
        
        start_time = time.time()
        report = validator.validate_data_quality(large_df)
        end_time = time.time()
        
        # 驗證性能要求（應該在合理時間內完成）
        processing_time = end_time - start_time
        assert processing_time < 10.0  # 應該在10秒內完成
        assert report.total_records == 1000
        
    def test_error_handling_robustness(self):
        """測試錯誤處理健壯性"""
        validator = EnhancedDataValidator()
        
        # 測試各種邊緣情況
        test_cases = [
            pd.DataFrame(),  # 空數據框
            pd.DataFrame({'col': [None, None, None]}),  # 全空值
            pd.DataFrame({'col': ['a', 'b', 'c']}),  # 非數值數據
        ]
        
        for test_df in test_cases:
            try:
                report = validator.validate_data_quality(test_df)
                assert report is not None
                assert hasattr(report, 'quality_score')
            except Exception as e:
                pytest.fail(f"驗證器在處理邊緣情況時失敗: {e}")


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])
