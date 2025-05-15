"""
工作流管理器

此模組實現了工作流管理器，用於管理和執行自動化工作流。
"""

import os
import threading
import time
from typing import Any, Dict, List, Optional

import requests

from src.core.logger import logger

from .config import WORKFLOW_TEMPLATES


class WorkflowManager:
    """
    工作流管理器

    管理和執行自動化工作流。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WorkflowManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, n8n_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        初始化工作流管理器

        Args:
            n8n_url: n8n URL
            api_key: API密鑰
        """
        # 避免重複初始化
        if self._initialized:
            return

        # n8n URL
        self.n8n_url = n8n_url or os.environ.get("N8N_URL", "http://localhost:5678")

        # API密鑰
        self.api_key = api_key or os.environ.get("N8N_API_KEY", "")

        # 工作流緩存
        self.workflows: Dict[str, Dict[str, Any]] = {}

        # 執行緩存
        self.executions: Dict[str, Dict[str, Any]] = {}

        # 監控線程
        self.monitoring_thread = None
        self.running = False

        # 標記為已初始化
        self._initialized = True

        logger.info("工作流管理器已初始化")

    def get_workflows(self) -> List[Dict[str, Any]]:
        """
        獲取所有工作流

        Returns:
            List[Dict[str, Any]]: 工作流列表
        """
        try:
            # 構建請求
            url = f"{self.n8n_url}/rest/workflows"
            headers = {"X-N8N-API-KEY": self.api_key}

            # 發送請求
            response = requests.get(url, headers=headers)

            # 檢查響應
            if response.status_code == 200:
                workflows = response.json()

                # 更新緩存
                for workflow in workflows:
                    self.workflows[workflow["id"]] = workflow

                return workflows
            else:
                logger.error(f"獲取工作流失敗: {response.status_code} {response.text}")
                return []
        except Exception as e:
            logger.error(f"獲取工作流時發生錯誤: {e}")
            return []

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取工作流

        Args:
            workflow_id: 工作流ID

        Returns:
            Optional[Dict[str, Any]]: 工作流
        """
        try:
            # 檢查緩存
            if workflow_id in self.workflows:
                return self.workflows[workflow_id]

            # 構建請求
            url = f"{self.n8n_url}/rest/workflows/{workflow_id}"
            headers = {"X-N8N-API-KEY": self.api_key}

            # 發送請求
            response = requests.get(url, headers=headers)

            # 檢查響應
            if response.status_code == 200:
                workflow = response.json()

                # 更新緩存
                self.workflows[workflow_id] = workflow

                return workflow
            else:
                logger.error(f"獲取工作流失敗: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"獲取工作流時發生錯誤: {e}")
            return None

    def create_workflow(self, workflow: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        創建工作流

        Args:
            workflow: 工作流

        Returns:
            Optional[Dict[str, Any]]: 創建的工作流
        """
        try:
            # 構建請求
            url = f"{self.n8n_url}/rest/workflows"
            headers = {"X-N8N-API-KEY": self.api_key}

            # 發送請求
            response = requests.post(url, headers=headers, json=workflow)

            # 檢查響應
            if response.status_code == 200:
                created_workflow = response.json()

                # 更新緩存
                self.workflows[created_workflow["id"]] = created_workflow

                return created_workflow
            else:
                logger.error(f"創建工作流失敗: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"創建工作流時發生錯誤: {e}")
            return None

    def update_workflow(
        self, workflow_id: str, workflow: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        更新工作流

        Args:
            workflow_id: 工作流ID
            workflow: 工作流

        Returns:
            Optional[Dict[str, Any]]: 更新的工作流
        """
        try:
            # 構建請求
            url = f"{self.n8n_url}/rest/workflows/{workflow_id}"
            headers = {"X-N8N-API-KEY": self.api_key}

            # 發送請求
            response = requests.put(url, headers=headers, json=workflow)

            # 檢查響應
            if response.status_code == 200:
                updated_workflow = response.json()

                # 更新緩存
                self.workflows[workflow_id] = updated_workflow

                return updated_workflow
            else:
                logger.error(f"更新工作流失敗: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"更新工作流時發生錯誤: {e}")
            return None

    def delete_workflow(self, workflow_id: str) -> bool:
        """
        刪除工作流

        Args:
            workflow_id: 工作流ID

        Returns:
            bool: 是否成功刪除
        """
        try:
            # 構建請求
            url = f"{self.n8n_url}/rest/workflows/{workflow_id}"
            headers = {"X-N8N-API-KEY": self.api_key}

            # 發送請求
            response = requests.delete(url, headers=headers)

            # 檢查響應
            if response.status_code == 200:
                # 更新緩存
                if workflow_id in self.workflows:
                    del self.workflows[workflow_id]

                return True
            else:
                logger.error(f"刪除工作流失敗: {response.status_code} {response.text}")
                return False
        except Exception as e:
            logger.error(f"刪除工作流時發生錯誤: {e}")
            return False

    def activate_workflow(self, workflow_id: str) -> bool:
        """
        激活工作流

        Args:
            workflow_id: 工作流ID

        Returns:
            bool: 是否成功激活
        """
        try:
            # 構建請求
            url = f"{self.n8n_url}/rest/workflows/{workflow_id}/activate"
            headers = {"X-N8N-API-KEY": self.api_key}

            # 發送請求
            response = requests.post(url, headers=headers)

            # 檢查響應
            if response.status_code == 200:
                # 更新緩存
                if workflow_id in self.workflows:
                    self.workflows[workflow_id]["active"] = True

                return True
            else:
                logger.error(f"激活工作流失敗: {response.status_code} {response.text}")
                return False
        except Exception as e:
            logger.error(f"激活工作流時發生錯誤: {e}")
            return False

    def deactivate_workflow(self, workflow_id: str) -> bool:
        """
        停用工作流

        Args:
            workflow_id: 工作流ID

        Returns:
            bool: 是否成功停用
        """
        try:
            # 構建請求
            url = f"{self.n8n_url}/rest/workflows/{workflow_id}/deactivate"
            headers = {"X-N8N-API-KEY": self.api_key}

            # 發送請求
            response = requests.post(url, headers=headers)

            # 檢查響應
            if response.status_code == 200:
                # 更新緩存
                if workflow_id in self.workflows:
                    self.workflows[workflow_id]["active"] = False

                return True
            else:
                logger.error(f"停用工作流失敗: {response.status_code} {response.text}")
                return False
        except Exception as e:
            logger.error(f"停用工作流時發生錯誤: {e}")
            return False

    def execute_workflow(
        self, workflow_id: str, data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        執行工作流

        Args:
            workflow_id: 工作流ID
            data: 執行數據

        Returns:
            Optional[Dict[str, Any]]: 執行結果
        """
        try:
            # 構建請求
            url = f"{self.n8n_url}/rest/workflows/{workflow_id}/execute"
            headers = {"X-N8N-API-KEY": self.api_key}

            # 發送請求
            response = requests.post(url, headers=headers, json=data or {})

            # 檢查響應
            if response.status_code == 200:
                execution = response.json()

                # 更新緩存
                self.executions[execution["id"]] = execution

                return execution
            else:
                logger.error(f"執行工作流失敗: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"執行工作流時發生錯誤: {e}")
            return None

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取執行

        Args:
            execution_id: 執行ID

        Returns:
            Optional[Dict[str, Any]]: 執行
        """
        try:
            # 檢查緩存
            if execution_id in self.executions:
                return self.executions[execution_id]

            # 構建請求
            url = f"{self.n8n_url}/rest/executions/{execution_id}"
            headers = {"X-N8N-API-KEY": self.api_key}

            # 發送請求
            response = requests.get(url, headers=headers)

            # 檢查響應
            if response.status_code == 200:
                execution = response.json()

                # 更新緩存
                self.executions[execution_id] = execution

                return execution
            else:
                logger.error(f"獲取執行失敗: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"獲取執行時發生錯誤: {e}")
            return None

    def get_executions(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        獲取執行列表

        Args:
            workflow_id: 工作流ID

        Returns:
            List[Dict[str, Any]]: 執行列表
        """
        try:
            # 構建請求
            url = f"{self.n8n_url}/rest/executions"
            if workflow_id:
                url += f"?workflowId={workflow_id}"
            headers = {"X-N8N-API-KEY": self.api_key}

            # 發送請求
            response = requests.get(url, headers=headers)

            # 檢查響應
            if response.status_code == 200:
                executions = response.json()

                # 更新緩存
                for execution in executions:
                    self.executions[execution["id"]] = execution

                return executions
            else:
                logger.error(
                    f"獲取執行列表失敗: {response.status_code} {response.text}"
                )
                return []
        except Exception as e:
            logger.error(f"獲取執行列表時發生錯誤: {e}")
            return []

    def start_monitoring(self, interval: int = 60) -> bool:
        """
        啟動監控

        Args:
            interval: 監控間隔（秒）

        Returns:
            bool: 是否成功啟動
        """
        if self.running:
            logger.warning("工作流監控已經在運行中")
            return False

        self.running = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, args=(interval,)
        )
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

        logger.info(f"工作流監控已啟動，間隔: {interval}秒")
        return True

    def stop_monitoring(self) -> bool:
        """
        停止監控

        Returns:
            bool: 是否成功停止
        """
        if not self.running:
            logger.warning("工作流監控未運行")
            return False

        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)

        logger.info("工作流監控已停止")
        return True

    def _monitoring_loop(self, interval: int):
        """
        監控循環

        Args:
            interval: 監控間隔（秒）
        """
        while self.running:
            try:
                # 獲取所有工作流
                self.get_workflows()

                # 獲取所有執行
                executions = self.get_executions()

                # 檢查執行狀態
                for execution in executions:
                    if execution["status"] == "failed":
                        logger.error(
                            f"工作流執行失敗: {execution['id']}, 工作流: {execution['workflowId']}"
                        )

                # 等待下一個監控間隔
                time.sleep(interval)
            except Exception as e:
                logger.error(f"工作流監控循環發生錯誤: {e}")
                time.sleep(10)  # 發生錯誤時等待較長時間

    def create_workflow_from_template(
        self, template_name: str, workflow_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        從模板創建工作流

        Args:
            template_name: 模板名稱
            workflow_name: 工作流名稱，如果為None則使用模板名稱

        Returns:
            Optional[Dict[str, Any]]: 創建的工作流
        """
        try:
            # 檢查模板是否存在
            if template_name not in WORKFLOW_TEMPLATES:
                logger.error(f"模板 {template_name} 不存在")
                return None

            # 獲取模板
            template = WORKFLOW_TEMPLATES[template_name]

            # 創建工作流
            workflow = template.copy()

            # 設置工作流名稱
            if workflow_name:
                workflow["name"] = workflow_name

            # 創建工作流
            return self.create_workflow(workflow)
        except Exception as e:
            logger.error(f"從模板創建工作流時發生錯誤: {e}")
            return None

    def setup_default_workflows(self) -> Dict[str, str]:
        """
        設置默認工作流

        Returns:
            Dict[str, str]: 工作流ID字典，鍵為模板名稱，值為工作流ID
        """
        workflow_ids = {}

        # 創建數據獲取工作流
        data_ingestion_workflow = self.create_workflow_from_template("data_ingestion")
        if data_ingestion_workflow:
            workflow_ids["data_ingestion"] = data_ingestion_workflow["id"]
            logger.info(f"已創建數據獲取工作流: {data_ingestion_workflow['id']}")

        # 創建交易訊號生成工作流
        signal_generation_workflow = self.create_workflow_from_template(
            "signal_generation"
        )
        if signal_generation_workflow:
            workflow_ids["signal_generation"] = signal_generation_workflow["id"]
            logger.info(f"已創建交易訊號生成工作流: {signal_generation_workflow['id']}")

        # 創建投資組合再平衡工作流
        from .templates import portfolio_rebalance_workflow

        portfolio_workflow = portfolio_rebalance_workflow()
        portfolio_workflow_created = self.create_workflow(portfolio_workflow)
        if portfolio_workflow_created:
            workflow_ids["portfolio_rebalance"] = portfolio_workflow_created["id"]
            logger.info(
                f"已創建投資組合再平衡工作流: {portfolio_workflow_created['id']}"
            )

        # 創建風險監控工作流
        from .templates import risk_monitoring_workflow

        risk_workflow = risk_monitoring_workflow()
        risk_workflow_created = self.create_workflow(risk_workflow)
        if risk_workflow_created:
            workflow_ids["risk_monitoring"] = risk_workflow_created["id"]
            logger.info(f"已創建風險監控工作流: {risk_workflow_created['id']}")

        # 創建報告生成工作流
        from .templates import reporting_workflow

        report_workflow = reporting_workflow()
        report_workflow_created = self.create_workflow(report_workflow)
        if report_workflow_created:
            workflow_ids["reporting"] = report_workflow_created["id"]
            logger.info(f"已創建報告生成工作流: {report_workflow_created['id']}")

        return workflow_ids


# 創建全局工作流管理器實例
workflow_manager = WorkflowManager()
