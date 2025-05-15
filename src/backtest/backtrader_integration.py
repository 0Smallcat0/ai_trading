# -*- coding: utf-8 -*-
"""
Backtrader 整合模組

此模組提供與 Backtrader 回測框架的整合功能，包括：
- 資料饋送轉換
- 策略包裝
- 回測執行
- 結果分析
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, Union

import backtrader as bt
import backtrader.analyzers as btanalyzers
import backtrader.feeds as btfeeds
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import LOG_LEVEL, RESULTS_DIR

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class PandasDataFeed(btfeeds.PandasData):
    """
    Pandas 資料饋送

    擴展 Backtrader 的 PandasData 類，支援更多欄位。
    """

    lines = ("signal",)
    params = (("signal", -1),)


class ModelSignalStrategy(bt.Strategy):
    """
    模型訊號策略

    基於模型訊號的 Backtrader 策略。
    """

    params = (
        ("model", None),  # 模型
        ("inference_pipeline", None),  # 推論管道
        ("feature_columns", None),  # 特徵欄位
        ("signal_threshold", 0.5),  # 訊號閾值
        ("position_size", 1.0),  # 倉位大小
        ("stop_loss", 0.05),  # 停損比例
        ("take_profit", 0.1),  # 停利比例
        ("trailing_stop", False),  # 是否使用追蹤止損
        ("trailing_stop_distance", 0.02),  # 追蹤止損距離
        ("use_atr_stop", False),  # 是否使用 ATR 止損
        ("atr_stop_multiplier", 2.0),  # ATR 止損乘數
        ("atr_period", 14),  # ATR 週期
        ("max_positions", 5),  # 最大持倉數量
        ("rebalance_freq", 5),  # 再平衡頻率（天）
        ("verbose", False),  # 是否輸出詳細資訊
    )

    def __init__(self):
        """
        初始化策略
        """
        # 初始化指標
        self.atr = (
            bt.indicators.ATR(self.data, period=self.p.atr_period)
            if self.p.use_atr_stop
            else None
        )

        # 初始化變數
        self.order = None
        self.stop_orders = {}
        self.take_profit_orders = {}
        self.last_rebalance_date = None
        self.features_df = None

        # 檢查模型或推論管道是否提供
        if self.p.model is None and self.p.inference_pipeline is None:
            logger.error("必須提供模型或推論管道")
            raise ValueError("必須提供模型或推論管道")

    def log(self, txt, dt=None):
        """
        記錄訊息

        Args:
            txt (str): 訊息
            dt (datetime, optional): 日期時間
        """
        if self.p.verbose:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()}, {txt}")

    def notify_order(self, order):
        """
        訂單通知

        Args:
            order (Order): 訂單
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 訂單已提交或已接受，等待執行
            return

        if order.status in [order.Completed]:
            # 訂單已完成
            if order.isbuy():
                self.log(
                    f"買入執行: 價格={order.executed.price:.2f}, 成本={order.executed.value:.2f}, 手續費={order.executed.comm:.2f}"
                )

                # 設定止損和止盈
                if self.p.stop_loss > 0:
                    stop_price = order.executed.price * (1.0 - self.p.stop_loss)
                    stop_order = self.sell(
                        exectype=bt.Order.Stop,
                        price=stop_price,
                        size=order.executed.size,
                    )
                    self.stop_orders[order.data._name] = stop_order

                if self.p.take_profit > 0:
                    take_profit_price = order.executed.price * (
                        1.0 + self.p.take_profit
                    )
                    take_profit_order = self.sell(
                        exectype=bt.Order.Limit,
                        price=take_profit_price,
                        size=order.executed.size,
                    )
                    self.take_profit_orders[order.data._name] = take_profit_order
            else:
                self.log(
                    f"賣出執行: 價格={order.executed.price:.2f}, 成本={order.executed.value:.2f}, 手續費={order.executed.comm:.2f}"
                )

                # 清除止損和止盈訂單
                if order.data._name in self.stop_orders:
                    self.cancel(self.stop_orders[order.data._name])
                    del self.stop_orders[order.data._name]

                if order.data._name in self.take_profit_orders:
                    self.cancel(self.take_profit_orders[order.data._name])
                    del self.take_profit_orders[order.data._name]

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # 訂單已取消、保證金不足或被拒絕
            self.log(f"訂單取消/保證金不足/拒絕: {order.status}")

        # 重設訂單
        self.order = None

    def notify_trade(self, trade):
        """
        交易通知

        Args:
            trade (Trade): 交易
        """
        if not trade.isclosed:
            return

        self.log(f"交易利潤: 毛利={trade.pnl:.2f}, 淨利={trade.pnlcomm:.2f}")

    def prepare_features(self):
        """
        準備特徵

        Returns:
            pd.DataFrame: 特徵資料框
        """
        # 獲取當前資料
        features = {}

        # 如果沒有指定特徵欄位，則使用所有可用欄位
        feature_columns = self.p.feature_columns or [
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        # 收集特徵
        for data in self.datas:
            for col in feature_columns:
                if hasattr(data.lines, col):
                    features[f"{data._name}_{col}"] = getattr(data.lines, col)[0]

        # 創建特徵資料框
        features_df = pd.DataFrame([features])

        return features_df

    def generate_signals(self):
        """
        生成訊號

        Returns:
            Dict[str, float]: 訊號字典，鍵為資料名稱，值為訊號值
        """
        # 準備特徵
        self.features_df = self.prepare_features()

        # 生成訊號
        signals = {}

        if self.p.inference_pipeline is not None:
            # 使用推論管道生成訊號
            predictions = self.p.inference_pipeline.predict(self.features_df)

            # 處理預測結果
            for i, data in enumerate(self.datas):
                if isinstance(predictions, list) and len(predictions) > i:
                    signals[data._name] = predictions[i]
                elif isinstance(predictions, np.ndarray) and len(predictions) > i:
                    signals[data._name] = predictions[i]
                elif isinstance(predictions, (int, float)):
                    signals[data._name] = predictions
                else:
                    signals[data._name] = 0.0
        elif self.p.model is not None:
            # 使用模型生成訊號
            predictions = self.p.model.predict(self.features_df)

            # 處理預測結果
            for i, data in enumerate(self.datas):
                if isinstance(predictions, list) and len(predictions) > i:
                    signals[data._name] = predictions[i]
                elif isinstance(predictions, np.ndarray) and len(predictions) > i:
                    signals[data._name] = predictions[i]
                elif isinstance(predictions, (int, float)):
                    signals[data._name] = predictions
                else:
                    signals[data._name] = 0.0
        else:
            # 使用資料中的訊號
            for data in self.datas:
                if hasattr(data.lines, "signal"):
                    signals[data._name] = data.lines.signal[0]
                else:
                    signals[data._name] = 0.0

        return signals

    def next(self):
        """
        策略主邏輯
        """
        # 檢查是否需要再平衡
        current_date = self.datas[0].datetime.date(0)
        if (
            self.last_rebalance_date is None
            or (current_date - self.last_rebalance_date).days >= self.p.rebalance_freq
        ):
            self.last_rebalance_date = current_date

            # 生成訊號
            signals = self.generate_signals()

            # 執行交易
            for data in self.datas:
                # 檢查是否有未完成的訂單
                if self.order:
                    return

                # 獲取訊號
                signal = signals.get(data._name, 0.0)

                # 檢查是否有持倉
                position = self.getposition(data)

                # 根據訊號執行交易
                if signal > self.p.signal_threshold and not position:
                    # 檢查是否達到最大持倉數量
                    if self.get_position_count() < self.p.max_positions:
                        # 計算倉位大小
                        size = self.calculate_position_size(data)

                        # 買入
                        self.log(
                            f"買入訊號: {data._name}, 訊號值={signal:.2f}, 倉位大小={size}"
                        )
                        self.order = self.buy(data=data, size=size)
                elif signal < -self.p.signal_threshold and position:
                    # 賣出
                    self.log(
                        f"賣出訊號: {data._name}, 訊號值={signal:.2f}, 倉位大小={position.size}"
                    )
                    self.order = self.sell(data=data, size=position.size)

                # 更新追蹤止損
                if self.p.trailing_stop and position:
                    # 獲取當前價格
                    current_price = data.close[0]

                    # 計算追蹤止損價格
                    if data._name in self.stop_orders:
                        stop_order = self.stop_orders[data._name]
                        new_stop_price = current_price * (
                            1.0 - self.p.trailing_stop_distance
                        )

                        # 如果新的止損價格高於當前止損價格，則更新止損價格
                        if new_stop_price > stop_order.price:
                            self.cancel(stop_order)
                            self.stop_orders[data._name] = self.sell(
                                data=data,
                                exectype=bt.Order.Stop,
                                price=new_stop_price,
                                size=position.size,
                            )
                            self.log(
                                f"更新追蹤止損: {data._name}, 新止損價格={new_stop_price:.2f}"
                            )

    def calculate_position_size(self, data):
        """
        計算倉位大小

        Args:
            data (Data): 資料

        Returns:
            int: 倉位大小
        """
        # 獲取當前價格
        current_price = data.close[0]

        # 獲取當前現金
        cash = self.broker.getcash()

        # 計算倉位大小
        size = int((cash * self.p.position_size) / current_price)

        return max(1, size)

    def get_position_count(self):
        """
        獲取持倉數量

        Returns:
            int: 持倉數量
        """
        count = 0
        for data in self.datas:
            position = self.getposition(data)
            if position.size > 0:
                count += 1

        return count


class BacktestEngine:
    """
    回測引擎

    提供回測功能。
    """

    def __init__(
        self,
        data: Optional[pd.DataFrame] = None,
        data_path: Optional[str] = None,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        cash: float = 100000.0,
        commission: float = 0.001,
        slippage: float = 0.001,
        tax: float = 0.003,
        output_dir: Optional[str] = None,
    ):
        """
        初始化回測引擎

        Args:
            data (Optional[pd.DataFrame]): 資料
            data_path (Optional[str]): 資料路徑
            start_date (Optional[Union[str, datetime]]): 開始日期
            end_date (Optional[Union[str, datetime]]): 結束日期
            cash (float): 初始資金
            commission (float): 手續費率
            slippage (float): 滑價率
            tax (float): 稅率
            output_dir (Optional[str]): 輸出目錄
        """
        self.data = data
        self.data_path = data_path
        self.start_date = pd.to_datetime(start_date) if start_date else None
        self.end_date = pd.to_datetime(end_date) if end_date else None
        self.cash = cash
        self.commission = commission
        self.slippage = slippage
        self.tax = tax
        self.output_dir = output_dir or os.path.join(
            RESULTS_DIR, "backtest", datetime.now().strftime("%Y%m%d%H%M%S")
        )

        # 創建輸出目錄
        os.makedirs(self.output_dir, exist_ok=True)

        # 初始化 Backtrader
        self.cerebro = bt.Cerebro()

        # 設定初始資金
        self.cerebro.broker.setcash(cash)

        # 設定手續費
        self.cerebro.broker.setcommission(commission=commission)

        # 設定滑價
        if slippage > 0:
            self.cerebro.broker.set_slippage_perc(slippage)

        # 設定分析器
        self.cerebro.addanalyzer(btanalyzers.SharpeRatio, _name="sharpe")
        self.cerebro.addanalyzer(btanalyzers.DrawDown, _name="drawdown")
        self.cerebro.addanalyzer(btanalyzers.Returns, _name="returns")
        self.cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name="trades")
        self.cerebro.addanalyzer(btanalyzers.SQN, _name="sqn")
        self.cerebro.addanalyzer(btanalyzers.TimeReturn, _name="time_return")

        # 結果
        self.results = None
        self.strats = None

    def add_data(
        self,
        data: Optional[pd.DataFrame] = None,
        data_path: Optional[str] = None,
        name: Optional[str] = None,
        timeframe: bt.TimeFrame = bt.TimeFrame.Days,
        compression: int = 1,
        fromdate: Optional[datetime] = None,
        todate: Optional[datetime] = None,
    ) -> None:
        """
        添加資料

        Args:
            data (Optional[pd.DataFrame]): 資料
            data_path (Optional[str]): 資料路徑
            name (Optional[str]): 資料名稱
            timeframe (bt.TimeFrame): 時間框架
            compression (int): 壓縮
            fromdate (Optional[datetime]): 開始日期
            todate (Optional[datetime]): 結束日期
        """
        if data is not None:
            # 使用 Pandas 資料
            data_feed = PandasDataFeed(
                dataname=data,
                name=name,
                timeframe=timeframe,
                compression=compression,
                fromdate=fromdate or self.start_date,
                todate=todate or self.end_date,
            )
            self.cerebro.adddata(data_feed)
        elif data_path is not None:
            # 使用 CSV 資料
            if data_path.endswith(".csv"):
                data_feed = btfeeds.GenericCSVData(
                    dataname=data_path,
                    name=name,
                    timeframe=timeframe,
                    compression=compression,
                    fromdate=fromdate or self.start_date,
                    todate=todate or self.end_date,
                    dtformat="%Y-%m-%d",
                    datetime=0,
                    open=1,
                    high=2,
                    low=3,
                    close=4,
                    volume=5,
                    openinterest=-1,
                )
                self.cerebro.adddata(data_feed)
            else:
                logger.error(f"不支援的資料格式: {data_path}")
                raise ValueError(f"不支援的資料格式: {data_path}")
        else:
            logger.error("必須提供資料或資料路徑")
            raise ValueError("必須提供資料或資料路徑")

    def add_strategy(self, strategy: bt.Strategy, **kwargs) -> None:
        """
        添加策略

        Args:
            strategy (bt.Strategy): 策略
            **kwargs: 策略參數
        """
        self.cerebro.addstrategy(strategy, **kwargs)

    def run(self) -> Dict[str, Any]:
        """
        執行回測

        Returns:
            Dict[str, Any]: 回測結果
        """
        # 執行回測
        self.results = self.cerebro.run()
        self.strats = self.results[0]

        # 獲取分析結果
        sharpe_ratio = self.strats.analyzers.sharpe.get_analysis()
        drawdown = self.strats.analyzers.drawdown.get_analysis()
        self.strats.analyzers.returns.get_analysis()
        trades = self.strats.analyzers.trades.get_analysis()
        sqn = self.strats.analyzers.sqn.get_analysis()
        time_return = self.strats.analyzers.time_return.get_analysis()

        # 計算年化收益率
        total_return = self.cerebro.broker.getvalue() / self.cash - 1
        days = (
            (self.end_date - self.start_date).days
            if self.end_date and self.start_date
            else 365
        )
        annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0

        # 整理結果
        result = {
            "initial_cash": self.cash,
            "final_value": self.cerebro.broker.getvalue(),
            "total_return": total_return,
            "annual_return": annual_return,
            "sharpe_ratio": sharpe_ratio.get("sharperatio", 0.0),
            "max_drawdown": drawdown.get("max", {}).get("drawdown", 0.0),
            "max_drawdown_length": drawdown.get("max", {}).get("len", 0),
            "trades": {
                "total": trades.get("total", 0),
                "won": trades.get("won", 0),
                "lost": trades.get("lost", 0),
                "win_rate": (
                    trades.get("won", 0) / trades.get("total", 1)
                    if trades.get("total", 0) > 0
                    else 0.0
                ),
                "pnl": {
                    "total": trades.get("pnl", {}).get("total", 0.0),
                    "average": trades.get("pnl", {}).get("average", 0.0),
                    "max_win": trades.get("pnl", {}).get("max", 0.0),
                    "max_loss": trades.get("pnl", {}).get("min", 0.0),
                },
            },
            "sqn": sqn.get("sqn", 0.0),
            "time_return": dict(time_return),
        }

        # 保存結果
        self.save_results(result)

        return result

    def plot(self, filename: Optional[str] = None, **kwargs) -> None:
        """
        繪製回測結果

        Args:
            filename (Optional[str]): 檔案名稱
            **kwargs: 繪圖參數
        """
        if self.results is None:
            logger.error("必須先執行回測")
            raise ValueError("必須先執行回測")

        # 設定檔案名稱
        if filename is None:
            filename = os.path.join(self.output_dir, "backtest_plot.png")

        # 繪製結果
        plt.figure(figsize=(12, 8))
        self.cerebro.plot(**kwargs)[0][0].savefig(filename)
        plt.close()

        logger.info(f"回測結果已繪製至: {filename}")

    def save_results(
        self, result: Dict[str, Any], filename: Optional[str] = None
    ) -> None:
        """
        保存回測結果

        Args:
            result (Dict[str, Any]): 回測結果
            filename (Optional[str]): 檔案名稱
        """
        # 設定檔案名稱
        if filename is None:
            filename = os.path.join(self.output_dir, "backtest_results.json")

        # 保存結果
        import json

        with open(filename, "w") as f:
            json.dump(result, f, indent=4, default=str)

        logger.info(f"回測結果已保存至: {filename}")

    def get_equity_curve(self) -> pd.DataFrame:
        """
        獲取權益曲線

        Returns:
            pd.DataFrame: 權益曲線
        """
        if self.results is None:
            logger.error("必須先執行回測")
            raise ValueError("必須先執行回測")

        # 獲取時間收益率
        time_return = self.strats.analyzers.time_return.get_analysis()

        # 創建權益曲線
        equity_curve = pd.DataFrame(
            [(pd.to_datetime(k), v) for k, v in time_return.items()],
            columns=["date", "return"],
        )
        equity_curve["equity"] = (1 + equity_curve["return"]).cumprod() * self.cash

        return equity_curve
