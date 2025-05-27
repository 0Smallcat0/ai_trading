"""基本監控模組測試

此腳本用於驗證重構後的監控模組是否可以正常導入和初始化。
"""

import sys
import os
from pathlib import Path

# 添加 src 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_prometheus_collector_import():
    """測試 PrometheusCollector 導入"""
    try:
        # 模擬缺失的依賴
        import sys
        from unittest.mock import MagicMock

        # 模擬 prometheus_client
        mock_prometheus = MagicMock()
        mock_prometheus.CollectorRegistry = MagicMock
        mock_prometheus.generate_latest = MagicMock()
        mock_prometheus.CONTENT_TYPE_LATEST = "text/plain"
        sys.modules['prometheus_client'] = mock_prometheus

        # 模擬子模組
        mock_modules = MagicMock()
        sys.modules['src.monitoring.prometheus_modules'] = mock_modules
        mock_modules.SystemMetricsCollector = MagicMock
        mock_modules.TradingMetricsCollector = MagicMock
        mock_modules.APIMetricsCollector = MagicMock
        mock_modules.BusinessMetricsCollector = MagicMock

        from src.monitoring.prometheus_collector import PrometheusCollector

        # 測試初始化
        collector = PrometheusCollector(collection_interval=15)

        print("✅ PrometheusCollector 導入和初始化成功")
        print(f"   - 收集間隔: {collector.collection_interval} 秒")
        print(f"   - 子收集器數量: {len(collector.collectors)}")
        print(f"   - 收集狀態: {collector.is_collecting}")

        return True

    except Exception as e:
        print(f"❌ PrometheusCollector 測試失敗: {e}")
        return False

def test_grafana_config_import():
    """測試 GrafanaConfigManager 導入"""
    try:
        import sys
        from unittest.mock import MagicMock

        # 模擬 grafana_api
        mock_grafana_api = MagicMock()
        sys.modules['grafana_api'] = mock_grafana_api
        sys.modules['grafana_api.grafana_face'] = mock_grafana_api
        mock_grafana_api.GrafanaFace = MagicMock

        # 模擬子模組
        mock_modules = MagicMock()
        sys.modules['src.monitoring.grafana_modules'] = mock_modules
        mock_modules.DashboardManager = MagicMock
        mock_modules.DatasourceManager = MagicMock
        mock_modules.TemplateGenerator = MagicMock

        # 模擬配置
        sys.modules['src.config'] = MagicMock()
        sys.modules['src.config'].CACHE_DIR = "cache"

        from src.monitoring.grafana_config import GrafanaConfigManager

        # 測試初始化
        manager = GrafanaConfigManager(
            grafana_host="http://localhost:3000",
            grafana_token="test_token"
        )

        print("✅ GrafanaConfigManager 導入和初始化成功")
        print(f"   - 配置目錄: {manager.config_dir}")
        print(f"   - Grafana API: {'已連接' if manager.grafana_api else '未連接'}")
        print(f"   - 儀表板管理器: {'已初始化' if manager.dashboard_manager else '未初始化'}")

        return True

    except Exception as e:
        print(f"❌ GrafanaConfigManager 測試失敗: {e}")
        return False

def test_monitor_system_import():
    """測試 MonitorSystem 導入"""
    try:
        import sys
        from unittest.mock import MagicMock

        # 模擬所有依賴
        mock_logger = MagicMock()
        sys.modules['src.core'] = MagicMock()
        sys.modules['src.core.logger'] = mock_logger
        mock_logger.get_logger = MagicMock(return_value=MagicMock())

        # 模擬監控模組
        mock_monitor_modules = MagicMock()
        sys.modules['src.monitoring.monitor_modules'] = mock_monitor_modules
        mock_monitor_modules.AlertHandler = MagicMock
        mock_monitor_modules.SystemMonitor = MagicMock
        mock_monitor_modules.ThresholdChecker = MagicMock

        # 模擬配置
        mock_config = MagicMock()
        sys.modules['src.monitoring.config'] = mock_config
        mock_config.ALERT_CHECK_INTERVAL = 60
        mock_config.ALERT_LOG_DIR = "logs/alerts"
        mock_config.API_ENDPOINTS = []
        mock_config.EMAIL_CONFIG = {}
        mock_config.GRAFANA_PORT = 3000
        mock_config.PROMETHEUS_COLLECTION_INTERVAL = 15
        mock_config.PROMETHEUS_PORT = 9090
        mock_config.SLACK_WEBHOOK_URL = ""
        mock_config.SMS_CONFIG = {}
        mock_config.THRESHOLDS = {
            "system": {"cpu_usage": 80, "memory_usage": 80, "disk_usage": 85},
            "api": {"latency": 1.0, "error_rate": 0.05},
            "model": {"accuracy": 0.8, "latency": 1.0, "drift": 0.1},
            "trade": {"success_rate": 0.7, "capital_change": -10.0}
        }

        # 模擬外部組件
        sys.modules['src.monitoring.prometheus_exporter'] = MagicMock()
        sys.modules['src.monitoring.alert_manager'] = MagicMock()

        from src.monitoring.monitor_system import MonitorSystem

        # 測試初始化
        config = {
            "prometheus_port": 9090,
            "prometheus_collection_interval": 15,
            "alert_check_interval": 60,
            "api_endpoints": [],
            "email_config": {},
            "slack_webhook_url": "",
            "sms_config": {},
            "alert_log_dir": "logs/alerts",
            "thresholds": {"system": {"cpu_usage": 80}}
        }

        system = MonitorSystem(config)

        print("✅ MonitorSystem 導入和初始化成功")
        print(f"   - 配置: {len(system.config)} 項設定")
        print(f"   - Prometheus 導出器: {'已設置' if system.prometheus_exporter else '未設置'}")
        print(f"   - 警報處理器: {'已設置' if system.alert_handler else '未設置'}")

        return True

    except Exception as e:
        print(f"❌ MonitorSystem 測試失敗: {e}")
        return False

def test_module_structure():
    """測試模組結構"""
    try:
        src_path = Path("src/monitoring")

        # 檢查主要檔案
        main_files = [
            "prometheus_collector.py",
            "grafana_config.py",
            "monitor_system.py"
        ]

        # 檢查子模組目錄
        sub_modules = [
            "prometheus_modules",
            "grafana_modules",
            "monitor_modules"
        ]

        print("📁 檢查模組結構:")

        for file in main_files:
            file_path = src_path / file
            if file_path.exists():
                lines = len(file_path.read_text(encoding='utf-8').splitlines())
                print(f"   ✅ {file}: {lines} 行")
            else:
                print(f"   ❌ {file}: 檔案不存在")

        for module in sub_modules:
            module_path = src_path / module
            if module_path.exists() and module_path.is_dir():
                files = list(module_path.glob("*.py"))
                print(f"   ✅ {module}/: {len(files)} 個檔案")
                for file in files:
                    if file.name != "__init__.py":
                        lines = len(file.read_text(encoding='utf-8').splitlines())
                        print(f"      - {file.name}: {lines} 行")
            else:
                print(f"   ❌ {module}/: 目錄不存在")

        return True

    except Exception as e:
        print(f"❌ 模組結構檢查失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🔍 開始監控模組基本測試\n")

    tests = [
        ("模組結構檢查", test_module_structure),
        ("PrometheusCollector 測試", test_prometheus_collector_import),
        ("GrafanaConfigManager 測試", test_grafana_config_import),
        ("MonitorSystem 測試", test_monitor_system_import),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 執行 {test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 執行失敗: {e}")
            results.append((test_name, False))

    # 總結報告
    print("\n" + "="*50)
    print("📊 測試結果總結:")
    print("="*50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\n🎯 總計: {passed}/{total} 個測試通過")

    if passed == total:
        print("🎉 所有基本測試通過！監控模組重構成功。")
    else:
        print("⚠️  部分測試失敗，需要進一步檢查。")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
