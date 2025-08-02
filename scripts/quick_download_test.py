#!/usr/bin/env python3
"""
快速下載測試腳本
驗證優化後的下載效率
"""

import sys
import time
from datetime import date
from pathlib import Path

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent))

def quick_efficiency_test():
    """快速效率測試"""
    print("🚀 快速下載效率測試...")
    
    try:
        from src.data_sources.real_data_crawler import RealDataCrawler
        
        crawler = RealDataCrawler(db_path='sqlite:///data/enhanced_stock_database.db')
        
        # 測試組合：成功股票 + 問題股票
        test_symbols = [
            "2330.TW",    # 台積電 - 應該成功
            "0050.TW",    # 台灣50 - 應該成功
            "3443.TWO",   # 創意 - 上櫃，可能成功
            "3227.TWO",   # 原相 - 應該被跳過
            "3293.TWO",   # 鈊象 - 應該被跳過
        ]
        
        print(f"📊 測試 {len(test_symbols)} 檔股票...")
        
        start_time = time.time()
        results = {
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'total_records': 0
        }
        
        for i, symbol in enumerate(test_symbols):
            print(f"   {i+1}/{len(test_symbols)} - {symbol}", end=" ")
            
            symbol_start = time.time()
            try:
                data = crawler.crawl_stock_data(symbol, 2024, 7)
                duration = time.time() - symbol_start
                
                if not data.empty:
                    results['successful'] += 1
                    results['total_records'] += len(data)
                    print(f"✅ {len(data)}筆 ({duration:.1f}s)")
                else:
                    if duration < 0.1:  # 快速跳過
                        results['skipped'] += 1
                        print(f"⏭️ 跳過 ({duration:.3f}s)")
                    else:
                        results['failed'] += 1
                        print(f"⚠️ 無數據 ({duration:.1f}s)")
                        
            except Exception as e:
                duration = time.time() - symbol_start
                results['failed'] += 1
                print(f"❌ 錯誤 ({duration:.1f}s)")
        
        total_time = time.time() - start_time
        
        # 顯示結果
        print(f"\n📈 測試結果:")
        print(f"   總耗時: {total_time:.1f}秒")
        print(f"   成功: {results['successful']}/{len(test_symbols)}")
        print(f"   跳過: {results['skipped']}/{len(test_symbols)} (智能跳過)")
        print(f"   失敗: {results['failed']}/{len(test_symbols)}")
        print(f"   總記錄: {results['total_records']}")
        print(f"   平均: {total_time/len(test_symbols):.1f}秒/股票")
        
        # 效率評估
        if results['skipped'] >= 2:
            print("✅ 智能跳過機制工作正常")
        if results['successful'] >= 2:
            print("✅ 數據下載功能正常")
        if total_time < 15:
            print("✅ 下載效率良好")
        
        return results
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return None

def main():
    """主函數"""
    print("=" * 50)
    print("📊 下載效率優化驗證")
    print("=" * 50)
    
    results = quick_efficiency_test()
    
    if results:
        print(f"\n💡 結論:")
        if results['skipped'] > 0 and results['successful'] > 0:
            print("   🎉 優化成功！系統運行良好")
            print("   ✅ 可以開始大規模數據下載")
        else:
            print("   ⚠️ 可能需要進一步檢查")
    
    print(f"\n🔧 使用方式:")
    print("   python -m streamlit run src/ui/web_ui.py --server.address=127.0.0.1 --server.port=8501")

if __name__ == "__main__":
    main()
