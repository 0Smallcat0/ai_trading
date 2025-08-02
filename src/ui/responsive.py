"""響應式設計管理模組（向後相容入口點）

此模組提供完整的響應式設計解決方案，支援多種螢幕尺寸的自適應佈局。
為了保持向後相容性，此檔案重新導出新模組化架構中的所有功能。

新的模組化架構位於 ui/responsive/ 目錄中：
- breakpoints.py: 斷點定義
- css_manager.py: CSS 樣式管理
- layout_manager.py: 佈局管理器
- components.py: 響應式組件
- utils.py: 工具函數
- touch_components.py: 觸控優化組件

支援的螢幕尺寸：
- 手機：< 768px
- 平板：768px - 1024px
- 桌面：> 1024px

注意：此檔案僅為向後相容性保留，建議使用新的模組化導入方式。
"""

# 向後相容性導入
from .responsive.breakpoints import ResponsiveBreakpoints
from .responsive.css_manager import ResponsiveCSS
from .responsive.layout_manager import ResponsiveLayoutManager, responsive_manager
from .responsive.components import ResponsiveComponents
from .responsive.utils import ResponsiveUtils
from .responsive.touch_components import TouchOptimizedComponents


# 便捷函數（向後相容）
def apply_responsive_design():
    """應用響應式設計（便捷函數）"""
    responsive_manager.apply_responsive_styles()


def get_responsive_columns(desktop: int = 4, tablet: int = 2, mobile: int = 1) -> int:
    """獲取響應式列數（便捷函數）"""
    return responsive_manager.get_columns_config(desktop, tablet, mobile)


def is_mobile_device() -> bool:
    """檢查是否為行動裝置（便捷函數）"""
    return responsive_manager.is_mobile


# 向後相容性：重新導出所有類別和函數
__all__ = [
    "ResponsiveBreakpoints",
    "ResponsiveCSS",
    "ResponsiveLayoutManager",
    "ResponsiveComponents",
    "ResponsiveUtils",
    "TouchOptimizedComponents",
    "responsive_manager",
    "apply_responsive_design",
    "get_responsive_columns",
    "is_mobile_device",
]
