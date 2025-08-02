"""
表單元件

此模組提供表單相關的元件，用於數據輸入和參數設置。
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta


def create_form(title, fields, submit_label="提交", key=None):
    """
    創建表單

    Args:
        title (str): 表單標題
        fields (list): 欄位列表，每個欄位是一個字典，包含 name, type, label, options 等
        submit_label (str, optional): 提交按鈕文字. Defaults to "提交".
        key (str, optional): 表單唯一標識. Defaults to None.

    Returns:
        dict: 表單數據
    """
    if key is None:
        key = f"form_{id(fields)}"

    st.subheader(title)

    with st.form(key=key):
        form_data = {}

        for field in fields:
            field_name = field["name"]
            field_type = field.get("type", "text")
            field_label = field.get("label", field_name)
            field_default = field.get("default", None)
            field_options = field.get("options", None)
            field_help = field.get("help", None)
            field_min = field.get("min", None)
            field_max = field.get("max", None)
            field_step = field.get("step", None)
            field_key = f"{key}_{field_name}"

            # 根據欄位類型創建不同的輸入元件
            if field_type == "text":
                form_data[field_name] = st.text_input(
                    field_label, value=field_default, help=field_help, key=field_key
                )
            elif field_type == "number":
                form_data[field_name] = st.number_input(
                    field_label,
                    min_value=field_min,
                    max_value=field_max,
                    value=field_default if field_default is not None else 0,
                    step=field_step if field_step is not None else 1,
                    help=field_help,
                    key=field_key,
                )
            elif field_type == "select":
                form_data[field_name] = st.selectbox(
                    field_label,
                    options=field_options,
                    index=(
                        0
                        if field_default is None
                        else field_options.index(field_default)
                    ),
                    help=field_help,
                    key=field_key,
                )
            elif field_type == "multiselect":
                form_data[field_name] = st.multiselect(
                    field_label,
                    options=field_options,
                    default=field_default,
                    help=field_help,
                    key=field_key,
                )
            elif field_type == "date":
                form_data[field_name] = st.date_input(
                    field_label,
                    value=(
                        field_default if field_default is not None else datetime.now()
                    ),
                    help=field_help,
                    key=field_key,
                )
            elif field_type == "time":
                form_data[field_name] = st.time_input(
                    field_label, value=field_default, help=field_help, key=field_key
                )
            elif field_type == "checkbox":
                form_data[field_name] = st.checkbox(
                    field_label,
                    value=field_default if field_default is not None else False,
                    help=field_help,
                    key=field_key,
                )
            elif field_type == "radio":
                form_data[field_name] = st.radio(
                    field_label,
                    options=field_options,
                    index=(
                        0
                        if field_default is None
                        else field_options.index(field_default)
                    ),
                    help=field_help,
                    key=field_key,
                    horizontal=field.get("horizontal", False),
                )
            elif field_type == "slider":
                form_data[field_name] = st.slider(
                    field_label,
                    min_value=field_min,
                    max_value=field_max,
                    value=field_default if field_default is not None else field_min,
                    step=field_step if field_step is not None else 1,
                    help=field_help,
                    key=field_key,
                )
            elif field_type == "textarea":
                form_data[field_name] = st.text_area(
                    field_label,
                    value=field_default if field_default is not None else "",
                    help=field_help,
                    key=field_key,
                )
            elif field_type == "file":
                form_data[field_name] = st.file_uploader(
                    field_label,
                    type=field.get("file_type", None),
                    accept_multiple_files=field.get("multiple", False),
                    help=field_help,
                    key=field_key,
                )

        # 提交按鈕
        submitted = st.form_submit_button(submit_label)

        if submitted:
            return form_data

        return None


def strategy_form():
    """
    策略參數表單

    Returns:
        dict: 策略參數
    """
    fields = [
        {
            "name": "strategy_name",
            "label": "策略名稱",
            "type": "text",
            "default": "我的策略",
            "help": "為您的策略取一個名稱",
        },
        {
            "name": "strategy_type",
            "label": "策略類型",
            "type": "select",
            "options": ["技術分析", "基本面", "統計套利", "機器學習"],
            "default": "技術分析",
            "help": "選擇策略類型",
        },
        {
            "name": "symbols",
            "label": "交易標的",
            "type": "text",
            "default": "2330.TW, 2317.TW",
            "help": "輸入交易標的代碼，多個標的請用逗號分隔",
        },
        {
            "name": "timeframe",
            "label": "時間框架",
            "type": "select",
            "options": [
                "1分鐘",
                "5分鐘",
                "15分鐘",
                "30分鐘",
                "1小時",
                "4小時",
                "日線",
                "週線",
                "月線",
            ],
            "default": "日線",
            "help": "選擇交易時間框架",
        },
        {
            "name": "initial_capital",
            "label": "初始資金",
            "type": "number",
            "default": 1000000,
            "min": 10000,
            "max": 100000000,
            "step": 10000,
            "help": "設置初始資金金額",
        },
        {
            "name": "position_size",
            "label": "倉位大小 (%)",
            "type": "slider",
            "min": 1,
            "max": 100,
            "default": 10,
            "help": "每筆交易使用的資金比例",
        },
        {
            "name": "stop_loss",
            "label": "停損比例 (%)",
            "type": "number",
            "default": 5,
            "min": 0,
            "max": 50,
            "step": 0.5,
            "help": "設置停損比例",
        },
        {
            "name": "take_profit",
            "label": "停利比例 (%)",
            "type": "number",
            "default": 10,
            "min": 0,
            "max": 100,
            "step": 0.5,
            "help": "設置停利比例",
        },
        {
            "name": "use_trailing_stop",
            "label": "使用追蹤停損",
            "type": "checkbox",
            "default": False,
            "help": "是否使用追蹤停損",
        },
        {
            "name": "risk_management",
            "label": "風險管理",
            "type": "multiselect",
            "options": [
                "每日最大虧損限制",
                "最大持倉數量限制",
                "波動率過濾",
                "流動性過濾",
            ],
            "default": ["每日最大虧損限制"],
            "help": "選擇風險管理方法",
        },
    ]

    return create_form(
        "策略參數設置", fields, submit_label="保存策略", key="strategy_form"
    )


def create_form_section(title, fields, columns=2, form_key=None, submit_label="提交"):
    """
    創建表單區段

    此函數創建一個帶有標題的表單區段，支援多列布局和各種輸入類型。
    適用於需要分段顯示表單內容的場景，如安裝嚮導、設定頁面等。

    Args:
        title (str): 區段標題
        fields (list): 欄位列表，每個欄位是一個字典，包含 name, type, label, options 等
        columns (int, optional): 列數，預設為 2
        form_key (str, optional): 表單唯一標識，預設自動生成
        submit_label (str, optional): 提交按鈕文字，預設為 "提交"

    Returns:
        dict or None: 如果表單提交則返回表單數據，否則返回 None

    Example:
        ```python
        fields = [
            {"name": "username", "type": "text", "label": "用戶名"},
            {"name": "email", "type": "text", "label": "電子郵件"},
            {"name": "age", "type": "number", "label": "年齡", "min": 18, "max": 100}
        ]

        data = create_form_section("用戶資訊", fields, columns=2)
        if data:
            st.write("提交的數據:", data)
        ```
    """
    if form_key is None:
        form_key = f"form_section_{id(fields)}"

    st.markdown(f"### {title}")

    form_data = {}

    with st.form(form_key):
        # 建立欄位網格
        if columns > 1:
            cols = st.columns(columns)
        else:
            cols = [st]  # 單列時直接使用 streamlit

        for i, field in enumerate(fields):
            # 選擇當前欄位所在的列
            if columns > 1:
                col = cols[i % columns]
            else:
                col = st

            with col:
                field_name = field["name"]
                field_type = field.get("type", "text")
                field_label = field.get("label", field_name)
                field_help = field.get("help", None)
                field_default = field.get("default", None)

                # 根據欄位類型創建對應的輸入元件
                if field_type == "text":
                    form_data[field_name] = st.text_input(
                        field_label,
                        value=field_default or "",
                        help=field_help
                    )
                elif field_type == "number":
                    form_data[field_name] = st.number_input(
                        field_label,
                        value=field_default or 0,
                        min_value=field.get("min", None),
                        max_value=field.get("max", None),
                        step=field.get("step", 1),
                        help=field_help,
                    )
                elif field_type == "select":
                    options = field.get("options", [])
                    default_index = 0
                    if field_default and field_default in options:
                        default_index = options.index(field_default)
                    form_data[field_name] = st.selectbox(
                        field_label,
                        options,
                        index=default_index,
                        help=field_help
                    )
                elif field_type == "multiselect":
                    form_data[field_name] = st.multiselect(
                        field_label,
                        field.get("options", []),
                        default=field_default or [],
                        help=field_help,
                    )
                elif field_type == "checkbox":
                    form_data[field_name] = st.checkbox(
                        field_label,
                        value=field_default or False,
                        help=field_help
                    )
                elif field_type == "slider":
                    form_data[field_name] = st.slider(
                        field_label,
                        min_value=field.get("min", 0),
                        max_value=field.get("max", 100),
                        value=field_default or field.get("min", 0),
                        step=field.get("step", 1),
                        help=field_help,
                    )
                elif field_type == "date":
                    form_data[field_name] = st.date_input(
                        field_label,
                        value=field_default,
                        help=field_help
                    )
                elif field_type == "time":
                    form_data[field_name] = st.time_input(
                        field_label,
                        value=field_default,
                        help=field_help
                    )
                elif field_type == "textarea":
                    form_data[field_name] = st.text_area(
                        field_label,
                        value=field_default or "",
                        height=field.get("height", 100),
                        help=field_help,
                    )
                elif field_type == "file":
                    form_data[field_name] = st.file_uploader(
                        field_label,
                        type=field.get("accept", None),
                        help=field_help,
                    )

        # 提交按鈕
        submitted = st.form_submit_button(submit_label, type="primary")

        if submitted:
            return form_data

    return None
