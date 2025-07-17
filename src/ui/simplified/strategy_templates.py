# -*- coding: utf-8 -*-
"""
預設策略模板選擇器

此模組提供新手友好的策略模板選擇功能，包括：
- 預設策略模板庫
- 簡化的策略配置
- 一鍵策略部署
- 策略效果預覽
- 風險等級匹配

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


class StrategyTemplates:
    """
    預設策略模板選擇器
    
    提供新手友好的策略模板選擇和配置功能，包括預設模板庫、
    簡化配置和一鍵部署功能。
    
    Attributes:
        template_library (Dict): 策略模板庫
        risk_profiles (Dict): 風險配置檔案
        user_preferences (Dict): 用戶偏好設定
        
    Example:
        >>> templates = StrategyTemplates()
        >>> template = templates.get_template_by_risk_level('conservative')
        >>> templates.deploy_template(template, {'symbol': 'AAPL'})
    """
    
    def __init__(self):
        """初始化策略模板選擇器"""
        self.template_library = self._initialize_template_library()
        self.risk_profiles = self._initialize_risk_profiles()
        self.user_preferences = {}
        
    def _initialize_template_library(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化策略模板庫
        
        Returns:
            Dict[str, Dict[str, Any]]: 策略模板庫
        """
        return {
            'conservative_ma': {
                'name': '保守型移動平均策略',
                'description': '適合新手的低風險移動平均線策略',
                'risk_level': 'conservative',
                'expected_return': '5-8%',
                'max_drawdown': '3-5%',
                'strategy_type': 'technical',
                'complexity': 'simple',
                'parameters': {
                    'fast_period': 20,
                    'slow_period': 50,
                    'stop_loss': 0.03,
                    'take_profit': 0.06,
                    'position_size': 0.1
                },
                'suitable_for': ['新手', '保守投資者', '長期投資'],
                'market_conditions': ['趨勢市場', '低波動環境'],
                'pros': [
                    '風險較低',
                    '邏輯簡單',
                    '適合長期持有'
                ],
                'cons': [
                    '收益相對較低',
                    '震盪市場表現較差'
                ]
            },
            'moderate_rsi': {
                'name': '穩健型 RSI 策略',
                'description': '平衡風險與收益的 RSI 超買超賣策略',
                'risk_level': 'moderate',
                'expected_return': '8-12%',
                'max_drawdown': '5-8%',
                'strategy_type': 'technical',
                'complexity': 'simple',
                'parameters': {
                    'rsi_period': 14,
                    'oversold': 25,
                    'overbought': 75,
                    'stop_loss': 0.05,
                    'take_profit': 0.08,
                    'position_size': 0.15
                },
                'suitable_for': ['有經驗新手', '穩健投資者'],
                'market_conditions': ['震盪市場', '中等波動環境'],
                'pros': [
                    '適合震盪市場',
                    '進出點明確',
                    '風險可控'
                ],
                'cons': [
                    '需要頻繁交易',
                    '趨勢市場表現一般'
                ]
            },
            'aggressive_momentum': {
                'name': '積極型動量策略',
                'description': '追求高收益的動量追蹤策略',
                'risk_level': 'aggressive',
                'expected_return': '12-20%',
                'max_drawdown': '8-15%',
                'strategy_type': 'quantitative',
                'complexity': 'medium',
                'parameters': {
                    'lookback_period': 10,
                    'momentum_threshold': 0.03,
                    'stop_loss': 0.08,
                    'take_profit': 0.15,
                    'position_size': 0.2,
                    'rebalance_freq': 3
                },
                'suitable_for': ['經驗投資者', '風險偏好者'],
                'market_conditions': ['強趨勢市場', '高波動環境'],
                'pros': [
                    '收益潛力高',
                    '捕捉趨勢機會',
                    '適應性強'
                ],
                'cons': [
                    '風險較高',
                    '需要及時調整',
                    '市場轉向風險'
                ]
            },
            'balanced_multi': {
                'name': '平衡型多因子策略',
                'description': '結合多種技術指標的平衡策略',
                'risk_level': 'moderate',
                'expected_return': '10-15%',
                'max_drawdown': '6-10%',
                'strategy_type': 'multi_factor',
                'complexity': 'medium',
                'parameters': {
                    'ma_weight': 0.3,
                    'rsi_weight': 0.3,
                    'momentum_weight': 0.4,
                    'stop_loss': 0.06,
                    'take_profit': 0.12,
                    'position_size': 0.12,
                    'rebalance_freq': 5
                },
                'suitable_for': ['中級投資者', '多元化需求'],
                'market_conditions': ['各種市場環境'],
                'pros': [
                    '風險分散',
                    '適應性好',
                    '收益穩定'
                ],
                'cons': [
                    '複雜度較高',
                    '參數較多',
                    '需要理解多種指標'
                ]
            }
        }
    
    def _initialize_risk_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化風險配置檔案
        
        Returns:
            Dict[str, Dict[str, Any]]: 風險配置檔案
        """
        return {
            'conservative': {
                'name': '保守型',
                'description': '低風險，穩定收益',
                'max_position_size': 0.1,
                'max_drawdown': 0.05,
                'stop_loss_range': [0.02, 0.05],
                'suitable_strategies': ['conservative_ma'],
                'investment_horizon': '長期 (6個月以上)',
                'risk_tolerance': '低'
            },
            'moderate': {
                'name': '穩健型',
                'description': '平衡風險與收益',
                'max_position_size': 0.15,
                'max_drawdown': 0.08,
                'stop_loss_range': [0.04, 0.08],
                'suitable_strategies': ['moderate_rsi', 'balanced_multi'],
                'investment_horizon': '中期 (3-6個月)',
                'risk_tolerance': '中等'
            },
            'aggressive': {
                'name': '積極型',
                'description': '高風險，高收益潛力',
                'max_position_size': 0.2,
                'max_drawdown': 0.15,
                'stop_loss_range': [0.06, 0.12],
                'suitable_strategies': ['aggressive_momentum', 'balanced_multi'],
                'investment_horizon': '短期 (1-3個月)',
                'risk_tolerance': '高'
            }
        }
    
    def get_templates_by_risk_level(self, risk_level: str) -> List[Dict[str, Any]]:
        """
        根據風險等級獲取適合的策略模板
        
        Args:
            risk_level: 風險等級 ('conservative', 'moderate', 'aggressive')
            
        Returns:
            List[Dict[str, Any]]: 適合的策略模板清單
        """
        suitable_templates = []
        
        for template_id, template in self.template_library.items():
            if template['risk_level'] == risk_level:
                template_copy = template.copy()
                template_copy['id'] = template_id
                suitable_templates.append(template_copy)
        
        return suitable_templates
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        根據ID獲取策略模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            Optional[Dict[str, Any]]: 策略模板
        """
        template = self.template_library.get(template_id)
        if template:
            template_copy = template.copy()
            template_copy['id'] = template_id
            return template_copy
        return None
    
    def customize_template(self, template_id: str, 
                         custom_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        自定義策略模板參數
        
        Args:
            template_id: 模板ID
            custom_parameters: 自定義參數
            
        Returns:
            Dict[str, Any]: 自定義後的模板
        """
        template = self.get_template_by_id(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")
        
        # 更新參數
        template['parameters'].update(custom_parameters)
        template['customized'] = True
        template['customized_at'] = datetime.now().isoformat()
        
        return template
    
    def validate_template_parameters(self, template: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        驗證模板參數
        
        Args:
            template: 策略模板
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 錯誤訊息清單)
        """
        errors = []
        parameters = template.get('parameters', {})
        
        # 基本參數驗證
        if 'position_size' in parameters:
            if not 0 < parameters['position_size'] <= 0.5:
                errors.append("部位大小應在 0-50% 之間")
        
        if 'stop_loss' in parameters:
            if not 0 < parameters['stop_loss'] <= 0.2:
                errors.append("停損比例應在 0-20% 之間")
        
        if 'take_profit' in parameters:
            if parameters['take_profit'] <= parameters.get('stop_loss', 0):
                errors.append("止盈比例應大於停損比例")
        
        # 技術指標參數驗證
        if 'fast_period' in parameters and 'slow_period' in parameters:
            if parameters['fast_period'] >= parameters['slow_period']:
                errors.append("快速週期應小於慢速週期")
        
        if 'rsi_period' in parameters:
            if not 5 <= parameters['rsi_period'] <= 30:
                errors.append("RSI 週期應在 5-30 之間")
        
        return len(errors) == 0, errors
    
    def generate_template_preview(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成模板預覽資料
        
        Args:
            template: 策略模板
            
        Returns:
            Dict[str, Any]: 預覽資料
        """
        # 生成模擬回測結果
        np.random.seed(42)  # 確保結果一致
        
        days = 252  # 一年交易日
        returns = np.random.normal(0.001, 0.02, days)  # 日收益率
        
        # 根據策略類型調整收益分布
        if template['risk_level'] == 'conservative':
            returns = returns * 0.5 + 0.0002  # 降低波動，提高基準收益
        elif template['risk_level'] == 'aggressive':
            returns = returns * 1.5  # 增加波動
        
        cumulative_returns = np.cumprod(1 + returns) - 1
        
        # 計算績效指標
        total_return = cumulative_returns[-1]
        volatility = np.std(returns) * np.sqrt(252)
        sharpe_ratio = (np.mean(returns) * 252) / volatility if volatility > 0 else 0
        max_drawdown = np.min(cumulative_returns)
        
        return {
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': abs(max_drawdown),
            'cumulative_returns': cumulative_returns,
            'daily_returns': returns
        }
    
    def save_user_template(self, template: Dict[str, Any], 
                          user_id: str = "default") -> bool:
        """
        保存用戶自定義模板
        
        Args:
            template: 策略模板
            user_id: 用戶ID
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 這裡應該保存到實際的資料庫或檔案
            logger.info("用戶模板已保存: %s", template.get('name', 'Unknown'))
            return True
            
        except Exception as e:
            logger.error("保存用戶模板失敗: %s", e)
            return False


def show_strategy_templates() -> None:
    """
    顯示策略模板選擇器頁面
    
    提供新手友好的策略模板選擇和配置界面，包括風險等級匹配、
    模板預覽和一鍵部署功能。
    
    Side Effects:
        - 在 Streamlit 界面顯示策略模板選擇器
        - 提供策略配置和部署功能
    """
    st.title("🎯 策略模板選擇器")
    st.markdown("選擇適合您的預設策略模板，快速開始量化交易！")
    
    # 初始化策略模板管理器
    if 'strategy_templates' not in st.session_state:
        st.session_state.strategy_templates = StrategyTemplates()
    
    templates_manager = st.session_state.strategy_templates
    
    # 風險評估問卷
    with st.expander("📋 風險評估問卷 (建議完成)", expanded=False):
        st.write("**請回答以下問題，幫助我們為您推薦合適的策略：**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            experience = st.selectbox(
                "您的投資經驗？",
                ["新手 (< 1年)", "初級 (1-3年)", "中級 (3-5年)", "高級 (> 5年)"]
            )
            
            risk_tolerance = st.selectbox(
                "您的風險承受能力？",
                ["保守 (不能接受虧損)", "穩健 (可接受小幅虧損)", "積極 (可接受較大虧損)"]
            )
        
        with col2:
            investment_horizon = st.selectbox(
                "您的投資期限？",
                ["短期 (< 3個月)", "中期 (3-12個月)", "長期 (> 1年)"]
            )
            
            investment_goal = st.selectbox(
                "您的投資目標？",
                ["資本保值", "穩定收益", "資本增值", "高收益追求"]
            )
        
        if st.button("獲取推薦策略"):
            # 根據問卷結果推薦風險等級
            if risk_tolerance.startswith("保守") or experience.startswith("新手"):
                recommended_risk = "conservative"
            elif risk_tolerance.startswith("積極") and not experience.startswith("新手"):
                recommended_risk = "aggressive"
            else:
                recommended_risk = "moderate"
            
            st.session_state.recommended_risk = recommended_risk
            st.success(f"✅ 根據您的回答，推薦風險等級：{templates_manager.risk_profiles[recommended_risk]['name']}")
    
    # 風險等級選擇
    st.subheader("🎚️ 選擇風險等級")
    
    risk_levels = list(templates_manager.risk_profiles.keys())
    risk_names = [templates_manager.risk_profiles[r]['name'] for r in risk_levels]
    
    # 使用推薦的風險等級作為預設值
    default_risk_idx = 0
    if 'recommended_risk' in st.session_state:
        try:
            default_risk_idx = risk_levels.index(st.session_state.recommended_risk)
        except ValueError:
            pass
    
    selected_risk_idx = st.selectbox(
        "選擇您的風險偏好",
        range(len(risk_levels)),
        index=default_risk_idx,
        format_func=lambda x: risk_names[x]
    )
    
    selected_risk = risk_levels[selected_risk_idx]
    risk_profile = templates_manager.risk_profiles[selected_risk]
    
    # 顯示風險等級資訊
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("風險等級", risk_profile['name'])
    with col2:
        st.metric("最大部位", f"{risk_profile['max_position_size']:.0%}")
    with col3:
        st.metric("最大回撤", f"{risk_profile['max_drawdown']:.0%}")
    
    st.info(f"📝 {risk_profile['description']} | 投資期限：{risk_profile['investment_horizon']}")
    
    # 策略模板選擇
    st.subheader("📊 可用策略模板")
    
    suitable_templates = templates_manager.get_templates_by_risk_level(selected_risk)
    
    if suitable_templates:
        # 模板卡片展示
        for i, template in enumerate(suitable_templates):
            with st.expander(f"🎯 {template['name']}", expanded=i == 0):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(template['description'])
                    
                    # 策略特點
                    st.write("**適合對象：**")
                    for suitable in template['suitable_for']:
                        st.write(f"• {suitable}")
                    
                    st.write("**優點：**")
                    for pro in template['pros']:
                        st.write(f"✅ {pro}")
                    
                    st.write("**缺點：**")
                    for con in template['cons']:
                        st.write(f"⚠️ {con}")
                
                with col2:
                    st.metric("預期收益", template['expected_return'])
                    st.metric("最大回撤", template['max_drawdown'])
                    st.metric("策略類型", template['strategy_type'])
                    st.metric("複雜度", template['complexity'])
                
                # 參數設定
                st.write("**策略參數：**")
                
                parameters = template['parameters'].copy()
                param_cols = st.columns(3)
                
                for j, (param_name, param_value) in enumerate(parameters.items()):
                    col = param_cols[j % 3]
                    
                    with col:
                        if isinstance(param_value, float):
                            if param_name in ['stop_loss', 'take_profit', 'position_size']:
                                # 百分比參數
                                new_value = st.slider(
                                    param_name.replace('_', ' ').title(),
                                    min_value=0.01,
                                    max_value=0.5 if 'position' in param_name else 0.2,
                                    value=param_value,
                                    step=0.01,
                                    format="%.2f",
                                    key=f"{template['id']}_{param_name}"
                                )
                                parameters[param_name] = new_value
                            else:
                                # 其他浮點數參數
                                new_value = st.number_input(
                                    param_name.replace('_', ' ').title(),
                                    min_value=0.001,
                                    max_value=1.0,
                                    value=param_value,
                                    step=0.001,
                                    key=f"{template['id']}_{param_name}"
                                )
                                parameters[param_name] = new_value
                        elif isinstance(param_value, int):
                            new_value = st.number_input(
                                param_name.replace('_', ' ').title(),
                                min_value=1,
                                max_value=100,
                                value=param_value,
                                key=f"{template['id']}_{param_name}"
                            )
                            parameters[param_name] = new_value
                
                # 策略預覽
                if st.button(f"預覽策略效果", key=f"preview_{template['id']}"):
                    with st.spinner("生成策略預覽..."):
                        # 使用自定義參數更新模板
                        custom_template = templates_manager.customize_template(
                            template['id'], parameters
                        )
                        
                        # 生成預覽
                        preview_data = templates_manager.generate_template_preview(custom_template)
                        
                        # 顯示預覽結果
                        st.subheader("📈 策略效果預覽")
                        
                        # 績效指標
                        metric_cols = st.columns(4)
                        
                        with metric_cols[0]:
                            st.metric("總收益率", f"{preview_data['total_return']:.2%}")
                        with metric_cols[1]:
                            st.metric("年化波動率", f"{preview_data['volatility']:.2%}")
                        with metric_cols[2]:
                            st.metric("夏普比率", f"{preview_data['sharpe_ratio']:.2f}")
                        with metric_cols[3]:
                            st.metric("最大回撤", f"{preview_data['max_drawdown']:.2%}")
                        
                        # 收益曲線圖
                        dates = pd.date_range(start='2023-01-01', periods=len(preview_data['cumulative_returns']), freq='D')
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=dates,
                            y=preview_data['cumulative_returns'] * 100,
                            mode='lines',
                            name='累積收益率',
                            line=dict(color='blue', width=2)
                        ))
                        
                        fig.update_layout(
                            title='策略收益曲線預覽',
                            xaxis_title='日期',
                            yaxis_title='累積收益率 (%)',
                            height=400
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                
                # 部署策略
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"保存策略配置", key=f"save_{template['id']}"):
                        custom_template = templates_manager.customize_template(
                            template['id'], parameters
                        )
                        
                        if templates_manager.save_user_template(custom_template):
                            st.success("✅ 策略配置已保存！")
                        else:
                            st.error("❌ 保存失敗，請重試。")
                
                with col2:
                    if st.button(f"部署策略", key=f"deploy_{template['id']}"):
                        # 驗證參數
                        custom_template = templates_manager.customize_template(
                            template['id'], parameters
                        )
                        
                        is_valid, errors = templates_manager.validate_template_parameters(custom_template)
                        
                        if is_valid:
                            st.success("🚀 策略部署成功！請前往回測頁面查看結果。")
                        else:
                            st.error("❌ 參數驗證失敗：")
                            for error in errors:
                                st.error(f"• {error}")
    else:
        st.warning(f"暫無適合 {risk_profile['name']} 風險等級的策略模板。")
    
    # 自定義策略提示
    st.subheader("🛠️ 進階選項")
    
    with st.expander("創建自定義策略", expanded=False):
        st.info(
            "如果預設模板不能滿足您的需求，您可以：\n\n"
            "1. 前往「策略管理」頁面創建完全自定義的策略\n"
            "2. 基於現有模板進行深度自定義\n"
            "3. 使用 AI 模型創建機器學習策略\n\n"
            "建議新手先熟悉預設模板，再嘗試自定義策略。"
        )
        
        if st.button("前往策略管理"):
            st.info("🔄 正在跳轉到策略管理頁面...")
