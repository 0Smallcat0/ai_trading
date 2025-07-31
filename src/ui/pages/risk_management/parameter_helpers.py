"""風險參數設定輔助模組

此模組提供風險參數設定的輔助函數，包括：
- VaR 與監控設定界面
- 參數保存控制
- 參數驗證和處理

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, Any, Optional
import streamlit as st
from datetime import datetime

from src.ui.pages.risk_management.utils import validate_risk_parameters


def show_var_monitoring_settings() -> None:
    """顯示 VaR 與監控設置區塊。

    提供 VaR 計算參數、監控設定和警報設定的界面。
    包括不同 VaR 計算方法的選擇和相應的參數設定。

    Returns:
        None

    Side Effects:
        - 更新 st.session_state.risk_params 中的 VaR 和監控相關參數
        - 在 Streamlit 界面顯示 VaR 與監控設定表單

    Note:
        此函數依賴於 st.session_state.risk_params 的存在，
        應在 show_risk_parameters() 函數中調用。
    """
    st.write("### 📊 VaR 與監控設置")
    params = st.session_state.risk_params

    # VaR 設置
    st.write("**VaR 設置**")
    params["var_confidence"] = st.slider(
        "VaR 信心水準 (%)",
        90.0,
        99.9,
        params.get("var_confidence", 95.0),
        0.1,
    )

    params["var_holding_period"] = st.selectbox(
        "VaR 持有期間",
        [1, 5, 10, 22],
        index=[1, 5, 10, 22].index(params.get("var_holding_period", 1)),
    )

    params["var_method"] = st.selectbox(
        "VaR 計算方法",
        ["歷史模擬法", "參數法", "蒙地卡羅法"],
        index=["歷史模擬法", "參數法", "蒙地卡羅法"].index(
            params.get("var_method", "歷史模擬法")
        ),
    )

    params["var_lookback_days"] = st.slider(
        "VaR 回顧天數",
        30,
        1000,
        params.get("var_lookback_days", 252),
        10,
    )

    params["stress_test_enabled"] = st.checkbox(
        "啟用壓力測試", value=params.get("stress_test_enabled", True)
    )

    # 監控設置
    st.write("**監控設置**")
    params["real_time_monitoring"] = st.checkbox(
        "即時監控", value=params.get("real_time_monitoring", True)
    )

    params["alert_threshold_var"] = st.slider(
        "VaR 警報閾值 (%)",
        0.5,
        10.0,
        params.get("alert_threshold_var", 2.0),
        0.1,
    )

    params["alert_threshold_drawdown"] = st.slider(
        "回撤警報閾值 (%)",
        1.0,
        30.0,
        params.get("alert_threshold_drawdown", 10.0),
        1.0,
    )

    # 警報設置
    st.write("**警報設置**")
    params["alert_email_enabled"] = st.checkbox(
        "Email 警報", value=params.get("alert_email_enabled", True)
    )

    params["alert_sms_enabled"] = st.checkbox(
        "SMS 警報", value=params.get("alert_sms_enabled", False)
    )


def show_save_controls(risk_service: Optional[Any]) -> None:
    """顯示保存控制按鈕區塊。

    提供風險參數的保存、重置和匯出功能按鈕。
    包括參數驗證、保存確認和錯誤處理。

    Args:
        risk_service (Optional[Any]): 風險管理服務實例，
            如果為 None 則使用本地保存。

    Returns:
        None

    Side Effects:
        - 可能更新風險管理服務中的參數
        - 可能重置 st.session_state.risk_params
        - 在 Streamlit 界面顯示操作結果訊息

    Note:
        此函數會進行參數驗證，只有通過驗證的參數才會被保存。
    """
    st.divider()
    col_save1, col_save2, col_save3 = st.columns([1, 1, 1])

    with col_save1:
        if st.button("💾 保存設置", type="primary", use_container_width=True):
            # 驗證參數
            errors = validate_risk_parameters(st.session_state.risk_params)
            if errors:
                for error in errors:
                    st.error(error)
                return

            if risk_service:
                try:
                    # 保存所有參數到服務層
                    success_count = 0
                    for param_name, param_value in st.session_state.risk_params.items():
                        if risk_service.update_risk_parameter(param_name, param_value):
                            success_count += 1

                    if success_count > 0:
                        st.success(f"風險參數設置已保存！({success_count} 個參數)")
                    else:
                        st.warning("沒有參數被保存")
                except Exception as e:
                    st.error(f"保存設置失敗: {e}")
            else:
                st.success("風險參數設置已保存！")

    with col_save2:
        if st.button("🔄 重置為預設", use_container_width=True):
            from src.ui.pages.risk_management.utils import get_default_risk_parameters

            st.session_state.risk_params = get_default_risk_parameters()
            st.success("已重置為預設設置！")
            st.rerun()

    with col_save3:
        if st.button("📋 匯出設置", use_container_width=True):
            try:
                import json

                settings_json = json.dumps(
                    st.session_state.risk_params, indent=2, ensure_ascii=False
                )
                st.download_button(
                    label="下載設置檔案",
                    data=settings_json,
                    file_name=f"risk_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )
                st.info("設置已準備匯出")
            except Exception as e:
                st.error(f"匯出設置失敗: {e}")


def validate_and_format_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """驗證和格式化風險參數。

    對風險參數進行驗證和格式化處理，確保參數的有效性和一致性。

    Args:
        params (Dict[str, Any]): 原始風險參數字典。

    Returns:
        Dict[str, Any]: 驗證和格式化後的參數字典。

    Raises:
        ValueError: 當參數驗證失敗時。

    Example:
        >>> params = {"stop_loss_percent": "5.0", "max_position_size": 10}
        >>> validated = validate_and_format_parameters(params)
        >>> validated["stop_loss_percent"]
        5.0

    Note:
        此函數會自動轉換數據類型並應用預設值。
    """
    formatted_params = params.copy()

    # 數值類型轉換
    numeric_fields = [
        "stop_loss_percent",
        "take_profit_percent",
        "trailing_stop_percent",
        "max_portfolio_risk",
        "max_position_size",
        "max_daily_loss",
        "max_drawdown",
        "max_sector_exposure",
        "max_single_stock",
        "correlation_limit",
        "var_confidence",
        "var_lookback_days",
        "alert_threshold_var",
        "alert_threshold_drawdown",
        "kelly_fraction",
    ]

    for field in numeric_fields:
        if field in formatted_params:
            try:
                formatted_params[field] = float(formatted_params[field])
            except (ValueError, TypeError):
                # 如果轉換失敗，使用預設值
                default_values = {
                    "stop_loss_percent": 5.0,
                    "take_profit_percent": 10.0,
                    "max_position_size": 10.0,
                    "var_confidence": 95.0,
                }
                if field in default_values:
                    formatted_params[field] = default_values[field]

    # 整數類型轉換
    integer_fields = ["max_positions", "var_holding_period"]

    for field in integer_fields:
        if field in formatted_params:
            try:
                formatted_params[field] = int(formatted_params[field])
            except (ValueError, TypeError):
                default_values = {
                    "max_positions": 10,
                    "var_holding_period": 1,
                }
                if field in default_values:
                    formatted_params[field] = default_values[field]

    # 布林類型確保
    boolean_fields = [
        "stop_loss_enabled",
        "take_profit_enabled",
        "trailing_stop_enabled",
        "stress_test_enabled",
        "real_time_monitoring",
        "alert_email_enabled",
        "alert_sms_enabled",
    ]

    for field in boolean_fields:
        if field in formatted_params:
            formatted_params[field] = bool(formatted_params[field])

    # 驗證參數
    errors = validate_risk_parameters(formatted_params)
    if errors:
        raise ValueError(f"參數驗證失敗: {'; '.join(errors)}")

    return formatted_params


def get_parameter_summary(params: Dict[str, Any]) -> Dict[str, str]:
    """獲取參數摘要信息。

    生成風險參數的摘要信息，用於顯示和確認。

    Args:
        params (Dict[str, Any]): 風險參數字典。

    Returns:
        Dict[str, str]: 參數摘要字典，鍵為類別，值為摘要文字。

    Example:
        >>> params = {"stop_loss_enabled": True, "stop_loss_percent": 5.0}
        >>> summary = get_parameter_summary(params)
        >>> summary["停損設定"]
        '啟用 (5.0%)'
    """
    summary = {}

    # 停損停利摘要
    if params.get("stop_loss_enabled"):
        summary["停損設定"] = f"啟用 ({params.get('stop_loss_percent', 0):.1f}%)"
    else:
        summary["停損設定"] = "停用"

    if params.get("take_profit_enabled"):
        summary["停利設定"] = f"啟用 ({params.get('take_profit_percent', 0):.1f}%)"
    else:
        summary["停利設定"] = "停用"

    # 部位管理摘要
    summary["最大部位"] = f"{params.get('max_position_size', 0):.1f}%"
    summary["最大持倉"] = f"{params.get('max_positions', 0)} 檔"
    summary["投資組合風險"] = f"{params.get('max_portfolio_risk', 0):.1f}%"

    # VaR 設定摘要
    summary["VaR 設定"] = (
        f"{params.get('var_confidence', 0):.1f}% ({params.get('var_method', 'N/A')})"
    )

    # 監控設定摘要
    if params.get("real_time_monitoring"):
        summary["即時監控"] = "啟用"
    else:
        summary["即時監控"] = "停用"

    return summary
