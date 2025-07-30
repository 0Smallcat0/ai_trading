# -*- coding: utf-8 -*-
"""
多代理管理器模組

此模組實現多代理系統的核心管理功能，包括：
- 代理生命週期管理
- 代理間協調和通信
- 資源分配和調度
- 績效監控和評估

主要功能：
- 註冊和管理多個交易代理
- 協調代理間的決策過程
- 動態調整代理權重
- 監控代理績效和狀態
"""

import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

import pandas as pd
import numpy as np

from .base import TradingAgent, AgentMessage, AgentDecision, AgentError
from .communication import AgentCommunication

# 設定日誌
logger = logging.getLogger(__name__)


class AgentManagerError(AgentError):
    """代理管理器錯誤"""
    pass


class AgentManager:
    """
    多代理管理器。
    
    負責管理所有交易代理的生命週期、協調代理間的通信和決策過程。
    
    Attributes:
        agents (Dict[str, TradingAgent]): 註冊的代理字典
        agent_weights (Dict[str, float]): 代理權重
        communication (AgentCommunication): 通信管理器
        is_running (bool): 管理器運行狀態
        performance_tracker (Dict): 績效追蹤器
    """
    
    def __init__(
        self,
        max_agents: int = 20,
        default_weight: float = 1.0,
        rebalance_frequency: int = 30,  # 天數
        enable_async: bool = True
    ) -> None:
        """
        初始化代理管理器。
        
        Args:
            max_agents: 最大代理數量
            default_weight: 默認代理權重
            rebalance_frequency: 權重重新平衡頻率（天數）
            enable_async: 是否啟用異步處理
        """
        self.max_agents = max_agents
        self.default_weight = default_weight
        self.rebalance_frequency = rebalance_frequency
        self.enable_async = enable_async
        
        # 代理管理
        self.agents: Dict[str, TradingAgent] = {}
        self.agent_weights: Dict[str, float] = {}
        self.agent_status: Dict[str, str] = {}  # active, inactive, error
        
        # 通信管理
        self.communication = AgentCommunication()
        
        # 狀態管理
        self.is_running = False
        self.last_rebalance = datetime.now()
        self._lock = threading.Lock()
        
        # 績效追蹤
        self.performance_tracker = {
            'total_decisions': 0,
            'successful_decisions': 0,
            'agent_performance': {},
            'last_update': datetime.now()
        }
        
        # 線程池（如果啟用異步）
        self.executor = ThreadPoolExecutor(max_workers=max_agents) if enable_async else None
        
        logger.info(f"初始化代理管理器，最大代理數: {max_agents}")
    
    def register_agent(
        self,
        agent: TradingAgent,
        weight: Optional[float] = None,
        auto_start: bool = True
    ) -> bool:
        """
        註冊新代理。
        
        Args:
            agent: 要註冊的代理
            weight: 代理權重，None使用默認權重
            auto_start: 是否自動啟動代理
            
        Returns:
            bool: 註冊是否成功
            
        Raises:
            AgentManagerError: 當註冊失敗時
        """
        try:
            with self._lock:
                # 檢查代理數量限制
                if len(self.agents) >= self.max_agents:
                    raise AgentManagerError(f"已達到最大代理數量限制: {self.max_agents}")
                
                # 檢查代理ID是否已存在
                if agent.agent_id in self.agents:
                    raise AgentManagerError(f"代理ID已存在: {agent.agent_id}")
                
                # 註冊代理
                self.agents[agent.agent_id] = agent
                self.agent_weights[agent.agent_id] = weight or self.default_weight
                self.agent_status[agent.agent_id] = "active" if auto_start else "inactive"
                
                # 初始化績效追蹤
                self.performance_tracker['agent_performance'][agent.agent_id] = {
                    'decisions': 0,
                    'success_rate': 0.0,
                    'avg_confidence': 0.0,
                    'last_decision': None
                }
                
                # 註冊到通信系統
                self.communication.register_agent(agent.agent_id)
                
                logger.info(f"成功註冊代理: {agent.name} (ID: {agent.agent_id[:8]})")
                return True
                
        except Exception as e:
            logger.error(f"註冊代理失敗: {e}")
            raise AgentManagerError(f"註冊代理失敗: {e}") from e
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        註銷代理。
        
        Args:
            agent_id: 代理ID
            
        Returns:
            bool: 註銷是否成功
        """
        try:
            with self._lock:
                if agent_id not in self.agents:
                    logger.warning(f"代理ID不存在: {agent_id}")
                    return False
                
                # 停止代理
                self.stop_agent(agent_id)
                
                # 移除代理
                agent = self.agents.pop(agent_id)
                self.agent_weights.pop(agent_id, None)
                self.agent_status.pop(agent_id, None)
                self.performance_tracker['agent_performance'].pop(agent_id, None)
                
                # 從通信系統註銷
                self.communication.unregister_agent(agent_id)
                
                logger.info(f"成功註銷代理: {agent.name}")
                return True
                
        except Exception as e:
            logger.error(f"註銷代理失敗: {e}")
            return False
    
    def start_agent(self, agent_id: str) -> bool:
        """
        啟動代理。
        
        Args:
            agent_id: 代理ID
            
        Returns:
            bool: 啟動是否成功
        """
        try:
            with self._lock:
                if agent_id not in self.agents:
                    logger.error(f"代理ID不存在: {agent_id}")
                    return False
                
                agent = self.agents[agent_id]
                agent.is_active = True
                self.agent_status[agent_id] = "active"
                
                logger.info(f"啟動代理: {agent.name}")
                return True
                
        except Exception as e:
            logger.error(f"啟動代理失敗: {e}")
            return False
    
    def stop_agent(self, agent_id: str) -> bool:
        """
        停止代理。
        
        Args:
            agent_id: 代理ID
            
        Returns:
            bool: 停止是否成功
        """
        try:
            with self._lock:
                if agent_id not in self.agents:
                    logger.error(f"代理ID不存在: {agent_id}")
                    return False
                
                agent = self.agents[agent_id]
                agent.is_active = False
                self.agent_status[agent_id] = "inactive"
                
                logger.info(f"停止代理: {agent.name}")
                return True
                
        except Exception as e:
            logger.error(f"停止代理失敗: {e}")
            return False
    
    def get_active_agents(self) -> List[TradingAgent]:
        """
        獲取所有活躍代理。
        
        Returns:
            List[TradingAgent]: 活躍代理列表
        """
        return [
            agent for agent_id, agent in self.agents.items()
            if self.agent_status.get(agent_id) == "active" and agent.is_active
        ]
    
    def get_agent_by_id(self, agent_id: str) -> Optional[TradingAgent]:
        """
        根據ID獲取代理。
        
        Args:
            agent_id: 代理ID
            
        Returns:
            Optional[TradingAgent]: 代理實例，不存在則返回None
        """
        return self.agents.get(agent_id)
    
    def get_agent_by_name(self, name: str) -> Optional[TradingAgent]:
        """
        根據名稱獲取代理。
        
        Args:
            name: 代理名稱
            
        Returns:
            Optional[TradingAgent]: 代理實例，不存在則返回None
        """
        for agent in self.agents.values():
            if agent.name == name:
                return agent
        return None
    
    def update_agent_weight(self, agent_id: str, weight: float) -> bool:
        """
        更新代理權重。
        
        Args:
            agent_id: 代理ID
            weight: 新權重
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with self._lock:
                if agent_id not in self.agents:
                    logger.error(f"代理ID不存在: {agent_id}")
                    return False
                
                if not 0 <= weight <= 1:
                    logger.error(f"權重必須在0-1之間: {weight}")
                    return False
                
                old_weight = self.agent_weights[agent_id]
                self.agent_weights[agent_id] = weight
                
                logger.info(f"更新代理權重: {agent_id[:8]} {old_weight:.3f} -> {weight:.3f}")
                return True
                
        except Exception as e:
            logger.error(f"更新代理權重失敗: {e}")
            return False
    
    def normalize_weights(self) -> None:
        """標準化所有代理權重，使其總和為1"""
        try:
            with self._lock:
                if not self.agent_weights:
                    return
                
                total_weight = sum(self.agent_weights.values())
                if total_weight > 0:
                    for agent_id in self.agent_weights:
                        self.agent_weights[agent_id] /= total_weight
                    
                    logger.debug("代理權重已標準化")
                
        except Exception as e:
            logger.error(f"標準化權重失敗: {e}")
    
    def get_manager_status(self) -> Dict[str, Any]:
        """
        獲取管理器狀態。
        
        Returns:
            Dict: 管理器狀態信息
        """
        active_agents = len([
            agent_id for agent_id, status in self.agent_status.items()
            if status == "active"
        ])
        
        return {
            'is_running': self.is_running,
            'total_agents': len(self.agents),
            'active_agents': active_agents,
            'inactive_agents': len(self.agents) - active_agents,
            'last_rebalance': self.last_rebalance,
            'performance_summary': self.performance_tracker,
            'agent_weights': self.agent_weights.copy(),
            'agent_status': self.agent_status.copy()
        }

    def collect_decisions(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> List[AgentDecision]:
        """
        收集所有活躍代理的決策。

        Args:
            data: 市場數據
            market_context: 市場上下文
            timeout: 超時時間（秒）

        Returns:
            List[AgentDecision]: 代理決策列表
        """
        active_agents = self.get_active_agents()
        if not active_agents:
            logger.warning("沒有活躍的代理")
            return []

        decisions = []

        if self.enable_async and self.executor:
            # 異步收集決策
            future_to_agent = {
                self.executor.submit(agent.make_decision, data, market_context): agent
                for agent in active_agents
            }

            try:
                for future in as_completed(future_to_agent, timeout=timeout):
                    agent = future_to_agent[future]
                    try:
                        decision = future.result()
                        decisions.append(decision)
                        self._update_agent_performance(agent.agent_id, decision)
                    except Exception as e:
                        logger.error(f"代理 {agent.name} 決策失敗: {e}")
                        self.agent_status[agent.agent_id] = "error"

            except Exception as e:
                logger.error(f"收集決策超時或失敗: {e}")

        else:
            # 同步收集決策
            for agent in active_agents:
                try:
                    decision = agent.make_decision(data, market_context)
                    decisions.append(decision)
                    self._update_agent_performance(agent.agent_id, decision)
                except Exception as e:
                    logger.error(f"代理 {agent.name} 決策失敗: {e}")
                    self.agent_status[agent.agent_id] = "error"

        self.performance_tracker['total_decisions'] += len(decisions)
        self.performance_tracker['last_update'] = datetime.now()

        logger.info(f"收集到 {len(decisions)} 個代理決策")
        return decisions

    def _update_agent_performance(self, agent_id: str, decision: AgentDecision) -> None:
        """更新代理績效統計"""
        if agent_id not in self.performance_tracker['agent_performance']:
            return

        perf = self.performance_tracker['agent_performance'][agent_id]
        perf['decisions'] += 1
        perf['last_decision'] = decision.timestamp

        # 更新平均置信度
        if perf['decisions'] == 1:
            perf['avg_confidence'] = decision.confidence
        else:
            # 指數移動平均
            alpha = 0.1
            perf['avg_confidence'] = (
                alpha * decision.confidence +
                (1 - alpha) * perf['avg_confidence']
            )

    def broadcast_message(
        self,
        message_type: str,
        content: Dict[str, Any],
        sender_id: Optional[str] = None,
        priority: int = 1
    ) -> int:
        """
        廣播消息給所有代理。

        Args:
            message_type: 消息類型
            content: 消息內容
            sender_id: 發送者ID
            priority: 優先級

        Returns:
            int: 成功發送的消息數量
        """
        active_agents = self.get_active_agents()
        sent_count = 0

        for agent in active_agents:
            if agent.agent_id != sender_id:  # 不發送給自己
                try:
                    message = AgentMessage(
                        sender_id=sender_id or "system",
                        receiver_id=agent.agent_id,
                        message_type=message_type,
                        content=content,
                        priority=priority
                    )
                    agent.receive_message(message)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"發送消息給代理 {agent.name} 失敗: {e}")

        logger.debug(f"廣播消息給 {sent_count} 個代理")
        return sent_count

    def rebalance_weights(self, performance_window: int = 30) -> bool:
        """
        基於績效重新平衡代理權重。

        Args:
            performance_window: 績效評估窗口（天數）

        Returns:
            bool: 重新平衡是否成功
        """
        try:
            if not self.agents:
                return False

            # 計算每個代理的績效分數
            performance_scores = {}

            for agent_id, agent in self.agents.items():
                if self.agent_status.get(agent_id) != "active":
                    performance_scores[agent_id] = 0.0
                    continue

                # 獲取績效摘要
                summary = agent.get_performance_summary(performance_window)

                # 計算綜合績效分數（夏普比率 + 勝率 - 最大回撤）
                sharpe_ratio = summary.get('sharpe_ratio', 0.0)
                win_rate = summary.get('win_rate', 0.0)
                max_drawdown = abs(summary.get('max_drawdown', 0.0))

                # 綜合分數（可以根據需要調整權重）
                score = 0.5 * sharpe_ratio + 0.3 * win_rate - 0.2 * max_drawdown
                performance_scores[agent_id] = max(0.0, score)  # 確保非負

            # 如果所有分數都為0，使用等權重
            total_score = sum(performance_scores.values())
            if total_score == 0:
                equal_weight = 1.0 / len(self.agents)
                for agent_id in self.agents:
                    self.agent_weights[agent_id] = equal_weight
            else:
                # 基於績效分數分配權重
                for agent_id, score in performance_scores.items():
                    self.agent_weights[agent_id] = score / total_score

            self.last_rebalance = datetime.now()
            logger.info("代理權重重新平衡完成")
            return True

        except Exception as e:
            logger.error(f"重新平衡權重失敗: {e}")
            return False

    def should_rebalance(self) -> bool:
        """檢查是否需要重新平衡權重"""
        days_since_rebalance = (datetime.now() - self.last_rebalance).days
        return days_since_rebalance >= self.rebalance_frequency

    def start_manager(self) -> bool:
        """啟動管理器"""
        try:
            self.is_running = True
            logger.info("代理管理器已啟動")
            return True
        except Exception as e:
            logger.error(f"啟動管理器失敗: {e}")
            return False

    def stop_manager(self) -> bool:
        """停止管理器"""
        try:
            self.is_running = False

            # 停止所有代理
            for agent_id in list(self.agents.keys()):
                self.stop_agent(agent_id)

            # 關閉線程池
            if self.executor:
                self.executor.shutdown(wait=True)

            logger.info("代理管理器已停止")
            return True
        except Exception as e:
            logger.error(f"停止管理器失敗: {e}")
            return False

    def __enter__(self):
        """上下文管理器入口"""
        self.start_manager()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop_manager()

    def __len__(self) -> int:
        """返回代理數量"""
        return len(self.agents)

    def __contains__(self, agent_id: str) -> bool:
        """檢查代理是否存在"""
        return agent_id in self.agents

    def __str__(self) -> str:
        """字符串表示"""
        return f"AgentManager(agents={len(self.agents)}, active={len(self.get_active_agents())})"
