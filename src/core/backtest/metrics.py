"""
回測績效指標計算模組

此模組提供完整的回測績效分析功能，包括：
- 收益率指標
- 風險指標
- 風險調整指標
- 交易統計
- 基準比較
"""

import logging
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BacktestMetrics:
    """回測績效指標類
    
    包含所有重要的績效指標和統計數據。
    """
    
    # 基本指標
    total_return: float
    annualized_return: float
    volatility: float
    max_drawdown: float
    
    # 風險調整指標
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    information_ratio: float
    
    # 交易統計
    total_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # 時間統計
    trading_days: int
    start_date: str
    end_date: str
    
    # 基準比較
    benchmark_return: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    tracking_error: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'basic_metrics': {
                'total_return': self.total_return,
                'annualized_return': self.annualized_return,
                'volatility': self.volatility,
                'max_drawdown': self.max_drawdown,
            },
            'risk_adjusted_metrics': {
                'sharpe_ratio': self.sharpe_ratio,
                'sortino_ratio': self.sortino_ratio,
                'calmar_ratio': self.calmar_ratio,
                'information_ratio': self.information_ratio,
            },
            'trading_statistics': {
                'total_trades': self.total_trades,
                'win_rate': self.win_rate,
                'avg_win': self.avg_win,
                'avg_loss': self.avg_loss,
                'profit_factor': self.profit_factor,
            },
            'time_statistics': {
                'trading_days': self.trading_days,
                'start_date': self.start_date,
                'end_date': self.end_date,
            },
            'benchmark_comparison': {
                'benchmark_return': self.benchmark_return,
                'alpha': self.alpha,
                'beta': self.beta,
                'tracking_error': self.tracking_error,
            }
        }


def calculate_performance_metrics(
    backtest_results: Dict[str, Any],
    config: Any,
    benchmark_data: Optional[pd.DataFrame] = None
) -> BacktestMetrics:
    """計算回測績效指標
    
    Args:
        backtest_results: 回測結果
        config: 回測配置
        benchmark_data: 基準數據
        
    Returns:
        BacktestMetrics: 績效指標
        
    Raises:
        ValueError: 當輸入數據無效時
    """
    try:
        # 提取數據
        summary = backtest_results.get('summary', {})
        daily_values = backtest_results.get('daily_values', pd.DataFrame())
        daily_returns = backtest_results.get('daily_returns', pd.DataFrame())
        trades = backtest_results.get('trades', pd.DataFrame())
        
        # 基本指標
        total_return = summary.get('total_return', 0)
        annualized_return = summary.get('annualized_return', 0)
        max_drawdown = summary.get('max_drawdown', 0)
        
        # 計算波動率
        volatility = _calculate_volatility(daily_returns)
        
        # 風險調整指標
        sharpe_ratio = _calculate_sharpe_ratio(daily_returns)
        sortino_ratio = _calculate_sortino_ratio(daily_returns)
        calmar_ratio = _calculate_calmar_ratio(annualized_return, max_drawdown)
        information_ratio = _calculate_information_ratio(daily_returns, benchmark_data)
        
        # 交易統計
        trading_stats = _calculate_trading_statistics(trades)
        
        # 時間統計
        trading_days = len(daily_values) if not daily_values.empty else 0
        start_date = config.start_date.strftime('%Y-%m-%d') if hasattr(config, 'start_date') else ''
        end_date = config.end_date.strftime('%Y-%m-%d') if hasattr(config, 'end_date') else ''
        
        # 基準比較
        benchmark_metrics = _calculate_benchmark_comparison(daily_returns, benchmark_data)
        
        return BacktestMetrics(
            # 基本指標
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            max_drawdown=max_drawdown,
            
            # 風險調整指標
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            information_ratio=information_ratio,
            
            # 交易統計
            total_trades=trading_stats['total_trades'],
            win_rate=trading_stats['win_rate'],
            avg_win=trading_stats['avg_win'],
            avg_loss=trading_stats['avg_loss'],
            profit_factor=trading_stats['profit_factor'],
            
            # 時間統計
            trading_days=trading_days,
            start_date=start_date,
            end_date=end_date,
            
            # 基準比較
            benchmark_return=benchmark_metrics.get('benchmark_return'),
            alpha=benchmark_metrics.get('alpha'),
            beta=benchmark_metrics.get('beta'),
            tracking_error=benchmark_metrics.get('tracking_error'),
        )
        
    except Exception as e:
        logger.error("計算績效指標失敗: %s", e, exc_info=True)
        raise ValueError(f"計算績效指標失敗: {e}") from e


def _calculate_volatility(daily_returns: pd.DataFrame) -> float:
    """計算年化波動率"""
    if daily_returns.empty or 'return' not in daily_returns.columns:
        return 0.0
    
    returns = daily_returns['return'].dropna()
    if len(returns) < 2:
        return 0.0
    
    return float(returns.std() * np.sqrt(252))


def _calculate_sharpe_ratio(daily_returns: pd.DataFrame, risk_free_rate: float = 0.02) -> float:
    """計算夏普比率"""
    if daily_returns.empty or 'return' not in daily_returns.columns:
        return 0.0
    
    returns = daily_returns['return'].dropna()
    if len(returns) < 2:
        return 0.0
    
    excess_returns = returns - risk_free_rate / 252
    return float(excess_returns.mean() / excess_returns.std() * np.sqrt(252)) if excess_returns.std() > 0 else 0.0


def _calculate_sortino_ratio(daily_returns: pd.DataFrame, risk_free_rate: float = 0.02) -> float:
    """計算索提諾比率"""
    if daily_returns.empty or 'return' not in daily_returns.columns:
        return 0.0
    
    returns = daily_returns['return'].dropna()
    if len(returns) < 2:
        return 0.0
    
    excess_returns = returns - risk_free_rate / 252
    downside_returns = excess_returns[excess_returns < 0]
    
    if len(downside_returns) == 0:
        return float('inf') if excess_returns.mean() > 0 else 0.0
    
    downside_deviation = np.sqrt((downside_returns ** 2).mean())
    return float(excess_returns.mean() / downside_deviation * np.sqrt(252)) if downside_deviation > 0 else 0.0


def _calculate_calmar_ratio(annualized_return: float, max_drawdown: float) -> float:
    """計算卡瑪比率"""
    if max_drawdown == 0:
        return float('inf') if annualized_return > 0 else 0.0
    
    return float(annualized_return / abs(max_drawdown))


def _calculate_information_ratio(
    daily_returns: pd.DataFrame,
    benchmark_data: Optional[pd.DataFrame]
) -> float:
    """計算信息比率"""
    if daily_returns.empty or benchmark_data is None or benchmark_data.empty:
        return 0.0
    
    if 'return' not in daily_returns.columns:
        return 0.0
    
    # 這裡需要實現基準收益率的計算邏輯
    # 簡化實現，實際應該根據基準數據計算
    return 0.0


def _calculate_trading_statistics(trades: pd.DataFrame) -> Dict[str, Any]:
    """計算交易統計"""
    if trades.empty:
        return {
            'total_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
        }
    
    # 計算每筆交易的盈虧
    if 'value' in trades.columns:
        # 按股票分組計算盈虧
        trade_pnl = []
        for symbol in trades['symbol'].unique():
            symbol_trades = trades[trades['symbol'] == symbol].sort_values('date')
            position = 0
            entry_price = 0
            
            for _, trade in symbol_trades.iterrows():
                if position == 0:  # 開倉
                    position = trade['shares']
                    entry_price = trade['price']
                elif (position > 0 and trade['shares'] < 0) or (position < 0 and trade['shares'] > 0):  # 平倉
                    pnl = (trade['price'] - entry_price) * min(abs(position), abs(trade['shares']))
                    if position < 0:
                        pnl = -pnl
                    trade_pnl.append(pnl)
                    position += trade['shares']
                    if position == 0:
                        entry_price = 0
        
        if not trade_pnl:
            return {
                'total_trades': len(trades),
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
            }
        
        trade_pnl = np.array(trade_pnl)
        winning_trades = trade_pnl[trade_pnl > 0]
        losing_trades = trade_pnl[trade_pnl < 0]
        
        win_rate = len(winning_trades) / len(trade_pnl) if len(trade_pnl) > 0 else 0
        avg_win = winning_trades.mean() if len(winning_trades) > 0 else 0
        avg_loss = abs(losing_trades.mean()) if len(losing_trades) > 0 else 0
        
        gross_profit = winning_trades.sum() if len(winning_trades) > 0 else 0
        gross_loss = abs(losing_trades.sum()) if len(losing_trades) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
        
        return {
            'total_trades': len(trade_pnl),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(profit_factor),
        }
    
    return {
        'total_trades': len(trades),
        'win_rate': 0.0,
        'avg_win': 0.0,
        'avg_loss': 0.0,
        'profit_factor': 0.0,
    }


def _calculate_benchmark_comparison(
    daily_returns: pd.DataFrame,
    benchmark_data: Optional[pd.DataFrame]
) -> Dict[str, Optional[float]]:
    """計算基準比較指標"""
    if daily_returns.empty or benchmark_data is None or benchmark_data.empty:
        return {
            'benchmark_return': None,
            'alpha': None,
            'beta': None,
            'tracking_error': None,
        }
    
    # 這裡需要實現基準比較的詳細邏輯
    # 簡化實現，實際應該根據基準數據計算
    return {
        'benchmark_return': None,
        'alpha': None,
        'beta': None,
        'tracking_error': None,
    }


def generate_performance_report(metrics: BacktestMetrics) -> str:
    """生成績效報告
    
    Args:
        metrics: 績效指標
        
    Returns:
        str: 格式化的績效報告
    """
    report = f"""
# 回測績效報告

## 基本指標
- 總收益率: {metrics.total_return:.2%}
- 年化收益率: {metrics.annualized_return:.2%}
- 年化波動率: {metrics.volatility:.2%}
- 最大回撤: {metrics.max_drawdown:.2%}

## 風險調整指標
- 夏普比率: {metrics.sharpe_ratio:.3f}
- 索提諾比率: {metrics.sortino_ratio:.3f}
- 卡瑪比率: {metrics.calmar_ratio:.3f}
- 信息比率: {metrics.information_ratio:.3f}

## 交易統計
- 總交易次數: {metrics.total_trades}
- 勝率: {metrics.win_rate:.2%}
- 平均盈利: {metrics.avg_win:.2f}
- 平均虧損: {metrics.avg_loss:.2f}
- 盈虧比: {metrics.profit_factor:.2f}

## 時間統計
- 交易天數: {metrics.trading_days}
- 開始日期: {metrics.start_date}
- 結束日期: {metrics.end_date}
"""
    
    if metrics.benchmark_return is not None:
        report += f"""
## 基準比較
- 基準收益率: {metrics.benchmark_return:.2%}
- Alpha: {metrics.alpha:.3f}
- Beta: {metrics.beta:.3f}
- 追蹤誤差: {metrics.tracking_error:.2%}
"""
    
    return report
