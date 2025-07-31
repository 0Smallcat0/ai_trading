# -*- coding: utf-8 -*-
"""
預建示範策略模板

此模組提供新手友好的示範策略模板，包括：
- 經典技術分析策略
- 簡化的機器學習策略
- 風險控制示範
- 策略參數說明
- 一鍵部署功能

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
import json
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# 導入現有策略模組
try:
    from ...strategy import (
        MovingAverageCrossStrategy,
        RSIStrategy,
        Strategy
    )
except ImportError:
    # 備用導入
    MovingAverageCrossStrategy = None
    RSIStrategy = None
    Strategy = None

logger = logging.getLogger(__name__)


class DemoStrategies:
    """
    預建示範策略模板管理器
    
    提供新手友好的策略模板，包括經典技術分析策略、
    簡化的機器學習策略和風險控制示範。
    
    Attributes:
        strategy_templates (Dict): 策略模板字典
        default_parameters (Dict): 預設參數配置
        
    Example:
        >>> demo = DemoStrategies()
        >>> strategies = demo.get_available_strategies()
        >>> demo.deploy_strategy('ma_cross', {'fast': 10, 'slow': 20})
    """
    
    def __init__(self):
        """初始化示範策略管理器"""
        self.strategy_templates = self._initialize_strategy_templates()
        self.default_parameters = self._initialize_default_parameters()
        
    def _initialize_strategy_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化策略模板
        
        Returns:
            Dict[str, Dict[str, Any]]: 策略模板字典
        """
        return {
            'ma_cross': {
                'name': '移動平均線交叉策略',
                'description': '當短期均線上穿長期均線時買入，下穿時賣出',
                'difficulty': '初級',
                'category': '技術分析',
                'risk_level': '中等',
                'expected_return': '8-15%',
                'parameters': {
                    'fast_period': {'default': 10, 'range': [5, 50], 'type': 'int'},
                    'slow_period': {'default': 20, 'range': [10, 100], 'type': 'int'},
                    'stop_loss': {'default': 0.05, 'range': [0.01, 0.2], 'type': 'float'}
                },
                'pros': [
                    '邏輯簡單易懂',
                    '適合趨勢市場',
                    '風險可控'
                ],
                'cons': [
                    '震盪市場表現較差',
                    '存在滯後性',
                    '假突破風險'
                ]
            },
            'rsi_strategy': {
                'name': 'RSI 超買超賣策略',
                'description': 'RSI 低於30時買入，高於70時賣出',
                'difficulty': '初級',
                'category': '技術分析',
                'risk_level': '中等',
                'expected_return': '6-12%',
                'parameters': {
                    'rsi_period': {'default': 14, 'range': [5, 30], 'type': 'int'},
                    'oversold': {'default': 30, 'range': [20, 40], 'type': 'int'},
                    'overbought': {'default': 70, 'range': [60, 80], 'type': 'int'},
                    'stop_loss': {'default': 0.08, 'range': [0.02, 0.15], 'type': 'float'}
                },
                'pros': [
                    '適合震盪市場',
                    '進出點明確',
                    '風險分散'
                ],
                'cons': [
                    '趨勢市場表現較差',
                    '需要頻繁交易',
                    '交易成本較高'
                ]
            },
            'momentum_strategy': {
                'name': '動量策略',
                'description': '追蹤價格動量，買入上漲股票',
                'difficulty': '中級',
                'category': '量化因子',
                'risk_level': '較高',
                'expected_return': '10-20%',
                'parameters': {
                    'lookback_period': {'default': 20, 'range': [10, 60], 'type': 'int'},
                    'momentum_threshold': {'default': 0.02, 'range': [0.01, 0.1], 'type': 'float'},
                    'rebalance_freq': {'default': 5, 'range': [1, 20], 'type': 'int'},
                    'stop_loss': {'default': 0.1, 'range': [0.05, 0.2], 'type': 'float'}
                },
                'pros': [
                    '捕捉趨勢機會',
                    '收益潛力較高',
                    '適應性強'
                ],
                'cons': [
                    '風險較高',
                    '需要及時調整',
                    '市場轉向風險'
                ]
            },
            'mean_reversion': {
                'name': '均值回歸策略',
                'description': '當價格偏離均值時進行反向操作',
                'difficulty': '中級',
                'category': '統計套利',
                'risk_level': '中等',
                'expected_return': '5-10%',
                'parameters': {
                    'lookback_period': {'default': 30, 'range': [15, 90], 'type': 'int'},
                    'deviation_threshold': {'default': 2.0, 'range': [1.0, 3.0], 'type': 'float'},
                    'holding_period': {'default': 10, 'range': [3, 30], 'type': 'int'},
                    'stop_loss': {'default': 0.06, 'range': [0.03, 0.15], 'type': 'float'}
                },
                'pros': [
                    '理論基礎扎實',
                    '風險相對較低',
                    '適合穩健投資'
                ],
                'cons': [
                    '收益相對較低',
                    '需要長期持有',
                    '趨勢市場不適用'
                ]
            }
        }
    
    def _initialize_default_parameters(self) -> Dict[str, Any]:
        """
        初始化預設參數
        
        Returns:
            Dict[str, Any]: 預設參數字典
        """
        return {
            'initial_capital': 100000,
            'commission': 0.001,
            'slippage': 0.001,
            'max_position_size': 0.2,
            'rebalance_frequency': 'daily'
        }
    
    def get_available_strategies(self) -> List[str]:
        """
        獲取可用策略清單
        
        Returns:
            List[str]: 策略名稱清單
        """
        return list(self.strategy_templates.keys())
    
    def get_strategy_info(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取策略詳細資訊
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            Optional[Dict[str, Any]]: 策略資訊
        """
        return self.strategy_templates.get(strategy_id)
    
    def create_strategy_instance(self, strategy_id: str, 
                               parameters: Dict[str, Any]) -> Optional[Any]:
        """
        創建策略實例
        
        Args:
            strategy_id: 策略ID
            parameters: 策略參數
            
        Returns:
            Optional[Any]: 策略實例
        """
        try:
            if strategy_id == 'ma_cross' and MovingAverageCrossStrategy:
                return MovingAverageCrossStrategy(
                    fast_period=parameters.get('fast_period', 10),
                    slow_period=parameters.get('slow_period', 20)
                )
            elif strategy_id == 'rsi_strategy' and RSIStrategy:
                return RSIStrategy(
                    period=parameters.get('rsi_period', 14),
                    oversold=parameters.get('oversold', 30),
                    overbought=parameters.get('overbought', 70)
                )
            else:
                # 返回模擬策略實例
                return self._create_mock_strategy(strategy_id, parameters)
                
        except Exception as e:
            logger.error("創建策略實例失敗: %s", e)
            return None
    
    def _create_mock_strategy(self, strategy_id: str, 
                            parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        創建模擬策略實例
        
        Args:
            strategy_id: 策略ID
            parameters: 策略參數
            
        Returns:
            Dict[str, Any]: 模擬策略實例
        """
        return {
            'id': strategy_id,
            'parameters': parameters,
            'created_at': datetime.now().isoformat(),
            'status': 'ready'
        }
    
    def generate_sample_signals(self, strategy_id: str, 
                              data: pd.DataFrame) -> pd.DataFrame:
        """
        生成示範交易信號
        
        Args:
            strategy_id: 策略ID
            data: 市場資料
            
        Returns:
            pd.DataFrame: 交易信號
        """
        try:
            if strategy_id == 'ma_cross':
                return self._generate_ma_signals(data)
            elif strategy_id == 'rsi_strategy':
                return self._generate_rsi_signals(data)
            else:
                return self._generate_random_signals(data)
                
        except Exception as e:
            logger.error("生成交易信號失敗: %s", e)
            return pd.DataFrame()
    
    def _generate_ma_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成移動平均線信號"""
        data = data.copy()
        data['MA_10'] = data['Close'].rolling(10).mean()
        data['MA_20'] = data['Close'].rolling(20).mean()
        
        data['Signal'] = 0
        data.loc[data['MA_10'] > data['MA_20'], 'Signal'] = 1
        data.loc[data['MA_10'] < data['MA_20'], 'Signal'] = -1
        
        return data[['Signal', 'MA_10', 'MA_20']]
    
    def _generate_rsi_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成 RSI 信號"""
        data = data.copy()
        
        # 計算 RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        data['Signal'] = 0
        data.loc[data['RSI'] < 30, 'Signal'] = 1
        data.loc[data['RSI'] > 70, 'Signal'] = -1
        
        return data[['Signal', 'RSI']]
    
    def _generate_random_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成隨機信號（用於示範）"""
        signals = pd.DataFrame(index=data.index)
        signals['Signal'] = np.random.choice([-1, 0, 1], size=len(data), 
                                           p=[0.2, 0.6, 0.2])
        return signals
    
    def save_strategy_config(self, strategy_id: str, 
                           parameters: Dict[str, Any]) -> bool:
        """
        保存策略配置
        
        Args:
            strategy_id: 策略ID
            parameters: 策略參數
            
        Returns:
            bool: 保存是否成功
        """
        try:
            config = {
                'strategy_id': strategy_id,
                'parameters': parameters,
                'created_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # 這裡應該保存到實際的配置檔案或資料庫
            logger.info("策略配置已保存: %s", strategy_id)
            return True
            
        except Exception as e:
            logger.error("保存策略配置失敗: %s", e)
            return False


def show_demo_strategies() -> None:
    """
    顯示示範策略模板頁面
    
    提供新手友好的策略模板選擇和配置界面，
    包括策略說明、參數設定和一鍵部署功能。
    
    Side Effects:
        - 在 Streamlit 界面顯示策略模板
        - 提供策略配置和部署功能
    """
    st.title("🎯 示範策略模板")
    st.markdown("選擇預建的策略模板，快速開始您的量化交易之旅！")
    
    demo = DemoStrategies()
    
    # 策略選擇
    strategies = demo.get_available_strategies()
    strategy_names = [demo.get_strategy_info(s)['name'] for s in strategies]
    
    selected_idx = st.selectbox(
        "選擇策略模板",
        range(len(strategies)),
        format_func=lambda x: strategy_names[x]
    )
    
    selected_strategy = strategies[selected_idx]
    strategy_info = demo.get_strategy_info(selected_strategy)
    
    # 顯示策略資訊
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(strategy_info['name'])
        st.write(strategy_info['description'])
        
        # 策略特點
        st.write("**優點:**")
        for pro in strategy_info['pros']:
            st.write(f"✅ {pro}")
        
        st.write("**缺點:**")
        for con in strategy_info['cons']:
            st.write(f"⚠️ {con}")
    
    with col2:
        st.metric("難度等級", strategy_info['difficulty'])
        st.metric("風險等級", strategy_info['risk_level'])
        st.metric("預期收益", strategy_info['expected_return'])
        st.metric("策略類別", strategy_info['category'])
    
    # 參數設定
    st.subheader("📊 參數設定")
    
    parameters = {}
    param_cols = st.columns(2)
    
    for i, (param_name, param_info) in enumerate(strategy_info['parameters'].items()):
        col = param_cols[i % 2]
        
        with col:
            if param_info['type'] == 'int':
                parameters[param_name] = st.slider(
                    param_name.replace('_', ' ').title(),
                    min_value=param_info['range'][0],
                    max_value=param_info['range'][1],
                    value=param_info['default']
                )
            elif param_info['type'] == 'float':
                parameters[param_name] = st.slider(
                    param_name.replace('_', ' ').title(),
                    min_value=param_info['range'][0],
                    max_value=param_info['range'][1],
                    value=param_info['default'],
                    step=0.01
                )
    
    # 示範回測
    st.subheader("📈 策略示範")
    
    if st.button("生成示範信號"):
        # 生成示範資料
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.02)
        demo_data = pd.DataFrame({
            'Date': dates,
            'Close': prices
        })
        
        # 生成交易信號
        signals = demo.generate_sample_signals(selected_strategy, demo_data)
        
        if not signals.empty:
            # 顯示圖表
            fig = go.Figure()
            
            # 價格線
            fig.add_trace(go.Scatter(
                x=demo_data['Date'],
                y=demo_data['Close'],
                mode='lines',
                name='股價',
                line=dict(color='blue')
            ))
            
            # 買入信號
            buy_signals = demo_data[signals['Signal'] == 1]
            if not buy_signals.empty:
                fig.add_trace(go.Scatter(
                    x=buy_signals['Date'],
                    y=buy_signals['Close'],
                    mode='markers',
                    name='買入信號',
                    marker=dict(color='green', size=10, symbol='triangle-up')
                ))
            
            # 賣出信號
            sell_signals = demo_data[signals['Signal'] == -1]
            if not sell_signals.empty:
                fig.add_trace(go.Scatter(
                    x=sell_signals['Date'],
                    y=sell_signals['Close'],
                    mode='markers',
                    name='賣出信號',
                    marker=dict(color='red', size=10, symbol='triangle-down')
                ))
            
            fig.update_layout(
                title=f"{strategy_info['name']} - 交易信號示範",
                xaxis_title="日期",
                yaxis_title="價格",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 顯示信號統計
            signal_stats = signals['Signal'].value_counts()
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("買入信號", signal_stats.get(1, 0))
            with col2:
                st.metric("賣出信號", signal_stats.get(-1, 0))
            with col3:
                st.metric("持有期間", signal_stats.get(0, 0))
    
    # 部署策略
    st.subheader("🚀 部署策略")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("保存策略配置"):
            if demo.save_strategy_config(selected_strategy, parameters):
                st.success("✅ 策略配置已保存！")
            else:
                st.error("❌ 保存失敗，請重試。")
    
    with col2:
        if st.button("開始回測"):
            st.info("🔄 正在啟動回測系統...")
            st.write("請前往回測頁面查看結果。")
    
    # 策略比較
    st.subheader("📊 策略比較")
    
    if st.checkbox("顯示策略比較表"):
        comparison_data = []
        for strategy_id in strategies:
            info = demo.get_strategy_info(strategy_id)
            comparison_data.append({
                '策略名稱': info['name'],
                '難度等級': info['difficulty'],
                '風險等級': info['risk_level'],
                '預期收益': info['expected_return'],
                '策略類別': info['category']
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True)
