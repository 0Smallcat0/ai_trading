"""
安全掃描器

此模組提供全面的安全掃描功能，包括漏洞檢測、安全標頭檢查等。
"""

import re
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import requests
from fastapi.testclient import TestClient


@dataclass
class SecurityIssue:
    """安全問題資料類"""

    severity: str  # "critical", "high", "medium", "low", "info"
    category: str  # "authentication", "injection", "xss", "data_leak", etc.
    title: str
    description: str
    endpoint: str
    method: str
    payload: Optional[str] = None
    response_code: Optional[int] = None
    evidence: Optional[str] = None
    recommendation: Optional[str] = None
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID


@dataclass
class SecurityScanResult:
    """安全掃描結果"""

    scan_id: str
    start_time: datetime
    end_time: datetime
    total_endpoints: int
    total_tests: int
    issues_found: List[SecurityIssue] = field(default_factory=list)
    security_score: float = 0.0

    @property
    def critical_issues(self) -> List[SecurityIssue]:
        return [issue for issue in self.issues_found if issue.severity == "critical"]

    @property
    def high_issues(self) -> List[SecurityIssue]:
        return [issue for issue in self.issues_found if issue.severity == "high"]

    @property
    def medium_issues(self) -> List[SecurityIssue]:
        return [issue for issue in self.issues_found if issue.severity == "medium"]

    @property
    def low_issues(self) -> List[SecurityIssue]:
        return [issue for issue in self.issues_found if issue.severity == "low"]


class SecurityScanner:
    """安全掃描器類"""

    def __init__(self):
        """初始化安全掃描器"""
        self.sensitive_patterns = [
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email"),
            (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "credit_card"),
            (r"\b\d{3}-\d{2}-\d{4}\b", "ssn"),
            (r'password\s*[:=]\s*[\'"]?([^\'"\\s]+)', "password"),
            (r'api[_-]?key\s*[:=]\s*[\'"]?([^\'"\\s]+)', "api_key"),
            (r'secret[_-]?key\s*[:=]\s*[\'"]?([^\'"\\s]+)', "secret_key"),
            (r'access[_-]?token\s*[:=]\s*[\'"]?([^\'"\\s]+)', "access_token"),
            (r'private[_-]?key\s*[:=]\s*[\'"]?([^\'"\\s]+)', "private_key"),
        ]

        self.security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy",
            "Permissions-Policy",
        ]

        self.sql_injection_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "1' AND (SELECT COUNT(*) FROM users) > 0 --",
            "admin'--",
            "' OR 1=1#",
            "' OR 'a'='a",
            "') OR ('1'='1",
        ]

        self.xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src=javascript:alert('XSS')></iframe>",
            "';alert('XSS');//",
            "\";alert('XSS');//",
        ]

    def scan_api_security(
        self,
        client: TestClient,
        endpoints: List[Dict[str, Any]],
        auth_headers: Optional[Dict[str, str]] = None,
    ) -> SecurityScanResult:
        """
        執行完整的 API 安全掃描

        Args:
            client: 測試客戶端
            endpoints: 要掃描的端點列表
            auth_headers: 認證標頭

        Returns:
            SecurityScanResult: 掃描結果
        """
        scan_id = f"scan_{int(time.time())}"
        start_time = datetime.now()

        result = SecurityScanResult(
            scan_id=scan_id,
            start_time=start_time,
            end_time=start_time,  # 暫時設置，稍後更新
            total_endpoints=len(endpoints),
            total_tests=0,
        )

        # 執行各種安全測試
        for endpoint in endpoints:
            # 檢查安全標頭
            self._check_security_headers(client, endpoint, result)

            # 檢查 SQL 注入
            self._check_sql_injection(client, endpoint, auth_headers, result)

            # 檢查 XSS
            self._check_xss_vulnerabilities(client, endpoint, auth_headers, result)

            # 檢查敏感資料洩漏
            self._check_sensitive_data_exposure(client, endpoint, auth_headers, result)

            # 檢查認證繞過
            self._check_authentication_bypass(client, endpoint, result)

        result.end_time = datetime.now()
        result.security_score = self._calculate_security_score(result)

        return result

    def _check_security_headers(
        self, client: TestClient, endpoint: Dict[str, Any], result: SecurityScanResult
    ):
        """檢查安全標頭"""
        try:
            response = client.get(endpoint.get("url", "/"))
            result.total_tests += 1

            missing_headers = []
            for header in self.security_headers:
                if header not in response.headers:
                    missing_headers.append(header)

            if missing_headers:
                issue = SecurityIssue(
                    severity="medium",
                    category="security_headers",
                    title="缺少安全標頭",
                    description=f"端點缺少重要的安全標頭: {', '.join(missing_headers)}",
                    endpoint=endpoint.get("url", "/"),
                    method="GET",
                    response_code=response.status_code,
                    evidence=f"缺少標頭: {missing_headers}",
                    recommendation="添加缺少的安全標頭以提高安全性",
                    cwe_id="CWE-693",
                )
                result.issues_found.append(issue)

        except Exception as e:
            pass  # 忽略測試錯誤

    def _check_sql_injection(
        self,
        client: TestClient,
        endpoint: Dict[str, Any],
        auth_headers: Optional[Dict[str, str]],
        result: SecurityScanResult,
    ):
        """檢查 SQL 注入漏洞"""
        url = endpoint.get("url", "/")
        method = endpoint.get("method", "GET").upper()

        for payload in self.sql_injection_payloads:
            try:
                result.total_tests += 1

                if method == "GET":
                    # 測試查詢參數
                    response = client.get(
                        url,
                        params={"q": payload, "search": payload},
                        headers=auth_headers,
                    )
                elif method == "POST":
                    # 測試 JSON 資料
                    test_data = {
                        "username": payload,
                        "search": payload,
                        "query": payload,
                    }
                    response = client.post(url, json=test_data, headers=auth_headers)
                else:
                    continue

                # 檢查可能的 SQL 錯誤
                response_text = response.text.lower()
                sql_error_indicators = [
                    "sql syntax",
                    "mysql_fetch",
                    "ora-",
                    "postgresql",
                    "sqlite",
                    "syntax error",
                    "database error",
                ]

                for indicator in sql_error_indicators:
                    if indicator in response_text:
                        issue = SecurityIssue(
                            severity="high",
                            category="sql_injection",
                            title="可能的 SQL 注入漏洞",
                            description=f"端點可能存在 SQL 注入漏洞，回應中包含資料庫錯誤訊息",
                            endpoint=url,
                            method=method,
                            payload=payload,
                            response_code=response.status_code,
                            evidence=f"回應包含: {indicator}",
                            recommendation="使用參數化查詢或 ORM 來防止 SQL 注入",
                            cwe_id="CWE-89",
                        )
                        result.issues_found.append(issue)
                        break

            except Exception as e:
                pass

    def _check_xss_vulnerabilities(
        self,
        client: TestClient,
        endpoint: Dict[str, Any],
        auth_headers: Optional[Dict[str, str]],
        result: SecurityScanResult,
    ):
        """檢查 XSS 漏洞"""
        url = endpoint.get("url", "/")
        method = endpoint.get("method", "GET").upper()

        for payload in self.xss_payloads:
            try:
                result.total_tests += 1

                if method == "GET":
                    response = client.get(
                        url,
                        params={"q": payload, "search": payload},
                        headers=auth_headers,
                    )
                elif method == "POST":
                    test_data = {
                        "content": payload,
                        "message": payload,
                        "comment": payload,
                    }
                    response = client.post(url, json=test_data, headers=auth_headers)
                else:
                    continue

                # 檢查回應中是否包含未轉義的載荷
                if payload in response.text and response.headers.get(
                    "content-type", ""
                ).startswith("text/html"):
                    issue = SecurityIssue(
                        severity="high",
                        category="xss",
                        title="可能的 XSS 漏洞",
                        description="端點可能存在跨站腳本攻擊漏洞，用戶輸入未正確轉義",
                        endpoint=url,
                        method=method,
                        payload=payload,
                        response_code=response.status_code,
                        evidence=f"回應中包含未轉義的載荷: {payload[:50]}...",
                        recommendation="對所有用戶輸入進行適當的轉義和驗證",
                        cwe_id="CWE-79",
                    )
                    result.issues_found.append(issue)

            except Exception as e:
                pass

    def _check_sensitive_data_exposure(
        self,
        client: TestClient,
        endpoint: Dict[str, Any],
        auth_headers: Optional[Dict[str, str]],
        result: SecurityScanResult,
    ):
        """檢查敏感資料洩漏"""
        try:
            url = endpoint.get("url", "/")
            response = client.get(url, headers=auth_headers)
            result.total_tests += 1

            response_text = response.text

            for pattern, data_type in self.sensitive_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE)
                if matches:
                    issue = SecurityIssue(
                        severity="medium" if data_type in ["email"] else "high",
                        category="data_exposure",
                        title=f"敏感資料洩漏 - {data_type}",
                        description=f"API 回應中包含敏感的 {data_type} 資料",
                        endpoint=url,
                        method="GET",
                        response_code=response.status_code,
                        evidence=f"發現 {len(matches)} 個 {data_type} 匹配",
                        recommendation="移除或遮罩回應中的敏感資料",
                        cwe_id="CWE-200",
                    )
                    result.issues_found.append(issue)

        except Exception as e:
            pass

    def _check_authentication_bypass(
        self, client: TestClient, endpoint: Dict[str, Any], result: SecurityScanResult
    ):
        """檢查認證繞過"""
        url = endpoint.get("url", "/")

        # 如果是受保護的端點（以 /api/v1/ 開頭但不是認證端點）
        if url.startswith("/api/v1/") and "/auth/" not in url:
            try:
                # 嘗試無認證訪問
                response = client.get(url)
                result.total_tests += 1

                # 如果返回 200 而不是 401，可能存在認證繞過
                if response.status_code == 200:
                    issue = SecurityIssue(
                        severity="critical",
                        category="authentication",
                        title="認證繞過漏洞",
                        description="受保護的端點可以在沒有認證的情況下訪問",
                        endpoint=url,
                        method="GET",
                        response_code=response.status_code,
                        evidence=f"無認證訪問返回 {response.status_code}",
                        recommendation="確保所有受保護的端點都需要有效的認證",
                        cwe_id="CWE-287",
                    )
                    result.issues_found.append(issue)

            except Exception as e:
                pass

    def _calculate_security_score(self, result: SecurityScanResult) -> float:
        """計算安全評分"""
        if result.total_tests == 0:
            return 0.0

        # 根據問題嚴重程度計算扣分
        deductions = 0
        deductions += len(result.critical_issues) * 25  # 嚴重問題扣 25 分
        deductions += len(result.high_issues) * 15  # 高危問題扣 15 分
        deductions += len(result.medium_issues) * 8  # 中危問題扣 8 分
        deductions += len(result.low_issues) * 3  # 低危問題扣 3 分

        # 基礎分數 100，減去扣分
        score = max(0, 100 - deductions)
        return score

    def generate_security_report(self, result: SecurityScanResult) -> str:
        """生成安全報告"""
        report = f"""
# 安全掃描報告

**掃描 ID**: {result.scan_id}
**掃描時間**: {result.start_time.strftime('%Y-%m-%d %H:%M:%S')} - {result.end_time.strftime('%Y-%m-%d %H:%M:%S')}
**掃描端點**: {result.total_endpoints}
**執行測試**: {result.total_tests}
**安全評分**: {result.security_score:.1f}/100

## 問題統計

- 🔴 嚴重問題: {len(result.critical_issues)}
- 🟠 高危問題: {len(result.high_issues)}
- 🟡 中危問題: {len(result.medium_issues)}
- 🔵 低危問題: {len(result.low_issues)}

## 詳細問題

"""

        for issue in result.issues_found:
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🔵",
                "info": "ℹ️",
            }.get(issue.severity, "❓")

            report += f"""
### {severity_emoji} {issue.title}

- **嚴重程度**: {issue.severity.upper()}
- **類別**: {issue.category}
- **端點**: {issue.method} {issue.endpoint}
- **描述**: {issue.description}
"""

            if issue.payload:
                report += f"- **測試載荷**: `{issue.payload}`\n"
            if issue.evidence:
                report += f"- **證據**: {issue.evidence}\n"
            if issue.recommendation:
                report += f"- **建議**: {issue.recommendation}\n"
            if issue.cwe_id:
                report += f"- **CWE ID**: {issue.cwe_id}\n"

        return report
