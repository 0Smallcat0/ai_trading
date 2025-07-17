# -*- coding: utf-8 -*-
"""多代理管理界面組件

此模組提供統一的多代理管理和控制面板，包括：
- 代理註冊、啟用、停用、刪除
- 代理狀態實時監控
- 代理類型和投資風格展示
- 批量操作和代理分組管理

主要功能：
- 代理生命週期管理
- 實時狀態監控
- 批量操作支持
- 代理分組和篩選
- 配置管理
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# 導入多代理系統組件
try:
    from ...agents import AgentManager, TradingAgent
    from ...agents.personas import BuffettAgent, SorosAgent, SimonsAgent, DalioAgent, GrahamAgent
    from ...coordination import AgentCommunication
    from ...integration import SystemIntegrator
except ImportError:
    # 開發環境備用導入
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

# 設定日誌
logger = logging.getLogger(__name__)


class MultiAgentManagementUI:
    """
    多代理管理界面類
    
    提供完整的代理管理功能，包括創建、配置、監控和控制代理。
    """
    
    def __init__(self):
        """初始化多代理管理界面"""
        self.agent_manager = None
        self.communication = None
        self.system_integrator = None
        
        # 代理類型映射
        self.agent_types = {
            'buffett': {'class': BuffettAgent, 'name': '巴菲特代理', 'style': '價值投資'},
            'soros': {'class': SorosAgent, 'name': '索羅斯代理', 'style': '宏觀對沖'},
            'simons': {'class': SimonsAgent, 'name': '西蒙斯代理', 'style': '量化交易'},
            'dalio': {'class': DalioAgent, 'name': '達里奧代理', 'style': '風險平價'},
            'graham': {'class': GrahamAgent, 'name': '格雷厄姆代理', 'style': '深度價值'}
        }
        
        # 狀態顏色映射
        self.status_colors = {
            'online': '#28a745',    # 綠色
            'offline': '#6c757d',   # 灰色
            'busy': '#ffc107',      # 黃色
            'error': '#dc3545',     # 紅色
            'paused': '#17a2b8'     # 藍色
        }
    
    def render(self):
        """渲染多代理管理界面"""
        st.title("🤖 多代理管理中心")
        st.markdown("---")
        
        # 初始化系統組件
        self._initialize_components()
        
        # 創建標籤頁
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 代理總覽", 
            "➕ 創建代理", 
            "⚙️ 批量操作", 
            "📈 系統狀態"
        ])
        
        with tab1:
            self._render_agent_overview()
        
        with tab2:
            self._render_agent_creation()
        
        with tab3:
            self._render_batch_operations()
        
        with tab4:
            self._render_system_status()
    
    def _initialize_components(self):
        """初始化系統組件"""
        try:
            # 從session state獲取或創建組件
            if 'agent_manager' not in st.session_state:
                st.session_state.agent_manager = AgentManager()
            
            if 'communication' not in st.session_state:
                st.session_state.communication = AgentCommunication()
                st.session_state.communication.start()
            
            if 'system_integrator' not in st.session_state:
                st.session_state.system_integrator = SystemIntegrator()
            
            self.agent_manager = st.session_state.agent_manager
            self.communication = st.session_state.communication
            self.system_integrator = st.session_state.system_integrator
            
        except Exception as e:
            st.error(f"初始化系統組件失敗: {e}")
            logger.error(f"初始化系統組件失敗: {e}")
    
    def _render_agent_overview(self):
        """渲染代理總覽"""
        st.subheader("📊 代理總覽")
        
        # 獲取代理列表
        agents = self._get_agent_list()
        
        if not agents:
            st.info("🔍 目前沒有註冊的代理。請前往「創建代理」標籤頁添加代理。")
            return
        
        # 代理統計
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("總代理數", len(agents))
        
        with col2:
            active_count = len([a for a in agents if a.get('status') == 'online'])
            st.metric("活躍代理", active_count)
        
        with col3:
            error_count = len([a for a in agents if a.get('status') == 'error'])
            st.metric("錯誤代理", error_count, delta_color="inverse")
        
        with col4:
            if agents:
                avg_performance = sum(a.get('performance', 0) for a in agents) / len(agents)
                st.metric("平均績效", f"{avg_performance:.2%}")
        
        # 代理列表表格
        st.subheader("代理列表")
        
        # 篩選選項
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox(
                "狀態篩選",
                ["全部", "online", "offline", "busy", "error", "paused"]
            )
        
        with col2:
            style_filter = st.selectbox(
                "投資風格篩選",
                ["全部"] + list(set(a.get('style', '') for a in agents))
            )
        
        with col3:
            sort_by = st.selectbox(
                "排序方式",
                ["名稱", "狀態", "績效", "創建時間"]
            )
        
        # 應用篩選
        filtered_agents = self._filter_agents(agents, status_filter, style_filter)
        
        # 創建代理表格
        if filtered_agents:
            df = pd.DataFrame(filtered_agents)
            
            # 格式化表格
            df['狀態'] = df['status'].apply(self._format_status)
            df['績效'] = df['performance'].apply(lambda x: f"{x:.2%}")
            df['創建時間'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            
            # 選擇顯示列
            display_df = df[['name', '狀態', 'style', '績效', '創建時間']].copy()
            display_df.columns = ['代理名稱', '狀態', '投資風格', '績效', '創建時間']
            
            # 顯示表格
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
            
            # 代理操作
            st.subheader("代理操作")
            
            selected_agent = st.selectbox(
                "選擇代理",
                options=[a['id'] for a in filtered_agents],
                format_func=lambda x: next(a['name'] for a in filtered_agents if a['id'] == x)
            )
            
            if selected_agent:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("▶️ 啟動", key=f"start_{selected_agent}"):
                        self._start_agent(selected_agent)
                
                with col2:
                    if st.button("⏸️ 暫停", key=f"pause_{selected_agent}"):
                        self._pause_agent(selected_agent)
                
                with col3:
                    if st.button("🔄 重啟", key=f"restart_{selected_agent}"):
                        self._restart_agent(selected_agent)
                
                with col4:
                    if st.button("🗑️ 刪除", key=f"delete_{selected_agent}"):
                        self._delete_agent(selected_agent)
        
        # 代理狀態圖表
        self._render_agent_charts(agents)
    
    def _render_agent_creation(self):
        """渲染代理創建界面"""
        st.subheader("➕ 創建新代理")
        
        # 代理類型選擇
        col1, col2 = st.columns(2)
        
        with col1:
            agent_type = st.selectbox(
                "代理類型",
                options=list(self.agent_types.keys()),
                format_func=lambda x: self.agent_types[x]['name']
            )
        
        with col2:
            agent_name = st.text_input(
                "代理名稱",
                value=f"{self.agent_types[agent_type]['name']}_{datetime.now().strftime('%H%M%S')}"
            )
        
        # 代理配置
        st.subheader("代理配置")
        
        col1, col2 = st.columns(2)
        
        with col1:
            risk_preference = st.selectbox(
                "風險偏好",
                ["conservative", "moderate", "aggressive"],
                format_func=lambda x: {"conservative": "保守", "moderate": "中等", "aggressive": "激進"}[x]
            )
        
        with col2:
            initial_weight = st.slider(
                "初始權重",
                min_value=0.1,
                max_value=2.0,
                value=1.0,
                step=0.1
            )
        
        # 高級配置
        with st.expander("🔧 高級配置"):
            col1, col2 = st.columns(2)
            
            with col1:
                decision_threshold = st.slider(
                    "決策閾值",
                    min_value=0.1,
                    max_value=1.0,
                    value=0.6,
                    step=0.05
                )
            
            with col2:
                max_position_size = st.slider(
                    "最大倉位",
                    min_value=0.05,
                    max_value=0.5,
                    value=0.2,
                    step=0.05
                )
            
            enable_learning = st.checkbox("啟用學習模式", value=True)
            enable_communication = st.checkbox("啟用通信", value=True)
        
        # 創建按鈕
        if st.button("🚀 創建代理", type="primary"):
            success = self._create_agent(
                agent_type=agent_type,
                agent_name=agent_name,
                risk_preference=risk_preference,
                initial_weight=initial_weight,
                decision_threshold=decision_threshold,
                max_position_size=max_position_size,
                enable_learning=enable_learning,
                enable_communication=enable_communication
            )
            
            if success:
                st.success(f"✅ 代理 '{agent_name}' 創建成功！")
                st.rerun()
            else:
                st.error("❌ 代理創建失敗，請檢查配置。")
    
    def _render_batch_operations(self):
        """渲染批量操作界面"""
        st.subheader("⚙️ 批量操作")
        
        agents = self._get_agent_list()
        
        if not agents:
            st.info("沒有可操作的代理。")
            return
        
        # 代理選擇
        st.subheader("選擇代理")
        
        # 全選/取消全選
        col1, col2 = st.columns([1, 3])
        
        with col1:
            select_all = st.checkbox("全選")
        
        # 代理複選框
        selected_agents = []
        
        for i, agent in enumerate(agents):
            if st.checkbox(
                f"{agent['name']} ({agent['style']})",
                value=select_all,
                key=f"agent_select_{i}"
            ):
                selected_agents.append(agent['id'])
        
        if selected_agents:
            st.info(f"已選擇 {len(selected_agents)} 個代理")
            
            # 批量操作選項
            st.subheader("批量操作")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("🚀 批量啟動"):
                    self._batch_start_agents(selected_agents)
            
            with col2:
                if st.button("⏸️ 批量暫停"):
                    self._batch_pause_agents(selected_agents)
            
            with col3:
                if st.button("🔄 批量重啟"):
                    self._batch_restart_agents(selected_agents)
            
            with col4:
                if st.button("🗑️ 批量刪除", type="secondary"):
                    if st.checkbox("確認刪除", key="confirm_batch_delete"):
                        self._batch_delete_agents(selected_agents)
            
            # 批量配置更新
            st.subheader("批量配置更新")
            
            col1, col2 = st.columns(2)
            
            with col1:
                new_weight = st.number_input(
                    "新權重",
                    min_value=0.1,
                    max_value=2.0,
                    value=1.0,
                    step=0.1
                )
            
            with col2:
                new_risk_preference = st.selectbox(
                    "新風險偏好",
                    ["不變", "conservative", "moderate", "aggressive"],
                    format_func=lambda x: {
                        "不變": "不變",
                        "conservative": "保守",
                        "moderate": "中等",
                        "aggressive": "激進"
                    }[x]
                )
            
            if st.button("📝 應用配置更新"):
                self._batch_update_config(
                    selected_agents,
                    new_weight if new_weight != 1.0 else None,
                    new_risk_preference if new_risk_preference != "不變" else None
                )
    
    def _render_system_status(self):
        """渲染系統狀態"""
        st.subheader("📈 系統狀態")
        
        # 系統指標
        if self.system_integrator:
            status = self.system_integrator.get_system_status()
            
            # 系統概覽
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("系統狀態", status.get('system_state', 'unknown'))
            
            with col2:
                uptime = status.get('uptime', 0)
                st.metric("運行時間", f"{uptime/3600:.1f}小時")
            
            with col3:
                memory_usage = status.get('metrics', {}).get('memory_usage', 0)
                st.metric("記憶體使用", f"{memory_usage:.1f}%")
            
            with col4:
                cpu_usage = status.get('metrics', {}).get('cpu_usage', 0)
                st.metric("CPU使用", f"{cpu_usage:.1f}%")
            
            # 組件狀態
            st.subheader("組件狀態")
            
            components = status.get('components', {})
            if components:
                component_data = []
                for name, info in components.items():
                    component_data.append({
                        '組件名稱': name,
                        '類型': info.get('type', 'unknown'),
                        '狀態': info.get('status', 'unknown'),
                        '最後更新': info.get('last_update', 'unknown'),
                        '錯誤次數': info.get('error_count', 0)
                    })
                
                df = pd.DataFrame(component_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 通信狀態
        if self.communication:
            st.subheader("通信狀態")
            
            comm_stats = self.communication.get_communication_stats()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("已發送消息", comm_stats.total_messages_sent)
            
            with col2:
                st.metric("已接收消息", comm_stats.total_messages_received)
            
            with col3:
                st.metric("活躍連接", comm_stats.active_connections)

    def _get_agent_list(self) -> List[Dict[str, Any]]:
        """獲取代理列表"""
        try:
            if not self.agent_manager:
                return []

            agents = []
            for agent_id, agent in self.agent_manager.agents.items():
                # 獲取代理狀態
                status = self.communication.get_agent_status(agent_id) if self.communication else 'unknown'

                # 獲取代理績效（模擬數據）
                performance = getattr(agent, 'performance', 0.05)  # 默認5%

                agents.append({
                    'id': agent_id,
                    'name': agent.name,
                    'type': agent.__class__.__name__,
                    'style': getattr(agent, 'investment_style', 'unknown'),
                    'status': status,
                    'performance': performance,
                    'created_at': getattr(agent, 'created_at', datetime.now()),
                    'is_active': getattr(agent, 'is_active', False)
                })

            return agents

        except Exception as e:
            logger.error(f"獲取代理列表失敗: {e}")
            return []

    def _filter_agents(self, agents: List[Dict], status_filter: str, style_filter: str) -> List[Dict]:
        """篩選代理"""
        filtered = agents.copy()

        if status_filter != "全部":
            filtered = [a for a in filtered if a['status'] == status_filter]

        if style_filter != "全部":
            filtered = [a for a in filtered if a['style'] == style_filter]

        return filtered

    def _format_status(self, status: str) -> str:
        """格式化狀態顯示"""
        status_map = {
            'online': '🟢 在線',
            'offline': '⚫ 離線',
            'busy': '🟡 忙碌',
            'error': '🔴 錯誤',
            'paused': '🔵 暫停'
        }
        return status_map.get(status, f'❓ {status}')

    def _render_agent_charts(self, agents: List[Dict]):
        """渲染代理圖表"""
        if not agents:
            return

        st.subheader("📊 代理分析圖表")

        col1, col2 = st.columns(2)

        with col1:
            # 狀態分布餅圖
            status_counts = {}
            for agent in agents:
                status = agent['status']
                status_counts[status] = status_counts.get(status, 0) + 1

            if status_counts:
                fig = px.pie(
                    values=list(status_counts.values()),
                    names=list(status_counts.keys()),
                    title="代理狀態分布",
                    color_discrete_map=self.status_colors
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # 績效分布柱狀圖
            performance_data = [agent['performance'] for agent in agents]
            names = [agent['name'] for agent in agents]

            fig = go.Figure(data=[
                go.Bar(x=names, y=performance_data, name='績效')
            ])
            fig.update_layout(
                title="代理績效對比",
                xaxis_title="代理名稱",
                yaxis_title="績效 (%)",
                yaxis_tickformat='.1%'
            )
            st.plotly_chart(fig, use_container_width=True)

    def _create_agent(self, **kwargs) -> bool:
        """創建代理"""
        try:
            agent_type = kwargs['agent_type']
            agent_name = kwargs['agent_name']

            # 獲取代理類
            agent_class = self.agent_types[agent_type]['class']

            # 創建代理實例
            agent = agent_class(name=agent_name)

            # 設置代理屬性
            agent.risk_preference = kwargs.get('risk_preference', 'moderate')
            agent.decision_threshold = kwargs.get('decision_threshold', 0.6)
            agent.max_position_size = kwargs.get('max_position_size', 0.2)
            agent.created_at = datetime.now()

            # 註冊代理
            success = self.agent_manager.register_agent(agent)

            if success and self.communication:
                # 註冊到通信系統
                self.communication.register_agent(agent.agent_id)

            return success

        except Exception as e:
            logger.error(f"創建代理失敗: {e}")
            st.error(f"創建代理失敗: {e}")
            return False

    def _start_agent(self, agent_id: str):
        """啟動代理"""
        try:
            if self.communication:
                self.communication.set_agent_status(agent_id, 'online')
            st.success(f"代理 {agent_id} 已啟動")
            st.rerun()
        except Exception as e:
            st.error(f"啟動代理失敗: {e}")

    def _pause_agent(self, agent_id: str):
        """暫停代理"""
        try:
            if self.communication:
                self.communication.set_agent_status(agent_id, 'paused')
            st.success(f"代理 {agent_id} 已暫停")
            st.rerun()
        except Exception as e:
            st.error(f"暫停代理失敗: {e}")

    def _restart_agent(self, agent_id: str):
        """重啟代理"""
        try:
            if self.communication:
                self.communication.set_agent_status(agent_id, 'offline')
                self.communication.set_agent_status(agent_id, 'online')
            st.success(f"代理 {agent_id} 已重啟")
            st.rerun()
        except Exception as e:
            st.error(f"重啟代理失敗: {e}")

    def _delete_agent(self, agent_id: str):
        """刪除代理"""
        try:
            # 從代理管理器刪除
            if self.agent_manager and agent_id in self.agent_manager.agents:
                del self.agent_manager.agents[agent_id]

            # 從通信系統取消註冊
            if self.communication:
                self.communication.unregister_agent(agent_id)

            st.success(f"代理 {agent_id} 已刪除")
            st.rerun()
        except Exception as e:
            st.error(f"刪除代理失敗: {e}")

    def _batch_start_agents(self, agent_ids: List[str]):
        """批量啟動代理"""
        success_count = 0
        for agent_id in agent_ids:
            try:
                if self.communication:
                    self.communication.set_agent_status(agent_id, 'online')
                success_count += 1
            except Exception as e:
                logger.error(f"啟動代理 {agent_id} 失敗: {e}")

        st.success(f"成功啟動 {success_count}/{len(agent_ids)} 個代理")
        st.rerun()

    def _batch_pause_agents(self, agent_ids: List[str]):
        """批量暫停代理"""
        success_count = 0
        for agent_id in agent_ids:
            try:
                if self.communication:
                    self.communication.set_agent_status(agent_id, 'paused')
                success_count += 1
            except Exception as e:
                logger.error(f"暫停代理 {agent_id} 失敗: {e}")

        st.success(f"成功暫停 {success_count}/{len(agent_ids)} 個代理")
        st.rerun()

    def _batch_restart_agents(self, agent_ids: List[str]):
        """批量重啟代理"""
        success_count = 0
        for agent_id in agent_ids:
            try:
                if self.communication:
                    self.communication.set_agent_status(agent_id, 'offline')
                    self.communication.set_agent_status(agent_id, 'online')
                success_count += 1
            except Exception as e:
                logger.error(f"重啟代理 {agent_id} 失敗: {e}")

        st.success(f"成功重啟 {success_count}/{len(agent_ids)} 個代理")
        st.rerun()

    def _batch_delete_agents(self, agent_ids: List[str]):
        """批量刪除代理"""
        success_count = 0
        for agent_id in agent_ids:
            try:
                # 從代理管理器刪除
                if self.agent_manager and agent_id in self.agent_manager.agents:
                    del self.agent_manager.agents[agent_id]

                # 從通信系統取消註冊
                if self.communication:
                    self.communication.unregister_agent(agent_id)

                success_count += 1
            except Exception as e:
                logger.error(f"刪除代理 {agent_id} 失敗: {e}")

        st.success(f"成功刪除 {success_count}/{len(agent_ids)} 個代理")
        st.rerun()

    def _batch_update_config(self, agent_ids: List[str], new_weight: Optional[float], new_risk_preference: Optional[str]):
        """批量更新配置"""
        success_count = 0
        for agent_id in agent_ids:
            try:
                if self.agent_manager and agent_id in self.agent_manager.agents:
                    agent = self.agent_manager.agents[agent_id]

                    if new_weight is not None:
                        agent.weight = new_weight

                    if new_risk_preference is not None:
                        agent.risk_preference = new_risk_preference

                    success_count += 1
            except Exception as e:
                logger.error(f"更新代理 {agent_id} 配置失敗: {e}")

        st.success(f"成功更新 {success_count}/{len(agent_ids)} 個代理配置")
        st.rerun()


def render_multi_agent_management():
    """渲染多代理管理界面的便捷函數"""
    ui = MultiAgentManagementUI()
    ui.render()


def show():
    """顯示多代理管理界面（標準入口點）

    此函數提供標準的show()入口點，用於與其他組件保持一致的接口。
    """
    render_multi_agent_management()
