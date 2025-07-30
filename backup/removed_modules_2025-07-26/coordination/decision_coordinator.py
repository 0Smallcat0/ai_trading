# -*- coding: utf-8 -*-
"""
決策協調器模組

此模組實現多代理決策協調機制，負責整合來自不同代理的投資決策。

核心功能：
- 多代理決策聚合
- 投票機制和加權平均
- 衝突檢測和解決
- 決策品質評估
- 協調策略優化

協調算法：
- 簡單投票（Simple Voting）
- 加權投票（Weighted Voting）
- 信心度加權（Confidence Weighted）
- 績效加權（Performance Weighted）
- 混合協調（Hybrid Coordination）
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict

from ..agents.base import AgentDecision, TradingAgent

# 設定日誌
logger = logging.getLogger(__name__)


class CoordinationMethod(Enum):
    """協調方法枚舉"""
    SIMPLE_VOTING = "simple_voting"           # 簡單投票
    WEIGHTED_VOTING = "weighted_voting"       # 加權投票
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # 信心度加權
    PERFORMANCE_WEIGHTED = "performance_weighted"  # 績效加權
    HYBRID = "hybrid"                         # 混合協調
    CONSENSUS = "consensus"                   # 共識機制


class ConflictResolution(Enum):
    """衝突解決策略枚舉"""
    MAJORITY_RULE = "majority_rule"           # 多數決
    HIGHEST_CONFIDENCE = "highest_confidence"  # 最高信心度
    BEST_PERFORMER = "best_performer"         # 最佳績效者
    WEIGHTED_AVERAGE = "weighted_average"     # 加權平均
    ABSTAIN = "abstain"                       # 棄權


@dataclass
class CoordinatedDecision:
    """協調決策結果"""
    symbol: str
    final_action: int                         # 最終行動 (-1, 0, 1)
    final_confidence: float                   # 最終信心度
    final_position_size: float                # 最終倉位大小
    coordination_method: CoordinationMethod   # 使用的協調方法
    participating_agents: List[str]           # 參與代理列表
    agent_decisions: Dict[str, AgentDecision] # 各代理決策
    decision_weights: Dict[str, float]        # 決策權重
    conflict_detected: bool                   # 是否檢測到衝突
    conflict_resolution: Optional[ConflictResolution]  # 衝突解決方法
    coordination_confidence: float            # 協調信心度
    reasoning: str                           # 協調推理
    timestamp: datetime                      # 決策時間
    metadata: Dict[str, Any]                 # 額外元數據


class DecisionCoordinator:
    """
    決策協調器 - 整合多代理決策的核心組件。
    
    負責收集各代理的投資決策，通過不同的協調算法
    生成最終的統一決策，並處理代理間的衝突。
    
    Attributes:
        coordination_method (CoordinationMethod): 默認協調方法
        conflict_resolution (ConflictResolution): 衝突解決策略
        min_agents_required (int): 最少參與代理數量
        consensus_threshold (float): 共識閾值
        confidence_threshold (float): 信心度閾值
        performance_window (int): 績效評估窗口
        weight_decay (float): 權重衰減因子
    """
    
    def __init__(
        self,
        coordination_method: CoordinationMethod = CoordinationMethod.HYBRID,
        conflict_resolution: ConflictResolution = ConflictResolution.WEIGHTED_AVERAGE,
        min_agents_required: int = 3,
        consensus_threshold: float = 0.7,
        confidence_threshold: float = 0.6,
        performance_window: int = 30,
        weight_decay: float = 0.95
    ) -> None:
        """
        初始化決策協調器。
        
        Args:
            coordination_method: 默認協調方法
            conflict_resolution: 衝突解決策略
            min_agents_required: 最少參與代理數量
            consensus_threshold: 共識閾值
            confidence_threshold: 信心度閾值
            performance_window: 績效評估窗口（天數）
            weight_decay: 權重衰減因子
        """
        self.coordination_method = coordination_method
        self.conflict_resolution = conflict_resolution
        self.min_agents_required = min_agents_required
        self.consensus_threshold = consensus_threshold
        self.confidence_threshold = confidence_threshold
        self.performance_window = performance_window
        self.weight_decay = weight_decay
        
        # 代理權重和績效追蹤
        self.agent_weights: Dict[str, float] = {}
        self.agent_performance: Dict[str, List[float]] = defaultdict(list)
        self.decision_history: List[CoordinatedDecision] = []
        
        # 協調統計
        self.coordination_stats = {
            'total_decisions': 0,
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'method_usage': defaultdict(int),
            'average_confidence': 0.0,
            'success_rate': 0.0
        }
        
        logger.info(f"初始化決策協調器: {coordination_method.value}")
    
    def coordinate_decisions(
        self,
        agent_decisions: Dict[str, AgentDecision],
        symbol: str,
        method: Optional[CoordinationMethod] = None,
        agent_weights: Optional[Dict[str, float]] = None
    ) -> CoordinatedDecision:
        """
        協調多代理決策。
        
        Args:
            agent_decisions: 各代理的決策字典
            symbol: 交易標的
            method: 指定協調方法（可選）
            agent_weights: 指定代理權重（可選）
            
        Returns:
            CoordinatedDecision: 協調後的決策
        """
        try:
            # 驗證輸入
            if not self._validate_decisions(agent_decisions):
                return self._create_abstain_decision(symbol, "決策驗證失敗")
            
            # 使用指定方法或默認方法
            coordination_method = method or self.coordination_method
            
            # 獲取代理權重
            weights = agent_weights or self._get_agent_weights(list(agent_decisions.keys()))
            
            # 檢測衝突
            conflict_info = self._detect_conflicts(agent_decisions)
            
            # 根據協調方法生成決策
            if coordination_method == CoordinationMethod.SIMPLE_VOTING:
                coordinated_decision = self._simple_voting(agent_decisions, symbol, weights)
            elif coordination_method == CoordinationMethod.WEIGHTED_VOTING:
                coordinated_decision = self._weighted_voting(agent_decisions, symbol, weights)
            elif coordination_method == CoordinationMethod.CONFIDENCE_WEIGHTED:
                coordinated_decision = self._confidence_weighted(agent_decisions, symbol)
            elif coordination_method == CoordinationMethod.PERFORMANCE_WEIGHTED:
                coordinated_decision = self._performance_weighted(agent_decisions, symbol)
            elif coordination_method == CoordinationMethod.CONSENSUS:
                coordinated_decision = self._consensus_coordination(agent_decisions, symbol, weights)
            else:  # HYBRID
                coordinated_decision = self._hybrid_coordination(agent_decisions, symbol, weights)
            
            # 處理衝突
            if conflict_info['has_conflict']:
                coordinated_decision = self._resolve_conflicts(
                    coordinated_decision, conflict_info, agent_decisions
                )
            
            # 更新統計和歷史
            self._update_coordination_stats(coordinated_decision, conflict_info)
            self.decision_history.append(coordinated_decision)
            
            return coordinated_decision
            
        except Exception as e:
            logger.error(f"決策協調失敗: {e}")
            return self._create_abstain_decision(symbol, f"協調過程異常: {e}")
    
    def _validate_decisions(self, agent_decisions: Dict[str, AgentDecision]) -> bool:
        """驗證代理決策"""
        if len(agent_decisions) < self.min_agents_required:
            logger.warning(f"參與代理數量不足: {len(agent_decisions)} < {self.min_agents_required}")
            return False
        
        # 檢查決策格式
        for agent_id, decision in agent_decisions.items():
            if not isinstance(decision, AgentDecision):
                logger.warning(f"代理 {agent_id} 決策格式錯誤")
                return False
            
            if decision.action not in [-1, 0, 1]:
                logger.warning(f"代理 {agent_id} 行動值無效: {decision.action}")
                return False
            
            if not (0 <= decision.confidence <= 1):
                logger.warning(f"代理 {agent_id} 信心度無效: {decision.confidence}")
                return False
        
        return True
    
    def _get_agent_weights(self, agent_ids: List[str]) -> Dict[str, float]:
        """獲取代理權重"""
        weights = {}
        total_weight = 0.0
        
        for agent_id in agent_ids:
            if agent_id in self.agent_weights:
                weights[agent_id] = self.agent_weights[agent_id]
            else:
                weights[agent_id] = 1.0  # 默認權重
            total_weight += weights[agent_id]
        
        # 標準化權重
        if total_weight > 0:
            weights = {agent_id: weight / total_weight for agent_id, weight in weights.items()}
        else:
            # 等權重
            equal_weight = 1.0 / len(agent_ids)
            weights = {agent_id: equal_weight for agent_id in agent_ids}
        
        return weights
    
    def _detect_conflicts(self, agent_decisions: Dict[str, AgentDecision]) -> Dict[str, Any]:
        """檢測代理間衝突"""
        actions = [decision.action for decision in agent_decisions.values()]
        unique_actions = set(actions)
        
        # 基本衝突檢測
        has_conflict = len(unique_actions) > 1 and 0 not in unique_actions
        
        # 詳細衝突分析
        buy_count = sum(1 for action in actions if action == 1)
        sell_count = sum(1 for action in actions if action == -1)
        hold_count = sum(1 for action in actions if action == 0)
        
        conflict_severity = 0.0
        if has_conflict:
            # 計算衝突嚴重程度
            total_agents = len(actions)
            if buy_count > 0 and sell_count > 0:
                conflict_severity = min(buy_count, sell_count) / total_agents
        
        return {
            'has_conflict': has_conflict,
            'conflict_severity': conflict_severity,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'hold_count': hold_count,
            'unique_actions': unique_actions,
            'action_distribution': {
                'buy': buy_count / len(actions),
                'sell': sell_count / len(actions),
                'hold': hold_count / len(actions)
            }
        }

    def _simple_voting(
        self,
        agent_decisions: Dict[str, AgentDecision],
        symbol: str,
        weights: Dict[str, float]
    ) -> CoordinatedDecision:
        """簡單投票協調"""
        actions = [decision.action for decision in agent_decisions.values()]

        # 統計投票
        vote_counts = {-1: 0, 0: 0, 1: 0}
        for action in actions:
            vote_counts[action] += 1

        # 多數決
        final_action = max(vote_counts.items(), key=lambda x: x[1])[0]

        # 計算平均信心度
        confidences = [decision.confidence for decision in agent_decisions.values()]
        final_confidence = np.mean(confidences)

        # 計算平均倉位大小
        position_sizes = [decision.position_size for decision in agent_decisions.values()]
        final_position_size = np.mean(position_sizes)

        return CoordinatedDecision(
            symbol=symbol,
            final_action=final_action,
            final_confidence=final_confidence,
            final_position_size=final_position_size,
            coordination_method=CoordinationMethod.SIMPLE_VOTING,
            participating_agents=list(agent_decisions.keys()),
            agent_decisions=agent_decisions,
            decision_weights=weights,
            conflict_detected=len(set(actions)) > 1,
            conflict_resolution=None,
            coordination_confidence=final_confidence,
            reasoning=f"簡單投票結果: {vote_counts}, 多數決選擇 {final_action}",
            timestamp=datetime.now(),
            metadata={'vote_counts': vote_counts}
        )

    def _weighted_voting(
        self,
        agent_decisions: Dict[str, AgentDecision],
        symbol: str,
        weights: Dict[str, float]
    ) -> CoordinatedDecision:
        """加權投票協調"""
        weighted_votes = {-1: 0.0, 0: 0.0, 1: 0.0}
        total_confidence = 0.0
        total_position_size = 0.0

        for agent_id, decision in agent_decisions.items():
            weight = weights.get(agent_id, 0.0)
            weighted_votes[decision.action] += weight
            total_confidence += decision.confidence * weight
            total_position_size += decision.position_size * weight

        # 加權多數決
        final_action = max(weighted_votes.items(), key=lambda x: x[1])[0]

        return CoordinatedDecision(
            symbol=symbol,
            final_action=final_action,
            final_confidence=total_confidence,
            final_position_size=total_position_size,
            coordination_method=CoordinationMethod.WEIGHTED_VOTING,
            participating_agents=list(agent_decisions.keys()),
            agent_decisions=agent_decisions,
            decision_weights=weights,
            conflict_detected=len(set(d.action for d in agent_decisions.values())) > 1,
            conflict_resolution=None,
            coordination_confidence=total_confidence,
            reasoning=f"加權投票結果: {weighted_votes}, 選擇 {final_action}",
            timestamp=datetime.now(),
            metadata={'weighted_votes': weighted_votes}
        )

    def _confidence_weighted(
        self,
        agent_decisions: Dict[str, AgentDecision],
        symbol: str
    ) -> CoordinatedDecision:
        """信心度加權協調"""
        total_weighted_action = 0.0
        total_confidence = 0.0
        total_position_size = 0.0
        confidence_weights = {}

        # 計算信心度權重
        total_conf = sum(decision.confidence for decision in agent_decisions.values())

        for agent_id, decision in agent_decisions.items():
            conf_weight = decision.confidence / total_conf if total_conf > 0 else 1.0 / len(agent_decisions)
            confidence_weights[agent_id] = conf_weight

            total_weighted_action += decision.action * conf_weight
            total_confidence += decision.confidence * conf_weight
            total_position_size += decision.position_size * conf_weight

        # 決定最終行動
        if total_weighted_action > 0.3:
            final_action = 1
        elif total_weighted_action < -0.3:
            final_action = -1
        else:
            final_action = 0

        return CoordinatedDecision(
            symbol=symbol,
            final_action=final_action,
            final_confidence=total_confidence,
            final_position_size=total_position_size,
            coordination_method=CoordinationMethod.CONFIDENCE_WEIGHTED,
            participating_agents=list(agent_decisions.keys()),
            agent_decisions=agent_decisions,
            decision_weights=confidence_weights,
            conflict_detected=len(set(d.action for d in agent_decisions.values())) > 1,
            conflict_resolution=None,
            coordination_confidence=total_confidence,
            reasoning=f"信心度加權結果: {total_weighted_action:.2f}, 選擇 {final_action}",
            timestamp=datetime.now(),
            metadata={'weighted_action_score': total_weighted_action}
        )

    def _performance_weighted(
        self,
        agent_decisions: Dict[str, AgentDecision],
        symbol: str
    ) -> CoordinatedDecision:
        """績效加權協調"""
        performance_weights = {}
        total_performance = 0.0

        # 計算績效權重
        for agent_id in agent_decisions.keys():
            if agent_id in self.agent_performance and self.agent_performance[agent_id]:
                # 使用最近績效的平均值
                recent_performance = self.agent_performance[agent_id][-self.performance_window:]
                avg_performance = np.mean(recent_performance)
                performance_weights[agent_id] = max(0.1, avg_performance)  # 最小權重0.1
            else:
                performance_weights[agent_id] = 0.5  # 默認中等權重
            total_performance += performance_weights[agent_id]

        # 標準化權重
        if total_performance > 0:
            performance_weights = {
                agent_id: weight / total_performance
                for agent_id, weight in performance_weights.items()
            }

        # 使用績效權重進行加權投票
        return self._weighted_voting(agent_decisions, symbol, performance_weights)

    def _consensus_coordination(
        self,
        agent_decisions: Dict[str, AgentDecision],
        symbol: str,
        weights: Dict[str, float]
    ) -> CoordinatedDecision:
        """共識協調"""
        actions = [decision.action for decision in agent_decisions.values()]
        action_counts = {-1: 0, 0: 0, 1: 0}

        for action in actions:
            action_counts[action] += 1

        total_agents = len(actions)
        max_count = max(action_counts.values())
        consensus_ratio = max_count / total_agents

        if consensus_ratio >= self.consensus_threshold:
            # 達成共識
            final_action = max(action_counts.items(), key=lambda x: x[1])[0]
            coordination_confidence = consensus_ratio
        else:
            # 未達成共識，棄權
            final_action = 0
            coordination_confidence = 0.5

        # 計算平均值
        avg_confidence = np.mean([d.confidence for d in agent_decisions.values()])
        avg_position_size = np.mean([d.position_size for d in agent_decisions.values()])

        return CoordinatedDecision(
            symbol=symbol,
            final_action=final_action,
            final_confidence=avg_confidence,
            final_position_size=avg_position_size if final_action != 0 else 0.0,
            coordination_method=CoordinationMethod.CONSENSUS,
            participating_agents=list(agent_decisions.keys()),
            agent_decisions=agent_decisions,
            decision_weights=weights,
            conflict_detected=consensus_ratio < self.consensus_threshold,
            conflict_resolution=ConflictResolution.ABSTAIN if consensus_ratio < self.consensus_threshold else None,
            coordination_confidence=coordination_confidence,
            reasoning=f"共識比例: {consensus_ratio:.2f}, 閾值: {self.consensus_threshold}, {'達成共識' if consensus_ratio >= self.consensus_threshold else '未達成共識'}",
            timestamp=datetime.now(),
            metadata={'consensus_ratio': consensus_ratio, 'action_counts': action_counts}
        )

    def _hybrid_coordination(
        self,
        agent_decisions: Dict[str, AgentDecision],
        symbol: str,
        weights: Dict[str, float]
    ) -> CoordinatedDecision:
        """混合協調策略"""
        # 先嘗試共識協調
        consensus_result = self._consensus_coordination(agent_decisions, symbol, weights)

        if not consensus_result.conflict_detected:
            # 達成共識，使用共識結果
            consensus_result.coordination_method = CoordinationMethod.HYBRID
            consensus_result.reasoning = f"混合協調-共識: {consensus_result.reasoning}"
            return consensus_result

        # 未達成共識，使用信心度加權
        confidence_result = self._confidence_weighted(agent_decisions, symbol)
        confidence_result.coordination_method = CoordinationMethod.HYBRID
        confidence_result.reasoning = f"混合協調-信心度加權: {confidence_result.reasoning}"

        return confidence_result

    def _resolve_conflicts(
        self,
        coordinated_decision: CoordinatedDecision,
        conflict_info: Dict[str, Any],
        agent_decisions: Dict[str, AgentDecision]
    ) -> CoordinatedDecision:
        """解決衝突"""
        if not conflict_info['has_conflict']:
            return coordinated_decision

        resolution_method = self.conflict_resolution

        if resolution_method == ConflictResolution.MAJORITY_RULE:
            # 已在投票中處理
            pass

        elif resolution_method == ConflictResolution.HIGHEST_CONFIDENCE:
            # 選擇信心度最高的決策
            highest_conf_agent = max(
                agent_decisions.items(),
                key=lambda x: x[1].confidence
            )
            best_decision = highest_conf_agent[1]

            coordinated_decision.final_action = best_decision.action
            coordinated_decision.final_confidence = best_decision.confidence
            coordinated_decision.final_position_size = best_decision.position_size
            coordinated_decision.reasoning += f" | 衝突解決：選擇最高信心度代理 {highest_conf_agent[0]}"

        elif resolution_method == ConflictResolution.BEST_PERFORMER:
            # 選擇績效最佳的代理決策
            best_performer = self._get_best_performer(list(agent_decisions.keys()))
            if best_performer and best_performer in agent_decisions:
                best_decision = agent_decisions[best_performer]
                coordinated_decision.final_action = best_decision.action
                coordinated_decision.final_confidence = best_decision.confidence
                coordinated_decision.final_position_size = best_decision.position_size
                coordinated_decision.reasoning += f" | 衝突解決：選擇最佳績效代理 {best_performer}"

        elif resolution_method == ConflictResolution.WEIGHTED_AVERAGE:
            # 已在加權協調中處理
            pass

        elif resolution_method == ConflictResolution.ABSTAIN:
            # 棄權
            coordinated_decision.final_action = 0
            coordinated_decision.final_position_size = 0.0
            coordinated_decision.reasoning += " | 衝突解決：棄權"

        coordinated_decision.conflict_resolution = resolution_method
        return coordinated_decision

    def _get_best_performer(self, agent_ids: List[str]) -> Optional[str]:
        """獲取績效最佳的代理"""
        best_agent = None
        best_performance = -float('inf')

        for agent_id in agent_ids:
            if agent_id in self.agent_performance and self.agent_performance[agent_id]:
                recent_performance = self.agent_performance[agent_id][-self.performance_window:]
                avg_performance = np.mean(recent_performance)

                if avg_performance > best_performance:
                    best_performance = avg_performance
                    best_agent = agent_id

        return best_agent

    def _create_abstain_decision(self, symbol: str, reason: str) -> CoordinatedDecision:
        """創建棄權決策"""
        return CoordinatedDecision(
            symbol=symbol,
            final_action=0,
            final_confidence=0.0,
            final_position_size=0.0,
            coordination_method=self.coordination_method,
            participating_agents=[],
            agent_decisions={},
            decision_weights={},
            conflict_detected=False,
            conflict_resolution=ConflictResolution.ABSTAIN,
            coordination_confidence=0.0,
            reasoning=f"協調器棄權: {reason}",
            timestamp=datetime.now(),
            metadata={'abstain_reason': reason}
        )

    def _update_coordination_stats(
        self,
        coordinated_decision: CoordinatedDecision,
        conflict_info: Dict[str, Any]
    ) -> None:
        """更新協調統計"""
        self.coordination_stats['total_decisions'] += 1

        if conflict_info['has_conflict']:
            self.coordination_stats['conflicts_detected'] += 1

            if coordinated_decision.conflict_resolution:
                self.coordination_stats['conflicts_resolved'] += 1

        self.coordination_stats['method_usage'][coordinated_decision.coordination_method.value] += 1

        # 更新平均信心度
        total_decisions = self.coordination_stats['total_decisions']
        current_avg = self.coordination_stats['average_confidence']
        new_confidence = coordinated_decision.final_confidence

        self.coordination_stats['average_confidence'] = (
            (current_avg * (total_decisions - 1) + new_confidence) / total_decisions
        )

    def update_agent_performance(self, agent_id: str, performance: float) -> None:
        """更新代理績效"""
        self.agent_performance[agent_id].append(performance)

        # 保持績效歷史在合理範圍內
        if len(self.agent_performance[agent_id]) > self.performance_window * 2:
            self.agent_performance[agent_id] = self.agent_performance[agent_id][-self.performance_window:]

        # 更新權重（基於績效）
        if len(self.agent_performance[agent_id]) >= 5:  # 至少5個績效記錄
            recent_performance = self.agent_performance[agent_id][-10:]  # 最近10個記錄
            avg_performance = np.mean(recent_performance)

            # 績效轉換為權重（0.1 到 2.0）
            normalized_performance = max(0.1, min(2.0, 1.0 + avg_performance))

            # 應用衰減
            if agent_id in self.agent_weights:
                self.agent_weights[agent_id] = (
                    self.agent_weights[agent_id] * self.weight_decay +
                    normalized_performance * (1 - self.weight_decay)
                )
            else:
                self.agent_weights[agent_id] = normalized_performance

    def set_agent_weight(self, agent_id: str, weight: float) -> None:
        """手動設定代理權重"""
        self.agent_weights[agent_id] = max(0.0, weight)
        logger.info(f"設定代理 {agent_id} 權重為 {weight}")

    def get_coordination_stats(self) -> Dict[str, Any]:
        """獲取協調統計信息"""
        stats = self.coordination_stats.copy()

        # 計算成功率
        if stats['total_decisions'] > 0:
            stats['conflict_rate'] = stats['conflicts_detected'] / stats['total_decisions']
            stats['resolution_rate'] = stats['conflicts_resolved'] / max(1, stats['conflicts_detected'])
        else:
            stats['conflict_rate'] = 0.0
            stats['resolution_rate'] = 0.0

        # 添加代理權重信息
        stats['agent_weights'] = self.agent_weights.copy()
        stats['active_agents'] = len(self.agent_weights)

        return stats

    def get_decision_history(self, limit: Optional[int] = None) -> List[CoordinatedDecision]:
        """獲取決策歷史"""
        if limit:
            return self.decision_history[-limit:]
        return self.decision_history.copy()

    def clear_history(self) -> None:
        """清除歷史記錄"""
        self.decision_history.clear()
        self.coordination_stats = {
            'total_decisions': 0,
            'conflicts_detected': 0,
            'conflicts_resolved': 0,
            'method_usage': defaultdict(int),
            'average_confidence': 0.0,
            'success_rate': 0.0
        }
        logger.info("協調器歷史記錄已清除")

    def __str__(self) -> str:
        """字符串表示"""
        return (f"DecisionCoordinator(method={self.coordination_method.value}, "
                f"agents={len(self.agent_weights)}, "
                f"decisions={self.coordination_stats['total_decisions']})")
