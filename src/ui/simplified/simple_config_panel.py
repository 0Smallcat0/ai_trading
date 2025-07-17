# -*- coding: utf-8 -*-
"""
簡化參數設定面板

此模組提供新手友好的簡化參數設定功能，包括：
- 預設參數模板
- 視覺化參數調整
- 參數影響說明
- 一鍵優化建議
- 配置保存和載入

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


class SimpleConfigPanel:
    """
    簡化參數設定面板
    
    提供新手友好的參數設定功能，包括預設模板、
    視覺化調整、影響說明和優化建議。
    
    Attributes:
        parameter_templates (Dict): 參數模板庫
        parameter_definitions (Dict): 參數定義和說明
        user_configs (Dict): 用戶配置記錄
        
    Example:
        >>> panel = SimpleConfigPanel()
        >>> config = panel.get_template_config('conservative')
        >>> panel.save_user_config(config, 'my_config')
    """
    
    def __init__(self):
        """初始化簡化配置面板"""
        self.parameter_templates = self._initialize_parameter_templates()
        self.parameter_definitions = self._initialize_parameter_definitions()
        self.user_configs = {}
        
    def _initialize_parameter_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化參數模板庫
        
        Returns:
            Dict[str, Dict[str, Any]]: 參數模板庫
        """
        return {
            'conservative': {
                'name': '保守型配置',
                'description': '低風險、穩定收益的參數設定',
                'parameters': {
                    'initial_capital': 100000,
                    'position_size': 0.1,
                    'stop_loss': 0.03,
                    'take_profit': 0.06,
                    'max_positions': 3,
                    'rebalance_frequency': 'weekly',
                    'commission': 0.001,
                    'slippage': 0.001
                },
                'risk_level': 'low',
                'expected_return': '5-8%',
                'suitable_for': ['新手', '保守投資者']
            },
            'moderate': {
                'name': '穩健型配置',
                'description': '平衡風險與收益的參數設定',
                'parameters': {
                    'initial_capital': 100000,
                    'position_size': 0.15,
                    'stop_loss': 0.05,
                    'take_profit': 0.1,
                    'max_positions': 5,
                    'rebalance_frequency': 'daily',
                    'commission': 0.001,
                    'slippage': 0.001
                },
                'risk_level': 'medium',
                'expected_return': '8-15%',
                'suitable_for': ['有經驗投資者', '穩健型投資者']
            },
            'aggressive': {
                'name': '積極型配置',
                'description': '高風險、高收益潛力的參數設定',
                'parameters': {
                    'initial_capital': 100000,
                    'position_size': 0.2,
                    'stop_loss': 0.08,
                    'take_profit': 0.15,
                    'max_positions': 8,
                    'rebalance_frequency': 'daily',
                    'commission': 0.001,
                    'slippage': 0.002
                },
                'risk_level': 'high',
                'expected_return': '15-25%',
                'suitable_for': ['經驗豐富投資者', '風險偏好者']
            },
            'custom': {
                'name': '自定義配置',
                'description': '根據個人需求自定義的參數設定',
                'parameters': {
                    'initial_capital': 100000,
                    'position_size': 0.12,
                    'stop_loss': 0.05,
                    'take_profit': 0.1,
                    'max_positions': 5,
                    'rebalance_frequency': 'daily',
                    'commission': 0.001,
                    'slippage': 0.001
                },
                'risk_level': 'custom',
                'expected_return': '可變',
                'suitable_for': ['所有投資者']
            }
        }
    
    def _initialize_parameter_definitions(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化參數定義和說明
        
        Returns:
            Dict[str, Dict[str, Any]]: 參數定義字典
        """
        return {
            'initial_capital': {
                'name': '初始資金',
                'description': '開始交易時的總資金金額',
                'unit': '元',
                'range': [10000, 10000000],
                'default': 100000,
                'impact': '影響可投資的股票數量和部位大小',
                'tips': '建議使用閒置資金，不要投入全部資產'
            },
            'position_size': {
                'name': '部位大小',
                'description': '單一股票投資佔總資金的比例',
                'unit': '%',
                'range': [0.05, 0.5],
                'default': 0.1,
                'impact': '影響風險分散程度和單筆投資風險',
                'tips': '新手建議不超過10%，經驗豐富者可適當提高'
            },
            'stop_loss': {
                'name': '停損比例',
                'description': '當虧損達到此比例時自動賣出',
                'unit': '%',
                'range': [0.01, 0.2],
                'default': 0.05,
                'impact': '影響最大虧損控制和交易頻率',
                'tips': '設定過小會頻繁停損，過大會增加虧損風險'
            },
            'take_profit': {
                'name': '止盈比例',
                'description': '當獲利達到此比例時自動賣出',
                'unit': '%',
                'range': [0.02, 0.5],
                'default': 0.1,
                'impact': '影響獲利實現和持有期間',
                'tips': '應大於停損比例，建議為停損的1.5-2倍'
            },
            'max_positions': {
                'name': '最大持倉數',
                'description': '同時持有的股票數量上限',
                'unit': '檔',
                'range': [1, 20],
                'default': 5,
                'impact': '影響風險分散程度和管理複雜度',
                'tips': '新手建議3-5檔，有經驗者可增加到8-10檔'
            },
            'rebalance_frequency': {
                'name': '再平衡頻率',
                'description': '調整投資組合的頻率',
                'unit': '',
                'options': ['daily', 'weekly', 'monthly'],
                'default': 'daily',
                'impact': '影響交易成本和策略敏感度',
                'tips': '頻率越高交易成本越高，但能更快適應市場變化'
            },
            'commission': {
                'name': '手續費率',
                'description': '每筆交易的手續費比例',
                'unit': '%',
                'range': [0.0001, 0.01],
                'default': 0.001,
                'impact': '影響交易成本和淨收益',
                'tips': '不同券商手續費不同，建議選擇低手續費券商'
            },
            'slippage': {
                'name': '滑點率',
                'description': '實際成交價與預期價格的差異',
                'unit': '%',
                'range': [0.0001, 0.01],
                'default': 0.001,
                'impact': '影響實際交易成本',
                'tips': '流動性好的股票滑點較小，小型股滑點較大'
            }
        }
    
    def get_template_config(self, template_name: str) -> Optional[Dict[str, Any]]:
        """
        獲取模板配置
        
        Args:
            template_name: 模板名稱
            
        Returns:
            Optional[Dict[str, Any]]: 模板配置
        """
        return self.parameter_templates.get(template_name)
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        驗證參數設定
        
        Args:
            parameters: 參數字典
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 錯誤訊息清單)
        """
        errors = []
        
        # 檢查必要參數
        required_params = [
            'initial_capital', 'position_size', 'stop_loss', 
            'take_profit', 'max_positions'
        ]
        
        for param in required_params:
            if param not in parameters:
                errors.append(f"缺少必要參數: {param}")
        
        # 檢查參數範圍
        for param_name, value in parameters.items():
            if param_name in self.parameter_definitions:
                definition = self.parameter_definitions[param_name]
                
                if 'range' in definition:
                    min_val, max_val = definition['range']
                    if not min_val <= value <= max_val:
                        errors.append(
                            f"{definition['name']} 應在 {min_val} - {max_val} 之間"
                        )
        
        # 邏輯檢查
        if 'stop_loss' in parameters and 'take_profit' in parameters:
            if parameters['take_profit'] <= parameters['stop_loss']:
                errors.append("止盈比例應大於停損比例")
        
        if 'position_size' in parameters and 'max_positions' in parameters:
            total_allocation = parameters['position_size'] * parameters['max_positions']
            if total_allocation > 1.0:
                errors.append("總投資比例不應超過100%")
        
        return len(errors) == 0, errors
    
    def calculate_risk_metrics(self, parameters: Dict[str, Any]) -> Dict[str, float]:
        """
        計算風險指標
        
        Args:
            parameters: 參數字典
            
        Returns:
            Dict[str, float]: 風險指標
        """
        # 計算最大單筆虧損
        max_single_loss = parameters.get('position_size', 0.1) * parameters.get('stop_loss', 0.05)
        
        # 計算最大總虧損（假設所有部位同時停損）
        max_total_loss = max_single_loss * parameters.get('max_positions', 5)
        
        # 計算風險分散度
        risk_concentration = parameters.get('position_size', 0.1) * parameters.get('max_positions', 5)
        
        # 計算預期交易成本
        commission = parameters.get('commission', 0.001)
        slippage = parameters.get('slippage', 0.001)
        trading_cost = (commission + slippage) * 2  # 買入和賣出
        
        return {
            'max_single_loss': max_single_loss,
            'max_total_loss': min(max_total_loss, 1.0),  # 不超過100%
            'risk_concentration': risk_concentration,
            'trading_cost_per_trade': trading_cost,
            'risk_score': self._calculate_risk_score(parameters)
        }
    
    def _calculate_risk_score(self, parameters: Dict[str, Any]) -> float:
        """
        計算風險評分 (0-10, 10為最高風險)
        
        Args:
            parameters: 參數字典
            
        Returns:
            float: 風險評分
        """
        score = 0.0
        
        # 部位大小風險 (0-3分)
        position_size = parameters.get('position_size', 0.1)
        if position_size <= 0.1:
            score += 1
        elif position_size <= 0.2:
            score += 2
        else:
            score += 3
        
        # 停損設定風險 (0-2分)
        stop_loss = parameters.get('stop_loss', 0.05)
        if stop_loss >= 0.05:
            score += 1
        else:
            score += 2
        
        # 持倉集中度風險 (0-3分)
        max_positions = parameters.get('max_positions', 5)
        if max_positions >= 8:
            score += 1
        elif max_positions >= 5:
            score += 2
        else:
            score += 3
        
        # 總投資比例風險 (0-2分)
        total_allocation = position_size * max_positions
        if total_allocation <= 0.5:
            score += 1
        elif total_allocation <= 0.8:
            score += 1.5
        else:
            score += 2
        
        return min(score, 10.0)
    
    def generate_optimization_suggestions(self, parameters: Dict[str, Any]) -> List[str]:
        """
        生成優化建議
        
        Args:
            parameters: 參數字典
            
        Returns:
            List[str]: 優化建議清單
        """
        suggestions = []
        risk_metrics = self.calculate_risk_metrics(parameters)
        
        # 風險控制建議
        if risk_metrics['max_total_loss'] > 0.3:
            suggestions.append("總風險過高，建議降低部位大小或減少持倉數量")
        
        if risk_metrics['risk_concentration'] > 0.8:
            suggestions.append("投資過於集中，建議增加持倉數量或降低單一部位大小")
        
        # 停損止盈建議
        stop_loss = parameters.get('stop_loss', 0.05)
        take_profit = parameters.get('take_profit', 0.1)
        
        if take_profit / stop_loss < 1.5:
            suggestions.append("止盈停損比例偏低，建議提高止盈比例或降低停損比例")
        
        if stop_loss < 0.02:
            suggestions.append("停損設定過於嚴格，可能導致頻繁停損")
        
        # 交易成本建議
        if risk_metrics['trading_cost_per_trade'] > 0.005:
            suggestions.append("交易成本較高，建議選擇低手續費券商或降低交易頻率")
        
        # 風險評分建議
        if risk_metrics['risk_score'] > 7:
            suggestions.append("整體風險偏高，建議採用更保守的參數設定")
        elif risk_metrics['risk_score'] < 3:
            suggestions.append("風險設定過於保守，可適當提高風險以獲得更好收益")
        
        if not suggestions:
            suggestions.append("參數設定合理，可以開始使用")
        
        return suggestions
    
    def save_user_config(self, parameters: Dict[str, Any], 
                        config_name: str, user_id: str = "default") -> bool:
        """
        保存用戶配置
        
        Args:
            parameters: 參數字典
            config_name: 配置名稱
            user_id: 用戶ID
            
        Returns:
            bool: 保存是否成功
        """
        try:
            if user_id not in self.user_configs:
                self.user_configs[user_id] = {}
            
            self.user_configs[user_id][config_name] = {
                'parameters': parameters,
                'created_at': datetime.now().isoformat(),
                'risk_metrics': self.calculate_risk_metrics(parameters)
            }
            
            logger.info("用戶配置已保存: %s - %s", user_id, config_name)
            return True
            
        except Exception as e:
            logger.error("保存用戶配置失敗: %s", e)
            return False


def show_simple_config_panel() -> None:
    """
    顯示簡化參數設定面板頁面
    
    提供新手友好的參數設定功能，包括預設模板、
    視覺化調整、影響說明和優化建議。
    
    Side Effects:
        - 在 Streamlit 界面顯示簡化配置面板
        - 提供參數設定和優化功能
    """
    st.title("⚙️ 簡化參數設定")
    st.markdown("輕鬆配置交易參數，無需複雜設定！")
    
    # 初始化配置面板
    if 'config_panel' not in st.session_state:
        st.session_state.config_panel = SimpleConfigPanel()
    
    panel = st.session_state.config_panel
    
    # 模板選擇
    st.subheader("📋 選擇配置模板")
    
    templates = panel.parameter_templates
    template_names = {k: v['name'] for k, v in templates.items()}
    
    selected_template = st.selectbox(
        "選擇預設模板",
        list(templates.keys()),
        format_func=lambda x: template_names[x]
    )
    
    template_info = templates[selected_template]
    
    # 顯示模板資訊
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("風險等級", template_info['risk_level'])
    with col2:
        st.metric("預期收益", template_info['expected_return'])
    with col3:
        st.metric("適合對象", ", ".join(template_info['suitable_for']))
    
    st.info(f"📝 {template_info['description']}")
    
    # 參數設定區域
    st.subheader("🔧 參數設定")
    
    # 載入模板參數
    if st.button("載入模板參數"):
        st.session_state.current_parameters = template_info['parameters'].copy()
        st.success(f"✅ 已載入 {template_info['name']} 參數")
    
    # 初始化參數
    if 'current_parameters' not in st.session_state:
        st.session_state.current_parameters = template_info['parameters'].copy()
    
    parameters = st.session_state.current_parameters
    
    # 參數調整界面
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**基本參數**")
        
        # 初始資金
        param_def = panel.parameter_definitions['initial_capital']
        parameters['initial_capital'] = st.number_input(
            f"{param_def['name']} ({param_def['unit']})",
            min_value=param_def['range'][0],
            max_value=param_def['range'][1],
            value=parameters['initial_capital'],
            step=10000,
            help=param_def['tips']
        )
        
        # 部位大小
        param_def = panel.parameter_definitions['position_size']
        parameters['position_size'] = st.slider(
            f"{param_def['name']} ({param_def['unit']})",
            min_value=param_def['range'][0],
            max_value=param_def['range'][1],
            value=parameters['position_size'],
            step=0.01,
            format="%.2f",
            help=param_def['tips']
        )
        
        # 最大持倉數
        param_def = panel.parameter_definitions['max_positions']
        parameters['max_positions'] = st.slider(
            f"{param_def['name']} ({param_def['unit']})",
            min_value=param_def['range'][0],
            max_value=param_def['range'][1],
            value=parameters['max_positions'],
            step=1,
            help=param_def['tips']
        )
        
        # 再平衡頻率
        param_def = panel.parameter_definitions['rebalance_frequency']
        freq_options = param_def['options']
        freq_names = {'daily': '每日', 'weekly': '每週', 'monthly': '每月'}
        
        current_freq_idx = freq_options.index(parameters['rebalance_frequency'])
        selected_freq_idx = st.selectbox(
            param_def['name'],
            range(len(freq_options)),
            index=current_freq_idx,
            format_func=lambda x: freq_names[freq_options[x]],
            help=param_def['tips']
        )
        parameters['rebalance_frequency'] = freq_options[selected_freq_idx]
    
    with col2:
        st.write("**風險控制參數**")
        
        # 停損比例
        param_def = panel.parameter_definitions['stop_loss']
        parameters['stop_loss'] = st.slider(
            f"{param_def['name']} ({param_def['unit']})",
            min_value=param_def['range'][0],
            max_value=param_def['range'][1],
            value=parameters['stop_loss'],
            step=0.01,
            format="%.2f",
            help=param_def['tips']
        )
        
        # 止盈比例
        param_def = panel.parameter_definitions['take_profit']
        parameters['take_profit'] = st.slider(
            f"{param_def['name']} ({param_def['unit']})",
            min_value=param_def['range'][0],
            max_value=param_def['range'][1],
            value=parameters['take_profit'],
            step=0.01,
            format="%.2f",
            help=param_def['tips']
        )
        
        # 手續費率
        param_def = panel.parameter_definitions['commission']
        parameters['commission'] = st.slider(
            f"{param_def['name']} ({param_def['unit']})",
            min_value=param_def['range'][0],
            max_value=param_def['range'][1],
            value=parameters['commission'],
            step=0.0001,
            format="%.4f",
            help=param_def['tips']
        )
        
        # 滑點率
        param_def = panel.parameter_definitions['slippage']
        parameters['slippage'] = st.slider(
            f"{param_def['name']} ({param_def['unit']})",
            min_value=param_def['range'][0],
            max_value=param_def['range'][1],
            value=parameters['slippage'],
            step=0.0001,
            format="%.4f",
            help=param_def['tips']
        )
    
    # 風險分析
    st.subheader("📊 風險分析")
    
    risk_metrics = panel.calculate_risk_metrics(parameters)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "最大單筆虧損",
            f"{risk_metrics['max_single_loss']:.2%}",
            help="單一股票最大可能虧損比例"
        )
    
    with col2:
        st.metric(
            "最大總虧損",
            f"{risk_metrics['max_total_loss']:.2%}",
            help="所有持倉同時停損的最大虧損"
        )
    
    with col3:
        st.metric(
            "風險集中度",
            f"{risk_metrics['risk_concentration']:.2%}",
            help="總投資比例，越高風險越集中"
        )
    
    with col4:
        risk_score = risk_metrics['risk_score']
        risk_color = "🟢" if risk_score <= 3 else "🟡" if risk_score <= 7 else "🔴"
        st.metric(
            "風險評分",
            f"{risk_color} {risk_score:.1f}/10",
            help="綜合風險評分，10為最高風險"
        )
    
    # 參數驗證
    is_valid, errors = panel.validate_parameters(parameters)
    
    if not is_valid:
        st.error("❌ 參數設定有誤：")
        for error in errors:
            st.error(f"• {error}")
    else:
        st.success("✅ 參數設定有效")
    
    # 優化建議
    st.subheader("💡 優化建議")
    
    suggestions = panel.generate_optimization_suggestions(parameters)
    
    for i, suggestion in enumerate(suggestions, 1):
        if "風險過高" in suggestion or "過於嚴格" in suggestion:
            st.warning(f"{i}. {suggestion}")
        elif "過於保守" in suggestion:
            st.info(f"{i}. {suggestion}")
        else:
            st.success(f"{i}. {suggestion}")
    
    # 配置操作
    st.subheader("💾 配置管理")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        config_name = st.text_input("配置名稱", value="我的配置")
        
        if st.button("保存配置"):
            if panel.save_user_config(parameters, config_name):
                st.success("✅ 配置已保存！")
            else:
                st.error("❌ 保存失敗，請重試。")
    
    with col2:
        if st.button("重置為預設"):
            st.session_state.current_parameters = template_info['parameters'].copy()
            st.success("✅ 已重置為預設參數")
            st.rerun()
    
    with col3:
        if st.button("應用配置"):
            if is_valid:
                st.success("🚀 配置已應用，可以開始交易！")
                st.info("請前往回測頁面驗證策略效果")
            else:
                st.error("❌ 請先修正參數錯誤")
    
    # 參數影響說明
    with st.expander("📚 參數影響說明", expanded=False):
        for param_name, definition in panel.parameter_definitions.items():
            st.write(f"**{definition['name']}**")
            st.write(f"說明：{definition['description']}")
            st.write(f"影響：{definition['impact']}")
            st.write(f"建議：{definition['tips']}")
            st.write("---")
    
    # 側邊欄：快速操作
    with st.sidebar:
        st.subheader("⚡ 快速操作")
        
        if st.button("🎯 智能優化"):
            st.info("智能優化功能開發中...")
        
        if st.button("📊 參數比較"):
            st.info("參數比較功能開發中...")
        
        if st.button("🔄 恢復上次配置"):
            st.info("恢復配置功能開發中...")
        
        # 風險提醒
        st.subheader("⚠️ 風險提醒")
        
        if risk_metrics['risk_score'] > 7:
            st.error("當前風險設定較高，請謹慎使用")
        elif risk_metrics['risk_score'] > 5:
            st.warning("當前風險設定中等，建議充分測試")
        else:
            st.success("當前風險設定較低，適合新手使用")
        
        # 配置歷史
        st.subheader("📋 配置歷史")
        
        if panel.user_configs:
            for user_id, configs in panel.user_configs.items():
                for config_name, config_data in configs.items():
                    if st.button(f"載入 {config_name}", key=f"load_{config_name}"):
                        st.session_state.current_parameters = config_data['parameters'].copy()
                        st.success(f"✅ 已載入 {config_name}")
                        st.rerun()
        else:
            st.info("尚無保存的配置")
