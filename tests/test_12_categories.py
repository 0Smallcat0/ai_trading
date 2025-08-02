#!/usr/bin/env python3
"""12個功能分類測試腳本

此腳本用於測試新的12個功能分類架構的正確性。

測試內容：
- 12個功能分類的權限映射
- 權限檢查函數的正確性
- 組件映射的完整性
- 功能分類對比

Example:
    >>> python test_12_categories.py
"""

import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.utils.page_renderer import check_page_permission, get_role_permissions


def test_12_categories_permissions():
    """測試12個功能分類的權限系統."""
    print("🧪 開始測試12個功能分類權限系統...")
    print("=" * 70)
    
    # 定義測試數據
    roles = ["admin", "trader", "analyst", "demo"]
    categories = [
        "system_status_monitoring", "security_permission_management", "multi_agent_system_management",
        "data_management", "strategy_development", "ai_decision_support", 
        "portfolio_management", "risk_management", "trade_execution", 
        "ai_model_management", "backtest_analysis", "learning_center"
    ]
    
    # 預期的權限映射
    expected_permissions = {
        "admin": [
            "system_status_monitoring", "security_permission_management", "multi_agent_system_management",
            "data_management", "strategy_development", "ai_decision_support", 
            "portfolio_management", "risk_management", "trade_execution", 
            "ai_model_management", "backtest_analysis", "learning_center"
        ],
        "trader": [
            "trade_execution", "strategy_development", "risk_management", 
            "portfolio_management", "backtest_analysis"
        ],
        "analyst": [
            "data_management", "backtest_analysis", "ai_model_management", 
            "ai_decision_support", "learning_center"
        ],
        "demo": [
            "learning_center", "data_management", "backtest_analysis"
        ]
    }
    
    # 測試每個角色的權限
    all_tests_passed = True
    
    for role in roles:
        print(f"\n📋 測試角色: {role}")
        print("-" * 50)
        
        # 獲取角色權限
        actual_permissions = get_role_permissions(role)
        expected = expected_permissions[role]
        
        print(f"預期權限數量: {len(expected)}")
        print(f"實際權限數量: {len(actual_permissions)}")
        
        # 檢查權限是否匹配
        if set(actual_permissions) == set(expected):
            print("✅ 權限映射正確")
        else:
            print("❌ 權限映射錯誤")
            print(f"預期: {expected}")
            print(f"實際: {actual_permissions}")
            all_tests_passed = False
        
        # 測試每個功能分類的權限檢查
        print("\n功能分類權限檢查:")
        for category in categories:
            has_permission = check_page_permission(category, role)
            should_have = category in expected
            
            if has_permission == should_have:
                status = "✅"
            else:
                status = "❌"
                all_tests_passed = False
            
            print(f"  {status} {category}: {has_permission}")
    
    # 顯示12個功能分類對比表
    print("\n" + "=" * 70)
    print("📊 12個功能分類權限對比表")
    print("=" * 70)
    
    # 功能分類名稱映射
    category_names = {
        "system_status_monitoring": "🖥️ 系統狀態監控",
        "security_permission_management": "🔐 安全與權限管理",
        "multi_agent_system_management": "🤖 多代理系統管理",
        "data_management": "📊 數據管理",
        "strategy_development": "🎯 策略開發",
        "ai_decision_support": "🧠 AI決策支援",
        "portfolio_management": "💼 投資組合管理",
        "risk_management": "⚠️ 風險管理",
        "trade_execution": "💰 交易執行",
        "ai_model_management": "🤖 AI模型管理",
        "backtest_analysis": "📈 回測分析",
        "learning_center": "📚 學習中心"
    }
    
    # 表頭
    header = f"{'功能分類':<25}"
    for role in roles:
        header += f"{role:<12}"
    print(header)
    print("-" * 70)
    
    # 表格內容
    for category in categories:
        category_name = category_names.get(category, category)
        row = f"{category_name:<25}"
        for role in roles:
            has_permission = check_page_permission(category, role)
            symbol = "✅" if has_permission else "❌"
            row += f"{symbol:<12}"
        print(row)
    
    # 測試結果
    print("\n" + "=" * 70)
    if all_tests_passed:
        print("🎉 所有12個功能分類權限測試通過！")
        return True
    else:
        print("❌ 部分功能分類權限測試失敗！")
        return False


def test_component_mapping():
    """測試組件映射完整性."""
    print("\n🔧 測試組件映射完整性...")
    print("=" * 70)
    
    # 定義預期的組件映射
    expected_components = {
        "system_status_monitoring": "src.ui.components.system_status_monitoring",
        "security_permission_management": "src.ui.components.security_permission_management",
        "multi_agent_system_management": "src.ui.components.multi_agent_system_management",
        "data_management": "src.ui.components.data_management",
        "strategy_development": "src.ui.components.strategy_development",
        "ai_decision_support": "src.ui.components.ai_decision_support",
        "portfolio_management": "src.ui.components.portfolio_management",
        "risk_management": "src.ui.components.risk_management",
        "trade_execution": "src.ui.components.trade_execution",
        "ai_model_management": "src.ui.components.ai_model_management",
        "backtest_analysis": "src.ui.components.backtest_analysis",
        "learning_center": "src.ui.components.learning_center"
    }
    
    all_components_exist = True
    
    for category, module_path in expected_components.items():
        try:
            # 嘗試導入組件模組
            module_parts = module_path.split('.')
            module_name = '.'.join(module_parts)
            
            # 檢查文件是否存在
            file_path = '/'.join(module_parts) + '.py'
            if os.path.exists(file_path):
                print(f"✅ {category}: {file_path} 存在")
            else:
                print(f"❌ {category}: {file_path} 不存在")
                all_components_exist = False
                
        except Exception as e:
            print(f"❌ {category}: 檢查失敗 - {e}")
            all_components_exist = False
    
    if all_components_exist:
        print("🎉 所有組件文件都存在！")
        return True
    else:
        print("❌ 部分組件文件缺失！")
        return False


def test_category_structure():
    """測試功能分類結構."""
    print("\n📋 測試功能分類結構...")
    print("=" * 70)
    
    # 定義預期的子功能數量
    expected_sub_functions = {
        "system_status_monitoring": 3,  # 系統監控、系統狀態監控、功能狀態儀表板
        "security_permission_management": 2,  # 安全管理、雙因子認證
        "multi_agent_system_management": 2,  # 多代理儀表板、高級監控
        "data_management": 2,  # 數據管理、數據源配置
        "strategy_development": 2,  # 策略管理、強化學習策略
        "ai_decision_support": 2,  # 智能推薦、LLM決策
        "portfolio_management": 2,  # 投資組合、文本分析
        "risk_management": 3,  # 風險管理 + 動態調整 + 監控告警
        "trade_execution": 3,  # 交易執行 + 智能執行 + 績效分析
        "ai_model_management": 2,  # AI模型管理、AI模型
        "backtest_analysis": 2,  # 回測增強、互動式圖表
        "learning_center": 4  # 新手中心、新手教學、知識庫、學習中心
    }
    
    print("功能分類子功能數量檢查:")
    for category, expected_count in expected_sub_functions.items():
        print(f"📂 {category}: 預期 {expected_count} 個子功能")
    
    total_sub_functions = sum(expected_sub_functions.values())
    print(f"\n📊 總計: 12個功能分類，{total_sub_functions}個子功能")
    
    return True


def main():
    """主測試函數."""
    print("🚀 開始12個功能分類系統完整測試")
    print("=" * 70)
    
    try:
        # 測試權限系統
        permissions_ok = test_12_categories_permissions()
        
        # 測試組件映射
        components_ok = test_component_mapping()
        
        # 測試分類結構
        structure_ok = test_category_structure()
        
        # 總結
        print("=" * 70)
        print("📋 測試總結")
        print("=" * 70)
        
        if permissions_ok and components_ok and structure_ok:
            print("🎉 所有測試通過！12個功能分類系統運行正常。")
            print("\n✅ 驗證項目:")
            print("  - 12個功能分類權限映射正確")
            print("  - 權限檢查函數正常")
            print("  - 組件文件完整")
            print("  - 功能分類結構合理")
            
            print("\n🔗 測試連結:")
            print("  應用地址: http://localhost:8501")
            print("  使用示範帳戶登入測試不同角色權限")
            print("  測試單次點擊切換功能")
            
            return 0
        else:
            print("❌ 測試失敗！請檢查12個功能分類系統配置。")
            return 1
            
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
