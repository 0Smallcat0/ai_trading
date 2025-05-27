#!/usr/bin/env python3
"""部署驗證腳本

此腳本驗證代碼品質審計後的生產部署是否成功，包括：
- 功能驗證
- 效能監控驗證
- 錯誤處理驗證
- 向後相容性驗證

使用方法:
    python scripts/validate_deployment.py --environment prod
    python scripts/validate_deployment.py --environment prod --detailed
"""

import os
import sys
import logging
import argparse
import requests
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 設置日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class DeploymentValidator:
    """部署驗證器"""

    def __init__(
        self, environment: str = "prod", base_url: str = "http://localhost:8000"
    ):
        """初始化驗證器

        Args:
            environment: 部署環境
            base_url: API 基礎 URL
        """
        self.environment = environment
        self.base_url = base_url
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "environment": environment,
            "tests": {},
            "overall_status": "unknown",
        }

    def validate_api_health(self) -> bool:
        """驗證 API 健康狀態"""
        logger.info("🔍 驗證 API 健康狀態...")

        try:
            # 測試根端點
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code != 200:
                logger.error(f"根端點失敗: {response.status_code}")
                return False

            # 測試健康檢查端點
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code != 200:
                logger.error(f"健康檢查失敗: {response.status_code}")
                return False

            # 測試 API 資訊端點
            response = requests.get(f"{self.base_url}/api/info", timeout=10)
            if response.status_code != 200:
                logger.error(f"API 資訊端點失敗: {response.status_code}")
                return False

            logger.info("✅ API 健康狀態驗證通過")
            self.validation_results["tests"]["api_health"] = {
                "status": "passed",
                "details": "所有核心端點正常回應",
            }
            return True

        except Exception as e:
            logger.error(f"API 健康檢查失敗: {e}")
            self.validation_results["tests"]["api_health"] = {
                "status": "failed",
                "error": str(e),
            }
            return False

    def validate_error_handling(self) -> bool:
        """驗證增強的錯誤處理"""
        logger.info("🔍 驗證增強的錯誤處理...")

        try:
            # 測試無效的認證請求
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"username": "", "password": ""},
                timeout=10,
            )

            # 應該返回適當的錯誤狀態碼
            if response.status_code not in [400, 401, 422]:
                logger.error(f"錯誤處理測試失敗: 預期 4xx，得到 {response.status_code}")
                return False

            # 檢查錯誤回應格式
            try:
                error_data = response.json()
                if "detail" not in error_data and "message" not in error_data:
                    logger.error("錯誤回應缺少詳細資訊")
                    return False
            except json.JSONDecodeError:
                logger.error("錯誤回應不是有效的 JSON")
                return False

            logger.info("✅ 錯誤處理驗證通過")
            self.validation_results["tests"]["error_handling"] = {
                "status": "passed",
                "details": "錯誤回應格式正確",
            }
            return True

        except Exception as e:
            logger.error(f"錯誤處理驗證失敗: {e}")
            self.validation_results["tests"]["error_handling"] = {
                "status": "failed",
                "error": str(e),
            }
            return False

    def validate_performance(self) -> bool:
        """驗證效能沒有回歸"""
        logger.info("🔍 驗證效能...")

        try:
            # 測試 API 回應時間
            endpoints = ["/", "/health", "/api/info"]

            response_times = []

            for endpoint in endpoints:
                start_time = time.time()
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                end_time = time.time()

                response_time = (end_time - start_time) * 1000  # 轉換為毫秒
                response_times.append(response_time)

                if response.status_code != 200:
                    logger.error(f"端點 {endpoint} 回應失敗: {response.status_code}")
                    return False

                logger.info(f"端點 {endpoint}: {response_time:.2f}ms")

            # 檢查平均回應時間
            avg_response_time = sum(response_times) / len(response_times)
            if avg_response_time > 2000:  # 2 秒閾值
                logger.warning(f"平均回應時間較慢: {avg_response_time:.2f}ms")

            logger.info(f"✅ 效能驗證通過 (平均回應時間: {avg_response_time:.2f}ms)")
            self.validation_results["tests"]["performance"] = {
                "status": "passed",
                "avg_response_time_ms": avg_response_time,
                "details": f"平均回應時間: {avg_response_time:.2f}ms",
            }
            return True

        except Exception as e:
            logger.error(f"效能驗證失敗: {e}")
            self.validation_results["tests"]["performance"] = {
                "status": "failed",
                "error": str(e),
            }
            return False

    def validate_backward_compatibility(self) -> bool:
        """驗證向後相容性"""
        logger.info("🔍 驗證向後相容性...")

        try:
            # 測試核心模組導入
            import_tests = [
                ("Web UI", "from src.ui.web_ui import run_web_ui"),
                ("API Main", "from src.api.main import app"),
                (
                    "Auth Service",
                    "from src.core.authentication_service import AuthenticationService",
                ),
                ("API Auth Router", "from src.api.routers.auth import router"),
            ]

            for test_name, import_stmt in import_tests:
                try:
                    exec(import_stmt)
                    logger.info(f"✅ {test_name} 導入成功")
                except Exception as e:
                    logger.error(f"❌ {test_name} 導入失敗: {e}")
                    self.validation_results["tests"]["backward_compatibility"] = {
                        "status": "failed",
                        "failed_import": test_name,
                        "error": str(e),
                    }
                    return False

            logger.info("✅ 向後相容性驗證通過")
            self.validation_results["tests"]["backward_compatibility"] = {
                "status": "passed",
                "details": "所有核心模組導入成功",
            }
            return True

        except Exception as e:
            logger.error(f"向後相容性驗證失敗: {e}")
            self.validation_results["tests"]["backward_compatibility"] = {
                "status": "failed",
                "error": str(e),
            }
            return False

    def validate_monitoring_setup(self) -> bool:
        """驗證監控設置"""
        logger.info("🔍 驗證監控設置...")

        try:
            # 檢查監控配置檔案
            monitoring_config_file = (
                PROJECT_ROOT / f"config/monitoring_{self.environment}.json"
            )
            if not monitoring_config_file.exists():
                logger.error(f"監控配置檔案不存在: {monitoring_config_file}")
                return False

            # 載入並驗證監控配置
            with open(monitoring_config_file, "r", encoding="utf-8") as f:
                monitoring_config = json.load(f)

            # 檢查必要的監控配置
            required_sections = [
                "error_tracking",
                "performance_monitoring",
                "structured_logging",
                "alerts",
            ]

            for section in required_sections:
                if section not in monitoring_config:
                    logger.error(f"監控配置缺少必要部分: {section}")
                    return False

            logger.info("✅ 監控設置驗證通過")
            self.validation_results["tests"]["monitoring_setup"] = {
                "status": "passed",
                "config_file": str(monitoring_config_file),
                "details": "監控配置完整",
            }
            return True

        except Exception as e:
            logger.error(f"監控設置驗證失敗: {e}")
            self.validation_results["tests"]["monitoring_setup"] = {
                "status": "failed",
                "error": str(e),
            }
            return False

    def validate_dependencies(self) -> bool:
        """驗證生產依賴"""
        logger.info("🔍 驗證生產依賴...")

        try:
            # 檢查生產 requirements 檔案
            prod_requirements = PROJECT_ROOT / "requirements-production.txt"
            if not prod_requirements.exists():
                logger.error("生產 requirements 檔案不存在")
                return False

            # 檢查關鍵依賴
            with open(prod_requirements, "r", encoding="utf-8") as f:
                requirements_content = f.read()

            critical_deps = [
                "bcrypt",  # 密碼雜湊
                "fastapi",  # API 框架
                "streamlit",  # UI 框架
                "pylint",  # 代碼品質
                "structlog",  # 結構化日誌
            ]

            for dep in critical_deps:
                if dep not in requirements_content:
                    logger.error(f"關鍵依賴缺失: {dep}")
                    return False
                logger.info(f"✅ 找到關鍵依賴: {dep}")

            logger.info("✅ 依賴驗證通過")
            self.validation_results["tests"]["dependencies"] = {
                "status": "passed",
                "requirements_file": str(prod_requirements),
                "critical_deps_found": critical_deps,
            }
            return True

        except Exception as e:
            logger.error(f"依賴驗證失敗: {e}")
            self.validation_results["tests"]["dependencies"] = {
                "status": "failed",
                "error": str(e),
            }
            return False

    def run_full_validation(self, detailed: bool = False) -> bool:
        """執行完整驗證"""
        logger.info(f"🚀 開始 {self.environment} 環境部署驗證...")

        validation_tests = [
            ("API 健康狀態", self.validate_api_health),
            ("錯誤處理", self.validate_error_handling),
            ("效能", self.validate_performance),
            ("向後相容性", self.validate_backward_compatibility),
            ("監控設置", self.validate_monitoring_setup),
            ("依賴", self.validate_dependencies),
        ]

        passed_tests = 0
        total_tests = len(validation_tests)

        for test_name, test_func in validation_tests:
            logger.info(f"\n--- 執行 {test_name} 驗證 ---")
            try:
                if test_func():
                    passed_tests += 1
                    logger.info(f"✅ {test_name} 驗證通過")
                else:
                    logger.error(f"❌ {test_name} 驗證失敗")
            except Exception as e:
                logger.error(f"❌ {test_name} 驗證異常: {e}")

        # 計算總體結果
        success_rate = (passed_tests / total_tests) * 100
        overall_success = passed_tests == total_tests

        self.validation_results["overall_status"] = (
            "passed" if overall_success else "failed"
        )
        self.validation_results["success_rate"] = success_rate
        self.validation_results["passed_tests"] = passed_tests
        self.validation_results["total_tests"] = total_tests

        # 輸出結果摘要
        logger.info(f"\n📊 驗證結果摘要:")
        logger.info(f"通過測試: {passed_tests}/{total_tests}")
        logger.info(f"成功率: {success_rate:.1f}%")
        logger.info(f"總體狀態: {'✅ 通過' if overall_success else '❌ 失敗'}")

        # 保存驗證結果
        results_file = (
            PROJECT_ROOT
            / f"logs/validation_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        results_file.parent.mkdir(exist_ok=True)

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(self.validation_results, f, indent=2, ensure_ascii=False)

        logger.info(f"📋 驗證結果已保存: {results_file}")

        if detailed:
            logger.info(f"\n📄 詳細結果:")
            for test_name, result in self.validation_results["tests"].items():
                logger.info(f"  {test_name}: {result['status']}")
                if "details" in result:
                    logger.info(f"    詳情: {result['details']}")
                if "error" in result:
                    logger.info(f"    錯誤: {result['error']}")

        return overall_success


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="AI 交易系統部署驗證")
    parser.add_argument(
        "--environment",
        choices=["dev", "test", "prod"],
        default="prod",
        help="驗證環境",
    )
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="API 基礎 URL"
    )
    parser.add_argument("--detailed", action="store_true", help="顯示詳細驗證結果")

    args = parser.parse_args()

    # 創建驗證器
    validator = DeploymentValidator(args.environment, args.base_url)

    try:
        success = validator.run_full_validation(args.detailed)
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("驗證被用戶中斷")
        sys.exit(1)
    except Exception as e:
        logger.error(f"驗證過程中發生未預期的錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
