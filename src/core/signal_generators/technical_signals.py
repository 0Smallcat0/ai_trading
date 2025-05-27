"""技術分析訊號產生器

此模組實現基於技術分析的交易訊號生成功能。
"""

import logging


import numpy as np
import pandas as pd

from .base_signal_generator import BaseSignalGenerator, LOG_MSGS
from .cache_manager import cached

logger = logging.getLogger(__name__)


class TechnicalSignalGenerator(BaseSignalGenerator):
    """技術分析訊號產生器

    基於價格動量、相對強弱指標 (RSI) 和移動平均線等技術指標生成訊號。
    """

    def generate_signals(
        self,
        short_window: int = 5,
        medium_window: int = 20,
        long_window: int = 60,
        **kwargs
    ) -> pd.DataFrame:
        """生成動量策略訊號

        基於價格動量、相對強弱指標 (RSI) 和移動平均線等技術指標生成訊號

        Args:
            short_window (int): 短期窗口大小
            medium_window (int): 中期窗口大小
            long_window (int): 長期窗口大小
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if not self.validate_data("price"):
            logger.warning(LOG_MSGS["no_price"].format(strategy="動量"))
            return pd.DataFrame()

        # 確保價格資料有 'close' 列
        if "close" not in self.price_data.columns:
            logger.warning(LOG_MSGS["no_close"])
            return pd.DataFrame()

        # 初始化訊號
        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0

        # 計算價格動量
        price_data = self.price_data.copy()

        # 使用向量化運算優化計算效能
        try:
            # 計算所有股票的移動平均線（向量化）
            close_prices = price_data["close"].unstack(level=0, fill_value=np.nan)

            # 批量計算移動平均線
            short_ma = close_prices.rolling(window=short_window).mean()
            medium_ma = close_prices.rolling(window=medium_window).mean()
            long_ma = close_prices.rolling(window=long_window).mean()

            # 批量計算 RSI
            rsi_data = close_prices.apply(lambda x: self._calculate_rsi(x))

            # 向量化訊號計算
            signal_matrix = pd.DataFrame(
                0, index=close_prices.index, columns=close_prices.columns
            )

            # 移動平均線訊號
            ma_signal_1 = (short_ma > medium_ma).astype(int) - (
                short_ma < medium_ma
            ).astype(int)
            ma_signal_2 = (medium_ma > long_ma).astype(int) - (
                medium_ma < long_ma
            ).astype(int)

            # RSI 訊號
            rsi_signal = (rsi_data < 30).astype(int) - (rsi_data > 70).astype(int)

            # 合併訊號
            signal_matrix = ma_signal_1 + ma_signal_2 + rsi_signal

            # 標準化訊號到 [-1, 0, 1]
            signal_matrix = signal_matrix.clip(-1, 1)

            # 轉換回多層索引格式
            signal_stacked = signal_matrix.stack()
            signal_stacked.index = signal_stacked.index.swaplevel(0, 1)
            signal_stacked = signal_stacked.sort_index()

            # 只保留有效的訊號
            valid_signals = signal_stacked.dropna()

            # 填充到結果 DataFrame
            for (stock_id, date), signal in valid_signals.items():
                if (stock_id, date) in signals.index:
                    signals.loc[(stock_id, date), "signal"] = int(signal)

        except Exception as e:
            logger.warning("向量化計算失敗，回退到逐股票計算: %s", e)
            # 回退到原始的逐股票計算方法
            self._calculate_momentum_signals_fallback(
                price_data, signals, short_window, medium_window, long_window
            )

        # 儲存訊號
        self.signals["momentum"] = signals

        return signals

    def _calculate_momentum_signals_fallback(
        self,
        price_data: pd.DataFrame,
        signals: pd.DataFrame,
        short_window: int,
        medium_window: int,
        long_window: int,
    ):
        """回退方法：逐股票計算動量訊號"""
        for stock_id in price_data.index.get_level_values(0).unique():
            try:
                stock_price = price_data.loc[stock_id]["close"]

                # 計算移動平均線
                short_ma = stock_price.rolling(window=short_window).mean()
                medium_ma = stock_price.rolling(window=medium_window).mean()
                long_ma = stock_price.rolling(window=long_window).mean()

                # 計算 RSI
                rsi = self._calculate_rsi(stock_price)

                # 生成訊號
                stock_signals = pd.Series(0, index=stock_price.index, dtype=int)

                # 移動平均線訊號
                stock_signals += (short_ma > medium_ma).astype(int)
                stock_signals -= (short_ma < medium_ma).astype(int)
                stock_signals += (medium_ma > long_ma).astype(int)
                stock_signals -= (medium_ma < long_ma).astype(int)

                # RSI 訊號
                stock_signals += (rsi < 30).astype(int)
                stock_signals -= (rsi > 70).astype(int)

                # 標準化訊號
                stock_signals = stock_signals.clip(-1, 1)

                # 填充結果
                for date, signal in stock_signals.items():
                    if pd.notna(signal) and (stock_id, date) in signals.index:
                        signals.loc[(stock_id, date), "signal"] = int(signal)

            except Exception as e:
                logger.warning("計算股票 %s 的動量訊號時發生錯誤: %s", stock_id, e)

    def generate_mean_reversion_signals(
        self, window: int = 20, std_dev: float = 2.0, **kwargs
    ) -> pd.DataFrame:
        """生成均值回歸策略訊號

        基於價格偏離移動平均線的程度生成訊號

        Args:
            window (int): 移動平均窗口大小
            std_dev (float): 標準差閾值，價格偏離移動平均線超過此標準差倍數時生成訊號
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if not self.validate_data("price"):
            logger.warning(LOG_MSGS["no_price"].format(strategy="均值回歸"))
            return pd.DataFrame()

        # 確保價格資料有 'close' 列
        if "close" not in self.price_data.columns:
            logger.warning(LOG_MSGS["no_close"])
            return pd.DataFrame()

        # 初始化訊號
        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0

        # 計算價格偏離移動平均線的程度
        price_data = self.price_data.copy()

        # 對每個股票分別計算
        for stock_id in price_data.index.get_level_values(0).unique():
            stock_price = price_data.loc[stock_id]["close"]

            # 計算移動平均線
            ma = stock_price.rolling(window=window).mean()

            # 計算價格偏離移動平均線的標準差
            std = stock_price.rolling(window=window).std()

            # 計算 z-score
            z_score = (stock_price - ma) / std

            # 根據 z-score 生成訊號
            stock_signals = pd.Series(0, index=stock_price.index, dtype=int)

            # 只在有效值時進行比較
            valid_zscore = ~z_score.isna()
            buy_condition = valid_zscore & (z_score < -std_dev)
            sell_condition = valid_zscore & (z_score > std_dev)

            stock_signals[buy_condition] = 1  # 價格過低，買入
            stock_signals[sell_condition] = -1  # 價格過高，賣出

            # 將股票訊號加入總訊號，使用正確的多層索引
            for date, signal in stock_signals.items():
                if pd.notna(signal):
                    signals.loc[(stock_id, date), "signal"] = int(signal)

        # 儲存訊號
        self.signals["mean_reversion"] = signals

        return signals

    def generate_breakout_signals(
        self, window: int = 20, volume_threshold: float = 1.5, **kwargs
    ) -> pd.DataFrame:
        """生成突破策略訊號

        基於價格突破和成交量確認生成訊號

        Args:
            window (int): 計算突破的窗口大小
            volume_threshold (float): 成交量閾值倍數
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 突破訊號
        """
        if not self.validate_data("price"):
            logger.warning(LOG_MSGS["no_price"].format(strategy="突破"))
            return pd.DataFrame()

        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0

        price_data = self.price_data.copy()

        # 對每個股票分別計算
        for stock_id in price_data.index.get_level_values(0).unique():
            stock_price = price_data.loc[stock_id]

            # 計算阻力位和支撐位
            high_resistance = stock_price["high"].rolling(window=window).max()
            low_support = stock_price["low"].rolling(window=window).min()

            # 計算平均成交量
            if self.volume_data is not None and stock_id in self.volume_data.index:
                avg_volume = (
                    self.volume_data.loc[stock_id].rolling(window=window).mean()
                )
                current_volume = self.volume_data.loc[stock_id]
                volume_condition = current_volume > avg_volume * volume_threshold
            else:
                volume_condition = pd.Series(True, index=stock_price.index)

            # 突破阻力位，買入訊號
            valid_resistance = (~high_resistance.isna()) & (
                ~stock_price["close"].isna()
            )
            breakout_up = (
                valid_resistance
                & (stock_price["close"] > high_resistance.shift(1))
                & volume_condition
            )

            # 跌破支撐位，賣出訊號
            valid_support = (~low_support.isna()) & (~stock_price["close"].isna())
            breakout_down = (
                valid_support
                & (stock_price["close"] < low_support.shift(1))
                & volume_condition
            )

            stock_signals = pd.Series(0, index=stock_price.index, dtype=int)
            stock_signals[breakout_up] = 1
            stock_signals[breakout_down] = -1

            # 將股票訊號加入總訊號，使用正確的多層索引
            for date, signal in stock_signals.items():
                if pd.notna(signal):
                    signals.loc[(stock_id, date), "signal"] = int(signal)

        # 儲存訊號
        self.signals["breakout"] = signals

        return signals

    def generate_crossover_signals(
        self, fast_period: int = 12, slow_period: int = 26, **kwargs
    ) -> pd.DataFrame:
        """生成交叉策略訊號

        基於移動平均線交叉生成訊號

        Args:
            fast_period (int): 快速移動平均線週期
            slow_period (int): 慢速移動平均線週期
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 交叉訊號
        """
        if not self.validate_data("price"):
            logger.warning(LOG_MSGS["no_price"].format(strategy="交叉"))
            return pd.DataFrame()

        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0

        price_data = self.price_data.copy()

        # 對每個股票分別計算
        for stock_id in price_data.index.get_level_values(0).unique():
            stock_price = price_data.loc[stock_id]["close"]

            # 計算快速和慢速移動平均線
            fast_ma = stock_price.rolling(window=fast_period).mean()
            slow_ma = stock_price.rolling(window=slow_period).mean()

            # 檢測交叉
            fast_above_slow = (fast_ma > slow_ma).fillna(False)
            fast_above_slow_prev = fast_above_slow.shift(1).fillna(False)

            # 黃金交叉（快線向上穿越慢線）
            golden_cross = fast_above_slow & (~fast_above_slow_prev)
            # 死亡交叉（快線向下穿越慢線）
            death_cross = (~fast_above_slow) & fast_above_slow_prev

            stock_signals = pd.Series(0, index=stock_price.index, dtype=int)
            stock_signals[golden_cross] = 1
            stock_signals[death_cross] = -1

            # 將股票訊號加入總訊號，使用正確的多層索引
            for date, signal in stock_signals.items():
                if pd.notna(signal):
                    signals.loc[(stock_id, date), "signal"] = int(signal)

        # 儲存訊號
        self.signals["crossover"] = signals

        return signals

    @cached(expire_hours=1, persist=False)
    def _calculate_rsi(self, price_series: pd.Series, period: int = 14) -> pd.Series:
        """計算相對強弱指標 (RSI) - 優化版本

        使用指數移動平均提升計算效率和準確度

        Args:
            price_series (pd.Series): 價格序列
            period (int): 計算週期

        Returns:
            pd.Series: RSI 值
        """
        # 使用向量化計算提升效能
        delta = price_series.diff()

        # 分離漲跌
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)

        # 使用指數移動平均 (更準確且高效)
        alpha = 1.0 / period
        avg_gains = gains.ewm(alpha=alpha, adjust=False).mean()
        avg_losses = losses.ewm(alpha=alpha, adjust=False).mean()

        # 計算 RS 和 RSI
        rs = avg_gains / avg_losses.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))

        # 處理邊界情況
        rsi = rsi.fillna(50)  # NaN 填充為中性值
        rsi = rsi.clip(0, 100)  # 確保在 0-100 範圍內

        return rsi

    def generate_all_technical_signals(self, **kwargs) -> dict:
        """生成所有技術分析訊號

        Args:
            **kwargs: 各種策略的參數

        Returns:
            dict: 包含所有技術分析訊號的字典
        """
        signals_dict = {}

        # 生成動量訊號
        signals_dict["momentum"] = self.generate_signals(**kwargs)

        # 生成均值回歸訊號
        signals_dict["mean_reversion"] = self.generate_mean_reversion_signals(**kwargs)

        # 生成突破訊號
        signals_dict["breakout"] = self.generate_breakout_signals(**kwargs)

        # 生成交叉訊號
        signals_dict["crossover"] = self.generate_crossover_signals(**kwargs)

        return signals_dict
