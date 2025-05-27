"""增強版風險管理頁面

此模組提供完整的風險管理功能，包括：
- 風險參數設定介面
- 實時風險監控儀表板
- 風險控制機制
- 日誌與警報管理

Author: AI Trading System
Version: 1.0.0
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import streamlit as st
import pandas as pd
import numpy as np

# 導入響應式設計組件
try:
    from ..responsive import (
        ResponsiveUtils,
        ResponsiveComponents,
        ResponsiveLayoutManager,
    )
except ImportError:
    # 備用導入
    from src.ui.responsive import (
        ResponsiveUtils,
        ResponsiveComponents,
        ResponsiveLayoutManager,
    )


# 創建備用 UI 組件類（未使用，保留以備將來擴展）
class UIComponents:  # pylint: disable=too-few-public-methods
    """備用 UI 組件類"""

    @staticmethod
    def show_info(message: str) -> None:
        """顯示資訊訊息"""
        st.info(message)


# 創建備用風險管理組件類
class RiskComponents:
    """風險管理組件類

    提供風險管理系統所需的各種 UI 組件和功能模組。包括風險參數表單、
    風險指標儀表板、監控圖表、控制面板和警報管理等核心組件。

    此類別作為風險管理系統的核心組件庫，提供模組化和可重用的 UI 元件，
    支援完整的風險管理流程，從參數設定到即時監控和警報處理。

    主要功能模組：
    - 風險參數表單：停損停利、部位限制、VaR 設定等
    - 風險指標儀表板：即時風險指標顯示和狀態監控
    - 監控圖表：風險趨勢分析和視覺化展示
    - 控制面板：風險控制機制的狀態管理
    - 警報管理：風險警報的顯示、確認和處理

    設計原則：
    - 模組化設計：每個組件獨立且可重用
    - 響應式佈局：適應不同裝置螢幕尺寸
    - 即時更新：支援動態數據更新和刷新
    - 用戶友善：直觀的操作界面和清晰的資訊展示
    """

    @staticmethod
    def risk_parameter_form(
        current_params: Dict[str, Any], form_key: str
    ) -> Optional[Dict[str, Any]]:
        """顯示風險參數表單

        Args:
            current_params: 當前參數
            form_key: 表單鍵值

        Returns:
            Optional[Dict[str, Any]]: 更新後的參數，如果沒有更新則返回 None
        """
        with st.form(form_key):
            st.subheader("風險參數設定")

            col1, col2 = st.columns(2)

            with col1:
                stop_loss_type = st.selectbox(
                    "停損類型",
                    ["percent", "amount"],
                    index=0 if current_params.get("stop_loss_type") == "percent" else 1,
                    format_func=lambda x: "百分比" if x == "percent" else "金額",
                )

                stop_loss_value = st.number_input(
                    "停損值 (%)" if stop_loss_type == "percent" else "停損值 ($)",
                    min_value=0.1,
                    max_value=50.0,
                    value=float(current_params.get("stop_loss_value", 5.0)),
                    step=0.1,
                )

                max_position_size = st.number_input(
                    "最大單一部位 (%)",
                    min_value=1.0,
                    max_value=100.0,
                    value=float(current_params.get("max_position_size", 10.0)),
                    step=1.0,
                )

            with col2:
                take_profit_type = st.selectbox(
                    "停利類型",
                    ["percent", "amount"],
                    index=(
                        0 if current_params.get("take_profit_type") == "percent" else 1
                    ),
                    format_func=lambda x: "百分比" if x == "percent" else "金額",
                )

                take_profit_value = st.number_input(
                    "停利值 (%)" if take_profit_type == "percent" else "停利值 ($)",
                    min_value=0.1,
                    max_value=100.0,
                    value=float(current_params.get("take_profit_value", 10.0)),
                    step=0.1,
                )

                max_portfolio_risk = st.number_input(
                    "最大投資組合風險 (%)",
                    min_value=0.1,
                    max_value=10.0,
                    value=float(current_params.get("max_portfolio_risk", 2.0)),
                    step=0.1,
                )

            var_confidence_level = st.slider(
                "VaR 信心水準 (%)",
                min_value=90.0,
                max_value=99.9,
                value=float(current_params.get("var_confidence_level", 95.0)),
                step=0.1,
            )

            max_correlation = st.slider(
                "最大相關性",
                min_value=0.1,
                max_value=1.0,
                value=float(current_params.get("max_correlation", 0.7)),
                step=0.05,
            )

            submitted = st.form_submit_button("💾 保存參數", use_container_width=True)

            if submitted:
                return {
                    "stop_loss_type": stop_loss_type,
                    "stop_loss_value": stop_loss_value,
                    "take_profit_type": take_profit_type,
                    "take_profit_value": take_profit_value,
                    "max_position_size": max_position_size,
                    "max_portfolio_risk": max_portfolio_risk,
                    "var_confidence_level": var_confidence_level,
                    "max_correlation": max_correlation,
                }

        return None

    @staticmethod
    def risk_metrics_dashboard(metrics: Dict[str, Any]) -> None:
        """
        顯示風險指標儀表板

        Args:
            metrics: 風險指標數據
        """
        if not metrics:
            st.warning("無風險指標數據")
            return

        # 創建指標卡片
        metric_cards = [
            {
                "title": "投資組合價值",
                "value": f"${metrics.get('portfolio_value', 0):,.0f}",
                "status": "info",
                "icon": "💰",
            },
            {
                "title": "當前回撤",
                "value": f"{metrics.get('current_drawdown', 0):.2%}",
                "status": (
                    "error"
                    if abs(metrics.get("current_drawdown", 0)) > 0.05
                    else "success"
                ),
                "icon": "📉",
            },
            {
                "title": "VaR (95%)",
                "value": f"{metrics.get('var_95', 0):.2%}",
                "status": (
                    "warning" if abs(metrics.get("var_95", 0)) > 0.03 else "success"
                ),
                "icon": "⚠️",
            },
            {
                "title": "夏普比率",
                "value": f"{metrics.get('sharpe_ratio', 0):.2f}",
                "status": (
                    "success" if metrics.get("sharpe_ratio", 0) > 1.0 else "warning"
                ),
                "icon": "📊",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            metric_cards, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

    @staticmethod
    def risk_monitoring_charts(metrics: Dict[str, Any]) -> None:
        """
        顯示風險監控圖表

        Args:
            metrics: 風險指標數據
        """
        if not metrics:
            st.warning("無圖表數據")
            return

        # 簡化的圖表顯示
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("風險分佈")
            # 創建簡單的風險分佈圖
            risk_data = pd.DataFrame(
                {
                    "指標": ["波動率", "最大回撤", "集中度風險", "平均相關性"],
                    "數值": [
                        metrics.get("volatility", 0),
                        abs(metrics.get("max_drawdown", 0)),
                        metrics.get("concentration_risk", 0),
                        metrics.get("avg_correlation", 0),
                    ],
                }
            )
            st.bar_chart(risk_data.set_index("指標"))

        with col2:
            st.subheader("風險趨勢")
            # 創建模擬的時間序列數據
            dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
            trend_data = pd.DataFrame(
                {
                    "VaR": np.random.normal(-0.02, 0.005, 30),
                    "回撤": np.random.normal(-0.03, 0.01, 30),
                },
                index=dates,
            )
            st.line_chart(trend_data)

    @staticmethod
    def risk_control_panel(control_status: Dict[str, Any]) -> None:
        """
        顯示風險控制面板

        Args:
            control_status: 風控狀態數據
        """
        if not control_status:
            st.warning("無風控狀態數據")
            return

        st.subheader("風控機制狀態")

        for control_name, status_info in control_status.items():
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(f"**{control_name}**")

            with col2:
                enabled = status_info.get("enabled", False)
                st.write("🟢 啟用" if enabled else "🔴 停用")

            with col3:
                status = status_info.get("status", "unknown")
                status_color = {
                    "active": "🟢",
                    "warning": "🟡",
                    "error": "🔴",
                    "standby": "⚪",
                }.get(status, "❓")
                st.write(f"{status_color} {status}")

    @staticmethod
    def risk_alerts_panel(alerts: List[Dict[str, Any]]) -> None:
        """
        顯示風險警報面板

        Args:
            alerts: 警報列表
        """
        if not alerts:
            st.info("目前沒有風險警報")
            return

        st.subheader("風險警報")

        # 警報統計
        total_alerts = len(alerts)
        high_severity = len([a for a in alerts if a.get("severity") == "高"])
        unacknowledged = len([a for a in alerts if not a.get("acknowledged", False)])

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("總警報數", total_alerts)

        with col2:
            st.metric("高嚴重性", high_severity)

        with col3:
            st.metric("未確認", unacknowledged)

        # 警報列表
        for alert in alerts[:5]:  # 只顯示前5個
            severity_color = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(
                alert.get("severity", "低"), "🟢"
            )

            with st.expander(f"{severity_color} {alert.get('title', 'Unknown Alert')}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**類型**: {alert.get('alert_type', 'N/A')}")
                    st.write(f"**標的**: {alert.get('symbol', 'N/A')}")

                with col2:
                    st.write(f"**狀態**: {alert.get('status', 'N/A')}")
                    st.write(f"**時間**: {alert.get('created_at', 'N/A')}")

                if not alert.get("acknowledged", False):
                    if st.button(f"確認警報", key=f"ack_{alert.get('id')}"):
                        st.success("警報已確認")


# 創建響應式管理器實例
responsive_manager = ResponsiveLayoutManager()


def show_enhanced() -> None:
    """顯示增強版風險管理頁面

    此函數是風險管理模組的主要入口點，提供完整的風險管理功能界面。
    包括風險參數設定、實時監控、風控機制和警報管理四個主要功能模組。
    """
    # 應用響應式頁面配置
    ResponsiveUtils.apply_responsive_page_config(
        page_title="風險管理 - AI 交易系統", page_icon="🛡️"
    )

    # 頁面標題
    st.markdown(
        '<h1 class="title-responsive">🛡️ 風險管理系統</h1>', unsafe_allow_html=True
    )

    # 初始化會話狀態
    _initialize_session_state()

    # 響應式標籤頁
    tabs_config = [
        {"name": "⚙️ 風險參數", "content_func": show_risk_parameters},
        {"name": "📊 實時監控", "content_func": show_risk_monitoring},
        {"name": "🛡️ 風控機制", "content_func": show_risk_controls},
        {"name": "🚨 警報管理", "content_func": show_risk_alerts},
    ]

    ResponsiveComponents.responsive_tabs(tabs_config)


def _initialize_session_state() -> None:
    """初始化會話狀態

    設定風險管理模組所需的會話狀態變數，包括風險參數、指標和警報。
    """
    if "risk_parameters" not in st.session_state:
        st.session_state.risk_parameters = get_default_risk_parameters()
    if "risk_metrics" not in st.session_state:
        st.session_state.risk_metrics = {}
    if "risk_alerts" not in st.session_state:
        st.session_state.risk_alerts = []


def show_risk_parameters() -> None:
    """顯示風險參數設定頁面

    提供風險參數的設定、保存、匯入匯出等功能。
    包括停損停利設定、部位限制、VaR 參數等風險控制參數。
    """
    st.subheader("風險參數設定")

    # 載入當前參數
    with st.spinner("載入風險參數..."):
        current_params = load_risk_parameters()

    # 風險參數表單
    form_data = RiskComponents.risk_parameter_form(current_params, "risk_params_form")

    if form_data:
        # 保存參數
        with st.spinner("保存風險參數..."):
            success = save_risk_parameters(form_data)

            if success:
                st.success("風險參數已成功保存！")
                st.session_state.risk_parameters = form_data

                # 顯示參數摘要
                show_parameter_summary(form_data)
            else:
                st.error("保存風險參數失敗，請重試")

    # 參數預設值和匯入/匯出
    st.subheader("參數管理")

    cols = responsive_manager.create_responsive_columns(
        desktop_cols=3, tablet_cols=2, mobile_cols=1
    )

    with cols[0]:
        if st.button("🔄 重置為預設值", use_container_width=True):
            st.session_state.risk_parameters = get_default_risk_parameters()
            st.success("已重置為預設參數")
            st.rerun()

    with cols[1 % len(cols)]:
        if st.button("📤 匯出參數", use_container_width=True):
            export_parameters(current_params)

    with cols[2 % len(cols)]:
        uploaded_file = st.file_uploader("📥 匯入參數", type=["json"])
        if uploaded_file:
            import_parameters(uploaded_file)


def show_risk_monitoring() -> None:
    """
    顯示實時風險監控

    提供即時風險監控功能，包括風險指標儀表板、趨勢分析圖表和自動刷新機制。
    監控投資組合的各項風險指標，如 VaR、回撤、波動率等，並提供視覺化的
    風險趨勢分析和警報提示。

    功能特點：
    - 即時風險指標監控（VaR、回撤、夏普比率等）
    - 風險趨勢圖表和歷史分析
    - 自動刷新機制，確保數據即時性
    - 響應式儀表板設計
    - 風險警報和閾值監控

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示風險監控儀表板和圖表
        - 可能觸發自動刷新機制更新數據
    """
    st.subheader("實時風險監控儀表板")

    # 自動刷新控制
    auto_refresh = st.checkbox("自動刷新 (30秒)", value=True)

    if auto_refresh:
        # 使用 st.empty() 創建可更新的容器
        placeholder = st.empty()

        # 模擬實時更新
        with placeholder.container():
            render_risk_dashboard()
    else:
        render_risk_dashboard()

    # 手動刷新按鈕
    if st.button("🔄 立即刷新", use_container_width=True):
        st.rerun()


def render_risk_dashboard() -> None:
    """
    渲染風險監控儀表板

    生成並顯示完整的風險管理儀表板，包括風險指標卡片、趨勢圖表、
    警報狀態和控制面板。提供即時的風險監控視覺化界面。

    功能特點：
    - 即時風險指標顯示（VaR、回撤、夏普比率等）
    - 響應式卡片佈局，適應不同螢幕尺寸
    - 風險趨勢圖表和歷史分析
    - 警報狀態指示和通知

    Returns:
        None

    Side Effects:
        在 Streamlit 界面渲染風險儀表板組件
    """
    # 載入風險指標
    with st.spinner("載入風險指標..."):
        risk_metrics = load_risk_metrics()

    # 風險指標儀表板
    RiskComponents.risk_metrics_dashboard(risk_metrics)

    # 風險監控圖表
    st.subheader("風險分析圖表")
    RiskComponents.risk_monitoring_charts(risk_metrics)

    # 風險評估摘要
    st.subheader("風險評估摘要")
    show_risk_assessment(risk_metrics)


def show_risk_controls() -> None:
    """
    顯示風險控制機制

    提供風險控制機制的管理界面，包括風險限制設定、緊急停損控制、
    部位限制管理等功能。允許用戶即時調整風險控制參數。

    功能特點：
    - 風險限制設定（VaR 限制、最大回撤等）
    - 緊急停損控制開關和參數設定
    - 部位限制管理（單一部位、總部位限制）
    - 即時風險控制狀態顯示

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示風險控制設定面板
        - 可能更新風險控制參數到系統配置
    """
    st.subheader("風險控制機制")

    # 載入風控狀態
    with st.spinner("載入風控狀態..."):
        control_status = load_risk_control_status()

    # 風險控制面板
    RiskComponents.risk_control_panel(control_status)

    # 風控機制詳細設定
    st.subheader("風控機制設定")

    # 使用響應式列佈局
    cols = responsive_manager.create_responsive_columns(
        desktop_cols=2, tablet_cols=1, mobile_cols=1
    )

    with cols[0]:
        show_stop_loss_controls()

    with cols[1 % len(cols)]:
        show_position_limit_controls()

    # 緊急控制
    st.subheader("緊急控制")
    show_emergency_controls()


def show_risk_alerts() -> None:
    """
    顯示風險警報管理

    提供風險警報系統的管理界面，包括警報查看、確認、設定和通知管理。
    支援多層級警報（低、中、高）和多種警報類型（VaR、回撤、部位等）。

    功能特點：
    - 風險警報列表顯示和狀態管理
    - 警報確認和批量操作功能
    - 警報閾值設定和通知配置
    - 即時警報狀態監控

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示風險警報管理面板
        - 載入和顯示系統風險警報數據
    """
    st.subheader("風險警報管理")

    # 載入警報數據
    with st.spinner("載入警報數據..."):
        alerts = load_risk_alerts()

    # 風險警報面板
    RiskComponents.risk_alerts_panel(alerts)

    # 警報設定
    st.subheader("警報設定")
    show_alert_settings()


def get_default_risk_parameters() -> Dict[str, Any]:
    """
    獲取預設風險參數

    返回系統預設的風險管理參數配置，包括停損停利設定、部位限制、
    VaR 配置等核心風險控制參數。

    Returns:
        Dict[str, Any]: 預設風險參數字典，包含：
            - stop_loss_type: 停損類型（percent）
            - stop_loss_value: 停損百分比（5.0%）
            - take_profit_type: 停利類型（percent）
            - take_profit_value: 停利百分比（10.0%）
            - max_position_size: 最大部位大小（10.0%）
            - max_portfolio_risk: 最大投資組合風險（2.0%）
            - var_confidence_level: VaR 信心水準（95.0%）
            - max_correlation: 最大相關性（0.7）
    """
    return {
        "stop_loss_type": "percent",
        "stop_loss_value": 5.0,
        "take_profit_type": "percent",
        "take_profit_value": 10.0,
        "max_position_size": 10.0,
        "max_portfolio_risk": 2.0,
        "var_confidence_level": 95.0,
        "max_correlation": 0.7,
    }


def load_risk_parameters() -> Dict[str, Any]:
    """
    載入風險參數

    從系統配置中載入當前的風險管理參數設定。如果載入失敗，
    則返回預設的風險參數配置。

    Returns:
        Dict[str, Any]: 風險參數字典，包含所有風險控制設定

    Raises:
        Exception: 當載入過程中發生錯誤時

    Example:
        >>> params = load_risk_parameters()
        >>> print(f"停損設定: {params['stop_loss_value']}%")
    """
    try:
        # 模擬 API 調用
        # response = requests.get("http://localhost:8000/api/v1/risk/parameters")
        # if response.status_code == 200:
        #     return response.json()["data"]

        # 返回模擬數據
        return st.session_state.get("risk_parameters", get_default_risk_parameters())

    except Exception as e:
        st.error(f"載入風險參數失敗: {e}")
        return get_default_risk_parameters()


def save_risk_parameters(params: Dict[str, Any]) -> bool:
    """
    保存風險參數

    將風險參數保存到後端系統。目前使用模擬實作，
    在實際部署時會連接到真實的 API 端點。

    Args:
        params: 風險參數字典，包含各種風險控制設定

    Returns:
        bool: 保存成功返回 True，失敗返回 False

    Raises:
        Exception: 當保存過程中發生錯誤時
    """
    try:
        # 驗證參數
        if not params:
            st.error("參數不能為空")
            return False

        # 模擬 API 調用
        # response = requests.post(
        #     "http://localhost:8000/api/v1/risk/parameters",
        #     json=params
        # )
        # return response.status_code == 200

        # 模擬保存成功
        st.info(f"正在保存參數: {len(params)} 個設定項目")
        time.sleep(1)  # 模擬網路延遲
        return True

    except Exception as e:
        st.error(f"保存風險參數失敗: {e}")
        return False


def load_risk_metrics() -> Dict[str, Any]:
    """載入風險指標"""
    try:
        # 模擬 API 調用
        # response = requests.get("http://localhost:8000/api/v1/risk/metrics")
        # if response.status_code == 200:
        #     return response.json()["data"]

        # 返回模擬數據
        return generate_mock_risk_metrics()

    except Exception as e:
        st.error(f"載入風險指標失敗: {e}")
        return {}


def generate_mock_risk_metrics() -> Dict[str, Any]:
    """生成模擬風險指標"""
    return {
        "portfolio_value": 1000000,
        "current_drawdown": np.random.uniform(-0.08, -0.01),
        "var_95": np.random.uniform(-0.04, -0.02),
        "sharpe_ratio": np.random.uniform(0.8, 2.0),
        "volatility": np.random.uniform(0.12, 0.25),
        "max_drawdown": np.random.uniform(-0.15, -0.05),
        "concentration_risk": np.random.uniform(0.25, 0.40),
        "avg_correlation": np.random.uniform(0.3, 0.7),
    }


def load_risk_control_status() -> Dict[str, Any]:
    """載入風控機制狀態"""
    try:
        # 模擬 API 調用
        return {
            "stop_loss": {"enabled": True, "status": "active"},
            "position_limit": {"enabled": True, "status": "active"},
            "var_monitoring": {"enabled": True, "status": "warning"},
            "emergency_stop": {"enabled": True, "status": "standby"},
        }

    except Exception as e:
        st.error(f"載入風控狀態失敗: {e}")
        return {}


def load_risk_alerts() -> List[Dict[str, Any]]:
    """載入風險警報"""
    try:
        # 模擬 API 調用
        alerts = []

        for i in range(5):
            alert = {
                "id": f"alert_{i+1}",
                "alert_type": np.random.choice(["VaR超限", "回撤警告", "部位超限"]),
                "severity": np.random.choice(["低", "中", "高"]),
                "title": f"風險警報 #{i+1}",
                "symbol": np.random.choice(["2330.TW", "AAPL", "全組合"]),
                "status": np.random.choice(["待處理", "處理中", "已解決"]),
                "created_at": (datetime.now() - timedelta(hours=i)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "acknowledged": np.random.choice([True, False]),
            }
            alerts.append(alert)

        return alerts

    except Exception as e:
        st.error(f"載入風險警報失敗: {e}")
        return []


def show_parameter_summary(params: Dict[str, Any]):
    """顯示參數摘要"""
    st.subheader("參數摘要")

    summary_data = [
        {"參數": "停損類型", "值": params.get("stop_loss_type", "N/A")},
        {"參數": "停損值", "值": f"{params.get('stop_loss_value', 0):.1f}%"},
        {"參數": "最大部位", "值": f"{params.get('max_position_size', 0):.1f}%"},
        {"參數": "VaR信心水準", "值": f"{params.get('var_confidence_level', 0):.1f}%"},
    ]

    df = pd.DataFrame(summary_data)
    ResponsiveComponents.responsive_dataframe(df, title="當前參數設定")


def show_risk_assessment(metrics: Dict[str, Any]):
    """顯示風險評估"""
    # 計算風險評分
    risk_score = calculate_risk_score(metrics)

    # 風險等級
    if risk_score >= 80:
        risk_level = "低風險"
        risk_color = "success"
    elif risk_score >= 60:
        risk_level = "中等風險"
        risk_color = "warning"
    else:
        risk_level = "高風險"
        risk_color = "error"

    # 顯示風險評估
    assessment_metrics = [
        {
            "title": "風險評分",
            "value": f"{risk_score}/100",
            "status": risk_color,
            "icon": "📊",
        },
        {"title": "風險等級", "value": risk_level, "status": risk_color, "icon": "🎯"},
    ]

    ResponsiveComponents.responsive_metric_cards(
        assessment_metrics, desktop_cols=2, tablet_cols=1, mobile_cols=1
    )


def calculate_risk_score(metrics: Dict[str, Any]) -> int:
    """計算風險評分"""
    score = 100

    # 根據各項指標調整評分
    if abs(metrics.get("current_drawdown", 0)) > 0.1:
        score -= 20
    elif abs(metrics.get("current_drawdown", 0)) > 0.05:
        score -= 10

    if abs(metrics.get("var_95", 0)) > 0.03:
        score -= 15

    if metrics.get("concentration_risk", 0) > 0.35:
        score -= 15

    if metrics.get("avg_correlation", 0) > 0.7:
        score -= 10

    return max(0, score)


def show_stop_loss_controls():
    """顯示停損控制設定"""
    st.write("### 停損控制")

    enabled = st.checkbox("啟用自動停損", value=True)

    if enabled:
        stop_type = st.selectbox("停損類型", ["百分比停損", "ATR停損", "追蹤停損"])

        if stop_type == "百分比停損":
            st.slider("停損百分比", 1.0, 20.0, 5.0, 0.5)
        elif stop_type == "ATR停損":
            st.slider("ATR倍數", 1.0, 5.0, 2.0, 0.1)
        else:
            st.slider("追蹤停損百分比", 1.0, 10.0, 3.0, 0.5)


def show_position_limit_controls():
    """顯示部位限制控制"""
    st.write("### 部位限制")

    st.slider("最大單一部位", 1.0, 50.0, 10.0, 1.0)
    st.slider("最大行業曝險", 10.0, 100.0, 30.0, 5.0)
    st.slider("最大相關性", 0.1, 1.0, 0.7, 0.05)


def show_emergency_controls():
    """顯示緊急控制"""
    st.warning("⚠️ 緊急控制功能將立即停止所有交易活動")

    cols = responsive_manager.create_responsive_columns(
        desktop_cols=2, tablet_cols=1, mobile_cols=1
    )

    with cols[0]:
        if st.button("🛑 緊急停止", type="primary", use_container_width=True):
            st.error("緊急停止已觸發！所有交易已暫停。")

    with cols[1 % len(cols)]:
        if st.button("🔄 恢復交易", use_container_width=True):
            st.success("交易已恢復正常。")


def show_alert_settings():
    """顯示警報設定"""
    cols = responsive_manager.create_responsive_columns(
        desktop_cols=2, tablet_cols=1, mobile_cols=1
    )

    with cols[0]:
        st.write("### 警報閾值")
        st.slider("VaR警報閾值 (%)", 1.0, 10.0, 3.0, 0.1)
        st.slider("回撤警報閾值 (%)", 5.0, 30.0, 10.0, 1.0)

    with cols[1 % len(cols)]:
        st.write("### 通知設定")
        st.checkbox("Email通知", value=True)
        st.checkbox("SMS通知", value=False)
        st.checkbox("系統通知", value=True)


def export_parameters(params: Dict[str, Any]):
    """匯出參數"""
    try:
        params_json = json.dumps(params, indent=2, ensure_ascii=False)
        st.download_button(
            label="下載參數檔案",
            data=params_json,
            file_name=f"risk_parameters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )
        st.success("參數檔案已準備下載")
    except Exception as e:
        st.error(f"匯出參數失敗: {e}")


def import_parameters(uploaded_file):
    """匯入參數"""
    try:
        params = json.load(uploaded_file)
        st.session_state.risk_parameters = params
        st.success("參數已成功匯入！")
        st.rerun()
    except Exception as e:
        st.error(f"匯入參數失敗: {e}")


if __name__ == "__main__":
    show_enhanced()
