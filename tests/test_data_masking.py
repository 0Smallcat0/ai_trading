"""
敏感資料遮罩測試

測試敏感資料遮罩功能的正確性和有效性。
"""

import pytest
import tempfile
import os
import json

from src.logging.data_masking import (
    DataMasker,
    MaskingStrategy,
    SensitiveDataType,
    mask_sensitive_data,
)


class TestDataMasker:
    """資料遮罩器測試"""

    def setup_method(self):
        """設置測試環境"""
        self.masker = DataMasker()

    def test_api_key_masking(self):
        """測試 API 金鑰遮罩"""
        test_data = {
            "api_key": "sk-1234567890abcdef1234567890abcdef",
            "other_field": "normal_value",
        }

        masked_data = self.masker.mask_data(test_data)

        assert masked_data["api_key"] != test_data["api_key"]
        assert "sk" in masked_data["api_key"]  # 保留前綴
        assert "*" in masked_data["api_key"]  # 包含遮罩字符
        assert masked_data["other_field"] == "normal_value"  # 其他欄位不變

    def test_password_masking(self):
        """測試密碼遮罩"""
        test_data = {"password": "mySecretPassword123", "username": "testuser"}

        masked_data = self.masker.mask_data(test_data)

        assert masked_data["password"] != test_data["password"]
        assert "*" in masked_data["password"]
        assert masked_data["username"] == "testuser"

    def test_credit_card_masking(self):
        """測試信用卡號遮罩"""
        test_data = "我的信用卡號是 4532-1234-5678-9012，請保密。"

        masked_data = self.masker.mask_data(test_data)

        assert "4532-1234-5678-9012" not in masked_data
        assert "45" in masked_data  # 保留前2位
        assert "12" in masked_data  # 保留後2位
        assert "*" in masked_data  # 包含遮罩字符

    def test_phone_number_masking(self):
        """測試電話號碼遮罩"""
        # 測試直接的電話號碼遮罩
        phone_data = {"phone": "0912-345-678"}

        masked_data = self.masker.mask_data(phone_data)

        assert masked_data["phone"] != phone_data["phone"]
        assert "*" in masked_data["phone"]  # 包含遮罩字符

    def test_email_masking(self):
        """測試電子郵件遮罩"""
        test_data = "請聯絡 user@example.com 獲取更多資訊。"

        masked_data = self.masker.mask_data(test_data)

        assert "user@example.com" not in masked_data
        assert "us" in masked_data  # 保留前2位
        assert "om" in masked_data  # 保留後2位
        assert "*" in masked_data  # 包含遮罩字符

    def test_id_number_masking(self):
        """測試身分證字號遮罩"""
        test_data = "身分證字號：A123456789"

        masked_data = self.masker.mask_data(test_data)

        assert "A123456789" not in masked_data
        assert "A1" in masked_data  # 保留前2位
        assert "89" in masked_data  # 保留後2位
        assert "*" in masked_data  # 包含遮罩字符

    def test_nested_data_masking(self):
        """測試嵌套資料遮罩"""
        test_data = {
            "user": {
                "name": "John Doe",
                "email": "john@example.com",
                "credentials": {"password": "secret123", "api_key": "sk-abcdef123456"},
            },
            "metadata": {"created_at": "2023-01-01", "phone": "0912-345-678"},
        }

        masked_data = self.masker.mask_data(test_data)

        assert masked_data["user"]["name"] == "John Doe"  # 普通欄位不變
        assert masked_data["user"]["email"] != test_data["user"]["email"]
        assert (
            masked_data["user"]["credentials"]["password"]
            != test_data["user"]["credentials"]["password"]
        )
        assert (
            masked_data["user"]["credentials"]["api_key"]
            != test_data["user"]["credentials"]["api_key"]
        )
        assert masked_data["metadata"]["created_at"] == "2023-01-01"

    def test_list_data_masking(self):
        """測試列表資料遮罩"""
        test_data = [
            {"email": "user1@example.com", "name": "User 1"},
            {"email": "user2@example.com", "name": "User 2"},
            {"phone": "0912-345-678", "description": "測試電話"},
        ]

        masked_data = self.masker.mask_data(test_data)

        assert len(masked_data) == 3
        assert masked_data[0]["email"] != test_data[0]["email"]
        assert masked_data[0]["name"] == "User 1"
        assert masked_data[1]["email"] != test_data[1]["email"]
        assert masked_data[1]["name"] == "User 2"
        assert masked_data[2]["phone"] != test_data[2]["phone"]

    def test_custom_rule_addition(self):
        """測試自定義規則添加"""
        # 添加自定義規則
        self.masker.add_custom_rule(
            name="測試規則",
            data_type=SensitiveDataType.CUSTOM,
            pattern=r"TEST-\d{4}",
            strategy=MaskingStrategy.PARTIAL,
            field_names=["test_field"],
            description="測試用的自定義規則",
        )

        test_data = "測試代碼：TEST-1234"
        masked_data = self.masker.mask_data(test_data)

        assert "TEST-1234" not in masked_data
        assert "TE" in masked_data or "34" in masked_data

    def test_rule_management(self):
        """測試規則管理"""
        # 獲取初始規則數量
        initial_rules = self.masker.get_rules()
        initial_count = len(initial_rules)

        # 添加規則
        self.masker.add_custom_rule(
            name="測試規則",
            data_type=SensitiveDataType.CUSTOM,
            pattern=r"CUSTOM-\d+",
            strategy=MaskingStrategy.HASH,
            field_names=["custom_field"],
        )

        # 檢查規則數量增加
        rules_after_add = self.masker.get_rules()
        assert len(rules_after_add) == initial_count + 1

        # 停用規則
        self.masker.disable_rule("測試規則")
        rules = self.masker.get_rules()
        test_rule = next(r for r in rules if r["name"] == "測試規則")
        assert test_rule["enabled"] is False

        # 啟用規則
        self.masker.enable_rule("測試規則")
        rules = self.masker.get_rules()
        test_rule = next(r for r in rules if r["name"] == "測試規則")
        assert test_rule["enabled"] is True

        # 移除規則
        self.masker.remove_rule("測試規則")
        rules_after_remove = self.masker.get_rules()
        assert len(rules_after_remove) == initial_count

    def test_masking_strategies(self):
        """測試不同的遮罩策略"""
        test_text = "sensitive_data_123"

        # 測試完全遮罩
        self.masker.add_custom_rule(
            name="完全遮罩測試",
            data_type=SensitiveDataType.CUSTOM,
            pattern=r"sensitive_data_\d+",
            strategy=MaskingStrategy.FULL,
            field_names=[],
        )

        masked_full = self.masker.mask_data(test_text)
        assert "sensitive_data_123" not in masked_full
        assert "*" in masked_full

        # 測試雜湊遮罩
        self.masker.remove_rule("完全遮罩測試")
        self.masker.add_custom_rule(
            name="雜湊遮罩測試",
            data_type=SensitiveDataType.CUSTOM,
            pattern=r"sensitive_data_\d+",
            strategy=MaskingStrategy.HASH,
            field_names=[],
        )

        masked_hash = self.masker.mask_data(test_text)
        assert "sensitive_data_123" not in masked_hash
        assert "[HASH:" in masked_hash

        # 測試標記化
        self.masker.remove_rule("雜湊遮罩測試")
        self.masker.add_custom_rule(
            name="標記化測試",
            data_type=SensitiveDataType.CUSTOM,
            pattern=r"sensitive_data_\d+",
            strategy=MaskingStrategy.TOKENIZE,
            field_names=[],
        )

        masked_token = self.masker.mask_data(test_text)
        assert "sensitive_data_123" not in masked_token
        assert "[TOKEN_" in masked_token

    def test_masking_test_function(self):
        """測試遮罩測試功能"""
        # 使用欄位名稱測試
        test_data = {"api_key": "sk-1234567890abcdef"}

        masked_result = self.masker.mask_data(test_data)

        assert masked_result["api_key"] != test_data["api_key"]
        assert "*" in masked_result["api_key"]

        # 測試遮罩測試功能
        result = self.masker.test_masking("test data")

        assert "original" in result
        assert "masked" in result
        assert "applied_rules" in result

    def test_statistics(self):
        """測試統計功能"""
        stats = self.masker.get_statistics()

        assert "total_rules" in stats
        assert "enabled_rules" in stats
        assert "disabled_rules" in stats
        assert "by_type" in stats
        assert "by_strategy" in stats
        assert "token_count" in stats

        assert stats["total_rules"] > 0
        assert stats["enabled_rules"] >= 0
        assert stats["disabled_rules"] >= 0

    def test_config_export_import(self):
        """測試配置匯出和匯入"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_file = f.name

        try:
            # 匯出配置
            self.masker.export_config(config_file)

            # 檢查文件是否存在
            assert os.path.exists(config_file)

            # 檢查文件內容
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            assert "custom_rules" in config
            assert isinstance(config["custom_rules"], list)

        finally:
            # 清理
            if os.path.exists(config_file):
                os.unlink(config_file)

    def test_global_masker_function(self):
        """測試全域遮罩函數"""
        test_data = {"password": "secret123", "normal_field": "normal_value"}

        masked_data = mask_sensitive_data(test_data)

        assert masked_data["password"] != test_data["password"]
        assert masked_data["normal_field"] == "normal_value"

    def test_error_handling(self):
        """測試錯誤處理"""
        # 測試無效的正則表達式
        with pytest.raises(Exception):
            self.masker.add_custom_rule(
                name="無效規則",
                data_type=SensitiveDataType.CUSTOM,
                pattern="[invalid regex",  # 無效的正則表達式
                strategy=MaskingStrategy.PARTIAL,
                field_names=[],
            )

        # 測試空資料
        assert self.masker.mask_data(None) is None
        assert self.masker.mask_data("") == ""
        assert self.masker.mask_data({}) == {}
        assert self.masker.mask_data([]) == []


if __name__ == "__main__":
    pytest.main([__file__])
