"""
帳戶同步服務 (Account Sync Service)

此模組提供帳戶資訊同步的統一管理服務，包括：
- 帳戶資訊同步
- 持倉資訊更新
- 資金狀況監控
- 交易記錄同步
- 資料一致性檢查

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable

from src.core.trade_execution_brokers import TradeExecutionBrokerManager
from .broker_connection_service import BrokerConnectionService


logger = logging.getLogger(__name__)


class AccountSyncError(Exception):
    """帳戶同步錯誤"""
    pass


class AccountInfo:
    """
    帳戶資訊類別
    
    Attributes:
        account_id: 帳戶ID
        broker_name: 券商名稱
        cash: 可用現金
        total_value: 總資產價值
        buying_power: 購買力
        positions: 持倉資訊
        orders: 訂單資訊
        last_updated: 最後更新時間
    """

    def __init__(
        self,
        account_id: str,
        broker_name: str,
        cash: float = 0.0,
        total_value: float = 0.0,
        buying_power: float = 0.0
    ):
        """
        初始化帳戶資訊
        
        Args:
            account_id: 帳戶ID
            broker_name: 券商名稱
            cash: 可用現金
            total_value: 總資產價值
            buying_power: 購買力
        """
        self.account_id = account_id
        self.broker_name = broker_name
        self.cash = cash
        self.total_value = total_value
        self.buying_power = buying_power
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.orders: List[Dict[str, Any]] = []
        self.last_updated = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            Dict[str, Any]: 帳戶資訊字典
        """
        return {
            "account_id": self.account_id,
            "broker_name": self.broker_name,
            "cash": self.cash,
            "total_value": self.total_value,
            "buying_power": self.buying_power,
            "positions": self.positions,
            "orders": self.orders,
            "last_updated": self.last_updated.isoformat()
        }


class AccountSyncService:
    """
    帳戶同步服務
    
    提供統一的帳戶資訊同步管理介面，包括帳戶資訊、
    持倉、資金等資料的定期同步和更新。
    
    Attributes:
        _connection_service: 券商連接服務
        _trade_executor: 交易執行器
        _accounts: 帳戶資訊快取
        _sync_thread: 同步執行緒
        _is_syncing: 同步狀態標誌
        _sync_interval: 同步間隔時間(秒)
        _sync_callbacks: 同步完成回調函數列表
        _lock: 執行緒鎖
    """

    def __init__(
        self,
        connection_service: Optional[BrokerConnectionService] = None,
        sync_interval: int = 30
    ):
        """
        初始化帳戶同步服務
        
        Args:
            connection_service: 券商連接服務實例
            sync_interval: 同步間隔時間(秒)
        """
        self._connection_service = connection_service or BrokerConnectionService()
        self._trade_executor = self._connection_service._trade_executor
        self._accounts: Dict[str, AccountInfo] = {}
        self._sync_thread: Optional[threading.Thread] = None
        self._is_syncing = False
        self._sync_interval = sync_interval
        self._sync_callbacks: List[Callable[[str, AccountInfo], None]] = []
        self._lock = threading.Lock()
        
        logger.info("帳戶同步服務初始化成功")

    def start_sync(self) -> None:
        """
        開始自動同步
        
        啟動背景執行緒定期同步所有券商的帳戶資訊。
        
        Raises:
            AccountSyncError: 同步啟動失敗時拋出
        """
        if self._is_syncing:
            logger.warning("帳戶同步已在運行中")
            return
            
        try:
            self._is_syncing = True
            self._sync_thread = threading.Thread(
                target=self._sync_loop,
                daemon=True
            )
            self._sync_thread.start()
            logger.info("帳戶自動同步已啟動")
        except Exception as e:
            self._is_syncing = False
            logger.error("啟動帳戶同步失敗: %s", e)
            raise AccountSyncError("同步啟動失敗") from e

    def stop_sync(self) -> None:
        """
        停止自動同步
        
        停止背景同步執行緒，清理資源。
        """
        self._is_syncing = False
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5)
        logger.info("帳戶自動同步已停止")

    def sync_account(self, broker_name: str) -> AccountInfo:
        """
        同步指定券商的帳戶資訊
        
        Args:
            broker_name: 券商名稱
            
        Returns:
            AccountInfo: 同步後的帳戶資訊
            
        Raises:
            AccountSyncError: 同步失敗時拋出
        """
        try:
            # 檢查券商連接
            if not self._is_broker_connected(broker_name):
                raise AccountSyncError(f"券商 {broker_name} 未連接")
            
            broker = self._trade_executor.brokers[broker_name]
            
            # 獲取帳戶基本資訊
            account_info = self._get_account_info(broker, broker_name)
            
            # 獲取持倉資訊
            positions = self._get_positions(broker)
            account_info.positions = positions
            
            # 獲取訂單資訊
            orders = self._get_orders(broker)
            account_info.orders = orders
            
            # 更新快取
            with self._lock:
                self._accounts[broker_name] = account_info
            
            # 觸發回調
            for callback in self._sync_callbacks:
                try:
                    callback(broker_name, account_info)
                except Exception as e:
                    logger.error("執行同步回調時發生錯誤: %s", e)
            
            logger.info("券商 %s 帳戶資訊同步完成", broker_name)
            return account_info
            
        except Exception as e:
            logger.error("同步券商 %s 帳戶資訊失敗: %s", broker_name, e)
            raise AccountSyncError(f"帳戶同步失敗: {broker_name}") from e

    def get_account_info(self, broker_name: str) -> Optional[AccountInfo]:
        """
        獲取帳戶資訊
        
        Args:
            broker_name: 券商名稱
            
        Returns:
            Optional[AccountInfo]: 帳戶資訊，不存在時返回 None
        """
        with self._lock:
            return self._accounts.get(broker_name)

    def get_all_accounts(self) -> Dict[str, AccountInfo]:
        """
        獲取所有帳戶資訊
        
        Returns:
            Dict[str, AccountInfo]: 所有帳戶資訊
        """
        with self._lock:
            return self._accounts.copy()

    def get_total_portfolio_value(self) -> float:
        """
        獲取總投資組合價值
        
        Returns:
            float: 總投資組合價值
        """
        total_value = 0.0
        with self._lock:
            for account in self._accounts.values():
                total_value += account.total_value
        return total_value

    def get_total_cash(self) -> float:
        """
        獲取總現金
        
        Returns:
            float: 總現金
        """
        total_cash = 0.0
        with self._lock:
            for account in self._accounts.values():
                total_cash += account.cash
        return total_cash

    def get_consolidated_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        獲取合併持倉資訊
        
        Returns:
            Dict[str, Dict[str, Any]]: 合併後的持倉資訊
        """
        consolidated = {}
        
        with self._lock:
            for account in self._accounts.values():
                for symbol, position in account.positions.items():
                    if symbol not in consolidated:
                        consolidated[symbol] = {
                            "symbol": symbol,
                            "quantity": 0,
                            "avg_cost": 0.0,
                            "market_value": 0.0,
                            "unrealized_pnl": 0.0,
                            "brokers": []
                        }
                    
                    # 合併數量
                    old_quantity = consolidated[symbol]["quantity"]
                    new_quantity = old_quantity + position.get("quantity", 0)
                    
                    # 計算平均成本
                    if new_quantity > 0:
                        old_cost = consolidated[symbol]["avg_cost"] * old_quantity
                        new_cost = position.get("avg_cost", 0) * position.get("quantity", 0)
                        consolidated[symbol]["avg_cost"] = (old_cost + new_cost) / new_quantity
                    
                    consolidated[symbol]["quantity"] = new_quantity
                    consolidated[symbol]["market_value"] += position.get("market_value", 0)
                    consolidated[symbol]["unrealized_pnl"] += position.get("unrealized_pnl", 0)
                    consolidated[symbol]["brokers"].append(account.broker_name)
        
        return consolidated

    def add_sync_callback(self, callback: Callable[[str, AccountInfo], None]) -> None:
        """
        添加同步完成回調函數
        
        Args:
            callback: 回調函數，接收券商名稱和帳戶資訊
        """
        self._sync_callbacks.append(callback)

    def force_sync_all(self) -> Dict[str, AccountInfo]:
        """
        強制同步所有券商帳戶
        
        Returns:
            Dict[str, AccountInfo]: 同步後的所有帳戶資訊
        """
        results = {}
        
        for broker_name in self._trade_executor.brokers:
            try:
                if self._is_broker_connected(broker_name):
                    account_info = self.sync_account(broker_name)
                    results[broker_name] = account_info
                else:
                    logger.warning("券商 %s 未連接，跳過同步", broker_name)
            except Exception as e:
                logger.error("同步券商 %s 失敗: %s", broker_name, e)
        
        return results

    def _sync_loop(self) -> None:
        """
        同步迴圈的背景執行緒
        
        定期同步所有已連接券商的帳戶資訊。
        """
        while self._is_syncing:
            try:
                self.force_sync_all()
                time.sleep(self._sync_interval)
                
            except Exception as e:
                logger.error("同步迴圈發生錯誤: %s", e)
                time.sleep(60)  # 錯誤時等待更長時間

    def _is_broker_connected(self, broker_name: str) -> bool:
        """
        檢查券商是否已連接
        
        Args:
            broker_name: 券商名稱
            
        Returns:
            bool: 是否已連接
        """
        status = self._connection_service.get_connection_status(broker_name)
        return status.get("status") == "connected"

    def _get_account_info(self, broker: Any, broker_name: str) -> AccountInfo:
        """
        獲取券商帳戶基本資訊
        
        Args:
            broker: 券商適配器實例
            broker_name: 券商名稱
            
        Returns:
            AccountInfo: 帳戶基本資訊
        """
        try:
            # 從券商適配器獲取帳戶資訊
            account_id = getattr(broker, 'account_id', broker_name)
            cash = getattr(broker, 'cash', 0.0)
            total_value = getattr(broker, 'total_value', 0.0)
            
            # 計算購買力 (簡化版本)
            buying_power = cash * 1.0  # 現金帳戶購買力等於現金
            
            return AccountInfo(
                account_id=account_id,
                broker_name=broker_name,
                cash=cash,
                total_value=total_value,
                buying_power=buying_power
            )
            
        except Exception as e:
            logger.error("獲取券商 %s 帳戶基本資訊失敗: %s", broker_name, e)
            # 返回預設帳戶資訊
            return AccountInfo(
                account_id=broker_name,
                broker_name=broker_name
            )

    def _get_positions(self, broker: Any) -> Dict[str, Dict[str, Any]]:
        """
        獲取持倉資訊
        
        Args:
            broker: 券商適配器實例
            
        Returns:
            Dict[str, Dict[str, Any]]: 持倉資訊
        """
        try:
            if hasattr(broker, 'positions') and broker.positions:
                return broker.positions.copy()
            else:
                return {}
        except Exception as e:
            logger.error("獲取持倉資訊失敗: %s", e)
            return {}

    def _get_orders(self, broker: Any) -> List[Dict[str, Any]]:
        """
        獲取訂單資訊
        
        Args:
            broker: 券商適配器實例
            
        Returns:
            List[Dict[str, Any]]: 訂單資訊列表
        """
        try:
            if hasattr(broker, 'orders') and broker.orders:
                return list(broker.orders.values())
            else:
                return []
        except Exception as e:
            logger.error("獲取訂單資訊失敗: %s", e)
            return []
