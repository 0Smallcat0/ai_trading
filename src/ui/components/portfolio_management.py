"""投資組合管理組件

此模組整合所有投資組合管理相關功能，提供統一的投資組合管理介面：
- 投資組合管理基本功能
- 文本分析功能

主要功能：
- 統一的投資組合管理入口
- 組合配置和優化
- 文本分析和市場情緒
- 績效評估和報告
- 統一的錯誤處理機制

Example:
    >>> from src.ui.components.portfolio_management import show
    >>> show()  # 顯示投資組合管理主介面
"""

import logging

import streamlit as st

logger = logging.getLogger(__name__)


def show() -> None:
    """顯示投資組合管理主介面.

    整合所有投資組合管理相關功能到統一的標籤頁介面中。
    提供2個子功能的完整整合，包括錯誤處理和狀態管理。

    主要子功能：
    - 投資組合管理：組合配置、優化、績效評估等功能
    - 文本分析：市場情緒分析、新聞分析等功能

    Side Effects:
        - 渲染 Streamlit 界面組件
        - 可能修改 st.session_state 中的相關狀態

    Example:
        >>> show()  # 顯示完整的投資組合管理介面

    Note:
        此函數整合了多個原有頁面的功能，保持向後兼容性。
        如果某個子功能不可用，會顯示相應的錯誤訊息。
    """
    try:
        st.title("💼 投資組合管理")
        st.markdown("---")

        # 創建子功能標籤頁
        tab1, tab2 = st.tabs([
            "💼 投資組合",
            "📝 文本分析"
        ])

        with tab1:
            _show_portfolio_management()

        with tab2:
            _show_text_analysis()

    except Exception as e:
        logger.error("顯示投資組合管理介面時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 投資組合管理介面載入失敗")
        with st.expander("錯誤詳情"):
            st.code(str(e))


def _show_portfolio_management() -> None:
    """顯示投資組合管理功能.

    調用原有的 portfolio_management 頁面功能。

    Raises:
        Exception: 當載入投資組合管理頁面失敗時
    """
    try:
        # 動態導入以避免循環依賴
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


def _show_text_analysis() -> None:
    """顯示文本分析功能.

    調用原有的 text_analysis 頁面功能。

    Raises:
        Exception: 當載入文本分析頁面失敗時
    """
    try:
        # 動態導入以避免循環依賴
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


def _show_fallback_portfolio_management() -> None:
    """投資組合管理的備用顯示函數.

    當原有的投資組合管理頁面無法載入時，顯示基本的功能說明。
    """
    st.info("💼 投資組合管理功能正在載入中...")

    st.markdown("""
    **投資組合管理系統** 提供完整的組合管理功能，包括：
    - 📊 **組合配置**: 資產配置和權重管理
    - 🎯 **組合優化**: 基於現代投資組合理論的優化
    - 📈 **績效評估**: 組合績效分析和歸因分析
    - ⚖️ **風險分散**: 風險分散和相關性分析
    - 📋 **再平衡**: 組合再平衡和調整建議
    """)

    # 顯示組合概覽
    st.markdown("### 📊 投資組合概覽")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("總市值", "$125,430", "+$2,340 (+1.9%)")

    with col2:
        st.metric("持倉數量", "12", "0")

    with col3:
        st.metric("年化收益", "12.5%", "+2.1%")

    with col4:
        st.metric("夏普比率", "1.35", "+0.15")
    
    # 顯示資產配置
    st.markdown("### 🥧 資產配置")

    allocation_data = [
        {"資產類別": "股票", "配置比例": "70%", "目標比例": "65%", "偏差": "+5%"},
        {"資產類別": "債券", "配置比例": "20%", "目標比例": "25%", "偏差": "-5%"},
        {"資產類別": "現金", "配置比例": "10%", "目標比例": "10%", "偏差": "0%"}
    ]

    for allocation in allocation_data:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.write(f"**{allocation['資產類別']}**")
        with col2:
            st.write(f"當前: {allocation['配置比例']}")
        with col3:
            st.write(f"目標: {allocation['目標比例']}")
        with col4:
            deviation_color = ("🔴" if allocation['偏差'].startswith('+') else
                              "🟢" if allocation['偏差'].startswith('-') else "⚪")
            st.write(f"{deviation_color} {allocation['偏差']}")
    
    # 顯示持倉明細
    st.markdown("### 📋 持倉明細")

    holdings = [
        {"股票": "AAPL", "數量": "100", "市值": "$15,000",
         "權重": "12%", "收益": "+8.5%"},
        {"股票": "GOOGL", "數量": "50", "市值": "$12,500",
         "權重": "10%", "收益": "+12.3%"},
        {"股票": "MSFT", "數量": "75", "市值": "$22,500",
         "權重": "18%", "收益": "+6.8%"},
        {"股票": "TSLA", "數量": "25", "市值": "$5,000",
         "權重": "4%", "收益": "-2.1%"}
    ]

    for holding in holdings:
        with st.expander(f"{holding['股票']} - 權重: {holding['權重']}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**數量**: {holding['數量']}")
                st.write(f"**市值**: {holding['市值']}")
            with col2:
                st.write(f"**權重**: {holding['權重']}")
                st.write(f"**收益**: {holding['收益']}")
            with col3:
                if st.button("調整", key=f"adjust_{holding['股票']}"):
                    st.info(f"{holding['股票']} 調整功能開發中...")
    
    # 再平衡建議
    st.markdown("### ⚖️ 再平衡建議")

    rebalance_suggestions = [
        {"操作": "減持", "股票": "MSFT", "建議": "減持3%", "原因": "權重超配"},
        {"操作": "增持", "股票": "債券ETF", "建議": "增持5%", "原因": "債券配置不足"},
        {"操作": "保持", "股票": "AAPL", "建議": "維持現狀", "原因": "配置合理"}
    ]

    for suggestion in rebalance_suggestions:
        action_color = ("🔴" if suggestion["操作"] == "減持" else
                       "🟢" if suggestion["操作"] == "增持" else "🟡")
        st.markdown(f"{action_color} **{suggestion['操作']} {suggestion['股票']}**: "
                   f"{suggestion['建議']} - {suggestion['原因']}")


def _show_fallback_text_analysis() -> None:
    """文本分析的備用顯示函數.

    當原有的文本分析頁面無法載入時，顯示基本的功能說明。
    """
    st.info("📝 文本分析功能正在載入中...")

    st.markdown("""
    **文本分析系統** 提供市場情緒和文本分析功能，包括：
    - 📰 **新聞分析**: 財經新聞情感分析和關鍵信息提取
    - 📊 **情緒指標**: 市場情緒指標和投資者情緒分析
    - 🔍 **關鍵詞追蹤**: 關鍵詞和話題趨勢追蹤
    - 📈 **影響評估**: 新聞事件對股價的影響評估
    - 🎯 **投資信號**: 基於文本分析的投資信號生成
    """)

    # 顯示情緒分析概覽
    st.markdown("### 📊 市場情緒概覽")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("整體情緒", "樂觀", "📈")

    with col2:
        st.metric("情緒指數", "72", "+5")

    with col3:
        st.metric("新聞數量", "156", "+23")

    with col4:
        st.metric("關鍵事件", "3", "+1")
    
    # 顯示新聞分析
    st.markdown("### 📰 最新新聞分析")

    news_analysis = [
        {
            "標題": "科技股強勢反彈，AI概念股領漲",
            "情緒": "🟢 正面",
            "影響": "高",
            "相關股票": "NVDA, GOOGL, MSFT",
            "信心度": "85%"
        },
        {
            "標題": "聯準會暗示可能暫停升息",
            "情緒": "🟢 正面",
            "影響": "中",
            "相關股票": "整體市場",
            "信心度": "78%"
        },
        {
            "標題": "能源價格上漲引發通脹擔憂",
            "情緒": "🔴 負面",
            "影響": "中",
            "相關股票": "XOM, CVX",
            "信心度": "72%"
        }
    ]

    for news in news_analysis:
        with st.expander(f"{news['情緒']} {news['標題']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**情緒**: {news['情緒']}")
                st.write(f"**影響程度**: {news['影響']}")
            with col2:
                st.write(f"**相關股票**: {news['相關股票']}")
                st.write(f"**信心度**: {news['信心度']}")
    
    # 顯示關鍵詞追蹤
    st.markdown("### 🔍 熱門關鍵詞")

    keywords = [
        {"關鍵詞": "人工智能", "提及次數": "89", "趨勢": "📈 上升"},
        {"關鍵詞": "升息", "提及次數": "67", "趨勢": "📉 下降"},
        {"關鍵詞": "通脹", "提及次數": "45", "趨勢": "📈 上升"},
        {"關鍵詞": "財報", "提及次數": "34", "趨勢": "➡️ 持平"}
    ]

    for keyword in keywords:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**{keyword['關鍵詞']}**")
        with col2:
            st.write(f"提及: {keyword['提及次數']}次")
        with col3:
            st.write(f"{keyword['趨勢']}")

    # 投資信號
    st.markdown("### 🎯 基於文本的投資信號")

    signals = [
        {"信號": "買入", "股票": "NVDA", "強度": "強", "原因": "AI相關正面新聞增加"},
        {"信號": "觀望", "股票": "銀行股", "強度": "中", "原因": "升息預期不明確"},
        {"信號": "減持", "股票": "能源股", "強度": "弱", "原因": "環保政策負面影響"}
    ]

    for signal in signals:
        signal_color = ("🟢" if signal["信號"] == "買入" else
                       "🟡" if signal["信號"] == "觀望" else "🔴")
        st.markdown(f"{signal_color} **{signal['信號']} {signal['股票']}** "
                   f"(強度: {signal['強度']}) - {signal['原因']}")


# 輔助函數
def get_portfolio_status() -> dict:
    """獲取投資組合狀態信息.

    Returns:
        dict: 包含投資組合狀態的字典

    Example:
        >>> status = get_portfolio_status()
        >>> print(status['total_value'])
        125430
    """
    return {
        'total_value': 125430,
        'holdings_count': 12,
        'annual_return': 12.5,
        'sharpe_ratio': 1.35
    }


def validate_portfolio_config(config: dict) -> bool:
    """驗證投資組合配置.

    Args:
        config: 投資組合配置字典

    Returns:
        bool: 配置是否有效

    Example:
        >>> config = {'stocks': 70, 'bonds': 20, 'cash': 10}
        >>> is_valid = validate_portfolio_config(config)
        >>> print(is_valid)
        True
    """
    required_fields = ['stocks', 'bonds', 'cash']
    if not all(field in config for field in required_fields):
        return False

    # 檢查配置比例總和是否為100%
    total = sum(config[field] for field in required_fields)
    return abs(total - 100) < 0.01
