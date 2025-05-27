"""
表格元件

此模組提供表格相關的元件，用於數據展示。
"""

import streamlit as st
import pandas as pd
import numpy as np


def data_table(
    data,
    title=None,
    height=None,
    width=None,
    editable=False,
    column_config=None,
    use_container_width=True,
    hide_index=False,
):
    """
    顯示數據表格

    Args:
        data (pd.DataFrame): 數據
        title (str, optional): 表格標題. Defaults to None.
        height (int, optional): 表格高度. Defaults to None.
        width (int, optional): 表格寬度. Defaults to None.
        editable (bool, optional): 是否可編輯. Defaults to False.
        column_config (dict, optional): 列配置. Defaults to None.
        use_container_width (bool, optional): 是否使用容器寬度. Defaults to True.
        hide_index (bool, optional): 是否隱藏索引. Defaults to False.

    Returns:
        pd.DataFrame: 可能被編輯過的數據
    """
    if title:
        st.subheader(title)

    # 設置列配置
    if column_config is None:
        column_config = {}

    # 顯示表格
    edited_df = st.data_editor(
        data,
        height=height,
        width=width,
        use_container_width=use_container_width,
        hide_index=hide_index,
        column_config=column_config,
        disabled=not editable,
        key=f"table_{id(data)}",
    )

    return edited_df


def sortable_table(
    data,
    title=None,
    height=None,
    width=None,
    use_container_width=True,
    hide_index=False,
):
    """
    可排序的數據表格

    Args:
        data (pd.DataFrame): 數據
        title (str, optional): 表格標題. Defaults to None.
        height (int, optional): 表格高度. Defaults to None.
        width (int, optional): 表格寬度. Defaults to None.
        use_container_width (bool, optional): 是否使用容器寬度. Defaults to True.
        hide_index (bool, optional): 是否隱藏索引. Defaults to False.
    """
    if title:
        st.subheader(title)

    # 排序選項
    sort_col = st.selectbox(
        "排序欄位", options=["無"] + list(data.columns), key=f"sort_col_{id(data)}"
    )

    if sort_col != "無":
        sort_order = st.radio(
            "排序方式",
            options=["升序", "降序"],
            horizontal=True,
            key=f"sort_order_{id(data)}",
        )

        # 排序數據
        if sort_order == "升序":
            data = data.sort_values(by=sort_col)
        else:
            data = data.sort_values(by=sort_col, ascending=False)

    # 顯示表格
    st.dataframe(
        data,
        height=height,
        width=width,
        use_container_width=use_container_width,
        hide_index=hide_index,
    )


def filterable_table(
    data,
    title=None,
    height=None,
    width=None,
    use_container_width=True,
    hide_index=False,
):
    """
    可過濾的數據表格

    Args:
        data (pd.DataFrame): 數據
        title (str, optional): 表格標題. Defaults to None.
        height (int, optional): 表格高度. Defaults to None.
        width (int, optional): 表格寬度. Defaults to None.
        use_container_width (bool, optional): 是否使用容器寬度. Defaults to True.
        hide_index (bool, optional): 是否隱藏索引. Defaults to False.
    """
    if title:
        st.subheader(title)

    # 過濾選項
    filter_col = st.selectbox(
        "過濾欄位", options=["無"] + list(data.columns), key=f"filter_col_{id(data)}"
    )

    filtered_data = data.copy()

    if filter_col != "無":
        # 根據欄位類型提供不同的過濾選項
        if pd.api.types.is_numeric_dtype(data[filter_col]):
            # 數值型欄位
            min_val = float(data[filter_col].min())
            max_val = float(data[filter_col].max())

            filter_range = st.slider(
                f"選擇{filter_col}範圍",
                min_value=min_val,
                max_value=max_val,
                value=(min_val, max_val),
                key=f"filter_range_{id(data)}",
            )

            filtered_data = filtered_data[
                (filtered_data[filter_col] >= filter_range[0])
                & (filtered_data[filter_col] <= filter_range[1])
            ]
        else:
            # 類別型欄位
            unique_values = data[filter_col].unique()
            selected_values = st.multiselect(
                f"選擇{filter_col}值",
                options=unique_values,
                default=list(unique_values),
                key=f"filter_values_{id(data)}",
            )

            if selected_values:
                filtered_data = filtered_data[
                    filtered_data[filter_col].isin(selected_values)
                ]

    # 顯示表格
    st.dataframe(
        filtered_data,
        height=height,
        width=width,
        use_container_width=use_container_width,
        hide_index=hide_index,
    )


def paginated_table(
    data,
    title=None,
    page_size=10,
    height=None,
    width=None,
    use_container_width=True,
    hide_index=False,
):
    """
    分頁數據表格

    Args:
        data (pd.DataFrame): 數據
        title (str, optional): 表格標題. Defaults to None.
        page_size (int, optional): 每頁顯示行數. Defaults to 10.
        height (int, optional): 表格高度. Defaults to None.
        width (int, optional): 表格寬度. Defaults to None.
        use_container_width (bool, optional): 是否使用容器寬度. Defaults to True.
        hide_index (bool, optional): 是否隱藏索引. Defaults to False.
    """
    if title:
        st.subheader(title)

    # 計算總頁數
    total_pages = (len(data) + page_size - 1) // page_size

    if total_pages > 0:
        # 頁碼選擇
        page = st.number_input(
            f"頁碼 (共{total_pages}頁)",
            min_value=1,
            max_value=total_pages,
            value=1,
            key=f"page_{id(data)}",
        )

        # 計算當前頁的數據
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, len(data))
        page_data = data.iloc[start_idx:end_idx]

        # 顯示表格
        st.dataframe(
            page_data,
            height=height,
            width=width,
            use_container_width=use_container_width,
            hide_index=hide_index,
        )

        # 分頁導航
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("上一頁", key=f"prev_{id(data)}") and page > 1:
                st.session_state[f"page_{id(data)}"] = page - 1
                st.rerun()

        with col3:
            if st.button("下一頁", key=f"next_{id(data)}") and page < total_pages:
                st.session_state[f"page_{id(data)}"] = page + 1
                st.rerun()

        with col2:
            st.write(f"顯示 {start_idx + 1} 到 {end_idx} 條記錄，共 {len(data)} 條")
    else:
        st.info("沒有數據可顯示")
