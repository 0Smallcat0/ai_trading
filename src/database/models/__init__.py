"""資料庫模型模組

此模組提供統一的資料庫模型導入介面，確保向後相容性。

Modules:
    base_models: 基礎模型和 Mixin
    stock_info_models: 股票基本資訊模型
    trading_models: 交易相關模型
    market_data_models: 市場資料模型

Example:
    >>> from src.database.models import MarketDaily, TradeRecord, StockInfo
    >>> # 或者使用原有的導入方式
    >>> from src.database.schema import MarketDaily, TradeRecord
"""

# 基礎模型和枚舉
from .base_models import (
    Base,
    MarketType,
    TimeGranularity,
    MarketDataMixin,
    calculate_checksum_before_insert,
    calculate_checksum_before_update,
    calculate_checksum_before_delete,
)

# 股票基本資訊模型
from .stock_info_models import (
    StockStatus,
    StockInfo,
)

# 交易相關模型
from .trading_models import (
    TradeSide,
    OrderType,
    TradeRecord,
)

# 市場資料模型
from .market_data_models import (
    MarketDaily,
    MarketMinute,
    MarketTick,
    Fundamental,
    TechnicalIndicator,
)

# 風險管理模型
from .risk_management_models import (
    RiskParameter,
    RiskControlStatus,
    RiskAlert,
    RiskLog,
)

# 為了向後相容性，將所有模型列在 __all__ 中
__all__ = [
    # 基礎模型
    "Base",
    "MarketType",
    "TimeGranularity",
    "MarketDataMixin",
    "calculate_checksum_before_insert",
    "calculate_checksum_before_update",
    "calculate_checksum_before_delete",
    
    # 股票基本資訊
    "StockStatus",
    "StockInfo",
    
    # 交易相關
    "TradeSide",
    "OrderType",
    "TradeRecord",
    
    # 市場資料
    "MarketDaily",
    "MarketMinute",
    "MarketTick",
    "Fundamental",
    "TechnicalIndicator",

    # 風險管理
    "RiskParameter",
    "RiskControlStatus",
    "RiskAlert",
    "RiskLog",
]
