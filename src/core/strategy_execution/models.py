"""
策略執行引擎數據模型

此模組定義了策略執行引擎中使用的所有數據模型，包括：
- 交易訊號模型
- 執行訂單模型
- 執行結果模型
- 滑點分析模型
- 執行配置模型
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """訊號類型枚舉"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


class ExecutionMode(Enum):
    """執行模式枚舉"""
    IMMEDIATE = "immediate"  # 立即執行
    TWAP = "twap"  # 時間加權平均價格
    VWAP = "vwap"  # 成交量加權平均價格
    BATCH = "batch"  # 分批執行


class ExecutionStatus(Enum):
    """執行狀態枚舉"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TradingSignal:
    """交易訊號數據模型
    
    此模型定義了策略產生的交易訊號格式。
    
    Attributes:
        symbol: 股票代碼
        signal_type: 訊號類型
        confidence: 信心度 (0-1)
        timestamp: 訊號產生時間
        price: 建議價格
        quantity: 建議數量
        strategy_name: 策略名稱
        metadata: 額外資訊
    """
    symbol: str
    signal_type: SignalType
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    price: Optional[float] = None
    quantity: Optional[int] = None
    strategy_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化後驗證"""
        if not 0 <= self.confidence <= 1:
            raise ValueError("信心度必須在 0-1 之間")
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("數量必須大於 0")


@dataclass
class ExecutionOrder:
    """執行訂單數據模型
    
    此模型定義了從訊號轉換後的執行訂單格式。
    
    Attributes:
        order_id: 訂單唯一識別碼
        symbol: 股票代碼
        action: 交易動作
        quantity: 交易數量
        order_type: 訂單類型
        price: 價格
        stop_price: 停損價格
        execution_mode: 執行模式
        created_at: 創建時間
        signal_id: 原始訊號ID
        strategy_name: 策略名稱
        risk_params: 風險參數
    """
    order_id: str
    symbol: str
    action: str
    quantity: int
    order_type: str = "market"
    price: Optional[float] = None
    stop_price: Optional[float] = None
    execution_mode: ExecutionMode = ExecutionMode.IMMEDIATE
    created_at: datetime = field(default_factory=datetime.now)
    signal_id: Optional[str] = None
    strategy_name: Optional[str] = None
    risk_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """執行結果數據模型
    
    此模型記錄訂單執行的結果和統計資訊。
    
    Attributes:
        execution_id: 執行唯一識別碼
        order_id: 關聯的訂單ID
        status: 執行狀態
        filled_quantity: 已成交數量
        filled_price: 成交價格
        execution_time: 執行時間
        commission: 手續費
        slippage: 滑點
        market_impact: 市場衝擊
        error_message: 錯誤訊息
    """
    execution_id: str
    order_id: str
    status: ExecutionStatus
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    execution_time: Optional[datetime] = None
    commission: float = 0.0
    slippage: float = 0.0
    market_impact: float = 0.0
    error_message: Optional[str] = None


@dataclass
class SlippageAnalysis:
    """滑點分析數據模型
    
    此模型用於分析執行品質和滑點情況。
    
    Attributes:
        symbol: 股票代碼
        expected_price: 預期價格
        actual_price: 實際成交價格
        slippage_bps: 滑點 (基點)
        market_impact_bps: 市場衝擊 (基點)
        execution_time_ms: 執行時間 (毫秒)
        volume_ratio: 成交量比例
        analysis_time: 分析時間
    """
    symbol: str
    expected_price: float
    actual_price: float
    slippage_bps: float
    market_impact_bps: float
    execution_time_ms: float
    volume_ratio: float
    analysis_time: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionConfig:
    """執行配置數據模型
    
    此模型定義了執行引擎的配置參數。
    
    Attributes:
        max_position_size: 最大部位大小
        risk_limit: 風險限制
        execution_timeout: 執行超時時間 (秒)
        slippage_tolerance: 滑點容忍度
        batch_size: 分批執行大小
        twap_duration: TWAP 執行時間 (分鐘)
        enable_optimization: 是否啟用執行優化
        dry_run: 是否為模擬模式
    """
    max_position_size: float = 1000000.0
    risk_limit: float = 0.02
    execution_timeout: int = 300
    slippage_tolerance: float = 0.001
    batch_size: int = 1000
    twap_duration: int = 30
    enable_optimization: bool = True
    dry_run: bool = False


# 類型別名
SignalData = Union[TradingSignal, Dict[str, Any]]
OrderData = Union[ExecutionOrder, Dict[str, Any]]
