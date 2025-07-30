# -*- coding: utf-8 -*-
"""
增強數據視覺化組件

此模組提供AI顯示邏輯改進說明中的額外視覺化功能，
包括季節性分析、多時間框架分析、性能監控等功能。

主要功能：
- 季節性模式分析和視覺化
- 多時間框架對比分析
- 交易訊號統計和性能分析
- 用戶行為分析視覺化
- 系統性能監控圖表

Example:
    基本使用：
    ```python
    from src.ui.components.enhanced_data_visualization import EnhancedDataVisualizer
    
    visualizer = EnhancedDataVisualizer()
    fig = visualizer.create_seasonal_analysis(df, symbol)
    ```

Note:
    此模組專門實現AI顯示邏輯改進說明中的進階視覺化功能，
    與現有的interactive_charts.py模組協同工作。
"""

import logging
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import streamlit as st

# 設定日誌
logger = logging.getLogger(__name__)


class EnhancedDataVisualizer:
    """
    增強數據視覺化器
    
    提供AI顯示邏輯改進說明中的進階視覺化功能。
    """
    
    def __init__(self):
        """初始化增強數據視覺化器"""
        self.color_palette = {
            'primary': '#1f77b4',
            'secondary': '#ff7f0e', 
            'success': '#2ca02c',
            'danger': '#d62728',
            'warning': '#ff9800',
            'info': '#17a2b8',
            'light': '#f8f9fa',
            'dark': '#343a40'
        }
        
        logger.info("✅ 增強數據視覺化器初始化完成")
        
    def create_seasonal_analysis(self, df: pd.DataFrame, symbol: str) -> go.Figure:
        """
        創建季節性分析圖表
        
        Args:
            df: 股價數據
            symbol: 股票代碼
            
        Returns:
            go.Figure: 季節性分析圖表
        """
        try:
            # 確保有日期索引
            if 'date' in df.columns:
                df = df.set_index('date')
            
            # 計算月份收益率
            df['month'] = df.index.month
            df['year'] = df.index.year
            df['returns'] = df['close'].pct_change()
            
            # 按月份統計平均收益率
            monthly_returns = df.groupby('month')['returns'].agg(['mean', 'std', 'count'])
            monthly_returns.index = [
                '1月', '2月', '3月', '4月', '5月', '6月',
                '7月', '8月', '9月', '10月', '11月', '12月'
            ]
            
            # 創建子圖
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=[
                    '月份平均收益率', '月份收益率波動性',
                    '年度收益率趨勢', '季度表現對比'
                ],
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # 1. 月份平均收益率
            fig.add_trace(
                go.Bar(
                    x=monthly_returns.index,
                    y=monthly_returns['mean'] * 100,
                    name='平均收益率(%)',
                    marker_color=self.color_palette['primary']
                ),
                row=1, col=1
            )
            
            # 2. 月份收益率波動性
            fig.add_trace(
                go.Bar(
                    x=monthly_returns.index,
                    y=monthly_returns['std'] * 100,
                    name='波動性(%)',
                    marker_color=self.color_palette['warning']
                ),
                row=1, col=2
            )
            
            # 3. 年度收益率趨勢
            yearly_returns = df.groupby('year')['returns'].sum() * 100
            fig.add_trace(
                go.Scatter(
                    x=yearly_returns.index,
                    y=yearly_returns.values,
                    mode='lines+markers',
                    name='年度收益率(%)',
                    line=dict(color=self.color_palette['success'])
                ),
                row=2, col=1
            )
            
            # 4. 季度表現對比
            df['quarter'] = df.index.quarter
            quarterly_returns = df.groupby('quarter')['returns'].mean() * 100
            quarter_names = ['Q1', 'Q2', 'Q3', 'Q4']
            
            fig.add_trace(
                go.Bar(
                    x=quarter_names,
                    y=quarterly_returns.values,
                    name='季度平均收益率(%)',
                    marker_color=self.color_palette['info']
                ),
                row=2, col=2
            )
            
            # 更新佈局
            fig.update_layout(
                title=f'{symbol} 季節性分析',
                height=800,
                showlegend=False,
                template='plotly_white'
            )
            
            logger.info(f"✅ 成功生成 {symbol} 的季節性分析圖表")
            return fig
            
        except Exception as e:
            logger.error(f"季節性分析圖表生成失敗: {e}")
            # 返回空圖表
            fig = go.Figure()
            fig.add_annotation(
                text=f"季節性分析生成失敗: {e}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
            
    def create_multi_timeframe_analysis(self, df: pd.DataFrame, symbol: str) -> go.Figure:
        """
        創建多時間框架分析圖表
        
        Args:
            df: 股價數據
            symbol: 股票代碼
            
        Returns:
            go.Figure: 多時間框架分析圖表
        """
        try:
            # 確保有日期索引
            if 'date' in df.columns:
                df = df.set_index('date')
                
            # 重採樣到不同時間框架
            daily_data = df.resample('D').last().dropna()
            weekly_data = df.resample('W').last().dropna()
            monthly_data = df.resample('M').last().dropna()
            
            # 計算移動平均線
            daily_data['MA20'] = daily_data['close'].rolling(20).mean()
            weekly_data['MA4'] = weekly_data['close'].rolling(4).mean()
            monthly_data['MA3'] = monthly_data['close'].rolling(3).mean()
            
            # 創建子圖
            fig = make_subplots(
                rows=3, cols=1,
                subplot_titles=['日線圖', '週線圖', '月線圖'],
                vertical_spacing=0.08
            )
            
            # 日線圖
            fig.add_trace(
                go.Scatter(
                    x=daily_data.index,
                    y=daily_data['close'],
                    mode='lines',
                    name='日收盤價',
                    line=dict(color=self.color_palette['primary'], width=1)
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=daily_data.index,
                    y=daily_data['MA20'],
                    mode='lines',
                    name='20日均線',
                    line=dict(color=self.color_palette['danger'], width=2)
                ),
                row=1, col=1
            )
            
            # 週線圖
            fig.add_trace(
                go.Scatter(
                    x=weekly_data.index,
                    y=weekly_data['close'],
                    mode='lines',
                    name='週收盤價',
                    line=dict(color=self.color_palette['success'], width=2)
                ),
                row=2, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=weekly_data.index,
                    y=weekly_data['MA4'],
                    mode='lines',
                    name='4週均線',
                    line=dict(color=self.color_palette['warning'], width=2)
                ),
                row=2, col=1
            )
            
            # 月線圖
            fig.add_trace(
                go.Scatter(
                    x=monthly_data.index,
                    y=monthly_data['close'],
                    mode='lines+markers',
                    name='月收盤價',
                    line=dict(color=self.color_palette['info'], width=3),
                    marker=dict(size=6)
                ),
                row=3, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=monthly_data.index,
                    y=monthly_data['MA3'],
                    mode='lines',
                    name='3月均線',
                    line=dict(color=self.color_palette['dark'], width=2)
                ),
                row=3, col=1
            )
            
            # 更新佈局
            fig.update_layout(
                title=f'{symbol} 多時間框架分析',
                height=900,
                showlegend=True,
                template='plotly_white'
            )
            
            # 更新x軸標籤
            fig.update_xaxes(title_text="日期", row=3, col=1)
            fig.update_yaxes(title_text="價格", row=1, col=1)
            fig.update_yaxes(title_text="價格", row=2, col=1)
            fig.update_yaxes(title_text="價格", row=3, col=1)
            
            logger.info(f"✅ 成功生成 {symbol} 的多時間框架分析圖表")
            return fig
            
        except Exception as e:
            logger.error(f"多時間框架分析圖表生成失敗: {e}")
            # 返回空圖表
            fig = go.Figure()
            fig.add_annotation(
                text=f"多時間框架分析生成失敗: {e}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
            
    def create_signal_performance_analysis(self, signals_data: List[Dict]) -> go.Figure:
        """
        創建交易訊號性能分析圖表
        
        Args:
            signals_data: 交易訊號數據列表
            
        Returns:
            go.Figure: 訊號性能分析圖表
        """
        try:
            if not signals_data:
                fig = go.Figure()
                fig.add_annotation(
                    text="暫無交易訊號數據",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                return fig
                
            # 轉換為DataFrame
            df = pd.DataFrame(signals_data)
            
            # 創建子圖
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=[
                    '訊號類型分布', '訊號準確率',
                    '月度訊號數量', '訊號強度分布'
                ],
                specs=[[{"type": "pie"}, {"type": "bar"}],
                       [{"type": "bar"}, {"type": "histogram"}]]
            )
            
            # 1. 訊號類型分布
            signal_counts = df['signal_type'].value_counts()
            fig.add_trace(
                go.Pie(
                    labels=signal_counts.index,
                    values=signal_counts.values,
                    name="訊號類型"
                ),
                row=1, col=1
            )
            
            # 2. 訊號準確率（模擬數據）
            accuracy_data = {
                'MACD金叉': 0.65,
                'MACD死叉': 0.58,
                'RSI超買': 0.72,
                'RSI超賣': 0.68
            }
            
            fig.add_trace(
                go.Bar(
                    x=list(accuracy_data.keys()),
                    y=list(accuracy_data.values()),
                    name='準確率',
                    marker_color=self.color_palette['success']
                ),
                row=1, col=2
            )
            
            # 3. 月度訊號數量
            if 'date' in df.columns:
                df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
                monthly_signals = df.groupby('month').size()
                
                fig.add_trace(
                    go.Bar(
                        x=[str(m) for m in monthly_signals.index],
                        y=monthly_signals.values,
                        name='月度訊號數',
                        marker_color=self.color_palette['info']
                    ),
                    row=2, col=1
                )
            
            # 4. 訊號強度分布
            if 'strength' in df.columns:
                fig.add_trace(
                    go.Histogram(
                        x=df['strength'],
                        name='訊號強度',
                        marker_color=self.color_palette['warning']
                    ),
                    row=2, col=2
                )
            
            # 更新佈局
            fig.update_layout(
                title='交易訊號性能分析',
                height=800,
                showlegend=False,
                template='plotly_white'
            )
            
            logger.info("✅ 成功生成交易訊號性能分析圖表")
            return fig
            
        except Exception as e:
            logger.error(f"交易訊號性能分析圖表生成失敗: {e}")
            # 返回空圖表
            fig = go.Figure()
            fig.add_annotation(
                text=f"訊號性能分析生成失敗: {e}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
            
    def create_user_behavior_analysis(self, user_interactions: List[Dict]) -> go.Figure:
        """
        創建用戶行為分析圖表
        
        Args:
            user_interactions: 用戶互動數據列表
            
        Returns:
            go.Figure: 用戶行為分析圖表
        """
        try:
            if not user_interactions:
                fig = go.Figure()
                fig.add_annotation(
                    text="暫無用戶互動數據",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                return fig
                
            # 轉換為DataFrame
            df = pd.DataFrame(user_interactions)
            
            # 創建子圖
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=[
                    '互動類型分布', '使用時間趨勢',
                    '偏好指標統計', '品質評分分布'
                ]
            )
            
            # 1. 互動類型分布
            interaction_counts = df['interaction_type'].value_counts()
            fig.add_trace(
                go.Bar(
                    x=interaction_counts.index,
                    y=interaction_counts.values,
                    name='互動次數',
                    marker_color=self.color_palette['primary']
                ),
                row=1, col=1
            )
            
            # 2. 使用時間趨勢
            if 'timestamp' in df.columns:
                df['date'] = pd.to_datetime(df['timestamp']).dt.date
                daily_usage = df.groupby('date').size()
                
                fig.add_trace(
                    go.Scatter(
                        x=daily_usage.index,
                        y=daily_usage.values,
                        mode='lines+markers',
                        name='日使用次數',
                        line=dict(color=self.color_palette['success'])
                    ),
                    row=1, col=2
                )
            
            # 3. 偏好指標統計
            all_indicators = []
            for interaction in user_interactions:
                params = interaction.get('parameters', {})
                indicators = params.get('indicators', [])
                all_indicators.extend(indicators)
                
            if all_indicators:
                indicator_counts = pd.Series(all_indicators).value_counts()
                fig.add_trace(
                    go.Bar(
                        x=indicator_counts.index,
                        y=indicator_counts.values,
                        name='使用次數',
                        marker_color=self.color_palette['info']
                    ),
                    row=2, col=1
                )
            
            # 4. 品質評分分布
            if 'result_quality' in df.columns:
                fig.add_trace(
                    go.Histogram(
                        x=df['result_quality'],
                        name='品質評分',
                        marker_color=self.color_palette['warning']
                    ),
                    row=2, col=2
                )
            
            # 更新佈局
            fig.update_layout(
                title='用戶行為分析',
                height=800,
                showlegend=False,
                template='plotly_white'
            )
            
            logger.info("✅ 成功生成用戶行為分析圖表")
            return fig
            
        except Exception as e:
            logger.error(f"用戶行為分析圖表生成失敗: {e}")
            # 返回空圖表
            fig = go.Figure()
            fig.add_annotation(
                text=f"用戶行為分析生成失敗: {e}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
            
    def create_system_performance_dashboard(self, performance_data: Dict) -> go.Figure:
        """
        創建系統性能監控儀表板
        
        Args:
            performance_data: 系統性能數據
            
        Returns:
            go.Figure: 系統性能儀表板
        """
        try:
            # 創建儀表板佈局
            fig = make_subplots(
                rows=2, cols=3,
                subplot_titles=[
                    'CPU使用率', '記憶體使用率', '圖表生成時間',
                    '數據處理速度', '錯誤率', '用戶滿意度'
                ],
                specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "scatter"}],
                       [{"type": "bar"}, {"type": "indicator"}, {"type": "indicator"}]]
            )
            
            # 1. CPU使用率指示器
            cpu_usage = performance_data.get('cpu_usage', 45)
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=cpu_usage,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "CPU (%)"},
                    gauge={'axis': {'range': [None, 100]},
                           'bar': {'color': self._get_performance_color(cpu_usage, 80)},
                           'steps': [{'range': [0, 50], 'color': "lightgray"},
                                   {'range': [50, 80], 'color': "yellow"}],
                           'threshold': {'line': {'color': "red", 'width': 4},
                                       'thickness': 0.75, 'value': 90}}
                ),
                row=1, col=1
            )
            
            # 2. 記憶體使用率指示器
            memory_usage = performance_data.get('memory_usage', 62)
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=memory_usage,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "記憶體 (%)"},
                    gauge={'axis': {'range': [None, 100]},
                           'bar': {'color': self._get_performance_color(memory_usage, 85)},
                           'steps': [{'range': [0, 60], 'color': "lightgray"},
                                   {'range': [60, 85], 'color': "yellow"}],
                           'threshold': {'line': {'color': "red", 'width': 4},
                                       'thickness': 0.75, 'value': 95}}
                ),
                row=1, col=2
            )
            
            # 3. 圖表生成時間趨勢
            chart_times = performance_data.get('chart_generation_times', [1.2, 1.5, 1.1, 1.8, 1.3])
            fig.add_trace(
                go.Scatter(
                    y=chart_times,
                    mode='lines+markers',
                    name='生成時間(秒)',
                    line=dict(color=self.color_palette['primary'])
                ),
                row=1, col=3
            )
            
            # 4. 數據處理速度
            processing_speeds = performance_data.get('processing_speeds', 
                                                   {'數據載入': 0.8, '指標計算': 1.2, '圖表渲染': 0.9})
            fig.add_trace(
                go.Bar(
                    x=list(processing_speeds.keys()),
                    y=list(processing_speeds.values()),
                    name='處理時間(秒)',
                    marker_color=self.color_palette['info']
                ),
                row=2, col=1
            )
            
            # 5. 錯誤率指示器
            error_rate = performance_data.get('error_rate', 2.1)
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=error_rate,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "錯誤率 (%)"},
                    gauge={'axis': {'range': [0, 10]},
                           'bar': {'color': self._get_performance_color(error_rate, 5, reverse=True)},
                           'steps': [{'range': [0, 2], 'color': "lightgreen"},
                                   {'range': [2, 5], 'color': "yellow"}],
                           'threshold': {'line': {'color': "red", 'width': 4},
                                       'thickness': 0.75, 'value': 8}}
                ),
                row=2, col=2
            )
            
            # 6. 用戶滿意度指示器
            satisfaction = performance_data.get('user_satisfaction', 8.5)
            fig.add_trace(
                go.Indicator(
                    mode="gauge+number",
                    value=satisfaction,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "滿意度 (1-10)"},
                    gauge={'axis': {'range': [0, 10]},
                           'bar': {'color': self._get_performance_color(satisfaction, 7)},
                           'steps': [{'range': [0, 5], 'color': "lightgray"},
                                   {'range': [5, 7], 'color': "yellow"}],
                           'threshold': {'line': {'color': "green", 'width': 4},
                                       'thickness': 0.75, 'value': 9}}
                ),
                row=2, col=3
            )
            
            # 更新佈局
            fig.update_layout(
                title='系統性能監控儀表板',
                height=800,
                showlegend=False,
                template='plotly_white'
            )
            
            logger.info("✅ 成功生成系統性能監控儀表板")
            return fig
            
        except Exception as e:
            logger.error(f"系統性能儀表板生成失敗: {e}")
            # 返回空圖表
            fig = go.Figure()
            fig.add_annotation(
                text=f"性能儀表板生成失敗: {e}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
            
    def _get_performance_color(self, value: float, threshold: float, reverse: bool = False) -> str:
        """
        根據性能值獲取顏色
        
        Args:
            value: 性能值
            threshold: 閾值
            reverse: 是否反向（值越低越好）
            
        Returns:
            str: 顏色代碼
        """
        if reverse:
            if value <= threshold * 0.5:
                return "green"
            elif value <= threshold:
                return "orange"
            else:
                return "red"
        else:
            if value >= threshold * 1.2:
                return "red"
            elif value >= threshold:
                return "orange"
            else:
                return "green"
