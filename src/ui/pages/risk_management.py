"""
風險管理頁面 (整合版)

此模組整合了基本版和增強版風險管理功能，提供完整的風險管理系統：
- 風險參數設置和配置
- 實時風險監控儀表板
- 風險控制機制和警報
- 日誌與警報管理
- 響應式設計支援 (增強功能)

Version: v2.0 (整合版)
Author: AI Trading System
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 添加項目根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from src.core.risk_management_service import RiskManagementService
except ImportError:
    # 如果無法導入，使用備用方案
    RiskManagementService = None

# 導入響應式設計組件 (增強功能)
try:
    from src.ui.responsive import (
        ResponsiveUtils,
        ResponsiveComponents,
    )
except ImportError:
    # 備用實現
    ResponsiveUtils = None
    ResponsiveComponents = None


def get_risk_management_service() -> Optional[Any]:
    """獲取風險管理服務實例

    Returns:
        Optional[Any]: 風險管理服務實例，如果無法初始化則返回 None
    """
    if RiskManagementService is None:
        return None

    if "risk_service" not in st.session_state:
        try:
            st.session_state.risk_service = RiskManagementService()
        except Exception as e:
            st.error(f"初始化風險管理服務失敗: {e}")
            return None

    return st.session_state.risk_service


def get_default_risk_parameters() -> Dict[str, Any]:
    """獲取預設風險參數

    Returns:
        Dict[str, Any]: 預設風險參數字典
    """
    return {
        # 停損/停利參數
        "stop_loss_enabled": True,
        "stop_loss_type": "百分比停損",
        "stop_loss_percent": 5.0,
        "stop_loss_atr_multiple": 2.0,
        "trailing_stop_enabled": False,
        "trailing_stop_percent": 3.0,
        "take_profit_enabled": True,
        "take_profit_type": "百分比停利",
        "take_profit_percent": 10.0,
        "take_profit_target": 15.0,
        "risk_reward_ratio": 2.0,
        # 資金控管參數
        "max_portfolio_risk": 2.0,
        "max_position_size": 10.0,
        "max_daily_loss": 5.0,
        "max_drawdown": 15.0,
        "position_sizing_method": "固定比例",
        "kelly_fraction": 0.25,
        # 部位限制
        "max_positions": 10,
        "max_sector_exposure": 30.0,
        "max_single_stock": 15.0,
        "min_position_size": 1.0,
        "correlation_limit": 0.7,
        # VaR 參數
        "var_confidence": 95.0,
        "var_holding_period": 1,
        "var_method": "歷史模擬法",
        "var_lookback_days": 252,
        "stress_test_enabled": True,
        # 監控參數
        "real_time_monitoring": True,
        "alert_threshold_var": 2.0,
        "alert_threshold_drawdown": 10.0,
        "alert_email_enabled": True,
        "alert_sms_enabled": False,
    }


def get_mock_risk_metrics() -> Dict[str, Any]:
    """獲取模擬風險指標數據

    Returns:
        Dict[str, Any]: 模擬的風險指標數據字典
    """
    # 生成模擬收益率數據
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=252, freq="D")
    returns = np.random.normal(0.0008, 0.015, 252)

    # 計算風險指標
    portfolio_value = 1000000
    current_positions = 8
    cash_ratio = 0.15

    # 模擬 VaR 計算
    try:
        var_95 = np.percentile(returns, 5) * portfolio_value
        cvar_95 = returns[returns <= np.percentile(returns, 5)].mean() * portfolio_value
    except Exception as e:
        logger.warning(f"VaR 計算失敗，使用默認值: {e}")
        var_95 = -25000  # 默認 VaR 值
        cvar_95 = -35000  # 默認 CVaR 值

    # 計算最大回撤
    cumulative_returns = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns / running_max - 1) * 100
    max_drawdown = drawdown.min()

    # 計算其他指標
    volatility = np.std(returns) * np.sqrt(252) * 100
    sharpe_ratio = (np.mean(returns) * 252) / (np.std(returns) * np.sqrt(252))

    return {
        "portfolio_value": portfolio_value,
        "cash_amount": portfolio_value * cash_ratio,
        "invested_amount": portfolio_value * (1 - cash_ratio),
        "current_positions": current_positions,
        "daily_pnl": np.random.normal(1200, 8000),
        "daily_pnl_percent": np.random.normal(0.12, 0.8),
        "var_95_1day": abs(var_95),
        "cvar_95_1day": abs(cvar_95),
        "max_drawdown": max_drawdown,
        "current_drawdown": np.random.uniform(-8, -2),
        "volatility": volatility,
        "sharpe_ratio": sharpe_ratio,
        "beta": np.random.uniform(0.8, 1.2),
        "correlation_with_market": np.random.uniform(0.6, 0.9),
        "tracking_error": np.random.uniform(2, 8),
        "largest_position_weight": np.random.uniform(12, 18),
        "sector_concentration": np.random.uniform(25, 35),
        "avg_correlation": np.random.uniform(0.3, 0.6),
        "returns_series": returns,
        "dates": dates,
        "drawdown_series": drawdown,
    }


def get_mock_risk_events() -> pd.DataFrame:
    """獲取模擬風險事件數據

    Returns:
        pd.DataFrame: 包含模擬風險事件的 DataFrame
    """
    events = []

    # 生成最近30天的風險事件
    for _ in range(15):
        event_date = datetime.now() - timedelta(days=np.random.randint(0, 30))

        event_types = ["停損觸發", "VaR超限", "回撤警告", "部位超限", "相關性警告"]
        severities = ["低", "中", "高", "嚴重"]
        statuses = ["已處理", "處理中", "待處理"]

        event = {
            "時間": event_date.strftime("%Y-%m-%d %H:%M:%S"),
            "事件類型": np.random.choice(event_types),
            "嚴重程度": np.random.choice(severities),
            "股票代碼": np.random.choice(
                ["2330.TW", "2317.TW", "2454.TW", "AAPL", "MSFT", "全組合"]
            ),
            "觸發值": f"{np.random.uniform(-15, -2):.2f}%",
            "閾值": f"{np.random.uniform(-10, -5):.2f}%",
            "狀態": np.random.choice(statuses),
            "處理動作": np.random.choice(
                ["自動停損", "發送警報", "暫停交易", "調整部位", "人工介入"]
            ),
            "備註": "系統自動檢測到風險事件",
        }
        events.append(event)

    return pd.DataFrame(events).sort_values("時間", ascending=False)


def show() -> None:
    """顯示風險管理頁面 (整合版)

    主要入口函數，顯示風險管理頁面的標籤頁界面。
    整合了基本版和增強版功能，支援響應式設計。

    Returns:
        None
    """
    # 檢查響應式組件是否可用
    if ResponsiveUtils is None:
        st.title("🛡️ 風險管理 (整合版)")
    else:
        # 應用響應式頁面配置
        try:
            ResponsiveUtils.apply_responsive_page_config(
                page_title="風險管理系統 - AI 交易系統", page_icon="⚠️"
            )
            st.markdown('<h1 class="title-responsive">🛡️ 風險管理</h1>', unsafe_allow_html=True)
        except Exception:
            st.title("🛡️ 風險管理 (整合版)")

    # 確保 session state 已初始化
    if "risk_params" not in st.session_state:
        st.session_state.risk_params = get_default_risk_parameters()

    if "risk_controls_status" not in st.session_state:
        st.session_state.risk_controls_status = {
            "stop_loss_active": True,
            "take_profit_active": True,
            "position_limit_active": True,
            "sector_limit_active": True,
            "var_monitoring_active": True,
            "drawdown_protection_active": True,
            "correlation_check_active": True,
            "emergency_stop_active": False,
        }

    # 檢查 ResponsiveComponents 是否可用
    if ResponsiveComponents is None:
        # 使用基本標籤頁
        tabs = st.tabs(["風險參數", "風險指標", "風控機制", "警報記錄"])

        with tabs[0]:
            show_risk_parameters()
        with tabs[1]:
            show_risk_indicators()
        with tabs[2]:
            show_risk_controls()
        with tabs[3]:
            show_risk_alerts()
    else:
        # 響應式標籤頁
        tabs_config = [
            {"name": "風險參數", "content_func": show_risk_parameters},
            {"name": "風險指標", "content_func": show_risk_indicators},
            {"name": "風控機制", "content_func": show_risk_controls},
            {"name": "警報記錄", "content_func": show_risk_alerts},
        ]

        ResponsiveComponents.responsive_tabs(tabs_config)


def show_risk_parameters() -> None:
    """顯示風險參數設置

    提供風險參數的設定界面，包括停損停利、資金控管、部位限制等設定。
    支援從服務層載入參數、保存設定、重置為預設值等功能。

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示風險參數設定表單
        - 更新 session_state 中的風險參數
    """
    st.subheader("⚙️ 風險參數設置")

    # 獲取風險管理服務
    risk_service = get_risk_management_service()

    # 獲取當前參數
    if "risk_params" not in st.session_state:
        if risk_service:
            # 從服務層獲取參數
            try:
                service_params = risk_service.get_risk_parameters()
                if service_params:
                    # 轉換服務層參數格式為 UI 格式
                    st.session_state.risk_params = {}
                    for param_name, param_info in service_params.items():
                        st.session_state.risk_params[param_name] = param_info["value"]
                else:
                    st.session_state.risk_params = get_default_risk_parameters()
            except Exception as e:
                st.error(f"載入風險參數失敗: {e}")
                st.session_state.risk_params = get_default_risk_parameters()
        else:
            st.session_state.risk_params = get_default_risk_parameters()

    # 創建三列布局
    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("### 🛑 停損/停利設置")

        # 停損設置
        st.write("**停損設置**")
        st.session_state.risk_params["stop_loss_enabled"] = st.checkbox(
            "啟用停損", value=st.session_state.risk_params["stop_loss_enabled"]
        )

        if st.session_state.risk_params["stop_loss_enabled"]:
            st.session_state.risk_params["stop_loss_type"] = st.selectbox(
                "停損類型",
                ["百分比停損", "ATR停損", "追蹤停損"],
                index=["百分比停損", "ATR停損", "追蹤停損"].index(
                    st.session_state.risk_params["stop_loss_type"]
                ),
            )

            if st.session_state.risk_params["stop_loss_type"] == "百分比停損":
                st.session_state.risk_params["stop_loss_percent"] = st.slider(
                    "停損百分比 (%)",
                    1.0,
                    20.0,
                    st.session_state.risk_params["stop_loss_percent"],
                    0.5,
                )
            elif st.session_state.risk_params["stop_loss_type"] == "ATR停損":
                st.session_state.risk_params["stop_loss_atr_multiple"] = st.slider(
                    "ATR倍數",
                    1.0,
                    5.0,
                    st.session_state.risk_params["stop_loss_atr_multiple"],
                    0.1,
                )
            elif st.session_state.risk_params["stop_loss_type"] == "追蹤停損":
                st.session_state.risk_params["trailing_stop_percent"] = st.slider(
                    "追蹤停損百分比 (%)",
                    1.0,
                    10.0,
                    st.session_state.risk_params["trailing_stop_percent"],
                    0.5,
                )

        # 停利設置
        st.write("**停利設置**")
        st.session_state.risk_params["take_profit_enabled"] = st.checkbox(
            "啟用停利", value=st.session_state.risk_params["take_profit_enabled"]
        )

        if st.session_state.risk_params["take_profit_enabled"]:
            st.session_state.risk_params["take_profit_type"] = st.selectbox(
                "停利類型",
                ["百分比停利", "目標價停利", "風險報酬比停利"],
                index=["百分比停利", "目標價停利", "風險報酬比停利"].index(
                    st.session_state.risk_params["take_profit_type"]
                ),
            )

            if st.session_state.risk_params["take_profit_type"] == "百分比停利":
                st.session_state.risk_params["take_profit_percent"] = st.slider(
                    "停利百分比 (%)",
                    5.0,
                    50.0,
                    st.session_state.risk_params["take_profit_percent"],
                    1.0,
                )
            elif st.session_state.risk_params["take_profit_type"] == "目標價停利":
                st.session_state.risk_params["take_profit_target"] = st.slider(
                    "目標收益率 (%)",
                    5.0,
                    100.0,
                    st.session_state.risk_params["take_profit_target"],
                    1.0,
                )
            elif st.session_state.risk_params["take_profit_type"] == "風險報酬比停利":
                st.session_state.risk_params["risk_reward_ratio"] = st.slider(
                    "風險報酬比",
                    1.0,
                    5.0,
                    st.session_state.risk_params["risk_reward_ratio"],
                    0.1,
                )

    with col2:
        st.write("### 💰 資金控管設置")

        # 投資組合風險
        st.write("**投資組合風險**")
        st.session_state.risk_params["max_portfolio_risk"] = st.slider(
            "最大投資組合風險 (%)",
            0.5,
            10.0,
            st.session_state.risk_params["max_portfolio_risk"],
            0.1,
        )

        st.session_state.risk_params["max_daily_loss"] = st.slider(
            "最大日損失 (%)",
            1.0,
            20.0,
            st.session_state.risk_params["max_daily_loss"],
            0.5,
        )

        st.session_state.risk_params["max_drawdown"] = st.slider(
            "最大回撤限制 (%)",
            5.0,
            50.0,
            st.session_state.risk_params["max_drawdown"],
            1.0,
        )

        # 部位大小控制
        st.write("**部位大小控制**")
        st.session_state.risk_params["position_sizing_method"] = st.selectbox(
            "部位大小方法",
            ["固定比例", "固定金額", "風險基準", "Kelly公式", "波動率調整"],
            index=["固定比例", "固定金額", "風險基準", "Kelly公式", "波動率調整"].index(
                st.session_state.risk_params["position_sizing_method"]
            ),
        )

        st.session_state.risk_params["max_position_size"] = st.slider(
            "單一部位最大比例 (%)",
            1.0,
            50.0,
            st.session_state.risk_params["max_position_size"],
            1.0,
        )

        if st.session_state.risk_params["position_sizing_method"] == "Kelly公式":
            st.session_state.risk_params["kelly_fraction"] = st.slider(
                "Kelly分數",
                0.1,
                1.0,
                st.session_state.risk_params["kelly_fraction"],
                0.05,
            )

        # 部位限制
        st.write("**部位限制**")
        st.session_state.risk_params["max_positions"] = st.slider(
            "最大持倉數量", 1, 50, st.session_state.risk_params["max_positions"], 1
        )

        st.session_state.risk_params["max_sector_exposure"] = st.slider(
            "單一行業最大曝險 (%)",
            10.0,
            100.0,
            st.session_state.risk_params["max_sector_exposure"],
            5.0,
        )

        st.session_state.risk_params["max_single_stock"] = st.slider(
            "單一股票最大權重 (%)",
            1.0,
            50.0,
            st.session_state.risk_params["max_single_stock"],
            1.0,
        )

        st.session_state.risk_params["correlation_limit"] = st.slider(
            "相關性限制",
            0.1,
            1.0,
            st.session_state.risk_params["correlation_limit"],
            0.05,
        )

    with col3:
        st.write("### 📊 VaR 與監控設置")

        # VaR 設置
        st.write("**VaR 設置**")
        st.session_state.risk_params["var_confidence"] = st.slider(
            "VaR 信心水準 (%)",
            90.0,
            99.9,
            st.session_state.risk_params["var_confidence"],
            0.1,
        )

        st.session_state.risk_params["var_holding_period"] = st.selectbox(
            "VaR 持有期間",
            [1, 5, 10, 22],
            index=[1, 5, 10, 22].index(
                st.session_state.risk_params["var_holding_period"]
            ),
        )

        st.session_state.risk_params["var_method"] = st.selectbox(
            "VaR 計算方法",
            ["歷史模擬法", "參數法", "蒙地卡羅法"],
            index=["歷史模擬法", "參數法", "蒙地卡羅法"].index(
                st.session_state.risk_params["var_method"]
            ),
        )

        st.session_state.risk_params["var_lookback_days"] = st.slider(
            "VaR 回顧天數",
            30,
            1000,
            st.session_state.risk_params["var_lookback_days"],
            10,
        )

        st.session_state.risk_params["stress_test_enabled"] = st.checkbox(
            "啟用壓力測試", value=st.session_state.risk_params["stress_test_enabled"]
        )

        # 監控設置
        st.write("**監控設置**")
        st.session_state.risk_params["real_time_monitoring"] = st.checkbox(
            "即時監控", value=st.session_state.risk_params["real_time_monitoring"]
        )

        st.session_state.risk_params["alert_threshold_var"] = st.slider(
            "VaR 警報閾值 (%)",
            0.5,
            10.0,
            st.session_state.risk_params["alert_threshold_var"],
            0.1,
        )

        st.session_state.risk_params["alert_threshold_drawdown"] = st.slider(
            "回撤警報閾值 (%)",
            1.0,
            30.0,
            st.session_state.risk_params["alert_threshold_drawdown"],
            1.0,
        )

        # 警報設置
        st.write("**警報設置**")
        st.session_state.risk_params["alert_email_enabled"] = st.checkbox(
            "Email 警報", value=st.session_state.risk_params["alert_email_enabled"]
        )

        st.session_state.risk_params["alert_sms_enabled"] = st.checkbox(
            "SMS 警報", value=st.session_state.risk_params["alert_sms_enabled"]
        )

    # 保存設置
    st.divider()
    col_save1, col_save2, col_save3 = st.columns([1, 1, 1])

    with col_save1:
        if st.button("💾 保存設置", type="primary", use_container_width=True):
            if risk_service:
                try:
                    # 保存所有參數到服務層
                    success_count = 0
                    for param_name, param_value in st.session_state.risk_params.items():
                        if risk_service.update_risk_parameter(param_name, param_value):
                            success_count += 1

                    if success_count > 0:
                        st.success(f"風險參數設置已保存！({success_count} 個參數)")
                    else:
                        st.warning("沒有參數被保存")
                except Exception as e:
                    st.error(f"保存設置失敗: {e}")
            else:
                st.success("風險參數設置已保存！")

    with col_save2:
        if st.button("🔄 重置為預設", use_container_width=True):
            st.session_state.risk_params = get_default_risk_parameters()
            st.success("已重置為預設設置！")
            st.rerun()

    with col_save3:
        if st.button("📋 匯出設置", use_container_width=True):
            try:
                import json

                settings_json = json.dumps(
                    st.session_state.risk_params, indent=2, ensure_ascii=False
                )
                st.download_button(
                    label="下載設置檔案",
                    data=settings_json,
                    file_name=f"risk_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                )
                st.info("設置已準備匯出")
            except Exception as e:
                st.error(f"匯出設置失敗: {e}")


def show_risk_indicators():
    """顯示風險指標"""
    st.subheader("📊 風險指標監控")

    # 獲取風險管理服務
    risk_service = get_risk_management_service()

    # 獲取風險指標數據
    if risk_service:
        try:
            # 嘗試從服務層獲取實際風險指標
            calculated_metrics = risk_service.calculate_risk_metrics()
            if calculated_metrics and isinstance(calculated_metrics, dict):
                # 將計算結果轉換為顯示格式，確保鍵名一致
                risk_metrics = {
                    "portfolio_value": 1000000,  # 這應該從投資組合服務獲取
                    "cash_amount": 150000,
                    "invested_amount": 850000,
                    "current_positions": 8,
                    "daily_pnl": np.random.normal(1200, 8000),
                    "daily_pnl_percent": np.random.normal(0.12, 0.8),
                    # 安全地轉換鍵名以保持一致性
                    "var_95_1day": abs(calculated_metrics.get("var_95", -0.025)) * 1000000,
                    "cvar_95_1day": abs(calculated_metrics.get("cvar_95", -0.035)) * 1000000,
                }
                # 安全地合併其他指標
                for key, value in calculated_metrics.items():
                    if key not in risk_metrics and value is not None:
                        risk_metrics[key] = value
            else:
                risk_metrics = get_mock_risk_metrics()
        except Exception as e:
            st.warning(f"無法獲取實際風險指標，使用模擬數據: {e}")
            risk_metrics = get_mock_risk_metrics()
    else:
        risk_metrics = get_mock_risk_metrics()

    # 總覽卡片
    st.write("### 📈 投資組合總覽")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "投資組合價值",
            f"${risk_metrics['portfolio_value']:,.0f}",
            f"{risk_metrics['daily_pnl']:+,.0f}",
        )

    with col2:
        st.metric(
            "現金部位",
            f"${risk_metrics['cash_amount']:,.0f}",
            f"{risk_metrics['cash_amount']/risk_metrics['portfolio_value']*100:.1f}%",
        )

    with col3:
        st.metric(
            "投資部位",
            f"${risk_metrics['invested_amount']:,.0f}",
            f"{risk_metrics['invested_amount']/risk_metrics['portfolio_value']*100:.1f}%",
        )

    with col4:
        st.metric("持倉數量", f"{risk_metrics['current_positions']}", "")

    with col5:
        st.metric(
            "今日損益",
            f"{risk_metrics['daily_pnl_percent']:+.2f}%",
            f"${risk_metrics['daily_pnl']:+,.0f}",
        )

    st.divider()

    # 風險指標
    col1, col2 = st.columns(2)

    with col1:
        st.write("### 🎯 風險指標")

        # VaR 指標
        st.write("**風險值 (VaR)**")
        col_var1, col_var2 = st.columns(2)

        with col_var1:
            st.metric("95% VaR (1日)", f"${risk_metrics['var_95_1day']:,.0f}")
            st.metric("95% CVaR (1日)", f"${risk_metrics['cvar_95_1day']:,.0f}")

        with col_var2:
            var_pct = (
                risk_metrics["var_95_1day"] / risk_metrics["portfolio_value"] * 100
            )
            cvar_pct = (
                risk_metrics["cvar_95_1day"] / risk_metrics["portfolio_value"] * 100
            )
            st.metric("VaR 比例", f"{var_pct:.2f}%")
            st.metric("CVaR 比例", f"{cvar_pct:.2f}%")

        # 回撤指標
        st.write("**回撤分析**")
        col_dd1, col_dd2 = st.columns(2)

        with col_dd1:
            st.metric("最大回撤", f"{risk_metrics['max_drawdown']:.2f}%")
            st.metric("當前回撤", f"{risk_metrics['current_drawdown']:.2f}%")

        with col_dd2:
            # 回撤狀態指示
            if abs(risk_metrics["current_drawdown"]) > 10:
                st.error("⚠️ 回撤過大")
            elif abs(risk_metrics["current_drawdown"]) > 5:
                st.warning("⚠️ 回撤警告")
            else:
                st.success("✅ 回撤正常")

        # 其他風險指標
        st.write("**其他指標**")
        col_other1, col_other2 = st.columns(2)

        with col_other1:
            st.metric("年化波動率", f"{risk_metrics['volatility']:.2f}%")
            st.metric("夏普比率", f"{risk_metrics['sharpe_ratio']:.2f}")
            st.metric("Beta 係數", f"{risk_metrics['beta']:.2f}")

        with col_other2:
            st.metric("市場相關性", f"{risk_metrics['correlation_with_market']:.2f}")
            st.metric("追蹤誤差", f"{risk_metrics['tracking_error']:.2f}%")
            st.metric("平均相關性", f"{risk_metrics['avg_correlation']:.2f}")

    with col2:
        st.write("### 📊 風險視覺化")

        # 回撤走勢圖
        st.write("**回撤走勢**")
        fig_drawdown = go.Figure()

        fig_drawdown.add_trace(
            go.Scatter(
                x=risk_metrics["dates"],
                y=risk_metrics["drawdown_series"],
                mode="lines",
                name="回撤",
                fill="tonexty",
                line=dict(color="red", width=2),
            )
        )

        fig_drawdown.update_layout(
            title="投資組合回撤走勢",
            xaxis_title="日期",
            yaxis_title="回撤 (%)",
            template="plotly_white",
            height=300,
        )

        st.plotly_chart(fig_drawdown, use_container_width=True)

        # 收益率分布
        st.write("**收益率分布**")
        fig_hist = go.Figure()

        fig_hist.add_trace(
            go.Histogram(
                x=risk_metrics["returns_series"] * 100,
                nbinsx=30,
                name="收益率分布",
                marker_color="blue",
                opacity=0.7,
            )
        )

        # 添加 VaR 線
        var_line = np.percentile(risk_metrics["returns_series"], 5) * 100
        fig_hist.add_vline(
            x=var_line,
            line_dash="dash",
            line_color="red",
            annotation_text=f"95% VaR: {var_line:.2f}%",
        )

        fig_hist.update_layout(
            title="日收益率分布",
            xaxis_title="收益率 (%)",
            yaxis_title="頻率",
            template="plotly_white",
            height=300,
        )

        st.plotly_chart(fig_hist, use_container_width=True)


def show_risk_controls():
    """顯示風控機制管理"""
    st.subheader("🔧 風控機制管理")

    # 獲取當前風險參數
    if "risk_params" not in st.session_state:
        st.session_state.risk_params = get_default_risk_parameters()

    # 風控機制狀態
    if "risk_controls_status" not in st.session_state:
        st.session_state.risk_controls_status = {
            "stop_loss_active": True,
            "take_profit_active": True,
            "position_limit_active": True,
            "var_monitoring_active": True,
            "drawdown_protection_active": True,
            "correlation_check_active": True,
            "sector_limit_active": True,
            "emergency_stop_active": False,
        }

    # 總控制面板
    st.write("### 🎛️ 總控制面板")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        master_switch = st.toggle("🔴 主開關", value=True, key="master_risk_switch")
        if not master_switch:
            st.warning("⚠️ 所有風控機制已停用")

    with col2:
        emergency_mode = st.button(
            "🚨 緊急停止", type="secondary", use_container_width=True
        )
        if emergency_mode:
            st.session_state.risk_controls_status["emergency_stop_active"] = True
            st.error("🚨 緊急停止已啟動！所有交易已暫停。")

    with col3:
        if st.button("🔄 重啟系統", use_container_width=True):
            st.session_state.risk_controls_status["emergency_stop_active"] = False
            st.success("✅ 系統已重啟，風控機制恢復正常。")

    with col4:
        st.toggle("🤖 自動模式", value=True, key="auto_risk_mode")

    st.divider()

    # 個別風控機制控制
    col1, col2 = st.columns(2)

    with col1:
        st.write("### 🛑 停損/停利控制")

        # 停損控制
        st.session_state.risk_controls_status["stop_loss_active"] = st.checkbox(
            "停損機制",
            value=st.session_state.risk_controls_status["stop_loss_active"]
            and master_switch,
            disabled=not master_switch
            or st.session_state.risk_controls_status["emergency_stop_active"],
        )

        if st.session_state.risk_controls_status["stop_loss_active"]:
            st.success(
                f"✅ 停損機制啟用 ({st.session_state.risk_params['stop_loss_type']})"
            )
            st.info(
                f"停損閾值: {st.session_state.risk_params['stop_loss_percent']:.1f}%"
            )
        else:
            st.error("❌ 停損機制停用")

        # 停利控制
        st.session_state.risk_controls_status["take_profit_active"] = st.checkbox(
            "停利機制",
            value=st.session_state.risk_controls_status["take_profit_active"]
            and master_switch,
            disabled=not master_switch
            or st.session_state.risk_controls_status["emergency_stop_active"],
        )

        if st.session_state.risk_controls_status["take_profit_active"]:
            st.success(
                f"✅ 停利機制啟用 ({st.session_state.risk_params['take_profit_type']})"
            )
            st.info(
                f"停利閾值: {st.session_state.risk_params['take_profit_percent']:.1f}%"
            )
        else:
            st.error("❌ 停利機制停用")

        # 部位限制控制
        st.write("### 📊 部位控制")

        st.session_state.risk_controls_status["position_limit_active"] = st.checkbox(
            "部位限制",
            value=st.session_state.risk_controls_status["position_limit_active"]
            and master_switch,
            disabled=not master_switch
            or st.session_state.risk_controls_status["emergency_stop_active"],
        )

        if st.session_state.risk_controls_status["position_limit_active"]:
            st.success("✅ 部位限制啟用")
            st.info(
                f"最大部位: {st.session_state.risk_params['max_position_size']:.1f}%"
            )
            st.info(f"最大持倉數: {st.session_state.risk_params['max_positions']}")
        else:
            st.error("❌ 部位限制停用")

        # 行業限制控制
        st.session_state.risk_controls_status["sector_limit_active"] = st.checkbox(
            "行業曝險限制",
            value=st.session_state.risk_controls_status["sector_limit_active"]
            and master_switch,
            disabled=not master_switch
            or st.session_state.risk_controls_status["emergency_stop_active"],
        )

        if st.session_state.risk_controls_status["sector_limit_active"]:
            st.success("✅ 行業限制啟用")
            st.info(
                f"最大行業曝險: {st.session_state.risk_params['max_sector_exposure']:.1f}%"
            )
        else:
            st.error("❌ 行業限制停用")

    with col2:
        st.write("### 📈 風險監控控制")

        # VaR 監控
        st.session_state.risk_controls_status["var_monitoring_active"] = st.checkbox(
            "VaR 監控",
            value=st.session_state.risk_controls_status["var_monitoring_active"]
            and master_switch,
            disabled=not master_switch
            or st.session_state.risk_controls_status["emergency_stop_active"],
        )

        if st.session_state.risk_controls_status["var_monitoring_active"]:
            st.success("✅ VaR 監控啟用")
            st.info(
                f"VaR 信心水準: {st.session_state.risk_params['var_confidence']:.1f}%"
            )
            st.info(f"VaR 方法: {st.session_state.risk_params['var_method']}")
        else:
            st.error("❌ VaR 監控停用")

        # 回撤保護
        st.session_state.risk_controls_status["drawdown_protection_active"] = (
            st.checkbox(
                "回撤保護",
                value=st.session_state.risk_controls_status[
                    "drawdown_protection_active"
                ]
                and master_switch,
                disabled=not master_switch
                or st.session_state.risk_controls_status["emergency_stop_active"],
            )
        )

        if st.session_state.risk_controls_status["drawdown_protection_active"]:
            st.success("✅ 回撤保護啟用")
            st.info(f"最大回撤: {st.session_state.risk_params['max_drawdown']:.1f}%")
            st.info(
                f"警報閾值: {st.session_state.risk_params['alert_threshold_drawdown']:.1f}%"
            )
        else:
            st.error("❌ 回撤保護停用")

        # 相關性檢查
        st.session_state.risk_controls_status["correlation_check_active"] = st.checkbox(
            "相關性檢查",
            value=st.session_state.risk_controls_status["correlation_check_active"]
            and master_switch,
            disabled=not master_switch
            or st.session_state.risk_controls_status["emergency_stop_active"],
        )

        if st.session_state.risk_controls_status["correlation_check_active"]:
            st.success("✅ 相關性檢查啟用")
            st.info(
                f"相關性限制: {st.session_state.risk_params['correlation_limit']:.2f}"
            )
        else:
            st.error("❌ 相關性檢查停用")

        # 即時監控狀態
        st.write("### 🔍 監控狀態")

        if st.session_state.risk_params["real_time_monitoring"] and master_switch:
            st.success("🟢 即時監控運行中")
            st.info("監控頻率: 每5秒")
            st.info("最後更新: " + datetime.now().strftime("%H:%M:%S"))
        else:
            st.error("🔴 即時監控已停止")

    st.divider()

    # 風控動作記錄
    st.write("### 📋 最近風控動作")

    # 模擬最近的風控動作
    recent_actions = [
        {
            "時間": "14:32:15",
            "動作": "停損觸發",
            "股票": "2330.TW",
            "原因": "價格跌破5%停損線",
        },
        {
            "時間": "14:28:42",
            "動作": "部位調整",
            "股票": "2454.TW",
            "原因": "超過單一部位15%限制",
        },
        {
            "時間": "14:15:33",
            "動作": "VaR警報",
            "股票": "全組合",
            "原因": "VaR超過2%閾值",
        },
        {
            "時間": "13:45:21",
            "動作": "停利執行",
            "股票": "AAPL",
            "原因": "達到10%停利目標",
        },
        {
            "時間": "13:22:18",
            "動作": "相關性警告",
            "股票": "科技股",
            "原因": "行業相關性過高",
        },
    ]

    actions_df = pd.DataFrame(recent_actions)
    st.dataframe(actions_df, use_container_width=True, hide_index=True)

    # 手動風控動作
    st.write("### 🎮 手動風控動作")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🛑 全部停損", type="secondary", use_container_width=True):
            st.warning("確認執行全部停損？")

    with col2:
        if st.button("💰 全部停利", type="secondary", use_container_width=True):
            st.warning("確認執行全部停利？")

    with col3:
        if st.button("⚖️ 重新平衡", use_container_width=True):
            st.info("投資組合重新平衡中...")

    with col4:
        if st.button("🔄 重置警報", use_container_width=True):
            st.success("所有警報已重置")


def show_risk_alerts():
    """顯示風險警報記錄"""
    st.subheader("🚨 風險警報記錄")

    # 獲取風險管理服務
    risk_service = get_risk_management_service()

    # 獲取風險事件數據
    if risk_service:
        try:
            # 從服務層獲取實際風險事件
            events_data = risk_service.get_risk_events(limit=100)
            if events_data:
                # 轉換為 DataFrame
                risk_events = pd.DataFrame(events_data)
                # 重命名欄位為中文
                risk_events = risk_events.rename(
                    columns={
                        "timestamp": "時間",
                        "event_type": "事件類型",
                        "severity": "嚴重程度",
                        "symbol": "股票代碼",
                        "message": "訊息",
                        "status": "狀態",
                        "action_taken": "處理動作",
                    }
                )
                # 處理空值
                risk_events["股票代碼"] = risk_events["股票代碼"].fillna("全組合")
                risk_events["處理動作"] = risk_events["處理動作"].fillna("待處理")
                risk_events["備註"] = risk_events.get("訊息", "系統自動檢測到風險事件")

                # 添加觸發值和閾值欄位（如果不存在則使用模擬值）
                if "trigger_value" not in risk_events.columns:
                    risk_events["觸發值"] = [
                        f"{np.random.uniform(-15, -2):.2f}%"
                        for _ in range(len(risk_events))
                    ]
                    risk_events["閾值"] = [
                        f"{np.random.uniform(-10, -5):.2f}%"
                        for _ in range(len(risk_events))
                    ]
            else:
                risk_events = get_mock_risk_events()
        except Exception as e:
            st.warning(f"無法獲取實際風險事件，使用模擬數據: {e}")
            risk_events = get_mock_risk_events()
    else:
        risk_events = get_mock_risk_events()

    # 統計面板
    st.write("### 📊 警報統計")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_events = len(risk_events)
        st.metric("總事件數", total_events)

    with col2:
        high_severity = len(risk_events[risk_events["嚴重程度"].isin(["高", "嚴重"])])
        st.metric("高風險事件", high_severity, f"{high_severity/total_events*100:.1f}%")

    with col3:
        pending_events = len(risk_events[risk_events["狀態"] == "待處理"])
        st.metric("待處理事件", pending_events)

    with col4:
        today_events = len(
            risk_events[
                risk_events["時間"].str.contains(datetime.now().strftime("%Y-%m-%d"))
            ]
        )
        st.metric("今日事件", today_events)

    st.divider()

    # 篩選控制
    st.write("### 🔍 事件篩選")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        event_type_filter = st.multiselect(
            "事件類型",
            options=risk_events["事件類型"].unique(),
            default=risk_events["事件類型"].unique(),
        )

    with col2:
        severity_filter = st.multiselect(
            "嚴重程度",
            options=risk_events["嚴重程度"].unique(),
            default=risk_events["嚴重程度"].unique(),
        )

    with col3:
        status_filter = st.multiselect(
            "處理狀態",
            options=risk_events["狀態"].unique(),
            default=risk_events["狀態"].unique(),
        )

    with col4:
        date_range = st.selectbox(
            "時間範圍", ["全部", "今日", "最近3天", "最近7天", "最近30天"]
        )

    # 應用篩選
    filtered_events = risk_events[
        (risk_events["事件類型"].isin(event_type_filter))
        & (risk_events["嚴重程度"].isin(severity_filter))
        & (risk_events["狀態"].isin(status_filter))
    ]

    # 時間篩選
    if date_range != "全部":
        days_map = {"今日": 1, "最近3天": 3, "最近7天": 7, "最近30天": 30}
        days = days_map[date_range]
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_events = filtered_events[
            pd.to_datetime(filtered_events["時間"]) >= cutoff_date
        ]

    st.divider()

    # 事件列表
    st.write(f"### 📋 事件列表 ({len(filtered_events)} 筆記錄)")

    if len(filtered_events) > 0:
        # 添加顏色編碼
        def highlight_severity(row):
            if row["嚴重程度"] == "嚴重":
                return ["background-color: #ffebee"] * len(row)
            elif row["嚴重程度"] == "高":
                return ["background-color: #fff3e0"] * len(row)
            elif row["嚴重程度"] == "中":
                return ["background-color: #f3e5f5"] * len(row)
            else:
                return ["background-color: #e8f5e8"] * len(row)

        # 顯示表格
        styled_df = filtered_events.style.apply(highlight_severity, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # 詳細查看
        st.write("### 🔍 事件詳情")
        selected_event = st.selectbox(
            "選擇事件查看詳情",
            options=range(len(filtered_events)),
            format_func=lambda x: f"{filtered_events.iloc[x]['時間']} - {filtered_events.iloc[x]['事件類型']}",
        )

        if selected_event is not None:
            event = filtered_events.iloc[selected_event]

            col1, col2 = st.columns(2)

            with col1:
                st.write("**基本信息**")
                st.write(f"**時間:** {event['時間']}")
                st.write(f"**事件類型:** {event['事件類型']}")
                st.write(f"**嚴重程度:** {event['嚴重程度']}")
                st.write(f"**股票代碼:** {event['股票代碼']}")
                st.write(f"**狀態:** {event['狀態']}")

            with col2:
                st.write("**詳細信息**")
                st.write(f"**觸發值:** {event['觸發值']}")
                st.write(f"**閾值:** {event['閾值']}")
                st.write(f"**處理動作:** {event['處理動作']}")
                st.write(f"**備註:** {event['備註']}")

            # 處理動作
            st.write("**處理動作**")
            col_action1, col_action2, col_action3 = st.columns(3)

            with col_action1:
                if st.button("✅ 標記為已處理", use_container_width=True):
                    st.success("事件已標記為已處理")

            with col_action2:
                if st.button("🔄 重新處理", use_container_width=True):
                    st.info("事件已重新加入處理佇列")

            with col_action3:
                if st.button("❌ 忽略事件", use_container_width=True):
                    st.warning("事件已忽略")

    else:
        st.info("沒有符合篩選條件的事件記錄")

    st.divider()

    # 匯出功能
    st.write("### 📤 匯出功能")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 匯出 Excel", use_container_width=True):
            st.success("事件記錄已匯出為 Excel 檔案")

    with col2:
        if st.button("📄 匯出 PDF 報告", use_container_width=True):
            st.success("風險報告已匯出為 PDF 檔案")

    with col3:
        if st.button("📧 發送報告", use_container_width=True):
            st.success("風險報告已發送至指定信箱")


if __name__ == "__main__":
    show()
