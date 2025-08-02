# -*- coding: utf-8 -*-
"""
整合配置管理器

此模組提供統一的配置管理功能，
管理整合系統的所有配置參數和設置。

主要功能：
- 配置文件管理
- 環境變量處理
- 配置驗證和校驗
- 動態配置更新
- 配置備份和恢復

配置層次：
- 默認配置
- 文件配置
- 環境變量配置
- 運行時配置
"""

import logging
import os
import json
import yaml
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import copy

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """數據庫配置"""
    host: str = "localhost"
    port: int = 5432
    database: str = "quant_trading"
    username: str = "postgres"
    password: str = ""
    pool_size: int = 10
    timeout: int = 30


@dataclass
class RedisConfig:
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: str = ""
    timeout: int = 10


@dataclass
class LoggingConfig:
    """日誌配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    console_output: bool = True


@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: str = ""
    jwt_expiration: int = 3600
    password_min_length: int = 8
    max_login_attempts: int = 5
    session_timeout: int = 1800


@dataclass
class PerformanceConfig:
    """性能配置"""
    max_workers: int = 4
    request_timeout: int = 30
    cache_ttl: int = 3600
    batch_size: int = 100
    memory_limit: int = 1024 * 1024 * 1024  # 1GB


class IntegrationConfigManager:
    """
    整合配置管理器
    
    統一管理整合系統的所有配置
    """
    
    def __init__(self, base_config=None):
        """
        初始化配置管理器
        
        Args:
            base_config: 基礎配置對象
        """
        self.base_config = base_config
        
        # 配置存儲
        self.config_data: Dict[str, Any] = {}
        self.config_sources: Dict[str, str] = {}  # 記錄配置來源
        
        # 配置文件路徑
        self.config_dir = Path("config")
        self.config_file = self.config_dir / "integration_config.yaml"
        self.env_file = self.config_dir / ".env"
        
        # 配置模式
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # 初始化配置
        self._initialize_config()
        
        logger.info(f"配置管理器初始化完成，環境: {self.environment}")
    
    def _initialize_config(self):
        """初始化配置"""
        try:
            # 加載默認配置
            self._load_default_config()
            
            # 加載文件配置
            self._load_file_config()
            
            # 加載環境變量配置
            self._load_env_config()
            
            # 驗證配置
            self._validate_config()
            
            logger.info("配置初始化完成")
            
        except Exception as e:
            logger.error(f"配置初始化失敗: {e}")
            raise
    
    def _load_default_config(self):
        """加載默認配置"""
        try:
            default_config = {
                # 基礎配置
                "app": {
                    "name": "AI量化交易系統",
                    "version": "1.0.0",
                    "debug": False,
                    "environment": self.environment
                },
                
                # 整合配置
                "integration": {
                    "legacy_project_path": "ai_quant_trade-0.0.1",
                    "legacy_project_enabled": True,
                    "multi_agent_enabled": True,
                    "llm_strategy_enabled": True,
                    "reinforcement_learning_enabled": True,
                    "knowledge_system_enabled": True,
                    "data_sources_enabled": True,
                    "integration_mode": "full",
                    "compatibility_mode": True,
                    "auto_migration": False
                },
                
                # 數據庫配置
                "database": asdict(DatabaseConfig()),
                
                # Redis配置
                "redis": asdict(RedisConfig()),
                
                # 日誌配置
                "logging": asdict(LoggingConfig()),
                
                # 安全配置
                "security": asdict(SecurityConfig()),
                
                # 性能配置
                "performance": asdict(PerformanceConfig()),
                
                # 代理配置
                "agents": {
                    "max_agents": 10,
                    "decision_timeout": 30,
                    "coordination_method": "weighted_voting",
                    "performance_tracking": True,
                    "default_weight": 1.0
                },
                
                # 數據源配置
                "data_sources": {
                    "primary_source": "yahoo",
                    "backup_sources": ["twse", "qstock"],
                    "cache_enabled": True,
                    "cache_ttl": 3600,
                    "health_check_interval": 60
                },
                
                # 知識庫配置
                "knowledge_base": {
                    "index_file": "docs/knowledge/knowledge_index.json",
                    "cache_dir": "cache/knowledge",
                    "scan_interval": 86400,  # 24小時
                    "auto_scan": True
                },
                
                # 學習系統配置
                "learning_system": {
                    "progress_tracking": True,
                    "achievement_system": True,
                    "recommendation_engine": True,
                    "analytics_enabled": True
                }
            }
            
            self._merge_config(default_config, "default")
            logger.info("默認配置加載完成")
            
        except Exception as e:
            logger.error(f"默認配置加載失敗: {e}")
            raise
    
    def _load_file_config(self):
        """加載文件配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f)
                
                if file_config:
                    self._merge_config(file_config, "file")
                    logger.info(f"文件配置加載完成: {self.config_file}")
            else:
                logger.info(f"配置文件不存在: {self.config_file}")
                
        except Exception as e:
            logger.error(f"文件配置加載失敗: {e}")
    
    def _load_env_config(self):
        """加載環境變量配置"""
        try:
            # 加載.env文件
            if self.env_file.exists():
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            os.environ[key] = value
            
            # 處理環境變量
            env_config = {}
            
            # 數據庫配置
            if os.getenv("DB_HOST"):
                env_config.setdefault("database", {})["host"] = os.getenv("DB_HOST")
            if os.getenv("DB_PORT"):
                env_config.setdefault("database", {})["port"] = int(os.getenv("DB_PORT"))
            if os.getenv("DB_NAME"):
                env_config.setdefault("database", {})["database"] = os.getenv("DB_NAME")
            if os.getenv("DB_USER"):
                env_config.setdefault("database", {})["username"] = os.getenv("DB_USER")
            if os.getenv("DB_PASSWORD"):
                env_config.setdefault("database", {})["password"] = os.getenv("DB_PASSWORD")
            
            # Redis配置
            if os.getenv("REDIS_HOST"):
                env_config.setdefault("redis", {})["host"] = os.getenv("REDIS_HOST")
            if os.getenv("REDIS_PORT"):
                env_config.setdefault("redis", {})["port"] = int(os.getenv("REDIS_PORT"))
            if os.getenv("REDIS_PASSWORD"):
                env_config.setdefault("redis", {})["password"] = os.getenv("REDIS_PASSWORD")
            
            # 安全配置
            if os.getenv("SECRET_KEY"):
                env_config.setdefault("security", {})["secret_key"] = os.getenv("SECRET_KEY")
            
            # 日誌配置
            if os.getenv("LOG_LEVEL"):
                env_config.setdefault("logging", {})["level"] = os.getenv("LOG_LEVEL")
            if os.getenv("LOG_FILE"):
                env_config.setdefault("logging", {})["file_path"] = os.getenv("LOG_FILE")
            
            if env_config:
                self._merge_config(env_config, "environment")
                logger.info("環境變量配置加載完成")
                
        except Exception as e:
            logger.error(f"環境變量配置加載失敗: {e}")
    
    def _merge_config(self, new_config: Dict[str, Any], source: str):
        """合併配置"""
        try:
            def deep_merge(base_dict: Dict, update_dict: Dict, path: str = ""):
                for key, value in update_dict.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                        deep_merge(base_dict[key], value, current_path)
                    else:
                        base_dict[key] = value
                        self.config_sources[current_path] = source
            
            deep_merge(self.config_data, new_config)
            
        except Exception as e:
            logger.error(f"配置合併失敗: {e}")
            raise
    
    def _validate_config(self):
        """驗證配置"""
        try:
            # 驗證必需配置
            required_configs = [
                "app.name",
                "integration.legacy_project_path",
                "database.host",
                "logging.level"
            ]
            
            missing_configs = []
            for config_path in required_configs:
                if not self.get(config_path):
                    missing_configs.append(config_path)
            
            if missing_configs:
                raise ValueError(f"缺少必需配置: {missing_configs}")
            
            # 驗證配置值
            self._validate_config_values()
            
            logger.info("配置驗證通過")
            
        except Exception as e:
            logger.error(f"配置驗證失敗: {e}")
            raise
    
    def _validate_config_values(self):
        """驗證配置值"""
        try:
            # 驗證端口號
            db_port = self.get("database.port")
            if not (1 <= db_port <= 65535):
                raise ValueError(f"無效的數據庫端口: {db_port}")
            
            redis_port = self.get("redis.port")
            if not (1 <= redis_port <= 65535):
                raise ValueError(f"無效的Redis端口: {redis_port}")
            
            # 驗證日誌級別
            log_level = self.get("logging.level")
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if log_level not in valid_levels:
                raise ValueError(f"無效的日誌級別: {log_level}")
            
            # 驗證環境
            environment = self.get("app.environment")
            valid_environments = ["development", "testing", "staging", "production"]
            if environment not in valid_environments:
                raise ValueError(f"無效的環境: {environment}")
            
        except Exception as e:
            logger.error(f"配置值驗證失敗: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        獲取配置值
        
        Args:
            key: 配置鍵（支持點號分隔的路徑）
            default: 默認值
            
        Returns:
            配置值
        """
        try:
            keys = key.split('.')
            value = self.config_data
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception as e:
            logger.error(f"獲取配置失敗 {key}: {e}")
            return default
    
    def set(self, key: str, value: Any, source: str = "runtime"):
        """
        設置配置值
        
        Args:
            key: 配置鍵
            value: 配置值
            source: 配置來源
        """
        try:
            keys = key.split('.')
            config = self.config_data
            
            # 導航到父級字典
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # 設置值
            config[keys[-1]] = value
            self.config_sources[key] = source
            
            logger.debug(f"配置已設置: {key} = {value}")
            
        except Exception as e:
            logger.error(f"設置配置失敗 {key}: {e}")
            raise
    
    def get_all(self) -> Dict[str, Any]:
        """獲取所有配置"""
        return copy.deepcopy(self.config_data)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """獲取配置段"""
        return self.get(section, {})
    
    def save_config(self, file_path: Optional[str] = None):
        """保存配置到文件"""
        try:
            save_path = Path(file_path) if file_path else self.config_file
            
            # 確保目錄存在
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存配置
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config_data, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"配置已保存到: {save_path}")
            
        except Exception as e:
            logger.error(f"保存配置失敗: {e}")
            raise
    
    def reload_config(self):
        """重新加載配置"""
        try:
            logger.info("重新加載配置...")
            
            # 清空當前配置
            self.config_data.clear()
            self.config_sources.clear()
            
            # 重新初始化
            self._initialize_config()
            
            logger.info("配置重新加載完成")
            
        except Exception as e:
            logger.error(f"配置重新加載失敗: {e}")
            raise
    
    def get_config_info(self) -> Dict[str, Any]:
        """獲取配置信息"""
        try:
            return {
                "environment": self.environment,
                "config_file": str(self.config_file),
                "config_exists": self.config_file.exists(),
                "total_configs": len(self.config_sources),
                "sources": {
                    source: len([k for k, s in self.config_sources.items() if s == source])
                    for source in set(self.config_sources.values())
                }
            }
            
        except Exception as e:
            logger.error(f"獲取配置信息失敗: {e}")
            return {}
    
    def validate_runtime_config(self) -> List[str]:
        """驗證運行時配置"""
        try:
            issues = []
            
            # 檢查原始項目路徑
            legacy_path = Path(self.get("integration.legacy_project_path"))
            if not legacy_path.exists():
                issues.append(f"原始項目路徑不存在: {legacy_path}")
            
            # 檢查必需目錄
            required_dirs = ["config", "logs", "cache"]
            for dir_name in required_dirs:
                dir_path = Path(dir_name)
                if not dir_path.exists():
                    issues.append(f"必需目錄不存在: {dir_path}")
            
            # 檢查數據庫連接（如果啟用）
            if self.get("database.host") != "localhost":
                # 這裡可以添加實際的數據庫連接測試
                pass
            
            return issues
            
        except Exception as e:
            logger.error(f"運行時配置驗證失敗: {e}")
            return [f"驗證失敗: {str(e)}"]
