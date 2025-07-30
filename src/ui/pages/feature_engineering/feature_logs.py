"""
特徵工程日誌模組

此模組實現了特徵工程日誌功能，包括：
- 特徵計算日誌查看
- 特徵更新歷史
- 錯誤日誌分析
- 性能監控
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from .utils import get_feature_service


def show_feature_engineering_log():
    """顯示特徵工程日誌頁面"""
    st.subheader("特徵工程日誌")

    # 獲取特徵工程服務
    feature_service = get_feature_service()

    # 創建標籤頁
    tabs = st.tabs(["計算日誌", "更新歷史", "錯誤日誌", "性能監控"])

    with tabs[0]:
        _show_calculation_logs()

    with tabs[1]:
        _show_update_history()

    with tabs[2]:
        _show_error_logs()

    with tabs[3]:
        _show_performance_monitoring()


def _show_calculation_logs():
    """顯示計算日誌"""
    st.subheader("特徵計算日誌")

    # 日誌過濾選項
    col1, col2, col3 = st.columns(3)

    with col1:
        # 選擇日期範圍
        date_range = st.date_input(
            "日期範圍",
            value=[datetime.now() - timedelta(days=7), datetime.now()],
            help="選擇要查看的日誌日期範圍",
        )

    with col2:
        # 選擇日誌級別
        log_level = st.selectbox(
            "日誌級別",
            options=["全部", "INFO", "WARNING", "ERROR"],
            index=0,
        )

    with col3:
        # 選擇特徵類型
        feature_type_filter = st.selectbox(
            "特徵類型",
            options=["全部", "技術指標", "基本面指標", "情緒指標"],
            index=0,
        )

    # 生成模擬日誌數據
    log_data = _generate_sample_logs(date_range, log_level, feature_type_filter)

    # 顯示日誌統計
    if not log_data.empty:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("總日誌數", len(log_data))

        with col2:
            info_count = len(log_data[log_data["級別"] == "INFO"])
            st.metric("INFO", info_count)

        with col3:
            warning_count = len(log_data[log_data["級別"] == "WARNING"])
            st.metric("WARNING", warning_count)

        with col4:
            error_count = len(log_data[log_data["級別"] == "ERROR"])
            st.metric("ERROR", error_count)

        # 顯示日誌表格
        st.subheader("日誌詳情")
        
        # 添加搜索功能
        search_term = st.text_input("搜索日誌", placeholder="輸入關鍵字搜索...")
        
        if search_term:
            filtered_logs = log_data[
                log_data["消息"].str.contains(search_term, case=False, na=False)
            ]
        else:
            filtered_logs = log_data

        # 顯示過濾後的日誌
        st.dataframe(filtered_logs, use_container_width=True)

        # 日誌級別分佈圖
        level_counts = log_data["級別"].value_counts()
        fig_pie = px.pie(values=level_counts.values, names=level_counts.index, title="日誌級別分佈")
        st.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.info("在選定的條件下沒有找到日誌記錄")


def _show_update_history():
    """顯示更新歷史"""
    st.subheader("特徵更新歷史")

    # 生成模擬更新歷史數據
    update_data = _generate_sample_update_history()

    if not update_data.empty:
        # 顯示更新統計
        col1, col2, col3 = st.columns(3)
        col1.metric("總更新次數", len(update_data))
        col2.metric("成功更新", len(update_data[update_data["狀態"] == "成功"]))
        col3.metric("失敗更新", len(update_data[update_data["狀態"] == "失敗"]))

        # 顯示更新歷史表格
        st.dataframe(update_data, use_container_width=True)

        # 更新趨勢圖
        daily_updates = update_data.groupby(update_data["更新時間"].dt.date).size().reset_index()
        daily_updates.columns = ["日期", "更新次數"]
        fig_trend = px.line(daily_updates, x="日期", y="更新次數", title="每日更新次數趨勢", markers=True)
        st.plotly_chart(fig_trend, use_container_width=True)

    else:
        st.info("沒有找到更新歷史記錄")


def _show_error_logs():
    """顯示錯誤日誌"""
    st.subheader("錯誤日誌分析")

    # 生成模擬錯誤日誌數據
    error_data = _generate_sample_error_logs()

    if not error_data.empty:
        # 錯誤統計
        col1, col2, col3 = st.columns(3)
        col1.metric("總錯誤數", len(error_data))
        col2.metric("嚴重錯誤", len(error_data[error_data["嚴重程度"] == "嚴重"]))
        col3.metric("24小時內錯誤", len(error_data[
            error_data["發生時間"] >= datetime.now() - timedelta(hours=24)]))

        # 顯示錯誤表格
        st.dataframe(error_data, use_container_width=True)

        # 錯誤類型分佈
        error_type_counts = error_data["錯誤類型"].value_counts()
        fig_bar = px.bar(x=error_type_counts.index, y=error_type_counts.values,
                        title="錯誤類型分佈", labels={"x": "錯誤類型", "y": "次數"})
        st.plotly_chart(fig_bar, use_container_width=True)

        # 錯誤時間分佈
        hourly_errors = error_data.groupby(error_data["發生時間"].dt.hour).size().reset_index()
        hourly_errors.columns = ["小時", "錯誤次數"]
        fig_hourly = px.line(hourly_errors, x="小時", y="錯誤次數",
                           title="每小時錯誤分佈", markers=True)
        st.plotly_chart(fig_hourly, use_container_width=True)

    else:
        st.info("沒有找到錯誤日誌記錄")


def _show_performance_monitoring():
    """顯示性能監控"""
    st.subheader("性能監控")

    # 生成模擬性能數據
    performance_data = _generate_sample_performance_data()

    # 性能指標卡片
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("平均計算時間", f"{performance_data['計算時間'].mean():.2f}s")
    col2.metric("峰值內存使用", f"{performance_data['內存使用'].max():.1f}MB")
    col3.metric("成功率", f"{(performance_data['狀態'] == '成功').mean() * 100:.1f}%")
    col4.metric("總計算特徵數", performance_data["特徵數量"].sum())

    # 性能趨勢圖
    fig_time = px.line(performance_data, x="時間", y="計算時間", title="計算時間趨勢")
    st.plotly_chart(fig_time, use_container_width=True)

    fig_memory = px.line(performance_data, x="時間", y="內存使用", title="內存使用趨勢")
    st.plotly_chart(fig_memory, use_container_width=True)

    # 性能詳細數據
    st.dataframe(performance_data, use_container_width=True)


def _generate_sample_logs(date_range, log_level, feature_type_filter):
    """生成模擬日誌數據"""
    import random

    if len(date_range) != 2:
        return pd.DataFrame()

    start_date, end_date = date_range
    time_range = pd.date_range(start=start_date, end=end_date, freq="H")

    logs = []
    for timestamp in time_range:
        if random.random() < 0.3:  # 30% 概率生成日誌
            level = random.choice(["INFO", "WARNING", "ERROR"])
            if log_level != "全部" and level != log_level:
                continue

            feature_type = random.choice(["技術指標", "基本面指標", "情緒指標"])
            if feature_type_filter != "全部" and feature_type != feature_type_filter:
                continue

            messages = {
                "INFO": [f"成功計算 {feature_type}", f"數據更新完成"],
                "WARNING": [f"數據缺失 - {feature_type}", f"計算超時"],
                "ERROR": [f"獲取數據失敗", f"計算錯誤 - {feature_type}"],
            }

            logs.append({
                "時間": timestamp,
                "級別": level,
                "特徵類型": feature_type,
                "消息": random.choice(messages[level]),
            })

    return pd.DataFrame(logs)


def _generate_sample_update_history():
    """生成模擬更新歷史數據"""
    import random
    updates = []
    for i in range(50):
        timestamp = datetime.now() - timedelta(days=random.randint(0, 30))
        updates.append({
            "更新時間": timestamp,
            "特徵類型": random.choice(["技術指標", "基本面指標", "情緒指標"]),
            "股票代碼": random.choice(["2330", "2317", "2454", "2881"]),
            "更新特徵數": random.randint(5, 20),
            "狀態": random.choice(["成功", "失敗"]),
            "耗時": f"{random.uniform(1, 60):.1f}秒",
        })
    return pd.DataFrame(updates)


def _generate_sample_error_logs():
    """生成模擬錯誤日誌數據"""
    import random
    errors = []
    for i in range(20):
        timestamp = datetime.now() - timedelta(hours=random.randint(0, 168))
        errors.append({
            "發生時間": timestamp,
            "錯誤類型": random.choice(["數據獲取錯誤", "計算錯誤", "網絡錯誤", "內存錯誤"]),
            "嚴重程度": random.choice(["輕微", "中等", "嚴重"]),
            "影響範圍": random.choice(["單一股票", "多個股票", "全系統"]),
            "錯誤描述": "模擬錯誤描述...",
        })
    return pd.DataFrame(errors)


def _generate_sample_performance_data():
    """生成模擬性能數據"""
    import random
    performance = []
    for i in range(100):
        timestamp = datetime.now() - timedelta(hours=i)
        performance.append({
            "時間": timestamp,
            "計算時間": random.uniform(1, 30),
            "內存使用": random.uniform(100, 1000),
            "特徵數量": random.randint(10, 100),
            "狀態": random.choice(["成功", "失敗"]),
        })
    return pd.DataFrame(performance)
