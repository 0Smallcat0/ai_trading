"""
多語言支持組件

提供完整的多語言支持界面組件，包括：
- 語言切換器
- 語言資源管理
- 本地化文字顯示
- 語言驗證工具
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from ..localization.language_switcher import (
    get_language_switcher,
    get_text,
    show_language_selector
)

logger = logging.getLogger(__name__)


def multilingual_dashboard():
    """多語言支持儀表板"""
    st.subheader("🌐 多語言支持中心")
    
    switcher = get_language_switcher()
    current_lang = switcher.get_current_language()
    
    # 當前語言狀態
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        lang_info = switcher.get_language_info(current_lang)
        st.metric(
            "當前語言",
            f"{lang_info.get('flag', '🌐')} {lang_info.get('name', current_lang)}"
        )
    
    with col2:
        available_langs = len(switcher.SUPPORTED_LANGUAGES)
        st.metric("支持語言", f"{available_langs} 種")
    
    with col3:
        direction = switcher.get_language_direction()
        st.metric("文字方向", direction.upper())
    
    with col4:
        if st.button("🔄 重新載入語言資源"):
            switcher._load_all_language_resources()
            st.success("語言資源已重新載入")
            st.rerun()
    
    # 標籤頁
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔄 語言切換", "📋 語言資源", "🔍 資源驗證", "🛠️ 本地化工具"
    ])
    
    with tab1:
        show_language_switcher_panel()
    
    with tab2:
        show_language_resources_panel()
    
    with tab3:
        show_resource_validation_panel()
    
    with tab4:
        show_localization_tools_panel()


def show_language_switcher_panel():
    """顯示語言切換面板"""
    st.markdown("### 🔄 語言切換")
    
    switcher = get_language_switcher()
    
    # 語言選擇器
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 快速切換")
        show_language_selector(key="main_language_selector", show_in_sidebar=False)
    
    with col2:
        st.markdown("#### 可用語言")
        available_languages = switcher.get_available_languages()
        
        for lang in available_languages:
            col_flag, col_name, col_action = st.columns([1, 3, 2])
            
            with col_flag:
                st.write(lang["flag"])
            
            with col_name:
                st.write(f"**{lang['native_name']}** ({lang['name']})")
            
            with col_action:
                if st.button("選擇", key=f"select_{lang['code']}"):
                    switcher.set_language(lang["code"])
                    st.success(f"已切換到 {lang['native_name']}")
                    st.rerun()
    
    # 語言檢測
    st.markdown("#### 🔍 語言檢測")
    
    if st.button("檢測瀏覽器語言"):
        detected_lang = switcher._detect_user_language()
        st.info(f"檢測到的語言: {detected_lang}")
    
    # 語言統計
    st.markdown("#### 📊 使用統計")
    
    # 模擬語言使用統計
    usage_data = {
        "語言": ["繁體中文", "English", "简体中文", "日本語"],
        "使用次數": [45, 32, 18, 5],
        "百分比": [45, 32, 18, 5]
    }
    
    df = pd.DataFrame(usage_data)
    
    fig = px.pie(
        df, 
        values="百分比", 
        names="語言",
        title="語言使用分布"
    )
    st.plotly_chart(fig, use_container_width=True)


def show_language_resources_panel():
    """顯示語言資源面板"""
    st.markdown("### 📋 語言資源管理")
    
    switcher = get_language_switcher()
    
    # 資源概覽
    st.markdown("#### 資源概覽")
    
    resource_stats = []
    for lang_code, resources in switcher.language_resources.items():
        lang_info = switcher.SUPPORTED_LANGUAGES.get(lang_code, {})
        total_keys = len(switcher._get_all_keys(resources))
        
        resource_stats.append({
            "語言": f"{lang_info.get('flag', '🌐')} {lang_info.get('name', lang_code)}",
            "代碼": lang_code,
            "總鍵值數": total_keys,
            "文件": lang_info.get('file', 'N/A')
        })
    
    df_stats = pd.DataFrame(resource_stats)
    st.dataframe(df_stats, use_container_width=True)
    
    # 資源瀏覽
    st.markdown("#### 🔍 資源瀏覽")
    
    selected_lang = st.selectbox(
        "選擇語言",
        options=list(switcher.SUPPORTED_LANGUAGES.keys()),
        format_func=lambda x: f"{switcher.SUPPORTED_LANGUAGES[x]['flag']} {switcher.SUPPORTED_LANGUAGES[x]['name']}"
    )
    
    if selected_lang:
        resources = switcher.language_resources.get(selected_lang, {})
        
        # 搜索功能
        search_term = st.text_input("🔍 搜索鍵值")
        
        # 顯示資源
        if search_term:
            filtered_resources = _filter_resources(resources, search_term)
            st.write(f"找到 {len(filtered_resources)} 個匹配項目")
            _display_resources(filtered_resources)
        else:
            _display_resources(resources)


def show_resource_validation_panel():
    """顯示資源驗證面板"""
    st.markdown("### 🔍 語言資源驗證")
    
    switcher = get_language_switcher()
    
    if st.button("🔍 開始驗證", type="primary"):
        with st.spinner("驗證中..."):
            validation_results = switcher.validate_language_resources()
        
        if validation_results:
            st.warning("發現缺失的翻譯:")
            
            for lang_code, missing_keys in validation_results.items():
                lang_info = switcher.SUPPORTED_LANGUAGES.get(lang_code, {})
                
                with st.expander(f"{lang_info.get('flag', '🌐')} {lang_info.get('name', lang_code)} - 缺失 {len(missing_keys)} 項"):
                    for key in missing_keys:
                        st.write(f"• `{key}`")
                    
                    # 提供修復建議
                    st.markdown("**修復建議:**")
                    st.code(f"""
# 在 {lang_info.get('file', f'{lang_code}.json')} 中添加:
{chr(10).join([f'"{key}": "待翻譯"' for key in missing_keys[:5]])}
{"..." if len(missing_keys) > 5 else ""}
                    """)
        else:
            st.success("✅ 所有語言資源完整!")
    
    # 資源統計
    st.markdown("#### 📊 資源統計")
    
    stats_data = []
    default_resources = switcher.language_resources.get(switcher.DEFAULT_LANGUAGE, {})
    default_keys_count = len(switcher._get_all_keys(default_resources))
    
    for lang_code, resources in switcher.language_resources.items():
        lang_info = switcher.SUPPORTED_LANGUAGES.get(lang_code, {})
        keys_count = len(switcher._get_all_keys(resources))
        completeness = (keys_count / default_keys_count * 100) if default_keys_count > 0 else 0
        
        stats_data.append({
            "語言": f"{lang_info.get('flag', '🌐')} {lang_info.get('name', lang_code)}",
            "鍵值數": keys_count,
            "完整度": f"{completeness:.1f}%",
            "狀態": "✅ 完整" if completeness >= 100 else "⚠️ 不完整"
        })
    
    df_stats = pd.DataFrame(stats_data)
    st.dataframe(df_stats, use_container_width=True)


def show_localization_tools_panel():
    """顯示本地化工具面板"""
    st.markdown("### 🛠️ 本地化工具")
    
    switcher = get_language_switcher()
    
    # 文字測試工具
    st.markdown("#### 📝 文字測試")
    
    col1, col2 = st.columns(2)
    
    with col1:
        test_key = st.text_input("輸入鍵值", value="common.save")
        test_params = st.text_input("參數 (JSON格式)", value='{"name": "測試"}')
    
    with col2:
        if st.button("🔍 測試翻譯"):
            try:
                import json
                params = json.loads(test_params) if test_params else {}
                
                for lang_code in switcher.SUPPORTED_LANGUAGES.keys():
                    original_lang = switcher.get_current_language()
                    switcher.set_language(lang_code)
                    
                    text = switcher.get_text(test_key, **params)
                    lang_info = switcher.SUPPORTED_LANGUAGES[lang_code]
                    
                    st.write(f"{lang_info['flag']} **{lang_info['name']}**: {text}")
                    
                    switcher.set_language(original_lang)
            
            except Exception as e:
                st.error(f"測試失敗: {e}")
    
    # 格式化工具
    st.markdown("#### 🔢 格式化工具")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        test_number = st.number_input("測試數字", value=1234567.89)
        if st.button("格式化數字"):
            formatted = switcher.format_number(test_number)
            st.success(f"格式化結果: {formatted}")
    
    with col2:
        test_amount = st.number_input("測試金額", value=1000.50)
        if st.button("格式化貨幣"):
            formatted = switcher.format_currency(test_amount)
            st.success(f"格式化結果: {formatted}")
    
    with col3:
        test_date = st.date_input("測試日期", value=datetime.now().date())
        if st.button("格式化日期"):
            formatted = switcher.format_date(datetime.combine(test_date, datetime.min.time()))
            st.success(f"格式化結果: {formatted}")
    
    # 導出工具
    st.markdown("#### 📤 導出工具")
    
    if st.button("📥 導出語言資源"):
        export_data = {}
        for lang_code, resources in switcher.language_resources.items():
            export_data[lang_code] = resources
        
        import json
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        
        st.download_button(
            label="下載語言資源",
            data=json_str,
            file_name=f"language_resources_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )


def _filter_resources(resources: Dict[str, Any], search_term: str, prefix: str = "") -> Dict[str, str]:
    """過濾資源"""
    filtered = {}
    
    for key, value in resources.items():
        full_key = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict):
            sub_filtered = _filter_resources(value, search_term, full_key)
            filtered.update(sub_filtered)
        else:
            if (search_term.lower() in full_key.lower() or 
                search_term.lower() in str(value).lower()):
                filtered[full_key] = str(value)
    
    return filtered


def _display_resources(resources: Dict[str, Any], prefix: str = "", max_items: int = 50):
    """顯示資源"""
    if isinstance(resources, dict):
        items = list(resources.items())
        if len(items) > max_items:
            st.warning(f"顯示前 {max_items} 項，共 {len(items)} 項")
            items = items[:max_items]
        
        for key, value in items:
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                with st.expander(f"📁 {key}"):
                    _display_resources(value, full_key, max_items)
            else:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.code(full_key)
                with col2:
                    st.write(str(value))
    else:
        flat_resources = {}
        for key, value in resources.items():
            flat_resources[key] = value
        
        df = pd.DataFrame(list(flat_resources.items()), columns=["鍵值", "內容"])
        st.dataframe(df, use_container_width=True)


def quick_language_indicator():
    """快速語言指示器（用於側邊欄）"""
    switcher = get_language_switcher()
    current_lang = switcher.get_current_language()
    lang_info = switcher.get_language_info(current_lang)
    
    st.markdown(f"**🌐 {lang_info.get('flag', '🌐')} {lang_info.get('native_name', current_lang)}**")


def localized_text(key: str, default: str = "", **kwargs) -> str:
    """本地化文字便捷函數"""
    return get_text(key, default, **kwargs)


def localized_metric(label_key: str, value, delta=None, help_key: str = None):
    """本地化指標組件"""
    label = get_text(label_key)
    help_text = get_text(help_key) if help_key else None
    
    st.metric(label=label, value=value, delta=delta, help=help_text)


def localized_button(label_key: str, **kwargs) -> bool:
    """本地化按鈕組件"""
    label = get_text(label_key)
    return st.button(label, **kwargs)


def localized_selectbox(label_key: str, options, **kwargs):
    """本地化選擇框組件"""
    label = get_text(label_key)
    return st.selectbox(label, options, **kwargs)
