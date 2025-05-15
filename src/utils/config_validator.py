"""
配置驗證模組

此模組提供配置驗證功能，確保必要的配置項存在且有效。
"""

import os
import sys
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union


class ConfigSeverity(Enum):
    """配置嚴重性級別"""

    ERROR = "ERROR"  # 錯誤：缺少此配置將導致系統無法運行
    WARNING = "WARNING"  # 警告：缺少此配置可能導致部分功能無法使用
    INFO = "INFO"  # 信息：提供有關配置的信息


class ConfigValidationResult:
    """配置驗證結果"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.infos: List[str] = []

    def add_issue(self, message: str, severity: ConfigSeverity):
        """添加問題"""
        if severity == ConfigSeverity.ERROR:
            self.errors.append(message)
        elif severity == ConfigSeverity.WARNING:
            self.warnings.append(message)
        elif severity == ConfigSeverity.INFO:
            self.infos.append(message)

    @property
    def has_errors(self) -> bool:
        """是否有錯誤"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0

    @property
    def has_issues(self) -> bool:
        """是否有問題"""
        return self.has_errors or self.has_warnings

    def __str__(self) -> str:
        """字符串表示"""
        result = []

        if self.errors:
            result.append("錯誤:")
            for error in self.errors:
                result.append(f"  - {error}")

        if self.warnings:
            result.append("警告:")
            for warning in self.warnings:
                result.append(f"  - {warning}")

        if self.infos:
            result.append("信息:")
            for info in self.infos:
                result.append(f"  - {info}")

        if not result:
            return "配置驗證通過，沒有發現問題。"

        return "\n".join(result)


class ConfigValidator:
    """配置驗證器"""

    def __init__(self):
        self.required_configs: List[Tuple[str, ConfigSeverity, Optional[str]]] = []

    def add_required_config(
        self,
        name: str,
        severity: ConfigSeverity = ConfigSeverity.ERROR,
        description: Optional[str] = None,
    ):
        """添加必要配置項"""
        self.required_configs.append((name, severity, description))
        return self

    def validate_env_vars(self) -> ConfigValidationResult:
        """驗證環境變數"""
        result = ConfigValidationResult()

        for name, severity, description in self.required_configs:
            value = os.environ.get(name)

            if value is None or value.strip() == "":
                message = f"缺少環境變數: {name}"
                if description:
                    message += f" - {description}"
                result.add_issue(message, severity)
            elif severity == ConfigSeverity.INFO:
                message = f"環境變數已設置: {name}"
                if description:
                    message += f" - {description}"
                result.add_issue(message, severity)

        return result

    def validate_config_dict(self, config: Dict[str, Any]) -> ConfigValidationResult:
        """驗證配置字典"""
        result = ConfigValidationResult()

        for name, severity, description in self.required_configs:
            if (
                name not in config
                or config[name] is None
                or (isinstance(config[name], str) and config[name].strip() == "")
            ):
                message = f"缺少配置項: {name}"
                if description:
                    message += f" - {description}"
                result.add_issue(message, severity)
            elif severity == ConfigSeverity.INFO:
                message = f"配置項已設置: {name}"
                if description:
                    message += f" - {description}"
                result.add_issue(message, severity)

        return result


# 預定義的驗證器
def create_core_validator() -> ConfigValidator:
    """創建核心配置驗證器"""
    validator = ConfigValidator()

    # 資料庫設定
    validator.add_required_config("DB_URL", ConfigSeverity.ERROR, "資料庫連接 URL")

    # API 設定
    validator.add_required_config("API_KEY", ConfigSeverity.ERROR, "API 金鑰")
    validator.add_required_config("API_SECRET", ConfigSeverity.ERROR, "API 密鑰")

    # 日誌設定
    validator.add_required_config("LOG_LEVEL", ConfigSeverity.WARNING, "日誌級別")

    return validator


def create_trading_validator() -> ConfigValidator:
    """創建交易配置驗證器"""
    validator = ConfigValidator()

    # 交易設定
    validator.add_required_config(
        "TRADING_HOURS_START", ConfigSeverity.WARNING, "交易開始時間"
    )
    validator.add_required_config(
        "TRADING_HOURS_END", ConfigSeverity.WARNING, "交易結束時間"
    )
    validator.add_required_config(
        "MAX_POSITION_SIZE", ConfigSeverity.WARNING, "最大持倉比例"
    )
    validator.add_required_config(
        "STOP_LOSS_THRESHOLD", ConfigSeverity.WARNING, "停損閾值"
    )

    # 券商設定
    validator.add_required_config("BROKER_NAME", ConfigSeverity.ERROR, "券商名稱")

    return validator


def create_monitoring_validator() -> ConfigValidator:
    """創建監控配置驗證器"""
    validator = ConfigValidator()

    # 監控設定
    validator.add_required_config(
        "PRICE_ANOMALY_THRESHOLD", ConfigSeverity.WARNING, "價格異常閾值"
    )
    validator.add_required_config(
        "VOLUME_ANOMALY_THRESHOLD", ConfigSeverity.WARNING, "成交量異常閾值"
    )
    validator.add_required_config("CHECK_INTERVAL", ConfigSeverity.WARNING, "檢查間隔")

    # Grafana 設定
    validator.add_required_config("GRAFANA_PORT", ConfigSeverity.INFO, "Grafana 端口")
    validator.add_required_config(
        "GRAFANA_ADMIN_USER", ConfigSeverity.INFO, "Grafana 管理員用戶名"
    )
    validator.add_required_config(
        "GRAFANA_ADMIN_PASSWORD", ConfigSeverity.INFO, "Grafana 管理員密碼"
    )

    return validator


def validate_all_configs() -> ConfigValidationResult:
    """驗證所有配置"""
    # 合併所有驗證器
    validators = [
        create_core_validator(),
        create_trading_validator(),
        create_monitoring_validator(),
    ]

    # 創建結果對象
    result = ConfigValidationResult()

    # 執行所有驗證
    for validator in validators:
        validator_result = validator.validate_env_vars()
        result.errors.extend(validator_result.errors)
        result.warnings.extend(validator_result.warnings)
        result.infos.extend(validator_result.infos)

    return result


def validate_and_exit_on_error():
    """驗證配置並在錯誤時退出"""
    result = validate_all_configs()

    if result.has_issues:
        print(str(result))

        if result.has_errors:
            print("\n錯誤: 配置驗證失敗，系統無法啟動。")
            sys.exit(1)

        if result.has_warnings:
            print("\n警告: 配置驗證發現警告，部分功能可能無法正常使用。")
    else:
        print("配置驗證通過，沒有發現問題。")
