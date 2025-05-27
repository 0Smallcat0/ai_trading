# -*- coding: utf-8 -*-
"""
績效指標工具函數

此模組提供績效指標計算過程中使用的工具函數，包括：
- 輸入驗證
- 指標年化
- 報告生成
- 視覺化功能

Functions:
    validate_performance_inputs: 驗證績效計算輸入資料
    annualize_metric: 年化指標
    create_performance_report: 創建績效報告
    plot_performance_comparison: 繪製績效比較圖
"""

import logging
from typing import Any, Dict, List, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.config import LOG_LEVEL

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


def validate_performance_inputs(
    data: Union[pd.Series, np.ndarray, List[float]]
) -> None:
    """
    驗證績效計算輸入資料格式
    
    Args:
        data: 輸入資料，可以是收益率、價格或其他數值序列
        
    Raises:
        ValueError: 當輸入資料格式不正確時
        TypeError: 當資料類型不正確時
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015])
        >>> validate_performance_inputs(returns)
    """
    if data is None:
        raise ValueError("輸入資料不能為 None")
    
    # 轉換為 numpy 陣列進行統一處理
    if isinstance(data, (pd.Series, list)):
        data_array = np.array(data)
    elif isinstance(data, np.ndarray):
        data_array = data
    else:
        raise TypeError(f"不支援的資料類型: {type(data)}")
    
    # 檢查是否為空
    if len(data_array) == 0:
        logger.warning("輸入資料為空")
        return
    
    # 檢查是否包含無效值
    if np.any(np.isnan(data_array)):
        raise ValueError("輸入資料包含 NaN 值")
    
    if np.any(np.isinf(data_array)):
        raise ValueError("輸入資料包含無窮大值")
    
    # 檢查資料類型
    if not np.issubdtype(data_array.dtype, np.number):
        raise TypeError("輸入資料必須是數值類型")


def annualize_metric(
    metric_value: float,
    periods_per_year: int = 252,
    metric_type: str = "return"
) -> float:
    """
    年化指標
    
    Args:
        metric_value: 指標值
        periods_per_year: 每年期數
        metric_type: 指標類型，"return"或"volatility"
        
    Returns:
        年化後的指標值
        
    Raises:
        ValueError: 當參數無效時
        
    Example:
        >>> daily_return = 0.001
        >>> annual_return = annualize_metric(daily_return, 252, "return")
    """
    if periods_per_year <= 0:
        raise ValueError("每年期數必須大於0")
    
    if metric_type == "return":
        return metric_value * periods_per_year
    elif metric_type == "volatility":
        return metric_value * np.sqrt(periods_per_year)
    else:
        raise ValueError(f"未知的指標類型: {metric_type}")


def create_performance_report(
    metrics: Dict[str, Any],
    strategy_name: str = "Strategy",
    save_path: str = "performance_report.html"
) -> str:
    """
    創建績效報告
    
    Args:
        metrics: 績效指標字典
        strategy_name: 策略名稱
        save_path: 報告保存路徑
        
    Returns:
        報告檔案路徑
        
    Example:
        >>> metrics = {"sharpe_ratio": 1.5, "max_drawdown": -0.1}
        >>> report_path = create_performance_report(metrics, "My Strategy")
    """
    try:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{strategy_name} Performance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1, h2 {{ color: #333; }}
                .metric-table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                .metric-table th, .metric-table td {{ 
                    border: 1px solid #ddd; 
                    padding: 12px; 
                    text-align: left; 
                }}
                .metric-table th {{ background-color: #f2f2f2; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .section {{ margin: 30px 0; }}
            </style>
        </head>
        <body>
            <h1>{strategy_name} Performance Report</h1>
            
            <div class="section">
                <h2>Risk-Adjusted Returns</h2>
                <table class="metric-table">
                    <tr><th>Metric</th><th>Value</th></tr>
        """
        
        # 添加風險調整收益指標
        risk_adjusted_metrics = [
            ("Sharpe Ratio", "sharpe_ratio"),
            ("Sortino Ratio", "sortino_ratio"),
            ("Calmar Ratio", "calmar_ratio")
        ]
        
        for name, key in risk_adjusted_metrics:
            if key in metrics:
                value = metrics[key]
                css_class = "positive" if value > 0 else "negative"
                html_content += f'<tr><td>{name}</td><td class="{css_class}">{value:.4f}</td></tr>'
        
        html_content += """
                </table>
            </div>
            
            <div class="section">
                <h2>Risk Metrics</h2>
                <table class="metric-table">
                    <tr><th>Metric</th><th>Value</th></tr>
        """
        
        # 添加風險指標
        risk_metrics = [
            ("Maximum Drawdown", "max_drawdown"),
            ("Volatility", "volatility"),
            ("VaR (95%)", "var_95"),
            ("CVaR (95%)", "cvar_95")
        ]
        
        for name, key in risk_metrics:
            if key in metrics:
                value = metrics[key]
                css_class = "negative" if value < 0 else ""
                if key in ["max_drawdown", "var_95", "cvar_95"]:
                    html_content += f'<tr><td>{name}</td><td class="{css_class}">{value:.2%}</td></tr>'
                else:
                    html_content += f'<tr><td>{name}</td><td class="{css_class}">{value:.4f}</td></tr>'
        
        html_content += """
                </table>
            </div>
            
            <div class="section">
                <h2>Trading Statistics</h2>
                <table class="metric-table">
                    <tr><th>Metric</th><th>Value</th></tr>
        """
        
        # 添加交易統計
        trading_metrics = [
            ("Win Rate", "win_rate"),
            ("Profit/Loss Ratio", "pnl_ratio"),
            ("Expectancy", "expectancy"),
            ("Profit Factor", "profit_factor")
        ]
        
        for name, key in trading_metrics:
            if key in metrics:
                value = metrics[key]
                if key == "win_rate":
                    html_content += f'<tr><td>{name}</td><td>{value:.2%}</td></tr>'
                else:
                    css_class = "positive" if value > 0 else "negative"
                    html_content += f'<tr><td>{name}</td><td class="{css_class}">{value:.4f}</td></tr>'
        
        html_content += """
                </table>
            </div>
        </body>
        </html>
        """
        
        # 保存報告
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"績效報告已生成: {save_path}")
        return save_path
        
    except Exception as e:
        logger.error(f"生成績效報告時發生錯誤: {e}")
        raise RuntimeError(f"報告生成失敗: {e}") from e


def plot_performance_comparison(
    strategies_metrics: Dict[str, Dict[str, float]],
    save_path: str = "performance_comparison.png",
    figsize: tuple = (15, 10)
) -> str:
    """
    繪製策略績效比較圖
    
    Args:
        strategies_metrics: 策略績效指標字典
        save_path: 圖片保存路徑
        figsize: 圖片大小
        
    Returns:
        圖片檔案路徑
        
    Example:
        >>> strategies = {
        ...     "Strategy A": {"sharpe_ratio": 1.5, "max_drawdown": -0.1},
        ...     "Strategy B": {"sharpe_ratio": 1.2, "max_drawdown": -0.15}
        ... }
        >>> plot_path = plot_performance_comparison(strategies)
    """
    try:
        # 準備資料
        metrics_to_plot = [
            "sharpe_ratio", "sortino_ratio", "calmar_ratio",
            "max_drawdown", "volatility", "win_rate"
        ]
        
        # 創建子圖
        fig, axes = plt.subplots(2, 3, figsize=figsize)
        axes = axes.flatten()
        
        for idx, metric in enumerate(metrics_to_plot):
            if idx >= len(axes):
                break
                
            ax = axes[idx]
            
            # 收集該指標的資料
            strategy_names = []
            metric_values = []
            
            for strategy_name, metrics in strategies_metrics.items():
                if metric in metrics:
                    strategy_names.append(strategy_name)
                    metric_values.append(metrics[metric])
            
            if metric_values:
                # 繪製條形圖
                colors = ['green' if v > 0 else 'red' for v in metric_values]
                if metric in ["max_drawdown", "volatility"]:
                    colors = ['red' if v < 0 else 'orange' for v in metric_values]
                
                bars = ax.bar(strategy_names, metric_values, color=colors, alpha=0.7)
                
                # 設定標題和標籤
                ax.set_title(metric.replace('_', ' ').title(), fontsize=12, fontweight='bold')
                ax.set_ylabel('Value')
                
                # 旋轉x軸標籤
                ax.tick_params(axis='x', rotation=45)
                
                # 添加數值標籤
                for bar, value in zip(bars, metric_values):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{value:.3f}', ha='center', va='bottom' if height > 0 else 'top')
                
                # 添加零線
                ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
                ax.grid(axis='y', alpha=0.3)
        
        # 移除多餘的子圖
        for idx in range(len(metrics_to_plot), len(axes)):
            fig.delaxes(axes[idx])
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"績效比較圖已保存: {save_path}")
        return save_path
        
    except Exception as e:
        logger.error(f"繪製績效比較圖時發生錯誤: {e}")
        plt.close()  # 確保關閉圖表
        raise RuntimeError(f"比較圖繪製失敗: {e}") from e
