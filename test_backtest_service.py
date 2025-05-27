#!/usr/bin/env python3
"""
測試回測服務的基本功能
"""

import sys
import os
from datetime import datetime

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_import():
    """測試基本導入功能"""
    try:
        from src.core.backtest_service import BacktestService, BacktestConfig
        print("✅ 成功導入 BacktestService 和 BacktestConfig")
        return True
    except Exception as e:
        print(f"❌ 導入失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_initialization():
    """測試服務初始化"""
    try:
        from src.core.backtest_service import BacktestService
        service = BacktestService()
        print("✅ 成功初始化 BacktestService")
        return service
    except Exception as e:
        print(f"❌ 初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_basic_methods(service):
    """測試基本方法"""
    try:
        # 測試獲取策略列表
        strategies = service.get_available_strategies()
        print(f"✅ 獲取策略列表成功，共 {len(strategies)} 個策略")
        
        # 測試獲取股票列表
        stocks = service.get_available_stocks()
        print(f"✅ 獲取股票列表成功，共 {len(stocks)} 個股票")
        
        # 測試配置驗證
        from src.core.backtest_service import BacktestConfig
        config = BacktestConfig(
            strategy_id="ma_cross",
            strategy_name="移動平均線交叉策略",
            symbols=["2330.TW", "2317.TW"],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=100000.0
        )
        
        is_valid, error_msg = service.validate_backtest_config(config)
        if is_valid:
            print("✅ 配置驗證成功")
        else:
            print(f"❌ 配置驗證失敗: {error_msg}")
        
        return True
    except Exception as e:
        print(f"❌ 方法測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_router():
    """測試 API 路由導入"""
    try:
        from src.api.routers.backtest import router
        print("✅ 成功導入 API 路由")
        return True
    except Exception as e:
        print(f"❌ API 路由導入失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主測試函數"""
    print("🔍 開始測試回測系統基本功能...")
    print("=" * 50)
    
    # 測試1: 基本導入
    if not test_basic_import():
        print("❌ 基本導入測試失敗，停止測試")
        return False
    
    # 測試2: 服務初始化
    service = test_service_initialization()
    if service is None:
        print("❌ 服務初始化測試失敗，停止測試")
        return False
    
    # 測試3: 基本方法
    if not test_basic_methods(service):
        print("❌ 基本方法測試失敗")
        return False
    
    # 測試4: API 路由
    if not test_api_router():
        print("❌ API 路由測試失敗")
        return False
    
    print("=" * 50)
    print("🎯 所有測試通過！回測系統基本功能正常")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
