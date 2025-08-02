"""策略管理組件

此模組整合所有策略管理相關功能，提供統一的策略管理介面：
- 策略管理基本功能
- 智能推薦系統
- LLM決策支援
- 投資組合管理
- 強化學習策略管理
- 文本分析功能

主要功能：
- 統一的策略管理入口
- 多種策略類型支援
- 智能決策輔助
- 投資組合優化
- 統一的錯誤處理機制

Example:
    >>> from src.ui.components.strategy_management import show
    >>> show()  # 顯示策略管理主介面
"""

import logging
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def show() -> None:
    """顯示策略管理主介面.
    
    整合所有策略管理相關功能到統一的標籤頁介面中。
    提供6個子功能的完整整合，包括錯誤處理和狀態管理。
    
    主要子功能：
    - 策略管理：基本的策略創建、編輯、版本控制等功能
    - 智能推薦：基於AI的策略推薦系統
    - LLM決策：大語言模型輔助決策功能
    - 投資組合：投資組合管理和優化
    - 強化學習策略：基於強化學習的策略管理
    - 文本分析：市場文本分析和情感分析
    
    Returns:
        None
        
    Side Effects:
        - 渲染 Streamlit 界面組件
        - 可能修改 st.session_state 中的相關狀態
        
    Example:
        >>> show()  # 顯示完整的策略管理介面
        
    Note:
        此函數整合了多個原有頁面的功能，保持向後兼容性。
        如果某個子功能不可用，會顯示相應的錯誤訊息。
    """
    try:
        st.title("🎯 策略管理")
        st.markdown("---")
        
        # 創建子功能標籤頁
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📈 策略管理",
            "🧠 智能推薦",
            "🤖 LLM決策",
            "💼 投資組合",
            "🎯 強化學習策略",
            "📝 文本分析"
        ])
        
        with tab1:
            _show_strategy_management()
            
        with tab2:
            _show_intelligent_recommendations()
            
        with tab3:
            _show_llm_decision()
            
        with tab4:
            _show_portfolio_management()
            
        with tab5:
            _show_rl_strategy_management()
            
        with tab6:
            _show_text_analysis()
            
    except Exception as e:
        logger.error("顯示策略管理介面時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 策略管理介面載入失敗")
        with st.expander("錯誤詳情"):
            st.code(str(e))


def _show_strategy_management() -> None:
    """顯示基本策略管理功能.
    
    調用原有的 strategy_management 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入策略管理頁面失敗時
    """
    try:
        from src.ui.pages.strategy_management import show as strategy_show
        strategy_show()
        
    except ImportError as e:
        logger.warning("無法導入策略管理頁面: %s", e)
        st.warning("⚠️ 策略管理功能暫時不可用")
        _show_fallback_strategy_management()
        
    except Exception as e:
        logger.error("顯示策略管理時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 策略管理功能載入失敗")
        _show_fallback_strategy_management()


def _show_intelligent_recommendations() -> None:
    """顯示智能推薦功能.
    
    調用原有的 intelligent_recommendations 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入智能推薦頁面失敗時
    """
    try:
        from src.ui.pages.intelligent_recommendations import show as recommendations_show
        recommendations_show()
        
    except ImportError as e:
        logger.warning("無法導入智能推薦頁面: %s", e)
        st.warning("⚠️ 智能推薦功能暫時不可用")
        _show_fallback_intelligent_recommendations()
        
    except Exception as e:
        logger.error("顯示智能推薦時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 智能推薦功能載入失敗")
        _show_fallback_intelligent_recommendations()


def _show_llm_decision() -> None:
    """顯示LLM決策功能.
    
    調用原有的 llm_decision 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入LLM決策頁面失敗時
    """
    try:
        from src.ui.pages.llm_decision import show as llm_show
        llm_show()
        
    except ImportError as e:
        logger.warning("無法導入LLM決策頁面: %s", e)
        st.warning("⚠️ LLM決策功能暫時不可用")
        _show_fallback_llm_decision()
        
    except Exception as e:
        logger.error("顯示LLM決策時發生錯誤: %s", e, exc_info=True)
        st.error("❌ LLM決策功能載入失敗")
        _show_fallback_llm_decision()


def _show_portfolio_management() -> None:
    """顯示投資組合管理功能.
    
    調用原有的 portfolio_management 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入投資組合管理頁面失敗時
    """
    try:
        from src.ui.pages.portfolio_management import show as portfolio_show
        portfolio_show()
        
    except ImportError as e:
        logger.warning("無法導入投資組合管理頁面: %s", e)
        st.warning("⚠️ 投資組合管理功能暫時不可用")
        _show_fallback_portfolio_management()
        
    except Exception as e:
        logger.error("顯示投資組合管理時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 投資組合管理功能載入失敗")
        _show_fallback_portfolio_management()


def _show_rl_strategy_management() -> None:
    """顯示強化學習策略管理功能.
    
    調用原有的 rl_strategy_management 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入強化學習策略管理頁面失敗時
    """
    try:
        from src.ui.pages.rl_strategy_management import show as rl_show
        rl_show()
        
    except ImportError as e:
        logger.warning("無法導入強化學習策略管理頁面: %s", e)
        st.warning("⚠️ 強化學習策略管理功能暫時不可用")
        _show_fallback_rl_strategy_management()
        
    except Exception as e:
        logger.error("顯示強化學習策略管理時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 強化學習策略管理功能載入失敗")
        _show_fallback_rl_strategy_management()


def _show_text_analysis() -> None:
    """顯示文本分析功能.
    
    調用原有的 text_analysis 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入文本分析頁面失敗時
    """
    try:
        from src.ui.pages.text_analysis import show as text_show
        text_show()
        
    except ImportError as e:
        logger.warning("無法導入文本分析頁面: %s", e)
        st.warning("⚠️ 文本分析功能暫時不可用")
        _show_fallback_text_analysis()
        
    except Exception as e:
        logger.error("顯示文本分析時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 文本分析功能載入失敗")
        _show_fallback_text_analysis()


# 備用顯示函數
def _show_fallback_strategy_management() -> None:
    """策略管理的備用顯示函數."""
    st.info("📈 策略管理功能正在載入中...")
    st.markdown("**基本功能**：策略創建、編輯、版本控制、效能分析")
    
    # 顯示策略統計
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("總策略數", "12", "+2")
    with col2:
        st.metric("活躍策略", "5", "+1")
    with col3:
        st.metric("平均收益", "8.5%", "+1.2%")
    with col4:
        st.metric("最佳策略", "動量策略", "✅")


def _show_fallback_intelligent_recommendations() -> None:
    """智能推薦的備用顯示函數."""
    st.info("🧠 智能推薦功能正在載入中...")
    st.markdown("**AI功能**：策略推薦、參數優化、市場分析")


def _show_fallback_llm_decision() -> None:
    """LLM決策的備用顯示函數."""
    st.info("🤖 LLM決策功能正在載入中...")
    st.markdown("**決策支援**：大語言模型分析、決策建議、風險評估")


def _show_fallback_portfolio_management() -> None:
    """投資組合管理的備用顯示函數."""
    st.info("💼 投資組合管理功能正在載入中...")
    st.markdown("**組合管理**：資產配置、風險分散、績效追蹤")


def _show_fallback_rl_strategy_management() -> None:
    """強化學習策略管理的備用顯示函數."""
    st.info("🎯 強化學習策略管理功能正在載入中...")
    st.markdown("**強化學習**：智能策略、自適應學習、環境互動")


def _show_fallback_text_analysis() -> None:
    """文本分析的備用顯示函數."""
    st.info("📝 文本分析功能正在載入中...")
    st.markdown("**文本分析**：新聞分析、情感分析、市場情緒")
