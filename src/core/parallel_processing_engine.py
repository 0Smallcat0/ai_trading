#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""並行處理引擎

此模組提供高效的並行資料下載和處理功能，包括：
1. 多執行緒並行下載
2. 多程序並行處理
3. 動態負載均衡
4. 資源使用監控
5. 錯誤恢復機制

主要功能：
- 智能並行度調整
- 任務佇列管理
- 資源池管理
- 失敗重試機制
- 效能監控整合

Example:
    基本使用：
    ```python
    from src.core.parallel_processing_engine import ParallelProcessingEngine
    
    # 創建並行處理引擎
    engine = ParallelProcessingEngine(max_workers=5)
    
    # 提交並行任務
    futures = engine.submit_batch_tasks(download_tasks)
    
    # 等待完成
    results = engine.wait_for_completion(futures)
    ```

Note:
    此模組整合了ThreadPoolExecutor和ProcessPoolExecutor，
    提供靈活的並行處理策略選擇。
"""

import logging
import threading
import multiprocessing
import time
import queue
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future, as_completed
import statistics
import psutil

# 設定日誌
logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """處理模式"""
    THREAD_POOL = "thread_pool"      # 執行緒池
    PROCESS_POOL = "process_pool"    # 程序池
    HYBRID = "hybrid"                # 混合模式
    ADAPTIVE = "adaptive"            # 自適應模式


class TaskPriority(Enum):
    """任務優先級"""
    URGENT = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class TaskStatus(Enum):
    """任務狀態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class ParallelTask:
    """並行任務"""
    task_id: str
    function: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    max_retries: int = 3
    timeout: Optional[int] = None
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    result: Any = None
    error: Optional[Exception] = None
    processing_time: float = 0.0


@dataclass
class WorkerMetrics:
    """工作者指標"""
    worker_id: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_processing_time: float = 0.0
    average_processing_time: float = 0.0
    current_task: Optional[str] = None
    last_activity: datetime = field(default_factory=datetime.now)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0


@dataclass
class ProcessingMetrics:
    """處理指標"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    success_rate: float = 0.0
    average_processing_time: float = 0.0
    throughput: float = 0.0  # 任務/秒
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None


class ParallelProcessingEngine:
    """並行處理引擎
    
    提供高效的並行資料下載和處理功能，支援多種並行模式
    和智能負載均衡。
    
    Attributes:
        max_workers: 最大工作者數量
        processing_mode: 處理模式
        task_queue: 任務佇列
        worker_metrics: 工作者指標
        processing_metrics: 處理指標
        
    Example:
        >>> engine = ParallelProcessingEngine(max_workers=5)
        >>> futures = engine.submit_batch_tasks(tasks)
        >>> results = engine.wait_for_completion(futures)
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        processing_mode: ProcessingMode = ProcessingMode.ADAPTIVE,
        config: Optional[Dict[str, Any]] = None
    ):
        """初始化並行處理引擎
        
        Args:
            max_workers: 最大工作者數量
            processing_mode: 處理模式
            config: 配置參數
        """
        self.config = config or {}
        
        # 自動確定最大工作者數量
        if max_workers is None:
            cpu_count = multiprocessing.cpu_count()
            self.max_workers = min(cpu_count * 2, 10)  # 限制最大值
        else:
            self.max_workers = max_workers
        
        self.processing_mode = processing_mode
        
        # 任務管理
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.active_tasks: Dict[str, ParallelTask] = {}
        self.completed_tasks: Dict[str, ParallelTask] = {}
        self.task_futures: Dict[str, Future] = {}
        
        # 執行器管理
        self.thread_executor: Optional[ThreadPoolExecutor] = None
        self.process_executor: Optional[ProcessPoolExecutor] = None
        
        # 指標和監控
        self.worker_metrics: Dict[str, WorkerMetrics] = {}
        self.processing_metrics = ProcessingMetrics()
        self.performance_history: deque = deque(maxlen=1000)
        
        # 執行緒安全鎖
        self.lock = threading.RLock()
        
        # 系統監控
        self.system_monitor_active = True
        self.load_balancer_active = True
        
        # 初始化執行器
        self._initialize_executors()
        
        # 啟動背景服務
        self._start_background_services()
        
        logger.info("並行處理引擎初始化完成 (最大工作者: %d, 模式: %s)", 
                   self.max_workers, processing_mode.value)
    
    def submit_task(
        self,
        function: Callable,
        *args,
        task_id: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[int] = None,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """提交單個任務
        
        Args:
            function: 要執行的函數
            *args: 函數參數
            task_id: 任務ID
            priority: 任務優先級
            timeout: 超時時間（秒）
            max_retries: 最大重試次數
            **kwargs: 函數關鍵字參數
            
        Returns:
            str: 任務ID
        """
        if task_id is None:
            task_id = f"task_{int(time.time() * 1000)}_{id(function)}"
        
        task = ParallelTask(
            task_id=task_id,
            function=function,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries
        )
        
        with self.lock:
            self.active_tasks[task_id] = task
            self.processing_metrics.total_tasks += 1
            self.processing_metrics.pending_tasks += 1
        
        # 提交到適當的執行器
        future = self._submit_to_executor(task)
        
        with self.lock:
            self.task_futures[task_id] = future
        
        logger.debug("提交任務: %s (優先級: %s)", task_id, priority.name)
        return task_id
    
    def submit_batch_tasks(
        self,
        tasks: List[Dict[str, Any]],
        batch_size: Optional[int] = None
    ) -> List[str]:
        """批量提交任務
        
        Args:
            tasks: 任務列表，每個任務包含function, args, kwargs等
            batch_size: 批次大小
            
        Returns:
            List[str]: 任務ID列表
        """
        if batch_size is None:
            batch_size = min(len(tasks), self.max_workers * 2)
        
        task_ids = []
        
        # 分批處理
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            
            for task_config in batch:
                task_id = self.submit_task(**task_config)
                task_ids.append(task_id)
            
            # 批次間短暫延遲，避免系統過載
            if i + batch_size < len(tasks):
                time.sleep(0.1)
        
        logger.info("批量提交任務完成: %d 個任務", len(task_ids))
        return task_ids
    
    def wait_for_completion(
        self,
        task_ids: Optional[List[str]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """等待任務完成
        
        Args:
            task_ids: 要等待的任務ID列表，None表示等待所有任務
            timeout: 超時時間（秒）
            
        Returns:
            Dict[str, Any]: 任務結果字典
        """
        if task_ids is None:
            task_ids = list(self.active_tasks.keys())
        
        results = {}
        start_time = time.time()
        
        while task_ids:
            completed_ids = []
            
            for task_id in task_ids:
                if task_id in self.task_futures:
                    future = self.task_futures[task_id]
                    
                    try:
                        # 檢查是否完成
                        if future.done():
                            task = self.active_tasks.get(task_id)
                            if task:
                                if future.exception():
                                    task.error = future.exception()
                                    task.status = TaskStatus.FAILED
                                    results[task_id] = {'error': str(task.error)}
                                else:
                                    task.result = future.result()
                                    task.status = TaskStatus.COMPLETED
                                    results[task_id] = {'result': task.result}
                                
                                task.completed_at = datetime.now()
                                self._update_task_metrics(task)
                            
                            completed_ids.append(task_id)
                    
                    except Exception as e:
                        logger.error("檢查任務 %s 狀態時發生錯誤: %s", task_id, e)
                        results[task_id] = {'error': str(e)}
                        completed_ids.append(task_id)
            
            # 移除已完成的任務
            for task_id in completed_ids:
                task_ids.remove(task_id)
            
            # 檢查超時
            if timeout and (time.time() - start_time) > timeout:
                logger.warning("等待任務完成超時，剩餘 %d 個任務", len(task_ids))
                break
            
            # 短暫休眠
            if task_ids:
                time.sleep(0.1)
        
        logger.info("任務完成等待結束，完成 %d 個任務", len(results))
        return results
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任務
        
        Args:
            task_id: 任務ID
            
        Returns:
            bool: 是否成功取消
        """
        try:
            with self.lock:
                if task_id in self.task_futures:
                    future = self.task_futures[task_id]
                    success = future.cancel()
                    
                    if success and task_id in self.active_tasks:
                        task = self.active_tasks[task_id]
                        task.status = TaskStatus.CANCELLED
                        task.completed_at = datetime.now()
                        
                        self.processing_metrics.cancelled_tasks += 1
                        self.processing_metrics.pending_tasks -= 1
                    
                    return success
            
            return False
            
        except Exception as e:
            logger.error("取消任務 %s 失敗: %s", task_id, e)
            return False
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """獲取任務狀態
        
        Args:
            task_id: 任務ID
            
        Returns:
            Optional[TaskStatus]: 任務狀態
        """
        with self.lock:
            task = self.active_tasks.get(task_id)
            return task.status if task else None
    
    def get_processing_metrics(self) -> ProcessingMetrics:
        """獲取處理指標
        
        Returns:
            ProcessingMetrics: 處理指標
        """
        with self.lock:
            # 更新成功率
            total_finished = (self.processing_metrics.completed_tasks + 
                            self.processing_metrics.failed_tasks + 
                            self.processing_metrics.cancelled_tasks)
            
            if total_finished > 0:
                self.processing_metrics.success_rate = (
                    self.processing_metrics.completed_tasks / total_finished
                )
            
            # 更新吞吐量
            elapsed_time = (datetime.now() - self.processing_metrics.start_time).total_seconds()
            if elapsed_time > 0:
                self.processing_metrics.throughput = total_finished / elapsed_time
            
            return self.processing_metrics

    def get_worker_metrics(self) -> Dict[str, WorkerMetrics]:
        """獲取工作者指標

        Returns:
            Dict[str, WorkerMetrics]: 工作者指標字典
        """
        with self.lock:
            return self.worker_metrics.copy()

    def adjust_worker_count(self, new_count: int) -> bool:
        """調整工作者數量

        Args:
            new_count: 新的工作者數量

        Returns:
            bool: 是否調整成功
        """
        try:
            if new_count <= 0 or new_count > 50:  # 合理範圍限制
                logger.warning("工作者數量超出合理範圍: %d", new_count)
                return False

            old_count = self.max_workers
            self.max_workers = new_count

            # 重新初始化執行器
            self._shutdown_executors()
            self._initialize_executors()

            logger.info("調整工作者數量: %d -> %d", old_count, new_count)
            return True

        except Exception as e:
            logger.error("調整工作者數量失敗: %s", e)
            return False

    def shutdown(self, wait: bool = True):
        """關閉並行處理引擎

        Args:
            wait: 是否等待所有任務完成
        """
        logger.info("開始關閉並行處理引擎...")

        # 停止背景服務
        self.system_monitor_active = False
        self.load_balancer_active = False

        # 關閉執行器
        self._shutdown_executors(wait=wait)

        # 更新結束時間
        self.processing_metrics.end_time = datetime.now()

        logger.info("並行處理引擎已關閉")

    # ==================== 私有輔助方法 ====================

    def _initialize_executors(self):
        """初始化執行器"""
        try:
            if self.processing_mode in [ProcessingMode.THREAD_POOL, ProcessingMode.HYBRID, ProcessingMode.ADAPTIVE]:
                self.thread_executor = ThreadPoolExecutor(
                    max_workers=self.max_workers,
                    thread_name_prefix="ParallelEngine"
                )
                logger.debug("初始化執行緒池執行器: %d 工作者", self.max_workers)

            if self.processing_mode in [ProcessingMode.PROCESS_POOL, ProcessingMode.HYBRID]:
                # 程序池通常使用較少的工作者
                process_workers = min(self.max_workers, multiprocessing.cpu_count())
                self.process_executor = ProcessPoolExecutor(
                    max_workers=process_workers
                )
                logger.debug("初始化程序池執行器: %d 工作者", process_workers)

        except Exception as e:
            logger.error("初始化執行器失敗: %s", e)
            raise

    def _shutdown_executors(self, wait: bool = True):
        """關閉執行器"""
        if self.thread_executor:
            self.thread_executor.shutdown(wait=wait)
            self.thread_executor = None
            logger.debug("執行緒池執行器已關閉")

        if self.process_executor:
            self.process_executor.shutdown(wait=wait)
            self.process_executor = None
            logger.debug("程序池執行器已關閉")

    def _submit_to_executor(self, task: ParallelTask) -> Future:
        """提交任務到執行器

        Args:
            task: 並行任務

        Returns:
            Future: 任務Future對象
        """
        # 選擇執行器
        executor = self._select_executor(task)

        if executor is None:
            raise RuntimeError("沒有可用的執行器")

        # 包裝任務函數以添加監控
        wrapped_function = self._wrap_task_function(task)

        # 提交任務
        future = executor.submit(wrapped_function)

        # 更新任務狀態
        task.started_at = datetime.now()
        task.status = TaskStatus.RUNNING

        with self.lock:
            self.processing_metrics.pending_tasks -= 1
            self.processing_metrics.running_tasks += 1

        return future

    def _select_executor(self, task: ParallelTask):
        """選擇執行器

        Args:
            task: 並行任務

        Returns:
            執行器實例
        """
        if self.processing_mode == ProcessingMode.THREAD_POOL:
            return self.thread_executor
        elif self.processing_mode == ProcessingMode.PROCESS_POOL:
            return self.process_executor
        elif self.processing_mode == ProcessingMode.ADAPTIVE:
            # 自適應選擇：I/O密集型用執行緒，CPU密集型用程序
            return self._adaptive_executor_selection(task)
        else:  # HYBRID
            # 混合模式：根據任務特性選擇
            return self._hybrid_executor_selection(task)

    def _adaptive_executor_selection(self, task: ParallelTask):
        """自適應執行器選擇"""
        # 簡化實現：預設使用執行緒池（適合I/O密集型任務）
        return self.thread_executor

    def _hybrid_executor_selection(self, task: ParallelTask):
        """混合執行器選擇"""
        # 簡化實現：根據當前負載選擇
        if self.thread_executor and self.process_executor:
            # 選擇負載較輕的執行器
            return self.thread_executor  # 預設選擇執行緒池
        elif self.thread_executor:
            return self.thread_executor
        else:
            return self.process_executor

    def _wrap_task_function(self, task: ParallelTask) -> Callable:
        """包裝任務函數以添加監控

        Args:
            task: 並行任務

        Returns:
            Callable: 包裝後的函數
        """
        def wrapped_function():
            start_time = time.time()

            try:
                # 執行原始函數
                result = task.function(*task.args, **task.kwargs)

                # 記錄成功
                processing_time = time.time() - start_time
                task.processing_time = processing_time

                return result

            except Exception as e:
                # 記錄錯誤
                processing_time = time.time() - start_time
                task.processing_time = processing_time
                task.error = e

                logger.error("任務 %s 執行失敗: %s", task.task_id, e)
                raise

        return wrapped_function

    def _update_task_metrics(self, task: ParallelTask):
        """更新任務指標

        Args:
            task: 並行任務
        """
        with self.lock:
            self.processing_metrics.running_tasks -= 1

            if task.status == TaskStatus.COMPLETED:
                self.processing_metrics.completed_tasks += 1

                # 更新平均處理時間
                total_time = (self.processing_metrics.average_processing_time *
                            (self.processing_metrics.completed_tasks - 1) +
                            task.processing_time)
                self.processing_metrics.average_processing_time = (
                    total_time / self.processing_metrics.completed_tasks
                )

            elif task.status == TaskStatus.FAILED:
                self.processing_metrics.failed_tasks += 1

                # 檢查是否需要重試
                if task.retry_count < task.max_retries:
                    self._schedule_retry(task)

            # 移動到已完成任務
            if task.task_id in self.active_tasks:
                self.completed_tasks[task.task_id] = self.active_tasks.pop(task.task_id)

    def _schedule_retry(self, task: ParallelTask):
        """排程重試任務

        Args:
            task: 要重試的任務
        """
        task.retry_count += 1
        task.status = TaskStatus.RETRYING

        # 指數退避延遲
        delay = min(2 ** task.retry_count, 60)  # 最大60秒

        def retry_task():
            time.sleep(delay)

            # 重新提交任務
            future = self._submit_to_executor(task)

            with self.lock:
                self.task_futures[task.task_id] = future

        # 在背景執行緒中執行重試
        retry_thread = threading.Thread(target=retry_task, daemon=True)
        retry_thread.start()

        logger.info("排程重試任務 %s (第 %d 次重試，延遲 %d 秒)",
                   task.task_id, task.retry_count, delay)

    def _start_background_services(self):
        """啟動背景服務"""
        # 系統監控執行緒
        monitor_thread = threading.Thread(
            target=self._system_monitor_loop,
            daemon=True,
            name="SystemMonitor"
        )
        monitor_thread.start()

        # 負載均衡執行緒
        balancer_thread = threading.Thread(
            target=self._load_balancer_loop,
            daemon=True,
            name="LoadBalancer"
        )
        balancer_thread.start()

        logger.debug("背景服務已啟動")

    def _system_monitor_loop(self):
        """系統監控迴圈"""
        while self.system_monitor_active:
            try:
                # 收集系統指標
                self._collect_system_metrics()

                # 檢查系統健康度
                self._check_system_health()

                time.sleep(30)  # 每30秒檢查一次

            except Exception as e:
                logger.error("系統監控錯誤: %s", e)
                time.sleep(60)

    def _load_balancer_loop(self):
        """負載均衡迴圈"""
        while self.load_balancer_active:
            try:
                # 執行負載均衡
                self._perform_load_balancing()

                time.sleep(60)  # 每分鐘執行一次

            except Exception as e:
                logger.error("負載均衡錯誤: %s", e)
                time.sleep(120)

    def _collect_system_metrics(self):
        """收集系統指標"""
        try:
            # 收集CPU和記憶體使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent

            # 記錄到效能歷史
            metrics = {
                'timestamp': datetime.now(),
                'cpu_usage': cpu_percent,
                'memory_usage': memory_percent,
                'active_tasks': len(self.active_tasks),
                'completed_tasks': self.processing_metrics.completed_tasks,
                'failed_tasks': self.processing_metrics.failed_tasks
            }

            self.performance_history.append(metrics)

        except Exception as e:
            logger.error("收集系統指標失敗: %s", e)

    def _check_system_health(self):
        """檢查系統健康度"""
        if not self.performance_history:
            return

        latest_metrics = self.performance_history[-1]

        # 檢查CPU使用率
        if latest_metrics['cpu_usage'] > 90:
            logger.warning("CPU使用率過高: %.1f%%", latest_metrics['cpu_usage'])
            self._handle_high_cpu_usage()

        # 檢查記憶體使用率
        if latest_metrics['memory_usage'] > 90:
            logger.warning("記憶體使用率過高: %.1f%%", latest_metrics['memory_usage'])
            self._handle_high_memory_usage()

    def _perform_load_balancing(self):
        """執行負載均衡"""
        # 簡化實現：根據系統負載調整工作者數量
        if len(self.performance_history) < 5:
            return

        recent_metrics = list(self.performance_history)[-5:]
        avg_cpu = statistics.mean([m['cpu_usage'] for m in recent_metrics])
        avg_memory = statistics.mean([m['memory_usage'] for m in recent_metrics])

        # 動態調整工作者數量
        if avg_cpu > 80 and self.max_workers > 2:
            new_count = max(2, self.max_workers - 1)
            self.adjust_worker_count(new_count)
        elif avg_cpu < 50 and self.max_workers < 10:
            new_count = min(10, self.max_workers + 1)
            self.adjust_worker_count(new_count)

    def _handle_high_cpu_usage(self):
        """處理高CPU使用率"""
        # 減少工作者數量
        if self.max_workers > 2:
            new_count = max(2, self.max_workers - 1)
            self.adjust_worker_count(new_count)

    def _handle_high_memory_usage(self):
        """處理高記憶體使用率"""
        # 減少工作者數量並清理快取
        if self.max_workers > 1:
            new_count = max(1, self.max_workers - 1)
            self.adjust_worker_count(new_count)
