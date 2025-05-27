#!/usr/bin/env python3
"""
綜合測試執行腳本

此腳本執行完整的測試套件，包括：
1. 單元測試 (pytest)
2. 程式碼覆蓋率測試 (coverage)
3. 效能測試
4. 安全測試
5. 整合測試
6. 程式碼品質檢查
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple
import json
from datetime import datetime

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ComprehensiveTestRunner:
    """綜合測試執行器"""

    def __init__(self):
        self.project_root = project_root
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'unit_tests': {},
            'coverage': {},
            'performance_tests': {},
            'security_tests': {},
            'integration_tests': {},
            'code_quality': {},
            'summary': {}
        }
        self.min_coverage = 70  # 最低覆蓋率要求
        self.target_coverage = 80  # 目標覆蓋率

    def run_command(self, command: str, cwd: str = None, timeout: int = 300) -> Tuple[int, str, str]:
        """執行命令並返回結果"""
        try:
            print(f"🔧 執行命令: {command}")
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return 1, "", str(e)

    def run_unit_tests(self) -> Dict:
        """執行單元測試"""
        print("\n" + "="*60)
        print("🧪 執行單元測試")
        print("="*60)

        # 基本 pytest 執行
        command = "python -m pytest tests/ -v --tb=short --durations=10"
        returncode, stdout, stderr = self.run_command(command)

        # 解析測試結果
        test_results = {
            'returncode': returncode,
            'passed': stdout.count(' PASSED'),
            'failed': stdout.count(' FAILED'),
            'skipped': stdout.count(' SKIPPED'),
            'errors': stdout.count(' ERROR'),
            'output': stdout,
            'errors_output': stderr
        }

        # 計算成功率
        total_tests = test_results['passed'] + test_results['failed'] + test_results['errors']
        if total_tests > 0:
            test_results['success_rate'] = (test_results['passed'] / total_tests) * 100
        else:
            test_results['success_rate'] = 0

        print(f"✅ 通過: {test_results['passed']}")
        print(f"❌ 失敗: {test_results['failed']}")
        print(f"⚠️ 錯誤: {test_results['errors']}")
        print(f"⏭️ 跳過: {test_results['skipped']}")
        print(f"📊 成功率: {test_results['success_rate']:.1f}%")

        self.test_results['unit_tests'] = test_results
        return test_results

    def run_coverage_tests(self) -> Dict:
        """執行覆蓋率測試"""
        print("\n" + "="*60)
        print("📊 執行覆蓋率測試")
        print("="*60)

        # 執行覆蓋率測試
        command = "python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml"
        returncode, stdout, stderr = self.run_command(command)

        # 解析覆蓋率結果
        coverage_results = {
            'returncode': returncode,
            'output': stdout,
            'errors_output': stderr
        }

        # 從輸出中提取覆蓋率百分比
        import re
        coverage_pattern = r'TOTAL\s+\d+\s+\d+\s+(\d+)%'
        match = re.search(coverage_pattern, stdout)

        if match:
            coverage_results['total_coverage'] = int(match.group(1))
        else:
            coverage_results['total_coverage'] = 0

        # 檢查是否達到目標
        coverage_results['meets_minimum'] = coverage_results['total_coverage'] >= self.min_coverage
        coverage_results['meets_target'] = coverage_results['total_coverage'] >= self.target_coverage

        print(f"📈 總覆蓋率: {coverage_results['total_coverage']}%")
        print(f"🎯 最低要求 ({self.min_coverage}%): {'✅ 達成' if coverage_results['meets_minimum'] else '❌ 未達成'}")
        print(f"🏆 目標 ({self.target_coverage}%): {'✅ 達成' if coverage_results['meets_target'] else '⚠️ 未達成'}")

        self.test_results['coverage'] = coverage_results
        return coverage_results

    def run_performance_tests(self) -> Dict:
        """執行效能測試"""
        print("\n" + "="*60)
        print("⚡ 執行效能測試")
        print("="*60)

        performance_results = {
            'api_performance': {},
            'memory_profiling': {},
            'load_testing': {}
        }

        # API 效能測試
        if (self.project_root / "tests" / "performance" / "test_api_performance.py").exists():
            command = "python -m pytest tests/performance/test_api_performance.py -v"
            returncode, stdout, stderr = self.run_command(command)
            performance_results['api_performance'] = {
                'returncode': returncode,
                'output': stdout,
                'errors': stderr
            }
            print(f"🔌 API 效能測試: {'✅ 通過' if returncode == 0 else '❌ 失敗'}")

        # 記憶體分析測試
        if (self.project_root / "tests" / "performance" / "test_memory_profiling.py").exists():
            command = "python -m pytest tests/performance/test_memory_profiling.py -v"
            returncode, stdout, stderr = self.run_command(command)
            performance_results['memory_profiling'] = {
                'returncode': returncode,
                'output': stdout,
                'errors': stderr
            }
            print(f"🧠 記憶體分析測試: {'✅ 通過' if returncode == 0 else '❌ 失敗'}")

        # 負載測試
        if (self.project_root / "tests" / "performance" / "test_load_testing.py").exists():
            command = "python -m pytest tests/performance/test_load_testing.py -v"
            returncode, stdout, stderr = self.run_command(command)
            performance_results['load_testing'] = {
                'returncode': returncode,
                'output': stdout,
                'errors': stderr
            }
            print(f"🏋️ 負載測試: {'✅ 通過' if returncode == 0 else '❌ 失敗'}")

        self.test_results['performance_tests'] = performance_results
        return performance_results

    def run_security_tests(self) -> Dict:
        """執行安全測試"""
        print("\n" + "="*60)
        print("🔒 執行安全測試")
        print("="*60)

        security_results = {
            'jwt_security': {},
            'sql_injection': {},
            'xss_protection': {},
            'rbac_permissions': {}
        }

        # JWT 安全測試
        if (self.project_root / "tests" / "security" / "test_jwt_security.py").exists():
            command = "python -m pytest tests/security/test_jwt_security.py -v"
            returncode, stdout, stderr = self.run_command(command)
            security_results['jwt_security'] = {
                'returncode': returncode,
                'output': stdout,
                'errors': stderr
            }
            print(f"🔑 JWT 安全測試: {'✅ 通過' if returncode == 0 else '❌ 失敗'}")

        # SQL 注入測試
        if (self.project_root / "tests" / "security" / "test_sql_injection.py").exists():
            command = "python -m pytest tests/security/test_sql_injection.py -v"
            returncode, stdout, stderr = self.run_command(command)
            security_results['sql_injection'] = {
                'returncode': returncode,
                'output': stdout,
                'errors': stderr
            }
            print(f"💉 SQL 注入測試: {'✅ 通過' if returncode == 0 else '❌ 失敗'}")

        # XSS 防護測試
        if (self.project_root / "tests" / "security" / "test_xss_protection.py").exists():
            command = "python -m pytest tests/security/test_xss_protection.py -v"
            returncode, stdout, stderr = self.run_command(command)
            security_results['xss_protection'] = {
                'returncode': returncode,
                'output': stdout,
                'errors': stderr
            }
            print(f"🛡️ XSS 防護測試: {'✅ 通過' if returncode == 0 else '❌ 失敗'}")

        # RBAC 權限測試
        if (self.project_root / "tests" / "security" / "test_rbac_permissions.py").exists():
            command = "python -m pytest tests/security/test_rbac_permissions.py -v"
            returncode, stdout, stderr = self.run_command(command)
            security_results['rbac_permissions'] = {
                'returncode': returncode,
                'output': stdout,
                'errors': stderr
            }
            print(f"👥 RBAC 權限測試: {'✅ 通過' if returncode == 0 else '❌ 失敗'}")

        self.test_results['security_tests'] = security_results
        return security_results

    def run_integration_tests(self) -> Dict:
        """執行整合測試"""
        print("\n" + "="*60)
        print("🔗 執行整合測試")
        print("="*60)

        integration_results = {}

        # 整合測試目錄
        integration_dir = self.project_root / "tests" / "integration"
        if integration_dir.exists():
            command = f"python -m pytest {integration_dir} -v"
            returncode, stdout, stderr = self.run_command(command)
            integration_results = {
                'returncode': returncode,
                'output': stdout,
                'errors': stderr,
                'passed': stdout.count(' PASSED'),
                'failed': stdout.count(' FAILED')
            }
            print(f"🔗 整合測試: {'✅ 通過' if returncode == 0 else '❌ 失敗'}")
        else:
            print("⚠️ 未找到整合測試目錄")
            integration_results = {'returncode': 0, 'message': 'No integration tests found'}

        self.test_results['integration_tests'] = integration_results
        return integration_results

    def run_code_quality_checks(self) -> Dict:
        """執行程式碼品質檢查"""
        print("\n" + "="*60)
        print("🎯 執行程式碼品質檢查")
        print("="*60)

        quality_results = {
            'pylint': {},
            'flake8': {},
            'mypy': {},
            'black': {}
        }

        # Pylint 檢查
        command = "pylint src/ --score=yes"
        returncode, stdout, stderr = self.run_command(command)
        quality_results['pylint'] = {
            'returncode': returncode,
            'output': stdout,
            'errors': stderr
        }

        # 提取 Pylint 評分
        import re
        score_pattern = r"Your code has been rated at ([\d\.-]+)/10"
        match = re.search(score_pattern, stdout)
        if match:
            quality_results['pylint']['score'] = float(match.group(1))
        else:
            quality_results['pylint']['score'] = 0.0

        print(f"📊 Pylint 評分: {quality_results['pylint']['score']:.1f}/10")

        # Flake8 檢查
        command = "flake8 src/"
        returncode, stdout, stderr = self.run_command(command)
        quality_results['flake8'] = {
            'returncode': returncode,
            'output': stdout,
            'errors': stderr,
            'issues_count': len(stdout.split('\n')) if stdout.strip() else 0
        }
        flake8_status = '✅ 通過' if returncode == 0 else f'❌ {quality_results["flake8"]["issues_count"]} 個問題'
        print(f"🔍 Flake8: {flake8_status}")

        # MyPy 檢查
        command = "mypy src/"
        returncode, stdout, stderr = self.run_command(command)
        quality_results['mypy'] = {
            'returncode': returncode,
            'output': stdout,
            'errors': stderr
        }
        print(f"🔬 MyPy: {'✅ 通過' if returncode == 0 else '❌ 有類型錯誤'}")

        # Black 格式檢查
        command = "black --check src/"
        returncode, stdout, stderr = self.run_command(command)
        quality_results['black'] = {
            'returncode': returncode,
            'output': stdout,
            'errors': stderr
        }
        print(f"🎨 Black 格式: {'✅ 通過' if returncode == 0 else '❌ 需要格式化'}")

        self.test_results['code_quality'] = quality_results
        return quality_results

    def generate_summary(self) -> Dict:
        """生成測試摘要"""
        summary = {
            'total_duration': 0,
            'overall_status': 'PASSED',
            'test_counts': {
                'unit_tests_passed': self.test_results['unit_tests'].get('passed', 0),
                'unit_tests_failed': self.test_results['unit_tests'].get('failed', 0),
                'coverage_percentage': self.test_results['coverage'].get('total_coverage', 0),
                'pylint_score': self.test_results['code_quality'].get('pylint', {}).get('score', 0)
            },
            'recommendations': []
        }

        # 檢查是否有失敗的測試
        if self.test_results['unit_tests'].get('failed', 0) > 0:
            summary['overall_status'] = 'FAILED'
            summary['recommendations'].append("修復失敗的單元測試")

        # 檢查覆蓋率
        if self.test_results['coverage'].get('total_coverage', 0) < self.min_coverage:
            summary['overall_status'] = 'WARNING'
            summary['recommendations'].append(f"提高測試覆蓋率至 {self.min_coverage}% 以上")

        # 檢查程式碼品質
        pylint_score = self.test_results['code_quality'].get('pylint', {}).get('score', 0)
        if pylint_score < 8.5:
            summary['overall_status'] = 'WARNING'
            summary['recommendations'].append("改善 Pylint 評分至 8.5 以上")

        self.test_results['summary'] = summary
        return summary

    def save_results(self):
        """保存測試結果"""
        results_dir = self.project_root / "test_results"
        results_dir.mkdir(exist_ok=True)

        # 保存 JSON 格式結果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = results_dir / f"test_results_{timestamp}.json"

        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)

        print(f"\n📄 測試結果已保存到: {json_file}")

        # 生成 Markdown 報告
        self.generate_markdown_report(results_dir / f"test_report_{timestamp}.md")

    def generate_markdown_report(self, report_path: Path):
        """生成 Markdown 測試報告"""
        report = []
        report.append("# 綜合測試報告")
        report.append(f"**執行時間**: {self.test_results['timestamp']}")
        report.append(f"**整體狀態**: {self.test_results['summary']['overall_status']}")
        report.append("")

        # 單元測試結果
        unit_tests = self.test_results['unit_tests']
        report.append("## 單元測試結果")
        report.append(f"- ✅ 通過: {unit_tests.get('passed', 0)}")
        report.append(f"- ❌ 失敗: {unit_tests.get('failed', 0)}")
        report.append(f"- ⚠️ 錯誤: {unit_tests.get('errors', 0)}")
        report.append(f"- ⏭️ 跳過: {unit_tests.get('skipped', 0)}")
        report.append(f"- 📊 成功率: {unit_tests.get('success_rate', 0):.1f}%")
        report.append("")

        # 覆蓋率結果
        coverage = self.test_results['coverage']
        report.append("## 測試覆蓋率")
        report.append(f"- 📈 總覆蓋率: {coverage.get('total_coverage', 0)}%")
        report.append(f"- 🎯 最低要求: {self.min_coverage}% ({'✅' if coverage.get('meets_minimum') else '❌'})")
        report.append(f"- 🏆 目標: {self.target_coverage}% ({'✅' if coverage.get('meets_target') else '❌'})")
        report.append("")

        # 程式碼品質
        quality = self.test_results['code_quality']
        report.append("## 程式碼品質")
        report.append(f"- 📊 Pylint 評分: {quality.get('pylint', {}).get('score', 0):.1f}/10")
        report.append(f"- 🔍 Flake8: {'✅ 通過' if quality.get('flake8', {}).get('returncode') == 0 else '❌ 有問題'}")
        report.append(f"- 🔬 MyPy: {'✅ 通過' if quality.get('mypy', {}).get('returncode') == 0 else '❌ 有問題'}")
        report.append(f"- 🎨 Black: {'✅ 通過' if quality.get('black', {}).get('returncode') == 0 else '❌ 需格式化'}")
        report.append("")

        # 建議
        recommendations = self.test_results['summary'].get('recommendations', [])
        if recommendations:
            report.append("## 改善建議")
            for rec in recommendations:
                report.append(f"- {rec}")
            report.append("")

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))

        print(f"📋 測試報告已保存到: {report_path}")

    def run_all_tests(self):
        """執行所有測試"""
        start_time = time.time()

        print("🚀 開始執行綜合測試套件")
        print("=" * 60)

        # 執行各種測試
        self.run_unit_tests()
        self.run_coverage_tests()
        self.run_performance_tests()
        self.run_security_tests()
        self.run_integration_tests()
        self.run_code_quality_checks()

        # 生成摘要
        summary = self.generate_summary()

        # 計算總執行時間
        end_time = time.time()
        duration = end_time - start_time
        summary['total_duration'] = duration

        # 保存結果
        self.save_results()

        # 顯示最終結果
        print("\n" + "="*60)
        print("📊 測試執行完成")
        print("="*60)
        print(f"🕐 總執行時間: {duration:.1f} 秒")
        print(f"📈 整體狀態: {summary['overall_status']}")
        print(f"✅ 單元測試通過: {summary['test_counts']['unit_tests_passed']}")
        print(f"❌ 單元測試失敗: {summary['test_counts']['unit_tests_failed']}")
        print(f"📊 測試覆蓋率: {summary['test_counts']['coverage_percentage']}%")
        print(f"🎯 Pylint 評分: {summary['test_counts']['pylint_score']:.1f}/10")

        if summary['recommendations']:
            print("\n💡 改善建議:")
            for rec in summary['recommendations']:
                print(f"  - {rec}")

        return summary['overall_status'] == 'PASSED'


def main():
    """主函數"""
    runner = ComprehensiveTestRunner()
    success = runner.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
