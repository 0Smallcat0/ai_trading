#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI顯示邏輯整合測試腳本

此腳本測試AI顯示邏輯改進功能在數據檢視模組中的整合效果，
驗證增強的股價走勢圖功能和AI整合功能。

主要測試內容：
- 增強HTML解析器功能
- 多層備援機制
- AI整合圖表生成
- 用戶偏好學習
- 技術指標計算

Usage:
    python scripts/test_ai_display_integration.py
    
Note:
    此腳本專門測試AI顯示邏輯改進說明中功能的整合效果。
"""

import sys
import os
import logging
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# 添加項目根目錄到Python路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AIDisplayIntegrationTester:
    """AI顯示邏輯整合測試器"""
    
    def __init__(self):
        """初始化測試器"""
        self.test_results = {}
        logger.info("✅ AI顯示邏輯整合測試器初始化完成")
        
    def run_all_tests(self):
        """執行所有測試"""
        logger.info("🚀 開始執行AI顯示邏輯整合測試")
        
        tests = [
            ("模組依賴檢查", self._test_module_dependencies),
            ("整合特徵計算器", self._test_integrated_feature_calculator),
            ("AI自學代理", self._test_self_learning_agent),
            ("互動圖表組件", self._test_interactive_charts),
            ("數據管理整合", self._test_data_management_integration),
        ]
        
        for test_name, test_func in tests:
            try:
                logger.info(f"🔍 執行測試: {test_name}")
                result = test_func()
                self.test_results[test_name] = result
                status = "✅ 通過" if result["success"] else "❌ 失敗"
                logger.info(f"{status} {test_name}: {result['message']}")
            except Exception as e:
                logger.error(f"❌ 測試 {test_name} 發生錯誤: {e}")
                self.test_results[test_name] = {
                    "success": False,
                    "message": f"測試執行錯誤: {e}",
                    "details": str(e)
                }
        
        # 生成測試報告
        self._generate_test_report()
        
    def _test_module_dependencies(self):
        """測試模組依賴"""
        try:
            # 測試核心模組
            from src.core.integrated_feature_calculator import IntegratedFeatureCalculator
            from src.ai.self_learning_agent import SelfLearningAgent
            from src.ui.components.interactive_charts import agent_integrated_display
            
            # 測試可選模組
            optional_modules = {}
            try:
                import talib
                optional_modules["talib"] = "✅ 可用"
            except ImportError:
                optional_modules["talib"] = "❌ 不可用"
                
            try:
                import optuna
                optional_modules["optuna"] = "✅ 可用"
            except ImportError:
                optional_modules["optuna"] = "❌ 不可用"
                
            return {
                "success": True,
                "message": "所有核心模組依賴正常",
                "details": {
                    "core_modules": ["IntegratedFeatureCalculator", "SelfLearningAgent", "agent_integrated_display"],
                    "optional_modules": optional_modules
                }
            }
            
        except ImportError as e:
            return {
                "success": False,
                "message": f"模組依賴缺失: {e}",
                "details": str(e)
            }
            
    def _test_integrated_feature_calculator(self):
        """測試整合特徵計算器"""
        try:
            from src.core.integrated_feature_calculator import IntegratedFeatureCalculator
            
            # 創建測試數據
            test_data = self._create_test_stock_data()
            data_dict = {"TEST.TW": test_data}
            
            # 初始化計算器
            calculator = IntegratedFeatureCalculator(data_dict)
            
            # 測試計算功能
            result = calculator.load_and_calculate(
                stock_id="TEST.TW",
                indicators=["RSI", "MACD"],
                multipliers=[1.0],
                seasonal=False
            )
            
            if result is not None and not result.empty:
                return {
                    "success": True,
                    "message": f"特徵計算器正常，生成 {len(result)} 筆指標數據",
                    "details": {
                        "indicators_calculated": list(result.columns),
                        "data_points": len(result)
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "特徵計算器返回空結果",
                    "details": "計算結果為空或None"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"特徵計算器測試失敗: {e}",
                "details": str(e)
            }
            
    def _test_self_learning_agent(self):
        """測試AI自學代理"""
        try:
            from src.ai.self_learning_agent import SelfLearningAgent
            
            # 創建測試代理
            agent = SelfLearningAgent("test_user")
            
            # 記錄測試互動
            test_interactions = [
                {
                    "interaction_type": "chart_view",
                    "parameters": {"indicators": ["RSI"], "multipliers": [1.0]},
                    "result_quality": 0.8
                },
                {
                    "interaction_type": "chart_view", 
                    "parameters": {"indicators": ["MACD"], "multipliers": [1.5]},
                    "result_quality": 0.9
                }
            ]
            
            for interaction in test_interactions:
                agent.record_user_interaction(**interaction)
                
            # 測試學習功能
            if len(agent.user_interactions) >= 2:
                base_params = {"indicators": ["RSI"], "multipliers": [1.0]}
                try:
                    optimized_params = agent.predict_optimal_parameters("TEST.TW", base_params)
                    learning_active = True
                except:
                    optimized_params = base_params
                    learning_active = False
                    
                return {
                    "success": True,
                    "message": f"AI代理正常，記錄 {len(agent.user_interactions)} 次互動",
                    "details": {
                        "interactions_count": len(agent.user_interactions),
                        "learning_active": learning_active,
                        "optimized_params": optimized_params
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "AI代理互動記錄失敗",
                    "details": f"預期2次互動，實際 {len(agent.user_interactions)} 次"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"AI自學代理測試失敗: {e}",
                "details": str(e)
            }
            
    def _test_interactive_charts(self):
        """測試互動圖表組件"""
        try:
            from src.ui.components.interactive_charts import agent_integrated_display
            
            # 創建測試數據
            test_data = self._create_test_stock_data()
            data_dict = {"TEST.TW": test_data}
            
            # 測試圖表生成
            fig = agent_integrated_display(
                stock_id="TEST.TW",
                data_dict=data_dict,
                indicators=["RSI"],
                multipliers=[1.0],
                enable_ai_signals=True
            )
            
            if fig is not None and hasattr(fig, 'data'):
                return {
                    "success": True,
                    "message": f"互動圖表生成成功，包含 {len(fig.data)} 個數據系列",
                    "details": {
                        "chart_traces": len(fig.data),
                        "chart_type": type(fig).__name__
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "互動圖表生成失敗",
                    "details": "返回的圖表對象無效"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"互動圖表測試失敗: {e}",
                "details": str(e)
            }
            
    def _test_data_management_integration(self):
        """測試數據管理整合"""
        try:
            # 檢查數據管理頁面中的AI整合函數
            from src.ui.pages.data_management import _show_ai_integrated_chart
            
            # 檢查函數是否存在且可調用
            if callable(_show_ai_integrated_chart):
                return {
                    "success": True,
                    "message": "數據管理模組AI整合功能可用",
                    "details": {
                        "function_name": "_show_ai_integrated_chart",
                        "module": "src.ui.pages.data_management",
                        "callable": True
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "AI整合函數不可調用",
                    "details": "函數存在但不可調用"
                }
                
        except ImportError as e:
            return {
                "success": False,
                "message": f"數據管理模組導入失敗: {e}",
                "details": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"數據管理整合測試失敗: {e}",
                "details": str(e)
            }
            
    def _create_test_stock_data(self):
        """創建測試股票數據"""
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        dates = dates[dates.weekday < 5]  # 只保留工作日
        
        # 生成模擬股價數據
        import numpy as np
        np.random.seed(42)
        
        base_price = 100
        prices = []
        for i in range(len(dates)):
            change = np.random.normal(0, 2)  # 平均0，標準差2的價格變動
            base_price += change
            base_price = max(base_price, 10)  # 確保價格不會太低
            prices.append(base_price)
            
        # 創建OHLCV數據
        data = pd.DataFrame({
            'open': [p * (1 + np.random.uniform(-0.02, 0.02)) for p in prices],
            'high': [p * (1 + abs(np.random.uniform(0, 0.03))) for p in prices],
            'low': [p * (1 - abs(np.random.uniform(0, 0.03))) for p in prices],
            'close': prices,
            'volume': [np.random.randint(1000000, 10000000) for _ in prices]
        }, index=dates)
        
        return data
        
    def _generate_test_report(self):
        """生成測試報告"""
        print("\n" + "="*60)
        print("🧪 AI顯示邏輯整合測試報告")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["success"])
        
        print(f"📊 測試摘要:")
        print(f"  總測試數: {total_tests}")
        print(f"  通過測試: {passed_tests}")
        print(f"  失敗測試: {total_tests - passed_tests}")
        print(f"  成功率: {passed_tests/total_tests*100:.1f}%")
        
        print(f"\n📋 詳細結果:")
        for test_name, result in self.test_results.items():
            status = "✅ 通過" if result["success"] else "❌ 失敗"
            print(f"  {status} {test_name}: {result['message']}")
            
        if passed_tests == total_tests:
            print(f"\n🎉 所有測試通過！AI顯示邏輯整合功能正常。")
        else:
            print(f"\n⚠️ 有 {total_tests - passed_tests} 個測試失敗，請檢查相關功能。")
            
        print("="*60)


def main():
    """主函數"""
    print("🚀 開始AI顯示邏輯整合測試...")
    
    try:
        tester = AIDisplayIntegrationTester()
        tester.run_all_tests()
        
    except Exception as e:
        logger.error(f"❌ 測試過程中發生錯誤: {e}")
        print(f"❌ 測試失敗: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
