"""
背壓控制和故障轉移功能示例

此示例展示如何使用新實現的背壓控制和故障轉移功能：
1. WebSocket 背壓控制
2. 資料源故障轉移
3. 健康檢查和監控
"""

import time
import logging
from src.core.data_ingest import DataIngestionManager
from src.core.websocket_client import WebSocketClient
from src.core.data_source_failover import DataSourceFailoverManager

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def demo_backpressure_control():
    """演示背壓控制功能"""
    logger.info("=== 背壓控制功能演示 ===")

    # 創建帶背壓控制的 WebSocket 客戶端
    client = WebSocketClient(
        url="ws://example.com/ws",
        enable_backpressure=True,
        backpressure_config={
            "warning_threshold": 0.7,
            "critical_threshold": 0.9,
            "adjustment_factor": 0.2,
            "min_interval": 0.001,
            "max_interval": 2.0,
        },
        max_queue_size=50,
    )

    # 模擬消息處理
    def on_message(message):
        logger.info(f"處理消息: {message}")
        time.sleep(0.1)  # 模擬處理時間

    client.on_message_callback = on_message

    # 模擬收到大量消息
    logger.info("模擬收到大量消息...")
    for i in range(60):
        client._on_message(None, f"message_{i}")
        if i % 10 == 0:
            stats = client.get_backpressure_stats()
            if stats:
                logger.info(
                    f"背壓統計: 當前間隔={stats['current_interval']:.3f}s, "
                    f"背壓事件={stats['backpressure_events']}"
                )

    # 獲取最終統計信息
    final_stats = client.get_stats()
    logger.info(f"最終統計: {final_stats}")

    client.close()


def demo_data_source_failover():
    """演示資料源故障轉移功能"""
    logger.info("=== 資料源故障轉移功能演示 ===")

    # 創建故障轉移管理器
    failover_manager = DataSourceFailoverManager(
        health_check_interval=10.0,
        max_consecutive_failures=2,
        circuit_breaker_timeout=30.0,
    )

    # 模擬資料源適配器
    class MockAdapter:
        def __init__(self, name, should_fail=False):
            self.name = name
            self.should_fail = should_fail
            self.call_count = 0

        def test_connection(self):
            self.call_count += 1
            if self.should_fail and self.call_count > 2:
                return False
            return True

        def get_data(self):
            if self.should_fail and self.call_count > 2:
                raise Exception(f"{self.name} 連接失敗")
            return f"來自 {self.name} 的資料"

    # 註冊資料源
    yahoo_adapter = MockAdapter("Yahoo", should_fail=False)
    broker_adapter = MockAdapter("Broker", should_fail=True)

    failover_manager.register_data_source(
        "yahoo", yahoo_adapter, priority_groups=["price"]
    )
    failover_manager.register_data_source(
        "broker", broker_adapter, priority_groups=["price"]
    )

    # 設定優先級
    failover_manager.set_priority_order("price", ["yahoo", "broker"])

    # 啟動健康監控
    failover_manager.start_health_monitoring()

    # 模擬請求
    logger.info("開始模擬資料請求...")
    for i in range(10):
        best_source = failover_manager.get_best_source("price")
        logger.info(f"第 {i+1} 次請求，選擇資料源: {best_source}")

        if best_source:
            try:
                # 模擬請求
                start_time = time.time()
                adapter = failover_manager.data_sources[best_source]["adapter"]
                data = adapter.get_data()
                response_time = time.time() - start_time

                # 記錄成功
                failover_manager.record_request_result(best_source, True, response_time)
                logger.info(f"成功獲取資料: {data}")

            except Exception as e:
                # 記錄失敗
                failover_manager.record_request_result(best_source, False, 0.0, str(e))
                logger.error(f"請求失敗: {e}")

        # 顯示健康狀態
        summary = failover_manager.get_health_summary()
        logger.info(
            f"健康狀態: 健康={summary['healthy_sources']}, "
            f"不健康={summary['unhealthy_sources']}"
        )

        time.sleep(2)

    # 停止監控
    failover_manager.stop_health_monitoring()


def demo_data_ingestion_manager():
    """演示資料擷取管理器的整合功能"""
    logger.info("=== 資料擷取管理器整合功能演示 ===")

    # 創建資料擷取管理器
    manager = DataIngestionManager(use_cache=False, max_workers=2)  # 關閉快取以便測試

    try:
        # 獲取健康狀態摘要
        summary = manager.get_health_summary()
        logger.info(f"初始健康狀態: {summary}")

        # 獲取故障轉移統計信息
        failover_stats = manager.get_failover_stats()
        logger.info(f"故障轉移統計: {failover_stats}")

        # 測試強制故障轉移
        logger.info("執行強制故障轉移...")
        manager.force_failover("yahoo", "演示故障轉移")

        # 檢查狀態變化
        summary = manager.get_health_summary()
        logger.info(f"故障轉移後健康狀態: {summary}")

        # 測試強制恢復
        logger.info("執行強制恢復...")
        manager.force_recovery("yahoo", "演示恢復")

        # 檢查狀態變化
        summary = manager.get_health_summary()
        logger.info(f"恢復後健康狀態: {summary}")

        # 獲取特定資料源的健康狀態
        yahoo_health = manager.get_source_health("yahoo")
        if yahoo_health:
            logger.info(f"Yahoo 資料源健康狀態: {yahoo_health}")

        # 獲取完整統計信息
        stats = manager.get_stats()
        logger.info(f"完整統計信息: {stats}")

    finally:
        # 清理資源
        manager.close()


def main():
    """主函數"""
    logger.info("開始背壓控制和故障轉移功能演示")

    try:
        # 演示背壓控制
        demo_backpressure_control()

        print("\n" + "=" * 50 + "\n")

        # 演示故障轉移
        demo_data_source_failover()

        print("\n" + "=" * 50 + "\n")

        # 演示整合功能
        demo_data_ingestion_manager()

    except Exception as e:
        logger.error(f"演示過程中發生錯誤: {e}")
        raise

    logger.info("演示完成")


if __name__ == "__main__":
    main()
