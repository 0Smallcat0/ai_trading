#!/usr/bin/env python3
"""
AI 交易系統自定義安全檢查腳本
版本: v1.0
最後更新: 2024-12-25

此腳本執行自定義安全檢查，包括：
- 配置文件安全檢查
- API 金鑰洩漏檢測
- 文件權限檢查
- 網路配置安全檢查
- 資料庫配置安全檢查
"""

import os
import sys
import json
import re
import stat
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
import yaml

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 項目根目錄
PROJECT_ROOT = Path(__file__).parent.parent


class SecurityChecker:
    """自定義安全檢查器"""
    
    def __init__(self):
        """初始化安全檢查器"""
        self.issues = []
        self.stats = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }
        
        # 敏感文件模式
        self.sensitive_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'private_key\s*=\s*["\'][^"\']+["\']',
            r'aws_access_key_id\s*=\s*["\'][^"\']+["\']',
            r'aws_secret_access_key\s*=\s*["\'][^"\']+["\']',
            r'database_url\s*=\s*["\']postgresql://[^"\']+["\']',
            r'redis_url\s*=\s*["\']redis://[^"\']+["\']',
        ]
        
        # 危險函數模式
        self.dangerous_functions = [
            r'eval\s*\(',
            r'exec\s*\(',
            r'subprocess\.call\s*\(',
            r'os\.system\s*\(',
            r'pickle\.loads\s*\(',
            r'yaml\.load\s*\(',
            r'input\s*\(',  # 在某些情況下可能危險
        ]
        
        # 不安全的配置模式
        self.insecure_configs = [
            r'debug\s*=\s*true',
            r'ssl_verify\s*=\s*false',
            r'verify_ssl\s*=\s*false',
            r'check_hostname\s*=\s*false',
        ]
    
    def add_issue(self, severity: str, title: str, description: str, file_path: str = None, line_number: int = None, recommendation: str = None):
        """添加安全問題"""
        issue = {
            "severity": severity,
            "title": title,
            "description": description,
            "file_path": file_path,
            "line_number": line_number,
            "recommendation": recommendation or self._get_default_recommendation(severity),
            "timestamp": "2024-12-25T00:00:00Z"
        }
        
        self.issues.append(issue)
        self.stats[severity] += 1
        
        logger.warning(f"[{severity.upper()}] {title}: {description}")
    
    def _get_default_recommendation(self, severity: str) -> str:
        """獲取預設建議"""
        recommendations = {
            "critical": "立即修復此問題，停止部署直到解決",
            "high": "優先修復此問題，建議在下次發布前解決",
            "medium": "計劃修復此問題，建議在未來版本中解決",
            "low": "考慮修復此問題以提高安全性",
            "info": "僅供參考，可選擇性處理"
        }
        return recommendations.get(severity, "請評估並適當處理此問題")
    
    def check_file_permissions(self) -> None:
        """檢查文件權限"""
        logger.info("檢查文件權限...")
        
        # 檢查敏感文件權限
        sensitive_files = [
            ".env",
            ".env.production",
            "config/database.yaml",
            "config/secrets.yaml",
            "private_key.pem",
            "ssl/private.key"
        ]
        
        for file_path in sensitive_files:
            full_path = PROJECT_ROOT / file_path
            if full_path.exists():
                file_stat = full_path.stat()
                file_mode = stat.filemode(file_stat.st_mode)
                
                # 檢查是否對其他用戶可讀
                if file_stat.st_mode & stat.S_IROTH:
                    self.add_issue(
                        "high",
                        "敏感文件對其他用戶可讀",
                        f"文件 {file_path} 對其他用戶可讀 ({file_mode})",
                        str(file_path),
                        recommendation="使用 chmod 600 限制文件權限僅對所有者可讀寫"
                    )
                
                # 檢查是否對組可寫
                if file_stat.st_mode & stat.S_IWGRP:
                    self.add_issue(
                        "medium",
                        "敏感文件對組可寫",
                        f"文件 {file_path} 對組可寫 ({file_mode})",
                        str(file_path),
                        recommendation="移除組寫權限以提高安全性"
                    )
    
    def check_hardcoded_secrets(self) -> None:
        """檢查硬編碼秘密"""
        logger.info("檢查硬編碼秘密...")
        
        # 要檢查的文件類型
        file_patterns = ["*.py", "*.yaml", "*.yml", "*.json", "*.conf", "*.cfg"]
        
        for pattern in file_patterns:
            for file_path in PROJECT_ROOT.rglob(pattern):
                # 跳過某些目錄
                if any(part in str(file_path) for part in ['.git', '__pycache__', '.pytest_cache', 'node_modules']):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')
                        
                        for line_num, line in enumerate(lines, 1):
                            # 檢查敏感模式
                            for pattern in self.sensitive_patterns:
                                if re.search(pattern, line, re.IGNORECASE):
                                    # 排除明顯的示例或註釋
                                    if not any(keyword in line.lower() for keyword in ['example', 'sample', 'placeholder', '#', '//']):
                                        self.add_issue(
                                            "critical",
                                            "發現硬編碼秘密",
                                            f"在第 {line_num} 行發現可能的硬編碼秘密: {line.strip()[:50]}...",
                                            str(file_path.relative_to(PROJECT_ROOT)),
                                            line_num,
                                            "將秘密移至環境變數或安全的秘密管理系統"
                                        )
                
                except Exception as e:
                    logger.warning(f"無法讀取文件 {file_path}: {e}")
    
    def check_dangerous_functions(self) -> None:
        """檢查危險函數使用"""
        logger.info("檢查危險函數使用...")
        
        for file_path in PROJECT_ROOT.rglob("*.py"):
            # 跳過測試文件和某些目錄
            if any(part in str(file_path) for part in ['.git', '__pycache__', 'test_', 'tests/']):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        for pattern in self.dangerous_functions:
                            if re.search(pattern, line):
                                # 檢查是否在註釋中
                                if not line.strip().startswith('#'):
                                    severity = "high" if "eval" in pattern or "exec" in pattern else "medium"
                                    self.add_issue(
                                        severity,
                                        "使用危險函數",
                                        f"在第 {line_num} 行使用危險函數: {line.strip()[:50]}...",
                                        str(file_path.relative_to(PROJECT_ROOT)),
                                        line_num,
                                        "避免使用危險函數，使用更安全的替代方案"
                                    )
            
            except Exception as e:
                logger.warning(f"無法讀取文件 {file_path}: {e}")
    
    def check_insecure_configurations(self) -> None:
        """檢查不安全配置"""
        logger.info("檢查不安全配置...")
        
        config_files = list(PROJECT_ROOT.rglob("*.yaml")) + list(PROJECT_ROOT.rglob("*.yml")) + list(PROJECT_ROOT.rglob("*.json"))
        
        for file_path in config_files:
            if any(part in str(file_path) for part in ['.git', '__pycache__']):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        for pattern in self.insecure_configs:
                            if re.search(pattern, line, re.IGNORECASE):
                                self.add_issue(
                                    "medium",
                                    "不安全配置",
                                    f"在第 {line_num} 行發現不安全配置: {line.strip()}",
                                    str(file_path.relative_to(PROJECT_ROOT)),
                                    line_num,
                                    "檢查並修正不安全的配置選項"
                                )
            
            except Exception as e:
                logger.warning(f"無法讀取文件 {file_path}: {e}")
    
    def check_docker_security(self) -> None:
        """檢查 Docker 安全配置"""
        logger.info("檢查 Docker 安全配置...")
        
        dockerfile_path = PROJECT_ROOT / "Dockerfile"
        if dockerfile_path.exists():
            try:
                with open(dockerfile_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    has_user = False
                    has_healthcheck = False
                    
                    for line_num, line in enumerate(lines, 1):
                        line = line.strip()
                        
                        # 檢查是否使用 root 用戶
                        if line.startswith('USER '):
                            has_user = True
                            if 'root' in line or '0' in line:
                                self.add_issue(
                                    "high",
                                    "Docker 容器使用 root 用戶",
                                    f"在第 {line_num} 行使用 root 用戶: {line}",
                                    "Dockerfile",
                                    line_num,
                                    "使用非特權用戶運行容器"
                                )
                        
                        # 檢查健康檢查
                        if line.startswith('HEALTHCHECK'):
                            has_healthcheck = True
                        
                        # 檢查危險的 RUN 命令
                        if line.startswith('RUN '):
                            if 'curl' in line and 'bash' in line:
                                self.add_issue(
                                    "medium",
                                    "Docker 中使用不安全的下載方式",
                                    f"在第 {line_num} 行使用 curl | bash: {line}",
                                    "Dockerfile",
                                    line_num,
                                    "使用更安全的軟體安裝方式"
                                )
                    
                    if not has_user:
                        self.add_issue(
                            "high",
                            "Docker 容器未指定用戶",
                            "Dockerfile 中未指定非 root 用戶",
                            "Dockerfile",
                            recommendation="添加 USER 指令使用非特權用戶"
                        )
                    
                    if not has_healthcheck:
                        self.add_issue(
                            "low",
                            "Docker 容器缺少健康檢查",
                            "Dockerfile 中未定義健康檢查",
                            "Dockerfile",
                            recommendation="添加 HEALTHCHECK 指令"
                        )
            
            except Exception as e:
                logger.warning(f"無法讀取 Dockerfile: {e}")
    
    def check_dependency_security(self) -> None:
        """檢查依賴安全性"""
        logger.info("檢查依賴安全性...")
        
        # 檢查 requirements.txt
        requirements_path = PROJECT_ROOT / "requirements.txt"
        if requirements_path.exists():
            try:
                with open(requirements_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # 檢查是否固定版本
                            if '==' not in line and '>=' not in line:
                                self.add_issue(
                                    "medium",
                                    "依賴版本未固定",
                                    f"在第 {line_num} 行依賴版本未固定: {line}",
                                    "requirements.txt",
                                    line_num,
                                    "固定依賴版本以確保可重現的構建"
                                )
            
            except Exception as e:
                logger.warning(f"無法讀取 requirements.txt: {e}")
        
        # 檢查 pyproject.toml
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        if pyproject_path.exists():
            try:
                with open(pyproject_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # 檢查是否有開發依賴在生產中
                    if '[tool.poetry.group.dev.dependencies]' in content:
                        self.add_issue(
                            "info",
                            "存在開發依賴配置",
                            "確保開發依賴不會安裝到生產環境",
                            "pyproject.toml",
                            recommendation="在生產構建中使用 --only=main 選項"
                        )
            
            except Exception as e:
                logger.warning(f"無法讀取 pyproject.toml: {e}")
    
    def check_network_security(self) -> None:
        """檢查網路安全配置"""
        logger.info("檢查網路安全配置...")
        
        # 檢查 nginx 配置
        nginx_config = PROJECT_ROOT / "config" / "nginx" / "nginx.conf"
        if nginx_config.exists():
            try:
                with open(nginx_config, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    if 'ssl_protocols' not in content:
                        self.add_issue(
                            "high",
                            "Nginx 未配置 SSL 協議",
                            "Nginx 配置中未指定 SSL 協議版本",
                            str(nginx_config.relative_to(PROJECT_ROOT)),
                            recommendation="配置安全的 SSL 協議版本"
                        )
                    
                    if 'ssl_ciphers' not in content:
                        self.add_issue(
                            "medium",
                            "Nginx 未配置 SSL 加密套件",
                            "Nginx 配置中未指定 SSL 加密套件",
                            str(nginx_config.relative_to(PROJECT_ROOT)),
                            recommendation="配置安全的 SSL 加密套件"
                        )
            
            except Exception as e:
                logger.warning(f"無法讀取 nginx 配置: {e}")
    
    def run_all_checks(self) -> Dict[str, Any]:
        """運行所有安全檢查"""
        logger.info("開始執行安全檢查...")
        
        # 執行各項檢查
        self.check_file_permissions()
        self.check_hardcoded_secrets()
        self.check_dangerous_functions()
        self.check_insecure_configurations()
        self.check_docker_security()
        self.check_dependency_security()
        self.check_network_security()
        
        # 生成報告
        report = {
            "scan_info": {
                "tool": "AI Trading System Custom Security Checker",
                "version": "1.0",
                "scan_time": "2024-12-25T00:00:00Z",
                "project_path": str(PROJECT_ROOT)
            },
            "summary": {
                "total_issues": len(self.issues),
                "by_severity": self.stats
            },
            "issues": self.issues
        }
        
        logger.info(f"安全檢查完成，發現 {len(self.issues)} 個問題")
        logger.info(f"嚴重程度分布: {self.stats}")
        
        return report


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="AI 交易系統自定義安全檢查")
    parser.add_argument("--output", "-o", help="輸出文件路徑", default="security-report.json")
    parser.add_argument("--format", "-f", choices=["json", "yaml"], default="json", help="輸出格式")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細輸出")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # 創建安全檢查器並運行檢查
        checker = SecurityChecker()
        report = checker.run_all_checks()
        
        # 保存報告
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if args.format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        elif args.format == "yaml":
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(report, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"安全報告已保存到: {output_path}")
        
        # 根據發現的問題設置退出碼
        if checker.stats["critical"] > 0:
            logger.error(f"發現 {checker.stats['critical']} 個關鍵安全問題")
            sys.exit(1)
        elif checker.stats["high"] > 0:
            logger.warning(f"發現 {checker.stats['high']} 個高風險安全問題")
            sys.exit(0)  # 高風險問題不阻止構建，但會記錄
        else:
            logger.info("未發現關鍵或高風險安全問題")
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"安全檢查失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
