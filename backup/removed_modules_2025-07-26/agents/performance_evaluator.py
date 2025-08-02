# -*- coding: utf-8 -*-
"""
代理績效評估器模組

此模組實現代理績效的評估和分析功能，包括：
- 代理績效指標計算
- 績效排名和比較
- 風險調整收益分析
- 績效報告生成

主要功能：
- 計算各種績效指標（夏普比率、索提諾比率、最大回撤等）
- 提供代理間的績效比較
- 生成詳細的績效報告
- 支持自定義評估指標
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .base import TradingAgent, AgentDecision

# 設定日誌
logger = logging.getLogger(__name__)


class PerformanceMetric(Enum):
    """績效指標枚舉"""
    TOTAL_RETURN = "total_return"
    ANNUALIZED_RETURN = "annualized_return"
    VOLATILITY = "volatility"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    INFORMATION_RATIO = "information_ratio"
    OVERALL_SCORE = "overall_score"


@dataclass
class PerformanceReport:
    """績效報告數據類"""
    agent_id: str
    agent_name: str
    evaluation_period: Tuple[datetime, datetime]
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    information_ratio: float
    total_trades: int
    successful_trades: int
    avg_trade_return: float
    best_trade: float
    worst_trade: float
    avg_holding_period: float
    risk_score: float
    overall_score: float
    rank: Optional[int] = None


class PerformanceEvaluator:
    """
    代理績效評估器。
    
    負責評估和分析交易代理的績效表現。
    
    Attributes:
        risk_free_rate (float): 無風險利率
        benchmark_return (float): 基準收益率
        evaluation_window (int): 評估窗口（天數）
        min_trades (int): 最小交易數量要求
    """
    
    def __init__(
        self,
        risk_free_rate: float = 0.02,  # 年化無風險利率
        benchmark_return: float = 0.08,  # 年化基準收益率
        evaluation_window: int = 30,  # 評估窗口（天數）
        min_trades: int = 5  # 最小交易數量
    ):
        """
        初始化績效評估器。
        
        Args:
            risk_free_rate: 無風險利率（年化）
            benchmark_return: 基準收益率（年化）
            evaluation_window: 評估窗口（天數）
            min_trades: 最小交易數量要求
        """
        self.risk_free_rate = risk_free_rate
        self.benchmark_return = benchmark_return
        self.evaluation_window = evaluation_window
        self.min_trades = min_trades
        
        # 績效緩存
        self._performance_cache: Dict[str, PerformanceReport] = {}
        self._cache_timestamp: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(hours=1)  # 緩存有效期
        
        logger.info("初始化代理績效評估器")
    
    def evaluate_agent(
        self,
        agent: TradingAgent,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> PerformanceReport:
        """
        評估單個代理的績效。
        
        Args:
            agent: 要評估的代理
            start_date: 評估開始日期
            end_date: 評估結束日期
            
        Returns:
            PerformanceReport: 績效報告
        """
        # 檢查緩存
        cache_key = f"{agent.agent_id}_{start_date}_{end_date}"
        if self._is_cache_valid(cache_key):
            return self._performance_cache[cache_key]
        
        # 設定評估期間
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=self.evaluation_window)
        
        # 獲取績效數據
        performance_data = self._get_agent_performance_data(agent, start_date, end_date)
        
        if not performance_data['returns'] or len(performance_data['returns']) < self.min_trades:
            # 數據不足，返回默認報告
            return self._create_default_report(agent, start_date, end_date)
        
        # 計算績效指標
        metrics = self._calculate_performance_metrics(performance_data)
        
        # 創建績效報告
        report = PerformanceReport(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            evaluation_period=(start_date, end_date),
            **metrics
        )
        
        # 緩存結果
        self._performance_cache[cache_key] = report
        self._cache_timestamp[cache_key] = datetime.now()
        
        return report
    
    def _get_agent_performance_data(
        self,
        agent: TradingAgent,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """獲取代理績效數據"""
        # 篩選指定期間的績效記錄
        performance_records = [
            record for record in agent.performance_history
            if start_date <= record['timestamp'] <= end_date
        ]
        
        # 篩選指定期間的決策記錄
        decision_records = [
            decision for decision in agent.decision_history
            if start_date <= decision.timestamp <= end_date
        ]
        
        # 提取收益率數據
        returns = [record['returns'] for record in performance_records]
        benchmark_returns = [record.get('benchmark_returns', 0.0) for record in performance_records]
        
        # 提取決策數據
        decisions = [decision.action for decision in decision_records]
        confidences = [decision.confidence for decision in decision_records]
        
        return {
            'returns': returns,
            'benchmark_returns': benchmark_returns,
            'decisions': decisions,
            'confidences': confidences,
            'performance_records': performance_records,
            'decision_records': decision_records
        }
    
    def _calculate_performance_metrics(self, data: Dict[str, Any]) -> Dict[str, float]:
        """計算績效指標"""
        returns = np.array(data['returns'])
        benchmark_returns = np.array(data['benchmark_returns'])
        
        # 基本統計
        total_return = np.prod(1 + returns) - 1
        avg_return = np.mean(returns)
        volatility = np.std(returns) if len(returns) > 1 else 0.0
        
        # 年化指標
        periods_per_year = 252  # 假設每年252個交易日
        annualized_return = (1 + avg_return) ** periods_per_year - 1
        annualized_volatility = volatility * np.sqrt(periods_per_year)
        
        # 夏普比率
        excess_returns = returns - self.risk_free_rate / periods_per_year
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) > 0 else 0.0
        
        # 索提諾比率（只考慮下行風險）
        downside_returns = returns[returns < 0]
        downside_volatility = np.std(downside_returns) if len(downside_returns) > 0 else 0.0
        sortino_ratio = np.mean(excess_returns) / downside_volatility if downside_volatility > 0 else 0.0
        
        # 最大回撤
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0.0
        
        # 卡爾瑪比率
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0
        
        # 勝率
        win_rate = np.mean(returns > 0) if len(returns) > 0 else 0.0
        
        # 盈虧比
        winning_trades = returns[returns > 0]
        losing_trades = returns[returns < 0]
        avg_win = np.mean(winning_trades) if len(winning_trades) > 0 else 0.0
        avg_loss = np.mean(losing_trades) if len(losing_trades) > 0 else 0.0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
        
        # 信息比率
        excess_returns_vs_benchmark = returns - benchmark_returns
        tracking_error = np.std(excess_returns_vs_benchmark) if len(excess_returns_vs_benchmark) > 1 else 0.0
        information_ratio = np.mean(excess_returns_vs_benchmark) / tracking_error if tracking_error > 0 else 0.0
        
        # 交易統計
        total_trades = len(returns)
        successful_trades = len(winning_trades)
        avg_trade_return = avg_return
        best_trade = np.max(returns) if len(returns) > 0 else 0.0
        worst_trade = np.min(returns) if len(returns) > 0 else 0.0
        
        # 平均持倉期間（假設每個決策對應一個交易日）
        avg_holding_period = 1.0  # 簡化假設
        
        # 風險評分（0-100，越低越好）
        risk_score = min(100, abs(max_drawdown) * 100 + annualized_volatility * 50)
        
        # 綜合評分（0-100，越高越好）
        overall_score = max(0, min(100, 
            sharpe_ratio * 20 + win_rate * 30 + (1 - abs(max_drawdown)) * 25 + 
            min(annualized_return, 0.5) * 50
        ))
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': annualized_volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'information_ratio': information_ratio,
            'total_trades': total_trades,
            'successful_trades': successful_trades,
            'avg_trade_return': avg_trade_return,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'avg_holding_period': avg_holding_period,
            'risk_score': risk_score,
            'overall_score': overall_score
        }
    
    def _create_default_report(
        self,
        agent: TradingAgent,
        start_date: datetime,
        end_date: datetime
    ) -> PerformanceReport:
        """創建默認績效報告（數據不足時）"""
        return PerformanceReport(
            agent_id=agent.agent_id,
            agent_name=agent.name,
            evaluation_period=(start_date, end_date),
            total_return=0.0,
            annualized_return=0.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            information_ratio=0.0,
            total_trades=0,
            successful_trades=0,
            avg_trade_return=0.0,
            best_trade=0.0,
            worst_trade=0.0,
            avg_holding_period=0.0,
            risk_score=50.0,  # 中性風險評分
            overall_score=0.0
        )

    def _is_cache_valid(self, cache_key: str) -> bool:
        """檢查緩存是否有效"""
        if cache_key not in self._cache_timestamp:
            return False

        cache_time = self._cache_timestamp[cache_key]
        return datetime.now() - cache_time < self.cache_ttl

    def evaluate_multiple_agents(
        self,
        agents: List[TradingAgent],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PerformanceReport]:
        """
        評估多個代理的績效。

        Args:
            agents: 要評估的代理列表
            start_date: 評估開始日期
            end_date: 評估結束日期

        Returns:
            List[PerformanceReport]: 績效報告列表（按綜合評分排序）
        """
        reports = []

        for agent in agents:
            try:
                report = self.evaluate_agent(agent, start_date, end_date)
                reports.append(report)
            except Exception as e:
                logger.error(f"評估代理 {agent.name} 失敗: {e}")

        # 按綜合評分排序並設定排名
        reports.sort(key=lambda x: x.overall_score, reverse=True)
        for i, report in enumerate(reports):
            report.rank = i + 1

        return reports

    def get_top_performers(
        self,
        agents: List[TradingAgent],
        metric: PerformanceMetric = PerformanceMetric.OVERALL_SCORE,
        top_n: int = 5,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[PerformanceReport]:
        """
        獲取表現最佳的代理。

        Args:
            agents: 代理列表
            metric: 排序指標
            top_n: 返回的代理數量
            start_date: 評估開始日期
            end_date: 評估結束日期

        Returns:
            List[PerformanceReport]: 表現最佳的代理報告
        """
        reports = self.evaluate_multiple_agents(agents, start_date, end_date)

        # 根據指定指標排序
        if metric == PerformanceMetric.TOTAL_RETURN:
            reports.sort(key=lambda x: x.total_return, reverse=True)
        elif metric == PerformanceMetric.SHARPE_RATIO:
            reports.sort(key=lambda x: x.sharpe_ratio, reverse=True)
        elif metric == PerformanceMetric.WIN_RATE:
            reports.sort(key=lambda x: x.win_rate, reverse=True)
        elif metric == PerformanceMetric.MAX_DRAWDOWN:
            reports.sort(key=lambda x: x.max_drawdown)  # 升序，回撤越小越好
        else:
            reports.sort(key=lambda x: x.overall_score, reverse=True)

        return reports[:top_n]

    def compare_agents(
        self,
        agent1: TradingAgent,
        agent2: TradingAgent,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        比較兩個代理的績效。

        Args:
            agent1: 第一個代理
            agent2: 第二個代理
            start_date: 評估開始日期
            end_date: 評估結束日期

        Returns:
            Dict: 比較結果
        """
        report1 = self.evaluate_agent(agent1, start_date, end_date)
        report2 = self.evaluate_agent(agent2, start_date, end_date)

        comparison = {
            'agent1': {
                'name': report1.agent_name,
                'report': report1
            },
            'agent2': {
                'name': report2.agent_name,
                'report': report2
            },
            'comparison': {
                'total_return_diff': report1.total_return - report2.total_return,
                'sharpe_ratio_diff': report1.sharpe_ratio - report2.sharpe_ratio,
                'win_rate_diff': report1.win_rate - report2.win_rate,
                'max_drawdown_diff': report1.max_drawdown - report2.max_drawdown,
                'overall_score_diff': report1.overall_score - report2.overall_score,
                'better_agent': report1.agent_name if report1.overall_score > report2.overall_score else report2.agent_name
            }
        }

        return comparison

    def generate_performance_summary(
        self,
        agents: List[TradingAgent],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        生成績效摘要。

        Args:
            agents: 代理列表
            start_date: 評估開始日期
            end_date: 評估結束日期

        Returns:
            Dict: 績效摘要
        """
        reports = self.evaluate_multiple_agents(agents, start_date, end_date)

        if not reports:
            return {
                'total_agents': 0,
                'evaluation_period': (start_date, end_date),
                'summary_stats': {},
                'top_performers': [],
                'worst_performers': []
            }

        # 計算統計摘要
        total_returns = [r.total_return for r in reports]
        sharpe_ratios = [r.sharpe_ratio for r in reports]
        win_rates = [r.win_rate for r in reports]
        overall_scores = [r.overall_score for r in reports]

        summary_stats = {
            'avg_total_return': np.mean(total_returns),
            'median_total_return': np.median(total_returns),
            'std_total_return': np.std(total_returns),
            'avg_sharpe_ratio': np.mean(sharpe_ratios),
            'median_sharpe_ratio': np.median(sharpe_ratios),
            'avg_win_rate': np.mean(win_rates),
            'median_win_rate': np.median(win_rates),
            'avg_overall_score': np.mean(overall_scores),
            'median_overall_score': np.median(overall_scores)
        }

        # 表現最佳和最差的代理
        top_performers = reports[:3]  # 前3名
        worst_performers = reports[-3:]  # 後3名

        return {
            'total_agents': len(reports),
            'evaluation_period': (start_date or datetime.now() - timedelta(days=self.evaluation_window),
                                 end_date or datetime.now()),
            'summary_stats': summary_stats,
            'top_performers': [
                {'name': r.agent_name, 'score': r.overall_score, 'rank': r.rank}
                for r in top_performers
            ],
            'worst_performers': [
                {'name': r.agent_name, 'score': r.overall_score, 'rank': r.rank}
                for r in worst_performers
            ],
            'all_reports': reports
        }

    def calculate_portfolio_weights(
        self,
        agents: List[TradingAgent],
        method: str = "score_weighted",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        基於績效計算代理權重。

        Args:
            agents: 代理列表
            method: 權重計算方法 ("score_weighted", "sharpe_weighted", "equal_weighted")
            start_date: 評估開始日期
            end_date: 評估結束日期

        Returns:
            Dict[str, float]: 代理權重字典
        """
        reports = self.evaluate_multiple_agents(agents, start_date, end_date)

        if not reports:
            return {}

        weights = {}

        if method == "equal_weighted":
            # 等權重
            equal_weight = 1.0 / len(reports)
            for report in reports:
                weights[report.agent_id] = equal_weight

        elif method == "sharpe_weighted":
            # 基於夏普比率的權重
            sharpe_ratios = [max(0, r.sharpe_ratio) for r in reports]  # 確保非負
            total_sharpe = sum(sharpe_ratios)

            if total_sharpe > 0:
                for report, sharpe in zip(reports, sharpe_ratios):
                    weights[report.agent_id] = sharpe / total_sharpe
            else:
                # 如果所有夏普比率都<=0，使用等權重
                equal_weight = 1.0 / len(reports)
                for report in reports:
                    weights[report.agent_id] = equal_weight

        else:  # score_weighted
            # 基於綜合評分的權重
            scores = [max(0, r.overall_score) for r in reports]  # 確保非負
            total_score = sum(scores)

            if total_score > 0:
                for report, score in zip(reports, scores):
                    weights[report.agent_id] = score / total_score
            else:
                # 如果所有評分都<=0，使用等權重
                equal_weight = 1.0 / len(reports)
                for report in reports:
                    weights[report.agent_id] = equal_weight

        return weights

    def clear_cache(self) -> None:
        """清空績效緩存"""
        self._performance_cache.clear()
        self._cache_timestamp.clear()
        logger.debug("績效評估緩存已清空")

    def get_cache_stats(self) -> Dict[str, Any]:
        """獲取緩存統計信息"""
        return {
            'cache_size': len(self._performance_cache),
            'cache_hit_rate': 0.0,  # 簡化實現，實際可以追蹤命中率
            'cache_ttl_hours': self.cache_ttl.total_seconds() / 3600
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"PerformanceEvaluator(window={self.evaluation_window}days, min_trades={self.min_trades})"
