"""交易指標研究與選擇模組 (Trading Indicators Research and Selection Module)

此模組實現並記錄了各種交易指標，包括技術指標、基本面指標和情緒指標。
每個指標都包含詳細的說明、計算方法、參數和使用示例。

主要功能：
- 實現常用技術指標（SMA, EMA, MACD, RSI, Bollinger Bands, OBV, ATR等）
- 實現基本面指標（EPS growth, P/E, P/B等）
- 實現情緒/主題指標（如適用）
- 提供指標標準化和比較方法
- 提供指標評估工具
"""

import logging
import warnings
from typing import Dict, List, Tuple, Union

import numpy as np
import pandas as pd

# 嘗試導入 TA-Lib
try:
    from talib import abstract

    TALIB_AVAILABLE = True
except ImportError as e:
    warnings.warn(f"無法匯入 TA-Lib，部分技術指標功能將無法使用: {e}")
    TALIB_AVAILABLE = False

    # 創建空的 abstract 模組以避免錯誤
    class DummyAbstract:
        """DummyAbstract"""

        def __getattr__(self, name):
            """__getattr__

            Args:
                name: 屬性名稱
            """
            # 忽略未使用的參數警告
            _ = name
            return None

    abstract = DummyAbstract()

# 設置日誌
logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """技術指標類

    實現各種技術分析指標，包括移動平均線、動量指標、波動率指標等。
    每個指標都包含詳細的說明、計算方法和參數。
    """

    def __init__(self, price_data: pd.DataFrame = None):
        """初始化技術指標類

        Args:
            price_data (pd.DataFrame, optional): 價格資料，應包含 OHLCV 欄位
        """
        self.price_data = price_data
        self.indicators_data = {}

    def set_price_data(self, price_data: pd.DataFrame):
        """設置價格資料

        Args:
            price_data (pd.DataFrame): 價格資料，應包含 OHLCV 欄位
        """
        self.price_data = price_data

    def _prepare_ohlcv_data(
        self, price_data: pd.DataFrame = None
    ) -> Dict[str, pd.Series]:
        """準備 OHLCV 資料

        Args:
            price_data (pd.DataFrame, optional): 價格資料

        Returns:
            Dict[str, pd.Series]: OHLCV 資料字典
        """
        if price_data is None:
            price_data = self.price_data

        if price_data is None:
            raise ValueError("未提供價格資料")

        # 標準化欄位名稱
        column_mapping = {
            "open": ["open", "Open", "開盤價", "開盤"],
            "high": ["high", "High", "最高價", "最高"],
            "low": ["low", "Low", "最低價", "最低"],
            "close": ["close", "Close", "收盤價", "收盤"],
            "volume": ["volume", "Volume", "成交量", "成交股數"],
        }

        ohlcv_dict = {}

        for key, possible_names in column_mapping.items():
            for name in possible_names:
                if name in price_data.columns:
                    ohlcv_dict[key] = price_data[name]
                    break

        return ohlcv_dict

    def calculate_sma(
        self, period: int = 20, column: str = "close", price_data: pd.DataFrame = None
    ) -> pd.Series:
        """計算簡單移動平均線 (Simple Moving Average, SMA)

        SMA是最基本的移動平均線，計算過去N個週期的價格平均值。

        計算公式：SMA = (P1 + P2 + ... + Pn) / n

        Args:
            period (int): 週期長度
            column (str): 使用的價格欄位
            price_data (pd.DataFrame, optional): 價格資料

        Returns:
            pd.Series: SMA 值
        """
        if price_data is None:
            price_data = self.price_data

        ohlcv_dict = self._prepare_ohlcv_data(price_data)

        if column not in ohlcv_dict:
            raise ValueError(f"找不到欄位: {column}")

        if TALIB_AVAILABLE:
            sma = abstract.SMA(ohlcv_dict, timeperiod=period)
        else:
            sma = ohlcv_dict[column].rolling(window=period).mean()

        indicator_name = f"SMA_{period}"
        self.indicators_data[indicator_name] = sma

        return sma

    def calculate_ema(
        self, period: int = 20, column: str = "close", price_data: pd.DataFrame = None
    ) -> pd.Series:
        """計算指數移動平均線 (Exponential Moving Average, EMA)

        EMA給予最近的價格更高的權重，對價格變化的反應比SMA更快。

        計算公式：EMA = Price(t) * k + EMA(y) * (1 - k)
        其中 k = 2/(period + 1)，EMA(y)是前一天的EMA

        Args:
            period (int): 週期長度
            column (str): 使用的價格欄位
            price_data (pd.DataFrame, optional): 價格資料

        Returns:
            pd.Series: EMA 值
        """
        if price_data is None:
            price_data = self.price_data

        ohlcv_dict = self._prepare_ohlcv_data(price_data)

        if column not in ohlcv_dict:
            raise ValueError(f"找不到欄位: {column}")

        if TALIB_AVAILABLE:
            ema = abstract.EMA(ohlcv_dict, timeperiod=period)
        else:
            ema = ohlcv_dict[column].ewm(span=period, adjust=False).mean()

        indicator_name = f"EMA_{period}"
        self.indicators_data[indicator_name] = ema

        return ema

    def calculate_macd(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        column: str = "close",
        price_data: pd.DataFrame = None,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """計算移動平均收斂散度 (Moving Average Convergence Divergence, MACD)

        MACD是一種趨勢跟蹤動量指標，顯示兩條移動平均線之間的關係。

        計算公式：
        - MACD Line = 快速EMA - 慢速EMA
        - Signal Line = MACD Line的EMA
        - Histogram = MACD Line - Signal Line

        Args:
            fast_period (int): 快速EMA週期
            slow_period (int): 慢速EMA週期
            signal_period (int): 信號線EMA週期
            column (str): 使用的價格欄位
            price_data (pd.DataFrame, optional): 價格資料

        Returns:
            Tuple[pd.Series, pd.Series, pd.Series]: (MACD線, 信號線, 柱狀圖)
        """
        if price_data is None:
            price_data = self.price_data

        ohlcv_dict = self._prepare_ohlcv_data(price_data)

        if column not in ohlcv_dict:
            raise ValueError(f"找不到欄位: {column}")

        if TALIB_AVAILABLE:
            macd, signal, hist = abstract.MACD(
                ohlcv_dict,
                fastperiod=fast_period,
                slowperiod=slow_period,
                signalperiod=signal_period,
            )
        else:
            # 手動計算MACD
            fast_ema = ohlcv_dict[column].ewm(span=fast_period, adjust=False).mean()
            slow_ema = ohlcv_dict[column].ewm(span=slow_period, adjust=False).mean()
            macd = fast_ema - slow_ema
            signal = macd.ewm(span=signal_period, adjust=False).mean()
            hist = macd - signal

        indicator_name = f"MACD_{fast_period}_{slow_period}_{signal_period}"
        self.indicators_data[f"{indicator_name}_line"] = macd
        self.indicators_data[f"{indicator_name}_signal"] = signal
        self.indicators_data[f"{indicator_name}_hist"] = hist

        return macd, signal, hist

    def calculate_rsi(
        self, period: int = 14, column: str = "close", price_data: pd.DataFrame = None
    ) -> pd.Series:
        """計算相對強弱指標 (Relative Strength Index, RSI)

        RSI是一種動量指標，測量價格變動的速度和變化。

        計算公式：RSI = 100 - (100 / (1 + RS))
        其中 RS = 平均上漲幅度 / 平均下跌幅度

        Args:
            period (int): 週期長度
            column (str): 使用的價格欄位
            price_data (pd.DataFrame, optional): 價格資料

        Returns:
            pd.Series: RSI 值
        """
        if price_data is None:
            price_data = self.price_data

        ohlcv_dict = self._prepare_ohlcv_data(price_data)

        if column not in ohlcv_dict:
            raise ValueError(f"找不到欄位: {column}")

        if TALIB_AVAILABLE:
            rsi = abstract.RSI(ohlcv_dict, timeperiod=period)
        else:
            # 手動計算RSI
            delta = ohlcv_dict[column].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        indicator_name = f"RSI_{period}"
        self.indicators_data[indicator_name] = rsi

        return rsi

    def calculate_bollinger_bands(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        column: str = "close",
        price_data: pd.DataFrame = None,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """計算布林帶 (Bollinger Bands)

        布林帶是一種波動率指標，由中軌（移動平均線）和上下軌（中軌加減標準差）組成。

        計算公式：
        - 中軌 = SMA
        - 上軌 = 中軌 + (標準差 * 倍數)
        - 下軌 = 中軌 - (標準差 * 倍數)

        Args:
            period (int): 週期長度
            std_dev (float): 標準差倍數
            column (str): 使用的價格欄位
            price_data (pd.DataFrame, optional): 價格資料

        Returns:
            Tuple[pd.Series, pd.Series, pd.Series]: (上軌, 中軌, 下軌)
        """
        if price_data is None:
            price_data = self.price_data

        ohlcv_dict = self._prepare_ohlcv_data(price_data)

        if column not in ohlcv_dict:
            raise ValueError(f"找不到欄位: {column}")

        if TALIB_AVAILABLE:
            upper, middle, lower = abstract.BBANDS(
                ohlcv_dict, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev
            )
        else:
            # 手動計算布林帶
            middle = ohlcv_dict[column].rolling(window=period).mean()
            std = ohlcv_dict[column].rolling(window=period).std()
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)

        indicator_name = f"BBANDS_{period}_{std_dev}"
        self.indicators_data[f"{indicator_name}_upper"] = upper
        self.indicators_data[f"{indicator_name}_middle"] = middle
        self.indicators_data[f"{indicator_name}_lower"] = lower

        return upper, middle, lower

    def calculate_obv(self, price_data: pd.DataFrame = None) -> pd.Series:
        """計算能量潮指標 (On-Balance Volume, OBV)

        OBV是一種成交量指標，通過累計成交量來預測價格變動。

        計算公式：
        - 如果今日收盤價 > 昨日收盤價，OBV = 昨日OBV + 今日成交量
        - 如果今日收盤價 < 昨日收盤價，OBV = 昨日OBV - 今日成交量
        - 如果今日收盤價 = 昨日收盤價，OBV = 昨日OBV

        Args:
            price_data (pd.DataFrame, optional): 價格資料

        Returns:
            pd.Series: OBV 值
        """
        if price_data is None:
            price_data = self.price_data

        ohlcv_dict = self._prepare_ohlcv_data(price_data)

        if "close" not in ohlcv_dict or "volume" not in ohlcv_dict:
            raise ValueError("找不到必要的欄位: close, volume")

        if TALIB_AVAILABLE:
            obv = abstract.OBV(ohlcv_dict)
        else:
            # 手動計算OBV
            close = ohlcv_dict["close"]
            volume = ohlcv_dict["volume"]

            obv = pd.Series(index=close.index)
            obv.iloc[0] = volume.iloc[0]

            for i in range(1, len(close)):
                if close.iloc[i] > close.iloc[i - 1]:
                    obv.iloc[i] = obv.iloc[i - 1] + volume.iloc[i]
                elif close.iloc[i] < close.iloc[i - 1]:
                    obv.iloc[i] = obv.iloc[i - 1] - volume.iloc[i]
                else:
                    obv.iloc[i] = obv.iloc[i - 1]

        self.indicators_data["OBV"] = obv

        return obv

    def calculate_atr(
        self, period: int = 14, price_data: pd.DataFrame = None
    ) -> pd.Series:
        """計算平均真實範圍 (Average True Range, ATR)

        ATR是一種波動率指標，測量市場波動的程度。

        計算公式：
        TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
        ATR = SMA(TR, period)

        Args:
            period (int): 週期長度
            price_data (pd.DataFrame, optional): 價格資料

        Returns:
            pd.Series: ATR 值
        """
        if price_data is None:
            price_data = self.price_data

        ohlcv_dict = self._prepare_ohlcv_data(price_data)

        if (
            "high" not in ohlcv_dict
            or "low" not in ohlcv_dict
            or "close" not in ohlcv_dict
        ):
            raise ValueError("找不到必要的欄位: high, low, close")

        if TALIB_AVAILABLE:
            atr = abstract.ATR(ohlcv_dict, timeperiod=period)
        else:
            # 手動計算ATR
            high = ohlcv_dict["high"]
            low = ohlcv_dict["low"]
            close = ohlcv_dict["close"]

            prev_close = close.shift(1)
            tr1 = high - low
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()

            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()

        indicator_name = f"ATR_{period}"
        self.indicators_data[indicator_name] = atr

        return atr

    def standardize_indicators(self, method: str = "zscore") -> pd.DataFrame:
        """標準化所有指標

        Args:
            method (str): 標準化方法，可選 'zscore', 'minmax', 'robust'

        Returns:
            pd.DataFrame: 標準化後的指標資料
        """
        if not self.indicators_data:
            raise ValueError("沒有指標資料可供標準化")

        # 將所有指標合併為一個DataFrame
        indicators_df = pd.DataFrame(self.indicators_data)

        # 標準化
        if method == "zscore":
            # Z-score標準化: (x - mean) / std
            standardized = (indicators_df - indicators_df.mean()) / indicators_df.std()
        elif method == "minmax":
            # Min-Max標準化: (x - min) / (max - min)
            standardized = (indicators_df - indicators_df.min()) / (
                indicators_df.max() - indicators_df.min()
            )
        elif method == "robust":
            # 穩健標準化: (x - median) / IQR
            median = indicators_df.median()
            q1 = indicators_df.quantile(0.25)
            q3 = indicators_df.quantile(0.75)
            iqr = q3 - q1
            standardized = (indicators_df - median) / iqr
        else:
            raise ValueError(f"不支援的標準化方法: {method}")

        return standardized

    def compare_indicators(
        self,
        price_series: pd.Series,
        periods: List[int] = None,
        indicators: List[str] = None,
    ) -> pd.DataFrame:
        """比較不同指標的表現

        Args:
            price_series (pd.Series): 價格序列
            periods (List[int], optional): 要比較的週期列表
            indicators (List[str], optional): 要比較的指標列表

        Returns:
            pd.DataFrame: 指標比較結果
        """
        if periods is None:
            periods = [5, 10, 20, 50, 100]

        if indicators is None:
            indicators = ["SMA", "EMA", "RSI", "BBANDS", "ATR"]

        results = {}

        # 計算價格變化
        price_change = price_series.pct_change()

        # 對每個指標和週期進行評估
        for indicator in indicators:
            for period in periods:
                # 計算指標
                if indicator == "SMA":
                    ind_values = self.calculate_sma(period=period)
                elif indicator == "EMA":
                    ind_values = self.calculate_ema(period=period)
                elif indicator == "RSI":
                    ind_values = self.calculate_rsi(period=period)
                elif indicator == "BBANDS":
                    upper, middle, lower = self.calculate_bollinger_bands(period=period)
                    ind_values = (price_series - middle) / (upper - lower)
                elif indicator == "ATR":
                    ind_values = self.calculate_atr(period=period)
                else:
                    continue

                # 計算與價格變化的相關性
                correlation = ind_values.shift(1).corr(price_change)

                # 計算預測準確率
                if indicator in ["SMA", "EMA"]:
                    # 價格高於均線買入，低於均線賣出
                    signals = (price_series > ind_values).astype(int)
                    next_change = price_change.shift(-1)
                    accuracy = (signals * next_change > 0).mean()
                elif indicator == "RSI":
                    # RSI低於30買入，高於70賣出
                    buy_signals = (ind_values < 30).astype(int)
                    sell_signals = (ind_values > 70).astype(int)
                    next_change = price_change.shift(-1)
                    buy_accuracy = (buy_signals * next_change > 0).mean()
                    sell_accuracy = (sell_signals * next_change < 0).mean()
                    accuracy = (buy_accuracy + sell_accuracy) / 2
                else:
                    accuracy = None

                results[f"{indicator}_{period}"] = {
                    "correlation": correlation,
                    "accuracy": accuracy,
                }

        return pd.DataFrame(results).T


class FundamentalIndicators:
    """基本面指標類

    實現各種基本面分析指標，包括盈利能力、估值、成長性等指標。
    每個指標都包含詳細的說明、計算方法和參數。
    """

    def __init__(self, financial_data: Dict[str, pd.DataFrame] = None):
        """初始化基本面指標類

        Args:
            financial_data (Dict[str, pd.DataFrame], optional): 財務資料字典
        """
        self.financial_data = financial_data or {}
        self.indicators_data = {}

    def set_financial_data(self, financial_data: Dict[str, pd.DataFrame]):
        """設置財務資料

        Args:
            financial_data (Dict[str, pd.DataFrame]): 財務資料字典
        """
        self.financial_data = financial_data

    def calculate_eps_growth(self, periods: List[int] = None) -> pd.DataFrame:
        """計算每股盈餘成長率 (EPS Growth)

        EPS成長率是衡量公司盈利能力成長的重要指標。

        計算公式：(本期EPS - 前期EPS) / 前期EPS

        Args:
            periods (List[int], optional): 計算週期列表，如 [1, 4, 12] 表示計算1季、4季和12季的成長率

        Returns:
            pd.DataFrame: EPS成長率

        Raises:
            ValueError: 當找不到必要的財務資料或EPS欄位時
        """
        if "income_statement" not in self.financial_data:
            raise ValueError("找不到損益表資料")

        if periods is None:
            periods = [1, 4, 12]  # 1季、1年、3年

        income_df = self.financial_data["income_statement"]

        if income_df.empty:
            logger.warning("損益表資料為空")
            return pd.DataFrame()

        # 檢查是否有EPS欄位
        eps_col = None
        for col in ["EPS", "eps", "每股盈餘", "earnings_per_share"]:
            if col in income_df.columns:
                eps_col = col
                break

        if eps_col is None:
            raise ValueError("找不到EPS欄位，可用欄位: " + str(list(income_df.columns)))

        # 確保EPS欄位為數值型態
        try:
            eps_series = pd.to_numeric(income_df[eps_col], errors="coerce")
        except Exception as e:
            raise ValueError(f"EPS欄位無法轉換為數值: {e}")

        # 計算不同週期的EPS成長率
        results = {}

        for period in periods:
            try:
                growth = eps_series.pct_change(periods=period)
                # 處理無限值和NaN
                growth = growth.replace([np.inf, -np.inf], np.nan)
                results[f"EPS_growth_{period}"] = growth
                logger.info("成功計算 {period} 季 EPS 成長率")
            except Exception as e:
                logger.warning("計算 {period} 季 EPS 成長率時發生錯誤: {e}")
                results[f"EPS_growth_{period}"] = pd.Series(
                    index=eps_series.index, dtype=float
                )

        growth_df = pd.DataFrame(results)
        self.indicators_data.update(results)

        return growth_df

    def calculate_pe_ratio(self, price_data: pd.DataFrame = None) -> pd.Series:
        """計算本益比 (Price-to-Earnings Ratio, P/E)

        P/E是最常用的估值指標，表示股價相對於每股盈餘的倍數。

        計算公式：股價 / 每股盈餘

        Args:
            price_data (pd.DataFrame, optional): 價格資料

        Returns:
            pd.Series: P/E值
        """
        if "income_statement" not in self.financial_data:
            raise ValueError("找不到損益表資料")

        if price_data is None and "price" in self.financial_data:
            price_data = self.financial_data["price"]

        if price_data is None:
            raise ValueError("找不到價格資料")

        income_df = self.financial_data["income_statement"]

        # 檢查是否有EPS欄位
        eps_col = None
        for col in ["EPS", "eps", "每股盈餘"]:
            if col in income_df.columns:
                eps_col = col
                break

        if eps_col is None:
            raise ValueError("找不到EPS欄位")

        # 檢查價格資料
        price_col = None
        for col in ["close", "Close", "收盤價", "收盤"]:
            if col in price_data.columns:
                price_col = col
                break

        if price_col is None:
            raise ValueError("找不到價格欄位")

        # 將EPS資料對齊到價格資料的日期
        eps = income_df[eps_col].reindex(price_data.index, method="ffill")

        # 計算P/E
        pe_ratio = price_data[price_col] / eps

        self.indicators_data["PE_ratio"] = pe_ratio

        return pe_ratio

    def calculate_pb_ratio(self, price_data: pd.DataFrame = None) -> pd.Series:
        """計算股價淨值比 (Price-to-Book Ratio, P/B)

        P/B是另一個常用的估值指標，表示股價相對於每股淨值的倍數。

        計算公式：股價 / 每股淨值

        Args:
            price_data (pd.DataFrame, optional): 價格資料

        Returns:
            pd.Series: P/B值
        """
        if "balance_sheet" not in self.financial_data:
            raise ValueError("找不到資產負債表資料")

        if price_data is None and "price" in self.financial_data:
            price_data = self.financial_data["price"]

        if price_data is None:
            raise ValueError("找不到價格資料")

        balance_df = self.financial_data["balance_sheet"]

        # 檢查是否有每股淨值欄位
        bps_col = None
        for col in ["BPS", "bps", "每股淨值", "每股權益"]:
            if col in balance_df.columns:
                bps_col = col
                break

        if bps_col is None:
            # 嘗試計算每股淨值
            equity_col = None
            shares_col = None

            for col in ["股東權益", "權益總計", "Total Equity", "equity"]:
                if col in balance_df.columns:
                    equity_col = col
                    break

            for col in ["股本", "普通股股本", "Common Stock", "shares"]:
                if col in balance_df.columns:
                    shares_col = col
                    break

            if equity_col is None or shares_col is None:
                raise ValueError("找不到計算每股淨值所需的欄位")

            # 計算每股淨值
            bps = balance_df[equity_col] / balance_df[shares_col]
        else:
            bps = balance_df[bps_col]

        # 檢查價格資料
        price_col = None
        for col in ["close", "Close", "收盤價", "收盤"]:
            if col in price_data.columns:
                price_col = col
                break

        if price_col is None:
            raise ValueError("找不到價格欄位")

        # 將BPS資料對齊到價格資料的日期
        bps = bps.reindex(price_data.index, method="ffill")

        # 計算P/B
        pb_ratio = price_data[price_col] / bps

        self.indicators_data["PB_ratio"] = pb_ratio

        return pb_ratio

    def calculate_roe(self, periods: List[int] = None) -> pd.DataFrame:
        """計算股東權益報酬率 (Return on Equity, ROE)

        ROE是衡量公司運用股東權益創造利潤能力的指標。

        計算公式：ROE = 淨利潤 / 股東權益

        Args:
            periods (List[int], optional): 計算週期列表

        Returns:
            pd.DataFrame: ROE值

        Raises:
            ValueError: 當找不到必要的財務資料時
        """
        if (
            "income_statement" not in self.financial_data
            or "balance_sheet" not in self.financial_data
        ):
            raise ValueError("找不到損益表或資產負債表資料")

        if periods is None:
            periods = [1, 4, 12]  # 1季、1年、3年

        income_df = self.financial_data["income_statement"]
        balance_df = self.financial_data["balance_sheet"]

        # 檢查淨利潤欄位
        net_income_col = None
        for col in ["net_income", "淨利潤", "淨收益", "Net Income"]:
            if col in income_df.columns:
                net_income_col = col
                break

        if net_income_col is None:
            raise ValueError(
                "找不到淨利潤欄位，可用欄位: " + str(list(income_df.columns))
            )

        # 檢查股東權益欄位
        equity_col = None
        for col in ["shareholders_equity", "股東權益", "權益總計", "Total Equity"]:
            if col in balance_df.columns:
                equity_col = col
                break

        if equity_col is None:
            raise ValueError(
                "找不到股東權益欄位，可用欄位: " + str(list(balance_df.columns))
            )

        # 計算不同週期的ROE
        results = {}

        try:
            net_income = pd.to_numeric(income_df[net_income_col], errors="coerce")
            equity = pd.to_numeric(balance_df[equity_col], errors="coerce")

            for period in periods:
                try:
                    # 計算滾動平均ROE
                    rolling_net_income = net_income.rolling(window=period).sum()
                    rolling_equity = equity.rolling(window=period).mean()

                    roe = rolling_net_income / rolling_equity
                    roe = roe.replace([np.inf, -np.inf], np.nan)
                    results[f"ROE_{period}Q"] = roe
                    logger.info("成功計算 {period} 季 ROE")
                except Exception as e:
                    logger.warning("計算 {period} 季 ROE 時發生錯誤: {e}")
                    results[f"ROE_{period}Q"] = pd.Series(
                        index=net_income.index, dtype=float
                    )

        except Exception as e:
            raise ValueError(f"ROE計算時發生錯誤: {e}")

        roe_df = pd.DataFrame(results)
        self.indicators_data.update(results)

        return roe_df

    def calculate_roa(self, periods: List[int] = None) -> pd.DataFrame:
        """計算資產報酬率 (Return on Assets, ROA)

        ROA是衡量公司運用資產創造利潤能力的指標。

        計算公式：ROA = 淨利潤 / 總資產

        Args:
            periods (List[int], optional): 計算週期列表

        Returns:
            pd.DataFrame: ROA值

        Raises:
            ValueError: 當找不到必要的財務資料時
        """
        if (
            "income_statement" not in self.financial_data
            or "balance_sheet" not in self.financial_data
        ):
            raise ValueError("找不到損益表或資產負債表資料")

        if periods is None:
            periods = [1, 4, 12]  # 1季、1年、3年

        income_df = self.financial_data["income_statement"]
        balance_df = self.financial_data["balance_sheet"]

        # 檢查淨利潤欄位
        net_income_col = None
        for col in ["net_income", "淨利潤", "淨收益", "Net Income"]:
            if col in income_df.columns:
                net_income_col = col
                break

        if net_income_col is None:
            raise ValueError("找不到淨利潤欄位")

        # 檢查總資產欄位
        assets_col = None
        for col in ["total_assets", "總資產", "資產總計", "Total Assets"]:
            if col in balance_df.columns:
                assets_col = col
                break

        if assets_col is None:
            raise ValueError("找不到總資產欄位")

        # 計算不同週期的ROA
        results = {}

        try:
            net_income = pd.to_numeric(income_df[net_income_col], errors="coerce")
            assets = pd.to_numeric(balance_df[assets_col], errors="coerce")

            for period in periods:
                try:
                    # 計算滾動平均ROA
                    rolling_net_income = net_income.rolling(window=period).sum()
                    rolling_assets = assets.rolling(window=period).mean()

                    roa = rolling_net_income / rolling_assets
                    roa = roa.replace([np.inf, -np.inf], np.nan)
                    results[f"ROA_{period}Q"] = roa
                    logger.info("成功計算 {period} 季 ROA")
                except Exception as e:
                    logger.warning("計算 {period} 季 ROA 時發生錯誤: {e}")
                    results[f"ROA_{period}Q"] = pd.Series(
                        index=net_income.index, dtype=float
                    )

        except Exception as e:
            raise ValueError(f"ROA計算時發生錯誤: {e}")

        roa_df = pd.DataFrame(results)
        self.indicators_data.update(results)

        return roa_df

    def calculate_debt_ratio(self) -> pd.Series:
        """計算負債比率 (Debt Ratio)

        負債比率是衡量公司財務槓桿程度的指標。

        計算公式：負債比率 = 總負債 / 總資產

        Returns:
            pd.Series: 負債比率

        Raises:
            ValueError: 當找不到必要的財務資料時
        """
        if "balance_sheet" not in self.financial_data:
            raise ValueError("找不到資產負債表資料")

        balance_df = self.financial_data["balance_sheet"]

        # 檢查總負債欄位
        debt_col = None
        for col in ["total_liabilities", "總負債", "負債總計", "Total Liabilities"]:
            if col in balance_df.columns:
                debt_col = col
                break

        if debt_col is None:
            raise ValueError("找不到總負債欄位")

        # 檢查總資產欄位
        assets_col = None
        for col in ["total_assets", "總資產", "資產總計", "Total Assets"]:
            if col in balance_df.columns:
                assets_col = col
                break

        if assets_col is None:
            raise ValueError("找不到總資產欄位")

        try:
            debt = pd.to_numeric(balance_df[debt_col], errors="coerce")
            assets = pd.to_numeric(balance_df[assets_col], errors="coerce")

            debt_ratio = debt / assets
            debt_ratio = debt_ratio.replace([np.inf, -np.inf], np.nan)

            self.indicators_data["debt_ratio"] = debt_ratio
            logger.info("成功計算負債比率")

            return debt_ratio

        except Exception as e:
            raise ValueError(f"負債比率計算時發生錯誤: {e}")


class SentimentIndicators:
    """情緒指標類

    實現各種情緒分析指標，包括新聞情緒、社交媒體情緒等。
    每個指標都包含詳細的說明、計算方法和參數。
    """

    def __init__(self, sentiment_data: Dict[str, pd.DataFrame] = None):
        """初始化情緒指標類

        Args:
            sentiment_data (Dict[str, pd.DataFrame], optional): 情緒資料字典
        """
        self.sentiment_data = sentiment_data or {}
        self.indicators_data = {}

    def set_sentiment_data(self, sentiment_data: Dict[str, pd.DataFrame]):
        """設置情緒資料

        Args:
            sentiment_data (Dict[str, pd.DataFrame]): 情緒資料字典
        """
        self.sentiment_data = sentiment_data

    def calculate_news_sentiment(self, window: int = 7) -> pd.Series:
        """計算新聞情緒指標

        根據新聞情緒分數計算移動平均情緒指標。

        Args:
            window (int): 移動平均窗口大小

        Returns:
            pd.Series: 新聞情緒指標

        Raises:
            ValueError: 當找不到必要的情緒資料時
        """
        if "news" not in self.sentiment_data:
            raise ValueError("找不到新聞情緒資料")

        news_df = self.sentiment_data["news"]

        if news_df.empty:
            logger.warning("新聞情緒資料為空")
            return pd.Series(dtype=float)

        # 檢查是否有情緒分數欄位
        sentiment_col = None
        for col in ["sentiment", "sentiment_score", "情緒分數", "score"]:
            if col in news_df.columns:
                sentiment_col = col
                break

        if sentiment_col is None:
            # 嘗試從文本內容計算情緒分數
            if "content" in news_df.columns or "title" in news_df.columns:
                logger.info("未找到情緒分數欄位，嘗試從文本計算情緒")
                sentiment_scores = self._calculate_text_sentiment(news_df)
                news_df = news_df.copy()
                news_df["calculated_sentiment"] = sentiment_scores
                sentiment_col = "calculated_sentiment"
            else:
                raise ValueError("找不到情緒分數欄位或文本內容欄位")

        try:
            # 確保情緒分數為數值型態
            sentiment_series = pd.to_numeric(news_df[sentiment_col], errors="coerce")

            # 計算移動平均情緒指標
            sentiment_ma = sentiment_series.rolling(window=window, min_periods=1).mean()

            # 處理異常值
            sentiment_ma = sentiment_ma.clip(-1, 1)  # 限制在 -1 到 1 之間

            self.indicators_data["news_sentiment"] = sentiment_ma
            logger.info("成功計算新聞情緒指標，窗口大小: {window}")

            return sentiment_ma

        except Exception as e:
            raise ValueError(f"計算新聞情緒指標時發生錯誤: {e}")

    def _calculate_text_sentiment(self, news_df: pd.DataFrame) -> pd.Series:
        """從文本內容計算情緒分數

        Args:
            news_df (pd.DataFrame): 新聞資料

        Returns:
            pd.Series: 情緒分數
        """
        # 簡單的關鍵字情緒分析
        positive_keywords = [
            "上漲",
            "增長",
            "成長",
            "獲利",
            "盈利",
            "突破",
            "創新高",
            "樂觀",
            "正面",
            "好消息",
            "利多",
            "買進",
            "推薦",
            "強勢",
            "回升",
            "反彈",
            "看好",
            "投資",
            "機會",
        ]

        negative_keywords = [
            "下跌",
            "下滑",
            "虧損",
            "衰退",
            "跌破",
            "創新低",
            "悲觀",
            "負面",
            "壞消息",
            "利空",
            "賣出",
            "不推薦",
            "弱勢",
            "下探",
            "重挫",
            "看壞",
            "風險",
            "危機",
        ]

        sentiment_scores = []

        for _, row in news_df.iterrows():
            # 合併標題和內容
            text = ""
            if "title" in row and pd.notna(row["title"]):
                text += str(row["title"]) + " "
            if "content" in row and pd.notna(row["content"]):
                text += str(row["content"])

            text = text.lower()

            # 計算正面和負面關鍵字數量
            positive_count = sum(1 for keyword in positive_keywords if keyword in text)
            negative_count = sum(1 for keyword in negative_keywords if keyword in text)

            # 計算情緒分數
            total_count = positive_count + negative_count
            if total_count == 0:
                score = 0.0
            else:
                score = (positive_count - negative_count) / total_count

            sentiment_scores.append(score)

        return pd.Series(sentiment_scores, index=news_df.index)

    def calculate_social_sentiment(self, window: int = 3) -> pd.Series:
        """計算社交媒體情緒指標

        根據社交媒體情緒分數計算移動平均情緒指標。

        Args:
            window (int): 移動平均窗口大小

        Returns:
            pd.Series: 社交媒體情緒指標
        """
        if "social" not in self.sentiment_data:
            raise ValueError("找不到社交媒體情緒資料")

        social_df = self.sentiment_data["social"]

        # 檢查是否有情緒分數欄位
        sentiment_col = None
        for col in ["sentiment", "sentiment_score", "情緒分數"]:
            if col in social_df.columns:
                sentiment_col = col
                break

        if sentiment_col is None:
            raise ValueError("找不到情緒分數欄位")

        # 計算移動平均情緒指標
        sentiment_ma = social_df[sentiment_col].rolling(window=window).mean()

        self.indicators_data["social_sentiment"] = sentiment_ma

        return sentiment_ma

    def calculate_topic_sentiment(
        self, topics: List[str] = None, window: int = 7
    ) -> pd.DataFrame:
        """計算主題情緒指標

        根據特定主題的新聞情緒分數計算移動平均情緒指標。

        Args:
            topics (List[str], optional): 主題列表
            window (int): 移動平均窗口大小

        Returns:
            pd.DataFrame: 主題情緒指標

        Raises:
            ValueError: 當找不到必要的資料時
        """
        if "news" not in self.sentiment_data:
            raise ValueError("找不到新聞情緒資料")

        news_df = self.sentiment_data["news"]

        if news_df.empty:
            logger.warning("新聞情緒資料為空")
            return pd.DataFrame()

        # 檢查是否有主題欄位和情緒分數欄位
        topic_col = None
        sentiment_col = None

        for col in ["topic", "category", "主題", "類別", "subject"]:
            if col in news_df.columns:
                topic_col = col
                break

        for col in ["sentiment", "sentiment_score", "情緒分數", "score"]:
            if col in news_df.columns:
                sentiment_col = col
                break

        # 如果沒有主題欄位，嘗試從文本中提取主題
        if topic_col is None:
            if "content" in news_df.columns or "title" in news_df.columns:
                logger.info("未找到主題欄位，嘗試從文本提取主題")
                news_df = news_df.copy()
                news_df["extracted_topic"] = self._extract_topics_from_text(news_df)
                topic_col = "extracted_topic"
            else:
                raise ValueError("找不到主題欄位或文本內容")

        # 如果沒有情緒分數，嘗試計算
        if sentiment_col is None:
            if "content" in news_df.columns or "title" in news_df.columns:
                logger.info("未找到情緒分數欄位，嘗試從文本計算情緒")
                news_df = news_df.copy()
                news_df["calculated_sentiment"] = self._calculate_text_sentiment(
                    news_df
                )
                sentiment_col = "calculated_sentiment"
            else:
                raise ValueError("找不到情緒分數欄位或文本內容")

        # 如果沒有指定主題，則使用所有主題
        if topics is None:
            topics = news_df[topic_col].unique().tolist()
            # 過濾掉空值和無效主題
            topics = [t for t in topics if pd.notna(t) and str(t).strip() != ""]

        # 計算每個主題的移動平均情緒指標
        results = {}

        try:
            for topic in topics:
                topic_news = news_df[news_df[topic_col] == topic]
                if not topic_news.empty:
                    sentiment_series = pd.to_numeric(
                        topic_news[sentiment_col], errors="coerce"
                    )
                    sentiment_ma = sentiment_series.rolling(
                        window=window, min_periods=1
                    ).mean()
                    # 處理異常值
                    sentiment_ma = sentiment_ma.clip(-1, 1)
                    results[f"topic_{topic}_sentiment"] = sentiment_ma
                    logger.info("成功計算主題 '{topic}' 的情緒指標")

            topic_sentiment_df = pd.DataFrame(results)
            self.indicators_data.update(results)

            return topic_sentiment_df

        except Exception as e:
            raise ValueError(f"計算主題情緒指標時發生錯誤: {e}")

    def _extract_topics_from_text(self, news_df: pd.DataFrame) -> pd.Series:
        """從文本中提取主題

        Args:
            news_df (pd.DataFrame): 新聞資料

        Returns:
            pd.Series: 提取的主題
        """
        # 預定義的主題關鍵字
        topic_keywords = {
            "財報": ["財報", "季報", "年報", "營收", "獲利", "EPS", "財務"],
            "併購": ["併購", "收購", "合併", "投資", "入股"],
            "產品": ["產品", "新品", "發布", "上市", "推出"],
            "技術": ["技術", "研發", "專利", "創新", "AI", "5G"],
            "市場": ["市場", "競爭", "份額", "需求", "供應"],
            "政策": ["政策", "法規", "監管", "政府", "法律"],
            "人事": ["人事", "CEO", "董事", "管理層", "離職", "任命"],
        }

        topics = []

        for _, row in news_df.iterrows():
            # 合併標題和內容
            text = ""
            if "title" in row and pd.notna(row["title"]):
                text += str(row["title"]) + " "
            if "content" in row and pd.notna(row["content"]):
                text += str(row["content"])

            text = text.lower()

            # 找到最匹配的主題
            best_topic = "其他"
            max_matches = 0

            for topic, keywords in topic_keywords.items():
                matches = sum(1 for keyword in keywords if keyword in text)
                if matches > max_matches:
                    max_matches = matches
                    best_topic = topic

            topics.append(best_topic)

        return pd.Series(topics, index=news_df.index)


def evaluate_indicator_efficacy(
    price_data: pd.DataFrame,
    indicator_data: pd.DataFrame,
    forward_periods: List[int] = None,
) -> pd.DataFrame:
    """評估指標有效性

    計算指標與未來價格變化的相關性，以評估指標的預測能力。

    Args:
        price_data (pd.DataFrame): 價格資料
        indicator_data (pd.DataFrame): 指標資料
        forward_periods (List[int], optional): 未來期間列表

    Returns:
        pd.DataFrame: 指標有效性評估結果
    """
    if forward_periods is None:
        forward_periods = [1, 5, 10, 20]

    # 確保價格資料有 'close' 列
    price_col = None
    for col in ["close", "Close", "收盤價", "收盤"]:
        if col in price_data.columns:
            price_col = col
            break

    if price_col is None:
        raise ValueError("找不到價格欄位")

    # 計算未來價格變化
    future_returns = {}
    for period in forward_periods:
        future_returns[f"future_return_{period}"] = (
            price_data[price_col].pct_change(periods=period).shift(-period)
        )

    future_returns_df = pd.DataFrame(future_returns)

    # 計算指標與未來價格變化的相關性
    correlation_matrix = pd.DataFrame(
        index=indicator_data.columns, columns=future_returns_df.columns
    )

    for ind_col in indicator_data.columns:
        for ret_col in future_returns_df.columns:
            correlation_matrix.loc[ind_col, ret_col] = indicator_data[ind_col].corr(
                future_returns_df[ret_col]
            )

    return correlation_matrix


def generate_trading_signals(
    price_data: pd.DataFrame,
    indicator_data: pd.DataFrame,
    signal_rules: Dict[str, Dict[str, Union[str, float]]],
) -> pd.DataFrame:
    """生成交易訊號

    根據指標和規則生成交易訊號。

    Args:
        price_data (pd.DataFrame): 價格資料
        indicator_data (pd.DataFrame): 指標資料
        signal_rules (Dict[str, Dict[str, Union[str, float]]]): 訊號規則

    Returns:
        pd.DataFrame: 交易訊號
    """
    signals = pd.DataFrame(index=price_data.index)
    signals["signal"] = 0

    for indicator, rule in signal_rules.items():
        if indicator not in indicator_data.columns:
            continue

        indicator_values = indicator_data[indicator]

        if rule["type"] == "threshold":
            # 閾值規則
            if "buy_threshold" in rule:
                signals.loc[indicator_values < rule["buy_threshold"], "signal"] = 1
            if "sell_threshold" in rule:
                signals.loc[indicator_values > rule["sell_threshold"], "signal"] = -1

        elif rule["type"] == "crossover":
            # 交叉規則
            if "reference" in rule:
                if rule["reference"] == "SMA":
                    reference_values = indicator_values.rolling(
                        window=rule["period"]
                    ).mean()
                elif rule["reference"] == "EMA":
                    reference_values = indicator_values.ewm(
                        span=rule["period"], adjust=False
                    ).mean()
                else:
                    continue

                # 上穿買入，下穿賣出
                signals.loc[
                    (indicator_values > reference_values)
                    & (indicator_values.shift(1) <= reference_values.shift(1)),
                    "signal",
                ] = 1
                signals.loc[
                    (indicator_values < reference_values)
                    & (indicator_values.shift(1) >= reference_values.shift(1)),
                    "signal",
                ] = -1

        elif rule["type"] == "momentum":
            # 動量規則
            momentum = indicator_values.diff(periods=rule["period"])
            signals.loc[momentum > 0, "signal"] = 1
            signals.loc[momentum < 0, "signal"] = -1

    return signals
