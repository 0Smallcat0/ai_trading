"""
回測系統路由

此模組實現回測系統相關的 API 端點，包括回測任務管理、效能分析、
交易記錄查詢和報表匯出等功能。
"""

import io
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.backtest_service import BacktestService, BacktestConfig

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化回測服務
backtest_service = BacktestService()


# ==================== 請求模型 ====================


class BacktestCreateRequest(BaseModel):
    """回測創建請求模型"""

    strategy_id: str = Field(..., description="策略 ID")
    strategy_name: str = Field(..., description="策略名稱")
    symbols: List[str] = Field(..., min_items=1, description="股票代碼列表")
    start_date: datetime = Field(..., description="回測開始日期")
    end_date: datetime = Field(..., description="回測結束日期")
    initial_capital: float = Field(default=100000.0, gt=0, description="初始資金")
    commission: float = Field(default=0.001425, ge=0, le=0.01, description="手續費率")
    slippage: float = Field(default=0.001, ge=0, le=0.01, description="滑點率")
    tax: float = Field(default=0.003, ge=0, le=0.01, description="證券交易稅")
    max_position_size: float = Field(
        default=0.2, gt=0, le=1.0, description="最大持倉比例"
    )
    stop_loss: float = Field(default=0.05, gt=0, le=1.0, description="停損比例")
    take_profit: float = Field(default=0.1, gt=0, le=1.0, description="停利比例")

    @validator("end_date")
    def validate_date_range(cls, v, values):  # pylint: disable=no-self-argument
        """驗證日期範圍"""
        if "start_date" in values and v <= values["start_date"]:
            raise ValueError("結束日期必須晚於開始日期")
        return v

    @validator("symbols")
    def validate_symbols(cls, v):  # pylint: disable=no-self-argument
        """驗證股票代碼"""
        if not v:
            raise ValueError("至少需要一個股票代碼")
        # 簡單的股票代碼格式驗證
        for symbol in v:
            if not symbol or len(symbol) < 2:
                raise ValueError(f"無效的股票代碼: {symbol}")
        return v


class BacktestConfigRequest(BaseModel):
    """回測配置請求模型"""

    commission: Optional[float] = Field(
        default=None, ge=0, le=0.01, description="手續費率"
    )
    slippage: Optional[float] = Field(default=None, ge=0, le=0.01, description="滑點率")
    tax: Optional[float] = Field(default=None, ge=0, le=0.01, description="證券交易稅")
    max_position_size: Optional[float] = Field(
        default=None, gt=0, le=1.0, description="最大持倉比例"
    )
    stop_loss: Optional[float] = Field(
        default=None, gt=0, le=1.0, description="停損比例"
    )
    take_profit: Optional[float] = Field(
        default=None, gt=0, le=1.0, description="停利比例"
    )


class ExportRequest(BaseModel):
    """報表匯出請求模型"""

    format: str = Field(..., description="匯出格式 (csv, excel, html)")
    include_charts: bool = Field(default=False, description="是否包含圖表")
    include_transactions: bool = Field(default=True, description="是否包含交易明細")

    @validator("format")
    def validate_format(cls, v):  # pylint: disable=no-self-argument
        """驗證匯出格式"""
        allowed_formats = ["csv", "excel", "html"]
        if v.lower() not in allowed_formats:
            raise ValueError(f'匯出格式必須是: {", ".join(allowed_formats)}')
        return v.lower()


# ==================== 響應模型 ====================


class BacktestInfo(BaseModel):
    """回測資訊模型"""

    id: str = Field(..., description="回測 ID")
    strategy_id: str = Field(..., description="策略 ID")
    strategy_name: str = Field(..., description="策略名稱")
    status: str = Field(..., description="回測狀態")
    progress: int = Field(..., description="進度百分比")
    message: str = Field(..., description="狀態訊息")
    symbols: List[str] = Field(..., description="股票代碼列表")
    start_date: datetime = Field(..., description="開始日期")
    end_date: datetime = Field(..., description="結束日期")
    initial_capital: float = Field(..., description="初始資金")
    created_at: datetime = Field(..., description="創建時間")
    started_at: Optional[datetime] = Field(default=None, description="開始時間")
    completed_at: Optional[datetime] = Field(default=None, description="完成時間")


class BacktestStatus(BaseModel):
    """回測狀態模型"""

    id: str = Field(..., description="回測 ID")
    status: str = Field(..., description="狀態")
    progress: int = Field(..., description="進度百分比")
    message: str = Field(..., description="狀態訊息")
    estimated_remaining_time: Optional[str] = Field(
        default=None, description="預估剩餘時間"
    )
    current_step: Optional[str] = Field(default=None, description="當前步驟")


class PerformanceMetrics(BaseModel):
    """效能指標模型"""

    total_return: float = Field(..., description="總回報率")
    annual_return: float = Field(..., description="年化回報率")
    sharpe_ratio: float = Field(..., description="夏普比率")
    max_drawdown: float = Field(..., description="最大回撤")
    win_rate: float = Field(..., description="勝率")
    profit_factor: float = Field(..., description="獲利因子")
    total_trades: int = Field(..., description="總交易次數")
    avg_trade_return: float = Field(..., description="平均交易回報")
    volatility: float = Field(..., description="波動率")
    calmar_ratio: float = Field(..., description="卡瑪比率")


class TransactionRecord(BaseModel):
    """交易記錄模型"""

    date: datetime = Field(..., description="交易日期")
    symbol: str = Field(..., description="股票代碼")
    action: str = Field(..., description="交易動作 (buy/sell)")
    quantity: int = Field(..., description="交易數量")
    price: float = Field(..., description="交易價格")
    amount: float = Field(..., description="交易金額")
    commission: float = Field(..., description="手續費")
    tax: float = Field(..., description="交易稅")
    net_amount: float = Field(..., description="淨交易金額")
    portfolio_value: float = Field(..., description="組合價值")
    cash_balance: float = Field(..., description="現金餘額")


class ChartData(BaseModel):
    """圖表數據模型"""

    dates: List[str] = Field(..., description="日期列表")
    portfolio_values: List[float] = Field(..., description="組合價值")
    benchmark_values: Optional[List[float]] = Field(default=None, description="基準值")
    drawdown: List[float] = Field(..., description="回撤")
    returns: List[float] = Field(..., description="回報率")


class BacktestResults(BaseModel):
    """回測結果模型"""

    id: str = Field(..., description="回測 ID")
    strategy_id: str = Field(..., description="策略 ID")
    strategy_name: str = Field(..., description="策略名稱")
    status: str = Field(..., description="狀態")
    symbols: List[str] = Field(..., description="股票代碼列表")
    start_date: datetime = Field(..., description="開始日期")
    end_date: datetime = Field(..., description="結束日期")
    initial_capital: float = Field(..., description="初始資金")
    final_capital: float = Field(..., description="最終資金")
    metrics: PerformanceMetrics = Field(..., description="效能指標")
    created_at: datetime = Field(..., description="創建時間")
    completed_at: datetime = Field(..., description="完成時間")


class StrategyOption(BaseModel):
    """策略選項模型"""

    id: str = Field(..., description="策略 ID")
    name: str = Field(..., description="策略名稱")
    type: str = Field(..., description="策略類型")
    description: str = Field(..., description="策略描述")
    enabled: bool = Field(..., description="是否啟用")


# ==================== API 端點實作 ====================


@router.post(
    "/start",
    response_model=APIResponse[BacktestInfo],
    responses=COMMON_RESPONSES,
    summary="啟動回測任務",
    description="創建並啟動新的回測任務",
)
async def start_backtest(request: BacktestCreateRequest):
    """啟動回測任務"""
    try:
        # 創建回測配置
        config = BacktestConfig(
            strategy_id=request.strategy_id,
            strategy_name=request.strategy_name,
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            commission=request.commission,
            slippage=request.slippage,
            tax=request.tax,
            max_position_size=request.max_position_size,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
        )

        # 啟動回測
        backtest_id = backtest_service.start_backtest(config)

        # 獲取回測資訊
        backtest_info = backtest_service.get_backtest_info(backtest_id)

        if not backtest_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="回測任務創建失敗",
            )

        # 轉換為響應模型
        response_data = BacktestInfo(
            id=backtest_info["id"],
            strategy_id=backtest_info["strategy_id"],
            strategy_name=backtest_info["strategy_name"],
            status=backtest_info["status"],
            progress=backtest_info["progress"],
            message=backtest_info["message"],
            symbols=backtest_info["symbols"],
            start_date=backtest_info["start_date"],
            end_date=backtest_info["end_date"],
            initial_capital=backtest_info["initial_capital"],
            created_at=backtest_info["created_at"],
            started_at=backtest_info.get("started_at"),
            completed_at=backtest_info.get("completed_at"),
        )

        return APIResponse(success=True, message="回測任務已啟動", data=response_data)

    except Exception as e:
        logger.error("啟動回測任務失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"啟動回測任務失敗: {str(e)}",
        ) from e


@router.get(
    "/{backtest_id}/status",
    response_model=APIResponse[BacktestStatus],
    responses=COMMON_RESPONSES,
    summary="查詢回測狀態",
    description="根據回測 ID 查詢回測任務的當前狀態",
)
async def get_backtest_status(backtest_id: str):
    """查詢回測狀態"""
    try:
        # 獲取回測狀態
        status_info = backtest_service.get_backtest_status(backtest_id)

        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="回測任務不存在"
            )

        # 計算預估剩餘時間
        estimated_time = None
        current_step = None

        if status_info["status"] == "running":
            progress = status_info["progress"]
            if progress > 0:
                # 簡單的時間估算
                estimated_minutes = max(1, int((100 - progress) * 0.3))
                estimated_time = f"{estimated_minutes} 分鐘"

            # 根據進度確定當前步驟
            if progress < 20:
                current_step = "載入市場資料"
            elif progress < 40:
                current_step = "初始化策略"
            elif progress < 60:
                current_step = "生成交易信號"
            elif progress < 80:
                current_step = "執行回測"
            else:
                current_step = "計算績效指標"

        response_data = BacktestStatus(
            id=backtest_id,
            status=status_info["status"],
            progress=status_info["progress"],
            message=status_info["message"],
            estimated_remaining_time=estimated_time,
            current_step=current_step,
        )

        return APIResponse(success=True, message="回測狀態獲取成功", data=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取回測狀態失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取回測狀態失敗: {str(e)}",
        ) from e


@router.get(
    "/{backtest_id}/results",
    response_model=APIResponse[BacktestResults],
    responses=COMMON_RESPONSES,
    summary="獲取回測結果",
    description="獲取已完成回測任務的詳細結果",
)
async def get_backtest_results(backtest_id: str):
    """獲取回測結果"""
    try:
        # 檢查回測是否存在
        backtest_info = backtest_service.get_backtest_info(backtest_id)
        if not backtest_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="回測任務不存在"
            )

        # 檢查回測是否已完成
        if backtest_info["status"] != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"回測任務尚未完成，當前狀態: {backtest_info['status']}",
            )

        # 獲取回測結果
        results = backtest_service.get_backtest_results(backtest_id)
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="回測結果不存在"
            )

        # 獲取效能指標
        metrics = backtest_service.get_performance_metrics(backtest_id)
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="效能指標不存在"
            )

        # 轉換為響應模型
        performance_metrics = PerformanceMetrics(
            total_return=metrics.get("total_return", 0.0),
            annual_return=metrics.get("annual_return", 0.0),
            sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
            max_drawdown=metrics.get("max_drawdown", 0.0),
            win_rate=metrics.get("win_rate", 0.0),
            profit_factor=metrics.get("profit_factor", 0.0),
            total_trades=metrics.get("total_trades", 0),
            avg_trade_return=metrics.get("avg_trade_return", 0.0),
            volatility=metrics.get("volatility", 0.0),
            calmar_ratio=metrics.get("calmar_ratio", 0.0),
        )

        response_data = BacktestResults(
            id=backtest_id,
            strategy_id=backtest_info["strategy_id"],
            strategy_name=backtest_info["strategy_name"],
            status=backtest_info["status"],
            symbols=backtest_info["symbols"],
            start_date=backtest_info["start_date"],
            end_date=backtest_info["end_date"],
            initial_capital=backtest_info["initial_capital"],
            final_capital=results.get(
                "final_capital", backtest_info["initial_capital"]
            ),
            metrics=performance_metrics,
            created_at=backtest_info["created_at"],
            completed_at=backtest_info.get("completed_at", datetime.now()),
        )

        return APIResponse(success=True, message="回測結果獲取成功", data=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取回測結果失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取回測結果失敗: {str(e)}",
        ) from e


@router.post(
    "/config",
    response_model=APIResponse[Dict[str, Any]],
    responses=COMMON_RESPONSES,
    summary="配置回測參數",
    description="設定回測的預設參數配置",
)
async def configure_backtest(config: BacktestConfigRequest):
    """配置回測參數"""
    try:
        # 這裡可以保存預設配置到資料庫或配置文件
        # 目前返回配置確認
        config_data = {
            "commission": config.commission,
            "slippage": config.slippage,
            "tax": config.tax,
            "max_position_size": config.max_position_size,
            "stop_loss": config.stop_loss,
            "take_profit": config.take_profit,
            "updated_at": datetime.now().isoformat(),
        }

        return APIResponse(success=True, message="回測參數配置成功", data=config_data)

    except Exception as e:
        logger.error("配置回測參數失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置回測參數失敗: {str(e)}",
        ) from e


@router.get(
    "/strategies",
    response_model=APIResponse[List[StrategyOption]],
    responses=COMMON_RESPONSES,
    summary="獲取可用策略列表",
    description="獲取可用於回測的策略列表",
)
async def get_available_strategies():
    """獲取可用策略列表"""
    try:
        # 獲取可用策略
        strategies = backtest_service.get_available_strategies()

        strategy_options = [
            StrategyOption(
                id=strategy["id"],
                name=strategy["name"],
                type=strategy.get("type", "unknown"),
                description=strategy.get("description", ""),
                enabled=strategy.get("enabled", True),
            )
            for strategy in strategies
        ]

        return APIResponse(
            success=True, message="策略列表獲取成功", data=strategy_options
        )

    except Exception as e:
        logger.error("獲取策略列表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取策略列表失敗: {str(e)}",
        ) from e


@router.delete(
    "/{backtest_id}",
    response_model=APIResponse[Dict[str, Any]],
    responses=COMMON_RESPONSES,
    summary="刪除回測任務",
    description="刪除指定的回測任務及其相關資料",
)
async def delete_backtest(backtest_id: str):
    """刪除回測任務"""
    try:
        # 檢查回測是否存在
        backtest_info = backtest_service.get_backtest_info(backtest_id)
        if not backtest_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="回測任務不存在"
            )

        # 檢查回測是否正在運行
        if backtest_info["status"] == "running":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無法刪除正在運行的回測任務，請先停止任務",
            )

        # 刪除回測
        success = backtest_service.delete_backtest(backtest_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="刪除回測任務失敗",
            )

        return APIResponse(
            success=True,
            message="回測任務已刪除",
            data={"backtest_id": backtest_id, "deleted_at": datetime.now().isoformat()},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("刪除回測任務失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除回測任務失敗: {str(e)}",
        ) from e


@router.get(
    "/{backtest_id}/metrics",
    response_model=APIResponse[PerformanceMetrics],
    responses=COMMON_RESPONSES,
    summary="獲取效能指標",
    description="獲取回測任務的詳細效能指標",
)
async def get_backtest_metrics(backtest_id: str):
    """獲取效能指標"""
    try:
        # 檢查回測是否存在
        backtest_info = backtest_service.get_backtest_info(backtest_id)
        if not backtest_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="回測任務不存在"
            )

        # 檢查回測是否已完成
        if backtest_info["status"] != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"回測任務尚未完成，當前狀態: {backtest_info['status']}",
            )

        # 獲取效能指標
        metrics = backtest_service.get_performance_metrics(backtest_id)
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="效能指標不存在"
            )

        performance_metrics = PerformanceMetrics(
            total_return=metrics.get("total_return", 0.0),
            annual_return=metrics.get("annual_return", 0.0),
            sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
            max_drawdown=metrics.get("max_drawdown", 0.0),
            win_rate=metrics.get("win_rate", 0.0),
            profit_factor=metrics.get("profit_factor", 0.0),
            total_trades=metrics.get("total_trades", 0),
            avg_trade_return=metrics.get("avg_trade_return", 0.0),
            volatility=metrics.get("volatility", 0.0),
            calmar_ratio=metrics.get("calmar_ratio", 0.0),
        )

        return APIResponse(
            success=True, message="效能指標獲取成功", data=performance_metrics
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取效能指標失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取效能指標失敗: {str(e)}",
        ) from e


@router.get(
    "/{backtest_id}/transactions",
    response_model=APIResponse[List[TransactionRecord]],
    responses=COMMON_RESPONSES,
    summary="獲取交易明細",
    description="獲取回測任務的詳細交易記錄",
)
async def get_backtest_transactions(
    backtest_id: str,
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=50, ge=1, le=200, description="每頁數量"),
    symbol: Optional[str] = Query(default=None, description="股票代碼篩選"),
    action: Optional[str] = Query(default=None, description="交易動作篩選 (buy/sell)"),
):
    """獲取交易明細"""
    try:
        # 檢查回測是否存在
        backtest_info = backtest_service.get_backtest_info(backtest_id)
        if not backtest_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="回測任務不存在"
            )

        # 檢查回測是否已完成
        if backtest_info["status"] != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"回測任務尚未完成，當前狀態: {backtest_info['status']}",
            )

        # 獲取交易記錄
        transactions = backtest_service.get_transaction_records(
            backtest_id, symbol=symbol, action=action
        )

        if not transactions:
            return APIResponse(success=True, message="無交易記錄", data=[])

        # 分頁處理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_transactions = transactions[start_idx:end_idx]

        # 轉換為響應模型
        transaction_records = [
            TransactionRecord(
                date=transaction["date"],
                symbol=transaction["symbol"],
                action=transaction["action"],
                quantity=transaction["quantity"],
                price=transaction["price"],
                amount=transaction["amount"],
                commission=transaction.get("commission", 0.0),
                tax=transaction.get("tax", 0.0),
                net_amount=transaction.get("net_amount", transaction["amount"]),
                portfolio_value=transaction.get("portfolio_value", 0.0),
                cash_balance=transaction.get("cash_balance", 0.0),
            )
            for transaction in paginated_transactions
        ]

        return APIResponse(
            success=True, message="交易明細獲取成功", data=transaction_records
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取交易明細失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取交易明細失敗: {str(e)}",
        ) from e


@router.get(
    "/{backtest_id}/charts",
    response_model=APIResponse[ChartData],
    responses=COMMON_RESPONSES,
    summary="獲取圖表數據",
    description="獲取回測任務的圖表數據，用於績效視覺化",
)
async def get_backtest_charts(backtest_id: str):
    """獲取圖表數據"""
    try:
        # 檢查回測是否存在
        backtest_info = backtest_service.get_backtest_info(backtest_id)
        if not backtest_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="回測任務不存在"
            )

        # 檢查回測是否已完成
        if backtest_info["status"] != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"回測任務尚未完成，當前狀態: {backtest_info['status']}",
            )

        # 獲取圖表數據
        chart_data = backtest_service.get_chart_data(backtest_id)
        if not chart_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="圖表數據不存在"
            )

        response_data = ChartData(
            dates=chart_data.get("dates", []),
            portfolio_values=chart_data.get("portfolio_values", []),
            benchmark_values=chart_data.get("benchmark_values"),
            drawdown=chart_data.get("drawdown", []),
            returns=chart_data.get("returns", []),
        )

        return APIResponse(success=True, message="圖表數據獲取成功", data=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取圖表數據失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取圖表數據失敗: {str(e)}",
        ) from e


@router.get(
    "/{backtest_id}/export",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "報表文件",
            "content": {
                "application/octet-stream": {},
                "text/csv": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
                "text/html": {},
            },
        }
    },
    summary="匯出回測報表",
    description="匯出回測結果為指定格式的報表文件",
)
async def export_backtest_report(
    backtest_id: str,
    export_format: str = Query(
        ..., alias="format", description="匯出格式 (csv, excel, html)"
    ),
    include_charts: bool = Query(default=False, description="是否包含圖表"),
    include_transactions: bool = Query(default=True, description="是否包含交易明細"),
):
    """匯出回測報表"""
    try:
        # 驗證格式
        allowed_formats = ["csv", "excel", "html"]
        if export_format.lower() not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支援的匯出格式: {export_format}，支援格式: {', '.join(allowed_formats)}",
            )

        # 檢查回測是否存在
        backtest_info = backtest_service.get_backtest_info(backtest_id)
        if not backtest_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="回測任務不存在"
            )

        # 檢查回測是否已完成
        if backtest_info["status"] != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"回測任務尚未完成，當前狀態: {backtest_info['status']}",
            )

        # 生成報表
        report_data = backtest_service.generate_report(
            backtest_id,
            format=export_format.lower(),
            include_charts=include_charts,
            include_transactions=include_transactions,
        )

        if not report_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="報表生成失敗"
            )

        # 設定檔案名稱和 MIME 類型
        filename = (
            f"backtest_report_{backtest_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        if export_format.lower() == "csv":
            filename += ".csv"
            media_type = "text/csv"
        elif export_format.lower() == "excel":
            filename += ".xlsx"
            media_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        elif export_format.lower() == "html":
            filename += ".html"
            media_type = "text/html"
        else:
            media_type = "application/octet-stream"

        return StreamingResponse(
            io.BytesIO(report_data),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(report_data)),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("匯出回測報表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"匯出回測報表失敗: {str(e)}",
        ) from e


@router.get(
    "/",
    response_model=APIResponse[List[BacktestInfo]],
    responses=COMMON_RESPONSES,
    summary="獲取回測列表",
    description="獲取所有回測任務的列表，支援篩選和分頁",
)
async def get_backtests(
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁數量"),
    backtest_status: Optional[str] = Query(
        default=None, alias="status", description="狀態篩選"
    ),
    strategy_id: Optional[str] = Query(default=None, description="策略 ID 篩選"),
):
    """獲取回測列表"""
    try:
        # 獲取回測列表
        backtests = backtest_service.get_backtest_list(
            status=backtest_status, strategy_id=strategy_id
        )

        # 分頁處理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_backtests = backtests[start_idx:end_idx]

        # 轉換為響應模型
        backtest_list = [
            BacktestInfo(
                id=backtest["id"],
                strategy_id=backtest["strategy_id"],
                strategy_name=backtest["strategy_name"],
                status=backtest["status"],
                progress=backtest.get("progress", 0),
                message=backtest.get("message", ""),
                symbols=backtest["symbols"],
                start_date=backtest["start_date"],
                end_date=backtest["end_date"],
                initial_capital=backtest["initial_capital"],
                created_at=backtest["created_at"],
                started_at=backtest.get("started_at"),
                completed_at=backtest.get("completed_at"),
            )
            for backtest in paginated_backtests
        ]

        return APIResponse(success=True, message="回測列表獲取成功", data=backtest_list)

    except Exception as e:
        logger.error("獲取回測列表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取回測列表失敗: {str(e)}",
        ) from e
