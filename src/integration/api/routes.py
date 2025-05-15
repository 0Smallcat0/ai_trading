"""
API路由

此模組定義了API路由。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordRequestForm

from src.core.logger import logger
from src.core.signal_gen import generate_signals
from src.execution.broker_base import OrderStatus
from src.execution.order_manager import OrderManager
from src.execution.signal_executor import SignalExecutor
from src.integration.workflows import workflow_manager

from .auth import authenticate, create_access_token, get_current_user
from .models import (
    BacktestRequestModel,
    BacktestResponseModel,
    MarketDataRequestModel,
    MarketDataResponseModel,
    PortfolioModel,
    SignalGenerationRequestModel,
    SignalGenerationResponseModel,
    StrategyModel,
    SystemStatusModel,
    TokenModel,
    TradeRequestModel,
    TradeResponseModel,
    UserModel,
    WorkflowRequestModel,
    WorkflowResponseModel,
)

# 創建認證路由
auth_router = APIRouter()


@auth_router.post("/token", response_model=TokenModel)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    獲取訪問令牌

    Args:
        form_data: 表單數據

    Returns:
        TokenModel: 令牌模型
    """
    user = authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用戶名或密碼錯誤",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 創建訪問令牌
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": form_data.scopes},
        expires_delta=access_token_expires,
    )

    return TokenModel(
        access_token=access_token,
        token_type="bearer",
        expires_in=1800,  # 30分鐘
        scopes=form_data.scopes,
    )


# 創建交易路由
trade_router = APIRouter()


@trade_router.post("/orders", response_model=TradeResponseModel)
async def create_order(
    trade_request: TradeRequestModel,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    創建訂單

    Args:
        trade_request: 交易請求
        current_user: 當前用戶

    Returns:
        TradeResponseModel: 交易響應
    """
    # 這裡應該調用交易系統的API來創建訂單
    # 為了示例，我們返回一個模擬的響應

    return TradeResponseModel(
        order_id="order-123456",
        symbol=trade_request.symbol,
        order_type=trade_request.order_type,
        side=trade_request.side,
        quantity=trade_request.quantity,
        price=trade_request.price,
        stop_price=trade_request.stop_price,
        status="pending",
        filled_quantity=0,
        created_at=datetime.now(),
        strategy_id=trade_request.strategy_id,
        tags=trade_request.tags,
    )


@trade_router.get("/orders/{order_id}", response_model=TradeResponseModel)
async def get_order(
    order_id: str, current_user: UserModel = Security(get_current_user, scopes=["read"])
):
    """
    獲取訂單

    Args:
        order_id: 訂單ID
        current_user: 當前用戶

    Returns:
        TradeResponseModel: 交易響應
    """
    # 這裡應該調用交易系統的API來獲取訂單
    # 為了示例，我們返回一個模擬的響應

    return TradeResponseModel(
        order_id=order_id,
        symbol="AAPL",
        order_type="market",
        side="buy",
        quantity=100,
        price=150.0,
        status="filled",
        filled_quantity=100,
        average_price=150.0,
        commission=1.5,
        created_at=datetime.now() - timedelta(hours=1),
        updated_at=datetime.now(),
        strategy_id="strategy-123",
        tags=["momentum", "tech"],
    )


@trade_router.get("/orders", response_model=List[TradeResponseModel])
async def list_orders(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    strategy_id: Optional[str] = None,
    current_user: UserModel = Security(get_current_user, scopes=["read"]),
):
    """
    列出訂單

    Args:
        status: 訂單狀態
        symbol: 股票代碼
        strategy_id: 策略ID
        current_user: 當前用戶

    Returns:
        List[TradeResponseModel]: 交易響應列表
    """
    # 這裡應該調用交易系統的API來列出訂單
    # 為了示例，我們返回一個模擬的響應

    return [
        TradeResponseModel(
            order_id="order-123456",
            symbol="AAPL",
            order_type="market",
            side="buy",
            quantity=100,
            price=150.0,
            status="filled",
            filled_quantity=100,
            average_price=150.0,
            commission=1.5,
            created_at=datetime.now() - timedelta(hours=1),
            updated_at=datetime.now(),
            strategy_id="strategy-123",
            tags=["momentum", "tech"],
        ),
        TradeResponseModel(
            order_id="order-123457",
            symbol="MSFT",
            order_type="limit",
            side="sell",
            quantity=50,
            price=300.0,
            status="pending",
            filled_quantity=0,
            created_at=datetime.now() - timedelta(minutes=30),
            strategy_id="strategy-123",
            tags=["momentum", "tech"],
        ),
    ]


@trade_router.delete("/orders/{order_id}", response_model=Dict[str, Any])
async def cancel_order(
    order_id: str,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    取消訂單

    Args:
        order_id: 訂單ID
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 取消結果
    """
    # 這裡應該調用交易系統的API來取消訂單
    # 為了示例，我們返回一個模擬的響應

    return {"order_id": order_id, "status": "cancelled", "message": "訂單已取消"}


# 創建投資組合路由
portfolio_router = APIRouter()


@portfolio_router.get("", response_model=List[PortfolioModel])
async def list_portfolios(
    current_user: UserModel = Security(get_current_user, scopes=["read"])
):
    """
    列出投資組合

    Args:
        current_user: 當前用戶

    Returns:
        List[PortfolioModel]: 投資組合列表
    """
    # 這裡應該調用交易系統的API來列出投資組合
    # 為了示例，我們返回一個模擬的響應

    return [
        PortfolioModel(
            portfolio_id="portfolio-123",
            name="主要投資組合",
            cash=10000.0,
            equity=50000.0,
            total_value=60000.0,
            day_pl=500.0,
            day_pl_percent=0.01,
            total_pl=5000.0,
            total_pl_percent=0.1,
            positions=[],
            created_at=datetime.now() - timedelta(days=30),
            updated_at=datetime.now(),
        )
    ]


@portfolio_router.get("/{portfolio_id}", response_model=PortfolioModel)
async def get_portfolio(
    portfolio_id: str,
    current_user: UserModel = Security(get_current_user, scopes=["read"]),
):
    """
    獲取投資組合

    Args:
        portfolio_id: 投資組合ID
        current_user: 當前用戶

    Returns:
        PortfolioModel: 投資組合
    """
    # 這裡應該調用交易系統的API來獲取投資組合
    # 為了示例，我們返回一個模擬的響應

    return PortfolioModel(
        portfolio_id=portfolio_id,
        name="主要投資組合",
        cash=10000.0,
        equity=50000.0,
        total_value=60000.0,
        day_pl=500.0,
        day_pl_percent=0.01,
        total_pl=5000.0,
        total_pl_percent=0.1,
        positions=[],
        created_at=datetime.now() - timedelta(days=30),
        updated_at=datetime.now(),
    )


# 創建策略路由
strategy_router = APIRouter()


@strategy_router.get("", response_model=List[StrategyModel])
async def list_strategies(
    status: Optional[str] = None,
    type: Optional[str] = None,
    current_user: UserModel = Security(get_current_user, scopes=["read"]),
):
    """
    列出策略

    Args:
        status: 策略狀態
        type: 策略類型
        current_user: 當前用戶

    Returns:
        List[StrategyModel]: 策略列表
    """
    # 這裡應該調用交易系統的API來列出策略
    # 為了示例，我們返回一個模擬的響應

    return [
        StrategyModel(
            strategy_id="strategy-123",
            name="動量策略",
            description="基於價格動量的交易策略",
            type="momentum",
            status="active",
            parameters={"lookback_period": 20, "threshold": 0.05},
            symbols=["AAPL", "MSFT", "GOOG"],
            created_at=datetime.now() - timedelta(days=10),
            updated_at=datetime.now(),
            performance={
                "total_return": 0.15,
                "sharpe_ratio": 1.2,
                "max_drawdown": 0.05,
            },
        )
    ]


@strategy_router.get("/{strategy_id}", response_model=StrategyModel)
async def get_strategy(
    strategy_id: str,
    current_user: UserModel = Security(get_current_user, scopes=["read"]),
):
    """
    獲取策略

    Args:
        strategy_id: 策略ID
        current_user: 當前用戶

    Returns:
        StrategyModel: 策略
    """
    # 這裡應該調用交易系統的API來獲取策略
    # 為了示例，我們返回一個模擬的響應

    return StrategyModel(
        strategy_id=strategy_id,
        name="動量策略",
        description="基於價格動量的交易策略",
        type="momentum",
        status="active",
        parameters={"lookback_period": 20, "threshold": 0.05},
        symbols=["AAPL", "MSFT", "GOOG"],
        created_at=datetime.now() - timedelta(days=10),
        updated_at=datetime.now(),
        performance={"total_return": 0.15, "sharpe_ratio": 1.2, "max_drawdown": 0.05},
    )


@strategy_router.post("/{strategy_id}/start", response_model=Dict[str, Any])
async def start_strategy(
    strategy_id: str,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    啟動策略

    Args:
        strategy_id: 策略ID
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 啟動結果
    """
    # 這裡應該調用交易系統的API來啟動策略
    # 為了示例，我們返回一個模擬的響應

    return {"strategy_id": strategy_id, "status": "active", "message": "策略已啟動"}


@strategy_router.post("/{strategy_id}/stop", response_model=Dict[str, Any])
async def stop_strategy(
    strategy_id: str,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    停止策略

    Args:
        strategy_id: 策略ID
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 停止結果
    """
    # 這裡應該調用交易系統的API來停止策略
    # 為了示例，我們返回一個模擬的響應

    return {"strategy_id": strategy_id, "status": "stopped", "message": "策略已停止"}


# 創建回測路由
backtest_router = APIRouter()


@backtest_router.post("", response_model=BacktestResponseModel)
async def create_backtest(
    backtest_request: BacktestRequestModel,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    創建回測

    Args:
        backtest_request: 回測請求
        background_tasks: 背景任務
        current_user: 當前用戶

    Returns:
        BacktestResponseModel: 回測響應
    """
    # 這裡應該調用交易系統的API來創建回測
    # 為了示例，我們返回一個模擬的響應

    # 添加背景任務來運行回測
    background_tasks.add_task(run_backtest, "backtest-123")

    return BacktestResponseModel(
        backtest_id="backtest-123",
        strategy_id=backtest_request.strategy_id,
        start_date=backtest_request.start_date,
        end_date=backtest_request.end_date,
        initial_capital=backtest_request.initial_capital,
        final_capital=0.0,  # 尚未完成
        total_return=0.0,  # 尚未完成
        annual_return=0.0,  # 尚未完成
        sharpe_ratio=0.0,  # 尚未完成
        max_drawdown=0.0,  # 尚未完成
        trades=0,  # 尚未完成
        win_rate=0.0,  # 尚未完成
        profit_factor=0.0,  # 尚未完成
        created_at=datetime.now(),
        status="running",
    )


@backtest_router.get("/{backtest_id}", response_model=BacktestResponseModel)
async def get_backtest(
    backtest_id: str,
    current_user: UserModel = Security(get_current_user, scopes=["read"]),
):
    """
    獲取回測

    Args:
        backtest_id: 回測ID
        current_user: 當前用戶

    Returns:
        BacktestResponseModel: 回測響應
    """
    # 這裡應該調用交易系統的API來獲取回測
    # 為了示例，我們返回一個模擬的響應

    return BacktestResponseModel(
        backtest_id=backtest_id,
        strategy_id="strategy-123",
        start_date=datetime(2020, 1, 1),
        end_date=datetime(2020, 12, 31),
        initial_capital=100000.0,
        final_capital=120000.0,
        total_return=0.2,
        annual_return=0.2,
        sharpe_ratio=1.5,
        max_drawdown=0.1,
        trades=100,
        win_rate=0.6,
        profit_factor=2.0,
        created_at=datetime.now() - timedelta(days=1),
        status="completed",
        results_url="/api/backtest/backtest-123/results",
    )


# 創建市場數據路由
market_data_router = APIRouter()


@market_data_router.post("", response_model=List[MarketDataResponseModel])
async def get_market_data(
    market_data_request: MarketDataRequestModel,
    current_user: UserModel = Security(get_current_user, scopes=["read"]),
):
    """
    獲取市場數據

    Args:
        market_data_request: 市場數據請求
        current_user: 當前用戶

    Returns:
        List[MarketDataResponseModel]: 市場數據響應列表
    """
    # 這裡應該調用交易系統的API來獲取市場數據
    # 為了示例，我們返回一個模擬的響應

    responses = []
    for symbol in market_data_request.symbols:
        responses.append(
            MarketDataResponseModel(
                symbol=symbol,
                interval=market_data_request.interval,
                data=[
                    {
                        "timestamp": datetime(2020, 1, 1),
                        "open": 100.0,
                        "high": 105.0,
                        "low": 99.0,
                        "close": 103.0,
                        "volume": 1000000,
                    },
                    {
                        "timestamp": datetime(2020, 1, 2),
                        "open": 103.0,
                        "high": 108.0,
                        "low": 102.0,
                        "close": 107.0,
                        "volume": 1200000,
                    },
                ],
            )
        )

    return responses


# 創建系統路由
system_router = APIRouter()


@system_router.get("/status", response_model=SystemStatusModel)
async def get_system_status(
    current_user: UserModel = Security(get_current_user, scopes=["read"])
):
    """
    獲取系統狀態

    Args:
        current_user: 當前用戶

    Returns:
        SystemStatusModel: 系統狀態
    """
    # 這裡應該調用交易系統的API來獲取系統狀態
    # 為了示例，我們返回一個模擬的響應

    return SystemStatusModel(
        status="running",
        version="1.0.0",
        uptime=86400,  # 1天
        cpu_usage=30.0,
        memory_usage=40.0,
        disk_usage=50.0,
        active_strategies=5,
        pending_orders=2,
        last_update=datetime.now(),
    )


# 創建工作流路由
workflow_router = APIRouter()


@workflow_router.get("", response_model=List[WorkflowResponseModel])
async def list_workflows(
    current_user: UserModel = Security(get_current_user, scopes=["read"])
):
    """
    列出工作流

    Args:
        current_user: 當前用戶

    Returns:
        List[WorkflowResponseModel]: 工作流列表
    """
    # 獲取所有工作流
    workflows = workflow_manager.get_workflows()

    # 轉換為響應模型
    response = []
    for workflow in workflows:
        # 獲取執行列表
        executions = workflow_manager.get_executions(workflow["id"])

        # 計算執行統計
        execution_count = len(executions)
        success_count = sum(1 for e in executions if e["status"] == "success")
        error_count = sum(1 for e in executions if e["status"] == "error")

        # 獲取最後執行時間
        last_execution = None
        if executions:
            last_execution = max(e["startedAt"] for e in executions if "startedAt" in e)

        response.append(
            WorkflowResponseModel(
                workflow_id=workflow["id"],
                name=workflow["name"],
                active=workflow.get("active", False),
                created_at=workflow.get("createdAt", datetime.now()),
                updated_at=workflow.get("updatedAt"),
                last_execution=last_execution,
                execution_count=execution_count,
                success_count=success_count,
                error_count=error_count,
            )
        )

    return response


@workflow_router.post("", response_model=WorkflowResponseModel)
async def create_workflow(
    workflow_request: WorkflowRequestModel,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    創建工作流

    Args:
        workflow_request: 工作流請求
        current_user: 當前用戶

    Returns:
        WorkflowResponseModel: 工作流響應
    """
    # 檢查是否使用模板
    if workflow_request.template:
        # 從模板創建工作流
        workflow = workflow_manager.create_workflow_from_template(
            workflow_request.template, workflow_request.name
        )
    else:
        # 創建空工作流
        workflow = workflow_manager.create_workflow(
            {
                "name": workflow_request.name,
                "nodes": [],
                "connections": {},
                "active": workflow_request.active,
                "settings": {
                    "saveManualExecutions": True,
                    "callerPolicy": "workflowsFromSameOwner",
                },
                "tags": [],
            }
        )

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="創建工作流失敗"
        )

    # 如果需要激活工作流
    if workflow_request.active and not workflow.get("active", False):
        workflow_manager.activate_workflow(workflow["id"])

    # 轉換為響應模型
    return WorkflowResponseModel(
        workflow_id=workflow["id"],
        name=workflow["name"],
        active=workflow.get("active", False),
        created_at=workflow.get("createdAt", datetime.now()),
        updated_at=workflow.get("updatedAt"),
        execution_count=0,
        success_count=0,
        error_count=0,
    )


@workflow_router.get("/{workflow_id}", response_model=WorkflowResponseModel)
async def get_workflow(
    workflow_id: str,
    current_user: UserModel = Security(get_current_user, scopes=["read"]),
):
    """
    獲取工作流

    Args:
        workflow_id: 工作流ID
        current_user: 當前用戶

    Returns:
        WorkflowResponseModel: 工作流響應
    """
    # 獲取工作流
    workflow = workflow_manager.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"工作流 {workflow_id} 不存在"
        )

    # 獲取執行列表
    executions = workflow_manager.get_executions(workflow_id)

    # 計算執行統計
    execution_count = len(executions)
    success_count = sum(1 for e in executions if e["status"] == "success")
    error_count = sum(1 for e in executions if e["status"] == "error")

    # 獲取最後執行時間
    last_execution = None
    if executions:
        last_execution = max(e["startedAt"] for e in executions if "startedAt" in e)

    # 轉換為響應模型
    return WorkflowResponseModel(
        workflow_id=workflow["id"],
        name=workflow["name"],
        active=workflow.get("active", False),
        created_at=workflow.get("createdAt", datetime.now()),
        updated_at=workflow.get("updatedAt"),
        last_execution=last_execution,
        execution_count=execution_count,
        success_count=success_count,
        error_count=error_count,
    )


@workflow_router.delete("/{workflow_id}", response_model=Dict[str, Any])
async def delete_workflow(
    workflow_id: str,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    刪除工作流

    Args:
        workflow_id: 工作流ID
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 刪除結果
    """
    # 獲取工作流
    workflow = workflow_manager.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"工作流 {workflow_id} 不存在"
        )

    # 刪除工作流
    success = workflow_manager.delete_workflow(workflow_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除工作流 {workflow_id} 失敗",
        )

    return {
        "workflow_id": workflow_id,
        "success": True,
        "message": f"工作流 {workflow_id} 已刪除",
    }


@workflow_router.post("/{workflow_id}/activate", response_model=Dict[str, Any])
async def activate_workflow(
    workflow_id: str,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    激活工作流

    Args:
        workflow_id: 工作流ID
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 激活結果
    """
    # 獲取工作流
    workflow = workflow_manager.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"工作流 {workflow_id} 不存在"
        )

    # 激活工作流
    success = workflow_manager.activate_workflow(workflow_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"激活工作流 {workflow_id} 失敗",
        )

    return {
        "workflow_id": workflow_id,
        "success": True,
        "message": f"工作流 {workflow_id} 已激活",
    }


@workflow_router.post("/{workflow_id}/deactivate", response_model=Dict[str, Any])
async def deactivate_workflow(
    workflow_id: str,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    停用工作流

    Args:
        workflow_id: 工作流ID
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 停用結果
    """
    # 獲取工作流
    workflow = workflow_manager.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"工作流 {workflow_id} 不存在"
        )

    # 停用工作流
    success = workflow_manager.deactivate_workflow(workflow_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停用工作流 {workflow_id} 失敗",
        )

    return {
        "workflow_id": workflow_id,
        "success": True,
        "message": f"工作流 {workflow_id} 已停用",
    }


@workflow_router.post(
    "/{workflow_id}/execute", response_model=WorkflowExecutionResponseModel
)
async def execute_workflow(
    workflow_id: str,
    execution_request: Optional[WorkflowExecutionRequestModel] = None,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    執行工作流

    Args:
        workflow_id: 工作流ID
        execution_request: 執行請求
        current_user: 當前用戶

    Returns:
        WorkflowExecutionResponseModel: 執行響應
    """
    # 獲取工作流
    workflow = workflow_manager.get_workflow(workflow_id)

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"工作流 {workflow_id} 不存在"
        )

    # 執行工作流
    execution = workflow_manager.execute_workflow(
        workflow_id, execution_request.data if execution_request else {}
    )

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"執行工作流 {workflow_id} 失敗",
        )

    # 轉換為響應模型
    return WorkflowExecutionResponseModel(
        execution_id=execution["id"],
        workflow_id=workflow_id,
        status=execution.get("status", "unknown"),
        started_at=execution.get("startedAt", datetime.now()),
        finished_at=execution.get("finishedAt"),
        data=execution.get("data", {}),
    )


# 創建訊號生成路由
signal_router = APIRouter()

# 創建全局的 SignalExecutor 實例
_signal_executor = None


def get_signal_executor():
    """獲取 SignalExecutor 實例"""
    global _signal_executor
    if _signal_executor is None:
        # 創建 OrderManager
        from src.core.executor import SimulatedBrokerAPI

        broker = SimulatedBrokerAPI()
        order_manager = OrderManager(broker)

        # 創建 SignalExecutor
        _signal_executor = SignalExecutor(order_manager)

        # 啟動 SignalExecutor
        _signal_executor.start()

    return _signal_executor


@signal_router.post("/generate", response_model=SignalGenerationResponseModel)
async def generate_trading_signals(
    signal_request: SignalGenerationRequestModel,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    生成交易訊號

    Args:
        signal_request: 訊號生成請求
        current_user: 當前用戶

    Returns:
        SignalGenerationResponseModel: 訊號生成響應
    """
    try:
        # 獲取策略參數
        strategy_id = signal_request.strategy_id
        symbols = signal_request.symbols
        parameters = signal_request.parameters

        # 生成訊號
        signals = generate_signals(
            strategy_id=strategy_id,
            symbols=symbols,
            parameters=parameters,
            start_date=signal_request.start_date,
            end_date=signal_request.end_date,
        )

        # 轉換為列表格式
        signal_list = []
        for symbol, signal_df in signals.items():
            # 將DataFrame轉換為字典列表
            signal_dict = signal_df.reset_index().to_dict(orient="records")

            # 添加到訊號列表
            for record in signal_dict:
                signal_list.append(
                    {
                        "symbol": symbol,
                        "date": record.get("date", datetime.now()),
                        "buy_signal": bool(record.get("buy_signal", 0)),
                        "sell_signal": bool(record.get("sell_signal", 0)),
                        "close_price": float(record.get("close", 0)),
                        "indicators": {
                            k: v
                            for k, v in record.items()
                            if k not in ["date", "buy_signal", "sell_signal", "close"]
                        },
                    }
                )

        # 返回響應
        return SignalGenerationResponseModel(
            strategy_id=strategy_id,
            signals=signal_list,
            generated_at=datetime.now(),
            parameters=parameters,
        )
    except Exception as e:
        logger.error(f"生成交易訊號時發生錯誤: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成交易訊號失敗: {str(e)}",
        )


@signal_router.post("/execute", response_model=Dict[str, Any])
async def execute_trading_signals(
    signal_request: SignalGenerationRequestModel,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    執行交易訊號

    Args:
        signal_request: 訊號生成請求
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 執行結果
    """
    try:
        # 獲取策略參數
        strategy_id = signal_request.strategy_id
        symbols = signal_request.symbols
        parameters = signal_request.parameters

        # 生成訊號
        signals = generate_signals(
            strategy_id=strategy_id,
            symbols=symbols,
            parameters=parameters,
            start_date=signal_request.start_date,
            end_date=signal_request.end_date,
        )

        # 使用 SignalExecutor 執行訊號
        signal_executor = get_signal_executor()
        order_ids = signal_executor.execute_signals(signals, strategy_id)

        return {
            "strategy_id": strategy_id,
            "success": True,
            "order_ids": order_ids,
            "message": f"已執行 {len(order_ids)} 個訂單",
        }
    except Exception as e:
        logger.error(f"執行交易訊號時發生錯誤: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"執行交易訊號失敗: {str(e)}",
        )


@signal_router.get("/orders", response_model=List[Dict[str, Any]])
async def get_signal_orders(
    status: Optional[str] = None,
    current_user: UserModel = Security(get_current_user, scopes=["read"]),
):
    """
    獲取訊號執行產生的訂單

    Args:
        status: 訂單狀態
        current_user: 當前用戶

    Returns:
        List[Dict[str, Any]]: 訂單列表
    """
    try:
        # 獲取 SignalExecutor
        signal_executor = get_signal_executor()

        # 獲取訂單
        order_status = OrderStatus(status) if status else None
        orders = signal_executor.order_manager.get_orders(order_status)

        # 轉換為字典列表
        order_dicts = [order.to_dict() for order in orders]

        return order_dicts
    except Exception as e:
        logger.error(f"獲取訊號訂單時發生錯誤: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取訊號訂單失敗: {str(e)}",
        )


@signal_router.delete("/orders/{order_id}", response_model=Dict[str, Any])
async def cancel_signal_order(
    order_id: str,
    current_user: UserModel = Security(get_current_user, scopes=["write"]),
):
    """
    取消訊號執行產生的訂單

    Args:
        order_id: 訂單ID
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 取消結果
    """
    try:
        # 獲取 SignalExecutor
        signal_executor = get_signal_executor()

        # 取消訂單
        success = signal_executor.order_manager.cancel_order(order_id)

        if success:
            return {
                "order_id": order_id,
                "success": True,
                "message": f"訂單 {order_id} 已取消",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"取消訂單 {order_id} 失敗",
            )
    except Exception as e:
        logger.error(f"取消訊號訂單時發生錯誤: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消訊號訂單失敗: {str(e)}",
        )


@signal_router.get("/account", response_model=Dict[str, Any])
async def get_signal_account_info(
    current_user: UserModel = Security(get_current_user, scopes=["read"]),
):
    """
    獲取訊號執行器的帳戶資訊

    Args:
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 帳戶資訊
    """
    try:
        # 獲取 SignalExecutor
        signal_executor = get_signal_executor()

        # 獲取帳戶資訊
        account_info = signal_executor._get_account_info()

        # 獲取持倉資訊
        positions = signal_executor._get_positions()

        # 組合返回資訊
        result = {
            "account": account_info,
            "positions": positions,
            "pending_orders": len(signal_executor.pending_orders),
        }

        return result
    except Exception as e:
        logger.error(f"獲取帳戶資訊時發生錯誤: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取帳戶資訊失敗: {str(e)}",
        )


# 背景任務
async def run_backtest(backtest_id: str):
    """
    運行回測

    Args:
        backtest_id: 回測ID
    """
    # 這裡應該調用交易系統的API來運行回測
    # 為了示例，我們只是記錄一條日誌

    logger.info(f"運行回測: {backtest_id}")

    # 模擬回測運行時間
    import asyncio

    await asyncio.sleep(10)

    logger.info(f"回測完成: {backtest_id}")
