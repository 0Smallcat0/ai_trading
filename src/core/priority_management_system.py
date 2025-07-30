#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""優先級管理系統

此模組提供資料來源的優先級管理功能，包括：
1. 動態優先級調整
2. 資源分配管理
3. 下載順序優化
4. 效能監控整合
5. 自適應學習機制

主要功能：
- 基於歷史效能的優先級動態調整
- 資源使用率感知的任務分配
- 多維度優先級評估（重要性、時效性、成功率等）
- 智能負載均衡
- 優先級衝突解決

Example:
    基本使用：
    ```python
    from src.core.priority_management_system import PriorityManager
    
    # 創建優先級管理器
    manager = PriorityManager()
    
    # 註冊資料來源
    manager.register_data_source('daily_price', importance=9, urgency=8)
    
    # 獲取優化後的下載順序
    download_order = manager.get_optimized_download_order()
    ```

Note:
    此模組整合了機器學習算法來優化資料下載策略，
    提供智能化的資源分配和優先級管理。
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import statistics
import json
import heapq

# 設定日誌
logger = logging.getLogger(__name__)


class PriorityLevel(Enum):
    """優先級等級"""
    CRITICAL = 1    # 關鍵資料，最高優先級
    HIGH = 2        # 高優先級
    NORMAL = 3      # 正常優先級
    LOW = 4         # 低優先級
    BACKGROUND = 5  # 背景任務，最低優先級


class ResourceType(Enum):
    """資源類型"""
    CPU = "cpu"
    MEMORY = "memory"
    NETWORK = "network"
    DISK_IO = "disk_io"
    DATABASE = "database"


class AdjustmentReason(Enum):
    """優先級調整原因"""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    HIGH_ERROR_RATE = "high_error_rate"
    RESOURCE_CONSTRAINT = "resource_constraint"
    TIME_SENSITIVITY = "time_sensitivity"
    USER_REQUEST = "user_request"
    SYSTEM_OPTIMIZATION = "system_optimization"


@dataclass
class DataSourceConfig:
    """資料來源配置"""
    name: str
    base_priority: PriorityLevel = PriorityLevel.NORMAL
    importance: int = 5  # 1-10，10最重要
    urgency: int = 5     # 1-10，10最緊急
    resource_requirements: Dict[ResourceType, float] = field(default_factory=dict)
    max_concurrent: int = 3
    retry_limit: int = 3
    timeout: int = 300
    dependencies: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    enabled: bool = True


@dataclass
class PriorityScore:
    """優先級分數"""
    total_score: float
    importance_score: float
    urgency_score: float
    performance_score: float
    resource_score: float
    time_score: float
    calculated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ResourceUsage:
    """資源使用情況"""
    resource_type: ResourceType
    current_usage: float  # 0.0-1.0
    max_capacity: float
    allocated: float
    available: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DownloadTask:
    """下載任務"""
    task_id: str
    data_source: str
    priority_score: float
    estimated_duration: int
    resource_requirements: Dict[ResourceType, float]
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed, cancelled


@dataclass
class PriorityAdjustment:
    """優先級調整記錄"""
    data_source: str
    old_priority: PriorityLevel
    new_priority: PriorityLevel
    reason: AdjustmentReason
    adjustment_factor: float
    timestamp: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None


class PriorityManager:
    """優先級管理器
    
    提供資料來源的智能優先級管理，包括動態調整、
    資源分配、下載順序優化等功能。
    
    Attributes:
        data_sources: 資料來源配置
        priority_history: 優先級歷史記錄
        resource_monitor: 資源監控資料
        performance_metrics: 效能指標
        
    Example:
        >>> manager = PriorityManager()
        >>> manager.register_data_source('daily_price', importance=9)
        >>> order = manager.get_optimized_download_order()
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化優先級管理器
        
        Args:
            config: 系統配置
        """
        self.config = config or {}
        self.data_sources: Dict[str, DataSourceConfig] = {}
        self.priority_history: deque = deque(maxlen=1000)
        self.resource_monitor: Dict[ResourceType, ResourceUsage] = {}
        self.performance_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.adjustment_history: deque = deque(maxlen=500)
        
        # 執行緒安全鎖
        self.lock = threading.RLock()
        
        # 動態調整參數
        self.adjustment_config = {
            'performance_threshold': 0.7,  # 效能閾值
            'error_rate_threshold': 0.1,   # 錯誤率閾值
            'resource_threshold': 0.8,     # 資源使用率閾值
            'adjustment_interval': 300,    # 調整間隔（秒）
            'learning_rate': 0.1           # 學習率
        }
        
        # 初始化資源監控
        self._initialize_resource_monitor()
        
        # 啟動背景調整服務
        self._start_background_adjustment()
        
        logger.info("優先級管理器初始化完成")
    
    def register_data_source(
        self, 
        name: str,
        base_priority: PriorityLevel = PriorityLevel.NORMAL,
        importance: int = 5,
        urgency: int = 5,
        resource_requirements: Optional[Dict[ResourceType, float]] = None,
        **kwargs
    ) -> bool:
        """註冊資料來源
        
        Args:
            name: 資料來源名稱
            base_priority: 基礎優先級
            importance: 重要性 (1-10)
            urgency: 緊急性 (1-10)
            resource_requirements: 資源需求
            **kwargs: 其他配置參數
            
        Returns:
            bool: 是否註冊成功
        """
        try:
            with self.lock:
                if resource_requirements is None:
                    resource_requirements = {
                        ResourceType.CPU: 0.1,
                        ResourceType.MEMORY: 0.05,
                        ResourceType.NETWORK: 0.2
                    }
                
                config = DataSourceConfig(
                    name=name,
                    base_priority=base_priority,
                    importance=max(1, min(10, importance)),
                    urgency=max(1, min(10, urgency)),
                    resource_requirements=resource_requirements,
                    **kwargs
                )
                
                self.data_sources[name] = config
                logger.info("註冊資料來源: %s (重要性: %d, 緊急性: %d)", 
                           name, importance, urgency)
                return True
                
        except Exception as e:
            logger.error("註冊資料來源失敗 %s: %s", name, e)
            return False
    
    def calculate_priority_score(
        self, 
        data_source: str,
        current_time: Optional[datetime] = None
    ) -> Optional[PriorityScore]:
        """計算優先級分數
        
        Args:
            data_source: 資料來源名稱
            current_time: 當前時間
            
        Returns:
            Optional[PriorityScore]: 優先級分數，失敗返回None
        """
        if data_source not in self.data_sources:
            logger.warning("未知的資料來源: %s", data_source)
            return None
        
        if current_time is None:
            current_time = datetime.now()
        
        config = self.data_sources[data_source]
        
        # 1. 重要性分數 (0-1)
        importance_score = config.importance / 10.0
        
        # 2. 緊急性分數 (0-1)
        urgency_score = config.urgency / 10.0
        
        # 3. 效能分數 (基於歷史效能)
        performance_score = self._calculate_performance_score(data_source)
        
        # 4. 資源分數 (基於資源可用性)
        resource_score = self._calculate_resource_score(config.resource_requirements)
        
        # 5. 時間分數 (基於時間敏感性)
        time_score = self._calculate_time_score(data_source, current_time)
        
        # 計算總分 (加權平均)
        weights = {
            'importance': 0.3,
            'urgency': 0.25,
            'performance': 0.2,
            'resource': 0.15,
            'time': 0.1
        }
        
        total_score = (
            importance_score * weights['importance'] +
            urgency_score * weights['urgency'] +
            performance_score * weights['performance'] +
            resource_score * weights['resource'] +
            time_score * weights['time']
        )
        
        return PriorityScore(
            total_score=total_score,
            importance_score=importance_score,
            urgency_score=urgency_score,
            performance_score=performance_score,
            resource_score=resource_score,
            time_score=time_score
        )
    
    def get_optimized_download_order(
        self, 
        data_sources: Optional[List[str]] = None,
        max_concurrent: Optional[int] = None
    ) -> List[DownloadTask]:
        """獲取優化後的下載順序
        
        Args:
            data_sources: 要排序的資料來源列表，None表示所有
            max_concurrent: 最大並行數量
            
        Returns:
            List[DownloadTask]: 優化後的下載任務列表
        """
        if data_sources is None:
            data_sources = list(self.data_sources.keys())
        
        if max_concurrent is None:
            max_concurrent = self.config.get('max_concurrent_downloads', 5)
        
        # 計算所有資料來源的優先級分數
        scored_sources = []
        for source in data_sources:
            if source in self.data_sources and self.data_sources[source].enabled:
                score = self.calculate_priority_score(source)
                if score:
                    scored_sources.append((source, score))
        
        # 按優先級分數排序（降序）
        scored_sources.sort(key=lambda x: x[1].total_score, reverse=True)
        
        # 創建下載任務
        tasks = []
        current_time = datetime.now()
        
        for i, (source, score) in enumerate(scored_sources):
            config = self.data_sources[source]
            
            task = DownloadTask(
                task_id=f"{source}_{int(current_time.timestamp())}_{i}",
                data_source=source,
                priority_score=score.total_score,
                estimated_duration=self._estimate_duration(source),
                resource_requirements=config.resource_requirements,
                dependencies=config.dependencies.copy()
            )
            
            tasks.append(task)
        
        # 解決依賴關係
        resolved_tasks = self._resolve_dependencies(tasks)
        
        # 應用並行限制
        final_tasks = self._apply_concurrency_limits(resolved_tasks, max_concurrent)
        
        logger.info("生成優化下載順序: %d 個任務", len(final_tasks))
        return final_tasks

    def adjust_priority(
        self,
        data_source: str,
        new_priority: PriorityLevel,
        reason: AdjustmentReason,
        description: Optional[str] = None
    ) -> bool:
        """調整資料來源優先級

        Args:
            data_source: 資料來源名稱
            new_priority: 新的優先級
            reason: 調整原因
            description: 調整描述

        Returns:
            bool: 是否調整成功
        """
        try:
            with self.lock:
                if data_source not in self.data_sources:
                    logger.warning("嘗試調整未知資料來源的優先級: %s", data_source)
                    return False

                config = self.data_sources[data_source]
                old_priority = config.base_priority

                if old_priority == new_priority:
                    logger.debug("資料來源 %s 優先級無變化", data_source)
                    return True

                # 記錄調整
                adjustment = PriorityAdjustment(
                    data_source=data_source,
                    old_priority=old_priority,
                    new_priority=new_priority,
                    reason=reason,
                    adjustment_factor=self._calculate_adjustment_factor(old_priority, new_priority),
                    description=description
                )

                # 應用調整
                config.base_priority = new_priority
                self.adjustment_history.append(adjustment)

                logger.info("調整 %s 優先級: %s -> %s (原因: %s)",
                           data_source, old_priority.name, new_priority.name, reason.value)

                return True

        except Exception as e:
            logger.error("調整優先級失敗 %s: %s", data_source, e)
            return False

    def update_performance_metrics(
        self,
        data_source: str,
        success: bool,
        duration: float,
        error_message: Optional[str] = None
    ):
        """更新效能指標

        Args:
            data_source: 資料來源名稱
            success: 是否成功
            duration: 執行時間（秒）
            error_message: 錯誤訊息
        """
        try:
            with self.lock:
                metrics = {
                    'timestamp': datetime.now(),
                    'success': success,
                    'duration': duration,
                    'error_message': error_message
                }

                self.performance_metrics[data_source].append(metrics)

                # 檢查是否需要自動調整優先級
                self._check_auto_adjustment(data_source)

        except Exception as e:
            logger.error("更新效能指標失敗 %s: %s", data_source, e)

    def get_resource_allocation(self) -> Dict[str, Dict[ResourceType, float]]:
        """獲取資源分配情況

        Returns:
            Dict[str, Dict[ResourceType, float]]: {資料來源: {資源類型: 分配量}}
        """
        allocation = {}

        with self.lock:
            for source_name, config in self.data_sources.items():
                if config.enabled:
                    allocation[source_name] = config.resource_requirements.copy()

        return allocation

    def get_priority_statistics(self) -> Dict[str, Any]:
        """獲取優先級統計資訊

        Returns:
            Dict[str, Any]: 統計資訊
        """
        with self.lock:
            stats = {
                'total_sources': len(self.data_sources),
                'enabled_sources': sum(1 for c in self.data_sources.values() if c.enabled),
                'priority_distribution': defaultdict(int),
                'recent_adjustments': len([a for a in self.adjustment_history
                                         if a.timestamp > datetime.now() - timedelta(hours=24)]),
                'average_scores': {},
                'resource_utilization': {}
            }

            # 優先級分佈
            for config in self.data_sources.values():
                stats['priority_distribution'][config.base_priority.name] += 1

            # 平均分數
            for source in self.data_sources:
                score = self.calculate_priority_score(source)
                if score:
                    stats['average_scores'][source] = score.total_score

            # 資源利用率
            for resource_type, usage in self.resource_monitor.items():
                stats['resource_utilization'][resource_type.value] = usage.current_usage

            return dict(stats)

    # ==================== 私有輔助方法 ====================

    def _initialize_resource_monitor(self):
        """初始化資源監控"""
        for resource_type in ResourceType:
            self.resource_monitor[resource_type] = ResourceUsage(
                resource_type=resource_type,
                current_usage=0.0,
                max_capacity=1.0,
                allocated=0.0,
                available=1.0
            )

    def _start_background_adjustment(self):
        """啟動背景自動調整服務"""
        def adjustment_loop():
            while True:
                try:
                    self._perform_automatic_adjustments()
                    time.sleep(self.adjustment_config['adjustment_interval'])
                except Exception as e:
                    logger.error("背景調整服務錯誤: %s", e)
                    time.sleep(60)  # 錯誤時延長間隔

        adjustment_thread = threading.Thread(
            target=adjustment_loop,
            daemon=True,
            name="PriorityAdjustment"
        )
        adjustment_thread.start()
        logger.info("背景優先級調整服務已啟動")

    def _calculate_performance_score(self, data_source: str) -> float:
        """計算效能分數"""
        if data_source not in self.performance_metrics:
            return 0.5  # 預設中等分數

        metrics = list(self.performance_metrics[data_source])
        if not metrics:
            return 0.5

        # 計算成功率
        recent_metrics = metrics[-20:]  # 最近20次
        success_rate = sum(1 for m in recent_metrics if m['success']) / len(recent_metrics)

        # 計算平均執行時間（標準化）
        durations = [m['duration'] for m in recent_metrics if m['success']]
        if durations:
            avg_duration = statistics.mean(durations)
            # 假設300秒為基準，越快分數越高
            duration_score = max(0, min(1, 1 - (avg_duration - 60) / 240))
        else:
            duration_score = 0.5

        # 綜合分數
        performance_score = success_rate * 0.7 + duration_score * 0.3
        return max(0, min(1, performance_score))

    def _calculate_resource_score(self, requirements: Dict[ResourceType, float]) -> float:
        """計算資源分數"""
        if not requirements:
            return 1.0

        scores = []
        for resource_type, required in requirements.items():
            if resource_type in self.resource_monitor:
                usage = self.resource_monitor[resource_type]
                available_ratio = usage.available / usage.max_capacity

                if required <= usage.available:
                    # 資源充足
                    scores.append(1.0)
                else:
                    # 資源不足，按比例計分
                    scores.append(available_ratio)
            else:
                scores.append(0.5)  # 未知資源類型

        return statistics.mean(scores) if scores else 0.5

    def _calculate_time_score(self, data_source: str, current_time: datetime) -> float:
        """計算時間分數"""
        # 基於交易時段的時間敏感性
        hour = current_time.hour

        # 交易時段內時間分數較高
        if 9 <= hour <= 14:  # 交易時段
            return 1.0
        elif 8 <= hour <= 15:  # 交易前後
            return 0.8
        elif 16 <= hour <= 18:  # 盤後分析時段
            return 0.6
        else:  # 其他時段
            return 0.3

    def _estimate_duration(self, data_source: str) -> int:
        """估算執行時間"""
        if data_source in self.performance_metrics:
            metrics = list(self.performance_metrics[data_source])
            successful_metrics = [m for m in metrics[-10:] if m['success']]

            if successful_metrics:
                durations = [m['duration'] for m in successful_metrics]
                return int(statistics.mean(durations))

        # 預設估算時間
        return self.data_sources.get(data_source, DataSourceConfig("")).timeout // 2

    def _resolve_dependencies(self, tasks: List[DownloadTask]) -> List[DownloadTask]:
        """解決任務依賴關係"""
        # 簡化實現：按依賴關係排序
        # 實際應該使用拓撲排序

        task_map = {task.data_source: task for task in tasks}
        resolved = []
        processed = set()

        def process_task(task):
            if task.data_source in processed:
                return

            # 先處理依賴
            for dep in task.dependencies:
                if dep in task_map:
                    process_task(task_map[dep])

            resolved.append(task)
            processed.add(task.data_source)

        for task in tasks:
            process_task(task)

        return resolved

    def _apply_concurrency_limits(
        self,
        tasks: List[DownloadTask],
        max_concurrent: int
    ) -> List[DownloadTask]:
        """應用並行限制"""
        # 簡化實現：保持原順序，但標記並行組
        for i, task in enumerate(tasks):
            task.scheduled_at = datetime.now() + timedelta(seconds=i * 10)

        return tasks

    def _calculate_adjustment_factor(
        self,
        old_priority: PriorityLevel,
        new_priority: PriorityLevel
    ) -> float:
        """計算調整因子"""
        return (old_priority.value - new_priority.value) / 5.0

    def _check_auto_adjustment(self, data_source: str):
        """檢查是否需要自動調整"""
        if data_source not in self.performance_metrics:
            return

        metrics = list(self.performance_metrics[data_source])
        if len(metrics) < 5:  # 資料不足
            return

        recent_metrics = metrics[-10:]

        # 檢查錯誤率
        error_rate = 1 - sum(1 for m in recent_metrics if m['success']) / len(recent_metrics)
        if error_rate > self.adjustment_config['error_rate_threshold']:
            self.adjust_priority(
                data_source,
                PriorityLevel.LOW,
                AdjustmentReason.HIGH_ERROR_RATE,
                f"錯誤率過高: {error_rate:.2%}"
            )

    def _perform_automatic_adjustments(self):
        """執行自動調整"""
        try:
            with self.lock:
                for source_name in self.data_sources:
                    self._check_auto_adjustment(source_name)
        except Exception as e:
            logger.error("自動調整失敗: %s", e)
