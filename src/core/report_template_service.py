"""
報表模板服務層

此模組實現報表模板管理的業務邏輯，包括模板的創建、查詢、更新、刪除、
版本控制、權限管理和預覽功能。
"""

import logging
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import pandas as pd

# 導入資料庫相關模組
from sqlalchemy import create_engine, desc, func, and_, or_, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

# 導入配置
from src.config import DB_URL, CACHE_DIR

# 導入模型
from src.api.models.reports import (
    ReportTemplate,
    ReportTemplateCreateRequest,
    ReportTemplateUpdateRequest,
    ReportTemplateListRequest,
    TemplateStatusEnum,
    TemplateVisibilityEnum,
    ReportTypeEnum,
)

logger = logging.getLogger(__name__)


class ReportTemplateService:
    """
    報表模板服務

    提供完整的報表模板管理功能，包括模板的 CRUD 操作、
    版本控制、權限管理和預覽功能。
    """

    def __init__(self):
        """初始化報表模板服務"""
        try:
            # 初始化資料庫連接
            self.engine = create_engine(DB_URL)
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("報表模板服務資料庫連接初始化成功")

            # 初始化快取設定
            self.cache_enabled = True
            self.cache_ttl = 300  # 5分鐘

            # 確保快取目錄存在
            Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

            logger.info("報表模板服務初始化完成")

        except Exception as e:
            logger.error(f"報表模板服務初始化失敗: {e}")
            raise

    def create_template(
        self, request: ReportTemplateCreateRequest, created_by: str
    ) -> Dict[str, Any]:
        """創建報表模板"""
        try:
            template_id = str(uuid.uuid4())
            current_time = datetime.now()

            # 構建模板數據
            template_data = {
                "template_id": template_id,
                "name": request.name,
                "description": request.description,
                "report_type": request.report_type.value,
                "template_config": request.template_config,
                "parameters": request.parameters,
                "chart_configs": request.chart_configs,
                "layout_config": request.layout_config,
                "status": TemplateStatusEnum.ACTIVE.value,
                "visibility": request.visibility.value,
                "tags": request.tags or [],
                "version": "1.0.0",
                "usage_count": 0,
                "created_by": created_by,
                "created_at": current_time,
                "updated_at": current_time,
                "last_used_at": None,
            }

            # 驗證模板配置
            self._validate_template_config(request.template_config, request.report_type)

            # 模擬資料庫保存（實際應使用 ORM）
            logger.info(f"創建報表模板: {template_id}, 名稱: {request.name}")

            return {
                "template": ReportTemplate(**template_data).dict(),
                "preview_data": self._generate_preview_data(template_data),
                "permissions": {
                    "can_edit": True,
                    "can_delete": True,
                    "can_share": True,
                    "can_export": True,
                },
            }

        except Exception as e:
            logger.error(f"創建報表模板失敗: {e}")
            raise

    def get_template(self, template_id: str, user_id: str) -> Dict[str, Any]:
        """獲取單個報表模板"""
        try:
            # 模擬從資料庫查詢
            template_data = self._get_mock_template_data(template_id)

            if not template_data:
                raise ValueError(f"模板不存在: {template_id}")

            # 檢查權限
            permissions = self._check_template_permissions(template_data, user_id)

            # 更新最後使用時間
            template_data["last_used_at"] = datetime.now()
            template_data["usage_count"] += 1

            return {
                "template": ReportTemplate(**template_data).dict(),
                "preview_data": self._generate_preview_data(template_data),
                "permissions": permissions,
            }

        except Exception as e:
            logger.error(f"獲取報表模板失敗: {e}")
            raise

    def list_templates(
        self, request: ReportTemplateListRequest, user_id: str
    ) -> Dict[str, Any]:
        """查詢報表模板列表"""
        try:
            # 模擬查詢邏輯
            all_templates = self._get_mock_templates_list()

            # 應用篩選條件
            filtered_templates = self._apply_filters(all_templates, request, user_id)

            # 應用排序
            sorted_templates = self._apply_sorting(filtered_templates, request)

            # 應用分頁
            total = len(sorted_templates)
            start_idx = (request.page - 1) * request.page_size
            end_idx = start_idx + request.page_size
            paginated_templates = sorted_templates[start_idx:end_idx]

            # 計算分頁信息
            total_pages = (total + request.page_size - 1) // request.page_size
            has_next = request.page < total_pages
            has_prev = request.page > 1

            return {
                "templates": [ReportTemplate(**t).dict() for t in paginated_templates],
                "total": total,
                "page": request.page,
                "page_size": request.page_size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
            }

        except Exception as e:
            logger.error(f"查詢報表模板列表失敗: {e}")
            raise

    def update_template(
        self, template_id: str, request: ReportTemplateUpdateRequest, user_id: str
    ) -> Dict[str, Any]:
        """更新報表模板"""
        try:
            # 獲取現有模板
            template_data = self._get_mock_template_data(template_id)

            if not template_data:
                raise ValueError(f"模板不存在: {template_id}")

            # 檢查權限
            permissions = self._check_template_permissions(template_data, user_id)
            if not permissions.get("can_edit", False):
                raise PermissionError("無權限編輯此模板")

            # 更新欄位
            update_fields = request.dict(exclude_unset=True)
            for field, value in update_fields.items():
                if field in template_data:
                    template_data[field] = value

            # 更新時間和版本
            template_data["updated_at"] = datetime.now()
            template_data["version"] = self._increment_version(template_data["version"])

            # 驗證更新後的配置
            if "template_config" in update_fields:
                report_type = ReportTypeEnum(template_data["report_type"])
                self._validate_template_config(
                    template_data["template_config"], report_type
                )

            logger.info(f"更新報表模板: {template_id}")

            return {
                "template": ReportTemplate(**template_data).dict(),
                "preview_data": self._generate_preview_data(template_data),
                "permissions": permissions,
            }

        except Exception as e:
            logger.error(f"更新報表模板失敗: {e}")
            raise

    def delete_template(self, template_id: str, user_id: str) -> bool:
        """刪除報表模板"""
        try:
            # 獲取現有模板
            template_data = self._get_mock_template_data(template_id)

            if not template_data:
                raise ValueError(f"模板不存在: {template_id}")

            # 檢查權限
            permissions = self._check_template_permissions(template_data, user_id)
            if not permissions.get("can_delete", False):
                raise PermissionError("無權限刪除此模板")

            # 軟刪除：更新狀態為 ARCHIVED
            template_data["status"] = TemplateStatusEnum.ARCHIVED.value
            template_data["updated_at"] = datetime.now()

            logger.info(f"刪除報表模板: {template_id}")
            return True

        except Exception as e:
            logger.error(f"刪除報表模板失敗: {e}")
            raise

    def preview_template(
        self,
        template_id: str,
        preview_data: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """預覽報表模板"""
        try:
            # 獲取模板
            template_data = self._get_mock_template_data(template_id)

            if not template_data:
                raise ValueError(f"模板不存在: {template_id}")

            # 合併參數
            merged_params = template_data["parameters"].copy()
            if parameters:
                merged_params.update(parameters)

            # 生成預覽數據
            preview_html = self._generate_preview_html(
                template_data, preview_data, merged_params
            )
            charts = self._generate_preview_charts(
                template_data, preview_data, merged_params
            )

            return {
                "template_id": template_id,
                "preview_html": preview_html,
                "charts": charts,
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "parameters_used": merged_params,
                    "template_version": template_data["version"],
                },
            }

        except Exception as e:
            logger.error(f"預覽報表模板失敗: {e}")
            raise

    # ==================== 私有方法 ====================

    def _validate_template_config(
        self, config: Dict[str, Any], report_type: ReportTypeEnum
    ):
        """驗證模板配置"""
        required_fields = {
            ReportTypeEnum.TRADING_SUMMARY: ["metrics", "time_range"],
            ReportTypeEnum.PORTFOLIO_PERFORMANCE: ["portfolios", "benchmark"],
            ReportTypeEnum.RISK_ANALYSIS: ["risk_types", "confidence_levels"],
            ReportTypeEnum.STRATEGY_BACKTEST: ["strategies", "period"],
            ReportTypeEnum.SYSTEM_MONITORING: ["metric_types", "alerts"],
            ReportTypeEnum.CUSTOM: ["data_sources", "metrics"],
        }

        if report_type in required_fields:
            for field in required_fields[report_type]:
                if field not in config:
                    raise ValueError(f"模板配置缺少必要欄位: {field}")

    def _get_mock_template_data(self, template_id: str) -> Optional[Dict[str, Any]]:
        """獲取模擬模板數據"""
        # 模擬數據，實際應從資料庫查詢
        mock_templates = {
            "template_001": {
                "template_id": "template_001",
                "name": "交易摘要報表模板",
                "description": "標準交易摘要報表模板",
                "report_type": "trading_summary",
                "template_config": {
                    "metrics": ["total_pnl", "win_rate", "sharpe_ratio"],
                    "time_range": "monthly",
                    "grouping": ["symbol", "strategy"],
                },
                "parameters": {
                    "default_period": 30,
                    "currency": "TWD",
                    "include_commission": True,
                },
                "chart_configs": [
                    {
                        "type": "line",
                        "title": "累積損益",
                        "data_source": "cumulative_pnl",
                    },
                    {
                        "type": "bar",
                        "title": "月度收益",
                        "data_source": "monthly_returns",
                    },
                ],
                "layout_config": {
                    "columns": 2,
                    "chart_height": 400,
                    "show_summary": True,
                },
                "status": "active",
                "visibility": "public",
                "tags": ["交易", "摘要", "標準"],
                "version": "1.2.0",
                "usage_count": 25,
                "created_by": "admin",
                "created_at": datetime.now() - timedelta(days=30),
                "updated_at": datetime.now() - timedelta(days=5),
                "last_used_at": datetime.now() - timedelta(hours=2),
            }
        }

        return mock_templates.get(template_id)

    def _get_mock_templates_list(self) -> List[Dict[str, Any]]:
        """獲取模擬模板列表"""
        return [
            {
                "template_id": "template_001",
                "name": "交易摘要報表模板",
                "description": "標準交易摘要報表模板",
                "report_type": "trading_summary",
                "template_config": {"metrics": ["total_pnl", "win_rate"]},
                "parameters": {"default_period": 30},
                "chart_configs": None,
                "layout_config": None,
                "status": "active",
                "visibility": "public",
                "tags": ["交易", "摘要"],
                "version": "1.2.0",
                "usage_count": 25,
                "created_by": "admin",
                "created_at": datetime.now() - timedelta(days=30),
                "updated_at": datetime.now() - timedelta(days=5),
                "last_used_at": datetime.now() - timedelta(hours=2),
            },
            {
                "template_id": "template_002",
                "name": "投資組合績效模板",
                "description": "投資組合績效分析模板",
                "report_type": "portfolio_performance",
                "template_config": {"portfolios": ["all"], "benchmark": "^TWII"},
                "parameters": {"include_risk": True},
                "chart_configs": None,
                "layout_config": None,
                "status": "active",
                "visibility": "private",
                "tags": ["投資組合", "績效"],
                "version": "1.0.0",
                "usage_count": 12,
                "created_by": "user_001",
                "created_at": datetime.now() - timedelta(days=15),
                "updated_at": datetime.now() - timedelta(days=3),
                "last_used_at": datetime.now() - timedelta(hours=6),
            },
            {
                "template_id": "template_003",
                "name": "風險分析報表模板",
                "description": "全面的風險分析報表",
                "report_type": "risk_analysis",
                "template_config": {
                    "risk_types": ["market", "credit"],
                    "confidence_levels": [0.95, 0.99],
                },
                "parameters": {"include_stress_test": False},
                "chart_configs": None,
                "layout_config": None,
                "status": "draft",
                "visibility": "private",
                "tags": ["風險", "分析"],
                "version": "0.9.0",
                "usage_count": 3,
                "created_by": "user_002",
                "created_at": datetime.now() - timedelta(days=7),
                "updated_at": datetime.now() - timedelta(days=1),
                "last_used_at": datetime.now() - timedelta(hours=12),
            },
        ]

    def _apply_filters(
        self,
        templates: List[Dict[str, Any]],
        request: ReportTemplateListRequest,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """應用篩選條件"""
        filtered = templates

        # 搜尋關鍵字
        if request.search:
            search_lower = request.search.lower()
            filtered = [
                t
                for t in filtered
                if search_lower in t["name"].lower()
                or (t["description"] and search_lower in t["description"].lower())
                or any(search_lower in tag.lower() for tag in t.get("tags", []))
            ]

        # 報表類型篩選
        if request.report_type:
            filtered = [
                t for t in filtered if t["report_type"] == request.report_type.value
            ]

        # 狀態篩選
        if request.status:
            filtered = [t for t in filtered if t["status"] == request.status.value]

        # 可見性篩選
        if request.visibility:
            filtered = [
                t for t in filtered if t["visibility"] == request.visibility.value
            ]

        # 標籤篩選
        if request.tags:
            filtered = [
                t
                for t in filtered
                if any(tag in t.get("tags", []) for tag in request.tags)
            ]

        # 權限篩選（只顯示用戶有權限查看的模板）
        filtered = [
            t
            for t in filtered
            if t["visibility"] == "public" or t["created_by"] == user_id
        ]

        return filtered

    def _apply_sorting(
        self, templates: List[Dict[str, Any]], request: ReportTemplateListRequest
    ) -> List[Dict[str, Any]]:
        """應用排序"""
        reverse = request.sort_order == "desc"

        if request.sort_by == "name":
            return sorted(templates, key=lambda x: x["name"], reverse=reverse)
        elif request.sort_by == "created_at":
            return sorted(templates, key=lambda x: x["created_at"], reverse=reverse)
        elif request.sort_by == "updated_at":
            return sorted(templates, key=lambda x: x["updated_at"], reverse=reverse)
        elif request.sort_by == "usage_count":
            return sorted(templates, key=lambda x: x["usage_count"], reverse=reverse)
        else:
            return sorted(templates, key=lambda x: x["created_at"], reverse=reverse)

    def _check_template_permissions(
        self, template_data: Dict[str, Any], user_id: str
    ) -> Dict[str, bool]:
        """檢查模板權限"""
        is_owner = template_data["created_by"] == user_id
        is_public = template_data["visibility"] == "public"

        return {
            "can_view": is_public or is_owner,
            "can_edit": is_owner,
            "can_delete": is_owner,
            "can_share": is_owner or is_public,
            "can_export": True,  # 所有用戶都可以匯出
        }

    def _increment_version(self, current_version: str) -> str:
        """遞增版本號"""
        try:
            parts = current_version.split(".")
            if len(parts) == 3:
                major, minor, patch = map(int, parts)
                return f"{major}.{minor}.{patch + 1}"
            else:
                return "1.0.1"
        except:
            return "1.0.1"

    def _generate_preview_data(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成預覽數據"""
        return {
            "sample_metrics": {
                "total_pnl": 125000.0,
                "win_rate": 65.5,
                "total_trades": 150,
                "sharpe_ratio": 1.25,
            },
            "sample_charts": [
                {"type": "line", "title": "累積損益曲線"},
                {"type": "bar", "title": "月度收益分布"},
            ],
            "data_points": 100,
            "last_updated": datetime.now().isoformat(),
        }

    def _generate_preview_html(
        self,
        template_data: Dict[str, Any],
        preview_data: Optional[Dict[str, Any]],
        parameters: Dict[str, Any],
    ) -> str:
        """生成預覽 HTML"""
        return f"""
        <div class="report-preview">
            <h2>{template_data['name']}</h2>
            <p>{template_data['description']}</p>
            <div class="metrics-summary">
                <div class="metric">
                    <span class="label">總損益:</span>
                    <span class="value">$125,000</span>
                </div>
                <div class="metric">
                    <span class="label">勝率:</span>
                    <span class="value">65.5%</span>
                </div>
            </div>
            <div class="charts-placeholder">
                <p>圖表將在此處顯示</p>
            </div>
        </div>
        """

    def _generate_preview_charts(
        self,
        template_data: Dict[str, Any],
        preview_data: Optional[Dict[str, Any]],
        parameters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """生成預覽圖表"""
        return [
            {
                "chart_type": "line",
                "library": "plotly",
                "data": {
                    "x": ["2024-01", "2024-02", "2024-03"],
                    "y": [10000, 15000, 12000],
                    "type": "scatter",
                    "mode": "lines",
                    "name": "累積損益",
                },
                "config": {
                    "title": "累積損益曲線",
                    "xaxis": {"title": "時間"},
                    "yaxis": {"title": "損益"},
                },
            }
        ]
