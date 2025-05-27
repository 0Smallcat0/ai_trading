"""
合規性日誌記錄測試

測試合規性日誌記錄功能的正確性和完整性。
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta

from src.logging.compliance import (
    ComplianceLogger,
    ComplianceEvent,
    ComplianceEventType,
    ComplianceLevel
)


class TestComplianceLogger:
    """合規日誌記錄器測試"""

    def setup_method(self):
        """設置測試環境"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = os.path.join(self.temp_dir, "compliance")
        self.key_dir = os.path.join(self.temp_dir, "keys")

        self.logger = ComplianceLogger(
            log_dir=self.log_dir,
            key_dir=self.key_dir,
            enable_encryption=True
        )

    def teardown_method(self):
        """清理測試環境"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_event_creation(self):
        """測試事件記錄創建"""
        event = self.logger.log_event(
            event_type=ComplianceEventType.TRADING_DECISION,
            level=ComplianceLevel.HIGH,
            user_id="test_user",
            description="測試交易決策",
            details={"symbol": "AAPL", "quantity": 100},
            business_context={"strategy": "momentum"},
            regulatory_context={"regulation": "MiFID II"}
        )

        assert event.event_type == ComplianceEventType.TRADING_DECISION
        assert event.level == ComplianceLevel.HIGH
        assert event.user_id == "test_user"
        assert event.description == "測試交易決策"
        assert event.details["symbol"] == "AAPL"
        assert event.hash_value is not None
        assert event.signature is not None

    def test_event_verification(self):
        """測試事件驗證"""
        # 記錄事件
        event = self.logger.log_event(
            event_type=ComplianceEventType.RISK_ASSESSMENT,
            level=ComplianceLevel.MEDIUM,
            user_id="test_user",
            description="風險評估測試"
        )

        # 驗證事件
        event_data = event.to_dict()
        assert self.logger.verify_event(event_data) is True

        # 篡改事件數據
        event_data["description"] = "篡改後的描述"
        assert self.logger.verify_event(event_data) is False

    def test_get_events_filtering(self):
        """測試事件查詢和過濾"""
        # 記錄多個事件
        events = []
        for i in range(5):
            event = self.logger.log_event(
                event_type=ComplianceEventType.USER_ACTION,
                level=ComplianceLevel.LOW,
                user_id=f"user_{i}",
                description=f"用戶操作 {i}"
            )
            events.append(event)

        # 查詢所有事件
        all_events = self.logger.get_events()
        assert len(all_events) == 5

        # 按用戶過濾
        user_events = self.logger.get_events(user_id="user_1")
        assert len(user_events) == 1
        assert user_events[0]["user_id"] == "user_1"

        # 按事件類型過濾
        type_events = self.logger.get_events(
            event_types=[ComplianceEventType.USER_ACTION]
        )
        assert len(type_events) == 5

        # 按級別過濾
        level_events = self.logger.get_events(
            levels=[ComplianceLevel.LOW]
        )
        assert len(level_events) == 5

    def test_compliance_report_generation(self):
        """測試合規報告生成"""
        # 記錄不同類型的事件
        events_data = [
            (ComplianceEventType.TRADING_DECISION, ComplianceLevel.HIGH),
            (ComplianceEventType.RISK_ASSESSMENT, ComplianceLevel.MEDIUM),
            (ComplianceEventType.USER_ACTION, ComplianceLevel.LOW),
            (ComplianceEventType.TRADING_DECISION, ComplianceLevel.CRITICAL),
        ]

        for event_type, level in events_data:
            self.logger.log_event(
                event_type=event_type,
                level=level,
                user_id="test_user",
                description=f"測試事件 {event_type.value}"
            )

        # 生成報告
        start_date = datetime.now() - timedelta(hours=1)
        end_date = datetime.now() + timedelta(hours=1)

        report = self.logger.generate_compliance_report(
            start_date=start_date,
            end_date=end_date
        )

        assert report["total_events"] == 4
        assert "trading_decision" in report["summary"]["by_type"]
        assert report["summary"]["by_type"]["trading_decision"] == 2
        assert "high" in report["summary"]["by_level"]
        assert "critical" in report["summary"]["by_level"]
        assert report["statistics"]["high_risk_events"] == 1
        assert report["statistics"]["critical_events"] == 1
        assert report["statistics"]["trading_decisions"] == 2
        assert report["integrity_check"]["total_events"] == 4
        assert report["integrity_check"]["verified_events"] == 4
        assert report["integrity_check"]["integrity_score"] == 1.0

    def test_hash_calculation(self):
        """測試雜湊值計算"""
        event = ComplianceEvent(
            event_id="test_id",
            event_type=ComplianceEventType.SYSTEM_CONFIG,
            level=ComplianceLevel.MEDIUM,
            timestamp=datetime.now(),
            user_id="test_user",
            description="測試事件",
            details={"key": "value"},
            business_context={},
            regulatory_context={}
        )

        hash1 = event.calculate_hash()
        hash2 = event.calculate_hash()

        # 相同事件應該產生相同雜湊值
        assert hash1 == hash2

        # 修改事件後雜湊值應該不同
        event.description = "修改後的描述"
        hash3 = event.calculate_hash()
        assert hash1 != hash3

    def test_encryption_disabled(self):
        """測試停用加密的情況"""
        logger_no_encryption = ComplianceLogger(
            log_dir=self.log_dir,
            key_dir=self.key_dir,
            enable_encryption=False
        )

        event = logger_no_encryption.log_event(
            event_type=ComplianceEventType.AUDIT_ACCESS,
            level=ComplianceLevel.LOW,
            user_id="test_user",
            description="測試審計訪問"
        )

        assert event.signature == "" or event.signature is None

        # 驗證應該總是返回 True
        event_data = event.to_dict()
        assert logger_no_encryption.verify_event(event_data) is True

    def test_error_handling(self):
        """測試錯誤處理"""
        # 測試無效的事件數據驗證
        invalid_event_data = {
            "event_id": "invalid",
            "event_type": "invalid_type",
            "level": "invalid_level",
            "timestamp": "invalid_timestamp",
            "user_id": "test_user",
            "description": "測試",
            "details": {},
            "business_context": {},
            "regulatory_context": {}
        }

        assert self.logger.verify_event(invalid_event_data) is False

    def test_logging_errors(self):
        """測試日誌記錄錯誤處理"""
        # 測試無效的事件數據驗證
        invalid_event_data = {
            "event_id": "invalid",
            "event_type": "invalid_type",
            "level": "invalid_level",
            "timestamp": "invalid_timestamp",
            "user_id": "test_user",
            "description": "測試",
            "details": {},
            "business_context": {},
            "regulatory_context": {}
        }

        # 驗證應該返回 False
        assert self.logger.verify_event(invalid_event_data) is False


class TestComplianceEvent:
    """合規事件測試"""

    def test_event_to_dict(self):
        """測試事件轉換為字典"""
        timestamp = datetime.now()
        event = ComplianceEvent(
            event_id="test_id",
            event_type=ComplianceEventType.PORTFOLIO_CHANGE,
            level=ComplianceLevel.HIGH,
            timestamp=timestamp,
            user_id="test_user",
            description="投資組合變更",
            details={"old_allocation": 0.5, "new_allocation": 0.6},
            business_context={"portfolio_id": "P001"},
            regulatory_context={"rule": "diversification"}
        )

        event_dict = event.to_dict()

        assert event_dict["event_id"] == "test_id"
        assert event_dict["event_type"] == "portfolio_change"
        assert event_dict["level"] == "high"
        assert event_dict["timestamp"] == timestamp.isoformat()
        assert event_dict["user_id"] == "test_user"
        assert event_dict["description"] == "投資組合變更"
        assert event_dict["details"]["old_allocation"] == 0.5
        assert event_dict["business_context"]["portfolio_id"] == "P001"
        assert event_dict["regulatory_context"]["rule"] == "diversification"


if __name__ == "__main__":
    pytest.main([__file__])
