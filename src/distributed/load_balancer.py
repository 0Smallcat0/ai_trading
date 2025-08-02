"""
負載均衡器和故障轉移組件
實現智能負載分配和自動故障恢復
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class LoadBalanceStrategy(Enum):
    """負載均衡策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_RESPONSE_TIME = "least_response_time"
    ADAPTIVE = "adaptive"

class HealthCheckStatus(Enum):
    """健康檢查狀態"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class NodeMetrics:
    """節點指標"""
    node_id: str
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_connections: int = 0
    response_times: List[float] = None
    error_rate: float = 0.0
    throughput: float = 0.0
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
        if self.last_updated is None:
            self.last_updated = datetime.now()
    
    @property
    def avg_response_time(self) -> float:
        """平均響應時間"""
        return statistics.mean(self.response_times) if self.response_times else 0.0
    
    @property
    def health_score(self) -> float:
        """健康分數 (0-100, 越高越好)"""
        # 基於多個指標計算健康分數
        cpu_score = max(0, 100 - self.cpu_usage)
        memory_score = max(0, 100 - self.memory_usage)
        error_score = max(0, 100 - self.error_rate * 100)
        response_score = max(0, 100 - min(self.avg_response_time * 10, 100))
        
        return (cpu_score * 0.3 + memory_score * 0.2 + 
                error_score * 0.3 + response_score * 0.2)

class LoadBalancer:
    """智能負載均衡器"""
    
    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.ADAPTIVE):
        self.strategy = strategy
        self.nodes = {}  # node_id -> WorkerNode
        self.node_metrics = {}  # node_id -> NodeMetrics
        self.node_weights = {}  # node_id -> weight
        self.round_robin_index = 0
        self.health_check_interval = 30  # 秒
        self.metrics_history_size = 100
        self.failover_threshold = 3  # 連續失敗次數閾值
        self.recovery_check_interval = 60  # 恢復檢查間隔
        
        # 故障轉移狀態
        self.failed_nodes = set()
        self.recovering_nodes = set()
        self.node_failure_counts = {}
        
        # 監控線程
        self.monitoring = False
        self.monitor_thread = None
        
        logger.info(f"負載均衡器初始化完成，策略: {strategy.value}")
    
    def add_node(self, node, weight: float = 1.0):
        """添加節點"""
        self.nodes[node.node_id] = node
        self.node_weights[node.node_id] = weight
        self.node_metrics[node.node_id] = NodeMetrics(node_id=node.node_id)
        self.node_failure_counts[node.node_id] = 0
        
        logger.info(f"添加節點 {node.node_id}，權重: {weight}")
    
    def remove_node(self, node_id: str):
        """移除節點"""
        if node_id in self.nodes:
            del self.nodes[node_id]
            del self.node_weights[node_id]
            del self.node_metrics[node_id]
            del self.node_failure_counts[node_id]
            self.failed_nodes.discard(node_id)
            self.recovering_nodes.discard(node_id)
            
            logger.info(f"移除節點 {node_id}")
    
    def update_node_metrics(self, node_id: str, metrics: Dict):
        """更新節點指標"""
        if node_id not in self.node_metrics:
            return
        
        node_metrics = self.node_metrics[node_id]
        
        # 更新基本指標
        node_metrics.cpu_usage = metrics.get('cpu_usage', 0.0)
        node_metrics.memory_usage = metrics.get('memory_usage', 0.0)
        node_metrics.active_connections = metrics.get('active_connections', 0)
        node_metrics.error_rate = metrics.get('error_rate', 0.0)
        node_metrics.throughput = metrics.get('throughput', 0.0)
        node_metrics.last_updated = datetime.now()
        
        # 更新響應時間歷史
        if 'response_time' in metrics:
            node_metrics.response_times.append(metrics['response_time'])
            if len(node_metrics.response_times) > self.metrics_history_size:
                node_metrics.response_times.pop(0)
    
    def get_healthy_nodes(self) -> List:
        """獲取健康節點列表"""
        healthy_nodes = []
        
        for node_id, node in self.nodes.items():
            if (node_id not in self.failed_nodes and 
                node.status == "active" and
                node.current_tasks < node.max_concurrent_tasks):
                healthy_nodes.append(node)
        
        return healthy_nodes
    
    def select_node_round_robin(self, healthy_nodes: List) -> Optional:
        """輪詢選擇節點"""
        if not healthy_nodes:
            return None
        
        node = healthy_nodes[self.round_robin_index % len(healthy_nodes)]
        self.round_robin_index += 1
        return node
    
    def select_node_least_connections(self, healthy_nodes: List) -> Optional:
        """最少連接選擇節點"""
        if not healthy_nodes:
            return None
        
        return min(healthy_nodes, key=lambda n: n.current_tasks)
    
    def select_node_weighted_round_robin(self, healthy_nodes: List) -> Optional:
        """加權輪詢選擇節點"""
        if not healthy_nodes:
            return None
        
        # 根據權重選擇節點
        weighted_nodes = []
        for node in healthy_nodes:
            weight = self.node_weights.get(node.node_id, 1.0)
            weighted_nodes.extend([node] * int(weight * 10))  # 權重放大10倍
        
        if not weighted_nodes:
            return healthy_nodes[0]
        
        return weighted_nodes[self.round_robin_index % len(weighted_nodes)]
    
    def select_node_least_response_time(self, healthy_nodes: List) -> Optional:
        """最短響應時間選擇節點"""
        if not healthy_nodes:
            return None
        
        def get_response_time(node):
            metrics = self.node_metrics.get(node.node_id)
            return metrics.avg_response_time if metrics else float('inf')
        
        return min(healthy_nodes, key=get_response_time)
    
    def select_node_adaptive(self, healthy_nodes: List) -> Optional:
        """自適應選擇節點"""
        if not healthy_nodes:
            return None
        
        # 綜合考慮多個因素
        def calculate_score(node):
            metrics = self.node_metrics.get(node.node_id)
            if not metrics:
                return 0.0
            
            # 負載分數 (越低越好)
            load_factor = node.current_tasks / node.max_concurrent_tasks
            response_factor = min(metrics.avg_response_time / 5.0, 1.0)  # 5秒為基準
            error_factor = metrics.error_rate
            health_factor = (100 - metrics.health_score) / 100
            
            # 綜合分數 (越低越好)
            score = (load_factor * 0.4 + response_factor * 0.3 + 
                    error_factor * 0.2 + health_factor * 0.1)
            
            return score
        
        return min(healthy_nodes, key=calculate_score)
    
    def select_best_node(self) -> Optional:
        """選擇最佳節點"""
        healthy_nodes = self.get_healthy_nodes()
        
        if not healthy_nodes:
            logger.warning("沒有可用的健康節點")
            return None
        
        # 根據策略選擇節點
        if self.strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self.select_node_round_robin(healthy_nodes)
        elif self.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return self.select_node_least_connections(healthy_nodes)
        elif self.strategy == LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN:
            return self.select_node_weighted_round_robin(healthy_nodes)
        elif self.strategy == LoadBalanceStrategy.LEAST_RESPONSE_TIME:
            return self.select_node_least_response_time(healthy_nodes)
        elif self.strategy == LoadBalanceStrategy.ADAPTIVE:
            return self.select_node_adaptive(healthy_nodes)
        else:
            return healthy_nodes[0]  # 默認選擇第一個
    
    def handle_node_failure(self, node_id: str, error: str = ""):
        """處理節點故障"""
        if node_id not in self.nodes:
            return
        
        # 增加失敗計數
        self.node_failure_counts[node_id] += 1
        
        logger.warning(f"節點 {node_id} 發生故障: {error}, 失敗次數: {self.node_failure_counts[node_id]}")
        
        # 檢查是否達到故障轉移閾值
        if self.node_failure_counts[node_id] >= self.failover_threshold:
            self.failed_nodes.add(node_id)
            self.nodes[node_id].status = "failed"
            
            logger.error(f"節點 {node_id} 被標記為故障，啟動故障轉移")
            
            # 觸發故障轉移事件
            self._trigger_failover(node_id)
    
    def handle_node_success(self, node_id: str, response_time: float = 0.0):
        """處理節點成功響應"""
        if node_id not in self.nodes:
            return
        
        # 重置失敗計數
        self.node_failure_counts[node_id] = 0
        
        # 更新響應時間
        if response_time > 0:
            self.update_node_metrics(node_id, {'response_time': response_time})
        
        # 如果節點正在恢復中，檢查是否可以標記為健康
        if node_id in self.recovering_nodes:
            self._check_node_recovery(node_id)
    
    def _trigger_failover(self, failed_node_id: str):
        """觸發故障轉移"""
        try:
            # 記錄故障轉移事件
            failover_event = {
                'timestamp': datetime.now().isoformat(),
                'failed_node': failed_node_id,
                'remaining_nodes': [n for n in self.nodes.keys() if n not in self.failed_nodes],
                'action': 'failover_triggered'
            }
            
            # 保存故障轉移日誌
            self._save_failover_log(failover_event)
            
            # 重新分配負載
            self._redistribute_load(failed_node_id)
            
            # 啟動恢復檢查
            self.recovering_nodes.add(failed_node_id)
            
        except Exception as e:
            logger.error(f"故障轉移處理失敗: {e}")
    
    def _redistribute_load(self, failed_node_id: str):
        """重新分配負載"""
        try:
            failed_node = self.nodes[failed_node_id]
            healthy_nodes = self.get_healthy_nodes()
            
            if not healthy_nodes:
                logger.critical("沒有健康節點可用於負載重分配")
                return
            
            # 計算需要重分配的任務數
            tasks_to_redistribute = failed_node.current_tasks
            
            if tasks_to_redistribute > 0:
                # 平均分配到健康節點
                tasks_per_node = tasks_to_redistribute // len(healthy_nodes)
                remaining_tasks = tasks_to_redistribute % len(healthy_nodes)
                
                for i, node in enumerate(healthy_nodes):
                    additional_tasks = tasks_per_node + (1 if i < remaining_tasks else 0)
                    # 這裡應該實際重新分配任務，當前只是模擬
                    logger.info(f"重分配 {additional_tasks} 個任務到節點 {node.node_id}")
            
            # 重置故障節點的任務計數
            failed_node.current_tasks = 0
            
        except Exception as e:
            logger.error(f"負載重分配失敗: {e}")
    
    def _check_node_recovery(self, node_id: str):
        """檢查節點恢復狀態"""
        try:
            if node_id not in self.recovering_nodes:
                return
            
            metrics = self.node_metrics.get(node_id)
            if not metrics:
                return
            
            # 檢查恢復條件
            recovery_conditions = [
                metrics.health_score > 80,  # 健康分數大於80
                metrics.error_rate < 0.05,  # 錯誤率小於5%
                metrics.avg_response_time < 10.0,  # 平均響應時間小於10秒
                self.node_failure_counts[node_id] == 0  # 沒有新的失敗
            ]
            
            if all(recovery_conditions):
                # 節點恢復
                self.failed_nodes.discard(node_id)
                self.recovering_nodes.discard(node_id)
                self.nodes[node_id].status = "active"
                
                logger.info(f"節點 {node_id} 已恢復正常")
                
                # 記錄恢復事件
                recovery_event = {
                    'timestamp': datetime.now().isoformat(),
                    'recovered_node': node_id,
                    'health_score': metrics.health_score,
                    'action': 'node_recovered'
                }
                self._save_failover_log(recovery_event)
        
        except Exception as e:
            logger.error(f"檢查節點恢復時發生錯誤: {e}")
    
    def _save_failover_log(self, event: Dict):
        """保存故障轉移日誌"""
        try:
            log_file = Path("data/failover_log.json")
            log_file.parent.mkdir(exist_ok=True)
            
            # 讀取現有日誌
            logs = []
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            # 添加新事件
            logs.append(event)
            
            # 保持最近1000條記錄
            if len(logs) > 1000:
                logs = logs[-1000:]
            
            # 保存日誌
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            logger.error(f"保存故障轉移日誌失敗: {e}")
    
    def start_monitoring(self):
        """啟動監控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("負載均衡器監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        logger.info("負載均衡器監控已停止")
    
    def _monitor_loop(self):
        """監控循環"""
        while self.monitoring:
            try:
                # 檢查節點健康狀態
                for node_id in list(self.recovering_nodes):
                    self._check_node_recovery(node_id)
                
                # 更新節點指標
                for node_id, node in self.nodes.items():
                    if node_id not in self.failed_nodes:
                        # 模擬指標更新 - 實際實現中會從節點獲取真實指標
                        self._simulate_metrics_update(node_id)
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"監控循環發生錯誤: {e}")
                time.sleep(5)
    
    def _simulate_metrics_update(self, node_id: str):
        """模擬指標更新"""
        # 這是模擬實現，實際中會從節點獲取真實指標
        import random
        
        metrics = {
            'cpu_usage': random.uniform(10, 80),
            'memory_usage': random.uniform(20, 70),
            'active_connections': random.randint(0, 50),
            'error_rate': random.uniform(0, 0.1),
            'throughput': random.uniform(10, 100),
            'response_time': random.uniform(0.5, 5.0)
        }
        
        self.update_node_metrics(node_id, metrics)
    
    def get_load_balancer_stats(self) -> Dict:
        """獲取負載均衡器統計信息"""
        healthy_nodes = len(self.get_healthy_nodes())
        total_nodes = len(self.nodes)
        
        return {
            'strategy': self.strategy.value,
            'total_nodes': total_nodes,
            'healthy_nodes': healthy_nodes,
            'failed_nodes': len(self.failed_nodes),
            'recovering_nodes': len(self.recovering_nodes),
            'node_details': {
                node_id: {
                    'status': node.status,
                    'current_tasks': node.current_tasks,
                    'max_tasks': node.max_concurrent_tasks,
                    'health_score': self.node_metrics[node_id].health_score,
                    'avg_response_time': self.node_metrics[node_id].avg_response_time,
                    'failure_count': self.node_failure_counts[node_id]
                }
                for node_id, node in self.nodes.items()
            }
        }
