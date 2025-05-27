"""回測報表匯出模組

此模組提供回測結果的多格式匯出功能，包含 JSON、CSV、Excel 和 HTML 格式。
"""

import json
from io import BytesIO, StringIO
from typing import Dict, Any, Optional
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class BacktestExportManager:
    """回測報表匯出管理器

    提供多種格式的回測結果匯出功能。
    """

    def __init__(self):
        """初始化匯出管理器"""
        self.supported_formats = ["json", "csv", "excel", "html"]

    def export_results(self, results: Dict[str, Any], export_format: str = "json") -> Optional[bytes]:
        """匯出回測結果

        Args:
            results: 回測結果字典
            export_format: 匯出格式 ('json', 'csv', 'excel', 'html')

        Returns:
            Optional[bytes]: 匯出的檔案內容
        """
        if export_format not in self.supported_formats:
            raise ValueError(f"不支援的匯出格式: {export_format}")

        try:
            if export_format == "json":
                return self._export_to_json(results)
            elif export_format == "csv":
                return self._export_to_csv(results)
            elif export_format == "excel":
                return self._export_to_excel(results)
            elif export_format == "html":
                return self._export_to_html(results)

        except Exception as e:
            logger.error("匯出回測結果失敗: %s", e)
            return None

    def _export_to_json(self, results: Dict[str, Any]) -> bytes:
        """匯出為 JSON 格式

        Args:
            results: 回測結果

        Returns:
            bytes: JSON 檔案內容
        """
        return json.dumps(results, ensure_ascii=False, indent=2).encode("utf-8")

    def _export_to_csv(self, results: Dict[str, Any]) -> bytes:
        """匯出為 CSV 格式

        Args:
            results: 回測結果

        Returns:
            bytes: CSV 檔案內容
        """
        output = StringIO()

        # 匯出績效指標
        metrics = results.get("metrics", {})
        if metrics:
            output.write("績效指標\n")
            output.write("指標名稱,數值\n")

            metric_names = {
                "initial_capital": "初始資金",
                "final_capital": "最終資金",
                "total_return": "總報酬率(%)",
                "annual_return": "年化報酬率(%)",
                "sharpe_ratio": "夏普比率",
                "max_drawdown": "最大回撤(%)",
                "win_rate": "勝率(%)",
                "total_trades": "總交易次數",
            }

            for key, name in metric_names.items():
                value = metrics.get(key, "N/A")
                output.write(f"{name},{value}\n")

            output.write("\n")

        # 匯出交易記錄
        trades = results.get("trades", [])
        if trades:
            output.write("交易記錄\n")

            # 轉換為 DataFrame
            trades_df = pd.DataFrame(trades)

            # 重新命名欄位
            column_mapping = {
                "symbol": "股票代碼",
                "side": "買賣方向",
                "quantity": "數量",
                "entry_price": "進場價格",
                "exit_price": "出場價格",
                "entry_date": "進場日期",
                "exit_date": "出場日期",
                "pnl": "損益",
                "commission": "手續費",
                "duration_days": "持有天數",
            }

            trades_df = trades_df.rename(columns=column_mapping)
            trades_df.to_csv(output, index=False)

        return output.getvalue().encode("utf-8")

    def _export_to_excel(self, results: Dict[str, Any]) -> bytes:
        """匯出為 Excel 格式

        Args:
            results: 回測結果

        Returns:
            bytes: Excel 檔案內容
        """
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 匯出績效指標
            metrics = results.get("metrics", {})
            if metrics:
                metrics_data = []

                metric_names = {
                    "initial_capital": "初始資金",
                    "final_capital": "最終資金",
                    "total_return": "總報酬率(%)",
                    "annual_return": "年化報酬率(%)",
                    "sharpe_ratio": "夏普比率",
                    "max_drawdown": "最大回撤(%)",
                    "win_rate": "勝率(%)",
                    "profit_ratio": "盈虧比",
                    "total_trades": "總交易次數",
                    "winning_trades": "獲利交易次數",
                    "losing_trades": "虧損交易次數",
                    "avg_trade_duration": "平均持有天數",
                    "calmar_ratio": "Calmar比率",
                    "sortino_ratio": "Sortino比率",
                    "var_95": "VaR(95%)",
                }

                for key, name in metric_names.items():
                    value = metrics.get(key, "N/A")
                    metrics_data.append({"指標名稱": name, "數值": value})

                metrics_df = pd.DataFrame(metrics_data)
                metrics_df.to_excel(writer, sheet_name="績效指標", index=False)

            # 匯出交易記錄
            trades = results.get("trades", [])
            if trades:
                trades_df = pd.DataFrame(trades)

                # 重新命名欄位
                column_mapping = {
                    "symbol": "股票代碼",
                    "side": "買賣方向",
                    "quantity": "數量",
                    "entry_price": "進場價格",
                    "exit_price": "出場價格",
                    "entry_date": "進場日期",
                    "exit_date": "出場日期",
                    "pnl": "損益",
                    "commission": "手續費",
                    "slippage": "滑點成本",
                    "duration_days": "持有天數",
                }

                trades_df = trades_df.rename(columns=column_mapping)
                trades_df.to_excel(writer, sheet_name="交易記錄", index=False)

            # 匯出權益曲線
            equity_curve = results.get("equity_curve", [])
            dates = results.get("dates", [])

            if equity_curve and dates and len(equity_curve) == len(dates):
                equity_df = pd.DataFrame({
                    "日期": dates,
                    "權益": equity_curve,
                })

                # 計算累積報酬率
                initial_capital = results.get("metrics", {}).get("initial_capital", equity_curve[0] if equity_curve else 1)
                equity_df["累積報酬率(%)"] = (equity_df["權益"] / initial_capital - 1) * 100

                equity_df.to_excel(writer, sheet_name="權益曲線", index=False)

        return output.getvalue()

    def _export_to_html(self, results: Dict[str, Any]) -> bytes:
        """匯出為 HTML 格式

        Args:
            results: 回測結果

        Returns:
            bytes: HTML 檔案內容
        """
        html_content = self._generate_html_report(results)
        return html_content.encode("utf-8")

    def _generate_html_report(self, results: Dict[str, Any]) -> str:
        """生成 HTML 報表

        Args:
            results: 回測結果

        Returns:
            str: HTML 內容
        """
        backtest_id = results.get("backtest_id", "未知")
        metrics = results.get("metrics", {})
        trades = results.get("trades", [])

        html = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>回測報告 - {backtest_id}</title>
            <style>
                body {{
                    font-family: 'Microsoft JhengHei', Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1, h2 {{
                    color: #333;
                    border-bottom: 2px solid #007bff;
                    padding-bottom: 10px;
                }}
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 15px;
                    margin: 20px 0;
                }}
                .metric-card {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                    border-left: 4px solid #007bff;
                }}
                .metric-label {{
                    font-weight: bold;
                    color: #666;
                    font-size: 14px;
                }}
                .metric-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #333;
                    margin-top: 5px;
                }}
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                th, td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }}
                th {{
                    background-color: #007bff;
                    color: white;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .summary {{
                    background: #e9ecef;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>回測報告</h1>
                <div class="summary">
                    <strong>回測ID:</strong> {backtest_id}<br>
                    <strong>生成時間:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>

                <h2>績效指標</h2>
                <div class="metrics-grid">
        """

        # 添加績效指標卡片
        metric_definitions = [
            ("initial_capital", "初始資金", "NT$", ""),
            ("final_capital", "最終資金", "NT$", ""),
            ("total_return", "總報酬率", "", "%"),
            ("annual_return", "年化報酬率", "", "%"),
            ("sharpe_ratio", "夏普比率", "", ""),
            ("max_drawdown", "最大回撤", "", "%"),
            ("win_rate", "勝率", "", "%"),
            ("total_trades", "總交易次數", "", "筆"),
        ]

        for key, label, prefix, suffix in metric_definitions:
            value = metrics.get(key, 0)

            # 格式化數值
            if isinstance(value, (int, float)):
                if key in ["initial_capital", "final_capital"]:
                    formatted_value = f"{prefix}{value:,.0f}"
                elif key in ["total_return", "annual_return", "max_drawdown", "win_rate"]:
                    formatted_value = f"{value:.2f}{suffix}"
                elif key == "sharpe_ratio":
                    formatted_value = f"{value:.3f}"
                else:
                    formatted_value = f"{value}{suffix}"
            else:
                formatted_value = str(value)

            # 確定顏色類別
            color_class = ""
            if key in ["total_return", "annual_return", "sharpe_ratio"] and isinstance(value, (int, float)):
                color_class = "positive" if value > 0 else "negative"
            elif key == "max_drawdown" and isinstance(value, (int, float)):
                color_class = "negative" if value > 0 else ""

            html += f"""
                    <div class="metric-card">
                        <div class="metric-label">{label}</div>
                        <div class="metric-value {color_class}">{formatted_value}</div>
                    </div>
            """

        html += """
                </div>

                <h2>交易記錄</h2>
        """

        # 添加交易記錄表格
        if trades:
            html += """
                <table>
                    <thead>
                        <tr>
                            <th>股票代碼</th>
                            <th>買賣方向</th>
                            <th>數量</th>
                            <th>進場價格</th>
                            <th>出場價格</th>
                            <th>進場日期</th>
                            <th>出場日期</th>
                            <th>損益</th>
                            <th>持有天數</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for trade in trades[:50]:  # 限制顯示前50筆交易
                pnl = trade.get("pnl", 0)
                pnl_class = "positive" if pnl > 0 else "negative" if pnl < 0 else ""

                html += f"""
                        <tr>
                            <td>{trade.get('symbol', '')}</td>
                            <td>{trade.get('side', '')}</td>
                            <td>{trade.get('quantity', 0):,}</td>
                            <td>{trade.get('entry_price', 0):.2f}</td>
                            <td>{trade.get('exit_price', 0):.2f}</td>
                            <td>{trade.get('entry_date', '')[:10]}</td>
                            <td>{trade.get('exit_date', '')[:10]}</td>
                            <td class="{pnl_class}">{pnl:,.2f}</td>
                            <td>{trade.get('duration_days', 0)}</td>
                        </tr>
                """

            html += """
                    </tbody>
                </table>
            """

            if len(trades) > 50:
                html += f"<p><em>註：僅顯示前50筆交易，總共{len(trades)}筆交易</em></p>"
        else:
            html += "<p>無交易記錄</p>"

        html += """
            </div>
        </body>
        </html>
        """

        return html

    def generate_report(
        self,
        backtest_id: str,
        results: Dict[str, Any],
        export_format: str = "html",
        include_charts: bool = False,
        include_transactions: bool = True
    ) -> Optional[bytes]:
        """生成回測報表

        Args:
            backtest_id: 回測ID
            results: 回測結果
            export_format: 報表格式
            include_charts: 是否包含圖表（暫未實現）
            include_transactions: 是否包含交易明細

        Returns:
            Optional[bytes]: 報表內容
        """
        # 根據參數調整結果內容
        filtered_results = results.copy()

        if not include_transactions:
            filtered_results.pop("trades", None)

        # 添加報表元數據
        filtered_results["backtest_id"] = backtest_id
        filtered_results["report_generated_at"] = pd.Timestamp.now().isoformat()
        filtered_results["include_charts"] = include_charts
        filtered_results["include_transactions"] = include_transactions

        return self.export_results(filtered_results, export_format)
