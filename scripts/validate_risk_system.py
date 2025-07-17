"""
風險控制系統整合驗證腳本

驗證實時風險控制系統的所有功能是否正常運作，包括：
- 模組導入檢查
- 基本功能驗證
- 整合流程測試
- 向後兼容性檢查
"""

import sys
import traceback
from datetime import datetime
from unittest.mock import Mock


def test_module_imports():
    """測試模組導入"""
    print("🔍 檢查模組導入...")
    
    modules_to_test = [
        ("資金監控基礎", "src.risk.live.fund_monitor_base", "FundMonitorBase"),
        ("資金計算器", "src.risk.live.fund_calculator", "FundCalculator"),
        ("資金監控器", "src.risk.live.fund_monitor", "FundMonitor"),
        ("停損策略", "src.risk.live.stop_loss_strategies", "StopLossCalculator"),
        ("停損監控", "src.risk.live.stop_loss_monitor", "StopLossMonitor"),
        ("動態停損", "src.risk.live.dynamic_stop_loss", "DynamicStopLoss"),
        ("緊急行動", "src.risk.live.emergency_actions", "EmergencyActionExecutor"),
        ("緊急事件管理", "src.risk.live.emergency_event_manager", "EmergencyEventManager"),
        ("緊急風控", "src.risk.live.emergency_risk_control", "EmergencyRiskControl"),
        ("統一風險控制", "src.risk.live.unified_risk_controller", "UnifiedRiskController"),
    ]
    
    import_results = {}
    
    for name, module_path, class_name in modules_to_test:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            import_results[name] = {"status": "SUCCESS", "class": cls}
            print(f"  ✅ {name}: 導入成功")
        except Exception as e:
            import_results[name] = {"status": "FAILED", "error": str(e)}
            print(f"  ❌ {name}: 導入失敗 - {e}")
    
    return import_results


def test_basic_functionality(import_results):
    """測試基本功能"""
    print("\n🧪 測試基本功能...")
    
    # 創建模擬券商
    mock_broker = Mock()
    mock_broker.get_account_info.return_value = {
        "cash": 100000,
        "buying_power": 200000,
        "total_value": 150000,
        "margin_used": 30000,
        "margin_available": 70000,
    }
    mock_broker.get_positions.return_value = {
        "AAPL": {
            "quantity": 100,
            "avg_price": 150.0,
            "current_price": 155.0,
            "market_value": 15500,
            "unrealized_pnl": 500,
        }
    }
    mock_broker.get_orders.return_value = []
    mock_broker.place_order.return_value = {"success": True, "order_id": "test_123"}
    mock_broker.cancel_order.return_value = {"success": True}
    
    functionality_results = {}
    
    # 測試資金監控器
    if "資金監控器" in import_results and import_results["資金監控器"]["status"] == "SUCCESS":
        try:
            FundMonitor = import_results["資金監控器"]["class"]
            fund_monitor = FundMonitor(mock_broker)
            
            # 測試基本方法
            fund_status = fund_monitor.get_fund_status()
            fund_summary = fund_monitor.get_fund_summary()
            leverage_ratio = fund_monitor.calculate_leverage_ratio()
            
            functionality_results["資金監控器"] = "SUCCESS"
            print(f"  ✅ 資金監控器: 基本功能正常")
        except Exception as e:
            functionality_results["資金監控器"] = f"FAILED: {e}"
            print(f"  ❌ 資金監控器: 功能測試失敗 - {e}")
    
    # 測試動態停損
    if "動態停損" in import_results and import_results["動態停損"]["status"] == "SUCCESS":
        try:
            DynamicStopLoss = import_results["動態停損"]["class"]
            dynamic_stop_loss = DynamicStopLoss(mock_broker)
            
            # 測試基本方法
            from src.risk.live.stop_loss_strategies import StopLossStrategy
            result = dynamic_stop_loss.set_position_stop_loss("AAPL", StopLossStrategy.TRAILING)
            stops = dynamic_stop_loss.get_position_stops()
            
            functionality_results["動態停損"] = "SUCCESS"
            print(f"  ✅ 動態停損: 基本功能正常")
        except Exception as e:
            functionality_results["動態停損"] = f"FAILED: {e}"
            print(f"  ❌ 動態停損: 功能測試失敗 - {e}")
    
    # 測試緊急風控
    if "緊急風控" in import_results and import_results["緊急風控"]["status"] == "SUCCESS":
        try:
            EmergencyRiskControl = import_results["緊急風控"]["class"]
            emergency_control = EmergencyRiskControl(mock_broker)
            
            # 測試基本方法
            from src.risk.live.emergency_risk_control import EmergencyLevel, EmergencyAction
            status = emergency_control.get_emergency_status()
            events = emergency_control.get_emergency_events()
            
            functionality_results["緊急風控"] = "SUCCESS"
            print(f"  ✅ 緊急風控: 基本功能正常")
        except Exception as e:
            functionality_results["緊急風控"] = f"FAILED: {e}"
            print(f"  ❌ 緊急風控: 功能測試失敗 - {e}")
    
    # 測試統一風險控制器
    if "統一風險控制" in import_results and import_results["統一風險控制"]["status"] == "SUCCESS":
        try:
            UnifiedRiskController = import_results["統一風險控制"]["class"]
            risk_controller = UnifiedRiskController(mock_broker)
            
            # 測試基本方法
            risk_status = risk_controller.get_overall_risk_status()
            dashboard_data = risk_controller.get_risk_dashboard_data()
            trade_validation = risk_controller.validate_new_trade("AAPL", 10, 150.0, "buy")
            
            functionality_results["統一風險控制"] = "SUCCESS"
            print(f"  ✅ 統一風險控制器: 基本功能正常")
        except Exception as e:
            functionality_results["統一風險控制"] = f"FAILED: {e}"
            print(f"  ❌ 統一風險控制器: 功能測試失敗 - {e}")
    
    return functionality_results


def test_integration_flow(import_results):
    """測試整合流程"""
    print("\n🔄 測試整合流程...")
    
    if "統一風險控制" not in import_results or import_results["統一風險控制"]["status"] != "SUCCESS":
        print("  ❌ 統一風險控制器導入失敗，跳過整合測試")
        return {"整合流程": "SKIPPED"}
    
    try:
        # 創建模擬券商
        mock_broker = Mock()
        mock_broker.get_account_info.return_value = {
            "cash": 100000,
            "buying_power": 200000,
            "total_value": 150000,
            "margin_used": 30000,
            "margin_available": 70000,
        }
        mock_broker.get_positions.return_value = {
            "AAPL": {
                "quantity": 100,
                "avg_price": 150.0,
                "current_price": 155.0,
                "market_value": 15500,
                "unrealized_pnl": 500,
            }
        }
        mock_broker.get_orders.return_value = []
        mock_broker.place_order.return_value = {"success": True, "order_id": "test_123"}
        mock_broker.cancel_order.return_value = {"success": True}
        
        # 創建統一風險控制器
        UnifiedRiskController = import_results["統一風險控制"]["class"]
        risk_controller = UnifiedRiskController(mock_broker)
        
        # 測試完整流程
        print("  📋 測試風險控制啟動...")
        risk_controller.start_risk_control()
        
        print("  📋 測試停損設置...")
        from src.risk.live.stop_loss_strategies import StopLossStrategy
        stop_result = risk_controller.set_position_stop_loss("AAPL", StopLossStrategy.TRAILING)
        
        print("  📋 測試交易驗證...")
        trade_validation = risk_controller.validate_new_trade("MSFT", 50, 100.0, "buy")
        
        print("  📋 測試緊急措施...")
        from src.risk.live.emergency_risk_control import EmergencyLevel, EmergencyAction
        emergency_result = risk_controller.trigger_emergency_action(
            EmergencyLevel.LOW, "測試", [EmergencyAction.ALERT_ONLY]
        )
        
        print("  📋 測試風險狀態...")
        risk_status = risk_controller.get_overall_risk_status()
        
        print("  📋 測試儀表板數據...")
        dashboard_data = risk_controller.get_risk_dashboard_data()
        
        print("  📋 測試風險控制停止...")
        risk_controller.stop_risk_control()
        
        print("  ✅ 整合流程測試完成")
        return {"整合流程": "SUCCESS"}
        
    except Exception as e:
        print(f"  ❌ 整合流程測試失敗: {e}")
        traceback.print_exc()
        return {"整合流程": f"FAILED: {e}"}


def test_backward_compatibility():
    """測試向後兼容性"""
    print("\n🔄 測試向後兼容性...")
    
    compatibility_results = {}
    
    try:
        # 測試舊的風險管理服務是否仍然可用
        try:
            from src.core.risk_management_service import RiskManagementService
            compatibility_results["舊風險管理服務"] = "SUCCESS"
            print("  ✅ 舊風險管理服務: 仍然可用")
        except ImportError:
            compatibility_results["舊風險管理服務"] = "NOT_FOUND"
            print("  ⚠️ 舊風險管理服務: 未找到（可能已重構）")
        except Exception as e:
            compatibility_results["舊風險管理服務"] = f"FAILED: {e}"
            print(f"  ❌ 舊風險管理服務: 導入失敗 - {e}")
        
        # 測試舊的風險管理模組
        try:
            from src.risk_management import RiskManager
            compatibility_results["舊風險管理模組"] = "SUCCESS"
            print("  ✅ 舊風險管理模組: 仍然可用")
        except ImportError:
            compatibility_results["舊風險管理模組"] = "NOT_FOUND"
            print("  ⚠️ 舊風險管理模組: 未找到（可能已重構）")
        except Exception as e:
            compatibility_results["舊風險管理模組"] = f"FAILED: {e}"
            print(f"  ❌ 舊風險管理模組: 導入失敗 - {e}")
        
    except Exception as e:
        print(f"  ❌ 向後兼容性測試失敗: {e}")
    
    return compatibility_results


def check_file_structure():
    """檢查文件結構"""
    print("\n📁 檢查文件結構...")
    
    import os
    
    expected_files = [
        "src/risk/live/fund_monitor_base.py",
        "src/risk/live/fund_calculator.py", 
        "src/risk/live/fund_monitor.py",
        "src/risk/live/stop_loss_strategies.py",
        "src/risk/live/stop_loss_monitor.py",
        "src/risk/live/dynamic_stop_loss.py",
        "src/risk/live/emergency_actions.py",
        "src/risk/live/emergency_event_manager.py",
        "src/risk/live/emergency_risk_control.py",
        "src/risk/live/unified_risk_controller.py",
    ]
    
    file_results = {}
    
    for file_path in expected_files:
        if os.path.exists(file_path):
            # 檢查文件大小
            size = os.path.getsize(file_path)
            lines = 0
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = len(f.readlines())
            except:
                pass
            
            file_results[file_path] = {
                "exists": True,
                "size": size,
                "lines": lines,
                "status": "OK" if lines <= 300 else "TOO_LARGE"
            }
            
            status_icon = "✅" if lines <= 300 else "⚠️"
            print(f"  {status_icon} {file_path}: {lines} 行")
        else:
            file_results[file_path] = {"exists": False, "status": "MISSING"}
            print(f"  ❌ {file_path}: 文件不存在")
    
    return file_results


def main():
    """主函數"""
    print("🚀 風險控制系統整合驗證開始")
    print("=" * 60)
    
    # 1. 測試模組導入
    import_results = test_module_imports()
    
    # 2. 測試基本功能
    functionality_results = test_basic_functionality(import_results)
    
    # 3. 測試整合流程
    integration_results = test_integration_flow(import_results)
    
    # 4. 測試向後兼容性
    compatibility_results = test_backward_compatibility()
    
    # 5. 檢查文件結構
    file_results = check_file_structure()
    
    # 6. 生成總結報告
    print("\n" + "=" * 60)
    print("📋 驗證總結報告")
    print("=" * 60)
    
    # 模組導入結果
    print("\n📦 模組導入結果:")
    import_success = 0
    import_total = len(import_results)
    for name, result in import_results.items():
        status_icon = "✅" if result["status"] == "SUCCESS" else "❌"
        print(f"  {status_icon} {name}: {result['status']}")
        if result["status"] == "SUCCESS":
            import_success += 1
    
    print(f"\n導入成功率: {import_success}/{import_total} ({import_success/import_total*100:.1f}%)")
    
    # 功能測試結果
    print("\n🧪 功能測試結果:")
    func_success = 0
    func_total = len(functionality_results)
    for name, result in functionality_results.items():
        status_icon = "✅" if result == "SUCCESS" else "❌"
        print(f"  {status_icon} {name}: {result}")
        if result == "SUCCESS":
            func_success += 1
    
    if func_total > 0:
        print(f"\n功能測試成功率: {func_success}/{func_total} ({func_success/func_total*100:.1f}%)")
    
    # 整合測試結果
    print("\n🔄 整合測試結果:")
    for name, result in integration_results.items():
        status_icon = "✅" if result == "SUCCESS" else "❌" if "FAILED" in result else "⚠️"
        print(f"  {status_icon} {name}: {result}")
    
    # 向後兼容性結果
    print("\n🔄 向後兼容性結果:")
    for name, result in compatibility_results.items():
        status_icon = "✅" if result == "SUCCESS" else "⚠️" if result == "NOT_FOUND" else "❌"
        print(f"  {status_icon} {name}: {result}")
    
    # 文件結構結果
    print("\n📁 文件結構檢查:")
    file_ok = sum(1 for r in file_results.values() if r.get("status") == "OK")
    file_total = len(file_results)
    print(f"文件結構合規率: {file_ok}/{file_total} ({file_ok/file_total*100:.1f}%)")
    
    # 總體評估
    overall_success = (
        import_success == import_total and
        func_success == func_total and
        all("SUCCESS" in str(r) for r in integration_results.values()) and
        file_ok >= file_total * 0.9  # 90%文件合規
    )
    
    print("\n" + "=" * 60)
    if overall_success:
        print("🎉 風險控制系統整合驗證通過！系統已準備就緒。")
        return 0
    else:
        print("⚠️ 風險控制系統整合驗證部分失敗，請檢查上述結果。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
