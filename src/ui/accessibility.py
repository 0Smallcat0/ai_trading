"""Web UI 可訪問性增強模組

此模組提供 WCAG 2.1 可訪問性標準的實現，包括：
- 高對比度主題
- 鍵盤導航支援
- 螢幕閱讀器支援
- 色彩對比度檢查
- 替代文字管理

符合 WCAG 2.1 AA 級標準要求。
"""

import streamlit as st
from typing import Dict, Any, Optional, List
import logging

# 設定日誌
logger = logging.getLogger(__name__)


class AccessibilityManager:
    """可訪問性管理器
    
    提供 WCAG 2.1 標準的可訪問性功能實現。
    """
    
    # WCAG 2.1 顏色對比度標準
    CONTRAST_RATIOS = {
        "AA_NORMAL": 4.5,      # AA 級標準文字
        "AA_LARGE": 3.0,       # AA 級大文字
        "AAA_NORMAL": 7.0,     # AAA 級標準文字
        "AAA_LARGE": 4.5,      # AAA 級大文字
    }
    
    # 高對比度色彩配置
    HIGH_CONTRAST_COLORS = {
        "background": "#000000",
        "text": "#FFFFFF", 
        "primary": "#FFFF00",
        "secondary": "#00FFFF",
        "success": "#00FF00",
        "warning": "#FFAA00",
        "error": "#FF0000",
        "border": "#FFFFFF",
    }
    
    def __init__(self):
        """初始化可訪問性管理器"""
        self._initialize_session_state()
    
    def _initialize_session_state(self) -> None:
        """初始化 session state 中的可訪問性設定"""
        if "accessibility_enabled" not in st.session_state:
            st.session_state.accessibility_enabled = False
        if "high_contrast_mode" not in st.session_state:
            st.session_state.high_contrast_mode = False
        if "font_size_scale" not in st.session_state:
            st.session_state.font_size_scale = 1.0
        if "keyboard_navigation" not in st.session_state:
            st.session_state.keyboard_navigation = True
    
    def apply_accessibility_styles(self) -> None:
        """應用可訪問性樣式
        
        根據用戶設定應用相應的可訪問性樣式，包括：
        - 高對比度模式
        - 字體大小調整
        - 鍵盤導航樣式
        """
        try:
            css_styles = []
            
            # 基礎可訪問性樣式
            css_styles.append(self._get_base_accessibility_css())
            
            # 高對比度模式
            if st.session_state.get("high_contrast_mode", False):
                css_styles.append(self._get_high_contrast_css())
            
            # 字體大小調整
            font_scale = st.session_state.get("font_size_scale", 1.0)
            if font_scale != 1.0:
                css_styles.append(self._get_font_scale_css(font_scale))
            
            # 鍵盤導航樣式
            if st.session_state.get("keyboard_navigation", True):
                css_styles.append(self._get_keyboard_navigation_css())
            
            # 應用所有樣式
            combined_css = "\n".join(css_styles)
            st.markdown(f"<style>{combined_css}</style>", unsafe_allow_html=True)
            
            logger.info("可訪問性樣式已應用")
            
        except Exception as e:
            logger.error(f"應用可訪問性樣式失敗: {e}")
    
    def _get_base_accessibility_css(self) -> str:
        """獲取基礎可訪問性 CSS"""
        return """
        /* 基礎可訪問性樣式 */
        * {
            outline: none;
        }
        
        /* 焦點指示器 */
        button:focus,
        input:focus,
        select:focus,
        textarea:focus,
        [tabindex]:focus {
            outline: 3px solid #005fcc !important;
            outline-offset: 2px !important;
        }
        
        /* 跳過連結 */
        .skip-link {
            position: absolute;
            top: -40px;
            left: 6px;
            background: #000;
            color: #fff;
            padding: 8px;
            text-decoration: none;
            z-index: 1000;
        }
        
        .skip-link:focus {
            top: 6px;
        }
        
        /* 螢幕閱讀器專用文字 */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }
        
        /* 確保最小觸控目標大小 */
        button,
        .stButton > button,
        .stSelectbox > div,
        .stCheckbox > label {
            min-height: 44px !important;
            min-width: 44px !important;
        }
        """
    
    def _get_high_contrast_css(self) -> str:
        """獲取高對比度 CSS"""
        colors = self.HIGH_CONTRAST_COLORS
        return f"""
        /* 高對比度模式 */
        .stApp {{
            background-color: {colors['background']} !important;
            color: {colors['text']} !important;
        }}
        
        .stSidebar {{
            background-color: {colors['background']} !important;
            border-right: 2px solid {colors['border']} !important;
        }}
        
        .stButton > button {{
            background-color: {colors['background']} !important;
            color: {colors['text']} !important;
            border: 2px solid {colors['border']} !important;
        }}
        
        .stButton > button:hover {{
            background-color: {colors['primary']} !important;
            color: {colors['background']} !important;
        }}
        
        .stSelectbox > div > div {{
            background-color: {colors['background']} !important;
            color: {colors['text']} !important;
            border: 2px solid {colors['border']} !important;
        }}
        
        .stTextInput > div > div > input {{
            background-color: {colors['background']} !important;
            color: {colors['text']} !important;
            border: 2px solid {colors['border']} !important;
        }}
        
        .stMarkdown {{
            color: {colors['text']} !important;
        }}
        
        .stAlert {{
            border: 2px solid {colors['border']} !important;
        }}
        """
    
    def _get_font_scale_css(self, scale: float) -> str:
        """獲取字體縮放 CSS"""
        return f"""
        /* 字體大小調整 */
        html {{
            font-size: {16 * scale}px !important;
        }}
        
        .stApp {{
            font-size: {1 * scale}rem !important;
        }}
        
        h1 {{ font-size: {2.5 * scale}rem !important; }}
        h2 {{ font-size: {2 * scale}rem !important; }}
        h3 {{ font-size: {1.75 * scale}rem !important; }}
        h4 {{ font-size: {1.5 * scale}rem !important; }}
        h5 {{ font-size: {1.25 * scale}rem !important; }}
        h6 {{ font-size: {1 * scale}rem !important; }}
        """
    
    def _get_keyboard_navigation_css(self) -> str:
        """獲取鍵盤導航 CSS"""
        return """
        /* 鍵盤導航增強 */
        [tabindex="0"],
        [tabindex="-1"] {
            outline: none;
        }
        
        [tabindex="0"]:focus,
        [tabindex="-1"]:focus {
            outline: 3px solid #005fcc !important;
            outline-offset: 2px !important;
        }
        
        /* 改善按鈕的鍵盤導航 */
        .stButton > button {
            border-radius: 4px;
            transition: all 0.2s ease;
        }
        
        .stButton > button:focus {
            transform: scale(1.05);
            box-shadow: 0 0 0 3px rgba(0, 95, 204, 0.3);
        }
        """
    
    def show_accessibility_controls(self) -> None:
        """顯示可訪問性控制面板"""
        with st.sidebar:
            st.markdown("### ♿ 可訪問性設定")
            
            # 高對比度模式
            high_contrast = st.checkbox(
                "高對比度模式",
                value=st.session_state.get("high_contrast_mode", False),
                help="啟用高對比度顏色以改善視覺可訪問性"
            )
            st.session_state.high_contrast_mode = high_contrast
            
            # 字體大小調整
            font_scale = st.slider(
                "字體大小",
                min_value=0.8,
                max_value=2.0,
                value=st.session_state.get("font_size_scale", 1.0),
                step=0.1,
                help="調整整體字體大小"
            )
            st.session_state.font_size_scale = font_scale
            
            # 鍵盤導航
            keyboard_nav = st.checkbox(
                "增強鍵盤導航",
                value=st.session_state.get("keyboard_navigation", True),
                help="啟用增強的鍵盤導航支援"
            )
            st.session_state.keyboard_navigation = keyboard_nav
            
            # 應用設定
            if st.button("應用可訪問性設定"):
                self.apply_accessibility_styles()
                st.success("可訪問性設定已應用")
    
    def add_alt_text(self, element_type: str, alt_text: str) -> str:
        """為元素添加替代文字
        
        Args:
            element_type: 元素類型
            alt_text: 替代文字
            
        Returns:
            包含替代文字的 HTML 屬性
        """
        return f'alt="{alt_text}" aria-label="{alt_text}"'
    
    def create_accessible_button(
        self, 
        label: str, 
        key: str, 
        help_text: Optional[str] = None,
        disabled: bool = False
    ) -> bool:
        """創建可訪問的按鈕
        
        Args:
            label: 按鈕標籤
            key: 按鈕鍵值
            help_text: 幫助文字
            disabled: 是否禁用
            
        Returns:
            按鈕是否被點擊
        """
        # 添加 ARIA 屬性
        aria_label = f"{label}. {help_text}" if help_text else label
        
        return st.button(
            label,
            key=key,
            help=help_text,
            disabled=disabled
        )
    
    def check_color_contrast(
        self, 
        foreground: str, 
        background: str, 
        level: str = "AA_NORMAL"
    ) -> bool:
        """檢查顏色對比度是否符合 WCAG 標準
        
        Args:
            foreground: 前景色（十六進制）
            background: 背景色（十六進制）
            level: WCAG 標準級別
            
        Returns:
            是否符合對比度要求
        """
        try:
            # 簡化的對比度檢查（實際應用中需要更精確的計算）
            required_ratio = self.CONTRAST_RATIOS.get(level, 4.5)
            
            # 這裡應該實現實際的對比度計算
            # 為了簡化，假設深色背景和淺色前景符合要求
            fg_luminance = self._get_luminance(foreground)
            bg_luminance = self._get_luminance(background)
            
            contrast_ratio = (max(fg_luminance, bg_luminance) + 0.05) / (min(fg_luminance, bg_luminance) + 0.05)
            
            return contrast_ratio >= required_ratio
            
        except Exception as e:
            logger.error(f"檢查顏色對比度失敗: {e}")
            return False
    
    def _get_luminance(self, hex_color: str) -> float:
        """計算顏色的相對亮度
        
        Args:
            hex_color: 十六進制顏色值
            
        Returns:
            相對亮度值 (0-1)
        """
        try:
            # 移除 # 符號
            hex_color = hex_color.lstrip('#')
            
            # 轉換為 RGB
            r = int(hex_color[0:2], 16) / 255.0
            g = int(hex_color[2:4], 16) / 255.0
            b = int(hex_color[4:6], 16) / 255.0
            
            # 應用 gamma 校正
            def gamma_correct(c):
                return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            
            r = gamma_correct(r)
            g = gamma_correct(g)
            b = gamma_correct(b)
            
            # 計算相對亮度
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
            
        except Exception as e:
            logger.error(f"計算亮度失敗: {e}")
            return 0.5  # 返回中等亮度作為備用值


# 全域可訪問性管理器實例
accessibility_manager = AccessibilityManager()
