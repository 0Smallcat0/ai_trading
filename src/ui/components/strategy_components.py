"""
策略管理專用 UI 組件

此模組提供策略管理頁面專用的 UI 組件，包括：
- 策略卡片展示
- 策略編輯器
- 參數調整介面
- 版本比較
- 效能圖表
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import json


def show_strategy_card(strategy: Dict, key_prefix: str = ""):
    """顯示策略資訊卡片"""
    with st.container():
        # 策略標題和狀態
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"### {strategy['name']}")
            st.markdown(f"**類型**: {strategy['type']}")
            if strategy.get("category"):
                st.markdown(f"**分類**: {strategy['category']}")

        with col2:
            # 狀態標籤
            status_colors = {
                "draft": "🟡",
                "active": "🟢",
                "testing": "🔵",
                "disabled": "🔴",
                "archived": "⚫",
            }
            status_text = {
                "draft": "草稿",
                "active": "啟用",
                "testing": "測試中",
                "disabled": "停用",
                "archived": "已歸檔",
            }

            status = strategy.get("status", "draft")
            st.markdown(
                f"**狀態**: {status_colors.get(status, '❓')} {status_text.get(status, status)}"
            )

        # 策略描述
        if strategy.get("description"):
            st.markdown(f"**描述**: {strategy['description']}")

        # 基本資訊
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"**作者**: {strategy.get('author', 'N/A')}")
            st.markdown(f"**版本**: {strategy.get('version', 'N/A')}")

        with col2:
            st.markdown(f"**創建時間**: {strategy.get('created_at', 'N/A')}")
            st.markdown(f"**更新時間**: {strategy.get('updated_at', 'N/A')}")

        with col3:
            # 標籤
            if strategy.get("tags"):
                tags_str = ", ".join(strategy["tags"])
                st.markdown(f"**標籤**: {tags_str}")

        # 效能指標
        if strategy.get("performance_metrics"):
            st.markdown("**效能指標**")
            metrics = strategy["performance_metrics"]

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if "sharpe_ratio" in metrics:
                    st.metric("夏普比率", f"{metrics['sharpe_ratio']:.2f}")

            with col2:
                if "max_drawdown" in metrics:
                    st.metric("最大回撤", f"{metrics['max_drawdown']:.2%}")

            with col3:
                if "win_rate" in metrics:
                    st.metric("勝率", f"{metrics['win_rate']:.2%}")

            with col4:
                if "total_return" in metrics:
                    st.metric("總報酬", f"{metrics['total_return']:.2%}")


def show_strategy_editor(strategy: Dict = None, templates: Dict = None):
    """顯示策略編輯器"""
    is_editing = strategy is not None

    # 基本資訊表單
    with st.form("strategy_basic_info"):
        st.subheader("基本資訊")

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "策略名稱",
                value=strategy.get("name", "") if is_editing else "",
                placeholder="輸入策略名稱",
            )

            strategy_type = st.selectbox(
                "策略類型",
                options=[
                    "技術分析策略",
                    "基本面策略",
                    "套利策略",
                    "AI/機器學習策略",
                    "量化策略",
                ],
                index=(
                    0
                    if not is_editing
                    else [
                        "技術分析策略",
                        "基本面策略",
                        "套利策略",
                        "AI/機器學習策略",
                        "量化策略",
                    ].index(strategy.get("type", "技術分析策略"))
                ),
            )

        with col2:
            author = st.text_input(
                "作者", value=strategy.get("author", "系統") if is_editing else "系統"
            )

            category = st.text_input(
                "分類",
                value=strategy.get("category", "") if is_editing else "",
                placeholder="選填",
            )

        description = st.text_area(
            "策略描述",
            value=strategy.get("description", "") if is_editing else "",
            placeholder="描述策略的目的、原理和適用場景",
            height=100,
        )

        tags = st.text_input(
            "標籤",
            value=", ".join(strategy.get("tags", [])) if is_editing else "",
            placeholder="用逗號分隔多個標籤",
        )

        submitted_basic = st.form_submit_button("保存基本資訊")

        if submitted_basic:
            st.success("基本資訊已保存")

    # 策略代碼編輯器
    st.subheader("策略代碼")

    # 模板選擇（僅新建時顯示）
    if not is_editing and templates:
        template_names = ["空白模板"] + list(templates.keys())
        selected_template = st.selectbox("選擇模板", options=template_names, index=0)

        if selected_template != "空白模板":
            template_code = templates[selected_template].get("code", "")
            st.info(f"已選擇模板: {selected_template}")
        else:
            template_code = ""
    else:
        template_code = strategy.get("code", "") if is_editing else ""

    # 代碼編輯器
    code = st.text_area(
        "策略代碼", value=template_code, height=400, placeholder="在此輸入策略代碼..."
    )

    # 代碼驗證
    if st.button("驗證代碼"):
        if code.strip():
            # 這裡可以調用策略管理服務的代碼驗證功能
            st.success("代碼語法檢查通過")
        else:
            st.warning("請輸入策略代碼")

    return {
        "name": name,
        "type": strategy_type,
        "category": category,
        "description": description,
        "author": author,
        "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
        "code": code,
    }


def show_parameter_editor(strategy: Dict, templates: Dict = None):
    """顯示參數編輯器"""
    st.subheader("策略參數")

    # 獲取參數模板
    template_params = {}
    if templates and strategy.get("type") in templates:
        template_info = None
        for template_name, template_data in templates.items():
            if template_name in strategy.get("name", ""):
                template_info = template_data
                break

        if template_info and "parameters" in template_info:
            template_params = template_info["parameters"]

    # 當前參數
    current_params = strategy.get("parameters", {})

    # 參數編輯
    updated_params = {}

    if template_params:
        st.markdown("**策略參數**")

        for param_name, param_config in template_params.items():
            param_type = param_config.get("type", "float")
            default_value = param_config.get("default", 0)
            min_value = param_config.get("min", 0)
            max_value = param_config.get("max", 100)
            description = param_config.get("description", "")

            current_value = current_params.get(param_name, default_value)

            if param_type == "int":
                updated_params[param_name] = st.number_input(
                    f"{param_name}",
                    min_value=int(min_value),
                    max_value=int(max_value),
                    value=int(current_value),
                    help=description,
                )
            elif param_type == "float":
                updated_params[param_name] = st.number_input(
                    f"{param_name}",
                    min_value=float(min_value),
                    max_value=float(max_value),
                    value=float(current_value),
                    step=0.01,
                    help=description,
                )
            elif param_type == "bool":
                updated_params[param_name] = st.checkbox(
                    f"{param_name}", value=bool(current_value), help=description
                )
            else:
                updated_params[param_name] = st.text_input(
                    f"{param_name}", value=str(current_value), help=description
                )

    # 風險管理參數
    st.markdown("**風險管理參數**")

    risk_params = strategy.get("risk_parameters", {})

    col1, col2, col3 = st.columns(3)

    with col1:
        stop_loss = st.number_input(
            "停損百分比",
            min_value=0.01,
            max_value=0.5,
            value=float(risk_params.get("stop_loss", 0.05)),
            step=0.01,
            format="%.2f",
        )

    with col2:
        take_profit = st.number_input(
            "停利百分比",
            min_value=0.02,
            max_value=1.0,
            value=float(risk_params.get("take_profit", 0.1)),
            step=0.01,
            format="%.2f",
        )

    with col3:
        max_position_size = st.number_input(
            "最大倉位大小",
            min_value=0.01,
            max_value=1.0,
            value=float(risk_params.get("max_position_size", 0.2)),
            step=0.01,
            format="%.2f",
        )

    updated_risk_params = {
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "max_position_size": max_position_size,
    }

    return updated_params, updated_risk_params


def show_version_comparison(version1: Dict, version2: Dict):
    """顯示版本比較"""
    st.subheader("版本比較")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"### 版本 {version1['version']}")
        st.markdown(f"**創建時間**: {version1['created_at']}")
        st.markdown(f"**創建者**: {version1['created_by']}")
        st.markdown(f"**變更說明**: {version1.get('change_log', 'N/A')}")

    with col2:
        st.markdown(f"### 版本 {version2['version']}")
        st.markdown(f"**創建時間**: {version2['created_at']}")
        st.markdown(f"**創建者**: {version2['created_by']}")
        st.markdown(f"**變更說明**: {version2.get('change_log', 'N/A')}")

    # 參數比較
    st.markdown("**參數比較**")

    params1 = version1.get("parameters", {})
    params2 = version2.get("parameters", {})

    all_params = set(params1.keys()) | set(params2.keys())

    if all_params:
        comparison_data = []
        for param in all_params:
            val1 = params1.get(param, "N/A")
            val2 = params2.get(param, "N/A")
            changed = val1 != val2

            comparison_data.append(
                {
                    "參數": param,
                    f"版本 {version1['version']}": val1,
                    f"版本 {version2['version']}": val2,
                    "是否變更": "✅" if changed else "❌",
                }
            )

        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True)

    # 代碼差異（簡化顯示）
    st.markdown("**代碼變更**")

    code1 = version1.get("code", "")
    code2 = version2.get("code", "")

    if code1 != code2:
        st.warning("代碼已變更")

        with st.expander("查看代碼差異"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**版本 {version1['version']} 代碼**")
                st.code(
                    code1[:500] + "..." if len(code1) > 500 else code1,
                    language="python",
                )

            with col2:
                st.markdown(f"**版本 {version2['version']} 代碼**")
                st.code(
                    code2[:500] + "..." if len(code2) > 500 else code2,
                    language="python",
                )
    else:
        st.info("代碼無變更")


def show_strategy_performance_chart(performance_data: Dict):
    """顯示策略效能圖表"""
    if not performance_data:
        st.warning("暫無效能資料")
        return

    # 創建子圖
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("累積報酬", "回撤曲線", "月度報酬", "風險指標"),
        specs=[
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"secondary_y": False}, {"type": "indicator"}],
        ],
    )

    # 模擬一些效能數據
    dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="D")
    np.random.seed(42)
    returns = np.random.randn(len(dates)) * 0.02
    cumulative_returns = (1 + pd.Series(returns)).cumprod()

    # 累積報酬曲線
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=cumulative_returns,
            mode="lines",
            name="累積報酬",
            line=dict(color="blue"),
        ),
        row=1,
        col=1,
    )

    # 回撤曲線
    rolling_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - rolling_max) / rolling_max

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=drawdown,
            mode="lines",
            name="回撤",
            line=dict(color="red"),
            fill="tonexty",
        ),
        row=1,
        col=2,
    )

    # 月度報酬
    monthly_returns = pd.Series(returns, index=dates).resample("M").sum()

    fig.add_trace(
        go.Bar(
            x=monthly_returns.index,
            y=monthly_returns.values,
            name="月度報酬",
            marker_color=["green" if x > 0 else "red" for x in monthly_returns.values],
        ),
        row=2,
        col=1,
    )

    # 風險指標
    sharpe_ratio = performance_data.get("sharpe_ratio", 1.2)

    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=sharpe_ratio,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "夏普比率"},
            gauge={
                "axis": {"range": [None, 3]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 1], "color": "lightgray"},
                    {"range": [1, 2], "color": "gray"},
                    {"range": [2, 3], "color": "lightgreen"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 2,
                },
            },
        ),
        row=2,
        col=2,
    )

    # 更新布局
    fig.update_layout(height=800, title_text="策略效能分析", showlegend=False)

    st.plotly_chart(fig, use_container_width=True)
