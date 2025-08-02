"""
異常登入檢測與封鎖服務

此模組實現了完整的異常登入檢測和自動封鎖功能，包括：
- IP 白名單和黑名單管理
- 異常行為檢測
- 自動封鎖機制
- 地理位置檢查
- 設備指紋識別
- 登入模式分析
- 風險評分系統

遵循金融級安全標準，提供多層次的安全防護。
"""

import logging
import json
import hashlib
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from enum import Enum
from collections import defaultdict, deque
import threading
import requests

# 導入資料庫相關模組
from sqlalchemy import create_engine, and_, or_, desc, func
from sqlalchemy.orm import sessionmaker, Session

# 導入配置和資料庫模型
from src.config import DB_URL
from src.database.schema import User, SecurityEvent, AuditLog

# 設置日誌
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """風險等級"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BlockReason(Enum):
    """封鎖原因"""
    FAILED_ATTEMPTS = "failed_attempts"
    SUSPICIOUS_IP = "suspicious_ip"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    GEOGRAPHIC_ANOMALY = "geographic_anomaly"
    DEVICE_ANOMALY = "device_anomaly"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    MANUAL_BLOCK = "manual_block"


class AnomalyDetectionService:
    """
    異常登入檢測與封鎖服務
    
    提供完整的異常檢測和自動防護功能，包括多種檢測算法
    和自動響應機制。
    """
    
    def __init__(self):
        """初始化異常檢測服務"""
        try:
            # 初始化資料庫連接
            self.engine = create_engine(DB_URL)
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("異常檢測服務資料庫連接初始化成功")
            
            # 服務配置
            self.config = {
                # 登入失敗限制
                "max_failed_attempts": 5,
                "failed_attempts_window": 900,  # 15分鐘
                "lockout_duration": 1800,  # 30分鐘
                
                # IP 相關配置
                "max_ips_per_user": 5,  # 每個使用者最多5個IP
                "ip_change_threshold": 3,  # IP變更閾值
                "suspicious_ip_score": 8.0,
                
                # 地理位置配置
                "max_distance_km": 1000,  # 最大地理距離（公里）
                "geo_change_threshold": 2,  # 地理位置變更閾值
                
                # 設備指紋配置
                "device_change_threshold": 2,  # 設備變更閾值
                "max_devices_per_user": 10,  # 每個使用者最多10個設備
                
                # 時間模式配置
                "unusual_hour_threshold": 3,  # 異常時間閾值
                "normal_hours": (8, 22),  # 正常活動時間
                
                # 風險評分配置
                "risk_thresholds": {
                    RiskLevel.LOW: 3.0,
                    RiskLevel.MEDIUM: 6.0,
                    RiskLevel.HIGH: 8.0,
                    RiskLevel.CRITICAL: 9.0,
                },
                
                # 自動封鎖配置
                "auto_block_enabled": True,
                "auto_block_threshold": 8.0,
                "temp_block_duration": 3600,  # 1小時
            }
            
            # 記憶體快取
            self._ip_whitelist: Set[str] = set()
            self._ip_blacklist: Set[str] = set()
            self._user_patterns: Dict[str, Dict] = defaultdict(dict)
            self._recent_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
            
            # 線程鎖
            self._lock = threading.RLock()
            
            # 載入配置
            self._load_ip_lists()
            self._load_user_patterns()
            
            logger.info("異常檢測服務初始化完成")
            
        except Exception as e:
            logger.error(f"異常檢測服務初始化失敗: {e}")
            raise
    
    def analyze_login_attempt(
        self,
        user_id: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, float, List[str]]:
        """
        分析登入嘗試
        
        Args:
            user_id: 使用者 ID
            ip_address: IP 地址
            user_agent: 使用者代理
            success: 是否成功
            additional_data: 額外資料
            
        Returns:
            Tuple[bool, float, List[str]]: (是否允許, 風險分數, 檢測到的異常)
        """
        try:
            with self._lock:
                # 記錄登入事件
                event_data = {
                    "user_id": user_id,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "success": success,
                    "timestamp": datetime.now(),
                    "additional_data": additional_data or {},
                }
                
                self._recent_events[user_id].append(event_data)
                
                # 執行各種檢測
                anomalies = []
                risk_score = 0.0
                
                # 1. IP 檢查
                ip_risk, ip_anomalies = self._check_ip_anomalies(user_id, ip_address)
                risk_score += ip_risk
                anomalies.extend(ip_anomalies)
                
                # 2. 失敗次數檢查
                if not success:
                    failure_risk, failure_anomalies = self._check_failure_patterns(user_id)
                    risk_score += failure_risk
                    anomalies.extend(failure_anomalies)
                
                # 3. 地理位置檢查
                geo_risk, geo_anomalies = self._check_geographic_anomalies(user_id, ip_address)
                risk_score += geo_risk
                anomalies.extend(geo_anomalies)
                
                # 4. 設備指紋檢查
                device_risk, device_anomalies = self._check_device_anomalies(user_id, user_agent)
                risk_score += device_risk
                anomalies.extend(device_anomalies)
                
                # 5. 時間模式檢查
                time_risk, time_anomalies = self._check_time_patterns(user_id)
                risk_score += time_risk
                anomalies.extend(time_anomalies)
                
                # 6. 行為模式檢查
                behavior_risk, behavior_anomalies = self._check_behavior_patterns(user_id)
                risk_score += behavior_risk
                anomalies.extend(behavior_anomalies)
                
                # 確定風險等級
                risk_level = self._get_risk_level(risk_score)
                
                # 決定是否允許
                should_allow = self._should_allow_login(risk_score, anomalies)
                
                # 記錄分析結果
                self._log_analysis_result(
                    user_id, ip_address, risk_score, risk_level, anomalies, should_allow
                )
                
                # 自動封鎖檢查
                if not should_allow and self.config["auto_block_enabled"]:
                    self._auto_block_user(user_id, ip_address, anomalies, risk_score)
                
                return should_allow, risk_score, anomalies
                
        except Exception as e:
            logger.error(f"分析登入嘗試失敗: {e}")
            return True, 0.0, []  # 發生錯誤時允許登入，避免誤封
    
    def _check_ip_anomalies(self, user_id: str, ip_address: str) -> Tuple[float, List[str]]:
        """檢查 IP 相關異常"""
        anomalies = []
        risk_score = 0.0
        
        try:
            # 檢查黑名單
            if ip_address in self._ip_blacklist:
                anomalies.append("IP 在黑名單中")
                risk_score += 9.0
                return risk_score, anomalies
            
            # 檢查白名單
            if ip_address in self._ip_whitelist:
                return risk_score, anomalies
            
            # 檢查是否為可疑 IP
            if self._is_suspicious_ip(ip_address):
                anomalies.append("可疑 IP 地址")
                risk_score += self.config["suspicious_ip_score"]
            
            # 檢查 IP 變更頻率
            user_ips = self._get_user_recent_ips(user_id)
            if len(user_ips) > self.config["max_ips_per_user"]:
                anomalies.append("IP 變更過於頻繁")
                risk_score += 3.0
            
            # 檢查新 IP
            if ip_address not in user_ips:
                recent_ip_changes = self._count_recent_ip_changes(user_id)
                if recent_ip_changes >= self.config["ip_change_threshold"]:
                    anomalies.append("短時間內多次 IP 變更")
                    risk_score += 2.0
            
            # 檢查 IP 類型
            if self._is_tor_or_proxy_ip(ip_address):
                anomalies.append("使用 Tor 或代理 IP")
                risk_score += 4.0
            
        except Exception as e:
            logger.error(f"檢查 IP 異常失敗: {e}")
        
        return risk_score, anomalies
    
    def _check_failure_patterns(self, user_id: str) -> Tuple[float, List[str]]:
        """檢查失敗模式"""
        anomalies = []
        risk_score = 0.0
        
        try:
            # 獲取最近的失敗次數
            recent_failures = self._count_recent_failures(user_id)
            
            if recent_failures >= self.config["max_failed_attempts"]:
                anomalies.append("登入失敗次數過多")
                risk_score += 5.0
            elif recent_failures >= self.config["max_failed_attempts"] // 2:
                anomalies.append("登入失敗次數較多")
                risk_score += 2.0
            
            # 檢查失敗模式
            failure_pattern = self._analyze_failure_pattern(user_id)
            if failure_pattern["is_brute_force"]:
                anomalies.append("疑似暴力破解攻擊")
                risk_score += 6.0
            
        except Exception as e:
            logger.error(f"檢查失敗模式失敗: {e}")
        
        return risk_score, anomalies
    
    def _check_geographic_anomalies(self, user_id: str, ip_address: str) -> Tuple[float, List[str]]:
        """檢查地理位置異常"""
        anomalies = []
        risk_score = 0.0
        
        try:
            # 獲取 IP 地理位置
            current_location = self._get_ip_location(ip_address)
            if not current_location:
                return risk_score, anomalies
            
            # 獲取使用者歷史位置
            user_locations = self._get_user_locations(user_id)
            
            if user_locations:
                # 計算距離
                min_distance = min(
                    self._calculate_distance(current_location, loc) 
                    for loc in user_locations
                )
                
                if min_distance > self.config["max_distance_km"]:
                    anomalies.append(f"地理位置異常（距離: {min_distance:.0f}km）")
                    risk_score += 3.0
            
            # 檢查國家變更
            current_country = current_location.get("country")
            user_countries = {loc.get("country") for loc in user_locations}
            
            if current_country and current_country not in user_countries:
                anomalies.append("從新國家登入")
                risk_score += 2.0
            
        except Exception as e:
            logger.error(f"檢查地理位置異常失敗: {e}")
        
        return risk_score, anomalies
    
    def _check_device_anomalies(self, user_id: str, user_agent: str) -> Tuple[float, List[str]]:
        """檢查設備異常"""
        anomalies = []
        risk_score = 0.0
        
        try:
            # 生成設備指紋
            device_fingerprint = self._generate_device_fingerprint(user_agent)
            
            # 獲取使用者設備歷史
            user_devices = self._get_user_devices(user_id)
            
            # 檢查新設備
            if device_fingerprint not in user_devices:
                recent_device_changes = self._count_recent_device_changes(user_id)
                if recent_device_changes >= self.config["device_change_threshold"]:
                    anomalies.append("短時間內多次設備變更")
                    risk_score += 2.0
                else:
                    anomalies.append("使用新設備")
                    risk_score += 1.0
            
            # 檢查設備數量
            if len(user_devices) > self.config["max_devices_per_user"]:
                anomalies.append("設備數量過多")
                risk_score += 1.5
            
            # 檢查可疑 User-Agent
            if self._is_suspicious_user_agent(user_agent):
                anomalies.append("可疑的 User-Agent")
                risk_score += 2.0
            
        except Exception as e:
            logger.error(f"檢查設備異常失敗: {e}")
        
        return risk_score, anomalies
    
    def _check_time_patterns(self, user_id: str) -> Tuple[float, List[str]]:
        """檢查時間模式異常"""
        anomalies = []
        risk_score = 0.0
        
        try:
            current_hour = datetime.now().hour
            normal_start, normal_end = self.config["normal_hours"]
            
            # 檢查是否在異常時間
            if not (normal_start <= current_hour <= normal_end):
                user_night_logins = self._count_user_night_logins(user_id)
                if user_night_logins < self.config["unusual_hour_threshold"]:
                    anomalies.append("在異常時間登入")
                    risk_score += 1.5
            
            # 檢查登入頻率
            login_frequency = self._analyze_login_frequency(user_id)
            if login_frequency["is_unusual"]:
                anomalies.append("登入頻率異常")
                risk_score += 1.0
            
        except Exception as e:
            logger.error(f"檢查時間模式失敗: {e}")
        
        return risk_score, anomalies
    
    def _check_behavior_patterns(self, user_id: str) -> Tuple[float, List[str]]:
        """檢查行為模式異常"""
        anomalies = []
        risk_score = 0.0
        
        try:
            # 檢查登入間隔
            login_intervals = self._get_login_intervals(user_id)
            if login_intervals and self._is_unusual_interval_pattern(login_intervals):
                anomalies.append("登入間隔模式異常")
                risk_score += 1.0
            
            # 檢查會話持續時間
            session_durations = self._get_session_durations(user_id)
            if session_durations and self._is_unusual_session_pattern(session_durations):
                anomalies.append("會話持續時間異常")
                risk_score += 1.0
            
        except Exception as e:
            logger.error(f"檢查行為模式失敗: {e}")

        return risk_score, anomalies

    def add_ip_to_whitelist(self, ip_address: str, reason: str = "") -> bool:
        """添加 IP 到白名單"""
        try:
            with self._lock:
                self._ip_whitelist.add(ip_address)

                # 從黑名單中移除（如果存在）
                self._ip_blacklist.discard(ip_address)

                # 保存到資料庫
                self._save_ip_list_change("whitelist", "add", ip_address, reason)

                logger.info(f"IP {ip_address} 已添加到白名單，原因: {reason}")
                return True

        except Exception as e:
            logger.error(f"添加 IP 到白名單失敗: {e}")
            return False

    def add_ip_to_blacklist(self, ip_address: str, reason: str = "") -> bool:
        """添加 IP 到黑名單"""
        try:
            with self._lock:
                self._ip_blacklist.add(ip_address)

                # 從白名單中移除（如果存在）
                self._ip_whitelist.discard(ip_address)

                # 保存到資料庫
                self._save_ip_list_change("blacklist", "add", ip_address, reason)

                logger.info(f"IP {ip_address} 已添加到黑名單，原因: {reason}")
                return True

        except Exception as e:
            logger.error(f"添加 IP 到黑名單失敗: {e}")
            return False

    def remove_ip_from_whitelist(self, ip_address: str) -> bool:
        """從白名單移除 IP"""
        try:
            with self._lock:
                self._ip_whitelist.discard(ip_address)
                self._save_ip_list_change("whitelist", "remove", ip_address)
                logger.info(f"IP {ip_address} 已從白名單移除")
                return True
        except Exception as e:
            logger.error(f"從白名單移除 IP 失敗: {e}")
            return False

    def remove_ip_from_blacklist(self, ip_address: str) -> bool:
        """從黑名單移除 IP"""
        try:
            with self._lock:
                self._ip_blacklist.discard(ip_address)
                self._save_ip_list_change("blacklist", "remove", ip_address)
                logger.info(f"IP {ip_address} 已從黑名單移除")
                return True
        except Exception as e:
            logger.error(f"從黑名單移除 IP 失敗: {e}")
            return False

    def block_user_temporarily(
        self,
        user_id: str,
        duration_seconds: int,
        reason: BlockReason,
        details: str = ""
    ) -> bool:
        """臨時封鎖使用者"""
        try:
            with self.session_factory() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if not user:
                    return False

                # 設置封鎖
                user.is_locked = True
                user.locked_at = datetime.now()
                user.locked_reason = f"{reason.value}: {details}"

                # 設置自動解封時間
                unlock_time = datetime.now() + timedelta(seconds=duration_seconds)

                # 記錄安全事件
                self._log_security_event(
                    session,
                    user_id,
                    "user_blocked_temporarily",
                    "high",
                    f"使用者被臨時封鎖: {reason.value}",
                    {
                        "reason": reason.value,
                        "details": details,
                        "duration_seconds": duration_seconds,
                        "unlock_time": unlock_time.isoformat(),
                    }
                )

                session.commit()

                logger.warning(f"使用者 {user_id} 被臨時封鎖 {duration_seconds} 秒，原因: {reason.value}")
                return True

        except Exception as e:
            logger.error(f"臨時封鎖使用者失敗: {e}")
            return False

    def unblock_user(self, user_id: str, reason: str = "") -> bool:
        """解除使用者封鎖"""
        try:
            with self.session_factory() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if not user:
                    return False

                # 解除封鎖
                user.is_locked = False
                user.locked_at = None
                user.locked_reason = None
                user.failed_login_attempts = 0

                # 記錄安全事件
                self._log_security_event(
                    session,
                    user_id,
                    "user_unblocked",
                    "medium",
                    f"使用者封鎖已解除: {reason}",
                    {"reason": reason}
                )

                session.commit()

                logger.info(f"使用者 {user_id} 封鎖已解除，原因: {reason}")
                return True

        except Exception as e:
            logger.error(f"解除使用者封鎖失敗: {e}")
            return False

    def get_risk_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """獲取風險統計"""
        try:
            with self.session_factory() as session:
                stats = {
                    "total_events": 0,
                    "high_risk_events": 0,
                    "blocked_attempts": 0,
                    "unique_ips": 0,
                    "geographic_anomalies": 0,
                    "device_anomalies": 0,
                    "time_anomalies": 0,
                }

                # 查詢條件
                query_filter = []
                if user_id:
                    query_filter.append(SecurityEvent.user_id == user_id)

                # 最近24小時的事件
                since = datetime.now() - timedelta(hours=24)
                query_filter.append(SecurityEvent.created_at >= since)

                # 獲取統計資料
                events = session.query(SecurityEvent).filter(and_(*query_filter)).all()

                stats["total_events"] = len(events)

                for event in events:
                    details = event.event_details or {}

                    # 高風險事件
                    if event.event_level in ["high", "critical"]:
                        stats["high_risk_events"] += 1

                    # 封鎖嘗試
                    if "blocked" in event.event_type:
                        stats["blocked_attempts"] += 1

                    # 地理異常
                    if "geographic" in str(details):
                        stats["geographic_anomalies"] += 1

                    # 設備異常
                    if "device" in str(details):
                        stats["device_anomalies"] += 1

                    # 時間異常
                    if "time" in str(details):
                        stats["time_anomalies"] += 1

                # 唯一 IP 數量
                unique_ips = set(event.ip_address for event in events if event.ip_address)
                stats["unique_ips"] = len(unique_ips)

                return stats

        except Exception as e:
            logger.error(f"獲取風險統計失敗: {e}")
            return {}

    def _get_risk_level(self, risk_score: float) -> RiskLevel:
        """根據風險分數確定風險等級"""
        thresholds = self.config["risk_thresholds"]

        if risk_score >= thresholds[RiskLevel.CRITICAL]:
            return RiskLevel.CRITICAL
        elif risk_score >= thresholds[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        elif risk_score >= thresholds[RiskLevel.MEDIUM]:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _should_allow_login(self, risk_score: float, anomalies: List[str]) -> bool:
        """決定是否允許登入"""
        # 檢查是否超過自動封鎖閾值
        if risk_score >= self.config["auto_block_threshold"]:
            return False

        # 檢查關鍵異常
        critical_anomalies = [
            "IP 在黑名單中",
            "疑似暴力破解攻擊",
            "可疑 IP 地址",
        ]

        for anomaly in anomalies:
            if any(critical in anomaly for critical in critical_anomalies):
                return False

        return True

    def _auto_block_user(
        self,
        user_id: str,
        ip_address: str,
        anomalies: List[str],
        risk_score: float
    ) -> None:
        """自動封鎖使用者"""
        try:
            # 確定封鎖原因
            if "暴力破解" in str(anomalies):
                reason = BlockReason.FAILED_ATTEMPTS
            elif "可疑 IP" in str(anomalies):
                reason = BlockReason.SUSPICIOUS_IP
            elif "地理位置異常" in str(anomalies):
                reason = BlockReason.GEOGRAPHIC_ANOMALY
            else:
                reason = BlockReason.ANOMALOUS_BEHAVIOR

            # 執行封鎖
            details = f"風險分數: {risk_score:.2f}, 異常: {', '.join(anomalies)}"
            self.block_user_temporarily(
                user_id,
                self.config["temp_block_duration"],
                reason,
                details
            )

            # 如果是可疑 IP，也加入黑名單
            if reason == BlockReason.SUSPICIOUS_IP:
                self.add_ip_to_blacklist(ip_address, f"自動封鎖，風險分數: {risk_score:.2f}")

        except Exception as e:
            logger.error(f"自動封鎖使用者失敗: {e}")

    def _log_analysis_result(
        self,
        user_id: str,
        ip_address: str,
        risk_score: float,
        risk_level: RiskLevel,
        anomalies: List[str],
        allowed: bool
    ) -> None:
        """記錄分析結果"""
        try:
            with self.session_factory() as session:
                self._log_security_event(
                    session,
                    user_id,
                    "anomaly_analysis",
                    risk_level.value,
                    f"異常檢測分析完成",
                    {
                        "risk_score": risk_score,
                        "risk_level": risk_level.value,
                        "anomalies": anomalies,
                        "allowed": allowed,
                        "ip_address": ip_address,
                    }
                )
                session.commit()

        except Exception as e:
            logger.error(f"記錄分析結果失敗: {e}")

    # 輔助方法
    def _load_ip_lists(self) -> None:
        """載入 IP 白名單和黑名單"""
        try:
            # 預設白名單 IP
            default_whitelist = {
                "127.0.0.1",
                "::1",
                "localhost",
            }
            self._ip_whitelist.update(default_whitelist)

            # 從資料庫載入（簡化實作）
            # 實際應該從資料庫或配置文件載入

        except Exception as e:
            logger.error(f"載入 IP 列表失敗: {e}")

    def _load_user_patterns(self) -> None:
        """載入使用者行為模式"""
        try:
            # 從資料庫載入使用者歷史模式
            # 簡化實作
            pass
        except Exception as e:
            logger.error(f"載入使用者模式失敗: {e}")

    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """檢查是否為可疑 IP"""
        try:
            # 檢查是否為已知惡意 IP
            # 這裡可以整合威脅情報 API

            # 簡化實作：檢查一些基本規則
            ip = ipaddress.ip_address(ip_address)

            # 檢查是否為私有 IP
            if ip.is_private:
                return False

            # 檢查是否為保留 IP
            if ip.is_reserved:
                return True

            # 可以添加更多檢查邏輯
            return False

        except Exception as e:
            logger.error(f"檢查可疑 IP 失敗: {e}")
            return False

    def _is_tor_or_proxy_ip(self, ip_address: str) -> bool:
        """檢查是否為 Tor 或代理 IP"""
        try:
            # 這裡可以整合 Tor 出口節點列表或代理檢測服務
            # 簡化實作
            return False
        except Exception as e:
            logger.error(f"檢查 Tor/代理 IP 失敗: {e}")
            return False

    def _get_user_recent_ips(self, user_id: str) -> Set[str]:
        """獲取使用者最近使用的 IP"""
        try:
            recent_events = self._recent_events.get(user_id, [])
            return {event["ip_address"] for event in recent_events}
        except Exception as e:
            logger.error(f"獲取使用者最近 IP 失敗: {e}")
            return set()

    def _count_recent_ip_changes(self, user_id: str) -> int:
        """計算最近的 IP 變更次數"""
        try:
            recent_events = list(self._recent_events.get(user_id, []))
            if len(recent_events) < 2:
                return 0

            # 計算最近1小時內的 IP 變更
            cutoff_time = datetime.now() - timedelta(hours=1)
            recent_ips = []

            for event in reversed(recent_events):
                if event["timestamp"] >= cutoff_time:
                    recent_ips.append(event["ip_address"])

            # 計算唯一 IP 數量
            return len(set(recent_ips)) - 1  # 減1因為當前IP不算變更

        except Exception as e:
            logger.error(f"計算 IP 變更次數失敗: {e}")
            return 0

    def _count_recent_failures(self, user_id: str) -> int:
        """計算最近的失敗次數"""
        try:
            recent_events = self._recent_events.get(user_id, [])
            cutoff_time = datetime.now() - timedelta(seconds=self.config["failed_attempts_window"])

            failures = 0
            for event in recent_events:
                if (event["timestamp"] >= cutoff_time and
                    not event["success"]):
                    failures += 1

            return failures

        except Exception as e:
            logger.error(f"計算失敗次數失敗: {e}")
            return 0

    def _analyze_failure_pattern(self, user_id: str) -> Dict[str, Any]:
        """分析失敗模式"""
        try:
            recent_events = list(self._recent_events.get(user_id, []))

            # 檢查是否為暴力破解模式
            failure_intervals = []
            last_failure_time = None

            for event in reversed(recent_events):
                if not event["success"]:
                    if last_failure_time:
                        interval = (last_failure_time - event["timestamp"]).total_seconds()
                        failure_intervals.append(interval)
                    last_failure_time = event["timestamp"]

            # 如果失敗間隔很短且規律，可能是暴力破解
            is_brute_force = False
            if len(failure_intervals) >= 3:
                avg_interval = sum(failure_intervals) / len(failure_intervals)
                if avg_interval < 10:  # 平均間隔小於10秒
                    is_brute_force = True

            return {
                "is_brute_force": is_brute_force,
                "failure_count": len(failure_intervals) + 1,
                "avg_interval": sum(failure_intervals) / len(failure_intervals) if failure_intervals else 0,
            }

        except Exception as e:
            logger.error(f"分析失敗模式失敗: {e}")
            return {"is_brute_force": False}

    def _get_ip_location(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """獲取 IP 地理位置"""
        try:
            # 這裡可以整合地理位置 API（如 MaxMind GeoIP）
            # 簡化實作，返回模擬資料
            return {
                "country": "TW",
                "city": "Taipei",
                "latitude": 25.0330,
                "longitude": 121.5654,
            }
        except Exception as e:
            logger.error(f"獲取 IP 地理位置失敗: {e}")
            return None

    def _get_user_locations(self, user_id: str) -> List[Dict[str, Any]]:
        """獲取使用者歷史位置"""
        try:
            # 從使用者模式中獲取歷史位置
            user_pattern = self._user_patterns.get(user_id, {})
            return user_pattern.get("locations", [])
        except Exception as e:
            logger.error(f"獲取使用者位置失敗: {e}")
            return []

    def _calculate_distance(self, loc1: Dict[str, Any], loc2: Dict[str, Any]) -> float:
        """計算兩個地理位置之間的距離（公里）"""
        try:
            import math

            lat1, lon1 = loc1["latitude"], loc1["longitude"]
            lat2, lon2 = loc2["latitude"], loc2["longitude"]

            # 使用 Haversine 公式
            R = 6371  # 地球半徑（公里）

            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)

            a = (math.sin(dlat/2) * math.sin(dlat/2) +
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
                 math.sin(dlon/2) * math.sin(dlon/2))

            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance = R * c

            return distance

        except Exception as e:
            logger.error(f"計算距離失敗: {e}")
            return 0.0

    def _generate_device_fingerprint(self, user_agent: str) -> str:
        """生成設備指紋"""
        try:
            # 簡化的設備指紋生成
            return hashlib.md5(user_agent.encode()).hexdigest()
        except Exception as e:
            logger.error(f"生成設備指紋失敗: {e}")
            return "unknown"

    def _get_user_devices(self, user_id: str) -> Set[str]:
        """獲取使用者設備歷史"""
        try:
            user_pattern = self._user_patterns.get(user_id, {})
            return set(user_pattern.get("devices", []))
        except Exception as e:
            logger.error(f"獲取使用者設備失敗: {e}")
            return set()

    def _count_recent_device_changes(self, user_id: str) -> int:
        """計算最近的設備變更次數"""
        try:
            recent_events = list(self._recent_events.get(user_id, []))
            cutoff_time = datetime.now() - timedelta(hours=24)

            recent_devices = []
            for event in recent_events:
                if event["timestamp"] >= cutoff_time:
                    device_fp = self._generate_device_fingerprint(event["user_agent"])
                    recent_devices.append(device_fp)

            return len(set(recent_devices)) - 1

        except Exception as e:
            logger.error(f"計算設備變更次數失敗: {e}")
            return 0

    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """檢查是否為可疑的 User-Agent"""
        try:
            suspicious_patterns = [
                "bot",
                "crawler",
                "spider",
                "scraper",
                "python",
                "curl",
                "wget",
            ]

            user_agent_lower = user_agent.lower()
            return any(pattern in user_agent_lower for pattern in suspicious_patterns)

        except Exception as e:
            logger.error(f"檢查可疑 User-Agent 失敗: {e}")
            return False

    def _count_user_night_logins(self, user_id: str) -> int:
        """計算使用者夜間登入次數"""
        try:
            user_pattern = self._user_patterns.get(user_id, {})
            return user_pattern.get("night_logins", 0)
        except Exception as e:
            logger.error(f"計算夜間登入次數失敗: {e}")
            return 0

    def _analyze_login_frequency(self, user_id: str) -> Dict[str, Any]:
        """分析登入頻率"""
        try:
            recent_events = list(self._recent_events.get(user_id, []))

            # 計算最近24小時的登入次數
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_logins = [
                event for event in recent_events
                if event["timestamp"] >= cutoff_time and event["success"]
            ]

            login_count = len(recent_logins)

            # 判斷是否異常（簡化邏輯）
            is_unusual = login_count > 20  # 24小時內超過20次登入

            return {
                "login_count_24h": login_count,
                "is_unusual": is_unusual,
            }

        except Exception as e:
            logger.error(f"分析登入頻率失敗: {e}")
            return {"is_unusual": False}

    def _get_login_intervals(self, user_id: str) -> List[float]:
        """獲取登入間隔"""
        try:
            recent_events = list(self._recent_events.get(user_id, []))
            successful_logins = [
                event for event in recent_events if event["success"]
            ]

            if len(successful_logins) < 2:
                return []

            # 按時間排序
            successful_logins.sort(key=lambda x: x["timestamp"])

            intervals = []
            for i in range(1, len(successful_logins)):
                interval = (successful_logins[i]["timestamp"] -
                           successful_logins[i-1]["timestamp"]).total_seconds()
                intervals.append(interval)

            return intervals

        except Exception as e:
            logger.error(f"獲取登入間隔失敗: {e}")
            return []

    def _is_unusual_interval_pattern(self, intervals: List[float]) -> bool:
        """檢查登入間隔是否異常"""
        try:
            if len(intervals) < 3:
                return False

            # 檢查是否有過於規律的間隔（可能是自動化攻擊）
            avg_interval = sum(intervals) / len(intervals)

            # 如果平均間隔很短且變化很小，可能是異常
            if avg_interval < 60:  # 平均間隔小於1分鐘
                variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
                if variance < 100:  # 變化很小
                    return True

            return False

        except Exception as e:
            logger.error(f"檢查間隔模式失敗: {e}")
            return False

    def _get_session_durations(self, user_id: str) -> List[float]:
        """獲取會話持續時間"""
        try:
            # 簡化實作，返回空列表
            # 實際應該從會話管理系統獲取
            return []
        except Exception as e:
            logger.error(f"獲取會話持續時間失敗: {e}")
            return []

    def _is_unusual_session_pattern(self, durations: List[float]) -> bool:
        """檢查會話持續時間是否異常"""
        try:
            if len(durations) < 3:
                return False

            # 檢查是否有異常短的會話（可能是自動化）
            avg_duration = sum(durations) / len(durations)
            short_sessions = [d for d in durations if d < 60]  # 小於1分鐘

            if len(short_sessions) > len(durations) * 0.5:  # 超過一半是短會話
                return True

            return False

        except Exception as e:
            logger.error(f"檢查會話模式失敗: {e}")
            return False

    def _save_ip_list_change(
        self,
        list_type: str,
        action: str,
        ip_address: str,
        reason: str = ""
    ) -> None:
        """保存 IP 列表變更"""
        try:
            with self.session_factory() as session:
                self._log_security_event(
                    session,
                    None,  # 系統操作
                    f"ip_{list_type}_{action}",
                    "medium",
                    f"IP {action} {list_type}: {ip_address}",
                    {
                        "list_type": list_type,
                        "action": action,
                        "ip_address": ip_address,
                        "reason": reason,
                    }
                )
                session.commit()

        except Exception as e:
            logger.error(f"保存 IP 列表變更失敗: {e}")

    def _log_security_event(
        self,
        session: Session,
        user_id: Optional[str],
        event_type: str,
        severity: str,
        description: str,
        details: Dict[str, Any]
    ) -> None:
        """記錄安全事件"""
        try:
            import secrets

            event = SecurityEvent(
                event_id=secrets.token_urlsafe(16),
                event_type=event_type,
                event_level=severity,
                user_id=user_id,
                description=description,
                event_details=details,
                ip_address=details.get("ip_address", "127.0.0.1"),
                user_agent="AnomalyDetectionService",
                created_at=datetime.now()
            )

            session.add(event)

        except Exception as e:
            logger.error(f"記錄安全事件失敗: {e}")


# 全域實例
anomaly_detector = AnomalyDetectionService()
