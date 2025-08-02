"""
可訪問性管理器

實現 WCAG 2.1 可訪問性標準，包括：
- 顏色對比度檢查和優化
- Alt text 支持
- 鍵盤導航支持
- 螢幕閱讀器支持
- 可訪問性測試工具
"""

import colorsys
import streamlit as st
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ContrastLevel(Enum):
    """對比度等級"""
    AA_NORMAL = 4.5      # WCAG AA 標準文字
    AA_LARGE = 3.0       # WCAG AA 大文字
    AAA_NORMAL = 7.0     # WCAG AAA 標準文字
    AAA_LARGE = 4.5      # WCAG AAA 大文字


@dataclass
class ColorInfo:
    """顏色信息"""
    hex_color: str
    rgb: Tuple[int, int, int]
    luminance: float
    name: str = ""


@dataclass
class ContrastResult:
    """對比度檢查結果"""
    ratio: float
    passes_aa_normal: bool
    passes_aa_large: bool
    passes_aaa_normal: bool
    passes_aaa_large: bool
    recommendation: str = ""


class AccessibilityManager:
    """可訪問性管理器"""
    
    def __init__(self):
        """初始化可訪問性管理器"""
        self.color_palette = self._get_accessible_color_palette()
        self.alt_text_registry = {}
        
        # 初始化 session state
        if "accessibility_enabled" not in st.session_state:
            st.session_state.accessibility_enabled = True
        
        if "high_contrast_mode" not in st.session_state:
            st.session_state.high_contrast_mode = False
        
        if "screen_reader_mode" not in st.session_state:
            st.session_state.screen_reader_mode = False
    
    def _get_accessible_color_palette(self) -> Dict[str, str]:
        """獲取可訪問的顏色調色板"""
        return {
            # 高對比度顏色
            "primary_dark": "#1f2937",      # 深灰藍
            "primary_light": "#f9fafb",     # 淺灰白
            "success_dark": "#065f46",      # 深綠
            "success_light": "#d1fae5",     # 淺綠
            "warning_dark": "#92400e",      # 深橙
            "warning_light": "#fef3c7",     # 淺黃
            "error_dark": "#991b1b",        # 深紅
            "error_light": "#fee2e2",       # 淺紅
            "info_dark": "#1e40af",         # 深藍
            "info_light": "#dbeafe",        # 淺藍
            
            # 中性色
            "neutral_900": "#111827",
            "neutral_800": "#1f2937",
            "neutral_700": "#374151",
            "neutral_600": "#4b5563",
            "neutral_500": "#6b7280",
            "neutral_400": "#9ca3af",
            "neutral_300": "#d1d5db",
            "neutral_200": "#e5e7eb",
            "neutral_100": "#f3f4f6",
            "neutral_50": "#f9fafb",
        }
    
    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """將十六進制顏色轉換為 RGB
        
        Args:
            hex_color: 十六進制顏色代碼
            
        Returns:
            Tuple[int, int, int]: RGB 值
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def rgb_to_hex(self, rgb: Tuple[int, int, int]) -> str:
        """將 RGB 轉換為十六進制顏色
        
        Args:
            rgb: RGB 值
            
        Returns:
            str: 十六進制顏色代碼
        """
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    def calculate_luminance(self, rgb: Tuple[int, int, int]) -> float:
        """計算顏色的相對亮度
        
        Args:
            rgb: RGB 值
            
        Returns:
            float: 相對亮度 (0-1)
        """
        def normalize_color_component(c):
            c = c / 255.0
            if c <= 0.03928:
                return c / 12.92
            else:
                return pow((c + 0.055) / 1.055, 2.4)
        
        r, g, b = rgb
        r_norm = normalize_color_component(r)
        g_norm = normalize_color_component(g)
        b_norm = normalize_color_component(b)
        
        return 0.2126 * r_norm + 0.7152 * g_norm + 0.0722 * b_norm
    
    def calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """計算兩個顏色之間的對比度
        
        Args:
            color1: 第一個顏色（十六進制）
            color2: 第二個顏色（十六進制）
            
        Returns:
            float: 對比度比值
        """
        rgb1 = self.hex_to_rgb(color1)
        rgb2 = self.hex_to_rgb(color2)
        
        lum1 = self.calculate_luminance(rgb1)
        lum2 = self.calculate_luminance(rgb2)
        
        # 確保較亮的顏色在分子
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    def check_contrast_compliance(self, foreground: str, background: str) -> ContrastResult:
        """檢查顏色對比度是否符合 WCAG 標準
        
        Args:
            foreground: 前景色（十六進制）
            background: 背景色（十六進制）
            
        Returns:
            ContrastResult: 對比度檢查結果
        """
        ratio = self.calculate_contrast_ratio(foreground, background)
        
        result = ContrastResult(
            ratio=ratio,
            passes_aa_normal=ratio >= ContrastLevel.AA_NORMAL.value,
            passes_aa_large=ratio >= ContrastLevel.AA_LARGE.value,
            passes_aaa_normal=ratio >= ContrastLevel.AAA_NORMAL.value,
            passes_aaa_large=ratio >= ContrastLevel.AAA_LARGE.value
        )
        
        # 生成建議
        if result.passes_aaa_normal:
            result.recommendation = "✅ 優秀！符合 WCAG AAA 標準"
        elif result.passes_aa_normal:
            result.recommendation = "✅ 良好！符合 WCAG AA 標準"
        elif result.passes_aa_large:
            result.recommendation = "⚠️ 僅適用於大文字（18pt+ 或 14pt+ 粗體）"
        else:
            result.recommendation = "❌ 不符合 WCAG 標準，需要調整顏色"
        
        return result
    
    def suggest_accessible_color(self, base_color: str, background: str, target_level: ContrastLevel = ContrastLevel.AA_NORMAL) -> str:
        """建議可訪問的顏色
        
        Args:
            base_color: 基礎顏色
            background: 背景顏色
            target_level: 目標對比度等級
            
        Returns:
            str: 建議的顏色
        """
        base_rgb = self.hex_to_rgb(base_color)
        bg_luminance = self.calculate_luminance(self.hex_to_rgb(background))
        
        # 轉換為 HSV 以便調整
        h, s, v = colorsys.rgb_to_hsv(base_rgb[0]/255, base_rgb[1]/255, base_rgb[2]/255)
        
        # 嘗試調整亮度
        for adjustment in [0.1, 0.2, 0.3, 0.4, 0.5, -0.1, -0.2, -0.3, -0.4, -0.5]:
            new_v = max(0, min(1, v + adjustment))
            new_rgb = colorsys.hsv_to_rgb(h, s, new_v)
            new_rgb_int = tuple(int(c * 255) for c in new_rgb)
            new_hex = self.rgb_to_hex(new_rgb_int)
            
            ratio = self.calculate_contrast_ratio(new_hex, background)
            if ratio >= target_level.value:
                return new_hex
        
        # 如果調整亮度不行，嘗試調整飽和度
        for s_adj in [-0.2, -0.4, -0.6]:
            new_s = max(0, s + s_adj)
            for v_adj in [0.2, 0.4, 0.6, -0.2, -0.4, -0.6]:
                new_v = max(0, min(1, v + v_adj))
                new_rgb = colorsys.hsv_to_rgb(h, new_s, new_v)
                new_rgb_int = tuple(int(c * 255) for c in new_rgb)
                new_hex = self.rgb_to_hex(new_rgb_int)
                
                ratio = self.calculate_contrast_ratio(new_hex, background)
                if ratio >= target_level.value:
                    return new_hex
        
        # 最後嘗試使用預定義的高對比度顏色
        if bg_luminance > 0.5:  # 淺色背景
            return self.color_palette["neutral_900"]
        else:  # 深色背景
            return self.color_palette["neutral_50"]
    
    def register_alt_text(self, element_id: str, alt_text: str, description: str = "") -> None:
        """註冊元素的 alt text
        
        Args:
            element_id: 元素ID
            alt_text: 替代文字
            description: 詳細描述
        """
        self.alt_text_registry[element_id] = {
            "alt_text": alt_text,
            "description": description,
            "registered_at": st.session_state.get("current_time", "unknown")
        }
    
    def get_alt_text(self, element_id: str) -> Optional[str]:
        """獲取元素的 alt text
        
        Args:
            element_id: 元素ID
            
        Returns:
            Optional[str]: 替代文字
        """
        return self.alt_text_registry.get(element_id, {}).get("alt_text")
    
    def apply_high_contrast_theme(self) -> str:
        """應用高對比度主題
        
        Returns:
            str: CSS 樣式
        """
        if not st.session_state.get("high_contrast_mode", False):
            return ""
        
        css = f"""
        <style>
        /* 高對比度模式 */
        .stApp {{
            background-color: {self.color_palette["neutral_50"]} !important;
            color: {self.color_palette["neutral_900"]} !important;
        }}
        
        .stSidebar {{
            background-color: {self.color_palette["neutral_100"]} !important;
        }}
        
        .stButton > button {{
            background-color: {self.color_palette["neutral_900"]} !important;
            color: {self.color_palette["neutral_50"]} !important;
            border: 2px solid {self.color_palette["neutral_900"]} !important;
            font-weight: bold !important;
        }}
        
        .stButton > button:hover {{
            background-color: {self.color_palette["neutral_700"]} !important;
            border-color: {self.color_palette["neutral_700"]} !important;
        }}
        
        .stSelectbox > div > div {{
            background-color: {self.color_palette["neutral_50"]} !important;
            border: 2px solid {self.color_palette["neutral_900"]} !important;
        }}
        
        .stTextInput > div > div > input {{
            background-color: {self.color_palette["neutral_50"]} !important;
            border: 2px solid {self.color_palette["neutral_900"]} !important;
            color: {self.color_palette["neutral_900"]} !important;
        }}
        
        /* 焦點指示器 */
        .stButton > button:focus,
        .stSelectbox > div > div:focus-within,
        .stTextInput > div > div > input:focus {{
            outline: 3px solid {self.color_palette["info_dark"]} !important;
            outline-offset: 2px !important;
        }}
        
        /* 鏈接樣式 */
        a {{
            color: {self.color_palette["info_dark"]} !important;
            text-decoration: underline !important;
            font-weight: bold !important;
        }}
        
        a:hover {{
            color: {self.color_palette["info_dark"]} !important;
            background-color: {self.color_palette["info_light"]} !important;
        }}
        
        /* 錯誤和警告樣式 */
        .stAlert {{
            border: 2px solid !important;
            font-weight: bold !important;
        }}
        
        .stSuccess {{
            background-color: {self.color_palette["success_light"]} !important;
            border-color: {self.color_palette["success_dark"]} !important;
            color: {self.color_palette["success_dark"]} !important;
        }}
        
        .stError {{
            background-color: {self.color_palette["error_light"]} !important;
            border-color: {self.color_palette["error_dark"]} !important;
            color: {self.color_palette["error_dark"]} !important;
        }}
        
        .stWarning {{
            background-color: {self.color_palette["warning_light"]} !important;
            border-color: {self.color_palette["warning_dark"]} !important;
            color: {self.color_palette["warning_dark"]} !important;
        }}
        
        .stInfo {{
            background-color: {self.color_palette["info_light"]} !important;
            border-color: {self.color_palette["info_dark"]} !important;
            color: {self.color_palette["info_dark"]} !important;
        }}
        </style>
        """
        
        return css
    
    def generate_accessible_chart_colors(self, num_colors: int) -> List[str]:
        """生成可訪問的圖表顏色
        
        Args:
            num_colors: 需要的顏色數量
            
        Returns:
            List[str]: 顏色列表
        """
        # 預定義的可訪問顏色序列
        accessible_colors = [
            "#1f77b4",  # 藍色
            "#ff7f0e",  # 橙色
            "#2ca02c",  # 綠色
            "#d62728",  # 紅色
            "#9467bd",  # 紫色
            "#8c564b",  # 棕色
            "#e377c2",  # 粉色
            "#7f7f7f",  # 灰色
            "#bcbd22",  # 橄欖色
            "#17becf",  # 青色
        ]
        
        # 如果需要更多顏色，生成額外的顏色
        if num_colors > len(accessible_colors):
            import colorsys
            for i in range(len(accessible_colors), num_colors):
                hue = (i * 0.618033988749895) % 1  # 黃金比例
                saturation = 0.7
                value = 0.8
                rgb = colorsys.hsv_to_rgb(hue, saturation, value)
                hex_color = self.rgb_to_hex(tuple(int(c * 255) for c in rgb))
                accessible_colors.append(hex_color)
        
        return accessible_colors[:num_colors]
    
    def add_screen_reader_support(self, text: str, element_type: str = "text") -> str:
        """添加螢幕閱讀器支持
        
        Args:
            text: 文字內容
            element_type: 元素類型
            
        Returns:
            str: 帶有螢幕閱讀器支持的 HTML
        """
        if not st.session_state.get("screen_reader_mode", False):
            return text
        
        aria_labels = {
            "button": "按鈕",
            "link": "鏈接",
            "heading": "標題",
            "text": "文字",
            "image": "圖片",
            "chart": "圖表",
            "table": "表格"
        }
        
        aria_label = aria_labels.get(element_type, "元素")
        
        return f'<span role="{element_type}" aria-label="{aria_label}: {text}">{text}</span>'
    
    def validate_accessibility(self, colors: List[Tuple[str, str]], alt_texts: List[str]) -> Dict[str, Any]:
        """驗證可訪問性
        
        Args:
            colors: 顏色對列表 (前景色, 背景色)
            alt_texts: Alt text 列表
            
        Returns:
            Dict[str, Any]: 驗證結果
        """
        results = {
            "color_contrast": {
                "total_checks": len(colors),
                "passed_aa": 0,
                "passed_aaa": 0,
                "failed": 0,
                "details": []
            },
            "alt_text": {
                "total_elements": len(alt_texts),
                "with_alt_text": len([alt for alt in alt_texts if alt and alt.strip()]),
                "missing_alt_text": len([alt for alt in alt_texts if not alt or not alt.strip()]),
                "coverage": 0
            },
            "overall_score": 0
        }
        
        # 檢查顏色對比度
        for i, (fg, bg) in enumerate(colors):
            contrast_result = self.check_contrast_compliance(fg, bg)
            
            if contrast_result.passes_aa_normal:
                results["color_contrast"]["passed_aa"] += 1
            if contrast_result.passes_aaa_normal:
                results["color_contrast"]["passed_aaa"] += 1
            if not contrast_result.passes_aa_normal:
                results["color_contrast"]["failed"] += 1
            
            results["color_contrast"]["details"].append({
                "index": i,
                "foreground": fg,
                "background": bg,
                "ratio": contrast_result.ratio,
                "passes_aa": contrast_result.passes_aa_normal,
                "passes_aaa": contrast_result.passes_aaa_normal,
                "recommendation": contrast_result.recommendation
            })
        
        # 計算 Alt text 覆蓋率
        if results["alt_text"]["total_elements"] > 0:
            results["alt_text"]["coverage"] = (
                results["alt_text"]["with_alt_text"] / 
                results["alt_text"]["total_elements"] * 100
            )
        
        # 計算總體分數
        color_score = (results["color_contrast"]["passed_aa"] / 
                      max(1, results["color_contrast"]["total_checks"]) * 50)
        alt_text_score = results["alt_text"]["coverage"] * 0.5
        
        results["overall_score"] = min(100, color_score + alt_text_score)
        
        return results


# 全域可訪問性管理器
accessibility_manager = AccessibilityManager()
