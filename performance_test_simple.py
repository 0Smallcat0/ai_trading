"""簡化監控系統效能測試

此腳本提供基本的效能測試，不依賴外部套件。
"""

import time
import threading
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加 src 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))


def measure_execution_time(func, *args, **kwargs):
    """測量函數執行時間"""
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    end_time = time.perf_counter()
    execution_time = (end_time - start_time) * 1000  # 轉換為毫秒
    return result, execution_time


def test_prometheus_collector_performance():
    """測試 Prometheus 收集器效能"""
    print("🔍 測試 Prometheus 收集器效能...")

    try:
        # 模擬依賴
        with patch("src.monitoring.prometheus_collector.CollectorRegistry"), patch(
            "src.monitoring.prometheus_collector.generate_latest"
        ), patch("src.monitoring.prometheus_collector.SystemMetricsCollector"), patch(
            "src.monitoring.prometheus_collector.TradingMetricsCollector"
        ), patch(
            "src.monitoring.prometheus_collector.APIMetricsCollector"
        ), patch(
            "src.monitoring.prometheus_collector.BusinessMetricsCollector"
        ):

            from src.monitoring.prometheus_collector import PrometheusCollector

            # 測試初始化效能
            def init_collector():
                return PrometheusCollector(collection_interval=1)

            collector, init_time = measure_execution_time(init_collector)
            print(f"  ⏱️  初始化時間: {init_time:.2f} ms")

            # 測試指標收集效能
            def collect_metrics():
                return collector.get_metrics()

            _, collection_time = measure_execution_time(collect_metrics)
            print(f"  ⏱️  指標收集時間: {collection_time:.2f} ms")

            # 測試啟動/停止效能
            _, start_time = measure_execution_time(collector.start_collection)
            print(f"  ⏱️  啟動時間: {start_time:.2f} ms")

            _, stop_time = measure_execution_time(collector.stop_collection)
            print(f"  ⏱️  停止時間: {stop_time:.2f} ms")

            # 效能評估
            results = {
                "init_time_ms": init_time,
                "collection_time_ms": collection_time,
                "start_time_ms": start_time,
                "stop_time_ms": stop_time,
                "init_ok": init_time < 100,
                "collection_ok": collection_time < 50,
                "start_ok": start_time < 100,
                "stop_ok": stop_time < 100,
            }

            passed = sum(1 for k, v in results.items() if k.endswith("_ok") and v)
            total = sum(1 for k in results.keys() if k.endswith("_ok"))

            print(f"  📊 效能評估: {passed}/{total} 項通過")

            return results

    except Exception as e:
        print(f"  ❌ 測試失敗: {e}")
        return {"error": str(e)}


def test_grafana_config_performance():
    """測試 Grafana 配置管理器效能"""
    print("🔍 測試 Grafana 配置管理器效能...")

    try:
        # 模擬依賴
        with patch("src.monitoring.grafana_config.GrafanaFace"), patch(
            "src.monitoring.grafana_config.DashboardManager"
        ), patch("src.monitoring.grafana_config.DatasourceManager"), patch(
            "src.monitoring.grafana_config.TemplateGenerator"
        ):

            from src.monitoring.grafana_config import GrafanaConfigManager

            # 測試初始化效能
            def init_manager():
                return GrafanaConfigManager()

            manager, init_time = measure_execution_time(init_manager)
            print(f"  ⏱️  初始化時間: {init_time:.2f} ms")

            # 測試狀態檢查效能
            def check_status():
                return manager.get_system_status()

            _, status_time = measure_execution_time(check_status)
            print(f"  ⏱️  狀態檢查時間: {status_time:.2f} ms")

            # 測試健康檢查效能
            def health_check():
                return manager.is_healthy()

            _, health_time = measure_execution_time(health_check)
            print(f"  ⏱️  健康檢查時間: {health_time:.2f} ms")

            # 效能評估
            results = {
                "init_time_ms": init_time,
                "status_time_ms": status_time,
                "health_time_ms": health_time,
                "init_ok": init_time < 200,
                "status_ok": status_time < 100,
                "health_ok": health_time < 50,
            }

            passed = sum(1 for k, v in results.items() if k.endswith("_ok") and v)
            total = sum(1 for k in results.keys() if k.endswith("_ok"))

            print(f"  📊 效能評估: {passed}/{total} 項通過")

            return results

    except Exception as e:
        print(f"  ❌ 測試失敗: {e}")
        return {"error": str(e)}


def test_monitor_system_performance():
    """測試監控系統效能"""
    print("🔍 測試監控系統效能...")

    try:
        # 模擬所有依賴
        with patch("src.monitoring.monitor_system.AlertHandler"), patch(
            "src.monitoring.monitor_system.SystemMonitor"
        ), patch("src.monitoring.monitor_system.ThresholdChecker"), patch(
            "src.monitoring.monitor_system.prometheus_exporter"
        ), patch(
            "src.monitoring.monitor_system.alert_manager"
        ), patch(
            "src.monitoring.monitor_system.get_logger"
        ):

            from src.monitoring.monitor_system import MonitorSystem

            # 測試初始化效能
            def init_system():
                return MonitorSystem()

            system, init_time = measure_execution_time(init_system)
            print(f"  ⏱️  初始化時間: {init_time:.2f} ms")

            # 測試狀態檢查效能
            def check_status():
                return system.get_status()

            _, status_time = measure_execution_time(check_status)
            print(f"  ⏱️  狀態檢查時間: {status_time:.2f} ms")

            # 測試健康檢查效能
            def health_check():
                return system.is_healthy()

            _, health_time = measure_execution_time(health_check)
            print(f"  ⏱️  健康檢查時間: {health_time:.2f} ms")

            # 效能評估
            results = {
                "init_time_ms": init_time,
                "status_time_ms": status_time,
                "health_time_ms": health_time,
                "init_ok": init_time < 500,
                "status_ok": status_time < 100,
                "health_ok": health_time < 50,
            }

            passed = sum(1 for k, v in results.items() if k.endswith("_ok") and v)
            total = sum(1 for k in results.keys() if k.endswith("_ok"))

            print(f"  📊 效能評估: {passed}/{total} 項通過")

            return results

    except Exception as e:
        print(f"  ❌ 測試失敗: {e}")
        return {"error": str(e)}


def test_concurrent_performance():
    """測試並發效能"""
    print("🔍 測試並發效能...")

    try:
        # 模擬依賴
        with patch("src.monitoring.prometheus_collector.CollectorRegistry"), patch(
            "src.monitoring.prometheus_collector.generate_latest"
        ), patch("src.monitoring.prometheus_collector.SystemMetricsCollector"), patch(
            "src.monitoring.prometheus_collector.TradingMetricsCollector"
        ), patch(
            "src.monitoring.prometheus_collector.APIMetricsCollector"
        ), patch(
            "src.monitoring.prometheus_collector.BusinessMetricsCollector"
        ):

            from src.monitoring.prometheus_collector import PrometheusCollector

            collector = PrometheusCollector(collection_interval=1)

            # 並發測試
            def worker():
                for _ in range(10):
                    collector.get_metrics()
                    collector.is_healthy()
                    collector.get_collector_status()

            num_threads = 5
            threads = []

            start_time = time.perf_counter()

            # 啟動線程
            for _ in range(num_threads):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()

            # 等待完成
            for thread in threads:
                thread.join()

            total_time = time.perf_counter() - start_time
            total_operations = num_threads * 10 * 3  # 每個線程 10 次迭代，每次 3 個操作
            throughput = total_operations / total_time

            print(f"  ⏱️  總執行時間: {total_time*1000:.2f} ms")
            print(f"  🚀 吞吐量: {throughput:.2f} 操作/秒")

            results = {
                "total_time_ms": total_time * 1000,
                "throughput_ops_per_sec": throughput,
                "total_operations": total_operations,
                "time_ok": total_time < 1.0,  # 1秒內完成
                "throughput_ok": throughput > 100,  # 每秒100個操作
            }

            passed = sum(1 for k, v in results.items() if k.endswith("_ok") and v)
            total = sum(1 for k in results.keys() if k.endswith("_ok"))

            print(f"  📊 並發效能評估: {passed}/{total} 項通過")

            return results

    except Exception as e:
        print(f"  ❌ 並發測試失敗: {e}")
        return {"error": str(e)}


def test_extended_business_metrics():
    """測試擴展業務指標"""
    print("🔍 測試擴展業務指標...")

    try:
        # 模擬依賴
        with patch("src.monitoring.business_metrics_extended.Counter"), patch(
            "src.monitoring.business_metrics_extended.Gauge"
        ), patch("src.monitoring.business_metrics_extended.Histogram"):

            from src.monitoring.business_metrics_extended import (
                ExtendedBusinessMetricsCollector,
            )

            # 測試初始化
            def init_collector():
                return ExtendedBusinessMetricsCollector()

            collector, init_time = measure_execution_time(init_collector)
            print(f"  ⏱️  初始化時間: {init_time:.2f} ms")

            # 測試指標摘要
            def get_summary():
                return collector.get_metrics_summary()

            summary, summary_time = measure_execution_time(get_summary)
            print(f"  ⏱️  指標摘要時間: {summary_time:.2f} ms")
            print(f"  📊 總指標數量: {summary.get('total_metrics', 0)}")

            # 測試更新指標
            def update_metrics():
                # 模擬交易數據
                trades = [
                    {
                        "pnl": 100,
                        "entry_time": "2024-01-01T10:00:00",
                        "exit_time": "2024-01-01T11:00:00",
                    },
                    {
                        "pnl": -50,
                        "entry_time": "2024-01-01T11:00:00",
                        "exit_time": "2024-01-01T12:00:00",
                    },
                    {
                        "pnl": 200,
                        "entry_time": "2024-01-01T12:00:00",
                        "exit_time": "2024-01-01T13:00:00",
                    },
                ]

                collector.update_trading_performance("test_strategy", "BTCUSDT", trades)
                collector.update_portfolio_metrics(
                    "test_strategy", [0.01, -0.005, 0.02]
                )
                collector.update_risk_metrics(
                    [0.01, -0.005, 0.02], {"BTCUSDT": 10000}, 100000
                )

            _, update_time = measure_execution_time(update_metrics)
            print(f"  ⏱️  指標更新時間: {update_time:.2f} ms")

            results = {
                "init_time_ms": init_time,
                "summary_time_ms": summary_time,
                "update_time_ms": update_time,
                "total_metrics": summary.get("total_metrics", 0),
                "init_ok": init_time < 100,
                "summary_ok": summary_time < 50,
                "update_ok": update_time < 100,
            }

            passed = sum(1 for k, v in results.items() if k.endswith("_ok") and v)
            total = sum(1 for k in results.keys() if k.endswith("_ok"))

            print(f"  📊 擴展指標評估: {passed}/{total} 項通過")

            return results

    except Exception as e:
        print(f"  ❌ 擴展指標測試失敗: {e}")
        return {"error": str(e)}


def main():
    """主測試函數"""
    print("🚀 開始監控系統效能測試")
    print("=" * 50)

    # 測試項目
    tests = [
        ("Prometheus 收集器", test_prometheus_collector_performance),
        ("Grafana 配置管理器", test_grafana_config_performance),
        ("監控系統", test_monitor_system_performance),
        ("並發效能", test_concurrent_performance),
        ("擴展業務指標", test_extended_business_metrics),
    ]

    all_results = {}
    total_passed = 0
    total_tests = 0

    for test_name, test_func in tests:
        print(f"\n📋 {test_name} 效能測試:")

        try:
            result = test_func()
            all_results[test_name] = result

            if "error" not in result:
                # 計算通過的測試數量
                passed = sum(1 for k, v in result.items() if k.endswith("_ok") and v)
                total = sum(1 for k in result.keys() if k.endswith("_ok"))
                total_passed += passed
                total_tests += total

                print(f"  ✅ {test_name} 完成: {passed}/{total} 項通過")
            else:
                print(f"  ❌ {test_name} 失敗: {result['error']}")

        except Exception as e:
            print(f"  ❌ {test_name} 執行失敗: {e}")
            all_results[test_name] = {"error": str(e)}

    # 總結報告
    print("\n" + "=" * 50)
    print("📊 效能測試總結報告")
    print("=" * 50)

    print(f"🎯 總體效能評估: {total_passed}/{total_tests} 項通過")
    print(
        f"📈 通過率: {total_passed/total_tests*100:.1f}%"
        if total_tests > 0
        else "📈 通過率: 0%"
    )

    # 詳細結果
    for test_name, result in all_results.items():
        if "error" in result:
            print(f"❌ {test_name}: 測試失敗")
        else:
            passed = sum(1 for k, v in result.items() if k.endswith("_ok") and v)
            total = sum(1 for k in result.keys() if k.endswith("_ok"))
            status = "✅" if passed == total else "⚠️"
            print(f"{status} {test_name}: {passed}/{total} 項通過")

    # 效能基準建議
    print("\n📋 效能基準建議:")
    print("  - 初始化時間: <500ms")
    print("  - 指標收集時間: <100ms")
    print("  - 狀態檢查時間: <100ms")
    print("  - 並發吞吐量: >100 操作/秒")

    # 儲存結果
    import json

    with open("performance_results_simple.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 效能測試結果已儲存到 performance_results_simple.json")

    if total_passed == total_tests and total_tests > 0:
        print("🎉 所有效能測試通過！")
        return True
    else:
        print("⚠️  部分效能測試未達標，建議進一步優化。")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
