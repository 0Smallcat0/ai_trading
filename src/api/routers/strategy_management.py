"""
策略管理路由

此模組實現策略管理相關的 API 端點，包括策略創建、編輯、版本控制、
回測配置和效能分析等功能。
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, validator

from src.api.models.responses import APIResponse, COMMON_RESPONSES

logger = logging.getLogger(__name__)
router = APIRouter()


# 請求模型
class StrategyConfig(BaseModel):
    """策略配置模型

    此模型定義了創建策略時需要的配置參數。

    Attributes:
        name: 策略名稱，長度限制 1-100 字符
        description: 策略描述，最多 500 字符
        type: 策略類型，必須是預定義的類型之一
        parameters: 策略參數字典，包含策略運行所需的參數
        enabled: 是否啟用此策略
        risk_level: 風險等級（low, medium, high）

    Example:
        >>> config = StrategyConfig(
        ...     name="趨勢跟隨策略",
        ...     description="基於移動平均線的趨勢跟隨策略",
        ...     type="trend_following",
        ...     parameters={"short_ma": 20, "long_ma": 50},
        ...     enabled=True,
        ...     risk_level="medium"
        ... )
    """

    name: str = Field(..., min_length=1, max_length=100, description="策略名稱")
    description: str = Field(default="", max_length=500, description="策略描述")
    type: str = Field(..., description="策略類型")
    parameters: Dict[str, Any] = Field(..., description="策略參數")
    enabled: bool = Field(default=True, description="是否啟用")
    risk_level: str = Field(default="medium", description="風險等級")

    @validator("type")
    def validate_type(cls, v):  # pylint: disable=no-self-argument
        """驗證策略類型

        Args:
            v: 待驗證的策略類型

        Returns:
            str: 驗證通過的策略類型

        Raises:
            ValueError: 當策略類型不在允許列表中時
        """
        allowed_types = [
            "trend_following",
            "mean_reversion",
            "momentum",
            "arbitrage",
            "ml_based",
            "custom",
        ]
        if v not in allowed_types:
            raise ValueError(f'策略類型必須是: {", ".join(allowed_types)}')
        return v

    @validator("risk_level")
    def validate_risk_level(cls, v):  # pylint: disable=no-self-argument
        """驗證風險等級

        Args:
            v: 待驗證的風險等級

        Returns:
            str: 驗證通過的風險等級

        Raises:
            ValueError: 當風險等級不在允許列表中時
        """
        allowed_levels = ["low", "medium", "high"]
        if v not in allowed_levels:
            raise ValueError(f'風險等級必須是: {", ".join(allowed_levels)}')
        return v


class StrategyUpdate(BaseModel):
    """策略更新模型

    此模型定義了更新策略時可以修改的欄位。

    Attributes:
        name: 策略名稱，可選更新
        description: 策略描述，可選更新
        parameters: 策略參數，可選更新
        enabled: 是否啟用，可選更新
        risk_level: 風險等級，可選更新

    Note:
        所有欄位都是可選的，只有提供的欄位會被更新
    """

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="策略名稱"
    )
    description: Optional[str] = Field(
        default=None, max_length=500, description="策略描述"
    )
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="策略參數")
    enabled: Optional[bool] = Field(default=None, description="是否啟用")
    risk_level: Optional[str] = Field(default=None, description="風險等級")


class BacktestRequest(BaseModel):
    """回測請求模型

    此模型定義了啟動策略回測時需要的參數。

    Attributes:
        strategy_id: 要回測的策略 ID
        start_date: 回測開始日期
        end_date: 回測結束日期
        initial_capital: 初始資金，必須大於 0
        symbols: 要回測的股票代碼列表
        benchmark: 基準指數，用於比較策略表現

    Example:
        >>> request = BacktestRequest(
        ...     strategy_id="strategy_001",
        ...     start_date=datetime(2024, 1, 1),
        ...     end_date=datetime(2024, 12, 31),
        ...     initial_capital=100000.0,
        ...     symbols=["2330", "2317"],
        ...     benchmark="TAIEX"
        ... )
    """

    strategy_id: str = Field(..., description="策略 ID")
    start_date: datetime = Field(..., description="開始日期")
    end_date: datetime = Field(..., description="結束日期")
    initial_capital: float = Field(default=100000.0, gt=0, description="初始資金")
    symbols: List[str] = Field(..., description="股票代碼列表")
    benchmark: Optional[str] = Field(default=None, description="基準指數")


# 響應模型
class StrategyInfo(BaseModel):
    """策略資訊模型

    此模型定義了策略的詳細資訊，用於 API 回應。

    Attributes:
        id: 策略的唯一識別碼
        name: 策略名稱
        description: 策略描述
        type: 策略類型
        version: 版本號
        status: 策略狀態（draft, active, inactive）
        enabled: 是否啟用
        risk_level: 風險等級
        parameters: 策略參數字典
        created_at: 創建時間
        updated_at: 最後更新時間
        performance: 效能指標（如果有的話）
    """

    id: str = Field(..., description="策略 ID")
    name: str = Field(..., description="策略名稱")
    description: str = Field(..., description="策略描述")
    type: str = Field(..., description="策略類型")
    version: str = Field(..., description="版本號")
    status: str = Field(..., description="狀態")
    enabled: bool = Field(..., description="是否啟用")
    risk_level: str = Field(..., description="風險等級")
    parameters: Dict[str, Any] = Field(..., description="策略參數")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")
    performance: Optional[Dict[str, float]] = Field(
        default=None, description="效能指標"
    )


class BacktestResult(BaseModel):
    """回測結果模型

    此模型定義了策略回測的結果和統計資訊。

    Attributes:
        task_id: 回測任務的唯一識別碼
        strategy_id: 關聯的策略 ID
        status: 回測狀態（running, completed, failed）
        start_date: 回測開始日期
        end_date: 回測結束日期
        initial_capital: 初始資金
        final_capital: 最終資金（回測完成後）
        total_return: 總回報率
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤
        win_rate: 勝率
        created_at: 回測任務創建時間
    """

    task_id: str = Field(..., description="任務 ID")
    strategy_id: str = Field(..., description="策略 ID")
    status: str = Field(..., description="狀態")
    start_date: datetime = Field(..., description="開始日期")
    end_date: datetime = Field(..., description="結束日期")
    initial_capital: float = Field(..., description="初始資金")
    final_capital: Optional[float] = Field(default=None, description="最終資金")
    total_return: Optional[float] = Field(default=None, description="總回報率")
    sharpe_ratio: Optional[float] = Field(default=None, description="夏普比率")
    max_drawdown: Optional[float] = Field(default=None, description="最大回撤")
    win_rate: Optional[float] = Field(default=None, description="勝率")
    created_at: datetime = Field(..., description="創建時間")


# 模擬策略服務
class MockStrategyService:
    """模擬策略管理服務

    此類別提供模擬的策略管理功能，用於開發和測試階段。
    在生產環境中應該替換為真實的策略管理服務。

    Attributes:
        strategies: 策略列表，包含各種交易策略的資訊
        backtests: 回測任務列表

    Note:
        這是一個模擬服務，不應在生產環境中使用
    """

    def __init__(self):
        """初始化模擬策略服務

        設定預設的策略列表和回測任務列表。
        """
        self.strategies = [
            {
                "id": "strategy_001",
                "name": "趨勢跟隨策略",
                "description": "基於移動平均線的趨勢跟隨策略",
                "type": "trend_following",
                "version": "1.0.0",
                "status": "active",
                "enabled": True,
                "risk_level": "medium",
                "parameters": {
                    "short_ma": 20,
                    "long_ma": 50,
                    "stop_loss": 0.05,
                    "take_profit": 0.15,
                },
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "performance": {
                    "total_return": 0.125,
                    "sharpe_ratio": 1.45,
                    "max_drawdown": -0.08,
                    "win_rate": 0.62,
                },
            },
            {
                "id": "strategy_002",
                "name": "均值回歸策略",
                "description": "基於 RSI 指標的均值回歸策略",
                "type": "mean_reversion",
                "version": "1.2.1",
                "status": "active",
                "enabled": True,
                "risk_level": "low",
                "parameters": {
                    "rsi_period": 14,
                    "oversold": 30,
                    "overbought": 70,
                    "position_size": 0.1,
                },
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "performance": {
                    "total_return": 0.089,
                    "sharpe_ratio": 1.12,
                    "max_drawdown": -0.05,
                    "win_rate": 0.58,
                },
            },
        ]
        self.backtests = []

    async def get_strategies(
        self, enabled_only: bool = False, strategy_type: str = None
    ):
        """獲取策略列表

        Args:
            enabled_only: 是否只返回啟用的策略
            strategy_type: 策略類型篩選條件

        Returns:
            List[Dict]: 符合條件的策略列表
        """
        strategies = self.strategies.copy()

        if enabled_only:
            strategies = [s for s in strategies if s["enabled"]]

        if strategy_type:
            strategies = [s for s in strategies if s["type"] == strategy_type]

        return strategies

    async def get_strategy(self, strategy_id: str):
        """獲取單個策略

        Args:
            strategy_id: 策略 ID

        Returns:
            Dict: 策略資訊，如果不存在則返回 None
        """
        for strategy in self.strategies:
            if strategy["id"] == strategy_id:
                return strategy
        return None

    async def create_strategy(self, config: StrategyConfig):
        """創建策略

        Args:
            config: 策略配置

        Returns:
            str: 新創建的策略 ID
        """
        strategy_id = f"strategy_{len(self.strategies) + 1:03d}"
        new_strategy = {
            "id": strategy_id,
            "name": config.name,
            "description": config.description,
            "type": config.type,
            "version": "1.0.0",
            "status": "draft",
            "enabled": config.enabled,
            "risk_level": config.risk_level,
            "parameters": config.parameters,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "performance": None,
        }
        self.strategies.append(new_strategy)
        return strategy_id

    async def update_strategy(self, strategy_id: str, update_data: StrategyUpdate):
        """更新策略

        Args:
            strategy_id: 策略 ID
            update_data: 更新資料

        Returns:
            bool: 更新是否成功
        """
        for strategy in self.strategies:
            if strategy["id"] == strategy_id:
                if update_data.name is not None:
                    strategy["name"] = update_data.name
                if update_data.description is not None:
                    strategy["description"] = update_data.description
                if update_data.parameters is not None:
                    strategy["parameters"] = update_data.parameters
                if update_data.enabled is not None:
                    strategy["enabled"] = update_data.enabled
                if update_data.risk_level is not None:
                    strategy["risk_level"] = update_data.risk_level

                strategy["updated_at"] = datetime.now()
                return True
        return False

    async def start_backtest(self, request: BacktestRequest):
        """啟動回測

        Args:
            request: 回測請求

        Returns:
            str: 回測任務 ID
        """
        task_id = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backtest = {
            "task_id": task_id,
            "strategy_id": request.strategy_id,
            "status": "running",
            "start_date": request.start_date,
            "end_date": request.end_date,
            "initial_capital": request.initial_capital,
            "symbols": request.symbols,
            "benchmark": request.benchmark,
            "created_at": datetime.now(),
        }
        self.backtests.append(backtest)
        return task_id


# 初始化服務
strategy_service = MockStrategyService()


@router.get(
    "/",
    response_model=APIResponse[List[StrategyInfo]],
    responses=COMMON_RESPONSES,
    summary="獲取策略列表",
    description="獲取所有策略的列表，支援篩選條件",
)
async def get_strategies(
    enabled_only: bool = Query(default=False, description="僅顯示啟用的策略"),
    strategy_type: Optional[str] = Query(default=None, description="策略類型篩選"),
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁數量"),
):
    """獲取策略列表

    此端點返回系統中所有策略的列表，支援多種篩選條件和分頁。

    Args:
        enabled_only: 是否只返回啟用的策略
        strategy_type: 策略類型篩選條件
        page: 頁碼，從 1 開始
        page_size: 每頁數量，範圍 1-100

    Returns:
        APIResponse[List[StrategyInfo]]: 包含策略列表的 API 回應

    Raises:
        HTTPException: 當獲取策略列表失敗時

    Example:
        GET /api/strategies?enabled_only=true&strategy_type=trend_following&page=1&page_size=10
    """
    try:
        strategies = await strategy_service.get_strategies(
            enabled_only=enabled_only, strategy_type=strategy_type
        )

        # 分頁處理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_strategies = strategies[start_idx:end_idx]

        strategy_list = [StrategyInfo(**strategy) for strategy in paginated_strategies]

        return APIResponse(success=True, message="策略列表獲取成功", data=strategy_list)

    except Exception as e:
        logger.error("獲取策略列表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="獲取策略列表失敗"
        ) from e


@router.post(
    "/",
    response_model=APIResponse[StrategyInfo],
    responses=COMMON_RESPONSES,
    summary="創建策略",
    description="創建新的交易策略",
)
async def create_strategy(strategy_config: StrategyConfig):
    """創建策略"""
    try:
        # 檢查策略名稱是否已存在
        existing_strategies = await strategy_service.get_strategies()
        if any(
            strategy["name"] == strategy_config.name for strategy in existing_strategies
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="策略名稱已存在"
            )

        # 創建策略
        strategy_id = await strategy_service.create_strategy(strategy_config)

        # 獲取創建的策略資訊
        strategy_info = await strategy_service.get_strategy(strategy_id)

        return APIResponse(
            success=True, message="策略創建成功", data=StrategyInfo(**strategy_info)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("創建策略失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="創建策略失敗"
        ) from e


@router.get(
    "/{strategy_id}",
    response_model=APIResponse[StrategyInfo],
    responses=COMMON_RESPONSES,
    summary="獲取策略詳情",
    description="根據 ID 獲取特定策略的詳細資訊",
)
async def get_strategy(strategy_id: str):
    """獲取策略詳情"""
    try:
        strategy_info = await strategy_service.get_strategy(strategy_id)

        if not strategy_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="策略不存在"
            )

        return APIResponse(
            success=True, message="策略詳情獲取成功", data=StrategyInfo(**strategy_info)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取策略詳情失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="獲取策略詳情失敗"
        ) from e


@router.put(
    "/{strategy_id}",
    response_model=APIResponse[StrategyInfo],
    responses=COMMON_RESPONSES,
    summary="更新策略",
    description="更新現有策略的配置",
)
async def update_strategy(strategy_id: str, update_data: StrategyUpdate):
    """更新策略"""
    try:
        # 檢查策略是否存在
        existing_strategy = await strategy_service.get_strategy(strategy_id)
        if not existing_strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="策略不存在"
            )

        # 更新策略
        success = await strategy_service.update_strategy(strategy_id, update_data)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="策略更新失敗"
            )

        # 獲取更新後的策略資訊
        updated_strategy = await strategy_service.get_strategy(strategy_id)

        return APIResponse(
            success=True, message="策略更新成功", data=StrategyInfo(**updated_strategy)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("更新策略失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="更新策略失敗"
        ) from e


@router.post(
    "/{strategy_id}/backtest",
    response_model=APIResponse[Dict[str, Any]],
    responses=COMMON_RESPONSES,
    summary="啟動策略回測",
    description="為指定策略啟動回測任務",
)
async def start_backtest(strategy_id: str, backtest_request: BacktestRequest):
    """啟動策略回測"""
    try:
        # 檢查策略是否存在
        strategy_info = await strategy_service.get_strategy(strategy_id)
        if not strategy_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="策略不存在"
            )

        # 設定策略 ID
        backtest_request.strategy_id = strategy_id

        # 啟動回測
        task_id = await strategy_service.start_backtest(backtest_request)

        backtest_result = {
            "task_id": task_id,
            "strategy_id": strategy_id,
            "status": "started",
            "start_date": backtest_request.start_date,
            "end_date": backtest_request.end_date,
            "initial_capital": backtest_request.initial_capital,
            "symbols": backtest_request.symbols,
            "benchmark": backtest_request.benchmark,
            "estimated_duration": "10-30 分鐘",
        }

        return APIResponse(success=True, message="回測任務已啟動", data=backtest_result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("啟動回測失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="啟動回測失敗"
        ) from e


@router.get(
    "/types/available",
    response_model=APIResponse[List[Dict[str, str]]],
    responses=COMMON_RESPONSES,
    summary="獲取可用策略類型",
    description="獲取系統支援的所有策略類型",
)
async def get_available_strategy_types():
    """獲取可用策略類型"""
    try:
        strategy_types = [
            {
                "type": "trend_following",
                "name": "趨勢跟隨",
                "description": "基於趨勢指標的策略",
            },
            {
                "type": "mean_reversion",
                "name": "均值回歸",
                "description": "基於價格回歸的策略",
            },
            {
                "type": "momentum",
                "name": "動量策略",
                "description": "基於價格動量的策略",
            },
            {
                "type": "arbitrage",
                "name": "套利策略",
                "description": "基於價差套利的策略",
            },
            {
                "type": "ml_based",
                "name": "機器學習",
                "description": "基於機器學習的策略",
            },
            {"type": "custom", "name": "自定義", "description": "用戶自定義策略"},
        ]

        return APIResponse(
            success=True, message="策略類型獲取成功", data=strategy_types
        )

    except Exception as e:
        logger.error("獲取策略類型失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="獲取策略類型失敗"
        ) from e
