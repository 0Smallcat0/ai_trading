"""Interactive Brokers 合約管理模組

此模組提供 IB API 合約的創建和管理功能，支援股票、期權、期貨等多種金融工具。
包括合約創建、驗證、格式化等功能。

版本: v1.0
作者: AI Trading System
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum

try:
    from ibapi.contract import Contract
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    # 定義模擬類型以避免 NameError
    class Contract:
        """模擬 Contract 類"""
        def __init__(self):
            self.symbol = ""
            self.secType = ""
            self.exchange = ""
            self.currency = ""
            self.lastTradeDateOrContractMonth = ""
            self.strike = 0.0
            self.right = ""
            self.multiplier = ""

# 設定日誌
logger = logging.getLogger("execution.ib.contracts")


class SecurityType(Enum):
    """證券類型枚舉"""
    STOCK = "STK"
    OPTION = "OPT"
    FUTURE = "FUT"
    FOREX = "CASH"
    INDEX = "IND"
    BOND = "BOND"
    COMMODITY = "CMDTY"


class OptionRight(Enum):
    """期權權利類型枚舉"""
    CALL = "C"
    PUT = "P"


class Exchange(Enum):
    """交易所枚舉"""
    # 美股
    SMART = "SMART"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    
    # 台股
    TSE = "TSE"
    TWSE = "TWSE"
    
    # 港股
    SEHK = "SEHK"
    
    # 期權
    CBOE = "CBOE"
    ISE = "ISE"


class Currency(Enum):
    """貨幣枚舉"""
    USD = "USD"
    TWD = "TWD"
    HKD = "HKD"
    EUR = "EUR"
    JPY = "JPY"


class IBContractManager:
    """IB 合約管理器
    
    提供創建和管理各種 IB 合約的功能，包括股票、期權、期貨等。
    支援多個市場和交易所。
    """

    def __init__(self):
        """初始化合約管理器"""
        self._contract_cache: Dict[str, Contract] = {}

    def create_stock_contract(
        self,
        symbol: str,
        exchange: Optional[str] = None,
        currency: Optional[str] = None
    ) -> Optional[Contract]:
        """創建股票合約
        
        Args:
            symbol: 股票代號
            exchange: 交易所（可選，自動判斷）
            currency: 貨幣（可選，自動判斷）
            
        Returns:
            Contract: IB 股票合約或 None
            
        Example:
            >>> manager = IBContractManager()
            >>> contract = manager.create_stock_contract("AAPL")
            >>> contract.symbol
            'AAPL'
        """
        try:
            # 檢查快取
            cache_key = f"STK_{symbol}_{exchange}_{currency}"
            if cache_key in self._contract_cache:
                return self._contract_cache[cache_key]

            contract = Contract()
            contract.secType = SecurityType.STOCK.value

            # 解析股票代號，判斷市場
            if symbol.endswith('.TW'):
                # 台股
                contract.symbol = symbol.replace('.TW', '')
                contract.exchange = exchange or Exchange.TSE.value
                contract.currency = currency or Currency.TWD.value
            elif symbol.endswith('.HK'):
                # 港股
                contract.symbol = symbol.replace('.HK', '')
                contract.exchange = exchange or Exchange.SEHK.value
                contract.currency = currency or Currency.HKD.value
            elif '.' not in symbol:
                # 美股 (預設)
                contract.symbol = symbol
                contract.exchange = exchange or Exchange.SMART.value
                contract.currency = currency or Currency.USD.value
            else:
                logger.error("不支援的股票代號格式: %s", symbol)
                return None

            # 快取合約
            self._contract_cache[cache_key] = contract
            
            logger.debug(
                "創建股票合約 - 代號: %s, 交易所: %s, 貨幣: %s",
                contract.symbol, contract.exchange, contract.currency
            )
            
            return contract

        except Exception as e:
            logger.exception("創建股票合約失敗: %s", e)
            return None

    def create_option_contract(
        self,
        symbol: str,
        expiry: str,
        strike: float,
        right: str,
        exchange: Optional[str] = None,
        currency: Optional[str] = None,
        multiplier: Optional[str] = None
    ) -> Optional[Contract]:
        """創建期權合約

        Args:
            symbol: 標的股票代號
            expiry: 到期日 (格式: YYYYMMDD)
            strike: 行權價
            right: 期權類型 ('C' for Call, 'P' for Put)
            exchange: 交易所（可選）
            currency: 貨幣（可選）
            multiplier: 合約乘數（可選）

        Returns:
            Contract: IB 期權合約或 None

        Example:
            >>> manager = IBContractManager()
            >>> contract = manager.create_option_contract(
            ...     "AAPL", "20241220", 150.0, "C"
            ... )
            >>> contract.secType
            'OPT'
        """
        try:
            # 驗證參數
            if not self._validate_option_params(symbol, expiry, strike, right):
                return None

            # 檢查快取
            cache_key = f"OPT_{symbol}_{expiry}_{strike}_{right}_{exchange}_{currency}"
            if cache_key in self._contract_cache:
                return self._contract_cache[cache_key]

            contract = self._build_option_contract(symbol, expiry, strike, right,
                                                 exchange, currency, multiplier)

            # 快取合約
            self._contract_cache[cache_key] = contract

            self._log_option_contract_creation(contract)
            return contract

        except Exception as e:
            logger.exception("創建期權合約失敗: %s", e)
            return None

    def _build_option_contract(self, symbol: str, expiry: str, strike: float,
                             right: str, exchange: Optional[str],
                             currency: Optional[str], multiplier: Optional[str]) -> Contract:
        """構建期權合約物件

        Args:
            symbol: 標的股票代號
            expiry: 到期日
            strike: 行權價
            right: 期權類型
            exchange: 交易所
            currency: 貨幣
            multiplier: 合約乘數

        Returns:
            Contract: 構建的期權合約
        """
        contract = Contract()
        contract.secType = SecurityType.OPTION.value
        contract.symbol = symbol.upper()
        contract.lastTradeDateOrContractMonth = expiry
        contract.strike = strike
        contract.right = right.upper()

        # 設定市場特定參數
        self._set_market_specific_params(contract, symbol, exchange, currency, multiplier)
        return contract

    def _set_market_specific_params(self, contract: Contract, symbol: str,
                                  exchange: Optional[str], currency: Optional[str],
                                  multiplier: Optional[str]) -> None:
        """設定市場特定參數

        Args:
            contract: 合約物件
            symbol: 股票代號
            exchange: 交易所
            currency: 貨幣
            multiplier: 合約乘數
        """
        if symbol.endswith('.TW'):
            contract.exchange = exchange or Exchange.TSE.value
            contract.currency = currency or Currency.TWD.value
            contract.multiplier = multiplier or "1000"  # 台股期權乘數
        elif symbol.endswith('.HK'):
            contract.exchange = exchange or Exchange.SEHK.value
            contract.currency = currency or Currency.HKD.value
            contract.multiplier = multiplier or "100"
        else:
            # 美股期權
            contract.exchange = exchange or Exchange.SMART.value
            contract.currency = currency or Currency.USD.value
            contract.multiplier = multiplier or "100"

    def _log_option_contract_creation(self, contract: Contract) -> None:
        """記錄期權合約創建日誌

        Args:
            contract: 創建的合約
        """
        logger.debug(
            "創建期權合約 - 代號: %s, 到期: %s, 行權價: %.2f, 類型: %s",
            contract.symbol, contract.lastTradeDateOrContractMonth,
            contract.strike, contract.right
        )

    def create_future_contract(
        self,
        symbol: str,
        expiry: str,
        exchange: str,
        currency: Optional[str] = None,
        multiplier: Optional[str] = None
    ) -> Optional[Contract]:
        """創建期貨合約
        
        Args:
            symbol: 期貨代號
            expiry: 到期月份 (格式: YYYYMM)
            exchange: 交易所
            currency: 貨幣（可選）
            multiplier: 合約乘數（可選）
            
        Returns:
            Contract: IB 期貨合約或 None
        """
        try:
            contract = Contract()
            contract.secType = SecurityType.FUTURE.value
            contract.symbol = symbol.upper()
            contract.lastTradeDateOrContractMonth = expiry
            contract.exchange = exchange
            contract.currency = currency or Currency.USD.value
            
            if multiplier:
                contract.multiplier = multiplier
            
            logger.debug(
                "創建期貨合約 - 代號: %s, 到期: %s, 交易所: %s",
                contract.symbol, contract.lastTradeDateOrContractMonth, contract.exchange
            )
            
            return contract

        except Exception as e:
            logger.exception("創建期貨合約失敗: %s", e)
            return None

    def get_option_expiry_dates(
        self,
        symbol: str,
        months_ahead: int = 6
    ) -> List[str]:
        """獲取期權到期日列表
        
        Args:
            symbol: 股票代號
            months_ahead: 向前幾個月
            
        Returns:
            List[str]: 到期日列表 (格式: YYYYMMDD)
        """
        try:
            expiry_dates = []
            current_date = datetime.now()
            
            for i in range(months_ahead):
                # 計算每月第三個星期五
                target_month = current_date.replace(day=1) + timedelta(days=32 * i)
                target_month = target_month.replace(day=1)
                
                # 找到第三個星期五
                first_friday = target_month + timedelta(days=(4 - target_month.weekday()) % 7)
                third_friday = first_friday + timedelta(days=14)
                
                expiry_dates.append(third_friday.strftime("%Y%m%d"))
            
            return expiry_dates

        except Exception as e:
            logger.exception("獲取期權到期日失敗: %s", e)
            return []

    def _validate_option_params(
        self,
        symbol: str,
        expiry: str,
        strike: float,
        right: str
    ) -> bool:
        """驗證期權參數
        
        Args:
            symbol: 股票代號
            expiry: 到期日
            strike: 行權價
            right: 期權類型
            
        Returns:
            bool: 參數是否有效
        """
        try:
            # 驗證股票代號
            if not symbol or len(symbol) < 1:
                logger.error("無效的股票代號: %s", symbol)
                return False

            # 驗證到期日格式
            if not expiry or len(expiry) != 8:
                logger.error("無效的到期日格式: %s (應為 YYYYMMDD)", expiry)
                return False
            
            try:
                datetime.strptime(expiry, "%Y%m%d")
            except ValueError:
                logger.error("無效的到期日: %s", expiry)
                return False

            # 驗證行權價
            if strike <= 0:
                logger.error("無效的行權價: %.2f", strike)
                return False

            # 驗證期權類型
            if right.upper() not in ['C', 'P', 'CALL', 'PUT']:
                logger.error("無效的期權類型: %s", right)
                return False

            return True

        except Exception as e:
            logger.exception("驗證期權參數時發生異常: %s", e)
            return False

    def clear_cache(self) -> None:
        """清除合約快取"""
        self._contract_cache.clear()
        logger.debug("已清除合約快取")

    def get_cache_size(self) -> int:
        """獲取快取大小
        
        Returns:
            int: 快取中的合約數量
        """
        return len(self._contract_cache)
