"""
用戶偏好設置界面組件

提供完整的用戶偏好設置界面，包括：
- 主題設置面板
- 語言偏好設置
- 交易默認參數
- 通知設置
- 個人化配置
"""

import streamlit as st
import json
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from ..utils.user_preferences_manager import (
    preferences_manager,
    UserPreferences,
    ThemeType,
    LanguageType,
    get_current_user_preferences,
    update_current_preference,
    get_current_preference,
    apply_theme_to_streamlit
)

logger = logging.getLogger(__name__)


def user_preferences_panel():
    """用戶偏好設置主面板"""
    st.subheader("⚙️ 個人偏好設置")
    
    # 檢查是否有當前用戶
    current_user = st.session_state.get("username", "demo_user")
    preferences = get_current_user_preferences()
    
    if not preferences:
        # 初始化偏好設置
        preferences = preferences_manager.load_preferences(current_user, current_user)
        st.session_state.user_preferences = preferences
    
    # 標籤頁
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🎨 界面設置", "🌐 語言設置", "💰 交易設置", 
        "🔔 通知設置", "📊 圖表設置", "🔧 高級設置"
    ])
    
    with tab1:
        show_interface_settings(preferences)
    
    with tab2:
        show_language_settings(preferences)
    
    with tab3:
        show_trading_settings(preferences)
    
    with tab4:
        show_notification_settings(preferences)
    
    with tab5:
        show_chart_settings(preferences)
    
    with tab6:
        show_advanced_settings(preferences)
    
    # 操作按鈕
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("💾 保存設置", type="primary"):
            if preferences_manager.save_preferences(preferences):
                st.success("✅ 設置已保存")
                st.rerun()
            else:
                st.error("❌ 保存失敗")
    
    with col2:
        if st.button("🔄 重置為默認"):
            if preferences_manager.reset_preferences(preferences.user_id, preferences.username):
                st.success("✅ 已重置為默認設置")
                st.rerun()
            else:
                st.error("❌ 重置失敗")
    
    with col3:
        if st.button("📤 導出設置"):
            export_data = preferences_manager.export_preferences(preferences.user_id)
            if export_data:
                st.download_button(
                    label="下載設置文件",
                    data=json.dumps(export_data, ensure_ascii=False, indent=2),
                    file_name=f"preferences_{preferences.user_id}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
    
    with col4:
        uploaded_file = st.file_uploader("📥 導入設置", type=["json"], key="import_prefs")
        if uploaded_file:
            try:
                import_data = json.load(uploaded_file)
                if preferences_manager.import_preferences(preferences.user_id, import_data):
                    st.success("✅ 設置已導入")
                    st.rerun()
                else:
                    st.error("❌ 導入失敗")
            except Exception as e:
                st.error(f"❌ 文件格式錯誤: {e}")


def show_interface_settings(preferences: UserPreferences):
    """顯示界面設置"""
    st.markdown("### 🎨 界面外觀")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 主題設置
        theme_options = {
            ThemeType.LIGHT.value: "☀️ 淺色主題",
            ThemeType.DARK.value: "🌙 深色主題",
            ThemeType.AUTO.value: "🔄 自動切換"
        }
        
        new_theme = st.selectbox(
            "主題",
            options=list(theme_options.keys()),
            index=list(theme_options.keys()).index(preferences.theme),
            format_func=lambda x: theme_options[x]
        )
        
        if new_theme != preferences.theme:
            preferences.theme = new_theme
            # 立即應用主題
            theme_config = preferences_manager.get_theme_config(new_theme)
            apply_theme_to_streamlit(theme_config)
        
        # 字體大小
        preferences.font_size = st.slider(
            "字體大小",
            min_value=0.8,
            max_value=2.0,
            value=preferences.font_size,
            step=0.1,
            help="調整整體字體大小"
        )
    
    with col2:
        # 側邊欄設置
        preferences.sidebar_collapsed = st.checkbox(
            "默認收起側邊欄",
            value=preferences.sidebar_collapsed
        )
        
        # 動畫效果
        preferences.enable_animations = st.checkbox(
            "啟用動畫效果",
            value=preferences.enable_animations
        )
        
        # 聲音效果
        preferences.enable_sound = st.checkbox(
            "啟用聲音效果",
            value=preferences.enable_sound
        )
    
    # 自動刷新設置
    st.markdown("### 🔄 自動刷新")
    
    col1, col2 = st.columns(2)
    
    with col1:
        preferences.auto_refresh = st.checkbox(
            "啟用自動刷新",
            value=preferences.auto_refresh
        )
    
    with col2:
        if preferences.auto_refresh:
            preferences.refresh_interval = st.slider(
                "刷新間隔（秒）",
                min_value=5,
                max_value=300,
                value=preferences.refresh_interval,
                step=5
            )


def show_language_settings(preferences: UserPreferences):
    """顯示語言設置"""
    st.markdown("### 🌐 語言偏好")
    
    language_options = {
        LanguageType.ZH_TW.value: "🇹🇼 繁體中文",
        LanguageType.ZH_CN.value: "🇨🇳 簡體中文",
        LanguageType.EN_US.value: "🇺🇸 English",
        LanguageType.JA_JP.value: "🇯🇵 日本語"
    }
    
    preferences.language = st.selectbox(
        "界面語言",
        options=list(language_options.keys()),
        index=list(language_options.keys()).index(preferences.language),
        format_func=lambda x: language_options[x]
    )
    
    st.info("💡 語言更改將在下次重新加載頁面時生效")


def show_trading_settings(preferences: UserPreferences):
    """顯示交易設置"""
    st.markdown("### 💰 交易默認參數")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 默認訂單類型
        order_type_options = {
            "market": "市價單",
            "limit": "限價單",
            "stop": "停損單",
            "stop_limit": "停損限價單"
        }
        
        preferences.default_order_type = st.selectbox(
            "默認訂單類型",
            options=list(order_type_options.keys()),
            index=list(order_type_options.keys()).index(preferences.default_order_type),
            format_func=lambda x: order_type_options[x]
        )
        
        # 默認數量
        preferences.default_quantity = st.number_input(
            "默認交易數量",
            min_value=1,
            max_value=10000,
            value=preferences.default_quantity,
            step=100
        )
    
    with col2:
        # 風險承受度
        risk_options = {
            "low": "🟢 保守型",
            "medium": "🟡 穩健型",
            "high": "🔴 積極型"
        }
        
        preferences.risk_tolerance = st.selectbox(
            "風險承受度",
            options=list(risk_options.keys()),
            index=list(risk_options.keys()).index(preferences.risk_tolerance),
            format_func=lambda x: risk_options[x]
        )
        
        # 自動停損
        preferences.auto_stop_loss = st.checkbox(
            "啟用自動停損",
            value=preferences.auto_stop_loss
        )
        
        if preferences.auto_stop_loss:
            preferences.stop_loss_percentage = st.slider(
                "停損百分比",
                min_value=0.01,
                max_value=0.20,
                value=preferences.stop_loss_percentage,
                step=0.01,
                format="%.2f%%"
            ) / 100


def show_notification_settings(preferences: UserPreferences):
    """顯示通知設置"""
    st.markdown("### 🔔 通知偏好")
    
    # 基本通知設置
    preferences.enable_notifications = st.checkbox(
        "啟用通知",
        value=preferences.enable_notifications
    )
    
    if preferences.enable_notifications:
        # 通知類型
        st.markdown("#### 通知類型")
        col1, col2 = st.columns(2)
        
        with col1:
            preferences.notification_types["trading"] = st.checkbox(
                "💰 交易通知",
                value=preferences.notification_types.get("trading", True)
            )
            
            preferences.notification_types["risk"] = st.checkbox(
                "⚠️ 風險警報",
                value=preferences.notification_types.get("risk", True)
            )
        
        with col2:
            preferences.notification_types["system"] = st.checkbox(
                "🔧 系統通知",
                value=preferences.notification_types.get("system", True)
            )
            
            preferences.notification_types["news"] = st.checkbox(
                "📰 新聞通知",
                value=preferences.notification_types.get("news", False)
            )
        
        # 靜音時間
        st.markdown("#### 靜音時間")
        col1, col2 = st.columns(2)
        
        with col1:
            preferences.quiet_hours_start = st.time_input(
                "開始時間",
                value=datetime.strptime(preferences.quiet_hours_start, "%H:%M").time()
            ).strftime("%H:%M")
        
        with col2:
            preferences.quiet_hours_end = st.time_input(
                "結束時間",
                value=datetime.strptime(preferences.quiet_hours_end, "%H:%M").time()
            ).strftime("%H:%M")


def show_chart_settings(preferences: UserPreferences):
    """顯示圖表設置"""
    st.markdown("### 📊 圖表偏好")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 圖表主題
        chart_theme_options = {
            "plotly_white": "白色主題",
            "plotly_dark": "深色主題",
            "ggplot2": "ggplot2 風格",
            "seaborn": "seaborn 風格"
        }
        
        preferences.chart_theme = st.selectbox(
            "圖表主題",
            options=list(chart_theme_options.keys()),
            index=list(chart_theme_options.keys()).index(preferences.chart_theme),
            format_func=lambda x: chart_theme_options[x]
        )
        
        # 圖表高度
        preferences.chart_height = st.slider(
            "圖表高度",
            min_value=300,
            max_value=800,
            value=preferences.chart_height,
            step=50
        )
    
    with col2:
        # 顯示選項
        preferences.show_volume = st.checkbox(
            "顯示成交量",
            value=preferences.show_volume
        )
        
        preferences.show_indicators = st.checkbox(
            "顯示技術指標",
            value=preferences.show_indicators
        )
        
        # 默認時間框架
        timeframe_options = {
            "1m": "1分鐘",
            "5m": "5分鐘",
            "15m": "15分鐘",
            "1h": "1小時",
            "1d": "1天",
            "1w": "1週"
        }
        
        preferences.default_timeframe = st.selectbox(
            "默認時間框架",
            options=list(timeframe_options.keys()),
            index=list(timeframe_options.keys()).index(preferences.default_timeframe),
            format_func=lambda x: timeframe_options[x]
        )


def show_advanced_settings(preferences: UserPreferences):
    """顯示高級設置"""
    st.markdown("### 🔧 高級選項")
    
    col1, col2 = st.columns(2)
    
    with col1:
        preferences.debug_mode = st.checkbox(
            "調試模式",
            value=preferences.debug_mode,
            help="啟用詳細的調試信息"
        )
        
        preferences.performance_mode = st.checkbox(
            "性能模式",
            value=preferences.performance_mode,
            help="優化性能，可能會減少某些功能"
        )
    
    with col2:
        preferences.experimental_features = st.checkbox(
            "實驗性功能",
            value=preferences.experimental_features,
            help="啟用實驗性功能（可能不穩定）"
        )
        
        preferences.cache_enabled = st.checkbox(
            "啟用快取",
            value=preferences.cache_enabled,
            help="啟用數據快取以提升性能"
        )
    
    # 數據源優先級
    st.markdown("#### 數據源優先級")
    
    available_sources = ["yahoo", "alpha_vantage", "quandl", "local"]
    
    # 使用多選框重新排序
    selected_sources = st.multiselect(
        "選擇並排序數據源（按優先級順序）",
        options=available_sources,
        default=preferences.data_source_priority[:len(available_sources)],
        help="拖拽重新排序，或重新選擇來改變優先級"
    )
    
    if selected_sources:
        preferences.data_source_priority = selected_sources
    
    # 顯示當前設置摘要
    st.markdown("#### 設置摘要")
    
    summary = {
        "主題": preferences.theme,
        "語言": preferences.language,
        "風險承受度": preferences.risk_tolerance,
        "通知": "啟用" if preferences.enable_notifications else "禁用",
        "調試模式": "啟用" if preferences.debug_mode else "禁用"
    }
    
    for key, value in summary.items():
        st.write(f"**{key}**: {value}")


def quick_theme_switcher():
    """快速主題切換器（用於側邊欄）"""
    preferences = get_current_user_preferences()
    if not preferences:
        return
    
    st.markdown("### 🎨 快速主題")
    
    theme_buttons = {
        ThemeType.LIGHT.value: "☀️",
        ThemeType.DARK.value: "🌙",
        ThemeType.AUTO.value: "🔄"
    }
    
    cols = st.columns(len(theme_buttons))
    
    for i, (theme, icon) in enumerate(theme_buttons.items()):
        with cols[i]:
            if st.button(icon, key=f"theme_{theme}", help=f"切換到{theme}主題"):
                preferences.theme = theme
                preferences_manager.save_preferences(preferences)
                
                # 立即應用主題
                theme_config = preferences_manager.get_theme_config(theme)
                apply_theme_to_streamlit(theme_config)
                
                st.rerun()


def preferences_status_indicator():
    """偏好設置狀態指示器"""
    preferences = get_current_user_preferences()
    if not preferences:
        st.warning("⚠️ 偏好設置未加載")
        return
    
    # 顯示當前主要設置
    col1, col2, col3 = st.columns(3)
    
    with col1:
        theme_icons = {
            ThemeType.LIGHT.value: "☀️",
            ThemeType.DARK.value: "🌙",
            ThemeType.AUTO.value: "🔄"
        }
        st.write(f"{theme_icons.get(preferences.theme, '🎨')} {preferences.theme}")
    
    with col2:
        lang_icons = {
            LanguageType.ZH_TW.value: "🇹🇼",
            LanguageType.ZH_CN.value: "🇨🇳",
            LanguageType.EN_US.value: "🇺🇸",
            LanguageType.JA_JP.value: "🇯🇵"
        }
        st.write(f"{lang_icons.get(preferences.language, '🌐')} {preferences.language}")
    
    with col3:
        risk_icons = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🔴"
        }
        st.write(f"{risk_icons.get(preferences.risk_tolerance, '⚪')} {preferences.risk_tolerance}")
