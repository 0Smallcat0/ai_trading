"""風險管理面板組件

此模組提供風險管理相關的面板組件，包括：
- 風險概覽面板
- 控制面板組件
- 警報面板
- 狀態指示面板

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, Any, List, Optional
import streamlit as st
from datetime import datetime


def risk_overview_panel(
    metrics: Dict[str, Any],
    title: str = "風險概覽"
) -> None:
    """風險概覽面板
    
    Args:
        metrics: 風險指標字典
        title: 面板標題
    """
    st.subheader(title)
    
    # 主要指標卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        portfolio_value = metrics.get("portfolio_value", 0)
        daily_pnl = metrics.get("daily_pnl", 0)
        st.metric(
            "投資組合價值",
            f"${portfolio_value:,.0f}",
            f"{daily_pnl:+,.0f}"
        )
    
    with col2:
        var_value = metrics.get("var_95_1day", 0)
        var_pct = var_value / portfolio_value * 100 if portfolio_value > 0 else 0
        st.metric(
            "95% VaR (1日)",
            f"${var_value:,.0f}",
            f"{var_pct:.2f}%"
        )
    
    with col3:
        current_drawdown = metrics.get("current_drawdown", 0)
        max_drawdown = metrics.get("max_drawdown", 0)
        st.metric(
            "當前回撤",
            f"{current_drawdown:.2f}%",
            f"最大: {max_drawdown:.2f}%"
        )
    
    with col4:
        volatility = metrics.get("volatility", 0)
        sharpe_ratio = metrics.get("sharpe_ratio", 0)
        st.metric(
            "年化波動率",
            f"{volatility:.1f}%",
            f"夏普: {sharpe_ratio:.2f}"
        )


def control_panel(
    controls: Dict[str, bool],
    on_change: Optional[callable] = None,
    title: str = "風控機制控制"
) -> Dict[str, bool]:
    """控制面板組件
    
    Args:
        controls: 控制狀態字典
        on_change: 狀態變更回調函數
        title: 面板標題
        
    Returns:
        Dict[str, bool]: 更新後的控制狀態
    """
    st.subheader(title)
    
    # 主開關
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        master_switch = st.toggle(
            "🔴 主開關",
            value=controls.get("master_switch", True),
            key="master_control_switch"
        )
        controls["master_switch"] = master_switch
    
    with col2:
        if st.button("🚨 緊急停止", type="secondary", use_container_width=True):
            controls["emergency_stop"] = True
            st.error("🚨 緊急停止已啟動！")
    
    with col3:
        if st.button("🔄 重啟系統", use_container_width=True):
            controls["emergency_stop"] = False
            st.success("✅ 系統已重啟")
    
    with col4:
        auto_mode = st.toggle(
            "🤖 自動模式",
            value=controls.get("auto_mode", True),
            key="auto_control_mode"
        )
        controls["auto_mode"] = auto_mode
    
    # 個別控制
    st.divider()
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.write("**交易控制**")
        controls["stop_loss_active"] = st.checkbox(
            "停損機制",
            value=controls.get("stop_loss_active", True),
            disabled=not master_switch,
            key="stop_loss_control"
        )
        
        controls["take_profit_active"] = st.checkbox(
            "停利機制",
            value=controls.get("take_profit_active", True),
            disabled=not master_switch,
            key="take_profit_control"
        )
        
        controls["position_limit_active"] = st.checkbox(
            "部位限制",
            value=controls.get("position_limit_active", True),
            disabled=not master_switch,
            key="position_limit_control"
        )
    
    with col_right:
        st.write("**風險監控**")
        controls["var_monitoring_active"] = st.checkbox(
            "VaR 監控",
            value=controls.get("var_monitoring_active", True),
            disabled=not master_switch,
            key="var_monitoring_control"
        )
        
        controls["drawdown_protection_active"] = st.checkbox(
            "回撤保護",
            value=controls.get("drawdown_protection_active", True),
            disabled=not master_switch,
            key="drawdown_protection_control"
        )
        
        controls["correlation_check_active"] = st.checkbox(
            "相關性檢查",
            value=controls.get("correlation_check_active", True),
            disabled=not master_switch,
            key="correlation_check_control"
        )
    
    if on_change:
        on_change(controls)
    
    return controls


def alert_panel(
    alerts: List[Dict[str, Any]],
    title: str = "風險警報"
) -> None:
    """警報面板
    
    Args:
        alerts: 警報列表
        title: 面板標題
    """
    st.subheader(title)
    
    if not alerts:
        st.info("目前沒有風險警報")
        return
    
    # 警報統計
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_alerts = len(alerts)
        st.metric("總警報數", total_alerts)
    
    with col2:
        high_severity = len([a for a in alerts if a.get("嚴重程度") in ["高", "嚴重"]])
        st.metric("高風險警報", high_severity)
    
    with col3:
        pending_alerts = len([a for a in alerts if a.get("狀態") == "待處理"])
        st.metric("待處理警報", pending_alerts)
    
    # 最新警報
    st.write("**最新警報**")
    for i, alert in enumerate(alerts[:5]):  # 顯示最新5個警報
        severity = alert.get("嚴重程度", "低")
        
        # 根據嚴重程度選擇顏色
        if severity == "嚴重":
            alert_type = "error"
        elif severity == "高":
            alert_type = "warning"
        else:
            alert_type = "info"
        
        with st.container():
            if alert_type == "error":
                st.error(f"🚨 {alert.get('類型', 'N/A')} - {alert.get('訊息', 'N/A')}")
            elif alert_type == "warning":
                st.warning(f"⚠️ {alert.get('類型', 'N/A')} - {alert.get('訊息', 'N/A')}")
            else:
                st.info(f"ℹ️ {alert.get('類型', 'N/A')} - {alert.get('訊息', 'N/A')}")
            
            st.caption(f"時間: {alert.get('時間', 'N/A')} | 狀態: {alert.get('狀態', 'N/A')}")


def status_indicator_panel(
    status: Dict[str, Any],
    title: str = "系統狀態"
) -> None:
    """狀態指示面板
    
    Args:
        status: 狀態字典
        title: 面板標題
    """
    st.subheader(title)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 系統狀態
        system_status = status.get("system_status", "unknown")
        if system_status == "normal":
            st.success("🟢 系統正常")
        elif system_status == "warning":
            st.warning("🟡 系統警告")
        else:
            st.error("🔴 系統異常")
    
    with col2:
        # 數據同步狀態
        data_sync = status.get("data_sync", "unknown")
        if data_sync == "synced":
            st.success("🟢 數據同步")
        else:
            st.error("🔴 同步異常")
    
    with col3:
        # 監控狀態
        monitoring = status.get("monitoring", False)
        if monitoring:
            st.success("🟢 監控運行")
        else:
            st.error("🔴 監控停止")
    
    # 詳細狀態信息
    with st.expander("詳細狀態信息"):
        st.write(f"**最後更新:** {status.get('last_update', 'N/A')}")
        st.write(f"**運行時間:** {status.get('uptime', 'N/A')}")
        st.write(f"**CPU 使用率:** {status.get('cpu_usage', 'N/A')}%")
        st.write(f"**記憶體使用率:** {status.get('memory_usage', 'N/A')}%")


def quick_action_panel(
    actions: Dict[str, callable],
    title: str = "快速操作"
) -> None:
    """快速操作面板
    
    Args:
        actions: 操作字典 {操作名稱: 回調函數}
        title: 面板標題
    """
    st.subheader(title)
    
    # 計算列數
    num_actions = len(actions)
    cols = st.columns(min(num_actions, 4))
    
    for i, (action_name, action_func) in enumerate(actions.items()):
        col_idx = i % 4
        with cols[col_idx]:
            if st.button(action_name, use_container_width=True):
                if action_func:
                    action_func()


def parameter_summary_panel(
    params: Dict[str, Any],
    title: str = "參數摘要"
) -> None:
    """參數摘要面板
    
    Args:
        params: 參數字典
        title: 面板標題
    """
    st.subheader(title)
    
    # 關鍵參數顯示
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**風險控制**")
        st.write(f"• 停損: {'啟用' if params.get('stop_loss_enabled') else '停用'} "
                f"({params.get('stop_loss_percent', 0):.1f}%)")
        st.write(f"• 停利: {'啟用' if params.get('take_profit_enabled') else '停用'} "
                f"({params.get('take_profit_percent', 0):.1f}%)")
        st.write(f"• 最大部位: {params.get('max_position_size', 0):.1f}%")
    
    with col2:
        st.write("**監控設定**")
        st.write(f"• VaR 信心水準: {params.get('var_confidence', 0):.1f}%")
        st.write(f"• 回撤警報: {params.get('alert_threshold_drawdown', 0):.1f}%")
        st.write(f"• 即時監控: {'啟用' if params.get('real_time_monitoring') else '停用'}")


def responsive_panel_layout(
    panels: List[Dict[str, Any]],
    layout_mode: str = "auto"
) -> None:
    """響應式面板佈局
    
    Args:
        panels: 面板列表 [{name: str, content: callable, size: str}]
        layout_mode: 佈局模式 ("auto", "desktop", "tablet", "mobile")
    """
    if layout_mode in ["auto", "desktop"]:
        # 桌面版：多列佈局
        num_cols = min(len(panels), 3)
        cols = st.columns(num_cols)
        
        for i, panel in enumerate(panels):
            col_idx = i % num_cols
            with cols[col_idx]:
                panel["content"]()
    
    elif layout_mode == "tablet":
        # 平板版：兩列佈局
        cols = st.columns(2)
        
        for i, panel in enumerate(panels):
            col_idx = i % 2
            with cols[col_idx]:
                panel["content"]()
    
    else:  # mobile
        # 手機版：單列佈局
        for panel in panels:
            panel["content"]()


def collapsible_panel(
    title: str,
    content_func: callable,
    expanded: bool = True,
    help_text: Optional[str] = None
) -> None:
    """可摺疊面板
    
    Args:
        title: 面板標題
        content_func: 內容生成函數
        expanded: 是否預設展開
        help_text: 幫助文字
    """
    with st.expander(title, expanded=expanded, help=help_text):
        content_func()
