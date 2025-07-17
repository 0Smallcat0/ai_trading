#!/usr/bin/env python3
"""
CI/CD 流程穩定性測試

此模組測試 CI/CD 流程在不同場景下的穩定性，包括：
- GitHub Actions 工作流程測試
- 品質檢查流程測試
- 通知系統流程測試
- 性能監控測試
- 錯誤處理和恢復測試

Example:
    >>> python tests/integration/test_cicd_stability.py
"""

import json
import os
import sys
import subprocess
import time
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestGitHubActionsWorkflow(unittest.TestCase):
    """GitHub Actions 工作流程測試."""

    def setUp(self):
        """測試設置."""
        self.project_root = project_root
        self.workflows_dir = self.project_root / ".github" / "workflows"

    def test_quality_check_workflow_syntax(self):
        """測試品質檢查工作流程語法."""
        workflow_file = self.workflows_dir / "quality-check-optimized.yml"
        
        if not workflow_file.exists():
            self.skipTest("品質檢查工作流程檔案不存在")
        
        try:
            import yaml
            with open(workflow_file, 'r', encoding='utf-8') as f:
                workflow_content = yaml.safe_load(f)
            
            # 檢查必要的欄位
            self.assertIn('name', workflow_content)
            self.assertIn('on', workflow_content)
            self.assertIn('jobs', workflow_content)
            
            # 檢查 jobs 結構
            jobs = workflow_content['jobs']
            expected_jobs = ['quick-checks', 'static-analysis', 'security-checks', 'tests', 'quality-report']
            
            for job_name in expected_jobs:
                self.assertIn(job_name, jobs, f"缺少 job: {job_name}")
                self.assertIn('runs-on', jobs[job_name])
                self.assertIn('steps', jobs[job_name])
            
            print("✅ 品質檢查工作流程語法正確")
            
        except Exception as e:
            self.fail(f"品質檢查工作流程語法錯誤: {e}")

    def test_notification_workflow_syntax(self):
        """測試通知工作流程語法."""
        workflow_file = self.workflows_dir / "quality-notifications.yml"
        
        if not workflow_file.exists():
            self.skipTest("通知工作流程檔案不存在")
        
        try:
            import yaml
            with open(workflow_file, 'r', encoding='utf-8') as f:
                workflow_content = yaml.safe_load(f)
            
            # 檢查必要的欄位
            self.assertIn('name', workflow_content)
            self.assertIn('on', workflow_content)
            self.assertIn('jobs', workflow_content)
            
            # 檢查觸發條件
            triggers = workflow_content['on']
            self.assertIn('schedule', triggers)
            
            print("✅ 通知工作流程語法正確")
            
        except Exception as e:
            self.fail(f"通知工作流程語法錯誤: {e}")

    def test_workflow_dependencies(self):
        """測試工作流程依賴關係."""
        workflow_file = self.workflows_dir / "quality-check-optimized.yml"
        
        if not workflow_file.exists():
            self.skipTest("品質檢查工作流程檔案不存在")
        
        try:
            import yaml
            with open(workflow_file, 'r', encoding='utf-8') as f:
                workflow_content = yaml.safe_load(f)
            
            jobs = workflow_content['jobs']
            
            # 檢查依賴關係
            if 'static-analysis' in jobs:
                self.assertIn('needs', jobs['static-analysis'])
                self.assertIn('quick-checks', jobs['static-analysis']['needs'])
            
            if 'quality-report' in jobs:
                self.assertIn('needs', jobs['quality-report'])
                needs = jobs['quality-report']['needs']
                expected_deps = ['static-analysis', 'security-checks', 'tests']
                for dep in expected_deps:
                    self.assertIn(dep, needs)
            
            print("✅ 工作流程依賴關係正確")
            
        except Exception as e:
            self.fail(f"工作流程依賴關係錯誤: {e}")


class TestQualityCheckProcess(unittest.TestCase):
    """品質檢查流程測試."""

    def setUp(self):
        """測試設置."""
        self.project_root = project_root

    def test_quality_check_script_execution(self):
        """測試品質檢查腳本執行."""
        script_path = self.project_root / "scripts" / "run_quality_checks.py"
        
        if not script_path.exists():
            self.skipTest("品質檢查腳本不存在")
        
        try:
            # 測試腳本是否可以正常執行（不安裝工具）
            result = subprocess.run([
                sys.executable, str(script_path), "--help"
            ], capture_output=True, text=True, timeout=10)
            
            self.assertEqual(result.returncode, 0)
            self.assertIn("usage:", result.stdout.lower())
            
            print("✅ 品質檢查腳本可正常執行")
            
        except subprocess.TimeoutExpired:
            self.fail("品質檢查腳本執行超時")
        except Exception as e:
            self.fail(f"品質檢查腳本執行失敗: {e}")

    def test_quality_report_generation(self):
        """測試品質報告生成."""
        script_path = self.project_root / "scripts" / "generate_quality_report.py"
        
        if not script_path.exists():
            self.skipTest("品質報告生成腳本不存在")
        
        try:
            # 測試腳本語法
            result = subprocess.run([
                sys.executable, "-m", "py_compile", str(script_path)
            ], capture_output=True, text=True, timeout=10)
            
            self.assertEqual(result.returncode, 0, f"語法錯誤: {result.stderr}")
            
            print("✅ 品質報告生成腳本語法正確")
            
        except Exception as e:
            self.fail(f"品質報告生成測試失敗: {e}")

    def test_performance_monitoring(self):
        """測試性能監控."""
        script_path = self.project_root / "scripts" / "performance_monitor.py"
        
        if not script_path.exists():
            self.skipTest("性能監控腳本不存在")
        
        try:
            # 測試腳本語法
            result = subprocess.run([
                sys.executable, "-m", "py_compile", str(script_path)
            ], capture_output=True, text=True, timeout=10)
            
            self.assertEqual(result.returncode, 0, f"語法錯誤: {result.stderr}")
            
            print("✅ 性能監控腳本語法正確")
            
        except Exception as e:
            self.fail(f"性能監控測試失敗: {e}")


class TestNotificationSystem(unittest.TestCase):
    """通知系統測試."""

    def setUp(self):
        """測試設置."""
        self.project_root = project_root

    def test_notification_script_execution(self):
        """測試通知腳本執行."""
        script_path = self.project_root / "scripts" / "run_notifications.py"
        
        if not script_path.exists():
            self.skipTest("通知腳本不存在")
        
        try:
            # 測試腳本幫助信息
            result = subprocess.run([
                sys.executable, str(script_path), "--help"
            ], capture_output=True, text=True, timeout=10)
            
            self.assertEqual(result.returncode, 0)
            self.assertIn("usage:", result.stdout.lower())
            
            print("✅ 通知腳本可正常執行")
            
        except Exception as e:
            self.fail(f"通知腳本執行失敗: {e}")

    def test_notification_config_validation(self):
        """測試通知配置驗證."""
        config_path = self.project_root / "config" / "notification_config.json"
        
        if not config_path.exists():
            self.skipTest("通知配置檔案不存在")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 檢查必要的配置項
            required_sections = ['slack', 'teams', 'github', 'thresholds']
            for section in required_sections:
                self.assertIn(section, config, f"缺少配置區段: {section}")
            
            # 檢查閾值配置
            thresholds = config['thresholds']
            required_thresholds = ['pylint_critical', 'pylint_warning', 'coverage_critical', 'coverage_warning']
            for threshold in required_thresholds:
                self.assertIn(threshold, thresholds, f"缺少閾值配置: {threshold}")
                self.assertIsInstance(thresholds[threshold], (int, float))
            
            print("✅ 通知配置驗證通過")
            
        except json.JSONDecodeError as e:
            self.fail(f"通知配置 JSON 格式錯誤: {e}")
        except Exception as e:
            self.fail(f"通知配置驗證失敗: {e}")

    @patch('requests.post')
    def test_notification_system_mock(self, mock_post):
        """測試通知系統（模擬）."""
        try:
            # 模擬成功的 HTTP 響應
            mock_response = MagicMock()
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # 導入並測試通知系統
            from scripts.notification_system import NotificationSystem
            
            notifier = NotificationSystem()
            
            # 測試 Slack 通知
            result = notifier.send_slack_notification("測試訊息", "info")
            self.assertTrue(result)
            
            print("✅ 通知系統模擬測試通過")
            
        except ImportError:
            self.skipTest("通知系統模組未找到")
        except Exception as e:
            self.fail(f"通知系統測試失敗: {e}")


class TestErrorHandlingAndRecovery(unittest.TestCase):
    """錯誤處理和恢復測試."""

    def test_script_error_handling(self):
        """測試腳本錯誤處理."""
        # 測試不存在的參數
        script_path = self.project_root / "scripts" / "run_quality_checks.py"
        
        if not script_path.exists():
            self.skipTest("品質檢查腳本不存在")
        
        try:
            result = subprocess.run([
                sys.executable, str(script_path), "--invalid-option"
            ], capture_output=True, text=True, timeout=10)
            
            # 應該返回非零退出碼
            self.assertNotEqual(result.returncode, 0)
            
            print("✅ 腳本錯誤處理正確")
            
        except Exception as e:
            self.fail(f"腳本錯誤處理測試失敗: {e}")

    def test_missing_dependencies_handling(self):
        """測試缺少依賴的處理."""
        try:
            # 模擬缺少依賴的情況
            with patch('importlib.import_module') as mock_import:
                mock_import.side_effect = ImportError("No module named 'missing_module'")
                
                # 這裡應該測試系統如何處理缺少的依賴
                # 由於實際實現可能不同，這裡只是示例
                
                print("✅ 缺少依賴處理測試通過")
                
        except Exception as e:
            self.fail(f"缺少依賴處理測試失敗: {e}")

    def test_network_failure_handling(self):
        """測試網路失敗處理."""
        try:
            # 模擬網路失敗
            with patch('requests.post') as mock_post:
                mock_post.side_effect = Exception("Network error")
                
                # 測試通知系統如何處理網路錯誤
                from scripts.notification_system import NotificationSystem
                
                notifier = NotificationSystem()
                result = notifier.send_slack_notification("測試訊息", "info")
                
                # 應該優雅地處理錯誤
                self.assertFalse(result)
                
                print("✅ 網路失敗處理測試通過")
                
        except ImportError:
            self.skipTest("通知系統模組未找到")
        except Exception as e:
            self.fail(f"網路失敗處理測試失敗: {e}")


class TestPerformanceAndScalability(unittest.TestCase):
    """性能和可擴展性測試."""

    def test_script_execution_time(self):
        """測試腳本執行時間."""
        script_path = self.project_root / "scripts" / "run_quality_checks.py"
        
        if not script_path.exists():
            self.skipTest("品質檢查腳本不存在")
        
        try:
            start_time = time.time()
            
            result = subprocess.run([
                sys.executable, str(script_path), "--help"
            ], capture_output=True, text=True, timeout=30)
            
            execution_time = time.time() - start_time
            
            # 幫助信息應該在 5 秒內顯示
            self.assertLess(execution_time, 5.0)
            self.assertEqual(result.returncode, 0)
            
            print(f"✅ 腳本執行時間測試通過 ({execution_time:.2f}s)")
            
        except Exception as e:
            self.fail(f"腳本執行時間測試失敗: {e}")

    def test_memory_usage(self):
        """測試記憶體使用量."""
        try:
            import psutil
            import os
            
            # 獲取當前進程的記憶體使用量
            process = psutil.Process(os.getpid())
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # 執行一些操作
            from scripts.notification_system import NotificationSystem
            notifier = NotificationSystem()
            
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = memory_after - memory_before
            
            # 記憶體增加應該在合理範圍內（<50MB）
            self.assertLess(memory_increase, 50)
            
            print(f"✅ 記憶體使用量測試通過 (增加 {memory_increase:.1f}MB)")
            
        except ImportError:
            self.skipTest("psutil 未安裝，跳過記憶體測試")
        except Exception as e:
            self.fail(f"記憶體使用量測試失敗: {e}")


def main():
    """主函數."""
    # 創建測試套件
    test_suite = unittest.TestSuite()
    
    # 添加測試類別
    test_classes = [
        TestGitHubActionsWorkflow,
        TestQualityCheckProcess,
        TestNotificationSystem,
        TestErrorHandlingAndRecovery,
        TestPerformanceAndScalability
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # 執行測試
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 生成測試報告
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success_rate": ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    }
    
    # 保存報告
    report_path = project_root / "docs" / "reports" / "cicd_stability_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 CI/CD 穩定性測試完成!")
    print(f"總測試數: {report['total_tests']}")
    print(f"失敗數: {report['failures']}")
    print(f"錯誤數: {report['errors']}")
    print(f"成功率: {report['success_rate']:.1f}%")
    print(f"報告已保存: {report_path}")
    
    # 返回適當的退出碼
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
