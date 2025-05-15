"""
交易記錄與績效分析模組

此模組負責記錄交易活動，並提供績效分析功能，
幫助評估交易策略的表現，並提供改進的依據。

主要功能：
- 交易記錄
- 績效分析
- 報表生成
- 資料視覺化
- 結構化日誌
- 異常檢測
- 日誌分析
"""

import json
import logging
import os
import re
import socket
import sys
import time
import traceback
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv
from plotly.subplots import make_subplots

# 載入環境變數
load_dotenv()

# 設定日誌目錄
log_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs"
)
os.makedirs(log_dir, exist_ok=True)

# 創建子目錄
trade_log_dir = os.path.join(log_dir, "trades")
os.makedirs(trade_log_dir, exist_ok=True)

system_log_dir = os.path.join(log_dir, "system")
os.makedirs(system_log_dir, exist_ok=True)

error_log_dir = os.path.join(log_dir, "errors")
os.makedirs(error_log_dir, exist_ok=True)

# 定義日誌格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
JSON_LOG_FORMAT = {
    "timestamp": "%(asctime)s",
    "level": "%(levelname)s",
    "logger": "%(name)s",
    "message": "%(message)s",
    "module": "%(module)s",
    "function": "%(funcName)s",
    "line": "%(lineno)d",
    "thread": "%(threadName)s",
    "process": "%(process)d",
}


# 自定義JSON格式化器
class JsonFormatter(logging.Formatter):
    """JSON格式化器，將日誌格式化為JSON格式"""

    def __init__(self, fmt_dict=None):
    """
    __init__
    
    Args:
        fmt_dict: 
    """
        super(JsonFormatter, self).__init__()
        self.fmt_dict = fmt_dict if fmt_dict else JSON_LOG_FORMAT
        self.hostname = socket.gethostname()

    def format(self, record):
    """
    format
    
    Args:
        record: 
    """
        record_dict = self.fmt_dict.copy()

        # 填充記錄字典
        for key, value in record_dict.items():
            if (
                isinstance(value, str)
                and value.startswith("%(")
                and value.endswith(")s")
            ):
                attr_name = value[2:-2]
                if hasattr(record, attr_name):
                    record_dict[key] = getattr(record, attr_name)

        # 添加異常信息
        if record.exc_info:
            record_dict["exception"] = {
                "type": str(record.exc_info[0].__name__),
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # 添加額外數據
        if hasattr(record, "data") and record.data:
            record_dict["data"] = record.data

        # 添加主機名
        record_dict["hostname"] = self.hostname

        # 添加唯一ID
        record_dict["id"] = str(uuid.uuid4())

        return json.dumps(record_dict, ensure_ascii=False)


# 創建日誌處理器
def create_logger(
    name,
    log_file=None,
    level=logging.INFO,
    use_json=False,
    max_bytes=10 * 1024 * 1024,
    backup_count=5,
):
    """
    創建日誌記錄器

    Args:
        name (str): 日誌記錄器名稱
        log_file (str, optional): 日誌文件路徑
        level (int): 日誌級別
        use_json (bool): 是否使用JSON格式
        max_bytes (int): 日誌文件最大大小
        backup_count (int): 備份文件數量

    Returns:
        logging.Logger: 日誌記錄器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 清除現有處理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 創建控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # 創建文件處理器
    if log_file:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(level)

    # 設置格式化器
    if use_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(LOG_FORMAT)

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 創建主日誌記錄器
logger = create_logger(
    "trading_logger", os.path.join(log_dir, "trading.log"), level=logging.INFO
)

# 創建交易日誌記錄器
trade_logger = create_logger(
    "trade_logger",
    os.path.join(trade_log_dir, "trades.log"),
    level=logging.INFO,
    use_json=True,
)

# 創建系統日誌記錄器
system_logger = create_logger(
    "system_logger",
    os.path.join(system_log_dir, "system.log"),
    level=logging.INFO,
    use_json=True,
)

# 創建錯誤日誌記錄器
error_logger = create_logger(
    "error_logger",
    os.path.join(error_log_dir, "errors.log"),
    level=logging.ERROR,
    use_json=True,
)


# 添加額外數據的日誌函數
def log_with_data(logger, level, msg, data=None, exc_info=None):
    """
    記錄帶有額外數據的日誌

    Args:
        logger (logging.Logger): 日誌記錄器
        level (int): 日誌級別
        msg (str): 日誌消息
        data (dict, optional): 額外數據
        exc_info (tuple, optional): 異常信息
    """
    if data is None:
        data = {}

    # 創建自定義記錄
    record = logging.LogRecord(
        name=logger.name,
        level=level,
        pathname=sys._getframe(1).f_code.co_filename,
        lineno=sys._getframe(1).f_lineno,
        msg=msg,
        args=(),
        exc_info=exc_info,
    )

    # 添加額外數據
    record.data = data

    # 處理記錄
    for handler in logger.handlers:
        if record.levelno >= handler.level:
            handler.handle(record)


# 異常檢測類
class LogAnomalyDetector:
    """日誌異常檢測類，用於檢測日誌中的異常模式"""

    def __init__(self, log_file, patterns=None, threshold=5, window_size=3600):
        """
        初始化日誌異常檢測器

        Args:
            log_file (str): 日誌文件路徑
            patterns (list, optional): 異常模式列表
            threshold (int): 異常閾值
            window_size (int): 時間窗口大小（秒）
        """
        self.log_file = log_file
        self.patterns = patterns or [
            r"error",
            r"exception",
            r"fail",
            r"timeout",
            r"refused",
            r"denied",
            r"rejected",
        ]
        self.threshold = threshold
        self.window_size = window_size
        self.error_counts = {}
        self.last_check_time = time.time()

    def check_anomalies(self):
        """
        檢查日誌異常

        Returns:
            list: 異常列表
        """
        anomalies = []
        current_time = time.time()

        # 讀取日誌文件
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            system_logger.error(f"讀取日誌文件時發生錯誤: {e}")
            return anomalies

        # 過濾時間窗口內的日誌
        window_start_time = current_time - self.window_size
        window_logs = []

        for line in lines:
            try:
                # 嘗試解析JSON格式
                log_data = json.loads(line)
                log_time = datetime.strptime(
                    log_data["timestamp"], "%Y-%m-%d %H:%M:%S,%f"
                )
                log_timestamp = log_time.timestamp()

                if log_timestamp >= window_start_time:
                    window_logs.append(log_data)
            except:
                # 如果不是JSON格式，嘗試解析標準格式
                try:
                    log_time_str = line.split(" - ")[0]
                    log_time = datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S,%f")
                    log_timestamp = log_time.timestamp()

                    if log_timestamp >= window_start_time:
                        window_logs.append({"message": line, "timestamp": log_time_str})
                except:
                    # 如果無法解析時間，則跳過
                    continue

        # 檢查異常模式
        pattern_counts = {}

        for log in window_logs:
            message = log.get("message", "")

            for pattern in self.patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    if pattern not in pattern_counts:
                        pattern_counts[pattern] = 0
                    pattern_counts[pattern] += 1

        # 檢查是否超過閾值
        for pattern, count in pattern_counts.items():
            if count >= self.threshold:
                anomaly = {
                    "pattern": pattern,
                    "count": count,
                    "window_size": self.window_size,
                    "threshold": self.threshold,
                    "timestamp": datetime.now().isoformat(),
                }
                anomalies.append(anomaly)

                # 記錄異常
                system_logger.warning(
                    f"檢測到日誌異常: 模式 '{pattern}' 在 {self.window_size} 秒內出現 {count} 次",
                    extra={"data": anomaly},
                )

        self.last_check_time = current_time
        return anomalies


# 創建日誌異常檢測器
error_anomaly_detector = LogAnomalyDetector(
    os.path.join(error_log_dir, "errors.log"), threshold=3, window_size=1800
)


# 日誌分析類
class LogAnalyzer:
    """日誌分析類，用於分析日誌數據"""

    def __init__(self, log_files=None):
        """
        初始化日誌分析器

        Args:
            log_files (list, optional): 日誌文件路徑列表
        """
        self.log_files = log_files or []

    def add_log_file(self, log_file):
        """
        添加日誌文件

        Args:
            log_file (str): 日誌文件路徑
        """
        if log_file not in self.log_files:
            self.log_files.append(log_file)

    def parse_logs(self, start_time=None, end_time=None):
        """
        解析日誌

        Args:
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            list: 日誌列表
        """
        logs = []

        for log_file in self.log_files:
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line in lines:
                    try:
                        # 嘗試解析JSON格式
                        log_data = json.loads(line)
                        log_time = datetime.strptime(
                            log_data["timestamp"], "%Y-%m-%d %H:%M:%S,%f"
                        )

                        # 過濾時間範圍
                        if start_time and log_time < start_time:
                            continue
                        if end_time and log_time > end_time:
                            continue

                        logs.append(log_data)
                    except:
                        # 如果不是JSON格式，嘗試解析標準格式
                        try:
                            parts = line.split(" - ")
                            log_time_str = parts[0]
                            log_time = datetime.strptime(
                                log_time_str, "%Y-%m-%d %H:%M:%S,%f"
                            )

                            # 過濾時間範圍
                            if start_time and log_time < start_time:
                                continue
                            if end_time and log_time > end_time:
                                continue

                            log_data = {
                                "timestamp": log_time_str,
                                "level": parts[1] if len(parts) > 1 else "",
                                "logger": parts[2] if len(parts) > 2 else "",
                                "message": parts[3] if len(parts) > 3 else line,
                            }
                            logs.append(log_data)
                        except:
                            # 如果無法解析，則跳過
                            continue
            except Exception as e:
                system_logger.error(f"解析日誌文件 {log_file} 時發生錯誤: {e}")

        return logs

    def analyze_error_frequency(self, start_time=None, end_time=None):
        """
        分析錯誤頻率

        Args:
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            dict: 錯誤頻率統計
        """
        logs = self.parse_logs(start_time, end_time)

        # 過濾錯誤日誌
        error_logs = [log for log in logs if log.get("level") in ["ERROR", "CRITICAL"]]

        # 按小時統計錯誤數量
        error_counts = {}

        for log in error_logs:
            try:
                log_time = datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S,%f")
                hour_key = log_time.strftime("%Y-%m-%d %H:00:00")

                if hour_key not in error_counts:
                    error_counts[hour_key] = 0

                error_counts[hour_key] += 1
            except:
                continue

        return error_counts

    def analyze_error_types(self, start_time=None, end_time=None):
        """
        分析錯誤類型

        Args:
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            dict: 錯誤類型統計
        """
        logs = self.parse_logs(start_time, end_time)

        # 過濾錯誤日誌
        error_logs = [log for log in logs if log.get("level") in ["ERROR", "CRITICAL"]]

        # 統計錯誤類型
        error_types = {}

        for log in error_logs:
            # 嘗試從異常信息中獲取錯誤類型
            exception = log.get("exception", {})
            error_type = exception.get("type", "Unknown")

            if error_type not in error_types:
                error_types[error_type] = 0

            error_types[error_type] += 1

        return error_types

    def generate_report(self, start_time=None, end_time=None):
        """
        生成日誌分析報告

        Args:
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            dict: 分析報告
        """
        logs = self.parse_logs(start_time, end_time)

        # 統計日誌級別
        level_counts = {}
        for log in logs:
            level = log.get("level", "UNKNOWN")
            if level not in level_counts:
                level_counts[level] = 0
            level_counts[level] += 1

        # 分析錯誤頻率
        error_frequency = self.analyze_error_frequency(start_time, end_time)

        # 分析錯誤類型
        error_types = self.analyze_error_types(start_time, end_time)

        # 生成報告
        report = {
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "total_logs": len(logs),
            "level_counts": level_counts,
            "error_frequency": error_frequency,
            "error_types": error_types,
        }

        return report


# 創建日誌分析器
log_analyzer = LogAnalyzer(
    [
        os.path.join(log_dir, "trading.log"),
        os.path.join(error_log_dir, "errors.log"),
        os.path.join(system_log_dir, "system.log"),
    ]
)


class TradeLogger:
    """交易記錄類，用於記錄交易活動"""

    def __init__(self, log_dir="logs"):
        """
        初始化交易記錄器

        Args:
            log_dir (str): 日誌目錄
        """
        self.log_dir = log_dir

        # 確保日誌目錄存在
        os.makedirs(log_dir, exist_ok=True)

        # 初始化交易記錄
        self.trades = []
        self.orders = []
        self.portfolio_values = []

        # 載入現有記錄
        self._load_records()

    def _load_records(self):
        """載入現有記錄"""
        # 載入交易記錄
        trades_file = os.path.join(self.log_dir, "trades.csv")
        if os.path.exists(trades_file):
            self.trades = pd.read_csv(trades_file).to_dict("records")

        # 載入訂單記錄
        orders_file = os.path.join(self.log_dir, "orders.csv")
        if os.path.exists(orders_file):
            self.orders = pd.read_csv(orders_file).to_dict("records")

        # 載入投資組合價值記錄
        portfolio_values_file = os.path.join(self.log_dir, "portfolio_values.csv")
        if os.path.exists(portfolio_values_file):
            self.portfolio_values = pd.read_csv(portfolio_values_file).to_dict(
                "records"
            )

    def _save_records(self):
        """儲存記錄"""
        # 儲存交易記錄
        trades_df = pd.DataFrame(self.trades)
        trades_df.to_csv(os.path.join(self.log_dir, "trades.csv"), index=False)

        # 儲存訂單記錄
        orders_df = pd.DataFrame(self.orders)
        orders_df.to_csv(os.path.join(self.log_dir, "orders.csv"), index=False)

        # 儲存投資組合價值記錄
        portfolio_values_df = pd.DataFrame(self.portfolio_values)
        portfolio_values_df.to_csv(
            os.path.join(self.log_dir, "portfolio_values.csv"), index=False
        )

    def log_trade(self, trade):
        """
        記錄交易

        Args:
            trade (dict): 交易資訊，包含以下欄位：
                - stock_id (str): 股票代號
                - action (str): 交易動作，'buy' 或 'sell'
                - quantity (int): 交易數量
                - price (float): 交易價格
                - timestamp (datetime): 交易時間
                - order_id (str): 訂單 ID
                - transaction_cost (float): 交易成本
                - tax (float): 交易稅
        """
        # 確保交易時間為字符串
        if isinstance(trade.get("timestamp"), datetime):
            trade["timestamp"] = trade["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

        # 添加交易記錄
        self.trades.append(trade)

        # 儲存記錄
        self._save_records()

        # 記錄到日誌
        logger.info(f"交易記錄: {trade}")

    def log_order(self, order):
        """
        記錄訂單

        Args:
            order (dict): 訂單資訊，包含以下欄位：
                - order_id (str): 訂單 ID
                - stock_id (str): 股票代號
                - action (str): 交易動作，'buy' 或 'sell'
                - quantity (int): 交易數量
                - order_type (str): 訂單類型
                - price (float): 限價
                - stop_price (float): 停損價
                - status (str): 訂單狀態
                - timestamp (datetime): 訂單時間
        """
        # 確保訂單時間為字符串
        if isinstance(order.get("timestamp"), datetime):
            order["timestamp"] = order["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

        # 添加訂單記錄
        self.orders.append(order)

        # 儲存記錄
        self._save_records()

        # 記錄到日誌
        logger.info(f"訂單記錄: {order}")

    def log_portfolio_value(self, portfolio_value):
        """
        記錄投資組合價值

        Args:
            portfolio_value (dict): 投資組合價值資訊，包含以下欄位：
                - timestamp (datetime): 時間
                - cash (float): 現金
                - positions_value (float): 持倉價值
                - total_value (float): 總價值
        """
        # 確保時間為字符串
        if isinstance(portfolio_value.get("timestamp"), datetime):
            portfolio_value["timestamp"] = portfolio_value["timestamp"].strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        # 添加投資組合價值記錄
        self.portfolio_values.append(portfolio_value)

        # 儲存記錄
        self._save_records()

        # 記錄到日誌
        logger.info(f"投資組合價值記錄: {portfolio_value}")

    def get_trades(self, stock_id=None, action=None, start_time=None, end_time=None):
        """
        獲取交易記錄

        Args:
            stock_id (str, optional): 股票代號
            action (str, optional): 交易動作
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            pandas.DataFrame: 交易記錄
        """
        # 轉換為 DataFrame
        trades_df = pd.DataFrame(self.trades)

        if trades_df.empty:
            return trades_df

        # 轉換時間欄位
        trades_df["timestamp"] = pd.to_datetime(trades_df["timestamp"])

        # 過濾股票代號
        if stock_id:
            trades_df = trades_df[trades_df["stock_id"] == stock_id]

        # 過濾交易動作
        if action:
            trades_df = trades_df[trades_df["action"] == action]

        # 過濾時間範圍
        if start_time:
            trades_df = trades_df[trades_df["timestamp"] >= start_time]

        if end_time:
            trades_df = trades_df[trades_df["timestamp"] <= end_time]

        return trades_df

    def get_orders(
        self, stock_id=None, action=None, status=None, start_time=None, end_time=None
    ):
        """
        獲取訂單記錄

        Args:
            stock_id (str, optional): 股票代號
            action (str, optional): 交易動作
            status (str, optional): 訂單狀態
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            pandas.DataFrame: 訂單記錄
        """
        # 轉換為 DataFrame
        orders_df = pd.DataFrame(self.orders)

        if orders_df.empty:
            return orders_df

        # 轉換時間欄位
        orders_df["timestamp"] = pd.to_datetime(orders_df["timestamp"])

        # 過濾股票代號
        if stock_id:
            orders_df = orders_df[orders_df["stock_id"] == stock_id]

        # 過濾交易動作
        if action:
            orders_df = orders_df[orders_df["action"] == action]

        # 過濾訂單狀態
        if status:
            orders_df = orders_df[orders_df["status"] == status]

        # 過濾時間範圍
        if start_time:
            orders_df = orders_df[orders_df["timestamp"] >= start_time]

        if end_time:
            orders_df = orders_df[orders_df["timestamp"] <= end_time]

        return orders_df

    def get_portfolio_values(self, start_time=None, end_time=None):
        """
        獲取投資組合價值記錄

        Args:
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            pandas.DataFrame: 投資組合價值記錄
        """
        # 轉換為 DataFrame
        portfolio_values_df = pd.DataFrame(self.portfolio_values)

        if portfolio_values_df.empty:
            return portfolio_values_df

        # 轉換時間欄位
        portfolio_values_df["timestamp"] = pd.to_datetime(
            portfolio_values_df["timestamp"]
        )

        # 過濾時間範圍
        if start_time:
            portfolio_values_df = portfolio_values_df[
                portfolio_values_df["timestamp"] >= start_time
            ]

        if end_time:
            portfolio_values_df = portfolio_values_df[
                portfolio_values_df["timestamp"] <= end_time
            ]

        return portfolio_values_df


class PerformanceAnalyzer:
    """績效分析類，用於分析交易策略的表現"""

    def __init__(self, trade_logger):
        """
        初始化績效分析器

        Args:
            trade_logger (TradeLogger): 交易記錄器
        """
        self.trade_logger = trade_logger

    def calculate_returns(self, start_time=None, end_time=None):
        """
        計算收益率

        Args:
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            dict: 收益率資訊
        """
        # 獲取投資組合價值記錄
        portfolio_values = self.trade_logger.get_portfolio_values(start_time, end_time)

        if portfolio_values.empty:
            return {
                "total_return": 0,
                "annual_return": 0,
                "daily_returns": pd.Series(),
                "cumulative_returns": pd.Series(),
            }

        # 計算每日收益率
        portfolio_values = portfolio_values.sort_values("timestamp")
        portfolio_values["daily_return"] = portfolio_values["total_value"].pct_change()

        # 計算累積收益率
        portfolio_values["cumulative_return"] = (
            1 + portfolio_values["daily_return"]
        ).cumprod() - 1

        # 計算總收益率
        total_return = (
            portfolio_values["cumulative_return"].iloc[-1]
            if not portfolio_values.empty
            else 0
        )

        # 計算年化收益率
        days = (
            portfolio_values["timestamp"].iloc[-1]
            - portfolio_values["timestamp"].iloc[0]
        ).days
        annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0

        return {
            "total_return": total_return,
            "annual_return": annual_return,
            "daily_returns": portfolio_values.set_index("timestamp")["daily_return"],
            "cumulative_returns": portfolio_values.set_index("timestamp")[
                "cumulative_return"
            ],
        }

    def calculate_risk_metrics(self, start_time=None, end_time=None):
        """
        計算風險指標

        Args:
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            dict: 風險指標資訊
        """
        # 獲取收益率資訊
        returns_info = self.calculate_returns(start_time, end_time)
        daily_returns = returns_info["daily_returns"]

        if daily_returns.empty:
            return {
                "volatility": 0,
                "sharpe_ratio": 0,
                "sortino_ratio": 0,
                "max_drawdown": 0,
                "var_95": 0,
                "var_99": 0,
            }

        # 計算波動率
        volatility = daily_returns.std() * np.sqrt(252)

        # 計算夏普比率
        risk_free_rate = 0.0  # 假設無風險利率為 0
        sharpe_ratio = (
            (returns_info["annual_return"] - risk_free_rate) / volatility
            if volatility > 0
            else 0
        )

        # 計算索提諾比率
        downside_returns = daily_returns[daily_returns < 0]
        downside_volatility = (
            downside_returns.std() * np.sqrt(252) if not downside_returns.empty else 0
        )
        sortino_ratio = (
            (returns_info["annual_return"] - risk_free_rate) / downside_volatility
            if downside_volatility > 0
            else 0
        )

        # 計算最大回撤
        cumulative_returns = returns_info["cumulative_returns"]
        max_drawdown = (
            (cumulative_returns / cumulative_returns.cummax() - 1).min()
            if not cumulative_returns.empty
            else 0
        )

        # 計算風險值 (VaR)
        var_95 = daily_returns.quantile(0.05)
        var_99 = daily_returns.quantile(0.01)

        return {
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "max_drawdown": max_drawdown,
            "var_95": var_95,
            "var_99": var_99,
        }

    def calculate_trade_metrics(self, start_time=None, end_time=None):
        """
        計算交易指標

        Args:
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            dict: 交易指標資訊
        """
        # 獲取交易記錄
        trades = self.trade_logger.get_trades(start_time=start_time, end_time=end_time)

        if trades.empty:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "profit_loss_ratio": 0,
                "average_profit": 0,
                "average_loss": 0,
                "largest_profit": 0,
                "largest_loss": 0,
                "average_holding_period": 0,
            }

        # 計算交易次數
        total_trades = len(trades)

        # 計算獲利和虧損交易
        trades["profit"] = np.where(
            trades["action"] == "buy",
            -trades["price"] * trades["quantity"]
            - trades["transaction_cost"]
            - trades["tax"],
            trades["price"] * trades["quantity"]
            - trades["transaction_cost"]
            - trades["tax"],
        )

        # 計算勝率
        winning_trades = trades[trades["profit"] > 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        # 計算盈虧比
        average_profit = (
            winning_trades["profit"].mean() if not winning_trades.empty else 0
        )
        losing_trades = trades[trades["profit"] < 0]
        average_loss = (
            abs(losing_trades["profit"].mean()) if not losing_trades.empty else 0
        )
        profit_loss_ratio = average_profit / average_loss if average_loss > 0 else 0

        # 計算最大獲利和最大虧損
        largest_profit = (
            winning_trades["profit"].max() if not winning_trades.empty else 0
        )
        largest_loss = (
            abs(losing_trades["profit"].min()) if not losing_trades.empty else 0
        )

        # 計算平均持有期
        # 這裡需要配對買入和賣出交易，但簡化起見，我們假設每個交易都是獨立的
        average_holding_period = 0

        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "profit_loss_ratio": profit_loss_ratio,
            "average_profit": average_profit,
            "average_loss": average_loss,
            "largest_profit": largest_profit,
            "largest_loss": largest_loss,
            "average_holding_period": average_holding_period,
        }

    def generate_performance_report(self, start_time=None, end_time=None):
        """
        生成績效報告

        Args:
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            dict: 績效報告
        """
        # 計算收益率指標
        returns_info = self.calculate_returns(start_time, end_time)

        # 計算風險指標
        risk_metrics = self.calculate_risk_metrics(start_time, end_time)

        # 計算交易指標
        trade_metrics = self.calculate_trade_metrics(start_time, end_time)

        # 生成報告
        report = {
            "start_time": start_time.strftime("%Y-%m-%d") if start_time else None,
            "end_time": end_time.strftime("%Y-%m-%d") if end_time else None,
            "returns": returns_info,
            "risk": risk_metrics,
            "trade": trade_metrics,
        }

        return report

    def plot_performance(self, start_time=None, end_time=None):
        """
        繪製績效圖表

        Args:
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            matplotlib.figure.Figure: 繪圖物件
        """
        # 獲取投資組合價值記錄
        portfolio_values = self.trade_logger.get_portfolio_values(start_time, end_time)

        if portfolio_values.empty:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(
                0.5,
                0.5,
                "沒有資料",
                horizontalalignment="center",
                verticalalignment="center",
            )
            return fig

        # 計算收益率
        returns_info = self.calculate_returns(start_time, end_time)

        # 創建繪圖物件
        fig, axes = plt.subplots(3, 1, figsize=(12, 15))

        # 繪製投資組合價值
        portfolio_values.plot(x="timestamp", y="total_value", ax=axes[0])
        axes[0].set_title("投資組合價值")
        axes[0].set_xlabel("日期")
        axes[0].set_ylabel("價值")
        axes[0].grid(True)

        # 繪製累積收益率
        returns_info["cumulative_returns"].plot(ax=axes[1])
        axes[1].set_title("累積收益率")
        axes[1].set_xlabel("日期")
        axes[1].set_ylabel("累積收益率")
        axes[1].grid(True)

        # 繪製回撤
        drawdown = (
            returns_info["cumulative_returns"]
            / returns_info["cumulative_returns"].cummax()
            - 1
        ) * 100
        drawdown.plot(ax=axes[2], color="red")
        axes[2].set_title("回撤 (%)")
        axes[2].set_xlabel("日期")
        axes[2].set_ylabel("回撤 (%)")
        axes[2].grid(True)

        # 調整佈局
        plt.tight_layout()

        return fig


def record(results, orders=None):
    """
    記錄交易結果的主函數

    Args:
        results (dict): 交易結果
        orders (list, optional): 訂單列表

    Returns:
        dict: 績效報告
    """
    # 創建交易記錄器
    trade_logger = TradeLogger()

    # 記錄投資組合價值
    if "daily_values" in results:
        for date, value in results["daily_values"].items():
            portfolio_value = {
                "timestamp": date,
                "total_value": value,
                "cash": 0,  # 這裡簡化了，實際上應該從結果中獲取
                "positions_value": value,  # 這裡簡化了，實際上應該從結果中獲取
            }
            trade_logger.log_portfolio_value(portfolio_value)

    # 記錄訂單
    if orders is not None:
        for order in orders:
            trade_logger.log_order(order)

    # 創建績效分析器
    analyzer = PerformanceAnalyzer(trade_logger)

    # 生成績效報告
    report = analyzer.generate_performance_report()

    return report


def analyze_performance(results: dict, orders: list):
    """
    分析交易績效並生成報表

    Args:
        results (dict): 交易結果，包含以下欄位：
            - daily_values (dict): 每日投資組合價值
            - equity_curve (dict): 淨值曲線
        orders (list): 訂單列表

    Returns:
        None: 函數會將圖表輸出為 HTML 檔案，並印出績效指標
    """
    # 導入配置
    from src.config import RESULTS_DIR

    # 確保 results 目錄存在
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # 創建交易記錄器
    trade_logger = TradeLogger()

    # 記錄投資組合價值
    if "daily_values" in results:
        for date, value in results["daily_values"].items():
            portfolio_value = {
                "timestamp": date,
                "total_value": value,
                "cash": results.get("cash", {}).get(date, 0),
                "positions_value": value - results.get("cash", {}).get(date, 0),
            }
            trade_logger.log_portfolio_value(portfolio_value)

    # 記錄訂單
    if orders is not None:
        for order in orders:
            trade_logger.log_order(order)

    # 創建績效分析器
    analyzer = PerformanceAnalyzer(trade_logger)

    # 獲取投資組合價值記錄
    portfolio_values = trade_logger.get_portfolio_values()

    if portfolio_values.empty:
        print("沒有足夠的資料進行分析")
        return

    # 計算收益率
    returns_info = analyzer.calculate_returns()

    # 計算風險指標
    risk_metrics = analyzer.calculate_risk_metrics()

    # 計算交易指標
    trade_metrics = analyzer.calculate_trade_metrics()

    # 印出績效指標
    print("\n===== 績效指標 =====")
    print(f"年化報酬: {returns_info['annual_return']:.2%}")
    print(f"夏普比率: {risk_metrics['sharpe_ratio']:.2f}")
    print(f"最大回撤: {risk_metrics['max_drawdown']:.2%}")
    print(f"勝率: {trade_metrics['win_rate']:.2%}")

    # 創建 plotly 圖表
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("淨值曲線", "每月報酬"),
        vertical_spacing=0.2,
        specs=[[{"type": "scatter"}], [{"type": "bar"}]],
    )

    # 繪製淨值曲線
    portfolio_values["timestamp"] = pd.to_datetime(portfolio_values["timestamp"])
    fig.add_trace(
        go.Scatter(
            x=portfolio_values["timestamp"],
            y=portfolio_values["total_value"],
            mode="lines",
            name="淨值",
        ),
        row=1,
        col=1,
    )

    # 計算每月報酬
    if not returns_info["daily_returns"].empty:
        monthly_returns = (
            returns_info["daily_returns"]
            .resample("M")
            .apply(lambda x: (1 + x).prod() - 1)
        )

        # 繪製每月報酬長條圖
        colors = ["green" if x > 0 else "red" for x in monthly_returns.values]
        fig.add_trace(
            go.Bar(
                x=monthly_returns.index,
                y=monthly_returns.values * 100,  # 轉換為百分比
                name="每月報酬",
                marker_color=colors,
            ),
            row=2,
            col=1,
        )

    # 更新圖表佈局
    fig.update_layout(title="交易績效分析", height=800, width=1000, showlegend=True)

    # 更新 y 軸標籤
    fig.update_yaxes(title_text="淨值", row=1, col=1)
    fig.update_yaxes(title_text="報酬率 (%)", row=2, col=1)

    # 導入配置
    from src.config import RESULTS_DIR

    # 將圖表輸出為 HTML
    report_path = os.path.join(RESULTS_DIR, "performance_report.html")
    fig.write_html(report_path)

    print(f"\n績效報告已保存至 {report_path}")


def get_logger(name="trading_logger"):
    """
    取得指定名稱的 logger 實例
    Args:
        name (str): logger 名稱，預設為 'trading_logger'
    Returns:
        logging.Logger: logger 實例
    """
    return logging.getLogger(name)
