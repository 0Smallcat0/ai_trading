"""
訂單執行模組 (Order Execution Module)

此模組負責將交易訊號轉換為實際的交易指令，並透過券商 API 執行交易。
主要功能包括：
- 券商 API 連接與管理
- 訂單生成與執行
- 訂單狀態監控
- 執行回報處理
- 模擬交易環境

支援多種券商 API，包括：
- 模擬交易 (Simulator)
- 永豐證券 (Shioaji)
- 富途證券 (Futu)
- Interactive Brokers (IB)
"""

from .broker_base import BrokerBase, OrderStatus, OrderType
from .config import BrokerConfig
from .futu_adapter import FutuAdapter
# 更新導入：使用推薦的重構版本
try:
    from .ib_adapter_refactored import IBAdapterRefactored as IBAdapter
except ImportError:
    # 向後相容：如果重構版本不存在，使用原版本
    from .ib_adapter import IBAdapter
from .order_manager import OrderManager
from .security import decrypt_api_key, encrypt_api_key
from .shioaji_adapter import ShioajiAdapter
from .simulator_adapter import SimulatorAdapter

__all__ = [
    "BrokerBase",
    "OrderStatus",
    "OrderType",
    "OrderManager",
    "encrypt_api_key",
    "decrypt_api_key",
    "SimulatorAdapter",
    "ShioajiAdapter",
    "FutuAdapter",
    "IBAdapter",
    "BrokerConfig",
]
