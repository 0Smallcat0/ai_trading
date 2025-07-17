"""
測試覆蓋率檢查腳本

檢查風險控制系統的測試覆蓋率，確保達到≥90%的要求
"""

import subprocess
import sys
import os
from pathlib import Path


def run_coverage_check():
    """運行測試覆蓋率檢查"""
    print("🔍 開始檢查風險控制系統測試覆蓋率...")
    
    # 設置工作目錄
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # 風險控制相關模組
    risk_modules = [
        "src.risk.live.fund_monitor",
        "src.risk.live.fund_calculator", 
        "src.risk.live.fund_monitor_base",
        "src.risk.live.dynamic_stop_loss",
        "src.risk.live.stop_loss_strategies",
        "src.risk.live.stop_loss_monitor",
        "src.risk.live.emergency_risk_control",
        "src.risk.live.emergency_actions",
        "src.risk.live.emergency_event_manager",
        "src.risk.live.unified_risk_controller",
    ]
    
    # 相關測試文件
    test_files = [
        "tests/test_fund_monitor_enhanced.py",
        "tests/test_dynamic_stop_loss_enhanced.py", 
        "tests/test_unified_risk_controller.py",
        "tests/test_risk_control_integration.py",
    ]
    
    try:
        # 構建覆蓋率命令
        coverage_cmd = [
            "python", "-m", "pytest"
        ] + test_files + [
            "--cov=" + module for module in risk_modules
        ] + [
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=90",
            "-v"
        ]
        
        print(f"📋 執行命令: {' '.join(coverage_cmd)}")
        
        # 運行測試覆蓋率檢查
        result = subprocess.run(
            coverage_cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5分鐘超時
        )
        
        print("📊 測試覆蓋率結果:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️ 警告/錯誤:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ 測試覆蓋率檢查通過！覆蓋率 ≥ 90%")
            return True
        else:
            print("❌ 測試覆蓋率檢查失敗！覆蓋率 < 90%")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ 測試覆蓋率檢查超時")
        return False
    except Exception as e:
        print(f"💥 測試覆蓋率檢查出錯: {e}")
        return False


def run_individual_module_tests():
    """運行個別模組測試"""
    print("\n🧪 運行個別模組測試...")
    
    test_commands = [
        {
            "name": "資金監控模組",
            "cmd": ["python", "-m", "pytest", "tests/test_fund_monitor_enhanced.py", "-v"]
        },
        {
            "name": "動態停損模組", 
            "cmd": ["python", "-m", "pytest", "tests/test_dynamic_stop_loss_enhanced.py", "-v"]
        },
        {
            "name": "統一風險控制器",
            "cmd": ["python", "-m", "pytest", "tests/test_unified_risk_controller.py", "-v"]
        },
        {
            "name": "整合測試",
            "cmd": ["python", "-m", "pytest", "tests/test_risk_control_integration.py", "-v"]
        }
    ]
    
    results = {}
    
    for test in test_commands:
        print(f"\n📝 測試 {test['name']}...")
        try:
            result = subprocess.run(
                test["cmd"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print(f"✅ {test['name']} 測試通過")
                results[test['name']] = "PASS"
            else:
                print(f"❌ {test['name']} 測試失敗")
                print("錯誤輸出:")
                print(result.stdout)
                print(result.stderr)
                results[test['name']] = "FAIL"
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {test['name']} 測試超時")
            results[test['name']] = "TIMEOUT"
        except Exception as e:
            print(f"💥 {test['name']} 測試出錯: {e}")
            results[test['name']] = "ERROR"
    
    return results


def generate_coverage_report():
    """生成覆蓋率報告"""
    print("\n📈 生成詳細覆蓋率報告...")
    
    try:
        # 生成 HTML 報告
        html_cmd = [
            "python", "-m", "coverage", "html",
            "--directory=htmlcov",
            "--title=風險控制系統測試覆蓋率報告"
        ]
        
        subprocess.run(html_cmd, check=True)
        print("✅ HTML 覆蓋率報告已生成: htmlcov/index.html")
        
        # 生成 XML 報告
        xml_cmd = ["python", "-m", "coverage", "xml"]
        subprocess.run(xml_cmd, check=True)
        print("✅ XML 覆蓋率報告已生成: coverage.xml")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 生成覆蓋率報告失敗: {e}")
        return False


def check_code_quality():
    """檢查代碼質量"""
    print("\n🔍 檢查代碼質量...")
    
    risk_files = [
        "src/risk/live/fund_monitor.py",
        "src/risk/live/fund_calculator.py",
        "src/risk/live/dynamic_stop_loss.py", 
        "src/risk/live/stop_loss_strategies.py",
        "src/risk/live/stop_loss_monitor.py",
        "src/risk/live/emergency_risk_control.py",
        "src/risk/live/emergency_actions.py",
        "src/risk/live/unified_risk_controller.py",
    ]
    
    quality_results = {}
    
    for file_path in risk_files:
        if os.path.exists(file_path):
            try:
                # 運行 pylint
                pylint_cmd = ["python", "-m", "pylint", file_path, "--score=yes"]
                result = subprocess.run(
                    pylint_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                # 提取分數
                output_lines = result.stdout.split('\n')
                score_line = [line for line in output_lines if "Your code has been rated at" in line]
                
                if score_line:
                    score_text = score_line[0]
                    score = float(score_text.split()[6].split('/')[0])
                    quality_results[file_path] = score
                    
                    if score >= 8.5:
                        print(f"✅ {file_path}: {score:.2f}/10")
                    else:
                        print(f"⚠️ {file_path}: {score:.2f}/10 (需要改進)")
                else:
                    quality_results[file_path] = 0.0
                    print(f"❌ {file_path}: 無法獲取分數")
                    
            except Exception as e:
                print(f"💥 檢查 {file_path} 失敗: {e}")
                quality_results[file_path] = 0.0
        else:
            print(f"⚠️ 文件不存在: {file_path}")
    
    return quality_results


def main():
    """主函數"""
    print("🚀 風險控制系統測試覆蓋率檢查開始")
    print("=" * 60)
    
    # 1. 運行個別模組測試
    test_results = run_individual_module_tests()
    
    # 2. 運行覆蓋率檢查
    coverage_passed = run_coverage_check()
    
    # 3. 生成覆蓋率報告
    report_generated = generate_coverage_report()
    
    # 4. 檢查代碼質量
    quality_results = check_code_quality()
    
    # 5. 總結報告
    print("\n" + "=" * 60)
    print("📋 測試總結報告")
    print("=" * 60)
    
    print("\n🧪 個別模組測試結果:")
    for module, result in test_results.items():
        status_icon = "✅" if result == "PASS" else "❌"
        print(f"  {status_icon} {module}: {result}")
    
    print(f"\n📊 測試覆蓋率: {'✅ 通過 (≥90%)' if coverage_passed else '❌ 未達標 (<90%)'}")
    print(f"📈 覆蓋率報告: {'✅ 已生成' if report_generated else '❌ 生成失敗'}")
    
    print("\n🔍 代碼質量檢查:")
    avg_quality = sum(quality_results.values()) / len(quality_results) if quality_results else 0
    for file_path, score in quality_results.items():
        status_icon = "✅" if score >= 8.5 else "⚠️"
        print(f"  {status_icon} {file_path}: {score:.2f}/10")
    
    print(f"\n📊 平均代碼質量分數: {avg_quality:.2f}/10")
    
    # 判斷整體結果
    all_tests_passed = all(result == "PASS" for result in test_results.values())
    quality_acceptable = avg_quality >= 8.5
    
    if all_tests_passed and coverage_passed and quality_acceptable:
        print("\n🎉 所有檢查通過！風險控制系統已準備就緒。")
        return 0
    else:
        print("\n⚠️ 部分檢查未通過，請檢查上述結果並進行修復。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
