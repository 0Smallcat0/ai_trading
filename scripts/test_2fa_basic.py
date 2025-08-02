#!/usr/bin/env python3
"""
基本 2FA 功能測試腳本

此腳本測試 2FA 核心功能的基本操作。
"""

import sys
import os
import time
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_backup_codes_generation():
    """測試備用碼生成"""
    print("=" * 60)
    print("🔑 測試備用碼生成")
    print("=" * 60)
    
    try:
        # 直接測試備用碼生成邏輯
        import secrets
        
        def generate_backup_codes(count=10):
            """生成備用碼"""
            codes = []
            for _ in range(count):
                code = ''.join([str(secrets.randbelow(10)) for _ in range(8)])
                codes.append(code)
            return codes
        
        codes = generate_backup_codes()
        
        print(f"✅ 成功生成 {len(codes)} 個備用碼")
        print("備用碼範例:")
        for i, code in enumerate(codes[:3]):
            print(f"  {i+1}. {code}")
        
        # 驗證備用碼格式
        assert len(codes) == 10, "備用碼數量不正確"
        assert all(len(code) == 8 for code in codes), "備用碼長度不正確"
        assert all(code.isdigit() for code in codes), "備用碼格式不正確"
        assert len(set(codes)) == 10, "備用碼有重複"
        
        print("✅ 備用碼格式驗證通過")
        return True
        
    except Exception as e:
        print(f"❌ 備用碼生成測試失敗: {e}")
        return False


def test_totp_functionality():
    """測試 TOTP 功能"""
    print("\n" + "=" * 60)
    print("🔐 測試 TOTP 功能")
    print("=" * 60)
    
    try:
        import pyotp
        import base64
        import io
        
        # 生成 secret
        secret = pyotp.random_base32()
        print(f"✅ 生成 TOTP secret: {secret[:8]}...")
        
        # 創建 TOTP 實例
        totp = pyotp.TOTP(secret)
        
        # 生成當前驗證碼
        current_code = totp.now()
        print(f"✅ 生成當前驗證碼: {current_code}")
        
        # 驗證碼驗證
        is_valid = totp.verify(current_code)
        print(f"✅ 驗證碼驗證結果: {is_valid}")
        
        # 生成 provisioning URI
        email = "test@example.com"
        issuer = "AI Trading System"
        provisioning_uri = totp.provisioning_uri(
            name=email,
            issuer_name=issuer
        )
        print(f"✅ 生成 provisioning URI: {provisioning_uri[:50]}...")
        
        assert is_valid, "TOTP 驗證失敗"
        assert len(current_code) == 6, "TOTP 碼長度不正確"
        assert current_code.isdigit(), "TOTP 碼格式不正確"
        
        print("✅ TOTP 功能測試通過")
        return True
        
    except ImportError as e:
        print(f"❌ 缺少必要的庫: {e}")
        print("請安裝: pip install pyotp")
        return False
    except Exception as e:
        print(f"❌ TOTP 功能測試失敗: {e}")
        return False


def test_qr_code_generation():
    """測試 QR 碼生成"""
    print("\n" + "=" * 60)
    print("📱 測試 QR 碼生成")
    print("=" * 60)
    
    try:
        import qrcode
        import pyotp
        import base64
        import io
        
        # 生成 TOTP 設定
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name="test@example.com",
            issuer_name="AI Trading System"
        )
        
        # 生成基本 QR 碼
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # 創建圖片
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 轉換為 Base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        print(f"✅ 成功生成 QR 碼 (Base64 長度: {len(img_str)})")
        print(f"✅ QR 碼數據: {provisioning_uri[:50]}...")
        
        assert len(img_str) > 0, "QR 碼生成失敗"
        assert img_str.startswith("iVBORw0KGgo"), "QR 碼格式不正確"
        
        print("✅ QR 碼生成測試通過")
        return True
        
    except ImportError as e:
        print(f"❌ 缺少必要的庫: {e}")
        print("請安裝: pip install qrcode[pil] pillow")
        return False
    except Exception as e:
        print(f"❌ QR 碼生成測試失敗: {e}")
        return False


def test_sms_verification_logic():
    """測試 SMS 驗證邏輯"""
    print("\n" + "=" * 60)
    print("📱 測試 SMS 驗證邏輯")
    print("=" * 60)
    
    try:
        import secrets
        import time
        
        # 模擬 SMS 服務
        class MockSMSService:
            def __init__(self):
                self.config = {
                    "code_length": 6,
                    "code_expiry": 300,  # 5 分鐘
                    "max_attempts": 3,
                    "rate_limit": 60,    # 1 分鐘
                }
                self._verification_codes = {}
                self._send_history = {}
            
            def send_verification_code(self, phone_number, user_id):
                # 檢查頻率限制
                if self._check_rate_limit(phone_number):
                    return False, "發送過於頻繁"
                
                # 生成驗證碼
                code = ''.join([str(secrets.randbelow(10)) for _ in range(self.config["code_length"])])
                
                # 存儲驗證碼
                self._verification_codes[phone_number] = {
                    "code": code,
                    "user_id": user_id,
                    "created_at": time.time(),
                    "attempts": 0,
                }
                
                self._send_history[phone_number] = time.time()
                return True, "驗證碼已發送"
            
            def verify_sms_code(self, phone_number, code, user_id):
                if phone_number not in self._verification_codes:
                    return False, "驗證碼不存在"
                
                verification_data = self._verification_codes[phone_number]
                
                # 檢查使用者 ID
                if verification_data["user_id"] != user_id:
                    return False, "驗證碼無效"
                
                # 檢查過期時間
                if time.time() - verification_data["created_at"] > self.config["code_expiry"]:
                    del self._verification_codes[phone_number]
                    return False, "驗證碼已過期"
                
                # 檢查嘗試次數
                if verification_data["attempts"] >= self.config["max_attempts"]:
                    del self._verification_codes[phone_number]
                    return False, "驗證失敗次數過多"
                
                # 驗證碼比對
                if verification_data["code"] == code:
                    del self._verification_codes[phone_number]
                    return True, "驗證成功"
                
                verification_data["attempts"] += 1
                remaining = self.config["max_attempts"] - verification_data["attempts"]
                return False, f"驗證碼錯誤，還有 {remaining} 次機會"
            
            def _check_rate_limit(self, phone_number):
                if phone_number in self._send_history:
                    last_send = self._send_history[phone_number]
                    if time.time() - last_send < self.config["rate_limit"]:
                        return True
                return False
        
        # 測試 SMS 服務
        sms_service = MockSMSService()
        phone_number = "+886912345678"
        user_id = "test_user_123"
        
        # 測試發送驗證碼
        success, message = sms_service.send_verification_code(phone_number, user_id)
        print(f"✅ 發送驗證碼: {success}, {message}")
        assert success, "發送驗證碼失敗"
        
        # 獲取驗證碼
        code = sms_service._verification_codes[phone_number]["code"]
        print(f"✅ 生成的驗證碼: {code}")
        
        # 測試驗證成功
        success, message = sms_service.verify_sms_code(phone_number, code, user_id)
        print(f"✅ 驗證結果: {success}, {message}")
        assert success, "驗證碼驗證失敗"
        
        # 測試頻率限制
        success, message = sms_service.send_verification_code(phone_number, user_id)
        print(f"✅ 頻率限制測試: {success}, {message}")
        assert not success, "頻率限制測試失敗"
        
        print("✅ SMS 驗證邏輯測試通過")
        return True
        
    except Exception as e:
        print(f"❌ SMS 驗證邏輯測試失敗: {e}")
        return False


def test_token_generation_and_verification():
    """測試令牌生成和驗證"""
    print("\n" + "=" * 60)
    print("🔑 測試令牌生成和驗證")
    print("=" * 60)
    
    try:
        import hmac
        import hashlib
        import base64
        import time
        
        def generate_setup_token(user_id, secret):
            """生成設定令牌"""
            timestamp = str(int(time.time()))
            data = f"{user_id}:{secret}:{timestamp}"
            
            signature = hmac.new(
                b"setup_secret_key",
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            token_data = f"{data}:{signature}"
            return base64.b64encode(token_data.encode()).decode()
        
        def verify_setup_token(token, user_id):
            """驗證設定令牌"""
            try:
                token_data = base64.b64decode(token.encode()).decode()
                parts = token_data.split(':')
                
                if len(parts) != 4:
                    return False
                
                token_user_id, secret, timestamp, signature = parts
                
                # 檢查使用者 ID
                if token_user_id != user_id:
                    return False
                
                # 檢查時間戳（10 分鐘有效期）
                if int(time.time()) - int(timestamp) > 600:
                    return False
                
                # 驗證簽名
                data = f"{token_user_id}:{secret}:{timestamp}"
                expected_signature = hmac.new(
                    b"setup_secret_key",
                    data.encode(),
                    hashlib.sha256
                ).hexdigest()
                
                return hmac.compare_digest(signature, expected_signature)
                
            except Exception:
                return False
        
        # 測試令牌生成和驗證
        user_id = "test_user_123"
        secret = "test_secret_key"
        
        # 生成令牌
        token = generate_setup_token(user_id, secret)
        print(f"✅ 生成令牌: {token[:50]}...")
        
        # 驗證令牌
        is_valid = verify_setup_token(token, user_id)
        print(f"✅ 令牌驗證結果: {is_valid}")
        assert is_valid, "令牌驗證失敗"
        
        # 測試錯誤的使用者 ID
        is_valid_wrong_user = verify_setup_token(token, "wrong_user")
        print(f"✅ 錯誤使用者驗證結果: {is_valid_wrong_user}")
        assert not is_valid_wrong_user, "錯誤使用者驗證應該失敗"
        
        print("✅ 令牌生成和驗證測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 令牌測試失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("🔐 AI Trading System - 2FA 基本功能測試")
    print("=" * 80)
    
    test_results = []
    
    # 執行各項測試
    tests = [
        ("備用碼生成", test_backup_codes_generation),
        ("TOTP 功能", test_totp_functionality),
        ("QR 碼生成", test_qr_code_generation),
        ("SMS 驗證邏輯", test_sms_verification_logic),
        ("令牌生成和驗證", test_token_generation_and_verification),
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
        print("🎉 所有 2FA 基本功能測試通過！")
        return True
    else:
        print("⚠️ 部分測試失敗，請檢查相關功能")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
