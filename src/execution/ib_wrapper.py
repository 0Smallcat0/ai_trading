"""Interactive Brokers API 包裝器模組

此模組提供 IB API 的包裝器類，處理所有來自 IB API 的回調事件。
包括錯誤處理、連接管理、訂單狀態更新、執行詳情和佣金報告。

版本: v1.0
作者: AI Trading System
"""

import logging
from typing import TYPE_CHECKING, Optional

try:
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.execution import Execution
    from ibapi.commission_report import CommissionReport
    from ibapi.common import OrderId, TickerId
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    # 定義模擬類型以避免 NameError
    class EWrapper:
        """模擬 EWrapper 類"""
        def __init__(self):
            pass

    class Contract:
        """模擬 Contract 類"""
        def __init__(self):
            self.symbol = ""
            self.secType = ""
            self.exchange = ""
            self.currency = ""

    class Execution:
        """模擬 Execution 類"""
        def __init__(self):
            pass

    class CommissionReport:
        """模擬 CommissionReport 類"""
        def __init__(self):
            pass

    OrderId = int
    TickerId = int

# 避免循環導入，使用字符串類型提示

# 設定日誌
logger = logging.getLogger("execution.ib.wrapper")


class IBWrapper(EWrapper):
    """Interactive Brokers API 包裝器
    
    此類繼承自 IB API 的 EWrapper，處理所有來自 IB API 的回調事件。
    提供統一的錯誤處理、連接管理和事件通知機制。
    
    Attributes:
        adapter: IB 適配器實例的引用
    """

    def __init__(self, adapter) -> None:
        """初始化包裝器
        
        Args:
            adapter: IB 適配器實例
            
        Raises:
            TypeError: 如果 adapter 參數無效
        """
        super().__init__()
        if adapter is None:
            raise TypeError("adapter 參數不能為 None")
        self.adapter = adapter

    def error(
        self,
        reqId: TickerId,
        errorCode: int,
        errorString: str,
        advancedOrderRejectJson: str = ""
    ) -> None:
        """錯誤處理回調
        
        處理來自 IB API 的錯誤和警告訊息，根據錯誤代碼進行分類處理。
        
        Args:
            reqId: 請求 ID
            errorCode: 錯誤代碼
            errorString: 錯誤訊息
            advancedOrderRejectJson: 進階訂單拒絕 JSON（未使用）
            
        Note:
            錯誤代碼分類：
            - 2104, 2106, 2158: 市場數據警告，可忽略
            - ≥2000: 系統訊息
            - <2000: 實際錯誤
        """
        try:
            if errorCode in [2104, 2106, 2158]:  # 市場數據警告，可忽略
                logger.debug("IB 警告 %d: %s", errorCode, errorString)
            elif errorCode >= 2000:  # 系統訊息
                logger.info("IB 系統訊息 %d: %s", errorCode, errorString)
            else:  # 錯誤
                logger.error("IB 錯誤 %d: %s", errorCode, errorString)

            # 通知適配器錯誤
            if hasattr(self.adapter, '_on_error'):
                self.adapter._on_error(reqId, errorCode, errorString)
                
        except Exception as e:
            logger.exception("處理錯誤回調時發生異常: %s", e)

    def connectAck(self) -> None:
        """連接確認回調
        
        當成功連接到 IB API 時被調用，設置適配器的連接狀態。
        """
        try:
            logger.info("IB API 連接確認")
            self.adapter._connected = True  # pylint: disable=protected-access
        except Exception as e:
            logger.exception("處理連接確認時發生異常: %s", e)

    def connectionClosed(self) -> None:
        """連接關閉回調
        
        當 IB API 連接關閉時被調用，更新適配器的連接狀態。
        """
        try:
            logger.info("IB API 連接關閉")
            self.adapter._connected = False  # pylint: disable=protected-access
        except Exception as e:
            logger.exception("處理連接關閉時發生異常: %s", e)

    def nextValidId(self, orderId: OrderId) -> None:
        """下一個有效訂單 ID 回調
        
        IB API 提供下一個可用的訂單 ID，用於後續的訂單提交。
        
        Args:
            orderId: 下一個有效的訂單 ID
        """
        try:
            self.adapter._next_order_id = orderId  # pylint: disable=protected-access
            logger.debug("下一個有效訂單 ID: %d", orderId)
        except Exception as e:
            logger.exception("處理下一個有效訂單 ID 時發生異常: %s", e)

    def orderStatus(
        self,
        orderId: OrderId,
        status: str,
        filled: float,
        remaining: float,
        avgFillPrice: float,
        permId: int,
        parentId: int,
        lastFillPrice: float,
        clientId: int,
        whyHeld: str,
        mktCapPrice: float
    ) -> None:
        """訂單狀態更新回調
        
        當訂單狀態發生變化時被調用，包括提交、成交、取消等狀態。
        
        Args:
            orderId: 訂單 ID
            status: 訂單狀態
            filled: 已成交數量
            remaining: 剩餘數量
            avgFillPrice: 平均成交價格
            permId: 永久 ID（未使用）
            parentId: 父訂單 ID（未使用）
            lastFillPrice: 最後成交價格（未使用）
            clientId: 客戶端 ID（未使用）
            whyHeld: 持有原因（未使用）
            mktCapPrice: 市價上限（未使用）
        """
        try:
            logger.debug(
                "訂單狀態更新 - ID: %d, 狀態: %s, 已成交: %.2f",
                orderId, status, filled
            )

            # 更新訂單狀態
            if hasattr(self.adapter, '_on_order_status'):
                self.adapter._on_order_status(  # pylint: disable=protected-access
                    orderId, status, filled, remaining, avgFillPrice
                )
        except Exception as e:
            logger.exception("處理訂單狀態更新時發生異常: %s", e)

    def execDetails(
        self,
        reqId: int,
        contract: Contract,
        execution: Execution
    ) -> None:
        """執行詳情回調
        
        當訂單執行時被調用，提供詳細的執行資訊。
        
        Args:
            reqId: 請求 ID（未使用）
            contract: 執行的合約
            execution: 執行詳情
        """
        try:
            logger.debug(
                "執行詳情 - 訂單 ID: %s, 數量: %s",
                execution.orderId, execution.shares
            )

            # 通知適配器執行詳情
            if hasattr(self.adapter, '_on_execution'):
                self.adapter._on_execution(  # pylint: disable=protected-access
                    reqId, contract, execution
                )
        except Exception as e:
            logger.exception("處理執行詳情時發生異常: %s", e)

    def commissionReport(self, commissionReport: CommissionReport) -> None:
        """佣金報告回調
        
        當收到佣金報告時被調用，提供交易的佣金資訊。
        
        Args:
            commissionReport: 佣金報告物件
        """
        try:
            logger.debug(
                "佣金報告 - 執行 ID: %s, 佣金: %s",
                commissionReport.execId, commissionReport.commission
            )

            # 通知適配器佣金報告
            if hasattr(self.adapter, '_on_commission'):
                self.adapter._on_commission(  # pylint: disable=protected-access
                    commissionReport
                )
        except Exception as e:
            logger.exception("處理佣金報告時發生異常: %s", e)

    def tickPrice(
        self,
        reqId: TickerId,
        tickType: int,
        price: float,
        attrib: object
    ) -> None:
        """價格數據回調
        
        當收到市場價格數據時被調用。
        
        Args:
            reqId: 請求 ID
            tickType: 價格類型
            price: 價格
            attrib: 屬性物件（未使用）
        """
        try:
            logger.debug(
                "價格數據 - 請求 ID: %d, 類型: %d, 價格: %.2f",
                reqId, tickType, price
            )

            # 通知適配器價格數據
            if hasattr(self.adapter, '_on_tick_price'):
                self.adapter._on_tick_price(  # pylint: disable=protected-access
                    reqId, tickType, price
                )
        except Exception as e:
            logger.exception("處理價格數據時發生異常: %s", e)

    def tickSize(
        self,
        reqId: TickerId,
        tickType: int,
        size: int
    ) -> None:
        """數量數據回調
        
        當收到市場數量數據時被調用。
        
        Args:
            reqId: 請求 ID
            tickType: 數量類型
            size: 數量
        """
        try:
            logger.debug(
                "數量數據 - 請求 ID: %d, 類型: %d, 數量: %d",
                reqId, tickType, size
            )

            # 通知適配器數量數據
            if hasattr(self.adapter, '_on_tick_size'):
                self.adapter._on_tick_size(  # pylint: disable=protected-access
                    reqId, tickType, size
                )
        except Exception as e:
            logger.exception("處理數量數據時發生異常: %s", e)
