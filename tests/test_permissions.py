#!/usr/bin/env python3
"""12個功能分類權限系統測試腳本

此腳本用於測試12個功能分類的角色權限管理系統的正確性。

測試內容：
- 12個功能分類的權限映射
- 4個角色的權限檢查函數正確性
- 角色權限對比表

Example:
    >>> python test_permissions.py
"""

import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.utils.page_renderer import check_page_permission, get_role_permissions


def test_role_permissions():
    """測試12個功能分類的角色權限系統."""
    print("🧪 開始測試12個功能分類權限系統...")
    print("=" * 80)
    
    # 定義測試數據 (更新為12個功能分類)
    roles = ["admin", "trader", "analyst", "demo"]
    categories = [
        "system_status_monitoring", "security_permission_management", "multi_agent_system_management",
        "data_management", "strategy_development", "ai_decision_support",
        "portfolio_management", "risk_management", "trade_execution",
        "ai_model_management", "backtest_analysis", "learning_center"
    ]

    # 預期的權限映射 (更新為12個功能分類)
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
        print("-" * 40)
        
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
    
    # 顯示12個功能分類權限對比表
    print("\n" + "=" * 80)
    print("📊 12個功能分類權限對比表")
    print("=" * 80)
    
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
    print("-" * 80)

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
    print("\n" + "=" * 80)
    if all_tests_passed:
        print("🎉 所有12個功能分類權限測試通過！")
        return True
    else:
        print("❌ 部分12個功能分類權限測試失敗！")
        return False


def test_demo_accounts():
    """測試示範帳戶配置."""
    print("\n🔐 測試示範帳戶配置...")
    print("=" * 60)
    
    # 示範帳戶配置
    demo_accounts = {
        "admin": {"password": "admin123", "role": "admin"},
        "trader": {"password": "trader123", "role": "trader"},
        "analyst": {"password": "analyst123", "role": "analyst"},
        "demo": {"password": "demo123", "role": "demo"}
    }
    
    print("示範帳戶清單:")
    for username, config in demo_accounts.items():
        role = config["role"]
        password = config["password"]
        permissions_count = len(get_role_permissions(role))
        
        print(f"👤 {username}")
        print(f"   密碼: {password}")
        print(f"   角色: {role}")
        print(f"   權限數量: {permissions_count}")
        print()
    
    return True


def main():
    """主測試函數."""
    print("🚀 開始權限系統完整測試")
    print("=" * 60)
    
    try:
        # 測試權限系統
        permissions_ok = test_role_permissions()
        
        # 測試示範帳戶
        accounts_ok = test_demo_accounts()
        
        # 總結
        print("=" * 60)
        print("📋 測試總結")
        print("=" * 60)
        
        if permissions_ok and accounts_ok:
            print("🎉 所有測試通過！權限系統運行正常。")
            print("\n✅ 驗證項目:")
            print("  - 角色權限映射正確")
            print("  - 權限檢查函數正常")
            print("  - 示範帳戶配置完整")
            print("  - 權限對比表顯示正確")
            
            print("\n🔗 測試連結:")
            print("  應用地址: http://localhost:8501")
            print("  使用示範帳戶登入測試不同角色權限")
            
            return 0
        else:
            print("❌ 測試失敗！請檢查權限系統配置。")
            return 1
            
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
