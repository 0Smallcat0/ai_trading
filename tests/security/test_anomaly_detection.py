"""
異常登入檢測測試

此模組測試異常登入檢測和自動封鎖功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.core.anomaly_detection_service import (
    AnomalyDetectionService, 
    RiskLevel, 
    BlockReason
)


class TestAnomalyDetectionService:
    """測試 AnomalyDetectionService 類別"""
    
    @pytest.fixture
    def anomaly_service(self):
        """創建 AnomalyDetectionService 實例"""
        with patch('src.core.anomaly_detection_service.create_engine'):
            service = AnomalyDetectionService()
            return service
    
    def test_analyze_login_attempt_normal(self, anomaly_service):
        """測試正常登入分析"""
        # 模擬正常登入
        allowed, risk_score, anomalies = anomaly_service.analyze_login_attempt(
            user_id="test_user",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            success=True
        )
        
        assert allowed is True
        assert risk_score < 5.0  # 正常情況下風險分數應該較低
        assert len(anomalies) == 0 or all("異常" not in anomaly for anomaly in anomalies)
    
    def test_analyze_login_attempt_failed(self, anomaly_service):
        """測試失敗登入分析"""
        # 模擬多次失敗登入
        for i in range(6):  # 超過最大失敗次數
            allowed, risk_score, anomalies = anomaly_service.analyze_login_attempt(
                user_id="test_user",
                ip_address="192.168.1.100",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                success=False
            )
        
        # 最後一次應該被封鎖
        assert allowed is False
        assert risk_score >= 5.0
        assert any("失敗" in anomaly for anomaly in anomalies)
    
    def test_ip_whitelist_management(self, anomaly_service):
        """測試 IP 白名單管理"""
        test_ip = "203.0.113.1"
        
        # 添加到白名單
        result = anomaly_service.add_ip_to_whitelist(test_ip, "測試用途")
        assert result is True
        assert test_ip in anomaly_service._ip_whitelist
        
        # 從白名單移除
        result = anomaly_service.remove_ip_from_whitelist(test_ip)
        assert result is True
        assert test_ip not in anomaly_service._ip_whitelist
    
    def test_ip_blacklist_management(self, anomaly_service):
        """測試 IP 黑名單管理"""
        test_ip = "203.0.113.2"
        
        # 添加到黑名單
        result = anomaly_service.add_ip_to_blacklist(test_ip, "惡意 IP")
        assert result is True
        assert test_ip in anomaly_service._ip_blacklist
        
        # 測試黑名單 IP 登入
        allowed, risk_score, anomalies = anomaly_service.analyze_login_attempt(
            user_id="test_user",
            ip_address=test_ip,
            user_agent="Mozilla/5.0",
            success=True
        )
        
        assert allowed is False
        assert risk_score >= 9.0
        assert "黑名單" in str(anomalies)
        
        # 從黑名單移除
        result = anomaly_service.remove_ip_from_blacklist(test_ip)
        assert result is True
        assert test_ip not in anomaly_service._ip_blacklist
    
    def test_suspicious_user_agent_detection(self, anomaly_service):
        """測試可疑 User-Agent 檢測"""
        suspicious_agents = [
            "python-requests/2.25.1",
            "curl/7.68.0",
            "bot/1.0",
            "spider/2.0",
        ]
        
        for agent in suspicious_agents:
            is_suspicious = anomaly_service._is_suspicious_user_agent(agent)
            assert is_suspicious is True
        
        # 正常的 User-Agent
        normal_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        is_suspicious = anomaly_service._is_suspicious_user_agent(normal_agent)
        assert is_suspicious is False
    
    def test_device_fingerprint_generation(self, anomaly_service):
        """測試設備指紋生成"""
        user_agent1 = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        user_agent2 = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        
        fingerprint1 = anomaly_service._generate_device_fingerprint(user_agent1)
        fingerprint2 = anomaly_service._generate_device_fingerprint(user_agent2)
        
        # 不同的 User-Agent 應該產生不同的指紋
        assert fingerprint1 != fingerprint2
        assert len(fingerprint1) == 32  # MD5 雜湊長度
        assert len(fingerprint2) == 32
        
        # 相同的 User-Agent 應該產生相同的指紋
        fingerprint1_repeat = anomaly_service._generate_device_fingerprint(user_agent1)
        assert fingerprint1 == fingerprint1_repeat
    
    def test_risk_level_calculation(self, anomaly_service):
        """測試風險等級計算"""
        # 測試不同風險分數對應的等級
        test_cases = [
            (1.0, RiskLevel.LOW),
            (4.0, RiskLevel.MEDIUM),
            (7.0, RiskLevel.HIGH),
            (9.5, RiskLevel.CRITICAL),
        ]
        
        for score, expected_level in test_cases:
            level = anomaly_service._get_risk_level(score)
            assert level == expected_level
    
    def test_login_frequency_analysis(self, anomaly_service):
        """測試登入頻率分析"""
        user_id = "test_user"
        
        # 模擬正常登入頻率
        for i in range(5):
            anomaly_service._recent_events[user_id].append({
                "timestamp": datetime.now() - timedelta(hours=i*2),
                "success": True,
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0",
            })
        
        frequency_analysis = anomaly_service._analyze_login_frequency(user_id)
        assert frequency_analysis["login_count_24h"] == 5
        assert frequency_analysis["is_unusual"] is False
        
        # 模擬異常高頻登入
        for i in range(20):
            anomaly_service._recent_events[user_id].append({
                "timestamp": datetime.now() - timedelta(minutes=i*30),
                "success": True,
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0",
            })
        
        frequency_analysis = anomaly_service._analyze_login_frequency(user_id)
        assert frequency_analysis["is_unusual"] is True
    
    def test_failure_pattern_analysis(self, anomaly_service):
        """測試失敗模式分析"""
        user_id = "test_user"
        
        # 模擬暴力破解模式（短間隔連續失敗）
        base_time = datetime.now()
        for i in range(5):
            anomaly_service._recent_events[user_id].append({
                "timestamp": base_time - timedelta(seconds=i*5),
                "success": False,
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0",
            })
        
        pattern = anomaly_service._analyze_failure_pattern(user_id)
        assert pattern["is_brute_force"] is True
        assert pattern["failure_count"] >= 5
        assert pattern["avg_interval"] < 10
    
    def test_ip_change_detection(self, anomaly_service):
        """測試 IP 變更檢測"""
        user_id = "test_user"
        
        # 模擬頻繁的 IP 變更
        ips = ["192.168.1.100", "192.168.1.101", "192.168.1.102", "192.168.1.103"]
        base_time = datetime.now()
        
        for i, ip in enumerate(ips):
            anomaly_service._recent_events[user_id].append({
                "timestamp": base_time - timedelta(minutes=i*10),
                "success": True,
                "ip_address": ip,
                "user_agent": "Mozilla/5.0",
            })
        
        ip_changes = anomaly_service._count_recent_ip_changes(user_id)
        assert ip_changes >= 3  # 4個不同IP，所以有3次變更
    
    def test_geographic_distance_calculation(self, anomaly_service):
        """測試地理距離計算"""
        # 台北和高雄的大概位置
        taipei = {"latitude": 25.0330, "longitude": 121.5654}
        kaohsiung = {"latitude": 22.6273, "longitude": 120.3014}
        
        distance = anomaly_service._calculate_distance(taipei, kaohsiung)
        
        # 台北到高雄大約350公里
        assert 300 <= distance <= 400
        
        # 相同位置的距離應該接近0
        same_distance = anomaly_service._calculate_distance(taipei, taipei)
        assert same_distance < 1
    
    @patch.object(AnomalyDetectionService, 'block_user_temporarily')
    def test_auto_blocking(self, mock_block, anomaly_service):
        """測試自動封鎖功能"""
        # 啟用自動封鎖
        anomaly_service.config["auto_block_enabled"] = True
        anomaly_service.config["auto_block_threshold"] = 5.0
        
        # 模擬高風險登入嘗試
        with patch.object(anomaly_service, '_check_ip_anomalies') as mock_ip_check:
            mock_ip_check.return_value = (9.0, ["可疑 IP 地址"])
            
            allowed, risk_score, anomalies = anomaly_service.analyze_login_attempt(
                user_id="test_user",
                ip_address="203.0.113.1",
                user_agent="Mozilla/5.0",
                success=False
            )
            
            # 應該被自動封鎖
            assert allowed is False
            assert risk_score >= 5.0
            mock_block.assert_called_once()
    
    def test_time_pattern_analysis(self, anomaly_service):
        """測試時間模式分析"""
        # 測試夜間登入檢測
        with patch('src.core.anomaly_detection_service.datetime') as mock_datetime:
            # 模擬凌晨3點登入
            mock_datetime.now.return_value = datetime(2023, 1, 1, 3, 0, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            risk_score, anomalies = anomaly_service._check_time_patterns("test_user")
            
            # 如果使用者很少在夜間登入，應該有風險分數
            assert "異常時間" in str(anomalies) or risk_score > 0
    
    def test_interval_pattern_detection(self, anomaly_service):
        """測試間隔模式檢測"""
        # 正常間隔
        normal_intervals = [3600, 7200, 1800, 5400]  # 1-2小時間隔
        is_unusual = anomaly_service._is_unusual_interval_pattern(normal_intervals)
        assert is_unusual is False
        
        # 異常規律間隔（可能是自動化）
        regular_intervals = [30, 32, 28, 31, 29]  # 30秒左右的規律間隔
        is_unusual = anomaly_service._is_unusual_interval_pattern(regular_intervals)
        assert is_unusual is True
    
    @patch.object(AnomalyDetectionService, 'session_factory')
    def test_user_blocking_and_unblocking(self, mock_session_factory, anomaly_service):
        """測試使用者封鎖和解封"""
        # 設置模擬
        mock_session = Mock()
        mock_session_factory.return_value.__enter__.return_value = mock_session
        
        mock_user = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user
        
        # 測試臨時封鎖
        result = anomaly_service.block_user_temporarily(
            user_id="test_user",
            duration_seconds=3600,
            reason=BlockReason.SUSPICIOUS_IP,
            details="可疑 IP 登入"
        )
        
        assert result is True
        assert mock_user.is_locked is True
        assert mock_user.locked_reason is not None
        
        # 測試解封
        result = anomaly_service.unblock_user("test_user", "手動解封")
        
        assert result is True
        assert mock_user.is_locked is False
        assert mock_user.locked_at is None
        assert mock_user.failed_login_attempts == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
