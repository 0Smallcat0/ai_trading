"""風險管理表單組件

此模組提供風險管理相關的表單組件，包括：
- 風險參數設定表單
- 參數驗證組件
- 動態表單生成器
- 表單狀態管理

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, Any, List, Optional, Callable
import streamlit as st


def risk_parameter_form(
    params: Dict[str, Any],
    on_change: Optional[Callable] = None,
    key_prefix: str = "risk_form",
) -> Dict[str, Any]:
    """風險參數設定表單

    Args:
        params: 當前參數值字典
        on_change: 參數變更回調函數
        key_prefix: 表單元件 key 前綴

    Returns:
        Dict[str, Any]: 更新後的參數字典
    """
    updated_params = params.copy()

    # 停損/停利設定
    with st.expander("🛑 停損/停利設定", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            updated_params["stop_loss_enabled"] = st.checkbox(
                "啟用停損",
                value=params.get("stop_loss_enabled", True),
                key=f"{key_prefix}_stop_loss_enabled",
                on_change=on_change,
            )

            if updated_params["stop_loss_enabled"]:
                updated_params["stop_loss_percent"] = st.slider(
                    "停損百分比 (%)",
                    min_value=1.0,
                    max_value=20.0,
                    value=params.get("stop_loss_percent", 5.0),
                    step=0.5,
                    key=f"{key_prefix}_stop_loss_percent",
                    on_change=on_change,
                )

        with col2:
            updated_params["take_profit_enabled"] = st.checkbox(
                "啟用停利",
                value=params.get("take_profit_enabled", True),
                key=f"{key_prefix}_take_profit_enabled",
                on_change=on_change,
            )

            if updated_params["take_profit_enabled"]:
                updated_params["take_profit_percent"] = st.slider(
                    "停利百分比 (%)",
                    min_value=5.0,
                    max_value=50.0,
                    value=params.get("take_profit_percent", 10.0),
                    step=1.0,
                    key=f"{key_prefix}_take_profit_percent",
                    on_change=on_change,
                )

    # 部位管理設定
    with st.expander("📊 部位管理設定", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            updated_params["max_position_size"] = st.slider(
                "最大部位大小 (%)",
                min_value=1.0,
                max_value=50.0,
                value=params.get("max_position_size", 10.0),
                step=1.0,
                key=f"{key_prefix}_max_position_size",
                on_change=on_change,
            )

            updated_params["max_positions"] = st.number_input(
                "最大持倉數量",
                min_value=1,
                max_value=50,
                value=params.get("max_positions", 10),
                key=f"{key_prefix}_max_positions",
                on_change=on_change,
            )

        with col2:
            updated_params["max_sector_exposure"] = st.slider(
                "最大行業曝險 (%)",
                min_value=10.0,
                max_value=100.0,
                value=params.get("max_sector_exposure", 30.0),
                step=5.0,
                key=f"{key_prefix}_max_sector_exposure",
                on_change=on_change,
            )

            updated_params["correlation_limit"] = st.slider(
                "相關性限制",
                min_value=0.1,
                max_value=1.0,
                value=params.get("correlation_limit", 0.7),
                step=0.05,
                key=f"{key_prefix}_correlation_limit",
                on_change=on_change,
            )

    return updated_params


def parameter_validation_display(params: Dict[str, Any]) -> List[str]:
    """參數驗證顯示組件

    Args:
        params: 要驗證的參數字典

    Returns:
        List[str]: 驗證錯誤列表
    """
    errors = []

    # 驗證停損參數
    if params.get("stop_loss_enabled") and params.get("stop_loss_percent", 0) <= 0:
        errors.append("停損百分比必須大於 0")

    # 驗證停利參數
    if params.get("take_profit_enabled") and params.get("take_profit_percent", 0) <= 0:
        errors.append("停利百分比必須大於 0")

    # 驗證部位大小
    max_position = params.get("max_position_size", 0)
    if max_position <= 0 or max_position > 100:
        errors.append("最大部位大小必須在 0-100% 之間")

    # 驗證持倉數量
    if params.get("max_positions", 0) <= 0:
        errors.append("最大持倉數量必須大於 0")

    # 顯示驗證結果
    if errors:
        st.error("⚠️ 參數驗證錯誤:")
        for error in errors:
            st.write(f"• {error}")
    else:
        st.success("✅ 所有參數驗證通過")

    return errors


def dynamic_form_generator(
    form_config: Dict[str, Any],
    current_values: Dict[str, Any],
    key_prefix: str = "dynamic_form",
) -> Dict[str, Any]:
    """動態表單生成器

    Args:
        form_config: 表單配置字典
        current_values: 當前值字典
        key_prefix: 表單元件 key 前綴

    Returns:
        Dict[str, Any]: 表單輸入值字典
    """
    form_values = {}

    for field_name, field_config in form_config.items():
        field_type = field_config.get("type", "text")
        field_label = field_config.get("label", field_name)
        field_help = field_config.get("help", "")
        current_value = current_values.get(field_name, field_config.get("default"))

        if field_type == "slider":
            form_values[field_name] = st.slider(
                field_label,
                min_value=field_config.get("min", 0),
                max_value=field_config.get("max", 100),
                value=current_value,
                step=field_config.get("step", 1),
                help=field_help,
                key=f"{key_prefix}_{field_name}",
            )

        elif field_type == "checkbox":
            form_values[field_name] = st.checkbox(
                field_label,
                value=current_value,
                help=field_help,
                key=f"{key_prefix}_{field_name}",
            )

        elif field_type == "selectbox":
            options = field_config.get("options", [])
            index = 0
            if current_value in options:
                index = options.index(current_value)

            form_values[field_name] = st.selectbox(
                field_label,
                options=options,
                index=index,
                help=field_help,
                key=f"{key_prefix}_{field_name}",
            )

        elif field_type == "number":
            form_values[field_name] = st.number_input(
                field_label,
                min_value=field_config.get("min", 0),
                max_value=field_config.get("max", 1000),
                value=current_value,
                step=field_config.get("step", 1),
                help=field_help,
                key=f"{key_prefix}_{field_name}",
            )

        else:  # text input
            form_values[field_name] = st.text_input(
                field_label,
                value=str(current_value),
                help=field_help,
                key=f"{key_prefix}_{field_name}",
            )

    return form_values


def form_state_manager(form_id: str, initial_state: Dict[str, Any]) -> Dict[str, Any]:
    """表單狀態管理器

    Args:
        form_id: 表單唯一識別碼
        initial_state: 初始狀態字典

    Returns:
        Dict[str, Any]: 當前表單狀態
    """
    state_key = f"form_state_{form_id}"

    if state_key not in st.session_state:
        st.session_state[state_key] = initial_state.copy()

    return st.session_state[state_key]


def save_form_state(form_id: str, state: Dict[str, Any]) -> None:
    """保存表單狀態

    Args:
        form_id: 表單唯一識別碼
        state: 要保存的狀態字典
    """
    state_key = f"form_state_{form_id}"
    st.session_state[state_key] = state.copy()


def reset_form_state(form_id: str, default_state: Dict[str, Any]) -> None:
    """重置表單狀態

    Args:
        form_id: 表單唯一識別碼
        default_state: 預設狀態字典
    """
    state_key = f"form_state_{form_id}"
    st.session_state[state_key] = default_state.copy()


def form_action_buttons(
    on_save: Optional[Callable] = None,
    on_reset: Optional[Callable] = None,
    on_export: Optional[Callable] = None,
    save_label: str = "💾 保存",
    reset_label: str = "🔄 重置",
    export_label: str = "📤 匯出",
) -> Dict[str, bool]:
    """表單動作按鈕組件

    Args:
        on_save: 保存回調函數
        on_reset: 重置回調函數
        on_export: 匯出回調函數
        save_label: 保存按鈕標籤
        reset_label: 重置按鈕標籤
        export_label: 匯出按鈕標籤

    Returns:
        Dict[str, bool]: 按鈕點擊狀態字典
    """
    col1, col2, col3 = st.columns(3)

    button_states = {}

    with col1:
        if st.button(save_label, type="primary", use_container_width=True):
            button_states["save"] = True
            if on_save:
                on_save()
        else:
            button_states["save"] = False

    with col2:
        if st.button(reset_label, use_container_width=True):
            button_states["reset"] = True
            if on_reset:
                on_reset()
        else:
            button_states["reset"] = False

    with col3:
        if st.button(export_label, use_container_width=True):
            button_states["export"] = True
            if on_export:
                on_export()
        else:
            button_states["export"] = False

    return button_states


def conditional_form_section(
    condition: bool, title: str, content_func: Callable, expanded: bool = True
) -> None:
    """條件式表單區塊

    Args:
        condition: 顯示條件
        title: 區塊標題
        content_func: 內容生成函數
        expanded: 是否預設展開
    """
    if condition:
        with st.expander(title, expanded=expanded):
            content_func()


def form_progress_indicator(
    current_step: int, total_steps: int, step_names: Optional[List[str]] = None
) -> None:
    """表單進度指示器

    Args:
        current_step: 當前步驟 (1-based)
        total_steps: 總步驟數
        step_names: 步驟名稱列表
    """
    progress = current_step / total_steps
    st.progress(progress)

    if step_names and len(step_names) >= total_steps:
        st.write(f"步驟 {current_step}/{total_steps}: {step_names[current_step-1]}")
    else:
        st.write(f"步驟 {current_step}/{total_steps}")


def form_help_sidebar(help_content: Dict[str, str]) -> None:
    """表單幫助側邊欄

    Args:
        help_content: 幫助內容字典 {標題: 內容}
    """
    # 修復：移除 st.sidebar，改為主頁面顯示
    with st.expander("📖 表單說明", expanded=False):
        for title, content in help_content.items():
            with st.expander(title):
                st.write(content)
