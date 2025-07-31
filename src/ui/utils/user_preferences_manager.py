"""
用戶偏好設置管理器

提供完整的用戶偏好設置功能，包括：
- 主題設置和切換
- 語言偏好管理
- 默認參數配置
- 個人化設置
- 偏好設置持久化
"""

import json
import os
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import streamlit as st
import logging

logger = logging.getLogger(__name__)


class ThemeType(Enum):
    """主題類型"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    CUSTOM = "custom"


class LanguageType(Enum):
    """語言類型"""
    ZH_TW = "zh-TW"
    ZH_CN = "zh-CN"
    EN_US = "en-US"
    JA_JP = "ja-JP"


@dataclass
class UserPreferences:
    """用戶偏好設置數據模型"""
    # 基本設置
    user_id: str
    username: str
    
    # 界面設置
    theme: str = ThemeType.LIGHT.value
    language: str = LanguageType.ZH_TW.value
    font_size: float = 1.0
    sidebar_collapsed: bool = False
    
    # 功能設置
    auto_refresh: bool = True
    refresh_interval: int = 30  # 秒
    enable_animations: bool = True
    enable_sound: bool = True
    
    # 交易設置
    default_order_type: str = "limit"
    default_quantity: int = 100
    risk_tolerance: str = "medium"  # low, medium, high
    auto_stop_loss: bool = True
    stop_loss_percentage: float = 0.05
    
    # 通知設置
    enable_notifications: bool = True
    notification_types: Dict[str, bool] = None
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    
    # 圖表設置
    chart_theme: str = "plotly_white"
    chart_height: int = 400
    show_volume: bool = True
    show_indicators: bool = True
    
    # 數據設置
    default_timeframe: str = "1d"
    data_source_priority: List[str] = None
    cache_enabled: bool = True
    
    # 高級設置
    debug_mode: bool = False
    performance_mode: bool = False
    experimental_features: bool = False
    
    # 元數據
    created_at: str = None
    updated_at: str = None
    version: str = "1.0"
    
    def __post_init__(self):
        """初始化後處理"""
        if self.notification_types is None:
            self.notification_types = {
                "trading": True,
                "risk": True,
                "system": True,
                "news": False
            }
        
        if self.data_source_priority is None:
            self.data_source_priority = ["yahoo", "alpha_vantage", "local"]
        
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        
        self.updated_at = datetime.now().isoformat()


class UserPreferencesManager:
    """用戶偏好設置管理器"""
    
    def __init__(self, storage_path: str = "data/user_preferences"):
        """初始化偏好設置管理器
        
        Args:
            storage_path: 存儲路徑
        """
        self.storage_path = storage_path
        self.preferences_cache: Dict[str, UserPreferences] = {}
        
        # 確保存儲目錄存在
        os.makedirs(storage_path, exist_ok=True)
        
        # 初始化 session state
        if "user_preferences" not in st.session_state:
            st.session_state.user_preferences = None
        
        if "preferences_loaded" not in st.session_state:
            st.session_state.preferences_loaded = False
    
    def get_default_preferences(self, user_id: str, username: str) -> UserPreferences:
        """獲取默認偏好設置
        
        Args:
            user_id: 用戶ID
            username: 用戶名
            
        Returns:
            UserPreferences: 默認偏好設置
        """
        return UserPreferences(
            user_id=user_id,
            username=username
        )
    
    def load_preferences(self, user_id: str, username: str = None) -> UserPreferences:
        """加載用戶偏好設置
        
        Args:
            user_id: 用戶ID
            username: 用戶名（可選）
            
        Returns:
            UserPreferences: 用戶偏好設置
        """
        # 檢查快取
        if user_id in self.preferences_cache:
            return self.preferences_cache[user_id]
        
        # 嘗試從文件加載
        file_path = os.path.join(self.storage_path, f"{user_id}.json")
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                preferences = UserPreferences(**data)
                self.preferences_cache[user_id] = preferences
                
                logger.info(f"已加載用戶 {user_id} 的偏好設置")
                return preferences
        
        except Exception as e:
            logger.error(f"加載用戶偏好設置失敗: {e}")
        
        # 返回默認設置
        default_prefs = self.get_default_preferences(user_id, username or user_id)
        self.preferences_cache[user_id] = default_prefs
        
        return default_prefs
    
    def save_preferences(self, preferences: UserPreferences) -> bool:
        """保存用戶偏好設置
        
        Args:
            preferences: 用戶偏好設置
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 更新時間戳
            preferences.updated_at = datetime.now().isoformat()
            
            # 保存到文件
            file_path = os.path.join(self.storage_path, f"{preferences.user_id}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(preferences), f, ensure_ascii=False, indent=2)
            
            # 更新快取
            self.preferences_cache[preferences.user_id] = preferences
            
            # 更新 session state
            if st.session_state.user_preferences and st.session_state.user_preferences.user_id == preferences.user_id:
                st.session_state.user_preferences = preferences
            
            logger.info(f"已保存用戶 {preferences.user_id} 的偏好設置")
            return True
        
        except Exception as e:
            logger.error(f"保存用戶偏好設置失敗: {e}")
            return False
    
    def update_preference(self, user_id: str, key: str, value: Any) -> bool:
        """更新單個偏好設置
        
        Args:
            user_id: 用戶ID
            key: 設置鍵
            value: 設置值
            
        Returns:
            bool: 是否更新成功
        """
        try:
            preferences = self.load_preferences(user_id)
            
            if hasattr(preferences, key):
                setattr(preferences, key, value)
                return self.save_preferences(preferences)
            else:
                logger.warning(f"未知的偏好設置鍵: {key}")
                return False
        
        except Exception as e:
            logger.error(f"更新偏好設置失敗: {e}")
            return False
    
    def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """獲取單個偏好設置
        
        Args:
            user_id: 用戶ID
            key: 設置鍵
            default: 默認值
            
        Returns:
            Any: 設置值
        """
        try:
            preferences = self.load_preferences(user_id)
            return getattr(preferences, key, default)
        
        except Exception as e:
            logger.error(f"獲取偏好設置失敗: {e}")
            return default
    
    def reset_preferences(self, user_id: str, username: str = None) -> bool:
        """重置用戶偏好設置為默認值
        
        Args:
            user_id: 用戶ID
            username: 用戶名
            
        Returns:
            bool: 是否重置成功
        """
        try:
            default_prefs = self.get_default_preferences(user_id, username or user_id)
            return self.save_preferences(default_prefs)
        
        except Exception as e:
            logger.error(f"重置偏好設置失敗: {e}")
            return False
    
    def export_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """導出用戶偏好設置
        
        Args:
            user_id: 用戶ID
            
        Returns:
            Optional[Dict[str, Any]]: 偏好設置字典
        """
        try:
            preferences = self.load_preferences(user_id)
            return asdict(preferences)
        
        except Exception as e:
            logger.error(f"導出偏好設置失敗: {e}")
            return None
    
    def import_preferences(self, user_id: str, preferences_data: Dict[str, Any]) -> bool:
        """導入用戶偏好設置
        
        Args:
            user_id: 用戶ID
            preferences_data: 偏好設置數據
            
        Returns:
            bool: 是否導入成功
        """
        try:
            # 確保用戶ID匹配
            preferences_data["user_id"] = user_id
            preferences_data["updated_at"] = datetime.now().isoformat()
            
            preferences = UserPreferences(**preferences_data)
            return self.save_preferences(preferences)
        
        except Exception as e:
            logger.error(f"導入偏好設置失敗: {e}")
            return False
    
    def get_theme_config(self, theme_type: str) -> Dict[str, Any]:
        """獲取主題配置
        
        Args:
            theme_type: 主題類型
            
        Returns:
            Dict[str, Any]: 主題配置
        """
        themes = {
            ThemeType.LIGHT.value: {
                "primary_color": "#1f77b4",
                "background_color": "#ffffff",
                "text_color": "#262730",
                "sidebar_color": "#f0f2f6"
            },
            ThemeType.DARK.value: {
                "primary_color": "#ff6b6b",
                "background_color": "#0e1117",
                "text_color": "#fafafa",
                "sidebar_color": "#262730"
            },
            ThemeType.AUTO.value: {
                "primary_color": "#1f77b4",
                "background_color": "auto",
                "text_color": "auto",
                "sidebar_color": "auto"
            }
        }
        
        return themes.get(theme_type, themes[ThemeType.LIGHT.value])
    
    def apply_preferences_to_session(self, user_id: str) -> None:
        """將偏好設置應用到 session state
        
        Args:
            user_id: 用戶ID
        """
        try:
            preferences = self.load_preferences(user_id)
            st.session_state.user_preferences = preferences
            st.session_state.preferences_loaded = True
            
            # 應用主題
            theme_config = self.get_theme_config(preferences.theme)
            st.session_state.theme_config = theme_config
            
            # 應用其他設置
            st.session_state.language = preferences.language
            st.session_state.font_size = preferences.font_size
            st.session_state.auto_refresh = preferences.auto_refresh
            st.session_state.refresh_interval = preferences.refresh_interval
            
            logger.info(f"已應用用戶 {user_id} 的偏好設置到 session")
        
        except Exception as e:
            logger.error(f"應用偏好設置失敗: {e}")


# 全域偏好設置管理器
preferences_manager = UserPreferencesManager()


# 便捷函數
def get_current_user_preferences() -> Optional[UserPreferences]:
    """獲取當前用戶的偏好設置"""
    return st.session_state.get("user_preferences")


def update_current_preference(key: str, value: Any) -> bool:
    """更新當前用戶的偏好設置"""
    preferences = get_current_user_preferences()
    if preferences:
        return preferences_manager.update_preference(preferences.user_id, key, value)
    return False


def get_current_preference(key: str, default: Any = None) -> Any:
    """獲取當前用戶的偏好設置值"""
    preferences = get_current_user_preferences()
    if preferences:
        return getattr(preferences, key, default)
    return default


def apply_theme_to_streamlit(theme_config: Dict[str, Any]) -> None:
    """將主題配置應用到 Streamlit"""
    try:
        css = f"""
        <style>
        .stApp {{
            background-color: {theme_config.get('background_color', '#ffffff')};
            color: {theme_config.get('text_color', '#262730')};
        }}

        .sidebar .sidebar-content {{
            background-color: {theme_config.get('sidebar_color', '#f0f2f6')};
        }}

        .stButton > button {{
            background-color: {theme_config.get('primary_color', '#1f77b4')};
            color: white;
            border: none;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            font-weight: bold;
            transition: all 0.3s ease;
        }}

        .stButton > button:hover {{
            opacity: 0.8;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        </style>
        """

        st.markdown(css, unsafe_allow_html=True)

    except Exception as e:
        logger.error(f"應用主題失敗: {e}")
