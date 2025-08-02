"""
AI模型管理專用UI組件

此模組提供AI模型管理頁面所需的各種UI組件，包括：
- 模型卡片展示
- 模型訓練進度
- 模型效能圖表
- 解釋性分析視覺化
- 模型比較工具
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any
import json
from datetime import datetime, timedelta


def show_model_card(model: Dict, show_actions: bool = True) -> None:
    """顯示模型資訊卡片"""

    # 狀態顏色映射
    status_colors = {
        "created": "🔵",
        "training": "🟡",
        "trained": "🟢",
        "deployed": "✅",
        "testing": "🟠",
        "failed": "🔴",
        "archived": "⚫",
    }

    # 模型類型圖標
    type_icons = {
        "機器學習模型": "🤖",
        "深度學習模型": "🧠",
        "規則型模型": "📏",
        "集成模型": "🔗",
    }

    with st.container():
        # 標題行
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.markdown(f"### {type_icons.get(model['type'], '🔧')} {model['name']}")
            st.markdown(f"**{model['sub_type']}** | 版本: {model['version']}")

        with col2:
            st.markdown(f"**狀態**")
            st.markdown(f"{status_colors.get(model['status'], '❓')} {model['status']}")

        with col3:
            if model.get("is_active"):
                st.markdown("**活躍模型**")
                st.markdown("🟢 使用中")
            else:
                st.markdown("**非活躍**")
                st.markdown("⚪ 待機")

        # 描述
        if model.get("description"):
            st.markdown(f"**描述**: {model['description']}")

        # 基本資訊
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("作者", model.get("author", "N/A"))

        with col2:
            created_date = model.get("created_at", "")
            if created_date:
                try:
                    date_obj = datetime.fromisoformat(
                        created_date.replace("Z", "+00:00")
                    )
                    formatted_date = date_obj.strftime("%Y-%m-%d")
                except:
                    formatted_date = created_date
            else:
                formatted_date = "N/A"
            st.metric("創建日期", formatted_date)

        with col3:
            file_size = model.get("file_size", 0)
            if file_size:
                if file_size > 1024 * 1024:
                    size_str = f"{file_size/(1024*1024):.1f} MB"
                elif file_size > 1024:
                    size_str = f"{file_size/1024:.1f} KB"
                else:
                    size_str = f"{file_size} B"
            else:
                size_str = "N/A"
            st.metric("檔案大小", size_str)

        with col4:
            training_time = model.get("training_time", 0)
            if training_time:
                if training_time > 3600:
                    time_str = f"{training_time/3600:.1f}h"
                elif training_time > 60:
                    time_str = f"{training_time/60:.1f}m"
                else:
                    time_str = f"{training_time:.1f}s"
            else:
                time_str = "N/A"
            st.metric("訓練時間", time_str)

        # 效能指標
        if model.get("performance_metrics"):
            st.markdown("**效能指標**")
            metrics = model["performance_metrics"]

            # 根據模型類型顯示不同指標
            if "accuracy" in metrics:
                # 分類模型指標
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("準確率", f"{metrics.get('accuracy', 0):.2%}")
                with col2:
                    st.metric("精確率", f"{metrics.get('precision', 0):.2%}")
                with col3:
                    st.metric("召回率", f"{metrics.get('recall', 0):.2%}")
                with col4:
                    st.metric("F1分數", f"{metrics.get('f1_score', 0):.2%}")

            elif "mse" in metrics:
                # 回歸模型指標
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("MSE", f"{metrics.get('mse', 0):.4f}")
                with col2:
                    st.metric("MAE", f"{metrics.get('mae', 0):.4f}")
                with col3:
                    st.metric("R²", f"{metrics.get('r2', 0):.3f}")

            elif "win_rate" in metrics:
                # 交易策略指標
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("勝率", f"{metrics.get('win_rate', 0):.2%}")
                with col2:
                    st.metric("獲利因子", f"{metrics.get('profit_factor', 0):.2f}")
                with col3:
                    st.metric("最大回撤", f"{metrics.get('max_drawdown', 0):.2%}")

            # 夏普比率（通用指標）
            if "sharpe_ratio" in metrics:
                st.metric("夏普比率", f"{metrics.get('sharpe_ratio', 0):.2f}")

        # 特徵和目標
        if model.get("features") or model.get("target"):
            col1, col2 = st.columns(2)

            with col1:
                if model.get("features"):
                    st.markdown("**特徵**")
                    features = model["features"]
                    if len(features) <= 5:
                        st.write(", ".join(features))
                    else:
                        st.write(f"{', '.join(features[:5])}... (共{len(features)}個)")

            with col2:
                if model.get("target"):
                    st.markdown("**目標變數**")
                    st.write(model["target"])

        # 操作按鈕
        if show_actions:
            st.markdown("---")
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                if st.button("查看詳情", key=f"details_{model['id']}"):
                    st.session_state.selected_model = model
                    st.session_state.current_tab = 1

            with col2:
                if st.button("開始訓練", key=f"train_{model['id']}"):
                    st.session_state.selected_model = model
                    st.session_state.current_tab = 1

            with col3:
                if st.button("執行推論", key=f"inference_{model['id']}"):
                    st.session_state.selected_model = model
                    st.session_state.current_tab = 2

            with col4:
                if model.get("is_active"):
                    if st.button("停用", key=f"deactivate_{model['id']}"):
                        st.warning(f"已停用模型: {model['name']}")
                else:
                    if st.button("啟用", key=f"activate_{model['id']}"):
                        st.success(f"已啟用模型: {model['name']}")

            with col5:
                if st.button("刪除", key=f"delete_{model['id']}"):
                    st.error("確定要刪除此模型嗎？")


def show_training_progress(training_logs: List[Dict]) -> None:
    """顯示訓練進度"""

    if not training_logs:
        st.info("沒有訓練日誌")
        return

    # 轉換為DataFrame
    df = pd.DataFrame(training_logs)

    # 訓練狀態統計
    col1, col2, col3 = st.columns(3)

    with col1:
        total_epochs = len(df)
        st.metric("總訓練輪數", total_epochs)

    with col2:
        if "loss" in df.columns:
            current_loss = df["loss"].iloc[-1] if not df["loss"].isna().iloc[-1] else 0
            st.metric("當前損失", f"{current_loss:.4f}")

    with col3:
        if "accuracy" in df.columns:
            current_acc = (
                df["accuracy"].iloc[-1] if not df["accuracy"].isna().iloc[-1] else 0
            )
            st.metric("當前準確率", f"{current_acc:.2%}")

    # 訓練曲線
    if "epoch" in df.columns and ("loss" in df.columns or "accuracy" in df.columns):
        fig = make_subplots(
            rows=2,
            cols=1,
            subplot_titles=("損失曲線", "準確率曲線"),
            vertical_spacing=0.1,
        )

        # 損失曲線
        if "loss" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["epoch"],
                    y=df["loss"],
                    mode="lines+markers",
                    name="訓練損失",
                    line=dict(color="red"),
                ),
                row=1,
                col=1,
            )

        if "val_loss" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["epoch"],
                    y=df["val_loss"],
                    mode="lines+markers",
                    name="驗證損失",
                    line=dict(color="orange"),
                ),
                row=1,
                col=1,
            )

        # 準確率曲線
        if "accuracy" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["epoch"],
                    y=df["accuracy"],
                    mode="lines+markers",
                    name="訓練準確率",
                    line=dict(color="blue"),
                ),
                row=2,
                col=1,
            )

        if "val_accuracy" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["epoch"],
                    y=df["val_accuracy"],
                    mode="lines+markers",
                    name="驗證準確率",
                    line=dict(color="green"),
                ),
                row=2,
                col=1,
            )

        fig.update_layout(height=600, title_text="訓練進度", showlegend=True)

        fig.update_xaxes(title_text="訓練輪數")
        fig.update_yaxes(title_text="損失", row=1, col=1)
        fig.update_yaxes(title_text="準確率", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)

    # 訓練日誌詳情
    with st.expander("訓練日誌詳情"):
        st.dataframe(df, use_container_width=True)


def show_model_performance_chart(
    performance_metrics: Dict, model_type: str = "classification"
) -> None:
    """顯示模型效能圖表"""

    if not performance_metrics:
        st.info("沒有效能指標數據")
        return

    if model_type == "classification":
        # 分類模型效能圖表
        metrics = ["accuracy", "precision", "recall", "f1_score"]
        values = [performance_metrics.get(metric, 0) for metric in metrics]
        labels = ["準確率", "精確率", "召回率", "F1分數"]

        # 雷達圖
        fig = go.Figure()

        fig.add_trace(
            go.Scatterpolar(r=values, theta=labels, fill="toself", name="效能指標")
        )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=True,
            title="分類模型效能雷達圖",
        )

        st.plotly_chart(fig, use_container_width=True)

    elif model_type == "regression":
        # 回歸模型效能圖表
        metrics = ["mse", "mae", "r2"]
        values = [performance_metrics.get(metric, 0) for metric in metrics]
        labels = ["MSE", "MAE", "R²"]

        # 柱狀圖
        fig = go.Figure(
            data=[go.Bar(x=labels, y=values, text=values, textposition="auto")]
        )

        fig.update_layout(
            title="回歸模型效能指標", xaxis_title="指標", yaxis_title="數值"
        )

        st.plotly_chart(fig, use_container_width=True)

    elif model_type == "trading":
        # 交易策略效能圖表
        metrics = ["win_rate", "profit_factor", "sharpe_ratio"]
        values = [performance_metrics.get(metric, 0) for metric in metrics]
        labels = ["勝率", "獲利因子", "夏普比率"]

        # 組合圖表
        fig = make_subplots(
            rows=1,
            cols=3,
            subplot_titles=labels,
            specs=[
                [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]
            ],
        )

        # 勝率指標
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=values[0],
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": labels[0]},
                gauge={
                    "axis": {"range": [None, 1]},
                    "bar": {"color": "darkblue"},
                    "steps": [
                        {"range": [0, 0.5], "color": "lightgray"},
                        {"range": [0.5, 1], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 0.8,
                    },
                },
            ),
            row=1,
            col=1,
        )

        fig.update_layout(height=300, title_text="交易策略效能指標")
        st.plotly_chart(fig, use_container_width=True)


def show_feature_importance(feature_importance: Dict, top_n: int = 10) -> None:
    """顯示特徵重要性圖表"""

    if not feature_importance:
        st.info("沒有特徵重要性數據")
        return

    # 排序特徵重要性
    sorted_features = sorted(
        feature_importance.items(), key=lambda x: x[1], reverse=True
    )

    # 取前N個特徵
    top_features = sorted_features[:top_n]

    features = [item[0] for item in top_features]
    importance = [item[1] for item in top_features]

    # 水平柱狀圖
    fig = go.Figure(
        go.Bar(
            x=importance,
            y=features,
            orientation="h",
            text=[f"{imp:.3f}" for imp in importance],
            textposition="auto",
        )
    )

    fig.update_layout(
        title=f"特徵重要性 (前{len(top_features)}個)",
        xaxis_title="重要性分數",
        yaxis_title="特徵",
        height=max(400, len(top_features) * 30),
    )

    st.plotly_chart(fig, use_container_width=True)


def show_model_explanation_analysis(explanation: Dict) -> None:
    """顯示模型解釋性分析"""

    if not explanation:
        st.info("沒有解釋性分析數據")
        return

    # 特徵重要性
    if explanation.get("feature_importance"):
        st.subheader("特徵重要性分析")
        show_feature_importance(explanation["feature_importance"])

    # 局部解釋
    if explanation.get("local_explanation"):
        st.subheader("局部解釋分析")
        local_exp = explanation["local_explanation"]

        if local_exp.get("feature_contributions"):
            contributions = local_exp["feature_contributions"]

            # 特徵貢獻圖
            features = list(contributions.keys())
            values = list(contributions.values())
            colors = ["red" if v < 0 else "green" for v in values]

            fig = go.Figure(
                go.Bar(
                    x=values,
                    y=features,
                    orientation="h",
                    marker_color=colors,
                    text=[f"{v:.3f}" for v in values],
                    textposition="auto",
                )
            )

            fig.update_layout(
                title="特徵對預測的貢獻",
                xaxis_title="貢獻值",
                yaxis_title="特徵",
                height=max(400, len(features) * 25),
            )

            st.plotly_chart(fig, use_container_width=True)

            # 基準值和預測值
            col1, col2 = st.columns(2)
            with col1:
                st.metric("基準值", f"{local_exp.get('base_value', 0):.4f}")
            with col2:
                st.metric("預測值", f"{local_exp.get('prediction_value', 0):.4f}")

    # 全局解釋
    if explanation.get("model_behavior"):
        st.subheader("模型行為分析")
        behavior = explanation["model_behavior"]

        col1, col2 = st.columns(2)

        with col1:
            if behavior.get("prediction_range"):
                pred_range = behavior["prediction_range"]
                st.metric("預測範圍", f"[{pred_range[0]:.3f}, {pred_range[1]:.3f}]")

        with col2:
            if behavior.get("confidence_distribution"):
                conf_dist = behavior["confidence_distribution"]
                st.metric("平均信心度", f"{conf_dist.get('mean', 0):.2%}")

        # 特徵敏感性
        if behavior.get("feature_sensitivity"):
            st.subheader("特徵敏感性分析")
            sensitivity = behavior["feature_sensitivity"]
            show_feature_importance(sensitivity, top_n=15)
