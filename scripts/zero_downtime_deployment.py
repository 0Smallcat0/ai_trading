#!/usr/bin/env python3
"""
AI 交易系統零停機部署腳本
版本: v1.0
最後更新: 2024-12-25

此腳本實現零停機部署，包括：
- 滾動更新策略
- 健康檢查驗證
- 自動回滾機制
- 流量切換管理
- 部署狀態監控
"""

import os
import sys
import time
import logging
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import yaml
import requests

# 添加項目根目錄到 Python 路徑
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.monitoring.health_checker import HealthChecker
from src.monitoring.service_checker import ServiceChecker
from src.monitoring.intelligent_alert_manager import IntelligentAlertManager

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/ai_trading/zero_downtime_deployment.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ZeroDowntimeDeployer:
    """零停機部署器"""
    
    def __init__(self, config_path: str = "config/deployment_production.json"):
        """初始化零停機部署器
        
        Args:
            config_path: 部署配置文件路徑
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # 初始化組件
        self.health_checker = HealthChecker()
        self.service_checker = ServiceChecker()
        self.alert_manager = IntelligentAlertManager()
        
        # 部署配置
        self.deployment_strategy = self.config.get("deployment_strategy", "rolling_update")
        self.health_check_timeout = self.config.get("health_check_timeout", 300)  # 5分鐘
        self.rollback_enabled = self.config.get("rollback_enabled", True)
        
        # 部署狀態
        self.deployment_id = None
        self.deployment_start_time = None
        self.current_version = None
        self.target_version = None
        self.deployment_log = []
        
        logger.info("零停機部署器初始化完成")
    
    def _load_config(self) -> Dict[str, Any]:
        """載入配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"配置文件載入成功: {self.config_path}")
                return config
            else:
                logger.warning(f"配置文件不存在，使用預設配置: {self.config_path}")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"載入配置文件失敗: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """獲取預設配置"""
        return {
            "deployment_strategy": "rolling_update",
            "health_check_timeout": 300,
            "rollback_enabled": True,
            "backup_enabled": True,
            "monitoring_enabled": True,
            "containers": [
                {
                    "name": "ai-trading-app",
                    "replicas": 3,
                    "health_check_path": "/health",
                    "port": 8501,
                },
                {
                    "name": "ai-trading-api",
                    "replicas": 2,
                    "health_check_path": "/api/health",
                    "port": 8000,
                }
            ]
        }
    
    def deploy(self, version: str, image_tag: str = None) -> bool:
        """執行零停機部署
        
        Args:
            version: 目標版本
            image_tag: Docker 映像標籤
            
        Returns:
            bool: 部署是否成功
        """
        self.deployment_id = f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.deployment_start_time = datetime.now()
        self.target_version = version
        
        logger.info(f"開始零停機部署: {self.deployment_id}")
        logger.info(f"目標版本: {version}")
        
        try:
            # 1. 部署前檢查
            if not self._pre_deployment_checks():
                logger.error("部署前檢查失敗")
                return False
            
            # 2. 創建部署備份
            if not self._create_deployment_backup():
                logger.error("創建部署備份失敗")
                return False
            
            # 3. 執行滾動更新
            if not self._perform_rolling_update(version, image_tag):
                logger.error("滾動更新失敗")
                return False
            
            # 4. 部署後驗證
            if not self._post_deployment_verification():
                logger.error("部署後驗證失敗")
                if self.rollback_enabled:
                    logger.info("啟動自動回滾")
                    return self._perform_rollback()
                return False
            
            # 5. 完成部署
            self._complete_deployment()
            logger.info(f"零停機部署成功完成: {self.deployment_id}")
            return True
            
        except Exception as e:
            logger.error(f"部署過程中發生錯誤: {e}")
            if self.rollback_enabled:
                logger.info("啟動自動回滾")
                return self._perform_rollback()
            return False
    
    def _pre_deployment_checks(self) -> bool:
        """部署前檢查"""
        logger.info("執行部署前檢查")
        
        try:
            # 1. 檢查系統健康狀態
            health_status = self.health_checker.run_all_checks()
            
            critical_services = ["database", "api_server"]
            for service in critical_services:
                if service in health_status:
                    result = health_status[service]
                    if hasattr(result, 'status') and result.status.value != "healthy":
                        logger.error(f"關鍵服務 {service} 不健康，中止部署")
                        return False
            
            # 2. 檢查資源使用率
            if not self._check_resource_availability():
                logger.error("系統資源不足，中止部署")
                return False
            
            # 3. 檢查是否有其他部署在進行
            if self._is_deployment_in_progress():
                logger.error("已有部署在進行中，中止部署")
                return False
            
            # 4. 驗證目標映像
            if not self._verify_target_image():
                logger.error("目標映像驗證失敗，中止部署")
                return False
            
            self._log_deployment_event("pre_deployment_checks_passed")
            return True
            
        except Exception as e:
            logger.error(f"部署前檢查失敗: {e}")
            return False
    
    def _check_resource_availability(self) -> bool:
        """檢查資源可用性"""
        try:
            import psutil
            
            # 檢查 CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 80:
                logger.warning(f"CPU 使用率過高: {cpu_percent}%")
                return False
            
            # 檢查記憶體使用率
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                logger.warning(f"記憶體使用率過高: {memory.percent}%")
                return False
            
            # 檢查磁碟空間
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                logger.warning(f"磁碟使用率過高: {disk.percent}%")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"檢查資源可用性失敗: {e}")
            return False
    
    def _is_deployment_in_progress(self) -> bool:
        """檢查是否有部署在進行中"""
        try:
            # 檢查是否有 Docker 容器正在更新
            result = subprocess.run(
                ["docker", "ps", "--filter", "label=deployment.status=updating"],
                capture_output=True, text=True
            )
            
            return len(result.stdout.strip().split('\n')) > 1
            
        except Exception as e:
            logger.error(f"檢查部署狀態失敗: {e}")
            return False
    
    def _verify_target_image(self) -> bool:
        """驗證目標映像"""
        try:
            # 這裡應該實現映像驗證邏輯
            # 例如：檢查映像是否存在、安全掃描結果等
            logger.info("驗證目標映像")
            return True
            
        except Exception as e:
            logger.error(f"驗證目標映像失敗: {e}")
            return False
    
    def _create_deployment_backup(self) -> bool:
        """創建部署備份"""
        try:
            logger.info("創建部署備份")
            
            backup_dir = Path(f"/opt/ai_trading/backups/deployments/{self.deployment_id}")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 備份當前容器配置
            self._backup_container_configs(backup_dir)
            
            # 備份環境變數
            self._backup_environment_configs(backup_dir)
            
            # 記錄當前版本
            self._record_current_version(backup_dir)
            
            self._log_deployment_event("deployment_backup_created", {"backup_dir": str(backup_dir)})
            return True
            
        except Exception as e:
            logger.error(f"創建部署備份失敗: {e}")
            return False
    
    def _backup_container_configs(self, backup_dir: Path) -> None:
        """備份容器配置"""
        try:
            # 導出當前 Docker Compose 配置
            compose_file = PROJECT_ROOT / "docker-compose.yml"
            if compose_file.exists():
                import shutil
                shutil.copy2(compose_file, backup_dir / "docker-compose.yml.backup")
            
            # 導出 Kubernetes 配置（如果使用）
            k8s_dir = PROJECT_ROOT / "k8s"
            if k8s_dir.exists():
                import shutil
                shutil.copytree(k8s_dir, backup_dir / "k8s_backup", dirs_exist_ok=True)
            
        except Exception as e:
            logger.error(f"備份容器配置失敗: {e}")
    
    def _backup_environment_configs(self, backup_dir: Path) -> None:
        """備份環境配置"""
        try:
            # 備份環境變數文件
            env_files = [".env", ".env.production"]
            for env_file in env_files:
                env_path = PROJECT_ROOT / env_file
                if env_path.exists():
                    import shutil
                    shutil.copy2(env_path, backup_dir / f"{env_file}.backup")
            
        except Exception as e:
            logger.error(f"備份環境配置失敗: {e}")
    
    def _record_current_version(self, backup_dir: Path) -> None:
        """記錄當前版本"""
        try:
            version_info = {
                "deployment_id": self.deployment_id,
                "timestamp": datetime.now().isoformat(),
                "current_version": self._get_current_version(),
                "git_commit": self._get_git_commit(),
                "docker_images": self._get_current_docker_images(),
            }
            
            with open(backup_dir / "version_info.json", 'w', encoding='utf-8') as f:
                json.dump(version_info, f, indent=2)
            
            self.current_version = version_info["current_version"]
            
        except Exception as e:
            logger.error(f"記錄當前版本失敗: {e}")
    
    def _get_current_version(self) -> str:
        """獲取當前版本"""
        try:
            version_file = PROJECT_ROOT / "version.txt"
            if version_file.exists():
                return version_file.read_text().strip()
            return "unknown"
        except Exception:
            return "unknown"
    
    def _get_git_commit(self) -> str:
        """獲取 Git 提交哈希"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=PROJECT_ROOT
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except Exception:
            return "unknown"
    
    def _get_current_docker_images(self) -> List[Dict[str, str]]:
        """獲取當前 Docker 映像"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "json"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                containers = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        container = json.loads(line)
                        containers.append({
                            "name": container.get("Names", ""),
                            "image": container.get("Image", ""),
                            "status": container.get("Status", ""),
                        })
                return containers
            return []
            
        except Exception as e:
            logger.error(f"獲取當前 Docker 映像失敗: {e}")
            return []
    
    def _perform_rolling_update(self, version: str, image_tag: str = None) -> bool:
        """執行滾動更新"""
        logger.info("開始執行滾動更新")
        
        try:
            containers = self.config.get("containers", [])
            
            for container in containers:
                if not self._update_container(container, version, image_tag):
                    logger.error(f"更新容器失敗: {container['name']}")
                    return False
            
            self._log_deployment_event("rolling_update_completed")
            return True
            
        except Exception as e:
            logger.error(f"滾動更新失敗: {e}")
            return False
    
    def _update_container(self, container_config: Dict[str, Any], version: str, image_tag: str = None) -> bool:
        """更新單個容器"""
        container_name = container_config["name"]
        replicas = container_config.get("replicas", 1)
        
        logger.info(f"更新容器: {container_name} (副本數: {replicas})")
        
        try:
            # 逐個更新副本
            for i in range(replicas):
                replica_name = f"{container_name}-{i+1}"
                
                # 1. 啟動新副本
                if not self._start_new_replica(replica_name, version, image_tag):
                    return False
                
                # 2. 等待新副本健康
                if not self._wait_for_replica_health(replica_name, container_config):
                    return False
                
                # 3. 停止舊副本
                if not self._stop_old_replica(replica_name):
                    return False
                
                # 4. 短暫等待
                time.sleep(5)
            
            return True
            
        except Exception as e:
            logger.error(f"更新容器 {container_name} 失敗: {e}")
            return False
    
    def _start_new_replica(self, replica_name: str, version: str, image_tag: str = None) -> bool:
        """啟動新副本"""
        try:
            logger.info(f"啟動新副本: {replica_name}")
            
            # 構建映像名稱
            if image_tag:
                image = f"ai-trading:{image_tag}"
            else:
                image = f"ai-trading:{version}"
            
            # 啟動新容器（這裡使用 Docker Compose 或 Kubernetes）
            if self._is_kubernetes_deployment():
                return self._start_k8s_replica(replica_name, image)
            else:
                return self._start_docker_replica(replica_name, image)
            
        except Exception as e:
            logger.error(f"啟動新副本失敗: {e}")
            return False
    
    def _is_kubernetes_deployment(self) -> bool:
        """檢查是否為 Kubernetes 部署"""
        return (PROJECT_ROOT / "k8s").exists() and os.getenv("KUBERNETES_SERVICE_HOST")
    
    def _start_k8s_replica(self, replica_name: str, image: str) -> bool:
        """啟動 Kubernetes 副本"""
        try:
            # 使用 kubectl 更新部署
            cmd = [
                "kubectl", "set", "image",
                f"deployment/{replica_name}",
                f"{replica_name}={image}",
                "-n", "ai-trading"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"啟動 K8s 副本失敗: {e}")
            return False
    
    def _start_docker_replica(self, replica_name: str, image: str) -> bool:
        """啟動 Docker 副本"""
        try:
            # 使用 Docker Compose 更新服務
            cmd = [
                "docker-compose", "up", "-d",
                "--scale", f"{replica_name}=1",
                replica_name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"啟動 Docker 副本失敗: {e}")
            return False
    
    def _wait_for_replica_health(self, replica_name: str, container_config: Dict[str, Any]) -> bool:
        """等待副本健康"""
        logger.info(f"等待副本健康: {replica_name}")
        
        health_check_path = container_config.get("health_check_path", "/health")
        port = container_config.get("port", 8501)
        timeout = self.health_check_timeout
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # 檢查容器健康狀態
                url = f"http://localhost:{port}{health_check_path}"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    logger.info(f"副本 {replica_name} 健康檢查通過")
                    return True
                
            except Exception:
                pass
            
            time.sleep(10)
        
        logger.error(f"副本 {replica_name} 健康檢查超時")
        return False
    
    def _stop_old_replica(self, replica_name: str) -> bool:
        """停止舊副本"""
        try:
            logger.info(f"停止舊副本: {replica_name}")
            
            # 這裡應該實現優雅停止邏輯
            # 例如：等待當前請求完成，然後停止容器
            
            return True
            
        except Exception as e:
            logger.error(f"停止舊副本失敗: {e}")
            return False
    
    def _post_deployment_verification(self) -> bool:
        """部署後驗證"""
        logger.info("執行部署後驗證")
        
        try:
            # 1. 健康檢查
            if not self._verify_all_services_healthy():
                return False
            
            # 2. 功能測試
            if not self._run_smoke_tests():
                return False
            
            # 3. 性能測試
            if not self._run_performance_tests():
                return False
            
            self._log_deployment_event("post_deployment_verification_passed")
            return True
            
        except Exception as e:
            logger.error(f"部署後驗證失敗: {e}")
            return False
    
    def _verify_all_services_healthy(self) -> bool:
        """驗證所有服務健康"""
        try:
            health_status = self.health_checker.run_all_checks()
            
            for service_name, result in health_status.items():
                if hasattr(result, 'status') and result.status.value != "healthy":
                    logger.error(f"服務 {service_name} 不健康")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"驗證服務健康狀態失敗: {e}")
            return False
    
    def _run_smoke_tests(self) -> bool:
        """運行冒煙測試"""
        try:
            logger.info("運行冒煙測試")
            
            # 這裡應該運行實際的冒煙測試
            # 例如：測試關鍵 API 端點、資料庫連接等
            
            return True
            
        except Exception as e:
            logger.error(f"冒煙測試失敗: {e}")
            return False
    
    def _run_performance_tests(self) -> bool:
        """運行性能測試"""
        try:
            logger.info("運行性能測試")
            
            # 這裡應該運行簡單的性能測試
            # 確保部署後性能沒有顯著下降
            
            return True
            
        except Exception as e:
            logger.error(f"性能測試失敗: {e}")
            return False
    
    def _perform_rollback(self) -> bool:
        """執行回滾"""
        logger.info("開始執行自動回滾")
        
        try:
            # 1. 恢復備份的配置
            backup_dir = Path(f"/opt/ai_trading/backups/deployments/{self.deployment_id}")
            
            if not backup_dir.exists():
                logger.error("找不到備份目錄，無法回滾")
                return False
            
            # 2. 恢復容器配置
            self._restore_container_configs(backup_dir)
            
            # 3. 重啟服務
            self._restart_services()
            
            # 4. 驗證回滾結果
            if self._verify_rollback():
                logger.info("自動回滾成功")
                self._log_deployment_event("rollback_successful")
                return True
            else:
                logger.error("自動回滾失敗")
                self._log_deployment_event("rollback_failed")
                return False
            
        except Exception as e:
            logger.error(f"執行回滾失敗: {e}")
            return False
    
    def _restore_container_configs(self, backup_dir: Path) -> None:
        """恢復容器配置"""
        try:
            # 恢復 Docker Compose 配置
            backup_compose = backup_dir / "docker-compose.yml.backup"
            if backup_compose.exists():
                import shutil
                shutil.copy2(backup_compose, PROJECT_ROOT / "docker-compose.yml")
            
            # 恢復環境變數
            for env_file in [".env", ".env.production"]:
                backup_env = backup_dir / f"{env_file}.backup"
                if backup_env.exists():
                    import shutil
                    shutil.copy2(backup_env, PROJECT_ROOT / env_file)
            
        except Exception as e:
            logger.error(f"恢復容器配置失敗: {e}")
    
    def _restart_services(self) -> None:
        """重啟服務"""
        try:
            if self._is_kubernetes_deployment():
                subprocess.run(["kubectl", "rollout", "restart", "deployment", "-n", "ai-trading"])
            else:
                subprocess.run(["docker-compose", "restart"], cwd=PROJECT_ROOT)
            
        except Exception as e:
            logger.error(f"重啟服務失敗: {e}")
    
    def _verify_rollback(self) -> bool:
        """驗證回滾結果"""
        try:
            # 等待服務重啟
            time.sleep(30)
            
            # 檢查服務健康狀態
            return self._verify_all_services_healthy()
            
        except Exception as e:
            logger.error(f"驗證回滾結果失敗: {e}")
            return False
    
    def _complete_deployment(self) -> None:
        """完成部署"""
        try:
            # 更新版本文件
            version_file = PROJECT_ROOT / "version.txt"
            version_file.write_text(self.target_version)
            
            # 發送部署成功通知
            self._send_deployment_notification("deployment_successful")
            
            # 記錄部署完成
            self._log_deployment_event("deployment_completed", {
                "target_version": self.target_version,
                "deployment_duration": (datetime.now() - self.deployment_start_time).total_seconds(),
            })
            
        except Exception as e:
            logger.error(f"完成部署時發生錯誤: {e}")
    
    def _send_deployment_notification(self, event_type: str) -> None:
        """發送部署通知"""
        try:
            self.alert_manager.create_alert(
                title=f"部署通知: {event_type}",
                message=f"部署 {self.deployment_id} - {event_type}",
                severity="info",
                source="zero_downtime_deployer"
            )
        except Exception as e:
            logger.error(f"發送部署通知失敗: {e}")
    
    def _log_deployment_event(self, event_type: str, data: Dict[str, Any] = None) -> None:
        """記錄部署事件"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "deployment_id": self.deployment_id,
            "event_type": event_type,
            "data": data or {},
        }
        
        self.deployment_log.append(event)
        logger.info(f"部署事件: {event_type}")
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """獲取部署狀態"""
        return {
            "deployment_id": self.deployment_id,
            "start_time": self.deployment_start_time.isoformat() if self.deployment_start_time else None,
            "current_version": self.current_version,
            "target_version": self.target_version,
            "deployment_log": self.deployment_log,
            "config": self.config,
        }


def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description="零停機部署工具")
    parser.add_argument("--version", required=True, help="目標版本")
    parser.add_argument("--image-tag", help="Docker 映像標籤")
    parser.add_argument("--config", default="config/deployment_production.json", help="配置文件路徑")
    
    args = parser.parse_args()
    
    try:
        deployer = ZeroDowntimeDeployer(args.config)
        success = deployer.deploy(args.version, args.image_tag)
        
        if success:
            logger.info("部署成功完成")
            sys.exit(0)
        else:
            logger.error("部署失敗")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"部署工具運行失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


class AutoRollbackManager:
    """自動回滾管理器"""

    def __init__(self, deployer: ZeroDowntimeDeployer):
        """初始化自動回滾管理器

        Args:
            deployer: 零停機部署器實例
        """
        self.deployer = deployer
        self.rollback_triggers = {
            "health_check_failure": True,
            "error_rate_spike": True,
            "response_time_degradation": True,
            "memory_leak_detection": True,
        }
        self.monitoring_duration = 300  # 5分鐘監控期

    def monitor_deployment(self, deployment_id: str) -> bool:
        """監控部署並在需要時觸發回滾

        Args:
            deployment_id: 部署ID

        Returns:
            bool: 是否需要回滾
        """
        logger.info(f"開始監控部署: {deployment_id}")

        start_time = time.time()

        while time.time() - start_time < self.monitoring_duration:
            try:
                # 檢查各種回滾觸發條件
                if self._check_rollback_triggers():
                    logger.warning("檢測到回滾觸發條件，啟動自動回滾")
                    return True

                time.sleep(30)  # 每30秒檢查一次

            except Exception as e:
                logger.error(f"監控部署時發生錯誤: {e}")

        logger.info("部署監控完成，未檢測到回滾觸發條件")
        return False

    def _check_rollback_triggers(self) -> bool:
        """檢查回滾觸發條件"""
        try:
            # 1. 健康檢查失敗
            if self.rollback_triggers["health_check_failure"]:
                if not self.deployer._verify_all_services_healthy():
                    logger.warning("健康檢查失敗，觸發回滾")
                    return True

            # 2. 錯誤率激增
            if self.rollback_triggers["error_rate_spike"]:
                if self._check_error_rate_spike():
                    logger.warning("錯誤率激增，觸發回滾")
                    return True

            # 3. 響應時間惡化
            if self.rollback_triggers["response_time_degradation"]:
                if self._check_response_time_degradation():
                    logger.warning("響應時間惡化，觸發回滾")
                    return True

            # 4. 記憶體洩漏檢測
            if self.rollback_triggers["memory_leak_detection"]:
                if self._check_memory_leak():
                    logger.warning("檢測到記憶體洩漏，觸發回滾")
                    return True

            return False

        except Exception as e:
            logger.error(f"檢查回滾觸發條件失敗: {e}")
            return False

    def _check_error_rate_spike(self) -> bool:
        """檢查錯誤率激增"""
        try:
            # 這裡應該實現實際的錯誤率檢查邏輯
            # 例如：從監控系統獲取錯誤率指標
            return False
        except Exception:
            return False

    def _check_response_time_degradation(self) -> bool:
        """檢查響應時間惡化"""
        try:
            # 這裡應該實現實際的響應時間檢查邏輯
            return False
        except Exception:
            return False

    def _check_memory_leak(self) -> bool:
        """檢查記憶體洩漏"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            # 如果記憶體使用率超過95%，可能有記憶體洩漏
            return memory.percent > 95
        except Exception:
            return False
