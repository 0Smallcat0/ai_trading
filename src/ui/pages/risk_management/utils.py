"""風險管理共用工具函數

此模組提供風險管理頁面所需的共用工具函數，包括：
- 服務實例獲取
- 預設參數配置
- 模擬數據生成
- 通用輔助函數

Author: AI Trading System
Version: 1.0.0
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import streamlit as st
import pandas as pd
import numpy as np

# 添加項目根目錄到 Python 路徑
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from src.core.risk_management_service import RiskManagementService
except ImportError:
    # 如果無法導入，使用備用方案
    RiskManagementService = None


def get_risk_management_service() -> Optional[Any]:
    """獲取風險管理服務實例

    Returns:
        Optional[Any]: 風險管理服務實例，如果無法初始化則返回 None

    Example:
        >>> service = get_risk_management_service()
        >>> if service:
        ...     params = service.get_risk_parameters()
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
        Dict[str, Any]: 預設風險參數字典，包含所有風險控制設定

    Note:
        這些預設值基於一般投資組合的風險管理最佳實踐
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

    Note:
        此函數生成用於演示的模擬數據，實際部署時應替換為真實數據源
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
    var_95 = np.percentile(returns, 5) * portfolio_value
    cvar_95 = returns[returns <= np.percentile(returns, 5)].mean() * portfolio_value

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

    Note:
        生成最近30天的模擬風險事件，用於演示警報管理功能
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


def format_currency(value: float) -> str:
    """格式化貨幣顯示為美元格式。

    將數值格式化為帶有千位分隔符的美元格式字符串。

    Args:
        value (float): 要格式化的數值，可以是正數或負數。

    Returns:
        str: 格式化後的貨幣字符串，格式為 "$1,234,567"。

    Example:
        >>> format_currency(1234567.89)
        '$1,234,568'
        >>> format_currency(-1000)
        '$-1,000'

    Note:
        函數會自動四捨五入到最接近的整數。
    """
    return f"${value:,.0f}"


def format_percentage(value: float, decimal_places: int = 2) -> str:
    """格式化百分比顯示。

    將小數形式的數值轉換為百分比格式字符串。

    Args:
        value (float): 小數形式的數值（例如 0.05 表示 5%）。
        decimal_places (int, optional): 小數位數。預設為 2。

    Returns:
        str: 格式化後的百分比字符串，格式為 "5.00%"。

    Raises:
        ValueError: 當 decimal_places 為負數時。

    Example:
        >>> format_percentage(0.0525)
        '5.25%'
        >>> format_percentage(0.1, 1)
        '10.0%'
        >>> format_percentage(-0.03)
        '-3.00%'
    """
    if decimal_places < 0:
        raise ValueError("decimal_places 必須為非負整數")
    return f"{value * 100:.{decimal_places}f}%"


def validate_risk_parameters(params: Dict[str, Any]) -> List[str]:
    """驗證風險參數的有效性和一致性。

    檢查風險參數字典中的各項設定是否符合業務規則和數值範圍要求。

    Args:
        params (Dict[str, Any]): 風險參數字典，包含各種風險控制設定。
            預期包含的鍵值：
            - stop_loss_percent (float): 停損百分比
            - max_position_size (float): 最大部位大小百分比
            - max_portfolio_risk (float): 最大投資組合風險百分比

    Returns:
        List[str]: 驗證錯誤訊息列表。空列表表示所有參數驗證通過。

    Raises:
        TypeError: 當 params 不是字典類型時。

    Example:
        >>> params = {
        ...     "stop_loss_percent": 5.0,
        ...     "max_position_size": 10.0,
        ...     "max_portfolio_risk": 2.0
        ... }
        >>> validate_risk_parameters(params)
        []

        >>> invalid_params = {"stop_loss_percent": -1.0}
        >>> validate_risk_parameters(invalid_params)
        ['停損百分比必須在 0-50% 之間']

    Note:
        此函數執行基本的數值範圍檢查，更複雜的業務邏輯驗證
        應在相應的業務層進行。
    """
    errors = []

    # 檢查必要參數
    required_params = ["stop_loss_percent", "max_position_size", "max_portfolio_risk"]
    for param in required_params:
        if param not in params:
            errors.append(f"缺少必要參數: {param}")

    # 檢查數值範圍
    if (
        params.get("stop_loss_percent", 0) <= 0
        or params.get("stop_loss_percent", 0) > 50
    ):
        errors.append("停損百分比必須在 0-50% 之間")

    if (
        params.get("max_position_size", 0) <= 0
        or params.get("max_position_size", 0) > 100
    ):
        errors.append("最大部位大小必須在 0-100% 之間")

    return errors
