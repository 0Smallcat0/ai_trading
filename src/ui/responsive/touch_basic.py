"""基礎觸控優化組件模組

此模組提供基礎的觸控優化 UI 組件，包括按鈕、滑桿和輸入框等基本元素。
"""

import streamlit as st
from typing import Dict, List, Any, Optional, Callable
from .utils import ResponsiveUtils


class TouchBasicComponents:
    """基礎觸控優化組件類

    提供基礎的觸控優化 UI 組件，確保在手機和平板上
    提供良好的觸控體驗。

    主要功能：
    - 觸控友善的按鈕尺寸
    - 觸控優化的滑桿
    - 觸控優化的表單元素

    設計原則：
    - 最小觸控目標 44x44 像素
    - 適當的間距避免誤觸
    - 視覺回饋和觸覺回饋
    """

    @staticmethod
    def touch_button(
        label: str,
        key: Optional[str] = None,
        help: Optional[str] = None,
        on_click: Optional[Callable] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        type: str = "secondary",
        disabled: bool = False,
        use_container_width: bool = True,
    ) -> bool:
        """觸控優化按鈕

        創建針對觸控裝置優化的按鈕，自動調整尺寸和間距。

        Args:
            label: 按鈕標籤
            key: 按鈕唯一鍵
            help: 幫助文字
            on_click: 點擊回調函數
            args: 回調函數參數
            kwargs: 回調函數關鍵字參數
            type: 按鈕類型
            disabled: 是否禁用
            use_container_width: 是否使用容器寬度

        Returns:
            bool: 是否被點擊
        """
        # 根據裝置類型調整按鈕配置
        if ResponsiveUtils.is_touch_device():
            # 觸控裝置使用較大的按鈕
            button_style = """
            <style>
            .stButton > button {
                min-height: 48px !important;
                min-width: 48px !important;
                font-size: 16px !important;
                padding: 12px 20px !important;
                margin: 8px 4px !important;
                border-radius: 8px !important;
                transition: all 0.2s ease !important;
            }
            .stButton > button:active {
                transform: scale(0.95) !important;
                background-color: rgba(0, 123, 255, 0.8) !important;
            }
            </style>
            """
            st.markdown(button_style, unsafe_allow_html=True)

        return st.button(
            label=label,
            key=key,
            help=help,
            on_click=on_click,
            args=args,
            kwargs=kwargs,
            type=type,
            disabled=disabled,
            use_container_width=use_container_width,
        )

    @staticmethod
    def touch_slider(
        label: str,
        min_value: float = 0.0,
        max_value: float = 100.0,
        value: float = 50.0,
        step: float = 1.0,
        format_str: str = "%f",
        key: Optional[str] = None,
        help: Optional[str] = None,
    ) -> float:
        """觸控優化滑桿

        創建針對觸控裝置優化的滑桿，增大觸控區域。

        Args:
            label: 滑桿標籤
            min_value: 最小值
            max_value: 最大值
            value: 預設值
            step: 步長
            format_str: 格式字串
            key: 滑桿唯一鍵
            help: 幫助文字

        Returns:
            float: 滑桿值
        """
        if ResponsiveUtils.is_touch_device():
            # 觸控裝置使用較大的滑桿
            slider_style = """
            <style>
            .stSlider > div > div > div > div {
                height: 20px !important;
            }
            .stSlider > div > div > div > div > div {
                height: 20px !important;
                width: 20px !important;
            }
            </style>
            """
            st.markdown(slider_style, unsafe_allow_html=True)

        return st.slider(
            label=label,
            min_value=min_value,
            max_value=max_value,
            value=value,
            step=step,
            format=format_str,
            key=key,
            help=help,
        )

    @staticmethod
    def touch_input_group(
        inputs: List[Dict[str, Any]], group_key: str = "input_group"
    ) -> Dict[str, Any]:
        """觸控優化輸入組

        創建針對觸控裝置優化的輸入組，自動調整間距和尺寸。

        Args:
            inputs: 輸入配置列表
            group_key: 輸入組唯一鍵

        Returns:
            Dict[str, Any]: 輸入值字典
        """
        if ResponsiveUtils.is_touch_device():
            # 觸控裝置使用較大的輸入框
            input_style = """
            <style>
            .stTextInput > div > div > input,
            .stNumberInput > div > div > input,
            .stSelectbox > div > div {
                min-height: 48px !important;
                font-size: 16px !important;
                padding: 12px !important;
            }
            .stTextInput, .stNumberInput, .stSelectbox {
                margin-bottom: 16px !important;
            }
            </style>
            """
            st.markdown(input_style, unsafe_allow_html=True)

        results = {}
        for input_config in inputs:
            input_type = input_config.get("type", "text")
            key = input_config["key"]
            label = input_config["label"]

            if input_type == "text":
                results[key] = st.text_input(
                    label,
                    value=input_config.get("default", ""),
                    key=f"{group_key}_{key}",
                    help=input_config.get("help", ""),
                )
            elif input_type == "number":
                results[key] = st.number_input(
                    label,
                    value=input_config.get("default", 0),
                    key=f"{group_key}_{key}",
                    help=input_config.get("help", ""),
                )
            elif input_type == "select":
                results[key] = st.selectbox(
                    label,
                    options=input_config["options"],
                    key=f"{group_key}_{key}",
                    help=input_config.get("help", ""),
                )

        return results

    @staticmethod
    def gesture_enabled_chart(
        chart_func: Callable, chart_data: Any, title: str = "", **kwargs
    ) -> None:
        """手勢支援圖表

        創建支援縮放和平移手勢的圖表。

        Args:
            chart_func: 圖表渲染函數
            chart_data: 圖表數據
            title: 圖表標題
            **kwargs: 額外參數
        """
        if ResponsiveUtils.is_touch_device():
            # 添加觸控手勢支援
            gesture_style = """
            <style>
            .stPlotlyChart {
                touch-action: pan-x pan-y;
            }
            .js-plotly-plot .plotly .modebar {
                display: none !important;
            }
            </style>
            """
            st.markdown(gesture_style, unsafe_allow_html=True)

            # 為觸控裝置調整圖表配置
            if "config" not in kwargs:
                kwargs["config"] = {}

            kwargs["config"].update(
                {
                    "scrollZoom": True,
                    "doubleClick": "reset+autosize",
                    "showTips": False,
                    "displayModeBar": False,
                    "responsive": True,
                }
            )

        # 渲染圖表
        if title:
            st.subheader(title)

        chart_func(chart_data, **kwargs)
