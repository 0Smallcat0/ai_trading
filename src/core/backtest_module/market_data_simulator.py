"""
市場數據模擬器模組

此模組提供市場數據模擬功能，用於生成模擬數據和異常情境，
以便在回測過程中測試策略在不同市場條件下的表現。
"""

import datetime
import random

import numpy as np
import pandas as pd

__all__ = ["MarketDataSimulator"]


class MarketDataSimulator:
    """
    市場數據模擬器，用於生成模擬數據和異常情境

    主要功能：
    - 生成正常市場數據
    - 模擬市場崩盤情境
    - 模擬流動性不足情境
    - 模擬高波動性情境
    """

    def __init__(self, base_data=None, seed=None):
        """
        初始化市場數據模擬器

        Args:
            base_data (pd.DataFrame, optional): 基礎數據，用於生成模擬數據
            seed (int, optional): 隨機種子，用於重現結果
        """
        self.base_data = base_data
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

    def generate_normal_market(self, n_stocks=5, n_days=252, start_date=None):
        """
        生成正常市場數據

        Args:
            n_stocks (int): 股票數量
            n_days (int): 天數
            start_date (datetime.date, optional): 開始日期

        Returns:
            pd.DataFrame: 模擬的市場數據，MultiIndex (stock_id, date)
        """
        if start_date is None:
            start_date = datetime.date.today() - datetime.timedelta(days=n_days)

        # 生成日期範圍
        dates = [start_date + datetime.timedelta(days=i) for i in range(n_days)]

        # 生成股票代碼
        stock_ids = [f"SIM{i:04d}" for i in range(n_stocks)]

        # 生成價格數據
        data = []
        for stock_id in stock_ids:
            # 初始價格在 50-200 之間隨機
            price = random.uniform(50, 200)
            for date in dates:
                # 每日價格變動在 -2% 到 2% 之間
                daily_return = random.uniform(-0.02, 0.02)
                price *= 1 + daily_return

                # 生成開高低收量
                open_price = price * random.uniform(0.99, 1.01)
                high_price = price * random.uniform(1.0, 1.03)
                low_price = price * random.uniform(0.97, 1.0)
                close_price = price
                volume = int(random.uniform(100000, 1000000))

                data.append(
                    {
                        "stock_id": stock_id,
                        "date": date,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "volume": volume,
                    }
                )

        # 創建 DataFrame 並設置 MultiIndex
        df = pd.DataFrame(data)
        df = df.set_index(["stock_id", "date"])

        return df

    def simulate_market_crash(
        self, data, crash_date, crash_pct=-0.15, recovery_days=30
    ):
        """
        模擬市場崩盤情境

        Args:
            data (pd.DataFrame): 原始市場數據
            crash_date (datetime.date): 崩盤日期
            crash_pct (float): 崩盤幅度，負數表示下跌
            recovery_days (int): 恢復天數

        Returns:
            pd.DataFrame: 模擬崩盤後的市場數據
        """
        # 複製原始數據
        simulated_data = data.copy()

        # 獲取所有日期並排序
        all_dates = sorted(data.index.get_level_values("date").unique())

        # 找到崩盤日期的索引
        try:
            crash_idx = all_dates.index(crash_date)
        except ValueError:
            # 如果找不到確切日期，找最接近的日期
            crash_idx = min(
                range(len(all_dates)),
                key=lambda i: abs((all_dates[i] - crash_date).days),
            )
            crash_date = all_dates[crash_idx]

        # 確保有足夠的恢復天數
        recovery_days = min(recovery_days, len(all_dates) - crash_idx - 1)

        # 對每支股票應用崩盤效應
        for stock_id in data.index.get_level_values("stock_id").unique():
            # 崩盤日價格變動
            if (stock_id, crash_date) in simulated_data.index:
                # 崩盤日的價格變動
                crash_factor = 1 + crash_pct * random.uniform(
                    0.8, 1.2
                )  # 添加一些隨機性

                # 更新崩盤日的價格
                for col in ["open", "high", "low", "close"]:
                    if col in simulated_data.columns:
                        simulated_data.loc[(stock_id, crash_date), col] *= crash_factor

                # 崩盤日成交量暴增
                if "volume" in simulated_data.columns:
                    simulated_data.loc[
                        (stock_id, crash_date), "volume"
                    ] *= random.uniform(3, 5)

                # 恢復期的價格變動
                for i in range(1, recovery_days + 1):
                    if crash_idx + i < len(all_dates):
                        recovery_date = all_dates[crash_idx + i]
                        if (stock_id, recovery_date) in simulated_data.index:
                            # 計算恢復因子，隨著時間推移逐漸恢復
                            recovery_progress = i / recovery_days
                            recovery_factor = 1 + (
                                abs(crash_pct)
                                * 0.7
                                * recovery_progress
                                * random.uniform(0.8, 1.2)
                            )

                            # 更新恢復期的價格
                            for col in ["open", "high", "low", "close"]:
                                if col in simulated_data.columns:
                                    simulated_data.loc[
                                        (stock_id, recovery_date), col
                                    ] *= recovery_factor

                            # 恢復期成交量逐漸回落
                            if "volume" in simulated_data.columns:
                                volume_factor = 3 - 2 * recovery_progress
                                simulated_data.loc[
                                    (stock_id, recovery_date), "volume"
                                ] *= volume_factor

        return simulated_data

    def simulate_liquidity_crisis(
        self, data, start_date, end_date, affected_stocks=None, severity=0.7
    ):
        """
        模擬流動性不足情境

        Args:
            data (pd.DataFrame): 原始市場數據
            start_date (datetime.date): 開始日期
            end_date (datetime.date): 結束日期
            affected_stocks (list, optional): 受影響的股票列表，如果為 None 則隨機選擇
            severity (float): 嚴重程度，0-1 之間

        Returns:
            pd.DataFrame: 模擬流動性危機後的市場數據
        """
        # 複製原始數據
        simulated_data = data.copy()

        # 獲取所有股票
        all_stocks = data.index.get_level_values("stock_id").unique()

        # 如果沒有指定受影響的股票，隨機選擇 30% 的股票
        if affected_stocks is None:
            n_affected = max(1, int(len(all_stocks) * 0.3))
            affected_stocks = random.sample(list(all_stocks), n_affected)

        # 獲取日期範圍
        date_mask = (data.index.get_level_values("date") >= start_date) & (
            data.index.get_level_values("date") <= end_date
        )

        # 對受影響的股票應用流動性危機效應
        for stock_id in affected_stocks:
            # 選擇該股票在日期範圍內的數據
            stock_mask = (
                data.index.get_level_values("stock_id") == stock_id
            ) & date_mask

            if stock_mask.any():
                # 成交量大幅下降
                if "volume" in simulated_data.columns:
                    simulated_data.loc[
                        stock_mask, "volume"
                    ] *= 1 - severity * random.uniform(0.8, 1.0)

                # 價格波動加大
                for col in ["open", "high", "low", "close"]:
                    if col in simulated_data.columns:
                        # 添加更大的價格波動
                        noise = np.random.normal(
                            0, severity * 0.03, size=stock_mask.sum()
                        )
                        simulated_data.loc[stock_mask, col] *= 1 + noise

                # 確保 high >= open >= low 和 high >= close >= low
                if all(
                    col in simulated_data.columns
                    for col in ["open", "high", "low", "close"]
                ):
                    for idx in simulated_data[stock_mask].index:
                        row = simulated_data.loc[idx]
                        high = max(row["open"], row["close"], row["high"])
                        low = min(row["open"], row["close"], row["low"])
                        simulated_data.loc[idx, "high"] = high
                        simulated_data.loc[idx, "low"] = low

        return simulated_data

    def simulate_high_volatility(
        self, data, start_date, end_date, volatility_factor=2.5
    ):
        """
        模擬高波動性情境

        Args:
            data (pd.DataFrame): 原始市場數據
            start_date (datetime.date): 開始日期
            end_date (datetime.date): 結束日期
            volatility_factor (float): 波動性放大因子

        Returns:
            pd.DataFrame: 模擬高波動性後的市場數據
        """
        # 複製原始數據
        simulated_data = data.copy()

        # 獲取日期範圍
        date_mask = (data.index.get_level_values("date") >= start_date) & (
            data.index.get_level_values("date") <= end_date
        )

        # 對所有股票應用高波動性效應
        for stock_id in data.index.get_level_values("stock_id").unique():
            # 選擇該股票在日期範圍內的數據
            stock_mask = (
                data.index.get_level_values("stock_id") == stock_id
            ) & date_mask

            if stock_mask.any():
                # 獲取該股票在日期範圍內的收盤價
                if "close" in simulated_data.columns:
                    # 計算原始波動性
                    close_prices = simulated_data.loc[stock_mask, "close"]
                    returns = close_prices.pct_change().dropna()

                    if len(returns) > 1:
                        # 生成新的高波動性收益率
                        mean_return = returns.mean()
                        std_return = returns.std() * volatility_factor
                        new_returns = np.random.normal(
                            mean_return, std_return, size=len(returns)
                        )

                        # 從第一個價格開始重建價格序列
                        first_price = close_prices.iloc[0]
                        new_prices = [first_price]
                        for ret in new_returns:
                            new_prices.append(new_prices[-1] * (1 + ret))

                        # 更新收盤價
                        simulated_data.loc[stock_mask, "close"] = pd.Series(
                            new_prices, index=close_prices.index
                        )

                        # 更新開高低價
                        if all(
                            col in simulated_data.columns
                            for col in ["open", "high", "low"]
                        ):
                            # 獲取原始的開高低收價差異
                            for i, idx in enumerate(simulated_data[stock_mask].index):
                                if i > 0:  # 跳過第一個數據點
                                    new_close = simulated_data.loc[idx, "close"]

                                    # 根據新的收盤價生成開高低價
                                    simulated_data.loc[idx, "open"] = new_close * (
                                        1 + np.random.normal(0, 0.01)
                                    )
                                    simulated_data.loc[idx, "high"] = new_close * (
                                        1 + abs(np.random.normal(0, 0.02))
                                    )
                                    simulated_data.loc[idx, "low"] = new_close * (
                                        1 - abs(np.random.normal(0, 0.02))
                                    )

                                    # 確保 high >= open >= low 和 high >= close >= low
                                    row = simulated_data.loc[idx]
                                    high = max(row["open"], row["close"], row["high"])
                                    low = min(row["open"], row["close"], row["low"])
                                    simulated_data.loc[idx, "high"] = high
                                    simulated_data.loc[idx, "low"] = low

        return simulated_data
