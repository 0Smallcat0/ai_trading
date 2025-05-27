"""基本面策略訊號產生器

此模組實現基於基本面分析的交易訊號生成功能。
"""

import logging


import pandas as pd

from .base_signal_generator import BaseSignalGenerator, LOG_MSGS

logger = logging.getLogger(__name__)


class FundamentalSignalGenerator(BaseSignalGenerator):
    """基本面策略訊號產生器

    基於本益比、股價淨值比和殖利率等基本面指標生成訊號。
    """

    def generate_signals(
        self,
        pe_threshold: float = 15,
        pb_threshold: float = 1.5,
        dividend_yield_threshold: float = 3.0,
        **kwargs
    ) -> pd.DataFrame:
        """生成基本面策略訊號

        基於本益比、股價淨值比和殖利率等基本面指標生成訊號

        Args:
            pe_threshold (float): 本益比閾值，低於此值視為買入訊號
            pb_threshold (float): 股價淨值比閾值，低於此值視為買入訊號
            dividend_yield_threshold (float): 殖利率閾值，高於此值視為買入訊號
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        if not self.validate_data("financial"):
            logger.warning(LOG_MSGS["no_financial"])
            return pd.DataFrame()

        # 複製財務資料
        financial_data = self.financial_data.copy()

        # 初始化訊號
        signals = pd.DataFrame(index=financial_data.index)
        signals["signal"] = 0

        # 根據本益比生成訊號
        if "pe_ratio" in financial_data.columns:
            signals.loc[financial_data["pe_ratio"] < pe_threshold, "signal"] += 1
            signals.loc[financial_data["pe_ratio"] > pe_threshold * 2, "signal"] -= 1

        # 根據股價淨值比生成訊號
        if "pb_ratio" in financial_data.columns:
            signals.loc[financial_data["pb_ratio"] < pb_threshold, "signal"] += 1
            signals.loc[financial_data["pb_ratio"] > pb_threshold * 2, "signal"] -= 1

        # 根據殖利率生成訊號
        if "dividend_yield" in financial_data.columns:
            signals.loc[
                financial_data["dividend_yield"] > dividend_yield_threshold, "signal"
            ] += 1
            signals.loc[
                financial_data["dividend_yield"] < dividend_yield_threshold / 2,
                "signal",
            ] -= 1

        # 標準化訊號
        signals["signal"] = signals["signal"].apply(
            lambda x: 1 if x > 0 else (-1 if x < 0 else 0)
        )

        # 儲存訊號
        self.signals["fundamental"] = signals

        return signals

    def generate_value_signals(
        self,
        pe_low: float = 10,
        pe_high: float = 25,
        pb_low: float = 0.8,
        pb_high: float = 2.0,
        roe_threshold: float = 0.15,
    ) -> pd.DataFrame:
        """生成價值投資訊號

        基於價值投資原則生成訊號

        Args:
            pe_low (float): P/E 比率低閾值
            pe_high (float): P/E 比率高閾值
            pb_low (float): P/B 比率低閾值
            pb_high (float): P/B 比率高閾值
            roe_threshold (float): ROE 閾值

        Returns:
            pd.DataFrame: 價值投資訊號
        """
        if not self.validate_data("financial"):
            logger.warning(LOG_MSGS["no_financial"])
            return pd.DataFrame()

        financial_data = self.financial_data.copy()
        signals = pd.DataFrame(index=financial_data.index)
        signals["signal"] = 0

        # 價值投資條件
        value_conditions = []

        # P/E 比率條件
        if "pe_ratio" in financial_data.columns:
            pe_condition = (financial_data["pe_ratio"] >= pe_low) & (
                financial_data["pe_ratio"] <= pe_high
            )
            value_conditions.append(pe_condition)

        # P/B 比率條件
        if "pb_ratio" in financial_data.columns:
            pb_condition = (financial_data["pb_ratio"] >= pb_low) & (
                financial_data["pb_ratio"] <= pb_high
            )
            value_conditions.append(pb_condition)

        # ROE 條件
        if "roe" in financial_data.columns:
            roe_condition = financial_data["roe"] >= roe_threshold
            value_conditions.append(roe_condition)

        # 合併條件
        if value_conditions:
            combined_condition = value_conditions[0]
            for condition in value_conditions[1:]:
                combined_condition = combined_condition & condition

            signals.loc[combined_condition, "signal"] = 1

        # 儲存訊號
        self.signals["value"] = signals

        return signals

    def generate_growth_signals(
        self,
        eps_growth_threshold: float = 0.15,
        revenue_growth_threshold: float = 0.10,
        pe_max: float = 30,
    ) -> pd.DataFrame:
        """生成成長投資訊號

        基於成長投資原則生成訊號

        Args:
            eps_growth_threshold (float): EPS 成長率閾值
            revenue_growth_threshold (float): 營收成長率閾值
            pe_max (float): P/E 比率上限

        Returns:
            pd.DataFrame: 成長投資訊號
        """
        if not self.validate_data("financial"):
            logger.warning(LOG_MSGS["no_financial"])
            return pd.DataFrame()

        financial_data = self.financial_data.copy()
        signals = pd.DataFrame(index=financial_data.index)
        signals["signal"] = 0

        # 成長投資條件
        growth_conditions = []

        # EPS 成長率條件
        if "eps_growth" in financial_data.columns:
            eps_condition = financial_data["eps_growth"] >= eps_growth_threshold
            growth_conditions.append(eps_condition)

        # 營收成長率條件
        if "revenue_growth" in financial_data.columns:
            revenue_condition = (
                financial_data["revenue_growth"] >= revenue_growth_threshold
            )
            growth_conditions.append(revenue_condition)

        # P/E 比率不能太高
        if "pe_ratio" in financial_data.columns:
            pe_condition = financial_data["pe_ratio"] <= pe_max
            growth_conditions.append(pe_condition)

        # 合併條件
        if growth_conditions:
            combined_condition = growth_conditions[0]
            for condition in growth_conditions[1:]:
                combined_condition = combined_condition & condition

            signals.loc[combined_condition, "signal"] = 1

        # 儲存訊號
        self.signals["growth"] = signals

        return signals

    def generate_dividend_signals(
        self,
        dividend_yield_min: float = 0.03,
        payout_ratio_max: float = 0.7,
        debt_ratio_max: float = 0.5,
    ) -> pd.DataFrame:
        """生成股息投資訊號

        基於股息投資原則生成訊號

        Args:
            dividend_yield_min (float): 最低股息殖利率
            payout_ratio_max (float): 最高配息率
            debt_ratio_max (float): 最高負債比率

        Returns:
            pd.DataFrame: 股息投資訊號
        """
        if not self.validate_data("financial"):
            logger.warning(LOG_MSGS["no_financial"])
            return pd.DataFrame()

        financial_data = self.financial_data.copy()
        signals = pd.DataFrame(index=financial_data.index)
        signals["signal"] = 0

        # 股息投資條件
        dividend_conditions = []

        # 股息殖利率條件
        if "dividend_yield" in financial_data.columns:
            yield_condition = financial_data["dividend_yield"] >= dividend_yield_min
            dividend_conditions.append(yield_condition)

        # 配息率條件
        if "payout_ratio" in financial_data.columns:
            payout_condition = financial_data["payout_ratio"] <= payout_ratio_max
            dividend_conditions.append(payout_condition)

        # 負債比率條件
        if "debt_ratio" in financial_data.columns:
            debt_condition = financial_data["debt_ratio"] <= debt_ratio_max
            dividend_conditions.append(debt_condition)

        # 合併條件
        if dividend_conditions:
            combined_condition = dividend_conditions[0]
            for condition in dividend_conditions[1:]:
                combined_condition = combined_condition & condition

            signals.loc[combined_condition, "signal"] = 1

        # 儲存訊號
        self.signals["dividend"] = signals

        return signals

    def generate_all_fundamental_signals(self, **kwargs) -> dict:
        """生成所有基本面訊號

        Args:
            **kwargs: 各種策略的參數

        Returns:
            dict: 包含所有基本面訊號的字典
        """
        signals_dict = {}

        # 生成基本面訊號
        signals_dict["fundamental"] = self.generate_signals(**kwargs)

        # 生成價值投資訊號
        signals_dict["value"] = self.generate_value_signals(**kwargs)

        # 生成成長投資訊號
        signals_dict["growth"] = self.generate_growth_signals(**kwargs)

        # 生成股息投資訊號
        signals_dict["dividend"] = self.generate_dividend_signals(**kwargs)

        return signals_dict
