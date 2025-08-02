#!/usr/bin/env python3
"""生產環境部署腳本

此腳本實施代碼品質審計後的即時生產部署行動，包括：
- 部署改進的模組 (Pylint ≥9.0/10)
- 驗證向後相容性
- 設置效能監控
- 更新文檔

使用方法:
    python scripts/deploy_production.py --environment prod --validate-only
    python scripts/deploy_production.py --environment prod --deploy
"""

import os
import sys
import logging
import argparse
import subprocess
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


class ProductionDeployment:
    """生產環境部署管理器"""

    def __init__(self, environment: str = "prod"):
        """初始化部署管理器

        Args:
            environment: 部署環境 (dev/test/prod)
        """
        self.environment = environment
        self.deployment_config = self._load_deployment_config()
        self.improved_modules = [
            "src/ui/web_ui.py",
            "src/api/routers/auth.py",
            "src/api/main.py",
            "src/core/authentication_service.py",
            "src/ui/components/auth.py",
        ]

    def _load_deployment_config(self) -> Dict:
        """載入部署配置"""
        config_file = PROJECT_ROOT / f"config/deployment_{self.environment}.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)

        # 預設配置
        return {
            "environment": self.environment,
            "quality_threshold": 9.0,
            "backup_enabled": True,
            "monitoring_enabled": True,
            "rollback_enabled": True,
        }

    def validate_code_quality(self) -> Tuple[bool, Dict[str, float]]:
        """驗證代碼品質

        Returns:
            Tuple[bool, Dict[str, float]]: (是否通過, 模組評分)
        """
        logger.info("🔍 驗證代碼品質...")
        scores = {}
        all_passed = True

        for module in self.improved_modules:
            module_path = PROJECT_ROOT / module
            if not module_path.exists():
                logger.warning(f"模組不存在: {module}")
                continue

            try:
                # 執行 pylint 檢查
                result = subprocess.run(
                    ["python", "-m", "pylint", str(module_path), "--score=y"],
                    capture_output=True,
                    text=True,
                    cwd=PROJECT_ROOT,
                )

                # 解析評分
                output = result.stdout
                for line in output.split("\n"):
                    if "Your code has been rated at" in line:
                        score_str = line.split("at ")[1].split("/")[0]
                        score = float(score_str)
                        scores[module] = score

                        if score < self.deployment_config["quality_threshold"]:
                            logger.error(
                                f"❌ {module}: {score}/10 (低於閾值 {self.deployment_config['quality_threshold']})"
                            )
                            all_passed = False
                        else:
                            logger.info(f"✅ {module}: {score}/10")
                        break

            except Exception as e:
                logger.error(f"檢查 {module} 時發生錯誤: {e}")
                all_passed = False

        return all_passed, scores

    def validate_backward_compatibility(self) -> bool:
        """驗證向後相容性"""
        logger.info("🔄 驗證向後相容性...")

        try:
            # 測試核心模組導入
            test_imports = [
                "from src.ui.web_ui import run_web_ui",
                "from src.api.main import app",
                "from src.core.authentication_service import AuthenticationService",
                "from src.api.routers.auth import router",
            ]

            for import_stmt in test_imports:
                try:
                    exec(import_stmt)
                    logger.info(f"✅ 導入成功: {import_stmt}")
                except Exception as e:
                    logger.error(f"❌ 導入失敗: {import_stmt} - {e}")
                    return False

            logger.info("✅ 向後相容性驗證通過")
            return True

        except Exception as e:
            logger.error(f"向後相容性驗證失敗: {e}")
            return False

    def setup_monitoring(self) -> bool:
        """設置效能監控"""
        logger.info("📊 設置效能監控...")

        try:
            # 創建監控配置
            monitoring_config = {
                "error_tracking": {
                    "enabled": True,
                    "chained_exceptions": True,
                    "lazy_logging": True,
                },
                "performance_monitoring": {
                    "api_response_times": True,
                    "error_rates": True,
                    "resolution_times": True,
                },
                "structured_logging": {
                    "format": "json",
                    "level": "INFO",
                    "include_traceback": True,
                },
            }

            # 保存監控配置
            monitoring_file = (
                PROJECT_ROOT / f"config/monitoring_{self.environment}.json"
            )
            monitoring_file.parent.mkdir(exist_ok=True)

            with open(monitoring_file, "w", encoding="utf-8") as f:
                json.dump(monitoring_config, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ 監控配置已保存: {monitoring_file}")
            return True

        except Exception as e:
            logger.error(f"設置監控失敗: {e}")
            return False

    def create_deployment_backup(self) -> Optional[str]:
        """創建部署備份"""
        if not self.deployment_config.get("backup_enabled", True):
            return None

        logger.info("💾 創建部署備份...")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = PROJECT_ROOT / f"backups/deployment_{timestamp}"
            backup_dir.mkdir(parents=True, exist_ok=True)

            # 備份改進的模組
            for module in self.improved_modules:
                module_path = PROJECT_ROOT / module
                if module_path.exists():
                    backup_path = backup_dir / module
                    backup_path.parent.mkdir(parents=True, exist_ok=True)

                    import shutil

                    shutil.copy2(module_path, backup_path)

            logger.info(f"✅ 備份已創建: {backup_dir}")
            return str(backup_dir)

        except Exception as e:
            logger.error(f"創建備份失敗: {e}")
            return None

    def deploy_to_production(self) -> bool:
        """部署到生產環境"""
        logger.info(f"🚀 開始部署到 {self.environment} 環境...")

        try:
            # 1. 創建備份
            backup_path = self.create_deployment_backup()
            if self.deployment_config.get("backup_enabled", True) and not backup_path:
                logger.error("備份創建失敗，中止部署")
                return False

            # 2. 驗證代碼品質
            quality_passed, scores = self.validate_code_quality()
            if not quality_passed:
                logger.error("代碼品質驗證失敗，中止部署")
                return False

            # 3. 驗證向後相容性
            if not self.validate_backward_compatibility():
                logger.error("向後相容性驗證失敗，中止部署")
                return False

            # 4. 設置監控
            if not self.setup_monitoring():
                logger.warning("監控設置失敗，但繼續部署")

            # 5. 記錄部署資訊
            deployment_info = {
                "timestamp": datetime.now().isoformat(),
                "environment": self.environment,
                "modules": self.improved_modules,
                "quality_scores": scores,
                "backup_path": backup_path,
                "status": "success",
            }

            deployment_log = PROJECT_ROOT / f"logs/deployment_{self.environment}.json"
            deployment_log.parent.mkdir(exist_ok=True)

            with open(deployment_log, "w", encoding="utf-8") as f:
                json.dump(deployment_info, f, indent=2, ensure_ascii=False)

            logger.info("🎉 部署成功完成！")
            logger.info(f"📋 部署日誌: {deployment_log}")

            return True

        except Exception as e:
            logger.error(f"部署失敗: {e}")
            return False

    def validate_only(self) -> bool:
        """僅執行驗證（不部署）"""
        logger.info("🔍 執行驗證模式...")

        # 驗證代碼品質
        quality_passed, scores = self.validate_code_quality()

        # 驗證向後相容性
        compatibility_passed = self.validate_backward_compatibility()

        # 輸出結果
        logger.info("\n📊 驗證結果摘要:")
        logger.info(f"代碼品質: {'✅ 通過' if quality_passed else '❌ 失敗'}")
        logger.info(f"向後相容性: {'✅ 通過' if compatibility_passed else '❌ 失敗'}")

        if scores:
            logger.info("\n📈 模組評分:")
            for module, score in scores.items():
                logger.info(f"  {module}: {score}/10")

        return quality_passed and compatibility_passed


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="AI 交易系統生產環境部署")
    parser.add_argument(
        "--environment",
        choices=["dev", "test", "prod"],
        default="prod",
        help="部署環境",
    )
    parser.add_argument(
        "--validate-only", action="store_true", help="僅執行驗證，不進行實際部署"
    )
    parser.add_argument("--deploy", action="store_true", help="執行實際部署")

    args = parser.parse_args()

    if not (args.validate_only or args.deploy):
        parser.error("必須指定 --validate-only 或 --deploy")

    # 創建部署管理器
    deployer = ProductionDeployment(args.environment)

    try:
        if args.validate_only:
            success = deployer.validate_only()
        else:
            success = deployer.deploy_to_production()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("部署被用戶中斷")
        sys.exit(1)
    except Exception as e:
        logger.error(f"部署過程中發生未預期的錯誤: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
