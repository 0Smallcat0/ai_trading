"""響應式斷點定義模組

此模組定義響應式設計的標準斷點值，用於區分不同裝置類型的螢幕尺寸。
"""

from typing import Dict


class ResponsiveBreakpoints:
    """響應式斷點定義類

    定義響應式設計的標準斷點值，用於區分不同裝置類型的螢幕尺寸。
    提供統一的斷點配置，確保整個應用程式的響應式行為一致性。

    斷點定義：
    - MOBILE: 768px - 手機裝置的最大寬度
    - TABLET: 1024px - 平板裝置的最大寬度
    - DESKTOP: 1200px - 桌面裝置的標準寬度

    使用範例：
        >>> breakpoints = ResponsiveBreakpoints.get_breakpoints()
        >>> mobile_width = ResponsiveBreakpoints.MOBILE
    """

    MOBILE = 768
    TABLET = 1024
    DESKTOP = 1200

    @classmethod
    def get_breakpoints(cls) -> Dict[str, int]:
        """獲取所有響應式斷點配置

        返回包含所有裝置類型斷點值的字典，方便程式化存取和配置。

        Returns:
            Dict[str, int]: 斷點配置字典，包含以下鍵值：
                - mobile: 手機裝置斷點 (768px)
                - tablet: 平板裝置斷點 (1024px)
                - desktop: 桌面裝置斷點 (1200px)

        Example:
            >>> breakpoints = ResponsiveBreakpoints.get_breakpoints()
            >>> print(breakpoints["mobile"])  # 輸出: 768
        """
        return {"mobile": cls.MOBILE, "tablet": cls.TABLET, "desktop": cls.DESKTOP}

    @classmethod
    def get_device_type(cls, width: int) -> str:
        """根據螢幕寬度判斷裝置類型

        Args:
            width: 螢幕寬度（像素）

        Returns:
            str: 裝置類型 ('mobile', 'tablet', 'desktop')

        Example:
            >>> device_type = ResponsiveBreakpoints.get_device_type(800)
            >>> print(device_type)  # 輸出: 'tablet'
        """
        if width < cls.MOBILE:
            return "mobile"
        elif width < cls.TABLET:
            return "tablet"
        else:
            return "desktop"

    @classmethod
    def is_mobile(cls, width: int) -> bool:
        """檢查是否為手機裝置

        Args:
            width: 螢幕寬度（像素）

        Returns:
            bool: 是否為手機裝置
        """
        return width < cls.MOBILE

    @classmethod
    def is_tablet(cls, width: int) -> bool:
        """檢查是否為平板裝置

        Args:
            width: 螢幕寬度（像素）

        Returns:
            bool: 是否為平板裝置
        """
        return cls.MOBILE <= width < cls.TABLET

    @classmethod
    def is_desktop(cls, width: int) -> bool:
        """檢查是否為桌面裝置

        Args:
            width: 螢幕寬度（像素）

        Returns:
            bool: 是否為桌面裝置
        """
        return width >= cls.TABLET

    @classmethod
    def get_optimal_columns(cls, width: int, max_cols: int = 4) -> int:
        """根據螢幕寬度獲取最佳列數

        Args:
            width: 螢幕寬度（像素）
            max_cols: 最大列數

        Returns:
            int: 建議的列數
        """
        device_type = cls.get_device_type(width)

        if device_type == "mobile":
            return 1
        elif device_type == "tablet":
            return min(2, max_cols)
        else:
            return max_cols
