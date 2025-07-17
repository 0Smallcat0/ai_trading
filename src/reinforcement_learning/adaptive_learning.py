# -*- coding: utf-8 -*-
"""
自適應學習管理器

此模組提供完整的自適應學習能力，包括：
- 在線學習機制
- 概念漂移檢測
- 動態模型選擇
- 性能監控和調整

主要功能：
- 增量學習和模型更新
- 市場狀態變化檢測
- 自動模型切換
- 性能基準追蹤
- 超參數自適應調整

技術特色：
- 實時適應市場變化
- 智能模型集成
- 統計檢驗方法
- 多層次監控機制
"""

import logging
import numpy as np
import pandas as pd
import torch
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from collections import deque
import time
from scipy import stats
from sklearn.metrics import mean_squared_error
import warnings

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class AdaptiveConfig:
    """自適應學習配置"""
    # 在線學習參數
    online_learning_enabled: bool = True
    update_frequency: int = 1000  # 每N步更新一次
    min_samples_for_update: int = 100
    learning_rate_decay: float = 0.99
    
    # 概念漂移檢測參數
    drift_detection_enabled: bool = True
    drift_window_size: int = 1000
    drift_threshold: float = 0.05
    drift_test_method: str = "ks_test"  # ks_test, t_test, adwin
    
    # 模型選擇參數
    model_selection_enabled: bool = True
    performance_window: int = 500
    model_switch_threshold: float = 0.1
    ensemble_enabled: bool = True
    
    # 性能監控參數
    monitoring_enabled: bool = True
    performance_metrics: List[str] = None
    alert_threshold: float = 0.2


class ConceptDriftDetector:
    """概念漂移檢測器"""
    
    def __init__(self, config: AdaptiveConfig):
        """
        初始化概念漂移檢測器
        
        Args:
            config: 自適應配置
        """
        self.config = config
        self.reference_window = deque(maxlen=config.drift_window_size)
        self.current_window = deque(maxlen=config.drift_window_size)
        self.drift_detected = False
        self.last_drift_time = 0
        
        logger.info("概念漂移檢測器初始化完成")
    
    def add_sample(self, performance_metric: float, is_reference: bool = False):
        """
        添加性能樣本
        
        Args:
            performance_metric: 性能指標
            is_reference: 是否為參考樣本
        """
        if is_reference:
            self.reference_window.append(performance_metric)
        else:
            self.current_window.append(performance_metric)
    
    def detect_drift(self) -> Tuple[bool, float]:
        """
        檢測概念漂移
        
        Returns:
            (是否檢測到漂移, p值)
        """
        if len(self.reference_window) < 50 or len(self.current_window) < 50:
            return False, 1.0
        
        try:
            if self.config.drift_test_method == "ks_test":
                return self._ks_test()
            elif self.config.drift_test_method == "t_test":
                return self._t_test()
            elif self.config.drift_test_method == "adwin":
                return self._adwin_test()
            else:
                logger.warning(f"未知的漂移檢測方法: {self.config.drift_test_method}")
                return False, 1.0
                
        except Exception as e:
            logger.error(f"概念漂移檢測失敗: {e}")
            return False, 1.0
    
    def _ks_test(self) -> Tuple[bool, float]:
        """Kolmogorov-Smirnov檢驗"""
        statistic, p_value = stats.ks_2samp(
            list(self.reference_window), 
            list(self.current_window)
        )
        
        drift_detected = p_value < self.config.drift_threshold
        
        if drift_detected:
            logger.info(f"KS檢驗檢測到概念漂移，p值: {p_value:.4f}")
            self.drift_detected = True
            self.last_drift_time = time.time()
        
        return drift_detected, p_value
    
    def _t_test(self) -> Tuple[bool, float]:
        """t檢驗"""
        statistic, p_value = stats.ttest_ind(
            list(self.reference_window), 
            list(self.current_window)
        )
        
        drift_detected = p_value < self.config.drift_threshold
        
        if drift_detected:
            logger.info(f"t檢驗檢測到概念漂移，p值: {p_value:.4f}")
            self.drift_detected = True
            self.last_drift_time = time.time()
        
        return drift_detected, p_value
    
    def _adwin_test(self) -> Tuple[bool, float]:
        """ADWIN檢驗（簡化實現）"""
        # 簡化的ADWIN實現
        ref_mean = np.mean(self.reference_window)
        cur_mean = np.mean(self.current_window)
        
        # 計算變化幅度
        change_magnitude = abs(cur_mean - ref_mean) / (abs(ref_mean) + 1e-8)
        
        drift_detected = change_magnitude > self.config.drift_threshold
        
        if drift_detected:
            logger.info(f"ADWIN檢測到概念漂移，變化幅度: {change_magnitude:.4f}")
            self.drift_detected = True
            self.last_drift_time = time.time()
        
        return drift_detected, change_magnitude
    
    def reset(self):
        """重置檢測器"""
        self.reference_window.clear()
        self.current_window.clear()
        self.drift_detected = False
        logger.info("概念漂移檢測器已重置")


class OnlineLearner:
    """在線學習器"""
    
    def __init__(self, agent, config: AdaptiveConfig):
        """
        初始化在線學習器
        
        Args:
            agent: RL代理
            config: 自適應配置
        """
        self.agent = agent
        self.config = config
        self.update_counter = 0
        self.experience_buffer = deque(maxlen=config.min_samples_for_update * 10)
        self.performance_history = deque(maxlen=1000)
        
        logger.info("在線學習器初始化完成")
    
    def add_experience(self, experience: Dict[str, Any]):
        """
        添加經驗
        
        Args:
            experience: 經驗字典
        """
        self.experience_buffer.append(experience)
        
        # 檢查是否需要更新
        if len(self.experience_buffer) >= self.config.min_samples_for_update:
            if self.update_counter % self.config.update_frequency == 0:
                self._perform_incremental_update()
        
        self.update_counter += 1
    
    def _perform_incremental_update(self):
        """執行增量更新"""
        try:
            # 準備批次數據
            batch_data = self._prepare_batch_data()
            
            if batch_data is None:
                return
            
            # 調整學習率
            self._adjust_learning_rate()
            
            # 執行更新
            update_stats = self.agent.update(batch_data)
            
            # 記錄性能
            self.performance_history.append(update_stats.get('total_loss', 0.0))
            
            logger.debug(f"增量更新完成，損失: {update_stats.get('total_loss', 0.0):.4f}")
            
        except Exception as e:
            logger.error(f"增量更新失敗: {e}")
    
    def _prepare_batch_data(self) -> Optional[Dict[str, np.ndarray]]:
        """準備批次數據"""
        if len(self.experience_buffer) < self.config.min_samples_for_update:
            return None
        
        try:
            # 從經驗緩衝區採樣
            sample_size = min(self.config.min_samples_for_update, len(self.experience_buffer))
            sampled_experiences = list(self.experience_buffer)[-sample_size:]
            
            # 轉換為批次格式
            batch_data = {}
            for key in ['states', 'actions', 'rewards', 'next_states', 'dones']:
                batch_data[key] = np.array([exp[key] for exp in sampled_experiences])
            
            return batch_data
            
        except Exception as e:
            logger.error(f"準備批次數據失敗: {e}")
            return None
    
    def _adjust_learning_rate(self):
        """調整學習率"""
        try:
            # 獲取當前學習率
            current_lr = self.agent.config.learning_rate
            
            # 應用衰減
            new_lr = current_lr * self.config.learning_rate_decay
            
            # 更新優化器學習率
            if hasattr(self.agent, 'policy_optimizer'):
                for param_group in self.agent.policy_optimizer.param_groups:
                    param_group['lr'] = new_lr
            
            if hasattr(self.agent, 'value_optimizer'):
                for param_group in self.agent.value_optimizer.param_groups:
                    param_group['lr'] = new_lr
            
            # 更新配置
            self.agent.config.learning_rate = new_lr
            
            logger.debug(f"學習率調整為: {new_lr:.6f}")
            
        except Exception as e:
            logger.error(f"學習率調整失敗: {e}")
    
    def get_performance_trend(self) -> str:
        """獲取性能趨勢"""
        if len(self.performance_history) < 10:
            return "insufficient_data"
        
        recent_performance = list(self.performance_history)[-10:]
        early_performance = list(self.performance_history)[-20:-10] if len(self.performance_history) >= 20 else recent_performance
        
        recent_mean = np.mean(recent_performance)
        early_mean = np.mean(early_performance)
        
        if recent_mean < early_mean * 0.9:
            return "improving"
        elif recent_mean > early_mean * 1.1:
            return "degrading"
        else:
            return "stable"


class ModelSelector:
    """模型選擇器"""
    
    def __init__(self, config: AdaptiveConfig):
        """
        初始化模型選擇器
        
        Args:
            config: 自適應配置
        """
        self.config = config
        self.models = {}
        self.model_performance = {}
        self.current_model = None
        self.performance_window = deque(maxlen=config.performance_window)
        
        logger.info("模型選擇器初始化完成")
    
    def register_model(self, model_name: str, model):
        """
        註冊模型
        
        Args:
            model_name: 模型名稱
            model: 模型對象
        """
        self.models[model_name] = model
        self.model_performance[model_name] = deque(maxlen=self.config.performance_window)
        
        if self.current_model is None:
            self.current_model = model_name
        
        logger.info(f"模型已註冊: {model_name}")
    
    def update_performance(self, model_name: str, performance: float):
        """
        更新模型性能
        
        Args:
            model_name: 模型名稱
            performance: 性能指標
        """
        if model_name in self.model_performance:
            self.model_performance[model_name].append(performance)
    
    def select_best_model(self) -> Optional[str]:
        """
        選擇最佳模型
        
        Returns:
            最佳模型名稱
        """
        if not self.models:
            return None
        
        try:
            # 計算各模型的平均性能
            model_scores = {}
            for model_name, performances in self.model_performance.items():
                if len(performances) >= 10:  # 至少需要10個性能樣本
                    model_scores[model_name] = np.mean(performances)
            
            if not model_scores:
                return self.current_model
            
            # 選擇性能最好的模型
            best_model = max(model_scores, key=model_scores.get)
            
            # 檢查是否需要切換模型
            if best_model != self.current_model:
                current_score = model_scores.get(self.current_model, 0)
                best_score = model_scores[best_model]
                
                improvement = (best_score - current_score) / (abs(current_score) + 1e-8)
                
                if improvement > self.config.model_switch_threshold:
                    logger.info(f"切換模型: {self.current_model} -> {best_model}, 性能提升: {improvement:.4f}")
                    self.current_model = best_model
                    return best_model
            
            return self.current_model
            
        except Exception as e:
            logger.error(f"模型選擇失敗: {e}")
            return self.current_model
    
    def get_model_rankings(self) -> Dict[str, float]:
        """獲取模型排名"""
        rankings = {}
        for model_name, performances in self.model_performance.items():
            if len(performances) > 0:
                rankings[model_name] = np.mean(performances)
        
        return dict(sorted(rankings.items(), key=lambda x: x[1], reverse=True))


class PerformanceMonitor:
    """性能監控器"""
    
    def __init__(self, config: AdaptiveConfig):
        """
        初始化性能監控器
        
        Args:
            config: 自適應配置
        """
        self.config = config
        self.metrics = config.performance_metrics or ['reward', 'loss', 'accuracy']
        self.metric_history = {metric: deque(maxlen=1000) for metric in self.metrics}
        self.alerts = []
        
        logger.info("性能監控器初始化完成")
    
    def record_metric(self, metric_name: str, value: float):
        """
        記錄性能指標
        
        Args:
            metric_name: 指標名稱
            value: 指標值
        """
        if metric_name in self.metric_history:
            self.metric_history[metric_name].append(value)
            
            # 檢查是否需要發出警報
            self._check_alert(metric_name, value)
    
    def _check_alert(self, metric_name: str, current_value: float):
        """檢查是否需要發出警報"""
        history = self.metric_history[metric_name]
        
        if len(history) < 10:
            return
        
        # 計算基準值
        baseline = np.mean(list(history)[:-1])
        
        # 計算變化幅度
        change_ratio = abs(current_value - baseline) / (abs(baseline) + 1e-8)
        
        if change_ratio > self.config.alert_threshold:
            alert = {
                'timestamp': time.time(),
                'metric': metric_name,
                'current_value': current_value,
                'baseline': baseline,
                'change_ratio': change_ratio,
                'severity': 'high' if change_ratio > 0.5 else 'medium'
            }
            
            self.alerts.append(alert)
            logger.warning(f"性能警報: {metric_name} 變化 {change_ratio:.2%}")
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """獲取最近的警報"""
        cutoff_time = time.time() - hours * 3600
        return [alert for alert in self.alerts if alert['timestamp'] > cutoff_time]
    
    def get_metric_summary(self) -> Dict[str, Dict[str, float]]:
        """獲取指標摘要"""
        summary = {}
        
        for metric_name, history in self.metric_history.items():
            if len(history) > 0:
                values = list(history)
                summary[metric_name] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values),
                    'recent': values[-1] if values else 0.0,
                    'trend': self._calculate_trend(values)
                }
        
        return summary
    
    def _calculate_trend(self, values: List[float]) -> str:
        """計算趨勢"""
        if len(values) < 5:
            return "insufficient_data"
        
        recent = np.mean(values[-5:])
        earlier = np.mean(values[-10:-5]) if len(values) >= 10 else np.mean(values[:-5])
        
        change_ratio = (recent - earlier) / (abs(earlier) + 1e-8)
        
        if change_ratio > 0.05:
            return "improving"
        elif change_ratio < -0.05:
            return "degrading"
        else:
            return "stable"


class AdaptiveLearningManager:
    """
    自適應學習管理器
    
    統一管理所有自適應學習組件
    """
    
    def __init__(self, agent, config: AdaptiveConfig):
        """
        初始化自適應學習管理器
        
        Args:
            agent: RL代理
            config: 自適應配置
        """
        self.agent = agent
        self.config = config
        
        # 初始化組件
        self.drift_detector = ConceptDriftDetector(config) if config.drift_detection_enabled else None
        self.online_learner = OnlineLearner(agent, config) if config.online_learning_enabled else None
        self.model_selector = ModelSelector(config) if config.model_selection_enabled else None
        self.performance_monitor = PerformanceMonitor(config) if config.monitoring_enabled else None
        
        # 狀態追蹤
        self.adaptation_history = []
        self.last_adaptation_time = 0
        
        logger.info("自適應學習管理器初始化完成")
    
    def step(self, experience: Dict[str, Any], performance_metrics: Dict[str, float]):
        """
        執行一步自適應學習
        
        Args:
            experience: 經驗數據
            performance_metrics: 性能指標
        """
        try:
            # 在線學習
            if self.online_learner:
                self.online_learner.add_experience(experience)
            
            # 概念漂移檢測
            if self.drift_detector and 'reward' in performance_metrics:
                drift_detected, p_value = self.drift_detector.detect_drift()
                if drift_detected:
                    self._handle_concept_drift()
            
            # 性能監控
            if self.performance_monitor:
                for metric_name, value in performance_metrics.items():
                    self.performance_monitor.record_metric(metric_name, value)
            
            # 模型選擇
            if self.model_selector and 'reward' in performance_metrics:
                self.model_selector.update_performance(self.agent.config.name, performance_metrics['reward'])
                best_model = self.model_selector.select_best_model()
                if best_model != self.agent.config.name:
                    self._switch_model(best_model)
            
        except Exception as e:
            logger.error(f"自適應學習步驟失敗: {e}")
    
    def _handle_concept_drift(self):
        """處理概念漂移"""
        try:
            logger.info("檢測到概念漂移，執行適應措施")
            
            # 重置漂移檢測器
            if self.drift_detector:
                self.drift_detector.reset()
            
            # 調整學習參數
            if self.online_learner:
                # 增加學習率以快速適應
                self.agent.config.learning_rate *= 1.5
                logger.info(f"學習率調整為: {self.agent.config.learning_rate:.6f}")
            
            # 記錄適應歷史
            self.adaptation_history.append({
                'timestamp': time.time(),
                'type': 'concept_drift',
                'action': 'parameter_adjustment'
            })
            
            self.last_adaptation_time = time.time()
            
        except Exception as e:
            logger.error(f"處理概念漂移失敗: {e}")
    
    def _switch_model(self, new_model_name: str):
        """切換模型"""
        try:
            logger.info(f"切換到模型: {new_model_name}")
            
            # 這裡實現模型切換邏輯
            # 具體實現取決於模型管理架構
            
            # 記錄適應歷史
            self.adaptation_history.append({
                'timestamp': time.time(),
                'type': 'model_switch',
                'from_model': self.agent.config.name,
                'to_model': new_model_name
            })
            
            self.last_adaptation_time = time.time()
            
        except Exception as e:
            logger.error(f"模型切換失敗: {e}")
    
    def get_adaptation_status(self) -> Dict[str, Any]:
        """獲取適應狀態"""
        status = {
            'last_adaptation_time': self.last_adaptation_time,
            'adaptation_count': len(self.adaptation_history),
            'drift_detected': self.drift_detector.drift_detected if self.drift_detector else False,
            'online_learning_active': self.config.online_learning_enabled,
            'model_selection_active': self.config.model_selection_enabled
        }
        
        # 添加性能監控狀態
        if self.performance_monitor:
            recent_alerts = self.performance_monitor.get_recent_alerts(hours=1)
            status['recent_alerts'] = len(recent_alerts)
            status['metric_summary'] = self.performance_monitor.get_metric_summary()
        
        # 添加模型選擇狀態
        if self.model_selector:
            status['model_rankings'] = self.model_selector.get_model_rankings()
            status['current_model'] = self.model_selector.current_model
        
        return status
    
    def reset(self):
        """重置自適應學習管理器"""
        if self.drift_detector:
            self.drift_detector.reset()
        
        self.adaptation_history.clear()
        self.last_adaptation_time = 0
        
        logger.info("自適應學習管理器已重置")
