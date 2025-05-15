# -*- coding: utf-8 -*-
"""
自定義策略模組

此模組提供各種自定義的回測策略，包括：
- 模型驅動策略
- 技術指標策略
- 混合策略
- 多資產策略
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
import backtrader as bt
import backtrader.indicators as btind

from src.config import LOG_LEVEL
from src.models.model_base import ModelBase
from src.models.inference_pipeline import InferencePipeline
from src.backtest.backtrader_integration import ModelSignalStrategy

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class MLStrategy(ModelSignalStrategy):
    """
    機器學習策略

    基於機器學習模型的交易策略。
    """

    params = (
        ("prediction_window", 1),  # 預測窗口
        ("confidence_threshold", 0.6),  # 信心閾值
        ("use_probability", True),  # 是否使用概率
        ("feature_window", 10),  # 特徵窗口
        ("retrain_freq", 20),  # 重新訓練頻率（天）
        ("retrain_window", 252),  # 重新訓練窗口（天）
    )

    def __init__(self):
        """
        初始化策略
        """
        super().__init__()

        # 初始化變數
        self.last_train_date = None
        self.feature_history = []
        self.target_history = []

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
            # 收集歷史資料
            for i in range(min(self.p.feature_window, len(data))):
                for col in feature_columns:
                    if hasattr(data.lines, col):
                        features[f"{data._name}_{col}_{i}"] = getattr(data.lines, col)[
                            -i
                        ]

            # 添加技術指標
            features[f"{data._name}_sma_5"] = btind.SMA(data, period=5)[0]
            features[f"{data._name}_sma_10"] = btind.SMA(data, period=10)[0]
            features[f"{data._name}_sma_20"] = btind.SMA(data, period=20)[0]
            features[f"{data._name}_rsi"] = btind.RSI(data, period=14)[0]
            features[f"{data._name}_macd"] = btind.MACD(data)[0]
            features[f"{data._name}_macd_signal"] = btind.MACD(data).signal[0]
            features[f"{data._name}_bb_upper"] = btind.BollingerBands(data).top[0]
            features[f"{data._name}_bb_middle"] = btind.BollingerBands(data).mid[0]
            features[f"{data._name}_bb_lower"] = btind.BollingerBands(data).bot[0]

        # 創建特徵資料框
        features_df = pd.DataFrame([features])

        return features_df

    def next(self):
        """
        策略主邏輯
        """
        # 檢查是否需要重新訓練模型
        current_date = self.datas[0].datetime.date(0)
        if (
            self.p.model is not None
            and hasattr(self.p.model, "train")
            and (
                self.last_train_date is None
                or (current_date - self.last_train_date).days >= self.p.retrain_freq
            )
        ):
            self.last_train_date = current_date

            # 收集訓練資料
            self.collect_training_data()

            # 重新訓練模型
            if (
                len(self.feature_history) >= self.p.retrain_window
                and len(self.target_history) >= self.p.retrain_window
            ):
                self.retrain_model()

        # 執行父類的 next 方法
        super().next()

    def collect_training_data(self):
        """
        收集訓練資料
        """
        # 準備特徵
        features = self.prepare_features()
        self.feature_history.append(features)

        # 準備目標
        for data in self.datas:
            # 計算未來收益率
            future_price = (
                data.close[self.p.prediction_window]
                if len(data) > self.p.prediction_window
                else data.close[0]
            )
            current_price = data.close[0]
            future_return = (future_price / current_price) - 1

            # 根據未來收益率生成目標
            if (
                self.p.model is not None
                and hasattr(self.p.model, "is_classifier")
                and self.p.model.is_classifier
            ):
                # 分類目標
                target = 1 if future_return > 0 else 0
            else:
                # 回歸目標
                target = future_return

            self.target_history.append(target)

        # 限制歷史資料長度
        if len(self.feature_history) > self.p.retrain_window:
            self.feature_history = self.feature_history[-self.p.retrain_window :]

        if len(self.target_history) > self.p.retrain_window:
            self.target_history = self.target_history[-self.p.retrain_window :]

    def retrain_model(self):
        """
        重新訓練模型
        """
        if self.p.model is None or not hasattr(self.p.model, "train"):
            return

        # 準備訓練資料
        X = pd.concat(self.feature_history)
        y = pd.Series(self.target_history)

        # 訓練模型
        self.p.model.train(X, y)

        self.log(f"模型已重新訓練，使用 {len(X)} 筆資料")


class EnsembleStrategy(ModelSignalStrategy):
    """
    集成策略

    結合多個模型的交易策略。
    """

    params = (
        ("models", []),  # 模型列表
        ("weights", []),  # 權重列表
        (
            "voting_method",
            "weighted",
        ),  # 投票方法，可選 'weighted', 'majority', 'average'
    )

    def __init__(self):
        """
        初始化策略
        """
        super().__init__()

        # 檢查模型和權重
        if not self.p.models:
            logger.error("必須提供至少一個模型")
            raise ValueError("必須提供至少一個模型")

        # 如果沒有提供權重，則使用平均權重
        if not self.p.weights:
            self.p.weights = [1.0 / len(self.p.models)] * len(self.p.models)

        # 檢查權重和模型數量是否一致
        if len(self.p.weights) != len(self.p.models):
            logger.error("權重數量必須與模型數量一致")
            raise ValueError("權重數量必須與模型數量一致")

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

        # 初始化訊號
        for data in self.datas:
            signals[data._name] = 0.0

        # 收集每個模型的訊號
        model_signals = []
        for model in self.p.models:
            if hasattr(model, "predict"):
                predictions = model.predict(self.features_df)

                # 處理預測結果
                model_signal = {}
                for i, data in enumerate(self.datas):
                    if isinstance(predictions, list) and len(predictions) > i:
                        model_signal[data._name] = predictions[i]
                    elif isinstance(predictions, np.ndarray) and len(predictions) > i:
                        model_signal[data._name] = predictions[i]
                    elif isinstance(predictions, (int, float)):
                        model_signal[data._name] = predictions
                    else:
                        model_signal[data._name] = 0.0

                model_signals.append(model_signal)

        # 根據投票方法合併訊號
        if self.p.voting_method == "weighted":
            # 加權平均
            for data in self.datas:
                signals[data._name] = sum(
                    model_signal[data._name] * weight
                    for model_signal, weight in zip(model_signals, self.p.weights)
                )
        elif self.p.voting_method == "majority":
            # 多數投票
            for data in self.datas:
                votes = [
                    1 if model_signal[data._name] > self.p.signal_threshold else 0
                    for model_signal in model_signals
                ]
                signals[data._name] = 1.0 if sum(votes) > len(votes) / 2 else 0.0
        elif self.p.voting_method == "average":
            # 平均
            for data in self.datas:
                signals[data._name] = sum(
                    model_signal[data._name] for model_signal in model_signals
                ) / len(model_signals)
        else:
            logger.error(f"未知的投票方法: {self.p.voting_method}")
            raise ValueError(f"未知的投票方法: {self.p.voting_method}")

        return signals


class TechnicalStrategy(bt.Strategy):
    """
    技術指標策略

    基於技術指標的交易策略。
    """

    params = (
        ("sma_short", 10),  # 短期移動平均線
        ("sma_long", 50),  # 長期移動平均線
        ("rsi_period", 14),  # RSI 週期
        ("rsi_overbought", 70),  # RSI 超買閾值
        ("rsi_oversold", 30),  # RSI 超賣閾值
        ("macd_fast", 12),  # MACD 快線
        ("macd_slow", 26),  # MACD 慢線
        ("macd_signal", 9),  # MACD 訊號線
        ("bb_period", 20),  # 布林通道週期
        ("bb_dev", 2.0),  # 布林通道標準差
        ("atr_period", 14),  # ATR 週期
        ("stop_loss", 0.05),  # 停損比例
        ("take_profit", 0.1),  # 停利比例
        ("trailing_stop", False),  # 是否使用追蹤止損
        ("trailing_stop_distance", 0.02),  # 追蹤止損距離
        ("position_size", 1.0),  # 倉位大小
        ("max_positions", 5),  # 最大持倉數量
        ("verbose", False),  # 是否輸出詳細資訊
    )

    def __init__(self):
        """
        初始化策略
        """
        # 初始化指標
        self.sma_short = {}
        self.sma_long = {}
        self.rsi = {}
        self.macd = {}
        self.macd_signal = {}
        self.macd_hist = {}
        self.bb_top = {}
        self.bb_mid = {}
        self.bb_bot = {}
        self.atr = {}

        for data in self.datas:
            # 移動平均線
            self.sma_short[data._name] = btind.SMA(data, period=self.p.sma_short)
            self.sma_long[data._name] = btind.SMA(data, period=self.p.sma_long)

            # RSI
            self.rsi[data._name] = btind.RSI(data, period=self.p.rsi_period)

            # MACD
            macd = btind.MACD(
                data,
                period_me1=self.p.macd_fast,
                period_me2=self.p.macd_slow,
                period_signal=self.p.macd_signal,
            )
            self.macd[data._name] = macd.macd
            self.macd_signal[data._name] = macd.signal
            self.macd_hist[data._name] = macd.macd - macd.signal

            # 布林通道
            bb = btind.BollingerBands(
                data, period=self.p.bb_period, devfactor=self.p.bb_dev
            )
            self.bb_top[data._name] = bb.top
            self.bb_mid[data._name] = bb.mid
            self.bb_bot[data._name] = bb.bot

            # ATR
            self.atr[data._name] = btind.ATR(data, period=self.p.atr_period)

        # 初始化變數
        self.order = None
        self.stop_orders = {}
        self.take_profit_orders = {}

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

    def next(self):
        """
        策略主邏輯
        """
        for data in self.datas:
            # 檢查是否有未完成的訂單
            if self.order:
                return

            # 獲取當前持倉
            position = self.getposition(data)

            # 生成訊號
            signal = self.generate_signal(data)

            # 根據訊號執行交易
            if signal > 0 and not position:
                # 檢查是否達到最大持倉數量
                if self.get_position_count() < self.p.max_positions:
                    # 計算倉位大小
                    size = self.calculate_position_size(data)

                    # 買入
                    self.log(f"買入訊號: {data._name}, 倉位大小={size}")
                    self.order = self.buy(data=data, size=size)
            elif signal < 0 and position:
                # 賣出
                self.log(f"賣出訊號: {data._name}, 倉位大小={position.size}")
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

    def generate_signal(self, data):
        """
        生成訊號

        Args:
            data (Data): 資料

        Returns:
            float: 訊號值
        """
        # 獲取指標值
        sma_short = self.sma_short[data._name][0]
        sma_long = self.sma_long[data._name][0]
        rsi = self.rsi[data._name][0]
        macd = self.macd[data._name][0]
        macd_signal = self.macd_signal[data._name][0]
        macd_hist = self.macd_hist[data._name][0]
        bb_top = self.bb_top[data._name][0]
        bb_mid = self.bb_mid[data._name][0]
        bb_bot = self.bb_bot[data._name][0]

        # 生成訊號
        signal = 0.0

        # 移動平均線交叉
        if sma_short > sma_long:
            signal += 1.0
        elif sma_short < sma_long:
            signal -= 1.0

        # RSI
        if rsi < self.p.rsi_oversold:
            signal += 1.0
        elif rsi > self.p.rsi_overbought:
            signal -= 1.0

        # MACD
        if macd > macd_signal:
            signal += 1.0
        elif macd < macd_signal:
            signal -= 1.0

        # 布林通道
        if data.close[0] < bb_bot:
            signal += 1.0
        elif data.close[0] > bb_top:
            signal -= 1.0

        return signal

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
