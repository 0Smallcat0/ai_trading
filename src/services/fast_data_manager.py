# -*- coding: utf-8 -*-
"""
數據管理服務修復 - 簡化版本
"""

import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class FastDataManager:
    """快速數據管理器 - 優化版本"""
    
    def __init__(self):
        self.cache = {}
        self.last_update = {}
        logger.info("快速數據管理器已初始化")
    
    def get_stock_data(self, symbol: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """快速獲取股票數據"""
        if use_cache and symbol in self.cache:
            cache_time = self.last_update.get(symbol, 0)
            if time.time() - cache_time < 300:  # 5分鐘緩存
                logger.info(f"使用緩存數據: {symbol}")
                return self.cache[symbol]
        
        # 模擬快速數據獲取
        data = {
            "symbol": symbol,
            "price": 100.0,
            "change": 1.5,
            "volume": 1000000,
            "timestamp": time.time()
        }
        
        # 更新緩存
        self.cache[symbol] = data
        self.last_update[symbol] = time.time()
        
        logger.info(f"獲取新數據: {symbol}")
        return data
    
    def search_stocks(self, query: str) -> list:
        """快速股票搜索"""
        # 返回模擬搜索結果
        mock_results = [
            {"symbol": "2330.TW", "name": "台積電", "market": "TWSE"},
            {"symbol": "2317.TW", "name": "鴻海", "market": "TWSE"},
            {"symbol": "AAPL", "name": "Apple Inc.", "market": "NASDAQ"},
            {"symbol": "TSLA", "name": "Tesla Inc.", "market": "NASDAQ"},
        ]
        
        # 簡單過濾
        results = [r for r in mock_results if query.upper() in r["symbol"] or query in r["name"]]
        logger.info(f"搜索結果: {len(results)} 筆")
        return results[:10]  # 限制結果數量

# 創建全局實例
fast_data_manager = FastDataManager()
