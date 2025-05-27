"""增強版風險參數設定模組

此模組提供增強版的風險參數設定界面，包括：
- 響應式參數設定表單
- 即時參數驗證
- 參數預覽和比較
- 批量參數管理

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, Any
import streamlit as st
from datetime import datetime

from .data_services import (
    load_risk_parameters,
    save_risk_parameters,
    export_risk_parameters,
    import_risk_parameters,
    validate_parameters,
)


def show_enhanced_parameters() -> None:
    """顯示增強版風險參數設定

    提供響應式的風險參數設定界面，支援即時驗證、
    參數預覽和批量管理功能。

    Returns:
        None
    """
    st.subheader("⚙️ 增強版風險參數設定")

    # 載入當前參數
    if "enhanced_risk_params" not in st.session_state:
        st.session_state.enhanced_risk_params = load_risk_parameters()

    # 創建響應式佈局
    _show_responsive_layout()


def _show_responsive_layout() -> None:
    """顯示響應式佈局"""
    # 檢測螢幕大小（簡化版）
    screen_size = st.selectbox(
        "佈局模式",
        ["自動", "桌面版", "平板版", "手機版"],
        index=0,
        help="選擇適合您設備的佈局模式",
    )

    if screen_size in ["自動", "桌面版"]:
        _show_desktop_layout()
    elif screen_size == "平板版":
        _show_tablet_layout()
    else:
        _show_mobile_layout()


def _show_desktop_layout() -> None:
    """顯示桌面版佈局（三列）"""
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        _show_stop_loss_section()

    with col2:
        _show_position_management_section()

    with col3:
        _show_monitoring_section()

    # 底部控制區
    _show_parameter_controls()


def _show_tablet_layout() -> None:
    """顯示平板版佈局（兩列）"""
    col1, col2 = st.columns([1, 1])

    with col1:
        _show_stop_loss_section()
        _show_monitoring_section()

    with col2:
        _show_position_management_section()
        _show_parameter_preview()

    _show_parameter_controls()


def _show_mobile_layout() -> None:
    """顯示手機版佈局（單列）"""
    _show_stop_loss_section()
    _show_position_management_section()
    _show_monitoring_section()
    _show_parameter_preview()
    _show_parameter_controls()


def _show_stop_loss_section() -> None:
    """顯示停損/停利設定區塊"""
    with st.expander("🛑 停損/停利設定", expanded=True):
        params = st.session_state.enhanced_risk_params

        # 停損設定
        st.write("**停損設定**")
        params["stop_loss_enabled"] = st.toggle(
            "啟用停損",
            value=params.get("stop_loss_enabled", True),
            key="enhanced_stop_loss_enabled",
        )

        if params["stop_loss_enabled"]:
            params["stop_loss_percent"] = st.slider(
                "停損百分比 (%)",
                min_value=1.0,
                max_value=20.0,
                value=params.get("stop_loss_percent", 5.0),
                step=0.5,
                key="enhanced_stop_loss_percent",
                help="當價格下跌超過此百分比時觸發停損",
            )

            # 即時計算停損金額
            portfolio_value = 1000000  # 假設投資組合價值
            stop_loss_amount = portfolio_value * params["stop_loss_percent"] / 100
            st.info(f"💰 預估停損金額: ${stop_loss_amount:,.0f}")

        # 停利設定
        st.write("**停利設定**")
        params["take_profit_enabled"] = st.toggle(
            "啟用停利",
            value=params.get("take_profit_enabled", True),
            key="enhanced_take_profit_enabled",
        )

        if params["take_profit_enabled"]:
            params["take_profit_percent"] = st.slider(
                "停利百分比 (%)",
                min_value=5.0,
                max_value=50.0,
                value=params.get("take_profit_percent", 10.0),
                step=1.0,
                key="enhanced_take_profit_percent",
                help="當價格上漲超過此百分比時觸發停利",
            )

            # 即時計算停利金額
            portfolio_value = 1000000
            take_profit_amount = portfolio_value * params["take_profit_percent"] / 100
            st.success(f"💰 預估停利金額: ${take_profit_amount:,.0f}")

        # 追蹤停損
        params["trailing_stop_enabled"] = st.toggle(
            "啟用追蹤停損",
            value=params.get("trailing_stop_enabled", False),
            key="enhanced_trailing_stop_enabled",
        )

        if params["trailing_stop_enabled"]:
            params["trailing_stop_percent"] = st.slider(
                "追蹤停損百分比 (%)",
                min_value=1.0,
                max_value=10.0,
                value=params.get("trailing_stop_percent", 3.0),
                step=0.5,
                key="enhanced_trailing_stop_percent",
            )


def _show_position_management_section() -> None:
    """顯示部位管理設定區塊"""
    with st.expander("📊 部位管理設定", expanded=True):
        params = st.session_state.enhanced_risk_params

        # 投資組合風險
        st.write("**投資組合風險**")
        params["max_portfolio_risk"] = st.slider(
            "最大投資組合風險 (%)",
            min_value=0.5,
            max_value=10.0,
            value=params.get("max_portfolio_risk", 2.0),
            step=0.1,
            key="enhanced_max_portfolio_risk",
            help="整個投資組合的最大風險暴露",
        )

        params["max_daily_loss"] = st.slider(
            "最大日損失 (%)",
            min_value=1.0,
            max_value=20.0,
            value=params.get("max_daily_loss", 5.0),
            step=0.5,
            key="enhanced_max_daily_loss",
        )

        # 部位大小控制
        st.write("**部位大小控制**")
        params["position_sizing_method"] = st.selectbox(
            "部位大小方法",
            ["固定比例", "固定金額", "風險基準", "Kelly公式", "波動率調整"],
            index=0,
            key="enhanced_position_sizing_method",
        )

        params["max_position_size"] = st.slider(
            "單一部位最大比例 (%)",
            min_value=1.0,
            max_value=50.0,
            value=params.get("max_position_size", 10.0),
            step=1.0,
            key="enhanced_max_position_size",
        )

        # 部位限制
        st.write("**部位限制**")
        col_pos1, col_pos2 = st.columns(2)

        with col_pos1:
            params["max_positions"] = st.number_input(
                "最大持倉數量",
                min_value=1,
                max_value=50,
                value=params.get("max_positions", 10),
                key="enhanced_max_positions",
            )

        with col_pos2:
            params["max_sector_exposure"] = st.slider(
                "單一行業最大曝險 (%)",
                min_value=10.0,
                max_value=100.0,
                value=params.get("max_sector_exposure", 30.0),
                step=5.0,
                key="enhanced_max_sector_exposure",
            )


def _show_monitoring_section() -> None:
    """顯示監控設定區塊"""
    with st.expander("📈 監控設定", expanded=True):
        params = st.session_state.enhanced_risk_params

        # VaR 設定
        st.write("**VaR 設定**")
        params["var_confidence"] = st.slider(
            "VaR 信心水準 (%)",
            min_value=90.0,
            max_value=99.9,
            value=params.get("var_confidence", 95.0),
            step=0.1,
            key="enhanced_var_confidence",
        )

        params["var_method"] = st.selectbox(
            "VaR 計算方法",
            ["歷史模擬法", "參數法", "蒙地卡羅法"],
            index=0,
            key="enhanced_var_method",
        )

        # 警報設定
        st.write("**警報設定**")
        params["alert_threshold_var"] = st.slider(
            "VaR 警報閾值 (%)",
            min_value=0.5,
            max_value=10.0,
            value=params.get("alert_threshold_var", 2.0),
            step=0.1,
            key="enhanced_alert_threshold_var",
        )

        params["alert_threshold_drawdown"] = st.slider(
            "回撤警報閾值 (%)",
            min_value=1.0,
            max_value=30.0,
            value=params.get("alert_threshold_drawdown", 10.0),
            step=1.0,
            key="enhanced_alert_threshold_drawdown",
        )

        # 通知設定
        st.write("**通知設定**")
        col_alert1, col_alert2 = st.columns(2)

        with col_alert1:
            params["alert_email_enabled"] = st.checkbox(
                "Email 通知",
                value=params.get("alert_email_enabled", True),
                key="enhanced_alert_email_enabled",
            )

        with col_alert2:
            params["real_time_monitoring"] = st.checkbox(
                "即時監控",
                value=params.get("real_time_monitoring", True),
                key="enhanced_real_time_monitoring",
            )


def _show_parameter_preview() -> None:
    """顯示參數預覽"""
    with st.expander("👁️ 參數預覽", expanded=False):
        params = st.session_state.enhanced_risk_params

        st.write("**當前設定摘要**")

        # 風險控制摘要
        st.write(
            f"• 停損: {'啟用' if params.get('stop_loss_enabled') else '停用'} "
            f"({params.get('stop_loss_percent', 0):.1f}%)"
        )
        st.write(
            f"• 停利: {'啟用' if params.get('take_profit_enabled') else '停用'} "
            f"({params.get('take_profit_percent', 0):.1f}%)"
        )
        st.write(f"• 最大部位: {params.get('max_position_size', 0):.1f}%")
        st.write(f"• 最大持倉: {params.get('max_positions', 0)} 檔")
        st.write(f"• VaR 信心水準: {params.get('var_confidence', 0):.1f}%")

        # 參數驗證
        errors = validate_parameters(params)
        if errors:
            st.error("⚠️ 參數驗證錯誤:")
            for error in errors:
                st.write(f"• {error}")
        else:
            st.success("✅ 所有參數驗證通過")


def _show_parameter_controls() -> None:
    """顯示參數控制按鈕"""
    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("💾 保存設定", type="primary", use_container_width=True):
            params = st.session_state.enhanced_risk_params
            errors = validate_parameters(params)

            if errors:
                st.error("無法保存，請修正以下錯誤:")
                for error in errors:
                    st.write(f"• {error}")
            else:
                if save_risk_parameters(params):
                    st.success("✅ 風險參數已成功保存！")
                else:
                    st.error("❌ 保存失敗，請稍後重試")

    with col2:
        if st.button("🔄 重新載入", use_container_width=True):
            st.session_state.enhanced_risk_params = load_risk_parameters()
            st.success("✅ 參數已重新載入")
            st.rerun()

    with col3:
        if st.button("📤 匯出設定", use_container_width=True):
            params = st.session_state.enhanced_risk_params
            json_data = export_risk_parameters(params)

            if json_data:
                st.download_button(
                    label="下載設定檔案",
                    data=json_data,
                    file_name=f"risk_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True,
                )

    with col4:
        uploaded_file = st.file_uploader(
            "📥 匯入設定", type="json", help="上傳之前匯出的設定檔案"
        )

        if uploaded_file is not None:
            try:
                json_data = uploaded_file.read().decode("utf-8")
                imported_params = import_risk_parameters(json_data)

                if imported_params:
                    st.session_state.enhanced_risk_params = imported_params
                    st.success("✅ 設定已成功匯入！")
                    st.rerun()
            except Exception as e:
                st.error(f"匯入失敗: {e}")
