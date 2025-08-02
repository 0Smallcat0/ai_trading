#!/usr/bin/env python3
"""
智能跳過功能驗證腳本
快速驗證問題股票跳過和正常股票下載功能
"""

import sys
import time
from datetime import date
from pathlib import Path

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent))

def quick_verification():
    """快速驗證智能跳過功能"""
    print("🔍 快速驗證智能跳過功能...")
    
    try:
        from src.data_sources.real_data_crawler import RealDataCrawler
        
        crawler = RealDataCrawler(db_path='sqlite:///data/enhanced_stock_database.db')
        
        # 測試組合：問題股票 + 正常股票
        test_cases = [
            ("3227.TWO", "問題股票", "應該被跳過"),
            ("3293.TWO", "問題股票", "應該被跳過"),
            ("2330.TW", "正常股票", "應該成功下載"),
        ]
        
        results = []
        total_time = 0
        
        for symbol, stock_type, expectation in test_cases:
            print(f"\n📊 測試 {symbol} ({stock_type})...")
            print(f"   期望: {expectation}")
            
            start_time = time.time()
            
            try:
                # 測試日期範圍下載
                data = crawler.crawl_date_range(symbol, date(2024, 7, 1), date(2024, 7, 31))
                duration = time.time() - start_time
                total_time += duration
                
                if stock_type == "問題股票":
                    if data.empty and duration < 0.1:
                        print(f"   ✅ 正確跳過 ({duration:.3f}秒)")
                        results.append("✅ 通過")
                    else:
                        print(f"   ❌ 跳過失敗 ({duration:.3f}秒)")
                        results.append("❌ 失敗")
                else:  # 正常股票
                    if not data.empty:
                        print(f"   ✅ 成功下載 {len(data)}筆記錄 ({duration:.1f}秒)")
                        results.append("✅ 通過")
                    else:
                        print(f"   ⚠️ 無數據 ({duration:.1f}秒)")
                        results.append("⚠️ 無數據")
                        
            except Exception as e:
                duration = time.time() - start_time
                total_time += duration
                print(f"   ❌ 錯誤: {e} ({duration:.1f}秒)")
                results.append("❌ 錯誤")
        
        # 顯示總結
        print(f"\n📈 驗證結果:")
        print(f"   總耗時: {total_time:.1f}秒")
        
        passed = sum(1 for r in results if r.startswith("✅"))
        total = len(results)
        
        print(f"   通過: {passed}/{total}")
        
        for i, (symbol, stock_type, expectation) in enumerate(test_cases):
            print(f"   {symbol}: {results[i]}")
        
        if passed == total:
            print("\n🎉 所有測試通過！智能跳過功能正常工作")
            return True
        else:
            print(f"\n⚠️ {total-passed} 個測試未通過，可能需要檢查")
            return False
            
    except Exception as e:
        print(f"❌ 驗證失敗: {e}")
        return False

def show_problematic_stocks():
    """顯示當前的問題股票列表"""
    print("\n📋 當前問題股票列表:")
    
    try:
        from src.data_sources.real_data_crawler import RealDataCrawler
        
        problematic_stocks = RealDataCrawler.KNOWN_PROBLEMATIC_STOCKS
        
        for i, stock in enumerate(problematic_stocks, 1):
            print(f"   {i:2d}. {stock}")
        
        print(f"\n📊 總計: {len(problematic_stocks)} 檔問題股票")
        print("💡 這些股票會被自動跳過，節省下載時間")
        
    except Exception as e:
        print(f"❌ 無法獲取問題股票列表: {e}")

def main():
    """主函數"""
    print("=" * 50)
    print("🚀 智能跳過功能驗證")
    print("=" * 50)
    
    # 1. 顯示問題股票列表
    show_problematic_stocks()
    
    # 2. 快速驗證
    success = quick_verification()
    
    # 3. 總結
    print("\n" + "=" * 50)
    print("📋 驗證總結")
    print("=" * 50)
    
    if success:
        print("✅ 智能跳過功能工作正常")
        print("💡 系統已準備好進行大規模數據下載")
        print("\n🔧 使用方式:")
        print("   python -m streamlit run src/ui/web_ui.py --server.address=127.0.0.1 --server.port=8501")
    else:
        print("⚠️ 智能跳過功能可能需要檢查")
        print("💡 建議檢查日誌並重新測試")

if __name__ == "__main__":
    main()
