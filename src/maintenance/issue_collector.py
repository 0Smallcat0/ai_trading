"""
問題收集模組

此模組用於收集和分析系統中的已知問題和異常，並生成報告。
"""

import datetime
import glob
import json
import logging
import os
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List

# 導入日誌模組
try:
    from src.logging import LogCategory, get_logger

    logger = get_logger("issue_collector", category=LogCategory.SYSTEM)
except ImportError:
    # 如果無法導入自定義日誌模組，則使用標準日誌模組
    logger = logging.getLogger("issue_collector")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)

# 導入配置
try:
    from src.config import LOGS_DIR, REPORTS_DIR
except ImportError:
    # 如果無法導入配置，則使用默認值
    LOGS_DIR = os.path.join(os.getcwd(), "logs")
    REPORTS_DIR = os.path.join(os.getcwd(), "reports")


class IssueCollector:
    """問題收集器類"""

    def __init__(
        self,
        logs_dir: str = LOGS_DIR,
        reports_dir: str = REPORTS_DIR,
        error_pattern: str = r"ERROR|CRITICAL|Exception|Error|Failed|Failure|Timeout|錯誤|失敗|異常|超時",
        max_log_size: int = 10 * 1024 * 1024,  # 10 MB
        max_logs_to_analyze: int = 100,
    ):
        """
        初始化問題收集器

        Args:
            logs_dir: 日誌目錄
            reports_dir: 報告目錄
            error_pattern: 錯誤模式正則表達式
            max_log_size: 最大日誌大小（字節）
            max_logs_to_analyze: 最大分析日誌數量
        """
        self.logs_dir = logs_dir
        self.reports_dir = reports_dir
        self.error_pattern = error_pattern
        self.max_log_size = max_log_size
        self.max_logs_to_analyze = max_logs_to_analyze

        # 創建報告目錄
        os.makedirs(reports_dir, exist_ok=True)

        # 初始化問題存儲
        self.issues: Dict[str, Dict[str, Any]] = {}
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.module_error_counts: Dict[str, int] = defaultdict(int)
        self.error_patterns: Dict[str, List[str]] = defaultdict(list)
        self.error_timestamps: Dict[str, List[float]] = defaultdict(list)

        logger.info(f"初始化問題收集器: 日誌目錄={logs_dir}, 報告目錄={reports_dir}")

    def collect_issues_from_logs(self) -> Dict[str, Dict[str, Any]]:
        """
        從日誌中收集問題

        Returns:
            Dict[str, Dict[str, Any]]: 問題字典
        """
        logger.info("開始從日誌中收集問題")

        # 獲取所有日誌文件
        log_files = []
        for ext in ["log", "json"]:
            log_files.extend(
                glob.glob(os.path.join(self.logs_dir, f"**/*.{ext}"), recursive=True)
            )

        # 按修改時間排序，最新的優先
        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        # 限制分析的日誌數量
        log_files = log_files[: self.max_logs_to_analyze]

        # 編譯錯誤模式
        error_regex = re.compile(self.error_pattern)

        # 分析日誌文件
        for log_file in log_files:
            try:
                # 檢查文件大小
                if os.path.getsize(log_file) > self.max_log_size:
                    logger.warning(f"日誌文件 {log_file} 太大，跳過分析")
                    continue

                logger.info(f"分析日誌文件: {log_file}")

                # 讀取日誌文件
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        # 檢查是否是錯誤行
                        if error_regex.search(line):
                            # 嘗試解析 JSON 格式的日誌
                            try:
                                log_entry = json.loads(line)
                                self._process_json_log_entry(
                                    log_entry, log_file, line_num
                                )
                            except json.JSONDecodeError:
                                # 如果不是 JSON 格式，則作為文本處理
                                self._process_text_log_entry(line, log_file, line_num)
            except Exception as e:
                logger.error(f"分析日誌文件 {log_file} 時發生錯誤: {str(e)}")

        logger.info(f"從日誌中收集到 {len(self.issues)} 個問題")
        return self.issues

    def _process_json_log_entry(
        self, log_entry: Dict[str, Any], log_file: str, line_num: int
    ) -> None:
        """
        處理 JSON 格式的日誌條目

        Args:
            log_entry: 日誌條目
            log_file: 日誌文件
            line_num: 行號
        """
        # 檢查是否是錯誤級別
        level = log_entry.get("level", "").upper()
        if level not in ["ERROR", "CRITICAL"]:
            return

        # 獲取錯誤信息
        message = log_entry.get("message", "")
        if not message:
            return

        # 獲取錯誤類型
        error_type = "Unknown"
        if "exception" in log_entry:
            error_type = log_entry["exception"].get("type", "Unknown")

        # 獲取模組
        module = log_entry.get("logger", "").split(".")[0]
        if not module:
            module = "Unknown"

        # 獲取時間戳
        timestamp = log_entry.get("timestamp", "")
        if not timestamp:
            timestamp = log_entry.get("time", datetime.datetime.now().isoformat())

        # 創建問題 ID
        issue_id = f"{module}_{error_type}_{hash(message) % 10000:04d}"

        # 更新問題
        self._update_issue(
            issue_id, error_type, message, module, timestamp, log_file, line_num
        )

    def _process_text_log_entry(self, line: str, log_file: str, line_num: int) -> None:
        """
        處理文本格式的日誌條目

        Args:
            line: 日誌行
            log_file: 日誌文件
            line_num: 行號
        """
        # 嘗試從文本中提取錯誤信息
        error_match = re.search(
            r"(ERROR|CRITICAL|Exception|Error|Failed|Failure|Timeout|錯誤|失敗|異常|超時)[\s:]+(.+)",
            line,
        )
        if not error_match:
            return

        # 獲取錯誤類型和消息
        error_type = error_match.group(1)
        message = error_match.group(2).strip()

        # 嘗試從文件名中提取模組
        module_match = re.search(r"([a-zA-Z0-9_]+)\.log", os.path.basename(log_file))
        module = module_match.group(1) if module_match else "Unknown"

        # 嘗試從行中提取時間戳
        timestamp_match = re.search(
            r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)", line
        )
        timestamp = (
            timestamp_match.group(1)
            if timestamp_match
            else datetime.datetime.now().isoformat()
        )

        # 創建問題 ID
        issue_id = f"{module}_{error_type}_{hash(message) % 10000:04d}"

        # 更新問題
        self._update_issue(
            issue_id, error_type, message, module, timestamp, log_file, line_num
        )

    def _update_issue(
        self,
        issue_id: str,
        error_type: str,
        message: str,
        module: str,
        timestamp: str,
        log_file: str,
        line_num: int,
    ) -> None:
        """
        更新問題

        Args:
            issue_id: 問題 ID
            error_type: 錯誤類型
            message: 錯誤消息
            module: 模組
            timestamp: 時間戳
            log_file: 日誌文件
            line_num: 行號
        """
        # 更新錯誤計數
        self.error_counts[error_type] += 1
        self.module_error_counts[module] += 1

        # 更新錯誤模式
        self.error_patterns[error_type].append(message)

        # 更新錯誤時間戳
        try:
            dt = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            self.error_timestamps[error_type].append(dt.timestamp())
        except (ValueError, TypeError):
            pass

        # 如果問題已存在，則更新
        if issue_id in self.issues:
            issue = self.issues[issue_id]
            issue["count"] += 1
            issue["last_seen"] = timestamp
            issue["occurrences"].append(
                {
                    "file": log_file,
                    "line": line_num,
                    "timestamp": timestamp,
                }
            )

            # 限制出現次數列表大小
            if len(issue["occurrences"]) > 10:
                issue["occurrences"] = issue["occurrences"][-10:]
        else:
            # 創建新問題
            self.issues[issue_id] = {
                "id": issue_id,
                "type": error_type,
                "message": message,
                "module": module,
                "count": 1,
                "first_seen": timestamp,
                "last_seen": timestamp,
                "occurrences": [
                    {
                        "file": log_file,
                        "line": line_num,
                        "timestamp": timestamp,
                    }
                ],
            }

    def analyze_issues(self) -> Dict[str, Any]:
        """
        分析問題

        Returns:
            Dict[str, Any]: 分析結果
        """
        logger.info("開始分析問題")

        # 如果沒有問題，則先收集
        if not self.issues:
            self.collect_issues_from_logs()

        # 分析結果
        result = {
            "total_issues": len(self.issues),
            "total_errors": sum(self.error_counts.values()),
            "error_types": dict(self.error_counts),
            "module_errors": dict(self.module_error_counts),
            "top_issues": [],
            "recent_issues": [],
            "error_patterns": {},
            "error_frequency": {},
        }

        # 獲取前 10 個最常見的問題
        top_issues = sorted(
            self.issues.values(), key=lambda x: x["count"], reverse=True
        )[:10]
        result["top_issues"] = top_issues

        # 獲取前 10 個最近的問題
        recent_issues = sorted(
            self.issues.values(), key=lambda x: x["last_seen"], reverse=True
        )[:10]
        result["recent_issues"] = recent_issues

        # 分析錯誤模式
        for error_type, messages in self.error_patterns.items():
            # 獲取前 5 個最常見的錯誤消息
            counter = Counter(messages)
            result["error_patterns"][error_type] = [
                {"message": msg, "count": count}
                for msg, count in counter.most_common(5)
            ]

        # 分析錯誤頻率
        for error_type, timestamps in self.error_timestamps.items():
            if not timestamps:
                continue

            # 按小時分組
            hour_counts = defaultdict(int)
            for ts in timestamps:
                dt = datetime.datetime.fromtimestamp(ts)
                hour = dt.strftime("%Y-%m-%d %H:00")
                hour_counts[hour] += 1

            # 獲取前 24 小時的錯誤頻率
            sorted_hours = sorted(
                hour_counts.items(), key=lambda x: x[0], reverse=True
            )[:24]
            result["error_frequency"][error_type] = [
                {"hour": hour, "count": count}
                for hour, count in sorted(sorted_hours, key=lambda x: x[0])
            ]

        logger.info("問題分析完成")
        return result

    def generate_report(self, format: str = "json") -> str:
        """
        生成報告

        Args:
            format: 報告格式，支持 "json" 和 "markdown"

        Returns:
            str: 報告文件路徑
        """
        logger.info(f"開始生成 {format} 格式的報告")

        # 分析問題
        analysis = self.analyze_issues()

        # 生成報告文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(
            self.reports_dir, f"issue_report_{timestamp}.{format}"
        )

        # 生成報告
        if format == "json":
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "issues": list(self.issues.values()),
                        "analysis": analysis,
                        "generated_at": datetime.datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        elif format == "markdown":
            with open(report_file, "w", encoding="utf-8") as f:
                f.write("# 系統問題報告\n\n")
                f.write(f"生成時間: {datetime.datetime.now().isoformat()}\n\n")

                f.write("## 問題概述\n\n")
                f.write(f"- 總問題數: {analysis['total_issues']}\n")
                f.write(f"- 總錯誤數: {analysis['total_errors']}\n\n")

                f.write("### 錯誤類型分佈\n\n")
                f.write("| 錯誤類型 | 數量 |\n")
                f.write("|---------|------|\n")
                for error_type, count in analysis["error_types"].items():
                    f.write(f"| {error_type} | {count} |\n")
                f.write("\n")

                f.write("### 模組錯誤分佈\n\n")
                f.write("| 模組 | 錯誤數 |\n")
                f.write("|------|--------|\n")
                for module, count in analysis["module_errors"].items():
                    f.write(f"| {module} | {count} |\n")
                f.write("\n")

                f.write("## 常見問題\n\n")
                for i, issue in enumerate(analysis["top_issues"], 1):
                    f.write(f"### {i}. {issue['type']} in {issue['module']}\n\n")
                    f.write(f"- ID: {issue['id']}\n")
                    f.write(f"- 消息: {issue['message']}\n")
                    f.write(f"- 出現次數: {issue['count']}\n")
                    f.write(f"- 首次出現: {issue['first_seen']}\n")
                    f.write(f"- 最後出現: {issue['last_seen']}\n\n")

                f.write("## 最近問題\n\n")
                for i, issue in enumerate(analysis["recent_issues"], 1):
                    f.write(f"### {i}. {issue['type']} in {issue['module']}\n\n")
                    f.write(f"- ID: {issue['id']}\n")
                    f.write(f"- 消息: {issue['message']}\n")
                    f.write(f"- 出現次數: {issue['count']}\n")
                    f.write(f"- 首次出現: {issue['first_seen']}\n")
                    f.write(f"- 最後出現: {issue['last_seen']}\n\n")
        else:
            raise ValueError(f"不支持的報告格式: {format}")

        logger.info(f"報告已生成: {report_file}")
        return report_file


def main():
    """主函數"""
    import argparse

    # 解析命令行參數
    parser = argparse.ArgumentParser(description="收集和分析系統問題")
    parser.add_argument("--logs-dir", default=LOGS_DIR, help="日誌目錄")
    parser.add_argument("--reports-dir", default=REPORTS_DIR, help="報告目錄")
    parser.add_argument(
        "--format", choices=["json", "markdown"], default="markdown", help="報告格式"
    )
    args = parser.parse_args()

    # 創建問題收集器
    collector = IssueCollector(logs_dir=args.logs_dir, reports_dir=args.reports_dir)

    # 收集問題
    collector.collect_issues_from_logs()

    # 生成報告
    report_file = collector.generate_report(format=args.format)

    print(f"報告已生成: {report_file}")


if __name__ == "__main__":
    main()
