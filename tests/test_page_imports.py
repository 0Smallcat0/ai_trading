#!/usr/bin/env python3
"""頁面導入測試腳本

此腳本用於測試12個功能分類組件調用原有頁面文件時的導入狀況。

測試內容：
- 檢查所有組件文件能否成功導入對應的頁面文件
- 識別 ImportError 問題
- 提供修復建議

Example:
    >>> python test_page_imports.py
"""

import sys
import os
import importlib
from typing import Dict, List, Tuple

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_page_import(page_module_name: str) -> Tuple[bool, str]:
    """測試頁面模組導入.
    
    Args:
        page_module_name: 頁面模組名稱
        
    Returns:
        Tuple[bool, str]: (是否成功, 錯誤訊息)
    """
    try:
        module = importlib.import_module(page_module_name)
        
        # 檢查是否有 show 函數
        if hasattr(module, 'show'):
            return True, "成功"
        else:
            return False, "缺少 show() 函數"
            
    except ImportError as e:
        return False, f"ImportError: {e}"
    except Exception as e:
        return False, f"其他錯誤: {e}"


def test_component_page_imports():
    """測試組件調用頁面的導入狀況."""
    print("🧪 開始測試12個功能分類的頁面導入...")
    print("=" * 80)
    
    # 定義組件調用的頁面映射
    component_page_mapping = {
        "system_status_monitoring": [
            "src.ui.pages.system_monitoring",
            "src.ui.pages.system_status_enhanced", 
            "src.ui.pages.function_status_dashboard"
        ],
        "security_permission_management": [
            "src.ui.pages.security_management",
            "src.ui.pages.two_factor_management"
        ],
        "multi_agent_system_management": [
            "src.ui.pages.multi_agent_dashboard",
            "src.ui.pages.advanced_monitoring"
        ],
        "data_management": [
            "src.ui.pages.data_management",
            "src.ui.pages.data_source_config_wizard"
        ],
        "strategy_development": [
            "src.ui.pages.strategy_management",
            "src.ui.pages.rl_strategy_management"
        ],
        "ai_decision_support": [
            "src.ui.pages.intelligent_recommendations",
            "src.ui.pages.llm_decision"
        ],
        "portfolio_management": [
            "src.ui.pages.portfolio_management",
            "src.ui.pages.text_analysis"
        ],
        "risk_management": [
            "src.ui.pages.risk_management"
        ],
        "trade_execution": [
            "src.ui.pages.trade_execution"
        ],
        "ai_model_management": [
            "src.ui.pages.ai_model_management",
            "src.ui.pages.ai_models"
        ],
        "backtest_analysis": [
            "src.ui.pages.backtest_enhanced",
            "src.ui.pages.interactive_charts"
        ],
        "learning_center": [
            "src.ui.pages.beginner_hub",
            "src.ui.pages.beginner_tutorial",
            "src.ui.pages.knowledge_base",
            "src.ui.pages.learning_center"
        ]
    }
    
    # 統計結果
    total_pages = 0
    successful_imports = 0
    failed_imports = []
    
    # 測試每個功能分類
    for component, pages in component_page_mapping.items():
        print(f"\n📂 {component}")
        print("-" * 60)
        
        for page in pages:
            total_pages += 1
            success, message = test_page_import(page)
            
            if success:
                successful_imports += 1
                print(f"  ✅ {page}: {message}")
            else:
                failed_imports.append((page, message))
                print(f"  ❌ {page}: {message}")
    
    # 顯示統計結果
    print("\n" + "=" * 80)
    print("📊 導入測試統計")
    print("=" * 80)
    
    success_rate = (successful_imports / total_pages) * 100 if total_pages > 0 else 0
    
    print(f"總頁面數: {total_pages}")
    print(f"成功導入: {successful_imports}")
    print(f"失敗導入: {len(failed_imports)}")
    print(f"成功率: {success_rate:.1f}%")
    
    # 顯示失敗的導入
    if failed_imports:
        print("\n❌ 失敗的導入清單:")
        print("-" * 60)
        for page, error in failed_imports:
            print(f"  {page}: {error}")
    
    return len(failed_imports) == 0, failed_imports


def test_component_imports():
    """測試組件文件本身的導入."""
    print("\n🔧 測試組件文件導入...")
    print("=" * 80)
    
    components = [
        "src.ui.components.system_status_monitoring",
        "src.ui.components.security_permission_management", 
        "src.ui.components.multi_agent_system_management",
        "src.ui.components.data_management",
        "src.ui.components.strategy_development",
        "src.ui.components.ai_decision_support",
        "src.ui.components.portfolio_management",
        "src.ui.components.risk_management",
        "src.ui.components.trade_execution",
        "src.ui.components.ai_model_management",
        "src.ui.components.backtest_analysis",
        "src.ui.components.learning_center"
    ]
    
    failed_components = []
    
    for component in components:
        success, message = test_page_import(component)
        if success:
            print(f"✅ {component}: {message}")
        else:
            failed_components.append((component, message))
            print(f"❌ {component}: {message}")
    
    return len(failed_components) == 0, failed_components


def generate_fix_suggestions(failed_imports: List[Tuple[str, str]]):
    """生成修復建議."""
    if not failed_imports:
        return
    
    print("\n🔧 修復建議:")
    print("=" * 80)
    
    for page, error in failed_imports:
        page_name = page.split('.')[-1]
        file_path = page.replace('.', '/') + '.py'
        
        print(f"\n📄 {page}")
        print(f"   文件路徑: {file_path}")
        print(f"   錯誤: {error}")
        
        if "ImportError" in error:
            print("   建議:")
            print("   1. 檢查文件是否存在")
            print("   2. 檢查文件中的導入語句")
            print("   3. 確保所有依賴模組都可用")
        elif "缺少 show() 函數" in error:
            print("   建議:")
            print("   1. 在文件中添加 show() 函數")
            print("   2. 確保函數簽名正確: def show() -> None:")
        else:
            print("   建議:")
            print("   1. 檢查文件語法錯誤")
            print("   2. 檢查文件編碼問題")


def main():
    """主測試函數."""
    print("🚀 開始12個功能分類頁面導入測試")
    print("=" * 80)
    
    try:
        # 測試組件文件導入
        components_ok, failed_components = test_component_imports()
        
        # 測試頁面文件導入
        pages_ok, failed_pages = test_component_page_imports()
        
        # 生成修復建議
        if failed_pages:
            generate_fix_suggestions(failed_pages)
        
        # 總結
        print("\n" + "=" * 80)
        print("📋 測試總結")
        print("=" * 80)
        
        if components_ok and pages_ok:
            print("🎉 所有導入測試通過！12個功能分類系統頁面導入正常。")
            print("\n✅ 驗證項目:")
            print("  - 所有組件文件導入成功")
            print("  - 所有頁面文件導入成功")
            print("  - 所有頁面都有 show() 函數")
            
            print("\n🔗 下一步:")
            print("  - 啟動應用測試功能")
            print("  - 檢查每個功能分類的子標籤頁")
            print("  - 確認不再出現「功能暫時不可用」警告")
            
            return 0
        else:
            print("❌ 部分導入測試失敗！")
            
            if not components_ok:
                print(f"  - {len(failed_components)} 個組件文件導入失敗")
            
            if not pages_ok:
                print(f"  - {len(failed_pages)} 個頁面文件導入失敗")
            
            print("\n請根據上述修復建議解決問題。")
            return 1
            
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
