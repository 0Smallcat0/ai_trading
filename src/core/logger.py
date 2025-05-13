"""
交易記錄與績效分析模組

此模組負責記錄交易活動，並提供績效分析功能，
幫助評估交易策略的表現，並提供改進的依據。

主要功能：
- 交易記錄
- 績效分析
- 報表生成
- 資料視覺化
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設定日誌目錄
log_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs"
)
os.makedirs(log_dir, exist_ok=True)

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "trading.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("trading_logger")


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
