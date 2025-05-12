"""
策略研究與訊號產生模組

此模組負責根據技術指標和基本面指標生成交易訊號，
實現各種交易策略，並提供策略評估和優化的功能。

主要功能：
- 實現各種交易策略（如趨勢跟蹤、反轉、突破等）
- 生成買入和賣出訊號
- 策略參數優化
- 策略評估和比較
"""

from numba import njit
import numpy as np
import pandas as pd
import math
import logging
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV

try:
    from .data_ingest import load_data
except ImportError as e:
    logger = logging.getLogger("strategy")
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.error(
        f"無法匯入 .data_ingest，請確認 package 結構與 PYTHONPATH 設定。錯誤: {e}"
    )
    raise

# 集中管理 log 訊息，方便多語系擴充
LOG_MSGS = {
    "zh_tw": {
        "no_close": "價格資料框架必須包含 '收盤價' 欄位",
        "no_rsi": "特徵資料框架必須包含 RSI 特徵",
        "no_model": "必須先訓練模型",
        "unknown_model": "不支援的模型類型: {model_type}",
        "unknown_strategy": "不支援的策略名稱: {strategy_name}",
        "index_structure_error": "價格資料 index 結構需包含 'stock_id' 層級，請確認資料格式。",
        "target_type_error": "target_df 必須為 pandas.Series 型別，請確認資料格式。",
    },
    # 可擴充其他語系
}
LOG_LANG = "zh_tw"

# 設定日誌
logger = logging.getLogger("strategy")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class Strategy:
    """策略基類，所有具體策略都應該繼承此類"""

    def __init__(self, name="BaseStrategy"):
        """
        初始化策略

        Args:
            name (str): 策略名稱
        """
        self.name = name

    def generate_signals(self, features_df):
        """
        生成交易訊號

        Args:
            features_df (pandas.DataFrame): 特徵資料框架

        Returns:
            pandas.DataFrame: 包含交易訊號的資料框架
        """
        # 基類不實現具體的訊號生成邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 generate_signals 方法")

    def optimize_parameters(self, features_df, target_df, param_grid):
        """
        優化策略參數

        Args:
            features_df (pandas.DataFrame): 特徵資料框架
            target_df (pandas.DataFrame): 目標資料框架
            param_grid (dict): 參數網格

        Returns:
            dict: 最佳參數
        """
        # 基類不實現具體的參數優化邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 optimize_parameters 方法")

    def evaluate(self, signals_df, price_df):
        """
        評估策略表現

        Args:
            signals_df (pandas.DataFrame): 訊號資料框架
            price_df (pandas.DataFrame): 價格資料框架

        Returns:
            dict: 評估結果
        """
        # 基類不實現具體的評估邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 evaluate 方法")


class MovingAverageCrossStrategy(Strategy):
    """移動平均線交叉策略"""

    def __init__(self, short_window=5, long_window=20):
        """
        初始化移動平均線交叉策略

        Args:
            short_window (int): 短期窗口大小
            long_window (int): 長期窗口大小
        """
        super().__init__(name="MovingAverageCross")
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, price_df):
        """
        生成移動平均線交叉訊號

        Args:
            price_df (pandas.DataFrame): 價格資料框架

        Returns:
            pandas.DataFrame: 包含交易訊號的資料框架
        """
        if "收盤價" not in price_df.columns:
            logger.error(LOG_MSGS[LOG_LANG]["no_close"])
            raise ValueError(LOG_MSGS[LOG_LANG]["no_close"])

        # 計算短期和長期移動平均線
        short_ma = (
            price_df["收盤價"].astype(float).rolling(window=self.short_window).mean()
        )
        long_ma = (
            price_df["收盤價"].astype(float).rolling(window=self.long_window).mean()
        )

        # 生成訊號
        signals = pd.DataFrame(index=price_df.index)
        signals["signal"] = 0.0

        # 當短期移動平均線上穿長期移動平均線時，產生買入訊號 (1)
        signals["signal"] = np.where(short_ma > long_ma, 1.0, 0.0)

        # 計算訊號變化
        signals["position_change"] = signals["signal"].diff()

        # 買入訊號
        signals["buy_signal"] = np.where(signals["position_change"] > 0, 1, 0)

        # 賣出訊號
        signals["sell_signal"] = np.where(signals["position_change"] < 0, 1, 0)

        return signals

    def optimize_parameters(self, price_df, target_returns, param_grid=None):
        """
        優化移動平均線交叉策略參數

        Args:
            price_df (pandas.DataFrame): 價格資料框架
            target_returns (pandas.Series): 目標收益率
            param_grid (dict, optional): 參數網格

        Returns:
            dict: 最佳參數
        """
        if param_grid is None:
            param_grid = {
                "short_window": range(5, 30, 5),
                "long_window": range(20, 100, 10),
            }

        best_score = -np.inf
        best_params = {}

        for short_window in param_grid["short_window"]:
            for long_window in param_grid["long_window"]:
                if short_window >= long_window:
                    continue

                # 使用當前參數創建策略
                strategy = MovingAverageCrossStrategy(short_window, long_window)

                # 生成訊號
                signals = strategy.generate_signals(price_df)

                # 計算策略收益率
                returns = self._calculate_returns(signals, price_df)

                # 計算策略評分（這裡使用夏普比率）
                score = self._calculate_sharpe_ratio(returns)

                if score > best_score:
                    best_score = score
                    best_params = {
                        "short_window": short_window,
                        "long_window": long_window,
                    }

        return best_params

    def _calculate_returns(self, signals, price_df):
        """
        計算策略收益率

        Args:
            signals (pandas.DataFrame): 訊號資料框架
            price_df (pandas.DataFrame): 價格資料框架

        Returns:
            pandas.Series: 策略收益率
        """
        # 計算每日收益率
        price_df["daily_return"] = price_df["收盤價"].astype(float).pct_change()

        # 根據訊號計算策略收益率
        strategy_returns = signals["signal"].shift(1) * price_df["daily_return"]

        return strategy_returns

    def _calculate_sharpe_ratio(self, returns, risk_free_rate=0.0):
        """
        計算夏普比率

        Args:
            returns (pandas.Series): 收益率序列
            risk_free_rate (float): 無風險利率

        Returns:
            float: 夏普比率
        """
        # 計算年化收益率
        annual_return = returns.mean() * 252

        # 計算年化波動率
        annual_volatility = returns.std() * np.sqrt(252)

        # 計算夏普比率
        sharpe_ratio = (
            (annual_return - risk_free_rate) / annual_volatility
            if annual_volatility != 0
            else 0
        )

        return sharpe_ratio

    def evaluate(self, price_df):
        """
        評估移動平均線交叉策略表現

        Args:
            price_df (pandas.DataFrame): 價格資料框架

        Returns:
            dict: 評估結果
        """
        # 生成訊號
        signals = self.generate_signals(price_df)

        # 計算策略收益率
        returns = self._calculate_returns(signals, price_df)

        # 計算累積收益率
        cumulative_returns = (1 + returns).cumprod()

        # 計算最大回撤
        max_drawdown = self._calculate_max_drawdown(cumulative_returns)

        # 計算夏普比率
        sharpe_ratio = self._calculate_sharpe_ratio(returns)

        # 計算勝率
        win_rate = self._calculate_win_rate(returns)

        # 返回評估結果
        return {
            "cumulative_returns": (
                cumulative_returns.iloc[-1] if not cumulative_returns.empty else 1.0
            ),
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "win_rate": win_rate,
        }

    def _calculate_max_drawdown(self, cumulative_returns):
        """
        計算最大回撤

        Args:
            cumulative_returns (pandas.Series): 累積收益率序列

        Returns:
            float: 最大回撤
        """
        # 計算歷史最高點
        running_max = cumulative_returns.cummax()

        # 計算回撤
        drawdown = cumulative_returns / running_max - 1

        # 計算最大回撤
        max_drawdown = drawdown.min()

        return max_drawdown

    def _calculate_win_rate(self, returns):
        """
        計算勝率

        Args:
            returns (pandas.Series): 收益率序列

        Returns:
            float: 勝率
        """
        # 計算勝率
        win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0

        return win_rate


class RSIStrategy(Strategy):
    """RSI 策略"""

    def __init__(self, rsi_window=14, overbought=70, oversold=30):
        """
        初始化 RSI 策略

        Args:
            rsi_window (int): RSI 窗口大小
            overbought (int): 超買閾值
            oversold (int): 超賣閾值
        """
        super().__init__(name="RSI")
        self.rsi_window = rsi_window
        self.overbought = overbought
        self.oversold = oversold

    def generate_signals(self, features_df):
        """
        生成 RSI 策略訊號

        Args:
            features_df (pandas.DataFrame): 特徵資料框架

        Returns:
            pandas.DataFrame: 包含交易訊號的資料框架
        """
        # 檢查是否有 RSI 特徵
        rsi_cols = [col for col in features_df.columns if "RSI" in col]
        if not rsi_cols:
            logger.error(LOG_MSGS[LOG_LANG]["no_rsi"])
            raise ValueError(LOG_MSGS[LOG_LANG]["no_rsi"])

        # 使用第一個 RSI 特徵
        rsi_col = rsi_cols[0]
        rsi = features_df[rsi_col]

        # 生成訊號
        signals = pd.DataFrame(index=features_df.index)
        signals["signal"] = 0.0

        # 當 RSI 低於超賣閾值時，產生買入訊號 (1)
        signals["signal"] = np.where(rsi < self.oversold, 1.0, 0.0)

        # 當 RSI 高於超買閾值時，產生賣出訊號 (-1)
        signals["signal"] = np.where(rsi > self.overbought, -1.0, signals["signal"])

        # 計算訊號變化
        signals["position_change"] = signals["signal"].diff()

        # 買入訊號
        signals["buy_signal"] = np.where(signals["position_change"] > 0, 1, 0)

        # 賣出訊號
        signals["sell_signal"] = np.where(signals["position_change"] < 0, 1, 0)

        return signals


class MachineLearningStrategy(Strategy):
    """機器學習策略"""

    def __init__(self, model_type="random_forest", **model_params):
        """
        初始化機器學習策略

        Args:
            model_type (str): 模型類型，可選 'random_forest', 'gradient_boosting', 'svm'
            **model_params: 模型參數
        """
        super().__init__(name=f"ML_{model_type}")
        self.model_type = model_type
        self.model_params = model_params
        self.model = None

    def _create_model(self):
        """
        創建機器學習模型

        Returns:
            object: 機器學習模型
        """
        if self.model_type == "random_forest":
            return RandomForestClassifier(**self.model_params)
        elif self.model_type == "gradient_boosting":
            return GradientBoostingClassifier(**self.model_params)
        elif self.model_type == "svm":
            return SVC(**self.model_params, probability=True)
        else:
            logger.error(
                LOG_MSGS[LOG_LANG]["unknown_model"].format(model_type=self.model_type)
            )
            raise ValueError(
                LOG_MSGS[LOG_LANG]["unknown_model"].format(model_type=self.model_type)
            )

    def train(self, features_df, target_df):
        """
        訓練機器學習模型

        Args:
            features_df (pandas.DataFrame): 特徵資料框架
            target_df (pandas.DataFrame): 目標資料框架

        Returns:
            self: 訓練好的策略物件
        """
        # 型別檢查
        if not isinstance(target_df, pd.Series):
            logger.error(LOG_MSGS[LOG_LANG]["target_type_error"])
            raise TypeError(LOG_MSGS[LOG_LANG]["target_type_error"])
        # 創建模型
        self.model = self._create_model()
        # 訓練模型
        self.model.fit(features_df, target_df)
        return self

    def generate_signals(self, features_df):
        """
        生成機器學習策略訊號

        Args:
            features_df (pandas.DataFrame): 特徵資料框架

        Returns:
            pandas.DataFrame: 包含交易訊號的資料框架
        """
        if self.model is None:
            logger.error(LOG_MSGS[LOG_LANG]["no_model"])
            raise ValueError(LOG_MSGS[LOG_LANG]["no_model"])

        # 預測概率
        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(features_df)
            # 取得正類的概率
            buy_proba = proba[:, 1]
        else:
            # 如果模型不支援 predict_proba，則使用 predict
            buy_proba = self.model.predict(features_df)

        # 生成訊號
        signals = pd.DataFrame(index=features_df.index)
        signals["signal"] = 0.0

        # 當買入概率大於 0.5 時，產生買入訊號 (1)
        signals["signal"] = np.where(buy_proba > 0.5, 1.0, 0.0)

        # 計算訊號變化
        signals["position_change"] = signals["signal"].diff()

        # 買入訊號
        signals["buy_signal"] = np.where(signals["position_change"] > 0, 1, 0)

        # 賣出訊號
        signals["sell_signal"] = np.where(signals["position_change"] < 0, 1, 0)

        return signals

    def optimize_parameters(self, features_df, target_df, param_grid=None):
        """
        優化機器學習策略參數

        Args:
            features_df (pandas.DataFrame): 特徵資料框架
            target_df (pandas.DataFrame): 目標資料框架
            param_grid (dict, optional): 參數網格

        Returns:
            dict: 最佳參數
        """
        if param_grid is None:
            if self.model_type == "random_forest":
                param_grid = {
                    "n_estimators": [50, 100, 200],
                    "max_depth": [None, 5, 10, 20],
                    "min_samples_split": [2, 5, 10],
                }
            elif self.model_type == "gradient_boosting":
                param_grid = {
                    "n_estimators": [50, 100, 200],
                    "learning_rate": [0.01, 0.1, 0.2],
                    "max_depth": [3, 5, 10],
                }
            elif self.model_type == "svm":
                param_grid = {
                    "C": [0.1, 1, 10],
                    "gamma": ["scale", "auto", 0.1, 1],
                    "kernel": ["rbf", "linear"],
                }

        # 創建模型
        model = self._create_model()

        # 使用網格搜索優化參數
        grid_search = GridSearchCV(model, param_grid, cv=5, scoring="f1")
        grid_search.fit(features_df, target_df)

        # 更新模型參數
        self.model_params = grid_search.best_params_

        # 使用最佳參數創建模型
        self.model = self._create_model()
        self.model.fit(features_df, target_df)

        return grid_search.best_params_


def trade_point_decision(price_series, threshold=200):
    """
    根據價格曲線找出交易點

    Args:
        price_series (pandas.Series): 價格序列
        threshold (int): 閾值

    Returns:
        pandas.Series: 交易點決策
    """
    threshold = abs(threshold)
    q = [(price_series.index[0], price_series.index[-1])]
    ret = pd.Series(0, price_series.index)

    while q:
        ts, te = q[-1]
        q = q[:-1]

        if ts == te:
            continue

        bb = price_series.loc[ts:te]
        delta = (price_series.loc[te] - price_series.loc[ts]) / len(bb)

        slop = pd.Series(delta, index=bb.index).cumsum() + price_series.loc[ts]
        diff = bb - slop

        tmin, tmax = diff.idxmin(), diff.idxmax()
        dmin, dmax = diff.loc[tmin], diff.loc[tmax]

        ps = set([ts, te])
        if dmin < -threshold:
            ps.add(tmin)
            ret.loc[tmin] = 1

        if dmax > threshold:
            ps.add(tmax)
            ret.loc[tmax] = -1

        ps = sorted(list(ps))

        for p1, p2 in zip(ps, ps[1:]):
            if p1 == ts and p2 == te:
                continue

            q.append((p1, p2))

    ret.name = "trade_point_decision"
    return ret


def continuous_trading_signal(price_series, window):
    """
    生成連續的交易訊號

    Args:
        price_series (pandas.Series): 價格序列
        window (int): 窗口大小

    Returns:
        pandas.Series: 連續交易訊號
    """

    def generate_signal(s):
        if s[0] < s[-1]:
            smin = s.min()
            smax = s.max()
            return (s[-1] - smin) / (smax - smin) / 2 + 0.5
        else:
            smin = s.min()
            smax = s.max()
            return (s[-1] - smin) / (smax - smin) / 2

    ret = price_series.rolling(window).apply(generate_signal, raw=True)
    ret.name = "continuous_trading_signal"
    return ret


def triple_barrier(price_series, upper_barrier, lower_barrier, max_period):
    """
    三重障礙法

    Args:
        price_series (pandas.Series): 價格序列
        upper_barrier (float): 上障礙
        lower_barrier (float): 下障礙
        max_period (int): 最大持有期

    Returns:
        pandas.DataFrame: 三重障礙結果
    """

    def end_price(s):
        return (
            np.append(
                s[(s / s[0] > upper_barrier) | (s / s[0] < lower_barrier)], s[-1]
            )[0]
            / s[0]
        )

    r = np.array(range(max_period))

    def end_time(s):
        return np.append(
            r[(s / s[0] > upper_barrier) | (s / s[0] < lower_barrier)], max_period - 1
        )[0]

    p = (
        price_series.rolling(max_period)
        .apply(end_price, raw=True)
        .shift(-max_period + 1)
    )
    t = (
        price_series.rolling(max_period)
        .apply(end_time, raw=True)
        .shift(-max_period + 1)
    )
    t = pd.Series(
        [
            t.index[int(k + i)] if not math.isnan(k + i) else np.datetime64("NaT")
            for i, k in enumerate(t)
        ],
        index=t.index,
    ).dropna()

    ret = pd.DataFrame(
        {
            "triple_barrier_profit": p,
            "triple_barrier_sell_time": t,
            "triple_barrier_signal": 0,
        }
    )
    ret.triple_barrier_signal.loc[ret["triple_barrier_profit"] > upper_barrier] = 1
    ret.triple_barrier_signal.loc[ret["triple_barrier_profit"] < lower_barrier] = -1
    return ret


def fixed_time_horizon(price_series, window):
    """
    固定時間範圍的交易訊號

    Args:
        price_series (pandas.Series): 價格序列
        window (int): 窗口大小

    Returns:
        pandas.Series: 固定時間範圍的交易訊號
    """
    std = price_series.rolling(window * 4).std()
    mean = price_series.rolling(window * 4).mean()

    upper_barrier = mean + 1.5 * std
    lower_barrier = mean - 1.5 * std

    ret = pd.Series(0, index=price_series.index)
    ret[price_series > upper_barrier.shift(-window)] = -1
    ret[price_series < lower_barrier.shift(-window)] = 1

    ret.name = f"fixed_time_horizon_{window}"

    return ret


def generate_signals(features, strategy_name="moving_average_cross", **strategy_params):
    """
    生成交易訊號的主函數

    Args:
        features (pandas.DataFrame): 特徵資料框架
        strategy_name (str): 策略名稱
        **strategy_params: 策略參數

    Returns:
        pandas.DataFrame: 包含交易訊號的資料框架
    """
    # 載入價格資料
    data_dict = load_data()
    price_df = data_dict["price"]
    # 多股票 index 結構檢查
    if strategy_name in [
        "trade_point_decision",
        "continuous_trading_signal",
        "triple_barrier",
        "fixed_time_horizon",
    ]:
        if not (
            isinstance(price_df.index, pd.MultiIndex)
            and "stock_id" in price_df.index.names
        ):
            logger.error(LOG_MSGS[LOG_LANG]["index_structure_error"])
            raise ValueError(LOG_MSGS[LOG_LANG]["index_structure_error"])
    # 創建策略
    if strategy_name == "moving_average_cross":
        strategy = MovingAverageCrossStrategy(**strategy_params)
        return strategy.generate_signals(price_df)
    elif strategy_name == "rsi":
        strategy = RSIStrategy(**strategy_params)
        return strategy.generate_signals(features)
    elif strategy_name == "machine_learning":
        # 機器學習策略需要先訓練模型
        # 這裡假設已經有訓練好的模型
        strategy = MachineLearningStrategy(**strategy_params)
        if "model" in strategy_params:
            strategy.model = strategy_params["model"]
        else:
            # 如果沒有提供模型，則使用隨機森林模型
            strategy.model = RandomForestClassifier()
            # 這裡應該有訓練模型的程式碼，但為了簡化，我們跳過
        return strategy.generate_signals(features)
    elif strategy_name == "trade_point_decision":
        # 使用 trade_point_decision 函數
        threshold = strategy_params.get("threshold", 200)
        signals = pd.DataFrame()
        for stock_id in price_df.index.get_level_values("stock_id").unique():
            stock_price = price_df.xs(stock_id, level="stock_id")["收盤價"].astype(
                float
            )
            stock_signals = trade_point_decision(stock_price, threshold)
            stock_signals = pd.DataFrame(stock_signals)
            stock_signals["stock_id"] = stock_id
            stock_signals.set_index("stock_id", append=True, inplace=True)
            stock_signals = stock_signals.reorder_levels(
                ["stock_id", stock_signals.index.names[0]]
            )
            signals = pd.concat([signals, stock_signals])
        return signals
    elif strategy_name == "continuous_trading_signal":
        # 使用 continuous_trading_signal 函數
        window = strategy_params.get("window", 20)
        signals = pd.DataFrame()
        for stock_id in price_df.index.get_level_values("stock_id").unique():
            stock_price = price_df.xs(stock_id, level="stock_id")["收盤價"].astype(
                float
            )
            stock_signals = continuous_trading_signal(stock_price, window)
            stock_signals = pd.DataFrame(stock_signals)
            stock_signals["stock_id"] = stock_id
            stock_signals.set_index("stock_id", append=True, inplace=True)
            stock_signals = stock_signals.reorder_levels(
                ["stock_id", stock_signals.index.names[0]]
            )
            signals = pd.concat([signals, stock_signals])
        return signals
    elif strategy_name == "triple_barrier":
        # 使用 triple_barrier 函數
        upper_barrier = strategy_params.get("upper_barrier", 1.1)
        lower_barrier = strategy_params.get("lower_barrier", 0.9)
        max_period = strategy_params.get("max_period", 20)
        signals = pd.DataFrame()
        for stock_id in price_df.index.get_level_values("stock_id").unique():
            stock_price = price_df.xs(stock_id, level="stock_id")["收盤價"].astype(
                float
            )
            stock_signals = triple_barrier(
                stock_price, upper_barrier, lower_barrier, max_period
            )
            stock_signals["stock_id"] = stock_id
            stock_signals.set_index("stock_id", append=True, inplace=True)
            stock_signals = stock_signals.reorder_levels(
                ["stock_id", stock_signals.index.names[0]]
            )
            signals = pd.concat([signals, stock_signals])
        return signals
    elif strategy_name == "fixed_time_horizon":
        # 使用 fixed_time_horizon 函數
        window = strategy_params.get("window", 20)
        signals = pd.DataFrame()
        for stock_id in price_df.index.get_level_values("stock_id").unique():
            stock_price = price_df.xs(stock_id, level="stock_id")["收盤價"].astype(
                float
            )
            stock_signals = fixed_time_horizon(stock_price, window)
            stock_signals = pd.DataFrame(stock_signals)
            stock_signals["stock_id"] = stock_id
            stock_signals.set_index("stock_id", append=True, inplace=True)
            stock_signals = stock_signals.reorder_levels(
                ["stock_id", stock_signals.index.names[0]]
            )
            signals = pd.concat([signals, stock_signals])
        return signals
    else:
        logger.error(
            LOG_MSGS[LOG_LANG]["unknown_strategy"].format(strategy_name=strategy_name)
        )
        raise ValueError(
            LOG_MSGS[LOG_LANG]["unknown_strategy"].format(strategy_name=strategy_name)
        )


class HybridStrategy:
    """
    多框架混合策略範本，支援VectorBT、Qlib等信號融合，可擴充FinRL、Riskfolio-Lib等。
    """

    def __init__(self):
        # 假設已經有對應的engine/adapters初始化
        try:
            from open_source_libs.vectorbt import VectorBTEngine
            from open_source_libs.qlib import QlibAnalyzer
        except ImportError:
            VectorBTEngine = None
            QlibAnalyzer = None
        self.vectorbt_engine = VectorBTEngine() if VectorBTEngine else None
        self.qlib_analyzer = QlibAnalyzer() if QlibAnalyzer else None
        # 可擴充：FinRL、Riskfolio-Lib等

    def generate_signal(self, data):
        """
        多框架信號融合
        :param data: 輸入資料
        :return: 融合後信號
        """
        bt_signal = (
            self.vectorbt_engine.analyze(data)
            if self.vectorbt_engine
            else np.ones(len(data))
        )
        qlib_signal = (
            self.qlib_analyzer.predict(data)
            if self.qlib_analyzer
            else np.ones(len(data))
        )
        # 融合規則可自訂，這裡以乘積大於0.5為例
        return np.where(bt_signal * qlib_signal > 0.5, 1, 0)


# ========== Cython加速範例 ==========
# 將下列函數內容複製到 strategy_cython.pyx 並用Cython編譯
# cdef: 靜態型別宣告, cpdef: 可被C/Python呼叫
# cython: boundscheck=False, wraparound=False
#
# cpdef cython_moving_average(double[:] arr, int window):
#     cdef int n = arr.shape[0]
#     cdef double[:] result = np.zeros(n, dtype=np.float64)
#     cdef double s = 0
#     cdef int i
#     for i in range(n):
#         if i < window:
#             s += arr[i]
#             result[i] = s / (i+1)
#         else:
#             s += arr[i] - arr[i-window]
#             result[i] = s / window
#     return np.asarray(result)

# ========== Numba JIT加速範例 ==========


@njit(fastmath=True, cache=True)
def numba_moving_average(arr, window):
    n = arr.shape[0]
    result = np.zeros(n, dtype=np.float64)
    s = 0.0
    for i in range(n):
        if i < window:
            s += arr[i]
            result[i] = s / (i + 1)
        else:
            s += arr[i] - arr[i - window]
            result[i] = s / window
    return result


# 在MovingAverageCrossStrategy內可用：
# short_ma = numba_moving_average(price_df['收盤價'].values, self.short_window)

# ========== FPGA加速代碼模板（VHDL/Verilog註解） ==========
# -- VHDL範例：移動平均
# -- entity MovingAverage is
# --   Port ( clk : in STD_LOGIC;
# --          rst : in STD_LOGIC;
# --          data_in : in STD_LOGIC_VECTOR(31 downto 0);
# --          ma_out : out STD_LOGIC_VECTOR(31 downto 0));
# -- end MovingAverage;
# -- architecture Behavioral of MovingAverage is
# --   signal window : array (0 to N-1) of STD_LOGIC_VECTOR(31 downto 0);
# --   signal sum : STD_LOGIC_VECTOR(31 downto 0);
# -- begin
# --   -- 實現移動平均邏輯
# -- end Behavioral;
