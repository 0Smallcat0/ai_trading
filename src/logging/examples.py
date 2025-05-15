"""
日誌系統使用示例

此模組提供日誌系統的使用示例。
"""

import random
import time

from src.logging import (
    LogCategory,
    api_logger,
    audit_logger,
    data_logger,
    database_logger,
    error_logger,
    log_function_call,
    log_method_call,
    log_with_context,
    logger,
    model_logger,
    network_logger,
    performance_logger,
    security_logger,
    system_logger,
    trade_logger,
    user_logger,
)


# 基本日誌記錄
def basic_logging_example():
    """基本日誌記錄示例"""
    logger.debug("這是一條調試日誌")
    logger.info("這是一條信息日誌")
    logger.warning("這是一條警告日誌")
    logger.error("這是一條錯誤日誌")
    logger.critical("這是一條嚴重錯誤日誌")


# 類別日誌記錄
def category_logging_example():
    """類別日誌記錄示例"""
    system_logger.info("系統啟動")
    data_logger.info("數據處理完成")
    model_logger.info("模型訓練完成")
    trade_logger.info("交易執行完成")
    error_logger.error("發生錯誤")
    security_logger.warning("檢測到可疑活動")
    performance_logger.info("性能指標收集完成")
    api_logger.info("API請求處理完成")
    database_logger.info("數據庫查詢完成")
    network_logger.info("網絡連接建立")
    user_logger.info("用戶登錄")
    audit_logger.info("審計事件記錄")


# 上下文日誌記錄
def context_logging_example():
    """上下文日誌記錄示例"""
    # 記錄帶有數據的日誌
    log_with_context(
        logger=logger,
        level=20,  # INFO
        msg="處理訂單",
        category=LogCategory.TRADE,
        data={"order_id": "12345", "amount": 100.0, "symbol": "2330.TW"},
        tags=["order", "processing"],
    )

    # 記錄帶有請求和響應的日誌
    log_with_context(
        logger=api_logger,
        level=20,  # INFO
        msg="處理API請求",
        category=LogCategory.API,
        request={
            "method": "POST",
            "path": "/api/orders",
            "body": {"symbol": "2330.TW", "amount": 100.0},
        },
        response={"status": 200, "body": {"order_id": "12345"}},
    )

    # 記錄帶有性能指標的日誌
    log_with_context(
        logger=performance_logger,
        level=20,  # INFO
        msg="性能指標",
        category=LogCategory.PERFORMANCE,
        performance={
            "cpu_usage": 45.2,
            "memory_usage": 78.5,
            "disk_usage": 62.3,
            "network_in": 1024,
            "network_out": 2048,
        },
    )

    # 記錄帶有用戶信息的日誌
    log_with_context(
        logger=user_logger,
        level=20,  # INFO
        msg="用戶活動",
        category=LogCategory.USER,
        user={"id": "user123", "name": "張三", "role": "trader"},
        data={"action": "login", "ip": "192.168.1.1"},
    )

    # 記錄帶有異常信息的日誌
    try:
        1 / 0
    except Exception as e:
        log_with_context(
            logger=error_logger,
            level=40,  # ERROR
            msg="發生異常",
            category=LogCategory.ERROR,
            data={"operation": "除法運算"},
            exc_info=e,
        )


# 函數調用日誌記錄
@log_function_call(logger=logger, level=20, category=LogCategory.SYSTEM)
def example_function(a, b, c=None):
    """示例函數"""
    time.sleep(random.random())
    return a + b


# 方法調用日誌記錄
class ExampleClass:
    """示例類"""

    def __init__(self):
        """初始化"""
        self.logger = logger

    @log_method_call(level=20, category=LogCategory.SYSTEM)
    def example_method(self, a, b, c=None):
        """示例方法"""
        time.sleep(random.random())
        return a * b


# 異常日誌記錄
@log_function_call(logger=error_logger, level=20, category=LogCategory.ERROR)
def example_error_function():
    """示例錯誤函數"""
    time.sleep(random.random())
    raise ValueError("示例錯誤")


# 性能日誌記錄
@log_function_call(
    logger=performance_logger, level=20, category=LogCategory.PERFORMANCE
)
def example_performance_function():
    """示例性能函數"""
    start_time = time.time()
    time.sleep(random.random())
    end_time = time.time()
    execution_time = end_time - start_time
    log_with_context(
        logger=performance_logger,
        level=20,  # INFO
        msg="函數執行時間",
        category=LogCategory.PERFORMANCE,
        performance={"execution_time": execution_time},
    )


# 主函數
def main():
    """主函數"""
    print("運行日誌系統示例...")

    # 基本日誌記錄
    basic_logging_example()

    # 類別日誌記錄
    category_logging_example()

    # 上下文日誌記錄
    context_logging_example()

    # 函數調用日誌記錄
    for i in range(5):
        example_function(i, i + 1, c="test")

    # 方法調用日誌記錄
    example = ExampleClass()
    for i in range(5):
        example.example_method(i, i + 1, c="test")

    # 異常日誌記錄
    try:
        example_error_function()
    except Exception:
        pass

    # 性能日誌記錄
    for i in range(5):
        example_performance_function()

    print("日誌系統示例運行完成。")


if __name__ == "__main__":
    main()
