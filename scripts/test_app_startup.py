#!/usr/bin/env python3
"""
應用程式啟動測試腳本

此腳本測試 AI 交易系統的各個組件是否能正常啟動，
包括 Web UI、API 服務器等。
"""

import sys
import time
import subprocess
import threading
import requests
from pathlib import Path
from typing import Dict, List, Tuple


def test_import_modules() -> Tuple[bool, List[str]]:
    """測試核心模組導入
    
    Returns:
        Tuple[bool, List[str]]: (是否成功, 錯誤訊息列表)
    """
    print("🔍 測試核心模組導入...")
    errors = []
    
    # 核心模組列表
    core_modules = [
        "src.ui.web_ui",
        "src.api.main",
        "src.core.main",
        "src.core.data_ingest",
        "src.core.signal_gen",
        "src.core.portfolio",
        "src.core.risk_control",
        "src.core.executor",
    ]
    
    for module in core_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            error_msg = f"  ❌ {module}: {e}"
            print(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"  ⚠️ {module}: {e}"
            print(error_msg)
            errors.append(error_msg)
    
    success = len(errors) == 0
    print(f"模組導入測試: {'✅ 成功' if success else '❌ 失敗'}")
    return success, errors


def test_streamlit_startup() -> Tuple[bool, str]:
    """測試 Streamlit 應用啟動
    
    Returns:
        Tuple[bool, str]: (是否成功, 錯誤訊息)
    """
    print("\n🚀 測試 Streamlit 應用啟動...")
    
    try:
        # 嘗試導入 Streamlit 應用
        from src.ui.web_ui import main
        print("  ✅ Web UI 模組導入成功")
        
        # 檢查主函數是否可調用
        if callable(main):
            print("  ✅ main 函數可調用")
            return True, "Streamlit 應用啟動測試成功"
        else:
            return False, "main 函數不可調用"
            
    except ImportError as e:
        return False, f"導入錯誤: {e}"
    except Exception as e:
        return False, f"未預期錯誤: {e}"


def test_api_startup() -> Tuple[bool, str]:
    """測試 API 服務器啟動
    
    Returns:
        Tuple[bool, str]: (是否成功, 錯誤訊息)
    """
    print("\n🌐 測試 API 服務器啟動...")
    
    try:
        # 嘗試導入 FastAPI 應用
        from src.api.main import create_app
        print("  ✅ API 模組導入成功")
        
        # 嘗試創建應用實例
        app = create_app()
        if app:
            print("  ✅ FastAPI 應用創建成功")
            return True, "API 服務器啟動測試成功"
        else:
            return False, "FastAPI 應用創建失敗"
            
    except ImportError as e:
        return False, f"導入錯誤: {e}"
    except Exception as e:
        return False, f"未預期錯誤: {e}"


def test_core_services() -> Tuple[bool, List[str]]:
    """測試核心服務
    
    Returns:
        Tuple[bool, List[str]]: (是否成功, 錯誤訊息列表)
    """
    print("\n⚙️ 測試核心服務...")
    errors = []
    
    # 測試核心服務模組
    services = [
        ("數據獲取", "src.core.data_ingest"),
        ("信號生成", "src.core.signal_gen"),
        ("投資組合", "src.core.portfolio"),
        ("風險控制", "src.core.risk_control"),
        ("交易執行", "src.core.executor"),
    ]
    
    for service_name, module_name in services:
        try:
            module = __import__(module_name, fromlist=[''])
            print(f"  ✅ {service_name} ({module_name})")
        except ImportError as e:
            error_msg = f"  ❌ {service_name}: 導入失敗 - {e}"
            print(error_msg)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"  ⚠️ {service_name}: {e}"
            print(error_msg)
            errors.append(error_msg)
    
    success = len(errors) == 0
    print(f"核心服務測試: {'✅ 成功' if success else '❌ 失敗'}")
    return success, errors


def test_optional_dependencies() -> Tuple[bool, List[str]]:
    """測試可選依賴
    
    Returns:
        Tuple[bool, List[str]]: (是否成功, 警告訊息列表)
    """
    print("\n📦 測試可選依賴...")
    warnings = []
    
    # 可選依賴列表
    optional_deps = [
        ("永豐證券 API", "shioaji"),
        ("Interactive Brokers API", "ibapi"),
        ("加密貨幣交易所 API", "ccxt"),
        ("結構化日誌", "structlog"),
        ("錯誤追蹤", "sentry_sdk"),
        ("PostgreSQL 驅動", "psycopg2"),
    ]
    
    for dep_name, module_name in optional_deps:
        try:
            __import__(module_name)
            print(f"  ✅ {dep_name} ({module_name})")
        except ImportError:
            warning_msg = f"  ⚠️ {dep_name}: 未安裝（可選）"
            print(warning_msg)
            warnings.append(warning_msg)
        except Exception as e:
            warning_msg = f"  ⚠️ {dep_name}: {e}"
            print(warning_msg)
            warnings.append(warning_msg)
    
    print(f"可選依賴測試: ✅ 完成（{len(warnings)} 個警告）")
    return True, warnings


def test_configuration() -> Tuple[bool, List[str]]:
    """測試配置檔案
    
    Returns:
        Tuple[bool, List[str]]: (是否成功, 錯誤訊息列表)
    """
    print("\n⚙️ 測試配置檔案...")
    errors = []
    
    # 檢查重要配置檔案
    config_files = [
        "pyproject.toml",
        "src/config.py",
    ]
    
    for config_file in config_files:
        config_path = Path(config_file)
        if config_path.exists():
            print(f"  ✅ {config_file}")
        else:
            error_msg = f"  ❌ {config_file}: 檔案不存在"
            print(error_msg)
            errors.append(error_msg)
    
    # 檢查環境變數檔案
    env_files = [".env", ".env.example"]
    for env_file in env_files:
        env_path = Path(env_file)
        if env_path.exists():
            print(f"  ✅ {env_file}")
        else:
            print(f"  ⚠️ {env_file}: 檔案不存在（可選）")
    
    success = len(errors) == 0
    print(f"配置檔案測試: {'✅ 成功' if success else '❌ 失敗'}")
    return success, errors


def generate_test_report(results: Dict[str, Tuple[bool, any]]) -> None:
    """生成測試報告
    
    Args:
        results: 測試結果字典
    """
    print("\n" + "="*60)
    print("📊 應用程式啟動測試報告")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for success, _ in results.values() if success)
    
    print(f"總測試項目: {total_tests}")
    print(f"通過測試: {passed_tests}")
    print(f"失敗測試: {total_tests - passed_tests}")
    print(f"成功率: {passed_tests/total_tests*100:.1f}%")
    
    print("\n詳細結果:")
    for test_name, (success, details) in results.items():
        status = "✅ 通過" if success else "❌ 失敗"
        print(f"  {test_name}: {status}")
        
        if not success and isinstance(details, list):
            for detail in details[:3]:  # 只顯示前3個錯誤
                print(f"    - {detail}")
            if len(details) > 3:
                print(f"    - ... 還有 {len(details) - 3} 個錯誤")
    
    print("\n建議:")
    if passed_tests == total_tests:
        print("  🎉 所有測試通過！系統可以正常啟動。")
    else:
        print("  🔧 請檢查失敗的測試項目，確保相關依賴已正確安裝。")
        print("  📚 參考文檔: docs/安裝與依賴管理指南.md")


def main():
    """主函數"""
    print("🚀 AI 交易系統 - 應用程式啟動測試")
    print("="*60)
    
    # 執行各項測試
    results = {}
    
    # 1. 模組導入測試
    success, errors = test_import_modules()
    results["模組導入"] = (success, errors)
    
    # 2. Streamlit 啟動測試
    success, message = test_streamlit_startup()
    results["Streamlit 應用"] = (success, [message] if not success else [])
    
    # 3. API 啟動測試
    success, message = test_api_startup()
    results["API 服務器"] = (success, [message] if not success else [])
    
    # 4. 核心服務測試
    success, errors = test_core_services()
    results["核心服務"] = (success, errors)
    
    # 5. 可選依賴測試
    success, warnings = test_optional_dependencies()
    results["可選依賴"] = (success, warnings)
    
    # 6. 配置檔案測試
    success, errors = test_configuration()
    results["配置檔案"] = (success, errors)
    
    # 生成報告
    generate_test_report(results)
    
    # 返回退出碼
    all_passed = all(success for success, _ in results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
