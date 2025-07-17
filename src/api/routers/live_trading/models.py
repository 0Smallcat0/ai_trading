"""Live Trading API 數據模型

此模組定義了實時交易 API 的所有請求和響應模型。
包含券商連接、交易執行、風險控制和通知相關的數據結構。
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


# 枚舉類型定義
class BrokerType(str, Enum):
    """券商類型"""
    FUBON = "fubon"
    CATHAY = "cathay"
    YUANTA = "yuanta"
    CAPITAL = "capital"
    SINOPAC = "sinopac"


class OrderType(str, Enum):
    """訂單類型"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """訂單方向"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """訂單狀態"""
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL_FILLED = "partial_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class RiskLevel(str, Enum):
    """風險等級"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(str, Enum):
    """通知類型"""
    TRADE = "trade"
    RISK_ALERT = "risk_alert"
    SYSTEM_STATUS = "system_status"
    ORDER_UPDATE = "order_update"


# 券商連接相關模型
class BrokerAuthRequest(BaseModel):
    """券商認證請求"""
    broker_type: BrokerType = Field(..., description="券商類型")
    username: str = Field(..., description="券商帳號")
    password: str = Field(..., description="券商密碼")
    api_key: Optional[str] = Field(None, description="API 金鑰")
    api_secret: Optional[str] = Field(None, description="API 密鑰")
    cert_path: Optional[str] = Field(None, description="憑證路徑")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "broker_type": "fubon",
                "username": "your_username",
                "password": "your_password",
                "api_key": "your_api_key",
                "api_secret": "your_api_secret"
            }
        }
    }


class BrokerAuthResponse(BaseModel):
    """券商認證響應"""
    success: bool = Field(..., description="認證是否成功")
    session_id: str = Field(..., description="會話 ID")
    broker_type: BrokerType = Field(..., description="券商類型")
    expires_at: datetime = Field(..., description="會話過期時間")
    message: str = Field(..., description="認證結果訊息")


class AccountInfoResponse(BaseModel):
    """帳戶資訊響應"""
    account_id: str = Field(..., description="帳戶 ID")
    account_name: str = Field(..., description="帳戶名稱")
    broker_type: BrokerType = Field(..., description="券商類型")
    total_equity: Decimal = Field(..., description="總權益")
    available_cash: Decimal = Field(..., description="可用現金")
    margin_used: Decimal = Field(..., description="已用保證金")
    margin_available: Decimal = Field(..., description="可用保證金")
    buying_power: Decimal = Field(..., description="購買力")
    unrealized_pnl: Decimal = Field(..., description="未實現損益")
    realized_pnl: Decimal = Field(..., description="已實現損益")
    last_updated: datetime = Field(..., description="最後更新時間")


class PositionResponse(BaseModel):
    """持倉響應"""
    symbol: str = Field(..., description="股票代碼")
    quantity: int = Field(..., description="持倉數量")
    average_price: Decimal = Field(..., description="平均成本")
    current_price: Decimal = Field(..., description="當前價格")
    market_value: Decimal = Field(..., description="市值")
    unrealized_pnl: Decimal = Field(..., description="未實現損益")
    unrealized_pnl_percent: Decimal = Field(..., description="未實現損益百分比")
    side: OrderSide = Field(..., description="持倉方向")
    last_updated: datetime = Field(..., description="最後更新時間")


class OrderResponse(BaseModel):
    """訂單響應"""
    order_id: str = Field(..., description="訂單 ID")
    symbol: str = Field(..., description="股票代碼")
    side: OrderSide = Field(..., description="買賣方向")
    order_type: OrderType = Field(..., description="訂單類型")
    quantity: int = Field(..., description="訂單數量")
    price: Optional[Decimal] = Field(None, description="訂單價格")
    stop_price: Optional[Decimal] = Field(None, description="停損價格")
    status: OrderStatus = Field(..., description="訂單狀態")
    filled_quantity: int = Field(0, description="已成交數量")
    filled_price: Optional[Decimal] = Field(None, description="成交價格")
    commission: Decimal = Field(0, description="手續費")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")


# 交易執行相關模型
class PlaceOrderRequest(BaseModel):
    """下單請求"""
    symbol: str = Field(..., description="股票代碼")
    side: OrderSide = Field(..., description="買賣方向")
    order_type: OrderType = Field(..., description="訂單類型")
    quantity: int = Field(..., gt=0, description="訂單數量")
    price: Optional[Decimal] = Field(None, gt=0, description="訂單價格")
    stop_price: Optional[Decimal] = Field(None, gt=0, description="停損價格")
    time_in_force: str = Field("DAY", description="有效期限")
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v, info):
        if info.data.get('order_type') in [OrderType.LIMIT, OrderType.STOP_LIMIT] and v is None:
            raise ValueError('限價單和停損限價單必須指定價格')
        return v

    @field_validator('stop_price')
    @classmethod
    def validate_stop_price(cls, v, info):
        if info.data.get('order_type') in [OrderType.STOP, OrderType.STOP_LIMIT] and v is None:
            raise ValueError('停損單和停損限價單必須指定停損價格')
        return v


class PlaceOrderResponse(BaseModel):
    """下單響應"""
    success: bool = Field(..., description="下單是否成功")
    order_id: Optional[str] = Field(None, description="訂單 ID")
    message: str = Field(..., description="下單結果訊息")
    order_details: Optional[OrderResponse] = Field(None, description="訂單詳情")


class CancelOrderRequest(BaseModel):
    """撤單請求"""
    order_id: str = Field(..., description="訂單 ID")


class ModifyOrderRequest(BaseModel):
    """修改訂單請求"""
    order_id: str = Field(..., description="訂單 ID")
    quantity: Optional[int] = Field(None, gt=0, description="新數量")
    price: Optional[Decimal] = Field(None, gt=0, description="新價格")
    stop_price: Optional[Decimal] = Field(None, gt=0, description="新停損價格")


class CloseAllPositionsRequest(BaseModel):
    """一鍵平倉請求"""
    symbols: Optional[List[str]] = Field(None, description="指定股票代碼，為空則平倉所有")
    order_type: OrderType = Field(OrderType.MARKET, description="平倉訂單類型")


# 風險控制相關模型
class RiskCheckRequest(BaseModel):
    """風險檢查請求"""
    symbol: str = Field(..., description="股票代碼")
    side: OrderSide = Field(..., description="買賣方向")
    quantity: int = Field(..., gt=0, description="數量")
    price: Optional[Decimal] = Field(None, description="價格")


class RiskCheckResponse(BaseModel):
    """風險檢查響應"""
    approved: bool = Field(..., description="是否通過風險檢查")
    risk_level: RiskLevel = Field(..., description="風險等級")
    warnings: List[str] = Field(default_factory=list, description="風險警告")
    max_allowed_quantity: Optional[int] = Field(None, description="最大允許數量")
    required_margin: Optional[Decimal] = Field(None, description="所需保證金")
    message: str = Field(..., description="檢查結果訊息")


class EmergencyStopRequest(BaseModel):
    """緊急停損請求"""
    reason: str = Field(..., description="停損原因")
    symbols: Optional[List[str]] = Field(None, description="指定股票代碼")


class FundMonitorResponse(BaseModel):
    """資金監控響應"""
    total_equity: Decimal = Field(..., description="總權益")
    available_cash: Decimal = Field(..., description="可用現金")
    margin_ratio: Decimal = Field(..., description="保證金比率")
    risk_level: RiskLevel = Field(..., description="風險等級")
    daily_pnl: Decimal = Field(..., description="當日損益")
    daily_pnl_percent: Decimal = Field(..., description="當日損益百分比")
    max_drawdown: Decimal = Field(..., description="最大回撤")
    alerts: List[str] = Field(default_factory=list, description="資金警報")


# 通知相關模型
class TradeNotification(BaseModel):
    """交易通知"""
    notification_type: NotificationType = Field(NotificationType.TRADE, description="通知類型")
    order_id: str = Field(..., description="訂單 ID")
    symbol: str = Field(..., description="股票代碼")
    side: OrderSide = Field(..., description="買賣方向")
    quantity: int = Field(..., description="數量")
    price: Decimal = Field(..., description="價格")
    status: OrderStatus = Field(..., description="訂單狀態")
    timestamp: datetime = Field(..., description="時間戳")
    message: str = Field(..., description="通知訊息")


class RiskAlert(BaseModel):
    """風險警報"""
    notification_type: NotificationType = Field(NotificationType.RISK_ALERT, description="通知類型")
    alert_level: RiskLevel = Field(..., description="警報等級")
    symbol: Optional[str] = Field(None, description="相關股票代碼")
    current_value: Decimal = Field(..., description="當前值")
    threshold_value: Decimal = Field(..., description="閾值")
    timestamp: datetime = Field(..., description="時間戳")
    message: str = Field(..., description="警報訊息")
    action_required: bool = Field(False, description="是否需要採取行動")


class SystemStatusNotification(BaseModel):
    """系統狀態通知"""
    notification_type: NotificationType = Field(NotificationType.SYSTEM_STATUS, description="通知類型")
    component: str = Field(..., description="系統組件")
    status: str = Field(..., description="狀態")
    timestamp: datetime = Field(..., description="時間戳")
    message: str = Field(..., description="狀態訊息")
    severity: str = Field("info", description="嚴重程度")
