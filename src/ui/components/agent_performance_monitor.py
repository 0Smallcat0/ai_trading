# -*- coding: utf-8 -*-
"""
代理績效監控面板組件

此模組提供實時績效追蹤和可視化分析，包括：
- 實時績效指標監控
- 交互式圖表和可視化
- 代理排名和績效對比
- 歷史績效回測和分析

主要功能：
- 多維度績效指標
- 實時數據更新
- 交互式圖表
- 績效對比分析
- 風險收益分析
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# 設定日誌
logger = logging.getLogger(__name__)


class AgentPerformanceMonitor:
    """
    代理績效監控面板類
    
    提供完整的代理績效監控和分析功能。
    """
    
    def __init__(self):
        """初始化績效監控面板"""
        self.performance_metrics = [
            'total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate',
            'volatility', 'alpha', 'beta', 'information_ratio'
        ]
        
        self.metric_names = {
            'total_return': '總收益率',
            'sharpe_ratio': '夏普比率',
            'max_drawdown': '最大回撤',
            'win_rate': '勝率',
            'volatility': '波動率',
            'alpha': 'Alpha',
            'beta': 'Beta',
            'information_ratio': '信息比率'
        }
    
    def render(self):
        """渲染績效監控面板"""
        st.title("📈 代理績效監控中心")
        st.markdown("---")
        
        # 創建標籤頁
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 實時監控", 
            "📈 績效對比", 
            "🎯 風險分析", 
            "📋 詳細報告"
        ])
        
        with tab1:
            self._render_realtime_monitoring()
        
        with tab2:
            self._render_performance_comparison()
        
        with tab3:
            self._render_risk_analysis()
        
        with tab4:
            self._render_detailed_reports()
    
    def _render_realtime_monitoring(self):
        """渲染實時監控"""
        st.subheader("📊 實時績效監控")
        
        # 獲取代理績效數據
        performance_data = self._get_performance_data()
        
        if not performance_data:
            st.info("🔍 暫無績效數據。請確保代理正在運行並產生交易記錄。")
            return
        
        # 總體績效指標
        st.subheader("總體績效")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_return = np.mean([data['total_return'] for data in performance_data.values()])
            st.metric("平均總收益率", f"{total_return:.2%}")
        
        with col2:
            avg_sharpe = np.mean([data['sharpe_ratio'] for data in performance_data.values()])
            st.metric("平均夏普比率", f"{avg_sharpe:.2f}")
        
        with col3:
            max_drawdown = np.max([data['max_drawdown'] for data in performance_data.values()])
            st.metric("最大回撤", f"{max_drawdown:.2%}", delta_color="inverse")
        
        with col4:
            avg_win_rate = np.mean([data['win_rate'] for data in performance_data.values()])
            st.metric("平均勝率", f"{avg_win_rate:.1%}")
        
        # 代理排名
        st.subheader("代理排名")
        
        # 排名指標選擇
        ranking_metric = st.selectbox(
            "排名依據",
            options=list(self.metric_names.keys()),
            format_func=lambda x: self.metric_names[x]
        )
        
        # 創建排名表格
        ranking_data = []
        for agent_id, data in performance_data.items():
            ranking_data.append({
                '排名': 0,  # 將在後面計算
                '代理名稱': data['name'],
                '投資風格': data['style'],
                self.metric_names[ranking_metric]: data[ranking_metric],
                '狀態': data['status']
            })
        
        # 排序
        ranking_df = pd.DataFrame(ranking_data)
        if ranking_metric in ['max_drawdown']:  # 越小越好的指標
            ranking_df = ranking_df.sort_values(self.metric_names[ranking_metric])
        else:  # 越大越好的指標
            ranking_df = ranking_df.sort_values(self.metric_names[ranking_metric], ascending=False)
        
        ranking_df['排名'] = range(1, len(ranking_df) + 1)
        
        # 格式化數值
        if ranking_metric in ['total_return', 'max_drawdown', 'win_rate', 'volatility']:
            ranking_df[self.metric_names[ranking_metric]] = ranking_df[self.metric_names[ranking_metric]].apply(lambda x: f"{x:.2%}")
        else:
            ranking_df[self.metric_names[ranking_metric]] = ranking_df[self.metric_names[ranking_metric]].apply(lambda x: f"{x:.2f}")
        
        st.dataframe(ranking_df, use_container_width=True, hide_index=True)
        
        # 實時績效圖表
        self._render_realtime_charts(performance_data)
    
    def _render_performance_comparison(self):
        """渲染績效對比"""
        st.subheader("📈 代理績效對比")
        
        performance_data = self._get_performance_data()
        
        if not performance_data:
            st.info("暫無績效數據。")
            return
        
        # 代理選擇
        agent_ids = list(performance_data.keys())
        selected_agents = st.multiselect(
            "選擇要對比的代理",
            options=agent_ids,
            default=agent_ids[:min(5, len(agent_ids))],  # 默認選擇前5個
            format_func=lambda x: performance_data[x]['name']
        )
        
        if not selected_agents:
            st.warning("請選擇至少一個代理進行對比。")
            return
        
        # 對比指標選擇
        comparison_metrics = st.multiselect(
            "選擇對比指標",
            options=list(self.metric_names.keys()),
            default=['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate'],
            format_func=lambda x: self.metric_names[x]
        )
        
        # 創建對比圖表
        if comparison_metrics:
            self._render_comparison_charts(performance_data, selected_agents, comparison_metrics)
        
        # 相關性分析
        st.subheader("相關性分析")
        self._render_correlation_analysis(performance_data, selected_agents)
    
    def _render_risk_analysis(self):
        """渲染風險分析"""
        st.subheader("🎯 風險分析")
        
        performance_data = self._get_performance_data()
        
        if not performance_data:
            st.info("暫無績效數據。")
            return
        
        # 風險收益散點圖
        st.subheader("風險收益分析")
        
        risk_return_data = []
        for agent_id, data in performance_data.items():
            risk_return_data.append({
                '代理名稱': data['name'],
                '收益率': data['total_return'],
                '波動率': data['volatility'],
                '夏普比率': data['sharpe_ratio'],
                '投資風格': data['style']
            })
        
        df = pd.DataFrame(risk_return_data)
        
        fig = px.scatter(
            df,
            x='波動率',
            y='收益率',
            size='夏普比率',
            color='投資風格',
            hover_name='代理名稱',
            title="風險收益散點圖",
            labels={'波動率': '風險 (波動率)', '收益率': '收益率'}
        )
        
        fig.update_traces(marker=dict(sizemin=10))
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # 風險指標分析
        st.subheader("風險指標")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # VaR分析
            self._render_var_analysis(performance_data)
        
        with col2:
            # 回撤分析
            self._render_drawdown_analysis(performance_data)
    
    def _render_detailed_reports(self):
        """渲染詳細報告"""
        st.subheader("📋 詳細績效報告")
        
        performance_data = self._get_performance_data()
        
        if not performance_data:
            st.info("暫無績效數據。")
            return
        
        # 代理選擇
        selected_agent = st.selectbox(
            "選擇代理",
            options=list(performance_data.keys()),
            format_func=lambda x: performance_data[x]['name']
        )
        
        if selected_agent:
            agent_data = performance_data[selected_agent]
            
            # 基本信息
            st.subheader("基本信息")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**代理名稱**: {agent_data['name']}")
                st.write(f"**投資風格**: {agent_data['style']}")
            
            with col2:
                st.write(f"**創建時間**: {agent_data.get('created_at', 'N/A')}")
                st.write(f"**運行狀態**: {agent_data['status']}")
            
            with col3:
                st.write(f"**總交易次數**: {agent_data.get('total_trades', 0)}")
                st.write(f"**活躍天數**: {agent_data.get('active_days', 0)}")
            
            # 詳細績效指標
            st.subheader("詳細績效指標")
            
            metrics_data = []
            for metric, value in agent_data.items():
                if metric in self.metric_names:
                    if metric in ['total_return', 'max_drawdown', 'win_rate', 'volatility']:
                        formatted_value = f"{value:.2%}"
                    else:
                        formatted_value = f"{value:.3f}"
                    
                    metrics_data.append({
                        '指標': self.metric_names[metric],
                        '數值': formatted_value,
                        '評級': self._get_metric_rating(metric, value)
                    })
            
            metrics_df = pd.DataFrame(metrics_data)
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)
            
            # 歷史績效圖表
            st.subheader("歷史績效")
            self._render_agent_history_chart(selected_agent, agent_data)
    
    def _get_performance_data(self) -> Dict[str, Any]:
        """獲取績效數據"""
        try:
            # 從session state獲取代理管理器
            if 'agent_manager' not in st.session_state:
                return {}
            
            agent_manager = st.session_state.agent_manager
            performance_data = {}
            
            for agent_id, agent in agent_manager.agents.items():
                # 模擬績效數據（實際應用中應從真實數據源獲取）
                performance_data[agent_id] = {
                    'name': agent.name,
                    'style': getattr(agent, 'investment_style', 'unknown'),
                    'status': getattr(agent, 'status', 'active'),
                    'total_return': np.random.normal(0.08, 0.15),  # 8% ± 15%
                    'sharpe_ratio': np.random.normal(1.2, 0.5),
                    'max_drawdown': abs(np.random.normal(-0.1, 0.05)),
                    'win_rate': np.random.uniform(0.45, 0.65),
                    'volatility': np.random.uniform(0.1, 0.3),
                    'alpha': np.random.normal(0.02, 0.03),
                    'beta': np.random.normal(1.0, 0.3),
                    'information_ratio': np.random.normal(0.5, 0.3),
                    'created_at': getattr(agent, 'created_at', datetime.now()).strftime('%Y-%m-%d'),
                    'total_trades': np.random.randint(50, 500),
                    'active_days': np.random.randint(30, 365)
                }
            
            return performance_data
            
        except Exception as e:
            logger.error(f"獲取績效數據失敗: {e}")
            return {}
    
    def _render_realtime_charts(self, performance_data: Dict[str, Any]):
        """渲染實時圖表"""
        st.subheader("實時績效圖表")
        
        # 績效分布直方圖
        col1, col2 = st.columns(2)
        
        with col1:
            returns = [data['total_return'] for data in performance_data.values()]
            fig = px.histogram(
                x=returns,
                nbins=10,
                title="收益率分布",
                labels={'x': '收益率', 'y': '代理數量'}
            )
            fig.update_traces(marker_color='lightblue')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            sharpe_ratios = [data['sharpe_ratio'] for data in performance_data.values()]
            fig = px.histogram(
                x=sharpe_ratios,
                nbins=10,
                title="夏普比率分布",
                labels={'x': '夏普比率', 'y': '代理數量'}
            )
            fig.update_traces(marker_color='lightgreen')
            st.plotly_chart(fig, use_container_width=True)
    
    def _render_comparison_charts(self, performance_data: Dict[str, Any], selected_agents: List[str], metrics: List[str]):
        """渲染對比圖表"""
        # 雷達圖
        fig = go.Figure()
        
        for agent_id in selected_agents:
            agent_data = performance_data[agent_id]
            values = [agent_data[metric] for metric in metrics]
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=[self.metric_names[m] for m in metrics],
                fill='toself',
                name=agent_data['name']
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max([max([performance_data[aid][m] for m in metrics]) for aid in selected_agents])]
                )),
            showlegend=True,
            title="代理績效雷達圖"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 柱狀圖對比
        comparison_df = pd.DataFrame({
            agent_id: [performance_data[agent_id][metric] for metric in metrics]
            for agent_id in selected_agents
        }, index=[self.metric_names[m] for m in metrics])
        
        fig = px.bar(
            comparison_df.T,
            title="代理績效對比",
            labels={'index': '代理', 'value': '數值', 'variable': '指標'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_correlation_analysis(self, performance_data: Dict[str, Any], selected_agents: List[str]):
        """渲染相關性分析"""
        if len(selected_agents) < 2:
            st.info("需要至少選擇2個代理進行相關性分析。")
            return
        
        # 創建相關性矩陣（模擬數據）
        correlation_data = {}
        for agent_id in selected_agents:
            # 模擬日收益率數據
            daily_returns = np.random.normal(0.001, 0.02, 252)  # 一年的日收益率
            correlation_data[performance_data[agent_id]['name']] = daily_returns
        
        corr_df = pd.DataFrame(correlation_data)
        correlation_matrix = corr_df.corr()
        
        fig = px.imshow(
            correlation_matrix,
            title="代理收益率相關性矩陣",
            color_continuous_scale='RdBu',
            aspect='auto'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_var_analysis(self, performance_data: Dict[str, Any]):
        """渲染VaR分析"""
        st.write("**風險價值 (VaR) 分析**")
        
        var_data = []
        for agent_id, data in performance_data.items():
            # 模擬VaR計算
            daily_return = data['total_return'] / 252
            volatility = data['volatility'] / np.sqrt(252)
            var_95 = daily_return - 1.645 * volatility  # 95% VaR
            
            var_data.append({
                '代理': data['name'],
                '日VaR (95%)': f"{var_95:.2%}"
            })
        
        var_df = pd.DataFrame(var_data)
        st.dataframe(var_df, use_container_width=True, hide_index=True)
    
    def _render_drawdown_analysis(self, performance_data: Dict[str, Any]):
        """渲染回撤分析"""
        st.write("**回撤分析**")
        
        drawdown_data = []
        for agent_id, data in performance_data.items():
            drawdown_data.append({
                '代理': data['name'],
                '最大回撤': f"{data['max_drawdown']:.2%}",
                '回撤評級': self._get_drawdown_rating(data['max_drawdown'])
            })
        
        drawdown_df = pd.DataFrame(drawdown_data)
        st.dataframe(drawdown_df, use_container_width=True, hide_index=True)
    
    def _render_agent_history_chart(self, agent_id: str, agent_data: Dict[str, Any]):
        """渲染代理歷史圖表"""
        # 模擬歷史數據
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        cumulative_returns = np.cumprod(1 + np.random.normal(0.0008, 0.02, len(dates))) - 1
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=cumulative_returns,
            mode='lines',
            name='累積收益率',
            line=dict(color='blue')
        ))
        
        fig.update_layout(
            title=f"{agent_data['name']} 歷史績效",
            xaxis_title="日期",
            yaxis_title="累積收益率",
            yaxis_tickformat='.1%'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def _get_metric_rating(self, metric: str, value: float) -> str:
        """獲取指標評級"""
        if metric == 'total_return':
            if value > 0.15: return "🟢 優秀"
            elif value > 0.08: return "🟡 良好"
            elif value > 0.03: return "🟠 一般"
            else: return "🔴 較差"
        elif metric == 'sharpe_ratio':
            if value > 2.0: return "🟢 優秀"
            elif value > 1.0: return "🟡 良好"
            elif value > 0.5: return "🟠 一般"
            else: return "🔴 較差"
        elif metric == 'max_drawdown':
            if value < 0.05: return "🟢 優秀"
            elif value < 0.1: return "🟡 良好"
            elif value < 0.2: return "🟠 一般"
            else: return "🔴 較差"
        else:
            return "⚪ 普通"
    
    def _get_drawdown_rating(self, drawdown: float) -> str:
        """獲取回撤評級"""
        if drawdown < 0.05: return "🟢 低風險"
        elif drawdown < 0.1: return "🟡 中等風險"
        elif drawdown < 0.2: return "🟠 較高風險"
        else: return "🔴 高風險"


def render_agent_performance_monitor():
    """渲染代理績效監控面板的便捷函數"""
    monitor = AgentPerformanceMonitor()
    monitor.render()
