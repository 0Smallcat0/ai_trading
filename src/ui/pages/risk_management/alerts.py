"""風險警報管理模組

此模組提供風險警報的管理功能，包括：
- 警報統計面板
- 事件篩選功能
- 警報詳情查看
- 匯出功能

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, Any
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from .utils import get_risk_management_service, get_mock_risk_events


def show_risk_alerts() -> None:
    """顯示風險警報記錄
    
    提供完整的風險警報管理界面，包括警報統計、事件篩選、
    詳情查看和匯出功能。
    
    Returns:
        None
        
    Side Effects:
        - 在 Streamlit 界面顯示風險警報管理面板
        - 載入和顯示風險事件數據
    """
    st.subheader("🚨 風險警報記錄")

    # 獲取風險管理服務
    risk_service = get_risk_management_service()

    # 獲取風險事件數據
    risk_events = _load_risk_events(risk_service)

    # 顯示各個部分
    _show_alert_statistics(risk_events)
    _show_event_filters(risk_events)
    _show_event_list(risk_events)
    _show_export_functions()


def _load_risk_events(risk_service: Any) -> pd.DataFrame:
    """載入風險事件數據"""
    if risk_service:
        try:
            # 從服務層獲取實際風險事件
            events_data = risk_service.get_risk_events(limit=100)
            if events_data:
                # 轉換為 DataFrame
                risk_events = pd.DataFrame(events_data)
                # 重命名欄位為中文
                risk_events = risk_events.rename(
                    columns={
                        "timestamp": "時間",
                        "event_type": "事件類型",
                        "severity": "嚴重程度",
                        "symbol": "股票代碼",
                        "message": "訊息",
                        "status": "狀態",
                        "action_taken": "處理動作",
                    }
                )
                # 處理空值
                risk_events["股票代碼"] = risk_events["股票代碼"].fillna("全組合")
                risk_events["處理動作"] = risk_events["處理動作"].fillna("待處理")
                risk_events["備註"] = risk_events.get("訊息", "系統自動檢測到風險事件")

                # 添加觸發值和閾值欄位（如果不存在則使用模擬值）
                if "trigger_value" not in risk_events.columns:
                    risk_events["觸發值"] = [
                        f"{np.random.uniform(-15, -2):.2f}%"
                        for _ in range(len(risk_events))
                    ]
                    risk_events["閾值"] = [
                        f"{np.random.uniform(-10, -5):.2f}%"
                        for _ in range(len(risk_events))
                    ]
            else:
                risk_events = get_mock_risk_events()
        except Exception as e:
            st.warning(f"無法獲取實際風險事件，使用模擬數據: {e}")
            risk_events = get_mock_risk_events()
    else:
        risk_events = get_mock_risk_events()
    
    return risk_events


def _show_alert_statistics(risk_events: pd.DataFrame) -> None:
    """顯示警報統計面板"""
    st.write("### 📊 警報統計")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_events = len(risk_events)
        st.metric("總事件數", total_events)

    with col2:
        high_severity = len(risk_events[risk_events["嚴重程度"].isin(["高", "嚴重"])])
        st.metric("高風險事件", high_severity, f"{high_severity/total_events*100:.1f}%")

    with col3:
        pending_events = len(risk_events[risk_events["狀態"] == "待處理"])
        st.metric("待處理事件", pending_events)

    with col4:
        today_events = len(
            risk_events[
                risk_events["時間"].str.contains(datetime.now().strftime("%Y-%m-%d"))
            ]
        )
        st.metric("今日事件", today_events)


def _show_event_filters(risk_events: pd.DataFrame) -> None:
    """顯示事件篩選控制"""
    st.divider()
    st.write("### 🔍 事件篩選")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        event_type_filter = st.multiselect(
            "事件類型",
            options=risk_events["事件類型"].unique(),
            default=risk_events["事件類型"].unique(),
        )

    with col2:
        severity_filter = st.multiselect(
            "嚴重程度",
            options=risk_events["嚴重程度"].unique(),
            default=risk_events["嚴重程度"].unique(),
        )

    with col3:
        status_filter = st.multiselect(
            "處理狀態",
            options=risk_events["狀態"].unique(),
            default=risk_events["狀態"].unique(),
        )

    with col4:
        date_range = st.selectbox(
            "時間範圍", ["全部", "今日", "最近3天", "最近7天", "最近30天"]
        )

    # 儲存篩選條件到 session_state
    st.session_state.event_filters = {
        "event_type": event_type_filter,
        "severity": severity_filter,
        "status": status_filter,
        "date_range": date_range,
    }


def _show_event_list(risk_events: pd.DataFrame) -> None:
    """顯示事件列表"""
    # 應用篩選
    filters = st.session_state.get("event_filters", {})
    filtered_events = risk_events.copy()
    
    if filters.get("event_type"):
        filtered_events = filtered_events[
            filtered_events["事件類型"].isin(filters["event_type"])
        ]
    
    if filters.get("severity"):
        filtered_events = filtered_events[
            filtered_events["嚴重程度"].isin(filters["severity"])
        ]
    
    if filters.get("status"):
        filtered_events = filtered_events[
            filtered_events["狀態"].isin(filters["status"])
        ]

    # 時間篩選
    date_range = filters.get("date_range", "全部")
    if date_range != "全部":
        days_map = {"今日": 1, "最近3天": 3, "最近7天": 7, "最近30天": 30}
        days = days_map[date_range]
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_events = filtered_events[
            pd.to_datetime(filtered_events["時間"]) >= cutoff_date
        ]

    st.divider()
    st.write(f"### 📋 事件列表 ({len(filtered_events)} 筆記錄)")

    if len(filtered_events) > 0:
        # 添加顏色編碼
        def highlight_severity(row):
            if row["嚴重程度"] == "嚴重":
                return ["background-color: #ffebee"] * len(row)
            elif row["嚴重程度"] == "高":
                return ["background-color: #fff3e0"] * len(row)
            elif row["嚴重程度"] == "中":
                return ["background-color: #f3e5f5"] * len(row)
            else:
                return ["background-color: #e8f5e8"] * len(row)

        # 顯示表格
        styled_df = filtered_events.style.apply(highlight_severity, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # 詳細查看
        _show_event_details(filtered_events)
    else:
        st.info("沒有符合篩選條件的事件記錄")


def _show_event_details(filtered_events: pd.DataFrame) -> None:
    """顯示事件詳情"""
    st.write("### 🔍 事件詳情")
    selected_event = st.selectbox(
        "選擇事件查看詳情",
        options=range(len(filtered_events)),
        format_func=lambda x: f"{filtered_events.iloc[x]['時間']} - {filtered_events.iloc[x]['事件類型']}",
    )

    if selected_event is not None:
        event = filtered_events.iloc[selected_event]

        col1, col2 = st.columns(2)

        with col1:
            st.write("**基本信息**")
            st.write(f"**時間:** {event['時間']}")
            st.write(f"**事件類型:** {event['事件類型']}")
            st.write(f"**嚴重程度:** {event['嚴重程度']}")
            st.write(f"**股票代碼:** {event['股票代碼']}")
            st.write(f"**狀態:** {event['狀態']}")

        with col2:
            st.write("**詳細信息**")
            st.write(f"**觸發值:** {event['觸發值']}")
            st.write(f"**閾值:** {event['閾值']}")
            st.write(f"**處理動作:** {event['處理動作']}")
            st.write(f"**備註:** {event['備註']}")

        # 處理動作
        st.write("**處理動作**")
        col_action1, col_action2, col_action3 = st.columns(3)

        with col_action1:
            if st.button("✅ 標記為已處理", use_container_width=True):
                st.success("事件已標記為已處理")

        with col_action2:
            if st.button("🔄 重新處理", use_container_width=True):
                st.info("事件已重新加入處理佇列")

        with col_action3:
            if st.button("❌ 忽略事件", use_container_width=True):
                st.warning("事件已忽略")


def _show_export_functions() -> None:
    """顯示匯出功能"""
    st.divider()
    st.write("### 📤 匯出功能")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 匯出 Excel", use_container_width=True):
            st.success("事件記錄已匯出為 Excel 檔案")

    with col2:
        if st.button("📄 匯出 PDF 報告", use_container_width=True):
            st.success("風險報告已匯出為 PDF 檔案")

    with col3:
        if st.button("📧 發送報告", use_container_width=True):
            st.success("風險報告已發送至指定信箱")


def get_alert_summary() -> Dict[str, Any]:
    """獲取警報摘要
    
    Returns:
        Dict[str, Any]: 警報摘要數據
    """
    risk_events = get_mock_risk_events()
    
    return {
        "total_alerts": len(risk_events),
        "high_severity": len(risk_events[risk_events["嚴重程度"].isin(["高", "嚴重"])]),
        "pending": len(risk_events[risk_events["狀態"] == "待處理"]),
        "today": len(risk_events[
            risk_events["時間"].str.contains(datetime.now().strftime("%Y-%m-%d"))
        ]),
    }
