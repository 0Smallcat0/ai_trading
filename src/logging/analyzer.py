"""
日誌分析模組

此模組提供日誌分析功能，用於分析日誌數據。
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from src.logging.config import LOG_DIRS


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
