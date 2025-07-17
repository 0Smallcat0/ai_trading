#!/usr/bin/env python3
"""
AI交易系統啟動性能測試

測試系統初始化性能，確保符合性能目標：
- 總初始化時間 < 10秒
- 主儀表板載入時間 < 5秒
- 系統響應時間 < 2秒
"""

import os
import sys
import time
import logging
import requests
from typing import Dict, List, Tuple

# 添加專案根目錄到Python路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTest:
    """性能測試類"""
    
    def __init__(self):
        self.results = {}
        self.web_ui_url = "http://localhost:8501"
    
    def test_module_import_performance(self) -> Dict[str, float]:
        """測試模組導入性能"""
        print("🚀 測試模組導入性能...")
        
        import_times = {}
        
        # 測試核心模組導入時間
        modules_to_test = [
            ("core.backtest", "BacktestEngine"),
            ("core.portfolio", "PortfolioOptimizer"),
            ("core.risk_control", "RiskController"),
        ]
        
        for module_name, class_name in modules_to_test:
            start_time = time.time()
            try:
                module = __import__(f"src.{module_name}", fromlist=[class_name])
                getattr(module, class_name)
                import_time = time.time() - start_time
                import_times[module_name] = import_time
                print(f"  ✅ {module_name}: {import_time:.3f}s")
            except Exception as e:
                import_times[module_name] = -1
                print(f"  ❌ {module_name}: 失敗 ({e})")
        
        return import_times
    
    def test_data_manager_initialization(self) -> float:
        """測試資料管理器初始化性能（延遲初始化）"""
        print("📊 測試資料管理器初始化性能...")
        
        start_time = time.time()
        try:
            from src.core.data_ingest import DataIngestionManager
            
            # 測試實例化時間（應該很快，因為我們優化了健康檢查）
            manager = DataIngestionManager()
            
            init_time = time.time() - start_time
            print(f"  ✅ 資料管理器初始化: {init_time:.3f}s")
            
            # 測試適配器可用性（不實際獲取資料）
            if hasattr(manager, 'adapters'):
                print(f"  📋 可用適配器: {list(manager.adapters.keys())}")
            
            return init_time
            
        except Exception as e:
            print(f"  ❌ 資料管理器初始化失敗: {e}")
            return -1
    
    def test_web_ui_response_time(self) -> Dict[str, float]:
        """測試Web UI響應時間"""
        print("🌐 測試Web UI響應時間...")
        
        response_times = {}
        
        try:
            # 測試主頁響應時間
            start_time = time.time()
            response = requests.get(self.web_ui_url, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                response_times["main_page"] = response_time
                print(f"  ✅ 主頁響應時間: {response_time:.3f}s")
            else:
                response_times["main_page"] = -1
                print(f"  ❌ 主頁響應失敗: HTTP {response.status_code}")
                
        except Exception as e:
            response_times["main_page"] = -1
            print(f"  ❌ Web UI響應測試失敗: {e}")
        
        return response_times
    
    def test_system_startup_sequence(self) -> Dict[str, float]:
        """測試系統啟動序列"""
        print("⚡ 測試系統啟動序列...")
        
        startup_times = {}
        total_start_time = time.time()
        
        # 1. 模組導入階段
        phase_start = time.time()
        import_times = self.test_module_import_performance()
        startup_times["module_import"] = time.time() - phase_start
        
        # 2. 資料管理器初始化階段
        phase_start = time.time()
        data_manager_time = self.test_data_manager_initialization()
        startup_times["data_manager_init"] = time.time() - phase_start
        
        # 3. Web UI響應階段
        phase_start = time.time()
        web_response_times = self.test_web_ui_response_time()
        startup_times["web_ui_response"] = time.time() - phase_start
        
        # 總啟動時間
        startup_times["total_startup"] = time.time() - total_start_time
        
        return startup_times
    
    def evaluate_performance(self, results: Dict[str, float]) -> Dict[str, bool]:
        """評估性能是否符合目標"""
        print("\n📊 性能評估結果:")
        
        # 性能目標
        targets = {
            "total_startup": 10.0,      # 總啟動時間 < 10秒
            "web_ui_response": 5.0,     # Web UI響應 < 5秒
            "module_import": 3.0,       # 模組導入 < 3秒
            "data_manager_init": 2.0,   # 資料管理器初始化 < 2秒
        }
        
        evaluation = {}
        
        for metric, target in targets.items():
            if metric in results and results[metric] > 0:
                passed = results[metric] < target
                status = "✅ 通過" if passed else "❌ 未達標"
                print(f"  {metric}: {results[metric]:.3f}s (目標: <{target}s) {status}")
                evaluation[metric] = passed
            else:
                print(f"  {metric}: 無資料 ❌")
                evaluation[metric] = False
        
        return evaluation
    
    def generate_performance_report(self, results: Dict[str, float], evaluation: Dict[str, bool]):
        """生成性能報告"""
        print("\n📋 性能測試報告")
        print("=" * 50)
        
        # 總體評估
        passed_count = sum(evaluation.values())
        total_count = len(evaluation)
        overall_pass = passed_count == total_count
        
        print(f"總體評估: {'✅ 通過' if overall_pass else '❌ 需要優化'}")
        print(f"通過率: {passed_count}/{total_count} ({passed_count/total_count*100:.1f}%)")
        
        # 詳細結果
        print("\n詳細結果:")
        for metric, result in results.items():
            if result > 0:
                status = "✅" if evaluation.get(metric, False) else "❌"
                print(f"  {status} {metric}: {result:.3f}s")
            else:
                print(f"  ❌ {metric}: 測試失敗")
        
        # 建議
        print("\n💡 優化建議:")
        if not evaluation.get("total_startup", True):
            print("  - 考慮進一步延遲非關鍵組件的初始化")
        if not evaluation.get("web_ui_response", True):
            print("  - 優化Web UI的載入速度")
        if not evaluation.get("module_import", True):
            print("  - 考慮使用延遲導入或模組快取")
        if not evaluation.get("data_manager_init", True):
            print("  - 進一步優化資料管理器的初始化流程")
        
        if overall_pass:
            print("  🎉 系統性能已達到所有目標！")
    
    def run_full_test(self):
        """執行完整的性能測試"""
        print("🚀 AI交易系統啟動性能測試")
        print("=" * 60)
        
        # 執行啟動序列測試
        startup_results = self.test_system_startup_sequence()
        
        # 評估性能
        evaluation = self.evaluate_performance(startup_results)
        
        # 生成報告
        self.generate_performance_report(startup_results, evaluation)
        
        return startup_results, evaluation


def main():
    """主函數"""
    tester = PerformanceTest()
    results, evaluation = tester.run_full_test()
    
    # 返回結果
    overall_pass = all(evaluation.values())
    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
