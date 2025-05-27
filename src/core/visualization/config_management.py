"""報表視覺化配置管理模組

此模組負責管理報表視覺化的各種配置，包括：
- 圖表配置管理
- 快取管理
- 模板管理
- 用戶偏好設定
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import sessionmaker

from src.database.schema import ChartConfig, ReportCache

logger = logging.getLogger(__name__)


class ConfigManagementService:
    """配置管理服務"""

    def __init__(self, session_factory: sessionmaker):
        """初始化配置管理服務

        Args:
            session_factory: SQLAlchemy session factory
        """
        self.session_factory = session_factory
        self.cache_enabled = True
        self.default_cache_duration = 300  # 5分鐘
        self.default_chart_config = {
            "plotly": {
                "template": "plotly_white",
                "height": 400,
                "showlegend": True,
            },
            "matplotlib": {
                "style": "seaborn-v0_8",
                "figsize": (12, 6),
                "dpi": 100,
            },
        }

    def save_chart_config(
        self,
        config_name: str,
        chart_type: str,
        config_data: Dict[str, Any],
        user_id: str = "system",
        description: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """保存圖表配置

        Args:
            config_name: 配置名稱
            chart_type: 圖表類型
            config_data: 配置數據
            user_id: 用戶ID
            description: 配置描述

        Returns:
            (成功標誌, 訊息)
        """
        try:
            with self.session_factory() as session:
                # 檢查是否已存在同名配置
                existing_config = (
                    session.query(ChartConfig)
                    .filter(
                        and_(
                            ChartConfig.config_name == config_name,
                            ChartConfig.created_by == user_id,
                        )
                    )
                    .first()
                )

                if existing_config:
                    # 更新現有配置
                    existing_config.chart_type = chart_type
                    existing_config.config_data = json.dumps(config_data)
                    existing_config.description = description
                    existing_config.updated_at = datetime.now()
                    message = f"圖表配置 '{config_name}' 已更新"
                else:
                    # 創建新配置
                    new_config = ChartConfig(
                        config_name=config_name,
                        chart_type=chart_type,
                        config_data=json.dumps(config_data),
                        description=description,
                        created_by=user_id,
                        created_at=datetime.now(),
                        is_active=True,
                    )
                    session.add(new_config)
                    message = f"圖表配置 '{config_name}' 已保存"

                session.commit()
                return True, message

        except Exception as e:
            logger.error("保存圖表配置失敗: %s", e)
            return False, f"保存配置失敗: {e}"

    def get_chart_configs(
        self,
        chart_type: Optional[str] = None,
        user_id: Optional[str] = None,
        include_system: bool = True,
    ) -> List[Dict[str, Any]]:
        """獲取圖表配置列表

        Args:
            chart_type: 圖表類型篩選
            user_id: 用戶ID篩選
            include_system: 是否包含系統配置

        Returns:
            配置列表
        """
        try:
            with self.session_factory() as session:
                query = session.query(ChartConfig).filter(
                    ChartConfig.is_active.is_(True)
                )

                if chart_type:
                    query = query.filter(ChartConfig.chart_type == chart_type)

                if user_id and not include_system:
                    query = query.filter(ChartConfig.created_by == user_id)
                elif user_id and include_system:
                    query = query.filter(
                        ChartConfig.created_by.in_([user_id, "system"])
                    )

                configs = query.order_by(ChartConfig.created_at.desc()).all()

                result = []
                for config in configs:
                    try:
                        config_data = json.loads(config.config_data)
                    except (json.JSONDecodeError, TypeError):
                        config_data = {}

                    result.append(
                        {
                            "config_id": config.config_id,
                            "config_name": config.config_name,
                            "chart_type": config.chart_type,
                            "config_data": config_data,
                            "description": config.description,
                            "created_by": config.created_by,
                            "created_at": config.created_at.isoformat(),
                            "usage_count": config.usage_count or 0,
                        }
                    )

                return result

        except Exception as e:
            logger.error("獲取圖表配置失敗: %s", e)
            return []

    def delete_chart_config(
        self, config_id: str, user_id: str
    ) -> Tuple[bool, str]:
        """刪除圖表配置

        Args:
            config_id: 配置ID
            user_id: 用戶ID

        Returns:
            (成功標誌, 訊息)
        """
        try:
            with self.session_factory() as session:
                config = (
                    session.query(ChartConfig)
                    .filter(
                        and_(
                            ChartConfig.config_id == config_id,
                            ChartConfig.created_by == user_id,
                        )
                    )
                    .first()
                )

                if not config:
                    return False, "配置不存在或無權限刪除"

                config.is_active = False
                config.updated_at = datetime.now()
                session.commit()

                return True, f"配置 '{config.config_name}' 已刪除"

        except Exception as e:
            logger.error("刪除圖表配置失敗: %s", e)
            return False, f"刪除配置失敗: {e}"

    def increment_config_usage(self, config_id: str):
        """增加配置使用次數

        Args:
            config_id: 配置ID
        """
        try:
            with self.session_factory() as session:
                config = (
                    session.query(ChartConfig)
                    .filter(ChartConfig.config_id == config_id)
                    .first()
                )

                if config:
                    config.usage_count = (config.usage_count or 0) + 1
                    session.commit()

        except Exception as e:
            logger.error("更新配置使用次數失敗: %s", e)

    def get_cache_entry(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """獲取快取條目

        Args:
            cache_key: 快取鍵

        Returns:
            快取數據或 None
        """
        if not self.cache_enabled:
            return None

        try:
            with self.session_factory() as session:
                cache_entry = (
                    session.query(ReportCache)
                    .filter(
                        and_(
                            ReportCache.cache_key == cache_key,
                            ReportCache.expires_at > datetime.now(),
                        )
                    )
                    .first()
                )

                if cache_entry:
                    try:
                        return json.loads(cache_entry.cache_data)
                    except (json.JSONDecodeError, TypeError):
                        return None

                return None

        except Exception as e:
            logger.error("獲取快取條目失敗: %s", e)
            return None

    def set_cache_entry(
        self,
        cache_key: str,
        cache_data: Dict[str, Any],
        duration_seconds: Optional[int] = None,
    ) -> bool:
        """設置快取條目

        Args:
            cache_key: 快取鍵
            cache_data: 快取數據
            duration_seconds: 快取持續時間（秒）

        Returns:
            成功標誌
        """
        if not self.cache_enabled:
            return False

        try:
            duration = duration_seconds or self.default_cache_duration
            expires_at = datetime.now() + timedelta(seconds=duration)

            with self.session_factory() as session:
                # 檢查是否已存在
                existing_entry = (
                    session.query(ReportCache)
                    .filter(ReportCache.cache_key == cache_key)
                    .first()
                )

                if existing_entry:
                    # 更新現有條目
                    existing_entry.cache_data = json.dumps(cache_data, default=str)
                    existing_entry.expires_at = expires_at
                    existing_entry.updated_at = datetime.now()
                else:
                    # 創建新條目
                    new_entry = ReportCache(
                        cache_key=cache_key,
                        cache_data=json.dumps(cache_data, default=str),
                        expires_at=expires_at,
                        created_at=datetime.now(),
                    )
                    session.add(new_entry)

                session.commit()
                return True

        except Exception as e:
            logger.error("設置快取條目失敗: %s", e)
            return False

    def cleanup_cache(self, max_age_hours: int = 24) -> Tuple[bool, str]:
        """清理過期快取

        Args:
            max_age_hours: 最大保留時間（小時）

        Returns:
            (成功標誌, 訊息)
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

            with self.session_factory() as session:
                deleted_count = (
                    session.query(ReportCache)
                    .filter(ReportCache.expires_at < cutoff_time)
                    .delete()
                )
                session.commit()

                return True, f"已清理 {deleted_count} 個過期快取條目"

        except Exception as e:
            logger.error("清理快取失敗: %s", e)
            return False, f"清理快取失敗: {e}"

    def get_default_config(self, chart_type: str) -> Dict[str, Any]:
        """獲取預設配置

        Args:
            chart_type: 圖表類型

        Returns:
            預設配置
        """
        return self.default_chart_config.get(chart_type, {})

    def update_default_config(
        self, chart_type: str, config_data: Dict[str, Any]
    ) -> bool:
        """更新預設配置

        Args:
            chart_type: 圖表類型
            config_data: 配置數據

        Returns:
            成功標誌
        """
        try:
            self.default_chart_config[chart_type] = config_data
            return True
        except Exception as e:
            logger.error("更新預設配置失敗: %s", e)
            return False

    def export_configs(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """匯出配置

        Args:
            user_id: 用戶ID（None 表示匯出所有）

        Returns:
            配置數據
        """
        try:
            configs = self.get_chart_configs(user_id=user_id)
            return {
                "configs": configs,
                "default_configs": self.default_chart_config,
                "export_time": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error("匯出配置失敗: %s", e)
            return {}

    def import_configs(
        self, config_data: Dict[str, Any], user_id: str
    ) -> Tuple[bool, str]:
        """匯入配置

        Args:
            config_data: 配置數據
            user_id: 用戶ID

        Returns:
            (成功標誌, 訊息)
        """
        try:
            imported_count = 0

            if "configs" in config_data:
                for config in config_data["configs"]:
                    success, _ = self.save_chart_config(
                        config_name=config["config_name"],
                        chart_type=config["chart_type"],
                        config_data=config["config_data"],
                        user_id=user_id,
                        description=config.get("description"),
                    )
                    if success:
                        imported_count += 1

            return True, f"成功匯入 {imported_count} 個配置"

        except Exception as e:
            logger.error("匯入配置失敗: %s", e)
            return False, f"匯入配置失敗: {e}"
