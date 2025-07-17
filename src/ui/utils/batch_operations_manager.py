"""
批量操作管理器

提供統一的批量操作功能，包括：
- 批量策略執行
- 批量數據更新
- 批量交易訂單處理
- 批量風險管理操作
- 進度追蹤和錯誤處理
"""

import time
import asyncio
import threading
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass
import streamlit as st
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BatchOperationType(Enum):
    """批量操作類型"""
    STRATEGY_EXECUTION = "strategy_execution"
    DATA_UPDATE = "data_update"
    TRADING_ORDERS = "trading_orders"
    RISK_MANAGEMENT = "risk_management"
    PORTFOLIO_REBALANCE = "portfolio_rebalance"
    REPORT_GENERATION = "report_generation"


class BatchOperationStatus(Enum):
    """批量操作狀態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class BatchOperationConfig:
    """批量操作配置"""
    operation_type: BatchOperationType
    batch_size: int = 100
    max_concurrent: int = 5
    retry_attempts: int = 3
    timeout_seconds: int = 300
    auto_retry: bool = True
    error_threshold: float = 0.1  # 10% 錯誤率閾值
    progress_callback: Optional[Callable] = None
    validation_callback: Optional[Callable] = None


@dataclass
class BatchOperationResult:
    """批量操作結果"""
    operation_id: str
    status: BatchOperationStatus
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    start_time: datetime
    end_time: Optional[datetime] = None
    error_messages: List[str] = None
    results: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []
        if self.results is None:
            self.results = []
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.processed_items == 0:
            return 0.0
        return self.successful_items / self.processed_items
    
    @property
    def duration(self) -> Optional[timedelta]:
        """執行時間"""
        if self.end_time:
            return self.end_time - self.start_time
        return None


class BatchOperationManager:
    """批量操作管理器"""
    
    def __init__(self):
        """初始化批量操作管理器"""
        self.operations: Dict[str, BatchOperationResult] = {}
        self.active_operations: Dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        
        # 初始化 session state
        if "batch_operations" not in st.session_state:
            st.session_state.batch_operations = {}
    
    def start_batch_operation(
        self,
        items: List[Any],
        operation_func: Callable,
        config: BatchOperationConfig,
        operation_name: str = "批量操作"
    ) -> str:
        """開始批量操作
        
        Args:
            items: 要處理的項目列表
            operation_func: 操作函數
            config: 操作配置
            operation_name: 操作名稱
            
        Returns:
            str: 操作ID
        """
        operation_id = f"{config.operation_type.value}_{datetime.now().timestamp()}"
        
        # 創建操作結果
        result = BatchOperationResult(
            operation_id=operation_id,
            status=BatchOperationStatus.PENDING,
            total_items=len(items),
            processed_items=0,
            successful_items=0,
            failed_items=0,
            start_time=datetime.now()
        )
        
        with self._lock:
            self.operations[operation_id] = result
            st.session_state.batch_operations[operation_id] = {
                "name": operation_name,
                "type": config.operation_type.value,
                "status": result.status.value,
                "progress": 0.0,
                "start_time": result.start_time.isoformat()
            }
        
        # 在背景執行操作
        thread = threading.Thread(
            target=self._execute_batch_operation,
            args=(operation_id, items, operation_func, config)
        )
        thread.daemon = True
        
        with self._lock:
            self.active_operations[operation_id] = thread
        
        thread.start()
        
        logger.info(f"批量操作已啟動: {operation_id}, 項目數: {len(items)}")
        return operation_id
    
    def _execute_batch_operation(
        self,
        operation_id: str,
        items: List[Any],
        operation_func: Callable,
        config: BatchOperationConfig
    ) -> None:
        """執行批量操作"""
        result = self.operations[operation_id]
        
        try:
            result.status = BatchOperationStatus.RUNNING
            self._update_session_state(operation_id, result)
            
            # 驗證項目（如果有驗證回調）
            if config.validation_callback:
                items = [item for item in items if config.validation_callback(item)]
                result.total_items = len(items)
            
            # 分批處理
            for i in range(0, len(items), config.batch_size):
                if result.status == BatchOperationStatus.CANCELLED:
                    break
                
                batch = items[i:i + config.batch_size]
                batch_results = self._process_batch(
                    batch, operation_func, config, operation_id
                )
                
                # 更新結果
                for batch_result in batch_results:
                    result.processed_items += 1
                    if batch_result.get("success", False):
                        result.successful_items += 1
                    else:
                        result.failed_items += 1
                        if batch_result.get("error"):
                            result.error_messages.append(str(batch_result["error"]))
                    
                    result.results.append(batch_result)
                
                # 檢查錯誤率
                if result.processed_items > 0:
                    error_rate = result.failed_items / result.processed_items
                    if error_rate > config.error_threshold:
                        logger.warning(f"操作 {operation_id} 錯誤率過高: {error_rate:.2%}")
                        if not config.auto_retry:
                            result.status = BatchOperationStatus.FAILED
                            break
                
                # 更新進度
                progress = result.processed_items / result.total_items
                if config.progress_callback:
                    config.progress_callback(progress, result)
                
                self._update_session_state(operation_id, result)
            
            # 完成操作
            if result.status != BatchOperationStatus.CANCELLED:
                result.status = BatchOperationStatus.COMPLETED
            
            result.end_time = datetime.now()
            
        except Exception as e:
            logger.error(f"批量操作 {operation_id} 執行失敗: {e}", exc_info=True)
            result.status = BatchOperationStatus.FAILED
            result.error_messages.append(str(e))
            result.end_time = datetime.now()
        
        finally:
            self._update_session_state(operation_id, result)
            with self._lock:
                if operation_id in self.active_operations:
                    del self.active_operations[operation_id]
    
    def _process_batch(
        self,
        batch: List[Any],
        operation_func: Callable,
        config: BatchOperationConfig,
        operation_id: str
    ) -> List[Dict[str, Any]]:
        """處理單個批次"""
        results = []
        
        for item in batch:
            if self.operations[operation_id].status == BatchOperationStatus.CANCELLED:
                break
            
            retry_count = 0
            while retry_count <= config.retry_attempts:
                try:
                    start_time = time.time()
                    result = operation_func(item)
                    execution_time = time.time() - start_time
                    
                    results.append({
                        "item": item,
                        "result": result,
                        "success": True,
                        "execution_time": execution_time,
                        "retry_count": retry_count
                    })
                    break
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count > config.retry_attempts:
                        results.append({
                            "item": item,
                            "result": None,
                            "success": False,
                            "error": str(e),
                            "retry_count": retry_count - 1
                        })
                    else:
                        time.sleep(0.5 * retry_count)  # 指數退避
        
        return results
    
    def _update_session_state(self, operation_id: str, result: BatchOperationResult) -> None:
        """更新 session state"""
        progress = result.processed_items / result.total_items if result.total_items > 0 else 0
        
        st.session_state.batch_operations[operation_id].update({
            "status": result.status.value,
            "progress": progress,
            "processed_items": result.processed_items,
            "successful_items": result.successful_items,
            "failed_items": result.failed_items,
            "success_rate": result.success_rate
        })
    
    def get_operation_status(self, operation_id: str) -> Optional[BatchOperationResult]:
        """獲取操作狀態"""
        return self.operations.get(operation_id)
    
    def cancel_operation(self, operation_id: str) -> bool:
        """取消操作"""
        if operation_id in self.operations:
            self.operations[operation_id].status = BatchOperationStatus.CANCELLED
            logger.info(f"批量操作已取消: {operation_id}")
            return True
        return False
    
    def pause_operation(self, operation_id: str) -> bool:
        """暫停操作"""
        if operation_id in self.operations:
            self.operations[operation_id].status = BatchOperationStatus.PAUSED
            logger.info(f"批量操作已暫停: {operation_id}")
            return True
        return False
    
    def resume_operation(self, operation_id: str) -> bool:
        """恢復操作"""
        if operation_id in self.operations:
            if self.operations[operation_id].status == BatchOperationStatus.PAUSED:
                self.operations[operation_id].status = BatchOperationStatus.RUNNING
                logger.info(f"批量操作已恢復: {operation_id}")
                return True
        return False
    
    def get_all_operations(self) -> Dict[str, BatchOperationResult]:
        """獲取所有操作"""
        return self.operations.copy()
    
    def cleanup_completed_operations(self, max_age_hours: int = 24) -> int:
        """清理已完成的操作"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        with self._lock:
            operations_to_remove = []
            for operation_id, result in self.operations.items():
                if (result.status in [BatchOperationStatus.COMPLETED, BatchOperationStatus.FAILED] and
                    result.end_time and result.end_time < cutoff_time):
                    operations_to_remove.append(operation_id)
            
            for operation_id in operations_to_remove:
                del self.operations[operation_id]
                if operation_id in st.session_state.batch_operations:
                    del st.session_state.batch_operations[operation_id]
                cleaned_count += 1
        
        logger.info(f"清理了 {cleaned_count} 個過期的批量操作")
        return cleaned_count


# 全域批量操作管理器
batch_manager = BatchOperationManager()


# 便捷函數
def start_batch_strategy_execution(
    strategies: List[Dict[str, Any]],
    execution_func: Callable,
    batch_size: int = 10
) -> str:
    """開始批量策略執行"""
    config = BatchOperationConfig(
        operation_type=BatchOperationType.STRATEGY_EXECUTION,
        batch_size=batch_size,
        max_concurrent=3,
        timeout_seconds=600
    )
    
    return batch_manager.start_batch_operation(
        items=strategies,
        operation_func=execution_func,
        config=config,
        operation_name="批量策略執行"
    )


def start_batch_data_update(
    symbols: List[str],
    update_func: Callable,
    batch_size: int = 50
) -> str:
    """開始批量數據更新"""
    config = BatchOperationConfig(
        operation_type=BatchOperationType.DATA_UPDATE,
        batch_size=batch_size,
        max_concurrent=5,
        timeout_seconds=300
    )
    
    return batch_manager.start_batch_operation(
        items=symbols,
        operation_func=update_func,
        config=config,
        operation_name="批量數據更新"
    )


def start_batch_trading_orders(
    orders: List[Dict[str, Any]],
    order_func: Callable,
    batch_size: int = 20
) -> str:
    """開始批量交易訂單"""
    config = BatchOperationConfig(
        operation_type=BatchOperationType.TRADING_ORDERS,
        batch_size=batch_size,
        max_concurrent=2,
        timeout_seconds=120,
        error_threshold=0.05  # 5% 錯誤率閾值
    )
    
    return batch_manager.start_batch_operation(
        items=orders,
        operation_func=order_func,
        config=config,
        operation_name="批量交易訂單"
    )
