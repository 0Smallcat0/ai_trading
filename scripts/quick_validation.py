#!/usr/bin/env python3
"""
快速驗證腳本

此腳本執行基本的系統驗證，確保依賴管理改進後系統仍能正常運行。
"""

import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_basic_imports():
    """測試基本模組導入"""
    print("🔍 測試基本模組導入...")
    
    try:
        # 測試標準庫
        import json
        import logging
        import datetime
        print("  ✅ 標準庫導入成功")
        
        # 測試核心依賴
        import pandas as pd
        import numpy as np
        import streamlit as st
        print("  ✅ 核心依賴導入成功")
        
        # 測試專案模組
        import src.config
        print("  ✅ 專案配置模組導入成功")
        
        return True
    except Exception as e:
        print(f"  ❌ 導入失敗: {e}")
        return False

def test_pyproject_config():
    """測試 pyproject.toml 配置"""
    print("\n📋 測試 pyproject.toml 配置...")
    
    try:
        pyproject_path = project_root / "pyproject.toml"
        if not pyproject_path.exists():
            print("  ❌ pyproject.toml 不存在")
            return False
        
        # 檢查檔案大小（應該不為空）
        if pyproject_path.stat().st_size == 0:
            print("  ❌ pyproject.toml 為空檔案")
            return False
        
        print("  ✅ pyproject.toml 存在且不為空")
        
        # 嘗試讀取內容
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 檢查關鍵區段
        required_sections = [
            '[tool.poetry]',
            '[tool.poetry.dependencies]',
            '[tool.poetry.group.dev.dependencies]',
            '[tool.poetry.scripts]'
        ]
        
        for section in required_sections:
            if section in content:
                print(f"  ✅ 找到 {section}")
            else:
                print(f"  ❌ 缺少 {section}")
                return False
        
        return True
    except Exception as e:
        print(f"  ❌ 配置檢查失敗: {e}")
        return False

def test_directory_structure():
    """測試目錄結構"""
    print("\n📁 測試目錄結構...")
    
    required_dirs = [
        "src",
        "src/ui",
        "src/core",
        "src/api",
        "docs",
        "scripts",
        "tests"
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ 不存在")
            all_exist = False
    
    return all_exist

def test_key_files():
    """測試關鍵檔案"""
    print("\n📄 測試關鍵檔案...")
    
    key_files = [
        "README.md",
        "pyproject.toml",
        "src/__init__.py",
        "src/ui/web_ui.py",
        "src/api/main.py",
        "src/core/main.py"
    ]
    
    all_exist = True
    for file_name in key_files:
        file_path = project_root / file_name
        if file_path.exists():
            print(f"  ✅ {file_name}")
        else:
            print(f"  ❌ {file_name} 不存在")
            all_exist = False
    
    return all_exist

def test_new_documentation():
    """測試新增的文檔"""
    print("\n📚 測試新增文檔...")
    
    new_docs = [
        "docs/安裝與依賴管理指南.md",
        "docs/依賴管理完善報告.md"
    ]
    
    all_exist = True
    for doc_name in new_docs:
        doc_path = project_root / doc_name
        if doc_path.exists():
            print(f"  ✅ {doc_name}")
        else:
            print(f"  ❌ {doc_name} 不存在")
            all_exist = False
    
    return all_exist

def test_scripts():
    """測試新增的腳本"""
    print("\n🔧 測試新增腳本...")
    
    new_scripts = [
        "scripts/validate_pyproject.py",
        "scripts/test_app_startup.py",
        "scripts/quick_validation.py"
    ]
    
    all_exist = True
    for script_name in new_scripts:
        script_path = project_root / script_name
        if script_path.exists():
            print(f"  ✅ {script_name}")
        else:
            print(f"  ❌ {script_name} 不存在")
            all_exist = False
    
    return all_exist

def main():
    """主函數"""
    print("🚀 AI 交易系統 - 快速驗證")
    print("="*50)
    
    tests = [
        ("基本模組導入", test_basic_imports),
        ("pyproject.toml 配置", test_pyproject_config),
        ("目錄結構", test_directory_structure),
        ("關鍵檔案", test_key_files),
        ("新增文檔", test_new_documentation),
        ("新增腳本", test_scripts)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} 測試失敗: {e}")
            results.append((test_name, False))
    
    # 生成報告
    print("\n" + "="*50)
    print("📊 驗證結果")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"總測試項目: {total}")
    print(f"通過測試: {passed}")
    print(f"失敗測試: {total - passed}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    print("\n詳細結果:")
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"  {test_name}: {status}")
    
    if passed == total:
        print("\n🎉 所有驗證通過！依賴管理改進成功。")
        return 0
    else:
        print("\n⚠️ 部分驗證失敗，請檢查相關問題。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
