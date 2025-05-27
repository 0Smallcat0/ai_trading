"""
通知元件

此模組提供通知相關的元件。
"""

import streamlit as st
from datetime import datetime


def show_notification(message, type="info", duration=3):
    """
    顯示通知

    Args:
        message (str): 通知訊息
        type (str, optional): 通知類型，可選 "info", "success", "warning", "error". Defaults to "info".
        duration (int, optional): 顯示時間（秒）. Defaults to 3.
    """
    if type == "info":
        st.info(message)
    elif type == "success":
        st.success(message)
    elif type == "warning":
        st.warning(message)
    elif type == "error":
        st.error(message)
    else:
        st.write(message)

    # 自動消失的通知需要在 JavaScript 中實現
    # 由於 Streamlit 限制，這裡只是模擬


def notification_center():
    """
    通知中心

    顯示系統的所有通知
    """
    with st.expander("通知中心"):
        # 模擬通知數據
        notifications = [
            {"time": "2023-05-01 10:30:00", "message": "系統更新完成", "type": "info"},
            {
                "time": "2023-05-01 09:15:00",
                "message": "交易執行成功",
                "type": "success",
            },
            {"time": "2023-04-30 15:45:00", "message": "資料更新失敗", "type": "error"},
            {
                "time": "2023-04-30 14:20:00",
                "message": "風險警告：市場波動增加",
                "type": "warning",
            },
            {"time": "2023-04-30 10:00:00", "message": "新策略已部署", "type": "info"},
        ]

        for notification in notifications:
            col1, col2 = st.columns([1, 4])
            with col1:
                st.write(notification["time"])
            with col2:
                if notification["type"] == "info":
                    st.info(notification["message"])
                elif notification["type"] == "success":
                    st.success(notification["message"])
                elif notification["type"] == "warning":
                    st.warning(notification["message"])
                elif notification["type"] == "error":
                    st.error(notification["message"])

        if st.button("清除所有通知"):
            st.success("已清除所有通知")


def alert_badge(count=0):
    """
    顯示通知徽章

    Args:
        count (int, optional): 未讀通知數量. Defaults to 0.
    """
    if count > 0:
        st.markdown(
            f"""
            <div style="
                position: relative;
                display: inline-block;
                margin-right: 10px;
            ">
                <span style="
                    position: absolute;
                    top: -8px;
                    right: -8px;
                    background-color: red;
                    color: white;
                    border-radius: 50%;
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                ">{count}</span>
                <span style="font-size: 24px;">🔔</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="
                position: relative;
                display: inline-block;
                margin-right: 10px;
            ">
                <span style="font-size: 24px;">🔔</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
