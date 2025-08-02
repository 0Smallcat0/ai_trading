# -*- coding: utf-8 -*-
"""
動態權重調整器模組

此模組實現基於績效的動態權重調整機制，使用機器學習算法
優化代理權重，提升整體協作效果。

核心功能：
- 績效追蹤和評估
- 動態權重調整算法
- 機器學習權重優化
- 風險調整績效評估
- 權重衰減和正則化

調整策略：
- 績效基礎調整（Performance Based）
- 風險調整收益（Risk Adjusted Return）
- 夏普比率優化（Sharpe Ratio）
- 最大回撤控制（Max Drawdown）
- 機器學習優化（ML Optimization）
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict, deque
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
import warnings

# 設定日誌
logger = logging.getLogger(__name__)

# 忽略sklearn警告
warnings.filterwarnings('ignore', category=UserWarning)


class WeightAdjustmentMethod(Enum):
    """權重調整方法枚舉"""
    PERFORMANCE_BASED = "performance_based"       # 績效基礎
    RISK_ADJUSTED = "risk_adjusted"              # 風險調整
    SHARPE_RATIO = "sharpe_ratio"                # 夏普比率
    KELLY_CRITERION = "kelly_criterion"          # 凱利公式
    MACHINE_LEARNING = "machine_learning"        # 機器學習
    ENSEMBLE = "ensemble"                        # 集成方法


class PerformanceMetric(Enum):
    """績效指標枚舉"""
    TOTAL_RETURN = "total_return"                # 總收益率
    SHARPE_RATIO = "sharpe_ratio"               # 夏普比率
    SORTINO_RATIO = "sortino_ratio"             # 索提諾比率
    MAX_DRAWDOWN = "max_drawdown"               # 最大回撤
    WIN_RATE = "win_rate"                       # 勝率
    PROFIT_FACTOR = "profit_factor"             # 盈利因子
    CALMAR_RATIO = "calmar_ratio"               # 卡瑪比率


@dataclass
class PerformanceRecord:
    """績效記錄"""
    agent_id: str
    timestamp: datetime
    decision_return: float                       # 決策收益率
    cumulative_return: float                     # 累積收益率
    volatility: float                           # 波動率
    sharpe_ratio: float                         # 夏普比率
    max_drawdown: float                         # 最大回撤
    win_rate: float                             # 勝率
    confidence: float                           # 決策信心度
    position_size: float                        # 倉位大小
    market_condition: str                       # 市場條件
    metadata: Dict[str, Any]                    # 額外信息


@dataclass
class WeightAdjustment:
    """權重調整結果"""
    agent_id: str
    old_weight: float
    new_weight: float
    adjustment_ratio: float
    adjustment_reason: str
    performance_score: float
    risk_score: float
    confidence_score: float
    timestamp: datetime
    metadata: Dict[str, Any]


class DynamicWeightAdjuster:
    """
    動態權重調整器 - 基於績效優化代理權重的核心組件。
    
    使用多種績效指標和機器學習算法，動態調整各代理的權重，
    以提升整體投資組合的風險調整收益。
    
    Attributes:
        adjustment_method (WeightAdjustmentMethod): 權重調整方法
        performance_window (int): 績效評估窗口
        min_weight (float): 最小權重
        max_weight (float): 最大權重
        weight_decay (float): 權重衰減因子
        learning_rate (float): 學習率
        risk_free_rate (float): 無風險利率
        rebalance_frequency (int): 再平衡頻率
    """
    
    def __init__(
        self,
        adjustment_method: WeightAdjustmentMethod = WeightAdjustmentMethod.ENSEMBLE,
        performance_window: int = 30,
        min_weight: float = 0.05,
        max_weight: float = 0.4,
        weight_decay: float = 0.95,
        learning_rate: float = 0.01,
        risk_free_rate: float = 0.02,
        rebalance_frequency: int = 5
    ) -> None:
        """
        初始化動態權重調整器。
        
        Args:
            adjustment_method: 權重調整方法
            performance_window: 績效評估窗口（天數）
            min_weight: 最小權重
            max_weight: 最大權重
            weight_decay: 權重衰減因子
            learning_rate: 學習率
            risk_free_rate: 年化無風險利率
            rebalance_frequency: 再平衡頻率（天數）
        """
        self.adjustment_method = adjustment_method
        self.performance_window = performance_window
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.weight_decay = weight_decay
        self.learning_rate = learning_rate
        self.risk_free_rate = risk_free_rate
        self.rebalance_frequency = rebalance_frequency
        
        # 權重和績效追蹤
        self.current_weights: Dict[str, float] = {}
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=performance_window * 2))
        self.adjustment_history: List[WeightAdjustment] = []
        
        # 機器學習模型
        self.ml_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.feature_scaler = StandardScaler()
        self.model_trained = False
        
        # 績效統計
        self.performance_stats = {
            'total_adjustments': 0,
            'positive_adjustments': 0,
            'negative_adjustments': 0,
            'average_improvement': 0.0,
            'best_performer': None,
            'worst_performer': None
        }
        
        # 最後再平衡時間
        self.last_rebalance = datetime.now()
        
        logger.info(f"初始化動態權重調整器: {adjustment_method.value}")
    
    def update_performance(
        self,
        agent_id: str,
        decision_return: float,
        market_data: Optional[Dict[str, Any]] = None,
        decision_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        更新代理績效記錄。
        
        Args:
            agent_id: 代理ID
            decision_return: 決策收益率
            market_data: 市場數據
            decision_metadata: 決策元數據
        """
        try:
            # 計算績效指標
            performance_metrics = self._calculate_performance_metrics(
                agent_id, decision_return, market_data
            )
            
            # 創建績效記錄
            performance_record = PerformanceRecord(
                agent_id=agent_id,
                timestamp=datetime.now(),
                decision_return=decision_return,
                cumulative_return=performance_metrics['cumulative_return'],
                volatility=performance_metrics['volatility'],
                sharpe_ratio=performance_metrics['sharpe_ratio'],
                max_drawdown=performance_metrics['max_drawdown'],
                win_rate=performance_metrics['win_rate'],
                confidence=decision_metadata.get('confidence', 0.5) if decision_metadata else 0.5,
                position_size=decision_metadata.get('position_size', 0.0) if decision_metadata else 0.0,
                market_condition=self._identify_market_condition(market_data),
                metadata=decision_metadata or {}
            )
            
            # 添加到歷史記錄
            self.performance_history[agent_id].append(performance_record)
            
            # 檢查是否需要調整權重
            if self._should_rebalance():
                self.adjust_weights()
                
        except Exception as e:
            logger.error(f"更新代理 {agent_id} 績效失敗: {e}")
    
    def adjust_weights(self, force_rebalance: bool = False) -> Dict[str, WeightAdjustment]:
        """
        調整代理權重。
        
        Args:
            force_rebalance: 是否強制再平衡
            
        Returns:
            Dict[str, WeightAdjustment]: 權重調整結果
        """
        try:
            if not force_rebalance and not self._should_rebalance():
                return {}
            
            # 獲取所有代理ID
            agent_ids = list(self.performance_history.keys())
            if not agent_ids:
                return {}
            
            # 根據調整方法計算新權重
            if self.adjustment_method == WeightAdjustmentMethod.PERFORMANCE_BASED:
                new_weights = self._performance_based_adjustment(agent_ids)
            elif self.adjustment_method == WeightAdjustmentMethod.RISK_ADJUSTED:
                new_weights = self._risk_adjusted_adjustment(agent_ids)
            elif self.adjustment_method == WeightAdjustmentMethod.SHARPE_RATIO:
                new_weights = self._sharpe_ratio_adjustment(agent_ids)
            elif self.adjustment_method == WeightAdjustmentMethod.KELLY_CRITERION:
                new_weights = self._kelly_criterion_adjustment(agent_ids)
            elif self.adjustment_method == WeightAdjustmentMethod.MACHINE_LEARNING:
                new_weights = self._machine_learning_adjustment(agent_ids)
            else:  # ENSEMBLE
                new_weights = self._ensemble_adjustment(agent_ids)
            
            # 應用權重約束
            new_weights = self._apply_weight_constraints(new_weights)
            
            # 生成調整記錄
            adjustments = self._create_adjustment_records(new_weights)
            
            # 更新當前權重
            self.current_weights.update(new_weights)
            self.adjustment_history.extend(adjustments.values())
            
            # 更新統計
            self._update_adjustment_stats(adjustments)
            
            # 更新再平衡時間
            self.last_rebalance = datetime.now()
            
            logger.info(f"權重調整完成，調整了 {len(adjustments)} 個代理")
            return adjustments
            
        except Exception as e:
            logger.error(f"權重調整失敗: {e}")
            return {}
    
    def _calculate_performance_metrics(
        self,
        agent_id: str,
        decision_return: float,
        market_data: Optional[Dict[str, Any]]
    ) -> Dict[str, float]:
        """計算績效指標"""
        
        # 獲取歷史績效
        history = list(self.performance_history[agent_id])
        
        if not history:
            # 首次記錄
            return {
                'cumulative_return': decision_return,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 1.0 if decision_return > 0 else 0.0
            }
        
        # 計算累積收益率
        returns = [record.decision_return for record in history] + [decision_return]
        cumulative_return = np.prod([1 + r for r in returns]) - 1
        
        # 計算波動率
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0.0
        
        # 計算夏普比率
        excess_returns = [r - self.risk_free_rate/252 for r in returns]
        sharpe_ratio = (
            np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
            if len(excess_returns) > 1 and np.std(excess_returns) > 0 else 0.0
        )
        
        # 計算最大回撤
        cumulative_returns = np.cumprod([1 + r for r in returns])
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0
        
        # 計算勝率
        positive_returns = sum(1 for r in returns if r > 0)
        win_rate = positive_returns / len(returns) if returns else 0.0
        
        return {
            'cumulative_return': cumulative_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate
        }

    def _identify_market_condition(self, market_data: Optional[Dict[str, Any]]) -> str:
        """識別市場條件"""
        if not market_data:
            return "unknown"

        # 簡化的市場條件識別
        volatility = market_data.get('volatility', 0.2)
        trend = market_data.get('trend', 0.0)

        if volatility > 0.3:
            return "high_volatility"
        elif volatility < 0.1:
            return "low_volatility"
        elif trend > 0.05:
            return "bull_market"
        elif trend < -0.05:
            return "bear_market"
        else:
            return "sideways"

    def _should_rebalance(self) -> bool:
        """檢查是否應該再平衡"""
        days_since_rebalance = (datetime.now() - self.last_rebalance).days
        return days_since_rebalance >= self.rebalance_frequency

    def _performance_based_adjustment(self, agent_ids: List[str]) -> Dict[str, float]:
        """基於績效的權重調整"""
        performance_scores = {}

        for agent_id in agent_ids:
            history = list(self.performance_history[agent_id])
            if not history:
                performance_scores[agent_id] = 0.5  # 默認分數
                continue

            # 計算最近績效
            recent_records = history[-self.performance_window:]

            # 綜合績效評分
            returns = [record.decision_return for record in recent_records]
            avg_return = np.mean(returns) if returns else 0.0
            win_rate = sum(1 for r in returns if r > 0) / len(returns) if returns else 0.0

            # 績效分數 = 平均收益率 * 勝率
            performance_scores[agent_id] = avg_return * win_rate

        # 轉換為權重
        return self._scores_to_weights(performance_scores)

    def _risk_adjusted_adjustment(self, agent_ids: List[str]) -> Dict[str, float]:
        """風險調整權重調整"""
        risk_adjusted_scores = {}

        for agent_id in agent_ids:
            history = list(self.performance_history[agent_id])
            if not history:
                risk_adjusted_scores[agent_id] = 0.5
                continue

            recent_records = history[-self.performance_window:]

            # 計算風險調整收益
            returns = [record.decision_return for record in recent_records]
            if len(returns) < 2:
                risk_adjusted_scores[agent_id] = 0.5
                continue

            avg_return = np.mean(returns)
            volatility = np.std(returns)

            # 風險調整分數 = 收益率 / 波動率
            if volatility > 0:
                risk_adjusted_scores[agent_id] = avg_return / volatility
            else:
                risk_adjusted_scores[agent_id] = avg_return

        return self._scores_to_weights(risk_adjusted_scores)

    def _sharpe_ratio_adjustment(self, agent_ids: List[str]) -> Dict[str, float]:
        """夏普比率權重調整"""
        sharpe_scores = {}

        for agent_id in agent_ids:
            history = list(self.performance_history[agent_id])
            if not history:
                sharpe_scores[agent_id] = 0.0
                continue

            recent_records = history[-self.performance_window:]

            # 計算夏普比率
            returns = [record.decision_return for record in recent_records]
            if len(returns) < 2:
                sharpe_scores[agent_id] = 0.0
                continue

            excess_returns = [r - self.risk_free_rate/252 for r in returns]
            avg_excess_return = np.mean(excess_returns)
            volatility = np.std(excess_returns)

            if volatility > 0:
                sharpe_scores[agent_id] = avg_excess_return / volatility
            else:
                sharpe_scores[agent_id] = 0.0

        return self._scores_to_weights(sharpe_scores)

    def _kelly_criterion_adjustment(self, agent_ids: List[str]) -> Dict[str, float]:
        """凱利公式權重調整"""
        kelly_weights = {}

        for agent_id in agent_ids:
            history = list(self.performance_history[agent_id])
            if not history:
                kelly_weights[agent_id] = self.min_weight
                continue

            recent_records = history[-self.performance_window:]
            returns = [record.decision_return for record in recent_records]

            if len(returns) < 5:  # 需要足夠的樣本
                kelly_weights[agent_id] = self.min_weight
                continue

            # 計算凱利比例
            positive_returns = [r for r in returns if r > 0]
            negative_returns = [r for r in returns if r < 0]

            if not positive_returns or not negative_returns:
                kelly_weights[agent_id] = self.min_weight
                continue

            win_prob = len(positive_returns) / len(returns)
            avg_win = np.mean(positive_returns)
            avg_loss = abs(np.mean(negative_returns))

            if avg_loss > 0:
                # Kelly公式: f = (bp - q) / b
                # 其中 b = avg_win/avg_loss, p = win_prob, q = 1-win_prob
                b = avg_win / avg_loss
                kelly_fraction = (b * win_prob - (1 - win_prob)) / b
                kelly_weights[agent_id] = max(self.min_weight, min(self.max_weight, kelly_fraction))
            else:
                kelly_weights[agent_id] = self.min_weight

        # 標準化權重
        total_weight = sum(kelly_weights.values())
        if total_weight > 0:
            kelly_weights = {k: v/total_weight for k, v in kelly_weights.items()}

        return kelly_weights

    def _machine_learning_adjustment(self, agent_ids: List[str]) -> Dict[str, float]:
        """機器學習權重調整"""
        try:
            # 準備訓練數據
            features, targets = self._prepare_ml_data(agent_ids)

            if len(features) < 10:  # 需要足夠的訓練數據
                logger.warning("機器學習訓練數據不足，使用績效基礎調整")
                return self._performance_based_adjustment(agent_ids)

            # 訓練模型
            if not self.model_trained or len(features) % 20 == 0:  # 定期重新訓練
                X_scaled = self.feature_scaler.fit_transform(features)
                self.ml_model.fit(X_scaled, targets)
                self.model_trained = True

            # 預測權重
            ml_weights = {}
            for agent_id in agent_ids:
                agent_features = self._extract_agent_features(agent_id)
                if agent_features is not None:
                    X_scaled = self.feature_scaler.transform([agent_features])
                    predicted_performance = self.ml_model.predict(X_scaled)[0]
                    ml_weights[agent_id] = max(0.0, predicted_performance)
                else:
                    ml_weights[agent_id] = 0.5

            return self._scores_to_weights(ml_weights)

        except Exception as e:
            logger.error(f"機器學習權重調整失敗: {e}")
            return self._performance_based_adjustment(agent_ids)

    def _ensemble_adjustment(self, agent_ids: List[str]) -> Dict[str, float]:
        """集成權重調整"""
        # 獲取多種方法的權重
        performance_weights = self._performance_based_adjustment(agent_ids)
        risk_adjusted_weights = self._risk_adjusted_adjustment(agent_ids)
        sharpe_weights = self._sharpe_ratio_adjustment(agent_ids)

        # 集成權重（等權重組合）
        ensemble_weights = {}
        for agent_id in agent_ids:
            ensemble_weights[agent_id] = (
                performance_weights.get(agent_id, 0.0) * 0.4 +
                risk_adjusted_weights.get(agent_id, 0.0) * 0.3 +
                sharpe_weights.get(agent_id, 0.0) * 0.3
            )

        return self._scores_to_weights(ensemble_weights)

    def _scores_to_weights(self, scores: Dict[str, float]) -> Dict[str, float]:
        """將評分轉換為權重"""
        if not scores:
            return {}

        # 處理負分數
        min_score = min(scores.values())
        if min_score < 0:
            adjusted_scores = {k: v - min_score + 0.1 for k, v in scores.items()}
        else:
            adjusted_scores = {k: v + 0.1 for k, v in scores.items()}  # 避免零權重

        # 標準化
        total_score = sum(adjusted_scores.values())
        if total_score > 0:
            weights = {k: v / total_score for k, v in adjusted_scores.items()}
        else:
            # 等權重
            equal_weight = 1.0 / len(scores)
            weights = {k: equal_weight for k in scores.keys()}

        return weights

    def _apply_weight_constraints(self, weights: Dict[str, float]) -> Dict[str, float]:
        """應用權重約束"""
        constrained_weights = {}

        for agent_id, weight in weights.items():
            # 應用最小最大權重約束
            constrained_weight = max(self.min_weight, min(self.max_weight, weight))
            constrained_weights[agent_id] = constrained_weight

        # 重新標準化
        total_weight = sum(constrained_weights.values())
        if total_weight > 0:
            constrained_weights = {k: v / total_weight for k, v in constrained_weights.items()}

        return constrained_weights

    def _create_adjustment_records(self, new_weights: Dict[str, float]) -> Dict[str, WeightAdjustment]:
        """創建權重調整記錄"""
        adjustments = {}

        for agent_id, new_weight in new_weights.items():
            old_weight = self.current_weights.get(agent_id, 1.0 / len(new_weights))

            if abs(new_weight - old_weight) > 0.01:  # 只記錄顯著變化
                adjustment_ratio = (new_weight - old_weight) / old_weight if old_weight > 0 else 0.0

                # 計算調整原因
                performance_score = self._get_agent_performance_score(agent_id)
                risk_score = self._get_agent_risk_score(agent_id)
                confidence_score = self._get_agent_confidence_score(agent_id)

                adjustment_reason = self._generate_adjustment_reason(
                    adjustment_ratio, performance_score, risk_score
                )

                adjustments[agent_id] = WeightAdjustment(
                    agent_id=agent_id,
                    old_weight=old_weight,
                    new_weight=new_weight,
                    adjustment_ratio=adjustment_ratio,
                    adjustment_reason=adjustment_reason,
                    performance_score=performance_score,
                    risk_score=risk_score,
                    confidence_score=confidence_score,
                    timestamp=datetime.now(),
                    metadata={
                        'adjustment_method': self.adjustment_method.value,
                        'performance_window': self.performance_window
                    }
                )

        return adjustments

    def _get_agent_performance_score(self, agent_id: str) -> float:
        """獲取代理績效評分"""
        history = list(self.performance_history[agent_id])
        if not history:
            return 0.5

        recent_records = history[-self.performance_window:]
        returns = [record.decision_return for record in recent_records]

        if not returns:
            return 0.5

        avg_return = np.mean(returns)
        win_rate = sum(1 for r in returns if r > 0) / len(returns)

        return avg_return * win_rate

    def _get_agent_risk_score(self, agent_id: str) -> float:
        """獲取代理風險評分"""
        history = list(self.performance_history[agent_id])
        if not history:
            return 0.5

        recent_records = history[-self.performance_window:]

        if len(recent_records) < 2:
            return 0.5

        # 風險評分基於最大回撤和波動率
        max_drawdown = max(record.max_drawdown for record in recent_records)
        avg_volatility = np.mean([record.volatility for record in recent_records])

        # 風險評分：回撤和波動率越低，評分越高
        risk_score = 1.0 - (max_drawdown * 0.5 + avg_volatility * 0.5)
        return max(0.0, min(1.0, risk_score))

    def _get_agent_confidence_score(self, agent_id: str) -> float:
        """獲取代理信心度評分"""
        history = list(self.performance_history[agent_id])
        if not history:
            return 0.5

        recent_records = history[-self.performance_window:]
        confidences = [record.confidence for record in recent_records]

        return np.mean(confidences) if confidences else 0.5

    def _generate_adjustment_reason(
        self,
        adjustment_ratio: float,
        performance_score: float,
        risk_score: float
    ) -> str:
        """生成調整原因"""
        if adjustment_ratio > 0.1:
            if performance_score > 0.7:
                return "績效優秀，增加權重"
            elif risk_score > 0.7:
                return "風險控制良好，增加權重"
            else:
                return "綜合表現改善，增加權重"
        elif adjustment_ratio < -0.1:
            if performance_score < 0.3:
                return "績效不佳，減少權重"
            elif risk_score < 0.3:
                return "風險過高，減少權重"
            else:
                return "相對表現下降，減少權重"
        else:
            return "微調權重"

    def _prepare_ml_data(self, agent_ids: List[str]) -> Tuple[List[List[float]], List[float]]:
        """準備機器學習訓練數據"""
        features = []
        targets = []

        for agent_id in agent_ids:
            history = list(self.performance_history[agent_id])

            for i in range(5, len(history)):  # 需要至少5個歷史記錄作為特徵
                # 提取特徵
                feature_window = history[i-5:i]
                agent_features = self._extract_features_from_window(feature_window)

                # 目標值（下一期績效）
                target_performance = history[i].decision_return

                features.append(agent_features)
                targets.append(target_performance)

        return features, targets

    def _extract_features_from_window(self, window: List[PerformanceRecord]) -> List[float]:
        """從績效窗口提取特徵"""
        if not window:
            return [0.0] * 10  # 返回默認特徵

        returns = [record.decision_return for record in window]
        confidences = [record.confidence for record in window]
        position_sizes = [record.position_size for record in window]

        features = [
            np.mean(returns),                    # 平均收益率
            np.std(returns),                     # 收益率標準差
            np.mean(confidences),                # 平均信心度
            np.std(confidences),                 # 信心度標準差
            np.mean(position_sizes),             # 平均倉位大小
            sum(1 for r in returns if r > 0) / len(returns),  # 勝率
            max(returns) if returns else 0.0,   # 最大收益
            min(returns) if returns else 0.0,   # 最大虧損
            window[-1].sharpe_ratio,             # 最新夏普比率
            window[-1].max_drawdown              # 最新最大回撤
        ]

        return features

    def _extract_agent_features(self, agent_id: str) -> Optional[List[float]]:
        """提取代理當前特徵"""
        history = list(self.performance_history[agent_id])

        if len(history) < 5:
            return None

        return self._extract_features_from_window(history[-5:])

    def _update_adjustment_stats(self, adjustments: Dict[str, WeightAdjustment]) -> None:
        """更新調整統計"""
        self.performance_stats['total_adjustments'] += len(adjustments)

        for adjustment in adjustments.values():
            if adjustment.adjustment_ratio > 0:
                self.performance_stats['positive_adjustments'] += 1
            else:
                self.performance_stats['negative_adjustments'] += 1

        # 更新最佳和最差表現者
        if adjustments:
            best_adjustment = max(adjustments.values(), key=lambda x: x.performance_score)
            worst_adjustment = min(adjustments.values(), key=lambda x: x.performance_score)

            self.performance_stats['best_performer'] = best_adjustment.agent_id
            self.performance_stats['worst_performer'] = worst_adjustment.agent_id

    def get_current_weights(self) -> Dict[str, float]:
        """獲取當前權重"""
        return self.current_weights.copy()

    def get_performance_stats(self) -> Dict[str, Any]:
        """獲取績效統計"""
        stats = self.performance_stats.copy()

        # 添加代理數量
        stats['total_agents'] = len(self.current_weights)
        stats['active_agents'] = len(self.performance_history)

        # 計算調整成功率
        total_adjustments = stats['total_adjustments']
        if total_adjustments > 0:
            stats['positive_adjustment_rate'] = stats['positive_adjustments'] / total_adjustments
        else:
            stats['positive_adjustment_rate'] = 0.0

        return stats

    def get_adjustment_history(self, limit: Optional[int] = None) -> List[WeightAdjustment]:
        """獲取調整歷史"""
        if limit:
            return self.adjustment_history[-limit:]
        return self.adjustment_history.copy()

    def set_weight(self, agent_id: str, weight: float) -> None:
        """手動設定代理權重"""
        constrained_weight = max(self.min_weight, min(self.max_weight, weight))
        self.current_weights[agent_id] = constrained_weight
        logger.info(f"手動設定代理 {agent_id} 權重為 {constrained_weight}")

    def reset_weights(self) -> None:
        """重置所有權重"""
        self.current_weights.clear()
        logger.info("所有代理權重已重置")

    def __str__(self) -> str:
        """字符串表示"""
        return (f"DynamicWeightAdjuster(method={self.adjustment_method.value}, "
                f"agents={len(self.current_weights)}, "
                f"adjustments={self.performance_stats['total_adjustments']})")
