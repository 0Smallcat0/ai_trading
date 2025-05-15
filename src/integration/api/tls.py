"""
TLS 配置模組

此模組提供 TLS/SSL 配置，用於加密 API 服務器與客戶端之間的通信。
"""

import os
import logging
import ssl
from typing import Dict, Optional, Any, Tuple
from pathlib import Path

from src.core.logger import logger


class TLSConfig:
    """
    TLS 配置類

    提供 TLS/SSL 配置，用於加密 API 服務器與客戶端之間的通信。
    """

    def __init__(
        self,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
        ca_file: Optional[str] = None,
        config_dir: str = "config/tls",
    ):
        """
        初始化 TLS 配置

        Args:
            cert_file: 證書文件路徑
            key_file: 私鑰文件路徑
            ca_file: CA 證書文件路徑
            config_dir: 配置目錄
        """
        # 獲取證書文件路徑
        self.cert_file = cert_file or os.environ.get("TLS_CERT_FILE")
        self.key_file = key_file or os.environ.get("TLS_KEY_FILE")
        self.ca_file = ca_file or os.environ.get("TLS_CA_FILE")
        self.config_dir = config_dir

        # 檢查證書文件是否存在
        if self.cert_file and not os.path.exists(self.cert_file):
            logger.warning(f"證書文件不存在: {self.cert_file}")
            self.cert_file = None

        if self.key_file and not os.path.exists(self.key_file):
            logger.warning(f"私鑰文件不存在: {self.key_file}")
            self.key_file = None

        if self.ca_file and not os.path.exists(self.ca_file):
            logger.warning(f"CA 證書文件不存在: {self.ca_file}")
            self.ca_file = None

        # 檢查配置目錄是否存在
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)

    def is_available(self) -> bool:
        """
        檢查 TLS 配置是否可用

        Returns:
            bool: TLS 配置是否可用
        """
        return self.cert_file is not None and self.key_file is not None

    def get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """
        獲取 SSL 上下文

        Returns:
            Optional[ssl.SSLContext]: SSL 上下文
        """
        if not self.is_available():
            logger.warning("TLS 配置不可用，無法創建 SSL 上下文")
            return None

        try:
            # 創建 SSL 上下文
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(self.cert_file, self.key_file)

            # 如果有 CA 證書，則加載
            if self.ca_file:
                context.load_verify_locations(self.ca_file)

            # 設置 TLS 版本
            context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
            context.minimum_version = ssl.TLSVersion.TLSv1_2

            # 設置加密套件
            context.set_ciphers(
                "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
            )

            return context
        except Exception as e:
            logger.error(f"創建 SSL 上下文時發生錯誤: {e}")
            return None

    def generate_self_signed_cert(
        self,
        common_name: str = "localhost",
        days_valid: int = 365,
        key_size: int = 2048,
    ) -> Tuple[bool, str, str]:
        """
        生成自簽名證書

        Args:
            common_name: 通用名稱
            days_valid: 有效天數
            key_size: 密鑰大小

        Returns:
            Tuple[bool, str, str]: (是否成功, 證書文件路徑, 私鑰文件路徑)
        """
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives.serialization import (
                Encoding,
                PrivateFormat,
                NoEncryption,
            )
        except ImportError:
            logger.error("未安裝 cryptography 套件，無法生成自簽名證書")
            return False, "", ""

        try:
            # 生成私鑰
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
            )

            # 生成證書
            subject = issuer = x509.Name(
                [
                    x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Trading System"),
                    x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "API Server"),
                ]
            )

            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.utcnow())
                .not_valid_after(datetime.utcnow() + timedelta(days=days_valid))
                .add_extension(
                    x509.SubjectAlternativeName([x509.DNSName(common_name)]),
                    critical=False,
                )
                .sign(private_key, hashes.SHA256())
            )

            # 保存證書和私鑰
            cert_path = os.path.join(self.config_dir, f"{common_name}.crt")
            key_path = os.path.join(self.config_dir, f"{common_name}.key")

            with open(cert_path, "wb") as f:
                f.write(cert.public_bytes(Encoding.PEM))

            with open(key_path, "wb") as f:
                f.write(
                    private_key.private_bytes(
                        Encoding.PEM,
                        PrivateFormat.PKCS8,
                        NoEncryption(),
                    )
                )

            # 更新配置
            self.cert_file = cert_path
            self.key_file = key_path

            logger.info(f"已生成自簽名證書: {cert_path}")
            return True, cert_path, key_path
        except Exception as e:
            logger.error(f"生成自簽名證書時發生錯誤: {e}")
            return False, "", ""


# 創建全局 TLS 配置實例
tls_config = TLSConfig()
