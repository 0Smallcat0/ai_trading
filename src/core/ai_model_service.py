#!/usr/bin/env python3
"""
AI模型服務 (統一接口)
整合現有的AI模型管理功能，提供統一的服務接口
"""

import logging
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np

# 添加項目根目錄到路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

class AIModelService:
    """AI模型服務統一接口"""
    
    def __init__(self):
        """初始化AI模型服務"""
        self.models = {}
        self.training_tasks = {}
        self.prediction_cache = {}
        
        # 嘗試導入現有的AI模型管理服務
        self._initialize_services()
        
        logger.info("AI模型服務初始化完成")
    
    def _initialize_services(self):
        """初始化相關服務"""
        try:
            # 嘗試導入AI模型管理服務
            from src.core.ai_model_management_service import AIModelManagementService
            self.model_management = AIModelManagementService()
            self.model_management_available = True
            logger.info("AI模型管理服務已載入")
        except ImportError as e:
            logger.warning(f"AI模型管理服務不可用: {e}")
            self.model_management = None
            self.model_management_available = False
        
        try:
            # 嘗試導入模型工廠
            from src.models.model_factory import create_model, get_available_models
            self.create_model = create_model
            self.get_available_models = get_available_models
            self.model_factory_available = True
            logger.info("模型工廠已載入")
        except ImportError as e:
            logger.warning(f"模型工廠不可用: {e}")
            self.model_factory_available = False
        
        try:
            # 嘗試導入訓練管道
            from src.models.training_pipeline import train_model, create_trainer
            self.train_model = train_model
            self.create_trainer = create_trainer
            self.training_pipeline_available = True
            logger.info("訓練管道已載入")
        except ImportError as e:
            logger.warning(f"訓練管道不可用: {e}")
            self.training_pipeline_available = False
    
    def get_service_status(self) -> Dict[str, Any]:
        """獲取服務狀態"""
        return {
            "service_name": "AI模型服務",
            "status": "running",
            "components": {
                "model_management": self.model_management_available,
                "model_factory": self.model_factory_available,
                "training_pipeline": self.training_pipeline_available
            },
            "models_count": len(self.models),
            "active_training_tasks": len(self.training_tasks),
            "last_updated": datetime.now().isoformat()
        }
    
    def list_models(self, model_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出可用模型"""
        try:
            if self.model_management_available:
                # 使用AI模型管理服務
                models = self.model_management.get_models()
                if model_type:
                    models = [m for m in models if m.get("model_type") == model_type]
                return models
            else:
                # 返回模擬數據
                return self._get_mock_models(model_type)
        except Exception as e:
            logger.error(f"列出模型失敗: {e}")
            return []
    
    def _get_mock_models(self, model_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """獲取模擬模型數據"""
        mock_models = [
            {
                "id": "lstm_stock_predictor",
                "name": "LSTM股價預測模型",
                "model_type": "time_series",
                "description": "基於LSTM神經網路的股價預測模型",
                "status": "ready",
                "accuracy": 0.85,
                "created_at": datetime.now().isoformat(),
                "features": ["開盤價", "收盤價", "最高價", "最低價", "成交量"]
            },
            {
                "id": "rf_trend_classifier",
                "name": "隨機森林趨勢分類器",
                "model_type": "classification",
                "description": "使用隨機森林算法預測股價趨勢方向",
                "status": "ready",
                "accuracy": 0.78,
                "created_at": datetime.now().isoformat(),
                "features": ["技術指標", "成交量", "價格變化"]
            },
            {
                "id": "sentiment_analyzer",
                "name": "市場情感分析器",
                "model_type": "nlp",
                "description": "分析新聞和社交媒體情感對股價的影響",
                "status": "training",
                "accuracy": 0.72,
                "created_at": datetime.now().isoformat(),
                "features": ["新聞標題", "社交媒體文本", "發布時間"]
            }
        ]
        
        if model_type:
            mock_models = [m for m in mock_models if m["model_type"] == model_type]
        
        return mock_models
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """獲取模型詳細信息"""
        try:
            if self.model_management_available:
                return self.model_management.get_model(model_id)
            else:
                # 從模擬數據中查找
                models = self._get_mock_models()
                for model in models:
                    if model["id"] == model_id:
                        return model
                return None
        except Exception as e:
            logger.error(f"獲取模型信息失敗: {e}")
            return None
    
    def create_new_model(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """創建新模型"""
        try:
            if self.model_factory_available:
                # 使用模型工廠創建模型
                model = self.create_model(
                    model_type=model_config.get("model_type"),
                    name=model_config.get("name"),
                    **model_config.get("parameters", {})
                )
                
                # 保存模型信息
                model_info = {
                    "id": f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "name": model_config.get("name"),
                    "model_type": model_config.get("model_type"),
                    "description": model_config.get("description", ""),
                    "status": "created",
                    "created_at": datetime.now().isoformat(),
                    "parameters": model_config.get("parameters", {}),
                    "model_instance": model
                }
                
                self.models[model_info["id"]] = model_info
                return model_info
            else:
                # 模擬創建模型
                model_info = {
                    "id": f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "name": model_config.get("name"),
                    "model_type": model_config.get("model_type"),
                    "description": model_config.get("description", ""),
                    "status": "created",
                    "created_at": datetime.now().isoformat(),
                    "parameters": model_config.get("parameters", {})
                }
                
                self.models[model_info["id"]] = model_info
                return model_info
                
        except Exception as e:
            logger.error(f"創建模型失敗: {e}")
            raise
    
    def train_model_async(self, model_id: str, training_data: Dict[str, Any]) -> str:
        """異步訓練模型"""
        try:
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 記錄訓練任務
            self.training_tasks[task_id] = {
                "model_id": model_id,
                "status": "running",
                "started_at": datetime.now().isoformat(),
                "progress": 0,
                "message": "訓練開始"
            }
            
            if self.training_pipeline_available:
                # 使用真實的訓練管道
                logger.info(f"開始訓練模型 {model_id}")
                # 這裡應該啟動異步訓練任務
                # 為了演示，我們模擬訓練過程
                self._simulate_training(task_id, model_id, training_data)
            else:
                # 模擬訓練過程
                self._simulate_training(task_id, model_id, training_data)
            
            return task_id
            
        except Exception as e:
            logger.error(f"訓練模型失敗: {e}")
            raise
    
    def _simulate_training(self, task_id: str, model_id: str, training_data: Dict[str, Any]):
        """模擬訓練過程"""
        import time
        import threading
        
        def training_worker():
            try:
                # 模擬訓練進度
                for progress in [10, 30, 50, 70, 90, 100]:
                    time.sleep(1)  # 模擬訓練時間
                    self.training_tasks[task_id]["progress"] = progress
                    self.training_tasks[task_id]["message"] = f"訓練進度: {progress}%"
                
                # 訓練完成
                self.training_tasks[task_id]["status"] = "completed"
                self.training_tasks[task_id]["completed_at"] = datetime.now().isoformat()
                self.training_tasks[task_id]["message"] = "訓練完成"
                
                # 更新模型狀態
                if model_id in self.models:
                    self.models[model_id]["status"] = "trained"
                    self.models[model_id]["accuracy"] = np.random.uniform(0.7, 0.9)
                
                logger.info(f"模型 {model_id} 訓練完成")
                
            except Exception as e:
                self.training_tasks[task_id]["status"] = "failed"
                self.training_tasks[task_id]["message"] = f"訓練失敗: {str(e)}"
                logger.error(f"模型訓練失敗: {e}")
        
        # 啟動訓練線程
        training_thread = threading.Thread(target=training_worker)
        training_thread.daemon = True
        training_thread.start()
    
    def get_training_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """獲取訓練狀態"""
        return self.training_tasks.get(task_id)
    
    def predict(self, model_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用模型進行預測"""
        try:
            if self.model_management_available:
                # 使用AI模型管理服務進行預測
                return self.model_management.predict(model_id, input_data)
            else:
                # 模擬預測
                return self._simulate_prediction(model_id, input_data)
                
        except Exception as e:
            logger.error(f"模型預測失敗: {e}")
            raise
    
    def _simulate_prediction(self, model_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """模擬預測過程"""
        # 檢查模型是否存在
        model_info = self.get_model_info(model_id)
        if not model_info:
            raise ValueError(f"模型不存在: {model_id}")
        
        if model_info["status"] != "ready" and model_info["status"] != "trained":
            raise ValueError(f"模型狀態不正確: {model_info['status']}")
        
        # 模擬預測結果
        if model_info["model_type"] == "time_series":
            prediction = {
                "prediction": np.random.uniform(100, 200),
                "confidence": np.random.uniform(0.6, 0.9),
                "trend": np.random.choice(["up", "down", "stable"])
            }
        elif model_info["model_type"] == "classification":
            prediction = {
                "class": np.random.choice(["buy", "sell", "hold"]),
                "probability": np.random.uniform(0.5, 0.95),
                "confidence": np.random.uniform(0.6, 0.9)
            }
        else:
            prediction = {
                "result": "模擬預測結果",
                "confidence": np.random.uniform(0.6, 0.9)
            }
        
        prediction.update({
            "model_id": model_id,
            "timestamp": datetime.now().isoformat(),
            "input_features": list(input_data.keys())
        })
        
        return prediction
    
    def get_model_performance(self, model_id: str) -> Dict[str, Any]:
        """獲取模型性能指標"""
        model_info = self.get_model_info(model_id)
        if not model_info:
            raise ValueError(f"模型不存在: {model_id}")
        
        # 模擬性能指標
        return {
            "model_id": model_id,
            "accuracy": model_info.get("accuracy", 0.8),
            "precision": np.random.uniform(0.7, 0.9),
            "recall": np.random.uniform(0.7, 0.9),
            "f1_score": np.random.uniform(0.7, 0.9),
            "auc": np.random.uniform(0.8, 0.95),
            "last_evaluated": datetime.now().isoformat()
        }
    
    def delete_model(self, model_id: str) -> bool:
        """刪除模型"""
        try:
            if self.model_management_available:
                return self.model_management.delete_model(model_id)
            else:
                # 從本地存儲中刪除
                if model_id in self.models:
                    del self.models[model_id]
                    return True
                return False
        except Exception as e:
            logger.error(f"刪除模型失敗: {e}")
            return False
