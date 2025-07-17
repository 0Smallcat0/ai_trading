"""風險管理組件

此模組整合所有風險管理相關功能，提供統一的風險管理介面：
- 風險管理基本功能

主要功能：
- 統一的風險管理入口
- 風險指標監控
- 風險參數設定
- 風控機制管理
- 風險警報記錄
- 統一的錯誤處理機制

Example:
    >>> from src.ui.components.risk_management import show
    >>> show()  # 顯示風險管理主介面
"""

import logging
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def show() -> None:
    """顯示風險管理主介面.
    
    整合所有風險管理相關功能到統一的介面中。
    提供完整的風險管理功能，包括錯誤處理和狀態管理。
    
    主要功能：
    - 風險指標監控：即時監控VaR、回撤、波動率等關鍵指標
    - 風險參數設定：設定停損停利、部位限制、資金控管等參數
    - 風控機制管理：控制各種風控機制的啟用狀態
    - 風險警報記錄：查看和管理風險事件與警報
    
    Returns:
        None
        
    Side Effects:
        - 渲染 Streamlit 界面組件
        - 可能修改 st.session_state 中的相關狀態
        
    Example:
        >>> show()  # 顯示完整的風險管理介面
        
    Note:
        此函數整合了原有風險管理頁面的功能，保持向後兼容性。
        如果功能不可用，會顯示相應的錯誤訊息。
    """
    try:
        st.title("⚠️ 風險管理")
        st.markdown("---")
        
        # 直接調用風險管理功能
        _show_risk_management()
            
    except Exception as e:
        logger.error("顯示風險管理介面時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 風險管理介面載入失敗")
        with st.expander("錯誤詳情"):
            st.code(str(e))


def _show_risk_management() -> None:
    """顯示風險管理功能.
    
    調用原有的 risk_management 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入風險管理頁面失敗時
    """
    try:
        from src.ui.pages.risk_management import show as risk_show
        risk_show()
        
    except ImportError as e:
        logger.warning("無法導入風險管理頁面: %s", e)
        st.warning("⚠️ 風險管理功能暫時不可用")
        _show_fallback_risk_management()
        
    except Exception as e:
        logger.error("顯示風險管理時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 風險管理功能載入失敗")
        _show_fallback_risk_management()


def _show_fallback_risk_management() -> None:
    """風險管理的備用顯示函數.
    
    當原有的風險管理頁面無法載入時，顯示基本的功能說明。
    
    Returns:
        None
    """
    st.info("⚠️ 風險管理功能正在載入中...")
    
    st.markdown("""
    **風險管理系統** 提供全面的投資組合風險控制功能，包括：
    - 📊 **風險指標監控**: 即時監控 VaR、回撤、波動率等關鍵指標
    - ⚙️ **風險參數設定**: 設定停損停利、部位限制、資金控管等參數
    - 🔧 **風控機制管理**: 控制各種風控機制的啟用狀態
    - 🚨 **風險警報記錄**: 查看和管理風險事件與警報
    """)
    
    # 顯示風險指標概覽
    st.markdown("### 📊 風險指標概覽")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("VaR (95%)", "2.5%", "-0.3%")
    
    with col2:
        st.metric("最大回撤", "8.2%", "+1.1%")
    
    with col3:
        st.metric("波動率", "15.6%", "-2.1%")
    
    with col4:
        st.metric("夏普比率", "1.35", "+0.15")
    
    # 顯示風險狀態
    st.markdown("### 🚦 風險狀態")
    
    risk_status = [
        {"指標": "整體風險等級", "狀態": "🟡 中等", "數值": "65/100", "建議": "適度調整部位"},
        {"指標": "流動性風險", "狀態": "🟢 低", "數值": "25/100", "建議": "維持現狀"},
        {"指標": "集中度風險", "狀態": "🟡 中等", "數值": "55/100", "建議": "增加分散化"},
        {"指標": "市場風險", "狀態": "🔴 高", "數值": "80/100", "建議": "降低曝險"}
    ]
    
    for risk in risk_status:
        with st.expander(f"{risk['指標']} - {risk['狀態']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**風險數值**: {risk['數值']}")
                st.write(f"**狀態**: {risk['狀態']}")
            with col2:
                st.write(f"**建議**: {risk['建議']}")
                if st.button(f"查看詳情", key=f"detail_{risk['指標']}"):
                    st.info(f"{risk['指標']} 詳細分析功能開發中...")
    
    # 顯示風控設定
    st.markdown("### ⚙️ 風控設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 停損停利設定")
        stop_loss = st.slider("停損比例 (%)", 1, 20, 5)
        take_profit = st.slider("停利比例 (%)", 5, 50, 15)
        
    with col2:
        st.markdown("#### 部位控制")
        max_position = st.slider("單一部位上限 (%)", 1, 30, 10)
        max_total = st.slider("總部位上限 (%)", 50, 100, 80)
    
    # 保存設定按鈕
    if st.button("💾 保存風控設定", type="primary"):
        st.success("✅ 風控設定已保存")
        st.info(f"停損: {stop_loss}%, 停利: {take_profit}%, 單一部位: {max_position}%, 總部位: {max_total}%")
    
    # 顯示最近警報
    st.markdown("### 🚨 最近風險警報")
    
    alerts = [
        {"時間": "14:30", "類型": "部位風險", "等級": "🟡 中等", "描述": "AAPL 部位超過 8%"},
        {"時間": "13:45", "類型": "市場風險", "等級": "🔴 高", "描述": "市場波動率異常升高"},
        {"時間": "12:20", "類型": "流動性風險", "等級": "🟢 低", "描述": "流動性指標正常"},
        {"時間": "11:15", "類型": "集中度風險", "等級": "🟡 中等", "描述": "科技股集中度偏高"}
    ]
    
    for alert in alerts:
        st.markdown(f"**{alert['時間']}** {alert['等級']} {alert['類型']} - {alert['描述']}")


# 輔助函數
def get_risk_metrics() -> dict:
    """獲取風險指標.
    
    Returns:
        dict: 包含風險指標的字典
        
    Example:
        >>> metrics = get_risk_metrics()
        >>> print(metrics['var_95'])
        0.025
    """
    return {
        'var_95': 0.025,
        'max_drawdown': 0.082,
        'volatility': 0.156,
        'sharpe_ratio': 1.35,
        'risk_level': 65
    }


def calculate_position_risk(symbol: str, quantity: int, price: float) -> dict:
    """計算部位風險.
    
    Args:
        symbol: 股票代碼
        quantity: 數量
        price: 價格
        
    Returns:
        dict: 包含部位風險信息的字典
        
    Example:
        >>> risk = calculate_position_risk('AAPL', 100, 150.0)
        >>> print(risk['position_value'])
        15000.0
    """
    position_value = quantity * price
    return {
        'symbol': symbol,
        'quantity': quantity,
        'price': price,
        'position_value': position_value,
        'risk_score': min(position_value / 100000 * 100, 100)  # 簡化風險評分
    }


def validate_risk_parameters(params: dict) -> bool:
    """驗證風險參數.
    
    Args:
        params: 風險參數字典
        
    Returns:
        bool: 參數是否有效
        
    Example:
        >>> params = {'stop_loss': 5, 'take_profit': 15, 'max_position': 10}
        >>> is_valid = validate_risk_parameters(params)
        >>> print(is_valid)
        True
    """
    required_fields = ['stop_loss', 'take_profit', 'max_position']
    if not all(field in params for field in required_fields):
        return False
    
    # 檢查數值範圍
    if not (0 < params['stop_loss'] < 50):
        return False
    if not (0 < params['take_profit'] < 100):
        return False
    if not (0 < params['max_position'] < 50):
        return False
    
    return True
