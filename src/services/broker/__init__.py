"""
券商整合服務模組 (Broker Integration Services)

此模組提供券商整合的核心服務功能，包括：
- 券商連接管理服務
- 訂單執行服務
- 帳戶同步服務

主要功能：
- 統一券商 API 介面
- 連接狀態監控與管理
- 訂單執行與追蹤
- 帳戶資訊同步
- 錯誤處理與重試機制

支援券商：
- 永豐證券 (Shioaji)
- 富途證券 (Futu)
- Interactive Brokers (IB)
- 模擬交易 (Simulator)
"""

from .broker_connection_service import BrokerConnectionService
from .order_execution_service import OrderExecutionService
from .account_sync_service import AccountSyncService

__all__ = [
    "BrokerConnectionService",
    "OrderExecutionService", 
    "AccountSyncService",
]
