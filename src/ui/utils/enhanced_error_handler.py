#!/usr/bin/env python3
"""
增強版錯誤處理系統
基於現有錯誤處理組件，提供更友好的用戶體驗和自動修復建議
"""

import streamlit as st
import logging
import traceback
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import importlib

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """錯誤嚴重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """錯誤類別"""
    DEPENDENCY = "dependency"
    NETWORK = "network"
    DATA = "data"
    PERMISSION = "permission"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    USER_INPUT = "user_input"
    UNKNOWN = "unknown"

class ErrorSolution:
    """錯誤解決方案"""
    def __init__(self, title: str, description: str, action: Optional[Callable] = None, 
                 command: Optional[str] = None, auto_fix: bool = False):
        self.title = title
        self.description = description
        self.action = action
        self.command = command
        self.auto_fix = auto_fix

class EnhancedErrorHandler:
    """增強版錯誤處理器"""
    
    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
        self.solution_registry = self._initialize_solutions()
    
    def _initialize_error_patterns(self) -> Dict[str, Dict]:
        """初始化錯誤模式匹配"""
        return {
            "ModuleNotFoundError": {
                "category": ErrorCategory.DEPENDENCY,
                "severity": ErrorSeverity.HIGH,
                "keywords": ["No module named", "ModuleNotFoundError"]
            },
            "ImportError": {
                "category": ErrorCategory.DEPENDENCY,
                "severity": ErrorSeverity.HIGH,
                "keywords": ["ImportError", "cannot import"]
            },
            "ConnectionError": {
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.MEDIUM,
                "keywords": ["ConnectionError", "timeout", "network"]
            },
            "PermissionError": {
                "category": ErrorCategory.PERMISSION,
                "severity": ErrorSeverity.HIGH,
                "keywords": ["PermissionError", "Access denied", "permission"]
            },
            "FileNotFoundError": {
                "category": ErrorCategory.CONFIGURATION,
                "severity": ErrorSeverity.MEDIUM,
                "keywords": ["FileNotFoundError", "No such file"]
            },
            "ValueError": {
                "category": ErrorCategory.USER_INPUT,
                "severity": ErrorSeverity.LOW,
                "keywords": ["ValueError", "invalid literal"]
            },
            "KeyError": {
                "category": ErrorCategory.DATA,
                "severity": ErrorSeverity.MEDIUM,
                "keywords": ["KeyError"]
            }
        }
    
    def _initialize_solutions(self) -> Dict[str, List[ErrorSolution]]:
        """初始化解決方案註冊表"""
        return {
            "streamlit": [
                ErrorSolution(
                    "安裝Streamlit",
                    "Streamlit是Web UI框架，系統必需",
                    command="pip install streamlit",
                    auto_fix=True
                )
            ],
            "pandas": [
                ErrorSolution(
                    "安裝Pandas",
                    "Pandas是數據處理核心庫",
                    command="pip install pandas",
                    auto_fix=True
                )
            ],
            "plotly": [
                ErrorSolution(
                    "安裝Plotly",
                    "Plotly用於數據可視化",
                    command="pip install plotly",
                    auto_fix=True
                )
            ],
            "backtrader": [
                ErrorSolution(
                    "安裝Backtrader",
                    "Backtrader是回測引擎",
                    command="pip install backtrader",
                    auto_fix=True
                )
            ],
            "yfinance": [
                ErrorSolution(
                    "安裝YFinance",
                    "YFinance用於獲取股價數據",
                    command="pip install yfinance",
                    auto_fix=True
                )
            ],
            "network": [
                ErrorSolution(
                    "檢查網絡連接",
                    "確保網絡連接正常，可以訪問數據源",
                    auto_fix=False
                ),
                ErrorSolution(
                    "重試操作",
                    "網絡問題通常是暫時的，請稍後重試",
                    auto_fix=False
                )
            ],
            "permission": [
                ErrorSolution(
                    "以管理員身份運行",
                    "某些操作需要管理員權限",
                    auto_fix=False
                ),
                ErrorSolution(
                    "檢查文件權限",
                    "確保對相關文件和目錄有讀寫權限",
                    auto_fix=False
                )
            ],
            "configuration": [
                ErrorSolution(
                    "檢查配置文件",
                    "確保配置文件存在且格式正確",
                    auto_fix=False
                ),
                ErrorSolution(
                    "重置配置",
                    "恢復默認配置設置",
                    auto_fix=False
                )
            ]
        }
    
    def analyze_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """分析錯誤並提供解決方案"""
        error_str = str(error)
        error_type = type(error).__name__
        
        # 匹配錯誤模式
        category = ErrorCategory.UNKNOWN
        severity = ErrorSeverity.MEDIUM
        
        for pattern_name, pattern_info in self.error_patterns.items():
            if (error_type == pattern_name or 
                any(keyword in error_str for keyword in pattern_info["keywords"])):
                category = pattern_info["category"]
                severity = pattern_info["severity"]
                break
        
        # 提取模組名稱（用於依賴錯誤）
        module_name = None
        if "No module named" in error_str:
            module_name = error_str.split("No module named '")[1].split("'")[0]
        
        # 生成用戶友好的消息
        user_message = self._generate_user_message(error, category, module_name)
        
        # 獲取解決方案
        solutions = self._get_solutions(category, module_name, error_str)
        
        return {
            "error_type": error_type,
            "category": category.value,
            "severity": severity.value,
            "original_message": error_str,
            "user_message": user_message,
            "solutions": solutions,
            "module_name": module_name,
            "context": context or {},
            "timestamp": datetime.now()
        }
    
    def _generate_user_message(self, error: Exception, category: ErrorCategory, 
                             module_name: Optional[str] = None) -> str:
        """生成用戶友好的錯誤消息"""
        if category == ErrorCategory.DEPENDENCY:
            if module_name:
                return f"缺少必需的程式庫 '{module_name}'，系統無法正常運行"
            return "缺少必需的程式庫，請安裝相關依賴"
        
        elif category == ErrorCategory.NETWORK:
            return "網絡連接問題，無法獲取數據。請檢查網絡連接後重試"
        
        elif category == ErrorCategory.PERMISSION:
            return "權限不足，無法執行此操作。請檢查文件權限或以管理員身份運行"
        
        elif category == ErrorCategory.CONFIGURATION:
            return "配置文件問題，請檢查相關設置"
        
        elif category == ErrorCategory.USER_INPUT:
            return "輸入數據格式不正確，請檢查輸入內容"
        
        elif category == ErrorCategory.DATA:
            return "數據處理錯誤，請檢查數據格式和完整性"
        
        else:
            return f"系統遇到未知錯誤：{str(error)}"
    
    def _get_solutions(self, category: ErrorCategory, module_name: Optional[str], 
                      error_str: str) -> List[ErrorSolution]:
        """獲取錯誤解決方案"""
        solutions = []
        
        # 針對特定模組的解決方案
        if module_name and module_name in self.solution_registry:
            solutions.extend(self.solution_registry[module_name])
        
        # 針對錯誤類別的通用解決方案
        category_key = category.value
        if category_key in self.solution_registry:
            solutions.extend(self.solution_registry[category_key])
        
        # 如果沒有找到特定解決方案，提供通用建議
        if not solutions:
            solutions.append(ErrorSolution(
                "聯繫技術支援",
                "此錯誤需要進一步診斷，請聯繫技術支援團隊",
                auto_fix=False
            ))
        
        return solutions
    
    def display_error(self, error_info: Dict[str, Any]):
        """顯示錯誤信息給用戶"""
        severity = error_info["severity"]
        user_message = error_info["user_message"]
        solutions = error_info["solutions"]
        
        # 根據嚴重程度選擇顯示方式
        if severity == "critical":
            st.error(f"🚨 嚴重錯誤: {user_message}")
        elif severity == "high":
            st.error(f"❌ 錯誤: {user_message}")
        elif severity == "medium":
            st.warning(f"⚠️ 警告: {user_message}")
        else:
            st.info(f"ℹ️ 提示: {user_message}")
        
        # 顯示解決方案
        if solutions:
            with st.expander("💡 解決方案", expanded=True):
                for i, solution in enumerate(solutions, 1):
                    st.write(f"**方案 {i}: {solution.title}**")
                    st.write(solution.description)
                    
                    if solution.command:
                        st.code(solution.command)
                        
                        if solution.auto_fix:
                            if st.button(f"🔧 自動修復 - {solution.title}", key=f"fix_{i}"):
                                self._execute_auto_fix(solution)
                    
                    st.write("---")
        
        # 顯示技術詳情（可摺疊）
        with st.expander("🔧 技術詳情"):
            st.write(f"**錯誤類型**: {error_info['error_type']}")
            st.write(f"**錯誤類別**: {error_info['category']}")
            st.write(f"**發生時間**: {error_info['timestamp']}")
            st.code(error_info['original_message'])
    
    def _execute_auto_fix(self, solution: ErrorSolution):
        """執行自動修復"""
        if solution.command and solution.command.startswith("pip install"):
            st.info(f"正在執行: {solution.command}")
            st.info("請在終端中運行上述命令，然後重新啟動系統")
        else:
            st.warning("此修復需要手動執行")

# 全局錯誤處理器實例
enhanced_error_handler = EnhancedErrorHandler()

def handle_error_with_ui(func: Callable) -> Callable:
    """裝飾器：為函數添加增強的錯誤處理"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_info = enhanced_error_handler.analyze_error(e, {
                "function": func.__name__,
                "args": str(args)[:100],
                "kwargs": str(kwargs)[:100]
            })
            enhanced_error_handler.display_error(error_info)
            return None
    return wrapper

def show_error_with_solutions(error: Exception, context: Dict[str, Any] = None):
    """顯示錯誤和解決方案"""
    error_info = enhanced_error_handler.analyze_error(error, context)
    enhanced_error_handler.display_error(error_info)
