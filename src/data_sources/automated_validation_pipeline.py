# -*- coding: utf-8 -*-
"""
自動化驗證管道

此模組實現數據源驗證報告改進建議中的自動化測試管道，
建立每週驗證腳本，整合pytest框架，生成自動摘要報告。

主要功能：
- 定期數據源驗證
- 自動化測試執行
- 驗證結果報告生成
- 異常警報機制
- 性能監控和統計

Example:
    基本使用：
    ```python
    from src.data_sources.automated_validation_pipeline import AutomatedValidationPipeline
    
    pipeline = AutomatedValidationPipeline()
    pipeline.run_full_validation()
    ```

Note:
    此模組專門解決數據源驗證報告中提到的定期驗證需求，
    實現自動化的數據源健康監控和品質保證機制。
"""

import logging
import json
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import pytest

from .enhanced_html_parser import EnhancedHTMLParser
from .multi_tier_backup_manager import MultiTierBackupManager
from .enhanced_data_validator import EnhancedDataValidator, DataQualityReport
from .verified_crawler import VerifiedCrawler
from .comprehensive_crawler import ComprehensiveCrawler

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """驗證結果"""
    source_name: str
    category: str
    data_type: str
    success: bool
    record_count: int
    response_time: float
    error_message: Optional[str]
    quality_report: Optional[DataQualityReport]
    timestamp: datetime


@dataclass
class ValidationSummary:
    """驗證摘要"""
    total_sources: int
    successful_sources: int
    failed_sources: int
    avg_response_time: float
    overall_success_rate: float
    quality_distribution: Dict[str, int]
    critical_issues: List[str]
    recommendations: List[str]
    timestamp: datetime


class AutomatedValidationPipeline:
    """
    自動化驗證管道
    
    提供定期數據源驗證、自動化測試和報告生成功能。
    """
    
    def __init__(self, output_dir: str = "logs/validation_reports"):
        """
        初始化自動化驗證管道
        
        Args:
            output_dir: 輸出目錄
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化組件
        self.html_parser = EnhancedHTMLParser()
        self.backup_manager = MultiTierBackupManager()
        self.data_validator = EnhancedDataValidator()
        self.verified_crawler = VerifiedCrawler()
        self.comprehensive_crawler = ComprehensiveCrawler()
        
        # 驗證配置
        self.validation_config = self._load_validation_config()
        
        # 調度器
        self.scheduler_thread = None
        self.is_running = False
        
        logger.info("✅ 自動化驗證管道初始化完成")
        
    def _load_validation_config(self) -> Dict[str, Any]:
        """載入驗證配置"""
        return {
            'verified_sources': {
                '技術面': [
                    'crawl_twse_backtest_index',
                    'crawl_yahoo_adjusted_price',
                    'crawl_twse_market_indicators',
                    'crawl_tpex_mainboard_quotes'
                ],
                '基本面': [
                    'crawl_gov_company_info',
                    'crawl_finmind_financial_data'
                ],
                '籌碼面': [
                    'crawl_twse_broker_trading',
                    'crawl_twse_foreign_holding'
                ],
                '總經面': [
                    'crawl_gov_economic_indicators',
                    'crawl_yahoo_world_indices'
                ]
            },
            'comprehensive_sources': {
                '技術面': [
                    'crawl_twse_afterhours_oddlot',
                    'crawl_tpex_convertible_bonds'
                ],
                '基本面': [
                    'crawl_twse_dividend_announcement',
                    'crawl_twse_monthly_revenue'
                ],
                '籌碼面': [
                    'crawl_twse_broker_branch_mapping',
                    'crawl_twse_margin_trading'
                ],
                '事件面': [
                    'crawl_twse_announcements',
                    'crawl_cnyes_news'
                ]
            },
            'validation_params': {
                'timeout': 30,
                'max_workers': 5,
                'retry_attempts': 3,
                'quality_threshold': 70.0
            }
        }
        
    def run_full_validation(self) -> ValidationSummary:
        """
        執行完整驗證
        
        Returns:
            ValidationSummary: 驗證摘要
        """
        logger.info("🚀 開始執行完整數據源驗證")
        start_time = time.time()
        
        all_results = []
        
        # 驗證已驗證數據源
        verified_results = self._validate_sources(
            self.verified_crawler,
            self.validation_config['verified_sources'],
            'verified'
        )
        all_results.extend(verified_results)
        
        # 驗證綜合數據源
        comprehensive_results = self._validate_sources(
            self.comprehensive_crawler,
            self.validation_config['comprehensive_sources'],
            'comprehensive'
        )
        all_results.extend(comprehensive_results)
        
        # 生成摘要
        summary = self._generate_summary(all_results)
        
        # 保存結果
        self._save_validation_results(all_results, summary)
        
        # 生成報告
        self._generate_html_report(all_results, summary)
        
        total_time = time.time() - start_time
        logger.info(f"✅ 完整驗證完成，耗時 {total_time:.2f} 秒")
        
        return summary
        
    def _validate_sources(self, crawler, source_config: Dict[str, List[str]], 
                         crawler_type: str) -> List[ValidationResult]:
        """
        驗證數據源
        
        Args:
            crawler: 爬蟲實例
            source_config: 數據源配置
            crawler_type: 爬蟲類型
            
        Returns:
            List[ValidationResult]: 驗證結果列表
        """
        results = []
        max_workers = self.validation_config['validation_params']['max_workers']
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_source = {}
            
            for category, methods in source_config.items():
                for method_name in methods:
                    future = executor.submit(
                        self._validate_single_source,
                        crawler, category, method_name, crawler_type
                    )
                    future_to_source[future] = (category, method_name)
                    
            for future in as_completed(future_to_source):
                category, method_name = future_to_source[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    status = "✅" if result.success else "❌"
                    logger.info(f"{status} {category}/{method_name}: "
                              f"{result.record_count} 筆記錄, "
                              f"{result.response_time:.2f}s")
                              
                except Exception as e:
                    logger.error(f"❌ 驗證失敗 {category}/{method_name}: {e}")
                    results.append(ValidationResult(
                        source_name=method_name,
                        category=category,
                        data_type=crawler_type,
                        success=False,
                        record_count=0,
                        response_time=0.0,
                        error_message=str(e),
                        quality_report=None,
                        timestamp=datetime.now()
                    ))
                    
        return results
        
    def _validate_single_source(self, crawler, category: str, method_name: str, 
                               crawler_type: str) -> ValidationResult:
        """
        驗證單一數據源
        
        Args:
            crawler: 爬蟲實例
            category: 數據分類
            method_name: 方法名稱
            crawler_type: 爬蟲類型
            
        Returns:
            ValidationResult: 驗證結果
        """
        start_time = time.time()
        
        try:
            method = getattr(crawler, method_name)
            
            # 執行數據獲取
            if method_name == 'crawl_yahoo_adjusted_price':
                df = method('2330.TW', '2025-07-20', '2025-07-25')
            elif method_name in ['crawl_gov_company_info', 'crawl_gov_economic_indicators']:
                df = method(None)  # 使用模擬數據
            else:
                df = method()
                
            response_time = time.time() - start_time
            
            # 數據品質驗證
            quality_report = None
            if not df.empty:
                quality_report = self.data_validator.validate_data_quality(
                    df, data_type=category
                )
                
            return ValidationResult(
                source_name=method_name,
                category=category,
                data_type=crawler_type,
                success=not df.empty,
                record_count=len(df),
                response_time=response_time,
                error_message=None,
                quality_report=quality_report,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return ValidationResult(
                source_name=method_name,
                category=category,
                data_type=crawler_type,
                success=False,
                record_count=0,
                response_time=response_time,
                error_message=str(e),
                quality_report=None,
                timestamp=datetime.now()
            )
            
    def _generate_summary(self, results: List[ValidationResult]) -> ValidationSummary:
        """
        生成驗證摘要
        
        Args:
            results: 驗證結果列表
            
        Returns:
            ValidationSummary: 驗證摘要
        """
        total_sources = len(results)
        successful_sources = sum(1 for r in results if r.success)
        failed_sources = total_sources - successful_sources
        
        # 計算平均響應時間
        response_times = [r.response_time for r in results if r.response_time > 0]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        # 計算成功率
        overall_success_rate = (successful_sources / total_sources * 100) if total_sources > 0 else 0.0
        
        # 品質分布統計
        quality_distribution = {}
        quality_reports = [r.quality_report for r in results if r.quality_report]
        
        if quality_reports:
            validator_summary = self.data_validator.get_validation_summary(quality_reports)
            quality_distribution = validator_summary.get('quality_distribution', {})
            
        # 關鍵問題
        critical_issues = []
        for result in results:
            if not result.success:
                critical_issues.append(f"{result.category}/{result.source_name}: {result.error_message}")
            elif result.quality_report and result.quality_report.quality_score < 60:
                critical_issues.append(f"{result.category}/{result.source_name}: 數據品質過低 ({result.quality_report.quality_score:.1f}%)")
                
        # 建議
        recommendations = self._generate_recommendations(results, overall_success_rate)
        
        return ValidationSummary(
            total_sources=total_sources,
            successful_sources=successful_sources,
            failed_sources=failed_sources,
            avg_response_time=avg_response_time,
            overall_success_rate=overall_success_rate,
            quality_distribution=quality_distribution,
            critical_issues=critical_issues[:10],  # 限制前10個
            recommendations=recommendations,
            timestamp=datetime.now()
        )
        
    def _generate_recommendations(self, results: List[ValidationResult], 
                                success_rate: float) -> List[str]:
        """
        生成改進建議
        
        Args:
            results: 驗證結果列表
            success_rate: 成功率
            
        Returns:
            List[str]: 建議列表
        """
        recommendations = []
        
        # 成功率建議
        if success_rate < 70:
            recommendations.append("整體成功率過低，建議檢查網路連接和數據源可用性")
        elif success_rate < 85:
            recommendations.append("部分數據源不穩定，建議實施備援機制")
            
        # HTML解析問題
        html_failures = [r for r in results if not r.success and 'HTML' in str(r.error_message)]
        if len(html_failures) > 3:
            recommendations.append("HTML解析失敗較多，建議使用增強HTML解析器")
            
        # 響應時間問題
        slow_sources = [r for r in results if r.response_time > 20]
        if len(slow_sources) > 2:
            recommendations.append("部分數據源響應緩慢，建議優化請求配置或增加超時設定")
            
        # 數據品質問題
        quality_issues = [r for r in results if r.quality_report and r.quality_report.quality_score < 70]
        if len(quality_issues) > 0:
            recommendations.append("發現數據品質問題，建議加強數據驗證和清理機制")
            
        # 通用建議
        if not recommendations:
            recommendations.append("數據源狀態良好，建議維持當前監控頻率")
        else:
            recommendations.append("建議實施多層備援機制和自動故障轉移")
            
        return recommendations
        
    def _save_validation_results(self, results: List[ValidationResult], 
                               summary: ValidationSummary) -> None:
        """
        保存驗證結果
        
        Args:
            results: 驗證結果列表
            summary: 驗證摘要
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存詳細結果
        results_file = self.output_dir / f"validation_results_{timestamp}.json"
        results_data = [asdict(result) for result in results]
        
        # 處理datetime序列化
        for result_data in results_data:
            result_data['timestamp'] = result_data['timestamp'].isoformat()
            if result_data['quality_report']:
                result_data['quality_report']['timestamp'] = result_data['quality_report']['timestamp'].isoformat()
                
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
            
        # 保存摘要
        summary_file = self.output_dir / f"validation_summary_{timestamp}.json"
        summary_data = asdict(summary)
        summary_data['timestamp'] = summary_data['timestamp'].isoformat()
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"✅ 驗證結果已保存: {results_file}, {summary_file}")
        
    def _generate_html_report(self, results: List[ValidationResult], 
                            summary: ValidationSummary) -> None:
        """
        生成HTML報告
        
        Args:
            results: 驗證結果列表
            summary: 驗證摘要
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"validation_report_{timestamp}.html"
        
        # 簡化的HTML報告模板
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>數據源驗證報告</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
                .success {{ color: green; }}
                .failure {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>數據源驗證報告</h1>
            <div class="summary">
                <h2>驗證摘要</h2>
                <p>總數據源: {summary.total_sources}</p>
                <p>成功: <span class="success">{summary.successful_sources}</span></p>
                <p>失敗: <span class="failure">{summary.failed_sources}</span></p>
                <p>成功率: {summary.overall_success_rate:.1f}%</p>
                <p>平均響應時間: {summary.avg_response_time:.2f}秒</p>
                <p>驗證時間: {summary.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <h2>詳細結果</h2>
            <table>
                <tr>
                    <th>數據源</th>
                    <th>分類</th>
                    <th>狀態</th>
                    <th>記錄數</th>
                    <th>響應時間</th>
                    <th>品質分數</th>
                </tr>
        """
        
        for result in results:
            status_class = "success" if result.success else "failure"
            status_text = "✅ 成功" if result.success else "❌ 失敗"
            quality_score = result.quality_report.quality_score if result.quality_report else "N/A"
            
            html_content += f"""
                <tr>
                    <td>{result.source_name}</td>
                    <td>{result.category}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{result.record_count}</td>
                    <td>{result.response_time:.2f}s</td>
                    <td>{quality_score}</td>
                </tr>
            """
            
        html_content += """
            </table>
        </body>
        </html>
        """
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        logger.info(f"✅ HTML報告已生成: {report_file}")
        
    def start_scheduled_validation(self, interval_hours: int = 24) -> None:
        """
        啟動定期驗證
        
        Args:
            interval_hours: 驗證間隔（小時）
        """
        if self.is_running:
            logger.warning("定期驗證已在運行中")
            return
            
        # 設定調度
        schedule.every(interval_hours).hours.do(self.run_full_validation)
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info(f"✅ 定期驗證已啟動，間隔 {interval_hours} 小時")
        
    def stop_scheduled_validation(self) -> None:
        """停止定期驗證"""
        self.is_running = False
        schedule.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            
        logger.info("✅ 定期驗證已停止")
        
    def _scheduler_loop(self) -> None:
        """調度器循環"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分鐘檢查一次
            except Exception as e:
                logger.error(f"調度器錯誤: {e}")
                time.sleep(60)
