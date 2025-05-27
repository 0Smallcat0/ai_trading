"""敏感資料遮罩模組

此模組實現了敏感資料的識別和遮罩功能，包括：
- 動態敏感資料識別
- 多種遮罩策略
- 可配置的遮罩規則
- 符合隱私保護法規的資料處理
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Union, Pattern
from enum import Enum
from dataclasses import dataclass
import hashlib
from functools import lru_cache

# 設置日誌
logger = logging.getLogger(__name__)

# 正則表達式常量
PATTERNS = {
    "API_KEY": (
        r"(?i)(api[_-]?key|apikey|access[_-]?key)\s*[:=]\s*"
        r"['\"]?([a-zA-Z0-9_-]{20,})['\"]?"
    ),
    "PASSWORD": (r"(?i)(password|passwd|pwd)\s*[:=]\s*" r"['\"]?([^'\"\s]+)['\"]?"),
    "JWT_TOKEN": (
        r"(?i)(token|jwt|bearer)\s*[:=]?\s*['\"]?"
        r"([a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)['\"]?"
    ),
    "CREDIT_CARD": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "PHONE_TW": (
        r"(?:\+?886[-\s]?)?"
        r"(?:0?9\d{8}|\(0\d{1,2}\)[-\s]?\d{7,8}|0\d{1,2}[-\s]?\d{7,8})"
    ),
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "ID_NUMBER_TW": r"\b[A-Z][12]\d{8}\b",
}


class MaskingStrategy(Enum):
    """遮罩策略"""

    FULL = "full"  # 完全遮罩
    PARTIAL = "partial"  # 部分遮罩
    HASH = "hash"  # 雜湊遮罩
    TOKENIZE = "tokenize"  # 標記化
    REDACT = "redact"  # 編輯遮罩


class SensitiveDataType(Enum):
    """敏感資料類型"""

    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    SECRET = "secret"
    CREDIT_CARD = "credit_card"
    PHONE = "phone"
    EMAIL = "email"
    ID_NUMBER = "id_number"
    BANK_ACCOUNT = "bank_account"
    ADDRESS = "address"
    NAME = "name"
    CUSTOM = "custom"


@dataclass
class MaskingRuleConfig:
    """遮罩規則配置"""

    name: str
    data_type: SensitiveDataType
    pattern: str
    strategy: MaskingStrategy
    field_names: List[str]
    description: str = ""
    enabled: bool = True
    preserve_length: bool = True
    preserve_format: bool = False
    replacement_char: str = "*"


@dataclass
class MaskingRule:
    """遮罩規則"""

    name: str
    data_type: SensitiveDataType
    pattern: Union[str, Pattern]
    strategy: MaskingStrategy
    field_names: List[str]
    description: str
    enabled: bool = True
    preserve_length: bool = True
    preserve_format: bool = False
    replacement_char: str = "*"

    def __post_init__(self):
        """初始化後處理"""
        if isinstance(self.pattern, str):
            self.pattern = re.compile(self.pattern, re.IGNORECASE)


class DataMasker:
    """資料遮罩器"""

    def __init__(self, config_file: Optional[str] = None):
        """初始化資料遮罩器。

        Args:
            config_file: 配置文件路徑
        """
        self.rules: List[MaskingRule] = []
        self.token_map: Dict[str, str] = {}
        self._compiled_patterns_cache: Dict[str, Pattern] = {}
        self._field_rule_cache: Dict[str, Optional[MaskingRule]] = {}

        # 載入預設規則
        self._load_default_rules()

        # 載入配置文件
        if config_file:
            self._load_config(config_file)

    def _load_default_rules(self):
        """載入預設遮罩規則"""
        default_rules = [
            MaskingRule(
                name="API金鑰",
                data_type=SensitiveDataType.API_KEY,
                pattern=PATTERNS["API_KEY"],
                strategy=MaskingStrategy.PARTIAL,
                field_names=["api_key", "apikey", "access_key", "key"],
                description="API金鑰遮罩",
            ),
            MaskingRule(
                name="密碼",
                data_type=SensitiveDataType.PASSWORD,
                pattern=PATTERNS["PASSWORD"],
                strategy=MaskingStrategy.FULL,
                field_names=["password", "passwd", "pwd"],
                description="密碼完全遮罩",
            ),
            MaskingRule(
                name="JWT Token",
                data_type=SensitiveDataType.TOKEN,
                pattern=PATTERNS["JWT_TOKEN"],
                strategy=MaskingStrategy.PARTIAL,
                field_names=["token", "jwt", "authorization", "bearer"],
                description="JWT Token遮罩",
            ),
            MaskingRule(
                name="信用卡號",
                data_type=SensitiveDataType.CREDIT_CARD,
                pattern=PATTERNS["CREDIT_CARD"],
                strategy=MaskingStrategy.PARTIAL,
                field_names=["credit_card", "card_number", "cc_number"],
                description="信用卡號遮罩",
                preserve_format=True,
            ),
            MaskingRule(
                name="電話號碼",
                data_type=SensitiveDataType.PHONE,
                pattern=PATTERNS["PHONE_TW"],
                strategy=MaskingStrategy.PARTIAL,
                field_names=["phone", "mobile", "telephone"],
                description="電話號碼遮罩",
                preserve_format=True,
            ),
            MaskingRule(
                name="電子郵件",
                data_type=SensitiveDataType.EMAIL,
                pattern=PATTERNS["EMAIL"],
                strategy=MaskingStrategy.PARTIAL,
                field_names=["email", "mail", "e_mail"],
                description="電子郵件遮罩",
            ),
            MaskingRule(
                name="身分證字號",
                data_type=SensitiveDataType.ID_NUMBER,
                pattern=PATTERNS["ID_NUMBER_TW"],
                strategy=MaskingStrategy.PARTIAL,
                field_names=["id_number", "national_id", "citizen_id"],
                description="身分證字號遮罩",
            ),
        ]

        self.rules.extend(default_rules)

    def _load_config(self, config_file: str):
        """載入配置文件"""
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 載入自定義規則
            if "custom_rules" in config:
                for rule_config in config["custom_rules"]:
                    rule = MaskingRule(**rule_config)
                    self.rules.append(rule)

            # 更新現有規則
            if "rule_updates" in config:
                for update in config["rule_updates"]:
                    self._update_rule(update)

        except Exception as e:
            logger.error("載入遮罩配置時發生錯誤: %s", e)

    def _update_rule(self, update: Dict[str, Any]):
        """更新規則"""
        rule_name = update.get("name")
        for rule in self.rules:
            if rule.name == rule_name:
                for key, value in update.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                break

    def mask_data(self, data: Any, context: Optional[str] = None) -> Any:
        """遮罩資料。

        Args:
            data: 要遮罩的資料
            context: 上下文信息

        Returns:
            Any: 遮罩後的資料
        """
        if isinstance(data, dict):
            return self._mask_dict(data, context)
        if isinstance(data, list):
            return self._mask_list(data, context)
        if isinstance(data, str):
            return self._mask_string(data, context)
        return data

    def _mask_dict(
        self, data: Dict[str, Any], context: Optional[str] = None
    ) -> Dict[str, Any]:
        """遮罩字典資料"""
        masked_data = {}

        for key, value in data.items():
            # 檢查欄位名稱是否需要遮罩
            field_rule = self._find_field_rule(key)

            if field_rule and field_rule.enabled:
                if isinstance(value, str):
                    masked_data[key] = self._apply_masking(value, field_rule)
                else:
                    masked_data[key] = self.mask_data(value, context)
                continue

            # 遞歸處理嵌套資料
            if isinstance(value, str):
                masked_data[key] = self._mask_string(value, context)
            else:
                masked_data[key] = self.mask_data(value, context)

        return masked_data

    def _mask_list(self, data: List[Any], context: Optional[str] = None) -> List[Any]:
        """遮罩列表資料"""
        return [self.mask_data(item, context) for item in data]

    def _mask_string(self, data: str, context: Optional[str] = None) -> str:
        """遮罩字串資料"""
        _ = context  # 保留參數以便未來擴展
        masked_data = data

        # 應用所有啟用的規則
        for rule in self.rules:
            if rule.enabled:
                masked_data = self._apply_pattern_masking(masked_data, rule)

        return masked_data

    def _find_field_rule(self, field_name: str) -> Optional[MaskingRule]:
        """查找欄位對應的規則（帶快取）。"""
        # 檢查快取
        if field_name in self._field_rule_cache:
            cached_rule = self._field_rule_cache[field_name]
            # 驗證快取的規則是否仍然啟用
            if cached_rule is None or cached_rule.enabled:
                return cached_rule

        # 查找規則
        field_name_lower = field_name.lower()
        found_rule = None

        for rule in self.rules:
            if rule.enabled and field_name_lower in [
                name.lower() for name in rule.field_names
            ]:
                found_rule = rule
                break

        # 更新快取
        self._field_rule_cache[field_name] = found_rule
        return found_rule

    def _get_compiled_pattern(self, rule: MaskingRule) -> Pattern:
        """獲取編譯後的正則表達式（帶快取）。"""
        cache_key = f"{rule.name}_{id(rule.pattern)}"

        if cache_key not in self._compiled_patterns_cache:
            if isinstance(rule.pattern, str):
                self._compiled_patterns_cache[cache_key] = re.compile(rule.pattern)
            else:
                self._compiled_patterns_cache[cache_key] = rule.pattern

        return self._compiled_patterns_cache[cache_key]

    def clear_cache(self):
        """清除快取。"""
        self._compiled_patterns_cache.clear()
        self._field_rule_cache.clear()

    def _apply_pattern_masking(self, text: str, rule: MaskingRule) -> str:
        """應用模式遮罩（使用快取的編譯模式）。"""

        def replace_match(match):
            # 如果有捕獲組，遮罩捕獲組的內容
            if match.groups():
                full_match = match.group(0)
                sensitive_part = match.group(-1)  # 最後一個捕獲組
                masked_part = self._apply_masking(sensitive_part, rule)
                return full_match.replace(sensitive_part, masked_part)
            else:
                # 遮罩整個匹配
                return self._apply_masking(match.group(0), rule)

        compiled_pattern = self._get_compiled_pattern(rule)
        return compiled_pattern.sub(replace_match, text)

    def _apply_masking(self, text: str, rule: MaskingRule) -> str:
        """應用遮罩策略。"""
        if not text:
            return text

        strategy_handlers = {
            MaskingStrategy.FULL: self._apply_full_masking,
            MaskingStrategy.PARTIAL: self._apply_partial_masking,
            MaskingStrategy.HASH: self._apply_hash_masking,
            MaskingStrategy.TOKENIZE: self._apply_tokenize_masking,
            MaskingStrategy.REDACT: self._apply_redact_masking,
        }

        handler = strategy_handlers.get(rule.strategy)
        if handler:
            return handler(text, rule)
        return text

    def _apply_full_masking(self, text: str, rule: MaskingRule) -> str:
        """應用完全遮罩。"""
        length = len(text) if rule.preserve_length else 8
        return rule.replacement_char * length

    def _apply_partial_masking(self, text: str, rule: MaskingRule) -> str:
        """應用部分遮罩。"""
        if len(text) <= 4:
            return rule.replacement_char * len(text)

        visible_chars = 2
        masked_length = len(text) - (visible_chars * 2)

        if rule.preserve_format:
            return self._apply_format_preserving_mask(text, rule, visible_chars)

        return (
            text[:visible_chars]
            + rule.replacement_char * masked_length
            + text[-visible_chars:]
        )

    def _apply_format_preserving_mask(
        self, text: str, rule: MaskingRule, visible_chars: int
    ) -> str:
        """應用保留格式的遮罩。"""
        masked = ""
        for i, char in enumerate(text):
            if i < visible_chars or i >= len(text) - visible_chars:
                masked += char
            elif char.isalnum():
                masked += rule.replacement_char
            else:
                masked += char
        return masked

    def _apply_hash_masking(self, text: str, rule: MaskingRule) -> str:
        """應用雜湊遮罩。"""
        _ = rule  # 保留參數以便未來擴展
        hash_value = hashlib.sha256(text.encode()).hexdigest()[:8]
        return f"[HASH:{hash_value}]"

    def _apply_tokenize_masking(self, text: str, rule: MaskingRule) -> str:
        """應用標記化遮罩。"""
        _ = rule  # 保留參數以便未來擴展
        if text not in self.token_map:
            token_id = f"TOKEN_{len(self.token_map) + 1:04d}"
            self.token_map[text] = token_id
        return f"[{self.token_map[text]}]"

    def _apply_redact_masking(self, text: str, rule: MaskingRule) -> str:
        """應用編輯遮罩。"""
        _ = text  # 保留參數以便未來擴展
        return f"[{rule.data_type.value.upper()}_REDACTED]"

    def add_custom_rule(
        self,
        name: str,
        data_type: SensitiveDataType,
        pattern: str,
        strategy: MaskingStrategy,
        field_names: List[str],
        description: str = "",
        **kwargs,
    ):
        """添加自定義遮罩規則。

        Args:
            name: 規則名稱
            data_type: 資料類型
            pattern: 正則表達式模式
            strategy: 遮罩策略
            field_names: 欄位名稱列表
            description: 描述
            **kwargs: 其他參數
        """
        rule = MaskingRule(
            name=name,
            data_type=data_type,
            pattern=pattern,
            strategy=strategy,
            field_names=field_names,
            description=description,
            **kwargs,
        )
        self.rules.append(rule)

    def add_rule_with_config(self, config: MaskingRuleConfig):
        """使用配置對象添加自定義遮罩規則。

        Args:
            config: 遮罩規則配置
        """
        self.add_custom_rule(
            name=config.name,
            data_type=config.data_type,
            pattern=config.pattern,
            strategy=config.strategy,
            field_names=config.field_names,
            description=config.description,
            enabled=config.enabled,
            preserve_length=config.preserve_length,
            preserve_format=config.preserve_format,
            replacement_char=config.replacement_char,
        )

    def mask_data_batch(
        self, data_list: List[Any], context: Optional[str] = None
    ) -> List[Any]:
        """批量遮罩資料。

        Args:
            data_list: 要遮罩的資料列表
            context: 上下文信息

        Returns:
            List[Any]: 遮罩後的資料列表
        """
        return [self.mask_data(data, context) for data in data_list]

    def mask_dict_batch(
        self, dict_list: List[Dict[str, Any]], context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """批量遮罩字典資料。

        Args:
            dict_list: 要遮罩的字典列表
            context: 上下文信息

        Returns:
            List[Dict[str, Any]]: 遮罩後的字典列表
        """
        masked_results = []

        # 預編譯所有啟用的規則（效能優化）
        active_rules = [rule for rule in self.rules if rule.enabled]

        for data_dict in dict_list:
            masked_dict = {}
            for key, value in data_dict.items():
                # 檢查欄位名稱是否需要遮罩
                field_rule = self._find_field_rule_cached(key, active_rules)

                if field_rule:
                    if isinstance(value, str):
                        masked_dict[key] = self._apply_masking(value, field_rule)
                    else:
                        masked_dict[key] = self.mask_data(value, context)
                else:
                    # 遞歸處理嵌套資料
                    if isinstance(value, str):
                        masked_dict[key] = self._mask_string_with_rules(
                            value, active_rules
                        )
                    else:
                        masked_dict[key] = self.mask_data(value, context)

            masked_results.append(masked_dict)

        return masked_results

    def _find_field_rule_cached(
        self, field_name: str, active_rules: List[MaskingRule]
    ) -> Optional[MaskingRule]:
        """使用快取查找欄位對應的規則。"""
        field_name_lower = field_name.lower()

        for rule in active_rules:
            if field_name_lower in [name.lower() for name in rule.field_names]:
                return rule

        return None

    def _mask_string_with_rules(
        self, data: str, active_rules: List[MaskingRule]
    ) -> str:
        """使用預編譯規則遮罩字串。"""
        masked_data = data

        for rule in active_rules:
            masked_data = self._apply_pattern_masking(masked_data, rule)

        return masked_data

    def remove_rule(self, rule_name: str):
        """移除規則"""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]

    def enable_rule(self, rule_name: str):
        """啟用規則"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = True
                break

    def disable_rule(self, rule_name: str):
        """停用規則"""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                break

    def get_rules(self) -> List[Dict[str, Any]]:
        """獲取所有規則"""
        return [
            {
                "name": rule.name,
                "data_type": rule.data_type.value,
                "strategy": rule.strategy.value,
                "field_names": rule.field_names,
                "description": rule.description,
                "enabled": rule.enabled,
            }
            for rule in self.rules
        ]

    def test_masking(
        self, test_data: str, rule_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """測試遮罩效果。

        Args:
            test_data: 測試資料
            rule_name: 特定規則名稱（可選）

        Returns:
            Dict[str, Any]: 測試結果
        """
        result = {"original": test_data, "masked": test_data, "applied_rules": []}

        if rule_name:
            # 測試特定規則
            rule = next((r for r in self.rules if r.name == rule_name), None)
            if rule and rule.enabled:
                masked = self._apply_pattern_masking(test_data, rule)
                if masked != test_data:
                    result["masked"] = masked
                    result["applied_rules"].append(rule.name)
        else:
            # 測試所有規則
            result["masked"] = self._mask_string(test_data)

            # 檢查哪些規則被應用
            for rule in self.rules:
                if rule.enabled and rule.pattern.search(test_data):
                    result["applied_rules"].append(rule.name)

        return result

    def export_config(self, file_path: str):
        """匯出配置"""
        config = {
            "custom_rules": [
                {
                    "name": rule.name,
                    "data_type": rule.data_type.value,
                    "pattern": rule.pattern.pattern,
                    "strategy": rule.strategy.value,
                    "field_names": rule.field_names,
                    "description": rule.description,
                    "enabled": rule.enabled,
                    "preserve_length": rule.preserve_length,
                    "preserve_format": rule.preserve_format,
                    "replacement_char": rule.replacement_char,
                }
                for rule in self.rules
            ]
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("匯出遮罩配置時發生錯誤: %s", e)

    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計信息"""
        total_rules = len(self.rules)
        enabled_rules = sum(1 for rule in self.rules if rule.enabled)

        by_type = {}
        by_strategy = {}

        for rule in self.rules:
            # 按類型統計
            type_name = rule.data_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

            # 按策略統計
            strategy_name = rule.strategy.value
            by_strategy[strategy_name] = by_strategy.get(strategy_name, 0) + 1

        return {
            "total_rules": total_rules,
            "enabled_rules": enabled_rules,
            "disabled_rules": total_rules - enabled_rules,
            "by_type": by_type,
            "by_strategy": by_strategy,
            "token_count": len(self.token_map),
        }


# 全域遮罩器實例
_global_masker = None


def get_global_masker() -> DataMasker:
    """獲取全域遮罩器實例"""
    global _global_masker
    if _global_masker is None:
        _global_masker = DataMasker()
    return _global_masker


def mask_sensitive_data(data: Any, context: Optional[str] = None) -> Any:
    """遮罩敏感資料（便利函數）。

    Args:
        data: 要遮罩的資料
        context: 上下文信息

    Returns:
        Any: 遮罩後的資料
    """
    masker = get_global_masker()
    return masker.mask_data(data, context)
