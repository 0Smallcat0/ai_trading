#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
進階技術指標圖表組件

提供各種技術指標的圖表顯示功能，包括：
- Williams %R 圖表
- Stochastic 圖表
- CCI 圖表
- ATR 圖表
- Parabolic SAR 圖表
- VWAP 圖表
- MFI 圖表
- Ichimoku Cloud 圖表
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.subplots as sp
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class AdvancedIndicatorCharts:
    """進階技術指標圖表類"""
    
    def __init__(self, theme: str = "plotly_white"):
        """
        初始化圖表組件
        
        Args:
            theme: 圖表主題
        """
        self.theme = theme
        self.colors = {
            'bullish': '#00ff88',
            'bearish': '#ff4444', 
            'neutral': '#888888',
            'overbought': '#ff6b6b',
            'oversold': '#4ecdc4',
            'signal': '#ffd93d'
        }
    
    def create_williams_r_chart(self, data: pd.DataFrame, willr: pd.Series, 
                               period: int = 14) -> go.Figure:
        """
        創建 Williams %R 圖表
        
        Args:
            data: 價格數據
            willr: Williams %R 值
            period: 計算週期
            
        Returns:
            Plotly 圖表對象
        """
        try:
            fig = sp.make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                subplot_titles=['價格走勢', f'Williams %R ({period})'],
                row_heights=[0.7, 0.3]
            )
            
            # 價格 K 線圖
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name='價格',
                    increasing_line_color=self.colors['bullish'],
                    decreasing_line_color=self.colors['bearish']
                ),
                row=1, col=1
            )
            
            # Williams %R 線圖
            fig.add_trace(
                go.Scatter(
                    x=willr.index,
                    y=willr,
                    mode='lines',
                    name=f'Williams %R ({period})',
                    line=dict(color='blue', width=2)
                ),
                row=2, col=1
            )
            
            # 添加超買超賣線
            fig.add_hline(y=-20, line_dash="dash", line_color=self.colors['overbought'], 
                         annotation_text="超買 (-20)", row=2, col=1)
            fig.add_hline(y=-80, line_dash="dash", line_color=self.colors['oversold'], 
                         annotation_text="超賣 (-80)", row=2, col=1)
            
            # 設置 Y 軸範圍
            fig.update_yaxes(range=[-100, 0], row=2, col=1)
            
            fig.update_layout(
                title=f"Williams %R 技術指標分析",
                template=self.theme,
                height=600,
                showlegend=True,
                xaxis_rangeslider_visible=False
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Williams %R 圖表創建失敗: {e}")
            return go.Figure()
    
    def create_stochastic_chart(self, data: pd.DataFrame, k_values: pd.Series, 
                               d_values: pd.Series, k_period: int = 14) -> go.Figure:
        """
        創建 Stochastic 圖表
        
        Args:
            data: 價格數據
            k_values: %K 值
            d_values: %D 值
            k_period: K 週期
            
        Returns:
            Plotly 圖表對象
        """
        try:
            fig = sp.make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                subplot_titles=['價格走勢', f'Stochastic Oscillator ({k_period})'],
                row_heights=[0.7, 0.3]
            )
            
            # 價格 K 線圖
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name='價格',
                    increasing_line_color=self.colors['bullish'],
                    decreasing_line_color=self.colors['bearish']
                ),
                row=1, col=1
            )
            
            # %K 線
            fig.add_trace(
                go.Scatter(
                    x=k_values.index,
                    y=k_values,
                    mode='lines',
                    name='%K',
                    line=dict(color='blue', width=2)
                ),
                row=2, col=1
            )
            
            # %D 線
            fig.add_trace(
                go.Scatter(
                    x=d_values.index,
                    y=d_values,
                    mode='lines',
                    name='%D',
                    line=dict(color='red', width=2)
                ),
                row=2, col=1
            )
            
            # 添加超買超賣線
            fig.add_hline(y=80, line_dash="dash", line_color=self.colors['overbought'], 
                         annotation_text="超買 (80)", row=2, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color=self.colors['oversold'], 
                         annotation_text="超賣 (20)", row=2, col=1)
            
            # 設置 Y 軸範圍
            fig.update_yaxes(range=[0, 100], row=2, col=1)
            
            fig.update_layout(
                title=f"Stochastic Oscillator 技術指標分析",
                template=self.theme,
                height=600,
                showlegend=True,
                xaxis_rangeslider_visible=False
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Stochastic 圖表創建失敗: {e}")
            return go.Figure()
    
    def create_cci_chart(self, data: pd.DataFrame, cci: pd.Series, 
                        period: int = 20) -> go.Figure:
        """
        創建 CCI 圖表
        
        Args:
            data: 價格數據
            cci: CCI 值
            period: 計算週期
            
        Returns:
            Plotly 圖表對象
        """
        try:
            fig = sp.make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                subplot_titles=['價格走勢', f'CCI ({period})'],
                row_heights=[0.7, 0.3]
            )
            
            # 價格 K 線圖
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name='價格',
                    increasing_line_color=self.colors['bullish'],
                    decreasing_line_color=self.colors['bearish']
                ),
                row=1, col=1
            )
            
            # CCI 線圖
            fig.add_trace(
                go.Scatter(
                    x=cci.index,
                    y=cci,
                    mode='lines',
                    name=f'CCI ({period})',
                    line=dict(color='purple', width=2)
                ),
                row=2, col=1
            )
            
            # 添加超買超賣線
            fig.add_hline(y=100, line_dash="dash", line_color=self.colors['overbought'], 
                         annotation_text="超買 (+100)", row=2, col=1)
            fig.add_hline(y=-100, line_dash="dash", line_color=self.colors['oversold'], 
                         annotation_text="超賣 (-100)", row=2, col=1)
            fig.add_hline(y=0, line_dash="dot", line_color=self.colors['neutral'], 
                         annotation_text="中線 (0)", row=2, col=1)
            
            fig.update_layout(
                title=f"CCI 技術指標分析",
                template=self.theme,
                height=600,
                showlegend=True,
                xaxis_rangeslider_visible=False
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"CCI 圖表創建失敗: {e}")
            return go.Figure()
    
    def create_atr_chart(self, data: pd.DataFrame, atr: pd.Series, 
                        period: int = 14) -> go.Figure:
        """
        創建 ATR 圖表
        
        Args:
            data: 價格數據
            atr: ATR 值
            period: 計算週期
            
        Returns:
            Plotly 圖表對象
        """
        try:
            fig = sp.make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                subplot_titles=['價格走勢', f'ATR ({period}) - 波動性指標'],
                row_heights=[0.7, 0.3]
            )
            
            # 價格 K 線圖
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name='價格',
                    increasing_line_color=self.colors['bullish'],
                    decreasing_line_color=self.colors['bearish']
                ),
                row=1, col=1
            )
            
            # ATR 線圖
            fig.add_trace(
                go.Scatter(
                    x=atr.index,
                    y=atr,
                    mode='lines',
                    name=f'ATR ({period})',
                    line=dict(color='orange', width=2),
                    fill='tonexty'
                ),
                row=2, col=1
            )
            
            # 添加 ATR 平均線
            atr_mean = atr.rolling(window=20).mean()
            fig.add_trace(
                go.Scatter(
                    x=atr_mean.index,
                    y=atr_mean,
                    mode='lines',
                    name='ATR 平均',
                    line=dict(color='red', width=1, dash='dash')
                ),
                row=2, col=1
            )
            
            fig.update_layout(
                title=f"ATR 波動性指標分析",
                template=self.theme,
                height=600,
                showlegend=True,
                xaxis_rangeslider_visible=False
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"ATR 圖表創建失敗: {e}")
            return go.Figure()

    def create_vwap_chart(self, data: pd.DataFrame, vwap: pd.Series) -> go.Figure:
        """
        創建 VWAP 圖表

        Args:
            data: 價格數據
            vwap: VWAP 值

        Returns:
            Plotly 圖表對象
        """
        try:
            fig = go.Figure()

            # 價格 K 線圖
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name='價格',
                    increasing_line_color=self.colors['bullish'],
                    decreasing_line_color=self.colors['bearish']
                )
            )

            # VWAP 線
            fig.add_trace(
                go.Scatter(
                    x=vwap.index,
                    y=vwap,
                    mode='lines',
                    name='VWAP',
                    line=dict(color='blue', width=3)
                )
            )

            # 添加價格與 VWAP 的關係區域
            above_vwap = data['close'] > vwap
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['close'].where(above_vwap),
                    mode='markers',
                    name='價格高於VWAP',
                    marker=dict(color=self.colors['bullish'], size=3),
                    showlegend=False
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['close'].where(~above_vwap),
                    mode='markers',
                    name='價格低於VWAP',
                    marker=dict(color=self.colors['bearish'], size=3),
                    showlegend=False
                )
            )

            fig.update_layout(
                title="VWAP (成交量加權平均價格) 分析",
                template=self.theme,
                height=500,
                showlegend=True,
                xaxis_rangeslider_visible=False
            )

            return fig

        except Exception as e:
            logger.error(f"VWAP 圖表創建失敗: {e}")
            return go.Figure()

    def create_mfi_chart(self, data: pd.DataFrame, mfi: pd.Series,
                        period: int = 14) -> go.Figure:
        """
        創建 MFI 圖表

        Args:
            data: 價格數據
            mfi: MFI 值
            period: 計算週期

        Returns:
            Plotly 圖表對象
        """
        try:
            fig = sp.make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                subplot_titles=['價格走勢', f'MFI ({period}) - 資金流量指標'],
                row_heights=[0.7, 0.3]
            )

            # 價格 K 線圖
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name='價格',
                    increasing_line_color=self.colors['bullish'],
                    decreasing_line_color=self.colors['bearish']
                ),
                row=1, col=1
            )

            # MFI 線圖
            fig.add_trace(
                go.Scatter(
                    x=mfi.index,
                    y=mfi,
                    mode='lines',
                    name=f'MFI ({period})',
                    line=dict(color='green', width=2)
                ),
                row=2, col=1
            )

            # 添加超買超賣線
            fig.add_hline(y=80, line_dash="dash", line_color=self.colors['overbought'],
                         annotation_text="超買 (80)", row=2, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color=self.colors['oversold'],
                         annotation_text="超賣 (20)", row=2, col=1)
            fig.add_hline(y=50, line_dash="dot", line_color=self.colors['neutral'],
                         annotation_text="中線 (50)", row=2, col=1)

            # 設置 Y 軸範圍
            fig.update_yaxes(range=[0, 100], row=2, col=1)

            fig.update_layout(
                title=f"MFI 資金流量指標分析",
                template=self.theme,
                height=600,
                showlegend=True,
                xaxis_rangeslider_visible=False
            )

            return fig

        except Exception as e:
            logger.error(f"MFI 圖表創建失敗: {e}")
            return go.Figure()

    def create_ichimoku_chart(self, data: pd.DataFrame,
                             ichimoku_data: Dict[str, pd.Series]) -> go.Figure:
        """
        創建一目均衡表圖表

        Args:
            data: 價格數據
            ichimoku_data: 一目均衡表數據

        Returns:
            Plotly 圖表對象
        """
        try:
            fig = go.Figure()

            # 價格 K 線圖
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name='價格',
                    increasing_line_color=self.colors['bullish'],
                    decreasing_line_color=self.colors['bearish']
                )
            )

            # 轉換線 (Tenkan-sen)
            if 'tenkan_sen' in ichimoku_data:
                fig.add_trace(
                    go.Scatter(
                        x=ichimoku_data['tenkan_sen'].index,
                        y=ichimoku_data['tenkan_sen'],
                        mode='lines',
                        name='轉換線',
                        line=dict(color='red', width=1)
                    )
                )

            # 基準線 (Kijun-sen)
            if 'kijun_sen' in ichimoku_data:
                fig.add_trace(
                    go.Scatter(
                        x=ichimoku_data['kijun_sen'].index,
                        y=ichimoku_data['kijun_sen'],
                        mode='lines',
                        name='基準線',
                        line=dict(color='blue', width=1)
                    )
                )

            # 先行帶 A 和 B (雲帶)
            if 'senkou_span_a' in ichimoku_data and 'senkou_span_b' in ichimoku_data:
                span_a = ichimoku_data['senkou_span_a']
                span_b = ichimoku_data['senkou_span_b']

                # 雲帶填充
                fig.add_trace(
                    go.Scatter(
                        x=span_a.index,
                        y=span_a,
                        mode='lines',
                        name='先行帶A',
                        line=dict(color='green', width=1),
                        fill=None
                    )
                )

                fig.add_trace(
                    go.Scatter(
                        x=span_b.index,
                        y=span_b,
                        mode='lines',
                        name='先行帶B',
                        line=dict(color='red', width=1),
                        fill='tonexty',
                        fillcolor='rgba(0,255,0,0.1)'
                    )
                )

            # 遲行線 (Chikou Span)
            if 'chikou_span' in ichimoku_data:
                fig.add_trace(
                    go.Scatter(
                        x=ichimoku_data['chikou_span'].index,
                        y=ichimoku_data['chikou_span'],
                        mode='lines',
                        name='遲行線',
                        line=dict(color='purple', width=1, dash='dash')
                    )
                )

            fig.update_layout(
                title="一目均衡表 (Ichimoku Cloud) 分析",
                template=self.theme,
                height=600,
                showlegend=True,
                xaxis_rangeslider_visible=False
            )

            return fig

        except Exception as e:
            logger.error(f"一目均衡表圖表創建失敗: {e}")
            return go.Figure()
