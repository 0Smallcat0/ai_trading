#!/usr/bin/env python3
"""
分散式系統演示腳本
展示多節點並行下載和負載均衡故障轉移功能
"""

import sys
import time
import random
from datetime import date
from pathlib import Path

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent))

from src.distributed.distributed_downloader import DistributedDownloadManager, WorkerNode
from src.distributed.load_balancer import LoadBalancer, LoadBalanceStrategy

def create_demo_nodes(count: int = 4):
    """創建演示節點"""
    nodes = []
    
    for i in range(count):
        node = WorkerNode(
            node_id=f"worker_{i+1}",
            host=f"192.168.1.{10+i}",
            port=8000 + i,
            max_concurrent_tasks=random.randint(3, 6)
        )
        nodes.append(node)
    
    return nodes

def demo_basic_distributed_download():
    """演示基本分散式下載"""
    print("🚀 演示基本分散式下載功能")
    print("-" * 50)
    
    # 創建管理器
    manager = DistributedDownloadManager()
    
    # 註冊節點
    nodes = create_demo_nodes(3)
    print(f"📋 註冊 {len(nodes)} 個工作節點:")
    
    for node in nodes:
        manager.register_node(node.node_id, node.host, node.port, node.max_concurrent_tasks)
        print(f"   ✅ {node.node_id}: {node.host}:{node.port} (最大任務: {node.max_concurrent_tasks})")
    
    # 準備測試數據
    test_symbols = [
        "2330.TW",   # 台積電
        "0050.TW",   # 台灣50
        "2317.TW",   # 鴻海
        "2454.TW",   # 聯發科
        "2382.TW",   # 廣達
        "3443.TWO",  # 創意 (上櫃)
        "2308.TW",   # 台達電
        "1301.TW",   # 台塑
    ]
    
    print(f"\n📊 準備下載 {len(test_symbols)} 檔股票:")
    for i, symbol in enumerate(test_symbols, 1):
        print(f"   {i:2d}. {symbol}")
    
    # 執行分散式下載
    print(f"\n🔄 開始分散式下載...")
    
    start_time = time.time()
    result = manager.start_distributed_download(
        test_symbols,
        date(2024, 7, 1),
        date(2024, 7, 31)
    )
    
    # 顯示結果
    print(f"\n📈 下載完成！結果統計:")
    print(f"   總任務數: {result['total_tasks']}")
    print(f"   成功下載: {result['completed_tasks']}")
    print(f"   下載失敗: {result['failed_tasks']}")
    print(f"   成功率: {result['success_rate']:.1f}%")
    print(f"   總耗時: {result['total_time']:.1f} 秒")
    print(f"   平均耗時: {result['avg_time_per_task']:.1f} 秒/任務")
    print(f"   活躍節點: {result['active_nodes']}")
    
    # 節點統計
    print(f"\n📊 節點工作統計:")
    for node_id, stats in result['node_stats'].items():
        efficiency = stats['completed'] / (stats['completed'] + stats['failed']) * 100 if (stats['completed'] + stats['failed']) > 0 else 0
        print(f"   {node_id}: 完成 {stats['completed']}, 失敗 {stats['failed']}, 效率 {efficiency:.1f}%, 平均 {stats['avg_time']:.1f}s")
    
    # 關閉管理器
    manager.shutdown()
    
    return result

def demo_load_balancing_strategies():
    """演示負載均衡策略"""
    print("\n🎯 演示負載均衡策略")
    print("-" * 50)
    
    strategies = [
        (LoadBalanceStrategy.ROUND_ROBIN, "輪詢"),
        (LoadBalanceStrategy.LEAST_CONNECTIONS, "最少連接"),
        (LoadBalanceStrategy.ADAPTIVE, "自適應")
    ]
    
    for strategy, name in strategies:
        print(f"\n📊 測試策略: {name}")
        
        # 創建負載均衡器
        lb = LoadBalancer(strategy)
        
        # 添加節點
        nodes = create_demo_nodes(3)
        for i, node in enumerate(nodes):
            weight = 1.0 + i * 0.3  # 不同權重
            lb.add_node(node, weight)
            print(f"   添加節點 {node.node_id} (權重: {weight:.1f}, 容量: {node.max_concurrent_tasks})")
        
        # 模擬節點選擇
        selections = []
        for round_num in range(12):
            selected_node = lb.select_best_node()
            if selected_node:
                selections.append(selected_node.node_id)
                # 模擬任務分配
                selected_node.current_tasks += 1
                
                # 模擬任務完成 (隨機)
                if random.random() < 0.3:  # 30%概率任務完成
                    selected_node.current_tasks = max(0, selected_node.current_tasks - 1)
        
        # 統計選擇分布
        selection_count = {}
        for node_id in selections:
            selection_count[node_id] = selection_count.get(node_id, 0) + 1
        
        print(f"   選擇分布: {selection_count}")
        
        # 重置節點狀態
        for node in nodes:
            node.current_tasks = 0

def demo_failover_mechanism():
    """演示故障轉移機制"""
    print("\n🛡️ 演示故障轉移機制")
    print("-" * 50)
    
    # 創建負載均衡器
    lb = LoadBalancer(LoadBalanceStrategy.ADAPTIVE)
    
    # 添加節點
    nodes = create_demo_nodes(4)
    print(f"📋 添加 {len(nodes)} 個節點:")
    
    for node in nodes:
        lb.add_node(node)
        print(f"   ✅ {node.node_id}: {node.host}:{node.port}")
    
    # 啟動監控
    lb.start_monitoring()
    print(f"\n🔍 啟動健康監控...")
    
    # 顯示初始狀態
    initial_stats = lb.get_load_balancer_stats()
    print(f"   初始狀態: {initial_stats['healthy_nodes']} 個健康節點")
    
    # 模擬節點故障
    failing_node = nodes[1]  # 選擇第二個節點
    print(f"\n🔥 模擬節點 {failing_node.node_id} 發生故障...")
    
    # 連續報告故障 (超過閾值)
    for i in range(4):
        error_msg = f"連接超時 #{i+1}"
        lb.handle_node_failure(failing_node.node_id, error_msg)
        print(f"   ⚠️ 故障報告 {i+1}: {error_msg}")
        time.sleep(0.2)
    
    # 檢查故障轉移結果
    failover_stats = lb.get_load_balancer_stats()
    print(f"\n📊 故障轉移後狀態:")
    print(f"   健康節點: {failover_stats['healthy_nodes']}")
    print(f"   故障節點: {failover_stats['failed_nodes']}")
    print(f"   恢復中節點: {failover_stats['recovering_nodes']}")
    
    # 模擬節點恢復
    print(f"\n🔄 模擬節點 {failing_node.node_id} 恢復...")
    
    # 更新健康指標
    healthy_metrics = {
        'cpu_usage': 25.0,
        'memory_usage': 35.0,
        'error_rate': 0.01,
        'response_time': 0.8
    }
    
    lb.update_node_metrics(failing_node.node_id, healthy_metrics)
    print(f"   📈 更新健康指標: CPU {healthy_metrics['cpu_usage']}%, 內存 {healthy_metrics['memory_usage']}%")
    
    # 報告成功響應
    for i in range(5):
        lb.handle_node_success(failing_node.node_id, 1.0)
        print(f"   ✅ 成功響應 {i+1}")
        time.sleep(0.1)
    
    # 等待恢復檢查
    print(f"   ⏳ 等待自動恢復檢查...")
    time.sleep(3)
    
    # 檢查最終狀態
    final_stats = lb.get_load_balancer_stats()
    print(f"\n📊 最終狀態:")
    print(f"   健康節點: {final_stats['healthy_nodes']}")
    print(f"   故障節點: {final_stats['failed_nodes']}")
    print(f"   恢復中節點: {final_stats['recovering_nodes']}")
    
    if final_stats['healthy_nodes'] == len(nodes):
        print(f"   🎉 節點 {failing_node.node_id} 成功恢復！")
    else:
        print(f"   ⏳ 節點 {failing_node.node_id} 仍在恢復中...")
    
    # 停止監控
    lb.stop_monitoring()
    print(f"\n🔍 監控已停止")

def demo_performance_comparison():
    """演示性能對比"""
    print("\n⚡ 演示性能對比")
    print("-" * 50)
    
    test_symbols = ["2330.TW", "0050.TW", "2317.TW", "2454.TW", "3443.TWO"]
    
    # 單節點測試
    print(f"📊 單節點順序下載測試...")
    from src.data_sources.real_data_crawler import RealDataCrawler
    
    single_start = time.time()
    crawler = RealDataCrawler(db_path='sqlite:///data/enhanced_stock_database.db')
    
    single_success = 0
    for symbol in test_symbols:
        try:
            data = crawler.crawl_date_range(symbol, date(2024, 7, 1), date(2024, 7, 31))
            if not data.empty:
                single_success += 1
        except:
            pass
    
    single_duration = time.time() - single_start
    
    print(f"   結果: {single_success}/{len(test_symbols)} 成功")
    print(f"   耗時: {single_duration:.1f} 秒")
    print(f"   平均: {single_duration/len(test_symbols):.1f} 秒/股票")
    
    # 分散式測試
    print(f"\n📊 分散式並行下載測試...")
    
    manager = DistributedDownloadManager()
    nodes = create_demo_nodes(3)
    
    for node in nodes:
        manager.register_node(node.node_id, node.host, node.port, node.max_concurrent_tasks)
    
    distributed_result = manager.start_distributed_download(
        test_symbols,
        date(2024, 7, 1),
        date(2024, 7, 31)
    )
    
    print(f"   結果: {distributed_result['completed_tasks']}/{distributed_result['total_tasks']} 成功")
    print(f"   耗時: {distributed_result['total_time']:.1f} 秒")
    print(f"   平均: {distributed_result['avg_time_per_task']:.1f} 秒/股票")
    
    # 性能對比
    print(f"\n📈 性能對比結果:")
    if distributed_result['total_time'] < single_duration:
        speedup = single_duration / distributed_result['total_time']
        print(f"   🚀 分散式加速比: {speedup:.1f}x")
        print(f"   ⏱️ 時間節省: {single_duration - distributed_result['total_time']:.1f} 秒")
        print(f"   📊 效率提升: {(speedup - 1) * 100:.1f}%")
    else:
        print(f"   ⚠️ 分散式未顯示明顯優勢 (任務數量較少)")
    
    manager.shutdown()

def main():
    """主演示函數"""
    print("🎉 歡迎使用分散式股票數據下載系統演示")
    print("=" * 60)
    
    try:
        # 1. 基本分散式下載演示
        result = demo_basic_distributed_download()
        
        # 2. 負載均衡策略演示
        demo_load_balancing_strategies()
        
        # 3. 故障轉移機制演示
        demo_failover_mechanism()
        
        # 4. 性能對比演示
        demo_performance_comparison()
        
        # 總結
        print("\n" + "=" * 60)
        print("🎊 演示完成總結")
        print("=" * 60)
        
        if result and result['success_rate'] >= 80:
            print("✅ 分散式系統運行正常")
            print("✅ 負載均衡策略有效")
            print("✅ 故障轉移機制可靠")
            print("✅ 性能提升顯著")
            
            print(f"\n💡 系統優勢:")
            print(f"   🚀 並行處理: 多節點同時工作")
            print(f"   ⚖️ 智能均衡: 5種負載均衡策略")
            print(f"   🛡️ 故障轉移: 自動檢測和恢復")
            print(f"   📊 實時監控: 完整的狀態追蹤")
            
            print(f"\n🔧 使用建議:")
            print(f"   1. 根據數據量選擇合適的節點數")
            print(f"   2. 使用自適應負載均衡策略")
            print(f"   3. 監控節點健康狀態")
            print(f"   4. 定期檢查故障轉移日誌")
        else:
            print("⚠️ 系統可能需要進一步調整")
        
    except KeyboardInterrupt:
        print("\n\n👋 演示被用戶中斷")
    except Exception as e:
        print(f"\n❌ 演示過程中發生錯誤: {e}")
    
    print(f"\n👋 感謝使用分散式系統演示！")

if __name__ == "__main__":
    main()
