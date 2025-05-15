"""
API模型

此模組定義了API使用的數據模型。
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class UserModel(BaseModel):
    """用戶模型"""
    username: str
    email: Optional[str] = None
    disabled: Optional[bool] = None
    hashed_password: str
    scopes: List[str] = []


class TokenModel(BaseModel):
    """令牌模型"""
    access_token: str
    token_type: str
    expires_in: int
    scopes: List[str] = []


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
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TradeRequestModel(BaseModel):
    """交易請求模型"""
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"
    strategy_id: Optional[str] = None
    tags: List[str] = []


class TradeResponseModel(BaseModel):
    """交易響應模型"""
    order_id: str
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus
    filled_quantity: float = 0
    average_price: Optional[float] = None
    commission: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    strategy_id: Optional[str] = None
    tags: List[str] = []


class PositionModel(BaseModel):
    """倉位模型"""
    symbol: str
    quantity: float
    average_price: float
    market_price: float
    market_value: float
    unrealized_pl: float
    unrealized_pl_percent: float
    realized_pl: float
    cost_basis: float
    open_date: datetime


class PortfolioModel(BaseModel):
    """投資組合模型"""
    portfolio_id: str
    name: str
    cash: float
    equity: float
    total_value: float
    day_pl: float
    day_pl_percent: float
    total_pl: float
    total_pl_percent: float
    positions: List[PositionModel] = []
    created_at: datetime
    updated_at: Optional[datetime] = None


class StrategyType(str, Enum):
    """策略類型"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    MACHINE_LEARNING = "machine_learning"
    CUSTOM = "custom"


class StrategyStatus(str, Enum):
    """策略狀態"""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    BACKTEST = "backtest"


class StrategyModel(BaseModel):
    """策略模型"""
    strategy_id: str
    name: str
    description: Optional[str] = None
    type: StrategyType
    status: StrategyStatus
    parameters: Dict[str, Any] = {}
    symbols: List[str] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    performance: Dict[str, Any] = {}


class BacktestRequestModel(BaseModel):
    """回測請求模型"""
    strategy_id: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    symbols: List[str]
    parameters: Dict[str, Any] = {}
    benchmark: Optional[str] = None


class BacktestResponseModel(BaseModel):
    """回測響應模型"""
    backtest_id: str
    strategy_id: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    trades: int
    win_rate: float
    profit_factor: float
    created_at: datetime
    status: str
    results_url: Optional[str] = None


class MarketDataRequestModel(BaseModel):
    """市場數據請求模型"""
    symbols: List[str]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    interval: str = "1d"
    fields: List[str] = ["open", "high", "low", "close", "volume"]


class MarketDataResponseModel(BaseModel):
    """市場數據響應模型"""
    symbol: str
    interval: str
    data: List[Dict[str, Any]]


class SystemStatusModel(BaseModel):
    """系統狀態模型"""
    status: str
    version: str
    uptime: int
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_strategies: int
    pending_orders: int
    last_update: datetime


class WorkflowRequestModel(BaseModel):
    """工作流請求模型"""
    name: str
    template: Optional[str] = None
    active: bool = False
    parameters: Dict[str, Any] = {}


class WorkflowResponseModel(BaseModel):
    """工作流響應模型"""
    workflow_id: str
    name: str
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_execution: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0
    error_count: int = 0


class WorkflowExecutionRequestModel(BaseModel):
    """工作流執行請求模型"""
    workflow_id: str
    data: Dict[str, Any] = {}


class WorkflowExecutionResponseModel(BaseModel):
    """工作流執行響應模型"""
    execution_id: str
    workflow_id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    data: Dict[str, Any] = {}


class SignalGenerationRequestModel(BaseModel):
    """訊號生成請求模型"""
    strategy_id: str
    symbols: List[str]
    parameters: Dict[str, Any] = {}
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SignalGenerationResponseModel(BaseModel):
    """訊號生成響應模型"""
    strategy_id: str
    signals: List[Dict[str, Any]]
    generated_at: datetime
    parameters: Dict[str, Any] = {}
