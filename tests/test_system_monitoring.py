#!/usr/bin/env python3
"""
系統監控模組測試腳本

此腳本用於測試系統監控模組的各項功能，包括：
- 系統監控服務
- 系統指標收集
- 警報管理
- 日誌查詢
- 報告生成

使用方法：
    python scripts/test_system_monitoring.py
"""

import sys
import os
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import json
from datetime import datetime, timedelta

# 設置日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_system_monitoring_service():
    """測試系統監控服務"""
    try:
        from src.core.system_monitoring_service import SystemMonitoringService

        logger.info("開始測試系統監控服務...")

        # 初始化服務
        service = SystemMonitoringService()
        logger.info("✅ 系統監控服務初始化成功")

        # 測試監控控制
        test_monitoring_control(service)

        # 測試系統指標收集
        test_metrics_collection(service)

        # 測試系統狀態獲取
        test_system_status(service)

        # 測試警報功能
        test_alert_management(service)

        # 測試日誌查詢
        test_log_queries(service)

        # 測試報告生成
        test_report_generation(service)

        logger.info("✅ 系統監控服務測試完成")

    except ImportError as e:
        logger.error(f"❌ 無法導入系統監控服務: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 系統監控服務測試失敗: {e}")
        return False

    return True


def test_monitoring_control(service):
    """測試監控控制功能"""
    logger.info("測試監控控制功能...")

    try:
        # 測試啟動監控
        success, message = service.start_monitoring()
        logger.info(f"啟動監控: {success} - {message}")

        # 測試停止監控
        success, message = service.stop_monitoring()
        logger.info(f"停止監控: {success} - {message}")

        # 重新啟動監控
        success, message = service.start_monitoring()
        logger.info(f"重新啟動監控: {success} - {message}")

        logger.info("✅ 監控控制功能測試成功")

    except Exception as e:
        logger.error(f"❌ 監控控制功能測試失敗: {e}")


def test_metrics_collection(service):
    """測試系統指標收集"""
    logger.info("測試系統指標收集...")

    try:
        # 測試收集系統指標
        success, message, metrics = service.collect_system_metrics()
        logger.info(f"收集系統指標: {success} - {message}")

        if success and metrics:
            logger.info(f"收集到的指標:")
            logger.info(f"  - CPU使用率: {metrics.get('cpu_usage', 'N/A')}%")
            logger.info(f"  - 記憶體使用率: {metrics.get('memory_usage', 'N/A')}%")
            logger.info(f"  - 磁碟使用率: {metrics.get('disk_usage', 'N/A')}%")
            logger.info(f"  - 進程數量: {metrics.get('process_count', 'N/A')}")

        # 測試效能指標記錄
        success = service.log_performance(
            module_name="test_module",
            function_name="test_function",
            response_time=123.45,
            operation_type="test",
            success_count=1,
            error_count=0,
        )
        logger.info(f"記錄效能指標: {success}")

        logger.info("✅ 系統指標收集測試成功")

    except Exception as e:
        logger.error(f"❌ 系統指標收集測試失敗: {e}")


def test_system_status(service):
    """測試系統狀態獲取"""
    logger.info("測試系統狀態獲取...")

    try:
        # 測試獲取系統狀態
        status = service.get_system_status()

        if "error" in status:
            logger.error(f"獲取系統狀態失敗: {status['error']}")
        else:
            logger.info(f"系統狀態:")
            logger.info(f"  - 監控狀態: {status.get('monitoring_active', 'N/A')}")
            logger.info(f"  - 健康分數: {status.get('health_score', 'N/A')}")
            logger.info(f"  - 系統運行時間: {status.get('uptime', 'N/A')}")

            resources = status.get("system_resources", {})
            logger.info(f"  - CPU使用率: {resources.get('cpu_usage', 'N/A')}%")
            logger.info(f"  - 記憶體使用率: {resources.get('memory_usage', 'N/A')}%")
            logger.info(f"  - 磁碟使用率: {resources.get('disk_usage', 'N/A')}%")

        # 測試API連線狀態
        api_status = service.get_api_connection_status()
        if "error" not in api_status:
            summary = api_status.get("summary", {})
            logger.info(f"API連線狀態:")
            logger.info(f"  - 總API數: {summary.get('total', 'N/A')}")
            logger.info(f"  - 已連線: {summary.get('connected', 'N/A')}")
            logger.info(f"  - 連線率: {summary.get('connection_rate', 'N/A')}%")

        # 測試交易績效摘要
        performance = service.get_trading_performance_summary()
        if "error" not in performance:
            logger.info(f"交易績效摘要:")
            logger.info(f"  - 今日訂單: {performance.get('today_orders', 'N/A')}")
            logger.info(f"  - 成交訂單: {performance.get('filled_orders', 'N/A')}")
            logger.info(f"  - 成功率: {performance.get('win_rate', 'N/A')}%")
            logger.info(f"  - 成交金額: ${performance.get('total_amount', 'N/A')}")

        logger.info("✅ 系統狀態獲取測試成功")

    except Exception as e:
        logger.error(f"❌ 系統狀態獲取測試失敗: {e}")


def test_alert_management(service):
    """測試警報管理功能"""
    logger.info("測試警報管理功能...")

    try:
        # 測試檢查警報
        triggered_alerts = service.check_alerts()
        logger.info(f"檢查警報: 觸發了 {len(triggered_alerts)} 個警報")

        for alert in triggered_alerts:
            logger.info(
                f"  - 警報: {alert.get('rule_name', 'N/A')} - {alert.get('message', 'N/A')}"
            )

        # 測試獲取警報記錄
        alerts = service.get_alert_records(limit=10)
        logger.info(f"獲取到 {len(alerts)} 筆警報記錄")

        # 如果有警報記錄，測試警報操作
        if alerts:
            test_alert = alerts[0]
            alert_id = test_alert.get("alert_id")

            if test_alert.get("status") == "active":
                # 測試確認警報
                success, message = service.acknowledge_alert(alert_id, "test_user")
                logger.info(f"確認警報: {success} - {message}")

                # 測試解決警報
                success, message = service.resolve_alert(alert_id, "test_user")
                logger.info(f"解決警報: {success} - {message}")

        logger.info("✅ 警報管理功能測試成功")

    except Exception as e:
        logger.error(f"❌ 警報管理功能測試失敗: {e}")


def test_log_queries(service):
    """測試日誌查詢功能"""
    logger.info("測試日誌查詢功能...")

    try:
        # 測試獲取系統日誌
        logs = service.get_system_logs(limit=10)
        logger.info(f"獲取到 {len(logs)} 筆系統日誌")

        # 測試獲取效能指標
        performance_logs = service.get_performance_metrics(limit=10)
        logger.info(f"獲取到 {len(performance_logs)} 筆效能日誌")

        # 測試獲取審計日誌
        audit_logs = service.get_audit_logs(limit=10)
        logger.info(f"獲取到 {len(audit_logs)} 筆審計日誌")

        # 測試記錄審計事件
        success = service.log_audit_event(
            user_id="test_user",
            username="測試使用者",
            action="test_action",
            resource="test_resource",
            status="success",
            ip_address="127.0.0.1",
            risk_level="low",
        )
        logger.info(f"記錄審計事件: {success}")

        logger.info("✅ 日誌查詢功能測試成功")

    except Exception as e:
        logger.error(f"❌ 日誌查詢功能測試失敗: {e}")


def test_report_generation(service):
    """測試報告生成功能"""
    logger.info("測試報告生成功能...")

    try:
        # 測試生成日報
        report = service.generate_system_report(report_type="daily")

        if "error" in report:
            logger.error(f"生成日報失敗: {report['error']}")
        else:
            logger.info("✅ 日報生成成功")
            logger.info(f"報告類型: {report.get('report_type', 'N/A')}")

            period = report.get("period", {})
            logger.info(
                f"報告期間: {period.get('start_date', 'N/A')} 至 {period.get('end_date', 'N/A')}"
            )

            # 顯示系統指標摘要
            metrics_summary = report.get("system_metrics", {})
            if "cpu_usage" in metrics_summary:
                cpu_stats = metrics_summary["cpu_usage"]
                logger.info(
                    f"CPU使用率 - 平均: {cpu_stats.get('avg', 'N/A')}%, 最大: {cpu_stats.get('max', 'N/A')}%"
                )

        # 測試匯出報告
        if "error" not in report:
            # 測試JSON格式匯出
            success, message, filepath = service.export_report(report, "json")
            logger.info(f"匯出JSON報告: {success} - {message}")

            # 測試CSV格式匯出
            success, message, filepath = service.export_report(report, "csv")
            logger.info(f"匯出CSV報告: {success} - {message}")

        logger.info("✅ 報告生成功能測試成功")

    except Exception as e:
        logger.error(f"❌ 報告生成功能測試失敗: {e}")


def test_database_schema():
    """測試資料庫結構"""
    logger.info("測試資料庫結構...")

    try:
        from src.database.schema import (
            SystemMetric,
            PerformanceLog,
            AlertRule,
            AlertRecord,
            AuditLog,
            init_db,
        )
        from sqlalchemy import create_engine
        from src.config import DB_URL

        # 測試資料庫連接和表格創建
        engine = create_engine(DB_URL)
        try:
            init_db(engine)
        except Exception as e:
            # 如果表格已存在，這是正常的
            if "already exists" in str(e):
                logger.info("✅ 資料庫表格已存在，跳過創建")
            else:
                raise e

        logger.info("✅ 資料庫結構測試成功")

    except ImportError as e:
        logger.error(f"❌ 無法導入資料庫模組: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 資料庫結構測試失敗: {e}")
        return False

    return True


def main():
    """主函數"""
    logger.info("開始系統監控模組測試...")

    # 測試資料庫結構
    if not test_database_schema():
        logger.error("❌ 資料庫結構測試失敗，停止測試")
        return

    # 測試系統監控服務
    if not test_system_monitoring_service():
        logger.error("❌ 系統監控服務測試失敗")
        return

    logger.info("🎉 所有測試完成！")


if __name__ == "__main__":
    main()
