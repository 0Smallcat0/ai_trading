"""重構後風險管理模組測試

此模組測試重構後的風險管理模組功能。
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch


# 測試新的風險管理器模組
def test_risk_manager_base_import():
    """測試風險管理器基礎類別導入"""
    try:
        from src.risk_management.risk_manager_base import RiskManagerBase

        # 創建實例
        manager = RiskManagerBase()

        # 檢查基本屬性
        assert hasattr(manager, "trading_enabled")
        assert hasattr(manager, "risk_parameters")
        assert hasattr(manager, "risk_metrics")
        assert hasattr(manager, "risk_events")

        print("✓ 風險管理器基礎類別測試通過")
        return True

    except Exception as e:
        print(f"❌ 風險管理器基礎類別測試失敗: {e}")
        return False


def test_strategy_manager_import():
    """測試策略管理器導入"""
    try:
        from src.risk_management.strategy_manager import StrategyManager

        # 創建實例
        manager = StrategyManager()

        # 檢查基本屬性
        assert hasattr(manager, "stop_loss_strategies")
        assert hasattr(manager, "take_profit_strategies")
        assert hasattr(manager, "position_sizing_strategies")
        assert hasattr(manager, "circuit_breakers")

        print("✓ 策略管理器測試通過")
        return True

    except Exception as e:
        print(f"❌ 策略管理器測試失敗: {e}")
        return False


def test_risk_monitor_import():
    """測試風險監控器導入"""
    try:
        from src.risk_management.risk_monitor import RiskMonitor

        # 創建實例
        monitor = RiskMonitor()

        # 檢查基本屬性
        assert hasattr(monitor, "risk_metrics_calculator")
        assert hasattr(monitor, "monitoring_enabled")
        assert hasattr(monitor, "risk_thresholds")

        print("✓ 風險監控器測試通過")
        return True

    except Exception as e:
        print(f"❌ 風險監控器測試失敗: {e}")
        return False


def test_new_risk_manager_import():
    """測試新風險管理器導入"""
    try:
        from src.risk_management.risk_manager_new import RiskManager

        # 創建實例
        manager = RiskManager()

        # 檢查基本屬性
        assert hasattr(manager, "strategy_manager")
        assert hasattr(manager, "risk_monitor")
        assert hasattr(manager, "portfolio_risk_manager")

        print("✓ 新風險管理器測試通過")
        return True

    except Exception as e:
        print(f"❌ 新風險管理器測試失敗: {e}")
        return False


def test_risk_manager_functionality():
    """測試風險管理器功能"""
    try:
        from src.risk_management.risk_manager_new import RiskManager

        # 創建實例
        manager = RiskManager()

        # 測試基本功能
        assert manager.is_trading_enabled() == True

        # 測試風險參數
        manager.update_risk_parameter("test_param", 0.1)
        assert manager.get_risk_parameter("test_param") == 0.1

        # 測試風險事件記錄
        initial_events = len(manager.get_risk_events())
        manager._record_risk_event("test_event", test_data="test")
        assert len(manager.get_risk_events()) == initial_events + 1

        print("✓ 風險管理器功能測試通過")
        return True

    except Exception as e:
        print(f"❌ 風險管理器功能測試失敗: {e}")
        return False


def test_risk_metrics_calculation():
    """測試風險指標計算"""
    try:
        from src.risk_management.risk_monitor import RiskMonitor

        # 創建實例
        monitor = RiskMonitor()

        # 創建測試數據
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 252))

        # 計算風險指標
        metrics = monitor.update_risk_metrics(returns)

        # 檢查指標是否存在
        assert isinstance(metrics, dict)

        print("✓ 風險指標計算測試通過")
        return True

    except Exception as e:
        print(f"❌ 風險指標計算測試失敗: {e}")
        return False


def test_portfolio_risk_calculation():
    """測試投資組合風險計算"""
    try:
        from src.risk_management.risk_monitor import RiskMonitor

        # 創建實例
        monitor = RiskMonitor()

        # 創建測試持倉數據
        positions = {
            "AAPL": {"value": 10000, "sector": "Technology"},
            "GOOGL": {"value": 8000, "sector": "Technology"},
            "JPM": {"value": 6000, "sector": "Financial"},
        }

        # 計算投資組合風險
        risk_metrics = monitor.calculate_portfolio_risk(positions)

        # 檢查指標
        assert "total_value" in risk_metrics
        assert "concentration_risk" in risk_metrics
        assert "herfindahl_index" in risk_metrics

        print("✓ 投資組合風險計算測試通過")
        return True

    except Exception as e:
        print(f"❌ 投資組合風險計算測試失敗: {e}")
        return False


def test_risk_report_generation():
    """測試風險報告生成"""
    try:
        from src.risk_management.risk_monitor import RiskMonitor

        # 創建實例
        monitor = RiskMonitor()

        # 創建測試數據
        metrics = {
            "max_drawdown": 0.15,
            "volatility": 0.25,
            "sharpe_ratio": 1.2,
        }

        violations = {
            "max_drawdown": False,
            "volatility": False,
            "sharpe_ratio": True,
        }

        # 生成報告
        report = monitor.generate_risk_report(metrics, violations)

        # 檢查報告內容
        assert "risk_score" in report
        assert "risk_level" in report
        assert "recommendations" in report

        print("✓ 風險報告生成測試通過")
        return True

    except Exception as e:
        print(f"❌ 風險報告生成測試失敗: {e}")
        return False


def test_file_size_compliance():
    """測試檔案大小合規性"""
    import os

    files_to_check = [
        "src/risk_management/risk_manager_base.py",
        "src/risk_management/strategy_manager.py",
        "src/risk_management/risk_monitor.py",
        "src/risk_management/risk_manager_new.py",
    ]

    all_compliant = True

    for file_path in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lines = len(f.readlines())

            if lines > 300:
                print(f"❌ {file_path}: {lines} 行 (超過 300 行限制)")
                all_compliant = False
            else:
                print(f"✓ {file_path}: {lines} 行 (符合限制)")
        else:
            print(f"⚠ {file_path}: 檔案不存在")

    return all_compliant


def main():
    """主測試函數"""
    print("開始重構後風險管理模組測試...")

    tests = [
        test_risk_manager_base_import,
        test_strategy_manager_import,
        test_risk_monitor_import,
        test_new_risk_manager_import,
        test_risk_manager_functionality,
        test_risk_metrics_calculation,
        test_portfolio_risk_calculation,
        test_risk_report_generation,
        test_file_size_compliance,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 測試 {test.__name__} 發生異常: {e}")

    print(f"\n測試結果: {passed}/{total} 通過")

    if passed == total:
        print("🎉 所有測試通過！")
    else:
        print("⚠ 部分測試失敗")

    return passed == total


if __name__ == "__main__":
    main()
