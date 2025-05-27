"""風控機制管理模組

此模組提供風控機制的管理界面，包括：
- 總控制面板
- 個別風控機制控制
- 緊急控制功能
- 風控動作記錄

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd
from datetime import datetime

from .utils import get_default_risk_parameters


def show_risk_controls() -> None:
    """顯示風控機制管理
    
    提供完整的風控機制管理界面，包括主開關、個別機制控制、
    緊急停止功能和風控動作記錄。
    
    Returns:
        None
        
    Side Effects:
        - 在 Streamlit 界面顯示風控機制管理面板
        - 更新風控機制狀態到 session_state
    """
    st.subheader("🔧 風控機制管理")

    # 獲取當前風險參數
    if "risk_params" not in st.session_state:
        st.session_state.risk_params = get_default_risk_parameters()

    # 風控機制狀態
    if "risk_controls_status" not in st.session_state:
        st.session_state.risk_controls_status = {
            "stop_loss_active": True,
            "take_profit_active": True,
            "position_limit_active": True,
            "var_monitoring_active": True,
            "drawdown_protection_active": True,
            "correlation_check_active": True,
            "sector_limit_active": True,
            "emergency_stop_active": False,
        }

    # 顯示各個控制面板
    _show_master_control_panel()
    _show_individual_controls()
    _show_recent_actions()
    _show_manual_actions()


def _show_master_control_panel() -> None:
    """顯示總控制面板"""
    st.write("### 🎛️ 總控制面板")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        master_switch = st.toggle("🔴 主開關", value=True, key="master_risk_switch")
        if not master_switch:
            st.warning("⚠️ 所有風控機制已停用")

    with col2:
        emergency_mode = st.button(
            "🚨 緊急停止", type="secondary", use_container_width=True
        )
        if emergency_mode:
            st.session_state.risk_controls_status["emergency_stop_active"] = True
            st.error("🚨 緊急停止已啟動！所有交易已暫停。")

    with col3:
        if st.button("🔄 重啟系統", use_container_width=True):
            st.session_state.risk_controls_status["emergency_stop_active"] = False
            st.success("✅ 系統已重啟，風控機制恢復正常。")

    with col4:
        st.toggle("🤖 自動模式", value=True, key="auto_risk_mode")


def _show_individual_controls() -> None:
    """顯示個別風控機制控制"""
    st.divider()
    
    # 個別風控機制控制
    col1, col2 = st.columns(2)
    master_switch = st.session_state.get("master_risk_switch", True)

    with col1:
        _show_stop_loss_controls(master_switch)
        _show_position_controls(master_switch)

    with col2:
        _show_monitoring_controls(master_switch)
        _show_monitoring_status()


def _show_stop_loss_controls(master_switch: bool) -> None:
    """顯示停損/停利控制"""
    st.write("### 🛑 停損/停利控制")

    # 停損控制
    st.session_state.risk_controls_status["stop_loss_active"] = st.checkbox(
        "停損機制",
        value=st.session_state.risk_controls_status["stop_loss_active"]
        and master_switch,
        disabled=not master_switch
        or st.session_state.risk_controls_status["emergency_stop_active"],
    )

    if st.session_state.risk_controls_status["stop_loss_active"]:
        st.success(
            f"✅ 停損機制啟用 ({st.session_state.risk_params['stop_loss_type']})"
        )
        st.info(
            f"停損閾值: {st.session_state.risk_params['stop_loss_percent']:.1f}%"
        )
    else:
        st.error("❌ 停損機制停用")

    # 停利控制
    st.session_state.risk_controls_status["take_profit_active"] = st.checkbox(
        "停利機制",
        value=st.session_state.risk_controls_status["take_profit_active"]
        and master_switch,
        disabled=not master_switch
        or st.session_state.risk_controls_status["emergency_stop_active"],
    )

    if st.session_state.risk_controls_status["take_profit_active"]:
        st.success(
            f"✅ 停利機制啟用 ({st.session_state.risk_params['take_profit_type']})"
        )
        st.info(
            f"停利閾值: {st.session_state.risk_params['take_profit_percent']:.1f}%"
        )
    else:
        st.error("❌ 停利機制停用")


def _show_position_controls(master_switch: bool) -> None:
    """顯示部位控制"""
    st.write("### 📊 部位控制")

    st.session_state.risk_controls_status["position_limit_active"] = st.checkbox(
        "部位限制",
        value=st.session_state.risk_controls_status["position_limit_active"]
        and master_switch,
        disabled=not master_switch
        or st.session_state.risk_controls_status["emergency_stop_active"],
    )

    if st.session_state.risk_controls_status["position_limit_active"]:
        st.success("✅ 部位限制啟用")
        st.info(
            f"最大部位: {st.session_state.risk_params['max_position_size']:.1f}%"
        )
        st.info(f"最大持倉數: {st.session_state.risk_params['max_positions']}")
    else:
        st.error("❌ 部位限制停用")

    # 行業限制控制
    st.session_state.risk_controls_status["sector_limit_active"] = st.checkbox(
        "行業曝險限制",
        value=st.session_state.risk_controls_status["sector_limit_active"]
        and master_switch,
        disabled=not master_switch
        or st.session_state.risk_controls_status["emergency_stop_active"],
    )

    if st.session_state.risk_controls_status["sector_limit_active"]:
        st.success("✅ 行業限制啟用")
        st.info(
            f"最大行業曝險: {st.session_state.risk_params['max_sector_exposure']:.1f}%"
        )
    else:
        st.error("❌ 行業限制停用")


def _show_monitoring_controls(master_switch: bool) -> None:
    """顯示風險監控控制"""
    st.write("### 📈 風險監控控制")

    # VaR 監控
    st.session_state.risk_controls_status["var_monitoring_active"] = st.checkbox(
        "VaR 監控",
        value=st.session_state.risk_controls_status["var_monitoring_active"]
        and master_switch,
        disabled=not master_switch
        or st.session_state.risk_controls_status["emergency_stop_active"],
    )

    if st.session_state.risk_controls_status["var_monitoring_active"]:
        st.success("✅ VaR 監控啟用")
        st.info(
            f"VaR 信心水準: {st.session_state.risk_params['var_confidence']:.1f}%"
        )
        st.info(f"VaR 方法: {st.session_state.risk_params['var_method']}")
    else:
        st.error("❌ VaR 監控停用")

    # 回撤保護
    st.session_state.risk_controls_status["drawdown_protection_active"] = (
        st.checkbox(
            "回撤保護",
            value=st.session_state.risk_controls_status[
                "drawdown_protection_active"
            ]
            and master_switch,
            disabled=not master_switch
            or st.session_state.risk_controls_status["emergency_stop_active"],
        )
    )

    if st.session_state.risk_controls_status["drawdown_protection_active"]:
        st.success("✅ 回撤保護啟用")
        st.info(f"最大回撤: {st.session_state.risk_params['max_drawdown']:.1f}%")
        st.info(
            f"警報閾值: {st.session_state.risk_params['alert_threshold_drawdown']:.1f}%"
        )
    else:
        st.error("❌ 回撤保護停用")

    # 相關性檢查
    st.session_state.risk_controls_status["correlation_check_active"] = st.checkbox(
        "相關性檢查",
        value=st.session_state.risk_controls_status["correlation_check_active"]
        and master_switch,
        disabled=not master_switch
        or st.session_state.risk_controls_status["emergency_stop_active"],
    )

    if st.session_state.risk_controls_status["correlation_check_active"]:
        st.success("✅ 相關性檢查啟用")
        st.info(
            f"相關性限制: {st.session_state.risk_params['correlation_limit']:.2f}"
        )
    else:
        st.error("❌ 相關性檢查停用")


def _show_monitoring_status() -> None:
    """顯示監控狀態"""
    st.write("### 🔍 監控狀態")
    master_switch = st.session_state.get("master_risk_switch", True)

    if st.session_state.risk_params["real_time_monitoring"] and master_switch:
        st.success("🟢 即時監控運行中")
        st.info("監控頻率: 每5秒")
        st.info("最後更新: " + datetime.now().strftime("%H:%M:%S"))
    else:
        st.error("🔴 即時監控已停止")


def _show_recent_actions() -> None:
    """顯示最近風控動作"""
    st.divider()
    st.write("### 📋 最近風控動作")

    # 模擬最近的風控動作
    recent_actions = [
        {
            "時間": "14:32:15",
            "動作": "停損觸發",
            "股票": "2330.TW",
            "原因": "價格跌破5%停損線",
        },
        {
            "時間": "14:28:42",
            "動作": "部位調整",
            "股票": "2454.TW",
            "原因": "超過單一部位15%限制",
        },
        {
            "時間": "14:15:33",
            "動作": "VaR警報",
            "股票": "全組合",
            "原因": "VaR超過2%閾值",
        },
        {
            "時間": "13:45:21",
            "動作": "停利執行",
            "股票": "AAPL",
            "原因": "達到10%停利目標",
        },
        {
            "時間": "13:22:18",
            "動作": "相關性警告",
            "股票": "科技股",
            "原因": "行業相關性過高",
        },
    ]

    actions_df = pd.DataFrame(recent_actions)
    st.dataframe(actions_df, use_container_width=True, hide_index=True)


def _show_manual_actions() -> None:
    """顯示手動風控動作"""
    st.write("### 🎮 手動風控動作")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🛑 全部停損", type="secondary", use_container_width=True):
            st.warning("確認執行全部停損？")

    with col2:
        if st.button("💰 全部停利", type="secondary", use_container_width=True):
            st.warning("確認執行全部停利？")

    with col3:
        if st.button("⚖️ 重新平衡", use_container_width=True):
            st.info("投資組合重新平衡中...")

    with col4:
        if st.button("🔄 重置警報", use_container_width=True):
            st.success("所有警報已重置")
