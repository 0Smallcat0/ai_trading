# -*- coding: utf-8 -*-
"""
系統整合器模組

此模組實現多代理AI交易系統的統一整合管理，
負責協調所有組件的運行和交互。

核心功能：
- 統一系統入口點和管理介面
- 組件生命週期管理
- 配置管理和參數調優
- 實時監控和性能追蹤
- 錯誤處理和系統恢復
- 資源調度和優化

整合架構：
- 多代理系統（Phase 1-4）
- LLM策略模組
- 投資組合管理
- 風險管理系統
- 數據管理和處理
- 交易執行系統
"""

import logging
import asyncio
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# 導入多代理系統組件
from ..agents import AgentManager, TradingAgent
from ..agents.personas import BuffettAgent, SorosAgent, SimonsAgent, DalioAgent, GrahamAgent
from ..coordination import (
    DecisionCoordinator, DynamicWeightAdjuster, 
    PortfolioAllocator, AgentCommunication
)

# 導入現有系統組件
from ..strategy.llm_integration import LLMStrategy
from ..portfolio import PortfolioManager
from ..risk_management import RiskManager
from ..core.config_manager import ConfigManager
from ..core.logger import setup_logger
from ..monitoring.system_monitoring_service import SystemMonitoringService

# 設定日誌
logger = logging.getLogger(__name__)


class SystemState(Enum):
    """系統狀態枚舉"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class ComponentType(Enum):
    """組件類型枚舉"""
    AGENT = "agent"
    COORDINATOR = "coordinator"
    PORTFOLIO = "portfolio"
    RISK = "risk"
    LLM = "llm"
    DATA = "data"
    EXECUTION = "execution"
    MONITORING = "monitoring"


@dataclass
class ComponentInfo:
    """組件信息"""
    name: str
    type: ComponentType
    instance: Any
    status: str = "inactive"
    last_update: datetime = field(default_factory=datetime.now)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """系統指標"""
    total_agents: int = 0
    active_agents: int = 0
    total_decisions: int = 0
    coordination_success_rate: float = 0.0
    portfolio_value: float = 0.0
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    system_uptime: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    error_rate: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)


class SystemIntegrator:
    """
    系統整合器 - 多代理AI交易系統的統一管理中心。
    
    負責整合和協調所有系統組件，提供統一的管理介面，
    實現高效的資源調度和性能優化。
    
    Attributes:
        config_manager (ConfigManager): 配置管理器
        agent_manager (AgentManager): 代理管理器
        decision_coordinator (DecisionCoordinator): 決策協調器
        weight_adjuster (DynamicWeightAdjuster): 權重調整器
        portfolio_allocator (PortfolioAllocator): 投資組合分配器
        communication (AgentCommunication): 通信管理器
        monitoring_service (SystemMonitoringService): 監控服務
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        enable_monitoring: bool = True,
        enable_auto_optimization: bool = True,
        max_workers: int = 10
    ) -> None:
        """
        初始化系統整合器。
        
        Args:
            config_path: 配置文件路徑
            enable_monitoring: 是否啟用監控
            enable_auto_optimization: 是否啟用自動優化
            max_workers: 最大工作線程數
        """
        # 基礎配置
        self.config_manager = ConfigManager(config_path)
        self.enable_monitoring = enable_monitoring
        self.enable_auto_optimization = enable_auto_optimization
        self.max_workers = max_workers
        
        # 系統狀態
        self.system_state = SystemState.INITIALIZING
        self.start_time = datetime.now()
        self.components: Dict[str, ComponentInfo] = {}
        self.system_metrics = SystemMetrics()
        
        # 多代理系統組件
        self.agent_manager: Optional[AgentManager] = None
        self.decision_coordinator: Optional[DecisionCoordinator] = None
        self.weight_adjuster: Optional[DynamicWeightAdjuster] = None
        self.portfolio_allocator: Optional[PortfolioAllocator] = None
        self.communication: Optional[AgentCommunication] = None
        
        # 現有系統組件
        self.llm_strategy: Optional[LLMStrategy] = None
        self.portfolio_manager: Optional[PortfolioManager] = None
        self.risk_manager: Optional[RiskManager] = None
        self.monitoring_service: Optional[SystemMonitoringService] = None
        
        # 執行器和任務管理
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.background_tasks: List[asyncio.Task] = []
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # 性能統計
        self.performance_stats = {
            'decisions_per_second': 0.0,
            'coordination_latency': 0.0,
            'memory_efficiency': 0.0,
            'error_recovery_time': 0.0
        }
        
        # 錯誤處理
        self.error_handlers: Dict[str, Callable] = {}
        self.recovery_strategies: Dict[str, Callable] = {}
        
        logger.info("系統整合器初始化完成")
    
    async def initialize_system(self) -> bool:
        """
        初始化整個系統。
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            logger.info("開始初始化多代理AI交易系統...")
            
            # 1. 初始化配置
            await self._initialize_configuration()
            
            # 2. 初始化通信系統
            await self._initialize_communication()
            
            # 3. 初始化多代理系統
            await self._initialize_multi_agent_system()
            
            # 4. 初始化現有系統組件
            await self._initialize_existing_components()
            
            # 5. 初始化監控系統
            if self.enable_monitoring:
                await self._initialize_monitoring()
            
            # 6. 啟動後台任務
            await self._start_background_tasks()
            
            # 7. 系統健康檢查
            if await self._system_health_check():
                self.system_state = SystemState.RUNNING
                logger.info("多代理AI交易系統初始化成功")
                return True
            else:
                self.system_state = SystemState.ERROR
                logger.error("系統健康檢查失敗")
                return False
                
        except Exception as e:
            logger.error(f"系統初始化失敗: {e}")
            self.system_state = SystemState.ERROR
            return False
    
    async def _initialize_configuration(self) -> None:
        """初始化配置"""
        logger.info("初始化系統配置...")
        
        # 載入默認配置
        default_config = {
            'agents': {
                'max_agents': 10,
                'default_personas': ['buffett', 'soros', 'simons', 'dalio', 'graham'],
                'coordination_method': 'hybrid',
                'weight_adjustment_method': 'ensemble'
            },
            'portfolio': {
                'initial_capital': 1000000,
                'max_position_size': 0.2,
                'rebalance_frequency': 'daily',
                'risk_tolerance': 0.15
            },
            'risk': {
                'max_drawdown': 0.2,
                'var_confidence': 0.95,
                'stress_test_frequency': 'weekly'
            },
            'performance': {
                'optimization_frequency': 'hourly',
                'memory_threshold': 0.8,
                'cpu_threshold': 0.7
            }
        }
        
        # 合併用戶配置
        self.config_manager.update_config(default_config)
        
        logger.info("系統配置初始化完成")
    
    async def _initialize_communication(self) -> None:
        """初始化通信系統"""
        logger.info("初始化代理間通信系統...")
        
        self.communication = AgentCommunication(
            max_queue_size=10000,
            message_ttl=3600,
            heartbeat_interval=30
        )
        
        self.communication.start()
        
        # 註冊組件
        self.components['communication'] = ComponentInfo(
            name='AgentCommunication',
            type=ComponentType.COORDINATOR,
            instance=self.communication,
            status='active'
        )
        
        logger.info("代理間通信系統初始化完成")
    
    async def _initialize_multi_agent_system(self) -> None:
        """初始化多代理系統"""
        logger.info("初始化多代理系統...")
        
        # 1. 創建代理管理器
        self.agent_manager = AgentManager()
        
        # 2. 創建決策協調器
        self.decision_coordinator = DecisionCoordinator(
            coordination_method=self.config_manager.get('agents.coordination_method', 'hybrid'),
            min_agents_required=2
        )
        
        # 3. 創建權重調整器
        self.weight_adjuster = DynamicWeightAdjuster(
            adjustment_method=self.config_manager.get('agents.weight_adjustment_method', 'ensemble'),
            performance_window=30
        )
        
        # 4. 創建投資組合分配器
        self.portfolio_allocator = PortfolioAllocator(
            target_volatility=self.config_manager.get('portfolio.risk_tolerance', 0.15),
            max_position_size=self.config_manager.get('portfolio.max_position_size', 0.2)
        )
        
        # 5. 創建默認代理
        await self._create_default_agents()
        
        # 註冊組件
        components_to_register = [
            ('agent_manager', ComponentType.AGENT, self.agent_manager),
            ('decision_coordinator', ComponentType.COORDINATOR, self.decision_coordinator),
            ('weight_adjuster', ComponentType.COORDINATOR, self.weight_adjuster),
            ('portfolio_allocator', ComponentType.PORTFOLIO, self.portfolio_allocator)
        ]
        
        for name, comp_type, instance in components_to_register:
            self.components[name] = ComponentInfo(
                name=name,
                type=comp_type,
                instance=instance,
                status='active'
            )
        
        logger.info("多代理系統初始化完成")
    
    async def _create_default_agents(self) -> None:
        """創建默認代理"""
        default_personas = self.config_manager.get('agents.default_personas', [])
        
        persona_classes = {
            'buffett': BuffettAgent,
            'soros': SorosAgent,
            'simons': SimonsAgent,
            'dalio': DalioAgent,
            'graham': GrahamAgent
        }
        
        for persona_name in default_personas:
            if persona_name in persona_classes:
                try:
                    agent_class = persona_classes[persona_name]
                    agent = agent_class(name=f"{persona_name}_agent")
                    
                    # 註冊代理
                    success = self.agent_manager.register_agent(agent)
                    if success:
                        # 註冊到通信系統
                        self.communication.register_agent(agent.agent_id)
                        logger.info(f"創建代理: {persona_name}")
                    else:
                        logger.warning(f"代理註冊失敗: {persona_name}")
                        
                except Exception as e:
                    logger.error(f"創建代理失敗 {persona_name}: {e}")
    
    async def _initialize_existing_components(self) -> None:
        """初始化現有系統組件"""
        logger.info("初始化現有系統組件...")
        
        try:
            # 1. 初始化LLM策略
            self.llm_strategy = LLMStrategy()
            
            # 2. 初始化投資組合管理器
            self.portfolio_manager = PortfolioManager(
                initial_capital=self.config_manager.get('portfolio.initial_capital', 1000000)
            )
            
            # 3. 初始化風險管理器
            self.risk_manager = RiskManager(
                max_drawdown=self.config_manager.get('risk.max_drawdown', 0.2)
            )
            
            # 註冊組件
            existing_components = [
                ('llm_strategy', ComponentType.LLM, self.llm_strategy),
                ('portfolio_manager', ComponentType.PORTFOLIO, self.portfolio_manager),
                ('risk_manager', ComponentType.RISK, self.risk_manager)
            ]
            
            for name, comp_type, instance in existing_components:
                self.components[name] = ComponentInfo(
                    name=name,
                    type=comp_type,
                    instance=instance,
                    status='active'
                )
            
            logger.info("現有系統組件初始化完成")
            
        except Exception as e:
            logger.error(f"現有系統組件初始化失敗: {e}")
            raise

    async def _initialize_monitoring(self) -> None:
        """初始化監控系統"""
        logger.info("初始化系統監控...")

        try:
            self.monitoring_service = SystemMonitoringService()
            await self.monitoring_service.start()

            # 註冊組件
            self.components['monitoring'] = ComponentInfo(
                name='SystemMonitoringService',
                type=ComponentType.MONITORING,
                instance=self.monitoring_service,
                status='active'
            )

            logger.info("系統監控初始化完成")

        except Exception as e:
            logger.warning(f"監控系統初始化失敗: {e}")

    async def _start_background_tasks(self) -> None:
        """啟動後台任務"""
        logger.info("啟動後台任務...")

        # 獲取事件循環
        self.event_loop = asyncio.get_event_loop()

        # 創建後台任務
        tasks = [
            self._system_health_monitor(),
            self._performance_optimizer(),
            self._metrics_collector(),
            self._error_recovery_monitor()
        ]

        # 啟動任務
        for task_coro in tasks:
            task = self.event_loop.create_task(task_coro)
            self.background_tasks.append(task)

        logger.info(f"啟動了 {len(self.background_tasks)} 個後台任務")

    async def _system_health_check(self) -> bool:
        """系統健康檢查"""
        logger.info("執行系統健康檢查...")

        try:
            health_status = {}

            # 檢查各組件狀態
            for name, component in self.components.items():
                try:
                    if hasattr(component.instance, 'health_check'):
                        health_status[name] = await component.instance.health_check()
                    else:
                        health_status[name] = component.status == 'active'
                except Exception as e:
                    logger.warning(f"組件 {name} 健康檢查失敗: {e}")
                    health_status[name] = False

            # 計算整體健康度
            healthy_components = sum(1 for status in health_status.values() if status)
            total_components = len(health_status)
            health_ratio = healthy_components / total_components if total_components > 0 else 0

            logger.info(f"系統健康度: {health_ratio:.2%} ({healthy_components}/{total_components})")

            # 健康度閾值
            return health_ratio >= 0.8

        except Exception as e:
            logger.error(f"系統健康檢查失敗: {e}")
            return False

    async def _system_health_monitor(self) -> None:
        """系統健康監控任務"""
        while self.system_state in [SystemState.RUNNING, SystemState.PAUSED]:
            try:
                await asyncio.sleep(60)  # 每分鐘檢查一次

                if not await self._system_health_check():
                    logger.warning("系統健康檢查失敗，嘗試恢復...")
                    await self._attempt_system_recovery()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康監控任務錯誤: {e}")

    async def _performance_optimizer(self) -> None:
        """性能優化任務"""
        while self.system_state in [SystemState.RUNNING, SystemState.PAUSED]:
            try:
                await asyncio.sleep(3600)  # 每小時優化一次

                if self.enable_auto_optimization:
                    await self._optimize_system_performance()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"性能優化任務錯誤: {e}")

    async def _metrics_collector(self) -> None:
        """指標收集任務"""
        while self.system_state in [SystemState.RUNNING, SystemState.PAUSED]:
            try:
                await asyncio.sleep(30)  # 每30秒收集一次

                await self._collect_system_metrics()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"指標收集任務錯誤: {e}")

    async def _error_recovery_monitor(self) -> None:
        """錯誤恢復監控任務"""
        while self.system_state in [SystemState.RUNNING, SystemState.PAUSED]:
            try:
                await asyncio.sleep(10)  # 每10秒檢查一次

                await self._check_component_errors()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"錯誤恢復監控任務錯誤: {e}")

    async def _attempt_system_recovery(self) -> None:
        """嘗試系統恢復"""
        logger.info("嘗試系統自動恢復...")

        try:
            # 檢查失效組件
            failed_components = []
            for name, component in self.components.items():
                if component.status != 'active':
                    failed_components.append(name)

            # 嘗試重啟失效組件
            for component_name in failed_components:
                try:
                    await self._restart_component(component_name)
                except Exception as e:
                    logger.error(f"重啟組件 {component_name} 失敗: {e}")

            # 重新檢查系統健康
            if await self._system_health_check():
                logger.info("系統恢復成功")
            else:
                logger.warning("系統恢復失敗，需要人工干預")

        except Exception as e:
            logger.error(f"系統恢復過程失敗: {e}")

    async def _restart_component(self, component_name: str) -> None:
        """重啟組件"""
        logger.info(f"重啟組件: {component_name}")

        if component_name not in self.components:
            logger.error(f"組件 {component_name} 不存在")
            return

        component = self.components[component_name]

        try:
            # 停止組件
            if hasattr(component.instance, 'stop'):
                await component.instance.stop()

            # 重新啟動組件
            if hasattr(component.instance, 'start'):
                await component.instance.start()

            component.status = 'active'
            component.last_update = datetime.now()
            component.error_count = 0

            logger.info(f"組件 {component_name} 重啟成功")

        except Exception as e:
            component.status = 'error'
            component.error_count += 1
            logger.error(f"組件 {component_name} 重啟失敗: {e}")
            raise

    async def _optimize_system_performance(self) -> None:
        """優化系統性能"""
        logger.info("執行系統性能優化...")

        try:
            # 1. 記憶體優化
            await self._optimize_memory_usage()

            # 2. CPU優化
            await self._optimize_cpu_usage()

            # 3. 網絡優化
            await self._optimize_network_usage()

            # 4. 代理權重優化
            if self.weight_adjuster:
                self.weight_adjuster.adjust_weights(force_rebalance=True)

            logger.info("系統性能優化完成")

        except Exception as e:
            logger.error(f"系統性能優化失敗: {e}")

    async def _optimize_memory_usage(self) -> None:
        """優化記憶體使用"""
        import gc
        import psutil

        # 獲取當前記憶體使用
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()

        logger.info(f"當前記憶體使用: {memory_percent:.1f}%")

        # 如果記憶體使用過高，執行清理
        if memory_percent > 80:
            logger.info("記憶體使用過高，執行清理...")

            # 清理組件緩存
            for component in self.components.values():
                if hasattr(component.instance, 'clear_cache'):
                    component.instance.clear_cache()

            # 強制垃圾回收
            gc.collect()

            # 檢查清理效果
            new_memory_percent = psutil.Process().memory_percent()
            logger.info(f"清理後記憶體使用: {new_memory_percent:.1f}%")

    async def _optimize_cpu_usage(self) -> None:
        """優化CPU使用"""
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        logger.info(f"當前CPU使用: {cpu_percent:.1f}%")

        # 如果CPU使用過高，調整線程池大小
        if cpu_percent > 70:
            logger.info("CPU使用過高，調整線程池...")

            # 減少線程池大小
            new_max_workers = max(2, self.max_workers // 2)
            self.executor._max_workers = new_max_workers

            logger.info(f"線程池大小調整為: {new_max_workers}")

    async def _optimize_network_usage(self) -> None:
        """優化網絡使用"""
        # 優化通信系統
        if self.communication:
            # 清理過期消息
            for agent_id in self.communication.get_registered_agents():
                queue_size = self.communication.get_queue_size(agent_id)
                if queue_size > 1000:  # 隊列過大時清理
                    cleared = self.communication.clear_queue(agent_id)
                    logger.info(f"清理代理 {agent_id} 消息隊列: {cleared} 條消息")

    async def _collect_system_metrics(self) -> None:
        """收集系統指標"""
        try:
            import psutil

            # 系統資源指標
            self.system_metrics.memory_usage = psutil.virtual_memory().percent
            self.system_metrics.cpu_usage = psutil.cpu_percent()

            # 代理系統指標
            if self.agent_manager:
                self.system_metrics.total_agents = len(self.agent_manager.agents)
                self.system_metrics.active_agents = len([
                    agent for agent in self.agent_manager.agents.values()
                    if agent.is_active
                ])

            # 決策協調指標
            if self.decision_coordinator:
                stats = self.decision_coordinator.get_coordination_stats()
                self.system_metrics.total_decisions = stats['total_decisions']
                self.system_metrics.coordination_success_rate = stats.get('resolution_rate', 0.0)

            # 投資組合指標
            if self.portfolio_manager:
                portfolio_stats = self.portfolio_manager.get_portfolio_summary()
                self.system_metrics.portfolio_value = portfolio_stats.get('total_value', 0.0)
                self.system_metrics.total_return = portfolio_stats.get('total_return', 0.0)

            # 系統運行時間
            uptime = (datetime.now() - self.start_time).total_seconds()
            self.system_metrics.system_uptime = uptime

            # 錯誤率
            total_errors = sum(comp.error_count for comp in self.components.values())
            total_operations = max(1, self.system_metrics.total_decisions)
            self.system_metrics.error_rate = total_errors / total_operations

            self.system_metrics.last_update = datetime.now()

        except Exception as e:
            logger.error(f"收集系統指標失敗: {e}")

    async def _check_component_errors(self) -> None:
        """檢查組件錯誤"""
        for name, component in self.components.items():
            try:
                # 檢查組件是否有錯誤
                if hasattr(component.instance, 'get_error_count'):
                    error_count = component.instance.get_error_count()
                    if error_count > component.error_count:
                        component.error_count = error_count
                        logger.warning(f"組件 {name} 發生錯誤，錯誤計數: {error_count}")

                        # 如果錯誤過多，嘗試重啟
                        if error_count > 10:
                            await self._restart_component(name)

            except Exception as e:
                logger.error(f"檢查組件 {name} 錯誤失敗: {e}")

    async def execute_trading_decision(
        self,
        symbol: str,
        market_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        執行交易決策的完整流程。

        Args:
            symbol: 交易標的
            market_data: 市場數據

        Returns:
            Dict[str, Any]: 執行結果
        """
        try:
            logger.info(f"開始執行交易決策: {symbol}")

            # 1. 收集代理決策
            agent_decisions = {}
            if self.agent_manager:
                for agent_id, agent in self.agent_manager.agents.items():
                    try:
                        decision = agent.make_decision(
                            data=market_data.get('price_data', pd.DataFrame()),
                            market_context={'symbol': symbol, **market_data}
                        )
                        agent_decisions[agent_id] = decision
                    except Exception as e:
                        logger.warning(f"代理 {agent_id} 決策失敗: {e}")

            # 2. 協調決策
            coordinated_decision = None
            if self.decision_coordinator and agent_decisions:
                coordinated_decision = self.decision_coordinator.coordinate_decisions(
                    agent_decisions, symbol
                )

            # 3. 更新權重
            if self.weight_adjuster and coordinated_decision:
                # 模擬績效更新（實際應用中需要真實績效數據）
                for agent_id in agent_decisions.keys():
                    performance = 0.01  # 簡化的績效模擬
                    self.weight_adjuster.update_performance(agent_id, performance)

            # 4. 投資組合配置
            portfolio_allocation = None
            if self.portfolio_allocator and coordinated_decision:
                coordinated_decisions = {symbol: coordinated_decision}
                portfolio_allocation = self.portfolio_allocator.allocate_portfolio(
                    coordinated_decisions, market_data
                )

            # 5. 風險檢查
            risk_assessment = None
            if self.risk_manager and portfolio_allocation:
                risk_assessment = self.risk_manager.assess_portfolio_risk(
                    portfolio_allocation.target_allocations
                )

            # 6. 執行決策
            execution_result = None
            if portfolio_allocation and (not risk_assessment or risk_assessment.get('approved', True)):
                execution_result = await self._execute_portfolio_allocation(portfolio_allocation)

            # 7. 記錄和監控
            result = {
                'symbol': symbol,
                'agent_decisions': len(agent_decisions),
                'coordinated_decision': coordinated_decision is not None,
                'portfolio_allocation': portfolio_allocation is not None,
                'risk_assessment': risk_assessment,
                'execution_result': execution_result,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"交易決策執行完成: {symbol}")
            return result

        except Exception as e:
            logger.error(f"執行交易決策失敗 {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def _execute_portfolio_allocation(self, allocation: Any) -> Dict[str, Any]:
        """執行投資組合配置"""
        try:
            # 這裡應該調用實際的交易執行系統
            # 目前只是模擬執行

            execution_results = {}
            for symbol, asset_allocation in allocation.target_allocations.items():
                execution_results[symbol] = {
                    'target_weight': asset_allocation.target_weight,
                    'executed_weight': asset_allocation.target_weight,  # 模擬完全執行
                    'execution_price': 100.0,  # 模擬價格
                    'execution_time': datetime.now().isoformat(),
                    'status': 'executed'
                }

            return {
                'total_allocations': len(execution_results),
                'execution_results': execution_results,
                'total_cost': 0.001,  # 模擬交易成本
                'status': 'success'
            }

        except Exception as e:
            logger.error(f"執行投資組合配置失敗: {e}")
            return {
                'status': 'failed',
                'error': str(e)
            }

    def get_system_status(self) -> Dict[str, Any]:
        """獲取系統狀態"""
        return {
            'system_state': self.system_state.value,
            'uptime': (datetime.now() - self.start_time).total_seconds(),
            'components': {
                name: {
                    'type': comp.type.value,
                    'status': comp.status,
                    'last_update': comp.last_update.isoformat(),
                    'error_count': comp.error_count
                }
                for name, comp in self.components.items()
            },
            'metrics': {
                'total_agents': self.system_metrics.total_agents,
                'active_agents': self.system_metrics.active_agents,
                'total_decisions': self.system_metrics.total_decisions,
                'coordination_success_rate': self.system_metrics.coordination_success_rate,
                'portfolio_value': self.system_metrics.portfolio_value,
                'memory_usage': self.system_metrics.memory_usage,
                'cpu_usage': self.system_metrics.cpu_usage,
                'error_rate': self.system_metrics.error_rate
            },
            'performance_stats': self.performance_stats
        }

    def get_component_info(self, component_name: str) -> Optional[Dict[str, Any]]:
        """獲取組件信息"""
        if component_name not in self.components:
            return None

        component = self.components[component_name]
        return {
            'name': component.name,
            'type': component.type.value,
            'status': component.status,
            'last_update': component.last_update.isoformat(),
            'error_count': component.error_count,
            'performance_metrics': component.performance_metrics,
            'metadata': component.metadata
        }

    async def pause_system(self) -> bool:
        """暫停系統"""
        try:
            logger.info("暫停系統...")
            self.system_state = SystemState.PAUSED

            # 暫停各組件
            for component in self.components.values():
                if hasattr(component.instance, 'pause'):
                    await component.instance.pause()

            logger.info("系統已暫停")
            return True

        except Exception as e:
            logger.error(f"暫停系統失敗: {e}")
            return False

    async def resume_system(self) -> bool:
        """恢復系統"""
        try:
            logger.info("恢復系統...")

            # 恢復各組件
            for component in self.components.values():
                if hasattr(component.instance, 'resume'):
                    await component.instance.resume()

            self.system_state = SystemState.RUNNING
            logger.info("系統已恢復")
            return True

        except Exception as e:
            logger.error(f"恢復系統失敗: {e}")
            return False

    async def shutdown_system(self) -> bool:
        """關閉系統"""
        try:
            logger.info("開始關閉系統...")
            self.system_state = SystemState.STOPPING

            # 取消後台任務
            for task in self.background_tasks:
                task.cancel()

            # 等待任務完成
            if self.background_tasks:
                await asyncio.gather(*self.background_tasks, return_exceptions=True)

            # 關閉各組件
            for name, component in self.components.items():
                try:
                    if hasattr(component.instance, 'stop'):
                        await component.instance.stop()
                    component.status = 'stopped'
                    logger.info(f"組件 {name} 已停止")
                except Exception as e:
                    logger.error(f"停止組件 {name} 失敗: {e}")

            # 關閉執行器
            self.executor.shutdown(wait=True)

            self.system_state = SystemState.STOPPED
            logger.info("系統已完全關閉")
            return True

        except Exception as e:
            logger.error(f"關閉系統失敗: {e}")
            self.system_state = SystemState.ERROR
            return False

    def add_error_handler(self, error_type: str, handler: Callable) -> None:
        """添加錯誤處理器"""
        self.error_handlers[error_type] = handler
        logger.info(f"添加錯誤處理器: {error_type}")

    def add_recovery_strategy(self, component_name: str, strategy: Callable) -> None:
        """添加恢復策略"""
        self.recovery_strategies[component_name] = strategy
        logger.info(f"添加恢復策略: {component_name}")

    def __str__(self) -> str:
        """字符串表示"""
        return (f"SystemIntegrator(state={self.system_state.value}, "
                f"components={len(self.components)}, "
                f"uptime={int((datetime.now() - self.start_time).total_seconds())}s)")
