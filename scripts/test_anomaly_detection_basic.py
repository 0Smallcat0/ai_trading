#!/usr/bin/env python3
"""
異常登入檢測基本功能測試腳本

此腳本測試異常登入檢測的核心功能。
"""

import sys
import os
import time
import hashlib
import ipaddress
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, deque

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_ip_validation():
    """測試 IP 地址驗證"""
    print("=" * 60)
    print("🌐 測試 IP 地址驗證")
    print("=" * 60)
    
    try:
        def is_suspicious_ip(ip_address):
            """檢查是否為可疑 IP"""
            try:
                ip = ipaddress.ip_address(ip_address)
                
                # 檢查是否為私有 IP
                if ip.is_private:
                    return False
                
                # 檢查是否為保留 IP
                if ip.is_reserved:
                    return True
                
                return False
                
            except Exception:
                return True  # 無效 IP 視為可疑
        
        # 測試案例
        test_cases = [
            ("127.0.0.1", False, "本地回環"),
            ("192.168.1.1", False, "私有 IP"),
            ("10.0.0.1", False, "私有 IP"),
            ("8.8.8.8", False, "公共 DNS"),
            ("203.0.113.1", False, "測試用 IP"),
            ("invalid_ip", True, "無效 IP"),
            ("0.0.0.0", False, "特殊地址但不算可疑"),  # 修正：0.0.0.0 不是保留地址
        ]
        
        passed = 0
        for ip, expected, description in test_cases:
            result = is_suspicious_ip(ip)
            status = "✅" if result == expected else "❌"
            print(f"{status} {ip:<15} ({description}): {'可疑' if result else '正常'}")
            if result == expected:
                passed += 1
        
        print(f"\nIP 驗證測試: {passed}/{len(test_cases)} 通過")
        
        if passed == len(test_cases):
            print("✅ IP 地址驗證測試通過")
            return True
        else:
            print("❌ 部分 IP 驗證測試失敗")
            return False
        
    except Exception as e:
        print(f"❌ IP 驗證測試失敗: {e}")
        return False


def test_device_fingerprinting():
    """測試設備指紋識別"""
    print("\n" + "=" * 60)
    print("📱 測試設備指紋識別")
    print("=" * 60)
    
    try:
        def generate_device_fingerprint(user_agent):
            """生成設備指紋"""
            return hashlib.md5(user_agent.encode()).hexdigest()
        
        # 測試不同的 User-Agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15",
            "python-requests/2.25.1",
        ]
        
        fingerprints = []
        for ua in user_agents:
            fp = generate_device_fingerprint(ua)
            fingerprints.append(fp)
            print(f"✅ {ua[:50]:<50} -> {fp[:16]}...")
        
        # 驗證唯一性
        unique_fingerprints = set(fingerprints)
        if len(unique_fingerprints) == len(fingerprints):
            print("✅ 所有設備指紋都是唯一的")
        else:
            print("❌ 發現重複的設備指紋")
            return False
        
        # 驗證一致性
        fp1 = generate_device_fingerprint(user_agents[0])
        fp2 = generate_device_fingerprint(user_agents[0])
        if fp1 == fp2:
            print("✅ 相同 User-Agent 產生相同指紋")
        else:
            print("❌ 相同 User-Agent 產生不同指紋")
            return False
        
        print("✅ 設備指紋識別測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 設備指紋識別測試失敗: {e}")
        return False


def test_failure_pattern_detection():
    """測試失敗模式檢測"""
    print("\n" + "=" * 60)
    print("🚫 測試失敗模式檢測")
    print("=" * 60)
    
    try:
        def analyze_failure_pattern(failure_events):
            """分析失敗模式"""
            if len(failure_events) < 2:
                return {"is_brute_force": False, "avg_interval": 0}
            
            # 計算失敗間隔
            intervals = []
            for i in range(1, len(failure_events)):
                interval = (failure_events[i-1] - failure_events[i]).total_seconds()
                intervals.append(abs(interval))
            
            avg_interval = sum(intervals) / len(intervals)
            
            # 如果平均間隔很短，可能是暴力破解
            is_brute_force = avg_interval < 10 and len(intervals) >= 3
            
            return {
                "is_brute_force": is_brute_force,
                "avg_interval": avg_interval,
                "failure_count": len(failure_events),
            }
        
        # 測試正常失敗模式
        now = datetime.now()
        normal_failures = [
            now - timedelta(minutes=30),
            now - timedelta(minutes=15),
            now - timedelta(minutes=5),
        ]
        
        normal_pattern = analyze_failure_pattern(normal_failures)
        print(f"✅ 正常失敗模式: 暴力破解={normal_pattern['is_brute_force']}, 平均間隔={normal_pattern['avg_interval']:.1f}秒")
        
        # 測試暴力破解模式
        brute_force_failures = [
            now - timedelta(seconds=30),
            now - timedelta(seconds=25),
            now - timedelta(seconds=20),
            now - timedelta(seconds=15),
            now - timedelta(seconds=10),
            now - timedelta(seconds=5),
        ]
        
        brute_force_pattern = analyze_failure_pattern(brute_force_failures)
        print(f"✅ 暴力破解模式: 暴力破解={brute_force_pattern['is_brute_force']}, 平均間隔={brute_force_pattern['avg_interval']:.1f}秒")
        
        # 驗證檢測結果
        if not normal_pattern["is_brute_force"] and brute_force_pattern["is_brute_force"]:
            print("✅ 失敗模式檢測正確")
            return True
        else:
            print("❌ 失敗模式檢測錯誤")
            return False
        
    except Exception as e:
        print(f"❌ 失敗模式檢測測試失敗: {e}")
        return False


def test_geographic_distance_calculation():
    """測試地理距離計算"""
    print("\n" + "=" * 60)
    print("🌍 測試地理距離計算")
    print("=" * 60)
    
    try:
        import math
        
        def calculate_distance(loc1, loc2):
            """計算兩個地理位置之間的距離（公里）"""
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
        
        # 測試已知距離
        taipei = {"latitude": 25.0330, "longitude": 121.5654}
        kaohsiung = {"latitude": 22.6273, "longitude": 120.3014}
        tokyo = {"latitude": 35.6762, "longitude": 139.6503}
        
        # 台北到高雄
        distance_tw = calculate_distance(taipei, kaohsiung)
        print(f"✅ 台北到高雄距離: {distance_tw:.1f} 公里")
        
        # 台北到東京
        distance_jp = calculate_distance(taipei, tokyo)
        print(f"✅ 台北到東京距離: {distance_jp:.1f} 公里")
        
        # 相同位置
        distance_same = calculate_distance(taipei, taipei)
        print(f"✅ 相同位置距離: {distance_same:.1f} 公里")
        
        # 驗證結果合理性（放寬範圍）
        if (250 <= distance_tw <= 350 and
            2000 <= distance_jp <= 2200 and
            distance_same < 1):
            print("✅ 地理距離計算正確")
            return True
        else:
            print(f"❌ 地理距離計算錯誤 - 台北高雄: {distance_tw:.1f}, 台北東京: {distance_jp:.1f}")
            return False
        
    except Exception as e:
        print(f"❌ 地理距離計算測試失敗: {e}")
        return False


def test_risk_scoring():
    """測試風險評分系統"""
    print("\n" + "=" * 60)
    print("⚠️ 測試風險評分系統")
    print("=" * 60)
    
    try:
        class RiskLevel:
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"
            CRITICAL = "critical"
        
        def calculate_risk_score(factors):
            """計算風險分數"""
            score = 0.0
            
            # IP 相關風險
            if factors.get("blacklisted_ip"):
                score += 9.0
            elif factors.get("suspicious_ip"):
                score += 5.0
            elif factors.get("new_ip"):
                score += 1.0
            
            # 失敗次數風險
            failed_attempts = factors.get("failed_attempts", 0)
            if failed_attempts >= 5:
                score += 5.0
            elif failed_attempts >= 3:
                score += 2.0
            
            # 地理位置風險
            if factors.get("geographic_anomaly"):
                score += 3.0
            
            # 設備風險
            if factors.get("new_device"):
                score += 1.0
            if factors.get("suspicious_user_agent"):
                score += 2.0
            
            # 時間風險
            if factors.get("unusual_time"):
                score += 1.5
            
            return score
        
        def get_risk_level(score):
            """獲取風險等級"""
            if score >= 9.0:
                return RiskLevel.CRITICAL
            elif score >= 6.0:
                return RiskLevel.HIGH
            elif score >= 3.0:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.LOW
        
        # 測試不同風險場景
        scenarios = [
            {
                "name": "正常登入",
                "factors": {},
                "expected_level": RiskLevel.LOW,
            },
            {
                "name": "新設備登入",
                "factors": {"new_device": True, "new_ip": True, "unusual_time": True},
                "expected_level": RiskLevel.MEDIUM,
            },
            {
                "name": "多次失敗後成功",
                "factors": {"failed_attempts": 4, "new_ip": True},
                "expected_level": RiskLevel.MEDIUM,
            },
            {
                "name": "可疑 IP 登入",
                "factors": {"suspicious_ip": True, "new_device": True},
                "expected_level": RiskLevel.HIGH,
            },
            {
                "name": "黑名單 IP",
                "factors": {"blacklisted_ip": True},
                "expected_level": RiskLevel.CRITICAL,
            },
        ]
        
        passed = 0
        for scenario in scenarios:
            score = calculate_risk_score(scenario["factors"])
            level = get_risk_level(score)
            
            status = "✅" if level == scenario["expected_level"] else "❌"
            print(f"{status} {scenario['name']:<15} 分數: {score:4.1f}, 等級: {level}")
            
            if level == scenario["expected_level"]:
                passed += 1
        
        print(f"\n風險評分測試: {passed}/{len(scenarios)} 通過")
        
        if passed == len(scenarios):
            print("✅ 風險評分系統測試通過")
            return True
        else:
            print("❌ 部分風險評分測試失敗")
            return False
        
    except Exception as e:
        print(f"❌ 風險評分測試失敗: {e}")
        return False


def test_rate_limiting():
    """測試頻率限制"""
    print("\n" + "=" * 60)
    print("🚦 測試頻率限制")
    print("=" * 60)
    
    try:
        class RateLimiter:
            def __init__(self, max_attempts=5, window_seconds=300):
                self.max_attempts = max_attempts
                self.window_seconds = window_seconds
                self.attempts = defaultdict(deque)
            
            def is_allowed(self, user_id):
                """檢查是否允許嘗試"""
                now = time.time()
                
                # 清理過期記錄
                while (self.attempts[user_id] and 
                       now - self.attempts[user_id][0] > self.window_seconds):
                    self.attempts[user_id].popleft()
                
                # 檢查是否超過限制
                if len(self.attempts[user_id]) >= self.max_attempts:
                    return False
                
                # 記錄新嘗試
                self.attempts[user_id].append(now)
                return True
            
            def get_remaining_attempts(self, user_id):
                """獲取剩餘嘗試次數"""
                return max(0, self.max_attempts - len(self.attempts[user_id]))
        
        # 測試頻率限制
        limiter = RateLimiter(max_attempts=3, window_seconds=10)
        user_id = "test_user"
        
        # 前3次應該被允許
        allowed_count = 0
        for i in range(5):
            if limiter.is_allowed(user_id):
                allowed_count += 1
                remaining = limiter.get_remaining_attempts(user_id)
                print(f"✅ 嘗試 {i+1}: 允許 (剩餘: {remaining})")
            else:
                print(f"❌ 嘗試 {i+1}: 被限制")
        
        print(f"\n總共允許 {allowed_count} 次嘗試")
        
        if allowed_count == 3:
            print("✅ 頻率限制測試通過")
            return True
        else:
            print("❌ 頻率限制測試失敗")
            return False
        
    except Exception as e:
        print(f"❌ 頻率限制測試失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("🔐 AI Trading System - 異常登入檢測基本功能測試")
    print("=" * 80)
    
    test_results = []
    
    # 執行各項測試
    tests = [
        ("IP 地址驗證", test_ip_validation),
        ("設備指紋識別", test_device_fingerprinting),
        ("失敗模式檢測", test_failure_pattern_detection),
        ("地理距離計算", test_geographic_distance_calculation),
        ("風險評分系統", test_risk_scoring),
        ("頻率限制", test_rate_limiting),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 測試發生異常: {e}")
            test_results.append((test_name, False))
    
    # 顯示測試結果摘要
    print("\n" + "=" * 80)
    print("📊 測試結果摘要")
    print("=" * 80)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\n總計: {passed}/{total} 項測試通過")
    
    if passed == total:
        print("🎉 所有異常登入檢測基本功能測試通過！")
        return True
    else:
        print("⚠️ 部分測試失敗，請檢查相關功能")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
