#!/usr/bin/env python3
"""
功能狀態指示器組件
為每個功能模組添加實時可用性狀態顯示，包括健康度指標、問題診斷和修復建議
"""

import streamlit as st
import time
import importlib
import sys
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

# 添加項目根目錄到路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

class FunctionStatus(Enum):
    """功能狀態枚舉"""
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNAVAILABLE = "unavailable"
    LOADING = "loading"

class FunctionStatusIndicator:
    """功能狀態指示器"""
    
    def __init__(self):
        """初始化狀態指示器"""
        self.status_cache = {}
        self.last_check_time = {}
        self.cache_duration = 30  # 緩存30秒
        
        # 功能模組配置
        self.function_modules = {
            "data_management": {
                "name": "數據管理",
                "module_path": "src.core.data_management_service",
                "service_class": "DataManagementService",
                "icon": "📊",
                "description": "股價數據獲取、存儲和管理",
                "dependencies": ["pandas", "yfinance", "requests"]
            },
            "backtest_service": {
                "name": "回測服務",
                "module_path": "src.core.backtest_service",
                "service_class": "BacktestService",
                "icon": "📈",
                "description": "策略歷史數據回測分析",
                "dependencies": ["pandas", "numpy", "backtrader"]
            },
            "portfolio_service": {
                "name": "投資組合管理",
                "module_path": "src.core.portfolio_service",
                "service_class": "PortfolioService",
                "icon": "💼",
                "description": "投資組合優化和風險管理",
                "dependencies": ["pandas", "numpy", "scipy"]
            },
            "strategy_management": {
                "name": "策略管理",
                "module_path": "src.core.strategy_management_service",
                "service_class": "StrategyManagementService",
                "icon": "🎯",
                "description": "交易策略創建和管理",
                "dependencies": ["pandas", "numpy"]
            },
            "ai_model_service": {
                "name": "AI模型服務",
                "module_path": "src.core.ai_model_service",
                "service_class": "AIModelService",
                "icon": "🤖",
                "description": "機器學習模型訓練和預測",
                "dependencies": ["pandas", "numpy", "scikit-learn"]
            },
            "risk_management": {
                "name": "風險管理",
                "module_path": "src.core.risk_management_service",
                "service_class": "RiskManagementService",
                "icon": "🛡️",
                "description": "投資風險評估和控制",
                "dependencies": ["pandas", "numpy"]
            },
            "system_monitoring": {
                "name": "系統監控",
                "module_path": "src.core.system_monitoring_service",
                "service_class": "SystemMonitoringService",
                "icon": "📡",
                "description": "系統性能和健康度監控",
                "dependencies": ["psutil"]
            },
            "data_sources": {
                "name": "數據源管理",
                "module_path": "src.data_sources.unified_data_manager",
                "service_class": "UnifiedDataManager",
                "icon": "🔗",
                "description": "多數據源統一管理",
                "dependencies": ["requests", "yfinance"]
            }
        }
    
    def check_function_status(self, function_id: str) -> Dict[str, Any]:
        """檢查功能狀態"""
        # 檢查緩存
        if self._is_cache_valid(function_id):
            return self.status_cache[function_id]
        
        if function_id not in self.function_modules:
            return {
                "status": FunctionStatus.UNAVAILABLE,
                "message": "未知功能模組",
                "health_score": 0,
                "issues": ["功能模組不存在"],
                "suggestions": ["檢查功能模組配置"]
            }
        
        function_config = self.function_modules[function_id]
        status_result = {
            "function_id": function_id,
            "name": function_config["name"],
            "icon": function_config["icon"],
            "description": function_config["description"],
            "timestamp": datetime.now(),
            "issues": [],
            "suggestions": [],
            "details": {}
        }
        
        try:
            # 檢查依賴項
            dependency_status = self._check_dependencies(function_config["dependencies"])
            status_result["details"]["dependencies"] = dependency_status
            
            # 檢查模組導入
            module_status = self._check_module_import(function_config)
            status_result["details"]["module"] = module_status
            
            # 檢查服務初始化
            service_status = self._check_service_initialization(function_config)
            status_result["details"]["service"] = service_status
            
            # 計算整體健康度
            health_score = self._calculate_health_score(dependency_status, module_status, service_status)
            status_result["health_score"] = health_score
            
            # 確定狀態
            if health_score >= 90:
                status_result["status"] = FunctionStatus.HEALTHY
                status_result["message"] = "功能正常運行"
            elif health_score >= 70:
                status_result["status"] = FunctionStatus.WARNING
                status_result["message"] = "功能可用但有警告"
            elif health_score >= 30:
                status_result["status"] = FunctionStatus.ERROR
                status_result["message"] = "功能存在錯誤"
            else:
                status_result["status"] = FunctionStatus.UNAVAILABLE
                status_result["message"] = "功能不可用"
            
            # 收集問題和建議
            self._collect_issues_and_suggestions(status_result)
            
        except Exception as e:
            status_result.update({
                "status": FunctionStatus.ERROR,
                "message": f"狀態檢查失敗: {str(e)}",
                "health_score": 0,
                "issues": [f"狀態檢查異常: {str(e)}"],
                "suggestions": ["重新啟動系統", "檢查系統日誌"]
            })
        
        # 更新緩存
        self.status_cache[function_id] = status_result
        self.last_check_time[function_id] = datetime.now()
        
        return status_result
    
    def _is_cache_valid(self, function_id: str) -> bool:
        """檢查緩存是否有效"""
        if function_id not in self.status_cache or function_id not in self.last_check_time:
            return False
        
        elapsed = (datetime.now() - self.last_check_time[function_id]).total_seconds()
        return elapsed < self.cache_duration
    
    def _check_dependencies(self, dependencies: List[str]) -> Dict[str, Any]:
        """檢查依賴項狀態"""
        result = {
            "total": len(dependencies),
            "available": 0,
            "missing": [],
            "versions": {}
        }
        
        for dep in dependencies:
            try:
                module = importlib.import_module(dep)
                result["available"] += 1
                result["versions"][dep] = getattr(module, '__version__', 'unknown')
            except ImportError:
                result["missing"].append(dep)
        
        result["success_rate"] = result["available"] / result["total"] if result["total"] > 0 else 0
        return result
    
    def _check_module_import(self, function_config: Dict[str, Any]) -> Dict[str, Any]:
        """檢查模組導入狀態"""
        try:
            module = importlib.import_module(function_config["module_path"])
            return {
                "importable": True,
                "module_path": function_config["module_path"],
                "file_path": getattr(module, '__file__', 'unknown')
            }
        except ImportError as e:
            return {
                "importable": False,
                "error": str(e),
                "module_path": function_config["module_path"]
            }
    
    def _check_service_initialization(self, function_config: Dict[str, Any]) -> Dict[str, Any]:
        """檢查服務初始化狀態"""
        try:
            module = importlib.import_module(function_config["module_path"])
            service_class = getattr(module, function_config["service_class"], None)
            
            if service_class is None:
                return {
                    "initializable": False,
                    "error": f"服務類 {function_config['service_class']} 不存在"
                }
            
            # 嘗試初始化（簡單測試）
            service_instance = service_class()
            
            return {
                "initializable": True,
                "service_class": function_config["service_class"],
                "instance_type": type(service_instance).__name__
            }
            
        except Exception as e:
            return {
                "initializable": False,
                "error": str(e)
            }
    
    def _calculate_health_score(self, dependency_status: Dict, module_status: Dict, service_status: Dict) -> int:
        """計算健康度評分"""
        score = 0
        
        # 依賴項評分 (40%)
        if dependency_status["success_rate"] == 1.0:
            score += 40
        elif dependency_status["success_rate"] >= 0.8:
            score += 30
        elif dependency_status["success_rate"] >= 0.5:
            score += 20
        else:
            score += 10
        
        # 模組導入評分 (30%)
        if module_status["importable"]:
            score += 30
        
        # 服務初始化評分 (30%)
        if service_status["initializable"]:
            score += 30
        
        return min(score, 100)
    
    def _collect_issues_and_suggestions(self, status_result: Dict[str, Any]):
        """收集問題和建議"""
        details = status_result["details"]
        
        # 依賴項問題
        if details["dependencies"]["missing"]:
            for dep in details["dependencies"]["missing"]:
                status_result["issues"].append(f"缺少依賴項: {dep}")
                status_result["suggestions"].append(f"安裝依賴項: pip install {dep}")
        
        # 模組導入問題
        if not details["module"]["importable"]:
            status_result["issues"].append(f"模組導入失敗: {details['module']['error']}")
            status_result["suggestions"].append("檢查模組路徑和文件完整性")
        
        # 服務初始化問題
        if not details["service"]["initializable"]:
            status_result["issues"].append(f"服務初始化失敗: {details['service']['error']}")
            status_result["suggestions"].append("檢查服務配置和依賴項")
    
    def get_all_function_status(self) -> Dict[str, Dict[str, Any]]:
        """獲取所有功能的狀態"""
        all_status = {}
        for function_id in self.function_modules.keys():
            all_status[function_id] = self.check_function_status(function_id)
        return all_status
    
    def get_system_overview(self) -> Dict[str, Any]:
        """獲取系統概覽"""
        all_status = self.get_all_function_status()
        
        status_counts = {
            FunctionStatus.HEALTHY: 0,
            FunctionStatus.WARNING: 0,
            FunctionStatus.ERROR: 0,
            FunctionStatus.UNAVAILABLE: 0
        }
        
        total_health_score = 0
        
        for status_info in all_status.values():
            status_counts[status_info["status"]] += 1
            total_health_score += status_info["health_score"]
        
        total_functions = len(all_status)
        average_health_score = total_health_score / total_functions if total_functions > 0 else 0
        
        return {
            "total_functions": total_functions,
            "status_counts": {k.value: v for k, v in status_counts.items()},
            "average_health_score": average_health_score,
            "healthy_percentage": (status_counts[FunctionStatus.HEALTHY] / total_functions * 100) if total_functions > 0 else 0,
            "timestamp": datetime.now()
        }

def show_function_status_indicator(function_id: str, indicator: FunctionStatusIndicator = None) -> None:
    """顯示單個功能的狀態指示器"""
    if indicator is None:
        indicator = FunctionStatusIndicator()
    
    status_info = indicator.check_function_status(function_id)
    
    # 狀態圖標和顏色
    status_icons = {
        FunctionStatus.HEALTHY: "🟢",
        FunctionStatus.WARNING: "🟡",
        FunctionStatus.ERROR: "🔴",
        FunctionStatus.UNAVAILABLE: "⚫",
        FunctionStatus.LOADING: "🔵"
    }
    
    status_colors = {
        FunctionStatus.HEALTHY: "#28a745",
        FunctionStatus.WARNING: "#ffc107",
        FunctionStatus.ERROR: "#dc3545",
        FunctionStatus.UNAVAILABLE: "#6c757d",
        FunctionStatus.LOADING: "#007bff"
    }
    
    status = status_info["status"]
    icon = status_icons.get(status, "❓")
    color = status_colors.get(status, "#6c757d")
    
    # 顯示狀態
    col1, col2, col3 = st.columns([1, 4, 2])
    
    with col1:
        st.markdown(f"<h3 style='color: {color};'>{icon}</h3>", unsafe_allow_html=True)
    
    with col2:
        st.write(f"**{status_info['icon']} {status_info['name']}**")
        st.caption(status_info["description"])
    
    with col3:
        health_score = status_info["health_score"]
        st.metric("健康度", f"{health_score}%")
    
    # 詳細信息
    if status != FunctionStatus.HEALTHY:
        with st.expander(f"🔍 {status_info['name']} 詳細信息"):
            st.write(f"**狀態**: {status_info['message']}")
            
            if status_info["issues"]:
                st.write("**問題**:")
                for issue in status_info["issues"]:
                    st.write(f"• {issue}")
            
            if status_info["suggestions"]:
                st.write("**建議**:")
                for suggestion in status_info["suggestions"]:
                    st.write(f"• {suggestion}")

def show_system_status_dashboard():
    """顯示系統狀態儀表板"""
    st.subheader("🎛️ 系統功能狀態儀表板")
    
    indicator = FunctionStatusIndicator()
    overview = indicator.get_system_overview()
    
    # 系統概覽
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("總功能數", overview["total_functions"])
    
    with col2:
        healthy_count = overview["status_counts"]["healthy"]
        st.metric("健康功能", healthy_count, delta=f"{overview['healthy_percentage']:.1f}%")
    
    with col3:
        warning_count = overview["status_counts"]["warning"]
        error_count = overview["status_counts"]["error"]
        problem_count = warning_count + error_count
        st.metric("問題功能", problem_count)
    
    with col4:
        st.metric("平均健康度", f"{overview['average_health_score']:.1f}%")
    
    # 功能狀態列表
    st.markdown("### 📋 功能狀態詳情")
    
    all_status = indicator.get_all_function_status()
    
    # 按狀態分組顯示
    healthy_functions = []
    warning_functions = []
    error_functions = []
    unavailable_functions = []
    
    for func_id, status_info in all_status.items():
        if status_info["status"] == FunctionStatus.HEALTHY:
            healthy_functions.append((func_id, status_info))
        elif status_info["status"] == FunctionStatus.WARNING:
            warning_functions.append((func_id, status_info))
        elif status_info["status"] == FunctionStatus.ERROR:
            error_functions.append((func_id, status_info))
        else:
            unavailable_functions.append((func_id, status_info))
    
    # 優先顯示有問題的功能
    for func_id, status_info in error_functions + unavailable_functions + warning_functions:
        show_function_status_indicator(func_id, indicator)
        st.markdown("---")
    
    # 最後顯示健康的功能
    if healthy_functions:
        with st.expander(f"✅ 健康功能 ({len(healthy_functions)}個)", expanded=False):
            for func_id, status_info in healthy_functions:
                col1, col2, col3 = st.columns([1, 4, 2])
                with col1:
                    st.write("🟢")
                with col2:
                    st.write(f"**{status_info['icon']} {status_info['name']}**")
                with col3:
                    st.write(f"{status_info['health_score']}%")
    
    # 刷新按鈕
    if st.button("🔄 刷新狀態", type="secondary"):
        # 清除緩存
        indicator.status_cache.clear()
        indicator.last_check_time.clear()
        st.rerun()

if __name__ == "__main__":
    show_system_status_dashboard()
