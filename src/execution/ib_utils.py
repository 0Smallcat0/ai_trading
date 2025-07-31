"""Interactive Brokers 工具函數模組

此模組提供 IB API 相關的工具函數和常數定義，包括錯誤代碼映射、
數據轉換、驗證函數等。

版本: v1.0
作者: AI Trading System
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime

# 設定日誌
logger = logging.getLogger("execution.ib.utils")


class IBErrorCode(Enum):
    """IB 錯誤代碼枚舉"""
    # 連接相關
    CONNECT_FAIL = 502
    UPDATE_TWS = 503
    NOT_CONNECTED = 504
    
    # 市場數據相關
    NO_MARKET_DATA_PERMISSIONS = 354
    MARKET_DATA_NOT_SUBSCRIBED = 2104
    MARKET_DATA_FARM_DISCONNECTED = 2106
    MARKET_DATA_FARM_CONNECTED = 2107
    
    # 訂單相關
    ORDER_REJECTED = 201
    ORDER_CANCELLED = 202
    INVALID_ORDER = 203
    INSUFFICIENT_FUNDS = 2174
    
    # 帳戶相關
    ACCOUNT_NOT_FOUND = 321
    ACCOUNT_PERMISSIONS = 322


class IBConstants:
    """IB 常數定義"""
    
    # 預設設定
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_TWS_PORT = 7497
    DEFAULT_GATEWAY_PORT = 4001
    DEFAULT_CLIENT_ID = 1
    
    # 超時設定
    CONNECTION_TIMEOUT = 10
    ORDER_TIMEOUT = 30
    DATA_TIMEOUT = 5
    
    # 重試設定
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    
    # 市場數據類型
    MARKET_DATA_TYPES = {
        'TRADES': 'TRADES',
        'MIDPOINT': 'MIDPOINT',
        'BID': 'BID',
        'ASK': 'ASK',
        'BID_ASK': 'BID_ASK',
        'HISTORICAL_VOLATILITY': 'HISTORICAL_VOLATILITY',
        'OPTION_IMPLIED_VOLATILITY': 'OPTION_IMPLIED_VOLATILITY'
    }
    
    # 交易所映射
    EXCHANGE_MAPPING = {
        'US': 'SMART',
        'TW': 'TSE',
        'HK': 'SEHK',
        'JP': 'TSE.JPN',
        'UK': 'LSE',
        'DE': 'IBIS',
        'FR': 'SBF',
        'CA': 'TSE.CA'
    }
    
    # 貨幣映射
    CURRENCY_MAPPING = {
        'US': 'USD',
        'TW': 'TWD',
        'HK': 'HKD',
        'JP': 'JPY',
        'UK': 'GBP',
        'DE': 'EUR',
        'FR': 'EUR',
        'CA': 'CAD'
    }


def format_ib_error(error_code: int, error_string: str) -> str:
    """格式化 IB 錯誤訊息
    
    Args:
        error_code: 錯誤代碼
        error_string: 錯誤訊息
        
    Returns:
        str: 格式化的錯誤訊息
    """
    try:
        error_type = get_error_type(error_code)
        return f"[{error_type}] {error_code}: {error_string}"
    except Exception as e:
        logger.exception("格式化錯誤訊息失敗: %s", e)
        return f"{error_code}: {error_string}"


def get_error_type(error_code: int) -> str:
    """獲取錯誤類型
    
    Args:
        error_code: 錯誤代碼
        
    Returns:
        str: 錯誤類型
    """
    try:
        if error_code in [502, 503, 504]:
            return "連接錯誤"
        elif error_code in [354, 2104, 2106, 2107]:
            return "市場數據錯誤"
        elif error_code in [201, 202, 203, 2174]:
            return "訂單錯誤"
        elif error_code in [321, 322]:
            return "帳戶錯誤"
        elif error_code >= 2000:
            return "系統訊息"
        else:
            return "一般錯誤"
    except Exception as e:
        logger.exception("獲取錯誤類型失敗: %s", e)
        return "未知錯誤"


def is_critical_error(error_code: int) -> bool:
    """判斷是否為嚴重錯誤
    
    Args:
        error_code: 錯誤代碼
        
    Returns:
        bool: 是否為嚴重錯誤
    """
    try:
        critical_errors = [502, 503, 504, 201, 203, 2174, 321, 322]
        return error_code in critical_errors
    except Exception as e:
        logger.exception("判斷錯誤嚴重性失敗: %s", e)
        return True  # 保守處理


def parse_symbol(symbol: str) -> Dict[str, str]:
    """解析股票代號
    
    Args:
        symbol: 股票代號
        
    Returns:
        Dict[str, str]: 解析結果
        
    Example:
        >>> parse_symbol("AAPL")
        {'symbol': 'AAPL', 'market': 'US', 'exchange': 'SMART', 'currency': 'USD'}
        >>> parse_symbol("2330.TW")
        {'symbol': '2330', 'market': 'TW', 'exchange': 'TSE', 'currency': 'TWD'}
    """
    try:
        result = {
            'symbol': symbol,
            'market': 'US',
            'exchange': 'SMART',
            'currency': 'USD'
        }
        
        if symbol.endswith('.TW'):
            result['symbol'] = symbol.replace('.TW', '')
            result['market'] = 'TW'
            result['exchange'] = 'TSE'
            result['currency'] = 'TWD'
        elif symbol.endswith('.HK'):
            result['symbol'] = symbol.replace('.HK', '')
            result['market'] = 'HK'
            result['exchange'] = 'SEHK'
            result['currency'] = 'HKD'
        elif symbol.endswith('.JP'):
            result['symbol'] = symbol.replace('.JP', '')
            result['market'] = 'JP'
            result['exchange'] = 'TSE.JPN'
            result['currency'] = 'JPY'
        
        return result
        
    except Exception as e:
        logger.exception("解析股票代號失敗: %s", e)
        return {
            'symbol': symbol,
            'market': 'US',
            'exchange': 'SMART',
            'currency': 'USD'
        }


def validate_order_params(
    action: str,
    quantity: int,
    price: Optional[float] = None,
    stop_price: Optional[float] = None
) -> bool:
    """驗證訂單參數
    
    Args:
        action: 買賣方向
        quantity: 數量
        price: 價格（可選）
        stop_price: 停損價（可選）
        
    Returns:
        bool: 參數是否有效
    """
    try:
        # 驗證買賣方向
        if not action or action.upper() not in ['BUY', 'SELL']:
            logger.error("無效的買賣方向: %s", action)
            return False
        
        # 驗證數量
        if quantity <= 0:
            logger.error("無效的數量: %d", quantity)
            return False
        
        # 驗證價格
        if price is not None and price <= 0:
            logger.error("無效的價格: %.2f", price)
            return False
        
        # 驗證停損價
        if stop_price is not None and stop_price <= 0:
            logger.error("無效的停損價: %.2f", stop_price)
            return False
        
        return True
        
    except Exception as e:
        logger.exception("驗證訂單參數失敗: %s", e)
        return False


def format_contract_description(contract_dict: Dict[str, Any]) -> str:
    """格式化合約描述
    
    Args:
        contract_dict: 合約字典
        
    Returns:
        str: 格式化的合約描述
    """
    try:
        symbol = contract_dict.get('symbol', 'N/A')
        sec_type = contract_dict.get('secType', 'N/A')
        exchange = contract_dict.get('exchange', 'N/A')
        currency = contract_dict.get('currency', 'N/A')
        
        if sec_type == 'STK':
            return f"{symbol} ({exchange}, {currency})"
        elif sec_type == 'OPT':
            expiry = contract_dict.get('lastTradeDateOrContractMonth', 'N/A')
            strike = contract_dict.get('strike', 'N/A')
            right = contract_dict.get('right', 'N/A')
            return f"{symbol} {expiry} {strike} {right} ({exchange}, {currency})"
        elif sec_type == 'FUT':
            expiry = contract_dict.get('lastTradeDateOrContractMonth', 'N/A')
            return f"{symbol} {expiry} ({exchange}, {currency})"
        else:
            return f"{symbol} {sec_type} ({exchange}, {currency})"
            
    except Exception as e:
        logger.exception("格式化合約描述失敗: %s", e)
        return "無效合約"


def convert_timestamp(timestamp_str: str) -> Optional[datetime]:
    """轉換時間戳
    
    Args:
        timestamp_str: 時間戳字串
        
    Returns:
        datetime: 轉換後的時間或 None
    """
    try:
        # 嘗試多種時間格式
        formats = [
            "%Y%m%d %H:%M:%S",
            "%Y%m%d-%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y%m%d",
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        logger.warning("無法解析時間戳: %s", timestamp_str)
        return None
        
    except Exception as e:
        logger.exception("轉換時間戳失敗: %s", e)
        return None


def calculate_commission(
    quantity: int,
    price: float,
    commission_rate: float = 0.005
) -> float:
    """計算佣金
    
    Args:
        quantity: 數量
        price: 價格
        commission_rate: 佣金率
        
    Returns:
        float: 佣金金額
    """
    try:
        if quantity <= 0 or price <= 0 or commission_rate < 0:
            return 0.0
        
        total_value = quantity * price
        commission = total_value * commission_rate
        
        # 最低佣金（可配置）
        min_commission = 1.0
        return max(commission, min_commission)
        
    except Exception as e:
        logger.exception("計算佣金失敗: %s", e)
        return 0.0


def format_currency(amount: float, currency: str = "USD") -> str:
    """格式化貨幣
    
    Args:
        amount: 金額
        currency: 貨幣代碼
        
    Returns:
        str: 格式化的貨幣字串
    """
    try:
        currency_symbols = {
            'USD': '$',
            'TWD': 'NT$',
            'HKD': 'HK$',
            'JPY': '¥',
            'EUR': '€',
            'GBP': '£'
        }
        
        symbol = currency_symbols.get(currency, currency)
        
        if currency == 'JPY':
            # 日圓不顯示小數
            return f"{symbol}{amount:,.0f}"
        else:
            return f"{symbol}{amount:,.2f}"
            
    except Exception as e:
        logger.exception("格式化貨幣失敗: %s", e)
        return f"{amount:.2f} {currency}"


def get_market_hours(market: str) -> Dict[str, str]:
    """獲取市場交易時間
    
    Args:
        market: 市場代碼
        
    Returns:
        Dict[str, str]: 交易時間資訊
    """
    try:
        market_hours = {
            'US': {
                'open': '09:30',
                'close': '16:00',
                'timezone': 'EST',
                'pre_market': '04:00-09:30',
                'after_hours': '16:00-20:00'
            },
            'TW': {
                'open': '09:00',
                'close': '13:30',
                'timezone': 'CST',
                'pre_market': 'N/A',
                'after_hours': 'N/A'
            },
            'HK': {
                'open': '09:30',
                'close': '16:00',
                'timezone': 'HKT',
                'pre_market': 'N/A',
                'after_hours': 'N/A'
            }
        }
        
        return market_hours.get(market, market_hours['US'])
        
    except Exception as e:
        logger.exception("獲取市場交易時間失敗: %s", e)
        return {
            'open': '09:30',
            'close': '16:00',
            'timezone': 'EST',
            'pre_market': 'N/A',
            'after_hours': 'N/A'
        }
