"""
模型上下文協議(MCP)客戶端

此模組實現了模型上下文協議(Model Context Protocol)客戶端，
用於標準化模型介面和數據交換。
"""

import os
import json
import requests
import logging
import threading
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from src.core.logger import logger


class MCPClient:
    """
    模型上下文協議(MCP)客戶端
    
    提供與模型上下文協議(Model Context Protocol)的整合功能，
    用於標準化模型介面和數據交換。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MCPClient, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        初始化MCP客戶端
        
        Args:
            base_url: MCP服務基礎URL
            api_key: API密鑰
        """
        # 避免重複初始化
        if self._initialized:
            return
        
        # MCP服務基礎URL
        self.base_url = base_url or os.environ.get("MCP_BASE_URL", "http://localhost:8080")
        
        # API密鑰
        self.api_key = api_key or os.environ.get("MCP_API_KEY", "")
        
        # 模型緩存
        self.models: Dict[str, Dict[str, Any]] = {}
        
        # 標記為已初始化
        self._initialized = True
        
        logger.info("MCP客戶端已初始化")
    
    def get_models(self) -> List[Dict[str, Any]]:
        """
        獲取所有可用模型
        
        Returns:
            List[Dict[str, Any]]: 模型列表
        """
        try:
            # 構建請求
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            # 發送請求
            response = requests.get(url, headers=headers)
            
            # 檢查響應
            if response.status_code == 200:
                models = response.json()
                
                # 更新緩存
                for model in models:
                    self.models[model["id"]] = model
                
                return models
            else:
                logger.error(f"獲取模型失敗: {response.status_code} {response.text}")
                return []
        except Exception as e:
            logger.error(f"獲取模型時發生錯誤: {e}")
            return []
    
    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取模型
        
        Args:
            model_id: 模型ID
            
        Returns:
            Optional[Dict[str, Any]]: 模型
        """
        try:
            # 檢查緩存
            if model_id in self.models:
                return self.models[model_id]
            
            # 構建請求
            url = f"{self.base_url}/models/{model_id}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            # 發送請求
            response = requests.get(url, headers=headers)
            
            # 檢查響應
            if response.status_code == 200:
                model = response.json()
                
                # 更新緩存
                self.models[model_id] = model
                
                return model
            else:
                logger.error(f"獲取模型失敗: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"獲取模型時發生錯誤: {e}")
            return None
    
    def predict(self, model_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        使用模型進行預測
        
        Args:
            model_id: 模型ID
            data: 預測數據
            
        Returns:
            Optional[Dict[str, Any]]: 預測結果
        """
        try:
            # 構建請求
            url = f"{self.base_url}/models/{model_id}/predict"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 發送請求
            response = requests.post(url, headers=headers, json=data)
            
            # 檢查響應
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"預測失敗: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"預測時發生錯誤: {e}")
            return None
    
    def batch_predict(self, model_id: str, data_list: List[Dict[str, Any]]) -> List[Optional[Dict[str, Any]]]:
        """
        使用模型進行批量預測
        
        Args:
            model_id: 模型ID
            data_list: 預測數據列表
            
        Returns:
            List[Optional[Dict[str, Any]]]: 預測結果列表
        """
        try:
            # 構建請求
            url = f"{self.base_url}/models/{model_id}/batch-predict"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 發送請求
            response = requests.post(url, headers=headers, json={"instances": data_list})
            
            # 檢查響應
            if response.status_code == 200:
                return response.json().get("predictions", [])
            else:
                logger.error(f"批量預測失敗: {response.status_code} {response.text}")
                return [None] * len(data_list)
        except Exception as e:
            logger.error(f"批量預測時發生錯誤: {e}")
            return [None] * len(data_list)
    
    def get_model_metadata(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取模型元數據
        
        Args:
            model_id: 模型ID
            
        Returns:
            Optional[Dict[str, Any]]: 模型元數據
        """
        try:
            # 構建請求
            url = f"{self.base_url}/models/{model_id}/metadata"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            # 發送請求
            response = requests.get(url, headers=headers)
            
            # 檢查響應
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"獲取模型元數據失敗: {response.status_code} {response.text}")
                return None
        except Exception as e:
            logger.error(f"獲取模型元數據時發生錯誤: {e}")
            return None
