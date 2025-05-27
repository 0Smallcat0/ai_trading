"""
回測報表生成模組

此模組包含回測報表的生成和導出功能。
"""

import io
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


def export_to_csv(results: Dict[str, Any]) -> bytes:
    """
    匯出為CSV格式

    Args:
        results: 回測結果

    Returns:
        bytes: CSV格式的報表內容
    """
    try:
        csv_buffer = io.StringIO()

        # 寫入基本資訊
        csv_buffer.write("# 回測報告\n")
        csv_buffer.write(f"策略名稱,{results.get('strategy_name', 'N/A')}\n")
        csv_buffer.write(
            f"回測期間,{results.get('start_date', 'N/A')} 至 {results.get('end_date', 'N/A')}\n"
        )
        csv_buffer.write(f"初始資金,{results.get('initial_capital', 0):,.0f}\n\n")

        # 寫入績效指標
        csv_buffer.write("# 績效指標\n")
        metrics = results.get("metrics", {})
        for key, value in metrics.items():
            if isinstance(value, float):
                csv_buffer.write(f"{key},{value:.4f}\n")
            else:
                csv_buffer.write(f"{key},{value}\n")
        csv_buffer.write("\n")

        # 寫入交易記錄
        csv_buffer.write("# 交易記錄\n")
        trades = results.get("trades", [])
        if trades:
            import pandas as pd

            trades_df = pd.DataFrame(trades)
            csv_buffer.write(trades_df.to_csv(index=False))

        return csv_buffer.getvalue().encode("utf-8")

    except Exception as e:
        logger.error("匯出CSV失敗: %s", e)
        raise


def export_to_excel(results: Dict[str, Any]) -> bytes:
    """
    匯出為Excel格式

    Args:
        results: 回測結果

    Returns:
        bytes: Excel格式的報表內容
    """
    try:
        import pandas as pd

        excel_buffer = io.BytesIO()

        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            # 基本資訊
            info_df = pd.DataFrame(
                {
                    "項目": ["策略名稱", "回測期間", "初始資金"],
                    "值": [
                        results.get("strategy_name", "N/A"),
                        f"{results.get('start_date', 'N/A')} 至 {results.get('end_date', 'N/A')}",
                        f"{results.get('initial_capital', 0):,.0f}",
                    ],
                }
            )
            info_df.to_excel(writer, sheet_name="基本資訊", index=False)

            # 績效指標
            metrics = results.get("metrics", {})
            if metrics:
                metrics_df = pd.DataFrame(
                    {"指標": list(metrics.keys()), "值": list(metrics.values())}
                )
                metrics_df.to_excel(writer, sheet_name="績效指標", index=False)

            # 交易記錄
            trades = results.get("trades", [])
            if trades:
                trades_df = pd.DataFrame(trades)
                trades_df.to_excel(writer, sheet_name="交易記錄", index=False)

            # 權益曲線
            equity_curve = results.get("equity_curve", [])
            dates = results.get("dates", [])
            if equity_curve and dates:
                equity_df = pd.DataFrame({"日期": dates, "權益": equity_curve})
                equity_df.to_excel(writer, sheet_name="權益曲線", index=False)

        excel_buffer.seek(0)
        return excel_buffer.getvalue()

    except Exception as e:
        logger.error("匯出Excel失敗: %s", e)
        raise


def export_to_html(results: Dict[str, Any]) -> bytes:
    """
    匯出為HTML格式

    Args:
        results: 回測結果

    Returns:
        bytes: HTML格式的報表內容
    """
    try:
        strategy_name = results.get("strategy_name", "N/A")
        start_date = results.get("start_date", "N/A")
        end_date = results.get("end_date", "N/A")
        initial_capital = results.get("initial_capital", 0)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>回測報告 - {strategy_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 20px 0; }}
                .metric {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; text-align: center; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #333; }}
                .metric-label {{ font-size: 14px; color: #666; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>回測報告</h1>
                <p><strong>策略名稱:</strong> {strategy_name}</p>
                <p><strong>回測期間:</strong> {start_date} 至 {end_date}</p>
                <p><strong>初始資金:</strong> {initial_capital:,.0f}</p>
            </div>

            <h2>績效指標</h2>
            <div class="metrics">
        """

        # 添加績效指標
        metrics = results.get("metrics", {})
        for key, value in metrics.items():
            if isinstance(value, float):
                html_content += f"""
                <div class="metric">
                    <div class="metric-value">{value:.2f}</div>
                    <div class="metric-label">{key}</div>
                </div>
                """
            else:
                html_content += f"""
                <div class="metric">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{key}</div>
                </div>
                """

        html_content += """
            </div>

            <h2>交易記錄</h2>
            <table>
                <tr>
                    <th>股票代碼</th>
                    <th>進場日期</th>
                    <th>出場日期</th>
                    <th>進場價格</th>
                    <th>出場價格</th>
                    <th>損益</th>
                    <th>損益率</th>
                </tr>
        """

        # 添加交易記錄
        trades = results.get("trades", [])
        for trade in trades[:50]:  # 限制顯示前50筆交易
            html_content += f"""
                <tr>
                    <td>{trade.get('symbol', '')}</td>
                    <td>{trade.get('entry_date', '')}</td>
                    <td>{trade.get('exit_date', '')}</td>
                    <td>{trade.get('entry_price', 0):.2f}</td>
                    <td>{trade.get('exit_price', 0):.2f}</td>
                    <td>{trade.get('profit', 0):.2f}</td>
                    <td>{trade.get('profit_pct', 0):.2f}%</td>
                </tr>
            """

        html_content += """
            </table>
        </body>
        </html>
        """

        return html_content.encode("utf-8")

    except Exception as e:
        logger.error("匯出HTML失敗: %s", e)
        raise


def generate_report(
    backtest_id: str,
    results: Dict[str, Any],
    report_format: str = "html",
    include_charts: bool = False,
    include_transactions: bool = True,
) -> Optional[bytes]:
    """
    生成回測報表

    Args:
        backtest_id: 回測ID
        results: 回測結果
        report_format: 報表格式 (html, csv, excel)
        include_charts: 是否包含圖表（暫未使用）
        include_transactions: 是否包含交易明細（暫未使用）

    Returns:
        Optional[bytes]: 報表內容
    """
    try:
        # 標記參數為已使用，避免 pylint 警告
        _ = backtest_id
        _ = include_charts
        _ = include_transactions

        if report_format.lower() == "csv":
            return export_to_csv(results)
        elif report_format.lower() == "excel":
            return export_to_excel(results)
        elif report_format.lower() == "html":
            return export_to_html(results)
        else:
            logger.warning("不支援的報表格式: %s", report_format)
            return export_to_html(results)  # 默認使用HTML格式

    except Exception as e:
        logger.error("生成報表失敗: %s", e)
        return None


def get_chart_data(
    backtest_id: str, results: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    獲取圖表數據

    Args:
        backtest_id: 回測ID
        results: 回測結果

    Returns:
        Optional[Dict[str, Any]]: 圖表數據
    """
    try:
        equity_curve = results.get("equity_curve", [])
        dates = results.get("dates", [])

        if not equity_curve or not dates:
            logger.warning("權益曲線數據不完整")
            return None

        # 計算回撤
        drawdown = []
        peak = equity_curve[0]
        for value in equity_curve:
            peak = max(peak, value)
            dd = (peak - value) / peak * 100
            drawdown.append(dd)

        # 計算收益率
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] / equity_curve[i - 1] - 1) * 100
            returns.append(ret)

        return {
            "equity_curve": {
                "dates": dates,
                "values": equity_curve,
            },
            "drawdown": {
                "dates": dates,
                "values": drawdown,
            },
            "returns": {
                "dates": dates[1:],  # 收益率比權益曲線少一個點
                "values": returns,
            },
            "benchmark_values": None,  # 需要基準數據
        }

    except Exception as e:
        logger.error("獲取圖表數據失敗: %s", e)
        return None
