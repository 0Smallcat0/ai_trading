# -*- coding: utf-8 -*-
"""
模擬交易練習環境

此模組提供新手友好的模擬交易練習環境，包括：
- 虛擬資金交易
- 實時市場模擬
- 交易技能訓練
- 風險管理練習
- 績效評估和反饋

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

# 導入現有組件
from ..components.common import UIComponents
from ..responsive import ResponsiveUtils

logger = logging.getLogger(__name__)


class PracticeMode:
    """
    模擬交易練習環境管理器
    
    提供新手友好的模擬交易環境，包括虛擬資金管理、
    實時市場模擬和交易技能訓練。
    
    Attributes:
        virtual_portfolio (Dict): 虛擬投資組合
        practice_sessions (List): 練習會話記錄
        skill_assessments (Dict): 技能評估結果
        
    Example:
        >>> practice = PracticeMode()
        >>> practice.start_practice_session()
        >>> practice.execute_virtual_trade('AAPL', 'buy', 100)
    """
    
    def __init__(self):
        """初始化模擬交易練習環境"""
        self.virtual_portfolio = self._initialize_virtual_portfolio()
        self.practice_sessions = []
        self.skill_assessments = {}
        self.market_scenarios = self._initialize_market_scenarios()
        
    def _initialize_virtual_portfolio(self) -> Dict[str, Any]:
        """
        初始化虛擬投資組合
        
        Returns:
            Dict[str, Any]: 虛擬投資組合
        """
        return {
            'cash': 100000.0,  # 虛擬現金
            'positions': {},   # 持倉
            'transaction_history': [],  # 交易記錄
            'performance_metrics': {
                'total_value': 100000.0,
                'total_return': 0.0,
                'win_rate': 0.0,
                'max_drawdown': 0.0
            }
        }
    
    def _initialize_market_scenarios(self) -> List[Dict[str, Any]]:
        """
        初始化市場情境
        
        Returns:
            List[Dict[str, Any]]: 市場情境清單
        """
        return [
            {
                'name': '牛市情境',
                'description': '市場持續上漲，適合練習趨勢跟隨策略',
                'trend': 'bullish',
                'volatility': 'low',
                'duration_days': 30,
                'difficulty': '初級'
            },
            {
                'name': '熊市情境',
                'description': '市場持續下跌，練習風險控制和空頻策略',
                'trend': 'bearish',
                'volatility': 'medium',
                'duration_days': 20,
                'difficulty': '中級'
            },
            {
                'name': '震盪市場',
                'description': '市場橫盤整理，適合練習區間交易',
                'trend': 'sideways',
                'volatility': 'high',
                'duration_days': 40,
                'difficulty': '中級'
            },
            {
                'name': '極端波動',
                'description': '市場劇烈波動，考驗風險管理能力',
                'trend': 'volatile',
                'volatility': 'extreme',
                'duration_days': 15,
                'difficulty': '高級'
            }
        ]
    
    def start_practice_session(self, scenario_name: str) -> str:
        """
        開始練習會話
        
        Args:
            scenario_name: 市場情境名稱
            
        Returns:
            str: 會話ID
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = {
            'session_id': session_id,
            'scenario': scenario_name,
            'start_time': datetime.now().isoformat(),
            'status': 'active',
            'trades': [],
            'initial_portfolio': self.virtual_portfolio.copy()
        }
        
        self.practice_sessions.append(session)
        logger.info("練習會話已開始: %s", session_id)
        
        return session_id
    
    def execute_virtual_trade(self, symbol: str, action: str, 
                            quantity: int, price: Optional[float] = None) -> bool:
        """
        執行虛擬交易
        
        Args:
            symbol: 股票代碼
            action: 交易動作 ('buy' 或 'sell')
            quantity: 交易數量
            price: 交易價格（如果為 None 則使用市價）
            
        Returns:
            bool: 交易是否成功
        """
        try:
            if price is None:
                price = self._get_current_price(symbol)
            
            trade_value = quantity * price
            commission = trade_value * 0.001  # 0.1% 手續費
            
            if action.lower() == 'buy':
                total_cost = trade_value + commission
                
                if self.virtual_portfolio['cash'] >= total_cost:
                    # 執行買入
                    self.virtual_portfolio['cash'] -= total_cost
                    
                    if symbol in self.virtual_portfolio['positions']:
                        self.virtual_portfolio['positions'][symbol]['quantity'] += quantity
                        # 更新平均成本
                        old_cost = (self.virtual_portfolio['positions'][symbol]['avg_price'] * 
                                  self.virtual_portfolio['positions'][symbol]['quantity'])
                        new_avg_price = (old_cost + trade_value) / (
                            self.virtual_portfolio['positions'][symbol]['quantity'] + quantity)
                        self.virtual_portfolio['positions'][symbol]['avg_price'] = new_avg_price
                    else:
                        self.virtual_portfolio['positions'][symbol] = {
                            'quantity': quantity,
                            'avg_price': price,
                            'current_price': price
                        }
                    
                    self._record_transaction(symbol, action, quantity, price, commission)
                    return True
                else:
                    logger.warning("資金不足，無法執行買入交易")
                    return False
                    
            elif action.lower() == 'sell':
                if (symbol in self.virtual_portfolio['positions'] and 
                    self.virtual_portfolio['positions'][symbol]['quantity'] >= quantity):
                    
                    # 執行賣出
                    self.virtual_portfolio['cash'] += trade_value - commission
                    self.virtual_portfolio['positions'][symbol]['quantity'] -= quantity
                    
                    if self.virtual_portfolio['positions'][symbol]['quantity'] == 0:
                        del self.virtual_portfolio['positions'][symbol]
                    
                    self._record_transaction(symbol, action, quantity, price, commission)
                    return True
                else:
                    logger.warning("持倉不足，無法執行賣出交易")
                    return False
            
            return False
            
        except Exception as e:
            logger.error("執行虛擬交易失敗: %s", e)
            return False
    
    def _get_current_price(self, symbol: str) -> float:
        """
        獲取當前價格（模擬）
        
        Args:
            symbol: 股票代碼
            
        Returns:
            float: 當前價格
        """
        # 模擬價格生成
        base_price = 100.0
        random_factor = np.random.normal(1.0, 0.02)
        return base_price * random_factor
    
    def _record_transaction(self, symbol: str, action: str, 
                          quantity: int, price: float, commission: float) -> None:
        """
        記錄交易
        
        Args:
            symbol: 股票代碼
            action: 交易動作
            quantity: 交易數量
            price: 交易價格
            commission: 手續費
        """
        transaction = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'total_value': quantity * price
        }
        
        self.virtual_portfolio['transaction_history'].append(transaction)
    
    def update_portfolio_value(self) -> None:
        """更新投資組合價值"""
        total_value = self.virtual_portfolio['cash']
        
        for symbol, position in self.virtual_portfolio['positions'].items():
            current_price = self._get_current_price(symbol)
            position['current_price'] = current_price
            total_value += position['quantity'] * current_price
        
        self.virtual_portfolio['performance_metrics']['total_value'] = total_value
        
        # 計算總收益率
        initial_value = 100000.0
        total_return = (total_value - initial_value) / initial_value
        self.virtual_portfolio['performance_metrics']['total_return'] = total_return
    
    def calculate_performance_metrics(self) -> Dict[str, float]:
        """
        計算績效指標
        
        Returns:
            Dict[str, float]: 績效指標
        """
        transactions = self.virtual_portfolio['transaction_history']
        
        if not transactions:
            return self.virtual_portfolio['performance_metrics']
        
        # 計算勝率
        profitable_trades = 0
        total_trades = 0
        
        for i in range(1, len(transactions)):
            if transactions[i]['action'] == 'sell':
                # 找到對應的買入交易
                symbol = transactions[i]['symbol']
                sell_price = transactions[i]['price']
                
                # 簡化計算：假設 FIFO
                for j in range(i-1, -1, -1):
                    if (transactions[j]['symbol'] == symbol and 
                        transactions[j]['action'] == 'buy'):
                        buy_price = transactions[j]['price']
                        if sell_price > buy_price:
                            profitable_trades += 1
                        total_trades += 1
                        break
        
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        self.virtual_portfolio['performance_metrics']['win_rate'] = win_rate
        
        return self.virtual_portfolio['performance_metrics']
    
    def generate_market_data(self, scenario: Dict[str, Any], 
                           days: int = 30) -> pd.DataFrame:
        """
        生成市場資料
        
        Args:
            scenario: 市場情境
            days: 天數
            
        Returns:
            pd.DataFrame: 市場資料
        """
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                            periods=days, freq='D')
        
        # 根據情境生成價格
        if scenario['trend'] == 'bullish':
            trend = 0.001  # 每日上漲 0.1%
            volatility = 0.01
        elif scenario['trend'] == 'bearish':
            trend = -0.001  # 每日下跌 0.1%
            volatility = 0.015
        elif scenario['trend'] == 'sideways':
            trend = 0.0
            volatility = 0.02
        else:  # volatile
            trend = 0.0
            volatility = 0.05
        
        # 生成價格序列
        returns = np.random.normal(trend, volatility, days)
        prices = 100 * np.exp(np.cumsum(returns))
        
        volumes = np.random.randint(1000000, 5000000, days)
        
        return pd.DataFrame({
            'Date': dates,
            'Close': prices,
            'Volume': volumes,
            'Returns': returns
        })
    
    def assess_trading_skills(self) -> Dict[str, float]:
        """
        評估交易技能
        
        Returns:
            Dict[str, float]: 技能評估結果
        """
        metrics = self.calculate_performance_metrics()
        
        # 技能評分 (0-100)
        skills = {
            'risk_management': min(100, max(0, (1 - abs(metrics.get('max_drawdown', 0))) * 100)),
            'profit_ability': min(100, max(0, metrics.get('total_return', 0) * 100 + 50)),
            'consistency': min(100, max(0, metrics.get('win_rate', 0) * 100)),
            'market_timing': 70,  # 簡化評估
            'overall_score': 0
        }
        
        # 計算總分
        skills['overall_score'] = np.mean(list(skills.values())[:-1])
        
        self.skill_assessments = skills
        return skills


def show_practice_mode() -> None:
    """
    顯示模擬交易練習環境頁面
    
    提供新手友好的模擬交易環境，包括虛擬資金管理、
    實時市場模擬和交易技能訓練。
    
    Side Effects:
        - 在 Streamlit 界面顯示練習環境
        - 管理虛擬交易和投資組合
    """
    st.title("🎮 模擬交易練習")
    st.markdown("在安全的虛擬環境中練習交易技能，無風險學習量化交易！")
    
    # 初始化練習模式
    if 'practice_mode' not in st.session_state:
        st.session_state.practice_mode = PracticeMode()
    
    practice = st.session_state.practice_mode
    
    # 側邊欄：投資組合概覽
    with st.sidebar:
        st.subheader("💰 虛擬投資組合")
        
        practice.update_portfolio_value()
        metrics = practice.calculate_performance_metrics()
        
        st.metric("總資產", f"${metrics['total_value']:,.2f}")
        st.metric("現金", f"${practice.virtual_portfolio['cash']:,.2f}")
        st.metric("總收益率", f"{metrics['total_return']:.2%}")
        st.metric("勝率", f"{metrics['win_rate']:.1%}")
        
        # 持倉概覽
        if practice.virtual_portfolio['positions']:
            st.subheader("📊 當前持倉")
            for symbol, position in practice.virtual_portfolio['positions'].items():
                st.write(f"**{symbol}**")
                st.write(f"數量: {position['quantity']}")
                st.write(f"均價: ${position['avg_price']:.2f}")
                st.write("---")
    
    # 主要內容區域
    tab1, tab2, tab3, tab4 = st.tabs(["市場情境", "虛擬交易", "績效分析", "技能評估"])
    
    with tab1:
        st.subheader("🌍 選擇市場情境")
        
        scenarios = practice.market_scenarios
        scenario_names = [s['name'] for s in scenarios]
        
        selected_scenario_idx = st.selectbox(
            "選擇練習情境",
            range(len(scenarios)),
            format_func=lambda x: scenario_names[x]
        )
        
        selected_scenario = scenarios[selected_scenario_idx]
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"**{selected_scenario['name']}**")
            st.write(selected_scenario['description'])
            
            # 生成並顯示市場資料
            if st.button("生成市場資料"):
                market_data = practice.generate_market_data(selected_scenario)
                
                fig = px.line(market_data, x='Date', y='Close', 
                            title=f"{selected_scenario['name']} - 價格走勢")
                st.plotly_chart(fig, use_container_width=True)
                
                st.session_state.current_market_data = market_data
        
        with col2:
            st.metric("難度等級", selected_scenario['difficulty'])
            st.metric("趨勢類型", selected_scenario['trend'])
            st.metric("波動程度", selected_scenario['volatility'])
            st.metric("持續天數", f"{selected_scenario['duration_days']} 天")
    
    with tab2:
        st.subheader("💹 虛擬交易")
        
        # 交易面板
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**買入交易**")
            buy_symbol = st.text_input("股票代碼", value="AAPL", key="buy_symbol")
            buy_quantity = st.number_input("買入數量", min_value=1, value=100, key="buy_qty")
            buy_price = st.number_input("買入價格", min_value=0.01, value=100.0, key="buy_price")
            
            if st.button("執行買入"):
                if practice.execute_virtual_trade(buy_symbol, 'buy', buy_quantity, buy_price):
                    st.success(f"✅ 成功買入 {buy_quantity} 股 {buy_symbol}")
                else:
                    st.error("❌ 買入失敗，請檢查資金是否充足")
        
        with col2:
            st.write("**賣出交易**")
            sell_symbol = st.text_input("股票代碼", value="AAPL", key="sell_symbol")
            sell_quantity = st.number_input("賣出數量", min_value=1, value=100, key="sell_qty")
            sell_price = st.number_input("賣出價格", min_value=0.01, value=100.0, key="sell_price")
            
            if st.button("執行賣出"):
                if practice.execute_virtual_trade(sell_symbol, 'sell', sell_quantity, sell_price):
                    st.success(f"✅ 成功賣出 {sell_quantity} 股 {sell_symbol}")
                else:
                    st.error("❌ 賣出失敗，請檢查持倉是否充足")
        
        # 交易記錄
        st.subheader("📋 交易記錄")
        
        if practice.virtual_portfolio['transaction_history']:
            transactions_df = pd.DataFrame(practice.virtual_portfolio['transaction_history'])
            transactions_df['timestamp'] = pd.to_datetime(transactions_df['timestamp'])
            transactions_df = transactions_df.sort_values('timestamp', ascending=False)
            
            st.dataframe(transactions_df, use_container_width=True)
        else:
            st.info("尚無交易記錄")
    
    with tab3:
        st.subheader("📈 績效分析")
        
        metrics = practice.calculate_performance_metrics()
        
        # 績效指標
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("總資產", f"${metrics['total_value']:,.2f}")
        with col2:
            st.metric("總收益率", f"{metrics['total_return']:.2%}")
        with col3:
            st.metric("勝率", f"{metrics['win_rate']:.1%}")
        with col4:
            st.metric("最大回撤", f"{metrics.get('max_drawdown', 0):.2%}")
        
        # 資產變化圖表
        if practice.virtual_portfolio['transaction_history']:
            st.subheader("💰 資產變化趨勢")
            
            # 簡化的資產變化計算
            transactions = practice.virtual_portfolio['transaction_history']
            asset_history = []
            current_value = 100000.0
            
            for transaction in transactions:
                if transaction['action'] == 'buy':
                    current_value -= transaction['total_value'] + transaction['commission']
                else:
                    current_value += transaction['total_value'] - transaction['commission']
                
                asset_history.append({
                    'timestamp': transaction['timestamp'],
                    'total_value': current_value
                })
            
            if asset_history:
                asset_df = pd.DataFrame(asset_history)
                asset_df['timestamp'] = pd.to_datetime(asset_df['timestamp'])
                
                fig = px.line(asset_df, x='timestamp', y='total_value',
                            title='資產變化趨勢')
                st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.subheader("🎯 技能評估")
        
        if st.button("評估交易技能"):
            skills = practice.assess_trading_skills()
            
            # 技能雷達圖
            categories = ['風險管理', '盈利能力', '一致性', '市場時機']
            values = [
                skills['risk_management'],
                skills['profit_ability'],
                skills['consistency'],
                skills['market_timing']
            ]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name='技能評分'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                showlegend=True,
                title="交易技能評估"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 技能評分詳情
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("風險管理", f"{skills['risk_management']:.1f}/100")
                st.metric("盈利能力", f"{skills['profit_ability']:.1f}/100")
            
            with col2:
                st.metric("一致性", f"{skills['consistency']:.1f}/100")
                st.metric("市場時機", f"{skills['market_timing']:.1f}/100")
            
            st.metric("總體評分", f"{skills['overall_score']:.1f}/100")
            
            # 改進建議
            st.subheader("💡 改進建議")
            
            if skills['risk_management'] < 70:
                st.warning("🛡️ 建議加強風險管理：設定合理的停損點，控制單筆交易風險")
            
            if skills['profit_ability'] < 60:
                st.warning("💰 建議提升盈利能力：學習更多交易策略，提高選股能力")
            
            if skills['consistency'] < 50:
                st.warning("📊 建議提高一致性：制定交易計劃並嚴格執行，避免情緒化交易")
            
            if skills['overall_score'] >= 80:
                st.success("🎉 恭喜！您的交易技能已達到優秀水平！")
            elif skills['overall_score'] >= 60:
                st.info("👍 您的交易技能良好，繼續練習可以進一步提升")
            else:
                st.warning("📚 建議多加練習，學習更多交易知識和技巧")
