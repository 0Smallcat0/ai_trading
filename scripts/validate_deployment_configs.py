#!/usr/bin/env python3
"""
部署配置驗證腳本

此腳本驗證所有部署配置檔案的正確性，包括：
1. Docker Compose 配置語法檢查
2. Kubernetes YAML 配置驗證
3. 環境變數一致性檢查
4. 服務依賴關係驗證
5. 資源配置合理性檢查
"""

import os
import sys
import yaml
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional


class DeploymentConfigValidator:
    """部署配置驗證器"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.project_root = Path(".")

    def validate_all(self) -> Dict[str, Any]:
        """驗證所有配置"""
        print("🔍 開始驗證部署配置...")

        results = {
            "docker_compose": self.validate_docker_compose(),
            "kubernetes": self.validate_kubernetes_configs(),
            "environment": self.validate_environment_configs(),
            "consistency": self.validate_consistency(),
            "summary": {
                "total_errors": len(self.errors),
                "total_warnings": len(self.warnings),
                "errors": self.errors,
                "warnings": self.warnings,
            },
        }

        return results

    def validate_docker_compose(self) -> Dict[str, Any]:
        """驗證 Docker Compose 配置"""
        print("🐳 驗證 Docker Compose 配置...")
        results = {}

        # 驗證主要的 docker-compose 檔案
        compose_files = ["docker-compose.yml", "docker-compose.dev.yml"]

        for compose_file in compose_files:
            file_path = self.project_root / compose_file
            if file_path.exists():
                results[compose_file] = self._validate_compose_file(file_path)
            else:
                self.warnings.append(f"{compose_file} 不存在")

        return results

    def _validate_compose_file(self, file_path: Path) -> Dict[str, Any]:
        """驗證單個 Docker Compose 檔案"""
        result = {"valid": True, "issues": [], "services": []}

        try:
            # 使用 docker-compose config 驗證語法
            cmd = ["docker-compose", "-f", str(file_path), "config", "--quiet"]
            process = subprocess.run(cmd, capture_output=True, text=True)

            if process.returncode != 0:
                result["valid"] = False
                result["issues"].append(f"Docker Compose 語法錯誤: {process.stderr}")
                self.errors.append(f"{file_path.name}: {process.stderr}")
                return result

            # 解析 YAML 內容
            with open(file_path, "r", encoding="utf-8") as f:
                compose_data = yaml.safe_load(f)

            # 檢查服務配置
            if "services" in compose_data:
                for service_name, service_config in compose_data["services"].items():
                    service_result = self._validate_service(
                        service_name, service_config, file_path.name
                    )
                    result["services"].append(service_result)

            # 檢查網路配置
            if "networks" not in compose_data:
                result["issues"].append("建議定義自定義網路")

            # 檢查資料卷配置
            if "volumes" not in compose_data:
                result["issues"].append("建議定義持久化資料卷")

        except yaml.YAMLError as e:
            result["valid"] = False
            result["issues"].append(f"YAML 語法錯誤: {e}")
            self.errors.append(f"{file_path.name}: YAML 語法錯誤")
        except FileNotFoundError:
            result["valid"] = False
            result["issues"].append("Docker Compose 命令未找到")
            self.warnings.append("無法執行 docker-compose 命令驗證")
        except Exception as e:
            result["valid"] = False
            result["issues"].append(f"驗證失敗: {e}")

        return result

    def _validate_service(
        self, service_name: str, config: Dict, filename: str
    ) -> Dict[str, Any]:
        """驗證服務配置"""
        result = {"name": service_name, "valid": True, "issues": []}

        # 檢查必要配置
        if "image" not in config and "build" not in config:
            result["valid"] = False
            result["issues"].append("缺少 image 或 build 配置")

        # 檢查重啟策略
        if "restart" not in config:
            result["issues"].append("建議設定重啟策略")

        # 檢查健康檢查
        if "healthcheck" not in config:
            result["issues"].append("建議添加健康檢查")

        # 檢查資源限制
        if "deploy" not in config and "mem_limit" not in config:
            result["issues"].append("建議設定資源限制")

        # 檢查環境變數安全性
        if "environment" in config:
            env_vars = config["environment"]
            if isinstance(env_vars, list):
                for env_var in env_vars:
                    if isinstance(env_var, str) and "=" in env_var:
                        key, value = env_var.split("=", 1)
                        if any(
                            secret in key.upper()
                            for secret in ["PASSWORD", "SECRET", "KEY", "TOKEN"]
                        ):
                            if not value.startswith("${"):
                                result["issues"].append(
                                    f"敏感資訊 {key} 建議使用環境變數"
                                )

        return result

    def validate_kubernetes_configs(self) -> Dict[str, Any]:
        """驗證 Kubernetes 配置"""
        print("☸️  驗證 Kubernetes 配置...")
        results = {"exists": False, "files": []}

        k8s_dir = self.project_root / "k8s"
        if not k8s_dir.exists():
            self.warnings.append("Kubernetes 配置目錄不存在")
            return results

        results["exists"] = True

        # 驗證 YAML 檔案
        for yaml_file in k8s_dir.rglob("*.yaml"):
            file_result = self._validate_k8s_yaml(yaml_file)
            results["files"].append(file_result)

        # 驗證 Kustomization 檔案
        for kustomization_file in k8s_dir.rglob("kustomization.yaml"):
            file_result = self._validate_kustomization(kustomization_file)
            results["files"].append(file_result)

        return results

    def _validate_k8s_yaml(self, file_path: Path) -> Dict[str, Any]:
        """驗證 Kubernetes YAML 檔案"""
        result = {
            "file": str(file_path.relative_to(self.project_root)),
            "valid": True,
            "issues": [],
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                docs = list(yaml.safe_load_all(f))

            for doc in docs:
                if doc is None:
                    continue

                # 檢查必要字段
                if "apiVersion" not in doc:
                    result["issues"].append("缺少 apiVersion 字段")
                if "kind" not in doc:
                    result["issues"].append("缺少 kind 字段")
                if "metadata" not in doc:
                    result["issues"].append("缺少 metadata 字段")

                # 檢查特定資源類型
                if doc.get("kind") == "Deployment":
                    self._validate_k8s_deployment(doc, result)
                elif doc.get("kind") == "Service":
                    self._validate_k8s_service(doc, result)
                elif doc.get("kind") == "Secret":
                    self._validate_k8s_secret(doc, result)

        except yaml.YAMLError as e:
            result["valid"] = False
            result["issues"].append(f"YAML 語法錯誤: {e}")
            self.errors.append(f"{file_path.name}: YAML 語法錯誤")
        except Exception as e:
            result["valid"] = False
            result["issues"].append(f"驗證失敗: {e}")

        return result

    def _validate_k8s_deployment(self, deployment: Dict, result: Dict):
        """驗證 Kubernetes Deployment"""
        spec = deployment.get("spec", {})
        template = spec.get("template", {})
        pod_spec = template.get("spec", {})

        # 檢查副本數
        if "replicas" not in spec:
            result["issues"].append("建議設定副本數")

        # 檢查容器配置
        containers = pod_spec.get("containers", [])
        for container in containers:
            if "resources" not in container:
                result["issues"].append(
                    f"容器 {container.get('name', 'unknown')} 建議設定資源限制"
                )
            if "livenessProbe" not in container:
                result["issues"].append(
                    f"容器 {container.get('name', 'unknown')} 建議設定存活探針"
                )
            if "readinessProbe" not in container:
                result["issues"].append(
                    f"容器 {container.get('name', 'unknown')} 建議設定就緒探針"
                )

    def _validate_k8s_service(self, service: Dict, result: Dict):
        """驗證 Kubernetes Service"""
        spec = service.get("spec", {})

        if "selector" not in spec:
            result["issues"].append("Service 缺少 selector")
        if "ports" not in spec:
            result["issues"].append("Service 缺少 ports 配置")

    def _validate_k8s_secret(self, secret: Dict, result: Dict):
        """驗證 Kubernetes Secret"""
        data = secret.get("data", {})

        if not data:
            result["issues"].append("Secret 沒有資料")

        # 檢查是否包含範例值
        for key, value in data.items():
            if isinstance(value, str) and value in ["example", "changeme", "password"]:
                result["issues"].append(f"Secret {key} 包含範例值，需要替換")

    def _validate_kustomization(self, file_path: Path) -> Dict[str, Any]:
        """驗證 Kustomization 檔案"""
        result = {
            "file": str(file_path.relative_to(self.project_root)),
            "valid": True,
            "issues": [],
        }

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                kustomization = yaml.safe_load(f)

            # 檢查必要字段
            if "resources" not in kustomization:
                result["issues"].append("Kustomization 缺少 resources 字段")

            # 檢查資源檔案是否存在
            resources = kustomization.get("resources", [])
            base_dir = file_path.parent
            for resource in resources:
                resource_path = base_dir / resource
                if not resource_path.exists():
                    result["issues"].append(f"資源檔案不存在: {resource}")

        except yaml.YAMLError as e:
            result["valid"] = False
            result["issues"].append(f"YAML 語法錯誤: {e}")
        except Exception as e:
            result["valid"] = False
            result["issues"].append(f"驗證失敗: {e}")

        return result

    def validate_environment_configs(self) -> Dict[str, Any]:
        """驗證環境配置"""
        print("🌍 驗證環境配置...")
        results = {}

        # 檢查環境變數範例檔案
        env_files = [".env.example", ".env.dev.example"]
        for env_file in env_files:
            file_path = self.project_root / env_file
            if file_path.exists():
                results[env_file] = self._validate_env_file(file_path)
            else:
                self.warnings.append(f"{env_file} 不存在")

        return results

    def _validate_env_file(self, file_path: Path) -> Dict[str, Any]:
        """驗證環境變數檔案"""
        result = {"valid": True, "issues": [], "variables": []}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)

                    # 檢查敏感資訊
                    if any(
                        secret in key.upper()
                        for secret in ["PASSWORD", "SECRET", "KEY", "TOKEN"]
                    ):
                        if value in ["changeme", "password", "secret", "your_key_here"]:
                            result["issues"].append(
                                f"第 {line_num} 行: {key} 包含範例值"
                            )

                    result["variables"].append({"key": key, "line": line_num})

        except Exception as e:
            result["valid"] = False
            result["issues"].append(f"讀取失敗: {e}")

        return result

    def validate_consistency(self) -> Dict[str, Any]:
        """驗證配置一致性"""
        print("🔄 驗證配置一致性...")
        results = {"consistent": True, "issues": []}

        # 檢查服務名稱一致性
        docker_services = self._get_docker_services()
        k8s_services = self._get_k8s_services()

        # 比較服務名稱
        docker_names = set(docker_services.keys())
        k8s_names = set(k8s_services.keys())

        missing_in_k8s = docker_names - k8s_names
        missing_in_docker = k8s_names - docker_names

        if missing_in_k8s:
            results["issues"].append(f"Kubernetes 中缺少服務: {missing_in_k8s}")
            results["consistent"] = False

        if missing_in_docker:
            results["issues"].append(f"Docker Compose 中缺少服務: {missing_in_docker}")
            results["consistent"] = False

        return results

    def _get_docker_services(self) -> Dict[str, Any]:
        """獲取 Docker Compose 服務列表"""
        services = {}

        compose_file = self.project_root / "docker-compose.yml"
        if compose_file.exists():
            try:
                with open(compose_file, "r", encoding="utf-8") as f:
                    compose_data = yaml.safe_load(f)
                services.update(compose_data.get("services", {}))
            except Exception:
                pass

        return services

    def _get_k8s_services(self) -> Dict[str, Any]:
        """獲取 Kubernetes 服務列表"""
        services = {}

        k8s_dir = self.project_root / "k8s"
        if k8s_dir.exists():
            for yaml_file in k8s_dir.rglob("*.yaml"):
                try:
                    with open(yaml_file, "r", encoding="utf-8") as f:
                        docs = list(yaml.safe_load_all(f))

                    for doc in docs:
                        if doc and doc.get("kind") in ["Deployment", "StatefulSet"]:
                            name = doc.get("metadata", {}).get("name")
                            if name:
                                services[name] = doc
                except Exception:
                    pass

        return services


def main():
    """主函數"""
    validator = DeploymentConfigValidator()
    results = validator.validate_all()

    print("\n" + "=" * 60)
    print("部署配置驗證結果")
    print("=" * 60)

    # 輸出結果
    for category, result in results.items():
        if category != "summary":
            print(f"\n📋 {category.upper().replace('_', ' ')} 驗證:")

            if isinstance(result, dict):
                if "exists" in result and not result["exists"]:
                    print("  ❌ 配置不存在")
                    continue

                for key, value in result.items():
                    if isinstance(value, dict) and "valid" in value:
                        status = "✅" if value["valid"] else "❌"
                        print(f"  {status} {key}")

                        if value.get("issues"):
                            for issue in value["issues"]:
                                print(f"    - {issue}")

                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict) and "file" in item:
                                status = "✅" if item.get("valid", True) else "❌"
                                print(f"  {status} {item['file']}")

                                if item.get("issues"):
                                    for issue in item["issues"]:
                                        print(f"    - {issue}")

    # 輸出總結
    summary = results["summary"]
    print(f"\n📊 總結:")
    print(f"  錯誤: {summary['total_errors']}")
    print(f"  警告: {summary['total_warnings']}")

    if summary["errors"]:
        print(f"\n❌ 錯誤:")
        for error in summary["errors"]:
            print(f"  - {error}")

    if summary["warnings"]:
        print(f"\n⚠️  警告:")
        for warning in summary["warnings"]:
            print(f"  - {warning}")

    # 返回適當的退出碼
    return 1 if summary["total_errors"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
