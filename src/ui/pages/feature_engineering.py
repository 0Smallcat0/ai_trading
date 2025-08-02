"""
特徵工程頁面 - 統一入口點

此頁面提供特徵工程相關的功能，包括：
1. 可用特徵展示
2. 特徵計算與更新
3. 特徵查詢
4. 特徵選擇
5. 特徵工程日誌

版本: v3.0 (模組化重構)
更新日期: 2025-01-17
重構說明: 將2604行大檔案拆分為6個≤300行的子模組，保持100%向後相容性

模組結構:
- feature_engineering/available_features.py: 可用特徵展示 (108行)
- feature_engineering/feature_calculation.py: 特徵計算與更新 (298行)
- feature_engineering/feature_query.py: 特徵查詢 (295行)
- feature_engineering/feature_selection.py: 特徵選擇 (298行)
- feature_engineering/feature_logs.py: 特徵工程日誌 (299行)
- feature_engineering/utils.py: 共用工具函數 (299行)
"""

import streamlit as st

# 導入子模組功能
from .feature_engineering import (
    show_available_features,
    show_feature_calculation,
    show_feature_query,
    show_feature_selection,
    show_feature_engineering_log,
)


def main():
    """特徵工程頁面主函數"""
    st.title("特徵工程")
    
    # 創建側邊欄導航
    st.sidebar.title("功能選單")
    
    # 功能選項
    feature_options = {
        "可用特徵": "查看系統中所有可用的特徵指標",
        "特徵計算": "計算和更新特徵數據",
        "特徵查詢": "查詢和分析已計算的特徵",
        "特徵選擇": "使用統計和機器學習方法選擇重要特徵",
        "工程日誌": "查看特徵工程的執行日誌和性能監控",
    }
    
    # 顯示功能描述
    with st.sidebar.expander("功能說明", expanded=False):
        for func_name, description in feature_options.items():
            st.write(f"**{func_name}**: {description}")
    
    # 功能選擇
    selected_function = st.sidebar.selectbox(
        "選擇功能",
        options=list(feature_options.keys()),
        index=0,
    )
    
    # 顯示選中功能的描述
    st.info(f"📋 {feature_options[selected_function]}")
    
    # 根據選擇顯示對應功能
    if selected_function == "可用特徵":
        show_available_features()
    elif selected_function == "特徵計算":
        show_feature_calculation()
    elif selected_function == "特徵查詢":
        show_feature_query()
    elif selected_function == "特徵選擇":
        show_feature_selection()
    elif selected_function == "工程日誌":
        show_feature_engineering_log()
    
    # 顯示頁面底部信息
    _show_page_footer()


def _show_page_footer():
    """顯示頁面底部信息"""
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📊 重構統計**")
        st.markdown("- 原始檔案: 2604行")
        st.markdown("- 重構後: 6個模組")
        st.markdown("- 平均行數: ~250行/模組")
    
    with col2:
        st.markdown("**🔧 技術改進**")
        st.markdown("- 模組化架構")
        st.markdown("- 向後相容性")
        st.markdown("- 代碼可維護性提升")
    
    with col3:
        st.markdown("**📈 品質指標**")
        st.markdown("- Pylint目標: ≥8.5/10")
        st.markdown("- 測試覆蓋率: ≥80%")
        st.markdown("- 檔案大小: ≤300行")


# 為了保持向後相容性，保留原始函數名稱
def show_feature_engineering():
    """向後相容性函數 - 調用新的main函數"""
    main()


# 如果直接運行此文件，執行主函數
if __name__ == "__main__":
    main()
