"""
錯誤處理和用戶反饋組件

提供錯誤處理和用戶反饋的完整界面，包括：
- 錯誤監控儀表板
- 用戶反饋收集
- 錯誤統計和分析
- 系統健康監控
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

from ..utils.error_handler import (
    error_handler,
    feedback_manager,
    ErrorSeverity,
    ErrorCategory,
    handle_errors,
    safe_execute,
    show_error_message
)

logger = logging.getLogger(__name__)


def error_monitoring_dashboard():
    """錯誤監控儀表板"""
    st.subheader("🚨 錯誤監控中心")
    
    # 獲取錯誤統計
    error_stats = error_handler.get_error_statistics()
    feedback_stats = feedback_manager.get_feedback_statistics()
    
    # 總體狀態
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_errors = error_stats["total_errors"]
        status_color = "🔴" if total_errors > 10 else "🟡" if total_errors > 5 else "🟢"
        st.metric("總錯誤數", f"{status_color} {total_errors}")
    
    with col2:
        total_feedback = feedback_stats["total_feedback"]
        st.metric("用戶反饋", f"📝 {total_feedback}")
    
    with col3:
        avg_satisfaction = feedback_stats["avg_satisfaction"]
        satisfaction_emoji = "😊" if avg_satisfaction >= 4 else "😐" if avg_satisfaction >= 3 else "😞"
        st.metric("平均滿意度", f"{satisfaction_emoji} {avg_satisfaction:.1f}/5")
    
    with col4:
        system_health = calculate_system_health(error_stats, feedback_stats)
        health_color = "🟢" if system_health >= 80 else "🟡" if system_health >= 60 else "🔴"
        st.metric("系統健康度", f"{health_color} {system_health:.0f}%")
    
    # 標籤頁
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 錯誤分析", "📝 用戶反饋", "🔍 錯誤詳情", "⚙️ 設置", "🧪 測試工具"
    ])
    
    with tab1:
        show_error_analysis(error_stats)
    
    with tab2:
        show_feedback_management(feedback_stats)
    
    with tab3:
        show_error_details()
    
    with tab4:
        show_error_settings()
    
    with tab5:
        show_error_testing_tools()


def show_error_analysis(error_stats: Dict[str, Any]):
    """顯示錯誤分析"""
    st.markdown("### 📊 錯誤分析")
    
    if error_stats["total_errors"] == 0:
        st.info("🎉 太棒了！目前沒有錯誤記錄。")
        return
    
    # 錯誤趨勢圖
    col1, col2 = st.columns(2)
    
    with col1:
        # 按類別分布
        if error_stats["by_category"]:
            category_df = pd.DataFrame(
                list(error_stats["by_category"].items()),
                columns=["類別", "數量"]
            )
            
            fig_pie = px.pie(
                category_df,
                values="數量",
                names="類別",
                title="錯誤類別分布"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # 按嚴重程度分布
        if error_stats["by_severity"]:
            severity_df = pd.DataFrame(
                list(error_stats["by_severity"].items()),
                columns=["嚴重程度", "數量"]
            )
            
            # 定義顏色映射
            color_map = {
                "low": "#28a745",
                "medium": "#ffc107", 
                "high": "#fd7e14",
                "critical": "#dc3545"
            }
            
            fig_bar = px.bar(
                severity_df,
                x="嚴重程度",
                y="數量",
                title="錯誤嚴重程度分布",
                color="嚴重程度",
                color_discrete_map=color_map
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    # 最近錯誤列表
    st.markdown("#### 📋 最近錯誤")
    
    if error_stats["recent_errors"]:
        recent_df = pd.DataFrame(error_stats["recent_errors"])
        recent_df["時間"] = pd.to_datetime(recent_df["timestamp"]).dt.strftime("%m-%d %H:%M")
        
        # 添加嚴重程度圖標
        severity_icons = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠",
            "critical": "🔴"
        }
        recent_df["嚴重程度"] = recent_df["severity"].map(severity_icons) + " " + recent_df["severity"]
        
        display_df = recent_df[["時間", "類別", "嚴重程度", "message"]].rename(columns={
            "category": "類別",
            "message": "錯誤消息"
        })
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("📭 沒有最近的錯誤記錄")
    
    # 錯誤統計表
    st.markdown("#### 📈 統計摘要")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**按類別統計**")
        for category, count in error_stats["by_category"].items():
            st.write(f"• {category}: {count}")
    
    with col2:
        st.markdown("**按嚴重程度統計**")
        for severity, count in error_stats["by_severity"].items():
            icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(severity, "⚪")
            st.write(f"• {icon} {severity}: {count}")
    
    with col3:
        st.markdown("**系統建議**")
        suggestions = generate_error_suggestions(error_stats)
        for suggestion in suggestions:
            st.write(f"• {suggestion}")


def show_feedback_management(feedback_stats: Dict[str, Any]):
    """顯示反饋管理"""
    st.markdown("### 📝 用戶反饋管理")
    
    # 反饋收集
    st.markdown("#### ➕ 收集新反饋")
    
    feedback_result = feedback_manager.collect_general_feedback()
    
    # 反饋統計
    if feedback_stats["total_feedback"] > 0:
        st.markdown("#### 📊 反饋統計")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 反饋類型分布
            if feedback_stats["by_type"]:
                type_df = pd.DataFrame(
                    list(feedback_stats["by_type"].items()),
                    columns=["類型", "數量"]
                )
                
                fig_type = px.bar(
                    type_df,
                    x="類型",
                    y="數量",
                    title="反饋類型分布"
                )
                st.plotly_chart(fig_type, use_container_width=True)
        
        with col2:
            # 滿意度趨勢
            st.metric(
                "平均滿意度",
                f"{feedback_stats['avg_satisfaction']:.1f}/5",
                help="基於用戶評分的平均滿意度"
            )
            
            # 滿意度分布（模擬）
            satisfaction_data = {
                "評分": ["1星", "2星", "3星", "4星", "5星"],
                "數量": [1, 2, 5, 8, 4]  # 模擬數據
            }
            
            sat_df = pd.DataFrame(satisfaction_data)
            fig_sat = px.bar(
                sat_df,
                x="評分",
                y="數量",
                title="滿意度分布",
                color="數量",
                color_continuous_scale="RdYlGn"
            )
            st.plotly_chart(fig_sat, use_container_width=True)
        
        # 最近反饋
        st.markdown("#### 📋 最近反饋")
        
        if feedback_stats["recent_feedback"]:
            recent_feedback_df = pd.DataFrame(feedback_stats["recent_feedback"])
            recent_feedback_df["時間"] = pd.to_datetime(recent_feedback_df["timestamp"]).dt.strftime("%m-%d %H:%M")
            
            display_feedback_df = recent_feedback_df[["時間", "type", "satisfaction"]].rename(columns={
                "type": "類型",
                "satisfaction": "滿意度"
            })
            
            st.dataframe(display_feedback_df, use_container_width=True)
        else:
            st.info("📭 沒有最近的反饋記錄")
    
    else:
        st.info("📭 尚未收到用戶反饋")


def show_error_details():
    """顯示錯誤詳情"""
    st.markdown("### 🔍 錯誤詳情")
    
    # 錯誤搜索
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_category = st.selectbox(
            "錯誤類別",
            options=["全部"] + [cat.value for cat in ErrorCategory]
        )
    
    with col2:
        search_severity = st.selectbox(
            "嚴重程度",
            options=["全部"] + [sev.value for sev in ErrorSeverity]
        )
    
    with col3:
        search_date = st.date_input(
            "日期範圍",
            value=[datetime.now().date() - timedelta(days=7), datetime.now().date()]
        )
    
    # 顯示過濾後的錯誤
    filtered_errors = filter_errors(search_category, search_severity, search_date)
    
    if filtered_errors:
        for error in filtered_errors:
            with st.expander(f"🚨 {error['error_id']} - {error['category']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**錯誤 ID**: {error['error_id']}")
                    st.write(f"**類別**: {error['category']}")
                    st.write(f"**嚴重程度**: {error['severity']}")
                    st.write(f"**時間**: {error['timestamp']}")
                
                with col2:
                    st.write(f"**用戶消息**: {error['user_message']}")
                    st.write(f"**用戶操作**: {error.get('user_action', '未知')}")
                
                if error.get("technical_details"):
                    st.code(error["technical_details"])
                
                if error.get("recovery_suggestions"):
                    st.markdown("**恢復建議**:")
                    for suggestion in error["recovery_suggestions"]:
                        st.write(f"• {suggestion}")
    else:
        st.info("📭 沒有符合條件的錯誤記錄")


def show_error_settings():
    """顯示錯誤設置"""
    st.markdown("### ⚙️ 錯誤處理設置")
    
    # 錯誤顯示設置
    st.markdown("#### 🔔 錯誤通知設置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        error_feedback_enabled = st.checkbox(
            "啟用錯誤反饋",
            value=st.session_state.get("error_feedback_enabled", True),
            help="向用戶顯示錯誤消息和恢復建議"
        )
        st.session_state.error_feedback_enabled = error_feedback_enabled
        
        auto_error_reporting = st.checkbox(
            "自動錯誤報告",
            value=st.session_state.get("auto_error_reporting", True),
            help="自動記錄和報告系統錯誤"
        )
        st.session_state.auto_error_reporting = auto_error_reporting
    
    with col2:
        feedback_enabled = st.checkbox(
            "啟用用戶反饋收集",
            value=st.session_state.get("feedback_enabled", True),
            help="允許用戶提供反饋"
        )
        st.session_state.feedback_enabled = feedback_enabled
        
        detailed_error_info = st.checkbox(
            "顯示詳細錯誤信息",
            value=st.session_state.get("detailed_error_info", False),
            help="向用戶顯示技術詳情（調試模式）"
        )
        st.session_state.detailed_error_info = detailed_error_info
    
    # 錯誤級別設置
    st.markdown("#### 📊 錯誤級別設置")
    
    min_severity = st.selectbox(
        "最低顯示級別",
        options=[sev.value for sev in ErrorSeverity],
        index=1,  # 默認為 medium
        help="只顯示此級別及以上的錯誤"
    )
    st.session_state.min_error_severity = min_severity
    
    # 清理設置
    st.markdown("#### 🧹 數據清理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ 清除錯誤歷史"):
            error_handler.clear_error_history()
            st.success("✅ 錯誤歷史已清除")
            st.rerun()
    
    with col2:
        if st.button("🗑️ 清除反饋歷史"):
            feedback_manager.feedback_history.clear()
            st.session_state.user_feedback = []
            st.success("✅ 反饋歷史已清除")
            st.rerun()


def show_error_testing_tools():
    """顯示錯誤測試工具"""
    st.markdown("### 🧪 錯誤測試工具")
    
    st.warning("⚠️ 這些工具僅用於測試目的，請謹慎使用")
    
    # 模擬錯誤
    st.markdown("#### 🎭 模擬錯誤")
    
    col1, col2 = st.columns(2)
    
    with col1:
        error_type = st.selectbox(
            "錯誤類型",
            options=[
                "網絡錯誤",
                "數據錯誤", 
                "權限錯誤",
                "驗證錯誤",
                "系統錯誤"
            ]
        )
        
        error_severity = st.selectbox(
            "錯誤嚴重程度",
            options=["low", "medium", "high", "critical"]
        )
    
    with col2:
        custom_message = st.text_input(
            "自定義錯誤消息",
            placeholder="輸入自定義錯誤消息..."
        )
        
        if st.button("🚨 觸發測試錯誤"):
            trigger_test_error(error_type, error_severity, custom_message)
    
    # 性能測試
    st.markdown("#### ⚡ 性能測試")
    
    if st.button("🔄 測試錯誤處理性能"):
        test_error_handling_performance()
    
    # 錯誤恢復測試
    st.markdown("#### 🔧 錯誤恢復測試")
    
    if st.button("🛠️ 測試錯誤恢復機制"):
        test_error_recovery()


def calculate_system_health(error_stats: Dict[str, Any], feedback_stats: Dict[str, Any]) -> float:
    """計算系統健康度
    
    Args:
        error_stats: 錯誤統計
        feedback_stats: 反饋統計
        
    Returns:
        float: 健康度分數 (0-100)
    """
    base_score = 100
    
    # 根據錯誤數量扣分
    total_errors = error_stats["total_errors"]
    if total_errors > 0:
        error_penalty = min(50, total_errors * 2)  # 最多扣50分
        base_score -= error_penalty
    
    # 根據嚴重錯誤扣分
    critical_errors = error_stats["by_severity"].get("critical", 0)
    high_errors = error_stats["by_severity"].get("high", 0)
    
    base_score -= critical_errors * 10  # 每個致命錯誤扣10分
    base_score -= high_errors * 5       # 每個嚴重錯誤扣5分
    
    # 根據用戶滿意度調整
    avg_satisfaction = feedback_stats["avg_satisfaction"]
    if avg_satisfaction > 0:
        satisfaction_bonus = (avg_satisfaction - 3) * 5  # 滿意度超過3分有加分
        base_score += satisfaction_bonus
    
    return max(0, min(100, base_score))


def generate_error_suggestions(error_stats: Dict[str, Any]) -> List[str]:
    """生成錯誤改進建議
    
    Args:
        error_stats: 錯誤統計
        
    Returns:
        List[str]: 建議列表
    """
    suggestions = []
    
    # 根據錯誤類別提供建議
    by_category = error_stats["by_category"]
    
    if by_category.get("network", 0) > 3:
        suggestions.append("考慮添加網絡重試機制")
    
    if by_category.get("data", 0) > 3:
        suggestions.append("加強數據驗證和清理")
    
    if by_category.get("validation", 0) > 5:
        suggestions.append("改進用戶輸入驗證提示")
    
    # 根據嚴重程度提供建議
    by_severity = error_stats["by_severity"]
    
    if by_severity.get("critical", 0) > 0:
        suggestions.append("立即處理致命錯誤")
    
    if by_severity.get("high", 0) > 2:
        suggestions.append("優先處理高嚴重程度錯誤")
    
    if not suggestions:
        suggestions.append("系統運行良好，繼續保持")
    
    return suggestions


def filter_errors(category: str, severity: str, date_range: List) -> List[Dict[str, Any]]:
    """過濾錯誤記錄
    
    Args:
        category: 錯誤類別
        severity: 嚴重程度
        date_range: 日期範圍
        
    Returns:
        List[Dict[str, Any]]: 過濾後的錯誤列表
    """
    # 這裡應該從實際的錯誤歷史中過濾
    # 目前返回模擬數據
    sample_errors = [
        {
            "error_id": "ERR_20231201_001",
            "category": "network",
            "severity": "medium",
            "user_message": "網絡連接超時",
            "timestamp": "2023-12-01 10:30:00",
            "technical_details": "ConnectionTimeout: Request timeout after 30s",
            "recovery_suggestions": ["檢查網絡連接", "稍後重試"]
        }
    ]
    
    # 應用過濾條件
    filtered = sample_errors
    
    if category != "全部":
        filtered = [e for e in filtered if e["category"] == category]
    
    if severity != "全部":
        filtered = [e for e in filtered if e["severity"] == severity]
    
    return filtered


def trigger_test_error(error_type: str, severity: str, message: str):
    """觸發測試錯誤
    
    Args:
        error_type: 錯誤類型
        severity: 嚴重程度
        message: 錯誤消息
    """
    try:
        # 根據錯誤類型觸發不同的異常
        if error_type == "網絡錯誤":
            raise ConnectionError(message or "模擬網絡連接錯誤")
        elif error_type == "數據錯誤":
            raise ValueError(message or "模擬數據格式錯誤")
        elif error_type == "權限錯誤":
            raise PermissionError(message or "模擬權限不足錯誤")
        elif error_type == "驗證錯誤":
            raise ValueError(message or "模擬數據驗證錯誤")
        else:
            raise Exception(message or "模擬系統錯誤")
    
    except Exception as e:
        error_handler.handle_error(
            error=e,
            context={"test_mode": True, "triggered_by": "user"},
            user_action="測試錯誤處理"
        )


def test_error_handling_performance():
    """測試錯誤處理性能"""
    import time
    
    start_time = time.time()
    
    # 模擬多個錯誤
    for i in range(10):
        try:
            raise ValueError(f"測試錯誤 {i}")
        except Exception as e:
            error_handler.handle_error(
                error=e,
                context={"test_index": i},
                user_action="性能測試",
                show_to_user=False
            )
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    st.success(f"✅ 性能測試完成！處理 10 個錯誤耗時 {processing_time:.3f} 秒")


def test_error_recovery():
    """測試錯誤恢復機制"""
    @handle_errors(user_action="測試錯誤恢復", fallback_value="恢復成功")
    def failing_function():
        raise Exception("故意失敗的函數")
    
    result = failing_function()
    
    if result == "恢復成功":
        st.success("✅ 錯誤恢復機制工作正常")
    else:
        st.error("❌ 錯誤恢復機制異常")
