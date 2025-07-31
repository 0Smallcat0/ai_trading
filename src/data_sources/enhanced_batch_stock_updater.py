#!/usr/bin/env python3
"""
增強版批量股票數據更新器 - 支持並行處理和智能更新

主要改進：
1. 並行股票更新，大幅提升處理速度
2. 智能增量更新，避免重複處理
3. 動態負載均衡，優化資源利用
4. 詳細性能監控和進度追蹤
5. 錯誤恢復和重試機制

作者：AI Trading System
版本：2.0
日期：2025-07-29
"""

import sys
import os
import time
import logging
import threading
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from pathlib import Path

# 添加項目路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.data_sources.batch_stock_updater import BatchStockUpdater, BatchConfig, BatchProgress, BatchStatus
from src.data_sources.enhanced_real_data_crawler import EnhancedRealDataCrawler, CrawlerConfig
from src.data_sources.taiwan_stock_list_manager import TaiwanStockListManager

# 設置日誌
logger = logging.getLogger(__name__)


@dataclass
class EnhancedBatchConfig(BatchConfig):
    """增強版批量更新配置"""
    # 並行處理配置
    max_workers: int = 4  # 最大並行線程數
    enable_parallel: bool = True  # 啟用並行處理
    
    # 增量更新配置
    enable_incremental: bool = True  # 啟用增量更新
    data_freshness_hours: int = 24  # 數據新鮮度（小時）
    
    # 性能優化配置
    batch_db_operations: bool = True  # 批量數據庫操作
    dynamic_rate_limit: bool = True  # 動態請求頻率控制
    
    # 監控配置
    enable_performance_monitor: bool = True  # 啟用性能監控
    progress_update_interval: float = 1.0  # 進度更新間隔（秒）


@dataclass
class EnhancedBatchProgress(BatchProgress):
    """增強版批量進度"""
    # 並行處理統計
    active_workers: int = 0
    parallel_efficiency: float = 0.0
    
    # 增量更新統計
    cache_hits: int = 0
    incremental_updates: int = 0
    
    # 性能統計
    avg_processing_time: float = 0.0
    records_per_second: float = 0.0
    estimated_completion: Optional[datetime] = None


class EnhancedBatchStockUpdater(BatchStockUpdater):
    """增強版批量股票數據更新器"""
    
    def __init__(self, db_path: str = 'sqlite:///data/enhanced_stock_database.db',
                 config: Optional[EnhancedBatchConfig] = None):
        """
        初始化增強版批量更新器
        
        Args:
            db_path: 資料庫路徑
            config: 增強版配置
        """
        # 初始化基類
        super().__init__(db_path)
        
        # 設置增強版配置
        self.enhanced_config = config or EnhancedBatchConfig()
        
        # 創建增強版爬取器
        crawler_config = CrawlerConfig(
            max_workers=self.enhanced_config.max_workers,
            enable_incremental=self.enhanced_config.enable_incremental,
            data_freshness_hours=self.enhanced_config.data_freshness_hours
        )
        self.enhanced_crawler = EnhancedRealDataCrawler(db_path=db_path, config=crawler_config)
        
        # 並行處理狀態
        self._worker_stats = {}
        self._stats_lock = threading.Lock()
        self._processing_times = []
        
        # 增強版進度
        self.enhanced_progress = None
        
        logger.info(f"增強版批量更新器初始化完成 - 並行度: {self.enhanced_config.max_workers}")
    
    def update_all_stocks_enhanced(self, start_date: date, end_date: date,
                                 config: Optional[EnhancedBatchConfig] = None,
                                 stock_list: Optional[List] = None) -> Dict:
        """
        增強版批量更新所有股票數據
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            config: 增強版配置
            stock_list: 自定義股票清單（用於測試模式）
            
        Returns:
            Dict: 更新結果統計
        """
        try:
            # 使用提供的配置或默認配置
            if config:
                self.enhanced_config = config
            
            # 如果提供了自定義股票清單（測試模式），強制重置進度
            if stock_list is not None:
                self.progress = None
                self.enhanced_progress = None
                logger.info(f"🧪 測試模式啟用：將更新 {len(stock_list)} 個股票")
            
            # 獲取股票清單
            if stock_list is not None:
                stocks = stock_list
                logger.info(f"🧪 使用測試模式股票清單: {len(stocks)} 個股票")
            else:
                stocks = self.stock_manager.get_all_stocks()
                if not stocks:
                    self.stock_manager.update_stock_list()
                    stocks = self.stock_manager.get_all_stocks()
                if not stocks:
                    raise Exception("無法獲取股票清單")
            
            # 初始化增強版進度
            self.enhanced_progress = EnhancedBatchProgress(
                total_stocks=len(stocks),
                completed_stocks=0,
                failed_stocks=0,
                current_stock="",
                status=BatchStatus.RUNNING,
                start_time=datetime.now(),
                total_batches=1,  # 並行處理不需要批次概念
                active_workers=0,
                cache_hits=0,
                incremental_updates=0
            )
            
            mode_text = "測試模式" if stock_list is not None else "正式模式"
            logger.info(f"🚀 開始增強版批量更新 {len(stocks)} 個股票 ({mode_text})")
            
            # 執行並行更新
            if self.enhanced_config.enable_parallel and len(stocks) > 1:
                result = self._update_stocks_parallel(stocks, start_date, end_date)
            else:
                result = self._update_stocks_sequential(stocks, start_date, end_date)
            
            # 完成統計
            self.enhanced_progress.status = BatchStatus.COMPLETED
            self.enhanced_progress.end_time = datetime.now()
            
            # 獲取性能報告
            performance_report = self.enhanced_crawler.get_performance_report()
            
            # 合併結果
            final_result = {
                **result,
                'performance': performance_report,
                'mode': mode_text,
                'parallel_enabled': self.enhanced_config.enable_parallel,
                'incremental_enabled': self.enhanced_config.enable_incremental
            }
            
            logger.info(f"✅ 增強版批量更新完成: {final_result}")
            return final_result
            
        except Exception as e:
            logger.error(f"❌ 增強版批量更新失敗: {e}")
            if self.enhanced_progress:
                self.enhanced_progress.status = BatchStatus.FAILED
            return {
                'status': 'failed',
                'error': str(e),
                'completed_stocks': self.enhanced_progress.completed_stocks if self.enhanced_progress else 0,
                'failed_stocks': self.enhanced_progress.failed_stocks if self.enhanced_progress else 0
            }
    
    def _update_stocks_parallel(self, stocks: List, start_date: date, end_date: date) -> Dict:
        """
        並行更新股票數據

        Args:
            stocks: 股票清單
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            更新結果統計
        """
        logger.info(f"🔄 啟動並行更新模式 - {self.enhanced_config.max_workers} 個線程")

        completed_stocks = 0
        failed_stocks = 0
        total_records = 0
        failed_symbols = []

        # 統計快取命中
        total_cache_hits = 0
        total_requests = 0

        # 使用線程池並行處理
        with ThreadPoolExecutor(max_workers=self.enhanced_config.max_workers) as executor:
            # 提交所有任務
            future_to_stock = {
                executor.submit(self._update_single_stock_enhanced, stock, start_date, end_date): stock
                for stock in stocks
            }

            # 更新活躍線程數
            with self._stats_lock:
                self.enhanced_progress.active_workers = len(future_to_stock)

            # 收集結果
            for future in as_completed(future_to_stock):
                stock = future_to_stock[future]
                symbol = stock.symbol if hasattr(stock, 'symbol') else str(stock)

                try:
                    start_time = time.time()
                    success, records, is_cache_hit = future.result()
                    processing_time = time.time() - start_time

                    # 更新統計
                    with self._stats_lock:
                        total_requests += 1
                        if is_cache_hit:
                            total_cache_hits += 1
                            self.enhanced_progress.cache_hits += 1

                        if success:
                            completed_stocks += 1
                            total_records += records
                            self.enhanced_progress.completed_stocks = completed_stocks
                        else:
                            failed_stocks += 1
                            failed_symbols.append(symbol)
                            self.enhanced_progress.failed_stocks = failed_stocks

                        # 記錄處理時間
                        self._processing_times.append(processing_time)
                        if len(self._processing_times) > 100:  # 保持最近100個記錄
                            self._processing_times.pop(0)
                        
                        # 更新進度信息
                        self.enhanced_progress.current_stock = symbol
                        self.enhanced_progress.avg_processing_time = sum(self._processing_times) / len(self._processing_times)
                        
                        # 計算預估完成時間
                        remaining_stocks = len(stocks) - completed_stocks - failed_stocks
                        if remaining_stocks > 0 and self.enhanced_progress.avg_processing_time > 0:
                            estimated_seconds = remaining_stocks * self.enhanced_progress.avg_processing_time / self.enhanced_config.max_workers
                            self.enhanced_progress.estimated_completion = datetime.now() + timedelta(seconds=estimated_seconds)
                    
                    # 調用進度回調
                    self._notify_progress()
                    
                    status = "✅" if success else "❌"
                    logger.info(f"{status} {symbol}: {records} 筆記錄 ({processing_time:.2f}s)")
                    
                except Exception as e:
                    failed_stocks += 1
                    failed_symbols.append(symbol)
                    logger.error(f"❌ 處理 {symbol} 時發生錯誤: {e}")
                    
                    with self._stats_lock:
                        self.enhanced_progress.failed_stocks = failed_stocks
                    
                    self._notify_progress()
        
        # 計算成功率和快取命中率
        total_processed = completed_stocks + failed_stocks
        success_rate = completed_stocks / total_processed if total_processed > 0 else 0
        cache_hit_rate = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'status': 'completed',
            'total_stocks': len(stocks),
            'completed_stocks': completed_stocks,
            'failed_stocks': failed_stocks,
            'success_rate': success_rate,
            'total_records': total_records,
            'failed_symbols': failed_symbols,
            'processing_mode': 'parallel',
            'cache_hits': total_cache_hits,
            'cache_hit_rate': cache_hit_rate
        }
    
    def _update_stocks_sequential(self, stocks: List, start_date: date, end_date: date) -> Dict:
        """
        序列更新股票數據（向後兼容）
        
        Args:
            stocks: 股票清單
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            更新結果統計
        """
        logger.info("🔄 使用序列更新模式")
        
        completed_stocks = 0
        failed_stocks = 0
        total_records = 0
        failed_symbols = []
        
        for i, stock in enumerate(stocks):
            symbol = stock.symbol if hasattr(stock, 'symbol') else str(stock)
            
            try:
                start_time = time.time()
                success, records = self._update_single_stock_enhanced(stock, start_date, end_date)
                processing_time = time.time() - start_time
                
                if success:
                    completed_stocks += 1
                    total_records += records
                else:
                    failed_stocks += 1
                    failed_symbols.append(symbol)
                
                # 更新進度
                self.enhanced_progress.completed_stocks = completed_stocks
                self.enhanced_progress.failed_stocks = failed_stocks
                self.enhanced_progress.current_stock = symbol
                
                # 記錄處理時間
                self._processing_times.append(processing_time)
                if len(self._processing_times) > 50:
                    self._processing_times.pop(0)
                
                self.enhanced_progress.avg_processing_time = sum(self._processing_times) / len(self._processing_times)
                
                self._notify_progress()
                
                status = "✅" if success else "❌"
                logger.info(f"{status} {symbol}: {records} 筆記錄 ({processing_time:.2f}s)")
                
            except Exception as e:
                failed_stocks += 1
                failed_symbols.append(symbol)
                logger.error(f"❌ 處理 {symbol} 時發生錯誤: {e}")
        
        # 計算成功率
        total_processed = completed_stocks + failed_stocks
        success_rate = completed_stocks / total_processed if total_processed > 0 else 0
        
        return {
            'status': 'completed',
            'total_stocks': len(stocks),
            'completed_stocks': completed_stocks,
            'failed_stocks': failed_stocks,
            'success_rate': success_rate,
            'total_records': total_records,
            'failed_symbols': failed_symbols,
            'processing_mode': 'sequential'
        }
    
    def _update_single_stock_enhanced(self, stock, start_date: date, end_date: date) -> tuple:
        """
        增強版單一股票更新

        Args:
            stock: 股票信息
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            (是否成功, 記錄數, 是否快取命中)
        """
        symbol = stock.symbol if hasattr(stock, 'symbol') else str(stock)

        for attempt in range(self.enhanced_config.max_retries):
            try:
                # 記錄爬取前的統計
                initial_cache_hits = self.enhanced_crawler.performance_stats.cache_hits

                # 使用增強版爬取器
                df = self.enhanced_crawler.crawl_stock_data_range_enhanced(symbol, start_date, end_date)

                # 檢查是否有快取命中
                final_cache_hits = self.enhanced_crawler.performance_stats.cache_hits
                is_cache_hit = final_cache_hits > initial_cache_hits

                if df is not None and not df.empty:
                    # 保存數據
                    self.enhanced_crawler.save_to_database(df)
                    return True, len(df), is_cache_hit
                else:
                    raise Exception("爬取結果為空")

            except Exception as e:
                if attempt < self.enhanced_config.max_retries - 1:
                    time.sleep(self.enhanced_config.retry_delay)
                else:
                    logger.warning(f"❌ {symbol} 更新失敗: {e}")

        return False, 0, False
    
    def _notify_progress(self):
        """通知進度更新"""
        if self.enhanced_progress:
            # 計算並行效率
            if self.enhanced_progress.total_stocks > 0:
                self.enhanced_progress.parallel_efficiency = (
                    self.enhanced_progress.completed_stocks / self.enhanced_progress.total_stocks
                )
            
            # 計算處理速度
            if self.enhanced_progress.start_time:
                elapsed = (datetime.now() - self.enhanced_progress.start_time).total_seconds()
                if elapsed > 0:
                    self.enhanced_progress.records_per_second = (
                        self.enhanced_crawler.performance_stats.total_records / elapsed
                    )
            
            # 調用所有回調
            for callback in self.progress_callbacks:
                try:
                    callback(self.enhanced_progress)
                except Exception as e:
                    logger.error(f"進度回調錯誤: {e}")
    
    def get_enhanced_progress(self) -> Optional[EnhancedBatchProgress]:
        """獲取增強版進度信息"""
        return self.enhanced_progress
    
    # 向後兼容性方法
    def update_all_stocks(self, year: int = None, month: int = None,
                         config: Optional[BatchConfig] = None,
                         resume: bool = False,
                         stock_list: Optional[List] = None,
                         start_date: Optional[date] = None,
                         end_date: Optional[date] = None) -> Dict:
        """
        向後兼容的批量更新方法
        
        自動檢測是否使用增強版功能
        """
        # 參數處理邏輯（與原版相同）
        if start_date and end_date:
            if start_date > end_date:
                raise ValueError("開始日期不能晚於結束日期")
            logger.info(f"📅 使用日期範圍模式: {start_date} 至 {end_date}")
        elif year and month:
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
            logger.info(f"📅 使用月份模式: {year}-{month:02d}")
        else:
            raise ValueError("必須提供 start_date/end_date 或 year/month 參數")
        
        # 如果啟用了增強功能，使用增強版方法
        if self.enhanced_config.enable_parallel or self.enhanced_config.enable_incremental:
            enhanced_config = self.enhanced_config
            if config:
                # 將舊配置轉換為增強版配置
                enhanced_config.batch_size = config.batch_size
                enhanced_config.request_delay = config.request_delay
                enhanced_config.max_retries = config.max_retries
                enhanced_config.retry_delay = config.retry_delay
            
            return self.update_all_stocks_enhanced(start_date, end_date, enhanced_config, stock_list)
        else:
            # 使用原版方法
            return super().update_all_stocks(year, month, config, resume, stock_list, start_date, end_date)


# 工廠函數
def create_enhanced_updater(enable_parallel: bool = True, max_workers: int = 4,
                          enable_incremental: bool = True) -> BatchStockUpdater:
    """
    創建增強版更新器的工廠函數
    
    Args:
        enable_parallel: 是否啟用並行處理
        max_workers: 最大並行線程數
        enable_incremental: 是否啟用增量更新
        
    Returns:
        更新器實例
    """
    if enable_parallel or enable_incremental:
        config = EnhancedBatchConfig(
            enable_parallel=enable_parallel,
            max_workers=max_workers,
            enable_incremental=enable_incremental
        )
        return EnhancedBatchStockUpdater(config=config)
    else:
        return BatchStockUpdater()


if __name__ == "__main__":
    # 測試增強版更新器
    logging.basicConfig(level=logging.INFO)
    
    config = EnhancedBatchConfig(
        max_workers=3,
        enable_parallel=True,
        enable_incremental=True
    )
    
    updater = EnhancedBatchStockUpdater(config=config)
    
    # 設置進度回調
    def progress_callback(progress):
        print(f"進度: {progress.completed_stocks}/{progress.total_stocks} "
              f"({progress.parallel_efficiency*100:.1f}%) - {progress.current_stock}")
    
    updater.add_progress_callback(progress_callback)
    
    # 測試日期範圍
    start_date = date(2025, 7, 22)
    end_date = date(2025, 7, 29)
    
    print(f"開始測試增強版批量更新 ({start_date} 至 {end_date})")
    
    # 執行更新（測試模式）
    result = updater.update_all_stocks_enhanced(start_date, end_date)
    print(f"更新結果: {result}")
