"""
特徵工程專用 UI 組件

此模組提供特徵工程頁面專用的 UI 組件，包括：
- 特徵展示卡片
- 特徵計算進度顯示
- 特徵統計圖表
- 特徵處理操作介面
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional, Any


def show_feature_card(feature_info: Dict, key_prefix: str = ""):
    """顯示特徵資訊卡片"""
    with st.container():
        # 卡片標題
        st.markdown(f"### {feature_info['name']} - {feature_info['full_name']}")

        # 基本資訊
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**類別**: {feature_info.get('category', 'N/A')}")
            st.markdown(f"**描述**: {feature_info.get('description', 'N/A')}")

            if "parameters" in feature_info:
                st.markdown(f"**參數**: {feature_info['parameters']}")

            if "value_range" in feature_info:
                st.markdown(f"**值範圍**: {feature_info['value_range']}")

        with col2:
            if "interpretation" in feature_info:
                st.markdown(f"**解釋**: {feature_info['interpretation']}")

            if "calculation_cost" in feature_info:
                cost_color = {"低": "🟢", "中": "🟡", "高": "🔴"}.get(
                    feature_info["calculation_cost"], "⚪"
                )
                st.markdown(
                    f"**計算成本**: {cost_color} {feature_info['calculation_cost']}"
                )

            if "data_requirements" in feature_info:
                st.markdown(
                    f"**資料需求**: {', '.join(feature_info['data_requirements'])}"
                )

        # 程式碼範例
        if "example_code" in feature_info:
            with st.expander("程式碼範例"):
                st.code(feature_info["example_code"], language="python")


def show_calculation_progress(task_status: Dict, key_prefix: str = ""):
    """顯示特徵計算進度"""
    if not task_status or task_status.get("status") == "not_found":
        st.warning("找不到任務狀態")
        return

    status = task_status.get("status", "unknown")
    progress = task_status.get("progress", 0)
    message = task_status.get("message", "")

    # 狀態顯示
    status_colors = {
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
        "pending": "⏳",
    }

    status_text = {
        "running": "執行中",
        "completed": "已完成",
        "failed": "失敗",
        "pending": "等待中",
    }

    st.markdown(
        f"**狀態**: {status_colors.get(status, '❓')} {status_text.get(status, status)}"
    )

    # 進度條
    if status == "running":
        st.progress(progress / 100)
        st.markdown(f"**進度**: {progress}%")

    # 訊息
    if message:
        st.markdown(f"**訊息**: {message}")

    # 時間資訊
    if "start_time" in task_status:
        st.markdown(f"**開始時間**: {task_status['start_time']}")

    if "end_time" in task_status:
        st.markdown(f"**結束時間**: {task_status['end_time']}")

    # 結果統計
    if status == "completed" and "processed_records" in task_status:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("處理記錄", task_status.get("processed_records", 0))

        with col2:
            st.metric("錯誤記錄", task_status.get("error_records", 0))

        with col3:
            success_rate = 0
            if task_status.get("processed_records", 0) > 0:
                total = task_status.get("processed_records", 0) + task_status.get(
                    "error_records", 0
                )
                success_rate = (task_status.get("processed_records", 0) / total) * 100
            st.metric("成功率", f"{success_rate:.1f}%")


def show_feature_statistics_chart(stats: Dict, feature_name: str):
    """顯示特徵統計圖表"""
    if not stats or stats.get("count", 0) == 0:
        st.warning("沒有統計資料可顯示")
        return

    # 統計摘要
    st.subheader(f"{feature_name} 統計摘要")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("資料筆數", f"{stats['count']:,}")

    with col2:
        st.metric("平均值", f"{stats['mean']:.4f}")

    with col3:
        st.metric("標準差", f"{stats['std']:.4f}")

    with col4:
        st.metric("中位數", f"{stats['median']:.4f}")

    # 範圍資訊
    col1, col2 = st.columns(2)

    with col1:
        st.metric("最小值", f"{stats['min']:.4f}")

    with col2:
        st.metric("最大值", f"{stats['max']:.4f}")


def show_feature_distribution_chart(data: pd.DataFrame, feature_column: str):
    """顯示特徵分布圖表"""
    if data.empty or feature_column not in data.columns:
        st.warning("沒有資料可顯示")
        return

    # 創建子圖
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("直方圖", "箱型圖", "時間序列", "Q-Q 圖"),
        specs=[
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": False}],
        ],
    )

    values = data[feature_column].dropna()

    # 直方圖
    fig.add_trace(go.Histogram(x=values, name="分布", nbinsx=30), row=1, col=1)

    # 箱型圖
    fig.add_trace(go.Box(y=values, name="箱型圖"), row=1, col=2)

    # 時間序列（如果有日期欄位）
    if "data_date" in data.columns:
        time_data = data.sort_values("data_date")
        fig.add_trace(
            go.Scatter(
                x=time_data["data_date"],
                y=time_data[feature_column],
                mode="lines+markers",
                name="時間序列",
            ),
            row=2,
            col=1,
        )
    else:
        # 如果沒有日期，顯示索引圖
        fig.add_trace(
            go.Scatter(
                x=list(range(len(values))),
                y=values,
                mode="lines+markers",
                name="序列圖",
            ),
            row=2,
            col=1,
        )

    # Q-Q 圖（與正態分布比較）
    from scipy import stats

    theoretical_quantiles = stats.norm.ppf(np.linspace(0.01, 0.99, len(values)))
    sample_quantiles = np.sort(values)

    fig.add_trace(
        go.Scatter(
            x=theoretical_quantiles, y=sample_quantiles, mode="markers", name="Q-Q 圖"
        ),
        row=2,
        col=2,
    )

    # 添加 Q-Q 圖的參考線
    min_val = min(theoretical_quantiles.min(), sample_quantiles.min())
    max_val = max(theoretical_quantiles.max(), sample_quantiles.max())
    fig.add_trace(
        go.Scatter(
            x=[min_val, max_val],
            y=[min_val, max_val],
            mode="lines",
            name="參考線",
            line=dict(dash="dash", color="red"),
        ),
        row=2,
        col=2,
    )

    # 更新布局
    fig.update_layout(
        height=800, title_text=f"{feature_column} 分布分析", showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)


def show_outlier_detection_chart(
    data: pd.DataFrame, feature_column: str, outlier_indices: List[int]
):
    """顯示異常值檢測圖表"""
    if data.empty or feature_column not in data.columns:
        st.warning("沒有資料可顯示")
        return

    # 創建散點圖
    fig = go.Figure()

    # 正常值
    normal_mask = ~data.index.isin(outlier_indices)
    normal_data = data[normal_mask]

    if not normal_data.empty:
        fig.add_trace(
            go.Scatter(
                x=normal_data.index,
                y=normal_data[feature_column],
                mode="markers",
                name="正常值",
                marker=dict(color="blue", size=6),
            )
        )

    # 異常值
    outlier_data = data[data.index.isin(outlier_indices)]

    if not outlier_data.empty:
        fig.add_trace(
            go.Scatter(
                x=outlier_data.index,
                y=outlier_data[feature_column],
                mode="markers",
                name="異常值",
                marker=dict(color="red", size=8, symbol="x"),
            )
        )

    # 更新布局
    fig.update_layout(
        title=f"{feature_column} 異常值檢測",
        xaxis_title="索引",
        yaxis_title=feature_column,
        hovermode="closest",
    )

    st.plotly_chart(fig, use_container_width=True)

    # 顯示異常值統計
    if outlier_indices:
        st.markdown(f"**檢測到 {len(outlier_indices)} 個異常值**")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("異常值數量", len(outlier_indices))

        with col2:
            outlier_rate = (len(outlier_indices) / len(data)) * 100
            st.metric("異常值比例", f"{outlier_rate:.2f}%")


def show_correlation_heatmap(data: pd.DataFrame, feature_columns: List[str] = None):
    """顯示特徵相關性熱力圖"""
    if data.empty:
        st.warning("沒有資料可顯示")
        return

    # 選擇數值欄位
    if feature_columns is None:
        numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        feature_columns = [
            col for col in numeric_columns if col not in ["id", "stock_id"]
        ]

    if len(feature_columns) < 2:
        st.warning("需要至少兩個數值特徵才能計算相關性")
        return

    # 計算相關性矩陣
    correlation_matrix = data[feature_columns].corr()

    # 創建熱力圖
    fig = px.imshow(
        correlation_matrix,
        text_auto=True,
        aspect="auto",
        title="特徵相關性熱力圖",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
    )

    fig.update_layout(width=800, height=600)

    st.plotly_chart(fig, use_container_width=True)

    # 顯示高相關性特徵對
    high_corr_pairs = []
    for i in range(len(correlation_matrix.columns)):
        for j in range(i + 1, len(correlation_matrix.columns)):
            corr_value = correlation_matrix.iloc[i, j]
            if abs(corr_value) > 0.7:  # 高相關性閾值
                high_corr_pairs.append(
                    {
                        "特徵1": correlation_matrix.columns[i],
                        "特徵2": correlation_matrix.columns[j],
                        "相關係數": corr_value,
                    }
                )

    if high_corr_pairs:
        st.subheader("高相關性特徵對 (|r| > 0.7)")
        df_high_corr = pd.DataFrame(high_corr_pairs)
        st.dataframe(df_high_corr, use_container_width=True)


def show_feature_importance_chart(
    feature_names: List[str], importance_scores: List[float]
):
    """顯示特徵重要性圖表"""
    if not feature_names or not importance_scores:
        st.warning("沒有特徵重要性資料可顯示")
        return

    # 創建 DataFrame
    df_importance = pd.DataFrame(
        {"特徵": feature_names, "重要性": importance_scores}
    ).sort_values("重要性", ascending=True)

    # 創建水平條形圖
    fig = px.bar(
        df_importance,
        x="重要性",
        y="特徵",
        orientation="h",
        title="特徵重要性排序",
        labels={"重要性": "重要性分數", "特徵": "特徵名稱"},
    )

    fig.update_layout(
        height=max(400, len(feature_names) * 25),
        yaxis={"categoryorder": "total ascending"},
    )

    st.plotly_chart(fig, use_container_width=True)


def show_pca_explained_variance_chart(explained_variance_ratio: List[float]):
    """顯示 PCA 解釋變異數圖表"""
    if not explained_variance_ratio:
        st.warning("沒有 PCA 資料可顯示")
        return

    # 計算累積解釋變異數
    cumulative_variance = np.cumsum(explained_variance_ratio)

    # 創建子圖
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("各主成分解釋變異數", "累積解釋變異數"),
        specs=[[{"secondary_y": False}, {"secondary_y": False}]],
    )

    # 各主成分解釋變異數
    fig.add_trace(
        go.Bar(
            x=[f"PC{i+1}" for i in range(len(explained_variance_ratio))],
            y=explained_variance_ratio,
            name="解釋變異數",
        ),
        row=1,
        col=1,
    )

    # 累積解釋變異數
    fig.add_trace(
        go.Scatter(
            x=[f"PC{i+1}" for i in range(len(cumulative_variance))],
            y=cumulative_variance,
            mode="lines+markers",
            name="累積解釋變異數",
        ),
        row=1,
        col=2,
    )

    # 更新布局
    fig.update_layout(height=400, title_text="PCA 解釋變異數分析", showlegend=False)

    fig.update_yaxes(title_text="解釋變異數比例", row=1, col=1)
    fig.update_yaxes(title_text="累積解釋變異數比例", row=1, col=2)
    fig.update_xaxes(title_text="主成分", row=1, col=1)
    fig.update_xaxes(title_text="主成分", row=1, col=2)

    st.plotly_chart(fig, use_container_width=True)

    # 顯示統計資訊
    col1, col2 = st.columns(2)

    with col1:
        st.metric("總解釋變異數", f"{cumulative_variance[-1]:.2%}")

    with col2:
        # 找到解釋 95% 變異數所需的主成分數
        n_components_95 = np.argmax(cumulative_variance >= 0.95) + 1
        st.metric("95% 變異數所需主成分", n_components_95)
