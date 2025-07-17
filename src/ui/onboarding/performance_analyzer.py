# -*- coding: utf-8 -*-
"""
績效分析報告

此模組提供詳細的交易績效分析功能，包括：
- 收益率分析
- 風險指標計算
- 績效歸因分析
- 基準比較
- 改進建議生成

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
import json

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    績效分析報告器
    
    提供全面的交易績效分析功能，包括收益率分析、
    風險指標計算和績效歸因分析。
    
    Attributes:
        performance_data (List): 績效資料
        benchmark_data (Dict): 基準資料
        analysis_metrics (Dict): 分析指標
        
    Example:
        >>> analyzer = PerformanceAnalyzer()
        >>> analyzer.add_trade_record('AAPL', 'buy', 150, 160, '2023-01-01', '2023-01-15')
        >>> report = analyzer.generate_performance_report()
    """
    
    def __init__(self):
        """初始化績效分析器"""
        self.performance_data = []
        self.benchmark_data = self._initialize_benchmark_data()
        self.analysis_metrics = self._initialize_analysis_metrics()
        
    def _initialize_benchmark_data(self) -> Dict[str, Any]:
        """
        初始化基準資料
        
        Returns:
            Dict[str, Any]: 基準資料字典
        """
        # 模擬基準指數資料
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        np.random.seed(42)
        
        # 模擬市場指數走勢
        returns = np.random.normal(0.0005, 0.012, len(dates))
        prices = 100 * np.exp(np.cumsum(returns))
        
        return {
            'dates': dates,
            'prices': prices,
            'returns': returns,
            'name': '市場指數',
            'annual_return': np.mean(returns) * 252,
            'annual_volatility': np.std(returns) * np.sqrt(252)
        }
    
    def _initialize_analysis_metrics(self) -> Dict[str, float]:
        """
        初始化分析指標
        
        Returns:
            Dict[str, float]: 分析指標字典
        """
        return {
            'total_return': 0.0,
            'annual_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0
        }
    
    def add_trade_record(self, symbol: str, action: str, entry_price: float,
                        exit_price: float, entry_date: str, exit_date: str,
                        quantity: int = 100, commission: float = 0.001) -> str:
        """
        添加交易記錄
        
        Args:
            symbol: 股票代碼
            action: 交易動作 ('buy', 'sell')
            entry_price: 進場價格
            exit_price: 出場價格
            entry_date: 進場日期
            exit_date: 出場日期
            quantity: 交易數量
            commission: 手續費率
            
        Returns:
            str: 交易記錄ID
        """
        trade_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 計算交易結果
        if action == 'buy':
            gross_return = (exit_price - entry_price) / entry_price
        else:  # sell (做空)
            gross_return = (entry_price - exit_price) / entry_price
        
        # 扣除手續費
        total_commission = commission * 2  # 進場和出場
        net_return = gross_return - total_commission
        
        # 計算持有期間
        entry_dt = pd.to_datetime(entry_date)
        exit_dt = pd.to_datetime(exit_date)
        holding_days = (exit_dt - entry_dt).days
        
        trade_record = {
            'id': trade_id,
            'symbol': symbol,
            'action': action,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'entry_date': entry_date,
            'exit_date': exit_date,
            'quantity': quantity,
            'commission': commission,
            'gross_return': gross_return,
            'net_return': net_return,
            'holding_days': holding_days,
            'profit_loss': net_return * entry_price * quantity,
            'is_winner': net_return > 0,
            'created_at': datetime.now().isoformat()
        }
        
        self.performance_data.append(trade_record)
        logger.info("交易記錄已添加: %s - %s %s", trade_id, action, symbol)
        
        return trade_id
    
    def calculate_performance_metrics(self) -> Dict[str, float]:
        """
        計算績效指標
        
        Returns:
            Dict[str, float]: 績效指標
        """
        if not self.performance_data:
            return self.analysis_metrics
        
        df = pd.DataFrame(self.performance_data)
        
        # 基本統計
        total_trades = len(df)
        winning_trades = len(df[df['is_winner']])
        losing_trades = total_trades - winning_trades
        
        # 收益率統計
        total_return = df['net_return'].sum()
        avg_return = df['net_return'].mean()
        
        # 勝率
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # 平均盈虧
        avg_win = df[df['is_winner']]['net_return'].mean() if winning_trades > 0 else 0
        avg_loss = df[~df['is_winner']]['net_return'].mean() if losing_trades > 0 else 0
        
        # 獲利因子
        total_wins = df[df['is_winner']]['net_return'].sum()
        total_losses = abs(df[~df['is_winner']]['net_return'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # 波動率（假設每日交易）
        volatility = df['net_return'].std() * np.sqrt(252) if len(df) > 1 else 0
        
        # 夏普比率（假設無風險利率2%）
        risk_free_rate = 0.02
        excess_return = avg_return * 252 - risk_free_rate
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0
        
        # 最大回撤
        cumulative_returns = (1 + df['net_return']).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
        
        # 年化收益率
        if len(df) > 0:
            first_date = pd.to_datetime(df['entry_date'].min())
            last_date = pd.to_datetime(df['exit_date'].max())
            days = (last_date - first_date).days
            annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
        else:
            annual_return = 0
        
        metrics = {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades
        }
        
        self.analysis_metrics.update(metrics)
        return metrics
    
    def generate_performance_report(self, period_days: int = 90) -> Dict[str, Any]:
        """
        生成績效報告
        
        Args:
            period_days: 報告期間（天數）
            
        Returns:
            Dict[str, Any]: 績效報告
        """
        if not self.performance_data:
            return {'message': '尚無交易記錄可供分析'}
        
        cutoff_date = datetime.now() - timedelta(days=period_days)
        
        # 篩選期間內的交易
        period_trades = [
            trade for trade in self.performance_data
            if pd.to_datetime(trade['exit_date']) >= cutoff_date
        ]
        
        if not period_trades:
            return {'message': f'過去 {period_days} 天內無交易記錄'}
        
        df = pd.DataFrame(period_trades)
        
        # 計算績效指標
        metrics = self.calculate_performance_metrics()
        
        # 基準比較
        benchmark_comparison = self._compare_with_benchmark(df)
        
        # 交易分析
        trade_analysis = self._analyze_trades(df)
        
        # 風險分析
        risk_analysis = self._analyze_risk(df)
        
        # 改進建議
        improvement_suggestions = self._generate_improvement_suggestions(metrics, df)
        
        return {
            'period_days': period_days,
            'metrics': metrics,
            'benchmark_comparison': benchmark_comparison,
            'trade_analysis': trade_analysis,
            'risk_analysis': risk_analysis,
            'improvement_suggestions': improvement_suggestions,
            'generated_at': datetime.now().isoformat()
        }
    
    def _compare_with_benchmark(self, df: pd.DataFrame) -> Dict[str, Any]:
        """與基準比較"""
        if df.empty:
            return {}
        
        # 計算投資組合收益
        portfolio_return = df['net_return'].sum()
        
        # 計算同期基準收益（簡化計算）
        start_date = pd.to_datetime(df['entry_date'].min())
        end_date = pd.to_datetime(df['exit_date'].max())
        
        benchmark_return = self.benchmark_data['annual_return'] * \
                          ((end_date - start_date).days / 365)
        
        # 超額收益
        excess_return = portfolio_return - benchmark_return
        
        return {
            'portfolio_return': portfolio_return,
            'benchmark_return': benchmark_return,
            'excess_return': excess_return,
            'outperformance': excess_return > 0
        }
    
    def _analyze_trades(self, df: pd.DataFrame) -> Dict[str, Any]:
        """交易分析"""
        # 按股票分組分析
        symbol_performance = df.groupby('symbol').agg({
            'net_return': ['count', 'sum', 'mean'],
            'is_winner': 'mean'
        }).round(4)
        
        # 按月份分析
        df['month'] = pd.to_datetime(df['exit_date']).dt.to_period('M')
        monthly_performance = df.groupby('month').agg({
            'net_return': ['count', 'sum', 'mean']
        }).round(4)
        
        # 持有期間分析
        holding_analysis = {
            'avg_holding_days': df['holding_days'].mean(),
            'median_holding_days': df['holding_days'].median(),
            'max_holding_days': df['holding_days'].max(),
            'min_holding_days': df['holding_days'].min()
        }
        
        return {
            'symbol_performance': symbol_performance.to_dict(),
            'monthly_performance': monthly_performance.to_dict(),
            'holding_analysis': holding_analysis
        }
    
    def _analyze_risk(self, df: pd.DataFrame) -> Dict[str, Any]:
        """風險分析"""
        returns = df['net_return']
        
        # VaR 計算（95% 信心水平）
        var_95 = returns.quantile(0.05)
        
        # 條件風險價值 (CVaR)
        cvar_95 = returns[returns <= var_95].mean()
        
        # 下檔風險
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() if len(downside_returns) > 0 else 0
        
        # 最大連續虧損
        consecutive_losses = self._calculate_consecutive_losses(df)
        
        return {
            'var_95': var_95,
            'cvar_95': cvar_95,
            'downside_deviation': downside_deviation,
            'max_consecutive_losses': consecutive_losses
        }
    
    def _calculate_consecutive_losses(self, df: pd.DataFrame) -> int:
        """計算最大連續虧損次數"""
        losses = (~df['is_winner']).astype(int)
        max_consecutive = 0
        current_consecutive = 0
        
        for loss in losses:
            if loss:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    def _generate_improvement_suggestions(self, metrics: Dict[str, float], 
                                        df: pd.DataFrame) -> List[str]:
        """生成改進建議"""
        suggestions = []
        
        # 勝率分析
        if metrics.get('win_rate', 0) < 0.5:
            suggestions.append("勝率偏低，建議改進進場時機選擇和分析方法")
        
        # 獲利因子分析
        if metrics.get('profit_factor', 0) < 1.5:
            suggestions.append("獲利因子偏低，建議優化停利停損策略")
        
        # 夏普比率分析
        if metrics.get('sharpe_ratio', 0) < 1.0:
            suggestions.append("風險調整後收益偏低，建議改善風險管理")
        
        # 最大回撤分析
        if metrics.get('max_drawdown', 0) > 0.15:
            suggestions.append("最大回撤過大，建議加強部位控制和風險管理")
        
        # 交易頻率分析
        avg_holding = df['holding_days'].mean() if not df.empty else 0
        if avg_holding < 3:
            suggestions.append("持有期間過短，可能存在過度交易問題")
        elif avg_holding > 60:
            suggestions.append("持有期間過長，建議更積極的部位管理")
        
        # 分散程度分析
        unique_symbols = df['symbol'].nunique() if not df.empty else 0
        total_trades = len(df) if not df.empty else 0
        if unique_symbols < 3 and total_trades > 10:
            suggestions.append("投資標的過於集中，建議增加分散投資")
        
        if not suggestions:
            suggestions.append("整體表現良好，繼續保持當前策略並持續優化")
        
        return suggestions
    
    def create_performance_charts(self) -> Dict[str, go.Figure]:
        """創建績效圖表"""
        if not self.performance_data:
            return {}
        
        df = pd.DataFrame(self.performance_data)
        
        charts = {}
        
        # 1. 累積收益圖
        df_sorted = df.sort_values('exit_date')
        df_sorted['cumulative_return'] = (1 + df_sorted['net_return']).cumprod() - 1
        
        fig_cumulative = go.Figure()
        fig_cumulative.add_trace(go.Scatter(
            x=pd.to_datetime(df_sorted['exit_date']),
            y=df_sorted['cumulative_return'] * 100,
            mode='lines',
            name='投資組合',
            line=dict(color='blue', width=2)
        ))
        
        fig_cumulative.update_layout(
            title='累積收益率',
            xaxis_title='日期',
            yaxis_title='累積收益率 (%)',
            height=400
        )
        
        charts['cumulative_return'] = fig_cumulative
        
        # 2. 收益分布圖
        fig_distribution = go.Figure()
        fig_distribution.add_trace(go.Histogram(
            x=df['net_return'] * 100,
            nbinsx=20,
            name='收益分布',
            marker_color='lightblue'
        ))
        
        fig_distribution.update_layout(
            title='交易收益分布',
            xaxis_title='收益率 (%)',
            yaxis_title='頻率',
            height=400
        )
        
        charts['return_distribution'] = fig_distribution
        
        # 3. 月度績效圖
        df['month'] = pd.to_datetime(df['exit_date']).dt.to_period('M')
        monthly_returns = df.groupby('month')['net_return'].sum() * 100
        
        fig_monthly = go.Figure()
        fig_monthly.add_trace(go.Bar(
            x=[str(m) for m in monthly_returns.index],
            y=monthly_returns.values,
            name='月度收益',
            marker_color=['green' if x > 0 else 'red' for x in monthly_returns.values]
        ))
        
        fig_monthly.update_layout(
            title='月度績效',
            xaxis_title='月份',
            yaxis_title='收益率 (%)',
            height=400
        )
        
        charts['monthly_performance'] = fig_monthly
        
        return charts


def show_performance_analyzer() -> None:
    """
    顯示績效分析報告頁面
    
    提供詳細的交易績效分析功能，包括收益率分析、
    風險指標計算和績效歸因分析。
    
    Side Effects:
        - 在 Streamlit 界面顯示績效分析器
        - 提供績效分析和報告功能
    """
    st.title("📊 績效分析報告")
    st.markdown("深入分析您的交易績效，發現改進機會！")
    
    # 初始化績效分析器
    if 'performance_analyzer' not in st.session_state:
        st.session_state.performance_analyzer = PerformanceAnalyzer()
    
    analyzer = st.session_state.performance_analyzer
    
    # 主要功能區域
    tab1, tab2, tab3, tab4 = st.tabs(["添加交易", "績效指標", "詳細分析", "圖表展示"])
    
    with tab1:
        st.subheader("📝 添加交易記錄")
        
        with st.form("trade_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                symbol = st.text_input("股票代碼", placeholder="例如: AAPL")
                action = st.selectbox("交易動作", ["buy", "sell"],
                                    format_func=lambda x: {"buy": "買入", "sell": "賣出"}[x])
                entry_price = st.number_input("進場價格", min_value=0.01, value=100.0, step=0.01)
                exit_price = st.number_input("出場價格", min_value=0.01, value=105.0, step=0.01)
            
            with col2:
                entry_date = st.date_input("進場日期")
                exit_date = st.date_input("出場日期")
                quantity = st.number_input("交易數量", min_value=1, value=100, step=1)
                commission = st.number_input("手續費率", min_value=0.0, max_value=0.01, value=0.001, step=0.0001, format="%.4f")
            
            if st.form_submit_button("添加交易記錄"):
                if symbol and entry_date <= exit_date:
                    trade_id = analyzer.add_trade_record(
                        symbol=symbol,
                        action=action,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        entry_date=str(entry_date),
                        exit_date=str(exit_date),
                        quantity=quantity,
                        commission=commission
                    )
                    st.success(f"✅ 交易記錄已添加！ID: {trade_id}")
                else:
                    st.error("請填寫完整資訊，且出場日期不能早於進場日期")
    
    with tab2:
        st.subheader("📈 績效指標")
        
        if analyzer.performance_data:
            metrics = analyzer.calculate_performance_metrics()
            
            # 主要指標
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("總收益率", f"{metrics['total_return']:.2%}")
                st.metric("勝率", f"{metrics['win_rate']:.1%}")
            
            with col2:
                st.metric("年化收益率", f"{metrics['annual_return']:.2%}")
                st.metric("獲利因子", f"{metrics['profit_factor']:.2f}")
            
            with col3:
                st.metric("波動率", f"{metrics['volatility']:.2%}")
                st.metric("夏普比率", f"{metrics['sharpe_ratio']:.2f}")
            
            with col4:
                st.metric("最大回撤", f"{metrics['max_drawdown']:.2%}")
                st.metric("總交易數", f"{metrics['total_trades']}")
            
            # 詳細統計
            st.subheader("📋 詳細統計")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**交易統計**")
                st.write(f"獲利交易: {metrics['winning_trades']}")
                st.write(f"虧損交易: {metrics['losing_trades']}")
                st.write(f"平均獲利: {metrics['avg_win']:.2%}")
                st.write(f"平均虧損: {metrics['avg_loss']:.2%}")
            
            with col2:
                st.write("**風險指標**")
                st.write(f"總收益率: {metrics['total_return']:.2%}")
                st.write(f"年化波動率: {metrics['volatility']:.2%}")
                st.write(f"最大回撤: {metrics['max_drawdown']:.2%}")
                st.write(f"夏普比率: {metrics['sharpe_ratio']:.2f}")
        
        else:
            st.info("尚無交易記錄，請先添加一些交易")
    
    with tab3:
        st.subheader("🔍 詳細分析")
        
        period_days = st.selectbox("分析期間", [30, 60, 90, 180, 365], index=2)
        
        if st.button("生成分析報告"):
            report = analyzer.generate_performance_report(period_days)
            
            if 'message' in report:
                st.info(report['message'])
            else:
                # 基準比較
                if 'benchmark_comparison' in report:
                    st.subheader("📊 基準比較")
                    benchmark = report['benchmark_comparison']
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("投資組合收益", f"{benchmark['portfolio_return']:.2%}")
                    with col2:
                        st.metric("基準收益", f"{benchmark['benchmark_return']:.2%}")
                    with col3:
                        st.metric("超額收益", f"{benchmark['excess_return']:.2%}")
                    
                    if benchmark['outperformance']:
                        st.success("✅ 跑贏基準指數")
                    else:
                        st.warning("⚠️ 落後基準指數")
                
                # 改進建議
                if 'improvement_suggestions' in report:
                    st.subheader("💡 改進建議")
                    for suggestion in report['improvement_suggestions']:
                        st.write(f"• {suggestion}")
    
    with tab4:
        st.subheader("📈 圖表展示")
        
        if analyzer.performance_data:
            charts = analyzer.create_performance_charts()
            
            if charts:
                # 累積收益圖
                if 'cumulative_return' in charts:
                    st.plotly_chart(charts['cumulative_return'], use_container_width=True)
                
                # 收益分布和月度績效
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'return_distribution' in charts:
                        st.plotly_chart(charts['return_distribution'], use_container_width=True)
                
                with col2:
                    if 'monthly_performance' in charts:
                        st.plotly_chart(charts['monthly_performance'], use_container_width=True)
        
        else:
            st.info("尚無交易記錄，請先添加一些交易以查看圖表")
    
    # 側邊欄：快速統計
    with st.sidebar:
        st.subheader("📊 快速統計")
        
        if analyzer.performance_data:
            total_trades = len(analyzer.performance_data)
            recent_trades = [t for t in analyzer.performance_data 
                           if pd.to_datetime(t['exit_date']) >= datetime.now() - timedelta(days=30)]
            
            st.metric("總交易數", total_trades)
            st.metric("本月交易", len(recent_trades))
            
            if recent_trades:
                recent_return = sum(t['net_return'] for t in recent_trades)
                st.metric("本月收益", f"{recent_return:.2%}")
        
        else:
            st.info("尚無交易記錄")
        
        # 快速操作
        st.subheader("⚡ 快速操作")
        
        if st.button("📥 匯入範例資料"):
            # 添加一些範例交易記錄
            example_trades = [
                ('AAPL', 'buy', 150, 155, '2023-11-01', '2023-11-15'),
                ('GOOGL', 'buy', 120, 118, '2023-11-05', '2023-11-20'),
                ('MSFT', 'buy', 300, 310, '2023-11-10', '2023-11-25'),
                ('TSLA', 'buy', 200, 195, '2023-11-15', '2023-11-30'),
                ('AMZN', 'buy', 140, 145, '2023-11-20', '2023-12-05')
            ]
            
            for trade in example_trades:
                analyzer.add_trade_record(*trade)
            
            st.success("✅ 範例資料已匯入")
            st.rerun()
        
        if st.button("🗑️ 清除所有資料"):
            analyzer.performance_data = []
            st.success("✅ 資料已清除")
            st.rerun()
