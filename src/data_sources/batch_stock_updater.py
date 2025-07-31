#!/usr/bin/env python3
"""
批量股票數據更新器
支援大規模股票數據更新，包含進度追蹤、斷點續傳、暫停恢復功能
"""

import sys
import os
import time
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import threading

# 添加項目路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.data_sources.taiwan_stock_list_manager import TaiwanStockListManager, StockInfo
from src.data_sources.real_data_crawler import RealDataCrawler

logger = logging.getLogger(__name__)

class BatchStatus(Enum):
    """批量更新狀態"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BatchProgress:
    """批量更新進度"""
    total_stocks: int
    completed_stocks: int
    failed_stocks: int
    current_stock: str
    status: BatchStatus
    start_time: datetime
    estimated_remaining_time: float = 0.0
    success_rate: float = 0.0
    current_batch: int = 0
    total_batches: int = 0

@dataclass
class BatchConfig:
    """批量更新配置"""
    batch_size: int = 50
    request_delay: float = 1.0
    max_retries: int = 3
    retry_delay: float = 2.0
    enable_pause_resume: bool = True
    save_progress_interval: int = 10

class BatchStockUpdater:
    """批量股票數據更新器"""
    
    def __init__(self, db_path: str = 'sqlite:///data/enhanced_stock_database.db'):
        """
        初始化批量更新器
        
        Args:
            db_path: 資料庫路徑
        """
        self.db_path = db_path
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 初始化組件
        self.stock_manager = TaiwanStockListManager(db_path.replace('sqlite:///', ''))
        self.crawler = RealDataCrawler(db_path=db_path)
        
        # 狀態管理
        self.progress = None
        self.config = BatchConfig()
        self.is_paused = False
        self.should_stop = False
        self.progress_callbacks = []
        
        # 進度保存路徑
        self.progress_file = 'data/batch_update_progress.json'
        
        self.logger.info("批量股票數據更新器初始化完成")
    
    def add_progress_callback(self, callback: Callable[[BatchProgress], None]):
        """
        添加進度回調函數
        
        Args:
            callback: 進度回調函數
        """
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self):
        """通知進度更新"""
        if self.progress:
            for callback in self.progress_callbacks:
                try:
                    callback(self.progress)
                except Exception as e:
                    self.logger.warning(f"進度回調執行失敗: {e}")
    
    def _save_progress(self):
        """保存進度到檔案"""
        if not self.progress:
            return
        
        try:
            os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
            
            progress_data = {
                'total_stocks': self.progress.total_stocks,
                'completed_stocks': self.progress.completed_stocks,
                'failed_stocks': self.progress.failed_stocks,
                'current_stock': self.progress.current_stock,
                'status': self.progress.status.value,
                'start_time': self.progress.start_time.isoformat(),
                'current_batch': self.progress.current_batch,
                'total_batches': self.progress.total_batches
            }
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.warning(f"保存進度失敗: {e}")
    
    def _load_progress(self) -> Optional[BatchProgress]:
        """從檔案載入進度"""
        try:
            if not os.path.exists(self.progress_file):
                return None
            
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            progress = BatchProgress(
                total_stocks=data['total_stocks'],
                completed_stocks=data['completed_stocks'],
                failed_stocks=data['failed_stocks'],
                current_stock=data['current_stock'],
                status=BatchStatus(data['status']),
                start_time=datetime.fromisoformat(data['start_time']),
                current_batch=data.get('current_batch', 0),
                total_batches=data.get('total_batches', 0)
            )
            
            return progress
            
        except Exception as e:
            self.logger.warning(f"載入進度失敗: {e}")
            return None
    
    def _calculate_estimated_time(self) -> float:
        """計算預估剩餘時間（秒）"""
        if not self.progress or self.progress.completed_stocks == 0:
            return 0.0
        
        elapsed_time = (datetime.now() - self.progress.start_time).total_seconds()
        avg_time_per_stock = elapsed_time / self.progress.completed_stocks
        remaining_stocks = self.progress.total_stocks - self.progress.completed_stocks
        
        return avg_time_per_stock * remaining_stocks
    
    def update_all_stocks(self, year: int = None, month: int = None,
                         config: Optional[BatchConfig] = None,
                         resume: bool = False,
                         stock_list: Optional[List[StockInfo]] = None,
                         start_date: Optional[date] = None,
                         end_date: Optional[date] = None) -> Dict:
        """
        更新所有股票數據

        Args:
            year: 年份（向後兼容，與month一起使用）
            month: 月份（向後兼容，與year一起使用）
            config: 批量更新配置
            resume: 是否恢復之前的進度
            stock_list: 自定義股票清單（用於測試模式）
            start_date: 開始日期（新功能，與end_date一起使用）
            end_date: 結束日期（新功能，與start_date一起使用）

        Returns:
            Dict: 更新結果
        """
        try:
            # 驗證參數
            if start_date and end_date:
                # 使用新的日期範圍模式
                if start_date > end_date:
                    raise ValueError("開始日期不能晚於結束日期")
                date_mode = "range"
                self.logger.info(f"📅 使用日期範圍模式: {start_date} 至 {end_date}")
            elif year and month:
                # 使用舊的年月模式（向後兼容）
                date_mode = "month"
                start_date = date(year, month, 1)
                if month == 12:
                    end_date = date(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = date(year, month + 1, 1) - timedelta(days=1)
                self.logger.info(f"📅 使用月份模式: {year}-{month:02d}")
            else:
                raise ValueError("必須提供 start_date/end_date 或 year/month 參數")

            # 使用提供的配置或默認配置
            if config:
                self.config = config

            # 如果提供了自定義股票清單（測試模式），強制重置進度
            if stock_list is not None:
                self.progress = None
                resume = False
                self.logger.info(f"🧪 測試模式啟用：將更新 {len(stock_list)} 個股票")

            # 嘗試恢復進度
            if resume:
                saved_progress = self._load_progress()
                if saved_progress and saved_progress.status == BatchStatus.PAUSED:
                    self.progress = saved_progress
                    self.logger.info(f"恢復之前的進度: {self.progress.completed_stocks}/{self.progress.total_stocks}")

            # 獲取股票清單
            if not self.progress:
                self.logger.info("🔄 獲取股票清單...")

                # 使用自定義股票清單或獲取所有股票
                if stock_list is not None:
                    stocks = stock_list
                    self.logger.info(f"🧪 使用自定義股票清單: {len(stocks)} 個股票")
                else:
                    stocks = self.stock_manager.get_all_stocks()

                    if not stocks:
                        # 嘗試更新股票清單
                        self.logger.info("股票清單為空，嘗試更新...")
                        self.stock_manager.update_stock_list()
                        stocks = self.stock_manager.get_all_stocks()

                    if not stocks:
                        raise Exception("無法獲取股票清單")
                
                # 初始化進度
                total_batches = (len(stocks) + self.config.batch_size - 1) // self.config.batch_size
                self.progress = BatchProgress(
                    total_stocks=len(stocks),
                    completed_stocks=0,
                    failed_stocks=0,
                    current_stock="",
                    status=BatchStatus.RUNNING,
                    start_time=datetime.now(),
                    total_batches=total_batches
                )
                
                self.logger.info(f"🚀 開始批量更新 {len(stocks)} 個股票")
            else:
                # 恢復進度時，使用自定義股票清單或獲取所有股票
                if stock_list is not None:
                    stocks = stock_list
                else:
                    stocks = self.stock_manager.get_all_stocks()
            
            # 重置控制標誌
            self.is_paused = False
            self.should_stop = False
            self.progress.status = BatchStatus.RUNNING
            
            # 分批處理
            failed_stocks = []
            start_index = self.progress.completed_stocks
            
            for i in range(start_index, len(stocks), self.config.batch_size):
                # 檢查是否需要暫停或停止
                if self.should_stop:
                    self.progress.status = BatchStatus.CANCELLED
                    break
                
                if self.is_paused:
                    self.progress.status = BatchStatus.PAUSED
                    self._save_progress()
                    self.logger.info("⏸️ 批量更新已暫停")
                    return self._get_current_result(failed_stocks)
                
                # 處理當前批次
                batch_stocks = stocks[i:i + self.config.batch_size]
                self.progress.current_batch = (i // self.config.batch_size) + 1
                
                self.logger.info(f"📊 處理批次 {self.progress.current_batch}/{self.progress.total_batches}")
                
                for stock in batch_stocks:
                    if self.should_stop or self.is_paused:
                        break
                    
                    self.progress.current_stock = stock.symbol
                    self._notify_progress()
                    
                    # 更新單一股票
                    success = self._update_single_stock(stock.symbol, start_date, end_date)
                    
                    if success:
                        self.progress.completed_stocks += 1
                    else:
                        self.progress.failed_stocks += 1
                        failed_stocks.append(stock.symbol)
                    
                    # 計算成功率和預估時間
                    total_processed = self.progress.completed_stocks + self.progress.failed_stocks
                    if total_processed > 0:
                        self.progress.success_rate = self.progress.completed_stocks / total_processed
                    
                    self.progress.estimated_remaining_time = self._calculate_estimated_time()
                    
                    # 請求間隔
                    time.sleep(self.config.request_delay)
                
                # 定期保存進度
                if self.progress.current_batch % self.config.save_progress_interval == 0:
                    self._save_progress()
                
                self._notify_progress()
            
            # 完成更新
            if not self.should_stop and not self.is_paused:
                self.progress.status = BatchStatus.COMPLETED
                self.logger.info("✅ 批量更新完成")
            
            # 保存最終進度
            self._save_progress()
            
            return self._get_current_result(failed_stocks)
            
        except Exception as e:
            self.logger.error(f"❌ 批量更新失敗: {e}")
            if self.progress:
                self.progress.status = BatchStatus.FAILED
                self._save_progress()
            raise
    
    def _update_single_stock(self, symbol: str, start_date: date, end_date: date) -> bool:
        """
        更新單一股票數據

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            bool: 是否成功
        """
        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"🔄 更新 {symbol} (第{attempt + 1}次嘗試)")

                # 爬取日期範圍數據
                df = self.crawler.crawl_stock_data_range(symbol, start_date, end_date)

                if df is not None and not df.empty:
                    # 保存數據
                    self.crawler.save_to_database(df)
                    self.logger.debug(f"✅ {symbol} 更新成功: {len(df)}筆記錄")
                    return True
                else:
                    raise Exception("爬取結果為空")

            except Exception as e:
                self.logger.debug(f"⚠️ {symbol} 第{attempt + 1}次嘗試失敗: {e}")

                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    self.logger.warning(f"❌ {symbol} 更新失敗: {e}")

        return False
    
    def _get_current_result(self, failed_stocks: List[str]) -> Dict:
        """獲取當前結果"""
        if not self.progress:
            return {}
        
        return {
            'status': self.progress.status.value,
            'total_stocks': self.progress.total_stocks,
            'completed_stocks': self.progress.completed_stocks,
            'failed_stocks': self.progress.failed_stocks,
            'success_rate': f"{self.progress.success_rate * 100:.1f}%",
            'failed_symbols': failed_stocks,
            'duration': (datetime.now() - self.progress.start_time).total_seconds(),
            'estimated_remaining_time': self.progress.estimated_remaining_time
        }
    
    def pause(self):
        """暫停批量更新"""
        self.is_paused = True
        self.logger.info("⏸️ 請求暫停批量更新...")
    
    def resume(self, year: int, month: int):
        """恢復批量更新"""
        self.logger.info("▶️ 恢復批量更新...")
        return self.update_all_stocks(year, month, resume=True)
    
    def stop(self):
        """停止批量更新"""
        self.should_stop = True
        self.logger.info("⏹️ 請求停止批量更新...")
    
    def get_progress(self) -> Optional[BatchProgress]:
        """獲取當前進度"""
        return self.progress

def main():
    """測試函數"""
    logging.basicConfig(level=logging.INFO)
    
    updater = BatchStockUpdater()
    
    # 設置進度回調
    def progress_callback(progress: BatchProgress):
        print(f"進度: {progress.completed_stocks}/{progress.total_stocks} "
              f"({progress.success_rate*100:.1f}%) - {progress.current_stock}")
    
    updater.add_progress_callback(progress_callback)
    
    # 配置小批次測試
    config = BatchConfig(
        batch_size=5,
        request_delay=1.0,
        max_retries=2
    )
    
    # 執行批量更新（僅測試前10個股票）
    result = updater.update_all_stocks(2025, 7, config)
    print(f"更新結果: {result}")

if __name__ == "__main__":
    main()
