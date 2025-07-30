#!/usr/bin/env python3
"""
Asynchronous Processor - Phase 2 Performance Optimization

Advanced asynchronous processing system for data-intensive operations.
Converts synchronous operations to async with progress indicators and
non-blocking UI updates.

Features:
- Background task processing for batch operations
- Non-blocking UI updates during long-running operations
- Async data pipelines for real-time processing
- Progress tracking and cancellation support
- Error handling and retry mechanisms
"""

import asyncio
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable, List, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
from enum import Enum
import weakref

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncTask:
    """Asynchronous task definition"""
    task_id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: int = 5
    timeout: float = 300.0
    retry_count: int = 0
    max_retries: int = 3
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress: float = 0.0
    progress_callback: Optional[Callable] = None
    completion_callback: Optional[Callable] = None


class AsyncProcessor:
    """Advanced asynchronous processor for data operations"""
    
    def __init__(self, max_workers: int = 4, max_concurrent_tasks: int = 10):
        self.max_workers = max_workers
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # Task management
        self.tasks: Dict[str, AsyncTask] = {}
        self.task_queue = asyncio.Queue(maxsize=100)
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
        # Thread pool for CPU-intensive operations
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        
        # Processing control
        self.is_running = False
        self.processor_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_cancelled': 0,
            'total_processing_time': 0.0,
            'avg_processing_time': 0.0
        }
        
        # Event loop management
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.loop_thread: Optional[threading.Thread] = None
        
        logger.info(f"Async Processor initialized with {max_workers} workers")
    
    def start(self) -> None:
        """Start the async processor"""
        if self.is_running:
            logger.warning("Async processor already running")
            return
        
        self.is_running = True
        
        # Start event loop in separate thread if needed
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            self.loop_thread = threading.Thread(
                target=self._run_event_loop,
                daemon=True,
                name="AsyncProcessor"
            )
            self.loop_thread.start()
        
        # Start processor task
        if self.loop and self.loop.is_running():
            self.processor_task = self.loop.create_task(self._process_tasks())
        else:
            # Run in current thread
            asyncio.create_task(self._process_tasks())
        
        logger.info("Async processor started")
    
    def stop(self) -> None:
        """Stop the async processor"""
        self.is_running = False
        
        # Cancel running tasks
        for task_id, task in self.running_tasks.items():
            task.cancel()
            logger.debug(f"Cancelled task: {task_id}")
        
        # Cancel processor task
        if self.processor_task:
            self.processor_task.cancel()
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=False)
        
        logger.info("Async processor stopped")
    
    def _run_event_loop(self) -> None:
        """Run event loop in separate thread"""
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        except Exception as e:
            logger.error(f"Event loop error: {e}")
        finally:
            self.loop.close()
    
    async def _process_tasks(self) -> None:
        """Main task processing loop"""
        while self.is_running:
            try:
                # Check if we can process more tasks
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(0.1)
                    continue
                
                # Get next task from queue
                try:
                    task = await asyncio.wait_for(
                        self.task_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Start processing task
                if task.task_id not in self.running_tasks:
                    processing_task = asyncio.create_task(
                        self._execute_task(task)
                    )
                    self.running_tasks[task.task_id] = processing_task
                
            except Exception as e:
                logger.error(f"Error in task processing loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _execute_task(self, task: AsyncTask) -> None:
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.now()
        
        try:
            logger.info(f"Starting task: {task.name} ({task.task_id})")
            
            # Update progress
            if task.progress_callback:
                task.progress_callback(0.0, "Starting...")
            
            # Execute task based on type
            if asyncio.iscoroutinefunction(task.func):
                # Async function
                result = await asyncio.wait_for(
                    task.func(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
            else:
                # Sync function - run in thread pool
                result = await asyncio.wait_for(
                    self.loop.run_in_executor(
                        self.thread_pool,
                        lambda: task.func(*task.args, **task.kwargs)
                    ),
                    timeout=task.timeout
                )
            
            # Task completed successfully
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.end_time = datetime.now()
            task.progress = 1.0
            
            # Update statistics
            self.stats['tasks_completed'] += 1
            processing_time = (task.end_time - task.start_time).total_seconds()
            self.stats['total_processing_time'] += processing_time
            self.stats['avg_processing_time'] = (
                self.stats['total_processing_time'] / 
                max(1, self.stats['tasks_completed'])
            )
            
            # Call completion callback
            if task.completion_callback:
                try:
                    task.completion_callback(task)
                except Exception as e:
                    logger.error(f"Completion callback error: {e}")
            
            # Update progress
            if task.progress_callback:
                task.progress_callback(1.0, "Completed")
            
            logger.info(f"Task completed: {task.name} ({processing_time:.2f}s)")
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = TimeoutError(f"Task timeout after {task.timeout}s")
            task.end_time = datetime.now()
            
            self.stats['tasks_failed'] += 1
            logger.error(f"Task timeout: {task.name}")
            
            # Retry if possible
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                logger.info(f"Retrying task: {task.name} (attempt {task.retry_count})")
                await self.task_queue.put(task)
            
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.end_time = datetime.now()
            self.stats['tasks_cancelled'] += 1
            logger.info(f"Task cancelled: {task.name}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = e
            task.end_time = datetime.now()
            
            self.stats['tasks_failed'] += 1
            logger.error(f"Task failed: {task.name} - {e}")
            
            # Retry if possible
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                logger.info(f"Retrying task: {task.name} (attempt {task.retry_count})")
                await self.task_queue.put(task)
        
        finally:
            # Remove from running tasks
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
    
    def submit_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: int = 5,
        timeout: float = 300.0,
        progress_callback: Optional[Callable] = None,
        completion_callback: Optional[Callable] = None
    ) -> AsyncTask:
        """Submit a task for async processing"""
        
        if kwargs is None:
            kwargs = {}
        
        task = AsyncTask(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout,
            progress_callback=progress_callback,
            completion_callback=completion_callback
        )
        
        self.tasks[task_id] = task
        self.stats['tasks_submitted'] += 1
        
        # Add to queue
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.task_queue.put(task),
                self.loop
            )
        else:
            # If no loop, create one
            try:
                asyncio.create_task(self.task_queue.put(task))
            except RuntimeError:
                # Store for later processing
                pass
        
        logger.debug(f"Task submitted: {name} ({task_id})")
        return task
    
    def get_task_status(self, task_id: str) -> Optional[AsyncTask]:
        """Get task status"""
        return self.tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            return True
        
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            **self.stats,
            'running_tasks': len(self.running_tasks),
            'queued_tasks': self.task_queue.qsize() if hasattr(self.task_queue, 'qsize') else 0,
            'total_tasks': len(self.tasks),
            'is_running': self.is_running
        }
    
    def clear_completed_tasks(self) -> int:
        """Clear completed tasks from memory"""
        completed_tasks = [
            task_id for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]
        
        for task_id in completed_tasks:
            del self.tasks[task_id]
        
        logger.info(f"Cleared {len(completed_tasks)} completed tasks")
        return len(completed_tasks)
    
    def __del__(self):
        """Cleanup when processor is destroyed"""
        self.stop()


# Global async processor instance
async_processor = AsyncProcessor()


def submit_async_task(
    task_id: str,
    name: str,
    func: Callable,
    *args,
    **kwargs
) -> AsyncTask:
    """Convenience function to submit async task"""
    return async_processor.submit_task(task_id, name, func, args, kwargs)


def get_task_status(task_id: str) -> Optional[AsyncTask]:
    """Convenience function to get task status"""
    return async_processor.get_task_status(task_id)


def start_async_processing() -> None:
    """Convenience function to start async processing"""
    async_processor.start()


def stop_async_processing() -> None:
    """Convenience function to stop async processing"""
    async_processor.stop()
