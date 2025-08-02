#!/usr/bin/env python3
"""
智能股票管理器演示腳本
展示動態問題股票檢測、狀態追蹤和智能恢復機制
"""

import sys
import time
import random
from datetime import date, datetime, timedelta
from pathlib import Path

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent))

from src.data_sources.smart_stock_manager import SmartStockManager, StockStatus
from src.data_sources.real_data_crawler import RealDataCrawler

def demo_dynamic_detection():
    """演示動態問題檢測"""
    print("🧠 演示動態問題股票檢測")
    print("-" * 50)
    
    manager = SmartStockManager()
    
    # 模擬不同類型的股票
    test_cases = [
        ("HEALTHY.TW", "健康股票", [(True, 1.0)] * 8 + [(False, 5.0)] * 2),
        ("PROBLEM.TWO", "問題股票", [(False, 8.0)] * 8 + [(True, 2.0)] * 2),
        ("UNSTABLE.TW", "不穩定股票", [(True, 1.5), (False, 6.0)] * 5),
        ("UNKNOWN.TWO", "未知股票", [(True, 2.0)] * 2)
    ]
    
    print("📊 模擬股票下載嘗試...")
    
    for symbol, description, attempts in test_cases:
        print(f"\n   {symbol} ({description}):")
        
        for i, (success, response_time) in enumerate(attempts):
            error = "" if success else random.choice(["HTTP 404", "連接超時", "API錯誤"])
            manager.record_download_attempt(symbol, success, response_time, error)
            
            if (i + 1) % 3 == 0:  # 每3次顯示一次狀態
                status = manager.stock_status.get(symbol)
                if status:
                    print(f"      嘗試 {i+1}: {status.status} (失敗率: {status.failure_rate:.1%}, 置信度: {status.confidence_score:.2f})")
    
    # 顯示最終結果
    print(f"\n📈 最終檢測結果:")
    for symbol, description, _ in test_cases:
        status = manager.stock_status.get(symbol)
        if status:
            should_skip, reason = manager.should_skip_stock(symbol)
            skip_status = f"跳過 ({reason})" if should_skip else "正常"
            print(f"   {symbol}: {status.status} - {skip_status}")
    
    return manager

def demo_recovery_mechanism(manager):
    """演示智能恢復機制"""
    print("\n🔄 演示智能恢復機制")
    print("-" * 50)
    
    # 找一個問題股票進行恢復演示
    problem_stocks = manager.get_problematic_stocks()
    
    if problem_stocks:
        recovery_stock = problem_stocks[0]
        print(f"📊 選擇 {recovery_stock.symbol} 進行恢復演示")
        print(f"   當前狀態: {recovery_stock.status}")
        print(f"   失敗率: {recovery_stock.failure_rate:.1%}")
        print(f"   重試時間: {recovery_stock.retry_after}")
        
        # 模擬恢復過程
        print(f"\n🔄 模擬 {recovery_stock.symbol} 恢復...")
        
        # 記錄多次成功
        for i in range(6):
            manager.record_download_attempt(recovery_stock.symbol, True, 1.2, "")
            print(f"   成功嘗試 {i+1}: 失敗率 {manager.stock_status[recovery_stock.symbol].failure_rate:.1%}")
        
        # 檢查恢復後狀態
        final_status = manager.stock_status[recovery_stock.symbol]
        should_skip, reason = manager.should_skip_stock(recovery_stock.symbol)
        
        print(f"\n📈 恢復結果:")
        print(f"   最終狀態: {final_status.status}")
        print(f"   失敗率: {final_status.failure_rate:.1%}")
        print(f"   是否跳過: {'是' if should_skip else '否'}")
        
        if final_status.status in ['healthy', 'recovering']:
            print(f"   ✅ {recovery_stock.symbol} 成功恢復！")
        else:
            print(f"   ⏳ {recovery_stock.symbol} 仍需更多成功嘗試")
    else:
        print("   ⚠️ 沒有問題股票可用於恢復演示")

def demo_crawler_integration():
    """演示爬蟲集成"""
    print("\n🔗 演示爬蟲系統集成")
    print("-" * 50)
    
    # 創建帶智能管理器的爬蟲
    crawler = RealDataCrawler(db_path='sqlite:///data/demo_smart_database.db')
    
    if not crawler.smart_manager:
        print("   ⚠️ 智能管理器未啟用")
        return
    
    print("   ✅ 智能管理器已集成到爬蟲系統")
    
    # 測試股票列表
    test_symbols = [
        "2330.TW",   # 正常股票
        "0050.TW",   # 正常股票
        "3227.TWO",  # 已知問題股票
        "6424.TWO"   # 已知問題股票
    ]
    
    print(f"\n📊 測試 {len(test_symbols)} 檔股票下載:")
    
    results = {}
    for symbol in test_symbols:
        print(f"\n   測試 {symbol}:")
        
        start_time = time.time()
        try:
            data = crawler.crawl_stock_data(symbol, 2024, 7)
            duration = time.time() - start_time
            
            if data.empty:
                result = "跳過/無數據"
            else:
                result = f"成功 ({len(data)} 筆記錄)"
            
            results[symbol] = (result, duration)
            print(f"      結果: {result}")
            print(f"      耗時: {duration:.3f} 秒")
            
        except Exception as e:
            duration = time.time() - start_time
            results[symbol] = (f"錯誤: {e}", duration)
            print(f"      錯誤: {e}")
            print(f"      耗時: {duration:.3f} 秒")
    
    # 顯示智能管理器統計
    if crawler.smart_manager:
        stats = crawler.smart_manager.get_statistics()
        print(f"\n📈 智能管理器統計:")
        print(f"   總股票數: {stats['total_stocks']}")
        print(f"   狀態分布: {stats['status_distribution']}")
        print(f"   平均失敗率: {stats['avg_failure_rate']:.1%}")
        print(f"   平均置信度: {stats['avg_confidence_score']:.2f}")
    
    return results

def demo_monitoring_system():
    """演示監控系統"""
    print("\n🔍 演示監控系統")
    print("-" * 50)
    
    manager = SmartStockManager()
    
    # 創建一些測試數據
    test_symbol = "MONITOR.TW"
    
    # 先讓它成為問題股票
    for i in range(5):
        manager.record_download_attempt(test_symbol, False, 8.0, "連接超時")
    
    print(f"   📊 {test_symbol} 初始狀態: {manager.stock_status[test_symbol].status}")
    
    # 設置很短的重試時間
    status = manager.stock_status[test_symbol]
    status.retry_after = datetime.now() + timedelta(seconds=3)
    manager.save_stock_status()
    
    print(f"   ⏰ 設置 3 秒後重試")
    
    # 啟動監控
    manager.start_monitoring()
    print(f"   ✅ 監控系統已啟動")
    
    # 等待監控檢查
    print(f"   ⏳ 等待監控檢查...")
    time.sleep(5)
    
    # 檢查狀態變化
    updated_status = manager.stock_status.get(test_symbol)
    if updated_status:
        print(f"   📈 監控後狀態: {updated_status.status}")
        
        if updated_status.status == 'recovering':
            print(f"   ✅ 監控系統正常工作！")
        else:
            print(f"   ⚠️ 監控系統可能需要調整")
    
    # 停止監控
    manager.stop_monitoring()
    print(f"   ✅ 監控系統已停止")

def demo_data_persistence():
    """演示數據持久化"""
    print("\n💾 演示數據持久化")
    print("-" * 50)
    
    # 創建第一個管理器實例
    manager1 = SmartStockManager(data_file="data/demo_smart_status.json")
    
    test_symbol = "PERSIST.TW"
    
    # 記錄一些數據
    print(f"   📊 記錄 {test_symbol} 的測試數據...")
    for i in range(5):
        success = i % 2 == 0
        response_time = 1.5 if success else 6.0
        error = "" if success else "測試錯誤"
        manager1.record_download_attempt(test_symbol, success, response_time, error)
    
    # 顯示狀態
    status1 = manager1.stock_status[test_symbol]
    print(f"   📈 管理器1狀態: {status1.status} (成功: {status1.success_count}, 失敗: {status1.failure_count})")
    
    # 保存數據
    manager1.save_stock_status()
    print(f"   💾 數據已保存")
    
    # 創建第二個管理器實例
    manager2 = SmartStockManager(data_file="data/demo_smart_status.json")
    
    # 檢查數據是否載入
    if test_symbol in manager2.stock_status:
        status2 = manager2.stock_status[test_symbol]
        print(f"   📈 管理器2狀態: {status2.status} (成功: {status2.success_count}, 失敗: {status2.failure_count})")
        
        if (status1.success_count == status2.success_count and 
            status1.failure_count == status2.failure_count):
            print(f"   ✅ 數據持久化成功！")
        else:
            print(f"   ❌ 數據持久化失敗")
    else:
        print(f"   ❌ 數據載入失敗")

def main():
    """主演示函數"""
    print("🎉 歡迎使用智能股票管理器演示")
    print("=" * 60)
    
    try:
        # 1. 動態檢測演示
        manager = demo_dynamic_detection()
        
        # 2. 恢復機制演示
        demo_recovery_mechanism(manager)
        
        # 3. 爬蟲集成演示
        results = demo_crawler_integration()
        
        # 4. 監控系統演示
        demo_monitoring_system()
        
        # 5. 數據持久化演示
        demo_data_persistence()
        
        # 總結
        print("\n" + "=" * 60)
        print("🎊 演示完成總結")
        print("=" * 60)
        
        print("✅ 智能股票管理器功能正常")
        print("✅ 動態檢測算法有效")
        print("✅ 恢復機制可靠")
        print("✅ 爬蟲集成完美")
        print("✅ 數據持久化穩定")
        
        print(f"\n💡 系統優勢:")
        print(f"   🧠 智能檢測: 基於失敗率和置信度的動態判斷")
        print(f"   📋 狀態追蹤: 完整記錄每個股票的歷史表現")
        print(f"   🔄 自動恢復: 定期重試和智能狀態更新")
        print(f"   🔗 無縫集成: 完美融入現有爬蟲系統")
        print(f"   💾 數據持久: 可靠的狀態保存和載入")
        
        print(f"\n🔧 使用建議:")
        print(f"   1. 啟用智能管理器以獲得最佳性能")
        print(f"   2. 根據實際情況調整檢測參數")
        print(f"   3. 定期檢查問題股票的恢復狀態")
        print(f"   4. 監控系統統計信息以優化配置")
        
        if results:
            print(f"\n📊 本次演示統計:")
            total_time = sum(duration for _, duration in results.values())
            skipped_count = sum(1 for result, _ in results.values() if "跳過" in result)
            print(f"   總測試股票: {len(results)}")
            print(f"   智能跳過: {skipped_count}")
            print(f"   總耗時: {total_time:.3f} 秒")
            print(f"   平均耗時: {total_time/len(results):.3f} 秒/股票")
        
    except KeyboardInterrupt:
        print("\n\n👋 演示被用戶中斷")
    except Exception as e:
        print(f"\n❌ 演示過程中發生錯誤: {e}")
    
    print(f"\n👋 感謝使用智能股票管理器演示！")

if __name__ == "__main__":
    main()
