"""風險參數設定模組

此模組提供風險參數的設定界面，包括：
- 停損/停利設定
- 資金控管設定
- 部位限制設定
- VaR 與監控設定

Author: AI Trading System
Version: 1.0.0
"""

import streamlit as st

from .utils import (
    get_risk_management_service,
    get_default_risk_parameters,
)
from .parameter_helpers import (
    show_var_monitoring_settings,
    show_save_controls,
)


def show_risk_parameters() -> None:
    """顯示風險參數設置

    提供風險參數的設定界面，包括停損停利、資金控管、部位限制等設定。
    支援從服務層載入參數、保存設定、重置為預設值等功能。

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示風險參數設定表單
        - 更新 session_state 中的風險參數
    """
    st.subheader("⚙️ 風險參數設置")

    # 獲取風險管理服務
    risk_service = get_risk_management_service()

    # 獲取當前參數
    if "risk_params" not in st.session_state:
        if risk_service:
            # 從服務層獲取參數
            try:
                service_params = risk_service.get_risk_parameters()
                if service_params:
                    # 轉換服務層參數格式為 UI 格式
                    st.session_state.risk_params = {}
                    for param_name, param_info in service_params.items():
                        st.session_state.risk_params[param_name] = param_info["value"]
                else:
                    st.session_state.risk_params = get_default_risk_parameters()
            except Exception as e:
                st.error(f"載入風險參數失敗: {e}")
                st.session_state.risk_params = get_default_risk_parameters()
        else:
            st.session_state.risk_params = get_default_risk_parameters()

    # 創建三列布局
    col1, col2, col3 = st.columns(3)

    with col1:
        _show_stop_loss_settings()

    with col2:
        _show_fund_management_settings()

    with col3:
        show_var_monitoring_settings()

    # 保存設置
    show_save_controls(risk_service)


def _show_stop_loss_settings() -> None:
    """顯示停損/停利設置區塊。

    提供停損和停利參數的設定界面，包括不同類型的停損停利策略選擇
    和相應的參數設定。會根據用戶選擇動態顯示相關的參數輸入控件。

    Returns:
        None

    Side Effects:
        - 更新 st.session_state.risk_params 中的停損停利相關參數
        - 在 Streamlit 界面顯示停損停利設定表單

    Note:
        此函數依賴於 st.session_state.risk_params 的存在，
        應在 show_risk_parameters() 函數中調用。
    """
    st.write("### 🛑 停損/停利設置")

    # 停損設置
    st.write("**停損設置**")
    st.session_state.risk_params["stop_loss_enabled"] = st.checkbox(
        "啟用停損", value=st.session_state.risk_params["stop_loss_enabled"]
    )

    if st.session_state.risk_params["stop_loss_enabled"]:
        st.session_state.risk_params["stop_loss_type"] = st.selectbox(
            "停損類型",
            ["百分比停損", "ATR停損", "追蹤停損"],
            index=["百分比停損", "ATR停損", "追蹤停損"].index(
                st.session_state.risk_params["stop_loss_type"]
            ),
        )

        if st.session_state.risk_params["stop_loss_type"] == "百分比停損":
            st.session_state.risk_params["stop_loss_percent"] = st.slider(
                "停損百分比 (%)",
                1.0,
                20.0,
                st.session_state.risk_params["stop_loss_percent"],
                0.5,
            )
        elif st.session_state.risk_params["stop_loss_type"] == "ATR停損":
            st.session_state.risk_params["stop_loss_atr_multiple"] = st.slider(
                "ATR倍數",
                1.0,
                5.0,
                st.session_state.risk_params["stop_loss_atr_multiple"],
                0.1,
            )
        elif st.session_state.risk_params["stop_loss_type"] == "追蹤停損":
            st.session_state.risk_params["trailing_stop_percent"] = st.slider(
                "追蹤停損百分比 (%)",
                1.0,
                10.0,
                st.session_state.risk_params["trailing_stop_percent"],
                0.5,
            )

    # 停利設置
    st.write("**停利設置**")
    st.session_state.risk_params["take_profit_enabled"] = st.checkbox(
        "啟用停利", value=st.session_state.risk_params["take_profit_enabled"]
    )

    if st.session_state.risk_params["take_profit_enabled"]:
        st.session_state.risk_params["take_profit_type"] = st.selectbox(
            "停利類型",
            ["百分比停利", "目標價停利", "風險報酬比停利"],
            index=["百分比停利", "目標價停利", "風險報酬比停利"].index(
                st.session_state.risk_params["take_profit_type"]
            ),
        )

        if st.session_state.risk_params["take_profit_type"] == "百分比停利":
            st.session_state.risk_params["take_profit_percent"] = st.slider(
                "停利百分比 (%)",
                5.0,
                50.0,
                st.session_state.risk_params["take_profit_percent"],
                1.0,
            )
        elif st.session_state.risk_params["take_profit_type"] == "目標價停利":
            st.session_state.risk_params["take_profit_target"] = st.slider(
                "目標收益率 (%)",
                5.0,
                100.0,
                st.session_state.risk_params["take_profit_target"],
                1.0,
            )
        elif st.session_state.risk_params["take_profit_type"] == "風險報酬比停利":
            st.session_state.risk_params["risk_reward_ratio"] = st.slider(
                "風險報酬比",
                1.0,
                5.0,
                st.session_state.risk_params["risk_reward_ratio"],
                0.1,
            )


def _show_fund_management_settings() -> None:
    """顯示資金控管設置區塊。

    提供投資組合風險控制、部位大小控制和部位限制的設定界面。
    包括風險基準、Kelly公式等進階部位大小計算方法的參數設定。

    Returns:
        None

    Side Effects:
        - 更新 st.session_state.risk_params 中的資金控管相關參數
        - 在 Streamlit 界面顯示資金控管設定表單

    Note:
        部位大小方法選擇會影響顯示的參數選項，
        例如選擇 Kelly公式 時會顯示 Kelly分數 設定。
    """
    st.write("### 💰 資金控管設置")

    # 投資組合風險
    st.write("**投資組合風險**")
    st.session_state.risk_params["max_portfolio_risk"] = st.slider(
        "最大投資組合風險 (%)",
        0.5,
        10.0,
        st.session_state.risk_params["max_portfolio_risk"],
        0.1,
    )

    st.session_state.risk_params["max_daily_loss"] = st.slider(
        "最大日損失 (%)",
        1.0,
        20.0,
        st.session_state.risk_params["max_daily_loss"],
        0.5,
    )

    st.session_state.risk_params["max_drawdown"] = st.slider(
        "最大回撤限制 (%)",
        5.0,
        50.0,
        st.session_state.risk_params["max_drawdown"],
        1.0,
    )

    # 部位大小控制
    st.write("**部位大小控制**")
    st.session_state.risk_params["position_sizing_method"] = st.selectbox(
        "部位大小方法",
        ["固定比例", "固定金額", "風險基準", "Kelly公式", "波動率調整"],
        index=["固定比例", "固定金額", "風險基準", "Kelly公式", "波動率調整"].index(
            st.session_state.risk_params["position_sizing_method"]
        ),
    )

    st.session_state.risk_params["max_position_size"] = st.slider(
        "單一部位最大比例 (%)",
        1.0,
        50.0,
        st.session_state.risk_params["max_position_size"],
        1.0,
    )

    if st.session_state.risk_params["position_sizing_method"] == "Kelly公式":
        st.session_state.risk_params["kelly_fraction"] = st.slider(
            "Kelly分數",
            0.1,
            1.0,
            st.session_state.risk_params["kelly_fraction"],
            0.05,
        )

    # 部位限制
    st.write("**部位限制**")
    st.session_state.risk_params["max_positions"] = st.slider(
        "最大持倉數量", 1, 50, st.session_state.risk_params["max_positions"], 1
    )

    st.session_state.risk_params["max_sector_exposure"] = st.slider(
        "單一行業最大曝險 (%)",
        10.0,
        100.0,
        st.session_state.risk_params["max_sector_exposure"],
        5.0,
    )

    st.session_state.risk_params["max_single_stock"] = st.slider(
        "單一股票最大權重 (%)",
        1.0,
        50.0,
        st.session_state.risk_params["max_single_stock"],
        1.0,
    )

    st.session_state.risk_params["correlation_limit"] = st.slider(
        "相關性限制",
        0.1,
        1.0,
        st.session_state.risk_params["correlation_limit"],
        0.05,
    )
