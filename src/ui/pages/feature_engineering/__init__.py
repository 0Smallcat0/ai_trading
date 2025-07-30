"""
特徵工程頁面模組

此模組實現了特徵工程頁面的所有功能，包括：
- 可用特徵展示
- 特徵計算與更新
- 特徵查詢
- 特徵選擇
- 特徵工程日誌

模組結構：
- available_features.py: 可用特徵展示
- feature_calculation.py: 特徵計算與更新
- feature_query.py: 特徵查詢
- feature_selection.py: 特徵選擇
- feature_logs.py: 特徵工程日誌
- utils.py: 共用工具函數
"""

from .available_features import show_available_features
from .feature_calculation import show_feature_calculation
from .feature_query import show_feature_query
from .feature_selection import show_feature_selection
from .feature_logs import show_feature_engineering_log
from .utils import (
    get_feature_service,
    get_stock_list,
    get_available_technical_indicators,
    get_available_fundamental_indicators,
)
from .indicators import (
    get_available_sentiment_indicators,
    generate_sample_feature_data,
)

# 為了向後相容性，提供show函數
def show():
    """特徵工程頁面主函數 - 向後相容性接口"""
    # 導入主函數並執行
    from src.ui.pages.feature_engineering import main
    main()


__all__ = [
    "show",
    "show_available_features",
    "show_feature_calculation",
    "show_feature_query",
    "show_feature_selection",
    "show_feature_engineering_log",
    "get_feature_service",
    "get_stock_list",
    "get_available_technical_indicators",
    "get_available_fundamental_indicators",
    "get_available_sentiment_indicators",
    "generate_sample_feature_data",
]
