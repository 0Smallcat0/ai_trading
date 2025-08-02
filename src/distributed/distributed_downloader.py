"""
分散式股票數據下載器
實現多節點並行下載和負載均衡故障轉移
"""

import time
import json
import logging
from datetime import date, datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue
import random
from pathlib import Path
import sys

# 添加項目根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.data_sources.real_data_crawler import RealDataCrawler

logger = logging.getLogger(__name__)

@dataclass
class DownloadTask:
    """下載任務"""
    task_id: str
    symbol: str
    start_date: date
    end_date: date
    priority: int = 1
    retry_count: int = 0
    max_retries: int = 3
    assigned_node: Optional[str] = None
    status: str = "pending"  # pending, assigned, running, completed, failed
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def __lt__(self, other):
        """支持優先級隊列比較"""
        if isinstance(other, DownloadTask):
            return self.priority < other.priority
        return NotImplemented

@dataclass
class WorkerNode:
    """工作節點"""
    node_id: str
    host: str
    port: int
    max_concurrent_tasks: int = 5
    current_tasks: int = 0
    status: str = "active"  # active, busy, inactive, failed
    last_heartbeat: Optional[datetime] = None
    total_completed: int = 0
    total_failed: int = 0
    avg_task_time: float = 0.0
    load_score: float = 0.0

    def __post_init__(self):
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.now()

    def update_load_score(self):
        """更新負載分數 (越低越好)"""
        utilization = self.current_tasks / self.max_concurrent_tasks
        failure_rate = self.total_failed / max(self.total_completed + self.total_failed, 1)
        time_penalty = self.avg_task_time / 10.0  # 假設10秒為基準
        
        self.load_score = utilization * 0.5 + failure_rate * 0.3 + time_penalty * 0.2

class DistributedDownloadManager:
    """分散式下載管理器"""
    
    def __init__(self, coordinator_port: int = 8600):
        self.coordinator_port = coordinator_port
        self.task_queue = queue.PriorityQueue()
        self.completed_tasks = {}
        self.failed_tasks = {}
        self.worker_nodes = {}
        self.task_assignments = {}
        self.running = False
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'active_nodes': 0,
            'start_time': None,
            'end_time': None
        }
        
        # 線程池
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.coordinator_thread = None
        self.heartbeat_thread = None
        
        # 配置
        self.heartbeat_interval = 30  # 秒
        self.node_timeout = 120  # 秒
        self.task_timeout = 300  # 秒
        
        logger.info(f"分散式下載管理器初始化完成，協調器端口: {coordinator_port}")

    def register_node(self, node_id: str, host: str, port: int, max_concurrent: int = 5) -> bool:
        """註冊工作節點"""
        try:
            node = WorkerNode(
                node_id=node_id,
                host=host,
                port=port,
                max_concurrent_tasks=max_concurrent
            )
            
            self.worker_nodes[node_id] = node
            logger.info(f"節點 {node_id} 註冊成功: {host}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"註冊節點 {node_id} 失敗: {e}")
            return False

    def add_download_tasks(self, symbols: List[str], start_date: date, end_date: date) -> List[str]:
        """添加下載任務"""
        task_ids = []
        
        for symbol in symbols:
            task_id = f"{symbol}_{start_date}_{end_date}_{int(time.time())}"
            task = DownloadTask(
                task_id=task_id,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            # 使用優先級隊列，優先級越小越優先
            priority = task.priority
            self.task_queue.put((priority, time.time(), task))
            task_ids.append(task_id)
            
        self.stats['total_tasks'] += len(symbols)
        logger.info(f"添加 {len(symbols)} 個下載任務")
        return task_ids

    def select_best_node(self) -> Optional[WorkerNode]:
        """選擇最佳工作節點 (負載均衡)"""
        available_nodes = [
            node for node in self.worker_nodes.values()
            if node.status == "active" and node.current_tasks < node.max_concurrent_tasks
        ]
        
        if not available_nodes:
            return None
        
        # 更新所有節點的負載分數
        for node in available_nodes:
            node.update_load_score()
        
        # 選擇負載分數最低的節點
        best_node = min(available_nodes, key=lambda n: n.load_score)
        return best_node

    def assign_task_to_node(self, task: DownloadTask, node: WorkerNode) -> bool:
        """將任務分配給節點"""
        try:
            task.assigned_node = node.node_id
            task.status = "assigned"
            task.started_at = datetime.now()
            
            node.current_tasks += 1
            self.task_assignments[task.task_id] = node.node_id
            
            logger.info(f"任務 {task.task_id} 分配給節點 {node.node_id}")
            return True
            
        except Exception as e:
            logger.error(f"分配任務失敗: {e}")
            return False

    def execute_task_on_node(self, task: DownloadTask, node: WorkerNode) -> Dict:
        """在節點上執行任務"""
        try:
            # 模擬遠程調用 - 實際實現中會通過HTTP/gRPC調用遠程節點
            crawler = RealDataCrawler(db_path='sqlite:///data/enhanced_stock_database.db')
            
            start_time = time.time()
            data = crawler.crawl_date_range(task.symbol, task.start_date, task.end_date)
            execution_time = time.time() - start_time
            
            # 更新節點統計
            node.total_completed += 1
            node.avg_task_time = (node.avg_task_time * (node.total_completed - 1) + execution_time) / node.total_completed
            
            result = {
                'task_id': task.task_id,
                'symbol': task.symbol,
                'records': len(data) if not data.empty else 0,
                'execution_time': execution_time,
                'node_id': node.node_id,
                'status': 'success' if not data.empty else 'no_data'
            }
            
            return result
            
        except Exception as e:
            node.total_failed += 1
            logger.error(f"節點 {node.node_id} 執行任務 {task.task_id} 失敗: {e}")
            return {
                'task_id': task.task_id,
                'symbol': task.symbol,
                'status': 'error',
                'error': str(e),
                'node_id': node.node_id
            }

    def handle_task_completion(self, task: DownloadTask, result: Dict):
        """處理任務完成"""
        try:
            task.completed_at = datetime.now()
            task.result = result
            
            if result['status'] in ['success', 'no_data']:
                task.status = "completed"
                self.completed_tasks[task.task_id] = task
                self.stats['completed_tasks'] += 1
                logger.info(f"任務 {task.task_id} 完成: {result.get('records', 0)} 筆記錄")
            else:
                task.status = "failed"
                task.error = result.get('error', 'Unknown error')
                self.failed_tasks[task.task_id] = task
                self.stats['failed_tasks'] += 1
                logger.warning(f"任務 {task.task_id} 失敗: {task.error}")
            
            # 釋放節點資源
            if task.assigned_node and task.assigned_node in self.worker_nodes:
                node = self.worker_nodes[task.assigned_node]
                node.current_tasks = max(0, node.current_tasks - 1)
            
        except Exception as e:
            logger.error(f"處理任務完成時發生錯誤: {e}")

    def handle_node_failure(self, node_id: str):
        """處理節點故障"""
        try:
            if node_id not in self.worker_nodes:
                return
            
            node = self.worker_nodes[node_id]
            node.status = "failed"
            node.current_tasks = 0
            
            # 重新分配該節點的任務
            failed_tasks = []
            for task_id, assigned_node in self.task_assignments.items():
                if assigned_node == node_id:
                    # 找到對應的任務並重新排隊
                    for task_dict in [self.completed_tasks, self.failed_tasks]:
                        if task_id in task_dict:
                            task = task_dict[task_id]
                            if task.status in ["assigned", "running"]:
                                task.status = "pending"
                                task.assigned_node = None
                                task.retry_count += 1
                                
                                if task.retry_count <= task.max_retries:
                                    self.task_queue.put((task.priority, time.time(), task))
                                    failed_tasks.append(task_id)
                                else:
                                    task.status = "failed"
                                    task.error = f"節點 {node_id} 故障，重試次數超限"
                                    self.failed_tasks[task_id] = task
            
            logger.warning(f"節點 {node_id} 故障，重新分配 {len(failed_tasks)} 個任務")
            
        except Exception as e:
            logger.error(f"處理節點故障時發生錯誤: {e}")

    def monitor_nodes(self):
        """監控節點健康狀態"""
        while self.running:
            try:
                current_time = datetime.now()
                
                for node_id, node in self.worker_nodes.items():
                    # 檢查心跳超時
                    if (current_time - node.last_heartbeat).total_seconds() > self.node_timeout:
                        if node.status != "failed":
                            logger.warning(f"節點 {node_id} 心跳超時")
                            self.handle_node_failure(node_id)
                
                # 更新活躍節點數
                self.stats['active_nodes'] = sum(
                    1 for node in self.worker_nodes.values() 
                    if node.status == "active"
                )
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"監控節點時發生錯誤: {e}")
                time.sleep(5)

    def coordinate_downloads(self):
        """協調下載任務"""
        logger.info("開始協調下載任務")
        
        while self.running or not self.task_queue.empty():
            try:
                # 獲取任務
                try:
                    priority, timestamp, task = self.task_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # 選擇最佳節點
                best_node = self.select_best_node()
                if not best_node:
                    # 沒有可用節點，重新排隊
                    self.task_queue.put((priority, timestamp, task))
                    time.sleep(1)
                    continue
                
                # 分配任務
                if self.assign_task_to_node(task, best_node):
                    # 提交任務執行
                    future = self.executor.submit(self.execute_task_on_node, task, best_node)
                    
                    # 異步處理結果
                    def handle_result(fut):
                        try:
                            result = fut.result(timeout=self.task_timeout)
                            self.handle_task_completion(task, result)
                        except Exception as e:
                            logger.error(f"任務執行異常: {e}")
                            task.status = "failed"
                            task.error = str(e)
                            self.failed_tasks[task.task_id] = task
                            self.stats['failed_tasks'] += 1
                    
                    future.add_done_callback(handle_result)
                
            except Exception as e:
                logger.error(f"協調任務時發生錯誤: {e}")
                time.sleep(1)

    def start_distributed_download(self, symbols: List[str], start_date: date, end_date: date) -> Dict:
        """啟動分散式下載"""
        try:
            logger.info(f"啟動分散式下載: {len(symbols)} 檔股票")
            
            # 重置統計
            self.stats['start_time'] = datetime.now()
            self.stats['total_tasks'] = 0
            self.stats['completed_tasks'] = 0
            self.stats['failed_tasks'] = 0
            
            # 添加任務
            task_ids = self.add_download_tasks(symbols, start_date, end_date)
            
            # 啟動協調器
            self.running = True
            self.coordinator_thread = threading.Thread(target=self.coordinate_downloads)
            self.heartbeat_thread = threading.Thread(target=self.monitor_nodes)
            
            self.coordinator_thread.start()
            self.heartbeat_thread.start()
            
            # 等待所有任務完成
            while (self.stats['completed_tasks'] + self.stats['failed_tasks']) < self.stats['total_tasks']:
                time.sleep(1)
            
            # 停止協調器
            self.running = False
            self.stats['end_time'] = datetime.now()
            
            # 等待線程結束
            if self.coordinator_thread.is_alive():
                self.coordinator_thread.join(timeout=5)
            if self.heartbeat_thread.is_alive():
                self.heartbeat_thread.join(timeout=5)
            
            # 計算統計結果
            total_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            success_rate = (self.stats['completed_tasks'] / self.stats['total_tasks'] * 100) if self.stats['total_tasks'] > 0 else 0
            
            result = {
                'total_tasks': self.stats['total_tasks'],
                'completed_tasks': self.stats['completed_tasks'],
                'failed_tasks': self.stats['failed_tasks'],
                'success_rate': success_rate,
                'total_time': total_time,
                'avg_time_per_task': total_time / self.stats['total_tasks'] if self.stats['total_tasks'] > 0 else 0,
                'active_nodes': len([n for n in self.worker_nodes.values() if n.status == "active"]),
                'node_stats': {
                    node_id: {
                        'completed': node.total_completed,
                        'failed': node.total_failed,
                        'avg_time': node.avg_task_time,
                        'load_score': node.load_score
                    }
                    for node_id, node in self.worker_nodes.items()
                }
            }
            
            logger.info(f"分散式下載完成: 成功率 {success_rate:.1f}%, 總耗時 {total_time:.1f}秒")
            return result
            
        except Exception as e:
            logger.error(f"分散式下載失敗: {e}")
            self.running = False
            raise

    def get_status(self) -> Dict:
        """獲取當前狀態"""
        return {
            'running': self.running,
            'stats': self.stats.copy(),
            'queue_size': self.task_queue.qsize(),
            'nodes': {
                node_id: {
                    'status': node.status,
                    'current_tasks': node.current_tasks,
                    'max_tasks': node.max_concurrent_tasks,
                    'total_completed': node.total_completed,
                    'total_failed': node.total_failed,
                    'load_score': node.load_score
                }
                for node_id, node in self.worker_nodes.items()
            }
        }

    def shutdown(self):
        """關閉分散式下載管理器"""
        logger.info("關閉分散式下載管理器")
        self.running = False
        
        if self.executor:
            self.executor.shutdown(wait=True)
        
        if self.coordinator_thread and self.coordinator_thread.is_alive():
            self.coordinator_thread.join(timeout=10)
        
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=10)
