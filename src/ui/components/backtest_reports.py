"""
回測報告生成組件

此模組提供回測系統的報告生成功能，支援多種格式：
- PDF 報告（使用 reportlab）
- Excel 報告（使用 xlsxwriter）
- HTML 報告（使用 Jinja2 模板）
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 報告生成相關導入
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        Image,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.linecharts import HorizontalLineChart

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import xlsxwriter

    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False

try:
    from jinja2 import Template

    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

# 導入響應式設計組件
from ..responsive import ResponsiveComponents, responsive_manager


class BacktestReports:
    """回測報告生成類"""

    def __init__(self):
        """初始化報告生成器"""
        self.executor = ThreadPoolExecutor(max_workers=2)

    @staticmethod
    def check_dependencies() -> Dict[str, bool]:
        """檢查依賴項是否可用"""
        return {
            "reportlab": REPORTLAB_AVAILABLE,
            "xlsxwriter": XLSXWRITER_AVAILABLE,
            "jinja2": JINJA2_AVAILABLE,
        }

    def generate_pdf_report(
        self, backtest_results: Dict[str, Any], include_charts: bool = True
    ) -> bytes:
        """
        生成 PDF 報告

        Args:
            backtest_results: 回測結果數據
            include_charts: 是否包含圖表

        Returns:
            PDF 文件的字節數據
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab 未安裝，無法生成 PDF 報告")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # 標題頁
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # 居中
        )

        story.append(Paragraph("回測分析報告", title_style))
        story.append(Spacer(1, 20))

        # 基本資訊
        info_data = [
            ["策略名稱", backtest_results.get("strategy_name", "N/A")],
            [
                "回測期間",
                f"{backtest_results.get('start_date', 'N/A')} 至 {backtest_results.get('end_date', 'N/A')}",
            ],
            ["初始資金", f"{backtest_results.get('initial_capital', 0):,.0f}"],
            ["最終資金", f"{backtest_results.get('final_capital', 0):,.0f}"],
            ["報告生成時間", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ]

        info_table = Table(info_data, colWidths=[2 * inch, 3 * inch])
        info_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(info_table)
        story.append(Spacer(1, 20))

        # 績效指標
        metrics = backtest_results.get("metrics", {})
        if metrics:
            story.append(Paragraph("績效指標", styles["Heading2"]))

            metrics_data = [
                ["指標", "數值"],
                ["總回報率", f"{metrics.get('total_return', 0):.2%}"],
                ["年化回報率", f"{metrics.get('annual_return', 0):.2%}"],
                ["夏普比率", f"{metrics.get('sharpe_ratio', 0):.3f}"],
                ["最大回撤", f"{metrics.get('max_drawdown', 0):.2%}"],
                ["勝率", f"{metrics.get('win_rate', 0):.2%}"],
                ["獲利因子", f"{metrics.get('profit_factor', 0):.3f}"],
                ["總交易次數", f"{metrics.get('total_trades', 0):,}"],
                ["平均交易回報", f"{metrics.get('avg_trade_return', 0):.2%}"],
                ["波動率", f"{metrics.get('volatility', 0):.2%}"],
            ]

            metrics_table = Table(metrics_data, colWidths=[2.5 * inch, 2.5 * inch])
            metrics_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            story.append(metrics_table)
            story.append(Spacer(1, 20))

        # 交易明細（前10筆）
        transactions = backtest_results.get("transactions", [])
        if transactions:
            story.append(Paragraph("交易明細（前10筆）", styles["Heading2"]))

            # 準備交易數據
            trans_data = [["日期", "股票", "動作", "數量", "價格", "金額"]]
            for i, trans in enumerate(transactions[:10]):
                trans_data.append(
                    [
                        trans.get("date", "N/A"),
                        trans.get("symbol", "N/A"),
                        trans.get("action", "N/A"),
                        f"{trans.get('quantity', 0):,}",
                        f"{trans.get('price', 0):.2f}",
                        f"{trans.get('amount', 0):,.0f}",
                    ]
                )

            trans_table = Table(
                trans_data,
                colWidths=[
                    1 * inch,
                    1 * inch,
                    0.8 * inch,
                    0.8 * inch,
                    1 * inch,
                    1.2 * inch,
                ],
            )
            trans_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            story.append(trans_table)

        # 建立 PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_excel_report(self, backtest_results: Dict[str, Any]) -> bytes:
        """
        生成 Excel 報告

        Args:
            backtest_results: 回測結果數據

        Returns:
            Excel 文件的字節數據
        """
        if not XLSXWRITER_AVAILABLE:
            raise ImportError("xlsxwriter 未安裝，無法生成 Excel 報告")

        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            workbook = writer.book

            # 定義格式
            header_format = workbook.add_format(
                {
                    "bold": True,
                    "text_wrap": True,
                    "valign": "top",
                    "fg_color": "#D7E4BC",
                    "border": 1,
                }
            )

            number_format = workbook.add_format({"num_format": "#,##0.00"})
            percent_format = workbook.add_format({"num_format": "0.00%"})

            # 摘要工作表
            summary_data = {
                "項目": [
                    "策略名稱",
                    "回測期間",
                    "初始資金",
                    "最終資金",
                    "總回報率",
                    "年化回報率",
                    "夏普比率",
                    "最大回撤",
                ],
                "數值": [
                    backtest_results.get("strategy_name", "N/A"),
                    f"{backtest_results.get('start_date', 'N/A')} 至 {backtest_results.get('end_date', 'N/A')}",
                    backtest_results.get("initial_capital", 0),
                    backtest_results.get("final_capital", 0),
                    backtest_results.get("metrics", {}).get("total_return", 0),
                    backtest_results.get("metrics", {}).get("annual_return", 0),
                    backtest_results.get("metrics", {}).get("sharpe_ratio", 0),
                    backtest_results.get("metrics", {}).get("max_drawdown", 0),
                ],
            }

            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="摘要", index=False)

            # 格式化摘要工作表
            summary_worksheet = writer.sheets["摘要"]
            summary_worksheet.set_column("A:A", 15)
            summary_worksheet.set_column("B:B", 20)

            # 投資組合數據工作表
            portfolio_data = backtest_results.get("portfolio_data", [])
            if portfolio_data:
                portfolio_df = pd.DataFrame(portfolio_data)
                portfolio_df.to_excel(writer, sheet_name="投資組合數據", index=False)

                portfolio_worksheet = writer.sheets["投資組合數據"]
                portfolio_worksheet.set_column("A:Z", 12)

            # 交易記錄工作表
            transactions = backtest_results.get("transactions", [])
            if transactions:
                transactions_df = pd.DataFrame(transactions)
                transactions_df.to_excel(writer, sheet_name="交易記錄", index=False)

                trans_worksheet = writer.sheets["交易記錄"]
                trans_worksheet.set_column("A:Z", 12)

            # 績效指標工作表
            metrics = backtest_results.get("metrics", {})
            if metrics:
                metrics_data = {
                    "指標": list(metrics.keys()),
                    "數值": list(metrics.values()),
                }
                metrics_df = pd.DataFrame(metrics_data)
                metrics_df.to_excel(writer, sheet_name="績效指標", index=False)

                metrics_worksheet = writer.sheets["績效指標"]
                metrics_worksheet.set_column("A:A", 20)
                metrics_worksheet.set_column("B:B", 15)

        buffer.seek(0)
        return buffer.getvalue()

    def generate_html_report(
        self, backtest_results: Dict[str, Any], include_charts: bool = True
    ) -> str:
        """
        生成 HTML 報告

        Args:
            backtest_results: 回測結果數據
            include_charts: 是否包含圖表

        Returns:
            HTML 報告字符串
        """
        if not JINJA2_AVAILABLE:
            raise ImportError("jinja2 未安裝，無法生成 HTML 報告")

        # HTML 模板
        html_template = """
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>回測分析報告</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { text-align: center; margin-bottom: 30px; }
                .section { margin-bottom: 30px; }
                .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
                .metric-card { background: #f5f5f5; padding: 15px; border-radius: 8px; text-align: center; }
                .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
                .metric-label { font-size: 14px; color: #7f8c8d; margin-top: 5px; }
                table { width: 100%; border-collapse: collapse; margin-top: 15px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; font-weight: bold; }
                .positive { color: #27ae60; }
                .negative { color: #e74c3c; }
                @media (max-width: 768px) {
                    .metrics-grid { grid-template-columns: 1fr; }
                    table { font-size: 12px; }
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>回測分析報告</h1>
                <p>策略：{{ strategy_name }} | 生成時間：{{ generation_time }}</p>
            </div>
            
            <div class="section">
                <h2>基本資訊</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{{ start_date }} - {{ end_date }}</div>
                        <div class="metric-label">回測期間</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{ "{:,.0f}".format(initial_capital) }}</div>
                        <div class="metric-label">初始資金</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{{ "{:,.0f}".format(final_capital) }}</div>
                        <div class="metric-label">最終資金</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>績效指標</h2>
                <div class="metrics-grid">
                    {% for key, value in metrics.items() %}
                    <div class="metric-card">
                        <div class="metric-value {% if value > 0 %}positive{% elif value < 0 %}negative{% endif %}">
                            {% if key in ['total_return', 'annual_return', 'max_drawdown', 'win_rate', 'avg_trade_return', 'volatility'] %}
                                {{ "{:.2%}".format(value) }}
                            {% elif key in ['sharpe_ratio', 'profit_factor', 'calmar_ratio'] %}
                                {{ "{:.3f}".format(value) }}
                            {% else %}
                                {{ "{:,}".format(value) if value is number else value }}
                            {% endif %}
                        </div>
                        <div class="metric-label">{{ key }}</div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            {% if transactions %}
            <div class="section">
                <h2>交易記錄（前20筆）</h2>
                <table>
                    <thead>
                        <tr>
                            <th>日期</th>
                            <th>股票</th>
                            <th>動作</th>
                            <th>數量</th>
                            <th>價格</th>
                            <th>金額</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for trans in transactions[:20] %}
                        <tr>
                            <td>{{ trans.date }}</td>
                            <td>{{ trans.symbol }}</td>
                            <td>{{ trans.action }}</td>
                            <td>{{ "{:,}".format(trans.quantity) }}</td>
                            <td>{{ "{:.2f}".format(trans.price) }}</td>
                            <td>{{ "{:,.0f}".format(trans.amount) }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
            
            <div class="section">
                <p><small>報告生成時間：{{ generation_time }}</small></p>
            </div>
        </body>
        </html>
        """

        template = Template(html_template)

        # 準備模板數據
        template_data = {
            "strategy_name": backtest_results.get("strategy_name", "N/A"),
            "start_date": backtest_results.get("start_date", "N/A"),
            "end_date": backtest_results.get("end_date", "N/A"),
            "initial_capital": backtest_results.get("initial_capital", 0),
            "final_capital": backtest_results.get("final_capital", 0),
            "metrics": backtest_results.get("metrics", {}),
            "transactions": backtest_results.get("transactions", []),
            "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        return template.render(**template_data)
