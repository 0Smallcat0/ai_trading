"""Interactive Brokers 市場數據模組

此模組提供 IB API 的市場數據獲取功能，包括實時報價、歷史數據、
技術指標等。支援股票、期權、期貨等多種金融工具。

版本: v1.0
作者: AI Trading System
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from enum import Enum

try:
    from ibapi.contract import Contract
    from ibapi.common import TickerId, BarData
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    # 定義模擬類型
    class Contract:
        def __init__(self):
            pass
    class BarData:
        def __init__(self):
            pass
    TickerId = int

# 設定日誌
logger = logging.getLogger("execution.ib.market_data")


class TickType(Enum):
    """報價類型枚舉"""
    BID_SIZE = 0
    BID_PRICE = 1
    ASK_PRICE = 2
    ASK_SIZE = 3
    LAST_PRICE = 4
    LAST_SIZE = 5
    HIGH = 6
    LOW = 7
    VOLUME = 8
    CLOSE = 9
    BID_OPTION = 10
    ASK_OPTION = 11
    LAST_OPTION = 12
    MODEL_OPTION = 13


class BarSize(Enum):
    """K線週期枚舉"""
    SEC_1 = "1 sec"
    SEC_5 = "5 secs"
    SEC_10 = "10 secs"
    SEC_15 = "15 secs"
    SEC_30 = "30 secs"
    MIN_1 = "1 min"
    MIN_2 = "2 mins"
    MIN_3 = "3 mins"
    MIN_5 = "5 mins"
    MIN_10 = "10 mins"
    MIN_15 = "15 mins"
    MIN_20 = "20 mins"
    MIN_30 = "30 mins"
    HOUR_1 = "1 hour"
    HOUR_2 = "2 hours"
    HOUR_3 = "3 hours"
    HOUR_4 = "4 hours"
    HOUR_8 = "8 hours"
    DAY_1 = "1 day"
    WEEK_1 = "1 week"
    MONTH_1 = "1 month"


@dataclass
class MarketData:
    """市場數據類"""
    symbol: str
    bid_price: float
    ask_price: float
    last_price: float
    bid_size: int
    ask_size: int
    last_size: int
    volume: int
    high: float
    low: float
    close: float
    timestamp: datetime


@dataclass
class HistoricalBar:
    """歷史K線數據類"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    wap: float  # 加權平均價
    count: int  # 交易次數


class IBMarketDataManager:
    """IB 市場數據管理器
    
    提供完整的市場數據獲取功能，包括實時報價、歷史數據、技術指標等。
    """

    def __init__(self, client=None):
        """初始化市場數據管理器
        
        Args:
            client: IB API 客戶端
        """
        self.client = client
        self._req_id_counter = 1000
        self._market_data: Dict[int, MarketData] = {}
        self._historical_data: Dict[int, List[HistoricalBar]] = {}
        self._data_callbacks: Dict[int, Callable] = {}

    def subscribe_market_data(
        self,
        contract: Contract,
        callback: Optional[Callable] = None
    ) -> Optional[int]:
        """訂閱實時市場數據
        
        Args:
            contract: 合約物件
            callback: 數據回調函數
            
        Returns:
            int: 請求 ID 或 None
        """
        try:
            if not self.client or not self.client.isConnected():
                logger.error("IB API 未連接")
                return None

            req_id = self._get_next_req_id()
            
            # 初始化市場數據
            self._market_data[req_id] = MarketData(
                symbol=contract.symbol,
                bid_price=0.0,
                ask_price=0.0,
                last_price=0.0,
                bid_size=0,
                ask_size=0,
                last_size=0,
                volume=0,
                high=0.0,
                low=0.0,
                close=0.0,
                timestamp=datetime.now()
            )

            # 設定回調函數
            if callback:
                self._data_callbacks[req_id] = callback

            # 請求市場數據
            self.client.reqMktData(req_id, contract, "", False, False, [])
            
            logger.debug("已訂閱市場數據 - 代號: %s, 請求 ID: %d", contract.symbol, req_id)
            return req_id

        except Exception as e:
            logger.exception("訂閱市場數據失敗: %s", e)
            return None

    def unsubscribe_market_data(self, req_id: int) -> bool:
        """取消訂閱市場數據
        
        Args:
            req_id: 請求 ID
            
        Returns:
            bool: 是否成功
        """
        try:
            if not self.client or not self.client.isConnected():
                logger.error("IB API 未連接")
                return False

            self.client.cancelMktData(req_id)
            
            # 清理數據
            if req_id in self._market_data:
                del self._market_data[req_id]
            if req_id in self._data_callbacks:
                del self._data_callbacks[req_id]

            logger.debug("已取消訂閱市場數據 - 請求 ID: %d", req_id)
            return True

        except Exception as e:
            logger.exception("取消訂閱市場數據失敗: %s", e)
            return False

    def get_historical_data(
        self,
        contract: Contract,
        duration: str = "1 D",
        bar_size: BarSize = BarSize.MIN_1,
        what_to_show: str = "TRADES",
        use_rth: bool = True
    ) -> Optional[List[HistoricalBar]]:
        """獲取歷史數據
        
        Args:
            contract: 合約物件
            duration: 數據期間 (如 "1 D", "1 W", "1 M")
            bar_size: K線週期
            what_to_show: 數據類型 ("TRADES", "MIDPOINT", "BID", "ASK")
            use_rth: 是否只使用常規交易時間
            
        Returns:
            List[HistoricalBar]: 歷史數據列表或 None
        """
        try:
            if not self.client or not self.client.isConnected():
                logger.error("IB API 未連接")
                return None

            req_id = self._get_next_req_id()
            end_time = datetime.now().strftime("%Y%m%d %H:%M:%S")

            # 請求歷史數據
            self.client.reqHistoricalData(
                req_id, contract, end_time, duration,
                bar_size.value, what_to_show, int(use_rth), 1, False, []
            )

            # 等待數據返回（簡化實現）
            timeout = 10
            start_time = time.time()
            while req_id not in self._historical_data and time.time() - start_time < timeout:
                time.sleep(0.1)

            if req_id in self._historical_data:
                data = self._historical_data[req_id]
                del self._historical_data[req_id]  # 清理數據
                
                logger.debug(
                    "獲取歷史數據成功 - 代號: %s, 數據量: %d",
                    contract.symbol, len(data)
                )
                return data
            else:
                logger.warning("獲取歷史數據超時")
                return None

        except Exception as e:
            logger.exception("獲取歷史數據失敗: %s", e)
            return None

    def get_current_price(self, contract: Contract) -> Optional[float]:
        """獲取當前價格
        
        Args:
            contract: 合約物件
            
        Returns:
            float: 當前價格或 None
        """
        try:
            # 訂閱市場數據
            req_id = self.subscribe_market_data(contract)
            if req_id is None:
                return None

            # 等待價格數據
            timeout = 5
            start_time = time.time()
            while time.time() - start_time < timeout:
                if req_id in self._market_data:
                    market_data = self._market_data[req_id]
                    if market_data.last_price > 0:
                        price = market_data.last_price
                        self.unsubscribe_market_data(req_id)
                        return price
                time.sleep(0.1)

            # 清理
            self.unsubscribe_market_data(req_id)
            logger.warning("獲取當前價格超時")
            return None

        except Exception as e:
            logger.exception("獲取當前價格失敗: %s", e)
            return None

    def get_market_data(self, req_id: int) -> Optional[MarketData]:
        """獲取市場數據
        
        Args:
            req_id: 請求 ID
            
        Returns:
            MarketData: 市場數據或 None
        """
        return self._market_data.get(req_id)

    def on_tick_price(self, req_id: int, tick_type: int, price: float) -> None:
        """處理價格數據回調
        
        Args:
            req_id: 請求 ID
            tick_type: 價格類型
            price: 價格
        """
        try:
            if req_id not in self._market_data:
                return

            market_data = self._market_data[req_id]
            market_data.timestamp = datetime.now()

            # 更新對應的價格
            if tick_type == TickType.BID_PRICE.value:
                market_data.bid_price = price
            elif tick_type == TickType.ASK_PRICE.value:
                market_data.ask_price = price
            elif tick_type == TickType.LAST_PRICE.value:
                market_data.last_price = price
            elif tick_type == TickType.HIGH.value:
                market_data.high = price
            elif tick_type == TickType.LOW.value:
                market_data.low = price
            elif tick_type == TickType.CLOSE.value:
                market_data.close = price

            # 調用回調函數
            if req_id in self._data_callbacks:
                self._data_callbacks[req_id](market_data)

        except Exception as e:
            logger.exception("處理價格數據失敗: %s", e)

    def on_tick_size(self, req_id: int, tick_type: int, size: int) -> None:
        """處理數量數據回調
        
        Args:
            req_id: 請求 ID
            tick_type: 數量類型
            size: 數量
        """
        try:
            if req_id not in self._market_data:
                return

            market_data = self._market_data[req_id]
            market_data.timestamp = datetime.now()

            # 更新對應的數量
            if tick_type == TickType.BID_SIZE.value:
                market_data.bid_size = size
            elif tick_type == TickType.ASK_SIZE.value:
                market_data.ask_size = size
            elif tick_type == TickType.LAST_SIZE.value:
                market_data.last_size = size
            elif tick_type == TickType.VOLUME.value:
                market_data.volume = size

            # 調用回調函數
            if req_id in self._data_callbacks:
                self._data_callbacks[req_id](market_data)

        except Exception as e:
            logger.exception("處理數量數據失敗: %s", e)

    def on_historical_data(self, req_id: int, bar: BarData) -> None:
        """處理歷史數據回調
        
        Args:
            req_id: 請求 ID
            bar: K線數據
        """
        try:
            if req_id not in self._historical_data:
                self._historical_data[req_id] = []

            historical_bar = HistoricalBar(
                timestamp=datetime.strptime(bar.date, "%Y%m%d %H:%M:%S"),
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                wap=bar.wap,
                count=bar.count
            )

            self._historical_data[req_id].append(historical_bar)

        except Exception as e:
            logger.exception("處理歷史數據失敗: %s", e)

    def _get_next_req_id(self) -> int:
        """獲取下一個請求 ID"""
        self._req_id_counter += 1
        return self._req_id_counter

    def cleanup(self) -> None:
        """清理資源"""
        try:
            # 取消所有訂閱
            for req_id in list(self._market_data.keys()):
                self.unsubscribe_market_data(req_id)

            # 清理數據
            self._market_data.clear()
            self._historical_data.clear()
            self._data_callbacks.clear()

            logger.debug("市場數據管理器清理完成")

        except Exception as e:
            logger.exception("清理市場數據管理器失敗: %s", e)
