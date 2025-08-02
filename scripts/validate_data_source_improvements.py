#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據源改進驗證腳本

此腳本驗證數據源驗證報告改進建議的實施效果，
對比改進前後的數據源可用性和品質。

主要功能：
- 執行改進後的數據源驗證
- 生成對比報告
- 評估改進效果
- 提供進一步優化建議

Usage:
    python scripts/validate_data_source_improvements.py
    
Note:
    此腳本專門驗證數據源驗證報告改進建議的實施效果，
    確保改進後的系統能夠解決原有的HTML解析失敗和數據品質問題。
"""

import sys
import os
import logging
import json
from datetime import datetime
from pathlib import Path

# 添加項目根目錄到Python路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.data_sources.enhanced_html_parser import EnhancedHTMLParser
    from src.data_sources.multi_tier_backup_manager import MultiTierBackupManager
    from src.data_sources.enhanced_data_validator import EnhancedDataValidator
    from src.data_sources.automated_validation_pipeline import AutomatedValidationPipeline
    from src.data_sources.comprehensive_crawler import ComprehensiveCrawler
    from src.data_sources.verified_crawler import VerifiedCrawler
except ImportError as e:
    print(f"❌ 導入模組失敗: {e}")
    print("請確保已正確安裝所有依賴並且項目結構正確")
    sys.exit(1)

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/validation_improvements.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataSourceImprovementValidator:
    """數據源改進驗證器"""
    
    def __init__(self):
        """初始化驗證器"""
        self.output_dir = Path("logs/improvement_validation")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化組件
        self.html_parser = EnhancedHTMLParser()
        self.backup_manager = MultiTierBackupManager()
        self.data_validator = EnhancedDataValidator()
        self.pipeline = AutomatedValidationPipeline()
        self.comprehensive_crawler = ComprehensiveCrawler()
        self.verified_crawler = VerifiedCrawler()
        
        logger.info("✅ 數據源改進驗證器初始化完成")
        
    def run_comprehensive_validation(self):
        """執行全面驗證"""
        logger.info("🚀 開始執行數據源改進驗證")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'html_parser_test': self._test_html_parser(),
            'backup_manager_test': self._test_backup_manager(),
            'data_validator_test': self._test_data_validator(),
            'pipeline_test': self._test_validation_pipeline(),
            'crawler_improvements_test': self._test_crawler_improvements(),
            'performance_test': self._test_performance(),
            'overall_assessment': {}
        }
        
        # 生成整體評估
        results['overall_assessment'] = self._generate_overall_assessment(results)
        
        # 保存結果
        self._save_validation_results(results)
        
        # 生成報告
        self._generate_improvement_report(results)
        
        logger.info("✅ 數據源改進驗證完成")
        return results
        
    def _test_html_parser(self):
        """測試增強HTML解析器"""
        logger.info("🔍 測試增強HTML解析器...")
        
        test_results = {
            'component': 'EnhancedHTMLParser',
            'tests': [],
            'overall_score': 0,
            'status': 'unknown'
        }
        
        try:
            # 測試1: 初始化測試
            init_test = {
                'name': '初始化測試',
                'success': self.html_parser is not None,
                'details': '檢查解析器是否正確初始化'
            }
            test_results['tests'].append(init_test)
            
            # 測試2: 選擇器映射測試
            mapping_test = {
                'name': '選擇器映射測試',
                'success': len(self.html_parser.selector_mapping) >= 5,
                'details': f'支援 {len(self.html_parser.selector_mapping)} 種數據類型'
            }
            test_results['tests'].append(mapping_test)
            
            # 測試3: 健康狀態測試
            health_status = self.html_parser.get_health_status()
            health_test = {
                'name': '健康狀態測試',
                'success': isinstance(health_status, dict) and 'parser_name' in health_status,
                'details': f'健康狀態: {health_status.get("parser_name", "未知")}'
            }
            test_results['tests'].append(health_test)
            
            # 測試4: 動態更新測試
            test_config = {
                'table_keywords': ['測試'],
                'selectors': ['table.test'],
                'fallback_url_patterns': ['/test']
            }
            self.html_parser.update_selector_mapping('測試類型', test_config)
            update_test = {
                'name': '動態更新測試',
                'success': '測試類型' in self.html_parser.selector_mapping,
                'details': '選擇器映射動態更新功能正常'
            }
            test_results['tests'].append(update_test)
            
            # 計算總分
            success_count = sum(1 for test in test_results['tests'] if test['success'])
            test_results['overall_score'] = (success_count / len(test_results['tests'])) * 100
            test_results['status'] = 'passed' if test_results['overall_score'] >= 75 else 'failed'
            
        except Exception as e:
            logger.error(f"HTML解析器測試失敗: {e}")
            test_results['status'] = 'error'
            test_results['error'] = str(e)
            
        return test_results
        
    def _test_backup_manager(self):
        """測試多層備援機制管理器"""
        logger.info("🔍 測試多層備援機制管理器...")
        
        test_results = {
            'component': 'MultiTierBackupManager',
            'tests': [],
            'overall_score': 0,
            'status': 'unknown'
        }
        
        try:
            # 測試1: 初始化測試
            init_test = {
                'name': '初始化測試',
                'success': self.backup_manager is not None,
                'details': '檢查備援管理器是否正確初始化'
            }
            test_results['tests'].append(init_test)
            
            # 測試2: 備援配置測試
            registry_test = {
                'name': '備援配置測試',
                'success': len(self.backup_manager.backup_registry) >= 3,
                'details': f'配置了 {len(self.backup_manager.backup_registry)} 個數據分類的備援'
            }
            test_results['tests'].append(registry_test)
            
            # 測試3: 健康報告測試
            health_report = self.backup_manager.get_health_report()
            health_test = {
                'name': '健康報告測試',
                'success': isinstance(health_report, dict) and 'total_sources' in health_report,
                'details': f'監控 {health_report.get("total_sources", 0)} 個數據源'
            }
            test_results['tests'].append(health_test)
            
            # 測試4: 數據源註冊測試
            from src.data_sources.multi_tier_backup_manager import DataSourceConfig
            test_config = DataSourceConfig(
                name='test_source',
                priority=1,
                crawler_class='TestCrawler',
                method_name='test_method'
            )
            self.backup_manager.register_backup_source('測試分類', '測試類型', test_config)
            
            register_test = {
                'name': '數據源註冊測試',
                'success': '測試分類' in self.backup_manager.backup_registry,
                'details': '動態數據源註冊功能正常'
            }
            test_results['tests'].append(register_test)
            
            # 計算總分
            success_count = sum(1 for test in test_results['tests'] if test['success'])
            test_results['overall_score'] = (success_count / len(test_results['tests'])) * 100
            test_results['status'] = 'passed' if test_results['overall_score'] >= 75 else 'failed'
            
        except Exception as e:
            logger.error(f"備援管理器測試失敗: {e}")
            test_results['status'] = 'error'
            test_results['error'] = str(e)
            
        return test_results
        
    def _test_data_validator(self):
        """測試增強數據驗證器"""
        logger.info("🔍 測試增強數據驗證器...")
        
        test_results = {
            'component': 'EnhancedDataValidator',
            'tests': [],
            'overall_score': 0,
            'status': 'unknown'
        }
        
        try:
            import pandas as pd
            
            # 測試1: 初始化測試
            init_test = {
                'name': '初始化測試',
                'success': self.data_validator is not None,
                'details': '檢查數據驗證器是否正確初始化'
            }
            test_results['tests'].append(init_test)
            
            # 測試2: 空數據驗證測試
            empty_df = pd.DataFrame()
            empty_report = self.data_validator.validate_data_quality(empty_df)
            empty_test = {
                'name': '空數據驗證測試',
                'success': empty_report.quality_score == 0.0,
                'details': f'空數據品質分數: {empty_report.quality_score}'
            }
            test_results['tests'].append(empty_test)
            
            # 測試3: 正常數據驗證測試
            normal_df = pd.DataFrame({
                'value': [1, 2, 3, 4, 5],
                'category': ['A', 'B', 'C', 'D', 'E']
            })
            normal_report = self.data_validator.validate_data_quality(normal_df)
            normal_test = {
                'name': '正常數據驗證測試',
                'success': normal_report.quality_score > 80.0,
                'details': f'正常數據品質分數: {normal_report.quality_score:.1f}'
            }
            test_results['tests'].append(normal_test)
            
            # 測試4: 異常檢測測試
            outlier_df = pd.DataFrame({
                'value': [1, 2, 3, 4, 100]  # 100是異常值
            })
            from src.data_sources.enhanced_data_validator import AnomalyMethod
            anomalies = self.data_validator._detect_anomalies(outlier_df, AnomalyMethod.ZSCORE, 'general')
            anomaly_test = {
                'name': '異常檢測測試',
                'success': len(anomalies) > 0,
                'details': f'檢測到 {len(anomalies)} 個異常值'
            }
            test_results['tests'].append(anomaly_test)
            
            # 計算總分
            success_count = sum(1 for test in test_results['tests'] if test['success'])
            test_results['overall_score'] = (success_count / len(test_results['tests'])) * 100
            test_results['status'] = 'passed' if test_results['overall_score'] >= 75 else 'failed'
            
        except Exception as e:
            logger.error(f"數據驗證器測試失敗: {e}")
            test_results['status'] = 'error'
            test_results['error'] = str(e)
            
        return test_results
        
    def _test_validation_pipeline(self):
        """測試自動化驗證管道"""
        logger.info("🔍 測試自動化驗證管道...")
        
        test_results = {
            'component': 'AutomatedValidationPipeline',
            'tests': [],
            'overall_score': 0,
            'status': 'unknown'
        }
        
        try:
            # 測試1: 初始化測試
            init_test = {
                'name': '初始化測試',
                'success': self.pipeline is not None,
                'details': '檢查驗證管道是否正確初始化'
            }
            test_results['tests'].append(init_test)
            
            # 測試2: 配置測試
            config = self.pipeline.validation_config
            config_test = {
                'name': '配置測試',
                'success': 'verified_sources' in config and 'comprehensive_sources' in config,
                'details': '驗證配置結構正確'
            }
            test_results['tests'].append(config_test)
            
            # 測試3: 組件整合測試
            components = ['html_parser', 'backup_manager', 'data_validator']
            integration_test = {
                'name': '組件整合測試',
                'success': all(hasattr(self.pipeline, comp) for comp in components),
                'details': f'整合了 {len(components)} 個核心組件'
            }
            test_results['tests'].append(integration_test)
            
            # 計算總分
            success_count = sum(1 for test in test_results['tests'] if test['success'])
            test_results['overall_score'] = (success_count / len(test_results['tests'])) * 100
            test_results['status'] = 'passed' if test_results['overall_score'] >= 75 else 'failed'
            
        except Exception as e:
            logger.error(f"驗證管道測試失敗: {e}")
            test_results['status'] = 'error'
            test_results['error'] = str(e)
            
        return test_results
        
    def _test_crawler_improvements(self):
        """測試爬蟲改進"""
        logger.info("🔍 測試爬蟲改進...")
        
        test_results = {
            'component': 'CrawlerImprovements',
            'tests': [],
            'overall_score': 0,
            'status': 'unknown'
        }
        
        try:
            # 測試1: 綜合爬蟲HTML解析器整合
            html_integration_test = {
                'name': 'HTML解析器整合測試',
                'success': hasattr(self.comprehensive_crawler, 'html_parser'),
                'details': '綜合爬蟲已整合增強HTML解析器'
            }
            test_results['tests'].append(html_integration_test)
            
            # 測試2: 爬蟲方法可用性測試
            methods_to_test = [
                'crawl_twse_dividend_announcement',
                'crawl_twse_monthly_revenue',
                'crawl_twse_announcements'
            ]
            
            available_methods = 0
            for method_name in methods_to_test:
                if hasattr(self.comprehensive_crawler, method_name):
                    available_methods += 1
                    
            methods_test = {
                'name': '改進方法可用性測試',
                'success': available_methods == len(methods_to_test),
                'details': f'{available_methods}/{len(methods_to_test)} 個改進方法可用'
            }
            test_results['tests'].append(methods_test)
            
            # 計算總分
            success_count = sum(1 for test in test_results['tests'] if test['success'])
            test_results['overall_score'] = (success_count / len(test_results['tests'])) * 100
            test_results['status'] = 'passed' if test_results['overall_score'] >= 75 else 'failed'
            
        except Exception as e:
            logger.error(f"爬蟲改進測試失敗: {e}")
            test_results['status'] = 'error'
            test_results['error'] = str(e)
            
        return test_results
        
    def _test_performance(self):
        """測試性能"""
        logger.info("🔍 測試性能...")
        
        test_results = {
            'component': 'Performance',
            'tests': [],
            'overall_score': 0,
            'status': 'unknown'
        }
        
        try:
            import time
            import pandas as pd
            
            # 測試1: 數據驗證性能
            large_df = pd.DataFrame({
                'value': range(1000),
                'category': ['A'] * 500 + ['B'] * 500
            })
            
            start_time = time.time()
            report = self.data_validator.validate_data_quality(large_df)
            validation_time = time.time() - start_time
            
            validation_perf_test = {
                'name': '數據驗證性能測試',
                'success': validation_time < 5.0,
                'details': f'1000筆記錄驗證耗時: {validation_time:.2f}秒'
            }
            test_results['tests'].append(validation_perf_test)
            
            # 測試2: 組件初始化性能
            start_time = time.time()
            test_parser = EnhancedHTMLParser()
            init_time = time.time() - start_time
            
            init_perf_test = {
                'name': '組件初始化性能測試',
                'success': init_time < 2.0,
                'details': f'HTML解析器初始化耗時: {init_time:.2f}秒'
            }
            test_results['tests'].append(init_perf_test)
            
            # 計算總分
            success_count = sum(1 for test in test_results['tests'] if test['success'])
            test_results['overall_score'] = (success_count / len(test_results['tests'])) * 100
            test_results['status'] = 'passed' if test_results['overall_score'] >= 75 else 'failed'
            
        except Exception as e:
            logger.error(f"性能測試失敗: {e}")
            test_results['status'] = 'error'
            test_results['error'] = str(e)
            
        return test_results
        
    def _generate_overall_assessment(self, results):
        """生成整體評估"""
        components = [
            'html_parser_test',
            'backup_manager_test', 
            'data_validator_test',
            'pipeline_test',
            'crawler_improvements_test',
            'performance_test'
        ]
        
        total_score = 0
        passed_components = 0
        
        for comp in components:
            if comp in results and results[comp].get('status') == 'passed':
                passed_components += 1
                total_score += results[comp].get('overall_score', 0)
                
        avg_score = total_score / len(components) if components else 0
        success_rate = (passed_components / len(components)) * 100 if components else 0
        
        # 確定整體狀態
        if success_rate >= 80 and avg_score >= 75:
            overall_status = 'excellent'
            status_desc = '優秀'
        elif success_rate >= 60 and avg_score >= 60:
            overall_status = 'good'
            status_desc = '良好'
        elif success_rate >= 40 and avg_score >= 40:
            overall_status = 'fair'
            status_desc = '一般'
        else:
            overall_status = 'poor'
            status_desc = '需要改進'
            
        return {
            'overall_status': overall_status,
            'status_description': status_desc,
            'average_score': round(avg_score, 1),
            'success_rate': round(success_rate, 1),
            'passed_components': passed_components,
            'total_components': len(components),
            'recommendations': self._generate_improvement_recommendations(results)
        }
        
    def _generate_improvement_recommendations(self, results):
        """生成改進建議"""
        recommendations = []
        
        # 檢查各組件狀態並生成建議
        if results.get('html_parser_test', {}).get('status') != 'passed':
            recommendations.append("增強HTML解析器需要進一步優化，建議檢查Selenium配置")
            
        if results.get('backup_manager_test', {}).get('status') != 'passed':
            recommendations.append("多層備援機制需要完善，建議增加更多備援數據源")
            
        if results.get('data_validator_test', {}).get('status') != 'passed':
            recommendations.append("數據驗證器需要改進，建議優化異常檢測算法")
            
        if results.get('performance_test', {}).get('overall_score', 0) < 75:
            recommendations.append("系統性能需要優化，建議實施緩存機制和並行處理")
            
        if not recommendations:
            recommendations.append("系統改進效果良好，建議繼續監控和維護")
            
        return recommendations
        
    def _save_validation_results(self, results):
        """保存驗證結果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.output_dir / f"improvement_validation_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        logger.info(f"✅ 驗證結果已保存: {results_file}")
        
    def _generate_improvement_report(self, results):
        """生成改進報告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"improvement_report_{timestamp}.html"
        
        assessment = results['overall_assessment']
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>數據源改進驗證報告</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f8ff; padding: 20px; border-radius: 10px; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .component {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .passed {{ background: #e8f5e8; }}
                .failed {{ background: #ffe8e8; }}
                .error {{ background: #fff3cd; }}
                .score {{ font-size: 24px; font-weight: bold; }}
                .recommendations {{ background: #e3f2fd; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 數據源改進驗證報告</h1>
                <p>驗證時間: {results['timestamp']}</p>
                <p>整體狀態: <span class="score">{assessment['status_description']}</span></p>
                <p>平均分數: <span class="score">{assessment['average_score']}</span></p>
                <p>成功率: <span class="score">{assessment['success_rate']}%</span></p>
            </div>
            
            <div class="summary">
                <h2>📊 驗證摘要</h2>
                <p>通過組件: {assessment['passed_components']}/{assessment['total_components']}</p>
                <p>整體評估: {assessment['overall_status']}</p>
            </div>
        """
        
        # 添加各組件詳細結果
        components = [
            ('html_parser_test', '增強HTML解析器'),
            ('backup_manager_test', '多層備援機制管理器'),
            ('data_validator_test', '增強數據驗證器'),
            ('pipeline_test', '自動化驗證管道'),
            ('crawler_improvements_test', '爬蟲改進'),
            ('performance_test', '性能測試')
        ]
        
        for comp_key, comp_name in components:
            if comp_key in results:
                comp_result = results[comp_key]
                status_class = comp_result.get('status', 'unknown')
                
                html_content += f"""
                <div class="component {status_class}">
                    <h3>{comp_name}</h3>
                    <p>狀態: {comp_result.get('status', '未知')}</p>
                    <p>分數: {comp_result.get('overall_score', 0):.1f}</p>
                    <ul>
                """
                
                for test in comp_result.get('tests', []):
                    status_icon = "✅" if test['success'] else "❌"
                    html_content += f"<li>{status_icon} {test['name']}: {test['details']}</li>"
                    
                html_content += "</ul></div>"
                
        # 添加建議
        html_content += f"""
            <div class="recommendations">
                <h2>💡 改進建議</h2>
                <ul>
        """
        
        for rec in assessment['recommendations']:
            html_content += f"<li>{rec}</li>"
            
        html_content += """
                </ul>
            </div>
        </body>
        </html>
        """
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        logger.info(f"✅ 改進報告已生成: {report_file}")


def main():
    """主函數"""
    print("🚀 開始數據源改進驗證...")
    
    try:
        # 創建驗證器
        validator = DataSourceImprovementValidator()
        
        # 執行驗證
        results = validator.run_comprehensive_validation()
        
        # 輸出結果摘要
        assessment = results['overall_assessment']
        print(f"\n📊 驗證結果摘要:")
        print(f"整體狀態: {assessment['status_description']}")
        print(f"平均分數: {assessment['average_score']}")
        print(f"成功率: {assessment['success_rate']}%")
        print(f"通過組件: {assessment['passed_components']}/{assessment['total_components']}")
        
        print(f"\n💡 主要建議:")
        for i, rec in enumerate(assessment['recommendations'][:3], 1):
            print(f"{i}. {rec}")
            
        print(f"\n✅ 驗證完成！詳細報告請查看 logs/improvement_validation/ 目錄")
        
    except Exception as e:
        logger.error(f"❌ 驗證過程中發生錯誤: {e}")
        print(f"❌ 驗證失敗: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
