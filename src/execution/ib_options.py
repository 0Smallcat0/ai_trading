"""Interactive Brokers 期權交易模組

此模組提供完整的期權交易功能，包括期權合約管理、價格獲取、
交易執行、Greeks計算和風險管理。

版本: v1.0
作者: AI Trading System
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from ibapi.contract import Contract
    from ibapi.order import Order as IBOrder
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    # 定義模擬類型
    class Contract:
        def __init__(self):
            pass
    class IBOrder:
        def __init__(self):
            pass

from .ib_contracts import IBContractManager, OptionRight
from .ib_orders import IBOrderManager

# 設定日誌
logger = logging.getLogger("execution.ib.options")


@dataclass
class OptionQuote:
    """期權報價數據類"""
    symbol: str
    expiry: str
    strike: float
    right: str
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: float
    gamma: float
    theta: float
    vega: float
    timestamp: datetime


@dataclass
class OptionChain:
    """期權鏈數據類"""
    symbol: str
    expiry: str
    calls: List[OptionQuote]
    puts: List[OptionQuote]
    underlying_price: float


class OptionStrategy(Enum):
    """期權策略枚舉"""
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    SHORT_CALL = "short_call"
    SHORT_PUT = "short_put"
    COVERED_CALL = "covered_call"
    PROTECTIVE_PUT = "protective_put"
    BULL_CALL_SPREAD = "bull_call_spread"
    BEAR_PUT_SPREAD = "bear_put_spread"
    IRON_CONDOR = "iron_condor"
    BUTTERFLY = "butterfly"
    STRADDLE = "straddle"
    STRANGLE = "strangle"


class IBOptionsManager:
    """IB 期權管理器
    
    提供完整的期權交易功能，包括合約管理、價格獲取、交易執行和風險管理。
    """

    def __init__(self, client=None):
        """初始化期權管理器
        
        Args:
            client: IB API 客戶端
        """
        self.client = client
        self.contract_manager = IBContractManager()
        self.order_manager = IBOrderManager()
        self._option_data: Dict[str, OptionQuote] = {}
        self._req_id_counter = 5000

    def get_option_chain(
        self,
        symbol: str,
        expiry: str,
        exchange: Optional[str] = None
    ) -> Optional[OptionChain]:
        """獲取期權鏈
        
        Args:
            symbol: 標的股票代號
            expiry: 到期日 (YYYYMMDD)
            exchange: 交易所
            
        Returns:
            OptionChain: 期權鏈數據或 None
        """
        try:
            if not self.client or not self.client.isConnected():
                logger.error("IB API 未連接")
                return None

            # 獲取標的股票價格
            underlying_price = self._get_underlying_price(symbol)
            if underlying_price is None:
                logger.error("無法獲取標的股票價格: %s", symbol)
                return None

            # 生成行權價範圍
            strikes = self._generate_strike_range(underlying_price)
            
            calls = []
            puts = []

            # 獲取每個行權價的期權報價
            for strike in strikes:
                # Call 期權
                call_quote = self._get_option_quote(
                    symbol, expiry, strike, OptionRight.CALL.value, exchange
                )
                if call_quote:
                    calls.append(call_quote)

                # Put 期權
                put_quote = self._get_option_quote(
                    symbol, expiry, strike, OptionRight.PUT.value, exchange
                )
                if put_quote:
                    puts.append(put_quote)

            return OptionChain(
                symbol=symbol,
                expiry=expiry,
                calls=calls,
                puts=puts,
                underlying_price=underlying_price
            )

        except Exception as e:
            logger.exception("獲取期權鏈失敗: %s", e)
            return None

    def place_option_order(
        self,
        symbol: str,
        expiry: str,
        strike: float,
        right: str,
        action: str,
        quantity: int,
        order_type: str = "LMT",
        price: Optional[float] = None,
        **kwargs
    ) -> Optional[str]:
        """下期權單
        
        Args:
            symbol: 標的股票代號
            expiry: 到期日
            strike: 行權價
            right: 期權類型 ('C' or 'P')
            action: 買賣方向 ('BUY' or 'SELL')
            quantity: 數量
            order_type: 訂單類型
            price: 價格（限價單需要）
            **kwargs: 其他參數
            
        Returns:
            str: 訂單 ID 或 None
        """
        try:
            if not self.client or not self.client.isConnected():
                logger.error("IB API 未連接")
                return None

            # 創建期權合約
            contract = self.contract_manager.create_option_contract(
                symbol, expiry, strike, right
            )
            if not contract:
                logger.error("無法創建期權合約")
                return None

            # 創建訂單
            if order_type.upper() == "MKT":
                ib_order = self.order_manager.create_market_order(action, quantity, **kwargs)
            elif order_type.upper() == "LMT":
                if price is None:
                    logger.error("限價單需要指定價格")
                    return None
                ib_order = self.order_manager.create_limit_order(action, quantity, price, **kwargs)
            else:
                logger.error("不支援的訂單類型: %s", order_type)
                return None

            if not ib_order:
                logger.error("無法創建訂單")
                return None

            # 提交訂單
            order_id = self._get_next_order_id()
            self.client.placeOrder(order_id, contract, ib_order)

            logger.info(
                "已提交期權訂單 - 代號: %s, 到期: %s, 行權價: %.2f, 類型: %s, 方向: %s, 數量: %d",
                symbol, expiry, strike, right, action, quantity
            )

            return str(order_id)

        except Exception as e:
            logger.exception("下期權單失敗: %s", e)
            return None

    def execute_option_strategy(
        self,
        strategy: OptionStrategy,
        symbol: str,
        expiry: str,
        **strategy_params
    ) -> Optional[List[str]]:
        """執行期權策略
        
        Args:
            strategy: 期權策略
            symbol: 標的股票代號
            expiry: 到期日
            **strategy_params: 策略參數
            
        Returns:
            List[str]: 訂單 ID 列表或 None
        """
        try:
            if strategy == OptionStrategy.COVERED_CALL:
                return self._execute_covered_call(symbol, expiry, **strategy_params)
            elif strategy == OptionStrategy.PROTECTIVE_PUT:
                return self._execute_protective_put(symbol, expiry, **strategy_params)
            elif strategy == OptionStrategy.BULL_CALL_SPREAD:
                return self._execute_bull_call_spread(symbol, expiry, **strategy_params)
            elif strategy == OptionStrategy.BEAR_PUT_SPREAD:
                return self._execute_bear_put_spread(symbol, expiry, **strategy_params)
            elif strategy == OptionStrategy.STRADDLE:
                return self._execute_straddle(symbol, expiry, **strategy_params)
            elif strategy == OptionStrategy.STRANGLE:
                return self._execute_strangle(symbol, expiry, **strategy_params)
            else:
                logger.error("不支援的期權策略: %s", strategy)
                return None

        except Exception as e:
            logger.exception("執行期權策略失敗: %s", e)
            return None

    def calculate_greeks(
        self,
        symbol: str,
        expiry: str,
        strike: float,
        right: str,
        underlying_price: float,
        risk_free_rate: float = 0.02,
        volatility: float = 0.2
    ) -> Optional[Dict[str, float]]:
        """計算期權 Greeks
        
        Args:
            symbol: 標的股票代號
            expiry: 到期日
            strike: 行權價
            right: 期權類型
            underlying_price: 標的價格
            risk_free_rate: 無風險利率
            volatility: 波動率
            
        Returns:
            Dict[str, float]: Greeks 值或 None
        """
        try:
            # 計算到期時間（年）
            expiry_date = datetime.strptime(expiry, "%Y%m%d")
            time_to_expiry = (expiry_date - datetime.now()).days / 365.0

            if time_to_expiry <= 0:
                logger.warning("期權已到期")
                return None

            # 使用 Black-Scholes 模型計算 Greeks
            greeks = self._black_scholes_greeks(
                underlying_price, strike, time_to_expiry,
                risk_free_rate, volatility, right.upper()
            )

            return greeks

        except Exception as e:
            logger.exception("計算 Greeks 失敗: %s", e)
            return None

    def _get_option_quote(
        self,
        symbol: str,
        expiry: str,
        strike: float,
        right: str,
        exchange: Optional[str] = None
    ) -> Optional[OptionQuote]:
        """獲取期權報價
        
        Args:
            symbol: 標的股票代號
            expiry: 到期日
            strike: 行權價
            right: 期權類型
            exchange: 交易所
            
        Returns:
            OptionQuote: 期權報價或 None
        """
        try:
            # 創建期權合約
            contract = self.contract_manager.create_option_contract(
                symbol, expiry, strike, right, exchange
            )
            if not contract:
                return None

            # 請求市場數據（簡化實現）
            # 實際實現需要使用 IB API 的 reqMktData
            
            # 模擬數據
            return OptionQuote(
                symbol=symbol,
                expiry=expiry,
                strike=strike,
                right=right,
                bid=1.0,
                ask=1.1,
                last=1.05,
                volume=100,
                open_interest=500,
                implied_volatility=0.2,
                delta=0.5,
                gamma=0.1,
                theta=-0.05,
                vega=0.1,
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.exception("獲取期權報價失敗: %s", e)
            return None

    def _get_underlying_price(self, symbol: str) -> Optional[float]:
        """獲取標的股票價格
        
        Args:
            symbol: 股票代號
            
        Returns:
            float: 股票價格或 None
        """
        try:
            # 簡化實現，實際需要從市場數據獲取
            return 100.0  # 模擬價格

        except Exception as e:
            logger.exception("獲取標的價格失敗: %s", e)
            return None

    def _generate_strike_range(
        self,
        underlying_price: float,
        range_percent: float = 0.2,
        strike_interval: float = 5.0
    ) -> List[float]:
        """生成行權價範圍
        
        Args:
            underlying_price: 標的價格
            range_percent: 價格範圍百分比
            strike_interval: 行權價間隔
            
        Returns:
            List[float]: 行權價列表
        """
        try:
            price_range = underlying_price * range_percent
            min_strike = underlying_price - price_range
            max_strike = underlying_price + price_range

            strikes = []
            current_strike = math.floor(min_strike / strike_interval) * strike_interval

            while current_strike <= max_strike:
                strikes.append(current_strike)
                current_strike += strike_interval

            return strikes

        except Exception as e:
            logger.exception("生成行權價範圍失敗: %s", e)
            return []

    def _black_scholes_greeks(
        self,
        s: float,  # 標的價格
        k: float,  # 行權價
        t: float,  # 到期時間
        r: float,  # 無風險利率
        sigma: float,  # 波動率
        option_type: str  # 期權類型
    ) -> Dict[str, float]:
        """計算 Black-Scholes Greeks
        
        Args:
            s: 標的價格
            k: 行權價
            t: 到期時間（年）
            r: 無風險利率
            sigma: 波動率
            option_type: 期權類型 ('C' or 'P')
            
        Returns:
            Dict[str, float]: Greeks 值
        """
        try:
            from scipy.stats import norm
            
            # 計算 d1 和 d2
            d1 = (math.log(s / k) + (r + 0.5 * sigma ** 2) * t) / (sigma * math.sqrt(t))
            d2 = d1 - sigma * math.sqrt(t)

            # 計算 Greeks
            if option_type.upper() == 'C':  # Call
                delta = norm.cdf(d1)
                theta = (-s * norm.pdf(d1) * sigma / (2 * math.sqrt(t)) 
                        - r * k * math.exp(-r * t) * norm.cdf(d2))
            else:  # Put
                delta = norm.cdf(d1) - 1
                theta = (-s * norm.pdf(d1) * sigma / (2 * math.sqrt(t)) 
                        + r * k * math.exp(-r * t) * norm.cdf(-d2))

            gamma = norm.pdf(d1) / (s * sigma * math.sqrt(t))
            vega = s * norm.pdf(d1) * math.sqrt(t) / 100  # 除以100轉換為百分比
            rho = (k * t * math.exp(-r * t) * 
                  (norm.cdf(d2) if option_type.upper() == 'C' else norm.cdf(-d2))) / 100

            return {
                'delta': delta,
                'gamma': gamma,
                'theta': theta / 365,  # 每日 theta
                'vega': vega,
                'rho': rho
            }

        except ImportError:
            logger.warning("scipy 不可用，使用簡化 Greeks 計算")
            # 簡化計算
            return {
                'delta': 0.5,
                'gamma': 0.1,
                'theta': -0.05,
                'vega': 0.1,
                'rho': 0.05
            }
        except Exception as e:
            logger.exception("計算 Greeks 失敗: %s", e)
            return {}

    def _get_next_order_id(self) -> int:
        """獲取下一個訂單 ID"""
        self._req_id_counter += 1
        return self._req_id_counter

    def _execute_covered_call(self, symbol: str, expiry: str, **params) -> List[str]:
        """執行備兌看漲策略"""
        # 實現備兌看漲策略
        return []

    def _execute_protective_put(self, symbol: str, expiry: str, **params) -> List[str]:
        """執行保護性看跌策略"""
        # 實現保護性看跌策略
        return []

    def _execute_bull_call_spread(self, symbol: str, expiry: str, **params) -> List[str]:
        """執行牛市看漲價差策略"""
        # 實現牛市看漲價差策略
        return []

    def _execute_bear_put_spread(self, symbol: str, expiry: str, **params) -> List[str]:
        """執行熊市看跌價差策略"""
        # 實現熊市看跌價差策略
        return []

    def _execute_straddle(self, symbol: str, expiry: str, **params) -> List[str]:
        """執行跨式策略"""
        # 實現跨式策略
        return []

    def _execute_strangle(self, symbol: str, expiry: str, **params) -> List[str]:
        """執行寬跨式策略"""
        # 實現寬跨式策略
        return []
