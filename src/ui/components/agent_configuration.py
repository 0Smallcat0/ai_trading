# -*- coding: utf-8 -*-
"""
代理配置和參數調整界面組件

此模組提供動態配置管理和參數優化界面，包括：
- 代理參數動態調整
- 協調機制配置
- 投資組合配置
- 系統參數優化和A/B測試

主要功能：
- 實時參數調整
- 配置模板管理
- A/B測試支持
- 參數優化建議
- 配置歷史追蹤
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import logging

# 設定日誌
logger = logging.getLogger(__name__)


class AgentConfigurationUI:
    """
    代理配置和參數調整界面類
    
    提供完整的代理配置管理功能。
    """
    
    def __init__(self):
        """初始化配置界面"""
        self.config_templates = {
            'conservative': {
                'name': '保守型配置',
                'risk_preference': 'conservative',
                'decision_threshold': 0.8,
                'max_position_size': 0.1,
                'stop_loss': 0.05,
                'take_profit': 0.1
            },
            'moderate': {
                'name': '穩健型配置',
                'risk_preference': 'moderate',
                'decision_threshold': 0.6,
                'max_position_size': 0.2,
                'stop_loss': 0.08,
                'take_profit': 0.15
            },
            'aggressive': {
                'name': '激進型配置',
                'risk_preference': 'aggressive',
                'decision_threshold': 0.4,
                'max_position_size': 0.3,
                'stop_loss': 0.12,
                'take_profit': 0.25
            }
        }
        
        self.coordination_methods = {
            'simple_voting': '簡單投票',
            'weighted_voting': '加權投票',
            'confidence_weighted': '信心度加權',
            'performance_weighted': '績效加權',
            'consensus': '共識機制',
            'hybrid': '混合協調'
        }
        
        self.conflict_resolutions = {
            'majority_rule': '多數決',
            'highest_confidence': '最高信心度',
            'best_performer': '最佳績效者',
            'weighted_average': '加權平均',
            'abstain': '棄權'
        }
    
    def render(self):
        """渲染配置界面"""
        st.title("⚙️ 代理配置和參數調整")
        st.markdown("---")
        
        # 創建標籤頁
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🤖 代理參數", 
            "🤝 協調機制", 
            "📊 投資組合", 
            "🧪 A/B測試", 
            "📋 配置管理"
        ])
        
        with tab1:
            self._render_agent_parameters()
        
        with tab2:
            self._render_coordination_config()
        
        with tab3:
            self._render_portfolio_config()
        
        with tab4:
            self._render_ab_testing()
        
        with tab5:
            self._render_config_management()
    
    def _render_agent_parameters(self):
        """渲染代理參數配置"""
        st.subheader("🤖 代理參數配置")
        
        # 獲取代理列表
        agents = self._get_agent_list()
        
        if not agents:
            st.info("🔍 目前沒有註冊的代理。請先創建代理。")
            return
        
        # 代理選擇
        selected_agent = st.selectbox(
            "選擇代理",
            options=[agent['id'] for agent in agents],
            format_func=lambda x: next(agent['name'] for agent in agents if agent['id'] == x)
        )
        
        if selected_agent:
            agent_data = next(agent for agent in agents if agent['id'] == selected_agent)
            
            st.subheader(f"配置代理: {agent_data['name']}")
            
            # 基本參數
            st.write("**基本參數**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                risk_preference = st.selectbox(
                    "風險偏好",
                    ["conservative", "moderate", "aggressive"],
                    index=["conservative", "moderate", "aggressive"].index(
                        agent_data.get('risk_preference', 'moderate')
                    ),
                    format_func=lambda x: {"conservative": "保守", "moderate": "穩健", "aggressive": "激進"}[x]
                )
                
                decision_threshold = st.slider(
                    "決策閾值",
                    min_value=0.1,
                    max_value=1.0,
                    value=agent_data.get('decision_threshold', 0.6),
                    step=0.05,
                    help="代理做出決策所需的最低信心度"
                )
            
            with col2:
                max_position_size = st.slider(
                    "最大倉位",
                    min_value=0.05,
                    max_value=0.5,
                    value=agent_data.get('max_position_size', 0.2),
                    step=0.05,
                    format="%",
                    help="單一資產的最大倉位比例"
                )
                
                weight = st.slider(
                    "代理權重",
                    min_value=0.1,
                    max_value=3.0,
                    value=agent_data.get('weight', 1.0),
                    step=0.1,
                    help="代理在協調決策中的權重"
                )
            
            # 風險管理參數
            st.write("**風險管理參數**")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                stop_loss = st.slider(
                    "止損比例",
                    min_value=0.01,
                    max_value=0.2,
                    value=agent_data.get('stop_loss', 0.08),
                    step=0.01,
                    format="%"
                )
            
            with col2:
                take_profit = st.slider(
                    "止盈比例",
                    min_value=0.05,
                    max_value=0.5,
                    value=agent_data.get('take_profit', 0.15),
                    step=0.05,
                    format="%"
                )
            
            with col3:
                max_drawdown = st.slider(
                    "最大回撤限制",
                    min_value=0.05,
                    max_value=0.3,
                    value=agent_data.get('max_drawdown', 0.15),
                    step=0.05,
                    format="%"
                )
            
            # 高級參數
            with st.expander("🔧 高級參數"):
                col1, col2 = st.columns(2)
                
                with col1:
                    learning_rate = st.slider(
                        "學習率",
                        min_value=0.001,
                        max_value=0.1,
                        value=agent_data.get('learning_rate', 0.01),
                        step=0.001,
                        format="%.3f"
                    )
                    
                    memory_length = st.slider(
                        "記憶長度",
                        min_value=10,
                        max_value=1000,
                        value=agent_data.get('memory_length', 100),
                        step=10,
                        help="代理記住的歷史決策數量"
                    )
                
                with col2:
                    update_frequency = st.selectbox(
                        "更新頻率",
                        ["realtime", "hourly", "daily", "weekly"],
                        index=["realtime", "hourly", "daily", "weekly"].index(
                            agent_data.get('update_frequency', 'daily')
                        ),
                        format_func=lambda x: {
                            "realtime": "實時", "hourly": "每小時", 
                            "daily": "每日", "weekly": "每週"
                        }[x]
                    )
                    
                    enable_adaptation = st.checkbox(
                        "啟用自適應",
                        value=agent_data.get('enable_adaptation', True),
                        help="允許代理根據績效自動調整參數"
                    )
            
            # 配置模板
            st.subheader("配置模板")
            
            template_col1, template_col2 = st.columns([2, 1])
            
            with template_col1:
                selected_template = st.selectbox(
                    "選擇配置模板",
                    options=list(self.config_templates.keys()),
                    format_func=lambda x: self.config_templates[x]['name']
                )
            
            with template_col2:
                if st.button("應用模板"):
                    self._apply_template(selected_agent, selected_template)
                    st.success("模板已應用！")
                    st.rerun()
            
            # 保存配置
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("💾 保存配置", type="primary"):
                    config = {
                        'risk_preference': risk_preference,
                        'decision_threshold': decision_threshold,
                        'max_position_size': max_position_size,
                        'weight': weight,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'max_drawdown': max_drawdown,
                        'learning_rate': learning_rate,
                        'memory_length': memory_length,
                        'update_frequency': update_frequency,
                        'enable_adaptation': enable_adaptation
                    }
                    
                    self._save_agent_config(selected_agent, config)
                    st.success("配置已保存！")
            
            with col2:
                if st.button("🔄 重置為默認"):
                    self._reset_agent_config(selected_agent)
                    st.success("已重置為默認配置！")
                    st.rerun()
            
            with col3:
                if st.button("📊 預覽效果"):
                    self._preview_config_effect(selected_agent, {
                        'risk_preference': risk_preference,
                        'decision_threshold': decision_threshold,
                        'max_position_size': max_position_size
                    })
    
    def _render_coordination_config(self):
        """渲染協調機制配置"""
        st.subheader("🤝 協調機制配置")
        
        # 當前協調配置
        current_config = self._get_coordination_config()
        
        col1, col2 = st.columns(2)
        
        with col1:
            coordination_method = st.selectbox(
                "協調方法",
                options=list(self.coordination_methods.keys()),
                index=list(self.coordination_methods.keys()).index(
                    current_config.get('coordination_method', 'hybrid')
                ),
                format_func=lambda x: self.coordination_methods[x]
            )
        
        with col2:
            conflict_resolution = st.selectbox(
                "衝突解決策略",
                options=list(self.conflict_resolutions.keys()),
                index=list(self.conflict_resolutions.keys()).index(
                    current_config.get('conflict_resolution', 'weighted_average')
                ),
                format_func=lambda x: self.conflict_resolutions[x]
            )
        
        # 協調參數
        st.subheader("協調參數")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_agents_required = st.slider(
                "最少代理數量",
                min_value=1,
                max_value=10,
                value=current_config.get('min_agents_required', 2),
                help="進行協調決策所需的最少代理數量"
            )
        
        with col2:
            consensus_threshold = st.slider(
                "共識閾值",
                min_value=0.5,
                max_value=1.0,
                value=current_config.get('consensus_threshold', 0.7),
                step=0.05,
                help="達成共識所需的一致性比例"
            )
        
        with col3:
            timeout_seconds = st.slider(
                "決策超時 (秒)",
                min_value=1,
                max_value=60,
                value=current_config.get('timeout_seconds', 10),
                help="等待代理響應的最大時間"
            )
        
        # 權重調整配置
        st.subheader("權重調整配置")
        
        col1, col2 = st.columns(2)
        
        with col1:
            weight_adjustment_method = st.selectbox(
                "權重調整方法",
                ["performance_based", "risk_adjusted", "sharpe_ratio", "ensemble"],
                format_func=lambda x: {
                    "performance_based": "基於績效",
                    "risk_adjusted": "風險調整",
                    "sharpe_ratio": "夏普比率",
                    "ensemble": "集成方法"
                }[x]
            )
        
        with col2:
            adjustment_frequency = st.selectbox(
                "調整頻率",
                ["daily", "weekly", "monthly", "quarterly"],
                format_func=lambda x: {
                    "daily": "每日", "weekly": "每週",
                    "monthly": "每月", "quarterly": "每季"
                }[x]
            )
        
        # 保存協調配置
        if st.button("💾 保存協調配置", type="primary"):
            coordination_config = {
                'coordination_method': coordination_method,
                'conflict_resolution': conflict_resolution,
                'min_agents_required': min_agents_required,
                'consensus_threshold': consensus_threshold,
                'timeout_seconds': timeout_seconds,
                'weight_adjustment_method': weight_adjustment_method,
                'adjustment_frequency': adjustment_frequency
            }
            
            self._save_coordination_config(coordination_config)
            st.success("協調配置已保存！")
    
    def _render_portfolio_config(self):
        """渲染投資組合配置"""
        st.subheader("📊 投資組合配置")
        
        # 當前投資組合配置
        current_config = self._get_portfolio_config()
        
        # 基本配置
        st.write("**基本配置**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            initial_capital = st.number_input(
                "初始資金",
                min_value=10000,
                max_value=10000000,
                value=current_config.get('initial_capital', 1000000),
                step=10000,
                format="%d"
            )
            
            target_volatility = st.slider(
                "目標波動率",
                min_value=0.05,
                max_value=0.3,
                value=current_config.get('target_volatility', 0.15),
                step=0.01,
                format="%.2f"
            )
        
        with col2:
            max_position_size = st.slider(
                "最大單一倉位",
                min_value=0.05,
                max_value=0.5,
                value=current_config.get('max_position_size', 0.2),
                step=0.05,
                format="%.2f"
            )
            
            rebalance_threshold = st.slider(
                "再平衡閾值",
                min_value=0.01,
                max_value=0.1,
                value=current_config.get('rebalance_threshold', 0.05),
                step=0.01,
                format="%.2f"
            )
        
        # 風險管理
        st.write("**風險管理**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            max_drawdown_limit = st.slider(
                "最大回撤限制",
                min_value=0.05,
                max_value=0.3,
                value=current_config.get('max_drawdown_limit', 0.2),
                step=0.05,
                format="%.2f"
            )
        
        with col2:
            var_confidence = st.slider(
                "VaR信心水平",
                min_value=0.9,
                max_value=0.99,
                value=current_config.get('var_confidence', 0.95),
                step=0.01,
                format="%.2f"
            )
        
        with col3:
            correlation_limit = st.slider(
                "相關性限制",
                min_value=0.3,
                max_value=0.9,
                value=current_config.get('correlation_limit', 0.7),
                step=0.05,
                format="%.2f"
            )
        
        # 交易設置
        st.write("**交易設置**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            transaction_cost = st.slider(
                "交易成本 (%)",
                min_value=0.001,
                max_value=0.01,
                value=current_config.get('transaction_cost', 0.002),
                step=0.001,
                format="%.3f"
            )
        
        with col2:
            slippage = st.slider(
                "滑點 (%)",
                min_value=0.001,
                max_value=0.01,
                value=current_config.get('slippage', 0.001),
                step=0.001,
                format="%.3f"
            )
        
        # 保存投資組合配置
        if st.button("💾 保存投資組合配置", type="primary"):
            portfolio_config = {
                'initial_capital': initial_capital,
                'target_volatility': target_volatility,
                'max_position_size': max_position_size,
                'rebalance_threshold': rebalance_threshold,
                'max_drawdown_limit': max_drawdown_limit,
                'var_confidence': var_confidence,
                'correlation_limit': correlation_limit,
                'transaction_cost': transaction_cost,
                'slippage': slippage
            }
            
            self._save_portfolio_config(portfolio_config)
            st.success("投資組合配置已保存！")
    
    def _render_ab_testing(self):
        """渲染A/B測試"""
        st.subheader("🧪 A/B測試")
        
        st.info("A/B測試功能允許您比較不同配置的效果，幫助優化系統參數。")
        
        # 測試配置
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**配置A (對照組)**")
            config_a = self._render_test_config("A")
        
        with col2:
            st.write("**配置B (實驗組)**")
            config_b = self._render_test_config("B")
        
        # 測試設置
        st.subheader("測試設置")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            test_duration = st.selectbox(
                "測試持續時間",
                ["1天", "1週", "2週", "1個月"],
                index=1
            )
        
        with col2:
            traffic_split = st.slider(
                "流量分配 (A:B)",
                min_value=10,
                max_value=90,
                value=50,
                help="配置A獲得的流量百分比"
            )
        
        with col3:
            significance_level = st.slider(
                "顯著性水平",
                min_value=0.01,
                max_value=0.1,
                value=0.05,
                step=0.01,
                format="%.2f"
            )
        
        # 開始測試
        if st.button("🚀 開始A/B測試", type="primary"):
            self._start_ab_test(config_a, config_b, test_duration, traffic_split, significance_level)
            st.success("A/B測試已開始！")
        
        # 顯示當前測試
        self._display_current_tests()
    
    def _render_config_management(self):
        """渲染配置管理"""
        st.subheader("📋 配置管理")
        
        # 配置歷史
        st.write("**配置歷史**")
        
        config_history = self._get_config_history()
        
        if config_history:
            df = pd.DataFrame(config_history)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暫無配置歷史記錄。")
        
        # 配置導入/導出
        st.write("**配置導入/導出**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📤 導出當前配置"):
                config = self._export_current_config()
                st.download_button(
                    label="下載配置文件",
                    data=json.dumps(config, indent=2, ensure_ascii=False),
                    file_name=f"agent_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        with col2:
            uploaded_file = st.file_uploader(
                "📥 導入配置文件",
                type=['json'],
                help="上傳之前導出的配置文件"
            )
            
            if uploaded_file is not None:
                try:
                    config = json.load(uploaded_file)
                    if st.button("應用導入的配置"):
                        self._import_config(config)
                        st.success("配置已導入並應用！")
                        st.rerun()
                except Exception as e:
                    st.error(f"配置文件格式錯誤: {e}")
        
        # 配置備份
        st.write("**配置備份**")
        
        if st.button("💾 創建配置備份"):
            backup_id = self._create_config_backup()
            st.success(f"配置備份已創建: {backup_id}")
        
        # 顯示備份列表
        backups = self._get_config_backups()
        if backups:
            selected_backup = st.selectbox(
                "選擇備份恢復",
                options=backups,
                format_func=lambda x: f"{x['name']} ({x['date']})"
            )
            
            if st.button("🔄 恢復選中備份"):
                self._restore_config_backup(selected_backup['id'])
                st.success("配置已恢復！")
                st.rerun()

    def _get_agent_list(self) -> List[Dict[str, Any]]:
        """獲取代理列表"""
        try:
            if 'agent_manager' not in st.session_state:
                return []

            agent_manager = st.session_state.agent_manager
            agents = []

            for agent_id, agent in agent_manager.agents.items():
                agents.append({
                    'id': agent_id,
                    'name': agent.name,
                    'type': agent.__class__.__name__,
                    'risk_preference': getattr(agent, 'risk_preference', 'moderate'),
                    'decision_threshold': getattr(agent, 'decision_threshold', 0.6),
                    'max_position_size': getattr(agent, 'max_position_size', 0.2),
                    'weight': getattr(agent, 'weight', 1.0),
                    'stop_loss': getattr(agent, 'stop_loss', 0.08),
                    'take_profit': getattr(agent, 'take_profit', 0.15),
                    'max_drawdown': getattr(agent, 'max_drawdown', 0.15),
                    'learning_rate': getattr(agent, 'learning_rate', 0.01),
                    'memory_length': getattr(agent, 'memory_length', 100),
                    'update_frequency': getattr(agent, 'update_frequency', 'daily'),
                    'enable_adaptation': getattr(agent, 'enable_adaptation', True)
                })

            return agents

        except Exception as e:
            logger.error(f"獲取代理列表失敗: {e}")
            return []

    def _apply_template(self, agent_id: str, template_key: str):
        """應用配置模板"""
        try:
            template = self.config_templates[template_key]

            if 'agent_manager' in st.session_state:
                agent_manager = st.session_state.agent_manager
                if agent_id in agent_manager.agents:
                    agent = agent_manager.agents[agent_id]

                    for key, value in template.items():
                        if key != 'name':
                            setattr(agent, key, value)

                    logger.info(f"應用模板 {template_key} 到代理 {agent_id}")

        except Exception as e:
            logger.error(f"應用模板失敗: {e}")
            st.error(f"應用模板失敗: {e}")

    def _save_agent_config(self, agent_id: str, config: Dict[str, Any]):
        """保存代理配置"""
        try:
            if 'agent_manager' in st.session_state:
                agent_manager = st.session_state.agent_manager
                if agent_id in agent_manager.agents:
                    agent = agent_manager.agents[agent_id]

                    for key, value in config.items():
                        setattr(agent, key, value)

                    # 記錄配置歷史
                    self._record_config_change(agent_id, config)

                    logger.info(f"保存代理 {agent_id} 配置")

        except Exception as e:
            logger.error(f"保存代理配置失敗: {e}")
            st.error(f"保存配置失敗: {e}")

    def _reset_agent_config(self, agent_id: str):
        """重置代理配置為默認值"""
        try:
            default_config = {
                'risk_preference': 'moderate',
                'decision_threshold': 0.6,
                'max_position_size': 0.2,
                'weight': 1.0,
                'stop_loss': 0.08,
                'take_profit': 0.15,
                'max_drawdown': 0.15,
                'learning_rate': 0.01,
                'memory_length': 100,
                'update_frequency': 'daily',
                'enable_adaptation': True
            }

            self._save_agent_config(agent_id, default_config)

        except Exception as e:
            logger.error(f"重置代理配置失敗: {e}")
            st.error(f"重置配置失敗: {e}")

    def _preview_config_effect(self, agent_id: str, config: Dict[str, Any]):
        """預覽配置效果"""
        st.subheader("配置效果預覽")

        # 模擬配置效果
        risk_score = self._calculate_risk_score(config)
        expected_return = self._estimate_expected_return(config)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("風險評分", f"{risk_score:.1f}/10")

        with col2:
            st.metric("預期年化收益", f"{expected_return:.1%}")

        with col3:
            volatility = self._estimate_volatility(config)
            st.metric("預期波動率", f"{volatility:.1%}")

        # 風險收益圖
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=[volatility],
            y=[expected_return],
            mode='markers',
            marker=dict(size=15, color='red'),
            name='新配置'
        ))

        # 添加基準點
        benchmark_configs = ['conservative', 'moderate', 'aggressive']
        for benchmark in benchmark_configs:
            bench_config = self.config_templates[benchmark]
            bench_vol = self._estimate_volatility(bench_config)
            bench_ret = self._estimate_expected_return(bench_config)

            fig.add_trace(go.Scatter(
                x=[bench_vol],
                y=[bench_ret],
                mode='markers',
                marker=dict(size=10),
                name=bench_config['name']
            ))

        fig.update_layout(
            title="風險收益預覽",
            xaxis_title="波動率",
            yaxis_title="預期收益率",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    def _calculate_risk_score(self, config: Dict[str, Any]) -> float:
        """計算風險評分"""
        risk_factors = {
            'max_position_size': config.get('max_position_size', 0.2) * 20,  # 0-10
            'decision_threshold': (1 - config.get('decision_threshold', 0.6)) * 10,  # 0-10
            'stop_loss': (1 - config.get('stop_loss', 0.08) / 0.2) * 10  # 0-10
        }

        return np.mean(list(risk_factors.values()))

    def _estimate_expected_return(self, config: Dict[str, Any]) -> float:
        """估算預期收益率"""
        base_return = 0.08  # 8% 基準收益率

        # 根據風險偏好調整
        risk_pref = config.get('risk_preference', 'moderate')
        if risk_pref == 'conservative':
            return base_return * 0.7
        elif risk_pref == 'aggressive':
            return base_return * 1.5
        else:
            return base_return

    def _estimate_volatility(self, config: Dict[str, Any]) -> float:
        """估算波動率"""
        base_volatility = 0.15  # 15% 基準波動率

        # 根據最大倉位調整
        position_factor = config.get('max_position_size', 0.2) / 0.2

        # 根據風險偏好調整
        risk_pref = config.get('risk_preference', 'moderate')
        if risk_pref == 'conservative':
            risk_factor = 0.7
        elif risk_pref == 'aggressive':
            risk_factor = 1.5
        else:
            risk_factor = 1.0

        return base_volatility * position_factor * risk_factor

    def _get_coordination_config(self) -> Dict[str, Any]:
        """獲取協調配置"""
        # 從session state或默認配置獲取
        return st.session_state.get('coordination_config', {
            'coordination_method': 'hybrid',
            'conflict_resolution': 'weighted_average',
            'min_agents_required': 2,
            'consensus_threshold': 0.7,
            'timeout_seconds': 10,
            'weight_adjustment_method': 'ensemble',
            'adjustment_frequency': 'daily'
        })

    def _save_coordination_config(self, config: Dict[str, Any]):
        """保存協調配置"""
        st.session_state.coordination_config = config
        logger.info("保存協調配置")

    def _get_portfolio_config(self) -> Dict[str, Any]:
        """獲取投資組合配置"""
        return st.session_state.get('portfolio_config', {
            'initial_capital': 1000000,
            'target_volatility': 0.15,
            'max_position_size': 0.2,
            'rebalance_threshold': 0.05,
            'max_drawdown_limit': 0.2,
            'var_confidence': 0.95,
            'correlation_limit': 0.7,
            'transaction_cost': 0.002,
            'slippage': 0.001
        })

    def _save_portfolio_config(self, config: Dict[str, Any]):
        """保存投資組合配置"""
        st.session_state.portfolio_config = config
        logger.info("保存投資組合配置")

    def _render_test_config(self, group: str) -> Dict[str, Any]:
        """渲染測試配置"""
        config = {}

        config['risk_preference'] = st.selectbox(
            f"風險偏好 {group}",
            ["conservative", "moderate", "aggressive"],
            key=f"risk_pref_{group}"
        )

        config['decision_threshold'] = st.slider(
            f"決策閾值 {group}",
            min_value=0.1,
            max_value=1.0,
            value=0.6,
            step=0.05,
            key=f"threshold_{group}"
        )

        config['max_position_size'] = st.slider(
            f"最大倉位 {group}",
            min_value=0.05,
            max_value=0.5,
            value=0.2,
            step=0.05,
            key=f"position_{group}"
        )

        return config

    def _start_ab_test(self, config_a: Dict, config_b: Dict, duration: str, split: int, significance: float):
        """開始A/B測試"""
        test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        test_config = {
            'id': test_id,
            'config_a': config_a,
            'config_b': config_b,
            'duration': duration,
            'traffic_split': split,
            'significance_level': significance,
            'start_time': datetime.now(),
            'status': 'running'
        }

        # 保存到session state
        if 'ab_tests' not in st.session_state:
            st.session_state.ab_tests = []

        st.session_state.ab_tests.append(test_config)
        logger.info(f"開始A/B測試: {test_id}")

    def _display_current_tests(self):
        """顯示當前測試"""
        if 'ab_tests' not in st.session_state or not st.session_state.ab_tests:
            st.info("目前沒有運行中的A/B測試。")
            return

        st.subheader("當前測試")

        for test in st.session_state.ab_tests:
            with st.expander(f"測試 {test['id']} - {test['status']}"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**開始時間**: {test['start_time'].strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"**持續時間**: {test['duration']}")

                with col2:
                    st.write(f"**流量分配**: {test['traffic_split']}% / {100-test['traffic_split']}%")
                    st.write(f"**顯著性水平**: {test['significance_level']}")

                with col3:
                    if st.button(f"停止測試", key=f"stop_{test['id']}"):
                        test['status'] = 'stopped'
                        st.rerun()

    def _get_config_history(self) -> List[Dict[str, Any]]:
        """獲取配置歷史"""
        return st.session_state.get('config_history', [])

    def _record_config_change(self, agent_id: str, config: Dict[str, Any]):
        """記錄配置變更"""
        if 'config_history' not in st.session_state:
            st.session_state.config_history = []

        history_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'agent_id': agent_id,
            'config': config.copy(),
            'user': 'current_user'  # 實際應用中應該是真實用戶
        }

        st.session_state.config_history.append(history_entry)

        # 保持歷史記錄在合理範圍內
        if len(st.session_state.config_history) > 100:
            st.session_state.config_history = st.session_state.config_history[-50:]

    def _export_current_config(self) -> Dict[str, Any]:
        """導出當前配置"""
        return {
            'agents': self._get_agent_list(),
            'coordination': self._get_coordination_config(),
            'portfolio': self._get_portfolio_config(),
            'export_time': datetime.now().isoformat()
        }

    def _import_config(self, config: Dict[str, Any]):
        """導入配置"""
        try:
            if 'coordination' in config:
                self._save_coordination_config(config['coordination'])

            if 'portfolio' in config:
                self._save_portfolio_config(config['portfolio'])

            if 'agents' in config:
                for agent_config in config['agents']:
                    self._save_agent_config(agent_config['id'], agent_config)

            logger.info("配置導入成功")

        except Exception as e:
            logger.error(f"配置導入失敗: {e}")
            raise

    def _create_config_backup(self) -> str:
        """創建配置備份"""
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup = {
            'id': backup_id,
            'name': f"配置備份 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'config': self._export_current_config()
        }

        if 'config_backups' not in st.session_state:
            st.session_state.config_backups = []

        st.session_state.config_backups.append(backup)

        return backup_id

    def _get_config_backups(self) -> List[Dict[str, Any]]:
        """獲取配置備份列表"""
        return st.session_state.get('config_backups', [])

    def _restore_config_backup(self, backup_id: str):
        """恢復配置備份"""
        backups = self._get_config_backups()
        backup = next((b for b in backups if b['id'] == backup_id), None)

        if backup:
            self._import_config(backup['config'])
            logger.info(f"恢復配置備份: {backup_id}")


def render_agent_configuration():
    """渲染代理配置界面的便捷函數"""
    ui = AgentConfigurationUI()
    ui.render()
