"""合規性日誌記錄模組

此模組實現了符合金融業法規要求的日誌記錄功能，包括：
- 關鍵業務操作記錄
- 決策過程追蹤
- 日誌完整性保證
- 不可篡改性驗證
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

# 設置日誌
logger = logging.getLogger(__name__)


class ComplianceEventType(Enum):
    """合規事件類型"""
    TRADING_DECISION = "trading_decision"  # 交易決策
    RISK_ASSESSMENT = "risk_assessment"    # 風險評估
    PORTFOLIO_CHANGE = "portfolio_change"  # 投資組合變更
    COMPLIANCE_CHECK = "compliance_check"  # 合規檢查
    AUDIT_ACCESS = "audit_access"          # 審計訪問
    DATA_EXPORT = "data_export"            # 資料匯出
    SYSTEM_CONFIG = "system_config"        # 系統配置變更
    USER_ACTION = "user_action"            # 用戶操作
    ALERT_TRIGGER = "alert_trigger"        # 警報觸發
    REGULATORY_REPORT = "regulatory_report"  # 監管報告


class ComplianceLevel(Enum):
    """合規級別"""
    LOW = "low"          # 低風險
    MEDIUM = "medium"    # 中風險
    HIGH = "high"        # 高風險
    CRITICAL = "critical"  # 關鍵


@dataclass
class ComplianceEventConfig:
    """合規事件配置"""
    event_type: ComplianceEventType
    level: ComplianceLevel
    user_id: str
    description: str
    details: Optional[Dict[str, Any]] = None
    business_context: Optional[Dict[str, Any]] = None
    regulatory_context: Optional[Dict[str, Any]] = None


@dataclass
class ComplianceEvent:
    """合規事件"""
    event_id: str
    event_type: ComplianceEventType
    level: ComplianceLevel
    timestamp: datetime
    user_id: str
    description: str
    details: Dict[str, Any]
    business_context: Dict[str, Any]
    regulatory_context: Dict[str, Any]
    hash_value: Optional[str] = None
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        data['level'] = self.level.value
        return data

    def calculate_hash(self) -> str:
        """計算事件雜湊值"""
        # 創建用於雜湊的數據
        hash_data = {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'level': self.level.value,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'description': self.description,
            'details': self.details,
            'business_context': self.business_context,
            'regulatory_context': self.regulatory_context
        }

        # 序列化並計算雜湊
        json_str = json.dumps(hash_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


class ComplianceLogger:
    """合規日誌記錄器"""

    def __init__(
        self,
        log_dir: str = "logs/compliance",
        key_dir: str = "config/keys",
        enable_encryption: bool = True,
        retention_days: int = 2555  # 7年保存期限
    ):
        """初始化合規日誌記錄器。

        Args:
            log_dir: 日誌目錄
            key_dir: 密鑰目錄
            enable_encryption: 是否啟用加密
            retention_days: 保留天數
        """
        self.log_dir = log_dir
        self.key_dir = key_dir
        self.enable_encryption = enable_encryption
        self.retention_days = retention_days

        # 監控指標
        self.metrics = {
            'events_logged': 0,
            'events_by_type': defaultdict(int),
            'events_by_level': defaultdict(int),
            'average_log_time': 0.0,
            'total_log_time': 0.0,
            'verification_success_rate': 0.0,
            'verification_attempts': 0,
            'verification_successes': 0,
            'batch_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

        # 創建目錄
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.key_dir, exist_ok=True)

        # 初始化加密密鑰
        if self.enable_encryption:
            self._init_encryption_keys()

        # 當前日誌文件
        self.current_log_file = self._get_current_log_file()

        # 設置日誌記錄器
        self._setup_logger()

    def _init_encryption_keys(self):
        """初始化加密密鑰"""
        private_key_path = os.path.join(self.key_dir, "compliance_private.pem")
        public_key_path = os.path.join(self.key_dir, "compliance_public.pem")

        if os.path.exists(private_key_path) and os.path.exists(public_key_path):
            # 載入現有密鑰
            with open(private_key_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )

            with open(public_key_path, "rb") as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(), backend=default_backend()
                )
        else:
            # 生成新密鑰對
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            self.public_key = self.private_key.public_key()

            # 保存密鑰
            with open(private_key_path, "wb") as f:
                f.write(self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            with open(public_key_path, "wb") as f:
                f.write(self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))

    def _get_current_log_file(self) -> str:
        """獲取當前日誌文件路徑"""
        today = datetime.now().strftime("%Y%m%d")
        return os.path.join(self.log_dir, f"compliance_{today}.jsonl")

    def _setup_logger(self):
        """設置日誌記錄器"""
        self.logger = logging.getLogger(f"compliance.{id(self)}")
        self.logger.setLevel(logging.INFO)

        # 清除現有處理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # 創建文件處理器
        handler = logging.FileHandler(
            self.current_log_file,
            encoding='utf-8'
        )
        handler.setLevel(logging.INFO)

        # 設置格式
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def _sign_event(self, event: ComplianceEvent) -> str:
        """簽名事件"""
        if not self.enable_encryption:
            return ""

        try:
            # 計算雜湊值
            hash_value = event.calculate_hash()

            # 使用私鑰簽名
            signature = self.private_key.sign(
                hash_value.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            return signature.hex()
        except Exception as e:
            logger.error("簽名事件時發生錯誤: %s", e)
            return ""

    def log_event(
        self,
        event_type: ComplianceEventType,
        level: ComplianceLevel,
        user_id: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        business_context: Optional[Dict[str, Any]] = None,
        regulatory_context: Optional[Dict[str, Any]] = None
    ) -> ComplianceEvent:
        """記錄合規事件。

        Args:
            event_type: 事件類型
            level: 合規級別
            user_id: 用戶ID
            description: 事件描述
            details: 詳細信息
            business_context: 業務上下文
            regulatory_context: 監管上下文

        Returns:
            ComplianceEvent: 合規事件
        """
        start_time = time.time()

        # 創建事件
        event = ComplianceEvent(
            event_id=f"{int(time.time() * 1000)}_{user_id}_{event_type.value}",
            event_type=event_type,
            level=level,
            timestamp=datetime.now(),
            user_id=user_id,
            description=description,
            details=details or {},
            business_context=business_context or {},
            regulatory_context=regulatory_context or {}
        )

        # 計算雜湊值
        event.hash_value = event.calculate_hash()

        # 簽名事件
        if self.enable_encryption:
            event.signature = self._sign_event(event)

        # 檢查是否需要輪換日誌文件
        current_file = self._get_current_log_file()
        if current_file != self.current_log_file:
            self.current_log_file = current_file
            self._setup_logger()

        # 記錄事件
        try:
            self.logger.info(json.dumps(event.to_dict(), ensure_ascii=False))
        except Exception as e:
            logger.error("記錄合規事件時發生錯誤: %s", e)

        # 計算日誌記錄時間
        log_time = time.time() - start_time

        # 更新監控指標
        self._update_metrics(event, log_time)

        return event

    def _create_event(
        self,
        event_type: ComplianceEventType,
        level: ComplianceLevel,
        user_id: str,
        description: str,
        details: Dict[str, Any],
        business_context: Dict[str, Any],
        regulatory_context: Dict[str, Any]
    ) -> ComplianceEvent:
        """創建合規事件。"""
        event = ComplianceEvent(
            event_id=f"{int(time.time() * 1000)}_{user_id}_{event_type.value}",
            event_type=event_type,
            level=level,
            timestamp=datetime.now(),
            user_id=user_id,
            description=description,
            details=details,
            business_context=business_context,
            regulatory_context=regulatory_context
        )

        # 計算雜湊值
        event.hash_value = event.calculate_hash()

        # 簽名事件
        if self.enable_encryption:
            event.signature = self._sign_event(event)

        return event

    def _update_metrics(self, event: ComplianceEvent, log_time: float):
        """更新監控指標。"""
        self.metrics['events_logged'] += 1
        self.metrics['events_by_type'][event.event_type.value] += 1
        self.metrics['events_by_level'][event.level.value] += 1

        # 更新平均日誌記錄時間
        self.metrics['total_log_time'] += log_time
        total_time = self.metrics['total_log_time']
        total_events = self.metrics['events_logged']
        self.metrics['average_log_time'] = total_time / total_events

    def get_metrics(self) -> Dict[str, Any]:
        """獲取監控指標。"""
        return dict(self.metrics)

    def reset_metrics(self):
        """重置監控指標。"""
        self.metrics = {
            'events_logged': 0,
            'events_by_type': defaultdict(int),
            'events_by_level': defaultdict(int),
            'average_log_time': 0.0,
            'total_log_time': 0.0,
            'verification_success_rate': 0.0,
            'verification_attempts': 0,
            'verification_successes': 0,
            'batch_operations': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

    def log_event_with_config(self, config: ComplianceEventConfig) -> ComplianceEvent:
        """使用配置對象記錄合規事件。

        Args:
            config: 合規事件配置

        Returns:
            ComplianceEvent: 合規事件
        """
        return self.log_event(
            event_type=config.event_type,
            level=config.level,
            user_id=config.user_id,
            description=config.description,
            details=config.details,
            business_context=config.business_context,
            regulatory_context=config.regulatory_context
        )

    def log_events_batch(self, configs: List[ComplianceEventConfig]) -> List[ComplianceEvent]:
        """批量記錄合規事件。

        Args:
            configs: 合規事件配置列表

        Returns:
            List[ComplianceEvent]: 合規事件列表
        """
        events = []
        log_entries = []

        # 批量創建事件
        for config in configs:
            event = self._create_event(
                event_type=config.event_type,
                level=config.level,
                user_id=config.user_id,
                description=config.description,
                details=config.details or {},
                business_context=config.business_context or {},
                regulatory_context=config.regulatory_context or {}
            )
            events.append(event)
            log_entries.append(json.dumps(event.to_dict(), ensure_ascii=False))

        # 批量寫入日誌
        try:
            self._write_batch_logs(log_entries)
        except Exception as e:
            logger.error("批量記錄合規事件時發生錯誤: %s", e)

        return events

    def _write_batch_logs(self, log_entries: List[str]):
        """批量寫入日誌。"""
        log_file = self._get_current_log_file()
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                for entry in log_entries:
                    f.write(entry + '\n')
                f.flush()  # 確保立即寫入
        except Exception as e:
            logger.error("批量寫入日誌文件時發生錯誤: %s", e)
            raise

    def verify_event(self, event_data: Dict[str, Any]) -> bool:
        """驗證事件完整性。

        Args:
            event_data: 事件數據

        Returns:
            bool: 驗證結果
        """
        if not self.enable_encryption:
            return True

        try:
            # 重建事件對象
            event = ComplianceEvent(
                event_id=event_data['event_id'],
                event_type=ComplianceEventType(event_data['event_type']),
                level=ComplianceLevel(event_data['level']),
                timestamp=datetime.fromisoformat(event_data['timestamp']),
                user_id=event_data['user_id'],
                description=event_data['description'],
                details=event_data['details'],
                business_context=event_data['business_context'],
                regulatory_context=event_data['regulatory_context']
            )

            # 驗證雜湊值
            calculated_hash = event.calculate_hash()
            if calculated_hash != event_data.get('hash_value'):
                return False

            # 驗證簽名
            if 'signature' in event_data and event_data['signature']:
                try:
                    signature_bytes = bytes.fromhex(event_data['signature'])
                    self.public_key.verify(
                        signature_bytes,
                        calculated_hash.encode('utf-8'),
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH
                        ),
                        hashes.SHA256()
                    )
                    return True
                except Exception:
                    return False

            return True
        except Exception as e:
            logger.error("驗證事件時發生錯誤: %s", e)
            return False

    def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[List[ComplianceEventType]] = None,
        levels: Optional[List[ComplianceLevel]] = None,
        user_id: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """獲取合規事件。

        Args:
            start_date: 開始日期
            end_date: 結束日期
            event_types: 事件類型列表
            levels: 合規級別列表
            user_id: 用戶ID
            limit: 限制數量

        Returns:
            List[Dict[str, Any]]: 事件列表
        """
        log_files = self._get_log_files()
        events = []

        for log_file in log_files:
            events.extend(
                self._read_events_from_file(
                    log_file, start_date, end_date, event_types, levels, user_id, limit - len(events)
                )
            )
            if len(events) >= limit:
                break

        return events[:limit]

    def _get_log_files(self) -> List[str]:
        """獲取日誌文件列表。"""
        log_files = []
        try:
            for file_name in os.listdir(self.log_dir):
                if file_name.startswith("compliance_") and file_name.endswith(".jsonl"):
                    log_files.append(os.path.join(self.log_dir, file_name))
        except OSError as e:
            logger.error("讀取日誌目錄時發生錯誤: %s", e)

        # 按時間排序
        log_files.sort(reverse=True)
        return log_files

    def _read_events_from_file(
        self,
        log_file: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        event_types: Optional[List[ComplianceEventType]],
        levels: Optional[List[ComplianceLevel]],
        user_id: Optional[str],
        remaining_limit: int
    ) -> List[Dict[str, Any]]:
        """從文件讀取事件。"""
        events = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if len(events) >= remaining_limit:
                        break

                    event_data = self._parse_event_line(line)
                    if event_data and self._match_filters(
                        event_data, start_date, end_date, event_types, levels, user_id
                    ):
                        events.append(event_data)

        except Exception as e:
            logger.error("讀取日誌文件時發生錯誤 %s: %s", log_file, e)

        return events

    def _parse_event_line(self, line: str) -> Optional[Dict[str, Any]]:
        """解析事件行。"""
        try:
            return json.loads(line.strip())
        except json.JSONDecodeError:
            return None

    def _match_filters(
        self,
        event_data: Dict[str, Any],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        event_types: Optional[List[ComplianceEventType]],
        levels: Optional[List[ComplianceLevel]],
        user_id: Optional[str]
    ) -> bool:
        """檢查事件是否符合過濾條件。"""
        return (
            self._match_time_filter(event_data, start_date, end_date) and
            self._match_type_filter(event_data, event_types) and
            self._match_level_filter(event_data, levels) and
            self._match_user_filter(event_data, user_id)
        )

    def _match_time_filter(
        self, event_data: Dict[str, Any], start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> bool:
        """檢查時間過濾條件。"""
        if not (start_date or end_date):
            return True

        try:
            event_time = datetime.fromisoformat(event_data['timestamp'])
            if start_date and event_time < start_date:
                return False
            if end_date and event_time > end_date:
                return False
            return True
        except (KeyError, ValueError):
            return False

    def _match_type_filter(
        self, event_data: Dict[str, Any], event_types: Optional[List[ComplianceEventType]]
    ) -> bool:
        """檢查事件類型過濾條件。"""
        if not event_types:
            return True
        event_type_values = [et.value for et in event_types]
        return event_data.get('event_type') in event_type_values

    def _match_level_filter(
        self, event_data: Dict[str, Any], levels: Optional[List[ComplianceLevel]]
    ) -> bool:
        """檢查合規級別過濾條件。"""
        if not levels:
            return True
        level_values = [l.value for l in levels]
        return event_data.get('level') in level_values

    def _match_user_filter(self, event_data: Dict[str, Any], user_id: Optional[str]) -> bool:
        """檢查用戶過濾條件。"""
        if not user_id:
            return True
        return event_data.get('user_id') == user_id

    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        report_type: str = "summary"
    ) -> Dict[str, Any]:
        """生成合規報告。

        Args:
            start_date: 開始日期
            end_date: 結束日期
            report_type: 報告類型

        Returns:
            Dict[str, Any]: 合規報告
        """
        events = self.get_events(start_date=start_date, end_date=end_date, limit=10000)

        report = {
            "report_id": f"compliance_report_{int(time.time())}",
            "report_type": report_type,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "generated_at": datetime.now().isoformat(),
            "total_events": len(events),
            "summary": self._generate_summary(events),
            "statistics": self._generate_statistics(events),
            "integrity_check": self._check_integrity(events)
        }

        return report

    def _generate_summary(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成摘要統計。"""
        summary = {
            "by_type": self._count_by_type(events),
            "by_level": self._count_by_level(events),
            "by_user": self._count_by_user(events),
            "by_day": self._count_by_day(events)
        }
        return summary

    def _count_by_type(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """按事件類型統計。"""
        counts = {}
        for event in events:
            event_type = event.get('event_type', 'unknown')
            counts[event_type] = counts.get(event_type, 0) + 1
        return counts

    def _count_by_level(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """按風險級別統計。"""
        counts = {}
        for event in events:
            level = event.get('level', 'unknown')
            counts[level] = counts.get(level, 0) + 1
        return counts

    def _count_by_user(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """按用戶統計。"""
        counts = {}
        for event in events:
            user_id = event.get('user_id', 'unknown')
            counts[user_id] = counts.get(user_id, 0) + 1
        return counts

    def _count_by_day(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """按日期統計。"""
        counts = {}
        for event in events:
            try:
                event_timestamp = event['timestamp']
                event_date = datetime.fromisoformat(event_timestamp).date().isoformat()
                counts[event_date] = counts.get(event_date, 0) + 1
            except (KeyError, ValueError):
                continue
        return counts

    def _generate_statistics(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成詳細統計"""
        statistics = {
            "high_risk_events": 0,
            "critical_events": 0,
            "trading_decisions": 0,
            "compliance_violations": 0,
            "data_exports": 0
        }

        for event in events:
            level = event.get('level')
            event_type = event.get('event_type')

            if level == 'high':
                statistics["high_risk_events"] += 1
            elif level == 'critical':
                statistics["critical_events"] += 1

            if event_type == 'trading_decision':
                statistics["trading_decisions"] += 1
            elif event_type == 'data_export':
                statistics["data_exports"] += 1

        return statistics

    def _check_integrity(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """檢查完整性"""
        integrity_check = {
            "total_events": len(events),
            "verified_events": 0,
            "failed_events": 0,
            "integrity_score": 0.0
        }

        for event in events:
            if self.verify_event(event):
                integrity_check["verified_events"] += 1
            else:
                integrity_check["failed_events"] += 1

        if integrity_check["total_events"] > 0:
            integrity_check["integrity_score"] = (
                integrity_check["verified_events"] / integrity_check["total_events"]
            )

        return integrity_check
