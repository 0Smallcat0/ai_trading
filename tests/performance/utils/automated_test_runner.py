"""
自動化測試執行器

此模組實現自動化測試執行和報告生成功能，整合效能測試和安全測試。

功能特性：
- 自動化測試執行
- 測試結果收集
- 綜合報告生成
- 測試指標監控
- 持續整合支援
"""

import logging
import asyncio
import json
import time
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# 導入測試工具
from tests.performance.utils.load_tester import LoadTester, LoadTestConfig
from tests.performance.utils.performance_monitor import PerformanceMonitor
from tests.security.utils.vulnerability_scanner import VulnerabilityScanner
from tests.security.utils.security_scanner import SecurityScanner

logger = logging.getLogger(__name__)


class TestType(str, Enum):
    """測試類型"""

    PERFORMANCE = "performance"
    SECURITY = "security"
    LOAD = "load"
    INTEGRATION = "integration"
    ALL = "all"


class TestStatus(str, Enum):
    """測試狀態"""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """測試結果"""

    test_name: str
    test_type: TestType
    status: TestStatus
    duration: float
    start_time: datetime
    end_time: datetime
    metrics: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    details: Optional[Dict[str, Any]] = None


@dataclass
class TestSuite:
    """測試套件"""

    name: str
    description: str
    tests: List[str]
    config: Dict[str, Any]
    requirements: List[str]


class AutomatedTestRunner:
    """自動化測試執行器"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        """
        初始化測試執行器

        Args:
            base_url: API 基礎 URL
        """
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.test_suites: Dict[str, TestSuite] = {}

        # 測試配置
        self.config = {
            "timeout": 300,  # 5 分鐘
            "retry_count": 3,
            "parallel_execution": True,
            "generate_reports": True,
            "cleanup_after_test": True,
        }

        # 初始化測試工具
        self.load_tester = LoadTester(base_url)
        self.vulnerability_scanner = VulnerabilityScanner(base_url)
        self.security_scanner = SecurityScanner()
        self.performance_monitor = PerformanceMonitor()

    def register_test_suite(self, suite: TestSuite) -> None:
        """
        註冊測試套件

        Args:
            suite: 測試套件
        """
        self.test_suites[suite.name] = suite
        logger.info(f"註冊測試套件: {suite.name}")

    def run_all_tests(self, test_types: List[TestType] = None) -> Dict[str, Any]:
        """
        執行所有測試

        Args:
            test_types: 要執行的測試類型列表

        Returns:
            Dict[str, Any]: 測試執行結果
        """
        if test_types is None:
            test_types = [TestType.PERFORMANCE, TestType.SECURITY, TestType.LOAD]

        logger.info(f"開始執行自動化測試，類型: {test_types}")
        start_time = datetime.now()

        # 清理之前的結果
        self.results = []

        try:
            # 執行不同類型的測試
            for test_type in test_types:
                if test_type == TestType.PERFORMANCE:
                    self._run_performance_tests()
                elif test_type == TestType.SECURITY:
                    self._run_security_tests()
                elif test_type == TestType.LOAD:
                    self._run_load_tests()
                elif test_type == TestType.INTEGRATION:
                    self._run_integration_tests()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # 生成測試報告
            report_data = self._generate_test_report(duration)

            # 保存報告
            if self.config["generate_reports"]:
                self._save_reports(report_data)

            logger.info(f"自動化測試完成，總時長: {duration:.2f}s")
            return report_data

        except Exception as e:
            logger.error(f"自動化測試執行失敗: {e}")
            raise

    def _run_performance_tests(self) -> None:
        """執行效能測試"""
        logger.info("開始執行效能測試")

        # API 回應時間測試
        self._test_api_response_time()

        # 記憶體使用測試
        self._test_memory_usage()

        # CPU 使用測試
        self._test_cpu_usage()

    def _test_api_response_time(self) -> None:
        """測試 API 回應時間"""
        test_name = "API 回應時間測試"
        start_time = datetime.now()

        try:
            # 測試關鍵端點
            endpoints = [
                "/health",
                "/api/v1/versions/",
                "/api/v1/data/",
                "/api/v1/strategies/",
            ]

            response_times = []
            errors = []

            for endpoint in endpoints:
                try:
                    import requests

                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                    response_times.append(response.elapsed.total_seconds() * 1000)
                except Exception as e:
                    errors.append(f"端點 {endpoint} 測試失敗: {e}")

            # 計算指標
            avg_response_time = (
                sum(response_times) / len(response_times) if response_times else 0
            )
            max_response_time = max(response_times) if response_times else 0

            # 判斷測試結果
            status = TestStatus.PASSED
            if avg_response_time > 100:  # 100ms 閾值
                status = TestStatus.FAILED
                errors.append(f"平均回應時間 {avg_response_time:.1f}ms 超過閾值")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.results.append(
                TestResult(
                    test_name=test_name,
                    test_type=TestType.PERFORMANCE,
                    status=status,
                    duration=duration,
                    start_time=start_time,
                    end_time=end_time,
                    metrics={
                        "avg_response_time": avg_response_time,
                        "max_response_time": max_response_time,
                        "tested_endpoints": len(endpoints),
                        "successful_requests": len(response_times),
                    },
                    errors=errors,
                    warnings=[],
                )
            )

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.results.append(
                TestResult(
                    test_name=test_name,
                    test_type=TestType.PERFORMANCE,
                    status=TestStatus.ERROR,
                    duration=duration,
                    start_time=start_time,
                    end_time=end_time,
                    metrics={},
                    errors=[str(e)],
                    warnings=[],
                )
            )

    def _test_memory_usage(self) -> None:
        """測試記憶體使用"""
        test_name = "記憶體使用測試"
        start_time = datetime.now()

        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # 執行一些操作來測試記憶體使用
            for _ in range(100):
                import requests

                try:
                    requests.get(f"{self.base_url}/health", timeout=5)
                except:
                    pass

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            # 判斷結果
            status = TestStatus.PASSED
            errors = []
            warnings = []

            if memory_increase > 50:  # 50MB 閾值
                status = TestStatus.FAILED
                errors.append(f"記憶體增長 {memory_increase:.2f}MB 超過閾值")
            elif memory_increase > 20:  # 20MB 警告
                warnings.append(f"記憶體增長 {memory_increase:.2f}MB 較高")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.results.append(
                TestResult(
                    test_name=test_name,
                    test_type=TestType.PERFORMANCE,
                    status=status,
                    duration=duration,
                    start_time=start_time,
                    end_time=end_time,
                    metrics={
                        "initial_memory_mb": initial_memory,
                        "final_memory_mb": final_memory,
                        "memory_increase_mb": memory_increase,
                    },
                    errors=errors,
                    warnings=warnings,
                )
            )

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.results.append(
                TestResult(
                    test_name=test_name,
                    test_type=TestType.PERFORMANCE,
                    status=TestStatus.ERROR,
                    duration=duration,
                    start_time=start_time,
                    end_time=end_time,
                    metrics={},
                    errors=[str(e)],
                    warnings=[],
                )
            )

    def _test_cpu_usage(self) -> None:
        """測試 CPU 使用"""
        test_name = "CPU 使用測試"
        start_time = datetime.now()

        try:
            import psutil

            # 監控 CPU 使用率
            cpu_percentages = []
            for _ in range(10):
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_percentages.append(cpu_percent)

            avg_cpu = sum(cpu_percentages) / len(cpu_percentages)
            max_cpu = max(cpu_percentages)

            # 判斷結果
            status = TestStatus.PASSED
            errors = []
            warnings = []

            if avg_cpu > 80:  # 80% 閾值
                status = TestStatus.FAILED
                errors.append(f"平均 CPU 使用率 {avg_cpu:.1f}% 過高")
            elif avg_cpu > 60:  # 60% 警告
                warnings.append(f"平均 CPU 使用率 {avg_cpu:.1f}% 較高")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.results.append(
                TestResult(
                    test_name=test_name,
                    test_type=TestType.PERFORMANCE,
                    status=status,
                    duration=duration,
                    start_time=start_time,
                    end_time=end_time,
                    metrics={
                        "avg_cpu_percent": avg_cpu,
                        "max_cpu_percent": max_cpu,
                        "samples": len(cpu_percentages),
                    },
                    errors=errors,
                    warnings=warnings,
                )
            )

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.results.append(
                TestResult(
                    test_name=test_name,
                    test_type=TestType.PERFORMANCE,
                    status=TestStatus.ERROR,
                    duration=duration,
                    start_time=start_time,
                    end_time=end_time,
                    metrics={},
                    errors=[str(e)],
                    warnings=[],
                )
            )

    def _run_security_tests(self) -> None:
        """執行安全測試"""
        logger.info("開始執行安全測試")

        test_name = "安全漏洞掃描"
        start_time = datetime.now()

        try:
            # 掃描端點
            endpoints = ["/api/v1/versions/", "/api/v1/auth/login", "/api/v1/data/"]

            # 執行漏洞掃描
            vulnerabilities = self.vulnerability_scanner.scan_all_vulnerabilities(
                endpoints
            )

            # 統計漏洞
            critical_count = sum(
                1 for v in vulnerabilities if v.level.value == "critical"
            )
            high_count = sum(1 for v in vulnerabilities if v.level.value == "high")
            medium_count = sum(1 for v in vulnerabilities if v.level.value == "medium")

            # 判斷結果
            status = TestStatus.PASSED
            errors = []
            warnings = []

            if critical_count > 0:
                status = TestStatus.FAILED
                errors.append(f"發現 {critical_count} 個嚴重漏洞")
            elif high_count > 0:
                status = TestStatus.FAILED
                errors.append(f"發現 {high_count} 個高危漏洞")
            elif medium_count > 3:
                warnings.append(f"發現 {medium_count} 個中等漏洞")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.results.append(
                TestResult(
                    test_name=test_name,
                    test_type=TestType.SECURITY,
                    status=status,
                    duration=duration,
                    start_time=start_time,
                    end_time=end_time,
                    metrics={
                        "total_vulnerabilities": len(vulnerabilities),
                        "critical_count": critical_count,
                        "high_count": high_count,
                        "medium_count": medium_count,
                        "scanned_endpoints": len(endpoints),
                    },
                    errors=errors,
                    warnings=warnings,
                    details={"vulnerabilities": [asdict(v) for v in vulnerabilities]},
                )
            )

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.results.append(
                TestResult(
                    test_name=test_name,
                    test_type=TestType.SECURITY,
                    status=TestStatus.ERROR,
                    duration=duration,
                    start_time=start_time,
                    end_time=end_time,
                    metrics={},
                    errors=[str(e)],
                    warnings=[],
                )
            )

    def _run_load_tests(self) -> None:
        """執行負載測試"""
        logger.info("開始執行負載測試")

        test_name = "負載測試"
        start_time = datetime.now()

        try:
            # 負載測試配置
            config = LoadTestConfig(
                concurrent_users=20, test_duration=60, ramp_up_time=10, think_time=1.0
            )

            # 測試場景
            scenarios = [
                {"method": "GET", "url": "/health"},
                {"method": "GET", "url": "/api/v1/versions/"},
            ]

            # 執行負載測試
            result = self.load_tester.run_load_test(scenarios, config)

            # 判斷結果
            status = TestStatus.PASSED
            errors = []
            warnings = []

            if result.avg_response_time > 100:
                status = TestStatus.FAILED
                errors.append(f"平均回應時間 {result.avg_response_time:.1f}ms 超過閾值")

            if result.throughput < 10:
                status = TestStatus.FAILED
                errors.append(f"吞吐量 {result.throughput:.1f} req/s 過低")

            success_rate = result.successful_requests / result.total_requests
            if success_rate < 0.95:
                status = TestStatus.FAILED
                errors.append(f"成功率 {success_rate*100:.1f}% 過低")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.results.append(
                TestResult(
                    test_name=test_name,
                    test_type=TestType.LOAD,
                    status=status,
                    duration=duration,
                    start_time=start_time,
                    end_time=end_time,
                    metrics={
                        "avg_response_time": result.avg_response_time,
                        "throughput": result.throughput,
                        "total_requests": result.total_requests,
                        "successful_requests": result.successful_requests,
                        "failed_requests": result.failed_requests,
                        "success_rate": success_rate,
                    },
                    errors=errors,
                    warnings=warnings,
                )
            )

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.results.append(
                TestResult(
                    test_name=test_name,
                    test_type=TestType.LOAD,
                    status=TestStatus.ERROR,
                    duration=duration,
                    start_time=start_time,
                    end_time=end_time,
                    metrics={},
                    errors=[str(e)],
                    warnings=[],
                )
            )

    def _run_integration_tests(self) -> None:
        """執行整合測試"""
        logger.info("開始執行整合測試")
        # 整合測試實現
        pass

    def _generate_test_report(self, total_duration: float) -> Dict[str, Any]:
        """生成測試報告"""
        # 統計結果
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed_tests = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        error_tests = sum(1 for r in self.results if r.status == TestStatus.ERROR)

        # 按類型統計
        type_summary = {}
        for test_type in TestType:
            type_results = [r for r in self.results if r.test_type == test_type]
            if type_results:
                type_summary[test_type.value] = {
                    "total": len(type_results),
                    "passed": sum(
                        1 for r in type_results if r.status == TestStatus.PASSED
                    ),
                    "failed": sum(
                        1 for r in type_results if r.status == TestStatus.FAILED
                    ),
                    "error": sum(
                        1 for r in type_results if r.status == TestStatus.ERROR
                    ),
                }

        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "error_tests": error_tests,
                "success_rate": (
                    (passed_tests / total_tests * 100) if total_tests > 0 else 0
                ),
                "total_duration": total_duration,
                "execution_time": datetime.now().isoformat(),
            },
            "type_summary": type_summary,
            "test_results": [asdict(result) for result in self.results],
        }

    def _save_reports(self, report_data: Dict[str, Any]) -> None:
        """保存測試報告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON 報告
        json_file = f"automated_test_report_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"測試報告已保存: {json_file}")


if __name__ == "__main__":
    # 示例使用
    runner = AutomatedTestRunner()
    results = runner.run_all_tests([TestType.PERFORMANCE, TestType.SECURITY])
    print(f"測試完成，成功率: {results['summary']['success_rate']:.1f}%")
