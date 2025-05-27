"""響應式設計模組

此模組提供完整的響應式設計解決方案，支援多種螢幕尺寸的自適應佈局。

主要組件：
- breakpoints: 響應式斷點定義
- css_manager: CSS 樣式管理
- layout_manager: 佈局管理器
- components: 響應式組件
- utils: 工具函數

支援的螢幕尺寸：
- 手機：< 768px
- 平板：768px - 1024px
- 桌面：> 1024px

Example:
    使用響應式設計：
    ```python
    from src.ui.responsive import apply_responsive_design, ResponsiveComponents

    apply_responsive_design()
    ResponsiveComponents.responsive_metric_cards(metrics)
    ```
"""

# 延遲導入避免 Streamlit 依賴問題
from .breakpoints import ResponsiveBreakpoints


def apply_responsive_design():
    """應用響應式設計（便捷函數）

    Returns:
        None
    """
    # pylint: disable=import-outside-toplevel
    from .layout_manager import responsive_manager

    responsive_manager.apply_responsive_styles()


def get_responsive_columns(desktop: int = 4, tablet: int = 2, mobile: int = 1) -> int:
    """獲取響應式列數（便捷函數）

    Args:
        desktop: 桌面裝置的列數，預設為 4
        tablet: 平板裝置的列數，預設為 2
        mobile: 手機裝置的列數，預設為 1

    Returns:
        int: 適合當前裝置的列數
    """
    # pylint: disable=import-outside-toplevel
    from .layout_manager import responsive_manager

    return responsive_manager.get_columns_config(desktop, tablet, mobile)


def is_mobile_device() -> bool:
    """檢查是否為行動裝置（便捷函數）

    Returns:
        bool: 如果是手機裝置返回 True，否則返回 False
    """
    # pylint: disable=import-outside-toplevel
    from .layout_manager import responsive_manager

    return responsive_manager.is_mobile


# 延遲導入的類別和函數
def get_responsive_manager():
    """獲取響應式管理器實例"""
    # pylint: disable=import-outside-toplevel
    from .layout_manager import responsive_manager

    return responsive_manager


def get_responsive_components():
    """獲取響應式組件類"""
    # pylint: disable=import-outside-toplevel
    from .components import ResponsiveComponents

    return ResponsiveComponents


def get_responsive_css():
    """獲取響應式 CSS 管理器"""
    # pylint: disable=import-outside-toplevel
    from .css_manager import ResponsiveCSS

    return ResponsiveCSS


def get_responsive_utils():
    """獲取響應式工具類"""
    # pylint: disable=import-outside-toplevel
    from .utils import ResponsiveUtils

    return ResponsiveUtils


# 向後相容性別名
responsive_manager = None
ResponsiveComponents = None
ResponsiveCSS = None
ResponsiveUtils = None


def __getattr__(name):
    """動態屬性存取，實現延遲導入"""
    if name == "responsive_manager":
        return get_responsive_manager()
    elif name == "ResponsiveComponents":
        return get_responsive_components()
    elif name == "ResponsiveCSS":
        return get_responsive_css()
    elif name == "ResponsiveUtils":
        return get_responsive_utils()
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "ResponsiveBreakpoints",
    "ResponsiveUtils",
    "apply_responsive_design",
    "get_responsive_columns",
    "is_mobile_device",
    "responsive_manager",
    "ResponsiveComponents",
    "ResponsiveCSS",
]
