#!/usr/bin/env python3
"""
增強版系統狀態檢查頁面
基於現有監控服務，提供實時模組狀態監控和健康度評估
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import importlib
import sys
import os
from typing import Dict, Any, List

# 添加項目根目錄到路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

def check_module_status(module_name: str) -> Dict[str, Any]:
    """檢查模組狀態"""
    try:
        module = importlib.import_module(module_name)
        return {
            "status": "healthy",
            "message": "模組正常運行",
            "details": {
                "path": getattr(module, '__file__', 'N/A'),
                "version": getattr(module, '__version__', 'N/A')
            }
        }
    except ImportError as e:
        return {
            "status": "error",
            "message": f"模組導入失敗: {str(e)}",
            "details": {"error": str(e)}
        }
    except Exception as e:
        return {
            "status": "warning",
            "message": f"模組檢查異常: {str(e)}",
            "details": {"error": str(e)}
        }

def get_system_health_score(module_results: Dict[str, Dict]) -> float:
    """計算系統健康度評分"""
    if not module_results:
        return 0.0
    
    total_modules = len(module_results)
    healthy_modules = sum(1 for result in module_results.values() if result["status"] == "healthy")
    warning_modules = sum(1 for result in module_results.values() if result["status"] == "warning")
    
    # 健康模組得滿分，警告模組得一半分，錯誤模組不得分
    score = (healthy_modules + warning_modules * 0.5) / total_modules * 100
    return round(score, 1)

def show_system_overview():
    """顯示系統概覽"""
    st.subheader("🎯 系統概覽")
    
    # 核心模組列表
    core_modules = {
        "數據管理": "src.core.data_management_service",
        "回測服務": "src.core.backtest_service", 
        "投資組合": "src.core.portfolio_service",
        "風險管理": "src.core.risk_management_service",
        "策略管理": "src.core.strategy_management_service",
        "系統監控": "src.core.system_monitoring_service",
        "數據源管理": "src.data_sources.unified_data_manager",
        "Web UI": "src.ui.web_ui_production"
    }
    
    # 檢查所有模組狀態
    module_results = {}
    for name, module_path in core_modules.items():
        module_results[name] = check_module_status(module_path)
    
    # 計算健康度
    health_score = get_system_health_score(module_results)
    
    # 顯示總體狀態
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        healthy_count = sum(1 for r in module_results.values() if r["status"] == "healthy")
        st.metric("健康模組", f"{healthy_count}/{len(module_results)}")
    
    with col2:
        warning_count = sum(1 for r in module_results.values() if r["status"] == "warning")
        st.metric("警告模組", warning_count)
    
    with col3:
        error_count = sum(1 for r in module_results.values() if r["status"] == "error")
        st.metric("錯誤模組", error_count)
    
    with col4:
        health_color = "🟢" if health_score >= 80 else "🟡" if health_score >= 60 else "🔴"
        st.metric("系統健康度", f"{health_color} {health_score}%")
    
    return module_results, health_score

def show_module_details(module_results: Dict[str, Dict]):
    """顯示模組詳細狀態"""
    st.subheader("📋 模組狀態詳情")
    
    # 創建狀態表格
    status_data = []
    for name, result in module_results.items():
        status_icon = {
            "healthy": "✅",
            "warning": "⚠️", 
            "error": "❌"
        }.get(result["status"], "❓")
        
        status_data.append({
            "模組名稱": name,
            "狀態": f"{status_icon} {result['status'].upper()}",
            "消息": result["message"],
            "路徑": result["details"].get("path", "N/A")
        })
    
    df = pd.DataFrame(status_data)
    st.dataframe(df, use_container_width=True)
    
    # 顯示問題模組的詳細信息
    problem_modules = {name: result for name, result in module_results.items() 
                      if result["status"] in ["warning", "error"]}
    
    if problem_modules:
        st.subheader("🔧 需要注意的問題")
        
        for name, result in problem_modules.items():
            with st.expander(f"{name} - {result['status'].upper()}"):
                st.write(f"**消息**: {result['message']}")
                if "error" in result["details"]:
                    st.code(result["details"]["error"])
                
                # 提供解決建議
                if result["status"] == "error":
                    st.info("💡 **解決建議**: 檢查模組是否正確安裝，或聯繫技術支援")
                elif result["status"] == "warning":
                    st.warning("⚠️ **注意**: 模組可能存在潛在問題，建議進一步檢查")

def show_dependency_check():
    """顯示依賴檢查"""
    st.subheader("📦 依賴包檢查")
    
    # 關鍵依賴列表
    dependencies = {
        "streamlit": "Web UI框架",
        "pandas": "數據處理",
        "numpy": "數值計算",
        "plotly": "數據可視化",
        "yfinance": "Yahoo Finance數據源",
        "requests": "HTTP請求",
        "backtrader": "回測引擎"
    }
    
    dependency_results = {}
    for package, description in dependencies.items():
        try:
            importlib.import_module(package)
            dependency_results[package] = {
                "status": "installed",
                "description": description
            }
        except ImportError:
            dependency_results[package] = {
                "status": "missing",
                "description": description
            }
    
    # 顯示依賴狀態
    dep_data = []
    for package, result in dependency_results.items():
        status_icon = "✅" if result["status"] == "installed" else "❌"
        dep_data.append({
            "依賴包": package,
            "狀態": f"{status_icon} {result['status'].upper()}",
            "描述": result["description"]
        })
    
    df = pd.DataFrame(dep_data)
    st.dataframe(df, use_container_width=True)
    
    # 顯示缺失依賴的安裝命令
    missing_deps = [pkg for pkg, result in dependency_results.items() 
                   if result["status"] == "missing"]
    
    if missing_deps:
        st.warning(f"發現 {len(missing_deps)} 個缺失的依賴包")
        st.code(f"pip install {' '.join(missing_deps)}")

def show_performance_metrics():
    """顯示性能指標"""
    st.subheader("⚡ 性能指標")
    
    # 模擬性能數據（實際應用中應該從監控服務獲取）
    import psutil
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        cpu_percent = psutil.cpu_percent(interval=1)
        st.metric("CPU使用率", f"{cpu_percent}%")
    
    with col2:
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        st.metric("內存使用率", f"{memory_percent}%")
    
    with col3:
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        st.metric("磁盤使用率", f"{disk_percent:.1f}%")

def show_quick_actions():
    """顯示快速操作"""
    st.subheader("⚡ 快速操作")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 重新檢查狀態", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("📦 安裝缺失依賴", use_container_width=True):
            st.info("請在終端運行: `pip install -r requirements.txt`")
    
    with col3:
        if st.button("📊 查看詳細日誌", use_container_width=True):
            st.info("日誌文件位於 logs/ 目錄")

def show():
    """主顯示函數"""
    st.title("🔍 系統狀態監控")
    
    # 添加自動刷新選項
    auto_refresh = st.checkbox("🔄 自動刷新 (30秒)", value=False)
    
    if auto_refresh:
        # 使用 st.empty() 創建可更新的容器
        placeholder = st.empty()
        
        # 自動刷新邏輯
        if "last_refresh" not in st.session_state:
            st.session_state.last_refresh = time.time()
        
        if time.time() - st.session_state.last_refresh > 30:
            st.session_state.last_refresh = time.time()
            st.rerun()
    
    # 顯示各個部分
    module_results, health_score = show_system_overview()
    
    st.markdown("---")
    show_module_details(module_results)
    
    st.markdown("---")
    show_dependency_check()
    
    st.markdown("---")
    show_performance_metrics()
    
    st.markdown("---")
    show_quick_actions()
    
    # 顯示最後更新時間
    st.caption(f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    show()
