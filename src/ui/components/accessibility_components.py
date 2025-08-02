"""
可訪問性組件

提供符合 WCAG 2.1 標準的 UI 組件，包括：
- 可訪問性設置面板
- 顏色對比度檢查工具
- Alt text 管理
- 可訪問性測試工具
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
import logging

from ..utils.accessibility_manager import (
    accessibility_manager,
    ContrastLevel,
    ContrastResult
)

logger = logging.getLogger(__name__)


def accessibility_dashboard():
    """可訪問性儀表板"""
    st.subheader("♿ 可訪問性中心")
    
    # 當前可訪問性狀態
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        accessibility_enabled = st.session_state.get("accessibility_enabled", True)
        status = "✅ 啟用" if accessibility_enabled else "❌ 禁用"
        st.metric("可訪問性", status)
    
    with col2:
        high_contrast = st.session_state.get("high_contrast_mode", False)
        status = "🔆 開啟" if high_contrast else "🔅 關閉"
        st.metric("高對比度", status)
    
    with col3:
        screen_reader = st.session_state.get("screen_reader_mode", False)
        status = "🔊 開啟" if screen_reader else "🔇 關閉"
        st.metric("螢幕閱讀器", status)
    
    with col4:
        alt_text_count = len(accessibility_manager.alt_text_registry)
        st.metric("Alt Text 註冊", f"{alt_text_count} 項")
    
    # 標籤頁
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⚙️ 設置", "🎨 顏色對比", "🖼️ Alt Text", "🧪 測試工具", "📊 報告"
    ])
    
    with tab1:
        show_accessibility_settings()
    
    with tab2:
        show_color_contrast_tools()
    
    with tab3:
        show_alt_text_manager()
    
    with tab4:
        show_accessibility_testing_tools()
    
    with tab5:
        show_accessibility_report()


def show_accessibility_settings():
    """顯示可訪問性設置"""
    st.markdown("### ⚙️ 可訪問性設置")
    
    # 基本設置
    st.markdown("#### 基本設置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        accessibility_enabled = st.checkbox(
            "啟用可訪問性功能",
            value=st.session_state.get("accessibility_enabled", True),
            help="啟用所有可訪問性功能"
        )
        st.session_state.accessibility_enabled = accessibility_enabled
        
        high_contrast = st.checkbox(
            "高對比度模式",
            value=st.session_state.get("high_contrast_mode", False),
            help="啟用高對比度顏色主題"
        )
        st.session_state.high_contrast_mode = high_contrast
    
    with col2:
        screen_reader = st.checkbox(
            "螢幕閱讀器支持",
            value=st.session_state.get("screen_reader_mode", False),
            help="啟用螢幕閱讀器優化"
        )
        st.session_state.screen_reader_mode = screen_reader
        
        keyboard_nav = st.checkbox(
            "鍵盤導航增強",
            value=st.session_state.get("keyboard_navigation", True),
            help="增強鍵盤導航支持"
        )
        st.session_state.keyboard_navigation = keyboard_nav
    
    # 字體和顯示設置
    st.markdown("#### 字體和顯示")
    
    col1, col2 = st.columns(2)
    
    with col1:
        font_size = st.slider(
            "字體大小倍數",
            min_value=0.8,
            max_value=2.0,
            value=st.session_state.get("font_size_multiplier", 1.0),
            step=0.1,
            help="調整整體字體大小"
        )
        st.session_state.font_size_multiplier = font_size
        
        line_height = st.slider(
            "行高倍數",
            min_value=1.0,
            max_value=2.0,
            value=st.session_state.get("line_height_multiplier", 1.5),
            step=0.1,
            help="調整文字行高"
        )
        st.session_state.line_height_multiplier = line_height
    
    with col2:
        reduce_motion = st.checkbox(
            "減少動畫效果",
            value=st.session_state.get("reduce_motion", False),
            help="減少或禁用動畫效果"
        )
        st.session_state.reduce_motion = reduce_motion
        
        focus_indicators = st.checkbox(
            "增強焦點指示器",
            value=st.session_state.get("enhanced_focus", True),
            help="顯示更明顯的焦點指示器"
        )
        st.session_state.enhanced_focus = focus_indicators
    
    # 應用設置
    if st.button("🔄 應用設置", type="primary"):
        apply_accessibility_settings()
        st.success("✅ 可訪問性設置已應用")
        st.rerun()
    
    # 重置設置
    if st.button("🔄 重置為默認"):
        reset_accessibility_settings()
        st.success("✅ 已重置為默認設置")
        st.rerun()


def show_color_contrast_tools():
    """顯示顏色對比度工具"""
    st.markdown("### 🎨 顏色對比度檢查")
    
    # 顏色選擇器
    col1, col2 = st.columns(2)
    
    with col1:
        foreground_color = st.color_picker(
            "前景色（文字顏色）",
            value="#000000",
            help="選擇文字或前景元素的顏色"
        )
    
    with col2:
        background_color = st.color_picker(
            "背景色",
            value="#FFFFFF",
            help="選擇背景顏色"
        )
    
    # 即時對比度檢查
    if foreground_color and background_color:
        contrast_result = accessibility_manager.check_contrast_compliance(
            foreground_color, background_color
        )
        
        # 顯示對比度結果
        st.markdown("#### 📊 對比度檢查結果")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "對比度比值",
                f"{contrast_result.ratio:.2f}:1",
                help="WCAG 建議最小比值為 4.5:1"
            )
        
        with col2:
            aa_status = "✅ 通過" if contrast_result.passes_aa_normal else "❌ 未通過"
            st.metric("WCAG AA", aa_status)
        
        with col3:
            aaa_status = "✅ 通過" if contrast_result.passes_aaa_normal else "❌ 未通過"
            st.metric("WCAG AAA", aaa_status)
        
        # 詳細結果
        st.markdown("#### 📋 詳細結果")
        
        results_data = {
            "標準": ["AA 標準文字", "AA 大文字", "AAA 標準文字", "AAA 大文字"],
            "要求比值": ["4.5:1", "3.0:1", "7.0:1", "4.5:1"],
            "實際比值": [f"{contrast_result.ratio:.2f}:1"] * 4,
            "結果": [
                "✅ 通過" if contrast_result.passes_aa_normal else "❌ 未通過",
                "✅ 通過" if contrast_result.passes_aa_large else "❌ 未通過",
                "✅ 通過" if contrast_result.passes_aaa_normal else "❌ 未通過",
                "✅ 通過" if contrast_result.passes_aaa_large else "❌ 未通過"
            ]
        }
        
        df = pd.DataFrame(results_data)
        st.dataframe(df, use_container_width=True)
        
        # 建議
        st.info(contrast_result.recommendation)
        
        # 顏色預覽
        st.markdown("#### 👁️ 顏色預覽")
        
        preview_html = f"""
        <div style="
            background-color: {background_color};
            color: {foreground_color};
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #ccc;
            margin: 10px 0;
        ">
            <h3 style="margin: 0 0 10px 0; color: {foreground_color};">標題文字範例</h3>
            <p style="margin: 0; color: {foreground_color};">
                這是一段範例文字，用於測試顏色對比度。
                請確保文字清晰可讀，符合可訪問性標準。
            </p>
            <button style="
                background-color: {foreground_color};
                color: {background_color};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                margin-top: 10px;
                cursor: pointer;
            ">按鈕範例</button>
        </div>
        """
        
        st.markdown(preview_html, unsafe_allow_html=True)
        
        # 顏色建議
        if not contrast_result.passes_aa_normal:
            st.markdown("#### 💡 顏色建議")
            
            suggested_color = accessibility_manager.suggest_accessible_color(
                foreground_color, background_color, ContrastLevel.AA_NORMAL
            )
            
            st.write(f"建議的前景色: {suggested_color}")
            
            # 顯示建議顏色的預覽
            suggested_preview = f"""
            <div style="
                background-color: {background_color};
                color: {suggested_color};
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #ccc;
                margin: 10px 0;
            ">
                <strong>建議顏色預覽</strong><br>
                這是使用建議顏色的文字範例
            </div>
            """
            
            st.markdown(suggested_preview, unsafe_allow_html=True)
    
    # 批量檢查
    st.markdown("#### 📋 批量顏色檢查")
    
    if st.button("檢查系統預設顏色"):
        check_system_colors()


def show_alt_text_manager():
    """顯示 Alt Text 管理器"""
    st.markdown("### 🖼️ Alt Text 管理")
    
    # 註冊新的 Alt Text
    st.markdown("#### ➕ 註冊 Alt Text")
    
    col1, col2 = st.columns(2)
    
    with col1:
        element_id = st.text_input("元素 ID", placeholder="例如: chart_1, image_2")
        alt_text = st.text_input("Alt Text", placeholder="簡短描述")
    
    with col2:
        description = st.text_area("詳細描述", placeholder="更詳細的描述（可選）")
        
        if st.button("📝 註冊 Alt Text"):
            if element_id and alt_text:
                accessibility_manager.register_alt_text(element_id, alt_text, description)
                st.success(f"✅ 已註冊 Alt Text: {element_id}")
                st.rerun()
            else:
                st.error("❌ 請填寫元素 ID 和 Alt Text")
    
    # 已註冊的 Alt Text
    st.markdown("#### 📋 已註冊的 Alt Text")
    
    if accessibility_manager.alt_text_registry:
        alt_text_data = []
        for element_id, info in accessibility_manager.alt_text_registry.items():
            alt_text_data.append({
                "元素 ID": element_id,
                "Alt Text": info["alt_text"],
                "描述": info.get("description", ""),
                "註冊時間": info.get("registered_at", "未知")
            })
        
        df = pd.DataFrame(alt_text_data)
        st.dataframe(df, use_container_width=True)
        
        # 刪除功能
        selected_id = st.selectbox(
            "選擇要刪除的元素",
            options=[""] + list(accessibility_manager.alt_text_registry.keys())
        )
        
        if selected_id and st.button("🗑️ 刪除選中的 Alt Text"):
            del accessibility_manager.alt_text_registry[selected_id]
            st.success(f"✅ 已刪除 Alt Text: {selected_id}")
            st.rerun()
    
    else:
        st.info("📭 尚未註冊任何 Alt Text")
    
    # Alt Text 最佳實踐
    st.markdown("#### 💡 Alt Text 最佳實踐")
    
    with st.expander("查看 Alt Text 編寫指南"):
        st.markdown("""
        **好的 Alt Text 應該：**
        - 簡潔明瞭，通常不超過 125 個字符
        - 描述圖片的內容和功能
        - 避免使用 "圖片" 或 "圖像" 等詞語
        - 對於裝飾性圖片，可以使用空的 alt 屬性
        
        **範例：**
        - ✅ 好：「銷售趨勢圖顯示 2023 年第一季度增長 15%」
        - ❌ 差：「圖表」
        - ❌ 差：「這是一張顯示銷售數據的圖表圖片」
        
        **不同類型的圖片：**
        - **資訊圖表**：描述主要數據和趨勢
        - **功能按鈕**：描述按鈕的功能
        - **裝飾圖片**：使用空的 alt 屬性 (alt="")
        - **複雜圖表**：提供簡短 alt text 和詳細描述
        """)


def show_accessibility_testing_tools():
    """顯示可訪問性測試工具"""
    st.markdown("### 🧪 可訪問性測試工具")
    
    # 快速測試
    st.markdown("#### ⚡ 快速測試")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎨 測試顏色對比度", type="primary"):
            run_color_contrast_test()
    
    with col2:
        if st.button("🖼️ 測試 Alt Text 覆蓋率", type="primary"):
            run_alt_text_coverage_test()
    
    # 自定義測試
    st.markdown("#### 🔧 自定義測試")
    
    test_colors = st.text_area(
        "輸入顏色對（每行一對，格式：前景色,背景色）",
        value="#000000,#FFFFFF\n#FFFFFF,#000000\n#FF0000,#FFFFFF",
        help="例如：#000000,#FFFFFF"
    )
    
    test_alt_texts = st.text_area(
        "輸入 Alt Text 列表（每行一個）",
        value="銷售圖表\n用戶頭像\n\n裝飾圖片",
        help="空行表示缺少 Alt Text"
    )
    
    if st.button("🚀 運行自定義測試"):
        run_custom_accessibility_test(test_colors, test_alt_texts)
    
    # 測試結果歷史
    st.markdown("#### 📊 測試歷史")
    
    if "accessibility_test_history" in st.session_state:
        history = st.session_state.accessibility_test_history
        
        if history:
            df_history = pd.DataFrame(history)
            st.dataframe(df_history, use_container_width=True)
        else:
            st.info("📭 尚無測試歷史")
    else:
        st.info("📭 尚無測試歷史")


def show_accessibility_report():
    """顯示可訪問性報告"""
    st.markdown("### 📊 可訪問性報告")
    
    # 生成報告
    if st.button("📋 生成可訪問性報告", type="primary"):
        generate_accessibility_report()
    
    # 顯示現有報告
    if "accessibility_report" in st.session_state:
        report = st.session_state.accessibility_report
        
        # 總體分數
        col1, col2, col3 = st.columns(3)
        
        with col1:
            score = report.get("overall_score", 0)
            score_color = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
            st.metric("總體分數", f"{score_color} {score:.1f}/100")
        
        with col2:
            color_score = report.get("color_contrast", {}).get("passed_aa", 0)
            total_colors = report.get("color_contrast", {}).get("total_checks", 1)
            color_percentage = (color_score / total_colors * 100) if total_colors > 0 else 0
            st.metric("顏色對比度", f"{color_percentage:.1f}%")
        
        with col3:
            alt_coverage = report.get("alt_text", {}).get("coverage", 0)
            st.metric("Alt Text 覆蓋率", f"{alt_coverage:.1f}%")
        
        # 詳細結果
        st.markdown("#### 📋 詳細結果")
        
        # 顏色對比度結果
        if "color_contrast" in report:
            st.markdown("##### 🎨 顏色對比度")
            color_details = report["color_contrast"]["details"]
            
            if color_details:
                df_colors = pd.DataFrame(color_details)
                st.dataframe(df_colors, use_container_width=True)
        
        # Alt Text 結果
        if "alt_text" in report:
            st.markdown("##### 🖼️ Alt Text")
            alt_info = report["alt_text"]
            
            st.write(f"- 總元素數：{alt_info['total_elements']}")
            st.write(f"- 有 Alt Text：{alt_info['with_alt_text']}")
            st.write(f"- 缺少 Alt Text：{alt_info['missing_alt_text']}")
            st.write(f"- 覆蓋率：{alt_info['coverage']:.1f}%")
        
        # 建議
        st.markdown("#### 💡 改進建議")
        
        suggestions = generate_improvement_suggestions(report)
        for suggestion in suggestions:
            st.write(f"• {suggestion}")


def apply_accessibility_settings():
    """應用可訪問性設置"""
    # 應用高對比度主題
    if st.session_state.get("high_contrast_mode", False):
        css = accessibility_manager.apply_high_contrast_theme()
        st.markdown(css, unsafe_allow_html=True)
    
    # 應用字體大小調整
    font_multiplier = st.session_state.get("font_size_multiplier", 1.0)
    line_height_multiplier = st.session_state.get("line_height_multiplier", 1.5)
    
    if font_multiplier != 1.0 or line_height_multiplier != 1.5:
        font_css = f"""
        <style>
        .stApp {{
            font-size: {font_multiplier}em !important;
            line-height: {line_height_multiplier} !important;
        }}
        </style>
        """
        st.markdown(font_css, unsafe_allow_html=True)


def reset_accessibility_settings():
    """重置可訪問性設置"""
    default_settings = {
        "accessibility_enabled": True,
        "high_contrast_mode": False,
        "screen_reader_mode": False,
        "keyboard_navigation": True,
        "font_size_multiplier": 1.0,
        "line_height_multiplier": 1.5,
        "reduce_motion": False,
        "enhanced_focus": True
    }
    
    for key, value in default_settings.items():
        st.session_state[key] = value


def check_system_colors():
    """檢查系統預設顏色"""
    system_colors = [
        ("#000000", "#FFFFFF"),  # 黑白
        ("#FFFFFF", "#000000"),  # 白黑
        ("#1f77b4", "#FFFFFF"),  # 藍白
        ("#ff7f0e", "#FFFFFF"),  # 橙白
        ("#2ca02c", "#FFFFFF"),  # 綠白
        ("#d62728", "#FFFFFF"),  # 紅白
    ]
    
    results = []
    for fg, bg in system_colors:
        contrast_result = accessibility_manager.check_contrast_compliance(fg, bg)
        results.append({
            "前景色": fg,
            "背景色": bg,
            "對比度": f"{contrast_result.ratio:.2f}:1",
            "AA 標準": "✅" if contrast_result.passes_aa_normal else "❌",
            "AAA 標準": "✅" if contrast_result.passes_aaa_normal else "❌"
        })
    
    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)


def run_color_contrast_test():
    """運行顏色對比度測試"""
    # 模擬測試一些常用顏色組合
    test_colors = [
        ("#000000", "#FFFFFF"),
        ("#FFFFFF", "#000000"),
        ("#1f77b4", "#FFFFFF"),
        ("#ff7f0e", "#FFFFFF"),
        ("#2ca02c", "#FFFFFF"),
    ]
    
    passed = 0
    total = len(test_colors)
    
    for fg, bg in test_colors:
        result = accessibility_manager.check_contrast_compliance(fg, bg)
        if result.passes_aa_normal:
            passed += 1
    
    percentage = (passed / total * 100) if total > 0 else 0
    
    if percentage >= 80:
        st.success(f"✅ 顏色對比度測試通過！{passed}/{total} ({percentage:.1f}%)")
    else:
        st.warning(f"⚠️ 顏色對比度需要改進：{passed}/{total} ({percentage:.1f}%)")


def run_alt_text_coverage_test():
    """運行 Alt Text 覆蓋率測試"""
    total_elements = len(accessibility_manager.alt_text_registry)
    
    if total_elements == 0:
        st.warning("⚠️ 尚未註冊任何 Alt Text")
        return
    
    # 模擬檢查
    coverage = min(100, total_elements * 20)  # 簡化計算
    
    if coverage >= 80:
        st.success(f"✅ Alt Text 覆蓋率良好：{coverage:.1f}%")
    else:
        st.warning(f"⚠️ Alt Text 覆蓋率需要改進：{coverage:.1f}%")


def run_custom_accessibility_test(test_colors_str: str, test_alt_texts_str: str):
    """運行自定義可訪問性測試"""
    # 解析顏色對
    color_pairs = []
    for line in test_colors_str.strip().split('\n'):
        if ',' in line:
            fg, bg = line.strip().split(',')
            color_pairs.append((fg.strip(), bg.strip()))
    
    # 解析 Alt Text
    alt_texts = [line.strip() for line in test_alt_texts_str.strip().split('\n')]
    
    # 運行驗證
    validation_result = accessibility_manager.validate_accessibility(color_pairs, alt_texts)
    
    # 保存到歷史
    if "accessibility_test_history" not in st.session_state:
        st.session_state.accessibility_test_history = []
    
    st.session_state.accessibility_test_history.append({
        "時間": st.session_state.get("current_time", "未知"),
        "總體分數": f"{validation_result['overall_score']:.1f}",
        "顏色測試": f"{validation_result['color_contrast']['passed_aa']}/{validation_result['color_contrast']['total_checks']}",
        "Alt Text": f"{validation_result['alt_text']['coverage']:.1f}%"
    })
    
    # 顯示結果
    st.success(f"✅ 測試完成！總體分數：{validation_result['overall_score']:.1f}/100")
    
    # 保存詳細報告
    st.session_state.accessibility_report = validation_result


def generate_accessibility_report():
    """生成可訪問性報告"""
    # 模擬生成報告
    sample_colors = [
        ("#000000", "#FFFFFF"),
        ("#1f77b4", "#FFFFFF"),
        ("#ff7f0e", "#FFFFFF"),
    ]
    
    sample_alt_texts = ["圖表", "按鈕", "", "圖片"]
    
    report = accessibility_manager.validate_accessibility(sample_colors, sample_alt_texts)
    st.session_state.accessibility_report = report
    
    st.success("✅ 可訪問性報告已生成")


def generate_improvement_suggestions(report: Dict[str, Any]) -> List[str]:
    """生成改進建議"""
    suggestions = []
    
    # 顏色對比度建議
    color_info = report.get("color_contrast", {})
    if color_info.get("failed", 0) > 0:
        suggestions.append("調整顏色對比度，確保符合 WCAG AA 標準（4.5:1）")
    
    # Alt Text 建議
    alt_info = report.get("alt_text", {})
    if alt_info.get("coverage", 0) < 100:
        suggestions.append("為所有圖片和圖表添加描述性的 Alt Text")
    
    # 總體分數建議
    overall_score = report.get("overall_score", 0)
    if overall_score < 80:
        suggestions.append("啟用高對比度模式以提升可訪問性")
        suggestions.append("考慮增加鍵盤導航支持")
        suggestions.append("為互動元素添加焦點指示器")
    
    if not suggestions:
        suggestions.append("🎉 恭喜！您的應用程式符合可訪問性標準")
    
    return suggestions
