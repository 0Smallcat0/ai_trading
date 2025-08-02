"""
AI自學擴充框架 (SelfLearningAgent)

實現用戶行為學習、參數優化和智能建議的AI代理系統。
支援LSTM預測、Optuna優化和強化學習框架。

基於AI股票自動交易系統顯示邏輯改進指南實現。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta
import json
import pickle
from pathlib import Path

# Phase 3 優化：使用AI框架懶加載系統
try:
    from src.ui.utils.ai_framework_lazy_loader import (
        is_optuna_available, is_tensorflow_available,
        load_optuna, load_tensorflow,
        lazy_tensorflow, tensorflow_context
    )
    FRAMEWORK_LAZY_LOADING = True

    # 檢查可用性但不加載框架
    OPTUNA_AVAILABLE = is_optuna_available()
    TF_AVAILABLE = is_tensorflow_available()

except ImportError:
    # 備用：傳統導入方式
    FRAMEWORK_LAZY_LOADING = False

    try:
        import optuna
        OPTUNA_AVAILABLE = True
    except ImportError:
        OPTUNA_AVAILABLE = False

    try:
        import tensorflow as tf
        TF_AVAILABLE = True
    except ImportError:
        TF_AVAILABLE = False

logger = logging.getLogger(__name__)


class SelfLearningAgent:
    """
    AI自學代理
    
    支援用戶行為學習、參數優化和智能預測的AI系統。
    可以學習用戶的操作偏好並提供個性化建議。
    """
    
    def __init__(self, agent_id: str = "default", model_path: str = "models/"):
        """
        初始化AI自學代理
        
        Args:
            agent_id: 代理ID
            model_path: 模型存儲路徑
        """
        self.agent_id = agent_id
        self.model_path = Path(model_path)
        self.model_path.mkdir(parents=True, exist_ok=True)
        
        # 用戶行為記錄
        self.user_interactions = []
        self.preference_model = None
        
        # LSTM預測模型
        self.lstm_model = None
        self.model_trained = False
        
        # Optuna優化器
        self.study = None
        
        # 載入已存在的模型和數據
        self._load_agent_state()
        
        logger.info(f"AI自學代理 {agent_id} 初始化完成")
    
    def record_user_interaction(
        self,
        interaction_type: str,
        parameters: Dict[str, Any],
        result_quality: float = 0.5,
        timestamp: Optional[datetime] = None
    ):
        """
        記錄用戶互動
        
        Args:
            interaction_type: 互動類型 ('chart_view', 'parameter_change', 'zoom', etc.)
            parameters: 互動參數
            result_quality: 結果品質評分 (0-1)
            timestamp: 時間戳
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        interaction = {
            'type': interaction_type,
            'parameters': parameters,
            'quality': result_quality,
            'timestamp': timestamp.isoformat(),
            'agent_id': self.agent_id
        }
        
        self.user_interactions.append(interaction)
        
        # 限制記錄數量，避免內存過載
        if len(self.user_interactions) > 1000:
            self.user_interactions = self.user_interactions[-800:]
        
        logger.debug(f"記錄用戶互動: {interaction_type}")
    
    def learn_from_interactions(self, min_interactions: int = 10) -> bool:
        """
        從用戶互動中學習偏好
        
        Args:
            min_interactions: 最少互動次數
            
        Returns:
            是否成功學習
        """
        if len(self.user_interactions) < min_interactions:
            logger.warning(f"互動記錄不足 ({len(self.user_interactions)} < {min_interactions})")
            return False
        
        try:
            # 分析用戶偏好模式
            preferences = self._analyze_user_preferences()
            
            # 更新偏好模型
            self.preference_model = preferences
            
            # 保存學習結果
            self._save_agent_state()
            
            logger.info(f"成功從 {len(self.user_interactions)} 個互動中學習用戶偏好")
            return True
            
        except Exception as e:
            logger.error(f"學習用戶偏好時發生錯誤: {e}")
            return False
    
    def predict_optimal_parameters(
        self,
        stock_id: str,
        base_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        預測最佳參數
        
        Args:
            stock_id: 股票代號
            base_parameters: 基礎參數
            
        Returns:
            優化後的參數
        """
        if self.preference_model is None:
            logger.warning("偏好模型未訓練，返回基礎參數")
            return base_parameters
        
        try:
            # 基於用戶偏好調整參數
            optimized_params = base_parameters.copy()
            
            # 應用學習到的偏好
            if 'preferred_multipliers' in self.preference_model:
                optimized_params['multipliers'] = self.preference_model['preferred_multipliers']
            
            if 'preferred_indicators' in self.preference_model:
                optimized_params['indicators'] = self.preference_model['preferred_indicators']
            
            if 'preferred_date_range' in self.preference_model:
                optimized_params['date_range_days'] = self.preference_model['preferred_date_range']
            
            logger.info(f"為 {stock_id} 預測最佳參數")
            return optimized_params
            
        except Exception as e:
            logger.error(f"預測最佳參數時發生錯誤: {e}")
            return base_parameters
    
    def optimize_with_optuna(
        self,
        objective_function: callable,
        n_trials: int = 50,
        study_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用Optuna進行參數優化
        
        Args:
            objective_function: 目標函數
            n_trials: 試驗次數
            study_name: 研究名稱
            
        Returns:
            最佳參數
        """
        if not OPTUNA_AVAILABLE:
            logger.error("Optuna未安裝，無法進行參數優化")
            return {}

        try:
            # Phase 3 優化：懶加載Optuna
            if FRAMEWORK_LAZY_LOADING:
                optuna = load_optuna()
                if optuna is None:
                    logger.error("Optuna懶加載失敗，無法進行參數優化")
                    return {}
            else:
                import optuna

            if study_name is None:
                study_name = f"{self.agent_id}_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 創建或載入研究
            self.study = optuna.create_study(
                direction='maximize',
                study_name=study_name,
                storage=f'sqlite:///{self.model_path}/optuna.db',
                load_if_exists=True
            )
            
            # 執行優化
            self.study.optimize(objective_function, n_trials=n_trials)
            
            best_params = self.study.best_params
            best_value = self.study.best_value
            
            logger.info(f"Optuna優化完成，最佳值: {best_value:.4f}")
            logger.info(f"最佳參數: {best_params}")
            
            return best_params
            
        except Exception as e:
            logger.error(f"Optuna優化時發生錯誤: {e}")
            return {}
    
    def train_lstm_predictor(
        self,
        training_data: pd.DataFrame,
        target_column: str = 'close',
        sequence_length: int = 60,
        epochs: int = 50
    ) -> bool:
        """
        訓練LSTM預測模型
        
        Args:
            training_data: 訓練數據
            target_column: 目標列
            sequence_length: 序列長度
            epochs: 訓練輪數
            
        Returns:
            是否訓練成功
        """
        if not TF_AVAILABLE:
            logger.info("TensorFlow未安裝，LSTM預測功能不可用")
            return False

        try:
            # Phase 3 優化：懶加載TensorFlow
            if FRAMEWORK_LAZY_LOADING:
                tf = load_tensorflow()
                if tf is None:
                    logger.error("TensorFlow懶加載失敗，LSTM預測功能不可用")
                    return False
            else:
                import tensorflow as tf

            # 準備訓練數據
            X, y = self._prepare_lstm_data(training_data, target_column, sequence_length)
            
            if len(X) == 0:
                logger.error("訓練數據不足")
                return False
            
            # 創建LSTM模型
            self.lstm_model = tf.keras.Sequential([
                tf.keras.layers.LSTM(50, return_sequences=True, input_shape=(sequence_length, 1)),
                tf.keras.layers.Dropout(0.2),
                tf.keras.layers.LSTM(50, return_sequences=False),
                tf.keras.layers.Dropout(0.2),
                tf.keras.layers.Dense(25),
                tf.keras.layers.Dense(1)
            ])
            
            # 編譯模型
            self.lstm_model.compile(
                optimizer='adam',
                loss='mean_squared_error',
                metrics=['mae']
            )
            
            # 訓練模型
            history = self.lstm_model.fit(
                X, y,
                batch_size=32,
                epochs=epochs,
                validation_split=0.2,
                verbose=0
            )
            
            self.model_trained = True
            
            # 保存模型
            model_file = self.model_path / f"{self.agent_id}_lstm_model.h5"
            self.lstm_model.save(str(model_file))
            
            logger.info(f"LSTM模型訓練完成，最終損失: {history.history['loss'][-1]:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"LSTM模型訓練時發生錯誤: {e}")
            return False
    
    def predict_with_lstm(
        self,
        input_data: pd.DataFrame,
        target_column: str = 'close',
        sequence_length: int = 60,
        prediction_days: int = 5
    ) -> Optional[np.ndarray]:
        """
        使用LSTM模型進行預測
        
        Args:
            input_data: 輸入數據
            target_column: 目標列
            sequence_length: 序列長度
            prediction_days: 預測天數
            
        Returns:
            預測結果
        """
        if not self.model_trained or self.lstm_model is None:
            logger.warning("LSTM模型未訓練")
            return None
        
        try:
            # 準備預測數據
            if len(input_data) < sequence_length:
                logger.error("輸入數據長度不足")
                return None
            
            # 標準化數據
            data = input_data[target_column].values.reshape(-1, 1)
            
            # 取最後sequence_length個數據點
            last_sequence = data[-sequence_length:].reshape(1, sequence_length, 1)
            
            # 進行預測
            predictions = []
            current_sequence = last_sequence.copy()
            
            for _ in range(prediction_days):
                pred = self.lstm_model.predict(current_sequence, verbose=0)
                predictions.append(pred[0, 0])
                
                # 更新序列
                current_sequence = np.roll(current_sequence, -1, axis=1)
                current_sequence[0, -1, 0] = pred[0, 0]
            
            logger.info(f"LSTM預測完成，預測 {prediction_days} 天")
            return np.array(predictions)
            
        except Exception as e:
            logger.error(f"LSTM預測時發生錯誤: {e}")
            return None

    def predict_lstm(
        self,
        input_data: pd.DataFrame,
        prediction_days: int = 5,
        target_column: str = 'close'
    ) -> Optional[np.ndarray]:
        """
        簡化版LSTM預測函數（為了向後兼容）

        Args:
            input_data: 輸入數據
            prediction_days: 預測天數
            target_column: 目標列

        Returns:
            預測結果
        """
        return self.predict_with_lstm(
            input_data=input_data,
            target_column=target_column,
            prediction_days=prediction_days
        )
    
    def _analyze_user_preferences(self) -> Dict[str, Any]:
        """分析用戶偏好"""
        preferences = {}
        
        # 分析參數使用頻率
        multiplier_usage = {}
        indicator_usage = {}
        date_range_usage = {}
        
        for interaction in self.user_interactions:
            params = interaction.get('parameters', {})
            quality = interaction.get('quality', 0.5)
            
            # 統計倍數使用
            if 'multipliers' in params:
                for mult in params['multipliers']:
                    if mult not in multiplier_usage:
                        multiplier_usage[mult] = []
                    multiplier_usage[mult].append(quality)
            
            # 統計指標使用
            if 'indicators' in params:
                for ind in params['indicators']:
                    if ind not in indicator_usage:
                        indicator_usage[ind] = []
                    indicator_usage[ind].append(quality)
            
            # 統計日期範圍使用
            if 'date_range_days' in params:
                days = params['date_range_days']
                if days not in date_range_usage:
                    date_range_usage[days] = []
                date_range_usage[days].append(quality)
        
        # 計算偏好權重
        if multiplier_usage:
            best_multipliers = sorted(
                multiplier_usage.items(),
                key=lambda x: np.mean(x[1]),
                reverse=True
            )
            preferences['preferred_multipliers'] = [m[0] for m in best_multipliers[:3]]
        
        if indicator_usage:
            best_indicators = sorted(
                indicator_usage.items(),
                key=lambda x: np.mean(x[1]),
                reverse=True
            )
            preferences['preferred_indicators'] = [i[0] for i in best_indicators[:5]]
        
        if date_range_usage:
            best_date_range = max(date_range_usage.items(), key=lambda x: np.mean(x[1]))
            preferences['preferred_date_range'] = best_date_range[0]
        
        return preferences
    
    def _prepare_lstm_data(
        self,
        data: pd.DataFrame,
        target_column: str,
        sequence_length: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """準備LSTM訓練數據"""
        values = data[target_column].values
        
        X, y = [], []
        for i in range(sequence_length, len(values)):
            X.append(values[i-sequence_length:i])
            y.append(values[i])
        
        return np.array(X).reshape(-1, sequence_length, 1), np.array(y)
    
    def _save_agent_state(self):
        """保存代理狀態"""
        try:
            state_file = self.model_path / f"{self.agent_id}_state.pkl"
            
            state = {
                'user_interactions': self.user_interactions,
                'preference_model': self.preference_model,
                'model_trained': self.model_trained
            }
            
            with open(state_file, 'wb') as f:
                pickle.dump(state, f)
                
            logger.debug(f"代理狀態已保存到 {state_file}")
            
        except Exception as e:
            logger.error(f"保存代理狀態時發生錯誤: {e}")
    
    def _load_agent_state(self):
        """載入代理狀態"""
        try:
            state_file = self.model_path / f"{self.agent_id}_state.pkl"
            
            if state_file.exists():
                with open(state_file, 'rb') as f:
                    state = pickle.load(f)
                
                self.user_interactions = state.get('user_interactions', [])
                self.preference_model = state.get('preference_model', None)
                self.model_trained = state.get('model_trained', False)
                
                # 嘗試載入LSTM模型
                if self.model_trained and TF_AVAILABLE:
                    model_file = self.model_path / f"{self.agent_id}_lstm_model.h5"
                    if model_file.exists():
                        self.lstm_model = tf.keras.models.load_model(str(model_file))
                
                logger.info(f"成功載入代理狀態，包含 {len(self.user_interactions)} 個互動記錄")
            
        except Exception as e:
            logger.error(f"載入代理狀態時發生錯誤: {e}")
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """
        獲取學習統計資訊
        
        Returns:
            學習統計資訊
        """
        return {
            'agent_id': self.agent_id,
            'total_interactions': len(self.user_interactions),
            'model_trained': self.model_trained,
            'has_preferences': self.preference_model is not None,
            'optuna_available': OPTUNA_AVAILABLE,
            'tensorflow_available': TF_AVAILABLE,
            'last_interaction': self.user_interactions[-1]['timestamp'] if self.user_interactions else None
        }
