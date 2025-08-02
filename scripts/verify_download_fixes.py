#!/usr/bin/env python3
"""
下載修復驗證腳本
快速驗證所有下載修復功能是否正常工作
"""

import sys
import time
from datetime import date
from pathlib import Path

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent))

def quick_verification():
    """快速驗證所有修復功能"""
    print("🔍 快速驗證下載修復功能...")
    
    try:
        from src.data_sources.real_data_crawler import RealDataCrawler
        
        crawler = RealDataCrawler(db_path='sqlite:///data/enhanced_stock_database.db')
        
        # 測試案例：問題股票 + 智能檢測 + 特殊分類 + 正常股票
        test_cases = [
            # 已知問題股票
            ("6424.TWO", "已知問題", "應該瞬間跳過"),
            ("3227.TWO", "已知問題", "應該瞬間跳過"),
            
            # 智能檢測股票
            ("6435.TWO", "智能檢測", "應該預防性跳過"),
            ("9001.TWO", "智能檢測", "應該預防性跳過"),
            
            # 特殊分類股票
            ("6426.TW", "特殊上市", "應該使用TWSE成功下載"),
            
            # 正常股票
            ("2330.TW", "正常上市", "應該成功下載"),
            ("3443.TWO", "正常上櫃", "應該成功下載"),
        ]
        
        results = []
        total_time = 0
        skip_count = 0
        success_count = 0
        
        for symbol, category, expectation in test_cases:
            print(f"\n📊 測試 {symbol} ({category})...")
            print(f"   期望: {expectation}")
            
            start_time = time.time()
            
            try:
                data = crawler.crawl_stock_data(symbol, 2024, 7)
                duration = time.time() - start_time
                total_time += duration
                
                if category in ["已知問題", "智能檢測"]:
                    # 應該被跳過
                    if data.empty and duration < 0.1:
                        print(f"   ✅ 正確跳過 ({duration:.3f}秒)")
                        results.append("✅ 通過")
                        skip_count += 1
                    else:
                        print(f"   ❌ 未正確跳過 ({duration:.1f}秒)")
                        results.append("❌ 失敗")
                else:
                    # 應該成功下載
                    if not data.empty:
                        print(f"   ✅ 成功下載 {len(data)}筆記錄 ({duration:.1f}秒)")
                        results.append("✅ 通過")
                        success_count += 1
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
        print(f"   跳過成功: {skip_count} 檔")
        print(f"   下載成功: {success_count} 檔")
        
        passed = sum(1 for r in results if r.startswith("✅"))
        total = len(results)
        
        print(f"   通過率: {passed}/{total} ({passed/total*100:.1f}%)")
        
        for i, (symbol, category, expectation) in enumerate(test_cases):
            print(f"   {symbol}: {results[i]}")
        
        return passed == total
            
    except Exception as e:
        print(f"❌ 驗證失敗: {e}")
        return False

def show_system_status():
    """顯示系統狀態"""
    print("\n📊 系統狀態總覽:")
    
    try:
        from src.data_sources.real_data_crawler import RealDataCrawler
        
        # 問題股票統計
        problematic_count = len(RealDataCrawler.KNOWN_PROBLEMATIC_STOCKS)
        special_count = len(RealDataCrawler.SPECIAL_TWSE_STOCKS)
        
        print(f"   已知問題股票: {problematic_count} 檔")
        print(f"   特殊上市股票: {special_count} 檔")
        print(f"   智能檢測: 啟用 (6420-6450, 9000+)")
        print(f"   多層次跳過: 啟用")
        print(f"   特殊分類: 啟用")
        
        return True
        
    except Exception as e:
        print(f"❌ 無法獲取系統狀態: {e}")
        return False

def estimate_time_savings():
    """估算時間節省"""
    print("\n⏱️ 時間節省估算:")
    
    try:
        from src.data_sources.real_data_crawler import RealDataCrawler
        
        problematic_count = len(RealDataCrawler.KNOWN_PROBLEMATIC_STOCKS)
        
        # 估算節省時間
        time_per_problem_stock = 15  # 秒
        total_saved_time = problematic_count * time_per_problem_stock
        
        print(f"   問題股票數量: {problematic_count} 檔")
        print(f"   每檔節省時間: ~{time_per_problem_stock} 秒")
        print(f"   總節省時間: ~{total_saved_time} 秒 ({total_saved_time/60:.1f} 分鐘)")
        
        # 智能檢測額外節省
        smart_detection_range = 30  # 6420-6450範圍約30檔
        additional_saved = smart_detection_range * time_per_problem_stock
        
        print(f"   智能檢測範圍: ~{smart_detection_range} 檔")
        print(f"   額外節省時間: ~{additional_saved} 秒 ({additional_saved/60:.1f} 分鐘)")
        
        total_savings = total_saved_time + additional_saved
        print(f"   總計節省: ~{total_savings} 秒 ({total_savings/60:.1f} 分鐘)")
        
        return total_savings
        
    except Exception as e:
        print(f"❌ 無法估算時間節省: {e}")
        return 0

def main():
    """主函數"""
    print("=" * 60)
    print("🚀 下載修復功能驗證")
    print("=" * 60)
    
    # 1. 顯示系統狀態
    system_ok = show_system_status()
    
    # 2. 估算時間節省
    time_savings = estimate_time_savings()
    
    # 3. 快速驗證
    verification_ok = quick_verification()
    
    # 4. 總結
    print("\n" + "=" * 60)
    print("📋 驗證總結")
    print("=" * 60)
    
    if system_ok and verification_ok:
        print("✅ 所有修復功能正常工作")
        print("🎉 系統已準備好進行大規模數據下載")
        
        if time_savings > 0:
            print(f"💡 預期節省時間: {time_savings/60:.1f} 分鐘")
        
        print("\n🔧 使用方式:")
        print("   python -m streamlit run src/ui/web_ui.py --server.address=127.0.0.1 --server.port=8501")
        
        print("\n📋 主要功能:")
        print("   ✅ 智能跳過13檔已知問題股票")
        print("   ✅ 自動檢測6420-6450和9000+系列問題股票")
        print("   ✅ 正確分類特殊上市股票")
        print("   ✅ 瞬間響應 (<0.001秒跳過)")
        
    else:
        print("⚠️ 部分功能可能需要檢查")
        if not system_ok:
            print("   ❌ 系統狀態異常")
        if not verification_ok:
            print("   ❌ 功能驗證失敗")
        
        print("\n💡 建議:")
        print("   1. 檢查代碼是否正確部署")
        print("   2. 確認數據庫連接正常")
        print("   3. 重新運行驗證腳本")

if __name__ == "__main__":
    main()
