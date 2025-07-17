"""
策略執行引擎 API 路由

此模組提供策略執行引擎的 RESTful API 接口，包括：
- 執行策略訊號
- 查詢執行狀態
- 獲取執行統計
- 配置管理
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field, validator

from src.api.models.responses import APIResponse
from src.api.utils.security import get_current_user
from src.core.strategy_execution import (
    StrategyExecutionEngine,
    TradingSignal,
    ExecutionConfig,
    SignalType,
    ExecutionMode,
)

logger = logging.getLogger(__name__)

# 創建路由器
router = APIRouter(prefix="/strategy-execution", tags=["策略執行引擎"])

# 全局執行引擎實例
_execution_engine: Optional[StrategyExecutionEngine] = None


# ==================== 請求模型 ====================

class SignalRequest(BaseModel):
    """策略訊號請求模型"""
    symbol: str = Field(..., description="股票代碼")
    signal_type: str = Field(..., description="訊號類型 (buy/sell/hold)")
    confidence: float = Field(..., ge=0, le=1, description="信心度 (0-1)")
    price: Optional[float] = Field(None, description="建議價格")
    quantity: Optional[int] = Field(None, description="建議數量")
    strategy_name: Optional[str] = Field(None, description="策略名稱")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外資訊")
    
    @validator('signal_type')
    def validate_signal_type(cls, v):
        """驗證訊號類型"""
        valid_types = ["buy", "sell", "hold", "close_long", "close_short"]
        if v.lower() not in valid_types:
            raise ValueError(f"訊號類型必須是: {valid_types}")
        return v.lower()


class BatchSignalRequest(BaseModel):
    """批量訊號請求模型"""
    signals: List[SignalRequest] = Field(..., description="訊號列表")
    market_data: Optional[Dict[str, Any]] = Field(None, description="市場數據")


class ExecutionConfigRequest(BaseModel):
    """執行配置請求模型"""
    max_position_size: Optional[float] = Field(None, description="最大部位大小")
    risk_limit: Optional[float] = Field(None, description="風險限制")
    execution_timeout: Optional[int] = Field(None, description="執行超時時間")
    slippage_tolerance: Optional[float] = Field(None, description="滑點容忍度")
    batch_size: Optional[int] = Field(None, description="分批執行大小")
    twap_duration: Optional[int] = Field(None, description="TWAP執行時間")
    enable_optimization: Optional[bool] = Field(None, description="是否啟用優化")
    dry_run: Optional[bool] = Field(None, description="是否為模擬模式")


# ==================== 響應模型 ====================

class ExecutionResultResponse(BaseModel):
    """執行結果響應模型"""
    execution_id: str
    success: bool
    message: str
    timestamp: datetime
    data: Dict[str, Any]


class ExecutionStatusResponse(BaseModel):
    """執行狀態響應模型"""
    order_id: str
    status: str
    symbol: Optional[str] = None
    filled_quantity: Optional[int] = None
    filled_price: Optional[float] = None
    execution_time: Optional[datetime] = None
    slippage: Optional[float] = None
    commission: Optional[float] = None


class ExecutionStatsResponse(BaseModel):
    """執行統計響應模型"""
    engine_stats: Dict[str, Any]
    tracker_stats: Dict[str, Any]
    portfolio_utilization: float
    portfolio_value: float


# ==================== 輔助函數 ====================

def get_execution_engine() -> StrategyExecutionEngine:
    """獲取執行引擎實例"""
    global _execution_engine
    
    if _execution_engine is None:
        # 初始化執行引擎
        config = ExecutionConfig()
        _execution_engine = StrategyExecutionEngine(config=config)
        _execution_engine.start_monitoring()
        logger.info("策略執行引擎已初始化")
    
    return _execution_engine


def convert_signal_request_to_trading_signal(request: SignalRequest) -> TradingSignal:
    """將請求模型轉換為交易訊號"""
    return TradingSignal(
        symbol=request.symbol,
        signal_type=SignalType(request.signal_type),
        confidence=request.confidence,
        price=request.price,
        quantity=request.quantity,
        strategy_name=request.strategy_name,
        metadata=request.metadata,
    )


# ==================== API 端點 ====================

@router.post("/execute-signal", response_model=APIResponse[ExecutionResultResponse])
async def execute_strategy_signal(
    request: SignalRequest,
    market_data: Optional[Dict[str, Any]] = None,
    current_user: str = Depends(get_current_user),
):
    """執行策略訊號
    
    Args:
        request: 策略訊號請求
        market_data: 市場數據
        current_user: 當前用戶
        
    Returns:
        APIResponse[ExecutionResultResponse]: 執行結果
        
    Example:
        POST /api/strategy-execution/execute-signal
        {
            "symbol": "2330.TW",
            "signal_type": "buy",
            "confidence": 0.8,
            "price": 500.0,
            "quantity": 1000,
            "strategy_name": "MA_Cross"
        }
    """
    try:
        engine = get_execution_engine()
        
        # 轉換請求為交易訊號
        signal = convert_signal_request_to_trading_signal(request)
        
        # 執行訊號
        result = engine.execute_strategy_signal(signal, market_data)
        
        # 轉換結果
        response_data = ExecutionResultResponse(
            execution_id=result["execution_id"],
            success=result["success"],
            message=result["message"],
            timestamp=result["timestamp"],
            data=result.get("data", {}),
        )
        
        return APIResponse(
            success=True,
            message="訊號執行完成",
            data=response_data,
        )
        
    except Exception as e:
        logger.error("執行策略訊號時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"執行策略訊號失敗: {str(e)}",
        )


@router.post("/execute-signals-batch", response_model=APIResponse[List[ExecutionResultResponse]])
async def execute_signals_batch(
    request: BatchSignalRequest,
    current_user: str = Depends(get_current_user),
):
    """批量執行策略訊號
    
    Args:
        request: 批量訊號請求
        current_user: 當前用戶
        
    Returns:
        APIResponse[List[ExecutionResultResponse]]: 批量執行結果
    """
    try:
        engine = get_execution_engine()
        
        # 轉換請求為交易訊號列表
        signals = [
            convert_signal_request_to_trading_signal(signal_req)
            for signal_req in request.signals
        ]
        
        # 批量執行
        results = engine.execute_signals_batch(signals, request.market_data)
        
        # 轉換結果
        response_data = [
            ExecutionResultResponse(
                execution_id=result["execution_id"],
                success=result["success"],
                message=result["message"],
                timestamp=result["timestamp"],
                data=result.get("data", {}),
            )
            for result in results
        ]
        
        return APIResponse(
            success=True,
            message=f"批量執行完成，處理了 {len(signals)} 個訊號",
            data=response_data,
        )
        
    except Exception as e:
        logger.error("批量執行策略訊號時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量執行失敗: {str(e)}",
        )


@router.get("/status/{order_id}", response_model=APIResponse[ExecutionStatusResponse])
async def get_execution_status(
    order_id: str,
    current_user: str = Depends(get_current_user),
):
    """獲取執行狀態
    
    Args:
        order_id: 訂單ID
        current_user: 當前用戶
        
    Returns:
        APIResponse[ExecutionStatusResponse]: 執行狀態
    """
    try:
        engine = get_execution_engine()
        
        status_info = engine.get_execution_status(order_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到訂單: {order_id}",
            )
        
        response_data = ExecutionStatusResponse(
            order_id=order_id,
            status=status_info["status"],
            symbol=status_info.get("symbol"),
            filled_quantity=status_info.get("filled_quantity"),
            filled_price=status_info.get("filled_price"),
            execution_time=status_info.get("execution_time"),
            slippage=status_info.get("slippage"),
            commission=status_info.get("commission"),
        )
        
        return APIResponse(
            success=True,
            message="獲取執行狀態成功",
            data=response_data,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取執行狀態時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取執行狀態失敗: {str(e)}",
        )


@router.get("/statistics", response_model=APIResponse[ExecutionStatsResponse])
async def get_execution_statistics(
    current_user: str = Depends(get_current_user),
):
    """獲取執行統計
    
    Args:
        current_user: 當前用戶
        
    Returns:
        APIResponse[ExecutionStatsResponse]: 執行統計
    """
    try:
        engine = get_execution_engine()
        
        stats = engine.get_execution_statistics()
        
        response_data = ExecutionStatsResponse(
            engine_stats=stats["engine_stats"],
            tracker_stats=stats["tracker_stats"],
            portfolio_utilization=stats["portfolio_utilization"],
            portfolio_value=stats["portfolio_value"],
        )
        
        return APIResponse(
            success=True,
            message="獲取執行統計成功",
            data=response_data,
        )
        
    except Exception as e:
        logger.error("獲取執行統計時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取執行統計失敗: {str(e)}",
        )


@router.put("/config", response_model=APIResponse[Dict[str, str]])
async def update_execution_config(
    request: ExecutionConfigRequest,
    current_user: str = Depends(get_current_user),
):
    """更新執行配置
    
    Args:
        request: 執行配置請求
        current_user: 當前用戶
        
    Returns:
        APIResponse[Dict[str, str]]: 更新結果
    """
    try:
        engine = get_execution_engine()
        
        # 獲取當前配置
        current_config = engine.config
        
        # 更新配置
        config_dict = current_config.__dict__.copy()
        
        for field, value in request.dict(exclude_unset=True).items():
            if value is not None:
                config_dict[field] = value
        
        # 創建新配置
        new_config = ExecutionConfig(**config_dict)
        engine.update_config(new_config)
        
        return APIResponse(
            success=True,
            message="執行配置更新成功",
            data={"status": "updated"},
        )
        
    except Exception as e:
        logger.error("更新執行配置時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新執行配置失敗: {str(e)}",
        )


@router.get("/config", response_model=APIResponse[Dict[str, Any]])
async def get_execution_config(
    current_user: str = Depends(get_current_user),
):
    """獲取執行配置
    
    Args:
        current_user: 當前用戶
        
    Returns:
        APIResponse[Dict[str, Any]]: 當前配置
    """
    try:
        engine = get_execution_engine()
        
        config_dict = engine.config.__dict__.copy()
        
        return APIResponse(
            success=True,
            message="獲取執行配置成功",
            data=config_dict,
        )
        
    except Exception as e:
        logger.error("獲取執行配置時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取執行配置失敗: {str(e)}",
        )
