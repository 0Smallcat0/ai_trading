# -*- coding: utf-8 -*-
"""
學習進度追蹤儀表板

此模組提供新手友好的學習進度追蹤功能，包括：
- 學習路徑規劃
- 進度可視化
- 成就系統
- 學習建議
- 個人化儀表板

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
from plotly.subplots import make_subplots

# 導入現有組件
from ..components.common import UIComponents
from ..responsive import ResponsiveUtils

logger = logging.getLogger(__name__)


class ProgressDashboard:
    """
    學習進度追蹤儀表板
    
    提供新手友好的學習進度追蹤和管理功能，包括學習路徑規劃、
    進度可視化、成就系統和個人化建議。
    
    Attributes:
        learning_path (Dict): 學習路徑配置
        user_progress (Dict): 用戶學習進度
        achievements (List): 成就清單
        learning_analytics (Dict): 學習分析資料
        
    Example:
        >>> dashboard = ProgressDashboard()
        >>> dashboard.update_progress('basic_concepts', 80)
        >>> dashboard.get_next_recommendations()
    """
    
    def __init__(self):
        """初始化學習進度追蹤儀表板"""
        self.learning_path = self._initialize_learning_path()
        self.user_progress = self._initialize_user_progress()
        self.achievements = self._initialize_achievements()
        self.learning_analytics = {}
        
    def _initialize_learning_path(self) -> Dict[str, Any]:
        """
        初始化學習路徑
        
        Returns:
            Dict[str, Any]: 學習路徑配置
        """
        return {
            'beginner': {
                'name': '新手入門',
                'description': '量化交易基礎知識和系統操作',
                'estimated_hours': 20,
                'modules': [
                    {
                        'id': 'basic_concepts',
                        'name': '基礎概念',
                        'description': '量化交易基本概念和術語',
                        'estimated_hours': 3,
                        'topics': [
                            '什麼是量化交易',
                            '技術分析基礎',
                            '風險管理概念',
                            '交易策略類型'
                        ]
                    },
                    {
                        'id': 'system_operation',
                        'name': '系統操作',
                        'description': '學習使用 AI 交易系統',
                        'estimated_hours': 4,
                        'topics': [
                            '系統安裝配置',
                            '資料管理操作',
                            '策略創建流程',
                            '回測系統使用'
                        ]
                    },
                    {
                        'id': 'strategy_basics',
                        'name': '策略基礎',
                        'description': '基本交易策略學習',
                        'estimated_hours': 6,
                        'topics': [
                            '移動平均線策略',
                            'RSI 策略',
                            '動量策略',
                            '策略參數調整'
                        ]
                    },
                    {
                        'id': 'risk_management',
                        'name': '風險管理',
                        'description': '風險控制和資金管理',
                        'estimated_hours': 4,
                        'topics': [
                            '停損設定',
                            '部位大小控制',
                            '風險指標理解',
                            '資金管理策略'
                        ]
                    },
                    {
                        'id': 'practice_trading',
                        'name': '模擬交易',
                        'description': '虛擬環境交易練習',
                        'estimated_hours': 3,
                        'topics': [
                            '模擬交易操作',
                            '績效分析',
                            '交易記錄管理',
                            '技能評估'
                        ]
                    }
                ]
            },
            'intermediate': {
                'name': '進階學習',
                'description': '深入策略開發和優化',
                'estimated_hours': 30,
                'modules': [
                    {
                        'id': 'advanced_strategies',
                        'name': '進階策略',
                        'description': '複雜交易策略學習',
                        'estimated_hours': 8,
                        'topics': [
                            '多因子策略',
                            '配對交易',
                            '統計套利',
                            '機器學習策略'
                        ]
                    },
                    {
                        'id': 'backtesting_optimization',
                        'name': '回測優化',
                        'description': '策略回測和參數優化',
                        'estimated_hours': 6,
                        'topics': [
                            '回測框架設計',
                            '參數優化方法',
                            '過擬合避免',
                            '績效評估指標'
                        ]
                    },
                    {
                        'id': 'portfolio_management',
                        'name': '投資組合管理',
                        'description': '多策略組合管理',
                        'estimated_hours': 8,
                        'topics': [
                            '資產配置',
                            '組合優化',
                            '相關性分析',
                            '再平衡策略'
                        ]
                    },
                    {
                        'id': 'live_trading',
                        'name': '實盤交易',
                        'description': '實際交易執行',
                        'estimated_hours': 8,
                        'topics': [
                            '券商 API 整合',
                            '實時交易執行',
                            '監控和警報',
                            '交易記錄分析'
                        ]
                    }
                ]
            }
        }
    
    def _initialize_user_progress(self) -> Dict[str, Any]:
        """
        初始化用戶進度
        
        Returns:
            Dict[str, Any]: 用戶進度資料
        """
        return {
            'current_level': 'beginner',
            'total_hours_spent': 0,
            'modules_completed': [],
            'module_progress': {},
            'last_activity': None,
            'learning_streak': 0,
            'total_achievements': 0
        }
    
    def _initialize_achievements(self) -> List[Dict[str, Any]]:
        """
        初始化成就系統
        
        Returns:
            List[Dict[str, Any]]: 成就清單
        """
        return [
            {
                'id': 'first_login',
                'name': '初次登入',
                'description': '完成系統首次登入',
                'icon': '🎯',
                'points': 10,
                'unlocked': False
            },
            {
                'id': 'setup_complete',
                'name': '系統設定完成',
                'description': '完成系統安裝和配置',
                'icon': '⚙️',
                'points': 50,
                'unlocked': False
            },
            {
                'id': 'first_strategy',
                'name': '策略新手',
                'description': '創建第一個交易策略',
                'icon': '🎯',
                'points': 100,
                'unlocked': False
            },
            {
                'id': 'first_backtest',
                'name': '回測達人',
                'description': '完成第一次策略回測',
                'icon': '📊',
                'points': 100,
                'unlocked': False
            },
            {
                'id': 'risk_master',
                'name': '風險管理專家',
                'description': '完成風險管理模組學習',
                'icon': '🛡️',
                'points': 150,
                'unlocked': False
            },
            {
                'id': 'practice_trader',
                'name': '模擬交易者',
                'description': '完成 10 筆模擬交易',
                'icon': '💹',
                'points': 200,
                'unlocked': False
            },
            {
                'id': 'learning_streak_7',
                'name': '學習達人',
                'description': '連續學習 7 天',
                'icon': '🔥',
                'points': 300,
                'unlocked': False
            },
            {
                'id': 'beginner_graduate',
                'name': '新手畢業',
                'description': '完成新手入門所有模組',
                'icon': '🎓',
                'points': 500,
                'unlocked': False
            }
        ]
    
    def update_progress(self, module_id: str, progress_percentage: float) -> None:
        """
        更新學習進度
        
        Args:
            module_id: 模組ID
            progress_percentage: 進度百分比 (0-100)
        """
        self.user_progress['module_progress'][module_id] = progress_percentage
        self.user_progress['last_activity'] = datetime.now().isoformat()
        
        # 檢查模組是否完成
        if progress_percentage >= 100 and module_id not in self.user_progress['modules_completed']:
            self.user_progress['modules_completed'].append(module_id)
            self._check_achievements(module_id)
        
        logger.info("學習進度已更新: %s - %s%%", module_id, progress_percentage)
    
    def _check_achievements(self, completed_module: str) -> None:
        """
        檢查成就解鎖
        
        Args:
            completed_module: 完成的模組ID
        """
        # 檢查特定模組成就
        if completed_module == 'risk_management':
            self._unlock_achievement('risk_master')
        
        # 檢查新手畢業成就
        beginner_modules = [m['id'] for m in self.learning_path['beginner']['modules']]
        if all(m in self.user_progress['modules_completed'] for m in beginner_modules):
            self._unlock_achievement('beginner_graduate')
    
    def _unlock_achievement(self, achievement_id: str) -> None:
        """
        解鎖成就
        
        Args:
            achievement_id: 成就ID
        """
        for achievement in self.achievements:
            if achievement['id'] == achievement_id and not achievement['unlocked']:
                achievement['unlocked'] = True
                self.user_progress['total_achievements'] += 1
                logger.info("成就解鎖: %s", achievement['name'])
                break
    
    def get_overall_progress(self) -> float:
        """
        獲取總體學習進度
        
        Returns:
            float: 總體進度百分比 (0-100)
        """
        current_level = self.user_progress['current_level']
        level_modules = self.learning_path[current_level]['modules']
        
        if not level_modules:
            return 0.0
        
        total_progress = 0.0
        for module in level_modules:
            module_id = module['id']
            progress = self.user_progress['module_progress'].get(module_id, 0)
            total_progress += progress
        
        return total_progress / len(level_modules)
    
    def get_next_recommendations(self) -> List[Dict[str, Any]]:
        """
        獲取下一步學習建議
        
        Returns:
            List[Dict[str, Any]]: 學習建議清單
        """
        recommendations = []
        current_level = self.user_progress['current_level']
        level_modules = self.learning_path[current_level]['modules']
        
        for module in level_modules:
            module_id = module['id']
            progress = self.user_progress['module_progress'].get(module_id, 0)
            
            if progress < 100:
                recommendations.append({
                    'type': 'continue_module',
                    'module': module,
                    'progress': progress,
                    'priority': 'high' if progress > 0 else 'medium'
                })
                break  # 只推薦下一個未完成的模組
        
        # 如果當前級別完成，推薦下一級別
        if self.get_overall_progress() >= 100:
            if current_level == 'beginner':
                recommendations.append({
                    'type': 'level_up',
                    'next_level': 'intermediate',
                    'priority': 'high'
                })
        
        return recommendations
    
    def get_learning_analytics(self) -> Dict[str, Any]:
        """
        獲取學習分析資料
        
        Returns:
            Dict[str, Any]: 學習分析資料
        """
        current_level = self.user_progress['current_level']
        level_modules = self.learning_path[current_level]['modules']
        
        # 計算各模組進度
        module_progress = []
        for module in level_modules:
            module_id = module['id']
            progress = self.user_progress['module_progress'].get(module_id, 0)
            module_progress.append({
                'module': module['name'],
                'progress': progress,
                'estimated_hours': module['estimated_hours']
            })
        
        # 計算學習統計
        total_modules = len(level_modules)
        completed_modules = len(self.user_progress['modules_completed'])
        
        analytics = {
            'overall_progress': self.get_overall_progress(),
            'module_progress': module_progress,
            'completion_stats': {
                'total_modules': total_modules,
                'completed_modules': completed_modules,
                'remaining_modules': total_modules - completed_modules
            },
            'time_stats': {
                'total_hours_spent': self.user_progress['total_hours_spent'],
                'estimated_remaining_hours': self._calculate_remaining_hours()
            },
            'achievement_stats': {
                'total_achievements': len(self.achievements),
                'unlocked_achievements': self.user_progress['total_achievements'],
                'achievement_rate': self.user_progress['total_achievements'] / len(self.achievements) * 100
            }
        }
        
        return analytics
    
    def _calculate_remaining_hours(self) -> float:
        """
        計算剩餘學習時間
        
        Returns:
            float: 剩餘學習小時數
        """
        current_level = self.user_progress['current_level']
        level_modules = self.learning_path[current_level]['modules']
        
        remaining_hours = 0.0
        for module in level_modules:
            module_id = module['id']
            progress = self.user_progress['module_progress'].get(module_id, 0)
            remaining_progress = (100 - progress) / 100
            remaining_hours += module['estimated_hours'] * remaining_progress
        
        return remaining_hours


def show_progress_dashboard() -> None:
    """
    顯示學習進度追蹤儀表板頁面
    
    提供新手友好的學習進度追蹤和管理功能，包括學習路徑規劃、
    進度可視化、成就系統和個人化建議。
    
    Side Effects:
        - 在 Streamlit 界面顯示學習進度儀表板
        - 追蹤和更新用戶學習進度
    """
    st.title("📊 學習進度儀表板")
    st.markdown("追蹤您的量化交易學習進度，獲得個人化學習建議！")
    
    # 初始化進度儀表板
    if 'progress_dashboard' not in st.session_state:
        st.session_state.progress_dashboard = ProgressDashboard()
    
    dashboard = st.session_state.progress_dashboard
    
    # 獲取學習分析資料
    analytics = dashboard.get_learning_analytics()
    
    # 總體進度概覽
    st.subheader("🎯 學習概覽")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "總體進度", 
            f"{analytics['overall_progress']:.1f}%",
            delta=f"+{analytics['overall_progress']:.1f}%" if analytics['overall_progress'] > 0 else None
        )
    
    with col2:
        st.metric(
            "已完成模組", 
            f"{analytics['completion_stats']['completed_modules']}/{analytics['completion_stats']['total_modules']}"
        )
    
    with col3:
        st.metric(
            "學習時數", 
            f"{analytics['time_stats']['total_hours_spent']:.1f}h"
        )
    
    with col4:
        st.metric(
            "獲得成就", 
            f"{analytics['achievement_stats']['unlocked_achievements']}/{analytics['achievement_stats']['total_achievements']}"
        )
    
    # 進度條
    progress_bar = st.progress(analytics['overall_progress'] / 100)
    
    # 主要內容區域
    tab1, tab2, tab3, tab4 = st.tabs(["學習路徑", "模組進度", "成就系統", "學習建議"])
    
    with tab1:
        st.subheader("🗺️ 學習路徑")
        
        current_level = dashboard.user_progress['current_level']
        level_info = dashboard.learning_path[current_level]
        
        st.write(f"**當前級別：{level_info['name']}**")
        st.write(level_info['description'])
        st.write(f"預計學習時間：{level_info['estimated_hours']} 小時")
        
        # 模組清單
        for i, module in enumerate(level_info['modules']):
            module_id = module['id']
            progress = dashboard.user_progress['module_progress'].get(module_id, 0)
            
            with st.expander(f"{i+1}. {module['name']} ({progress:.0f}% 完成)"):
                st.write(module['description'])
                st.write(f"預計時間：{module['estimated_hours']} 小時")
                
                st.write("**學習主題：**")
                for topic in module['topics']:
                    st.write(f"• {topic}")
                
                # 進度更新
                new_progress = st.slider(
                    f"更新 {module['name']} 進度",
                    min_value=0,
                    max_value=100,
                    value=int(progress),
                    key=f"progress_{module_id}"
                )
                
                if st.button(f"保存進度", key=f"save_{module_id}"):
                    dashboard.update_progress(module_id, new_progress)
                    st.success("進度已更新！")
                    st.rerun()
    
    with tab2:
        st.subheader("📈 模組進度詳情")
        
        # 進度圖表
        module_data = analytics['module_progress']
        
        if module_data:
            df = pd.DataFrame(module_data)
            
            # 進度條圖
            fig = px.bar(
                df, 
                x='module', 
                y='progress',
                title='各模組學習進度',
                color='progress',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # 時間分配圖
            fig2 = px.pie(
                df, 
                values='estimated_hours', 
                names='module',
                title='學習時間分配'
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # 詳細進度表
        st.subheader("📋 詳細進度")
        
        if module_data:
            progress_df = pd.DataFrame(module_data)
            progress_df['狀態'] = progress_df['progress'].apply(
                lambda x: '✅ 已完成' if x >= 100 else 
                         '🔄 進行中' if x > 0 else '⏳ 未開始'
            )
            
            st.dataframe(
                progress_df[['module', 'progress', '狀態', 'estimated_hours']].rename(columns={
                    'module': '模組名稱',
                    'progress': '進度 (%)',
                    'estimated_hours': '預計時間 (小時)'
                }),
                use_container_width=True
            )
    
    with tab3:
        st.subheader("🏆 成就系統")
        
        # 成就統計
        achievement_stats = analytics['achievement_stats']
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("成就完成率", f"{achievement_stats['achievement_rate']:.1f}%")
        with col2:
            st.metric("總積分", sum(a['points'] for a in dashboard.achievements if a['unlocked']))
        
        # 成就清單
        st.write("**成就清單：**")
        
        for achievement in dashboard.achievements:
            if achievement['unlocked']:
                st.success(
                    f"{achievement['icon']} **{achievement['name']}** - {achievement['points']} 積分\n\n"
                    f"{achievement['description']}"
                )
            else:
                st.info(
                    f"{achievement['icon']} **{achievement['name']}** - {achievement['points']} 積分\n\n"
                    f"{achievement['description']} (未解鎖)"
                )
        
        # 手動解鎖成就（用於測試）
        st.subheader("🎮 測試成就解鎖")
        
        locked_achievements = [a for a in dashboard.achievements if not a['unlocked']]
        if locked_achievements:
            selected_achievement = st.selectbox(
                "選擇要解鎖的成就",
                locked_achievements,
                format_func=lambda x: x['name']
            )
            
            if st.button("解鎖成就"):
                dashboard._unlock_achievement(selected_achievement['id'])
                st.success(f"🎉 成就已解鎖：{selected_achievement['name']}")
                st.rerun()
    
    with tab4:
        st.subheader("💡 學習建議")
        
        recommendations = dashboard.get_next_recommendations()
        
        if recommendations:
            for rec in recommendations:
                if rec['type'] == 'continue_module':
                    module = rec['module']
                    progress = rec['progress']
                    
                    if progress == 0:
                        st.info(
                            f"🎯 **開始學習：{module['name']}**\n\n"
                            f"{module['description']}\n\n"
                            f"預計時間：{module['estimated_hours']} 小時"
                        )
                    else:
                        st.warning(
                            f"🔄 **繼續學習：{module['name']}**\n\n"
                            f"當前進度：{progress:.1f}%\n\n"
                            f"預計剩餘時間：{module['estimated_hours'] * (100-progress)/100:.1f} 小時"
                        )
                
                elif rec['type'] == 'level_up':
                    st.success(
                        f"🎓 **恭喜！準備升級到：{rec['next_level']}**\n\n"
                        f"您已完成當前級別的所有模組，可以開始進階學習了！"
                    )
        else:
            st.info("暫無學習建議，請繼續當前的學習進度。")
        
        # 學習提醒
        st.subheader("⏰ 學習提醒")
        
        remaining_hours = analytics['time_stats']['estimated_remaining_hours']
        if remaining_hours > 0:
            st.write(f"📚 預計還需要 {remaining_hours:.1f} 小時完成當前級別")
            
            # 學習計劃建議
            daily_hours = st.slider("每日學習時間 (小時)", 0.5, 4.0, 1.0, 0.5)
            estimated_days = remaining_hours / daily_hours
            
            st.write(f"⏱️ 按每日 {daily_hours} 小時的學習進度，預計 {estimated_days:.0f} 天完成")
            
            completion_date = datetime.now() + timedelta(days=estimated_days)
            st.write(f"🎯 預計完成日期：{completion_date.strftime('%Y-%m-%d')}")
        else:
            st.success("🎉 恭喜！您已完成當前級別的所有學習內容！")
    
    # 側邊欄：快速操作
    with st.sidebar:
        st.subheader("⚡ 快速操作")
        
        if st.button("🔄 刷新進度"):
            st.rerun()
        
        if st.button("📊 生成學習報告"):
            st.info("學習報告功能開發中...")
        
        if st.button("🎯 設定學習目標"):
            st.info("學習目標設定功能開發中...")
        
        # 學習統計
        st.subheader("📈 學習統計")
        
        st.write(f"**當前級別：** {dashboard.user_progress['current_level']}")
        st.write(f"**學習連續天數：** {dashboard.user_progress['learning_streak']}")
        st.write(f"**最後活動：** {dashboard.user_progress.get('last_activity', '無')}")
