#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真實數據API - 替代模擬數據的統一接口
==================================

提供統一的真實數據訪問接口，完全替代系統中的模擬數據服務。
所有數據均來自官方交易所渠道，確保數據的準確性和可靠性。

功能特點：
- 統一的數據訪問接口
- 完全基於真實數據源
- 向後兼容現有API
- 自動數據更新機制
- 數據品質監控

Author: AI Trading System
Date: 2025-01-28
Version: 1.0
"""

import sys
import os
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date, timedelta
import pandas as pd

# 添加項目路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from src.core.real_data_integration import real_data_service
    from src.core.data_scheduler import data_scheduler
    logger = logging.getLogger(__name__)
    logger.info("✅ 成功導入真實數據服務")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"❌ 無法導入真實數據服務: {e}")
    # 提供基本的錯誤處理
    class MockRealDataService:
        def get_stock_data(self, *args, **kwargs):
            return pd.DataFrame()
        def update_data(self, *args, **kwargs):
            return {"success": False, "message": "真實數據服務不可用"}
        def get_market_info(self, *args, **kwargs):
            return {"status": "服務不可用"}
    
    real_data_service = MockRealDataService()
    data_scheduler = None

# ============================================================================
# 主要數據接口 - 替代模擬數據
# ============================================================================

def get_stock_data(
    symbol: str,
    start_date: Optional[Union[str, date]] = None,
    end_date: Optional[Union[str, date]] = None,
    **kwargs
) -> pd.DataFrame:
    """
    獲取股票數據 - 真實數據版本
    
    Args:
        symbol: 股票代碼 (如 '2330.TW' 或 '2330')
        start_date: 開始日期
        end_date: 結束日期
        **kwargs: 其他參數（保持兼容性）
        
    Returns:
        pd.DataFrame: 股票數據
    """
    try:
        # 確保股票代碼格式正確
        if not symbol.endswith('.TW'):
            symbol = f"{symbol}.TW"
        
        # 轉換日期格式
        start_dt = None
        end_dt = None
        
        if start_date:
            if isinstance(start_date, str):
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            else:
                start_dt = start_date
                
        if end_date:
            if isinstance(end_date, str):
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            else:
                end_dt = end_date
        
        # 獲取真實數據
        df = real_data_service.get_stock_data(symbol, start_dt, end_dt)
        
        if not df.empty:
            logger.info(f"✅ 獲取 {symbol} 真實數據: {len(df)} 筆記錄")
        else:
            logger.warning(f"⚠️ 未找到 {symbol} 的數據")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ 獲取 {symbol} 數據失敗: {e}")
        return pd.DataFrame()

def update_data(
    symbols: Optional[List[str]] = None,
    data_types: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    更新數據 - 真實數據版本
    
    Args:
        symbols: 股票代碼列表
        data_types: 數據類型列表（保持兼容性）
        **kwargs: 其他參數
        
    Returns:
        Dict[str, Any]: 更新結果
    """
    try:
        logger.info("🚀 開始更新真實數據")
        
        # 調用真實數據服務
        result = real_data_service.update_data(symbols=symbols)
        
        if result['success']:
            logger.info(f"✅ 真實數據更新成功: {result['message']}")
        else:
            logger.error(f"❌ 真實數據更新失敗: {result['message']}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 數據更新異常: {e}")
        return {
            "success": False,
            "message": f"數據更新異常: {e}",
            "data_source": "真實數據源"
        }

def get_market_info(**kwargs) -> Dict[str, Any]:
    """
    獲取市場信息 - 真實數據版本
    
    Returns:
        Dict[str, Any]: 市場信息
    """
    try:
        market_info = real_data_service.get_market_info()
        logger.info("✅ 獲取市場信息成功")
        return market_info
        
    except Exception as e:
        logger.error(f"❌ 獲取市場信息失敗: {e}")
        return {
            "status": "錯誤",
            "message": f"獲取市場信息失敗: {e}",
            "data_source": "真實數據源"
        }

def get_available_symbols() -> List[str]:
    """
    獲取可用的股票代碼列表
    
    Returns:
        List[str]: 股票代碼列表
    """
    try:
        symbols = real_data_service.get_available_symbols()
        logger.info(f"✅ 獲取可用股票列表: {len(symbols)} 個")
        return symbols
        
    except Exception as e:
        logger.error(f"❌ 獲取股票列表失敗: {e}")
        return []

def get_data_quality_metrics() -> Dict[str, Any]:
    """
    獲取數據品質指標
    
    Returns:
        Dict[str, Any]: 品質指標
    """
    try:
        metrics = real_data_service.get_quality_metrics()
        logger.info("✅ 獲取數據品質指標成功")
        return metrics
        
    except Exception as e:
        logger.error(f"❌ 獲取品質指標失敗: {e}")
        return {}

def system_health_check() -> Dict[str, Any]:
    """
    系統健康檢查
    
    Returns:
        Dict[str, Any]: 健康狀態
    """
    try:
        health = real_data_service.health_check()
        logger.info(f"✅ 系統健康檢查: {health['status']}")
        return health
        
    except Exception as e:
        logger.error(f"❌ 健康檢查失敗: {e}")
        return {
            "status": "異常",
            "error": str(e),
            "last_check": datetime.now()
        }

# ============================================================================
# 調度器控制接口
# ============================================================================

def start_data_scheduler():
    """啟動數據調度器"""
    if data_scheduler:
        try:
            data_scheduler.start()
            logger.info("✅ 數據調度器已啟動")
            return {"success": True, "message": "調度器啟動成功"}
        except Exception as e:
            logger.error(f"❌ 調度器啟動失敗: {e}")
            return {"success": False, "message": f"調度器啟動失敗: {e}"}
    else:
        return {"success": False, "message": "調度器不可用"}

def stop_data_scheduler():
    """停止數據調度器"""
    if data_scheduler:
        try:
            data_scheduler.stop()
            logger.info("⏹️ 數據調度器已停止")
            return {"success": True, "message": "調度器停止成功"}
        except Exception as e:
            logger.error(f"❌ 調度器停止失敗: {e}")
            return {"success": False, "message": f"調度器停止失敗: {e}"}
    else:
        return {"success": False, "message": "調度器不可用"}

def get_scheduler_status() -> Dict[str, Any]:
    """獲取調度器狀態"""
    if data_scheduler:
        try:
            status = data_scheduler.get_status()
            logger.info("✅ 獲取調度器狀態成功")
            return status
        except Exception as e:
            logger.error(f"❌ 獲取調度器狀態失敗: {e}")
            return {"error": str(e)}
    else:
        return {"error": "調度器不可用"}

def run_immediate_update(task_name: str = "daily_update") -> Dict[str, Any]:
    """立即執行數據更新"""
    if data_scheduler:
        try:
            result = data_scheduler.run_task_now(task_name)
            logger.info(f"✅ 立即執行任務 {task_name} 完成")
            return result
        except Exception as e:
            logger.error(f"❌ 立即執行任務失敗: {e}")
            return {"success": False, "message": f"任務執行失敗: {e}"}
    else:
        # 如果調度器不可用，直接調用數據服務
        return update_data()

# ============================================================================
# 向後兼容接口
# ============================================================================

# 為了保持向後兼容性，提供舊API的別名
def get_stock_price(symbol: str, **kwargs) -> pd.DataFrame:
    """獲取股價數據 - 兼容接口"""
    return get_stock_data(symbol, **kwargs)

def get_stock_info(symbol: str, **kwargs) -> Dict[str, Any]:
    """獲取股票信息 - 兼容接口"""
    df = get_stock_data(symbol, **kwargs)
    if not df.empty:
        latest = df.iloc[-1]
        return {
            "symbol": symbol,
            "price": latest['close'],
            "volume": latest['volume'],
            "date": latest['date'],
            "data_source": "真實數據源"
        }
    else:
        return {"symbol": symbol, "error": "無數據"}

def update_stock_data(**kwargs) -> Dict[str, Any]:
    """更新股票數據 - 兼容接口"""
    return update_data(**kwargs)

# ============================================================================
# 模組初始化
# ============================================================================

def initialize_real_data_system():
    """初始化真實數據系統"""
    try:
        logger.info("🚀 初始化真實數據系統")
        
        # 檢查系統健康狀態
        health = system_health_check()
        if health['status'] == '健康':
            logger.info("✅ 真實數據系統健康狀態良好")
        else:
            logger.warning(f"⚠️ 真實數據系統狀態: {health['status']}")
        
        # 啟動調度器
        scheduler_result = start_data_scheduler()
        if scheduler_result['success']:
            logger.info("✅ 數據調度器啟動成功")
        else:
            logger.warning(f"⚠️ 調度器啟動失敗: {scheduler_result['message']}")
        
        logger.info("🎉 真實數據系統初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 真實數據系統初始化失敗: {e}")
        return False

# 自動初始化
if __name__ != "__main__":
    initialize_real_data_system()

if __name__ == "__main__":
    # 測試真實數據API
    print("🧪 測試真實數據API")
    
    # 測試系統健康檢查
    health = system_health_check()
    print(f"系統健康狀態: {health['status']}")
    
    # 測試獲取股票數據
    df = get_stock_data('2330.TW')
    if not df.empty:
        print(f"✅ 成功獲取台積電數據: {len(df)} 筆記錄")
    else:
        print("❌ 未獲取到數據")
    
    # 測試市場信息
    market_info = get_market_info()
    print(f"市場狀態: {market_info.get('market_status', '未知')}")
    
    print("🎉 真實數據API測試完成")
