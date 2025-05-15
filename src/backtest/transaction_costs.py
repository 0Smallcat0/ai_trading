# -*- coding: utf-8 -*-
"""
交易成本模組

此模組提供各種交易成本模型，包括：
- 固定手續費
- 比例手續費
- 滑價模型
- 稅費模型
"""

import logging
from typing import Optional

import backtrader as bt

from src.config import LOG_LEVEL

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class FixedCommissionScheme(bt.CommInfoBase):
    """
    固定手續費模型

    每筆交易收取固定金額的手續費。
    """

    params = (
        ("commission", 20.0),  # 固定手續費金額
        ("stocklike", True),  # 是否為股票類資產
        ("commtype", bt.CommInfoBase.COMM_FIXED),  # 手續費類型
    )

    def _getcommission(self, size, price, pseudoexec):
        """
        計算手續費

        Args:
            size (float): 交易數量
            price (float): 交易價格
            pseudoexec (bool): 是否為虛擬執行

        Returns:
            float: 手續費金額
        """
        return self.p.commission


class PercentCommissionScheme(bt.CommInfoBase):
    """
    比例手續費模型

    每筆交易收取交易金額一定比例的手續費。
    """

    params = (
        ("commission", 0.001),  # 手續費比例
        ("stocklike", True),  # 是否為股票類資產
        ("commtype", bt.CommInfoBase.COMM_PERC),  # 手續費類型
        ("min_commission", 0.0),  # 最低手續費
    )

    def _getcommission(self, size, price, pseudoexec):
        """
        計算手續費

        Args:
            size (float): 交易數量
            price (float): 交易價格
            pseudoexec (bool): 是否為虛擬執行

        Returns:
            float: 手續費金額
        """
        commission = abs(size) * price * self.p.commission

        # 檢查是否低於最低手續費
        if commission < self.p.min_commission:
            commission = self.p.min_commission

        return commission


class TieredCommissionScheme(bt.CommInfoBase):
    """
    階梯式手續費模型

    根據交易金額或數量使用不同的手續費率。
    """

    params = (
        ("tiers", {}),  # 階梯式手續費，格式為 {閾值: 手續費率}
        ("stocklike", True),  # 是否為股票類資產
        ("commtype", bt.CommInfoBase.COMM_PERC),  # 手續費類型
        ("tier_type", "amount"),  # 階梯類型，可選 'amount' 或 'size'
        ("min_commission", 0.0),  # 最低手續費
    )

    def _getcommission(self, size, price, pseudoexec):
        """
        計算手續費

        Args:
            size (float): 交易數量
            price (float): 交易價格
            pseudoexec (bool): 是否為虛擬執行

        Returns:
            float: 手續費金額
        """
        # 計算交易金額或數量
        if self.p.tier_type == "amount":
            value = abs(size) * price
        else:
            value = abs(size)

        # 找到適用的手續費率
        commission_rate = self.p.tiers.get(0, 0.0)  # 預設手續費率

        for threshold, rate in sorted(self.p.tiers.items()):
            if value >= threshold:
                commission_rate = rate
            else:
                break

        # 計算手續費
        commission = value * commission_rate

        # 檢查是否低於最低手續費
        if commission < self.p.min_commission:
            commission = self.p.min_commission

        return commission


class TaxScheme(bt.CommInfoBase):
    """
    稅費模型

    計算交易稅費。
    """

    params = (
        ("tax_rate", 0.003),  # 稅率
        ("stocklike", True),  # 是否為股票類資產
        ("commtype", bt.CommInfoBase.COMM_PERC),  # 手續費類型
        ("tax_on_sell_only", True),  # 是否只對賣出收稅
    )

    def _getcommission(self, size, price, pseudoexec):
        """
        計算稅費

        Args:
            size (float): 交易數量
            price (float): 交易價格
            pseudoexec (bool): 是否為虛擬執行

        Returns:
            float: 稅費金額
        """
        # 如果只對賣出收稅，則檢查交易方向
        if self.p.tax_on_sell_only and size > 0:
            return 0.0

        # 計算稅費
        tax = abs(size) * price * self.p.tax_rate

        return tax


class CombinedCostScheme(bt.CommInfoBase):
    """
    組合成本模型

    結合手續費、稅費和滑價的成本模型。
    """

    params = (
        ("commission_rate", 0.001),  # 手續費比例
        ("min_commission", 0.0),  # 最低手續費
        ("tax_rate", 0.003),  # 稅率
        ("tax_on_sell_only", True),  # 是否只對賣出收稅
        ("slippage_perc", 0.001),  # 滑價比例
        ("stocklike", True),  # 是否為股票類資產
        ("commtype", bt.CommInfoBase.COMM_PERC),  # 手續費類型
    )

    def _getcommission(self, size, price, pseudoexec):
        """
        計算總成本

        Args:
            size (float): 交易數量
            price (float): 交易價格
            pseudoexec (bool): 是否為虛擬執行

        Returns:
            float: 總成本金額
        """
        # 計算手續費
        commission = abs(size) * price * self.p.commission_rate

        # 檢查是否低於最低手續費
        if commission < self.p.min_commission:
            commission = self.p.min_commission

        # 計算稅費
        if self.p.tax_on_sell_only and size > 0:
            tax = 0.0
        else:
            tax = abs(size) * price * self.p.tax_rate

        # 總成本
        total_cost = commission + tax

        return total_cost

    def get_slippage(self, size, price):
        """
        計算滑價

        Args:
            size (float): 交易數量
            price (float): 交易價格

        Returns:
            float: 滑價後的價格
        """
        # 計算滑價
        slippage = price * self.p.slippage_perc

        # 根據交易方向調整價格
        if size > 0:
            # 買入，價格上調
            adjusted_price = price + slippage
        else:
            # 賣出，價格下調
            adjusted_price = price - slippage

        return adjusted_price


class TWStockCostScheme(bt.CommInfoBase):
    """
    台股成本模型

    模擬台灣股市的交易成本，包括手續費和證券交易稅。
    """

    params = (
        ("commission_rate", 0.001425),  # 手續費比例，預設 0.1425%
        ("min_commission", 20.0),  # 最低手續費，預設 20 元
        ("tax_rate", 0.003),  # 證券交易稅，預設 0.3%
        ("slippage_perc", 0.001),  # 滑價比例，預設 0.1%
        ("stocklike", True),  # 是否為股票類資產
        ("commtype", bt.CommInfoBase.COMM_PERC),  # 手續費類型
    )

    def _getcommission(self, size, price, pseudoexec):
        """
        計算總成本

        Args:
            size (float): 交易數量
            price (float): 交易價格
            pseudoexec (bool): 是否為虛擬執行

        Returns:
            float: 總成本金額
        """
        # 計算手續費
        commission = abs(size) * price * self.p.commission_rate

        # 檢查是否低於最低手續費
        if commission < self.p.min_commission:
            commission = self.p.min_commission

        # 計算證券交易稅（只對賣出收取）
        tax = 0.0
        if size < 0:  # 賣出
            tax = abs(size) * price * self.p.tax_rate

        # 總成本
        total_cost = commission + tax

        return total_cost

    def get_slippage(self, size, price):
        """
        計算滑價

        Args:
            size (float): 交易數量
            price (float): 交易價格

        Returns:
            float: 滑價後的價格
        """
        # 計算滑價
        slippage = price * self.p.slippage_perc

        # 根據交易方向調整價格
        if size > 0:
            # 買入，價格上調
            adjusted_price = price + slippage
        else:
            # 賣出，價格下調
            adjusted_price = price - slippage

        return adjusted_price


class USStockCostScheme(bt.CommInfoBase):
    """
    美股成本模型

    模擬美國股市的交易成本，包括手續費和 SEC 費用。
    """

    params = (
        ("commission_rate", 0.0),  # 手續費比例，預設 0%（免傭金）
        ("min_commission", 0.0),  # 最低手續費，預設 0 美元
        ("sec_fee_rate", 0.0000229),  # SEC 費用，預設 0.00229%
        ("finra_fee", 0.000119),  # FINRA 費用，預設 0.0119%
        ("slippage_perc", 0.0005),  # 滑價比例，預設 0.05%
        ("stocklike", True),  # 是否為股票類資產
        ("commtype", bt.CommInfoBase.COMM_PERC),  # 手續費類型
    )

    def _getcommission(self, size, price, pseudoexec):
        """
        計算總成本

        Args:
            size (float): 交易數量
            price (float): 交易價格
            pseudoexec (bool): 是否為虛擬執行

        Returns:
            float: 總成本金額
        """
        # 計算手續費
        commission = abs(size) * price * self.p.commission_rate

        # 檢查是否低於最低手續費
        if commission < self.p.min_commission:
            commission = self.p.min_commission

        # 計算 SEC 費用（只對賣出收取）
        sec_fee = 0.0
        if size < 0:  # 賣出
            sec_fee = abs(size) * price * self.p.sec_fee_rate

        # 計算 FINRA 費用（只對賣出收取）
        finra_fee = 0.0
        if size < 0:  # 賣出
            finra_fee = abs(size) * price * self.p.finra_fee

        # 總成本
        total_cost = commission + sec_fee + finra_fee

        return total_cost

    def get_slippage(self, size, price):
        """
        計算滑價

        Args:
            size (float): 交易數量
            price (float): 交易價格

        Returns:
            float: 滑價後的價格
        """
        # 計算滑價
        slippage = price * self.p.slippage_perc

        # 根據交易方向調整價格
        if size > 0:
            # 買入，價格上調
            adjusted_price = price + slippage
        else:
            # 賣出，價格下調
            adjusted_price = price - slippage

        return adjusted_price


def get_cost_scheme(
    market: str = "TW",
    commission_rate: Optional[float] = None,
    min_commission: Optional[float] = None,
    tax_rate: Optional[float] = None,
    slippage_perc: Optional[float] = None,
) -> bt.CommInfoBase:
    """
    獲取成本模型

    Args:
        market (str): 市場，可選 'TW'（台灣）或 'US'（美國）
        commission_rate (Optional[float]): 手續費比例
        min_commission (Optional[float]): 最低手續費
        tax_rate (Optional[float]): 稅率
        slippage_perc (Optional[float]): 滑價比例

    Returns:
        bt.CommInfoBase: 成本模型
    """
    if market == "TW":
        # 台股成本模型
        params = {}
        if commission_rate is not None:
            params["commission_rate"] = commission_rate
        if min_commission is not None:
            params["min_commission"] = min_commission
        if tax_rate is not None:
            params["tax_rate"] = tax_rate
        if slippage_perc is not None:
            params["slippage_perc"] = slippage_perc

        return TWStockCostScheme(**params)
    elif market == "US":
        # 美股成本模型
        params = {}
        if commission_rate is not None:
            params["commission_rate"] = commission_rate
        if min_commission is not None:
            params["min_commission"] = min_commission
        if slippage_perc is not None:
            params["slippage_perc"] = slippage_perc

        return USStockCostScheme(**params)
    else:
        # 預設使用組合成本模型
        params = {}
        if commission_rate is not None:
            params["commission_rate"] = commission_rate
        if min_commission is not None:
            params["min_commission"] = min_commission
        if tax_rate is not None:
            params["tax_rate"] = tax_rate
        if slippage_perc is not None:
            params["slippage_perc"] = slippage_perc

        return CombinedCostScheme(**params)
