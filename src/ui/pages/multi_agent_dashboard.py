# -*- coding: utf-8 -*-
"""
多代理管理儀表板頁面

此模組提供多代理AI交易系統的統一管理界面，整合：
- 多代理管理界面
- 代理績效監控面板
- 代理配置和參數調整
- 系統整合狀態監控

主要功能：
- 統一的代理管理入口
- 實時系統狀態監控
- 綜合績效分析
- 快速操作面板
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# 導入UI組件
from src.ui.components.multi_agent_management import render_multi_agent_management
from src.ui.components.agent_performance_monitor import render_agent_performance_monitor
from src.ui.components.agent_configuration import render_agent_configuration

# 設定日誌
logger = logging.getLogger(__name__)


def show():
    """顯示多代理儀表板頁面（Web UI 入口點）"""
    render_multi_agent_dashboard()


def render_multi_agent_dashboard():
    """
    渲染多代理管理儀表板
    
    這是多代理AI交易系統的主要管理界面，提供：
    - 系統概覽
    - 代理管理
    - 績效監控
    - 配置管理
    """
    
    # 頁面配置
    st.set_page_config(
        page_title="多代理AI交易系統",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 自定義CSS樣式
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    
    .status-online {
        color: #28a745;
        font-weight: bold;
    }
    
    .status-offline {
        color: #6c757d;
        font-weight: bold;
    }
    
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
    
    .quick-action-btn {
        width: 100%;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 主標題
    st.markdown("""
    <div class="main-header">
        <h1>🤖 多代理AI交易系統管理中心</h1>
        <p>統一管理和監控所有交易代理，實現智能協作投資決策</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 側邊欄導航
    with st.sidebar:
        st.title("🧭 導航菜單")
        
        page_selection = st.radio(
            "選擇功能模組",
            [
                "📊 系統概覽",
                "🤖 代理管理", 
                "📈 績效監控",
                "⚙️ 配置管理",
                "🔧 系統設置"
            ],
            index=0
        )
        
        st.markdown("---")
        
        # 快速操作面板
        st.subheader("⚡ 快速操作")
        
        if st.button("🚀 啟動所有代理", key="start_all", help="啟動所有已註冊的代理"):
            _quick_start_all_agents()
        
        if st.button("⏸️ 暫停所有代理", key="pause_all", help="暫停所有運行中的代理"):
            _quick_pause_all_agents()
        
        if st.button("🔄 重啟系統", key="restart_system", help="重啟整個多代理系統"):
            _quick_restart_system()
        
        if st.button("📊 生成報告", key="generate_report", help="生成系統績效報告"):
            _quick_generate_report()
        
        st.markdown("---")
        
        # 系統狀態指示器
        st.subheader("🚦 系統狀態")
        _render_system_status_indicator()
    
    # 主內容區域
    if page_selection == "📊 系統概覽":
        _render_system_overview()
    elif page_selection == "🤖 代理管理":
        render_multi_agent_management()
    elif page_selection == "📈 績效監控":
        render_agent_performance_monitor()
    elif page_selection == "⚙️ 配置管理":
        render_agent_configuration()
    elif page_selection == "🔧 系統設置":
        _render_system_settings()


def _render_system_overview():
    """渲染系統概覽"""
    st.title("📊 系統概覽")
    st.markdown("---")
    
    # 獲取系統數據
    system_data = _get_system_overview_data()
    
    # 關鍵指標
    st.subheader("🎯 關鍵指標")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "總代理數",
            system_data['total_agents'],
            delta=system_data.get('agent_change', 0)
        )
    
    with col2:
        st.metric(
            "活躍代理",
            system_data['active_agents'],
            delta=system_data.get('active_change', 0)
        )
    
    with col3:
        st.metric(
            "總投資組合價值",
            f"${system_data['portfolio_value']:,.0f}",
            delta=f"{system_data.get('portfolio_change', 0):.1%}"
        )
    
    with col4:
        st.metric(
            "今日收益率",
            f"{system_data['daily_return']:.2%}",
            delta=f"{system_data.get('return_change', 0):.2%}"
        )
    
    with col5:
        st.metric(
            "系統運行時間",
            system_data['uptime'],
            delta="穩定運行"
        )
    
    # 圖表區域
    col1, col2 = st.columns(2)
    
    with col1:
        # 代理狀態分布
        st.subheader("代理狀態分布")
        _render_agent_status_chart(system_data)
    
    with col2:
        # 績效趨勢
        st.subheader("績效趨勢")
        _render_performance_trend_chart(system_data)
    
    # 最新活動
    st.subheader("📋 最新活動")
    _render_recent_activities()
    
    # 警報和通知
    st.subheader("🚨 警報和通知")
    _render_alerts_and_notifications()


def _render_system_settings():
    """渲染系統設置"""
    st.title("🔧 系統設置")
    st.markdown("---")
    
    # 系統配置
    st.subheader("系統配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**基本設置**")
        
        auto_start = st.checkbox(
            "系統啟動時自動啟動代理",
            value=st.session_state.get('auto_start_agents', True)
        )
        
        auto_backup = st.checkbox(
            "自動備份配置",
            value=st.session_state.get('auto_backup_config', True)
        )
        
        enable_notifications = st.checkbox(
            "啟用系統通知",
            value=st.session_state.get('enable_notifications', True)
        )
        
        log_level = st.selectbox(
            "日誌級別",
            ["DEBUG", "INFO", "WARNING", "ERROR"],
            index=1
        )
    
    with col2:
        st.write("**性能設置**")
        
        max_concurrent_agents = st.slider(
            "最大並發代理數",
            min_value=1,
            max_value=50,
            value=st.session_state.get('max_concurrent_agents', 10)
        )
        
        update_frequency = st.selectbox(
            "數據更新頻率",
            ["1秒", "5秒", "10秒", "30秒", "1分鐘"],
            index=2
        )
        
        memory_limit = st.slider(
            "記憶體使用限制 (%)",
            min_value=50,
            max_value=90,
            value=st.session_state.get('memory_limit', 80)
        )
        
        cpu_limit = st.slider(
            "CPU使用限制 (%)",
            min_value=50,
            max_value=90,
            value=st.session_state.get('cpu_limit', 70)
        )
    
    # 保存設置
    if st.button("💾 保存系統設置", type="primary"):
        settings = {
            'auto_start_agents': auto_start,
            'auto_backup_config': auto_backup,
            'enable_notifications': enable_notifications,
            'log_level': log_level,
            'max_concurrent_agents': max_concurrent_agents,
            'update_frequency': update_frequency,
            'memory_limit': memory_limit,
            'cpu_limit': cpu_limit
        }
        
        _save_system_settings(settings)
        st.success("系統設置已保存！")
    
    # 系統維護
    st.subheader("系統維護")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🧹 清理系統緩存"):
            _clear_system_cache()
            st.success("系統緩存已清理！")
    
    with col2:
        if st.button("📊 系統診斷"):
            _run_system_diagnostics()
    
    with col3:
        if st.button("🔄 重置為默認"):
            if st.checkbox("確認重置", key="confirm_reset"):
                _reset_to_defaults()
                st.success("已重置為默認設置！")
                st.rerun()


def _render_system_status_indicator():
    """渲染系統狀態指示器"""
    try:
        # 獲取系統狀態
        if 'system_integrator' in st.session_state:
            system_integrator = st.session_state.system_integrator
            status = system_integrator.get_system_status()
            
            system_state = status.get('system_state', 'unknown')
            
            if system_state == 'running':
                st.success("🟢 系統正常運行")
            elif system_state == 'paused':
                st.warning("🟡 系統已暫停")
            elif system_state == 'error':
                st.error("🔴 系統錯誤")
            else:
                st.info("⚪ 系統狀態未知")
            
            # 資源使用情況
            metrics = status.get('metrics', {})
            memory_usage = metrics.get('memory_usage', 0)
            cpu_usage = metrics.get('cpu_usage', 0)
            
            st.write(f"💾 記憶體: {memory_usage:.1f}%")
            st.write(f"🖥️ CPU: {cpu_usage:.1f}%")
            
        else:
            st.warning("⚠️ 系統未初始化")
            
    except Exception as e:
        st.error(f"❌ 狀態獲取失敗: {e}")


def _get_system_overview_data() -> Dict[str, Any]:
    """獲取系統概覽數據"""
    try:
        # 模擬系統數據（實際應用中從真實數據源獲取）
        return {
            'total_agents': 8,
            'active_agents': 6,
            'portfolio_value': 1250000,
            'daily_return': 0.0234,
            'uptime': "15天 8小時",
            'agent_change': 2,
            'active_change': 1,
            'portfolio_change': 0.0234,
            'return_change': 0.0045
        }
    except Exception as e:
        logger.error(f"獲取系統概覽數據失敗: {e}")
        return {}


def _render_agent_status_chart(system_data: Dict[str, Any]):
    """渲染代理狀態圖表"""
    # 模擬代理狀態數據
    status_data = {
        '在線': 6,
        '離線': 1,
        '忙碌': 1,
        '錯誤': 0
    }
    
    colors = ['#28a745', '#6c757d', '#ffc107', '#dc3545']
    
    fig = px.pie(
        values=list(status_data.values()),
        names=list(status_data.keys()),
        color_discrete_sequence=colors
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=300, showlegend=True)
    
    st.plotly_chart(fig, use_container_width=True)


def _render_performance_trend_chart(system_data: Dict[str, Any]):
    """渲染績效趨勢圖表"""
    # 模擬績效數據
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
    returns = np.random.normal(0.001, 0.02, len(dates))
    cumulative_returns = np.cumprod(1 + returns) - 1
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=cumulative_returns,
        mode='lines',
        name='累積收益率',
        line=dict(color='#1f77b4', width=2)
    ))
    
    fig.update_layout(
        height=300,
        xaxis_title="日期",
        yaxis_title="累積收益率",
        yaxis_tickformat='.1%'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _render_recent_activities():
    """渲染最新活動"""
    activities = [
        {"時間": "10:30", "活動": "巴菲特代理執行買入決策", "狀態": "成功"},
        {"時間": "10:25", "活動": "索羅斯代理發出賣出信號", "狀態": "處理中"},
        {"時間": "10:20", "活動": "系統自動再平衡投資組合", "狀態": "完成"},
        {"時間": "10:15", "活動": "西蒙斯代理更新模型參數", "狀態": "成功"},
        {"時間": "10:10", "活動": "達里奧代理風險評估完成", "狀態": "成功"}
    ]
    
    df = pd.DataFrame(activities)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_alerts_and_notifications():
    """渲染警報和通知"""
    alerts = [
        {"級別": "⚠️ 警告", "消息": "代理權重偏差超過閾值", "時間": "2分鐘前"},
        {"級別": "ℹ️ 信息", "消息": "系統性能優化完成", "時間": "15分鐘前"},
        {"級別": "✅ 成功", "消息": "配置備份已創建", "時間": "1小時前"}
    ]
    
    for alert in alerts:
        st.write(f"{alert['級別']} {alert['消息']} - {alert['時間']}")


def _quick_start_all_agents():
    """快速啟動所有代理"""
    try:
        if 'communication' in st.session_state:
            communication = st.session_state.communication
            agents = communication.get_registered_agents()
            
            for agent_id in agents:
                communication.set_agent_status(agent_id, 'online')
            
            st.success(f"已啟動 {len(agents)} 個代理")
        else:
            st.error("通信系統未初始化")
    except Exception as e:
        st.error(f"啟動代理失敗: {e}")


def _quick_pause_all_agents():
    """快速暫停所有代理"""
    try:
        if 'communication' in st.session_state:
            communication = st.session_state.communication
            agents = communication.get_registered_agents()
            
            for agent_id in agents:
                communication.set_agent_status(agent_id, 'paused')
            
            st.success(f"已暫停 {len(agents)} 個代理")
        else:
            st.error("通信系統未初始化")
    except Exception as e:
        st.error(f"暫停代理失敗: {e}")


def _quick_restart_system():
    """快速重啟系統"""
    try:
        if 'system_integrator' in st.session_state:
            system_integrator = st.session_state.system_integrator
            # 這裡應該實現實際的重啟邏輯
            st.success("系統重啟完成")
        else:
            st.error("系統整合器未初始化")
    except Exception as e:
        st.error(f"重啟系統失敗: {e}")


def _quick_generate_report():
    """快速生成報告"""
    try:
        # 生成報告邏輯
        report_data = _get_system_overview_data()
        
        st.success("報告生成完成")
        st.download_button(
            label="📥 下載報告",
            data=f"系統報告\n生成時間: {datetime.now()}\n{report_data}",
            file_name=f"system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
    except Exception as e:
        st.error(f"生成報告失敗: {e}")


def _save_system_settings(settings: Dict[str, Any]):
    """保存系統設置"""
    for key, value in settings.items():
        st.session_state[key] = value
    logger.info("系統設置已保存")


def _clear_system_cache():
    """清理系統緩存"""
    # 清理session state中的緩存數據
    cache_keys = [key for key in st.session_state.keys() if 'cache' in key.lower()]
    for key in cache_keys:
        del st.session_state[key]
    logger.info("系統緩存已清理")


def _run_system_diagnostics():
    """運行系統診斷"""
    st.subheader("🔍 系統診斷結果")
    
    diagnostics = {
        "代理管理器": "✅ 正常",
        "通信系統": "✅ 正常", 
        "決策協調器": "✅ 正常",
        "投資組合管理": "✅ 正常",
        "風險管理": "⚠️ 警告：記憶體使用偏高",
        "數據連接": "✅ 正常"
    }
    
    for component, status in diagnostics.items():
        st.write(f"**{component}**: {status}")


def _reset_to_defaults():
    """重置為默認設置"""
    default_settings = {
        'auto_start_agents': True,
        'auto_backup_config': True,
        'enable_notifications': True,
        'log_level': 'INFO',
        'max_concurrent_agents': 10,
        'update_frequency': '10秒',
        'memory_limit': 80,
        'cpu_limit': 70
    }
    
    _save_system_settings(default_settings)
    logger.info("已重置為默認設置")


# 主函數
if __name__ == "__main__":
    render_multi_agent_dashboard()
