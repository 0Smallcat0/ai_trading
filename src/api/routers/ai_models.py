"""
AI 模型管理路由

此模組實現 AI 模型管理相關的 API 端點，包括模型上傳、下載、訓練、
推理、版本控制和效能監控等功能。
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel, Field, validator

from src.api.models.responses import APIResponse, COMMON_RESPONSES

logger = logging.getLogger(__name__)
router = APIRouter()


# 請求模型
class ModelUploadRequest(BaseModel):
    """模型上傳請求模型

    此模型定義了上傳 AI 模型時需要的參數和元數據。

    Attributes:
        name: 模型名稱，長度限制 1-100 字符
        description: 模型描述，最多 500 字符
        model_type: 模型類型，必須是預定義的類型之一
        framework: 機器學習框架
        version: 版本號，遵循語義化版本規範
        tags: 標籤列表，用於分類和搜尋

    Example:
        >>> request = ModelUploadRequest(
        ...     name="股價預測模型",
        ...     description="基於 LSTM 的股價預測模型",
        ...     model_type="time_series",
        ...     framework="tensorflow",
        ...     version="1.0.0",
        ...     tags=["stock", "prediction"]
        ... )
    """

    name: str = Field(..., min_length=1, max_length=100, description="模型名稱")
    description: str = Field(default="", max_length=500, description="模型描述")
    model_type: str = Field(..., description="模型類型")
    framework: str = Field(..., description="機器學習框架")
    version: str = Field(default="1.0.0", description="版本號")
    tags: List[str] = Field(default=[], description="標籤")

    @validator("model_type")
    def validate_model_type(cls, v):  # pylint: disable=no-self-argument
        """驗證模型類型

        Args:
            v: 待驗證的模型類型

        Returns:
            str: 驗證通過的模型類型

        Raises:
            ValueError: 當模型類型不在允許列表中時
        """
        allowed_types = [
            "classification",
            "regression",
            "clustering",
            "time_series",
            "nlp",
            "computer_vision",
        ]
        if v not in allowed_types:
            raise ValueError(f'模型類型必須是: {", ".join(allowed_types)}')
        return v

    @validator("framework")
    def validate_framework(cls, v):  # pylint: disable=no-self-argument
        """驗證機器學習框架

        Args:
            v: 待驗證的框架名稱

        Returns:
            str: 驗證通過的框架名稱

        Raises:
            ValueError: 當框架不在允許列表中時
        """
        allowed_frameworks = [
            "sklearn",
            "tensorflow",
            "pytorch",
            "xgboost",
            "lightgbm",
            "onnx",
        ]
        if v not in allowed_frameworks:
            raise ValueError(f'框架必須是: {", ".join(allowed_frameworks)}')
        return v

    @validator("version")
    def validate_version(cls, v):  # pylint: disable=no-self-argument
        """驗證版本號格式

        Args:
            v: 待驗證的版本號

        Returns:
            str: 驗證通過的版本號

        Raises:
            ValueError: 當版本號格式不正確時
        """
        import re  # pylint: disable=import-outside-toplevel

        # 簡單的語義化版本驗證
        pattern = r"^\d+\.\d+\.\d+$"
        if not re.match(pattern, v):
            raise ValueError("版本號必須遵循語義化版本格式 (例如: 1.0.0)")
        return v


class TrainingRequest(BaseModel):
    """模型訓練請求模型

    此模型定義了啟動模型訓練時需要的參數配置。

    Attributes:
        dataset_id: 訓練數據集的唯一識別碼
        hyperparameters: 超參數配置字典
        validation_split: 驗證集比例，範圍 0.1-0.5
        epochs: 訓練輪數，範圍 1-1000
        early_stopping: 是否啟用早停機制

    Example:
        >>> request = TrainingRequest(
        ...     dataset_id="dataset_001",
        ...     hyperparameters={"learning_rate": 0.001, "batch_size": 32},
        ...     validation_split=0.2,
        ...     epochs=100
        ... )
    """

    dataset_id: str = Field(..., description="訓練數據集 ID")
    hyperparameters: Dict[str, Any] = Field(..., description="超參數配置")
    validation_split: float = Field(
        default=0.2, ge=0.1, le=0.5, description="驗證集比例"
    )
    epochs: int = Field(default=100, ge=1, le=1000, description="訓練輪數")
    early_stopping: bool = Field(default=True, description="是否啟用早停")


class PredictionRequest(BaseModel):
    """推理請求模型

    此模型定義了模型推理時需要的輸入參數和選項。

    Attributes:
        input_data: 輸入數據，可以是數值列表或字典格式
        return_probabilities: 是否返回預測概率
        explain: 是否返回模型解釋結果

    Example:
        >>> request = PredictionRequest(
        ...     input_data=[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
        ...     return_probabilities=True,
        ...     explain=True
        ... )
    """

    input_data: Union[List[List[float]], Dict[str, Any]] = Field(
        ..., description="輸入數據"
    )
    return_probabilities: bool = Field(default=False, description="是否返回概率")
    explain: bool = Field(default=False, description="是否返回解釋")


# 響應模型
class ModelInfo(BaseModel):
    """AI 模型資訊模型

    此模型定義了 AI 模型的詳細資訊，用於 API 回應。

    Attributes:
        id: 模型的唯一識別碼
        name: 模型名稱
        description: 模型描述
        model_type: 模型類型（分類、回歸等）
        framework: 機器學習框架
        version: 版本號
        status: 模型狀態（training, ready, deprecated）
        file_size: 檔案大小（位元組）
        created_at: 創建時間
        updated_at: 最後更新時間
        tags: 標籤列表
        metrics: 效能指標字典
    """

    id: str = Field(..., description="模型 ID")
    name: str = Field(..., description="模型名稱")
    description: str = Field(..., description="模型描述")
    model_type: str = Field(..., description="模型類型")
    framework: str = Field(..., description="機器學習框架")
    version: str = Field(..., description="版本號")
    status: str = Field(..., description="狀態")
    file_size: int = Field(..., description="文件大小 (bytes)")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: datetime = Field(..., description="更新時間")
    tags: List[str] = Field(..., description="標籤")
    metrics: Optional[Dict[str, float]] = Field(default=None, description="效能指標")


class ModelVersion(BaseModel):
    """模型版本模型

    此模型定義了模型版本的詳細資訊。

    Attributes:
        version: 版本號
        created_at: 版本創建時間
        status: 版本狀態（ready, deprecated）
        metrics: 該版本的效能指標
        changelog: 版本變更日誌
    """

    version: str = Field(..., description="版本號")
    created_at: datetime = Field(..., description="創建時間")
    status: str = Field(..., description="狀態")
    metrics: Optional[Dict[str, float]] = Field(default=None, description="效能指標")
    changelog: str = Field(default="", description="變更日誌")


class TrainingTask(BaseModel):
    """訓練任務模型

    此模型定義了模型訓練任務的狀態和進度資訊。

    Attributes:
        task_id: 任務的唯一識別碼
        model_id: 關聯的模型 ID
        status: 任務狀態（running, completed, failed）
        progress: 進度百分比（0-100）
        current_epoch: 當前訓練輪數
        total_epochs: 總訓練輪數
        loss: 當前損失值
        metrics: 當前訓練指標
        started_at: 任務開始時間
        estimated_completion: 預計完成時間
    """

    task_id: str = Field(..., description="任務 ID")
    model_id: str = Field(..., description="模型 ID")
    status: str = Field(..., description="狀態")
    progress: float = Field(..., description="進度百分比")
    current_epoch: int = Field(default=0, description="當前輪數")
    total_epochs: int = Field(..., description="總輪數")
    loss: Optional[float] = Field(default=None, description="當前損失")
    metrics: Optional[Dict[str, float]] = Field(default=None, description="當前指標")
    started_at: datetime = Field(..., description="開始時間")
    estimated_completion: Optional[datetime] = Field(
        default=None, description="預計完成時間"
    )


class PredictionResult(BaseModel):
    """推理結果模型

    此模型定義了模型推理的結果和相關資訊。

    Attributes:
        predictions: 預測結果列表
        probabilities: 預測概率（分類模型）
        explanations: 模型解釋結果（SHAP/LIME）
        model_version: 使用的模型版本
        inference_time: 推理耗時（秒）
    """

    predictions: List[Any] = Field(..., description="預測結果")
    probabilities: Optional[List[List[float]]] = Field(
        default=None, description="預測概率"
    )
    explanations: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="解釋結果"
    )
    model_version: str = Field(..., description="模型版本")
    inference_time: float = Field(..., description="推理時間 (秒)")


# 模擬 AI 模型服務
class MockAIModelService:
    """模擬 AI 模型管理服務

    此類別提供模擬的 AI 模型管理功能，用於開發和測試階段。
    在生產環境中應該替換為真實的模型管理服務。

    Attributes:
        models: 模型列表，包含各種 AI 模型的資訊
        training_tasks: 訓練任務列表
        model_versions: 模型版本字典

    Note:
        這是一個模擬服務，不應在生產環境中使用
    """

    def __init__(self):
        """初始化模擬 AI 模型服務

        設定預設的模型列表、訓練任務和版本資訊。
        """
        self.models = [
            {
                "id": "model_001",
                "name": "股價預測模型",
                "description": "基於 LSTM 的股價預測模型",
                "model_type": "time_series",
                "framework": "tensorflow",
                "version": "2.1.0",
                "status": "ready",
                "file_size": 15728640,  # 15MB
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "tags": ["stock", "prediction", "lstm"],
                "metrics": {"mse": 0.0234, "mae": 0.1123, "r2_score": 0.8567},
            },
            {
                "id": "model_002",
                "name": "情感分析模型",
                "description": "基於 BERT 的金融新聞情感分析模型",
                "model_type": "nlp",
                "framework": "pytorch",
                "version": "1.3.2",
                "status": "ready",
                "file_size": 438041600,  # 418MB
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "tags": ["nlp", "sentiment", "bert", "finance"],
                "metrics": {
                    "accuracy": 0.9234,
                    "f1_score": 0.9156,
                    "precision": 0.9278,
                    "recall": 0.9045,
                },
            },
            {
                "id": "model_003",
                "name": "風險評估模型",
                "description": "基於 XGBoost 的投資風險評估模型",
                "model_type": "classification",
                "framework": "xgboost",
                "version": "1.0.5",
                "status": "training",
                "file_size": 5242880,  # 5MB
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "tags": ["risk", "classification", "xgboost"],
                "metrics": None,
            },
        ]

        self.training_tasks = []
        self.model_versions = {
            "model_001": [
                {
                    "version": "2.1.0",
                    "created_at": datetime.now(),
                    "status": "ready",
                    "metrics": {"mse": 0.0234, "mae": 0.1123, "r2_score": 0.8567},
                    "changelog": "改進了 LSTM 架構，提升預測準確性",
                },
                {
                    "version": "2.0.0",
                    "created_at": datetime.now(),
                    "status": "deprecated",
                    "metrics": {"mse": 0.0289, "mae": 0.1245, "r2_score": 0.8234},
                    "changelog": "初始版本",
                },
            ]
        }

    async def get_models(
        self,
        model_type: str = None,
        framework: str = None,
        model_status: str = None,
        tags: List[str] = None,
    ):
        """獲取模型列表

        Args:
            model_type: 模型類型篩選條件
            framework: 框架篩選條件
            model_status: 狀態篩選條件
            tags: 標籤篩選條件

        Returns:
            List[Dict]: 符合條件的模型列表
        """
        models = self.models.copy()

        if model_type:
            models = [m for m in models if m["model_type"] == model_type]

        if framework:
            models = [m for m in models if m["framework"] == framework]

        if model_status:
            models = [m for m in models if m["status"] == model_status]

        if tags:
            models = [m for m in models if any(tag in m["tags"] for tag in tags)]

        return models

    async def get_model(self, model_id: str):
        """獲取單個模型

        Args:
            model_id: 模型 ID

        Returns:
            Dict: 模型資訊，如果不存在則返回 None
        """
        for model in self.models:
            if model["id"] == model_id:
                return model
        return None

    async def upload_model(self, request: ModelUploadRequest, file_size: int):
        """上傳模型

        Args:
            request: 模型上傳請求
            file_size: 檔案大小

        Returns:
            str: 新創建的模型 ID
        """
        model_id = f"model_{len(self.models) + 1:03d}"
        new_model = {
            "id": model_id,
            "name": request.name,
            "description": request.description,
            "model_type": request.model_type,
            "framework": request.framework,
            "version": request.version,
            "status": "uploading",
            "file_size": file_size,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "tags": request.tags,
            "metrics": None,
        }
        self.models.append(new_model)
        return model_id

    async def start_training(self, model_id: str, request: TrainingRequest):
        """啟動模型訓練"""
        task_id = f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        training_task = {
            "task_id": task_id,
            "model_id": model_id,
            "status": "running",
            "progress": 0.0,
            "current_epoch": 0,
            "total_epochs": request.epochs,
            "loss": None,
            "metrics": None,
            "started_at": datetime.now(),
            "estimated_completion": None,
            "dataset_id": request.dataset_id,
            "hyperparameters": request.hyperparameters,
        }
        self.training_tasks.append(training_task)
        return task_id

    async def get_training_task(self, task_id: str):
        """獲取訓練任務狀態"""
        for task in self.training_tasks:
            if task["task_id"] == task_id:
                return task
        return None

    async def predict(self, model_id: str, request: PredictionRequest):
        """模型推理

        Args:
            model_id: 模型 ID（用於記錄和驗證）
            request: 推理請求

        Returns:
            Dict: 推理結果，包含預測值、概率和解釋
        """
        import time  # pylint: disable=import-outside-toplevel
        import random  # pylint: disable=import-outside-toplevel

        # 記錄使用的模型（用於日誌和驗證）
        logger.info("使用模型 %s 進行推理", model_id)

        start_time = time.time()

        # 模擬推理過程
        if isinstance(request.input_data, list):
            num_samples = len(request.input_data)
        else:
            num_samples = 1

        # 生成模擬預測結果
        predictions = [random.uniform(0, 1) for _ in range(num_samples)]

        probabilities = None
        if request.return_probabilities:
            probabilities = [
                [random.uniform(0, 1), random.uniform(0, 1)] for _ in range(num_samples)
            ]

        explanations = None
        if request.explain:
            explanations = [
                {
                    "feature_importance": {
                        f"feature_{i}": random.uniform(0, 1) for i in range(5)
                    },
                    "shap_values": [random.uniform(-0.5, 0.5) for _ in range(5)],
                }
                for _ in range(num_samples)
            ]

        inference_time = time.time() - start_time

        return {
            "predictions": predictions,
            "probabilities": probabilities,
            "explanations": explanations,
            "model_version": "2.1.0",
            "inference_time": inference_time,
        }

    async def get_model_versions(self, model_id: str):
        """獲取模型版本列表"""
        return self.model_versions.get(model_id, [])

    async def get_model_metrics(self, model_id: str):
        """獲取模型效能指標"""
        model = await self.get_model(model_id)
        if not model:
            return None

        return {
            "model_id": model_id,
            "current_version": model["version"],
            "metrics": model["metrics"],
            "benchmark_comparison": {
                "baseline_model": {"accuracy": 0.85, "f1_score": 0.82},
                "improvement": "+8.2%" if model["metrics"] else "N/A",
            },
            "performance_history": [
                {"date": "2024-01-01", "accuracy": 0.89},
                {"date": "2024-02-01", "accuracy": 0.91},
                {"date": "2024-03-01", "accuracy": 0.92},
            ],
        }


# 初始化服務
ai_model_service = MockAIModelService()


@router.get(
    "/",
    response_model=APIResponse[List[ModelInfo]],
    responses=COMMON_RESPONSES,
    summary="獲取 AI 模型列表",
    description="獲取所有 AI 模型的列表，支援多種篩選條件",
)
async def get_models(
    model_type: Optional[str] = Query(default=None, description="模型類型篩選"),
    framework: Optional[str] = Query(default=None, description="框架篩選"),
    model_status: Optional[str] = Query(
        default=None, description="狀態篩選", alias="status"
    ),
    tags: Optional[str] = Query(default=None, description="標籤篩選，多個用逗號分隔"),
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁數量"),
):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """獲取 AI 模型列表

    此端點返回系統中所有 AI 模型的列表，支援多種篩選條件和分頁。

    Args:
        model_type: 模型類型篩選條件
        framework: 機器學習框架篩選條件
        model_status: 模型狀態篩選條件
        tags: 標籤篩選條件，多個標籤用逗號分隔
        page: 頁碼，從 1 開始
        page_size: 每頁數量，範圍 1-100

    Returns:
        APIResponse[List[ModelInfo]]: 包含模型列表的 API 回應

    Raises:
        HTTPException: 當獲取模型列表失敗時

    Example:
        GET /api/ai-models?model_type=time_series&framework=tensorflow&page=1&page_size=10
    """
    try:
        # 處理標籤篩選
        tag_list = tags.split(",") if tags else None

        models = await ai_model_service.get_models(
            model_type=model_type,
            framework=framework,
            model_status=model_status,
            tags=tag_list,
        )

        # 分頁處理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_models = models[start_idx:end_idx]

        model_list = [ModelInfo(**model) for model in paginated_models]

        return APIResponse(success=True, message="AI 模型列表獲取成功", data=model_list)

    except Exception as e:
        logger.error("獲取 AI 模型列表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取 AI 模型列表失敗",
        ) from e


@router.post(
    "/upload",
    response_model=APIResponse[ModelInfo],
    responses=COMMON_RESPONSES,
    summary="上傳 AI 模型",
    description="上傳新的 AI 模型文件",
)
async def upload_model(
    file: UploadFile = File(..., description="模型文件"),
    name: str = Query(..., description="模型名稱"),
    description: str = Query(default="", description="模型描述"),
    model_type: str = Query(..., description="模型類型"),
    framework: str = Query(..., description="機器學習框架"),
    version: str = Query(default="1.0.0", description="版本號"),
    tags: str = Query(default="", description="標籤，多個用逗號分隔"),
):  # pylint: disable=too-many-arguments,too-many-locals,too-many-positional-arguments
    """上傳 AI 模型

    此端點允許上傳新的 AI 模型檔案到系統中。

    Args:
        file: 模型檔案（支援 .pkl, .joblib, .h5, .pb, .pth, .onnx, .json）
        name: 模型名稱
        description: 模型描述
        model_type: 模型類型
        framework: 機器學習框架
        version: 版本號
        tags: 標籤，多個用逗號分隔

    Returns:
        APIResponse[ModelInfo]: 包含上傳模型資訊的 API 回應

    Raises:
        HTTPException: 當檔案格式不支援、檔案過大或上傳失敗時

    Example:
        POST /api/ai-models/upload
        Content-Type: multipart/form-data
    """
    try:
        # 驗證文件類型
        allowed_extensions = [".pkl", ".joblib", ".h5", ".pb", ".pth", ".onnx", ".json"]
        file_extension = os.path.splitext(file.filename)[1].lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支援的文件格式。支援的格式: {', '.join(allowed_extensions)}",
            )

        # 檢查文件大小 (限制 500MB)
        max_size = 500 * 1024 * 1024  # 500MB
        file_size = 0

        # 模擬讀取文件大小
        content = await file.read()
        file_size = len(content)

        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="文件大小超過限制 (500MB)",
            )

        # 創建上傳請求
        tag_list = (
            [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
        )

        upload_request = ModelUploadRequest(
            name=name,
            description=description,
            model_type=model_type,
            framework=framework,
            version=version,
            tags=tag_list,
        )

        # 上傳模型
        model_id = await ai_model_service.upload_model(upload_request, file_size)

        # 獲取上傳的模型資訊
        model_info = await ai_model_service.get_model(model_id)

        return APIResponse(
            success=True, message="模型上傳成功", data=ModelInfo(**model_info)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("模型上傳失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="模型上傳失敗"
        ) from e


@router.get(
    "/{model_id}",
    response_model=APIResponse[ModelInfo],
    responses=COMMON_RESPONSES,
    summary="獲取 AI 模型詳情",
    description="根據 ID 獲取特定 AI 模型的詳細資訊",
)
async def get_model(model_id: str):
    """獲取 AI 模型詳情"""
    try:
        model_info = await ai_model_service.get_model(model_id)

        if not model_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="AI 模型不存在"
            )

        return APIResponse(
            success=True, message="AI 模型詳情獲取成功", data=ModelInfo(**model_info)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取 AI 模型詳情失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取 AI 模型詳情失敗",
        ) from e


@router.get(
    "/{model_id}/download",
    response_model=APIResponse[Dict[str, Any]],
    responses=COMMON_RESPONSES,
    summary="下載 AI 模型",
    description="下載指定的 AI 模型文件",
)
async def download_model(model_id: str):
    """下載 AI 模型"""
    try:
        model_info = await ai_model_service.get_model(model_id)

        if not model_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="AI 模型不存在"
            )

        if model_info["status"] != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="模型尚未準備就緒，無法下載",
            )

        # 由於這是模擬，我們返回一個示例響應
        # 實際應用中應該返回真實的文件
        return APIResponse(
            success=True,
            message="模型下載連結已生成",
            data={
                "download_url": f"/api/v1/models/{model_id}/download",
                "expires_in": 3600,  # 1小時
                "file_size": model_info["file_size"],
                "filename": f"{model_info['name']}_v{model_info['version']}.pkl",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("下載 AI 模型失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="下載 AI 模型失敗"
        ) from e


@router.post(
    "/{model_id}/train",
    response_model=APIResponse[TrainingTask],
    responses=COMMON_RESPONSES,
    summary="啟動模型訓練",
    description="為指定模型啟動訓練任務",
)
async def start_training(model_id: str, training_request: TrainingRequest):
    """啟動模型訓練"""
    try:
        # 檢查模型是否存在
        model_info = await ai_model_service.get_model(model_id)
        if not model_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="AI 模型不存在"
            )

        # 檢查模型狀態
        if model_info["status"] == "training":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="模型正在訓練中，請等待完成",
            )

        # 啟動訓練
        task_id = await ai_model_service.start_training(model_id, training_request)

        # 獲取訓練任務資訊
        training_task = await ai_model_service.get_training_task(task_id)

        return APIResponse(
            success=True,
            message="模型訓練任務已啟動",
            data=TrainingTask(**training_task),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("啟動模型訓練失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="啟動模型訓練失敗"
        ) from e


@router.post(
    "/{model_id}/predict",
    response_model=APIResponse[PredictionResult],
    responses=COMMON_RESPONSES,
    summary="模型推理",
    description="使用指定模型進行預測推理",
)
async def predict(model_id: str, prediction_request: PredictionRequest):
    """模型推理"""
    try:
        # 檢查模型是否存在
        model_info = await ai_model_service.get_model(model_id)
        if not model_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="AI 模型不存在"
            )

        # 檢查模型狀態
        if model_info["status"] != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="模型尚未準備就緒，無法進行推理",
            )

        # 執行推理
        prediction_result = await ai_model_service.predict(model_id, prediction_request)

        return APIResponse(
            success=True,
            message="模型推理完成",
            data=PredictionResult(**prediction_result),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("模型推理失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="模型推理失敗"
        ) from e


@router.get(
    "/{model_id}/versions",
    response_model=APIResponse[List[ModelVersion]],
    responses=COMMON_RESPONSES,
    summary="獲取模型版本列表",
    description="獲取指定模型的所有版本資訊",
)
async def get_model_versions(model_id: str):
    """獲取模型版本列表"""
    try:
        # 檢查模型是否存在
        model_info = await ai_model_service.get_model(model_id)
        if not model_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="AI 模型不存在"
            )

        # 獲取版本列表
        versions = await ai_model_service.get_model_versions(model_id)

        version_list = [ModelVersion(**version) for version in versions]

        return APIResponse(
            success=True, message="模型版本列表獲取成功", data=version_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取模型版本列表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取模型版本列表失敗",
        ) from e


@router.get(
    "/{model_id}/metrics",
    response_model=APIResponse[Dict[str, Any]],
    responses=COMMON_RESPONSES,
    summary="獲取模型效能指標",
    description="獲取指定模型的詳細效能指標和分析",
)
async def get_model_metrics(model_id: str):
    """獲取模型效能指標"""
    try:
        # 檢查模型是否存在
        model_info = await ai_model_service.get_model(model_id)
        if not model_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="AI 模型不存在"
            )

        # 獲取效能指標
        metrics = await ai_model_service.get_model_metrics(model_id)

        return APIResponse(success=True, message="模型效能指標獲取成功", data=metrics)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取模型效能指標失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取模型效能指標失敗",
        ) from e
