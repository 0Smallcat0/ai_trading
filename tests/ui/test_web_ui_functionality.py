#!/usr/bin/env python3
"""
Web UI 功能測試腳本

測試所有Web UI頁面模組的可用性和功能完整性
"""

import os
import sys
import importlib.util
import logging

# 添加專案根目錄到Python路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_page_module(page_name: str, module_path: str) -> dict:
    """測試單個頁面模組"""
    result = {
        "name": page_name,
        "module_path": module_path,
        "importable": False,
        "has_show_function": False,
        "error": None
    }
    
    try:
        # 測試模組是否可導入
        spec = importlib.util.find_spec(module_path)
        if spec is None:
            result["error"] = f"模組不存在: {module_path}"
            return result
        
        module = importlib.import_module(module_path)
        result["importable"] = True
        
        # 測試是否有show函數
        if hasattr(module, 'show'):
            result["has_show_function"] = True
        else:
            result["error"] = "缺少show函數"
        
    except Exception as e:
        result["error"] = str(e)
    
    return result

def test_core_modules() -> dict:
    """測試核心模組"""
    core_modules = {
        "數據獲取": "src.core.data_ingest",
        "回測引擎": "src.core.backtest",
        "投資組合": "src.core.portfolio", 
        "風險控制": "src.core.risk_control",
        "策略管理": "src.strategy.utils",
        "執行引擎": "src.execution",
        "AI模型": "src.models",
        "強化學習": "src.reinforcement_learning"
    }
    
    results = {}
    
    for name, module_path in core_modules.items():
        try:
            spec = importlib.util.find_spec(module_path)
            if spec is not None:
                module = importlib.import_module(module_path)
                results[name] = "✅ 可用"
            else:
                results[name] = "❌ 不存在"
        except Exception as e:
            results[name] = f"❌ 錯誤: {str(e)[:50]}..."
    
    return results

def test_ui_pages() -> list:
    """測試所有UI頁面"""
    pages_to_test = [
        ("系統儀表板", "src.ui.pages.realtime_dashboard"),
        ("數據管理", "src.ui.pages.data_management"),
        ("特徵工程", "src.ui.pages.feature_engineering"),
        ("策略管理", "src.ui.pages.strategy_management"),
        ("AI模型", "src.ui.pages.ai_models"),
        ("回測分析", "src.ui.pages.backtest_enhanced"),
        ("投資組合", "src.ui.pages.portfolio_management"),
        ("風險控制", "src.ui.pages.risk_management"),
        ("交易執行", "src.ui.pages.trade_execution"),
        ("系統監控", "src.ui.pages.system_monitoring"),
        ("報告分析", "src.ui.pages.reports"),
        ("強化學習策略", "src.ui.pages.rl_strategy_management"),
        ("多代理儀表板", "src.ui.pages.multi_agent_dashboard"),
        ("知識庫", "src.ui.pages.knowledge_base"),
        ("學習中心", "src.ui.pages.learning_center"),
        ("市場監控", "src.ui.pages.market_watch"),
        ("互動圖表", "src.ui.pages.interactive_charts"),
        ("文本分析", "src.ui.pages.text_analysis"),
        ("LLM決策", "src.ui.pages.llm_decision"),
        ("新手中心", "src.ui.pages.beginner_hub"),
        ("安全管理", "src.ui.pages.security_management"),
        ("雙因子認證", "src.ui.pages.two_factor_management")
    ]
    
    results = []
    
    for page_name, module_path in pages_to_test:
        result = test_page_module(page_name, module_path)
        results.append(result)
    
    return results

def test_api_endpoints() -> dict:
    """測試API端點"""
    api_modules = {
        "數據管理API": "src.api.routers.data_management",
        "策略管理API": "src.api.routers.strategy_management", 
        "AI模型API": "src.api.routers.ai_models",
        "回測API": "src.api.routers.backtest",
        "投資組合API": "src.api.routers.portfolio",
        "風險管理API": "src.api.routers.risk_management",
        "交易API": "src.api.routers.trading",
        "監控API": "src.api.routers.monitoring",
        "報告API": "src.api.routers.reports",
        "認證API": "src.api.routers.auth",
        "系統API": "src.api.routers.system"
    }
    
    results = {}
    
    for name, module_path in api_modules.items():
        try:
            spec = importlib.util.find_spec(module_path)
            if spec is not None:
                results[name] = "✅ 可用"
            else:
                results[name] = "❌ 不存在"
        except Exception as e:
            results[name] = f"❌ 錯誤: {str(e)[:50]}..."
    
    return results

def generate_functionality_report():
    """生成功能完整性報告"""
    print("🚀 AI交易系統功能完整性測試")
    print("=" * 60)
    
    # 測試核心模組
    print("\n📦 核心模組測試:")
    core_results = test_core_modules()
    for name, status in core_results.items():
        print(f"  {status} {name}")
    
    # 測試UI頁面
    print("\n🌐 Web UI 頁面測試:")
    ui_results = test_ui_pages()
    
    available_pages = 0
    total_pages = len(ui_results)
    
    for result in ui_results:
        if result["importable"] and result["has_show_function"]:
            status = "✅ 完整功能"
            available_pages += 1
        elif result["importable"]:
            status = "⚠️ 部分功能"
        else:
            status = "❌ 不可用"
        
        print(f"  {status} {result['name']}")
        if result["error"]:
            print(f"    錯誤: {result['error']}")
    
    # 測試API端點
    print("\n🔌 API 端點測試:")
    api_results = test_api_endpoints()
    for name, status in api_results.items():
        print(f"  {status} {name}")
    
    # 統計摘要
    print("\n📊 功能完整性摘要:")
    print(f"  核心模組: {sum(1 for s in core_results.values() if '✅' in s)}/{len(core_results)} 可用")
    print(f"  UI頁面: {available_pages}/{total_pages} 完整功能")
    print(f"  API端點: {sum(1 for s in api_results.values() if '✅' in s)}/{len(api_results)} 可用")
    
    # 計算總體完成度
    core_completion = sum(1 for s in core_results.values() if '✅' in s) / len(core_results)
    ui_completion = available_pages / total_pages
    api_completion = sum(1 for s in api_results.values() if '✅' in s) / len(api_results)
    
    overall_completion = (core_completion + ui_completion + api_completion) / 3
    
    print(f"\n🎯 總體完成度: {overall_completion:.1%}")
    
    if overall_completion >= 0.8:
        print("🎉 系統功能完整性良好！")
    elif overall_completion >= 0.6:
        print("⚠️ 系統功能基本完整，部分功能需要完善")
    else:
        print("❌ 系統功能不完整，需要大量開發工作")
    
    return {
        "core_results": core_results,
        "ui_results": ui_results,
        "api_results": api_results,
        "overall_completion": overall_completion
    }

def main():
    """主函數"""
    try:
        report = generate_functionality_report()
        return 0 if report["overall_completion"] >= 0.6 else 1
    except Exception as e:
        logger.error(f"測試執行失敗: {e}")
        print(f"❌ 測試執行失敗: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
