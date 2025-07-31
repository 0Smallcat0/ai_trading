#!/usr/bin/env python3
"""
AI交易系統 - 一鍵依賴安裝腳本

此腳本自動安裝AI交易系統所需的所有依賴包，
並提供新手友好的安裝體驗。

使用方式:
    python install_dependencies.py

功能:
- 自動檢測缺失的依賴包
- 提供安裝進度顯示
- 錯誤處理和重試機制
- 安裝後驗證功能
"""

import subprocess
import sys
import os
from typing import List, Dict, Tuple
import importlib

class DependencyInstaller:
    """依賴包安裝器"""
    
    def __init__(self):
        self.required_packages = {
            # 核心依賴
            'streamlit': 'Web UI框架',
            'streamlit-option-menu': 'UI導航組件',
            'plotly': '數據可視化',
            'pandas': '數據處理',
            'numpy': '數值計算',
            
            # 數據源依賴
            'FinMind': '台股數據源',
            'baostock': '免費A股數據源',
            'yfinance': 'Yahoo Finance數據源',
            
            # 回測依賴
            'backtrader': '回測引擎',
            
            # 機器學習依賴
            'scikit-learn': '機器學習',
            'tensorflow': '深度學習 (可選)',
            
            # 其他依賴
            'requests': 'HTTP請求',
            'python-dotenv': '環境變數管理',
            'sqlalchemy': '資料庫ORM',
            'fastapi': 'API框架',
            'uvicorn': 'ASGI服務器',
        }
        
        self.optional_packages = {
            'tensorflow': '深度學習功能 (大型包，可選)',
            'torch': 'PyTorch深度學習 (可選)',
            'gym': '強化學習環境 (可選)',
        }

        # 推薦的可選包（對新手友好）
        self.recommended_packages = {
            'backtrader': '專業回測引擎 (推薦)',
            'baostock': '免費A股數據源 (推薦)',
            'FinMind': '台股數據源 (推薦)',
            'snownlp': '中文情緒分析 (推薦)',
            'psutil': '系統監控 (推薦)',
            'beautifulsoup4': '網頁解析 (推薦)',
            'lxml': 'XML解析器 (推薦)',
        }
    
    def check_package(self, package_name: str) -> bool:
        """檢查包是否已安裝"""
        try:
            importlib.import_module(package_name.replace('-', '_'))
            return True
        except ImportError:
            return False
    
    def install_package(self, package_name: str) -> Tuple[bool, str]:
        """安裝單個包"""
        try:
            print(f"正在安裝 {package_name}...")
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package_name],
                capture_output=True,
                text=True,
                timeout=300  # 5分鐘超時
            )
            
            if result.returncode == 0:
                print(f"✅ {package_name} 安裝成功")
                return True, ""
            else:
                error_msg = result.stderr or result.stdout
                print(f"❌ {package_name} 安裝失敗: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            print(f"❌ {package_name} 安裝超時")
            return False, "安裝超時"
        except Exception as e:
            print(f"❌ {package_name} 安裝出錯: {e}")
            return False, str(e)
    
    def install_all_dependencies(self, include_optional: bool = False, include_recommended: bool = True):
        """安裝所有依賴"""
        print("🚀 開始安裝AI交易系統依賴包...")
        print("=" * 50)

        packages_to_install = self.required_packages.copy()
        if include_recommended:
            packages_to_install.update(self.recommended_packages)
        if include_optional:
            packages_to_install.update(self.optional_packages)
        
        # 檢查已安裝的包
        installed_packages = []
        missing_packages = []
        
        for package_name, description in packages_to_install.items():
            if self.check_package(package_name):
                print(f"✅ {package_name} 已安裝 - {description}")
                installed_packages.append(package_name)
            else:
                print(f"❌ {package_name} 未安裝 - {description}")
                missing_packages.append(package_name)
        
        if not missing_packages:
            print("\n🎉 所有依賴包都已安裝！")
            return True
        
        print(f"\n需要安裝 {len(missing_packages)} 個包...")
        
        # 安裝缺失的包
        failed_packages = []
        for package_name in missing_packages:
            success, error = self.install_package(package_name)
            if not success:
                failed_packages.append((package_name, error))
        
        # 安裝結果總結
        print("\n" + "=" * 50)
        print("📊 安裝結果總結:")
        print(f"✅ 成功安裝: {len(missing_packages) - len(failed_packages)} 個包")
        print(f"❌ 安裝失敗: {len(failed_packages)} 個包")
        
        if failed_packages:
            print("\n失敗的包:")
            for package_name, error in failed_packages:
                print(f"  - {package_name}: {error}")
            return False
        
        print("\n🎉 所有依賴包安裝完成！")
        return True
    
    def verify_installation(self):
        """驗證安裝結果"""
        print("\n🔍 驗證安裝結果...")
        
        # 測試核心功能
        test_results = {}
        
        # 測試Streamlit
        try:
            import streamlit
            test_results['Streamlit'] = "✅ 正常"
        except ImportError:
            test_results['Streamlit'] = "❌ 導入失敗"
        
        # 測試數據處理
        try:
            import pandas
            import numpy
            test_results['數據處理'] = "✅ 正常"
        except ImportError:
            test_results['數據處理'] = "❌ 導入失敗"
        
        # 測試可視化
        try:
            import plotly
            test_results['數據可視化'] = "✅ 正常"
        except ImportError:
            test_results['數據可視化'] = "❌ 導入失敗"
        
        # 顯示測試結果
        print("\n驗證結果:")
        for component, status in test_results.items():
            print(f"  {component}: {status}")
        
        return all("✅" in status for status in test_results.values())

def main():
    """主函數"""
    print("🎯 AI交易系統依賴安裝器")
    print("=" * 50)
    
    installer = DependencyInstaller()

    # 詢問安裝選項
    print("\n📦 安裝選項:")
    print("1. 基礎安裝 (僅核心依賴)")
    print("2. 推薦安裝 (核心 + 推薦依賴，適合新手)")
    print("3. 完整安裝 (包含所有可選依賴)")

    while True:
        choice = input("\n請選擇安裝選項 (1/2/3): ").strip()
        if choice == '1':
            include_recommended = False
            include_optional = False
            break
        elif choice == '2':
            include_recommended = True
            include_optional = False
            break
        elif choice == '3':
            include_recommended = True
            include_optional = True
            break
        else:
            print("請輸入 1、2 或 3")

    # 安裝依賴
    success = installer.install_all_dependencies(include_optional, include_recommended)
    
    if success:
        # 驗證安裝
        if installer.verify_installation():
            print("\n🎉 安裝完成！現在可以啟動AI交易系統:")
            print("python -m streamlit run src/ui/web_ui_production.py --server.address=127.0.0.1 --server.port=8501")
        else:
            print("\n⚠️ 安裝完成但驗證失敗，請檢查錯誤信息")
    else:
        print("\n❌ 安裝過程中出現錯誤，請檢查網絡連接和權限")

if __name__ == "__main__":
    main()
