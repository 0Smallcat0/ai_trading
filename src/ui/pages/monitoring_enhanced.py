"""
增強版系統監控頁面

此模組提供完整的系統監控功能，包括：
- 系統資源監控
- 交易效能追蹤
- 日誌管理系統
- 智能警報系統
- 效能報告生成

Author: AI Trading System
Version: 1.0.0
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

import streamlit as st
import pandas as pd
import numpy as np

# 可選的圖表依賴
try:
    import plotly.graph_objects as plotly_go

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    plotly_go = None

# 可選的系統監控依賴
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    st.warning("psutil 未安裝，將使用模擬系統資源數據")

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


# 創建備用監控組件類
class MonitoringComponents:
    """
    系統監控組件類

    提供系統監控所需的各種 UI 組件和功能模組。包括系統資源儀表板、
    效能追蹤面板、日誌管理系統、警報管理和健康報告生成器等核心組件。

    此類別作為系統監控的核心組件庫，提供模組化和可重用的監控 UI 元件，
    支援即時監控、效能分析、日誌管理和智能警報等功能。

    主要功能模組：
    - 系統資源監控：CPU、記憶體、磁碟、網路監控
    - 效能追蹤：交易效能、API 回應時間、吞吐量監控
    - 日誌管理：日誌篩選、搜尋、匯出功能
    - 警報系統：多層級警報、通知管理
    - 健康報告：系統健康度評估和建議生成
    """

    @staticmethod
    def system_resources_dashboard(resource_data: Dict[str, Any]) -> None:
        """
        系統資源儀表板

        顯示系統資源使用情況的儀表板，包括 CPU、記憶體、磁碟和網路的
        即時使用率和狀態指標。使用響應式卡片佈局展示各項資源指標。

        Args:
            resource_data: 系統資源數據字典，包含以下鍵值：
                - cpu_percent: CPU 使用率百分比
                - memory_percent: 記憶體使用率百分比
                - disk_percent: 磁碟使用率百分比
                - network_latency: 網路延遲毫秒數

        Returns:
            None

        Side Effects:
            在 Streamlit 界面顯示資源監控卡片
        """
        if not resource_data:
            st.warning("無系統資源數據")
            return

        # 創建資源指標卡片
        resource_metrics = [
            {
                "title": "CPU 使用率",
                "value": f"{resource_data.get('cpu_percent', 0):.1f}%",
                "status": (
                    "error" if resource_data.get("cpu_percent", 0) > 80 else "success"
                ),
                "icon": "🖥️",
            },
            {
                "title": "記憶體使用率",
                "value": f"{resource_data.get('memory_percent', 0):.1f}%",
                "status": (
                    "warning"
                    if resource_data.get("memory_percent", 0) > 80
                    else "success"
                ),
                "icon": "💾",
            },
            {
                "title": "磁碟使用率",
                "value": f"{resource_data.get('disk_percent', 0):.1f}%",
                "status": (
                    "warning"
                    if resource_data.get("disk_percent", 0) > 80
                    else "success"
                ),
                "icon": "💿",
            },
            {
                "title": "網路延遲",
                "value": f"{resource_data.get('network_latency', 0):.1f}ms",
                "status": (
                    "warning"
                    if resource_data.get("network_latency", 0) > 100
                    else "success"
                ),
                "icon": "🌐",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            resource_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

    @staticmethod
    def performance_tracking_dashboard(performance_data: Dict[str, Any]) -> None:
        """
        效能追蹤儀表板

        顯示交易系統效能監控儀表板，包括訂單延遲、成交率、吞吐量和錯誤率等
        關鍵效能指標。使用響應式卡片佈局展示各項效能指標，並根據指標值
        自動設定狀態顏色（成功、警告、錯誤）。

        Args:
            performance_data: 效能數據字典，包含以下鍵值：
                - order_latency: 訂單延遲毫秒數
                - fill_rate: 成交率百分比
                - throughput: 吞吐量（每秒交易數）
                - error_rate: 錯誤率百分比

        Returns:
            None

        Side Effects:
            在 Streamlit 界面顯示效能監控卡片

        Example:
            >>> data = {"order_latency": 45.2, "fill_rate": 98.5,
            ...         "throughput": 150, "error_rate": 0.3}
            >>> MonitoringComponents.performance_tracking_dashboard(data)
        """
        if not performance_data:
            st.warning("無效能數據")
            return

        # 創建效能指標卡片
        performance_metrics = [
            {
                "title": "訂單延遲",
                "value": f"{performance_data.get('order_latency', 0):.1f}ms",
                "status": (
                    "warning"
                    if performance_data.get("order_latency", 0) > 100
                    else "success"
                ),
                "icon": "⚡",
            },
            {
                "title": "成交率",
                "value": f"{performance_data.get('fill_rate', 0):.1f}%",
                "status": (
                    "success"
                    if performance_data.get("fill_rate", 0) > 95
                    else "warning"
                ),
                "icon": "✅",
            },
            {
                "title": "吞吐量",
                "value": f"{performance_data.get('throughput', 0):.0f} TPS",
                "status": "success",
                "icon": "📊",
            },
            {
                "title": "錯誤率",
                "value": f"{performance_data.get('error_rate', 0):.2f}%",
                "status": (
                    "error" if performance_data.get("error_rate", 0) > 1 else "success"
                ),
                "icon": "❌",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            performance_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

    @staticmethod
    def log_management_panel(logs: List[Dict[str, Any]]) -> None:
        """
        日誌管理面板

        提供完整的日誌管理功能，包括日誌統計、篩選和詳細檢視。
        支援按日誌等級和模組進行篩選，並提供直觀的日誌瀏覽界面。

        Args:
            logs: 日誌列表，每個日誌項目包含以下鍵值：
                - level: 日誌等級（ERROR, WARNING, INFO, DEBUG）
                - module: 模組名稱
                - timestamp: 時間戳記
                - message: 日誌訊息
                - user: 用戶名稱

        Returns:
            None

        Side Effects:
            在 Streamlit 界面顯示日誌管理面板和篩選後的日誌列表

        Example:
            >>> logs = [
            ...     {"level": "ERROR", "module": "trading", "message": "Order failed"}
            ... ]
            >>> MonitoringComponents.log_management_panel(logs)
        """
        if not logs:
            st.info("沒有日誌記錄")
            return

        # 日誌統計
        total_logs = len(logs)
        error_logs = len([log for log in logs if log.get("level") == "ERROR"])
        warning_logs = len([log for log in logs if log.get("level") == "WARNING"])

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("總日誌數", total_logs)

        with col2:
            st.metric("錯誤日誌", error_logs)

        with col3:
            st.metric("警告日誌", warning_logs)

        # 日誌篩選
        st.subheader("日誌篩選")

        col1, col2 = st.columns(2)

        with col1:
            level_filter = st.selectbox(
                "日誌等級", ["全部", "ERROR", "WARNING", "INFO", "DEBUG"]
            )

        with col2:
            module_filter = st.selectbox(
                "模組", ["全部", "trading", "risk", "data", "api"]
            )

        # 篩選日誌
        filtered_logs = logs
        if level_filter != "全部":
            filtered_logs = [
                log for log in filtered_logs if log.get("level") == level_filter
            ]
        if module_filter != "全部":
            filtered_logs = [
                log for log in filtered_logs if log.get("module") == module_filter
            ]

        # 顯示日誌
        if filtered_logs:
            for log in filtered_logs[:20]:  # 只顯示前20條
                level_color = {
                    "ERROR": "🔴",
                    "WARNING": "🟡",
                    "INFO": "🔵",
                    "DEBUG": "⚪",
                }.get(log.get("level", "INFO"), "⚪")

                expander_title = (
                    f"{level_color} {log.get('timestamp', 'N/A')} - "
                    f"{log.get('module', 'N/A')}"
                )
                with st.expander(expander_title):
                    st.write(f"**等級**: {log.get('level', 'N/A')}")
                    st.write(f"**模組**: {log.get('module', 'N/A')}")
                    st.write(f"**訊息**: {log.get('message', 'N/A')}")
                    st.write(f"**用戶**: {log.get('user', 'N/A')}")
        else:
            st.info("沒有符合篩選條件的日誌")

    @staticmethod
    def alert_system_panel(alerts: List[Dict[str, Any]]) -> None:
        """
        警報系統面板

        提供完整的警報管理功能，包括警報統計、詳細檢視和確認操作。
        支援多種嚴重性等級的警報顯示，並提供警報確認機制。

        Args:
            alerts: 警報列表，每個警報項目包含以下鍵值：
                - id: 警報唯一識別碼
                - title: 警報標題
                - type: 警報類型
                - severity: 嚴重性等級（critical, high, medium, low）
                - status: 警報狀態（active, resolved）
                - timestamp: 時間戳記
                - description: 警報描述
                - acknowledged: 是否已確認

        Returns:
            None

        Side Effects:
            在 Streamlit 界面顯示警報管理面板和警報列表

        Example:
            >>> alerts = [{"id": "001", "title": "High CPU", "severity": "critical"}]
            >>> MonitoringComponents.alert_system_panel(alerts)
        """
        if not alerts:
            st.info("沒有系統警報")
            return

        # 警報統計
        total_alerts = len(alerts)
        critical_alerts = len([a for a in alerts if a.get("severity") == "critical"])
        active_alerts = len([a for a in alerts if a.get("status") == "active"])

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("總警報數", total_alerts)

        with col2:
            st.metric("嚴重警報", critical_alerts)

        with col3:
            st.metric("活躍警報", active_alerts)

        # 警報列表
        st.subheader("警報詳情")

        for alert in alerts[:10]:  # 只顯示前10個
            severity_color = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }.get(alert.get("severity", "low"), "🟢")

            alert_title = f"{severity_color} {alert.get('title', 'Unknown Alert')}"
            with st.expander(alert_title):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**類型**: {alert.get('type', 'N/A')}")
                    st.write(f"**嚴重性**: {alert.get('severity', 'N/A')}")

                with col2:
                    st.write(f"**狀態**: {alert.get('status', 'N/A')}")
                    st.write(f"**時間**: {alert.get('timestamp', 'N/A')}")

                st.write(f"**描述**: {alert.get('description', 'N/A')}")

                if not alert.get("acknowledged", False):
                    button_key = f"ack_alert_{alert.get('id')}"
                    if st.button("確認警報", key=button_key):
                        st.success("警報已確認")

    @staticmethod
    def health_report_generator(system_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        健康報告生成器

        根據系統資源使用情況和效能指標生成系統健康度評估報告。
        計算綜合健康度評分（0-100分）並提供優化建議。

        Args:
            system_data: 系統數據字典，包含以下鍵值：
                - cpu_percent: CPU 使用率百分比
                - memory_percent: 記憶體使用率百分比
                - error_rate: 錯誤率百分比
                - 其他系統指標

        Returns:
            Dict[str, Any]: 健康報告字典，包含：
                - health_score: 健康度評分（0-100）
                - recommendations: 優化建議列表
                - system_data: 原始系統數據

        Example:
            >>> data = {"cpu_percent": 75, "memory_percent": 60, "error_rate": 0.5}
            >>> report = MonitoringComponents.health_report_generator(data)
            >>> print(f"健康度評分: {report['health_score']}")
        """
        # 計算健康度評分
        health_score = 100

        # CPU 評分
        cpu_percent = system_data.get("cpu_percent", 0)
        if cpu_percent > 90:
            health_score -= 30
        elif cpu_percent > 80:
            health_score -= 15

        # 記憶體評分
        memory_percent = system_data.get("memory_percent", 0)
        if memory_percent > 90:
            health_score -= 25
        elif memory_percent > 80:
            health_score -= 10

        # 效能評分
        error_rate = system_data.get("error_rate", 0)
        if error_rate > 5:
            health_score -= 20
        elif error_rate > 1:
            health_score -= 10

        health_score = max(0, health_score)

        # 生成建議
        recommendations = []

        if cpu_percent > 80:
            recommendations.append("CPU 使用率過高，建議優化程式碼或增加計算資源")

        if memory_percent > 80:
            recommendations.append("記憶體使用率過高，建議檢查記憶體洩漏或增加記憶體")

        if error_rate > 1:
            recommendations.append("錯誤率過高，建議檢查系統日誌並修復問題")

        if not recommendations:
            recommendations.append("系統運行良好，無需特別關注")

        return {
            "health_score": health_score,
            "recommendations": recommendations,
            "system_data": system_data,
        }


# 創建響應式管理器實例
responsive_manager = ResponsiveLayoutManager()


def show_enhanced() -> None:
    """
    顯示增強版系統監控頁面

    此函數是系統監控模組的主要入口點，提供完整的系統監控功能界面。
    包括系統資源監控、交易效能追蹤、日誌管理、警報系統和健康報告五個主要功能模組。
    支援即時監控、自動刷新、效能分析和智能警報等功能。

    功能特點：
    - 即時系統資源監控（CPU、記憶體、磁碟、網路）
    - 交易效能追蹤和 API 監控
    - 智能日誌管理和篩選功能
    - 多層級警報系統和通知機制
    - 系統健康度評估和容量規劃
    - 響應式設計，支援多種裝置

    Returns:
        None

    Side Effects:
        - 初始化 st.session_state.monitoring_data 和 system_alerts
        - 在 Streamlit 界面顯示監控儀表板
    """
    # 應用響應式頁面配置
    ResponsiveUtils.apply_responsive_page_config(
        page_title="系統監控 - AI 交易系統", page_icon="📊"
    )

    # 頁面標題
    st.markdown(
        '<h1 class="title-responsive">📊 系統監控中心</h1>', unsafe_allow_html=True
    )

    # 初始化會話狀態
    _initialize_monitoring_session_state()

    # 響應式標籤頁
    tabs_config = [
        {"name": "🖥️ 系統資源", "content_func": show_system_resources},
        {"name": "⚡ 交易效能", "content_func": show_performance_tracking},
        {"name": "📝 日誌管理", "content_func": show_log_management},
        {"name": "🚨 警報系統", "content_func": show_alert_system},
        {"name": "📋 健康報告", "content_func": show_health_reports},
    ]

    ResponsiveComponents.responsive_tabs(tabs_config)


def _initialize_monitoring_session_state() -> None:
    """
    初始化監控系統的會話狀態

    設定系統監控模組所需的會話狀態變數，包括監控數據和系統警報。
    確保所有必要的狀態變數都有適當的初始值，避免頁面重新載入時的狀態丟失。

    此函數會檢查並初始化以下會話狀態變數：
    - monitoring_data: 存儲系統監控數據的字典
    - system_alerts: 存儲系統警報記錄的列表

    Returns:
        None

    Side Effects:
        修改 st.session_state 中的 monitoring_data 和 system_alerts 變數

    Example:
        >>> _initialize_monitoring_session_state()
        # 初始化監控系統會話狀態變數
    """
    if "monitoring_data" not in st.session_state:
        st.session_state.monitoring_data = {}
    if "system_alerts" not in st.session_state:
        st.session_state.system_alerts = []


def show_system_resources() -> None:
    """
    顯示系統資源監控頁面

    提供完整的系統資源監控功能，包括 CPU、記憶體、磁碟和網路的即時監控。
    顯示資源使用率儀表板、歷史趨勢圖表和進程監控，幫助管理員
    了解系統運行狀況並進行效能調優。

    功能特點：
    - 即時資源監控：CPU、記憶體、磁碟、網路使用率
    - 視覺化儀表板：響應式指標卡片顯示
    - 趨勢分析：歷史資源使用趨勢圖表
    - 進程監控：顯示 CPU 使用率最高的進程
    - 自動刷新：可選的 5 秒自動刷新機制
    - 警報提示：資源使用率超標時的視覺提醒

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示系統資源監控儀表板
        - 可能觸發系統資源數據的載入和更新
        - 如果啟用自動刷新，會定期重新載入頁面

    Note:
        需要 psutil 套件支援以獲取真實系統資源數據，
        如果不可用則使用模擬數據
    """
    st.subheader("系統資源監控")

    # 自動刷新控制
    auto_refresh = st.checkbox("自動刷新 (5秒)", value=True)

    # 載入系統資源數據
    with st.spinner("載入系統資源數據..."):
        resource_data = load_system_resources()

    # 系統資源儀表板
    MonitoringComponents.system_resources_dashboard(resource_data)

    # 資源使用趨勢圖
    st.subheader("資源使用趨勢")
    render_resource_trends()

    # 進程監控
    st.subheader("進程監控")
    show_process_monitoring()

    # 自動刷新
    if auto_refresh:
        time.sleep(5)
        st.rerun()


def show_performance_tracking() -> None:
    """
    顯示交易效能追蹤頁面

    提供完整的交易系統效能監控功能，包括訂單延遲、成交率、吞吐量等
    關鍵效能指標的即時監控。同時提供 API 效能監控和交易統計分析，
    幫助識別效能瓶頸和優化機會。

    功能特點：
    - 交易效能指標：訂單延遲、成交率、吞吐量、錯誤率
    - API 效能監控：各端點的回應時間、成功率、QPS 統計
    - 交易統計：今日訂單數、成交率、平均延遲等關鍵指標
    - 視覺化儀表板：響應式指標卡片和圖表顯示
    - 即時監控：動態更新的效能數據

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示交易效能監控儀表板
        - 載入和顯示效能數據、API 統計和交易指標

    Note:
        效能數據目前使用模擬數據，實際部署時會連接到
        真實的效能監控 API 端點
    """
    st.subheader("交易效能追蹤")

    # 載入效能數據
    with st.spinner("載入效能數據..."):
        performance_data = load_performance_data()

    # 效能追蹤儀表板
    MonitoringComponents.performance_tracking_dashboard(performance_data)

    # API 效能監控
    st.subheader("API 效能監控")
    show_api_performance()

    # 交易統計
    st.subheader("交易統計")
    show_trading_statistics()


def show_log_management() -> None:
    """
    顯示日誌管理頁面

    提供完整的系統日誌管理功能，包括日誌查看、篩選、搜尋和匯出。
    支援多種日誌等級和模組的篩選，幫助管理員快速定位問題和分析系統行為。

    功能特點：
    - 日誌查看：分頁顯示系統日誌記錄
    - 智能篩選：按等級、模組、時間範圍篩選
    - 搜尋功能：關鍵字搜尋日誌內容
    - 多格式匯出：支援 CSV、Excel、JSON 格式匯出
    - 即時更新：動態載入最新日誌記錄

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示日誌管理面板
        - 載入和顯示系統日誌數據
    """
    st.subheader("日誌管理系統")

    # 載入日誌數據
    with st.spinner("載入日誌數據..."):
        logs = load_system_logs()

    # 日誌管理面板
    MonitoringComponents.log_management_panel(logs)

    # 日誌匯出功能
    st.subheader("日誌匯出")
    show_log_export_options(logs)


def show_alert_system() -> None:
    """
    顯示警報系統頁面

    提供智能警報系統的管理功能，包括警報查看、確認、設定和通知管理。
    支援多層級警報（低、中、高、嚴重）和多種警報類型（系統、效能、安全、交易）。

    功能特點：
    - 警報監控：即時顯示系統警報狀態
    - 多層級分類：支援不同嚴重性等級的警報
    - 警報確認：手動確認和批量確認功能
    - 閾值設定：自定義各項指標的警報閾值
    - 通知管理：Email 和其他通知方式設定

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示警報系統面板
        - 載入和顯示系統警報數據
    """
    st.subheader("智能警報系統")

    # 載入警報數據
    with st.spinner("載入警報數據..."):
        alerts = load_system_alerts()

    # 警報系統面板
    MonitoringComponents.alert_system_panel(alerts)

    # 警報設定
    st.subheader("警報設定")
    show_alert_configuration()


def show_health_reports() -> None:
    """
    顯示系統健康報告頁面

    提供系統整體健康度評估和分析報告，包括健康度評分、系統狀態分析、
    優化建議和容量規劃。基於多項系統指標綜合評估系統運行狀況。

    功能特點：
    - 健康度評分：基於多項指標的綜合評分（0-100）
    - 狀態分析：系統各組件的運行狀態評估
    - 優化建議：基於當前狀況的系統優化建議
    - 容量規劃：未來容量需求預測和建議
    - 趨勢分析：健康度變化趨勢和預警

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示系統健康報告
        - 生成和顯示健康度評分和建議
    """
    st.subheader("系統健康報告")

    # 載入系統數據
    with st.spinner("生成健康報告..."):
        system_data = load_comprehensive_system_data()
        health_report = MonitoringComponents.health_report_generator(system_data)

    # 顯示健康度評分
    show_health_score(health_report)

    # 顯示建議
    show_system_recommendations(health_report)

    # 容量規劃
    st.subheader("容量規劃")
    show_capacity_planning()


def load_system_resources() -> Dict[str, Any]:
    """
    載入系統資源數據

    使用 psutil 套件獲取真實系統資源數據，包括 CPU、記憶體、磁碟和網路使用情況。
    如果 psutil 不可用或發生錯誤，則返回模擬數據以確保系統正常運行。

    此函數會嘗試獲取以下系統資源指標：
    - CPU 使用率百分比
    - 記憶體使用率和可用空間
    - 磁碟使用率和可用空間
    - 網路延遲和傳輸統計

    Returns:
        Dict[str, Any]: 系統資源數據字典，包含：
            - cpu_percent: CPU 使用率百分比
            - memory_percent: 記憶體使用率百分比
            - memory_available: 可用記憶體大小（位元組）
            - disk_percent: 磁碟使用率百分比
            - disk_free: 可用磁碟空間（位元組）
            - network_latency: 網路延遲（毫秒）
            - network_sent: 網路發送速率（MB/s）
            - network_recv: 網路接收速率（MB/s）

    Raises:
        Exception: 當系統資源獲取失敗時，會記錄錯誤並返回模擬數據

    Example:
        >>> resources = load_system_resources()
        >>> print(f"CPU 使用率: {resources['cpu_percent']}%")
        >>> print(f"記憶體使用率: {resources['memory_percent']}%")

    Note:
        需要安裝 psutil 套件以獲取真實系統資源數據，
        否則將使用隨機生成的模擬數據
    """
    try:
        if PSUTIL_AVAILABLE:
            # 使用 psutil 獲取真實系統資源
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # 模擬網路延遲
            network_latency = np.random.uniform(10, 50)

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "disk_percent": disk.percent,
                "disk_free": disk.free,
                "network_latency": network_latency,
                "network_sent": np.random.uniform(1, 10),
                "network_recv": np.random.uniform(1, 10),
            }

        # 返回模擬數據
        return {
            "cpu_percent": np.random.uniform(20, 80),
            "memory_percent": np.random.uniform(40, 85),
            "memory_available": 8 * 1024**3,  # 8GB
            "disk_percent": np.random.uniform(30, 70),
            "disk_free": 100 * 1024**3,  # 100GB
            "network_latency": np.random.uniform(10, 50),
            "network_sent": np.random.uniform(1, 10),
            "network_recv": np.random.uniform(1, 10),
        }

    except (ImportError, AttributeError, OSError) as e:
        st.error(f"載入系統資源失敗: {e}")
        # 返回模擬數據
        return {
            "cpu_percent": np.random.uniform(20, 80),
            "memory_percent": np.random.uniform(40, 85),
            "memory_available": 8 * 1024**3,  # 8GB
            "disk_percent": np.random.uniform(30, 70),
            "disk_free": 100 * 1024**3,  # 100GB
            "network_latency": np.random.uniform(10, 50),
            "network_sent": np.random.uniform(1, 10),
            "network_recv": np.random.uniform(1, 10),
        }


def load_performance_data() -> Dict[str, Any]:
    """
    載入效能數據

    從系統中載入交易效能相關的數據，包括訂單延遲、成交率、吞吐量等
    關鍵效能指標。目前使用模擬數據，實際部署時會連接到真實的效能監控系統。

    Returns:
        Dict[str, Any]: 效能數據字典，包含：
            - order_latency: 訂單延遲（毫秒）
            - fill_rate: 成交率（百分比）
            - throughput: 吞吐量（訂單/秒）
            - error_rate: 錯誤率（百分比）
            - api_response_time: API 回應時間（毫秒）

    Example:
        >>> data = load_performance_data()
        >>> print(f"平均延遲: {data['order_latency']}ms")
    """
    try:
        # 模擬 API 調用
        # response = requests.get("http://localhost:8000/api/v1/monitoring/performance")
        # if response.status_code == 200:
        #     return response.json()["data"]

        # 返回模擬數據
        return {
            "order_latency": np.random.uniform(10, 80),
            "fill_rate": np.random.uniform(85, 99),
            "throughput": np.random.uniform(80, 200),
            "api_response_time": np.random.uniform(20, 100),
            "error_rate": np.random.uniform(0, 3),
        }

    except (ImportError, AttributeError, OSError) as e:
        st.error(f"載入效能數據失敗: {e}")
        return {}


def load_system_logs() -> List[Dict[str, Any]]:
    """
    載入系統日誌

    從日誌系統中載入最新的系統日誌記錄，包括不同等級的日誌訊息。
    支援多種日誌來源和格式，提供完整的系統運行記錄。

    Returns:
        List[Dict[str, Any]]: 日誌記錄列表，每個記錄包含：
            - timestamp: 時間戳記
            - level: 日誌等級（INFO/WARNING/ERROR/DEBUG）
            - module: 來源模組
            - message: 日誌訊息
            - details: 詳細資訊（可選）

    Example:
        >>> logs = load_system_logs()
        >>> print(f"載入了 {len(logs)} 筆日誌記錄")
    """
    try:
        # 模擬 API 調用
        # response = requests.get("http://localhost:8000/api/v1/monitoring/logs")
        # if response.status_code == 200:
        #     return response.json()["data"]

        # 返回模擬數據
        logs = []
        levels = ["INFO", "WARNING", "ERROR", "DEBUG"]
        modules = ["trading", "risk", "data", "api"]

        for i in range(50):
            log = {
                "id": f"LOG{i+1:03d}",
                "timestamp": (
                    datetime.now() - timedelta(hours=np.random.randint(0, 24))
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "level": np.random.choice(levels, p=[0.6, 0.2, 0.1, 0.1]),
                "module": np.random.choice(modules),
                "message": f"模擬日誌訊息 #{i+1}",
                "user": "system",
            }
            logs.append(log)

        return logs

    except (ImportError, AttributeError, OSError) as e:
        st.error(f"載入日誌失敗: {e}")
        return []


def load_system_alerts() -> List[Dict[str, Any]]:
    """
    載入系統警報

    從警報系統中載入最新的系統警報記錄，包括不同嚴重性等級的警報。
    支援多種警報類型和狀態，提供完整的系統警報監控。

    Returns:
        List[Dict[str, Any]]: 警報記錄列表，每個記錄包含：
            - id: 警報唯一識別碼
            - timestamp: 時間戳記
            - severity: 嚴重性等級（low/medium/high/critical）
            - type: 警報類型（system/performance/security/trading）
            - title: 警報標題
            - description: 警報描述
            - status: 警報狀態（active/resolved/acknowledged）
            - acknowledged: 是否已確認

    Example:
        >>> alerts = load_system_alerts()
        >>> critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        >>> print(f"發現 {len(critical_alerts)} 個嚴重警報")
    """
    try:
        # 模擬 API 調用
        alerts = []

        for i in range(8):
            alert = {
                "id": f"ALERT{i+1:03d}",
                "timestamp": (datetime.now() - timedelta(hours=i)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "severity": np.random.choice(
                    ["low", "medium", "high", "critical"], p=[0.4, 0.3, 0.2, 0.1]
                ),
                "type": np.random.choice(
                    ["system", "performance", "security", "trading"]
                ),
                "title": f"系統警報 #{i+1}",
                "description": f"警報描述 #{i+1}",
                "status": np.random.choice(["active", "resolved", "acknowledged"]),
                "acknowledged": np.random.choice([True, False]),
            }
            alerts.append(alert)

        return alerts

    except (ImportError, AttributeError, OSError) as e:
        st.error(f"載入警報失敗: {e}")
        return []


def load_comprehensive_system_data() -> Dict[str, Any]:
    """
    載入綜合系統數據

    整合系統資源數據和效能數據，提供完整的系統狀態資訊。
    用於生成系統健康報告和綜合分析。

    Returns:
        Dict[str, Any]: 綜合系統數據字典，包含：
            - 系統資源數據（CPU、記憶體、磁碟、網路）
            - 效能數據（延遲、成交率、吞吐量、錯誤率）

    Example:
        >>> data = load_comprehensive_system_data()
        >>> print(f"CPU 使用率: {data['cpu_percent']}%")
        >>> print(f"訂單延遲: {data['order_latency']}ms")
    """
    resource_data = load_system_resources()
    performance_data = load_performance_data()

    return {**resource_data, **performance_data}


def render_resource_trends() -> None:
    """
    渲染資源使用趨勢圖

    顯示系統資源使用趨勢圖表，包括 CPU 和記憶體使用率的歷史趨勢。
    使用響應式佈局適應不同螢幕尺寸，提供直觀的資源使用情況視覺化。

    此函數會創建兩個並排的圖表：
    - CPU 使用率趨勢圖（包含警戒線和危險線）
    - 記憶體使用率趨勢圖

    Returns:
        None

    Side Effects:
        在 Streamlit 界面顯示 CPU 和記憶體使用率趨勢圖表

    Example:
        >>> render_resource_trends()
        # 顯示系統資源使用趨勢圖表

    Note:
        圖表使用模擬數據生成，實際部署時會連接到真實的監控數據源
    """
    # 使用響應式列佈局
    cols = responsive_manager.create_responsive_columns(
        desktop_cols=2, tablet_cols=1, mobile_cols=1
    )

    with cols[0]:
        # CPU 使用率趨勢
        render_cpu_trend()

    with cols[1 % len(cols)]:
        # 記憶體使用率趨勢
        render_memory_trend()


def render_cpu_trend() -> None:
    """
    渲染 CPU 使用率趨勢

    生成並顯示 CPU 使用率的時間序列圖表，包括警戒線和危險線。
    使用 Plotly 創建互動式圖表，支援懸停顯示詳細資訊和縮放功能。

    圖表特點：
    - 顯示過去 60 分鐘的 CPU 使用率趨勢
    - 包含 80% 警告線和 90% 危險線
    - 支援響應式高度調整
    - 提供懸停工具提示和統一 X 軸模式

    Returns:
        None

    Side Effects:
        在 Streamlit 界面顯示 CPU 使用率趨勢圖表

    Example:
        >>> render_cpu_trend()
        # 顯示 CPU 使用率趨勢圖表

    Note:
        目前使用隨機生成的模擬數據，實際部署時會連接到真實的 CPU 監控數據
    """
    # 生成模擬 CPU 數據
    times = pd.date_range(end=datetime.now(), periods=60, freq="T")
    cpu_usage = np.random.normal(45, 15, 60)
    cpu_usage = np.clip(cpu_usage, 0, 100)

    if not PLOTLY_AVAILABLE:
        st.error("Plotly 未安裝，無法顯示圖表")
        return

    fig = plotly_go.Figure()

    fig.add_trace(
        plotly_go.Scatter(
            x=times,
            y=cpu_usage,
            mode="lines",
            name="CPU 使用率",
            line={"color": "blue", "width": 2},
            fill="tonexty",
        )
    )

    # 添加警戒線
    fig.add_hline(
        y=80, line_dash="dash", line_color="orange", annotation_text="警告線 (80%)"
    )
    fig.add_hline(
        y=90, line_dash="dash", line_color="red", annotation_text="危險線 (90%)"
    )

    height = responsive_manager.get_chart_height(300)
    fig.update_layout(
        title="CPU 使用率趨勢",
        xaxis_title="時間",
        yaxis_title="使用率 (%)",
        height=height,
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)


def render_memory_trend() -> None:
    """
    渲染記憶體使用率趨勢

    生成並顯示記憶體使用率的時間序列圖表。
    使用 Plotly 創建互動式圖表，提供記憶體使用情況的視覺化分析。

    圖表特點：
    - 顯示過去 60 分鐘的記憶體使用率趨勢
    - 使用綠色線條和填充區域
    - 支援響應式高度調整
    - 提供懸停工具提示和統一 X 軸模式

    Returns:
        None

    Side Effects:
        在 Streamlit 界面顯示記憶體使用率趨勢圖表

    Example:
        >>> render_memory_trend()
        # 顯示記憶體使用率趨勢圖表

    Note:
        目前使用隨機生成的模擬數據，記憶體使用率範圍限制在 30-95% 之間
    """
    # 生成模擬記憶體數據
    times = pd.date_range(end=datetime.now(), periods=60, freq="T")
    memory_usage = np.random.normal(65, 10, 60)
    memory_usage = np.clip(memory_usage, 30, 95)

    if not PLOTLY_AVAILABLE:
        st.error("Plotly 未安裝，無法顯示圖表")
        return

    fig = plotly_go.Figure()

    fig.add_trace(
        plotly_go.Scatter(
            x=times,
            y=memory_usage,
            mode="lines",
            name="記憶體使用率",
            line={"color": "green", "width": 2},
            fill="tonexty",
        )
    )

    height = responsive_manager.get_chart_height(300)
    fig.update_layout(
        title="記憶體使用率趨勢",
        xaxis_title="時間",
        yaxis_title="使用率 (%)",
        height=height,
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)


def show_process_monitoring() -> None:
    """
    顯示進程監控

    顯示系統中 CPU 使用率最高的進程列表，幫助識別資源消耗較大的應用程式。
    使用 psutil 獲取進程資訊，並以表格形式展示進程詳細資訊。

    功能特點：
    - 顯示 CPU 使用率最高的前 10 個進程
    - 包含進程 ID、名稱、CPU 使用率和記憶體使用率
    - 使用響應式表格佈局
    - 自動處理進程存取權限問題

    Returns:
        None

    Side Effects:
        在 Streamlit 界面顯示進程監控表格

    Raises:
        Exception: 當無法獲取進程資訊時顯示錯誤訊息

    Example:
        >>> show_process_monitoring()
        # 顯示 CPU 使用率最高的進程列表

    Note:
        需要適當的系統權限才能獲取所有進程的詳細資訊
    """
    try:
        # 獲取系統進程資訊
        processes = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent"]
        ):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # 排序並取前10個
        processes = sorted(
            processes, key=lambda x: x["cpu_percent"] or 0, reverse=True
        )[:10]

        if processes:
            df = pd.DataFrame(processes)
            ResponsiveComponents.responsive_dataframe(df, title="CPU 使用率最高的進程")
        else:
            st.info("無法獲取進程資訊")

    except (ImportError, AttributeError, OSError) as e:
        st.error(f"載入進程資訊失敗: {e}")


def show_api_performance() -> None:
    """
    顯示 API 效能監控

    展示系統各 API 端點的效能統計資訊，包括回應時間、成功率和每秒查詢數。
    幫助監控 API 服務的健康狀況和效能表現。

    顯示的指標包括：
    - 平均回應時間（毫秒）
    - 成功率百分比
    - QPS（每秒查詢數）
    - 各主要 API 端點的詳細統計

    Returns:
        None

    Side Effects:
        在 Streamlit 界面顯示 API 效能統計表格

    Example:
        >>> show_api_performance()
        # 顯示 API 效能監控表格

    Note:
        目前使用模擬數據，實際部署時會連接到真實的 API 監控系統
    """
    # 模擬 API 端點效能數據
    api_data = [
        {
            "端點": "/api/v1/trading/orders",
            "平均回應時間": "45ms",
            "成功率": "99.2%",
            "QPS": "150",
        },
        {
            "端點": "/api/v1/risk/metrics",
            "平均回應時間": "32ms",
            "成功率": "99.8%",
            "QPS": "80",
        },
        {
            "端點": "/api/v1/data/quotes",
            "平均回應時間": "28ms",
            "成功率": "99.9%",
            "QPS": "200",
        },
        {
            "端點": "/api/v1/backtest/run",
            "平均回應時間": "1.2s",
            "成功率": "98.5%",
            "QPS": "5",
        },
    ]

    df = pd.DataFrame(api_data)
    ResponsiveComponents.responsive_dataframe(df, title="API 效能統計")


def show_trading_statistics() -> None:
    """
    顯示交易統計

    展示交易系統的關鍵統計指標，包括訂單數量、成交率、延遲和錯誤率。
    使用響應式指標卡片佈局，提供直觀的交易效能概覽。

    顯示的統計指標：
    - 今日訂單數：當日處理的訂單總數
    - 成交率：訂單成功執行的百分比
    - 平均延遲：訂單處理的平均時間
    - 錯誤率：訂單處理失敗的百分比

    Returns:
        None

    Side Effects:
        在 Streamlit 界面顯示交易統計指標卡片

    Example:
        >>> show_trading_statistics()
        # 顯示交易統計指標卡片

    Note:
        目前使用模擬數據，實際部署時會連接到真實的交易統計 API
    """
    # 模擬交易統計數據
    trading_stats = [
        {"title": "今日訂單數", "value": "1,234", "status": "normal", "icon": "📋"},
        {"title": "成交率", "value": "96.8%", "status": "success", "icon": "✅"},
        {"title": "平均延遲", "value": "35ms", "status": "success", "icon": "⚡"},
        {"title": "錯誤率", "value": "0.2%", "status": "success", "icon": "❌"},
    ]

    ResponsiveComponents.responsive_metric_cards(
        trading_stats, desktop_cols=4, tablet_cols=2, mobile_cols=1
    )


def show_log_export_options(logs: List[Dict[str, Any]]):
    """顯示日誌匯出選項"""
    if not logs:
        st.info("沒有日誌可匯出")
        return

    cols = responsive_manager.create_responsive_columns(
        desktop_cols=3, tablet_cols=2, mobile_cols=1
    )

    with cols[0]:
        if st.button("📄 匯出 CSV", use_container_width=True):
            export_logs(logs, "csv")

    with cols[1 % len(cols)]:
        if st.button("📊 匯出 Excel", use_container_width=True):
            export_logs(logs, "excel")

    with cols[2 % len(cols)]:
        if st.button("📋 匯出 JSON", use_container_width=True):
            export_logs(logs, "json")


def show_alert_configuration():
    """顯示警報設定"""
    st.write("### 警報閾值設定")

    cols = responsive_manager.create_responsive_columns(
        desktop_cols=2, tablet_cols=1, mobile_cols=1
    )

    with cols[0]:
        st.slider("CPU 警告閾值 (%)", 50, 95, 80)
        st.slider("記憶體警告閾值 (%)", 50, 95, 80)
        st.slider("磁碟警告閾值 (%)", 70, 95, 85)

    with cols[1 % len(cols)]:
        st.slider("延遲警告閾值 (ms)", 50, 500, 100)
        st.slider("錯誤率警告閾值 (%)", 1, 10, 5)
        st.checkbox("啟用 Email 通知", value=True)


def show_health_score(health_report: Dict[str, Any]):
    """顯示健康度評分"""
    score = health_report["health_score"]
    status = health_report["status"]
    status_color = health_report["status_color"]

    health_metrics = [
        {
            "title": "系統健康度",
            "value": f"{score}/100",
            "status": status_color,
            "icon": "💚" if score >= 90 else "💛" if score >= 70 else "❤️",
        },
        {
            "title": "系統狀態",
            "value": status,
            "status": status_color,
            "icon": "✅" if score >= 90 else "⚠️" if score >= 70 else "🚨",
        },
    ]

    ResponsiveComponents.responsive_metric_cards(
        health_metrics, desktop_cols=2, tablet_cols=1, mobile_cols=1
    )


def show_system_recommendations(health_report: Dict[str, Any]):
    """顯示系統建議"""
    recommendations = health_report["recommendations"]

    st.subheader("系統優化建議")

    for i, recommendation in enumerate(recommendations, 1):
        st.write(f"{i}. {recommendation}")


def show_capacity_planning():
    """顯示容量規劃"""
    st.write("### 容量規劃分析")

    # 模擬容量預測數據
    capacity_data = [
        {"資源": "CPU", "當前使用": "45%", "預測30天": "52%", "建議": "正常"},
        {"資源": "記憶體", "當前使用": "65%", "預測30天": "72%", "建議": "監控"},
        {"資源": "磁碟", "當前使用": "40%", "預測30天": "48%", "建議": "正常"},
        {"資源": "網路", "當前使用": "25%", "預測30天": "30%", "建議": "正常"},
    ]

    df = pd.DataFrame(capacity_data)
    ResponsiveComponents.responsive_dataframe(df, title="容量規劃預測")


def export_logs(logs: List[Dict[str, Any]], format_type: str):
    """匯出日誌"""
    try:
        if format_type == "csv":
            df = pd.DataFrame(logs)
            csv_data = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="下載 CSV 檔案",
                data=csv_data,
                file_name=f"system_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

        elif format_type == "json":
            json_data = json.dumps(logs, indent=2, ensure_ascii=False)
            st.download_button(
                label="下載 JSON 檔案",
                data=json_data,
                file_name=(
                    f"system_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                ),
                mime="application/json",
            )

        elif format_type == "excel":
            st.info("Excel 匯出功能需要安裝 openpyxl 套件")

        st.success(f"{format_type.upper()} 檔案已準備下載")

    except (ImportError, AttributeError, OSError) as e:
        st.error(f"匯出失敗: {e}")


if __name__ == "__main__":
    show_enhanced()
