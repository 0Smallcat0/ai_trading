#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心功能測試腳本（不依賴 Streamlit）

此腳本測試新手友好界面的核心邏輯功能，
不依賴 Streamlit 等 UI 框架。

Author: AI Trading System
Version: 1.0.0
"""

import sys
import os
import traceback
import pandas as pd
import numpy as np

# 添加項目根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

class MockStreamlit:
    """模擬 Streamlit 模組以進行測試"""
    
    def __init__(self):
        self.session_state = {}
    
    def title(self, text):
        pass
    
    def markdown(self, text):
        pass
    
    def subheader(self, text):
        pass
    
    def write(self, text):
        pass
    
    def selectbox(self, label, options, **kwargs):
        return options[0] if options else None
    
    def slider(self, label, min_val, max_val, value, **kwargs):
        return value
    
    def button(self, label, **kwargs):
        return False
    
    def columns(self, num):
        return [MockColumn() for _ in range(num)]
    
    def container(self):
        return MockContainer()
    
    def expander(self, label, **kwargs):
        return MockExpander()
    
    def tabs(self, labels):
        return [MockTab() for _ in labels]
    
    def success(self, text):
        pass
    
    def warning(self, text):
        pass
    
    def error(self, text):
        pass
    
    def info(self, text):
        pass
    
    def progress(self, value):
        pass
    
    def metric(self, label, value, delta=None):
        pass
    
    def plotly_chart(self, fig, **kwargs):
        pass
    
    def dataframe(self, df, **kwargs):
        pass
    
    def json(self, data):
        pass

class MockColumn:
    """模擬 Streamlit Column"""
    
    def __init__(self):
        self.session_state = {}
    
    def title(self, text):
        pass
    
    def markdown(self, text):
        pass
    
    def write(self, text):
        pass
    
    def button(self, label, **kwargs):
        return False
    
    def selectbox(self, label, options, **kwargs):
        return options[0] if options else None
    
    def metric(self, label, value, delta=None):
        pass

class MockContainer:
    """模擬 Streamlit Container"""
    
    def __init__(self):
        pass
    
    def title(self, text):
        pass
    
    def markdown(self, text):
        pass
    
    def write(self, text):
        pass

class MockExpander:
    """模擬 Streamlit Expander"""
    
    def __init__(self):
        pass
    
    def title(self, text):
        pass
    
    def markdown(self, text):
        pass
    
    def write(self, text):
        pass

class MockTab:
    """模擬 Streamlit Tab"""
    
    def __init__(self):
        pass
    
    def title(self, text):
        pass
    
    def markdown(self, text):
        pass
    
    def write(self, text):
        pass

# 模擬 Streamlit 模組
sys.modules['streamlit'] = MockStreamlit()

def test_strategy_templates():
    """測試策略模板功能"""
    print("🎯 測試策略模板功能...")
    
    try:
        from src.ui.simplified import StrategyTemplates
        strategy_templates = StrategyTemplates()
        
        # 測試獲取可用模板
        templates = strategy_templates.get_available_templates()
        assert isinstance(templates, dict), "模板應該是字典格式"
        assert len(templates) > 0, "應該有可用的策略模板"
        
        # 測試模板配置
        for template_name, template_config in templates.items():
            assert 'name' in template_config, f"模板 {template_name} 應該有名稱"
            assert 'description' in template_config, f"模板 {template_name} 應該有描述"
            assert 'risk_level' in template_config, f"模板 {template_name} 應該有風險等級"
        
        print("  ✅ 策略模板核心功能正常")
        return True
        
    except Exception as e:
        print(f"  ❌ 策略模板功能測試失敗: {e}")
        traceback.print_exc()
        return False

def test_risk_assessment():
    """測試風險評估功能"""
    print("🎚️ 測試風險評估功能...")
    
    try:
        from src.ui.simplified import RiskLevelSelector
        risk_selector = RiskLevelSelector()
        
        # 測試風險評估問題
        questions = risk_selector.get_risk_assessment_questions()
        assert isinstance(questions, list), "問題應該是列表格式"
        assert len(questions) > 0, "應該有風險評估問題"
        
        # 測試風險等級計算
        sample_answers = [3, 2, 4, 1, 3]  # 示例答案
        risk_level = risk_selector.calculate_risk_level(sample_answers)
        assert risk_level in ['conservative', 'moderate', 'aggressive', 'very_aggressive'], "風險等級應該是有效值"
        
        print("  ✅ 風險評估核心功能正常")
        return True
        
    except Exception as e:
        print(f"  ❌ 風險評估功能測試失敗: {e}")
        traceback.print_exc()
        return False

def test_education_content():
    """測試教育內容功能"""
    print("📚 測試教育內容功能...")
    
    try:
        from src.education import TradingBasics
        trading_basics = TradingBasics()
        
        # 測試課程模組
        modules = trading_basics.get_course_modules()
        assert isinstance(modules, dict), "課程模組應該是字典格式"
        assert len(modules) > 0, "應該有課程模組"
        
        # 測試術語詞典
        glossary = trading_basics.get_glossary()
        assert isinstance(glossary, dict), "術語詞典應該是字典格式"
        assert len(glossary) > 0, "應該有術語定義"
        
        # 測試示範資料生成
        sample_data = trading_basics.generate_sample_data(100)
        assert isinstance(sample_data, pd.DataFrame), "示範資料應該是 DataFrame"
        assert len(sample_data) == 100, "應該生成指定數量的資料"
        
        print("  ✅ 教育內容核心功能正常")
        return True
        
    except Exception as e:
        print(f"  ❌ 教育內容功能測試失敗: {e}")
        traceback.print_exc()
        return False

def test_error_prevention():
    """測試錯誤預防功能"""
    print("🚨 測試錯誤預防功能...")
    
    try:
        from src.education import ErrorPrevention
        error_prevention = ErrorPrevention()
        
        # 測試錯誤類型
        error_types = error_prevention.get_error_types()
        assert isinstance(error_types, dict), "錯誤類型應該是字典格式"
        assert len(error_types) > 0, "應該有錯誤類型定義"
        
        # 測試錯誤檢查
        sample_config = {
            'position_size': 0.5,
            'stop_loss': 0.02,
            'take_profit': 0.04
        }
        
        errors = error_prevention.check_configuration(sample_config)
        assert isinstance(errors, list), "錯誤檢查結果應該是列表"
        
        print("  ✅ 錯誤預防核心功能正常")
        return True
        
    except Exception as e:
        print(f"  ❌ 錯誤預防功能測試失敗: {e}")
        traceback.print_exc()
        return False

def test_backtest_simulation():
    """測試回測模擬功能"""
    print("📊 測試回測模擬功能...")
    
    try:
        from src.ui.simplified import OneClickBacktest
        backtest = OneClickBacktest()
        
        # 測試測試類型
        test_types = backtest.get_test_types()
        assert isinstance(test_types, dict), "測試類型應該是字典格式"
        assert len(test_types) > 0, "應該有測試類型"
        
        # 測試快速回測
        sample_strategy = {
            'name': 'moving_average',
            'parameters': {'short_window': 10, 'long_window': 30}
        }
        
        result = backtest.run_quick_test(sample_strategy)
        assert isinstance(result, dict), "回測結果應該是字典格式"
        assert 'performance' in result, "結果應該包含績效資訊"
        
        print("  ✅ 回測模擬核心功能正常")
        return True
        
    except Exception as e:
        print(f"  ❌ 回測模擬功能測試失敗: {e}")
        traceback.print_exc()
        return False

def run_core_functionality_tests():
    """運行核心功能測試"""
    print("🚀 開始新手友好界面核心功能測試")
    print("=" * 60)
    
    tests = [
        test_strategy_templates,
        test_risk_assessment,
        test_education_content,
        test_error_prevention,
        test_backtest_simulation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 測試 {test.__name__} 發生異常: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有核心功能測試通過！")
        return True
    else:
        print("⚠️ 部分核心功能測試失敗，請檢查相關模組。")
        return False

if __name__ == "__main__":
    success = run_core_functionality_tests()
    sys.exit(0 if success else 1)
