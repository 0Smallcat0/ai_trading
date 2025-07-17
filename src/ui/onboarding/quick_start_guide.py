# -*- coding: utf-8 -*-
"""
互動式快速入門教程

此模組提供新手友好的快速入門教程，包括：
- 系統功能介紹
- 基本操作演示
- 互動式學習步驟
- 實時指導和提示
- 進度追蹤

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any
import logging

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 導入現有組件
from ..components.common import UIComponents
from ..responsive import ResponsiveUtils

logger = logging.getLogger(__name__)


class QuickStartGuide:
    """
    互動式快速入門教程
    
    提供新手友好的系統學習流程，包括功能介紹、
    操作演示和互動式學習步驟。
    
    Attributes:
        tutorial_steps (List[Dict]): 教程步驟清單
        current_step (int): 當前步驟索引
        user_progress (Dict): 用戶學習進度
        
    Example:
        >>> guide = QuickStartGuide()
        >>> guide.start_tutorial()
    """
    
    def __init__(self):
        """初始化快速入門教程"""
        self.tutorial_steps = self._initialize_tutorial_steps()
        self.current_step = 0
        self.user_progress = {}
        
    def _initialize_tutorial_steps(self) -> List[Dict[str, Any]]:
        """
        初始化教程步驟
        
        Returns:
            List[Dict[str, Any]]: 教程步驟清單
        """
        return [
            {
                'title': '歡迎使用 AI 交易系統',
                'description': '了解系統的核心功能和優勢',
                'content': self._get_welcome_content(),
                'interactive': False,
                'estimated_time': 2
            },
            {
                'title': '資料管理基礎',
                'description': '學習如何管理和查看市場資料',
                'content': self._get_data_management_content(),
                'interactive': True,
                'estimated_time': 5
            },
            {
                'title': '策略創建入門',
                'description': '創建您的第一個交易策略',
                'content': self._get_strategy_creation_content(),
                'interactive': True,
                'estimated_time': 8
            },
            {
                'title': '回測系統使用',
                'description': '學習如何進行策略回測',
                'content': self._get_backtest_content(),
                'interactive': True,
                'estimated_time': 10
            },
            {
                'title': '風險管理設定',
                'description': '設定風險控制參數',
                'content': self._get_risk_management_content(),
                'interactive': True,
                'estimated_time': 6
            },
            {
                'title': '系統監控概覽',
                'description': '了解如何監控系統狀態',
                'content': self._get_monitoring_content(),
                'interactive': False,
                'estimated_time': 4
            }
        ]
    
    def _get_welcome_content(self) -> Dict[str, Any]:
        """獲取歡迎內容"""
        return {
            'text': """
            ## 🎉 歡迎使用 AI 交易系統！
            
            這是一個專為量化交易設計的智能系統，具備以下核心功能：
            
            ### 🔍 智能資料分析
            - 多源資料整合
            - 實時市場監控
            - 技術指標計算
            
            ### 🤖 AI 策略引擎
            - 機器學習模型
            - 策略自動優化
            - 風險智能控制
            
            ### 📊 專業回測系統
            - 歷史資料回測
            - 績效分析報告
            - 多策略比較
            
            ### 🛡️ 風險管理
            - 實時風險監控
            - 動態停損機制
            - 資金管理策略
            """,
            'features': [
                '智能資料分析', 'AI 策略引擎', 
                '專業回測系統', '風險管理'
            ]
        }
    
    def _get_data_management_content(self) -> Dict[str, Any]:
        """獲取資料管理內容"""
        return {
            'text': """
            ## 📈 資料管理基礎
            
            資料是量化交易的基礎。讓我們學習如何管理市場資料：
            
            ### 資料來源
            - Yahoo Finance
            - 券商 API
            - 第三方資料提供商
            
            ### 資料類型
            - 股價資料（OHLCV）
            - 技術指標
            - 基本面資料
            - 市場情緒指標
            """,
            'demo_data': self._generate_demo_data(),
            'interactive_task': '請選擇一個股票代碼查看資料'
        }
    
    def _get_strategy_creation_content(self) -> Dict[str, Any]:
        """獲取策略創建內容"""
        return {
            'text': """
            ## 🎯 策略創建入門
            
            創建交易策略是系統的核心功能：
            
            ### 策略類型
            - 技術分析策略
            - 機器學習策略
            - 量化因子策略
            
            ### 創建步驟
            1. 選擇策略模板
            2. 設定參數
            3. 回測驗證
            4. 部署執行
            """,
            'strategy_templates': [
                '移動平均線交叉', 'RSI 策略', 
                '動量策略', '均值回歸'
            ]
        }
    
    def _get_backtest_content(self) -> Dict[str, Any]:
        """獲取回測內容"""
        return {
            'text': """
            ## 🔬 回測系統使用
            
            回測幫助您驗證策略的有效性：
            
            ### 回測流程
            1. 選擇策略
            2. 設定時間範圍
            3. 配置參數
            4. 執行回測
            5. 分析結果
            
            ### 關鍵指標
            - 總收益率
            - 夏普比率
            - 最大回撤
            - 勝率
            """,
            'sample_results': self._generate_sample_backtest_results()
        }
    
    def _get_risk_management_content(self) -> Dict[str, Any]:
        """獲取風險管理內容"""
        return {
            'text': """
            ## 🛡️ 風險管理設定
            
            風險管理是交易成功的關鍵：
            
            ### 風險控制方法
            - 停損設定
            - 部位大小控制
            - 最大虧損限制
            - 相關性控制
            
            ### 風險指標
            - VaR (風險價值)
            - 波動率
            - 貝塔係數
            - 相關係數
            """,
            'risk_parameters': {
                'stop_loss': 0.05,
                'position_size': 0.1,
                'max_drawdown': 0.15
            }
        }
    
    def _get_monitoring_content(self) -> Dict[str, Any]:
        """獲取監控內容"""
        return {
            'text': """
            ## 📊 系統監控概覽
            
            監控系統狀態確保穩定運行：
            
            ### 監控項目
            - 系統效能
            - 交易狀態
            - 風險指標
            - 資金狀況
            
            ### 警報機制
            - 即時通知
            - 風險警報
            - 系統異常
            - 績效提醒
            """
        }
    
    def _generate_demo_data(self) -> pd.DataFrame:
        """生成示範資料"""
        import numpy as np
        
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.02)
        
        return pd.DataFrame({
            'Date': dates,
            'Close': prices,
            'Volume': np.random.randint(1000000, 5000000, 100)
        })
    
    def _generate_sample_backtest_results(self) -> Dict[str, float]:
        """生成示範回測結果"""
        return {
            'total_return': 0.15,
            'sharpe_ratio': 1.2,
            'max_drawdown': -0.08,
            'win_rate': 0.65,
            'profit_factor': 1.8
        }
    
    def get_step_content(self, step_index: int) -> Optional[Dict[str, Any]]:
        """
        獲取指定步驟的內容
        
        Args:
            step_index: 步驟索引
            
        Returns:
            Optional[Dict[str, Any]]: 步驟內容
        """
        if 0 <= step_index < len(self.tutorial_steps):
            return self.tutorial_steps[step_index]
        return None
    
    def mark_step_completed(self, step_index: int) -> None:
        """
        標記步驟為已完成
        
        Args:
            step_index: 步驟索引
        """
        self.user_progress[step_index] = True
        logger.info("步驟 %d 已完成", step_index)
    
    def get_progress_percentage(self) -> float:
        """
        獲取學習進度百分比
        
        Returns:
            float: 進度百分比 (0-100)
        """
        completed_steps = len(self.user_progress)
        total_steps = len(self.tutorial_steps)
        return (completed_steps / total_steps) * 100 if total_steps > 0 else 0


def show_quick_start_guide() -> None:
    """
    顯示快速入門教程頁面
    
    提供互動式的系統學習流程，包括功能介紹、
    操作演示和實時指導。
    
    Side Effects:
        - 在 Streamlit 界面顯示快速入門教程
        - 追蹤用戶學習進度
    """
    st.title("🎓 快速入門教程")
    
    # 初始化教程
    if 'guide' not in st.session_state:
        st.session_state.guide = QuickStartGuide()
    
    guide = st.session_state.guide
    
    # 顯示進度
    progress = guide.get_progress_percentage()
    st.progress(progress / 100)
    st.write(f"學習進度: {progress:.1f}%")
    
    # 步驟選擇
    step_titles = [step['title'] for step in guide.tutorial_steps]
    selected_step = st.selectbox(
        "選擇教程步驟",
        range(len(step_titles)),
        format_func=lambda x: f"{x+1}. {step_titles[x]}"
    )
    
    # 顯示當前步驟
    current_step = guide.get_step_content(selected_step)
    if current_step:
        st.header(current_step['title'])
        st.write(f"⏱️ 預計時間: {current_step['estimated_time']} 分鐘")
        st.markdown(current_step['description'])
        
        # 顯示內容
        content = current_step['content']
        st.markdown(content['text'])
        
        # 互動式內容
        if current_step['interactive']:
            if 'demo_data' in content:
                st.subheader("📊 示範資料")
                demo_data = content['demo_data']
                st.dataframe(demo_data.head())
                
                # 簡單圖表
                fig = px.line(demo_data, x='Date', y='Close', 
                            title='股價走勢圖')
                st.plotly_chart(fig, use_container_width=True)
            
            if 'strategy_templates' in content:
                st.subheader("🎯 策略模板")
                selected_template = st.selectbox(
                    "選擇策略模板",
                    content['strategy_templates']
                )
                st.info(f"您選擇了: {selected_template}")
            
            if 'sample_results' in content:
                st.subheader("📈 示範回測結果")
                results = content['sample_results']
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("總收益率", f"{results['total_return']:.1%}")
                    st.metric("夏普比率", f"{results['sharpe_ratio']:.2f}")
                
                with col2:
                    st.metric("最大回撤", f"{results['max_drawdown']:.1%}")
                    st.metric("勝率", f"{results['win_rate']:.1%}")
        
        # 完成按鈕
        if st.button(f"完成步驟 {selected_step + 1}"):
            guide.mark_step_completed(selected_step)
            st.success("✅ 步驟已完成！")
            st.rerun()
    
    # 導航按鈕
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if selected_step > 0:
            if st.button("⬅️ 上一步"):
                st.session_state.selected_step = selected_step - 1
                st.rerun()
    
    with col3:
        if selected_step < len(guide.tutorial_steps) - 1:
            if st.button("下一步 ➡️"):
                st.session_state.selected_step = selected_step + 1
                st.rerun()
    
    # 完成教程
    if progress >= 100:
        st.balloons()
        st.success("🎉 恭喜！您已完成快速入門教程！")
        st.info("現在您可以開始使用 AI 交易系統的各項功能了。")
