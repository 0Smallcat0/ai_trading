"""觸控優化組件模組（統一入口點）

此模組提供專門針對觸控裝置優化的 UI 組件的統一入口點。
實際實作分散在子模組中以保持檔案大小合理。
"""

from typing import Dict, List, Any, Optional, Callable
from .touch_basic import TouchBasicComponents
from .touch_navigation import TouchNavigationComponents


class TouchOptimizedComponents:
    """觸控優化組件類（統一入口點）

    提供專門針對觸控裝置優化的 UI 組件，確保在手機和平板上
    提供良好的觸控體驗。此類別作為統一入口點，實際功能
    委託給專門的子模組實作。

    主要功能：
    - 觸控友善的按鈕尺寸
    - 手勢支援組件
    - 滑動式導航
    - 觸控優化的表單元素
    - 拖拽和縮放支援

    設計原則：
    - 最小觸控目標 44x44 像素
    - 適當的間距避免誤觸
    - 視覺回饋和觸覺回饋
    - 手勢直觀性
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

        委託給 TouchBasicComponents.touch_button 實作。
        """
        return TouchBasicComponents.touch_button(
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

        委託給 TouchBasicComponents.touch_slider 實作。
        """
        return TouchBasicComponents.touch_slider(
            label=label,
            min_value=min_value,
            max_value=max_value,
            value=value,
            step=step,
            format_str=format_str,
            key=key,
            help=help,
        )

    @staticmethod
    def swipe_navigation(
        pages: List[Dict[str, Any]], current_page_key: str = "current_page"
    ) -> str:
        """滑動式導航

        委託給 TouchNavigationComponents.swipe_navigation 實作。
        """
        return TouchNavigationComponents.swipe_navigation(
            pages=pages, current_page_key=current_page_key
        )

    @staticmethod
    def touch_input_group(
        inputs: List[Dict[str, Any]], group_key: str = "input_group"
    ) -> Dict[str, Any]:
        """觸控優化輸入組

        委託給 TouchBasicComponents.touch_input_group 實作。
        """
        return TouchBasicComponents.touch_input_group(
            inputs=inputs, group_key=group_key
        )

    @staticmethod
    def gesture_enabled_chart(
        chart_func: Callable, chart_data: Any, title: str = "", **kwargs
    ) -> None:
        """手勢支援圖表

        委託給 TouchBasicComponents.gesture_enabled_chart 實作。
        """
        return TouchBasicComponents.gesture_enabled_chart(
            chart_func=chart_func, chart_data=chart_data, title=title, **kwargs
        )
