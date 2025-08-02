#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真實數據批量更新腳本
==================

定期從官方交易所渠道獲取最新的股票數據，
替代不準確的模擬數據，確保系統使用真實市場數據。

功能特點：
- 支持批量股票數據更新
- 多數據源備援機制
- 自動數據驗證
- 進度監控和錯誤處理
- 統計報告生成

Author: AI Trading System
Date: 2025-01-28
Version: 1.0
"""

import sys
import os
import argparse
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple
import time

# 添加項目路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.data_sources.real_data_crawler import RealDataCrawler

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/real_data_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RealDataUpdater:
    """真實數據批量更新器"""
    
    def __init__(self, db_path: str = 'sqlite:///data/real_stock_database.db'):
        """
        初始化數據更新器
        
        Args:
            db_path: 資料庫連接路徑
        """
        self.crawler = RealDataCrawler(db_path)
        self.update_stats = {
            'total_symbols': 0,
            'successful_symbols': 0,
            'failed_symbols': 0,
            'total_records': 0,
            'start_time': None,
            'end_time': None,
            'failed_symbols_list': []
        }
        
        logger.info("RealDataUpdater 初始化完成")
    
    def get_trading_months(self, start_date: date, end_date: date) -> List[Tuple[int, int]]:
        """
        獲取交易月份列表
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            (年, 月) 元組列表
        """
        months = []
        current_date = start_date.replace(day=1)  # 月初
        
        while current_date <= end_date:
            months.append((current_date.year, current_date.month))
            
            # 移動到下個月
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return months
    
    def update_symbol_data(self, symbol: str, start_date: date, end_date: date) -> bool:
        """
        更新單個股票的數據
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            是否成功
        """
        try:
            logger.info(f"開始更新 {symbol} 數據 ({start_date} 至 {end_date})")
            
            # 獲取需要更新的月份
            months = self.get_trading_months(start_date, end_date)
            
            total_records = 0
            successful_months = 0
            
            for year, month in months:
                try:
                    # 爬取數據
                    df = self.crawler.crawl_stock_data(symbol, year, month)
                    
                    if not df.empty:
                        # 存入資料庫
                        self.crawler.save_to_database(df)
                        total_records += len(df)
                        successful_months += 1
                        
                        logger.info(f"✅ {symbol} {year}-{month:02d}: {len(df)} 筆記錄")
                    else:
                        logger.warning(f"⚠️ {symbol} {year}-{month:02d}: 無數據")
                    
                    # 請求間隔，避免被封鎖
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ {symbol} {year}-{month:02d} 更新失敗: {e}")
                    continue
            
            if successful_months > 0:
                logger.info(f"✅ {symbol} 更新完成: {successful_months}/{len(months)} 個月, 總計 {total_records} 筆記錄")
                self.update_stats['total_records'] += total_records
                return True
            else:
                logger.error(f"❌ {symbol} 更新失敗: 沒有成功獲取任何月份的數據")
                return False
                
        except Exception as e:
            logger.error(f"❌ {symbol} 更新過程發生錯誤: {e}")
            return False
    
    def update_multiple_symbols(self, symbols: List[str], start_date: date, end_date: date):
        """
        批量更新多個股票數據
        
        Args:
            symbols: 股票代碼列表
            start_date: 開始日期
            end_date: 結束日期
        """
        self.update_stats['start_time'] = datetime.now()
        self.update_stats['total_symbols'] = len(symbols)
        
        logger.info(f"🚀 開始批量更新 {len(symbols)} 個股票數據")
        logger.info(f"📅 更新期間: {start_date} 至 {end_date}")
        logger.info("=" * 80)
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"📊 進度: {i}/{len(symbols)} - 處理 {symbol}")
            
            success = self.update_symbol_data(symbol, start_date, end_date)
            
            if success:
                self.update_stats['successful_symbols'] += 1
            else:
                self.update_stats['failed_symbols'] += 1
                self.update_stats['failed_symbols_list'].append(symbol)
            
            # 股票間隔，避免請求過於頻繁
            if i < len(symbols):
                time.sleep(3)
        
        self.update_stats['end_time'] = datetime.now()
        self._print_update_summary()
    
    def _print_update_summary(self):
        """打印更新總結"""
        duration = self.update_stats['end_time'] - self.update_stats['start_time']
        
        print("\n" + "=" * 80)
        print("📋 真實數據批量更新總結報告")
        print("=" * 80)
        print(f"更新時間: {self.update_stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')} 至 {self.update_stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"總耗時: {duration}")
        print()
        
        print("📊 更新統計:")
        print(f"   總股票數: {self.update_stats['total_symbols']}")
        print(f"   成功更新: {self.update_stats['successful_symbols']}")
        print(f"   更新失敗: {self.update_stats['failed_symbols']}")
        print(f"   總記錄數: {self.update_stats['total_records']}")
        
        if self.update_stats['total_symbols'] > 0:
            success_rate = (self.update_stats['successful_symbols'] / self.update_stats['total_symbols']) * 100
            print(f"   成功率: {success_rate:.1f}%")
        
        if self.update_stats['failed_symbols_list']:
            print(f"\n❌ 更新失敗的股票:")
            for symbol in self.update_stats['failed_symbols_list']:
                print(f"   - {symbol}")
        
        print("\n🔍 爬取器統計:")
        self.crawler.print_stats()
        
        # 評估更新效果
        if success_rate >= 90:
            print("\n🎉 更新結論: 批量更新成功，數據品質優秀！")
        elif success_rate >= 70:
            print("\n✅ 更新結論: 批量更新基本成功，大部分數據已更新！")
        else:
            print("\n⚠️ 更新結論: 更新效果不佳，建議檢查網路連接和數據源狀態")
        
        print("=" * 80)

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='真實數據批量更新腳本')
    
    parser.add_argument(
        '--symbols', 
        nargs='+', 
        default=['2330.TW', '2317.TW', '2454.TW', '2412.TW', '2882.TW'],
        help='股票代碼列表 (預設: 2330.TW 2317.TW 2454.TW 2412.TW 2882.TW)'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        default='2025-07-01',
        help='開始日期 (格式: YYYY-MM-DD, 預設: 2025-07-01)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        default='2025-07-27',
        help='結束日期 (格式: YYYY-MM-DD, 預設: 2025-07-27)'
    )
    
    parser.add_argument(
        '--db-path',
        type=str,
        default='sqlite:///real_stock_database.db',
        help='資料庫路徑 (預設: sqlite:///real_stock_database.db)'
    )
    
    args = parser.parse_args()
    
    try:
        # 解析日期
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        
        if start_date > end_date:
            raise ValueError("開始日期不能晚於結束日期")
        
        # 創建日誌目錄
        os.makedirs('logs', exist_ok=True)
        
        # 初始化更新器
        updater = RealDataUpdater(args.db_path)
        
        # 執行批量更新
        updater.update_multiple_symbols(args.symbols, start_date, end_date)
        
    except ValueError as e:
        logger.error(f"參數錯誤: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"執行錯誤: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
