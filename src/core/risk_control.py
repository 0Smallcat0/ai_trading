"""
風險管理與停損／停利模組

此模組負責管理交易風險，實現各種風險控制策略，
包括停損、停利、部位大小控制、風險分散等。

主要功能：
- 停損策略
- 停利策略
- 部位大小控制
- 風險分散
- 風險指標計算
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

try:
    from src.core.data_ingest import load_data
except ImportError as e:
    raise ImportError(
        "無法匯入 .data_ingest，請確認你在 package 結構下執行，或設置 PYTHONPATH。錯誤："
        + str(e)
    )
try:
    from src.utils.utils import align_timeseries
except ImportError as e:
    raise ImportError(
        "無法匯入 .utils，請確認你在 package 結構下執行，或設置 PYTHONPATH。錯誤："
        + str(e)
    )


def compute_position_size(portfolio_value, risk_pct):
    """
    依據投資組合價值與單筆風險比例計算最大下單量

    Args:
        portfolio_value (float): 投資組合總價值
        risk_pct (float): 單筆交易風險比例，例如 0.01 表示 1%

    Returns:
        float: 最大下單量（金額）

    Example:
        volume = compute_position_size(1000000, 0.01)  # 風險 1%，回傳 10000
    """
    # 計算最大風險金額
    max_risk_amount = portfolio_value * risk_pct

    return max_risk_amount


def monitor_drawdown(equity_curve, threshold):
    """
    監控最大回撤，如果超過閾值則觸發停單

    Args:
        equity_curve (pandas.Series): 權益曲線，索引為日期
        threshold (float): 回撤閾值，例如 0.1 表示 10%

    Returns:
        bool: 如果最大回撤超過閾值，回傳 True（觸發停單）

    Example:
        stop_trading = monitor_drawdown(equity_curve, 0.1)  # 回撤超過 10% 觸發停單
    """
    # 確保 equity_curve 是 Series
    if not isinstance(equity_curve, pd.Series):
        equity_curve = pd.Series(equity_curve)

    # 計算累積最大值
    running_max = equity_curve.cummax()

    # 計算回撤
    drawdown = equity_curve / running_max - 1

    # 計算最大回撤
    max_drawdown = drawdown.min()

    # 檢查是否超過閾值
    return abs(max_drawdown) > threshold


class RiskManager:
    """風險管理類，用於管理交易風險"""

    def __init__(
        self,
        max_position_size=0.1,
        max_portfolio_risk=0.02,
        stop_loss_pct=0.05,
        stop_profit_pct=0.1,
    ):
        """
        初始化風險管理器

        Args:
            max_position_size (float): 最大部位大小（佔總資金的比例）
            max_portfolio_risk (float): 最大投資組合風險（佔總資金的比例）
            stop_loss_pct (float): 停損百分比
            stop_profit_pct (float): 停利百分比
        """
        self.max_position_size = max_position_size
        self.max_portfolio_risk = max_portfolio_risk
        self.stop_loss_pct = stop_loss_pct
        self.stop_profit_pct = stop_profit_pct

    def filter_signals(self, signals, portfolio_value, positions=None, price_df=None):
        """
        過濾交易訊號，根據風險控制策略

        Args:
            signals (pandas.DataFrame): 交易訊號
            portfolio_value (float): 投資組合價值
            positions (dict, optional): 當前持倉
            price_df (pandas.DataFrame, optional): 價格資料

        Returns:
            pandas.DataFrame: 過濾後的交易訊號
        """
        if positions is None:
            positions = {}

        if price_df is None:
            # 如果沒有提供價格資料，則載入資料
            data_dict = load_data()
            assert isinstance(
                data_dict, dict
            ), "load_data() 應回傳 dict，且需包含 'price' 鍵"
            if "price" not in data_dict:
                raise KeyError(
                    "data_dict 必須包含 'price' 鍵，請檢查 load_data() 回傳內容"
                )
            price_df = data_dict["price"]
            assert isinstance(
                price_df, pd.DataFrame
            ), "data_dict['price'] 應為 pandas.DataFrame"

        # 複製訊號資料框架
        assert isinstance(signals, pd.DataFrame), "signals 必須為 pandas.DataFrame"
        filtered_signals = signals.copy()

        # 獲取所有有買入訊號的股票
        if "buy_signal" in filtered_signals.columns:
            buy_signals = filtered_signals[filtered_signals["buy_signal"] == 1]
        else:
            if "signal" not in filtered_signals.columns:
                raise ValueError("signals 必須包含 'buy_signal' 或 'signal' 欄位")
            buy_signals = filtered_signals[filtered_signals["signal"] > 0]

        # 獲取所有有賣出訊號的股票
        if "sell_signal" in filtered_signals.columns:
            sell_signals = filtered_signals[filtered_signals["sell_signal"] == 1]
        else:
            if "signal" not in filtered_signals.columns:
                raise ValueError("signals 必須包含 'sell_signal' 或 'signal' 欄位")
            sell_signals = filtered_signals[filtered_signals["signal"] < 0]

        # 過濾買入訊號
        for (stock_id, date), _ in buy_signals.iterrows():
            assert isinstance(stock_id, str), "stock_id 必須為字串"
            # 檢查是否已經持有該股票
            if stock_id in positions:
                # 如果已經持有，則不再買入
                filtered_signals.loc[(stock_id, date), "buy_signal"] = 0
                continue

            # 計算部位大小
            position_size = self.calculate_position_size(
                stock_id, portfolio_value, price_df
            )

            # 檢查部位大小是否超過最大限制
            if position_size > self.max_position_size * portfolio_value:
                # 如果超過，則不買入
                filtered_signals.loc[(stock_id, date), "buy_signal"] = 0

        # 過濾賣出訊號
        for (stock_id, date), _ in sell_signals.iterrows():
            assert isinstance(stock_id, str), "stock_id 必須為字串"
            # 檢查是否持有該股票
            if stock_id not in positions:
                # 如果沒有持有，則不賣出
                filtered_signals.loc[(stock_id, date), "sell_signal"] = 0
                continue

            # 檢查是否需要停損或停利
            if self.check_stop_loss_profit(stock_id, date, positions, price_df):
                # 如果需要停損或停利，則保留賣出訊號
                pass
            else:
                # 如果不需要停損或停利，則根據原始訊號決定是否賣出
                pass

        return filtered_signals

    def calculate_position_size(self, stock_id, portfolio_value, price_df):
        """
        計算部位大小

        Args:
            stock_id (str): 股票代號
            portfolio_value (float): 投資組合價值
            price_df (pandas.DataFrame): 價格資料

        Returns:
            float: 部位大小（金額）
        """
        # 獲取最新價格
        assert isinstance(price_df, pd.DataFrame), "price_df 必須為 pandas.DataFrame"
        stock_prices = price_df.xs(stock_id, level="stock_id")["收盤價"].astype(float)

        # 計算波動率
        volatility = self._calculate_volatility(stock_id, price_df)

        # 計算部位大小（根據波動率調整）
        position_size = (
            portfolio_value * self.max_portfolio_risk / volatility
            if volatility > 0
            else 0
        )

        # 限制部位大小不超過最大限制
        position_size = min(position_size, portfolio_value * self.max_position_size)

        return position_size

    def check_stop_loss_profit(self, stock_id, date, positions, price_df):
        """
        檢查是否需要停損或停利

        Args:
            stock_id (str): 股票代號
            date (datetime.date): 日期
            positions (dict): 當前持倉
            price_df (pandas.DataFrame): 價格資料

        Returns:
            bool: 是否需要停損或停利
        """
        # 檢查是否持有該股票
        if stock_id not in positions:
            return False

        # 獲取持倉資訊
        position = positions[stock_id]

        # 獲取當前價格
        current_price = self._get_price(stock_id, date, price_df)

        # 計算收益率
        if "cost" in position:
            cost = position["cost"]
            return_rate = (current_price - cost) / cost

            # 檢查是否需要停損
            if return_rate <= -self.stop_loss_pct:
                return True

            # 檢查是否需要停利
            if return_rate >= self.stop_profit_pct:
                return True

        return False

    def _get_latest_price(self, stock_id, price_df):
        """
        獲取最新價格

        Args:
            stock_id (str): 股票代號
            price_df (pandas.DataFrame): 價格資料

        Returns:
            float: 最新價格
        """
        # 獲取該股票的所有價格
        stock_prices = price_df.xs(stock_id, level="stock_id")["收盤價"].astype(float)

        # 獲取最新價格
        latest_price = stock_prices.iloc[-1] if not stock_prices.empty else 0

        return latest_price

    def _get_price(self, stock_id, date, price_df):
        """
        獲取指定日期的價格

        Args:
            stock_id (str): 股票代號
            date (datetime.date): 日期
            price_df (pandas.DataFrame): 價格資料

        Returns:
            float: 價格
        """
        # 檢查是否有該日期的價格
        assert isinstance(price_df, pd.DataFrame), "price_df 必須為 pandas.DataFrame"
        if (stock_id, date) in price_df.index:
            return price_df.loc[(stock_id, date), "收盤價"]

        # 如果沒有該日期的價格，則返回最近的價格
        stock_prices = price_df.xs(stock_id, level="stock_id")["收盤價"].astype(float)

        # 獲取最近的價格
        nearest_price = stock_prices.iloc[-1] if not stock_prices.empty else 0

        return nearest_price

    def _calculate_volatility(self, stock_id, price_df, window=20):
        """
        計算波動率

        Args:
            stock_id (str): 股票代號
            price_df (pandas.DataFrame): 價格資料
            window (int): 窗口大小

        Returns:
            float: 波動率
        """
        # 獲取該股票的所有價格
        stock_prices = price_df.xs(stock_id, level="stock_id")["收盤價"].astype(float)

        # 計算收益率
        returns = stock_prices.pct_change().dropna()

        # 計算波動率
        volatility = (
            returns.rolling(window=window).std().iloc[-1]
            if len(returns) >= window
            else returns.std()
        )

        return (
            volatility if not np.isnan(volatility) else 0.01
        )  # 如果波動率為 NaN，則使用預設值


class PositionSizer:
    """部位大小計算類，用於計算交易部位大小"""

    def __init__(self, risk_per_trade=0.01, position_sizing_method="risk_based"):
        """
        初始化部位大小計算器

        Args:
            risk_per_trade (float): 每筆交易的風險（佔總資金的比例）
            position_sizing_method (str): 部位大小計算方法，可選 'risk_based'（風險基礎）,
                                         'equal_weight'（等權重）, 'kelly'（凱利公式）
        """
        self.risk_per_trade = risk_per_trade
        self.position_sizing_method = position_sizing_method

    def calculate_position_size(
        self,
        portfolio_value,
        entry_price,
        stop_loss_price,
        win_rate=None,
        reward_risk_ratio=None,
    ):
        """
        計算部位大小

        Args:
            portfolio_value (float): 投資組合價值
            entry_price (float): 進場價格
            stop_loss_price (float): 停損價格
            win_rate (float, optional): 勝率，用於凱利公式計算
            reward_risk_ratio (float, optional): 獎風險比，用於凱利公式計算

        Returns:
            float: 部位大小（股數）
        """
        if self.position_sizing_method == "risk_based":
            return self._risk_based_position_size(
                portfolio_value, entry_price, stop_loss_price
            )
        elif self.position_sizing_method == "equal_weight":
            return self._equal_weight_position_size(portfolio_value, entry_price)
        elif self.position_sizing_method == "kelly":
            if win_rate is None or reward_risk_ratio is None:
                raise ValueError("使用凱利公式計算部位大小需要提供勝率和獎風險比")
            return self._kelly_position_size(
                portfolio_value, win_rate, reward_risk_ratio
            )
        else:
            raise ValueError(f"不支援的部位大小計算方法: {self.position_sizing_method}")

    def _risk_based_position_size(self, portfolio_value, entry_price, stop_loss_price):
        """
        基於風險的部位大小計算

        Args:
            portfolio_value (float): 投資組合價值
            entry_price (float): 進場價格
            stop_loss_price (float): 停損價格

        Returns:
            float: 部位大小（股數）
        """
        # 計算每股風險
        risk_per_share = abs(entry_price - stop_loss_price)

        # 計算可承受的風險金額
        risk_amount = portfolio_value * self.risk_per_trade

        # 計算部位大小
        position_size = risk_amount / risk_per_share if risk_per_share > 0 else 0

        return position_size

    def _equal_weight_position_size(
        self, portfolio_value, entry_price, num_positions=10
    ):
        """
        等權重部位大小計算

        Args:
            portfolio_value (float): 投資組合價值
            entry_price (float): 進場價格
            num_positions (int): 預計持有的部位數量

        Returns:
            float: 部位大小（股數）
        """
        # 計算每個部位的資金
        position_value = portfolio_value / num_positions

        # 計算股數
        shares = position_value / entry_price if entry_price > 0 else 0

        return shares

    def _kelly_position_size(self, portfolio_value, win_rate, reward_risk_ratio):
        """
        凱利公式部位大小計算

        Args:
            portfolio_value (float): 投資組合價值
            win_rate (float): 勝率
            reward_risk_ratio (float): 獎風險比

        Returns:
            float: 部位大小（佔總資金的比例）
        """
        # 凱利公式: f* = (p * b - q) / b
        # 其中 p 是勝率，q 是敗率 (1-p)，b 是獎風險比

        q = 1 - win_rate
        kelly_fraction = (win_rate * reward_risk_ratio - q) / reward_risk_ratio

        # 限制凱利比例在 0 到 1 之間
        kelly_fraction = max(0, min(kelly_fraction, 1))

        # 通常使用半凱利或四分之一凱利以降低風險
        kelly_fraction = kelly_fraction * 0.5  # 半凱利

        return portfolio_value * kelly_fraction


class StopLossStrategy:
    """停損策略類，用於實現各種停損策略"""

    def __init__(self, strategy_type="fixed", **params):
        """
        初始化停損策略

        Args:
            strategy_type (str): 停損策略類型，可選 'fixed'（固定百分比）,
                               'trailing'（追蹤停損）, 'atr'（ATR停損）,
                               'time_based'（時間停損）
            **params: 策略參數，根據策略類型不同而不同
                - fixed: stop_loss_pct (float) - 停損百分比
                - trailing: stop_loss_pct (float) - 停損百分比
                - atr: atr_multiple (float) - ATR倍數
                - time_based: max_days (int) - 最大持有天數
        """
        self.strategy_type = strategy_type
        self.params = params

        # 設置預設參數
        if strategy_type == "fixed" and "stop_loss_pct" not in params:
            self.params["stop_loss_pct"] = 0.05
        elif strategy_type == "trailing" and "stop_loss_pct" not in params:
            self.params["stop_loss_pct"] = 0.05
        elif strategy_type == "atr" and "atr_multiple" not in params:
            self.params["atr_multiple"] = 2.0
        elif strategy_type == "time_based" and "max_days" not in params:
            self.params["max_days"] = 20

    def calculate_stop_loss(
        self,
        entry_price,
        current_price=None,
        high_price=None,
        atr=None,
        entry_date=None,
        current_date=None,
    ):
        """
        計算停損價格

        Args:
            entry_price (float): 進場價格
            current_price (float, optional): 當前價格
            high_price (float, optional): 最高價格
            atr (float, optional): 平均真實範圍
            entry_date (datetime.date, optional): 進場日期
            current_date (datetime.date, optional): 當前日期

        Returns:
            float: 停損價格
        """
        if self.strategy_type == "fixed":
            return self._fixed_stop_loss(entry_price)
        elif self.strategy_type == "trailing":
            return self._trailing_stop_loss(entry_price, high_price)
        elif self.strategy_type == "atr":
            return self._atr_stop_loss(entry_price, atr)
        elif self.strategy_type == "time_based":
            return self._time_based_stop_loss(
                entry_price, current_price, entry_date, current_date
            )
        else:
            raise ValueError(f"不支援的停損策略類型: {self.strategy_type}")

    def _fixed_stop_loss(self, entry_price):
        """
        固定百分比停損

        Args:
            entry_price (float): 進場價格

        Returns:
            float: 停損價格
        """
        stop_loss_pct = self.params.get("stop_loss_pct", 0.05)
        return entry_price * (1 - stop_loss_pct)

    def _trailing_stop_loss(self, entry_price, high_price):
        """
        追蹤停損

        Args:
            entry_price (float): 進場價格
            high_price (float): 最高價格

        Returns:
            float: 停損價格
        """
        stop_loss_pct = self.params.get("stop_loss_pct", 0.05)

        if high_price is None:
            return entry_price * (1 - stop_loss_pct)

        # 計算追蹤停損價格
        trailing_stop = high_price * (1 - stop_loss_pct)

        # 返回較高的停損價格
        return max(trailing_stop, entry_price * (1 - stop_loss_pct))

    def _atr_stop_loss(self, entry_price, atr):
        """
        ATR停損

        Args:
            entry_price (float): 進場價格
            atr (float): 平均真實範圍

        Returns:
            float: 停損價格
        """
        atr_multiple = self.params.get("atr_multiple", 2.0)

        if atr is None:
            return entry_price * 0.95  # 預設停損

        return entry_price - (atr * atr_multiple)

    def _time_based_stop_loss(
        self, entry_price, current_price, entry_date, current_date
    ):
        """
        時間停損

        Args:
            entry_price (float): 進場價格
            current_price (float): 當前價格
            entry_date (datetime.date): 進場日期
            current_date (datetime.date): 當前日期

        Returns:
            float: 停損價格或 None（表示不需要停損）
        """
        max_days = self.params.get("max_days", 20)

        if entry_date is None or current_date is None:
            return None

        # 計算持有天數
        holding_days = (current_date - entry_date).days

        # 如果超過最大持有天數，則返回當前價格（觸發停損）
        if holding_days >= max_days:
            return current_price

        return None  # 不需要停損


class StopProfitStrategy:
    """停利策略類，用於實現各種停利策略"""

    def __init__(self, strategy_type="fixed", **params):
        """
        初始化停利策略

        Args:
            strategy_type (str): 停利策略類型，可選 'fixed'（固定百分比）,
                               'trailing'（追蹤停利）, 'risk_reward'（風險報酬比）,
                               'target'（目標價格）
            **params: 策略參數，根據策略類型不同而不同
                - fixed: stop_profit_pct (float) - 停利百分比
                - trailing: stop_profit_pct (float) - 停利百分比
                - risk_reward: risk_reward_ratio (float) - 風險報酬比
                - target: target_price (float) - 目標價格
        """
        self.strategy_type = strategy_type
        self.params = params

        # 設置預設參數
        if strategy_type == "fixed" and "stop_profit_pct" not in params:
            self.params["stop_profit_pct"] = 0.1
        elif strategy_type == "trailing" and "stop_profit_pct" not in params:
            self.params["stop_profit_pct"] = 0.1
        elif strategy_type == "risk_reward" and "risk_reward_ratio" not in params:
            self.params["risk_reward_ratio"] = 2.0

    def calculate_stop_profit(
        self, entry_price, current_price=None, high_price=None, stop_loss_price=None
    ):
        """
        計算停利價格

        Args:
            entry_price (float): 進場價格
            current_price (float, optional): 當前價格
            high_price (float, optional): 最高價格
            stop_loss_price (float, optional): 停損價格，用於風險報酬比計算

        Returns:
            float: 停利價格
        """
        if self.strategy_type == "fixed":
            return self._fixed_stop_profit(entry_price)
        elif self.strategy_type == "trailing":
            return self._trailing_stop_profit(entry_price, high_price, current_price)
        elif self.strategy_type == "risk_reward":
            return self._risk_reward_stop_profit(entry_price, stop_loss_price)
        elif self.strategy_type == "target":
            return self._target_stop_profit()
        else:
            raise ValueError(f"不支援的停利策略類型: {self.strategy_type}")

    def _fixed_stop_profit(self, entry_price):
        """
        固定百分比停利

        Args:
            entry_price (float): 進場價格

        Returns:
            float: 停利價格
        """
        stop_profit_pct = self.params.get("stop_profit_pct", 0.1)
        return entry_price * (1 + stop_profit_pct)

    def _trailing_stop_profit(self, entry_price, high_price, current_price):
        """
        追蹤停利

        Args:
            entry_price (float): 進場價格
            high_price (float): 最高價格
            current_price (float): 當前價格

        Returns:
            float: 停利價格
        """
        stop_profit_pct = self.params.get("stop_profit_pct", 0.1)

        if high_price is None or current_price is None:
            return entry_price * (1 + stop_profit_pct)

        # 如果當前價格已經達到停利條件
        if current_price >= entry_price * (1 + stop_profit_pct):
            # 計算追蹤停利價格（從最高價回落一定比例）
            trailing_stop = high_price * (1 - stop_profit_pct * 0.3)

            # 如果追蹤停利價格高於原始停利價格，則使用追蹤停利
            if trailing_stop > entry_price * (1 + stop_profit_pct):
                return trailing_stop

        # 否則使用固定百分比停利
        return entry_price * (1 + stop_profit_pct)

    def _risk_reward_stop_profit(self, entry_price, stop_loss_price):
        """
        風險報酬比停利

        Args:
            entry_price (float): 進場價格
            stop_loss_price (float): 停損價格

        Returns:
            float: 停利價格
        """
        risk_reward_ratio = self.params.get("risk_reward_ratio", 2.0)

        if stop_loss_price is None:
            return entry_price * 1.1  # 預設停利

        # 計算風險
        risk = entry_price - stop_loss_price

        # 計算停利價格
        return entry_price + risk * risk_reward_ratio

    def _target_stop_profit(self):
        """
        目標價格停利

        Returns:
            float: 停利價格
        """
        target_price = self.params.get("target_price")

        if target_price is None:
            raise ValueError("使用目標價格停利策略需要提供 target_price 參數")

        return target_price


class RiskMetricsCalculator:
    """風險指標計算類，用於計算各種風險指標"""

    def __init__(self):
        """初始化風險指標計算器"""

    def calculate_var(self, returns, confidence_level=0.95, method="historical"):
        """
        計算風險值 (Value at Risk, VaR)

        Args:
            returns (pandas.Series): 收益率序列
            confidence_level (float): 信心水平，例如 0.95 表示 95%
            method (str): 計算方法，可選 'historical'（歷史模擬法）,
                         'parametric'（參數法）, 'monte_carlo'（蒙特卡洛模擬法）

        Returns:
            float: 風險值 (VaR)
        """
        if method == "historical":
            # 歷史模擬法
            return self._historical_var(returns, confidence_level)
        elif method == "parametric":
            # 參數法
            return self._parametric_var(returns, confidence_level)
        elif method == "monte_carlo":
            # 蒙特卡洛模擬法
            return self._monte_carlo_var(returns, confidence_level)
        else:
            raise ValueError(f"不支援的 VaR 計算方法: {method}")

    def _historical_var(self, returns, confidence_level):
        """
        使用歷史模擬法計算 VaR

        Args:
            returns (pandas.Series): 收益率序列
            confidence_level (float): 信心水平

        Returns:
            float: 風險值 (VaR)
        """
        # 排序收益率
        sorted_returns = returns.sort_values()

        # 計算分位數
        var_percentile = 1 - confidence_level

        # 計算 VaR
        var = -sorted_returns.quantile(var_percentile)

        return var

    def _parametric_var(self, returns, confidence_level):
        """
        使用參數法計算 VaR

        Args:
            returns (pandas.Series): 收益率序列
            confidence_level (float): 信心水平

        Returns:
            float: 風險值 (VaR)
        """
        # 計算均值和標準差
        mu = returns.mean()
        sigma = returns.std()

        # 計算 z 值
        z = stats.norm.ppf(confidence_level)

        # 計算 VaR
        var = -(mu + z * sigma)

        return var

    def _monte_carlo_var(self, returns, confidence_level, n_sims=10000):
        """
        使用蒙特卡洛模擬法計算 VaR

        Args:
            returns (pandas.Series): 收益率序列
            confidence_level (float): 信心水平
            n_sims (int): 模擬次數

        Returns:
            float: 風險值 (VaR)
        """
        # 計算均值和標準差
        mu = returns.mean()
        sigma = returns.std()

        # 生成隨機收益率
        random_returns = np.random.normal(mu, sigma, n_sims)

        # 排序收益率
        sorted_returns = np.sort(random_returns)

        # 計算分位數
        var_percentile = 1 - confidence_level
        var_index = int(n_sims * var_percentile)

        # 計算 VaR
        var = -sorted_returns[var_index]

        return var

    def calculate_cvar(self, returns, confidence_level=0.95):
        """
        計算條件風險值 (Conditional Value at Risk, CVaR)

        Args:
            returns (pandas.Series): 收益率序列
            confidence_level (float): 信心水平，例如 0.95 表示 95%

        Returns:
            float: 條件風險值 (CVaR)
        """
        # 排序收益率
        sorted_returns = returns.sort_values()

        # 計算分位數
        var_percentile = 1 - confidence_level

        # 計算 VaR
        var = -sorted_returns.quantile(var_percentile)

        # 計算 CVaR
        cvar = -sorted_returns[sorted_returns <= -var].mean()

        return cvar

    def calculate_volatility(
        self, returns, window=None, annualize=True, trading_days=252
    ):
        """
        計算波動率

        Args:
            returns (pandas.Series): 收益率序列
            window (int, optional): 窗口大小，如果為 None 則計算整個序列的波動率
            annualize (bool): 是否年化
            trading_days (int): 一年的交易日數

        Returns:
            float or pandas.Series: 波動率
        """
        if window is None:
            # 計算整個序列的波動率
            volatility = returns.std()

            # 年化波動率
            if annualize:
                volatility = volatility * np.sqrt(trading_days)
        else:
            # 計算滾動波動率
            volatility = returns.rolling(window=window).std()

            # 年化波動率
            if annualize:
                volatility = volatility * np.sqrt(trading_days)

        return volatility

    def calculate_max_drawdown(self, equity_curve):
        """
        計算最大回撤

        Args:
            equity_curve (pandas.Series): 權益曲線

        Returns:
            float: 最大回撤
        """
        # 計算累積最大值
        running_max = equity_curve.cummax()

        # 計算回撤
        drawdown = equity_curve / running_max - 1

        # 計算最大回撤
        max_drawdown = drawdown.min()

        return abs(max_drawdown)

    def calculate_sharpe_ratio(self, returns, risk_free_rate=0.0, trading_days=252):
        """
        計算夏普比率

        Args:
            returns (pandas.Series): 收益率序列
            risk_free_rate (float): 無風險利率
            trading_days (int): 一年的交易日數

        Returns:
            float: 夏普比率
        """
        # 計算年化收益率
        annual_return = returns.mean() * trading_days

        # 計算年化波動率
        annual_volatility = returns.std() * np.sqrt(trading_days)

        # 計算夏普比率
        sharpe_ratio = (
            (annual_return - risk_free_rate) / annual_volatility
            if annual_volatility > 0
            else 0
        )

        return sharpe_ratio

    def calculate_sortino_ratio(self, returns, risk_free_rate=0.0, trading_days=252):
        """
        計算索提諾比率

        Args:
            returns (pandas.Series): 收益率序列
            risk_free_rate (float): 無風險利率
            trading_days (int): 一年的交易日數

        Returns:
            float: 索提諾比率
        """
        # 計算年化收益率
        annual_return = returns.mean() * trading_days

        # 計算下行波動率
        downside_returns = returns[returns < 0]
        downside_volatility = (
            downside_returns.std() * np.sqrt(trading_days)
            if len(downside_returns) > 0
            else 0
        )

        # 計算索提諾比率
        sortino_ratio = (
            (annual_return - risk_free_rate) / downside_volatility
            if downside_volatility > 0
            else 0
        )

        return sortino_ratio


def filter_signals(
    signals,
    portfolio_value,
    positions=None,
    price_df=None,
    max_position_size=0.1,
    max_portfolio_risk=0.02,
    stop_loss_pct=0.05,
    stop_profit_pct=0.1,
    risk_pct=0.01,
    equity_curve=None,
    drawdown_threshold=0.1,
    max_sector_exposure=0.3,
    max_stock_count=None,
):
    """
    過濾交易訊號的主函數，結合頭寸控制與回撤保護

    Args:
        signals (pandas.DataFrame): 交易訊號
        portfolio_value (float): 投資組合價值
        positions (dict, optional): 當前持倉
        price_df (pandas.DataFrame, optional): 價格資料
        max_position_size (float): 最大部位大小（佔總資金的比例）
        max_portfolio_risk (float): 最大投資組合風險（佔總資金的比例）
        stop_loss_pct (float): 停損百分比
        stop_profit_pct (float): 停利百分比
        risk_pct (float): 單筆交易風險比例
        equity_curve (pandas.Series, optional): 權益曲線
        drawdown_threshold (float): 回撤閾值
        max_sector_exposure (float): 單一產業最大曝險（佔總資金的比例）
        max_stock_count (int, optional): 最大持股數量

    Returns:
        pandas.DataFrame: 過濾後的交易訊號
    """
    # 避免 look-ahead bias，統一用 align_timeseries() 前處理
    if signals is not None and not signals.empty:
        signals = align_timeseries(signals, None, None)

    if price_df is not None and not price_df.empty:
        price_df = align_timeseries(price_df, None, None)

    # 創建風險管理器
    risk_manager = RiskManager(
        max_position_size=max_position_size,
        max_portfolio_risk=max_portfolio_risk,
        stop_loss_pct=stop_loss_pct,
        stop_profit_pct=stop_profit_pct,
    )

    # 計算最大下單量
    compute_position_size(portfolio_value, risk_pct)

    # 檢查回撤是否超過閾值
    if equity_curve is not None and monitor_drawdown(equity_curve, drawdown_threshold):
        # 如果回撤超過閾值，清空訊號
        return pd.DataFrame(index=signals.index, columns=signals.columns).fillna(0)

    # 過濾訊號
    filtered_signals = risk_manager.filter_signals(
        signals, portfolio_value, positions, price_df
    )

    # 如果有持倉，強制執行投資組合限制
    if positions is not None:
        assert isinstance(
            positions, dict
        ), "positions 必須為 dict，格式為 {stock_id: {...}}"
        adjusted_positions = enforce_limits(
            positions,
            portfolio_value,
            max_position_size=max_position_size,
            max_sector_exposure=max_sector_exposure,
            max_stock_count=max_stock_count,
        )

        # 如果持倉有調整，更新賣出訊號
        if adjusted_positions != positions:
            for stock_id, position in positions.items():
                if (
                    stock_id not in adjusted_positions
                    or adjusted_positions[stock_id]["shares"] < position["shares"]
                ):
                    # 需要賣出或減少持倉
                    for date in filtered_signals.index.get_level_values(
                        "date"
                    ).unique():
                        if (stock_id, date) in filtered_signals.index:
                            if "sell_signal" in filtered_signals.columns:
                                filtered_signals.loc[
                                    (stock_id, date), "sell_signal"
                                ] = 1
                            elif "signal" in filtered_signals.columns:
                                filtered_signals.loc[(stock_id, date), "signal"] = -1

    # 如果有權益曲線，執行蒙特卡洛風險模擬
    if equity_curve is not None and len(equity_curve) > 30:
        risk_metrics = MonteCarlo_risk_simulation(equity_curve, n_sims=1000, horizon=20)

        # 如果預期最大回撤超過閾值，減少買入訊號
        if risk_metrics["expected_max_drawdown"] > drawdown_threshold:
            # 減少買入訊號的數量
            buy_signals = (
                filtered_signals[filtered_signals["buy_signal"] == 1]
                if "buy_signal" in filtered_signals.columns
                else filtered_signals[filtered_signals["signal"] > 0]
            )

            # 按照風險排序，只保留風險較低的前 50%
            if not buy_signals.empty:
                # 計算每個股票的波動率
                volatilities = {}
                for (stock_id, _), _ in buy_signals.iterrows():
                    if (
                        price_df is not None
                        and stock_id in price_df.index.get_level_values("stock_id")
                    ):
                        stock_prices = price_df.xs(stock_id, level="stock_id")[
                            "收盤價"
                        ].astype(float)
                        returns = stock_prices.pct_change().dropna()
                        volatilities[stock_id] = returns.std()

                # 按波動率排序
                sorted_stocks = sorted(volatilities.items(), key=lambda x: x[1])
                keep_count = max(1, len(sorted_stocks) // 2)
                keep_stocks = [stock_id for stock_id, _ in sorted_stocks[:keep_count]]

                # 清除不保留的買入訊號
                for (stock_id, date), _ in buy_signals.iterrows():
                    if stock_id not in keep_stocks:
                        if "buy_signal" in filtered_signals.columns:
                            filtered_signals.loc[(stock_id, date), "buy_signal"] = 0
                        elif "signal" in filtered_signals.columns:
                            filtered_signals.loc[(stock_id, date), "signal"] = 0

    return filtered_signals


def enforce_limits(
    positions,
    portfolio_value,
    max_position_size=0.1,
    max_sector_exposure=0.3,
    max_stock_count=None,
):
    """
    強制執行投資組合限制，調整部位大小

    Args:
        positions (dict): 當前持倉，格式為 {stock_id: {'shares': shares, 'value': value, 'sector': sector}}
        portfolio_value (float): 投資組合總價值
        max_position_size (float): 單一股票最大部位大小（佔總資金的比例）
        max_sector_exposure (float): 單一產業最大曝險（佔總資金的比例）
        max_stock_count (int, optional): 最大持股數量

    Returns:
        dict: 調整後的持倉

    Example:
        adjusted_positions = enforce_limits(positions, 1000000, max_position_size=0.1, max_sector_exposure=0.3)
    """
    # 如果沒有持倉，直接返回
    if not positions:
        return positions

    # 複製持倉，避免修改原始資料
    adjusted_positions = {
        stock_id: position.copy() for stock_id, position in positions.items()
    }

    # 計算總持倉價值
    total_position_value = sum(
        position["value"] for position in adjusted_positions.values()
    )

    # 如果總持倉價值為 0，直接返回
    if total_position_value == 0:
        return adjusted_positions

    # 檢查最大持股數量
    if max_stock_count is not None and len(adjusted_positions) > max_stock_count:
        # 按價值排序，保留價值最高的股票
        sorted_positions = sorted(
            adjusted_positions.items(), key=lambda x: x[1]["value"], reverse=True
        )
        adjusted_positions = {
            stock_id: position
            for stock_id, position in sorted_positions[:max_stock_count]
        }

    # 檢查單一股票最大部位大小
    for stock_id, position in list(adjusted_positions.items()):
        if position["value"] > portfolio_value * max_position_size:
            # 調整部位大小
            scale_factor = portfolio_value * max_position_size / position["value"]
            position["shares"] *= scale_factor
            position["value"] *= scale_factor

    # 檢查單一產業最大曝險
    if max_sector_exposure < 1.0:
        # 計算各產業曝險
        sector_exposure = {}
        for position in adjusted_positions.values():
            if "sector" in position:
                sector = position["sector"]
                if sector not in sector_exposure:
                    sector_exposure[sector] = 0
                sector_exposure[sector] += position["value"]

        # 檢查各產業曝險是否超過限制
        for sector, exposure in sector_exposure.items():
            if exposure > portfolio_value * max_sector_exposure:
                # 計算調整因子
                scale_factor = portfolio_value * max_sector_exposure / exposure

                # 調整該產業的所有持倉
                for stock_id, position in adjusted_positions.items():
                    if "sector" in position and position["sector"] == sector:
                        position["shares"] *= scale_factor
                        position["value"] *= scale_factor

    return adjusted_positions


def MonteCarlo_risk_simulation(
    equity_curve, n_sims=1000, horizon=20, confidence_level=0.95
):
    """
    使用蒙特卡洛模擬檢測尾部風險

    Args:
        equity_curve (pandas.Series): 權益曲線，索引為日期
        n_sims (int): 模擬次數
        horizon (int): 預測期間（天數）
        confidence_level (float): 信心水平，例如 0.95 表示 95%

    Returns:
        dict: 風險指標，包含 VaR、CVaR、最大回撤等

    Example:
        risk_metrics = MonteCarlo_risk_simulation(equity_curve, n_sims=1000, horizon=20)
    """
    # 確保 equity_curve 是 Series
    if not isinstance(equity_curve, pd.Series):
        equity_curve = pd.Series(equity_curve)

    # 計算每日收益率
    returns = equity_curve.pct_change().dropna()

    # 如果收益率資料不足，返回空結果
    if len(returns) < 30:
        return {
            "VaR": np.nan,
            "CVaR": np.nan,
            "max_drawdown": np.nan,
            "simulated_paths": None,
        }

    # 計算收益率的均值和標準差
    mu = returns.mean()
    sigma = returns.std()

    # 檢查是否符合常態分佈
    _, p_value = stats.normaltest(returns)
    is_normal = p_value > 0.05

    # 初始化模擬結果
    simulated_paths = np.zeros((n_sims, horizon))
    final_values = np.zeros(n_sims)
    max_drawdowns = np.zeros(n_sims)

    # 執行蒙特卡洛模擬
    for i in range(n_sims):
        # 初始值為最後一個權益值
        path = np.zeros(horizon)
        path[0] = equity_curve.iloc[-1]

        # 生成隨機收益率
        if is_normal:
            # 如果符合常態分佈，使用常態分佈生成收益率
            random_returns = np.random.normal(mu, sigma, horizon - 1)
        else:
            # 否則使用歷史收益率重抽樣
            random_returns = np.random.choice(returns, size=horizon - 1)

        # 計算模擬路徑
        for j in range(1, horizon):
            path[j] = path[j - 1] * (1 + random_returns[j - 1])

        # 儲存模擬路徑
        simulated_paths[i] = path

        # 計算最終值
        final_values[i] = path[-1]

        # 計算最大回撤
        peak = path[0]
        max_drawdown = 0
        for value in path:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        max_drawdowns[i] = max_drawdown

    # 計算風險指標
    # 計算 VaR（Value at Risk）
    VaR = np.percentile(final_values, 100 * (1 - confidence_level))

    # 計算 CVaR（Conditional Value at Risk）
    CVaR = final_values[final_values <= VaR].mean()

    # 計算最大回撤的期望值
    expected_max_drawdown = max_drawdowns.mean()

    # 繪製模擬路徑
    plt.figure(figsize=(12, 8))

    # 繪製所有模擬路徑
    for i in range(min(100, n_sims)):  # 只繪製前 100 條路徑，避免圖表過於擁擠
        plt.plot(simulated_paths[i], color="blue", alpha=0.1)

    # 繪製平均路徑
    plt.plot(simulated_paths.mean(axis=0), color="red", linewidth=2, label="平均路徑")

    # 繪製 VaR 路徑
    var_path_idx = np.abs(final_values - VaR).argmin()
    plt.plot(
        simulated_paths[var_path_idx],
        color="orange",
        linewidth=2,
        label=f"VaR ({confidence_level*100}%)",
    )

    plt.title(f"蒙特卡洛模擬 ({n_sims} 次)")
    plt.xlabel("天數")
    plt.ylabel("投資組合價值")
    plt.legend()
    plt.grid(True)

    # 繪製最終值的分佈
    plt.figure(figsize=(12, 6))
    sns.histplot(final_values, kde=True)
    plt.axvline(
        x=VaR,
        color="red",
        linestyle="--",
        label=f"VaR ({confidence_level*100}%): {VaR:.2f}",
    )
    plt.axvline(x=CVaR, color="orange", linestyle="--", label=f"CVaR: {CVaR:.2f}")
    plt.title("最終值分佈")
    plt.xlabel("投資組合價值")
    plt.ylabel("頻率")
    plt.legend()
    plt.grid(True)

    return {
        "VaR": VaR,
        "CVaR": CVaR,
        "expected_max_drawdown": expected_max_drawdown,
        "simulated_paths": simulated_paths,
        "final_values": final_values,
        "max_drawdowns": max_drawdowns,
    }
