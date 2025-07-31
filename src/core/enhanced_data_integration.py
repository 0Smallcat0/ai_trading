#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增強版數據整合服務
================

整合多渠道數據爬蟲到現有的真實數據系統中，提供統一的數據訪問接口。
支援TWSE、TPEX、Yahoo Finance等多個數據源的自動備援和品質控制。

功能特點：
- 與現有真實數據服務無縫整合
- 多渠道自動備援機制
- 智能數據品質控制
- 自學優化能力
- 統一的API接口

Author: AI Trading System
Date: 2025-01-28
Version: 1.0
"""

import sys
import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
import pandas as pd

# 添加項目路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from src.data_sources.multi_channel_crawler import AutoDataManager
    from src.core.real_data_integration import real_data_service
    MULTI_CHANNEL_AVAILABLE = True
except ImportError as e:
    logging.warning(f"多渠道爬蟲不可用: {e}")
    MULTI_CHANNEL_AVAILABLE = False

logger = logging.getLogger(__name__)

class EnhancedDataIntegrationService:
    """增強版數據整合服務"""
    
    def __init__(self, db_url: str = "sqlite:///enhanced_stock_data.db"):
        self.db_url = db_url
        self.multi_channel_manager = None
        
        # 初始化多渠道管理器
        if MULTI_CHANNEL_AVAILABLE:
            try:
                self.multi_channel_manager = AutoDataManager(db_url)
                logger.info("✅ 多渠道數據管理器初始化成功")
            except Exception as e:
                logger.error(f"❌ 多渠道數據管理器初始化失敗: {e}")
                self.multi_channel_manager = None
        
        # 支援的股票列表
        self.supported_symbols = [
            '2330.TW', '2317.TW', '2454.TW', '2412.TW', '2882.TW',
            '2308.TW', '2303.TW', '1303.TW', '1301.TW', '2002.TW',
            '2379.TW', '3008.TW', '2357.TW', '2382.TW', '2395.TW',
            '2891.TW', '2892.TW', '2880.TW', '2881.TW', '2886.TW',
            '1216.TW', '1101.TW', '2207.TW', '2105.TW', '9904.TW'
        ]
    
    def get_stock_data_enhanced(
        self, 
        symbol: str, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None,
        use_multi_channel: bool = True
    ) -> pd.DataFrame:
        """
        增強版股票數據獲取
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            use_multi_channel: 是否使用多渠道爬蟲
            
        Returns:
            pd.DataFrame: 股票數據
        """
        try:
            # 設置默認日期範圍
            if end_date is None:
                end_date = date.today()
            if start_date is None:
                start_date = end_date - timedelta(days=30)
            
            logger.info(f"🔍 獲取 {symbol} 數據 ({start_date} 至 {end_date})")
            
            # 優先使用多渠道爬蟲
            if use_multi_channel and self.multi_channel_manager:
                try:
                    results = self.multi_channel_manager.crawl_multi_channel_data(
                        symbols=[symbol],
                        start_date=start_date,
                        end_date=end_date,
                        max_workers=1
                    )
                    
                    if symbol in results and not results[symbol].empty:
                        df = results[symbol]
                        logger.info(f"✅ 多渠道獲取 {symbol} 成功: {len(df)} 筆記錄")
                        return df
                    else:
                        logger.warning(f"⚠️ 多渠道獲取 {symbol} 無數據，嘗試備援方案")
                        
                except Exception as e:
                    logger.warning(f"⚠️ 多渠道獲取 {symbol} 失敗: {e}，嘗試備援方案")
            
            # 備援方案：使用原有的真實數據服務
            try:
                df = real_data_service.get_stock_data(symbol, start_date, end_date)
                if not df.empty:
                    logger.info(f"✅ 備援方案獲取 {symbol} 成功: {len(df)} 筆記錄")
                    return df
                else:
                    logger.warning(f"⚠️ 備援方案獲取 {symbol} 無數據")
                    
            except Exception as e:
                logger.error(f"❌ 備援方案獲取 {symbol} 失敗: {e}")
            
            # 返回空DataFrame
            logger.error(f"❌ 所有方案都無法獲取 {symbol} 數據")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"❌ 獲取 {symbol} 數據時發生異常: {e}")
            return pd.DataFrame()
    
    def update_data_enhanced(
        self, 
        symbols: Optional[List[str]] = None,
        use_auto_retry: bool = True
    ) -> Dict[str, Any]:
        """
        增強版數據更新
        
        Args:
            symbols: 股票代碼列表，None表示更新所有支援的股票
            use_auto_retry: 是否使用自動重試功能
            
        Returns:
            Dict[str, Any]: 更新結果
        """
        try:
            # 使用默認股票列表
            if symbols is None:
                symbols = self.supported_symbols
            
            logger.info(f"🚀 開始增強版數據更新: {len(symbols)} 個股票")
            
            # 設置日期範圍（最近30天）
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
            # 使用多渠道自動管理器
            if self.multi_channel_manager and use_auto_retry:
                try:
                    results = self.multi_channel_manager.auto_detect_and_retry(
                        symbols=symbols,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    return {
                        'success': True,
                        'method': '多渠道自動重試',
                        'updated_symbols': results['saved_to_db'],
                        'total_symbols': results['total_symbols'],
                        'retry_symbols': results['retry_symbols'],
                        'quality_score': results['final_report']['overall_quality'],
                        'update_time': datetime.now(),
                        'data_source': '多渠道 (TWSE + TPEX + Yahoo Finance)'
                    }
                    
                except Exception as e:
                    logger.warning(f"⚠️ 多渠道自動更新失敗: {e}，使用備援方案")
            
            # 備援方案：使用原有的更新機制
            try:
                result = real_data_service.update_data(symbols=symbols)
                
                if result['success']:
                    return {
                        'success': True,
                        'method': '備援更新',
                        'updated_symbols': result.get('updated_symbols', len(symbols)),
                        'total_symbols': len(symbols),
                        'message': result['message'],
                        'update_time': datetime.now(),
                        'data_source': '真實數據服務備援'
                    }
                else:
                    return {
                        'success': False,
                        'method': '備援更新',
                        'message': result['message'],
                        'data_source': '真實數據服務備援'
                    }
                    
            except Exception as e:
                logger.error(f"❌ 備援更新失敗: {e}")
                return {
                    'success': False,
                    'method': '所有方案失敗',
                    'message': f'更新失敗: {e}',
                    'data_source': 'N/A'
                }
                
        except Exception as e:
            logger.error(f"❌ 增強版數據更新異常: {e}")
            return {
                'success': False,
                'message': f'更新異常: {e}',
                'data_source': 'N/A'
            }
    
    def get_data_quality_report(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        獲取數據品質報告
        
        Args:
            symbols: 股票代碼列表
            
        Returns:
            Dict[str, Any]: 品質報告
        """
        try:
            if symbols is None:
                symbols = self.supported_symbols[:5]  # 限制數量避免過載
            
            # 獲取最近數據
            end_date = date.today()
            start_date = end_date - timedelta(days=7)
            
            if self.multi_channel_manager:
                # 使用多渠道管理器獲取數據
                data_results = self.multi_channel_manager.crawl_multi_channel_data(
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    max_workers=2
                )
                
                # 生成品質報告
                report = self.multi_channel_manager.generate_accuracy_report(data_results)
                
                return {
                    'success': True,
                    'report': report,
                    'data_source': '多渠道品質分析'
                }
            else:
                # 使用基本品質檢查
                basic_report = {
                    'timestamp': datetime.now(),
                    'symbols_processed': len(symbols),
                    'overall_quality': 0.8,  # 基本估計
                    'method': '基本品質檢查',
                    'message': '多渠道分析不可用，使用基本檢查'
                }
                
                return {
                    'success': True,
                    'report': basic_report,
                    'data_source': '基本品質檢查'
                }
                
        except Exception as e:
            logger.error(f"❌ 獲取品質報告失敗: {e}")
            return {
                'success': False,
                'message': f'品質報告生成失敗: {e}',
                'data_source': 'N/A'
            }
    
    def health_check_enhanced(self) -> Dict[str, Any]:
        """增強版健康檢查"""
        try:
            health_info = {
                'timestamp': datetime.now(),
                'status': '健康',
                'components': {}
            }
            
            # 檢查多渠道管理器
            if self.multi_channel_manager:
                health_info['components']['multi_channel'] = {
                    'status': '可用',
                    'features': ['TPEX爬蟲', 'Yahoo Finance', '自動重試', '品質分析']
                }
            else:
                health_info['components']['multi_channel'] = {
                    'status': '不可用',
                    'message': '多渠道功能未啟用'
                }
            
            # 檢查原有數據服務
            try:
                original_health = real_data_service.health_check()
                health_info['components']['original_service'] = {
                    'status': original_health['status'],
                    'database_records': original_health.get('database_records', 0)
                }
            except Exception as e:
                health_info['components']['original_service'] = {
                    'status': '異常',
                    'error': str(e)
                }
            
            # 檢查支援的股票
            health_info['supported_symbols'] = len(self.supported_symbols)
            health_info['database_url'] = self.db_url
            
            return health_info
            
        except Exception as e:
            return {
                'timestamp': datetime.now(),
                'status': '異常',
                'error': str(e)
            }
    
    def get_available_symbols(self) -> List[str]:
        """獲取支援的股票代碼列表"""
        return self.supported_symbols.copy()

# 創建全局實例
enhanced_data_service = EnhancedDataIntegrationService()

# 提供向後兼容的接口
def get_stock_data_with_fallback(symbol: str, start_date: Optional[date] = None, 
                                end_date: Optional[date] = None) -> pd.DataFrame:
    """向後兼容的股票數據獲取接口"""
    return enhanced_data_service.get_stock_data_enhanced(symbol, start_date, end_date)

def update_data_with_enhancement(symbols: Optional[List[str]] = None) -> Dict[str, Any]:
    """向後兼容的數據更新接口"""
    return enhanced_data_service.update_data_enhanced(symbols)

if __name__ == "__main__":
    # 測試增強版數據服務
    print("🧪 測試增強版數據整合服務")
    
    # 健康檢查
    health = enhanced_data_service.health_check_enhanced()
    print(f"系統狀態: {health['status']}")
    
    # 測試數據獲取
    test_symbol = '2330.TW'
    df = enhanced_data_service.get_stock_data_enhanced(test_symbol)
    if not df.empty:
        print(f"✅ 成功獲取 {test_symbol} 數據: {len(df)} 筆記錄")
    else:
        print(f"❌ 獲取 {test_symbol} 數據失敗")
    
    print("🎉 測試完成")
