# -*- coding: utf-8 -*-
"""
Streamlit界面整合

此模組提供統一的Streamlit界面整合，
將所有增強功能整合到統一的Web界面中。

主要功能：
- 統一的導航系統
- 功能模組整合
- 用戶界面統一
- 狀態管理
- 錯誤處理

整合策略：
- 保持原始項目界面風格
- 添加新功能頁面
- 提供統一的用戶體驗
- 實現功能間的無縫切換
"""

import logging
import streamlit as st
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd

# 設定日誌
logger = logging.getLogger(__name__)


class StreamlitIntegration:
    """
    Streamlit界面整合器
    
    統一管理所有Streamlit界面組件
    """
    
    def __init__(self, system_integrator):
        """
        初始化Streamlit整合器
        
        Args:
            system_integrator: 系統整合器實例
        """
        self.system_integrator = system_integrator
        self.interface_bridge = system_integrator.interface_bridge
        
        # 頁面配置
        self.pages = {}
        self.navigation = {}
        
        # 狀態管理
        self.session_state_keys = [
            'current_page',
            'user_id',
            'integration_status',
            'last_update'
        ]
        
        # 初始化會話狀態
        self._initialize_session_state()
        
        # 設置頁面配置
        self._setup_pages()
        
        logger.info("Streamlit界面整合器初始化完成")
    
    def _initialize_session_state(self):
        """初始化會話狀態"""
        try:
            # 初始化基本狀態
            if 'current_page' not in st.session_state:
                st.session_state.current_page = 'dashboard'
            
            if 'user_id' not in st.session_state:
                st.session_state.user_id = 'default_user'
            
            if 'integration_status' not in st.session_state:
                st.session_state.integration_status = {}
            
            if 'last_update' not in st.session_state:
                st.session_state.last_update = datetime.now()
            
            # 初始化功能狀態
            if 'agents_enabled' not in st.session_state:
                st.session_state.agents_enabled = True
            
            if 'rl_enabled' not in st.session_state:
                st.session_state.rl_enabled = True
            
            if 'knowledge_enabled' not in st.session_state:
                st.session_state.knowledge_enabled = True
            
            if 'data_sources_enabled' not in st.session_state:
                st.session_state.data_sources_enabled = True
            
        except Exception as e:
            logger.error(f"會話狀態初始化失敗: {e}")
    
    def _setup_pages(self):
        """設置頁面配置"""
        try:
            self.pages = {
                'dashboard': {
                    'title': '🏠 系統儀表板',
                    'icon': '🏠',
                    'description': '系統整合狀態和概覽',
                    'category': 'main',
                    'order': 1
                },
                'trading': {
                    'title': '📈 交易管理',
                    'icon': '📈',
                    'description': '多代理交易決策和執行',
                    'category': 'trading',
                    'order': 2
                },
                'portfolio': {
                    'title': '💼 投資組合',
                    'icon': '💼',
                    'description': '投資組合管理和分析',
                    'category': 'trading',
                    'order': 3
                },
                'data_management': {
                    'title': '📊 數據管理',
                    'icon': '📊',
                    'description': '數據源管理和監控',
                    'category': 'data',
                    'order': 4
                },
                'knowledge_base': {
                    'title': '📚 知識庫',
                    'icon': '📚',
                    'description': '知識搜索和管理',
                    'category': 'learning',
                    'order': 5
                },
                'learning_center': {
                    'title': '🎓 學習中心',
                    'icon': '🎓',
                    'description': '交互式學習系統',
                    'category': 'learning',
                    'order': 6
                },
                'rl_training': {
                    'title': '🤖 強化學習',
                    'icon': '🤖',
                    'description': '強化學習訓練和管理',
                    'category': 'ai',
                    'order': 7
                },
                'system_settings': {
                    'title': '⚙️ 系統設置',
                    'icon': '⚙️',
                    'description': '系統配置和管理',
                    'category': 'admin',
                    'order': 8
                }
            }
            
            # 設置導航結構
            self.navigation = {
                'main': ['dashboard'],
                'trading': ['trading', 'portfolio'],
                'data': ['data_management'],
                'learning': ['knowledge_base', 'learning_center'],
                'ai': ['rl_training'],
                'admin': ['system_settings']
            }
            
        except Exception as e:
            logger.error(f"頁面配置設置失敗: {e}")
    
    def render_sidebar(self):
        """渲染側邊欄"""
        try:
            with st.sidebar:
                st.title("🚀 AI量化交易系統")
                st.markdown("---")
                
                # 系統狀態指示器
                self._render_system_status()
                
                st.markdown("---")
                
                # 導航菜單
                self._render_navigation_menu()
                
                st.markdown("---")
                
                # 快速操作
                self._render_quick_actions()
                
        except Exception as e:
            logger.error(f"側邊欄渲染失敗: {e}")
            st.sidebar.error("側邊欄載入失敗")
    
    def _render_system_status(self):
        """渲染系統狀態"""
        try:
            st.subheader("📊 系統狀態")
            
            # 獲取整合狀態
            integration_status = self.system_integrator.get_integration_status()
            
            # 顯示各組件狀態
            components = {
                'multi_agent': '🤖 多代理系統',
                'reinforcement_learning': '🧠 強化學習',
                'knowledge_system': '📚 知識庫',
                'data_sources': '📊 數據源'
            }
            
            for component_key, component_name in components.items():
                if component_key in integration_status:
                    status = integration_status[component_key]
                    if status.status == 'active':
                        st.success(f"{component_name} ✅")
                    elif status.status == 'error':
                        st.error(f"{component_name} ❌")
                    else:
                        st.warning(f"{component_name} ⚠️")
                else:
                    st.info(f"{component_name} ℹ️")
            
        except Exception as e:
            logger.error(f"系統狀態渲染失敗: {e}")
            st.error("系統狀態載入失敗")
    
    def _render_navigation_menu(self):
        """渲染導航菜單"""
        try:
            st.subheader("🧭 導航菜單")
            
            # 按類別組織頁面
            for category, page_keys in self.navigation.items():
                if not page_keys:
                    continue
                
                # 類別標題
                category_names = {
                    'main': '主要功能',
                    'trading': '交易功能',
                    'data': '數據管理',
                    'learning': '學習系統',
                    'ai': 'AI功能',
                    'admin': '系統管理'
                }
                
                st.markdown(f"**{category_names.get(category, category)}**")
                
                # 頁面按鈕
                for page_key in page_keys:
                    if page_key in self.pages:
                        page_info = self.pages[page_key]
                        
                        # 檢查頁面是否可用
                        if self._is_page_available(page_key):
                            if st.button(
                                page_info['title'],
                                key=f"nav_{page_key}",
                                help=page_info['description']
                            ):
                                st.session_state.current_page = page_key
                                st.rerun()
                        else:
                            st.button(
                                f"{page_info['title']} (不可用)",
                                disabled=True,
                                key=f"nav_{page_key}_disabled"
                            )
                
                st.markdown("")  # 添加間距
            
        except Exception as e:
            logger.error(f"導航菜單渲染失敗: {e}")
            st.error("導航菜單載入失敗")
    
    def _render_quick_actions(self):
        """渲染快速操作"""
        try:
            st.subheader("⚡ 快速操作")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 刷新狀態", key="refresh_status"):
                    st.session_state.last_update = datetime.now()
                    st.rerun()
                
                if st.button("📊 系統統計", key="system_stats"):
                    st.session_state.current_page = 'dashboard'
                    st.rerun()
            
            with col2:
                if st.button("🔍 搜索知識", key="quick_search"):
                    st.session_state.current_page = 'knowledge_base'
                    st.rerun()
                
                if st.button("⚙️ 設置", key="quick_settings"):
                    st.session_state.current_page = 'system_settings'
                    st.rerun()
            
        except Exception as e:
            logger.error(f"快速操作渲染失敗: {e}")
            st.error("快速操作載入失敗")
    
    def _is_page_available(self, page_key: str) -> bool:
        """檢查頁面是否可用"""
        try:
            # 檢查依賴的適配器是否可用
            page_dependencies = {
                'trading': ['multi_agent'],
                'rl_training': ['reinforcement_learning'],
                'knowledge_base': ['knowledge_system'],
                'learning_center': ['knowledge_system'],
                'data_management': ['data_sources']
            }
            
            if page_key in page_dependencies:
                required_adapters = page_dependencies[page_key]
                for adapter_name in required_adapters:
                    adapter = self.system_integrator.get_adapter(adapter_name)
                    if not adapter or not adapter.initialized:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"頁面可用性檢查失敗 {page_key}: {e}")
            return False
    
    def render_main_content(self):
        """渲染主要內容"""
        try:
            current_page = st.session_state.get('current_page', 'dashboard')
            
            # 頁面標題
            if current_page in self.pages:
                page_info = self.pages[current_page]
                st.title(page_info['title'])
                st.markdown(f"*{page_info['description']}*")
                st.markdown("---")
            
            # 渲染對應頁面
            if current_page == 'dashboard':
                self._render_dashboard()
            elif current_page == 'trading':
                self._render_trading_page()
            elif current_page == 'portfolio':
                self._render_portfolio_page()
            elif current_page == 'data_management':
                self._render_data_management_page()
            elif current_page == 'knowledge_base':
                self._render_knowledge_base_page()
            elif current_page == 'learning_center':
                self._render_learning_center_page()
            elif current_page == 'rl_training':
                self._render_rl_training_page()
            elif current_page == 'system_settings':
                self._render_system_settings_page()
            else:
                st.error(f"未知頁面: {current_page}")
            
        except Exception as e:
            logger.error(f"主要內容渲染失敗: {e}")
            st.error("頁面載入失敗")
    
    def _render_dashboard(self):
        """渲染儀表板"""
        try:
            # 系統概覽
            st.subheader("📊 系統概覽")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("活躍代理", "5", "↑1")
            
            with col2:
                st.metric("數據源", "3", "→0")
            
            with col3:
                st.metric("知識項目", "1,234", "↑56")
            
            with col4:
                st.metric("系統健康度", "95%", "↑2%")
            
            # 最近活動
            st.subheader("📈 最近活動")
            
            # 模擬活動數據
            activity_data = pd.DataFrame({
                '時間': pd.date_range('2024-01-01', periods=10, freq='H'),
                '事件': ['交易決策', '數據更新', '模型訓練', '知識更新', '系統監控'] * 2,
                '狀態': ['成功', '成功', '進行中', '成功', '成功'] * 2
            })
            
            st.dataframe(activity_data, use_container_width=True)
            
        except Exception as e:
            logger.error(f"儀表板渲染失敗: {e}")
            st.error("儀表板載入失敗")
    
    def _render_trading_page(self):
        """渲染交易頁面"""
        try:
            st.subheader("🤖 多代理交易決策")
            
            # 股票選擇
            symbol = st.text_input("股票代碼", value="2330.TW", key="trading_symbol")
            
            if st.button("獲取交易建議", key="get_trading_advice"):
                with st.spinner("正在分析..."):
                    try:
                        # 模擬市場數據
                        market_data = {
                            'symbol': symbol,
                            'price': 500.0,
                            'volume': 1000000,
                            'historical_data': []
                        }
                        
                        # 調用交易決策API
                        result = self.interface_bridge.call_api(
                            'make_trading_decision',
                            symbol,
                            market_data
                        )
                        
                        if result['success']:
                            decision = result['data']
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("建議動作", decision.get('action', 'hold'))
                            
                            with col2:
                                st.metric("信心度", f"{decision.get('confidence', 0):.2%}")
                            
                            with col3:
                                st.metric("建議數量", decision.get('quantity', 0))
                            
                            st.info(f"決策理由: {decision.get('reasoning', '無')}")
                        else:
                            st.error(f"決策失敗: {result['error']['message']}")
                            
                    except Exception as e:
                        st.error(f"交易決策失敗: {e}")
            
        except Exception as e:
            logger.error(f"交易頁面渲染失敗: {e}")
            st.error("交易頁面載入失敗")
    
    def _render_portfolio_page(self):
        """渲染投資組合頁面"""
        try:
            st.subheader("💼 投資組合狀態")
            
            # 獲取投資組合狀態
            try:
                result = self.interface_bridge.call_api('get_portfolio_status')
                
                if result['success']:
                    portfolio = result['data']
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("總價值", f"${portfolio.get('total_value', 0):,.2f}")
                    
                    with col2:
                        st.metric("現金", f"${portfolio.get('cash', 0):,.2f}")
                    
                    with col3:
                        st.metric("持倉數量", len(portfolio.get('positions', {})))
                    
                    # 持倉詳情
                    st.subheader("📊 持倉詳情")
                    positions = portfolio.get('positions', {})
                    
                    if positions:
                        positions_df = pd.DataFrame.from_dict(positions, orient='index')
                        st.dataframe(positions_df, use_container_width=True)
                    else:
                        st.info("目前無持倉")
                        
                else:
                    st.error(f"獲取投資組合失敗: {result['error']['message']}")
                    
            except Exception as e:
                st.error(f"投資組合載入失敗: {e}")
            
        except Exception as e:
            logger.error(f"投資組合頁面渲染失敗: {e}")
            st.error("投資組合頁面載入失敗")
    
    def _render_data_management_page(self):
        """渲染數據管理頁面"""
        try:
            st.subheader("📊 數據源管理")
            
            # 獲取數據源狀態
            data_adapter = self.system_integrator.get_adapter('data_sources')
            if data_adapter:
                status = data_adapter.get_data_source_status()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("活躍數據源", status.get('active_sources', 0))
                
                with col2:
                    st.metric("健康監控", "啟用" if status.get('health_monitor_active') else "停用")
                
                with col3:
                    st.metric("緩存狀態", "啟用" if status.get('cache_enabled') else "停用")
                
                # 數據源詳情
                st.subheader("📈 數據源狀態")
                sources = status.get('sources', {})
                
                for source_name, source_info in sources.items():
                    with st.expander(f"📊 {source_name}"):
                        if 'error' in source_info:
                            st.error(f"錯誤: {source_info['error']}")
                        else:
                            st.success("狀態: 正常")
                            st.info(f"類型: {source_info.get('type', '未知')}")
                            st.info(f"最後檢查: {source_info.get('last_check', '未知')}")
            else:
                st.warning("數據源適配器不可用")
            
        except Exception as e:
            logger.error(f"數據管理頁面渲染失敗: {e}")
            st.error("數據管理頁面載入失敗")
    
    def _render_knowledge_base_page(self):
        """渲染知識庫頁面"""
        try:
            st.subheader("🔍 知識搜索")
            
            # 搜索界面
            query = st.text_input("搜索知識", placeholder="輸入關鍵詞...", key="knowledge_search")
            
            if st.button("搜索", key="search_knowledge") and query:
                with st.spinner("搜索中..."):
                    try:
                        result = self.interface_bridge.call_api('search_knowledge', query, 10)
                        
                        if result['success']:
                            results = result['data']
                            
                            if results:
                                st.success(f"找到 {len(results)} 個結果")
                                
                                for i, item in enumerate(results, 1):
                                    with st.expander(f"{i}. {item.get('title', '無標題')}"):
                                        st.markdown(item.get('content', '無內容'))
                                        
                                        col1, col2, col3 = st.columns(3)
                                        with col1:
                                            st.info(f"類別: {item.get('category', '未分類')}")
                                        with col2:
                                            st.info(f"難度: {item.get('difficulty_level', 1)}")
                                        with col3:
                                            st.info(f"閱讀時間: {item.get('estimated_reading_time', 0)}分鐘")
                            else:
                                st.info("未找到相關結果")
                        else:
                            st.error(f"搜索失敗: {result['error']['message']}")
                            
                    except Exception as e:
                        st.error(f"搜索失敗: {e}")
            
        except Exception as e:
            logger.error(f"知識庫頁面渲染失敗: {e}")
            st.error("知識庫頁面載入失敗")
    
    def _render_learning_center_page(self):
        """渲染學習中心頁面"""
        try:
            st.subheader("🎓 學習進度")
            
            user_id = st.session_state.get('user_id', 'default_user')
            
            try:
                result = self.interface_bridge.call_api('get_learning_progress', user_id)
                
                if result['success']:
                    progress = result['data']
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("總項目", progress.get('total_items', 0))
                    
                    with col2:
                        st.metric("已完成", progress.get('completed_items', 0))
                    
                    with col3:
                        completion_rate = progress.get('completion_rate', 0)
                        st.metric("完成率", f"{completion_rate:.1%}")
                    
                    # 最近活動
                    st.subheader("📚 最近學習")
                    recent_activity = progress.get('recent_activity', [])
                    
                    if recent_activity:
                        for activity in recent_activity:
                            progress_val = activity.get('progress', 0)
                            st.progress(progress_val, text=f"項目 {activity.get('item_id', '未知')}: {progress_val:.1%}")
                    else:
                        st.info("暫無學習記錄")
                        
                else:
                    st.error(f"獲取學習進度失敗: {result['error']['message']}")
                    
            except Exception as e:
                st.error(f"學習進度載入失敗: {e}")
            
        except Exception as e:
            logger.error(f"學習中心頁面渲染失敗: {e}")
            st.error("學習中心頁面載入失敗")
    
    def _render_rl_training_page(self):
        """渲染強化學習訓練頁面"""
        try:
            st.subheader("🤖 強化學習訓練")
            
            rl_adapter = self.system_integrator.get_adapter('reinforcement_learning')
            if rl_adapter:
                status = rl_adapter.get_rl_status()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("RL環境", status.get('environments', 0))
                
                with col2:
                    st.metric("RL代理", status.get('agents', 0))
                
                with col3:
                    st.metric("訓練器", status.get('trainers', 0))
                
                # 代理詳情
                st.subheader("🧠 代理狀態")
                agent_details = status.get('agent_details', {})
                
                for agent_name, agent_info in agent_details.items():
                    with st.expander(f"🤖 {agent_name}"):
                        if 'error' in agent_info:
                            st.error(f"錯誤: {agent_info['error']}")
                        else:
                            st.success("狀態: 正常")
                            # 這裡可以添加更多代理信息
                
                # 訓練控制
                st.subheader("🎯 訓練控制")
                
                if st.button("開始訓練", key="start_rl_training"):
                    st.info("訓練功能開發中...")
                    
            else:
                st.warning("強化學習適配器不可用")
            
        except Exception as e:
            logger.error(f"強化學習頁面渲染失敗: {e}")
            st.error("強化學習頁面載入失敗")
    
    def _render_system_settings_page(self):
        """渲染系統設置頁面"""
        try:
            st.subheader("⚙️ 系統配置")
            
            # 功能開關
            st.subheader("🔧 功能開關")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.session_state.agents_enabled = st.checkbox(
                    "多代理系統",
                    value=st.session_state.get('agents_enabled', True),
                    key="toggle_agents"
                )
                
                st.session_state.rl_enabled = st.checkbox(
                    "強化學習",
                    value=st.session_state.get('rl_enabled', True),
                    key="toggle_rl"
                )
            
            with col2:
                st.session_state.knowledge_enabled = st.checkbox(
                    "知識庫系統",
                    value=st.session_state.get('knowledge_enabled', True),
                    key="toggle_knowledge"
                )
                
                st.session_state.data_sources_enabled = st.checkbox(
                    "數據源擴展",
                    value=st.session_state.get('data_sources_enabled', True),
                    key="toggle_data_sources"
                )
            
            # 系統信息
            st.subheader("ℹ️ 系統信息")
            
            if self.interface_bridge:
                api_info = self.interface_bridge.get_api_info()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"API版本: {api_info.get('api_version', '未知')}")
                    st.info(f"原始項目版本: {api_info.get('legacy_version', '未知')}")
                
                with col2:
                    st.info(f"可用API: {len(api_info.get('available_apis', []))}")
                    st.info(f"橋樑狀態: {api_info.get('bridge_status', '未知')}")
            
        except Exception as e:
            logger.error(f"系統設置頁面渲染失敗: {e}")
            st.error("系統設置頁面載入失敗")
    
    def run(self):
        """運行Streamlit應用"""
        try:
            # 設置頁面配置
            st.set_page_config(
                page_title="AI量化交易系統",
                page_icon="🚀",
                layout="wide",
                initial_sidebar_state="expanded"
            )
            
            # 渲染側邊欄
            self.render_sidebar()
            
            # 渲染主要內容
            self.render_main_content()
            
        except Exception as e:
            logger.error(f"Streamlit應用運行失敗: {e}")
            st.error("應用載入失敗")
