"""風險管理組件庫

此模組提供風險管理相關的 UI 組件，包括：
- 表單組件 (forms.py): 風險參數設定表單、驗證組件
- 圖表組件 (charts.py): VaR 分析、回撤走勢、風險分解圖表
- 面板組件 (panels.py): 概覽面板、控制面板、警報面板

Author: AI Trading System
Version: 1.0.0
"""

# 導入所有組件
from .forms import (
    risk_parameter_form,
    parameter_validation_display,
    dynamic_form_generator,
    form_state_manager,
    save_form_state,
    reset_form_state,
    form_action_buttons,
    conditional_form_section,
    form_progress_indicator,
    form_help_sidebar,
)

from .charts import (
    var_analysis_chart,
    drawdown_chart,
    risk_decomposition_pie_chart,
    correlation_heatmap,
    risk_trend_chart,
    portfolio_composition_chart,
    risk_gauge_chart,
    multi_metric_dashboard,
    create_sample_data,
)

from .panels import (
    risk_overview_panel,
    control_panel,
    alert_panel,
    status_indicator_panel,
    quick_action_panel,
    parameter_summary_panel,
    responsive_panel_layout,
    collapsible_panel,
)


# 導出所有組件
__all__ = [
    # 表單組件
    "risk_parameter_form",
    "parameter_validation_display", 
    "dynamic_form_generator",
    "form_state_manager",
    "save_form_state",
    "reset_form_state",
    "form_action_buttons",
    "conditional_form_section",
    "form_progress_indicator",
    "form_help_sidebar",
    
    # 圖表組件
    "var_analysis_chart",
    "drawdown_chart",
    "risk_decomposition_pie_chart",
    "correlation_heatmap",
    "risk_trend_chart",
    "portfolio_composition_chart",
    "risk_gauge_chart",
    "multi_metric_dashboard",
    "create_sample_data",
    
    # 面板組件
    "risk_overview_panel",
    "control_panel",
    "alert_panel",
    "status_indicator_panel",
    "quick_action_panel",
    "parameter_summary_panel",
    "responsive_panel_layout",
    "collapsible_panel",
]


# 組件庫版本信息
RISK_COMPONENTS_VERSION = "1.0.0"
SUPPORTED_FEATURES = [
    "parameter_forms",
    "risk_charts",
    "control_panels",
    "alert_management",
    "responsive_design",
    "state_management",
]


def get_component_info() -> dict:
    """獲取組件庫信息
    
    Returns:
        dict: 組件庫版本和功能信息
    """
    return {
        "version": RISK_COMPONENTS_VERSION,
        "features": SUPPORTED_FEATURES,
        "modules": ["forms", "charts", "panels"],
        "total_components": len(__all__)
    }


# 便利函數：創建完整的風險管理儀表板
def create_risk_dashboard(
    risk_data: dict,
    layout_mode: str = "auto"
) -> None:
    """創建完整的風險管理儀表板
    
    Args:
        risk_data: 風險數據字典
        layout_mode: 佈局模式
    """
    import streamlit as st
    
    # 概覽面板
    risk_overview_panel(risk_data.get("metrics", {}))
    
    # 圖表區域
    col1, col2 = st.columns(2)
    
    with col1:
        if "returns" in risk_data:
            fig_var = var_analysis_chart(risk_data["returns"])
            st.plotly_chart(fig_var, use_container_width=True)
    
    with col2:
        if "drawdown" in risk_data and "dates" in risk_data:
            fig_dd = drawdown_chart(risk_data["dates"], risk_data["drawdown"])
            st.plotly_chart(fig_dd, use_container_width=True)
    
    # 控制面板
    controls = risk_data.get("controls", {})
    updated_controls = control_panel(controls)
    
    # 警報面板
    alerts = risk_data.get("alerts", [])
    alert_panel(alerts)


# 便利函數：創建風險參數設定頁面
def create_parameter_page(
    current_params: dict,
    on_save: callable = None
) -> dict:
    """創建風險參數設定頁面
    
    Args:
        current_params: 當前參數字典
        on_save: 保存回調函數
        
    Returns:
        dict: 更新後的參數字典
    """
    import streamlit as st
    
    # 參數表單
    updated_params = risk_parameter_form(current_params)
    
    # 參數驗證
    parameter_validation_display(updated_params)
    
    # 參數摘要
    parameter_summary_panel(updated_params)
    
    # 操作按鈕
    button_states = form_action_buttons(on_save=on_save)
    
    return updated_params


# 便利函數：創建風險監控頁面
def create_monitoring_page(risk_metrics: dict) -> None:
    """創建風險監控頁面
    
    Args:
        risk_metrics: 風險指標字典
    """
    import streamlit as st
    
    # 風險評分儀表
    risk_score = risk_metrics.get("risk_score", 75)
    fig_gauge = risk_gauge_chart(risk_score)
    st.plotly_chart(fig_gauge, use_container_width=True)
    
    # 多指標儀表板
    metrics_for_dashboard = {
        "VaR": {
            "value": f"${risk_metrics.get('var_95_1day', 0):,.0f}",
            "delta": "-5.2%"
        },
        "回撤": {
            "value": f"{risk_metrics.get('current_drawdown', 0):.2f}%",
            "delta": "+1.1%"
        },
        "波動率": {
            "value": f"{risk_metrics.get('volatility', 0):.1f}%",
            "delta": "-0.3%"
        }
    }
    
    multi_metric_dashboard(metrics_for_dashboard, layout="grid")


# 組件使用示例
def show_component_examples() -> None:
    """顯示組件使用示例"""
    import streamlit as st
    
    st.title("風險管理組件庫示例")
    
    # 創建示例數據
    sample_data = create_sample_data()
    
    # 示例：完整儀表板
    with st.expander("完整風險管理儀表板", expanded=True):
        risk_data = {
            "metrics": {
                "portfolio_value": 1000000,
                "daily_pnl": 5000,
                "var_95_1day": 25000,
                "current_drawdown": -3.2,
                "volatility": 18.5,
                "sharpe_ratio": 1.25
            },
            "returns": sample_data["returns"],
            "dates": sample_data["dates"],
            "drawdown": sample_data["drawdown"],
            "controls": {
                "master_switch": True,
                "stop_loss_active": True,
                "take_profit_active": True
            },
            "alerts": [
                {
                    "類型": "VaR超限",
                    "嚴重程度": "高",
                    "訊息": "VaR超過設定閾值",
                    "時間": "2024-01-15 14:30:00",
                    "狀態": "待處理"
                }
            ]
        }
        
        create_risk_dashboard(risk_data)
    
    # 示例：參數設定頁面
    with st.expander("風險參數設定頁面"):
        default_params = {
            "stop_loss_enabled": True,
            "stop_loss_percent": 5.0,
            "take_profit_enabled": True,
            "take_profit_percent": 10.0,
            "max_position_size": 10.0,
            "max_positions": 10
        }
        
        create_parameter_page(default_params)
    
    # 示例：監控頁面
    with st.expander("風險監控頁面"):
        monitoring_metrics = {
            "risk_score": 78,
            "var_95_1day": 25000,
            "current_drawdown": -3.2,
            "volatility": 18.5
        }
        
        create_monitoring_page(monitoring_metrics)
