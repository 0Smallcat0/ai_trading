"""
API 版本控制模型

此模組定義了 API 版本控制相關的數據模型，包括版本信息、
相容性檢查、遷移狀態等核心數據結構。
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import re


class VersionStatusEnum(str, Enum):
    """版本狀態枚舉"""

    DEVELOPMENT = "development"
    BETA = "beta"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class VersionTypeEnum(str, Enum):
    """版本類型枚舉"""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"


class CompatibilityLevelEnum(str, Enum):
    """相容性級別枚舉"""

    FULL = "full"
    BACKWARD = "backward"
    FORWARD = "forward"
    BREAKING = "breaking"
    NONE = "none"


class MigrationStatusEnum(str, Enum):
    """遷移狀態枚舉"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class VersionDetectionMethodEnum(str, Enum):
    """版本檢測方法枚舉"""

    URL_PATH = "url_path"
    HEADER = "header"
    QUERY_PARAM = "query_param"
    CONTENT_TYPE = "content_type"


# ==================== 版本信息模型 ====================


class SemanticVersion(BaseModel):
    """語義化版本模型"""

    major: int = Field(..., ge=0, description="主版本號")
    minor: int = Field(..., ge=0, description="次版本號")
    patch: int = Field(..., ge=0, description="修訂版本號")
    prerelease: Optional[str] = Field(default=None, description="預發布版本標識")
    build: Optional[str] = Field(default=None, description="構建元數據")

    @field_validator("prerelease")
    @classmethod
    def validate_prerelease(cls, v):
        """驗證預發布版本格式"""
        if v is not None:
            if not re.match(r"^[0-9A-Za-z\-\.]+$", v):
                raise ValueError("預發布版本格式無效")
        return v

    @field_validator("build")
    @classmethod
    def validate_build(cls, v):
        """驗證構建元數據格式"""
        if v is not None:
            if not re.match(r"^[0-9A-Za-z\-\.]+$", v):
                raise ValueError("構建元數據格式無效")
        return v

    def __str__(self) -> str:
        """返回版本字符串"""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __lt__(self, other: "SemanticVersion") -> bool:
        """版本比較：小於"""
        if (self.major, self.minor, self.patch) != (
            other.major,
            other.minor,
            other.patch,
        ):
            return (self.major, self.minor, self.patch) < (
                other.major,
                other.minor,
                other.patch,
            )

        # 如果主版本號相同，比較預發布版本
        if self.prerelease is None and other.prerelease is not None:
            return False
        if self.prerelease is not None and other.prerelease is None:
            return True
        if self.prerelease is not None and other.prerelease is not None:
            return self.prerelease < other.prerelease

        return False

    def __eq__(self, other: "SemanticVersion") -> bool:
        """版本比較：等於"""
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __le__(self, other: "SemanticVersion") -> bool:
        """版本比較：小於等於"""
        return self < other or self == other

    def __gt__(self, other: "SemanticVersion") -> bool:
        """版本比較：大於"""
        return not self <= other

    def __ge__(self, other: "SemanticVersion") -> bool:
        """版本比較：大於等於"""
        return not self < other

    @classmethod
    def parse(cls, version_string: str) -> "SemanticVersion":
        """解析版本字符串"""
        # 匹配語義化版本格式
        pattern = (
            r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z\-\.]+))?(?:\+([0-9A-Za-z\-\.]+))?$"
        )
        match = re.match(pattern, version_string)

        if not match:
            raise ValueError(f"無效的版本格式: {version_string}")

        major, minor, patch, prerelease, build = match.groups()

        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            prerelease=prerelease,
            build=build,
        )


class APIVersion(BaseModel):
    """API 版本信息模型"""

    version: SemanticVersion = Field(..., description="語義化版本")
    status: VersionStatusEnum = Field(..., description="版本狀態")
    release_date: datetime = Field(..., description="發布日期")
    deprecation_date: Optional[datetime] = Field(default=None, description="棄用日期")
    retirement_date: Optional[datetime] = Field(default=None, description="停用日期")

    # 版本描述
    title: str = Field(..., min_length=1, max_length=100, description="版本標題")
    description: Optional[str] = Field(
        default=None, max_length=1000, description="版本描述"
    )
    changelog: Optional[List[str]] = Field(default=None, description="變更日誌")

    # 相容性信息
    compatible_versions: List[str] = Field(
        default_factory=list, description="相容版本列表"
    )
    breaking_changes: List[str] = Field(
        default_factory=list, description="破壞性變更列表"
    )

    # 技術信息
    api_endpoints: Dict[str, Any] = Field(
        default_factory=dict, description="API 端點信息"
    )
    schema_changes: Dict[str, Any] = Field(
        default_factory=dict, description="Schema 變更"
    )

    # 元數據
    maintainer: Optional[str] = Field(default=None, description="維護者")
    documentation_url: Optional[str] = Field(default=None, description="文檔 URL")
    migration_guide_url: Optional[str] = Field(default=None, description="遷移指南 URL")

    created_at: datetime = Field(default_factory=datetime.now, description="創建時間")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新時間")

    @field_validator("deprecation_date")
    @classmethod
    def validate_deprecation_date(cls, v, info):
        """驗證棄用日期"""
        if (
            v
            and hasattr(info, "data")
            and "release_date" in info.data
            and v <= info.data["release_date"]
        ):
            raise ValueError("棄用日期必須晚於發布日期")
        return v

    @field_validator("retirement_date")
    @classmethod
    def validate_retirement_date(cls, v, info):
        """驗證停用日期"""
        if v and hasattr(info, "data"):
            if "release_date" in info.data and v <= info.data["release_date"]:
                raise ValueError("停用日期必須晚於發布日期")
            if (
                "deprecation_date" in info.data
                and info.data["deprecation_date"]
                and v <= info.data["deprecation_date"]
            ):
                raise ValueError("停用日期必須晚於棄用日期")
        return v

    def is_active(self) -> bool:
        """檢查版本是否處於活躍狀態"""
        now = datetime.now()
        return self.status in [
            VersionStatusEnum.DEVELOPMENT,
            VersionStatusEnum.BETA,
            VersionStatusEnum.STABLE,
        ] and (self.retirement_date is None or self.retirement_date > now)

    def is_deprecated(self) -> bool:
        """檢查版本是否已棄用"""
        now = datetime.now()
        return self.status == VersionStatusEnum.DEPRECATED or (
            self.deprecation_date is not None and self.deprecation_date <= now
        )

    def days_until_retirement(self) -> Optional[int]:
        """計算距離停用還有多少天"""
        if self.retirement_date is None:
            return None

        now = datetime.now()
        if self.retirement_date <= now:
            return 0

        return (self.retirement_date - now).days


# ==================== 相容性檢查模型 ====================


class CompatibilityCheck(BaseModel):
    """相容性檢查模型"""

    source_version: str = Field(..., description="源版本")
    target_version: str = Field(..., description="目標版本")
    compatibility_level: CompatibilityLevelEnum = Field(..., description="相容性級別")

    # 檢查結果
    is_compatible: bool = Field(..., description="是否相容")
    breaking_changes: List[str] = Field(default_factory=list, description="破壞性變更")
    warnings: List[str] = Field(default_factory=list, description="警告信息")
    recommendations: List[str] = Field(default_factory=list, description="建議")

    # 檢查詳情
    endpoint_changes: Dict[str, Any] = Field(
        default_factory=dict, description="端點變更"
    )
    schema_changes: Dict[str, Any] = Field(
        default_factory=dict, description="Schema 變更"
    )
    parameter_changes: Dict[str, Any] = Field(
        default_factory=dict, description="參數變更"
    )

    # 元數據
    checked_at: datetime = Field(default_factory=datetime.now, description="檢查時間")
    checked_by: Optional[str] = Field(default=None, description="檢查者")


class MigrationPlan(BaseModel):
    """遷移計劃模型"""

    migration_id: str = Field(..., description="遷移ID")
    name: str = Field(..., min_length=1, max_length=100, description="遷移名稱")
    description: Optional[str] = Field(
        default=None, max_length=1000, description="遷移描述"
    )

    # 版本信息
    source_version: str = Field(..., description="源版本")
    target_version: str = Field(..., description="目標版本")

    # 遷移步驟
    steps: List[Dict[str, Any]] = Field(..., description="遷移步驟")
    rollback_steps: List[Dict[str, Any]] = Field(
        default_factory=list, description="回滾步驟"
    )

    # 狀態信息
    status: MigrationStatusEnum = Field(
        default=MigrationStatusEnum.PENDING, description="遷移狀態"
    )
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="進度百分比")

    # 時間信息
    estimated_duration: Optional[int] = Field(
        default=None, description="預估時長（分鐘）"
    )
    started_at: Optional[datetime] = Field(default=None, description="開始時間")
    completed_at: Optional[datetime] = Field(default=None, description="完成時間")

    # 結果信息
    success_count: int = Field(default=0, description="成功步驟數")
    failure_count: int = Field(default=0, description="失敗步驟數")
    error_messages: List[str] = Field(default_factory=list, description="錯誤信息")

    # 元數據
    created_by: str = Field(..., description="創建者")
    created_at: datetime = Field(default_factory=datetime.now, description="創建時間")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新時間")


# ==================== 請求和響應模型 ====================


class VersionDetectionRequest(BaseModel):
    """版本檢測請求模型"""

    method: VersionDetectionMethodEnum = Field(..., description="檢測方法")
    url_path: Optional[str] = Field(default=None, description="URL 路徑")
    headers: Optional[Dict[str, str]] = Field(default=None, description="請求標頭")
    query_params: Optional[Dict[str, str]] = Field(default=None, description="查詢參數")
    content_type: Optional[str] = Field(default=None, description="內容類型")


class VersionNegotiationRequest(BaseModel):
    """版本協商請求模型"""

    client_version: Optional[str] = Field(default=None, description="客戶端版本")
    supported_versions: List[str] = Field(
        default_factory=list, description="支援版本列表"
    )
    preferred_version: Optional[str] = Field(default=None, description="偏好版本")
    fallback_version: Optional[str] = Field(default=None, description="備用版本")


class VersionCreateRequest(BaseModel):
    """創建版本請求模型"""

    version: str = Field(..., description="版本號")
    title: str = Field(..., min_length=1, max_length=100, description="版本標題")
    description: Optional[str] = Field(
        default=None, max_length=1000, description="版本描述"
    )
    status: VersionStatusEnum = Field(
        default=VersionStatusEnum.DEVELOPMENT, description="版本狀態"
    )

    # 時間設定
    release_date: Optional[datetime] = Field(default=None, description="發布日期")
    deprecation_date: Optional[datetime] = Field(default=None, description="棄用日期")
    retirement_date: Optional[datetime] = Field(default=None, description="停用日期")

    # 變更信息
    changelog: Optional[List[str]] = Field(default=None, description="變更日誌")
    breaking_changes: Optional[List[str]] = Field(
        default=None, description="破壞性變更"
    )
    compatible_versions: Optional[List[str]] = Field(
        default=None, description="相容版本"
    )

    # 元數據
    maintainer: Optional[str] = Field(default=None, description="維護者")
    documentation_url: Optional[str] = Field(default=None, description="文檔 URL")
    migration_guide_url: Optional[str] = Field(default=None, description="遷移指南 URL")


class VersionUpdateRequest(BaseModel):
    """更新版本請求模型"""

    title: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="版本標題"
    )
    description: Optional[str] = Field(
        default=None, max_length=1000, description="版本描述"
    )
    status: Optional[VersionStatusEnum] = Field(default=None, description="版本狀態")

    # 時間設定
    deprecation_date: Optional[datetime] = Field(default=None, description="棄用日期")
    retirement_date: Optional[datetime] = Field(default=None, description="停用日期")

    # 變更信息
    changelog: Optional[List[str]] = Field(default=None, description="變更日誌")
    breaking_changes: Optional[List[str]] = Field(
        default=None, description="破壞性變更"
    )
    compatible_versions: Optional[List[str]] = Field(
        default=None, description="相容版本"
    )

    # 元數據
    maintainer: Optional[str] = Field(default=None, description="維護者")
    documentation_url: Optional[str] = Field(default=None, description="文檔 URL")
    migration_guide_url: Optional[str] = Field(default=None, description="遷移指南 URL")


class VersionListRequest(BaseModel):
    """版本列表查詢請求模型"""

    page: int = Field(default=1, ge=1, description="頁碼")
    page_size: int = Field(default=20, ge=1, le=100, description="每頁數量")
    status: Optional[VersionStatusEnum] = Field(default=None, description="狀態篩選")
    search: Optional[str] = Field(
        default=None, max_length=100, description="搜尋關鍵字"
    )
    sort_by: str = Field(default="version", description="排序欄位")
    sort_order: str = Field(
        default="desc", pattern="^(asc|desc)$", description="排序方向"
    )
    include_retired: bool = Field(default=False, description="是否包含已停用版本")

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        """驗證排序欄位"""
        allowed_fields = [
            "version",
            "status",
            "release_date",
            "deprecation_date",
            "retirement_date",
            "created_at",
            "updated_at",
        ]
        if v not in allowed_fields:
            raise ValueError(f'排序欄位必須是: {", ".join(allowed_fields)}')
        return v


# ==================== 響應模型 ====================


class VersionResponse(BaseModel):
    """版本響應模型"""

    version: APIVersion = Field(..., description="版本信息")
    compatibility_info: Optional[Dict[str, Any]] = Field(
        default=None, description="相容性信息"
    )
    migration_info: Optional[Dict[str, Any]] = Field(
        default=None, description="遷移信息"
    )
    permissions: Dict[str, bool] = Field(..., description="權限信息")


class VersionListResponse(BaseModel):
    """版本列表響應模型"""

    versions: List[APIVersion] = Field(..., description="版本列表")
    total: int = Field(..., description="總數量")
    page: int = Field(..., description="當前頁碼")
    page_size: int = Field(..., description="每頁數量")
    total_pages: int = Field(..., description="總頁數")
    has_next: bool = Field(..., description="是否有下一頁")
    has_prev: bool = Field(..., description="是否有上一頁")


class VersionNegotiationResponse(BaseModel):
    """版本協商響應模型"""

    selected_version: str = Field(..., description="選定版本")
    available_versions: List[str] = Field(..., description="可用版本列表")
    compatibility_warnings: List[str] = Field(
        default_factory=list, description="相容性警告"
    )
    migration_required: bool = Field(default=False, description="是否需要遷移")
    migration_url: Optional[str] = Field(default=None, description="遷移指南 URL")


class CompatibilityCheckResponse(BaseModel):
    """相容性檢查響應模型"""

    check_result: CompatibilityCheck = Field(..., description="檢查結果")
    recommendations: List[str] = Field(..., description="建議")
    migration_plan: Optional[MigrationPlan] = Field(
        default=None, description="遷移計劃"
    )
