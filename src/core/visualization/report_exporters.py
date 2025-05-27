"""報表視覺化匯出模組

此模組負責將報表匯出為各種格式，包括：
- PDF 報表
- Excel 報表
- JSON 數據
- CSV 數據
- HTML 報表
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import pandas as pd
from sqlalchemy.orm import sessionmaker

from src.database.schema import ExportLog

logger = logging.getLogger(__name__)


class ReportExporterService:
    """報表匯出服務"""

    def __init__(self, session_factory: sessionmaker):
        """初始化報表匯出服務
        
        Args:
            session_factory: SQLAlchemy session factory
        """
        self.session_factory = session_factory
        self.export_dir = Path("exports")
        self.export_dir.mkdir(exist_ok=True)

    def export_report(
        self,
        report_data: Dict[str, Any],
        export_format: str = "pdf",
        template_id: Optional[str] = None,
        user_id: str = "system",
    ) -> Tuple[bool, str, Optional[str]]:
        """匯出報表
        
        Args:
            report_data: 報表數據
            export_format: 匯出格式 ('pdf', 'excel', 'json', 'csv', 'html')
            template_id: 模板ID
            user_id: 用戶ID
            
        Returns:
            (成功標誌, 訊息, 檔案路徑)
        """
        export_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            # 記錄匯出開始
            self._log_export_start(export_id, export_format, user_id)

            # 根據格式選擇匯出方法
            if export_format.lower() == "json":
                success, message, filepath = self._export_json(
                    report_data, export_id, timestamp
                )
            elif export_format.lower() == "csv":
                success, message, filepath = self._export_csv(
                    report_data, export_id, timestamp
                )
            elif export_format.lower() == "excel":
                success, message, filepath = self._export_excel(
                    report_data, export_id, timestamp
                )
            elif export_format.lower() == "html":
                success, message, filepath = self._export_html(
                    report_data, export_id, timestamp, template_id
                )
            elif export_format.lower() == "pdf":
                success, message, filepath = self._export_pdf(
                    report_data, export_id, timestamp, template_id
                )
            else:
                return False, f"不支援的匯出格式: {export_format}", None

            # 更新匯出狀態
            if success:
                self._log_export_success(export_id, filepath)
            else:
                self._log_export_failure(export_id, message)

            return success, message, filepath

        except Exception as e:
            logger.error("匯出報表失敗: %s", e)
            self._log_export_failure(export_id, str(e))
            return False, f"匯出失敗: {e}", None

    def _export_json(
        self, report_data: Dict[str, Any], export_id: str, timestamp: str
    ) -> Tuple[bool, str, str]:
        """匯出為 JSON 格式
        
        Args:
            report_data: 報表數據
            export_id: 匯出ID
            timestamp: 時間戳
            
        Returns:
            (成功標誌, 訊息, 檔案路徑)
        """
        try:
            filename = f"report_{timestamp}_{export_id[:8]}.json"
            filepath = self.export_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)

            file_size = filepath.stat().st_size
            return (
                True,
                f"JSON 報表匯出成功，檔案大小: {file_size} bytes",
                str(filepath),
            )

        except Exception as e:
            logger.error("JSON 匯出失敗: %s", e)
            return False, f"JSON 匯出失敗: {e}", ""

    def _export_csv(
        self, report_data: Dict[str, Any], export_id: str, timestamp: str
    ) -> Tuple[bool, str, str]:
        """匯出為 CSV 格式
        
        Args:
            report_data: 報表數據
            export_id: 匯出ID
            timestamp: 時間戳
            
        Returns:
            (成功標誌, 訊息, 檔案路徑)
        """
        try:
            filename = f"report_{timestamp}_{export_id[:8]}.csv"
            filepath = self.export_dir / filename

            # 如果數據包含 DataFrame 可序列化的部分
            if "data" in report_data and isinstance(report_data["data"], list):
                df = pd.DataFrame(report_data["data"])
                df.to_csv(filepath, index=False, encoding="utf-8-sig")
            else:
                # 將字典轉換為 DataFrame
                df = pd.DataFrame([report_data])
                df.to_csv(filepath, index=False, encoding="utf-8-sig")

            file_size = filepath.stat().st_size
            return (
                True,
                f"CSV 報表匯出成功，檔案大小: {file_size} bytes",
                str(filepath),
            )

        except Exception as e:
            logger.error("CSV 匯出失敗: %s", e)
            return False, f"CSV 匯出失敗: {e}", ""

    def _export_excel(
        self, report_data: Dict[str, Any], export_id: str, timestamp: str
    ) -> Tuple[bool, str, str]:
        """匯出為 Excel 格式
        
        Args:
            report_data: 報表數據
            export_id: 匯出ID
            timestamp: 時間戳
            
        Returns:
            (成功標誌, 訊息, 檔案路徑)
        """
        try:
            filename = f"report_{timestamp}_{export_id[:8]}.xlsx"
            filepath = self.export_dir / filename

            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
                # 如果有數據表格
                if "data" in report_data and isinstance(report_data["data"], list):
                    df = pd.DataFrame(report_data["data"])
                    df.to_excel(writer, sheet_name="數據", index=False)

                # 如果有指標數據
                if "metrics" in report_data:
                    metrics_df = pd.DataFrame([report_data["metrics"]])
                    metrics_df.to_excel(writer, sheet_name="指標", index=False)

                # 如果有統計數據
                if "statistics" in report_data:
                    stats_df = pd.DataFrame([report_data["statistics"]])
                    stats_df.to_excel(writer, sheet_name="統計", index=False)

            file_size = filepath.stat().st_size
            return (
                True,
                f"Excel 報表匯出成功，檔案大小: {file_size} bytes",
                str(filepath),
            )

        except Exception as e:
            logger.error("Excel 匯出失敗: %s", e)
            return False, f"Excel 匯出失敗: {e}", ""

    def _export_html(
        self,
        report_data: Dict[str, Any],
        export_id: str,
        timestamp: str,
        template_id: Optional[str] = None,
    ) -> Tuple[bool, str, str]:
        """匯出為 HTML 格式
        
        Args:
            report_data: 報表數據
            export_id: 匯出ID
            timestamp: 時間戳
            template_id: 模板ID
            
        Returns:
            (成功標誌, 訊息, 檔案路徑)
        """
        try:
            filename = f"report_{timestamp}_{export_id[:8]}.html"
            filepath = self.export_dir / filename

            # 生成 HTML 內容
            html_content = self._generate_html_content(report_data, template_id)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_content)

            file_size = filepath.stat().st_size
            return (
                True,
                f"HTML 報表匯出成功，檔案大小: {file_size} bytes",
                str(filepath),
            )

        except Exception as e:
            logger.error("HTML 匯出失敗: %s", e)
            return False, f"HTML 匯出失敗: {e}", ""

    def _export_pdf(
        self,
        report_data: Dict[str, Any],
        export_id: str,
        timestamp: str,
        template_id: Optional[str] = None,
    ) -> Tuple[bool, str, str]:
        """匯出為 PDF 格式
        
        Args:
            report_data: 報表數據
            export_id: 匯出ID
            timestamp: 時間戳
            template_id: 模板ID
            
        Returns:
            (成功標誌, 訊息, 檔案路徑)
        """
        try:
            # 注意：這裡需要安裝 weasyprint 或其他 PDF 生成庫
            # 目前提供基本實現
            filename = f"report_{timestamp}_{export_id[:8]}.pdf"
            filepath = self.export_dir / filename

            # 先生成 HTML，然後轉換為 PDF
            html_content = self._generate_html_content(report_data, template_id)

            # 這裡應該使用 PDF 生成庫，暫時保存為 HTML
            with open(filepath.with_suffix(".html"), "w", encoding="utf-8") as f:
                f.write(html_content)

            return (
                True,
                f"PDF 報表匯出成功（暫存為 HTML），檔案: {filepath.with_suffix('.html')}",
                str(filepath.with_suffix(".html")),
            )

        except Exception as e:
            logger.error("PDF 匯出失敗: %s", e)
            return False, f"PDF 匯出失敗: {e}", ""

    def _generate_html_content(
        self, report_data: Dict[str, Any], template_id: Optional[str] = None
    ) -> str:
        """生成 HTML 內容
        
        Args:
            report_data: 報表數據
            template_id: 模板ID
            
        Returns:
            HTML 內容字串
        """
        # 基本 HTML 模板
        html_template = """
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>交易報表</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .metrics {{ 
                    display: grid; 
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                    gap: 20px; 
                    margin-bottom: 30px; 
                }}
                .metric-card {{ 
                    border: 1px solid #ddd; 
                    padding: 15px; 
                    border-radius: 5px; 
                    text-align: center; 
                }}
                .metric-value {{ 
                    font-size: 24px; 
                    font-weight: bold; 
                    color: #333; 
                }}
                .metric-label {{ 
                    font-size: 14px; 
                    color: #666; 
                    margin-top: 5px; 
                }}
                table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin-top: 20px; 
                }}
                th, td {{ 
                    border: 1px solid #ddd; 
                    padding: 8px; 
                    text-align: left; 
                }}
                th {{ background-color: #f2f2f2; }}
                .footer {{ 
                    margin-top: 30px; 
                    text-align: center; 
                    color: #666; 
                    font-size: 12px; 
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>交易績效報表</h1>
                <p>生成時間: {timestamp}</p>
            </div>
            
            {metrics_section}
            {data_section}
            
            <div class="footer">
                <p>此報表由自動交易系統生成</p>
            </div>
        </body>
        </html>
        """

        # 生成指標區塊
        metrics_section = ""
        if "metrics" in report_data:
            metrics = report_data["metrics"]
            metrics_section = "<div class='metrics'>"
            for key, value in metrics.items():
                metrics_section += f"""
                <div class="metric-card">
                    <div class="metric-value">{value}</div>
                    <div class="metric-label">{key}</div>
                </div>
                """
            metrics_section += "</div>"

        # 生成數據表格
        data_section = ""
        if "data" in report_data and isinstance(report_data["data"], list):
            df = pd.DataFrame(report_data["data"])
            if not df.empty:
                html_table = df.to_html(
                    index=False, classes='data-table'
                )
                data_section = f"<h2>交易明細</h2>{html_table}"

        return html_template.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            metrics_section=metrics_section,
            data_section=data_section,
        )

    def _log_export_start(self, export_id: str, export_format: str, user_id: str):
        """記錄匯出開始"""
        try:
            with self.session_factory() as session:
                export_log = ExportLog(
                    export_id=export_id,
                    export_format=export_format,
                    user_id=user_id,
                    status="processing",
                    created_at=datetime.now(),
                )
                session.add(export_log)
                session.commit()
        except Exception as e:
            logger.error("記錄匯出開始失敗: %s", e)

    def _log_export_success(self, export_id: str, filepath: str):
        """記錄匯出成功"""
        try:
            with self.session_factory() as session:
                export_log = (
                    session.query(ExportLog).filter_by(export_id=export_id).first()
                )
                if export_log:
                    export_log.status = "completed"
                    export_log.file_path = filepath
                    export_log.completed_at = datetime.now()
                    session.commit()
        except Exception as e:
            logger.error("記錄匯出成功失敗: %s", e)

    def _log_export_failure(self, export_id: str, error_message: str):
        """記錄匯出失敗"""
        try:
            with self.session_factory() as session:
                export_log = (
                    session.query(ExportLog).filter_by(export_id=export_id).first()
                )
                if export_log:
                    export_log.status = "failed"
                    export_log.error_message = error_message
                    export_log.completed_at = datetime.now()
                    session.commit()
        except Exception as update_error:
            logger.error("記錄匯出失敗失敗: %s", update_error)
