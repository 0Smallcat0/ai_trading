"""
投資組合管理路由

此模組實現投資組合管理相關的 API 端點，包括投資組合 CRUD 操作、
資產配置管理、績效計算、風險指標分析和投資組合優化等功能。
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, validator

from src.api.models.responses import (
    APIResponse,
    PaginatedResponse,
    PaginationMeta,
    COMMON_RESPONSES,
)
from src.core.portfolio_service import PortfolioService, Portfolio, PortfolioHolding

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化投資組合服務
portfolio_service = PortfolioService()


# ==================== 請求模型 ====================


class HoldingRequest(BaseModel):
    """持倉請求模型"""

    symbol: str = Field(..., description="股票代碼")
    name: str = Field(..., description="股票名稱")
    quantity: float = Field(..., gt=0, description="持倉數量")
    price: float = Field(..., gt=0, description="買入價格")
    sector: Optional[str] = Field(default="", description="行業分類")
    exchange: Optional[str] = Field(default="", description="交易所")

    @validator("symbol")
    def validate_symbol(cls, v):  # pylint: disable=no-self-argument
        """驗證股票代碼"""
        if not v or len(v.strip()) < 2:
            raise ValueError("股票代碼不能為空且長度至少為2")
        return v.strip().upper()


class PortfolioCreateRequest(BaseModel):
    """投資組合創建請求模型"""

    name: str = Field(..., min_length=1, max_length=100, description="投資組合名稱")
    description: str = Field(default="", max_length=500, description="投資組合描述")
    benchmark: str = Field(default="^TWII", description="基準指數")
    risk_free_rate: float = Field(default=0.02, ge=0, le=0.1, description="無風險利率")
    holdings: List[HoldingRequest] = Field(..., min_items=1, description="持倉列表")

    @validator("name")
    def validate_name(cls, v):  # pylint: disable=no-self-argument
        """驗證投資組合名稱"""
        if not v.strip():
            raise ValueError("投資組合名稱不能為空")
        return v.strip()

    @validator("holdings")
    def validate_holdings(cls, v):  # pylint: disable=no-self-argument
        """驗證持倉列表"""
        if not v:
            raise ValueError("至少需要一個持倉")

        # 檢查重複的股票代碼
        symbols = [h.symbol for h in v]
        if len(symbols) != len(set(symbols)):
            raise ValueError("持倉中不能有重複的股票代碼")

        return v


class PortfolioUpdateRequest(BaseModel):
    """投資組合更新請求模型"""

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="投資組合名稱"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, description="投資組合描述"
    )
    benchmark: Optional[str] = Field(default=None, description="基準指數")
    risk_free_rate: Optional[float] = Field(
        default=None, ge=0, le=0.1, description="無風險利率"
    )
    holdings: Optional[List[HoldingRequest]] = Field(
        default=None, description="持倉列表"
    )

    @validator("holdings")
    def validate_holdings(cls, v):  # pylint: disable=no-self-argument
        """驗證持倉列表"""
        if v is not None:
            if not v:
                raise ValueError("持倉列表不能為空")

            # 檢查重複的股票代碼
            symbols = [h.symbol for h in v]
            if len(symbols) != len(set(symbols)):
                raise ValueError("持倉中不能有重複的股票代碼")

        return v


class RebalanceRequest(BaseModel):
    """再平衡請求模型"""

    method: str = Field(default="equal_weight", description="再平衡方法")
    target_weights: Optional[Dict[str, float]] = Field(
        default=None, description="目標權重"
    )
    constraints: Optional[Dict[str, Any]] = Field(default=None, description="約束條件")

    @validator("method")
    def validate_method(cls, v):  # pylint: disable=no-self-argument
        """驗證再平衡方法"""
        allowed_methods = [
            "equal_weight",
            "mean_variance",
            "risk_parity",
            "max_sharpe",
            "min_variance",
            "custom",
        ]
        if v not in allowed_methods:
            raise ValueError(f'再平衡方法必須是: {", ".join(allowed_methods)}')
        return v

    @validator("target_weights")
    def validate_target_weights(
        cls, v, values
    ):  # pylint: disable=no-self-argument,unused-argument
        """驗證目標權重"""
        if v is not None:
            # 檢查權重總和
            total_weight = sum(v.values())
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError("目標權重總和必須等於1.0")

            # 檢查權重範圍
            for symbol, weight in v.items():
                if weight < 0 or weight > 1:
                    raise ValueError(f"權重必須在0-1之間: {symbol}={weight}")

        return v


# ==================== 響應模型 ====================


class HoldingResponse(BaseModel):
    """持倉響應模型"""

    symbol: str = Field(..., description="股票代碼")
    name: str = Field(..., description="股票名稱")
    quantity: float = Field(..., description="持倉數量")
    price: float = Field(..., description="買入價格")
    market_value: float = Field(..., description="市值")
    weight: float = Field(..., description="權重")
    sector: str = Field(..., description="行業分類")
    exchange: str = Field(..., description="交易所")


class PortfolioResponse(BaseModel):
    """投資組合響應模型"""

    id: str = Field(..., description="投資組合 ID")
    name: str = Field(..., description="投資組合名稱")
    description: str = Field(..., description="投資組合描述")
    created_at: str = Field(..., description="創建時間")
    updated_at: str = Field(..., description="更新時間")
    total_value: float = Field(..., description="總價值")
    benchmark: str = Field(..., description="基準指數")
    risk_free_rate: float = Field(..., description="無風險利率")
    holdings: List[HoldingResponse] = Field(..., description="持倉列表")


class PortfolioSummary(BaseModel):
    """投資組合摘要模型"""

    id: str = Field(..., description="投資組合 ID")
    name: str = Field(..., description="投資組合名稱")
    description: str = Field(..., description="投資組合描述")
    total_value: float = Field(..., description="總價值")
    holdings_count: int = Field(..., description="持倉數量")
    created_at: str = Field(..., description="創建時間")
    updated_at: str = Field(..., description="更新時間")


class PerformanceMetrics(BaseModel):
    """績效指標模型"""

    total_return: float = Field(..., description="總回報率")
    annual_return: float = Field(..., description="年化回報率")
    volatility: float = Field(..., description="波動率")
    sharpe_ratio: float = Field(..., description="夏普比率")
    max_drawdown: float = Field(..., description="最大回撤")
    calmar_ratio: float = Field(..., description="卡瑪比率")
    sortino_ratio: float = Field(..., description="索提諾比率")
    information_ratio: float = Field(..., description="資訊比率")
    beta: float = Field(..., description="Beta值")
    alpha: float = Field(..., description="Alpha值")
    tracking_error: float = Field(..., description="追蹤誤差")


class RiskMetrics(BaseModel):
    """風險指標模型"""

    var_95: float = Field(..., description="95% VaR")
    var_99: float = Field(..., description="99% VaR")
    cvar_95: float = Field(..., description="95% CVaR")
    cvar_99: float = Field(..., description="99% CVaR")
    volatility: float = Field(..., description="波動率")
    downside_deviation: float = Field(..., description="下行偏差")
    max_drawdown: float = Field(..., description="最大回撤")
    correlation_matrix: Dict[str, Dict[str, float]] = Field(
        ..., description="相關性矩陣"
    )
    concentration_risk: float = Field(..., description="集中度風險")


class RebalanceResult(BaseModel):
    """再平衡結果模型"""

    portfolio_id: str = Field(..., description="投資組合 ID")
    method: str = Field(..., description="再平衡方法")
    old_weights: Dict[str, float] = Field(..., description="舊權重")
    new_weights: Dict[str, float] = Field(..., description="新權重")
    weight_changes: Dict[str, float] = Field(..., description="權重變化")
    expected_return: float = Field(..., description="預期回報率")
    expected_risk: float = Field(..., description="預期風險")
    rebalance_cost: float = Field(..., description="再平衡成本")
    execution_time: str = Field(..., description="執行時間")


class OptimizationConstraints(BaseModel):
    """優化約束條件模型"""

    min_weight: float = Field(default=0.0, description="最小權重")
    max_weight: float = Field(default=1.0, description="最大權重")
    max_concentration: float = Field(default=0.4, description="最大集中度")
    sector_limits: Optional[Dict[str, float]] = Field(
        default=None, description="行業限制"
    )
    turnover_limit: Optional[float] = Field(default=None, description="換手率限制")


# ==================== 輔助函數 ====================


def _convert_portfolio_to_response(portfolio: Portfolio) -> PortfolioResponse:
    """將 Portfolio 對象轉換為響應模型"""
    holdings_response = [
        HoldingResponse(
            symbol=holding.symbol,
            name=holding.name,
            quantity=holding.quantity,
            price=holding.price,
            market_value=holding.market_value,
            weight=holding.weight,
            sector=holding.sector,
            exchange=holding.exchange,
        )
        for holding in portfolio.holdings
    ]

    return PortfolioResponse(
        id=portfolio.id,
        name=portfolio.name,
        description=portfolio.description,
        created_at=portfolio.created_at.isoformat(),
        updated_at=portfolio.updated_at.isoformat(),
        total_value=portfolio.total_value,
        benchmark=portfolio.benchmark,
        risk_free_rate=portfolio.risk_free_rate,
        holdings=holdings_response,
    )


def _convert_portfolio_to_summary(portfolio: Portfolio) -> PortfolioSummary:
    """將 Portfolio 對象轉換為摘要模型"""
    return PortfolioSummary(
        id=portfolio.id,
        name=portfolio.name,
        description=portfolio.description,
        total_value=portfolio.total_value,
        holdings_count=len(portfolio.holdings),
        created_at=portfolio.created_at.isoformat(),
        updated_at=portfolio.updated_at.isoformat(),
    )


# ==================== API 端點實作 ====================


@router.post(
    "/portfolios",
    response_model=APIResponse[PortfolioResponse],
    responses=COMMON_RESPONSES,
    summary="創建新投資組合",
    description="創建新的投資組合，包含持倉配置和基本設定",
)
async def create_portfolio(request: PortfolioCreateRequest):
    """創建新投資組合"""
    try:
        # 轉換持倉請求為持倉對象
        holdings = []
        total_value = 0.0

        for holding_req in request.holdings:
            market_value = holding_req.quantity * holding_req.price
            total_value += market_value

            holding = PortfolioHolding(
                symbol=holding_req.symbol,
                name=holding_req.name,
                quantity=holding_req.quantity,
                price=holding_req.price,
                market_value=market_value,
                weight=0.0,  # 稍後計算
                sector=holding_req.sector,
                exchange=holding_req.exchange,
            )
            holdings.append(holding)

        # 計算權重
        for holding in holdings:
            holding.weight = (
                holding.market_value / total_value if total_value > 0 else 0.0
            )

        # 創建投資組合對象
        portfolio_id = str(uuid.uuid4())
        now = datetime.now()

        portfolio = Portfolio(
            id=portfolio_id,
            name=request.name,
            description=request.description,
            created_at=now,
            updated_at=now,
            total_value=total_value,
            holdings=holdings,
            benchmark=request.benchmark,
            risk_free_rate=request.risk_free_rate,
        )

        # 保存投資組合
        saved_portfolio = portfolio_service.create_portfolio(portfolio)

        if not saved_portfolio:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="投資組合創建失敗",
            )

        # 轉換為響應模型
        response_data = _convert_portfolio_to_response(saved_portfolio)

        return APIResponse(success=True, message="投資組合創建成功", data=response_data)

    except ValueError as e:
        logger.error("投資組合創建參數錯誤: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"參數錯誤: {str(e)}"
        ) from e
    except Exception as e:
        logger.error("創建投資組合失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"創建投資組合失敗: {str(e)}",
        ) from e


@router.get(
    "/portfolios",
    response_model=PaginatedResponse[PortfolioSummary],
    responses=COMMON_RESPONSES,
    summary="查詢投資組合列表",
    description="獲取投資組合列表，支援分頁和篩選",
)
async def list_portfolios(
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁項目數"),
    search: Optional[str] = Query(default=None, description="搜尋關鍵字"),
    sort_by: str = Query(default="created_at", description="排序欄位"),
    sort_order: str = Query(
        default="desc", regex="^(asc|desc)$", description="排序順序"
    ),
):
    """查詢投資組合列表"""
    try:
        # 獲取投資組合列表
        portfolios, total_count = portfolio_service.list_portfolios(
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # 轉換為摘要模型
        portfolio_summaries = [
            _convert_portfolio_to_summary(portfolio) for portfolio in portfolios
        ]

        # 計算分頁資訊
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1

        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_count,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        )

        return PaginatedResponse(
            success=True,
            message="投資組合列表獲取成功",
            data=portfolio_summaries,
            pagination=pagination,
        )

    except Exception as e:
        logger.error("獲取投資組合列表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取投資組合列表失敗: {str(e)}",
        ) from e


@router.get(
    "/portfolios/{portfolio_id}",
    response_model=APIResponse[PortfolioResponse],
    responses=COMMON_RESPONSES,
    summary="查詢特定投資組合詳情",
    description="根據投資組合 ID 獲取詳細資訊",
)
async def get_portfolio(portfolio_id: str):
    """查詢特定投資組合詳情"""
    try:
        # 獲取投資組合
        portfolio = portfolio_service.get_portfolio(portfolio_id)

        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="投資組合不存在"
            )

        # 轉換為響應模型
        response_data = _convert_portfolio_to_response(portfolio)

        return APIResponse(
            success=True, message="投資組合詳情獲取成功", data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取投資組合詳情失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取投資組合詳情失敗: {str(e)}",
        ) from e


@router.put(
    "/portfolios/{portfolio_id}",
    response_model=APIResponse[PortfolioResponse],
    responses=COMMON_RESPONSES,
    summary="更新投資組合配置",
    description="更新投資組合的基本資訊和持倉配置",
)
async def update_portfolio(portfolio_id: str, request: PortfolioUpdateRequest):
    """更新投資組合配置"""
    try:
        # 檢查投資組合是否存在
        existing_portfolio = portfolio_service.get_portfolio(portfolio_id)
        if not existing_portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="投資組合不存在"
            )

        # 準備更新資料
        update_data = {}

        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.benchmark is not None:
            update_data["benchmark"] = request.benchmark
        if request.risk_free_rate is not None:
            update_data["risk_free_rate"] = request.risk_free_rate

        # 處理持倉更新
        if request.holdings is not None:
            holdings = []
            total_value = 0.0

            for holding_req in request.holdings:
                market_value = holding_req.quantity * holding_req.price
                total_value += market_value

                holding = PortfolioHolding(
                    symbol=holding_req.symbol,
                    name=holding_req.name,
                    quantity=holding_req.quantity,
                    price=holding_req.price,
                    market_value=market_value,
                    weight=0.0,  # 稍後計算
                    sector=holding_req.sector,
                    exchange=holding_req.exchange,
                )
                holdings.append(holding)

            # 計算權重
            for holding in holdings:
                holding.weight = (
                    holding.market_value / total_value if total_value > 0 else 0.0
                )

            update_data["holdings"] = holdings
            update_data["total_value"] = total_value

        # 更新投資組合
        updated_portfolio = portfolio_service.update_portfolio(
            portfolio_id, update_data
        )

        if not updated_portfolio:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="投資組合更新失敗",
            )

        # 轉換為響應模型
        response_data = _convert_portfolio_to_response(updated_portfolio)

        return APIResponse(success=True, message="投資組合更新成功", data=response_data)

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"投資組合更新參數錯誤: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"參數錯誤: {str(e)}"
        )
    except Exception as e:
        logger.error(f"更新投資組合失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新投資組合失敗: {str(e)}",
        )


@router.delete(
    "/portfolios/{portfolio_id}",
    response_model=APIResponse[Dict[str, Any]],
    responses=COMMON_RESPONSES,
    summary="刪除投資組合",
    description="刪除指定的投資組合及其相關資料",
)
async def delete_portfolio(portfolio_id: str):
    """刪除投資組合"""
    try:
        # 檢查投資組合是否存在
        existing_portfolio = portfolio_service.get_portfolio(portfolio_id)
        if not existing_portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="投資組合不存在"
            )

        # 刪除投資組合
        success = portfolio_service.delete_portfolio(portfolio_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="投資組合刪除失敗",
            )

        return APIResponse(
            success=True,
            message="投資組合刪除成功",
            data={
                "portfolio_id": portfolio_id,
                "deleted_at": datetime.now().isoformat(),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刪除投資組合失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除投資組合失敗: {str(e)}",
        )


@router.post(
    "/portfolios/{portfolio_id}/rebalance",
    response_model=APIResponse[RebalanceResult],
    responses=COMMON_RESPONSES,
    summary="執行投資組合再平衡",
    description="根據指定方法執行投資組合再平衡",
)
async def rebalance_portfolio(portfolio_id: str, request: RebalanceRequest):
    """執行投資組合再平衡"""
    try:
        # 檢查投資組合是否存在
        portfolio = portfolio_service.get_portfolio(portfolio_id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="投資組合不存在"
            )

        # 執行再平衡
        rebalance_result = portfolio_service.rebalance_portfolio(
            portfolio_id=portfolio_id,
            method=request.method,
            target_weights=request.target_weights,
            constraints=request.constraints,
        )

        if not rebalance_result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="投資組合再平衡失敗",
            )

        # 轉換為響應模型
        response_data = RebalanceResult(
            portfolio_id=portfolio_id,
            method=request.method,
            old_weights=rebalance_result.get("old_weights", {}),
            new_weights=rebalance_result.get("new_weights", {}),
            weight_changes=rebalance_result.get("weight_changes", {}),
            expected_return=rebalance_result.get("expected_return", 0.0),
            expected_risk=rebalance_result.get("expected_risk", 0.0),
            rebalance_cost=rebalance_result.get("rebalance_cost", 0.0),
            execution_time=datetime.now().isoformat(),
        )

        return APIResponse(
            success=True, message="投資組合再平衡完成", data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"投資組合再平衡失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"投資組合再平衡失敗: {str(e)}",
        )


@router.get(
    "/portfolios/{portfolio_id}/performance",
    response_model=APIResponse[PerformanceMetrics],
    responses=COMMON_RESPONSES,
    summary="查詢績效指標",
    description="獲取投資組合的詳細績效指標",
)
async def get_portfolio_performance(
    portfolio_id: str,
    start_date: Optional[str] = Query(
        default=None, description="開始日期 (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(default=None, description="結束日期 (YYYY-MM-DD)"),
    benchmark: Optional[str] = Query(default=None, description="基準指數"),
):
    """查詢績效指標"""
    try:
        # 檢查投資組合是否存在
        portfolio = portfolio_service.get_portfolio(portfolio_id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="投資組合不存在"
            )

        # 解析日期參數
        start_dt = None
        end_dt = None

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="開始日期格式錯誤，請使用 YYYY-MM-DD 格式",
                )

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="結束日期格式錯誤，請使用 YYYY-MM-DD 格式",
                )

        # 計算績效指標
        performance_metrics = portfolio_service.calculate_performance_metrics(
            portfolio_id=portfolio_id,
            start_date=start_dt,
            end_date=end_dt,
            benchmark=benchmark or portfolio.benchmark,
        )

        if not performance_metrics:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="績效指標計算失敗",
            )

        # 轉換為響應模型
        response_data = PerformanceMetrics(
            total_return=performance_metrics.get("total_return", 0.0),
            annual_return=performance_metrics.get("annual_return", 0.0),
            volatility=performance_metrics.get("volatility", 0.0),
            sharpe_ratio=performance_metrics.get("sharpe_ratio", 0.0),
            max_drawdown=performance_metrics.get("max_drawdown", 0.0),
            calmar_ratio=performance_metrics.get("calmar_ratio", 0.0),
            sortino_ratio=performance_metrics.get("sortino_ratio", 0.0),
            information_ratio=performance_metrics.get("information_ratio", 0.0),
            beta=performance_metrics.get("beta", 0.0),
            alpha=performance_metrics.get("alpha", 0.0),
            tracking_error=performance_metrics.get("tracking_error", 0.0),
        )

        return APIResponse(success=True, message="績效指標獲取成功", data=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取績效指標失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取績效指標失敗: {str(e)}",
        )


@router.get(
    "/portfolios/{portfolio_id}/risk-metrics",
    response_model=APIResponse[RiskMetrics],
    responses=COMMON_RESPONSES,
    summary="查詢風險指標",
    description="獲取投資組合的詳細風險指標",
)
async def get_portfolio_risk_metrics(
    portfolio_id: str,
    confidence_level: float = Query(
        default=0.95, ge=0.9, le=0.99, description="信心水準"
    ),
    lookback_days: int = Query(default=252, ge=30, le=1000, description="回看天數"),
):
    """查詢風險指標"""
    try:
        # 檢查投資組合是否存在
        portfolio = portfolio_service.get_portfolio(portfolio_id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="投資組合不存在"
            )

        # 計算風險指標
        risk_metrics = portfolio_service.calculate_risk_metrics(
            portfolio_id=portfolio_id,
            confidence_level=confidence_level,
            lookback_days=lookback_days,
        )

        if not risk_metrics:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="風險指標計算失敗",
            )

        # 轉換為響應模型
        response_data = RiskMetrics(
            var_95=risk_metrics.get("var_95", 0.0),
            var_99=risk_metrics.get("var_99", 0.0),
            cvar_95=risk_metrics.get("cvar_95", 0.0),
            cvar_99=risk_metrics.get("cvar_99", 0.0),
            volatility=risk_metrics.get("volatility", 0.0),
            downside_deviation=risk_metrics.get("downside_deviation", 0.0),
            max_drawdown=risk_metrics.get("max_drawdown", 0.0),
            correlation_matrix=risk_metrics.get("correlation_matrix", {}),
            concentration_risk=risk_metrics.get("concentration_risk", 0.0),
        )

        return APIResponse(success=True, message="風險指標獲取成功", data=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取風險指標失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取風險指標失敗: {str(e)}",
        )
