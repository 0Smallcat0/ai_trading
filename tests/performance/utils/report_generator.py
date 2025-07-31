"""
效能測試報告生成器

此模組提供效能測試報告的生成功能，支援 HTML 和 JSON 格式。
"""

import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import List

from .memory_profiler import MemoryLeakResult
from .performance_monitor import PerformanceResult


class ReportGenerator:
    """效能測試報告生成器"""

    def __init__(self, output_dir: str = "tests/performance/reports"):
        """
        初始化報告生成器

        Args:
            output_dir: 報告輸出目錄
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_performance_report(
        self,
        results: List[PerformanceResult],
        report_name: str = "performance_report",
        format_type: str = "html",
    ) -> str:
        """
        生成效能測試報告

        Args:
            results: 效能測試結果列表
            report_name: 報告名稱
            format_type: 報告格式 ('html' 或 'json')

        Returns:
            str: 報告檔案路徑
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_name}_{timestamp}.{format_type}"
        filepath = self.output_dir / filename

        if format_type.lower() == "html":
            content = self._generate_html_report(results)
        elif format_type.lower() == "json":
            content = self._generate_json_report(results)
        else:
            raise ValueError(f"不支援的報告格式: {format_type}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return str(filepath)

    def generate_memory_report(
        self,
        results: List[MemoryLeakResult],
        report_name: str = "memory_report",
        format_type: str = "html",
    ) -> str:
        """
        生成記憶體測試報告

        Args:
            results: 記憶體測試結果列表
            report_name: 報告名稱
            format_type: 報告格式

        Returns:
            str: 報告檔案路徑
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_name}_{timestamp}.{format_type}"
        filepath = self.output_dir / filename

        if format_type.lower() == "html":
            content = self._generate_memory_html_report(results)
        elif format_type.lower() == "json":
            content = self._generate_memory_json_report(results)
        else:
            raise ValueError(f"不支援的報告格式: {format_type}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return str(filepath)

    def _generate_html_report(self, results: List[PerformanceResult]) -> str:
        """生成 HTML 效能報告"""
        # 計算總體統計
        total_requests = sum(r.total_requests for r in results)
        total_successful = sum(r.successful_requests for r in results)
        total_failed = sum(r.failed_requests for r in results)
        avg_response_time = statistics.mean([r.avg_response_time for r in results])
        avg_throughput = statistics.mean([r.throughput for r in results])

        html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>效能測試報告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .metric {{ text-align: center; padding: 15px; background-color: #e9e9e9; border-radius: 5px; }}
        .metric h3 {{ margin: 0; color: #333; }}
        .metric p {{ margin: 5px 0; font-size: 24px; font-weight: bold; color: #007bff; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        .warning {{ color: orange; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 API 效能測試報告</h1>
        <p>生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>測試項目數量: {len(results)}</p>
    </div>

    <div class="summary">
        <div class="metric">
            <h3>總請求數</h3>
            <p>{total_requests:,}</p>
        </div>
        <div class="metric">
            <h3>成功率</h3>
            <p>{(total_successful/total_requests*100):.1f}%</p>
        </div>
        <div class="metric">
            <h3>平均回應時間</h3>
            <p>{avg_response_time:.1f}ms</p>
        </div>
        <div class="metric">
            <h3>平均吞吐量</h3>
            <p>{avg_throughput:.1f} req/s</p>
        </div>
    </div>

    <h2>📊 詳細測試結果</h2>
    <table>
        <thead>
            <tr>
                <th>測試名稱</th>
                <th>持續時間(s)</th>
                <th>總請求數</th>
                <th>成功請求</th>
                <th>失敗請求</th>
                <th>平均回應時間(ms)</th>
                <th>P95回應時間(ms)</th>
                <th>P99回應時間(ms)</th>
                <th>吞吐量(req/s)</th>
                <th>狀態</th>
            </tr>
        </thead>
        <tbody>
"""

        for result in results:
            status_class = (
                "pass"
                if result.avg_response_time < 100
                else "fail" if result.avg_response_time > 200 else "warning"
            )
            status_text = (
                "✅ 通過"
                if result.avg_response_time < 100
                else "❌ 失敗" if result.avg_response_time > 200 else "⚠️ 警告"
            )

            html_content += f"""
            <tr>
                <td>{result.test_name}</td>
                <td>{result.duration:.1f}</td>
                <td>{result.total_requests:,}</td>
                <td>{result.successful_requests:,}</td>
                <td>{result.failed_requests:,}</td>
                <td>{result.avg_response_time:.1f}</td>
                <td>{result.p95_response_time:.1f}</td>
                <td>{result.p99_response_time:.1f}</td>
                <td>{result.throughput:.1f}</td>
                <td class="{status_class}">{status_text}</td>
            </tr>
"""

        html_content += """
        </tbody>
    </table>

    <h2>🔍 錯誤分析</h2>
"""

        # 錯誤分析
        all_errors = []
        for result in results:
            all_errors.extend(result.errors)

        if all_errors:
            error_counts = {}
            for error in all_errors:
                error_counts[error] = error_counts.get(error, 0) + 1

            html_content += "<ul>"
            for error, count in sorted(
                error_counts.items(), key=lambda x: x[1], reverse=True
            ):
                html_content += f"<li><strong>{error}</strong>: {count} 次</li>"
            html_content += "</ul>"
        else:
            html_content += "<p>✅ 沒有發現錯誤</p>"

        html_content += """
    <h2>📈 效能建議</h2>
    <ul>
"""

        # 效能建議
        if avg_response_time > 100:
            html_content += "<li>⚠️ 平均回應時間超過 100ms，建議優化 API 效能</li>"
        if total_failed > 0:
            html_content += (
                f"<li>❌ 發現 {total_failed} 個失敗請求，需要檢查錯誤原因</li>"
            )
        if avg_throughput < 50:
            html_content += "<li>⚠️ 吞吐量較低，建議檢查系統瓶頸</li>"

        html_content += """
    </ul>
</body>
</html>
"""

        return html_content

    def _generate_json_report(self, results: List[PerformanceResult]) -> str:
        """生成 JSON 效能報告"""
        report_data = {
            "report_info": {
                "generated_at": datetime.now().isoformat(),
                "test_count": len(results),
                "report_type": "performance",
            },
            "summary": {
                "total_requests": sum(r.total_requests for r in results),
                "total_successful": sum(r.successful_requests for r in results),
                "total_failed": sum(r.failed_requests for r in results),
                "avg_response_time": statistics.mean(
                    [r.avg_response_time for r in results]
                ),
                "avg_throughput": statistics.mean([r.throughput for r in results]),
            },
            "test_results": [],
        }

        for result in results:
            report_data["test_results"].append(
                {
                    "test_name": result.test_name,
                    "duration": result.duration,
                    "total_requests": result.total_requests,
                    "successful_requests": result.successful_requests,
                    "failed_requests": result.failed_requests,
                    "avg_response_time": result.avg_response_time,
                    "min_response_time": result.min_response_time,
                    "max_response_time": result.max_response_time,
                    "p95_response_time": result.p95_response_time,
                    "p99_response_time": result.p99_response_time,
                    "throughput": result.throughput,
                    "avg_memory_usage": result.avg_memory_usage,
                    "max_memory_usage": result.max_memory_usage,
                    "avg_cpu_usage": result.avg_cpu_usage,
                    "max_cpu_usage": result.max_cpu_usage,
                    "errors": result.errors,
                }
            )

        return json.dumps(report_data, indent=2, ensure_ascii=False)

    def _generate_memory_html_report(self, results: List[MemoryLeakResult]) -> str:
        """生成 HTML 記憶體報告"""
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>記憶體測試報告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .metric {{ text-align: center; padding: 15px; background-color: #e9e9e9; border-radius: 5px; }}
        .metric h3 {{ margin: 0; color: #333; }}
        .metric p {{ margin: 5px 0; font-size: 24px; font-weight: bold; color: #007bff; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .leak {{ color: red; }}
        .no-leak {{ color: green; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 記憶體洩漏測試報告</h1>
        <p>生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>測試項目數量: {len(results)}</p>
    </div>

    <h2>📊 測試結果</h2>
    <table>
        <thead>
            <tr>
                <th>測試名稱</th>
                <th>持續時間(s)</th>
                <th>初始記憶體(MB)</th>
                <th>最終記憶體(MB)</th>
                <th>峰值記憶體(MB)</th>
                <th>記憶體增長(MB)</th>
                <th>增長率(MB/h)</th>
                <th>洩漏狀態</th>
            </tr>
        </thead>
        <tbody>
"""

        for result in results:
            leak_class = "leak" if result.leak_detected else "no-leak"
            leak_status = "❌ 檢測到洩漏" if result.leak_detected else "✅ 無洩漏"

            html_content += f"""
            <tr>
                <td>{result.test_name}</td>
                <td>{result.duration:.1f}</td>
                <td>{result.initial_memory:.1f}</td>
                <td>{result.final_memory:.1f}</td>
                <td>{result.peak_memory:.1f}</td>
                <td>{result.memory_growth:.1f}</td>
                <td>{result.memory_growth_rate:.2f}</td>
                <td class="{leak_class}">{leak_status}</td>
            </tr>
"""

        html_content += """
        </tbody>
    </table>
</body>
</html>
"""

        return html_content

    def _generate_memory_json_report(self, results: List[MemoryLeakResult]) -> str:
        """生成 JSON 記憶體報告"""
        report_data = {
            "report_info": {
                "generated_at": datetime.now().isoformat(),
                "test_count": len(results),
                "report_type": "memory",
            },
            "test_results": [],
        }

        for result in results:
            report_data["test_results"].append(
                {
                    "test_name": result.test_name,
                    "duration": result.duration,
                    "initial_memory": result.initial_memory,
                    "final_memory": result.final_memory,
                    "peak_memory": result.peak_memory,
                    "memory_growth": result.memory_growth,
                    "memory_growth_rate": result.memory_growth_rate,
                    "leak_detected": result.leak_detected,
                    "top_allocations": result.top_allocations,
                }
            )

        return json.dumps(report_data, indent=2, ensure_ascii=False)
