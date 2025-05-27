"""
小工具庫

提供所有可用小工具的註冊、創建和管理功能。
"""

from typing import Dict, Type, List, Any, Optional, Tuple
import logging

from .widgets.base_widget import BaseWidget
from .widgets.stock_widgets import StockPriceCard, MarketStatusWidget, CandlestickWidget
from .widgets.portfolio_widgets import (
    PortfolioSummaryWidget,
    AllocationPieWidget,
    PerformanceChartWidget,
)
from .widgets.indicator_widgets import (
    RSIIndicatorWidget,
    MACDIndicatorWidget,
    BollingerBandsWidget,
)
from .widgets.utility_widgets import (
    TextWidget,
    AlertsPanelWidget,
    TradingActivityWidget,
    VolumeChartWidget,
)

logger = logging.getLogger(__name__)


class WidgetLibrary:
    """小工具庫類"""

    def __init__(self):
        """初始化小工具庫"""
        self._widgets: Dict[str, Type[BaseWidget]] = {}
        self._categories: Dict[str, List[str]] = {}
        self._register_default_widgets()

    def _register_default_widgets(self) -> None:
        """註冊預設小工具"""
        # 股票相關小工具
        self.register_widget("stock_price_card", StockPriceCard, "股票分析")
        self.register_widget("market_status", MarketStatusWidget, "股票分析")
        self.register_widget("candlestick_chart", CandlestickWidget, "股票分析")

        # 投資組合小工具
        self.register_widget("portfolio_summary", PortfolioSummaryWidget, "投資組合")
        self.register_widget("allocation_pie", AllocationPieWidget, "投資組合")
        self.register_widget("performance_chart", PerformanceChartWidget, "投資組合")

        # 技術指標小工具
        self.register_widget("rsi_indicator", RSIIndicatorWidget, "技術指標")
        self.register_widget("macd_indicator", MACDIndicatorWidget, "技術指標")
        self.register_widget("bollinger_bands", BollingerBandsWidget, "技術指標")

        # 實用工具小工具
        self.register_widget("text_widget", TextWidget, "實用工具")
        self.register_widget("alerts_panel", AlertsPanelWidget, "實用工具")
        self.register_widget("trading_activity", TradingActivityWidget, "實用工具")
        self.register_widget("volume_chart", VolumeChartWidget, "實用工具")

    def register_widget(
        self, widget_type: str, widget_class: Type[BaseWidget], category: str = "其他"
    ) -> None:
        """註冊小工具

        Args:
            widget_type: 小工具類型
            widget_class: 小工具類別
            category: 分類
        """
        self._widgets[widget_type] = widget_class

        if category not in self._categories:
            self._categories[category] = []

        if widget_type not in self._categories[category]:
            self._categories[category].append(widget_type)

        logger.info(f"已註冊小工具: {widget_type} ({category})")

    def create_widget(
        self, widget_type: str, widget_id: str, config: Dict[str, Any] = None
    ) -> Optional[BaseWidget]:
        """創建小工具實例

        Args:
            widget_type: 小工具類型
            widget_id: 小工具ID
            config: 配置

        Returns:
            小工具實例
        """
        if widget_type not in self._widgets:
            logger.error(f"未知的小工具類型: {widget_type}")
            return None

        try:
            widget_class = self._widgets[widget_type]
            widget = widget_class(widget_id, config)
            logger.info(f"已創建小工具: {widget_type} (ID: {widget_id})")
            return widget
        except Exception as e:
            logger.error(f"創建小工具失敗: {e}")
            return None

    def get_widget_info(self, widget_type: str) -> Optional[Dict[str, Any]]:
        """獲取小工具資訊

        Args:
            widget_type: 小工具類型

        Returns:
            小工具資訊
        """
        if widget_type not in self._widgets:
            return None

        widget_class = self._widgets[widget_type]

        # 創建臨時實例獲取資訊
        temp_widget = widget_class("temp", {})

        return {
            "type": widget_type,
            "name": temp_widget.get_default_title(),
            "default_size": temp_widget.get_default_size(),
            "data_requirements": temp_widget.get_data_requirements(),
            "category": self._get_widget_category(widget_type),
        }

    def get_available_widgets(self) -> Dict[str, List[Dict[str, Any]]]:
        """獲取所有可用小工具

        Returns:
            按分類組織的小工具列表
        """
        result = {}

        for category, widget_types in self._categories.items():
            result[category] = []

            for widget_type in widget_types:
                widget_info = self.get_widget_info(widget_type)
                if widget_info:
                    result[category].append(widget_info)

        return result

    def get_widget_categories(self) -> List[str]:
        """獲取所有分類

        Returns:
            分類列表
        """
        return list(self._categories.keys())

    def get_widgets_by_category(self, category: str) -> List[Dict[str, Any]]:
        """根據分類獲取小工具

        Args:
            category: 分類名稱

        Returns:
            小工具列表
        """
        if category not in self._categories:
            return []

        widgets = []
        for widget_type in self._categories[category]:
            widget_info = self.get_widget_info(widget_type)
            if widget_info:
                widgets.append(widget_info)

        return widgets

    def _get_widget_category(self, widget_type: str) -> str:
        """獲取小工具分類

        Args:
            widget_type: 小工具類型

        Returns:
            分類名稱
        """
        for category, widget_types in self._categories.items():
            if widget_type in widget_types:
                return category
        return "其他"

    def validate_widget_config(
        self, widget_type: str, config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """驗證小工具配置

        Args:
            widget_type: 小工具類型
            config: 配置

        Returns:
            (是否有效, 錯誤訊息列表)
        """
        if widget_type not in self._widgets:
            return False, [f"未知的小工具類型: {widget_type}"]

        try:
            widget_class = self._widgets[widget_type]
            temp_widget = widget_class("temp", config)
            return temp_widget.validate_config()
        except Exception as e:
            return False, [f"配置驗證失敗: {e}"]

    def get_widget_templates(self) -> Dict[str, Dict[str, Any]]:
        """獲取小工具模板

        Returns:
            小工具模板字典
        """
        templates = {
            "股價監控卡片": {
                "type": "stock_price_card",
                "size": {"width": 3, "height": 2},
                "config": {"symbol": "2330.TW", "theme": "light"},
            },
            "K線圖表": {
                "type": "candlestick_chart",
                "size": {"width": 8, "height": 4},
                "config": {"symbol": "2330.TW", "days": 30, "show_volume": True},
            },
            "投資組合摘要": {
                "type": "portfolio_summary",
                "size": {"width": 6, "height": 4},
                "config": {"show_holdings": True},
            },
            "RSI指標": {
                "type": "rsi_indicator",
                "size": {"width": 4, "height": 3},
                "config": {"symbol": "2330.TW", "period": 14, "days": 30},
            },
            "MACD指標": {
                "type": "macd_indicator",
                "size": {"width": 6, "height": 4},
                "config": {"symbol": "2330.TW", "days": 60},
            },
            "資產配置圓餅圖": {
                "type": "allocation_pie",
                "size": {"width": 4, "height": 3},
                "config": {"allocation_type": "sector"},
            },
            "系統警報面板": {
                "type": "alerts_panel",
                "size": {"width": 12, "height": 2},
                "config": {"max_alerts": 5, "show_resolved": False},
            },
            "交易活動": {
                "type": "trading_activity",
                "size": {"width": 4, "height": 3},
                "config": {"activity_type": "recent_trades", "max_items": 10},
            },
        }

        return templates

    def search_widgets(self, query: str) -> List[Dict[str, Any]]:
        """搜尋小工具

        Args:
            query: 搜尋關鍵字

        Returns:
            匹配的小工具列表
        """
        results = []
        query_lower = query.lower()

        for widget_type in self._widgets:
            widget_info = self.get_widget_info(widget_type)
            if widget_info:
                # 搜尋名稱和類型
                if (
                    query_lower in widget_info["name"].lower()
                    or query_lower in widget_type.lower()
                    or query_lower in widget_info["category"].lower()
                ):
                    results.append(widget_info)

        return results

    def get_widget_dependencies(self, widget_type: str) -> List[str]:
        """獲取小工具依賴

        Args:
            widget_type: 小工具類型

        Returns:
            依賴列表
        """
        widget_info = self.get_widget_info(widget_type)
        if widget_info:
            return widget_info.get("data_requirements", [])
        return []

    def export_widget_library(self) -> Dict[str, Any]:
        """匯出小工具庫配置

        Returns:
            小工具庫配置
        """
        return {
            "widgets": {
                widget_type: self.get_widget_info(widget_type)
                for widget_type in self._widgets
            },
            "categories": self._categories,
            "templates": self.get_widget_templates(),
        }


# 全域小工具庫實例
widget_library = WidgetLibrary()
