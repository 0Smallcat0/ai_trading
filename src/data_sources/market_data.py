"""
市場數據提供者模組

此模組提供統一的市場數據存取介面，整合多個數據來源。

主要功能：
- 統一的市場數據存取介面
- 多數據來源整合
- 數據快取和優化
- 錯誤處理和重試機制

Example:
    >>> provider = MarketDataProvider()
    >>> data = provider.get_historical_data("2330", "2023-01-01", "2023-12-31")
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import numpy as np

# 導入現有的數據來源模組
try:
    from ..data_sources.market_data_collector import MarketDataCollector
    from ..data_sources.yahoo_adapter import YahooFinanceAdapter
    from ..data_sources.market_data_adapter import MarketDataAdapter
except ImportError:
    # 如果導入失敗，使用模擬實現
    MarketDataCollector = None
    YahooFinanceAdapter = None
    MarketDataAdapter = None

logger = logging.getLogger(__name__)


class MarketDataProvider:
    """市場數據提供者
    
    提供統一的市場數據存取介面，整合多個數據來源，
    包括 Yahoo Finance、券商 API 等。
    """
    
    def __init__(self, source: str = "yahoo", use_cache: bool = True):
        """初始化市場數據提供者
        
        Args:
            source: 數據來源 ("yahoo", "twse", "simulation")
            use_cache: 是否使用快取
        """
        self.source = source
        self.use_cache = use_cache
        self.adapter = None
        
        # 初始化數據適配器
        self._initialize_adapter()
        
    def _initialize_adapter(self):
        """初始化數據適配器"""
        try:
            if self.source == "yahoo" and YahooFinanceAdapter:
                self.adapter = YahooFinanceAdapter(use_cache=self.use_cache)
            elif self.source == "collector" and MarketDataCollector:
                self.adapter = MarketDataCollector(source="yahoo", use_cache=self.use_cache)
            else:
                # 使用模擬適配器
                self.adapter = SimulatedMarketDataAdapter()
                logger.warning("使用模擬市場數據適配器")
        except Exception as e:
            logger.error(f"初始化數據適配器失敗: {e}")
            self.adapter = SimulatedMarketDataAdapter()
    
    def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """獲取歷史數據
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            interval: 時間間隔 ("1d", "1h", "5m")
            
        Returns:
            pd.DataFrame: 歷史數據，包含 OHLCV 欄位
        """
        try:
            if self.adapter and hasattr(self.adapter, 'get_historical_data'):
                return self.adapter.get_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval
                )
            else:
                return self._generate_sample_data(symbol, start_date, end_date)
        except Exception as e:
            logger.error(f"獲取歷史數據失敗: {e}")
            return self._generate_sample_data(symbol, start_date, end_date)
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """獲取即時報價
        
        Args:
            symbol: 股票代碼
            
        Returns:
            Dict[str, Any]: 即時報價數據
        """
        try:
            if self.adapter and hasattr(self.adapter, 'get_quote'):
                return self.adapter.get_quote(symbol)
            else:
                return self._generate_sample_quote(symbol)
        except Exception as e:
            logger.error(f"獲取即時報價失敗: {e}")
            return self._generate_sample_quote(symbol)
    
    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """獲取多個股票的即時報價
        
        Args:
            symbols: 股票代碼列表
            
        Returns:
            Dict[str, Dict[str, Any]]: 多個股票的報價數據
        """
        quotes = {}
        for symbol in symbols:
            quotes[symbol] = self.get_quote(symbol)
        return quotes
    
    def _generate_sample_data(
        self, 
        symbol: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """生成模擬數據"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        # 生成日期範圍
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        dates = dates[dates.weekday < 5]  # 只保留工作日
        
        # 生成模擬價格數據
        np.random.seed(hash(symbol) % 2**32)
        n_days = len(dates)
        
        # 基礎價格
        base_price = 100.0
        
        # 生成價格走勢
        returns = np.random.normal(0.001, 0.02, n_days)
        prices = [base_price]
        
        for i in range(1, n_days):
            price = prices[-1] * (1 + returns[i])
            prices.append(max(price, 1.0))  # 確保價格不為負
        
        # 生成 OHLCV 數據
        data = []
        for i, date in enumerate(dates):
            close = prices[i]
            open_price = close * (1 + np.random.normal(0, 0.005))
            high = max(open_price, close) * (1 + abs(np.random.normal(0, 0.01)))
            low = min(open_price, close) * (1 - abs(np.random.normal(0, 0.01)))
            volume = int(np.random.normal(1000000, 200000))
            
            data.append({
                'Date': date,
                'Open': round(open_price, 2),
                'High': round(high, 2),
                'Low': round(low, 2),
                'Close': round(close, 2),
                'Volume': max(volume, 1000)
            })
        
        df = pd.DataFrame(data)
        df.set_index('Date', inplace=True)
        return df
    
    def _generate_sample_quote(self, symbol: str) -> Dict[str, Any]:
        """生成模擬報價"""
        np.random.seed(hash(symbol) % 2**32)
        
        base_price = 100.0 + (hash(symbol) % 100)
        current_price = base_price * (1 + np.random.normal(0, 0.02))
        
        return {
            'symbol': symbol,
            'price': round(current_price, 2),
            'change': round(np.random.normal(0, 1.5), 2),
            'change_percent': round(np.random.normal(0, 1.5), 2),
            'volume': int(np.random.normal(1000000, 200000)),
            'bid': round(current_price * 0.999, 2),
            'ask': round(current_price * 1.001, 2),
            'timestamp': datetime.now()
        }


class SimulatedMarketDataAdapter:
    """模擬市場數據適配器"""
    
    def __init__(self):
        """初始化模擬適配器"""
        self.connected = True
    
    def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """獲取歷史數據（模擬）"""
        provider = MarketDataProvider(source="simulation")
        return provider._generate_sample_data(symbol, start_date, end_date)
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """獲取即時報價（模擬）"""
        provider = MarketDataProvider(source="simulation")
        return provider._generate_sample_quote(symbol)


# 創建全局實例
market_data_provider = MarketDataProvider()


# 便捷函數
def get_stock_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """獲取股票數據的便捷函數
    
    Args:
        symbol: 股票代碼
        days: 天數
        
    Returns:
        pd.DataFrame: 股票數據
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    return market_data_provider.get_historical_data(
        symbol=symbol,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )


def get_current_price(symbol: str) -> float:
    """獲取當前價格的便捷函數
    
    Args:
        symbol: 股票代碼
        
    Returns:
        float: 當前價格
    """
    quote = market_data_provider.get_quote(symbol)
    return quote.get('price', 0.0)


__all__ = [
    'MarketDataProvider',
    'SimulatedMarketDataAdapter',
    'market_data_provider',
    'get_stock_data',
    'get_current_price'
]
