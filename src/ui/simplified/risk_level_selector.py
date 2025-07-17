# -*- coding: utf-8 -*-
"""
風險等級選擇器

此模組提供新手友好的風險等級選擇功能，包括：
- 風險評估問卷
- 風險等級匹配
- 個人化風險配置
- 風險教育內容
- 動態風險調整

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime
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


class RiskLevelSelector:
    """
    風險等級選擇器
    
    提供新手友好的風險評估和等級選擇功能，包括風險問卷、
    等級匹配、個人化配置和教育內容。
    
    Attributes:
        risk_questionnaire (Dict): 風險評估問卷
        risk_levels (Dict): 風險等級定義
        user_profile (Dict): 用戶風險檔案
        
    Example:
        >>> selector = RiskLevelSelector()
        >>> risk_level = selector.assess_risk_level(answers)
        >>> config = selector.get_risk_configuration(risk_level)
    """
    
    def __init__(self):
        """初始化風險等級選擇器"""
        self.risk_questionnaire = self._initialize_questionnaire()
        self.risk_levels = self._initialize_risk_levels()
        self.user_profile = {}
        
    def _initialize_questionnaire(self) -> Dict[str, Any]:
        """
        初始化風險評估問卷
        
        Returns:
            Dict[str, Any]: 風險評估問卷
        """
        return {
            'questions': [
                {
                    'id': 'experience',
                    'question': '您的投資經驗如何？',
                    'type': 'single_choice',
                    'options': [
                        {'text': '完全沒有經驗', 'score': 1},
                        {'text': '少於1年', 'score': 2},
                        {'text': '1-3年', 'score': 3},
                        {'text': '3-5年', 'score': 4},
                        {'text': '5年以上', 'score': 5}
                    ],
                    'weight': 0.2
                },
                {
                    'id': 'loss_tolerance',
                    'question': '您能接受的最大虧損是多少？',
                    'type': 'single_choice',
                    'options': [
                        {'text': '完全不能接受虧損', 'score': 1},
                        {'text': '最多5%的虧損', 'score': 2},
                        {'text': '最多10%的虧損', 'score': 3},
                        {'text': '最多20%的虧損', 'score': 4},
                        {'text': '可以接受更大虧損', 'score': 5}
                    ],
                    'weight': 0.25
                },
                {
                    'id': 'investment_horizon',
                    'question': '您的投資期限是多久？',
                    'type': 'single_choice',
                    'options': [
                        {'text': '少於3個月', 'score': 2},
                        {'text': '3-6個月', 'score': 3},
                        {'text': '6個月-1年', 'score': 4},
                        {'text': '1-3年', 'score': 5},
                        {'text': '3年以上', 'score': 5}
                    ],
                    'weight': 0.15
                },
                {
                    'id': 'investment_goal',
                    'question': '您的主要投資目標是什麼？',
                    'type': 'single_choice',
                    'options': [
                        {'text': '資本保值', 'score': 1},
                        {'text': '穩定收益', 'score': 2},
                        {'text': '資本增值', 'score': 3},
                        {'text': '積極成長', 'score': 4},
                        {'text': '高收益追求', 'score': 5}
                    ],
                    'weight': 0.2
                },
                {
                    'id': 'market_volatility',
                    'question': '當市場大幅波動時，您會如何反應？',
                    'type': 'single_choice',
                    'options': [
                        {'text': '立即賣出止損', 'score': 1},
                        {'text': '減少部位', 'score': 2},
                        {'text': '保持不變', 'score': 3},
                        {'text': '逢低加碼', 'score': 4},
                        {'text': '大幅加碼', 'score': 5}
                    ],
                    'weight': 0.2
                }
            ],
            'scoring': {
                'conservative': {'min': 1.0, 'max': 2.5},
                'moderate': {'min': 2.5, 'max': 3.5},
                'aggressive': {'min': 3.5, 'max': 5.0}
            }
        }
    
    def _initialize_risk_levels(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化風險等級定義
        
        Returns:
            Dict[str, Dict[str, Any]]: 風險等級定義
        """
        return {
            'conservative': {
                'name': '保守型',
                'description': '追求穩定收益，風險承受能力較低',
                'characteristics': [
                    '優先考慮資本保值',
                    '不能接受大幅虧損',
                    '偏好穩定的投資策略',
                    '投資期限較長'
                ],
                'risk_parameters': {
                    'max_position_size': 0.1,
                    'max_portfolio_risk': 0.05,
                    'stop_loss_range': [0.02, 0.05],
                    'max_drawdown': 0.08,
                    'volatility_target': 0.12
                },
                'suitable_strategies': [
                    '移動平均線策略',
                    '債券配置策略',
                    '低波動因子策略'
                ],
                'expected_return': '3-8%',
                'risk_level': '低',
                'color': '#28a745'
            },
            'moderate': {
                'name': '穩健型',
                'description': '平衡風險與收益，追求穩健成長',
                'characteristics': [
                    '平衡風險與收益',
                    '可接受適度波動',
                    '追求穩健成長',
                    '中長期投資視角'
                ],
                'risk_parameters': {
                    'max_position_size': 0.15,
                    'max_portfolio_risk': 0.1,
                    'stop_loss_range': [0.05, 0.1],
                    'max_drawdown': 0.15,
                    'volatility_target': 0.18
                },
                'suitable_strategies': [
                    'RSI 策略',
                    '多因子策略',
                    '動量策略',
                    '均值回歸策略'
                ],
                'expected_return': '6-15%',
                'risk_level': '中等',
                'color': '#ffc107'
            },
            'aggressive': {
                'name': '積極型',
                'description': '追求高收益，能承受較高風險',
                'characteristics': [
                    '追求高收益',
                    '能承受較大波動',
                    '積極的投資策略',
                    '短中期投資視角'
                ],
                'risk_parameters': {
                    'max_position_size': 0.25,
                    'max_portfolio_risk': 0.2,
                    'stop_loss_range': [0.08, 0.15],
                    'max_drawdown': 0.25,
                    'volatility_target': 0.25
                },
                'suitable_strategies': [
                    '動量策略',
                    '成長股策略',
                    '高頻交易策略',
                    '槓桿策略'
                ],
                'expected_return': '10-25%',
                'risk_level': '高',
                'color': '#dc3545'
            }
        }
    
    def calculate_risk_score(self, answers: Dict[str, int]) -> float:
        """
        計算風險評分
        
        Args:
            answers: 問卷答案字典
            
        Returns:
            float: 風險評分 (1-5)
        """
        total_score = 0.0
        total_weight = 0.0
        
        for question in self.risk_questionnaire['questions']:
            question_id = question['id']
            if question_id in answers:
                score = answers[question_id]
                weight = question['weight']
                total_score += score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 2.5
    
    def determine_risk_level(self, risk_score: float) -> str:
        """
        根據評分確定風險等級
        
        Args:
            risk_score: 風險評分
            
        Returns:
            str: 風險等級
        """
        scoring = self.risk_questionnaire['scoring']
        
        for level, range_info in scoring.items():
            if range_info['min'] <= risk_score < range_info['max']:
                return level
        
        # 邊界情況處理
        if risk_score >= 3.5:
            return 'aggressive'
        elif risk_score >= 2.5:
            return 'moderate'
        else:
            return 'conservative'
    
    def get_risk_configuration(self, risk_level: str) -> Dict[str, Any]:
        """
        獲取風險配置
        
        Args:
            risk_level: 風險等級
            
        Returns:
            Dict[str, Any]: 風險配置
        """
        if risk_level not in self.risk_levels:
            risk_level = 'moderate'  # 預設值
        
        return self.risk_levels[risk_level].copy()
    
    def generate_risk_report(self, risk_level: str, 
                           risk_score: float) -> Dict[str, Any]:
        """
        生成風險評估報告
        
        Args:
            risk_level: 風險等級
            risk_score: 風險評分
            
        Returns:
            Dict[str, Any]: 風險評估報告
        """
        config = self.get_risk_configuration(risk_level)
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'level_name': config['name'],
            'description': config['description'],
            'characteristics': config['characteristics'],
            'risk_parameters': config['risk_parameters'],
            'suitable_strategies': config['suitable_strategies'],
            'expected_return': config['expected_return'],
            'recommendations': self._generate_recommendations(risk_level),
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_recommendations(self, risk_level: str) -> List[str]:
        """
        生成個人化建議
        
        Args:
            risk_level: 風險等級
            
        Returns:
            List[str]: 建議清單
        """
        recommendations = {
            'conservative': [
                "建議從簡單的移動平均線策略開始",
                "設定較小的部位大小（不超過10%）",
                "使用較嚴格的停損點（2-5%）",
                "定期檢視投資組合，避免過度集中",
                "考慮分散投資到不同資產類別"
            ],
            'moderate': [
                "可以嘗試多種技術分析策略",
                "適當增加部位大小（10-15%）",
                "使用中等程度的停損點（5-10%）",
                "定期進行策略績效評估",
                "考慮結合基本面和技術面分析"
            ],
            'aggressive': [
                "可以使用較複雜的量化策略",
                "適當增加部位大小（15-25%）",
                "使用較寬鬆的停損點（8-15%）",
                "密切監控市場變化",
                "考慮使用槓桿或衍生品工具"
            ]
        }
        
        return recommendations.get(risk_level, recommendations['moderate'])
    
    def save_user_profile(self, risk_level: str, answers: Dict[str, int],
                         user_id: str = "default") -> bool:
        """
        保存用戶風險檔案
        
        Args:
            risk_level: 風險等級
            answers: 問卷答案
            user_id: 用戶ID
            
        Returns:
            bool: 保存是否成功
        """
        try:
            self.user_profile[user_id] = {
                'risk_level': risk_level,
                'answers': answers,
                'created_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            
            logger.info("用戶風險檔案已保存: %s - %s", user_id, risk_level)
            return True
            
        except Exception as e:
            logger.error("保存用戶風險檔案失敗: %s", e)
            return False


def show_risk_level_selector() -> None:
    """
    顯示風險等級選擇器頁面
    
    提供新手友好的風險評估和等級選擇功能，包括風險問卷、
    等級匹配、個人化配置和教育內容。
    
    Side Effects:
        - 在 Streamlit 界面顯示風險等級選擇器
        - 進行風險評估和配置推薦
    """
    st.title("🎚️ 風險等級選擇器")
    st.markdown("通過專業的風險評估，為您推薦最適合的投資策略配置！")
    
    # 初始化風險等級選擇器
    if 'risk_selector' not in st.session_state:
        st.session_state.risk_selector = RiskLevelSelector()
    
    selector = st.session_state.risk_selector
    
    # 風險教育區域
    with st.expander("📚 風險教育 - 了解投資風險", expanded=False):
        st.markdown("""
        ### 什麼是投資風險？
        
        投資風險是指投資可能面臨的損失或收益不確定性。主要包括：
        
        - **市場風險**: 整體市場波動導致的損失
        - **個股風險**: 特定股票表現不佳的風險
        - **流動性風險**: 無法及時買賣的風險
        - **通膨風險**: 通貨膨脹侵蝕購買力的風險
        
        ### 風險與收益的關係
        
        一般來說，風險與收益成正比：
        - 低風險 → 低收益 → 適合保守投資者
        - 中風險 → 中收益 → 適合穩健投資者  
        - 高風險 → 高收益 → 適合積極投資者
        
        ### 風險管理的重要性
        
        - 設定合理的停損點
        - 分散投資降低風險
        - 定期檢視投資組合
        - 根據市場變化調整策略
        """)
    
    # 風險評估問卷
    st.subheader("📋 風險評估問卷")
    st.write("請誠實回答以下問題，幫助我們為您推薦最適合的風險等級：")
    
    questionnaire = selector.risk_questionnaire
    answers = {}
    
    for i, question in enumerate(questionnaire['questions']):
        st.write(f"**{i+1}. {question['question']}**")
        
        options = [opt['text'] for opt in question['options']]
        selected_idx = st.radio(
            f"選擇答案 {i+1}",
            range(len(options)),
            format_func=lambda x, opts=options: opts[x],
            key=f"q_{question['id']}",
            label_visibility="collapsed"
        )
        
        answers[question['id']] = question['options'][selected_idx]['score']
        st.write("")  # 添加間距
    
    # 評估結果
    if st.button("🎯 完成評估", type="primary"):
        # 計算風險評分
        risk_score = selector.calculate_risk_score(answers)
        risk_level = selector.determine_risk_level(risk_score)
        
        # 生成報告
        report = selector.generate_risk_report(risk_level, risk_score)
        
        # 保存到 session state
        st.session_state.risk_assessment_result = report
        st.session_state.risk_answers = answers
        
        st.success("✅ 風險評估完成！")
    
    # 顯示評估結果
    if 'risk_assessment_result' in st.session_state:
        report = st.session_state.risk_assessment_result
        
        st.subheader("📊 您的風險評估結果")
        
        # 風險等級展示
        config = selector.get_risk_configuration(report['risk_level'])
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # 風險等級卡片
            st.markdown(f"""
            <div style="
                background-color: {config['color']}20;
                border: 2px solid {config['color']};
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                margin: 20px 0;
            ">
                <h2 style="color: {config['color']}; margin: 0;">
                    {config['name']}
                </h2>
                <p style="margin: 10px 0; font-size: 16px;">
                    {config['description']}
                </p>
                <p style="margin: 0; font-weight: bold;">
                    風險評分: {report['risk_score']:.2f}/5.0
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        # 詳細資訊
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**您的特徵：**")
            for char in config['characteristics']:
                st.write(f"• {char}")
            
            st.write("**預期收益：**")
            st.write(f"📈 {config['expected_return']}")
            
            st.write("**風險等級：**")
            st.write(f"⚖️ {config['risk_level']}")
        
        with col2:
            st.write("**適合的策略：**")
            for strategy in config['suitable_strategies']:
                st.write(f"• {strategy}")
            
            st.write("**風險參數：**")
            params = config['risk_parameters']
            st.write(f"• 最大部位: {params['max_position_size']:.0%}")
            st.write(f"• 最大回撤: {params['max_drawdown']:.0%}")
            st.write(f"• 波動率目標: {params['volatility_target']:.0%}")
        
        # 個人化建議
        st.subheader("💡 個人化建議")
        
        recommendations = report['recommendations']
        for i, rec in enumerate(recommendations, 1):
            st.write(f"{i}. {rec}")
        
        # 風險參數配置
        st.subheader("⚙️ 推薦的風險參數配置")
        
        params = config['risk_parameters']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("最大部位大小", f"{params['max_position_size']:.0%}")
            st.metric("投資組合風險", f"{params['max_portfolio_risk']:.0%}")
        
        with col2:
            stop_loss_min, stop_loss_max = params['stop_loss_range']
            st.metric("停損範圍", f"{stop_loss_min:.0%} - {stop_loss_max:.0%}")
            st.metric("最大回撤", f"{params['max_drawdown']:.0%}")
        
        with col3:
            st.metric("波動率目標", f"{params['volatility_target']:.0%}")
        
        # 風險等級比較
        st.subheader("📊 風險等級比較")
        
        # 創建比較圖表
        levels = ['conservative', 'moderate', 'aggressive']
        level_names = [selector.risk_levels[l]['name'] for l in levels]
        returns = [8, 15, 25]  # 預期收益上限
        risks = [8, 15, 25]    # 最大回撤
        
        fig = go.Figure()
        
        # 添加散點圖
        colors = ['#28a745', '#ffc107', '#dc3545']
        for i, level in enumerate(levels):
            is_selected = level == report['risk_level']
            fig.add_trace(go.Scatter(
                x=[risks[i]],
                y=[returns[i]],
                mode='markers',
                name=level_names[i],
                marker=dict(
                    size=20 if is_selected else 15,
                    color=colors[i],
                    line=dict(width=3 if is_selected else 1, color='black')
                ),
                text=level_names[i],
                textposition="middle center"
            ))
        
        fig.update_layout(
            title='風險收益分布圖',
            xaxis_title='風險水平 (%)',
            yaxis_title='預期收益 (%)',
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 操作按鈕
        st.subheader("🔧 下一步操作")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 保存風險檔案"):
                if selector.save_user_profile(
                    report['risk_level'], 
                    st.session_state.risk_answers
                ):
                    st.success("✅ 風險檔案已保存！")
                else:
                    st.error("❌ 保存失敗，請重試。")
        
        with col2:
            if st.button("🎯 查看推薦策略"):
                st.info("🔄 正在跳轉到策略模板頁面...")
        
        with col3:
            if st.button("🔄 重新評估"):
                if 'risk_assessment_result' in st.session_state:
                    del st.session_state.risk_assessment_result
                if 'risk_answers' in st.session_state:
                    del st.session_state.risk_answers
                st.rerun()
    
    # 側邊欄：風險等級概覽
    with st.sidebar:
        st.subheader("🎚️ 風險等級概覽")
        
        for level_id, level_info in selector.risk_levels.items():
            with st.expander(level_info['name'], expanded=False):
                st.write(level_info['description'])
                st.write(f"**預期收益**: {level_info['expected_return']}")
                st.write(f"**風險等級**: {level_info['risk_level']}")
        
        # 快速選擇
        st.subheader("⚡ 快速選擇")
        
        if st.button("🛡️ 我是保守型"):
            st.session_state.quick_risk_level = 'conservative'
            st.info("已選擇保守型風險等級")
        
        if st.button("⚖️ 我是穩健型"):
            st.session_state.quick_risk_level = 'moderate'
            st.info("已選擇穩健型風險等級")
        
        if st.button("🚀 我是積極型"):
            st.session_state.quick_risk_level = 'aggressive'
            st.info("已選擇積極型風險等級")
        
        # 顯示快速選擇結果
        if 'quick_risk_level' in st.session_state:
            quick_level = st.session_state.quick_risk_level
            quick_config = selector.get_risk_configuration(quick_level)
            
            st.write("**快速選擇結果：**")
            st.write(f"風險等級：{quick_config['name']}")
            st.write(f"預期收益：{quick_config['expected_return']}")
            
            if st.button("應用此配置"):
                # 創建快速評估報告
                quick_report = selector.generate_risk_report(quick_level, 3.0)
                st.session_state.risk_assessment_result = quick_report
                st.rerun()
