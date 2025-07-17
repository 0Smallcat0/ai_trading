#!/usr/bin/env python3
"""
現代化主題管理器
實現響應式設計、深色/淺色主題切換、自定義儀表板
"""

import streamlit as st
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime

class ModernThemeManager:
    """現代化主題管理器"""
    
    def __init__(self):
        """初始化主題管理器"""
        self.themes = self._load_themes()
        self.current_theme = self._get_current_theme()
    
    def _load_themes(self) -> Dict[str, Dict[str, Any]]:
        """載入主題配置"""
        return {
            "light": {
                "name": "淺色主題",
                "icon": "☀️",
                "colors": {
                    "primary": "#1f77b4",
                    "secondary": "#ff7f0e",
                    "success": "#2ca02c",
                    "warning": "#ff7f0e",
                    "error": "#d62728",
                    "info": "#17a2b8",
                    "background": "#ffffff",
                    "surface": "#f8f9fa",
                    "text": "#212529",
                    "text_secondary": "#6c757d"
                },
                "css": """
                <style>
                .main-header {
                    background: linear-gradient(90deg, #1f77b4 0%, #17a2b8 100%);
                    color: white;
                    padding: 1rem;
                    border-radius: 10px;
                    margin-bottom: 2rem;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }
                
                .metric-card {
                    background: #ffffff;
                    padding: 1.5rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    border-left: 4px solid #1f77b4;
                    margin-bottom: 1rem;
                }
                
                .status-indicator {
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }
                
                .status-healthy { background-color: #2ca02c; }
                .status-warning { background-color: #ff7f0e; }
                .status-error { background-color: #d62728; }
                
                .modern-button {
                    background: linear-gradient(45deg, #1f77b4, #17a2b8);
                    color: white;
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 25px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                
                .modern-button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                }
                
                .sidebar-modern {
                    background: #f8f9fa;
                    border-right: 1px solid #dee2e6;
                }
                
                .chart-container {
                    background: white;
                    padding: 1rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    margin-bottom: 1rem;
                }
                </style>
                """
            },
            "dark": {
                "name": "深色主題",
                "icon": "🌙",
                "colors": {
                    "primary": "#4dabf7",
                    "secondary": "#ffd43b",
                    "success": "#51cf66",
                    "warning": "#ffd43b",
                    "error": "#ff6b6b",
                    "info": "#4dabf7",
                    "background": "#1a1a1a",
                    "surface": "#2d2d2d",
                    "text": "#ffffff",
                    "text_secondary": "#adb5bd"
                },
                "css": """
                <style>
                .main-header {
                    background: linear-gradient(90deg, #4dabf7 0%, #339af0 100%);
                    color: white;
                    padding: 1rem;
                    border-radius: 10px;
                    margin-bottom: 2rem;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                }
                
                .metric-card {
                    background: #2d2d2d;
                    padding: 1.5rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
                    border-left: 4px solid #4dabf7;
                    margin-bottom: 1rem;
                    color: #ffffff;
                }
                
                .status-indicator {
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }
                
                .status-healthy { background-color: #51cf66; }
                .status-warning { background-color: #ffd43b; }
                .status-error { background-color: #ff6b6b; }
                
                .modern-button {
                    background: linear-gradient(45deg, #4dabf7, #339af0);
                    color: white;
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 25px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                
                .modern-button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
                }
                
                .sidebar-modern {
                    background: #2d2d2d;
                    border-right: 1px solid #495057;
                }
                
                .chart-container {
                    background: #2d2d2d;
                    padding: 1rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
                    margin-bottom: 1rem;
                }
                
                /* Streamlit 深色主題覆蓋 */
                .stApp {
                    background-color: #1a1a1a;
                    color: #ffffff;
                }
                
                .stSidebar {
                    background-color: #2d2d2d;
                }
                
                .stSelectbox > div > div {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                
                .stTextInput > div > div > input {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #495057;
                }
                </style>
                """
            },
            "blue": {
                "name": "商務藍主題",
                "icon": "💼",
                "colors": {
                    "primary": "#0066cc",
                    "secondary": "#4d94ff",
                    "success": "#00cc66",
                    "warning": "#ff9900",
                    "error": "#cc0000",
                    "info": "#0099cc",
                    "background": "#f5f7fa",
                    "surface": "#ffffff",
                    "text": "#2c3e50",
                    "text_secondary": "#7f8c8d"
                },
                "css": """
                <style>
                .main-header {
                    background: linear-gradient(90deg, #0066cc 0%, #4d94ff 100%);
                    color: white;
                    padding: 1rem;
                    border-radius: 10px;
                    margin-bottom: 2rem;
                    box-shadow: 0 4px 6px rgba(0, 102, 204, 0.3);
                }
                
                .metric-card {
                    background: #ffffff;
                    padding: 1.5rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0, 102, 204, 0.1);
                    border-left: 4px solid #0066cc;
                    margin-bottom: 1rem;
                }
                
                .modern-button {
                    background: linear-gradient(45deg, #0066cc, #4d94ff);
                    color: white;
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 25px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                
                .chart-container {
                    background: white;
                    padding: 1rem;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0, 102, 204, 0.1);
                    margin-bottom: 1rem;
                    border-top: 3px solid #0066cc;
                }
                </style>
                """
            }
        }
    
    def _get_current_theme(self) -> str:
        """獲取當前主題"""
        return st.session_state.get("current_theme", "light")
    
    def set_theme(self, theme_name: str):
        """設置主題"""
        if theme_name in self.themes:
            st.session_state.current_theme = theme_name
            self.current_theme = theme_name
    
    def get_theme_config(self, theme_name: Optional[str] = None) -> Dict[str, Any]:
        """獲取主題配置"""
        theme_name = theme_name or self.current_theme
        return self.themes.get(theme_name, self.themes["light"])
    
    def apply_theme(self, theme_name: Optional[str] = None):
        """應用主題"""
        theme_config = self.get_theme_config(theme_name)
        
        # 應用CSS樣式
        st.markdown(theme_config["css"], unsafe_allow_html=True)
        
        # 設置Streamlit配置
        if theme_name == "dark":
            st.markdown("""
            <script>
            // 嘗試設置Streamlit為深色模式
            if (window.parent && window.parent.document) {
                window.parent.document.body.classList.add('dark-theme');
            }
            </script>
            """, unsafe_allow_html=True)
    
    def show_theme_selector(self):
        """顯示主題選擇器"""
        st.sidebar.markdown("### 🎨 主題設置")
        
        theme_options = []
        theme_keys = []
        
        for key, config in self.themes.items():
            theme_options.append(f"{config['icon']} {config['name']}")
            theme_keys.append(key)
        
        selected_index = theme_keys.index(self.current_theme) if self.current_theme in theme_keys else 0
        
        selected_theme_display = st.sidebar.selectbox(
            "選擇主題",
            theme_options,
            index=selected_index,
            key="theme_selector"
        )
        
        # 獲取選中的主題key
        selected_index = theme_options.index(selected_theme_display)
        selected_theme = theme_keys[selected_index]
        
        if selected_theme != self.current_theme:
            self.set_theme(selected_theme)
            st.rerun()
        
        return selected_theme
    
    def create_modern_header(self, title: str, subtitle: Optional[str] = None):
        """創建現代化頁面標題"""
        header_html = f"""
        <div class="main-header">
            <h1 style="margin: 0; font-size: 2rem;">{title}</h1>
            {f'<p style="margin: 0.5rem 0 0 0; opacity: 0.9;">{subtitle}</p>' if subtitle else ''}
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)
    
    def create_metric_card(self, title: str, value: str, delta: Optional[str] = None, 
                          delta_color: str = "normal"):
        """創建現代化指標卡片"""
        delta_html = ""
        if delta:
            delta_colors = {
                "normal": "#6c757d",
                "positive": "#2ca02c",
                "negative": "#d62728"
            }
            color = delta_colors.get(delta_color, "#6c757d")
            delta_html = f'<p style="margin: 0.5rem 0 0 0; color: {color}; font-size: 0.9rem;">{delta}</p>'
        
        card_html = f"""
        <div class="metric-card">
            <h3 style="margin: 0; color: #6c757d; font-size: 0.9rem; text-transform: uppercase;">{title}</h3>
            <h2 style="margin: 0.5rem 0 0 0; font-size: 2rem; font-weight: bold;">{value}</h2>
            {delta_html}
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)
    
    def create_status_badge(self, status: str, text: str):
        """創建狀態徽章"""
        status_classes = {
            "healthy": "status-healthy",
            "warning": "status-warning", 
            "error": "status-error"
        }
        
        class_name = status_classes.get(status, "status-healthy")
        
        badge_html = f"""
        <span style="display: inline-flex; align-items: center; font-size: 0.9rem;">
            <span class="status-indicator {class_name}"></span>
            {text}
        </span>
        """
        st.markdown(badge_html, unsafe_allow_html=True)
    
    def create_modern_button(self, text: str, key: str, onclick_action=None):
        """創建現代化按鈕"""
        button_html = f"""
        <button class="modern-button" onclick="{onclick_action or ''}">{text}</button>
        """
        return st.markdown(button_html, unsafe_allow_html=True)
    
    def create_chart_container(self, chart_content):
        """創建圖表容器"""
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        chart_content()
        st.markdown('</div>', unsafe_allow_html=True)
    
    def get_responsive_columns(self, desktop_cols: int = 4, tablet_cols: int = 2, mobile_cols: int = 1):
        """獲取響應式列配置"""
        # 簡化的響應式實現
        # 實際應用中可以通過JavaScript檢測屏幕寬度
        return st.columns(desktop_cols)
    
    def save_theme_preference(self):
        """保存主題偏好"""
        try:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True)
            
            config_file = os.path.join(config_dir, "ui_preferences.json")
            
            preferences = {
                "theme": self.current_theme,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(preferences, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            st.warning(f"保存主題偏好失敗: {e}")
    
    def load_theme_preference(self):
        """載入主題偏好"""
        try:
            config_file = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "ui_preferences.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    preferences = json.load(f)
                    
                saved_theme = preferences.get("theme", "light")
                if saved_theme in self.themes:
                    self.set_theme(saved_theme)
                    
        except Exception as e:
            st.warning(f"載入主題偏好失敗: {e}")

# 全局主題管理器實例
theme_manager = ModernThemeManager()

def apply_modern_theme():
    """應用現代化主題"""
    theme_manager.load_theme_preference()
    selected_theme = theme_manager.show_theme_selector()
    theme_manager.apply_theme(selected_theme)
    
    # 保存主題偏好
    if selected_theme != st.session_state.get("last_saved_theme"):
        theme_manager.save_theme_preference()
        st.session_state.last_saved_theme = selected_theme
    
    return theme_manager

def create_modern_layout():
    """創建現代化佈局"""
    # 添加響應式CSS
    st.markdown("""
    <style>
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 1.5rem !important;
        }
        
        .metric-card {
            margin-bottom: 0.5rem;
        }
        
        .stColumns > div {
            padding: 0.25rem;
        }
    }
    
    @media (max-width: 480px) {
        .main-header {
            padding: 0.5rem;
        }
        
        .main-header h1 {
            font-size: 1.2rem !important;
        }
        
        .metric-card h2 {
            font-size: 1.5rem !important;
        }
    }
    
    /* 平滑過渡效果 */
    * {
        transition: all 0.3s ease;
    }
    
    /* 自定義滾動條 */
    ::-webkit-scrollbar {
        width: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8;
    }

    /* 動畫效果 */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .fade-in {
        animation: fadeIn 0.5s ease-out;
    }
    </style>
    """, unsafe_allow_html=True)
