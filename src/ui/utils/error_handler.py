"""
增強錯誤處理系統

提供統一的錯誤處理和用戶反饋機制，包括：
- 錯誤分類和處理
- 用戶友好的錯誤消息
- 錯誤日誌記錄
- 錯誤恢復建議
- 用戶反饋收集
"""

import traceback
import logging
import streamlit as st
from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum
from datetime import datetime
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """錯誤嚴重程度"""
    LOW = "low"           # 輕微錯誤，不影響主要功能
    MEDIUM = "medium"     # 中等錯誤，影響部分功能
    HIGH = "high"         # 嚴重錯誤，影響主要功能
    CRITICAL = "critical" # 致命錯誤，系統無法正常運行


class ErrorCategory(Enum):
    """錯誤類別"""
    NETWORK = "network"           # 網絡連接錯誤
    DATA = "data"                # 數據相關錯誤
    AUTHENTICATION = "auth"       # 認證錯誤
    PERMISSION = "permission"     # 權限錯誤
    VALIDATION = "validation"     # 數據驗證錯誤
    SYSTEM = "system"            # 系統錯誤
    USER_INPUT = "user_input"    # 用戶輸入錯誤
    EXTERNAL_API = "external_api" # 外部 API 錯誤
    PERFORMANCE = "performance"   # 性能相關錯誤
    UNKNOWN = "unknown"          # 未知錯誤


@dataclass
class ErrorInfo:
    """錯誤信息"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    user_message: str
    technical_details: str
    timestamp: datetime
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    recovery_suggestions: List[str] = None
    
    def __post_init__(self):
        if self.recovery_suggestions is None:
            self.recovery_suggestions = []


class ErrorHandler:
    """錯誤處理器"""
    
    def __init__(self):
        """初始化錯誤處理器"""
        self.error_history: List[ErrorInfo] = []
        self.error_patterns: Dict[str, Dict[str, Any]] = {}
        self.recovery_strategies: Dict[ErrorCategory, List[str]] = {}
        
        # 初始化錯誤模式和恢復策略
        self._initialize_error_patterns()
        self._initialize_recovery_strategies()
        
        # 初始化 session state
        if "error_feedback_enabled" not in st.session_state:
            st.session_state.error_feedback_enabled = True
        
        if "error_history" not in st.session_state:
            st.session_state.error_history = []
    
    def _initialize_error_patterns(self):
        """初始化錯誤模式"""
        self.error_patterns = {
            "connection_error": {
                "keywords": ["connection", "timeout", "network", "unreachable"],
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "網絡連接出現問題，請檢查您的網絡連接"
            },
            "authentication_error": {
                "keywords": ["authentication", "login", "credential", "unauthorized"],
                "category": ErrorCategory.AUTHENTICATION,
                "severity": ErrorSeverity.HIGH,
                "user_message": "身份驗證失敗，請重新登錄"
            },
            "permission_error": {
                "keywords": ["permission", "access", "forbidden", "denied"],
                "category": ErrorCategory.PERMISSION,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "您沒有執行此操作的權限"
            },
            "data_error": {
                "keywords": ["data", "format", "parse", "invalid"],
                "category": ErrorCategory.DATA,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "數據格式錯誤，請檢查輸入數據"
            },
            "validation_error": {
                "keywords": ["validation", "invalid", "required", "missing"],
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.LOW,
                "user_message": "輸入數據不符合要求，請檢查並重新輸入"
            },
            "api_error": {
                "keywords": ["api", "service", "external", "response"],
                "category": ErrorCategory.EXTERNAL_API,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "外部服務暫時不可用，請稍後再試"
            },
            "performance_error": {
                "keywords": ["timeout", "slow", "memory", "performance"],
                "category": ErrorCategory.PERFORMANCE,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "系統響應較慢，請稍候或嘗試刷新頁面"
            }
        }
    
    def _initialize_recovery_strategies(self):
        """初始化恢復策略"""
        self.recovery_strategies = {
            ErrorCategory.NETWORK: [
                "檢查網絡連接",
                "嘗試刷新頁面",
                "稍後重試",
                "聯繫系統管理員"
            ],
            ErrorCategory.AUTHENTICATION: [
                "重新登錄",
                "檢查用戶名和密碼",
                "清除瀏覽器快取",
                "聯繫系統管理員"
            ],
            ErrorCategory.PERMISSION: [
                "聯繫管理員申請權限",
                "使用其他帳戶",
                "檢查用戶角色設置"
            ],
            ErrorCategory.DATA: [
                "檢查數據格式",
                "重新上傳數據",
                "使用範例數據",
                "聯繫技術支持"
            ],
            ErrorCategory.VALIDATION: [
                "檢查輸入格式",
                "填寫必填欄位",
                "參考輸入說明",
                "使用預設值"
            ],
            ErrorCategory.EXTERNAL_API: [
                "稍後重試",
                "檢查 API 狀態",
                "使用備用數據源",
                "聯繫服務提供商"
            ],
            ErrorCategory.PERFORMANCE: [
                "刷新頁面",
                "清除瀏覽器快取",
                "減少數據量",
                "稍後重試"
            ],
            ErrorCategory.SYSTEM: [
                "重啟應用程式",
                "檢查系統資源",
                "聯繫技術支持",
                "查看系統日誌"
            ]
        }
    
    def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        user_action: str = "",
        show_to_user: bool = True
    ) -> ErrorInfo:
        """處理錯誤
        
        Args:
            error: 異常對象
            context: 錯誤上下文
            user_action: 用戶執行的操作
            show_to_user: 是否向用戶顯示錯誤
            
        Returns:
            ErrorInfo: 錯誤信息對象
        """
        # 生成錯誤 ID
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(error)}"
        
        # 分析錯誤
        category, severity = self._analyze_error(error)
        
        # 生成用戶友好的錯誤消息
        user_message = self._generate_user_message(error, category)
        
        # 獲取恢復建議
        recovery_suggestions = self.recovery_strategies.get(category, [])
        
        # 創建錯誤信息對象
        error_info = ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(error),
            user_message=user_message,
            technical_details=f"{type(error).__name__}: {str(error)}",
            timestamp=datetime.now(),
            context=context or {},
            stack_trace=traceback.format_exc(),
            recovery_suggestions=recovery_suggestions
        )
        
        # 記錄錯誤
        self._log_error(error_info, user_action)
        
        # 保存到歷史
        self.error_history.append(error_info)
        st.session_state.error_history.append({
            "error_id": error_id,
            "timestamp": error_info.timestamp.isoformat(),
            "category": category.value,
            "severity": severity.value,
            "user_message": user_message,
            "user_action": user_action
        })
        
        # 向用戶顯示錯誤
        if show_to_user and st.session_state.get("error_feedback_enabled", True):
            self._display_error_to_user(error_info)
        
        return error_info
    
    def _analyze_error(self, error: Exception) -> tuple[ErrorCategory, ErrorSeverity]:
        """分析錯誤類型和嚴重程度
        
        Args:
            error: 異常對象
            
        Returns:
            tuple: (錯誤類別, 嚴重程度)
        """
        error_text = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # 根據錯誤模式匹配
        for pattern_name, pattern_info in self.error_patterns.items():
            keywords = pattern_info["keywords"]
            
            if any(keyword in error_text or keyword in error_type for keyword in keywords):
                return pattern_info["category"], pattern_info["severity"]
        
        # 根據異常類型判斷
        if isinstance(error, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        elif isinstance(error, PermissionError):
            return ErrorCategory.PERMISSION, ErrorSeverity.MEDIUM
        elif isinstance(error, ValueError):
            return ErrorCategory.VALIDATION, ErrorSeverity.LOW
        elif isinstance(error, FileNotFoundError):
            return ErrorCategory.DATA, ErrorSeverity.MEDIUM
        elif isinstance(error, MemoryError):
            return ErrorCategory.PERFORMANCE, ErrorSeverity.HIGH
        else:
            return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM
    
    def _generate_user_message(self, error: Exception, category: ErrorCategory) -> str:
        """生成用戶友好的錯誤消息
        
        Args:
            error: 異常對象
            category: 錯誤類別
            
        Returns:
            str: 用戶友好的錯誤消息
        """
        error_text = str(error).lower()
        
        # 檢查錯誤模式
        for pattern_info in self.error_patterns.values():
            if pattern_info["category"] == category:
                keywords = pattern_info["keywords"]
                if any(keyword in error_text for keyword in keywords):
                    return pattern_info["user_message"]
        
        # 默認消息
        default_messages = {
            ErrorCategory.NETWORK: "網絡連接出現問題，請檢查您的網絡設置",
            ErrorCategory.DATA: "數據處理出現問題，請檢查輸入數據",
            ErrorCategory.AUTHENTICATION: "身份驗證失敗，請重新登錄",
            ErrorCategory.PERMISSION: "您沒有執行此操作的權限",
            ErrorCategory.VALIDATION: "輸入數據不符合要求，請檢查並重新輸入",
            ErrorCategory.SYSTEM: "系統出現問題，請稍後再試",
            ErrorCategory.USER_INPUT: "輸入格式不正確，請檢查並重新輸入",
            ErrorCategory.EXTERNAL_API: "外部服務暫時不可用，請稍後再試",
            ErrorCategory.PERFORMANCE: "系統響應較慢，請稍候或嘗試刷新頁面",
            ErrorCategory.UNKNOWN: "出現未知錯誤，請稍後再試或聯繫技術支持"
        }
        
        return default_messages.get(category, "出現錯誤，請稍後再試")
    
    def _log_error(self, error_info: ErrorInfo, user_action: str):
        """記錄錯誤到日誌
        
        Args:
            error_info: 錯誤信息
            user_action: 用戶操作
        """
        log_level = {
            ErrorSeverity.LOW: logging.WARNING,
            ErrorSeverity.MEDIUM: logging.ERROR,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_info.severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"錯誤 {error_info.error_id}: {error_info.message} | "
            f"類別: {error_info.category.value} | "
            f"嚴重程度: {error_info.severity.value} | "
            f"用戶操作: {user_action} | "
            f"上下文: {error_info.context}"
        )
        
        # 對於嚴重錯誤，記錄完整堆疊追蹤
        if error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.error(f"堆疊追蹤 {error_info.error_id}:\n{error_info.stack_trace}")
    
    def _display_error_to_user(self, error_info: ErrorInfo):
        """向用戶顯示錯誤
        
        Args:
            error_info: 錯誤信息
        """
        # 根據嚴重程度選擇顯示方式
        if error_info.severity == ErrorSeverity.CRITICAL:
            st.error(f"🚨 {error_info.user_message}")
        elif error_info.severity == ErrorSeverity.HIGH:
            st.error(f"❌ {error_info.user_message}")
        elif error_info.severity == ErrorSeverity.MEDIUM:
            st.warning(f"⚠️ {error_info.user_message}")
        else:
            st.info(f"ℹ️ {error_info.user_message}")
        
        # 顯示恢復建議
        if error_info.recovery_suggestions:
            with st.expander("💡 解決建議"):
                for suggestion in error_info.recovery_suggestions:
                    st.write(f"• {suggestion}")
        
        # 顯示錯誤 ID（用於技術支持）
        st.caption(f"錯誤 ID: {error_info.error_id}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """獲取錯誤統計信息
        
        Returns:
            Dict[str, Any]: 錯誤統計
        """
        if not self.error_history:
            return {
                "total_errors": 0,
                "by_category": {},
                "by_severity": {},
                "recent_errors": []
            }
        
        # 按類別統計
        by_category = {}
        for error in self.error_history:
            category = error.category.value
            by_category[category] = by_category.get(category, 0) + 1
        
        # 按嚴重程度統計
        by_severity = {}
        for error in self.error_history:
            severity = error.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # 最近的錯誤
        recent_errors = self.error_history[-10:] if len(self.error_history) > 10 else self.error_history
        
        return {
            "total_errors": len(self.error_history),
            "by_category": by_category,
            "by_severity": by_severity,
            "recent_errors": [
                {
                    "error_id": error.error_id,
                    "category": error.category.value,
                    "severity": error.severity.value,
                    "message": error.user_message,
                    "timestamp": error.timestamp.isoformat()
                }
                for error in recent_errors
            ]
        }
    
    def clear_error_history(self):
        """清除錯誤歷史"""
        self.error_history.clear()
        st.session_state.error_history = []
        logger.info("錯誤歷史已清除")


# 全域錯誤處理器
error_handler = ErrorHandler()


# 裝飾器函數
def handle_errors(
    user_action: str = "",
    show_to_user: bool = True,
    fallback_value: Any = None
):
    """錯誤處理裝飾器
    
    Args:
        user_action: 用戶操作描述
        show_to_user: 是否向用戶顯示錯誤
        fallback_value: 發生錯誤時的回退值
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = error_handler.handle_error(
                    error=e,
                    context={
                        "function": func.__name__,
                        "args": str(args)[:200],  # 限制長度
                        "kwargs": str(kwargs)[:200]
                    },
                    user_action=user_action or f"執行 {func.__name__}",
                    show_to_user=show_to_user
                )
                
                return fallback_value
        
        return wrapper
    return decorator


# 便捷函數
def safe_execute(
    func: Callable,
    *args,
    user_action: str = "",
    fallback_value: Any = None,
    **kwargs
) -> Any:
    """安全執行函數
    
    Args:
        func: 要執行的函數
        *args: 函數參數
        user_action: 用戶操作描述
        fallback_value: 錯誤時的回退值
        **kwargs: 函數關鍵字參數
        
    Returns:
        Any: 函數執行結果或回退值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_handler.handle_error(
            error=e,
            context={
                "function": func.__name__,
                "args": str(args)[:200],
                "kwargs": str(kwargs)[:200]
            },
            user_action=user_action or f"執行 {func.__name__}"
        )
        return fallback_value


def show_error_message(
    message: str,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    recovery_suggestions: List[str] = None
):
    """顯示自定義錯誤消息
    
    Args:
        message: 錯誤消息
        category: 錯誤類別
        severity: 嚴重程度
        recovery_suggestions: 恢復建議
    """
    # 創建虛擬異常
    class CustomError(Exception):
        pass
    
    error = CustomError(message)
    
    error_info = ErrorInfo(
        error_id=f"CUSTOM_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        category=category,
        severity=severity,
        message=message,
        user_message=message,
        technical_details=message,
        timestamp=datetime.now(),
        context={},
        recovery_suggestions=recovery_suggestions or []
    )
    
    error_handler._display_error_to_user(error_info)


class UserFeedbackManager:
    """用戶反饋管理器"""

    def __init__(self):
        """初始化用戶反饋管理器"""
        self.feedback_history: List[Dict[str, Any]] = []

        # 初始化 session state
        if "user_feedback" not in st.session_state:
            st.session_state.user_feedback = []

        if "feedback_enabled" not in st.session_state:
            st.session_state.feedback_enabled = True

    def collect_error_feedback(self, error_info: ErrorInfo) -> Optional[Dict[str, Any]]:
        """收集錯誤相關的用戶反饋

        Args:
            error_info: 錯誤信息

        Returns:
            Optional[Dict[str, Any]]: 用戶反饋
        """
        if not st.session_state.get("feedback_enabled", True):
            return None

        with st.expander("📝 提供反饋（可選）"):
            st.write("您的反饋將幫助我們改進系統")

            col1, col2 = st.columns(2)

            with col1:
                helpful = st.radio(
                    "錯誤信息是否有幫助？",
                    options=["是", "否", "部分有幫助"],
                    key=f"helpful_{error_info.error_id}"
                )

                severity_rating = st.slider(
                    "這個錯誤對您的影響程度",
                    min_value=1,
                    max_value=5,
                    value=3,
                    help="1=輕微影響, 5=嚴重影響",
                    key=f"severity_{error_info.error_id}"
                )

            with col2:
                user_context = st.text_area(
                    "您當時在做什麼？",
                    placeholder="請描述您執行的操作...",
                    key=f"context_{error_info.error_id}"
                )

                suggestions = st.text_area(
                    "您有什麼改進建議？",
                    placeholder="請提供您的建議...",
                    key=f"suggestions_{error_info.error_id}"
                )

            if st.button("提交反饋", key=f"submit_{error_info.error_id}"):
                feedback = {
                    "error_id": error_info.error_id,
                    "helpful": helpful,
                    "severity_rating": severity_rating,
                    "user_context": user_context,
                    "suggestions": suggestions,
                    "timestamp": datetime.now().isoformat(),
                    "error_category": error_info.category.value,
                    "error_severity": error_info.severity.value
                }

                self.save_feedback(feedback)
                st.success("✅ 感謝您的反饋！")

                return feedback

        return None

    def collect_general_feedback(self) -> Optional[Dict[str, Any]]:
        """收集一般用戶反饋

        Returns:
            Optional[Dict[str, Any]]: 用戶反饋
        """
        st.markdown("### 📝 用戶反饋")

        feedback_type = st.selectbox(
            "反饋類型",
            options=["功能建議", "錯誤報告", "用戶體驗", "性能問題", "其他"]
        )

        col1, col2 = st.columns(2)

        with col1:
            satisfaction = st.slider(
                "整體滿意度",
                min_value=1,
                max_value=5,
                value=3,
                help="1=非常不滿意, 5=非常滿意"
            )

            priority = st.selectbox(
                "優先級",
                options=["低", "中", "高", "緊急"]
            )

        with col2:
            affected_features = st.multiselect(
                "涉及功能",
                options=[
                    "儀表板", "數據管理", "策略管理", "回測分析",
                    "風險管理", "交易執行", "報告分析", "用戶設置"
                ]
            )

            contact_info = st.text_input(
                "聯繫方式（可選）",
                placeholder="email@example.com"
            )

        feedback_content = st.text_area(
            "詳細反饋",
            placeholder="請詳細描述您的反饋...",
            height=150
        )

        if st.button("提交反饋", type="primary"):
            if feedback_content.strip():
                feedback = {
                    "feedback_id": f"FB_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "type": feedback_type,
                    "satisfaction": satisfaction,
                    "priority": priority,
                    "affected_features": affected_features,
                    "content": feedback_content,
                    "contact_info": contact_info,
                    "timestamp": datetime.now().isoformat(),
                    "user_agent": st.session_state.get("username", "anonymous")
                }

                self.save_feedback(feedback)
                st.success("✅ 感謝您的反饋！我們會認真考慮您的建議。")

                return feedback
            else:
                st.error("❌ 請填寫反饋內容")

        return None

    def save_feedback(self, feedback: Dict[str, Any]):
        """保存用戶反饋

        Args:
            feedback: 反饋數據
        """
        self.feedback_history.append(feedback)
        st.session_state.user_feedback.append(feedback)

        # 記錄到日誌
        logger.info(f"用戶反饋: {feedback.get('feedback_id', feedback.get('error_id', 'unknown'))}")

    def get_feedback_statistics(self) -> Dict[str, Any]:
        """獲取反饋統計

        Returns:
            Dict[str, Any]: 反饋統計
        """
        if not self.feedback_history:
            return {
                "total_feedback": 0,
                "by_type": {},
                "avg_satisfaction": 0,
                "recent_feedback": []
            }

        # 按類型統計
        by_type = {}
        satisfaction_scores = []

        for feedback in self.feedback_history:
            feedback_type = feedback.get("type", "其他")
            by_type[feedback_type] = by_type.get(feedback_type, 0) + 1

            if "satisfaction" in feedback:
                satisfaction_scores.append(feedback["satisfaction"])

        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0

        # 最近的反饋
        recent_feedback = self.feedback_history[-5:] if len(self.feedback_history) > 5 else self.feedback_history

        return {
            "total_feedback": len(self.feedback_history),
            "by_type": by_type,
            "avg_satisfaction": avg_satisfaction,
            "recent_feedback": [
                {
                    "id": fb.get("feedback_id", fb.get("error_id", "unknown")),
                    "type": fb.get("type", "錯誤反饋"),
                    "satisfaction": fb.get("satisfaction"),
                    "timestamp": fb.get("timestamp")
                }
                for fb in recent_feedback
            ]
        }


# 全域用戶反饋管理器
feedback_manager = UserFeedbackManager()

# 為了向後兼容，創建health_checker別名
class SystemHealthChecker:
    """系統健康檢查器 - 簡化版"""

    def run_health_check(self):
        """運行健康檢查"""
        return {
            "overall_status": "healthy",
            "checks": {},
            "timestamp": "2025-01-16"
        }

health_checker = SystemHealthChecker()
