#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新手友好界面測試腳本

此腳本用於測試新手友好界面的各個功能模組，
確保所有組件都能正常工作。

Author: AI Trading System
Version: 1.0.0
"""

import sys
import os
import traceback

# 添加項目根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_imports():
    """測試所有模組的導入"""
    print("🔍 測試模組導入...")
    
    try:
        # 測試新手引導模組
        print("  📚 測試新手引導模組...")
        from src.ui.onboarding import (
            SetupWizard, QuickStartGuide, DemoStrategies, 
            PracticeMode, ProgressDashboard
        )
        print("    ✅ 新手引導模組導入成功")
        
        # 測試簡化操作模組
        print("  🎯 測試簡化操作模組...")
        from src.ui.simplified import (
            StrategyTemplates, OneClickBacktest, 
            RiskLevelSelector, SimpleConfigPanel
        )
        print("    ✅ 簡化操作模組導入成功")
        
        # 測試教育資源模組
        print("  📖 測試教育資源模組...")
        from src.education import (
            TradingBasics, StrategyExplainer, 
            RiskEducation, ErrorPrevention
        )
        print("    ✅ 教育資源模組導入成功")
        
        # 測試新手中心
        print("  🎓 測試新手中心...")
        from src.ui.pages.beginner_hub import show_beginner_hub
        print("    ✅ 新手中心導入成功")
        
        print("✅ 所有模組導入測試通過！")
        return True
        
    except Exception as e:
        print(f"❌ 模組導入測試失敗: {e}")
        traceback.print_exc()
        return False

def test_class_initialization():
    """測試類別初始化"""
    print("\n🏗️ 測試類別初始化...")
    
    try:
        # 測試新手引導類別
        print("  📚 測試新手引導類別...")
        from src.ui.onboarding import (
            SetupWizard, QuickStartGuide, DemoStrategies, 
            PracticeMode, ProgressDashboard
        )
        
        setup_wizard = SetupWizard()
        quick_start = QuickStartGuide()
        demo_strategies = DemoStrategies()
        practice_mode = PracticeMode()
        progress_dashboard = ProgressDashboard()
        print("    ✅ 新手引導類別初始化成功")
        
        # 測試簡化操作類別
        print("  🎯 測試簡化操作類別...")
        from src.ui.simplified import (
            StrategyTemplates, OneClickBacktest, 
            RiskLevelSelector, SimpleConfigPanel
        )
        
        strategy_templates = StrategyTemplates()
        one_click_backtest = OneClickBacktest()
        risk_level_selector = RiskLevelSelector()
        simple_config_panel = SimpleConfigPanel()
        print("    ✅ 簡化操作類別初始化成功")
        
        # 測試教育資源類別
        print("  📖 測試教育資源類別...")
        from src.education import (
            TradingBasics, StrategyExplainer, 
            RiskEducation, ErrorPrevention
        )
        
        trading_basics = TradingBasics()
        strategy_explainer = StrategyExplainer()
        risk_education = RiskEducation()
        error_prevention = ErrorPrevention()
        print("    ✅ 教育資源類別初始化成功")
        
        print("✅ 所有類別初始化測試通過！")
        return True
        
    except Exception as e:
        print(f"❌ 類別初始化測試失敗: {e}")
        traceback.print_exc()
        return False

def test_basic_functionality():
    """測試基本功能"""
    print("\n🚀 測試核心功能...")
    
    try:
        # 測試策略模板功能
        print("  🎯 測試策略模板功能...")
        from src.ui.simplified import StrategyTemplates
        strategy_templates = StrategyTemplates()
        
        templates = strategy_templates.get_available_templates()
        assert len(templates) > 0, "應該有可用的策略模板"
        print("    ✅ 策略模板核心功能正常")
        
        # 測試風險評估功能
        print("  🎚️ 測試風險評估功能...")
        from src.ui.simplified import RiskLevelSelector
        risk_selector = RiskLevelSelector()
        
        risk_questions = risk_selector.get_risk_assessment_questions()
        assert len(risk_questions) > 0, "應該有風險評估問題"
        print("    ✅ 風險評估核心功能正常")
        
        # 測試教育內容功能
        print("  📚 測試教育內容功能...")
        from src.education import TradingBasics
        trading_basics = TradingBasics()
        
        course_modules = trading_basics.get_course_modules()
        assert len(course_modules) > 0, "應該有課程模組"
        print("    ✅ 教育內容核心功能正常")
        
        # 測試錯誤預防功能
        print("  🚨 測試錯誤預防功能...")
        from src.education import ErrorPrevention
        error_prevention = ErrorPrevention()
        
        error_types = error_prevention.get_error_types()
        assert len(error_types) > 0, "應該有錯誤類型定義"
        print("    ✅ 錯誤預防核心功能正常")
        
        # 測試回測模擬功能
        print("  📊 測試回測模擬功能...")
        from src.ui.simplified import OneClickBacktest
        backtest = OneClickBacktest()
        
        test_types = backtest.get_test_types()
        assert len(test_types) > 0, "應該有測試類型"
        print("    ✅ 回測模擬核心功能正常")
        
        print("✅ 所有核心功能測試通過！")
        return True
        
    except Exception as e:
        print(f"❌ 核心功能測試失敗: {e}")
        traceback.print_exc()
        return False

def test_data_generation():
    """測試資料生成功能"""
    print("\n📊 測試資料生成功能...")
    
    try:
        # 測試示範資料生成
        from src.education import TradingBasics
        basics = TradingBasics()
        
        demo_data = basics.generate_sample_data(100)
        assert len(demo_data) == 100, "應該生成100天的資料"
        assert 'Close' in demo_data.columns, "應該包含收盤價"
        print("  ✅ 示範資料生成正常")
        
        # 測試策略演示資料
        from src.education import StrategyExplainer
        explainer = StrategyExplainer()
        
        strategy_data = explainer.generate_strategy_demo_data('moving_average', 50)
        assert len(strategy_data) == 50, "應該生成50天的策略資料"
        print("  ✅ 策略演示資料生成正常")
        
        # 測試風險情境資料
        from src.education import RiskEducation
        risk_education = RiskEducation()
        
        scenario_data = risk_education.generate_risk_scenario('normal')
        assert len(scenario_data) == 252, "應該生成252天的情境資料"
        print("  ✅ 風險情境資料生成正常")
        
        print("✅ 所有資料生成功能測試通過！")
        return True
        
    except Exception as e:
        print(f"❌ 資料生成功能測試失敗: {e}")
        traceback.print_exc()
        return False

def run_all_tests():
    """運行所有測試"""
    print("🚀 開始新手友好界面測試")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_class_initialization,
        test_basic_functionality,
        test_data_generation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 測試 {test.__name__} 發生異常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有測試通過！新手友好界面準備就緒。")
        return True
    else:
        print("⚠️ 部分測試失敗，請檢查相關模組。")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
