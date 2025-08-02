"""
日誌分析模組

此模組提供日誌分析功能，用於分析日誌數據。
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# 可選依賴處理
try:
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None

    # 為了類型提示，定義一個假的 Figure 類型
    class Figure:
        pass


from src.log_system.config import LOG_DIRS


class LogAnalyzer:
    """日誌分析器"""

    def __init__(self, log_dirs: Optional[Dict[str, str]] = None):
        """
        初始化分析器

        Args:
            log_dirs: 日誌目錄
        """
        self.log_dirs = log_dirs or LOG_DIRS

    def load_logs(
        self,
        category: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[str] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        載入日誌

        Args:
            category: 日誌類別
            start_time: 開始時間
            end_time: 結束時間
            level: 日誌級別
            limit: 限制數量

        Returns:
            pd.DataFrame: 日誌數據
        """
        # 確定日誌目錄
        if category:
            log_dirs = [
                self.log_dirs.get(
                    category,
                    os.path.join(
                        os.path.dirname(list(self.log_dirs.values())[0]), category
                    ),
                )
            ]
        else:
            log_dirs = list(self.log_dirs.values())

        # 載入日誌
        logs = []
        for log_dir in log_dirs:
            if not os.path.exists(log_dir):
                continue

            # 遍歷日誌文件
            for file_name in os.listdir(log_dir):
                if not file_name.endswith(".log"):
                    continue

                file_path = os.path.join(log_dir, file_name)
                logs.extend(
                    self._load_log_file(
                        file_path, start_time, end_time, level, limit - len(logs)
                    )
                )

                # 檢查是否達到限制
                if len(logs) >= limit:
                    break

            # 檢查是否達到限制
            if len(logs) >= limit:
                break

        # 創建數據框
        if logs:
            df = pd.DataFrame(logs)

            # 轉換時間戳
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])

            # 排序
            if "timestamp" in df.columns:
                df = df.sort_values("timestamp", ascending=False)

            return df
        else:
            return pd.DataFrame()

    def _load_log_file(
        self,
        file_path: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        載入日誌文件

        Args:
            file_path: 文件路徑
            start_time: 開始時間
            end_time: 結束時間
            level: 日誌級別
            limit: 限制數量

        Returns:
            List[Dict[str, Any]]: 日誌數據
        """
        logs = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    # 檢查是否達到限制
                    if len(logs) >= limit:
                        break

                    # 解析日誌
                    try:
                        log = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # 檢查級別
                    if level and log.get("level") != level:
                        continue

                    # 檢查時間
                    if "timestamp" in log:
                        log_time = datetime.fromisoformat(
                            log["timestamp"].replace("Z", "+00:00")
                        )
                        if start_time and log_time < start_time:
                            continue
                        if end_time and log_time > end_time:
                            continue

                    # 添加日誌
                    logs.append(log)
        except Exception as e:
            print(f"載入日誌文件時發生錯誤: {e}")

        return logs

    def count_logs_by_level(
        self,
        category: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """
        按級別統計日誌

        Args:
            category: 日誌類別
            start_time: 開始時間
            end_time: 結束時間

        Returns:
            Dict[str, int]: 日誌統計
        """
        # 載入日誌
        df = self.load_logs(category, start_time, end_time, limit=10000)

        # 統計日誌
        if not df.empty and "level" in df.columns:
            return dict(df["level"].value_counts())
        else:
            return {}

    def count_logs_by_category(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """
        按類別統計日誌

        Args:
            start_time: 開始時間
            end_time: 結束時間

        Returns:
            Dict[str, int]: 日誌統計
        """
        # 載入日誌
        df = self.load_logs(start_time=start_time, end_time=end_time, limit=10000)

        # 統計日誌
        if not df.empty and "category" in df.columns:
            return dict(df["category"].value_counts())
        else:
            return {}

    def count_logs_by_time(
        self,
        category: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        interval: str = "1H",
    ) -> Dict[str, int]:
        """
        按時間統計日誌

        Args:
            category: 日誌類別
            level: 日誌級別
            start_time: 開始時間
            end_time: 結束時間
            interval: 時間間隔

        Returns:
            Dict[str, int]: 日誌統計
        """
        # 載入日誌
        df = self.load_logs(category, start_time, end_time, level, limit=10000)

        # 統計日誌
        if not df.empty and "timestamp" in df.columns:
            # 按時間間隔分組
            df["time_group"] = df["timestamp"].dt.floor(interval)
            counts = df.groupby("time_group").size()
            return {str(k): v for k, v in counts.items()}
        else:
            return {}

    def find_errors(
        self,
        category: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        查找錯誤

        Args:
            category: 日誌類別
            start_time: 開始時間
            end_time: 結束時間
            limit: 限制數量

        Returns:
            pd.DataFrame: 錯誤日誌
        """
        # 載入日誌
        df = self.load_logs(category, start_time, end_time, level="ERROR", limit=limit)

        return df

    def find_slow_operations(
        self,
        category: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        threshold: float = 1.0,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        查找慢操作

        Args:
            category: 日誌類別
            start_time: 開始時間
            end_time: 結束時間
            threshold: 閾值（秒）
            limit: 限制數量

        Returns:
            pd.DataFrame: 慢操作日誌
        """
        # 載入日誌
        df = self.load_logs(category, start_time, end_time, limit=10000)

        # 查找慢操作
        if not df.empty:
            # 檢查是否有執行時間
            if "data" in df.columns:
                # 提取執行時間
                df["execution_time"] = df["data"].apply(
                    lambda x: x.get("execution_time") if isinstance(x, dict) else None
                )

                # 過濾慢操作
                slow_df = df[df["execution_time"] >= threshold].sort_values(
                    "execution_time", ascending=False
                )

                return slow_df.head(limit)

        return pd.DataFrame()

    def plot_logs_by_level(
        self,
        category: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        figsize: Tuple[int, int] = (10, 6),
    ) -> Figure:
        """
        繪製日誌級別分佈圖

        Args:
            category: 日誌類別
            start_time: 開始時間
            end_time: 結束時間
            figsize: 圖形大小

        Returns:
            Figure: 圖形
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib 不可用，無法繪製圖表")

        # 統計日誌
        counts = self.count_logs_by_level(category, start_time, end_time)

        # 繪製圖形
        fig, ax = plt.subplots(figsize=figsize)
        ax.bar(counts.keys(), counts.values())
        ax.set_title("日誌級別分佈")
        ax.set_xlabel("級別")
        ax.set_ylabel("數量")

        return fig

    def plot_logs_by_category(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        figsize: Tuple[int, int] = (10, 6),
    ) -> Figure:
        """
        繪製日誌類別分佈圖

        Args:
            start_time: 開始時間
            end_time: 結束時間
            figsize: 圖形大小

        Returns:
            Figure: 圖形
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib 不可用，無法繪製圖表")

        # 統計日誌
        counts = self.count_logs_by_category(start_time, end_time)

        # 繪製圖形
        fig, ax = plt.subplots(figsize=figsize)
        ax.bar(counts.keys(), counts.values())
        ax.set_title("日誌類別分佈")
        ax.set_xlabel("類別")
        ax.set_ylabel("數量")

        return fig

    def plot_logs_by_time(
        self,
        category: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        interval: str = "1H",
        figsize: Tuple[int, int] = (10, 6),
    ) -> Figure:
        """
        繪製日誌時間分佈圖

        Args:
            category: 日誌類別
            level: 日誌級別
            start_time: 開始時間
            end_time: 結束時間
            interval: 時間間隔
            figsize: 圖形大小

        Returns:
            Figure: 圖形
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib 不可用，無法繪製圖表")

        # 統計日誌
        counts = self.count_logs_by_time(
            category, level, start_time, end_time, interval
        )

        # 繪製圖形
        fig, ax = plt.subplots(figsize=figsize)
        times = [
            datetime.fromisoformat(k.replace("Z", "+00:00")) for k in counts.keys()
        ]
        ax.plot(times, list(counts.values()))
        ax.set_title("日誌時間分佈")
        ax.set_xlabel("時間")
        ax.set_ylabel("數量")

        return fig

    def detect_anomalies(
        self,
        category: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        threshold_multiplier: float = 2.0,
    ) -> Dict[str, Any]:
        """
        檢測異常行為

        Args:
            category: 日誌類別
            start_time: 開始時間
            end_time: 結束時間
            threshold_multiplier: 閾值倍數

        Returns:
            Dict[str, Any]: 異常檢測結果
        """
        # 載入日誌
        df = self.load_logs(category, start_time, end_time, limit=10000)

        anomalies = {
            "error_spikes": [],
            "unusual_patterns": [],
            "performance_issues": [],
            "security_concerns": [],
        }

        if df.empty:
            return anomalies

        # 檢測錯誤激增
        if "level" in df.columns and "timestamp" in df.columns:
            error_df = df[df["level"] == "ERROR"]
            if not error_df.empty:
                # 按小時統計錯誤數量
                error_df["hour"] = error_df["timestamp"].dt.floor("H")
                hourly_errors = error_df.groupby("hour").size()

                if len(hourly_errors) > 1:
                    mean_errors = hourly_errors.mean()
                    std_errors = hourly_errors.std()
                    threshold = mean_errors + (threshold_multiplier * std_errors)

                    for hour, count in hourly_errors.items():
                        if count > threshold:
                            anomalies["error_spikes"].append(
                                {
                                    "time": hour.isoformat(),
                                    "error_count": int(count),
                                    "threshold": threshold,
                                    "severity": (
                                        "high" if count > threshold * 1.5 else "medium"
                                    ),
                                }
                            )

        # 檢測異常模式
        anomalies["unusual_patterns"] = self._detect_unusual_patterns(df)

        # 檢測效能問題
        anomalies["performance_issues"] = self._detect_performance_issues(df)

        # 檢測安全問題
        anomalies["security_concerns"] = self._detect_security_concerns(df)

        return anomalies

    def _detect_unusual_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """檢測異常模式"""
        patterns = []

        if "message" in df.columns:
            # 檢測重複錯誤訊息
            message_counts = df["message"].value_counts()
            for message, count in message_counts.head(10).items():
                if count > 50:  # 超過50次的重複訊息
                    patterns.append(
                        {
                            "type": "repeated_message",
                            "message": (
                                message[:100] + "..." if len(message) > 100 else message
                            ),
                            "count": int(count),
                            "severity": "high" if count > 100 else "medium",
                        }
                    )

        return patterns

    def _detect_performance_issues(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """檢測效能問題"""
        issues = []

        # 檢查是否有執行時間資料
        if "data" in df.columns:
            for _, row in df.iterrows():
                if isinstance(row["data"], dict):
                    execution_time = row["data"].get("execution_time")
                    if execution_time and execution_time > 5.0:  # 超過5秒
                        issues.append(
                            {
                                "type": "slow_operation",
                                "timestamp": (
                                    row.get("timestamp", "").isoformat()
                                    if hasattr(row.get("timestamp", ""), "isoformat")
                                    else str(row.get("timestamp", ""))
                                ),
                                "execution_time": execution_time,
                                "operation": row["data"].get("operation", "unknown"),
                                "severity": (
                                    "critical" if execution_time > 10.0 else "high"
                                ),
                            }
                        )

        return issues

    def _detect_security_concerns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """檢測安全問題"""
        concerns = []

        if "message" in df.columns:
            security_keywords = [
                "unauthorized",
                "forbidden",
                "access denied",
                "authentication failed",
                "invalid token",
                "suspicious",
                "attack",
                "injection",
                "malicious",
            ]

            for _, row in df.iterrows():
                message = str(row["message"]).lower()
                for keyword in security_keywords:
                    if keyword in message:
                        concerns.append(
                            {
                                "type": "security_alert",
                                "timestamp": (
                                    row.get("timestamp", "").isoformat()
                                    if hasattr(row.get("timestamp", ""), "isoformat")
                                    else str(row.get("timestamp", ""))
                                ),
                                "keyword": keyword,
                                "message": (
                                    str(row["message"])[:200] + "..."
                                    if len(str(row["message"])) > 200
                                    else str(row["message"])
                                ),
                                "level": row.get("level", "unknown"),
                                "severity": "critical",
                            }
                        )
                        break

        return concerns

    def generate_analysis_report(
        self,
        category: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        生成分析報告

        Args:
            category: 日誌類別
            start_time: 開始時間
            end_time: 結束時間

        Returns:
            Dict[str, Any]: 分析報告
        """
        # 載入日誌
        df = self.load_logs(category, start_time, end_time, limit=10000)

        report = {
            "report_id": f"log_analysis_{int(time.time())}",
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
            },
            "category": category,
            "total_logs": len(df),
            "summary": {},
            "anomalies": {},
            "recommendations": [],
        }

        if not df.empty:
            # 基本統計
            report["summary"] = {
                "by_level": self.count_logs_by_level(category, start_time, end_time),
                "by_time": self.count_logs_by_time(
                    category, None, start_time, end_time, "1H"
                ),
                "error_logs": (
                    len(df[df.get("level", "") == "ERROR"])
                    if "level" in df.columns
                    else 0
                ),
                "warning_logs": (
                    len(df[df.get("level", "") == "WARNING"])
                    if "level" in df.columns
                    else 0
                ),
            }

            # 異常檢測
            report["anomalies"] = self.detect_anomalies(category, start_time, end_time)

            # 生成建議
            report["recommendations"] = self._generate_recommendations(report)

        return report

    def _generate_recommendations(self, report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成建議"""
        recommendations = []

        # 檢查錯誤率
        total_logs = report["total_logs"]
        error_logs = report["summary"].get("error_logs", 0)

        if total_logs > 0:
            error_rate = error_logs / total_logs
            if error_rate > 0.1:  # 錯誤率超過10%
                recommendations.append(
                    {
                        "type": "high_error_rate",
                        "priority": "high",
                        "description": f"錯誤率過高 ({error_rate:.1%})，建議檢查系統穩定性",
                        "action": "檢查錯誤日誌並修復相關問題",
                    }
                )

        # 檢查異常
        anomalies = report["anomalies"]

        if anomalies.get("error_spikes"):
            recommendations.append(
                {
                    "type": "error_spikes",
                    "priority": "high",
                    "description": "檢測到錯誤激增，可能存在系統問題",
                    "action": "調查錯誤激增的原因並採取修復措施",
                }
            )

        if anomalies.get("performance_issues"):
            recommendations.append(
                {
                    "type": "performance_issues",
                    "priority": "medium",
                    "description": "檢測到效能問題，建議優化相關操作",
                    "action": "分析慢操作並進行效能優化",
                }
            )

        if anomalies.get("security_concerns"):
            recommendations.append(
                {
                    "type": "security_concerns",
                    "priority": "critical",
                    "description": "檢測到安全問題，需要立即處理",
                    "action": "檢查安全日誌並加強安全措施",
                }
            )

        return recommendations
