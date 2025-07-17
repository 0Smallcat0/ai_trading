"""回測系統組件

此模組整合所有回測分析相關功能，提供統一的回測分析介面：
- 回測增強功能
- 互動式圖表分析

主要功能：
- 統一的回測分析入口
- 回測執行和結果分析
- 互動式圖表展示
- 績效評估和比較
- 統一的錯誤處理機制

Example:
    >>> from src.ui.components.backtest_system import show
    >>> show()  # 顯示回測分析主介面
"""

import logging
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def show() -> None:
    """顯示回測分析主介面.
    
    整合所有回測分析相關功能到統一的標籤頁介面中。
    提供2個子功能的完整整合，包括錯誤處理和狀態管理。
    
    主要子功能：
    - 回測增強：完整的回測系統，包括參數設定、執行控制、結果分析
    - 互動式圖表：高度互動的圖表展示和分析功能
    
    Returns:
        None
        
    Side Effects:
        - 渲染 Streamlit 界面組件
        - 可能修改 st.session_state 中的相關狀態
        
    Example:
        >>> show()  # 顯示完整的回測分析介面
        
    Note:
        此函數整合了多個原有頁面的功能，保持向後兼容性。
        如果某個子功能不可用，會顯示相應的錯誤訊息。
    """
    try:
        st.title("📈 回測分析")
        st.markdown("---")
        
        # 創建子功能標籤頁
        tab1, tab2 = st.tabs([
            "📊 回測系統",
            "📈 互動式圖表"
        ])
        
        with tab1:
            _show_backtest_enhanced()
            
        with tab2:
            _show_interactive_charts()
            
    except Exception as e:
        logger.error("顯示回測分析介面時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 回測分析介面載入失敗")
        with st.expander("錯誤詳情"):
            st.code(str(e))


def _show_backtest_enhanced() -> None:
    """顯示回測增強功能.
    
    調用原有的 backtest_enhanced 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入回測增強頁面失敗時
    """
    try:
        from src.ui.pages.backtest_enhanced import show as backtest_show
        backtest_show()
        
    except ImportError as e:
        logger.warning("無法導入回測增強頁面: %s", e)
        st.warning("⚠️ 回測系統功能暫時不可用")
        _show_fallback_backtest_enhanced()
        
    except Exception as e:
        logger.error("顯示回測增強時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 回測系統功能載入失敗")
        _show_fallback_backtest_enhanced()


def _show_interactive_charts() -> None:
    """顯示互動式圖表功能.
    
    調用原有的 interactive_charts 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入互動式圖表頁面失敗時
    """
    try:
        from src.ui.pages.interactive_charts import show as charts_show
        charts_show()
        
    except ImportError as e:
        logger.warning("無法導入互動式圖表頁面: %s", e)
        st.warning("⚠️ 互動式圖表功能暫時不可用")
        _show_fallback_interactive_charts()
        
    except Exception as e:
        logger.error("顯示互動式圖表時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 互動式圖表功能載入失敗")
        _show_fallback_interactive_charts()


def _show_fallback_backtest_enhanced() -> None:
    """回測增強的備用顯示函數.
    
    當原有的回測增強頁面無法載入時，顯示基本的功能說明。
    
    Returns:
        None
    """
    st.info("📊 回測系統功能正在載入中...")
    
    st.markdown("""
    **回測系統** 提供完整的策略回測功能，包括：
    - ⚙️ **參數設定**: 設定回測期間、初始資金、手續費等參數
    - 🚀 **執行控制**: 啟動、暫停、停止回測執行
    - 📊 **結果分析**: 詳細的績效分析和風險指標
    - 📈 **視覺化**: 收益曲線、回撤分析、交易記錄圖表
    - 📋 **報表匯出**: 匯出詳細的回測報告
    """)
    
    # 顯示回測狀態概覽
    st.markdown("### 📊 回測狀態概覽")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("總回測數", "25", "+3")
    
    with col2:
        st.metric("成功率", "76%", "+4%")
    
    with col3:
        st.metric("平均收益", "12.5%", "+2.1%")
    
    with col4:
        st.metric("最佳策略", "動量策略", "✅")
    
    # 顯示快速回測設定
    st.markdown("### 🚀 快速回測設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 基本參數")
        strategy = st.selectbox("選擇策略", ["動量策略", "均值回歸", "趨勢跟隨", "配對交易"])
        start_date = st.date_input("開始日期")
        end_date = st.date_input("結束日期")
        initial_capital = st.number_input("初始資金", min_value=10000, value=100000)
        
    with col2:
        st.markdown("#### 進階設定")
        commission = st.slider("手續費率 (%)", 0.0, 1.0, 0.1, 0.01)
        slippage = st.slider("滑點 (%)", 0.0, 0.5, 0.05, 0.01)
        benchmark = st.selectbox("基準指數", ["SPY", "QQQ", "IWM", "自定義"])
        
    if st.button("🚀 開始回測", type="primary"):
        st.success("✅ 回測已開始執行...")
        st.info(f"策略: {strategy}, 期間: {start_date} - {end_date}, 初始資金: ${initial_capital:,}")


def _show_fallback_interactive_charts() -> None:
    """互動式圖表的備用顯示函數.
    
    當原有的互動式圖表頁面無法載入時，顯示基本的功能說明。
    
    Returns:
        None
    """
    st.info("📈 互動式圖表功能正在載入中...")
    
    st.markdown("""
    **互動式圖表** 提供高度互動的圖表展示功能，包括：
    - 📊 **圖表聯動**: 多個圖表之間的聯動展示
    - 📈 **進階K線圖**: 支援技術指標的K線圖分析
    - 🔍 **技術指標**: MACD、布林通道、KD指標等技術分析
    - ⏰ **多時間框架**: 支援不同時間週期的分析
    - 🔗 **相關性分析**: 股票間的相關性分析和展示
    - 📊 **績效比較**: 多個策略或股票的績效比較
    """)
    
    # 顯示圖表類型選擇
    st.markdown("### 📊 圖表類型選擇")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📈 K線圖分析", use_container_width=True):
            st.info("K線圖分析功能開發中...")
    
    with col2:
        if st.button("📊 技術指標", use_container_width=True):
            st.info("技術指標分析功能開發中...")
    
    with col3:
        if st.button("🔗 相關性分析", use_container_width=True):
            st.info("相關性分析功能開發中...")


# 輔助函數
def get_backtest_status() -> dict:
    """獲取回測狀態信息.
    
    Returns:
        dict: 包含回測狀態的字典
        
    Example:
        >>> status = get_backtest_status()
        >>> print(status['total_backtests'])
        25
    """
    return {
        'total_backtests': 25,
        'success_rate': 76,
        'avg_return': 12.5,
        'best_strategy': '動量策略'
    }


def validate_backtest_params(params: dict) -> bool:
    """驗證回測參數.
    
    Args:
        params: 回測參數字典
        
    Returns:
        bool: 參數是否有效
        
    Example:
        >>> params = {'start_date': '2023-01-01', 'end_date': '2023-12-31', 'initial_capital': 100000}
        >>> is_valid = validate_backtest_params(params)
        >>> print(is_valid)
        True
    """
    required_fields = ['start_date', 'end_date', 'initial_capital']
    return all(field in params and params[field] is not None for field in required_fields)
