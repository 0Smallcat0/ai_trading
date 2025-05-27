"""
注入攻擊測試器

此模組提供 SQL 注入、NoSQL 注入、命令注入等攻擊測試功能。
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from fastapi.testclient import TestClient


@dataclass
class InjectionTestResult:
    """注入測試結果"""

    test_name: str
    endpoint: str
    method: str
    payload: str
    vulnerability_detected: bool
    response_code: int
    evidence: Optional[str] = None
    severity: str = "medium"
    description: str = ""
    recommendation: str = ""


class InjectionTester:
    """注入攻擊測試器類"""

    def __init__(self):
        """初始化注入測試器"""
        self.sql_injection_payloads = [
            # 基本 SQL 注入
            "' OR '1'='1",
            "' OR 1=1--",
            "' OR 'a'='a",
            "admin'--",
            "admin' /*",
            # Union 注入
            "' UNION SELECT NULL--",
            "' UNION SELECT 1,2,3--",
            "' UNION SELECT username,password FROM users--",
            # 布林盲注
            "' AND (SELECT COUNT(*) FROM users) > 0--",
            "' AND (SELECT SUBSTRING(username,1,1) FROM users WHERE id=1)='a'--",
            # 時間盲注
            "'; WAITFOR DELAY '00:00:05'--",
            "' AND (SELECT SLEEP(5))--",
            # 錯誤注入
            "' AND EXTRACTVALUE(1, CONCAT(0x7e, (SELECT version()), 0x7e))--",
            "' AND (SELECT * FROM (SELECT COUNT(*),CONCAT(version(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--",
            # 堆疊注入
            "'; DROP TABLE users; --",
            "'; INSERT INTO users VALUES ('hacker','password'); --",
            # 二階注入
            "admin'; UPDATE users SET password='hacked' WHERE username='admin'--",
        ]

        self.nosql_injection_payloads = [
            # MongoDB 注入
            {"$ne": None},
            {"$gt": ""},
            {"$regex": ".*"},
            {"$where": "this.username == this.password"},
            {"$or": [{"username": "admin"}, {"username": "administrator"}]},
            # JSON 注入
            '{"$ne": null}',
            '{"$gt": ""}',
            '{"$regex": ".*"}',
            '{"username": {"$ne": null}}',
            '{"password": {"$exists": true}}',
        ]

        self.command_injection_payloads = [
            # 基本命令注入
            "; ls",
            "| ls",
            "&& ls",
            "|| ls",
            "`ls`",
            "$(ls)",
            # Windows 命令注入
            "; dir",
            "| dir",
            "&& dir",
            "|| dir",
            # 盲命令注入
            "; sleep 5",
            "| sleep 5",
            "&& ping -c 5 127.0.0.1",
            "|| ping -n 5 127.0.0.1",
            # 數據外洩
            "; cat /etc/passwd",
            "| cat /etc/passwd",
            "&& type C:\\Windows\\System32\\drivers\\etc\\hosts",
        ]

        self.ldap_injection_payloads = [
            "*",
            "*)(uid=*",
            "*)(|(uid=*",
            "*)(&(uid=*",
            "*))%00",
            "admin)(&(password=*))",
            "*)(cn=*)",
        ]

        # SQL 錯誤模式
        self.sql_error_patterns = [
            r"sql syntax",
            r"mysql_fetch",
            r"ora-\d+",
            r"postgresql",
            r"sqlite",
            r"syntax error",
            r"database error",
            r"invalid query",
            r"mysql_num_rows",
            r"mysql_result",
            r"pg_query",
            r"sqlite3",
            r"odbc_exec",
        ]

        # 命令執行模式
        self.command_execution_patterns = [
            r"total \d+",  # ls 輸出
            r"volume in drive",  # dir 輸出
            r"directory of",  # dir 輸出
            r"root:x:0:0",  # /etc/passwd
            r"# localhost name resolution",  # hosts 文件
            r"ping statistics",  # ping 輸出
            r"packets transmitted",  # ping 輸出
        ]

    def test_sql_injection(
        self,
        client: TestClient,
        endpoints: List[Dict[str, Any]],
        auth_headers: Optional[Dict[str, str]] = None,
    ) -> List[InjectionTestResult]:
        """
        測試 SQL 注入漏洞

        Args:
            client: 測試客戶端
            endpoints: 要測試的端點列表
            auth_headers: 認證標頭

        Returns:
            List[InjectionTestResult]: 測試結果列表
        """
        results = []

        for endpoint in endpoints:
            url = endpoint.get("url", "/")
            method = endpoint.get("method", "GET").upper()

            for payload in self.sql_injection_payloads:
                try:
                    response = None

                    if method == "GET":
                        # 測試查詢參數
                        params = {
                            "id": payload,
                            "search": payload,
                            "q": payload,
                            "query": payload,
                            "filter": payload,
                        }
                        response = client.get(url, params=params, headers=auth_headers)

                    elif method == "POST":
                        # 測試 JSON 資料
                        test_data = {
                            "username": payload,
                            "email": payload,
                            "search": payload,
                            "query": payload,
                            "id": payload,
                            "filter": payload,
                        }
                        response = client.post(
                            url, json=test_data, headers=auth_headers
                        )

                    elif method == "PUT":
                        test_data = {"id": payload, "data": payload}
                        response = client.put(url, json=test_data, headers=auth_headers)

                    if response:
                        vulnerability_detected, evidence = self._analyze_sql_response(
                            response
                        )

                        result = InjectionTestResult(
                            test_name="SQL 注入測試",
                            endpoint=url,
                            method=method,
                            payload=payload,
                            vulnerability_detected=vulnerability_detected,
                            response_code=response.status_code,
                            evidence=evidence,
                            severity="high" if vulnerability_detected else "info",
                            description="測試 SQL 注入漏洞"
                            + (
                                f" - 檢測到漏洞: {evidence}"
                                if vulnerability_detected
                                else ""
                            ),
                            recommendation=(
                                "使用參數化查詢或 ORM 來防止 SQL 注入"
                                if vulnerability_detected
                                else ""
                            ),
                        )
                        results.append(result)

                except Exception as e:
                    # 記錄異常但繼續測試
                    pass

        return results

    def test_nosql_injection(
        self,
        client: TestClient,
        endpoints: List[Dict[str, Any]],
        auth_headers: Optional[Dict[str, str]] = None,
    ) -> List[InjectionTestResult]:
        """
        測試 NoSQL 注入漏洞

        Args:
            client: 測試客戶端
            endpoints: 要測試的端點列表
            auth_headers: 認證標頭

        Returns:
            List[InjectionTestResult]: 測試結果列表
        """
        results = []

        for endpoint in endpoints:
            url = endpoint.get("url", "/")
            method = endpoint.get("method", "GET").upper()

            for payload in self.nosql_injection_payloads:
                try:
                    response = None

                    if method == "POST" and isinstance(payload, dict):
                        # 測試 MongoDB 風格的注入
                        test_data = {
                            "username": payload,
                            "password": payload,
                            "filter": payload,
                        }
                        response = client.post(
                            url, json=test_data, headers=auth_headers
                        )

                    elif method == "POST" and isinstance(payload, str):
                        # 測試 JSON 字符串注入
                        test_data = {"query": payload, "filter": payload}
                        response = client.post(
                            url, json=test_data, headers=auth_headers
                        )

                    if response:
                        vulnerability_detected = self._analyze_nosql_response(response)

                        result = InjectionTestResult(
                            test_name="NoSQL 注入測試",
                            endpoint=url,
                            method=method,
                            payload=str(payload),
                            vulnerability_detected=vulnerability_detected,
                            response_code=response.status_code,
                            evidence="異常回應行為" if vulnerability_detected else None,
                            severity="high" if vulnerability_detected else "info",
                            description="測試 NoSQL 注入漏洞",
                            recommendation=(
                                "驗證和清理所有用戶輸入，使用安全的查詢方法"
                                if vulnerability_detected
                                else ""
                            ),
                        )
                        results.append(result)

                except Exception as e:
                    pass

        return results

    def test_command_injection(
        self,
        client: TestClient,
        endpoints: List[Dict[str, Any]],
        auth_headers: Optional[Dict[str, str]] = None,
    ) -> List[InjectionTestResult]:
        """
        測試命令注入漏洞

        Args:
            client: 測試客戶端
            endpoints: 要測試的端點列表
            auth_headers: 認證標頭

        Returns:
            List[InjectionTestResult]: 測試結果列表
        """
        results = []

        for endpoint in endpoints:
            url = endpoint.get("url", "/")
            method = endpoint.get("method", "GET").upper()

            for payload in self.command_injection_payloads:
                try:
                    response = None

                    if method == "GET":
                        params = {
                            "cmd": payload,
                            "command": payload,
                            "exec": payload,
                            "file": payload,
                            "path": payload,
                        }
                        response = client.get(url, params=params, headers=auth_headers)

                    elif method == "POST":
                        test_data = {
                            "command": payload,
                            "cmd": payload,
                            "exec": payload,
                            "file": payload,
                            "path": payload,
                            "input": payload,
                        }
                        response = client.post(
                            url, json=test_data, headers=auth_headers
                        )

                    if response:
                        vulnerability_detected, evidence = (
                            self._analyze_command_response(response)
                        )

                        result = InjectionTestResult(
                            test_name="命令注入測試",
                            endpoint=url,
                            method=method,
                            payload=payload,
                            vulnerability_detected=vulnerability_detected,
                            response_code=response.status_code,
                            evidence=evidence,
                            severity="critical" if vulnerability_detected else "info",
                            description="測試命令注入漏洞",
                            recommendation=(
                                "避免直接執行用戶輸入，使用安全的 API 替代系統命令"
                                if vulnerability_detected
                                else ""
                            ),
                        )
                        results.append(result)

                except Exception as e:
                    pass

        return results

    def get_sql_injection_payloads(self) -> List[str]:
        """
        獲取 SQL 注入測試載荷

        Returns:
            List[str]: SQL 注入載荷列表
        """
        return self.sql_injection_payloads.copy()

    def get_nosql_injection_payloads(self) -> List[Any]:
        """
        獲取 NoSQL 注入測試載荷

        Returns:
            List[Any]: NoSQL 注入載荷列表
        """
        return self.nosql_injection_payloads.copy()

    def get_command_injection_payloads(self) -> List[str]:
        """
        獲取命令注入測試載荷

        Returns:
            List[str]: 命令注入載荷列表
        """
        return self.command_injection_payloads.copy()

    def get_ldap_injection_payloads(self) -> List[str]:
        """
        獲取 LDAP 注入測試載荷

        Returns:
            List[str]: LDAP 注入載荷列表
        """
        return self.ldap_injection_payloads.copy()

    def _analyze_sql_response(self, response) -> Tuple[bool, Optional[str]]:
        """分析 SQL 注入回應"""
        response_text = response.text.lower()

        # 檢查 SQL 錯誤模式
        for pattern in self.sql_error_patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                return True, f"SQL 錯誤: {pattern}"

        # 檢查異常長的回應（可能是 UNION 注入成功）
        if len(response_text) > 10000:
            return True, "異常長的回應內容"

        # 檢查狀態碼異常
        if response.status_code == 500:
            return True, "內部伺服器錯誤"

        return False, None

    def _analyze_nosql_response(self, response) -> bool:
        """分析 NoSQL 注入回應"""
        # 檢查是否返回了意外的資料
        if response.status_code == 200:
            try:
                data = response.json()
                # 如果返回了大量資料或敏感資料，可能是注入成功
                if isinstance(data, dict) and len(str(data)) > 5000:
                    return True
                if isinstance(data, list) and len(data) > 100:
                    return True
            except:
                pass

        return False

    def _analyze_command_response(self, response) -> Tuple[bool, Optional[str]]:
        """分析命令注入回應"""
        response_text = response.text

        # 檢查命令執行模式
        for pattern in self.command_execution_patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                return True, f"命令執行證據: {pattern}"

        # 檢查異常的回應時間（可能是 sleep 命令）
        # 這需要在實際測試中測量時間

        return False, None
