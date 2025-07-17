"""
多重身份驗證管理頁面

此模組提供完整的 2FA/MFA 管理介面，包括：
- TOTP 設定和管理
- SMS 驗證設定
- 備用碼管理
- 2FA 狀態查看
"""

import streamlit as st
import base64
from typing import Optional, Dict, Any

from src.core.two_factor_service import TwoFactorService, SMSService


class TwoFactorManagement:
    """多重身份驗證管理類別"""
    
    def __init__(self):
        """初始化 2FA 管理"""
        try:
            self.two_factor_service = TwoFactorService()
            self.sms_service = SMSService()
        except Exception as e:
            st.error(f"初始化 2FA 服務失敗: {e}")
            self.two_factor_service = None
            self.sms_service = None
    
    def show_2fa_management(self):
        """顯示 2FA 管理主頁面"""
        st.title("🔐 多重身份驗證管理")
        
        if not self.two_factor_service:
            st.error("2FA 服務不可用")
            return
        
        # 檢查使用者登入狀態
        if not self._check_user_authenticated():
            st.warning("請先登入以管理您的兩步驗證設定")

            # 提供更詳細的信息
            st.info("""
            **如何訪問 2FA 設定：**
            1. 請確保您已經登入系統
            2. 確認您有管理員權限
            3. 如果問題持續，請嘗試重新登入
            """)

            # 顯示當前認證狀態（僅供調試）
            if st.checkbox("顯示調試信息"):
                st.json({
                    "authenticated": st.session_state.get("authenticated", False),
                    "user_id": st.session_state.get("user_id"),
                    "username": st.session_state.get("username"),
                    "user_role": st.session_state.get("user_role"),
                })

            return
        
        user_id = st.session_state.get("user_id")
        
        # 獲取 2FA 狀態
        status = self.two_factor_service.get_2fa_status(user_id)
        
        if "error" in status:
            st.error(f"獲取 2FA 狀態失敗: {status['error']}")
            return
        
        # 顯示當前狀態
        self._show_2fa_status(status)
        
        # 根據狀態顯示不同的管理選項
        if status["enabled"]:
            self._show_enabled_2fa_management(user_id, status)
        else:
            self._show_setup_2fa(user_id)
    
    def _check_user_authenticated(self) -> bool:
        """檢查使用者是否已認證"""
        authenticated = st.session_state.get("authenticated", False)
        user_id = st.session_state.get("user_id")
        username = st.session_state.get("username")
        user_role = st.session_state.get("user_role")

        # 調試信息（僅在開發模式下顯示）
        if st.session_state.get("debug_mode", False):
            st.sidebar.write(f"認證狀態: {authenticated}")
            st.sidebar.write(f"用戶ID: {user_id}")
            st.sidebar.write(f"用戶名: {username}")
            st.sidebar.write(f"用戶角色: {user_role}")

        # 檢查多種可能的認證狀態
        is_authenticated = (
            authenticated and
            (user_id is not None or username is not None)
        )

        return is_authenticated
    
    def _show_2fa_status(self, status: Dict[str, Any]):
        """顯示 2FA 狀態"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if status["enabled"]:
                st.success("✅ 兩步驗證已啟用")
            else:
                st.warning("⚠️ 兩步驗證未啟用")
        
        with col2:
            if status["enabled"]:
                st.info(f"📱 備用碼數量: {status['backup_codes_count']}")
        
        with col3:
            if status.get("is_locked", False):
                st.error("🔒 帳戶已鎖定")
            elif status.get("failed_attempts", 0) > 0:
                st.warning(f"⚠️ 失敗嘗試: {status['failed_attempts']}")
    
    def _show_setup_2fa(self, user_id: str):
        """顯示 2FA 設定介面"""
        st.subheader("🔧 設定兩步驗證")
        
        st.info("""
        兩步驗證為您的帳戶提供額外的安全保護。即使有人知道您的密碼，
        沒有您的手機或驗證器應用程式，他們也無法登入您的帳戶。
        """)
        
        # 選擇設定方式
        setup_method = st.radio(
            "選擇設定方式",
            ["TOTP 驗證器應用程式", "SMS 簡訊驗證"],
            help="建議使用 TOTP 驗證器應用程式，更安全且不依賴網路"
        )
        
        if setup_method == "TOTP 驗證器應用程式":
            self._show_totp_setup(user_id)
        else:
            self._show_sms_setup(user_id)
    
    def _show_totp_setup(self, user_id: str):
        """顯示 TOTP 設定"""
        st.subheader("📱 TOTP 驗證器設定")
        
        if st.button("開始設定 TOTP", type="primary"):
            try:
                user_email = st.session_state.get("email", "user@example.com")
                setup_data = self.two_factor_service.setup_totp(user_id, user_email)
                
                # 存儲設定資料到 session state
                st.session_state.totp_setup_data = setup_data
                st.session_state.totp_setup_step = "qr_code"
                st.rerun()
                
            except Exception as e:
                st.error(f"設定失敗: {e}")
        
        # 顯示設定步驟
        if st.session_state.get("totp_setup_step") == "qr_code":
            self._show_qr_code_step()
        elif st.session_state.get("totp_setup_step") == "verify":
            self._show_verification_step(user_id)
    
    def _show_qr_code_step(self):
        """顯示 QR 碼步驟"""
        st.subheader("📷 掃描 QR 碼")
        
        setup_data = st.session_state.get("totp_setup_data", {})
        
        if "qr_code" in setup_data:
            # 顯示 QR 碼
            qr_code_data = setup_data["qr_code"]
            st.image(
                f"data:image/png;base64,{qr_code_data}",
                caption="請使用驗證器應用程式掃描此 QR 碼",
                width=300
            )
            
            # 顯示手動輸入的 secret
            with st.expander("手動輸入密鑰"):
                st.code(setup_data.get("secret", ""), language="text")
                st.caption("如果無法掃描 QR 碼，請手動輸入上述密鑰到您的驗證器應用程式")
            
            # 推薦的驗證器應用程式
            st.info("""
            **推薦的驗證器應用程式：**
            - Google Authenticator
            - Microsoft Authenticator
            - Authy
            - 1Password
            """)
            
            if st.button("我已掃描 QR 碼，繼續驗證"):
                st.session_state.totp_setup_step = "verify"
                st.rerun()
    
    def _show_verification_step(self, user_id: str):
        """顯示驗證步驟"""
        st.subheader("🔢 驗證設定")
        
        st.info("請輸入您的驗證器應用程式中顯示的 6 位數驗證碼")
        
        with st.form("totp_verification_form"):
            verification_code = st.text_input(
                "驗證碼",
                max_chars=6,
                placeholder="請輸入 6 位數驗證碼"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                verify_button = st.form_submit_button("✅ 驗證並啟用", type="primary")
            with col2:
                cancel_button = st.form_submit_button("❌ 取消設定")
            
            if cancel_button:
                self._cancel_totp_setup()
                return
            
            if verify_button and verification_code:
                self._verify_totp_setup(user_id, verification_code)
    
    def _verify_totp_setup(self, user_id: str, verification_code: str):
        """驗證 TOTP 設定"""
        setup_data = st.session_state.get("totp_setup_data", {})
        setup_token = setup_data.get("setup_token")
        
        if not setup_token:
            st.error("設定資料遺失，請重新開始設定")
            self._cancel_totp_setup()
            return
        
        try:
            success, message = self.two_factor_service.verify_totp_setup(
                user_id, verification_code, setup_token
            )
            
            if success:
                st.success("🎉 兩步驗證設定成功！")
                
                # 顯示備用碼
                backup_codes = setup_data.get("backup_codes", [])
                if backup_codes:
                    st.warning("⚠️ 請妥善保存以下備用碼，每個備用碼只能使用一次：")
                    
                    # 以表格形式顯示備用碼
                    cols = st.columns(2)
                    for i, code in enumerate(backup_codes):
                        with cols[i % 2]:
                            st.code(code)
                    
                    st.info("建議將這些備用碼列印或保存在安全的地方")
                
                # 清理 session state
                self._cleanup_totp_setup()
                
                # 重新載入頁面
                st.rerun()
            else:
                st.error(f"驗證失敗: {message}")
                
        except Exception as e:
            st.error(f"驗證過程發生錯誤: {e}")
    
    def _show_sms_setup(self, user_id: str):
        """顯示 SMS 設定"""
        st.subheader("📱 SMS 簡訊驗證設定")
        
        st.warning("""
        **注意：** SMS 驗證相對不如 TOTP 安全，建議優先使用 TOTP 驗證器應用程式。
        """)
        
        with st.form("sms_setup_form"):
            phone_number = st.text_input(
                "手機號碼",
                placeholder="+886912345678",
                help="請輸入完整的國際格式手機號碼"
            )
            
            if st.form_submit_button("發送驗證碼"):
                if phone_number:
                    self._send_sms_verification(user_id, phone_number)
                else:
                    st.error("請輸入手機號碼")
        
        # 如果已發送驗證碼，顯示驗證介面
        if st.session_state.get("sms_verification_sent"):
            self._show_sms_verification(user_id)
    
    def _send_sms_verification(self, user_id: str, phone_number: str):
        """發送 SMS 驗證碼"""
        try:
            success, message = self.sms_service.send_verification_code(phone_number, user_id)
            
            if success:
                st.success(f"驗證碼已發送到 {phone_number}")
                st.session_state.sms_verification_sent = True
                st.session_state.sms_phone_number = phone_number
                st.rerun()
            else:
                st.error(f"發送失敗: {message}")
                
        except Exception as e:
            st.error(f"發送驗證碼時發生錯誤: {e}")
    
    def _show_sms_verification(self, user_id: str):
        """顯示 SMS 驗證介面"""
        st.subheader("📱 驗證 SMS 驗證碼")
        
        phone_number = st.session_state.get("sms_phone_number")
        st.info(f"驗證碼已發送到 {phone_number}")
        
        with st.form("sms_verification_form"):
            sms_code = st.text_input(
                "驗證碼",
                max_chars=6,
                placeholder="請輸入 6 位數驗證碼"
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                verify_button = st.form_submit_button("✅ 驗證")
            with col2:
                resend_button = st.form_submit_button("🔄 重新發送")
            with col3:
                cancel_button = st.form_submit_button("❌ 取消")
            
            if cancel_button:
                self._cancel_sms_setup()
                return
            
            if resend_button:
                self._send_sms_verification(user_id, phone_number)
                return
            
            if verify_button and sms_code:
                self._verify_sms_code(user_id, phone_number, sms_code)
    
    def _verify_sms_code(self, user_id: str, phone_number: str, sms_code: str):
        """驗證 SMS 驗證碼"""
        try:
            success, message = self.sms_service.verify_sms_code(phone_number, sms_code, user_id)
            
            if success:
                st.success("🎉 SMS 驗證設定成功！")
                self._cleanup_sms_setup()
                st.rerun()
            else:
                st.error(f"驗證失敗: {message}")
                
        except Exception as e:
            st.error(f"驗證過程發生錯誤: {e}")
    
    def _show_enabled_2fa_management(self, user_id: str, status: Dict[str, Any]):
        """顯示已啟用 2FA 的管理選項"""
        st.subheader("🔧 管理兩步驗證")
        
        # 備用碼管理
        self._show_backup_codes_management(user_id, status)
        
        # 停用 2FA
        self._show_disable_2fa(user_id)
    
    def _show_backup_codes_management(self, user_id: str, status: Dict[str, Any]):
        """顯示備用碼管理"""
        st.subheader("🔑 備用碼管理")
        
        backup_codes_count = status.get("backup_codes_count", 0)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("剩餘備用碼", backup_codes_count)
        
        with col2:
            if backup_codes_count <= 2:
                st.warning("⚠️ 備用碼不足，建議重新生成")
        
        if st.button("🔄 重新生成備用碼", type="secondary"):
            try:
                success, message, new_codes = self.two_factor_service.regenerate_backup_codes(user_id)
                
                if success:
                    st.success(message)
                    
                    st.warning("⚠️ 請妥善保存以下新的備用碼：")
                    cols = st.columns(2)
                    for i, code in enumerate(new_codes):
                        with cols[i % 2]:
                            st.code(code)
                    
                    st.info("舊的備用碼已失效，請使用新的備用碼")
                else:
                    st.error(f"重新生成失敗: {message}")
                    
            except Exception as e:
                st.error(f"重新生成備用碼時發生錯誤: {e}")
    
    def _show_disable_2fa(self, user_id: str):
        """顯示停用 2FA 選項"""
        st.subheader("⚠️ 停用兩步驗證")
        
        st.warning("""
        **警告：** 停用兩步驗證會降低您帳戶的安全性。
        只有在確實需要時才停用此功能。
        """)
        
        with st.expander("停用兩步驗證"):
            password = st.text_input(
                "請輸入您的密碼以確認身份",
                type="password",
                key="disable_2fa_password"
            )
            
            if st.button("🔓 確認停用兩步驗證", type="secondary"):
                if password:
                    try:
                        success, message = self.two_factor_service.disable_2fa(user_id, password)
                        
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(f"停用失敗: {message}")
                            
                    except Exception as e:
                        st.error(f"停用過程發生錯誤: {e}")
                else:
                    st.error("請輸入密碼")
    
    def _cancel_totp_setup(self):
        """取消 TOTP 設定"""
        self._cleanup_totp_setup()
        st.info("已取消 TOTP 設定")
        st.rerun()
    
    def _cancel_sms_setup(self):
        """取消 SMS 設定"""
        self._cleanup_sms_setup()
        st.info("已取消 SMS 設定")
        st.rerun()
    
    def _cleanup_totp_setup(self):
        """清理 TOTP 設定相關的 session state"""
        keys_to_remove = ["totp_setup_data", "totp_setup_step"]
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
    
    def _cleanup_sms_setup(self):
        """清理 SMS 設定相關的 session state"""
        keys_to_remove = ["sms_verification_sent", "sms_phone_number"]
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]


def show() -> None:
    """顯示多重身份驗證管理頁面 (Web UI 入口點).

    Returns:
        None
    """
    show_two_factor_management()


def show_two_factor_management():
    """顯示多重身份驗證管理頁面"""
    two_factor_mgr = TwoFactorManagement()
    two_factor_mgr.show_2fa_management()


if __name__ == "__main__":
    show_two_factor_management()
