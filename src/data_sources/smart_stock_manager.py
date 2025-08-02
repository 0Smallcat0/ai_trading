"""
智能股票管理器
實現動態問題股票檢測、狀態追蹤和智能恢復機制
"""

import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)

@dataclass
class StockStatus:
    """股票狀態"""
    symbol: str
    status: str  # healthy, problematic, recovering, unknown
    reason: str = ""
    failure_count: int = 0
    success_count: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_check: Optional[datetime] = None
    retry_after: Optional[datetime] = None
    avg_response_time: float = 0.0
    failure_rate: float = 0.0
    confidence_score: float = 0.0
    
    def to_dict(self):
        """轉換為字典"""
        return {
            'symbol': self.symbol,
            'status': self.status,
            'reason': self.reason,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_success': self.last_success.isoformat() if self.last_success else None,
            'last_failure': self.last_failure.isoformat() if self.last_failure else None,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'retry_after': self.retry_after.isoformat() if self.retry_after else None,
            'avg_response_time': self.avg_response_time,
            'failure_rate': self.failure_rate,
            'confidence_score': self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        """從字典創建"""
        return cls(
            symbol=data['symbol'],
            status=data['status'],
            reason=data.get('reason', ''),
            failure_count=data.get('failure_count', 0),
            success_count=data.get('success_count', 0),
            last_success=datetime.fromisoformat(data['last_success']) if data.get('last_success') else None,
            last_failure=datetime.fromisoformat(data['last_failure']) if data.get('last_failure') else None,
            last_check=datetime.fromisoformat(data['last_check']) if data.get('last_check') else None,
            retry_after=datetime.fromisoformat(data['retry_after']) if data.get('retry_after') else None,
            avg_response_time=data.get('avg_response_time', 0.0),
            failure_rate=data.get('failure_rate', 0.0),
            confidence_score=data.get('confidence_score', 0.0)
        )

class SmartStockManager:
    """智能股票管理器"""
    
    def __init__(self, data_file: str = "data/smart_stock_status.json"):
        self.data_file = data_file
        self.stock_status = {}  # symbol -> StockStatus
        self.response_times = defaultdict(list)  # symbol -> [response_times]
        
        # 配置參數
        self.failure_threshold = 0.6  # 失敗率閾值 (降低以便更容易檢測)
        self.min_attempts = 3  # 最少嘗試次數
        self.confidence_threshold = 0.7  # 置信度閾值 (降低以便更容易達到)
        self.recovery_check_interval = 5  # 恢復檢查間隔 (秒) - 測試用短間隔
        self.max_response_time_history = 50  # 響應時間歷史記錄數量
        
        # 重試策略
        self.retry_intervals = {
            'HTTP 404': timedelta(days=7),
            'YFTzMissingError': timedelta(days=3),
            'API問題': timedelta(days=1),
            'timeout': timedelta(hours=6),
            'default': timedelta(hours=12)
        }
        
        # 監控線程
        self.monitoring = False
        self.monitor_thread = None
        
        # 載入數據
        self.load_stock_status()
        
        logger.info("智能股票管理器初始化完成")
    
    def load_stock_status(self):
        """載入股票狀態"""
        try:
            if Path(self.data_file).exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for symbol, status_data in data.items():
                    self.stock_status[symbol] = StockStatus.from_dict(status_data)
                
                logger.info(f"載入 {len(self.stock_status)} 個股票狀態")
            else:
                logger.info("股票狀態文件不存在，使用空狀態")
                
        except Exception as e:
            logger.error(f"載入股票狀態失敗: {e}")
            self.stock_status = {}
    
    def save_stock_status(self):
        """保存股票狀態"""
        try:
            Path(self.data_file).parent.mkdir(exist_ok=True)
            
            data = {
                symbol: status.to_dict() 
                for symbol, status in self.stock_status.items()
            }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"保存 {len(self.stock_status)} 個股票狀態")
            
        except Exception as e:
            logger.error(f"保存股票狀態失敗: {e}")
    
    def record_download_attempt(self, symbol: str, success: bool, response_time: float = 0.0, error: str = ""):
        """記錄下載嘗試"""
        current_time = datetime.now()
        
        # 獲取或創建股票狀態
        if symbol not in self.stock_status:
            self.stock_status[symbol] = StockStatus(symbol=symbol, status='unknown')
        
        status = self.stock_status[symbol]
        status.last_check = current_time
        
        if success:
            status.success_count += 1
            status.last_success = current_time
            
            # 記錄響應時間
            if response_time > 0:
                self.response_times[symbol].append(response_time)
                if len(self.response_times[symbol]) > self.max_response_time_history:
                    self.response_times[symbol].pop(0)
                
                status.avg_response_time = statistics.mean(self.response_times[symbol])
        else:
            status.failure_count += 1
            status.last_failure = current_time
            
            # 記錄錯誤原因
            if error:
                status.reason = error
        
        # 更新統計
        self._update_stock_statistics(status)
        
        # 動態調整狀態
        self._update_stock_status(status)
        
        # 保存狀態
        self.save_stock_status()
        
        logger.debug(f"記錄 {symbol} 嘗試: {'成功' if success else '失敗'} ({response_time:.2f}s)")
    
    def _update_stock_statistics(self, status: StockStatus):
        """更新股票統計"""
        total_attempts = status.success_count + status.failure_count
        
        if total_attempts > 0:
            status.failure_rate = status.failure_count / total_attempts
            
            # 計算置信度分數
            # 基於嘗試次數、時間跨度、一致性等因素
            attempts_factor = min(total_attempts / 10, 1.0)  # 10次嘗試為滿分
            
            time_factor = 1.0
            if status.last_check and status.last_success:
                days_since_success = (status.last_check - status.last_success).days
                time_factor = max(0.1, 1.0 - days_since_success / 30)  # 30天衰減
            
            consistency_factor = 1.0 - abs(status.failure_rate - 0.5) * 2  # 一致性越高置信度越高
            
            status.confidence_score = (attempts_factor * 0.4 + time_factor * 0.3 + consistency_factor * 0.3)
    
    def _update_stock_status(self, status: StockStatus):
        """更新股票狀態"""
        total_attempts = status.success_count + status.failure_count
        
        # 需要足夠的嘗試次數才能做判斷
        if total_attempts < self.min_attempts:
            status.status = 'unknown'
            return
        
        # 基於失敗率和置信度判斷
        if status.failure_rate >= self.failure_threshold and status.confidence_score >= self.confidence_threshold:
            if status.status != 'problematic':
                status.status = 'problematic'
                # 設置重試時間
                retry_interval = self.retry_intervals.get(status.reason, self.retry_intervals['default'])
                status.retry_after = datetime.now() + retry_interval
                
                logger.info(f"股票 {status.symbol} 被標記為問題股票: {status.reason} (失敗率: {status.failure_rate:.1%})")
        
        elif status.failure_rate < 0.4 and status.confidence_score >= self.confidence_threshold:
            if status.status == 'problematic':
                status.status = 'recovering'
                logger.info(f"股票 {status.symbol} 進入恢復狀態 (失敗率: {status.failure_rate:.1%})")
            elif status.status in ['recovering', 'unknown']:
                status.status = 'healthy'
                status.retry_after = None
                logger.info(f"股票 {status.symbol} 標記為健康 (失敗率: {status.failure_rate:.1%})")
    
    def is_stock_problematic(self, symbol: str) -> bool:
        """動態檢測股票是否有問題"""
        if symbol not in self.stock_status:
            return False
        
        status = self.stock_status[symbol]
        
        # 檢查是否為已知問題股票
        if status.status == 'problematic':
            # 檢查是否到了重試時間
            if status.retry_after and datetime.now() < status.retry_after:
                return True
            else:
                # 到了重試時間，標記為恢復中
                status.status = 'recovering'
                self.save_stock_status()
                return False
        
        return False
    
    def should_skip_stock(self, symbol: str) -> Tuple[bool, str]:
        """判斷是否應該跳過股票"""
        if symbol not in self.stock_status:
            return False, ""
        
        status = self.stock_status[symbol]
        
        if status.status == 'problematic':
            if status.retry_after and datetime.now() < status.retry_after:
                remaining = status.retry_after - datetime.now()
                return True, f"問題股票，{remaining.days}天後重試 ({status.reason})"
        
        return False, ""
    
    def get_problematic_stocks(self) -> List[StockStatus]:
        """獲取問題股票列表"""
        return [
            status for status in self.stock_status.values()
            if status.status == 'problematic'
        ]
    
    def get_recovering_stocks(self) -> List[StockStatus]:
        """獲取恢復中股票列表"""
        return [
            status for status in self.stock_status.values()
            if status.status == 'recovering'
        ]
    
    def get_stocks_ready_for_retry(self) -> List[StockStatus]:
        """獲取準備重試的股票列表"""
        current_time = datetime.now()
        ready_stocks = []
        
        for status in self.stock_status.values():
            if (status.status == 'problematic' and 
                status.retry_after and 
                current_time >= status.retry_after):
                ready_stocks.append(status)
        
        return ready_stocks
    
    def start_monitoring(self):
        """啟動監控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("智能股票監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        logger.info("智能股票監控已停止")
    
    def _monitor_loop(self):
        """監控循環"""
        while self.monitoring:
            try:
                # 檢查準備重試的股票
                ready_stocks = self.get_stocks_ready_for_retry()
                
                if ready_stocks:
                    logger.info(f"發現 {len(ready_stocks)} 個股票準備重試")
                    
                    for status in ready_stocks:
                        status.status = 'recovering'
                        logger.info(f"股票 {status.symbol} 進入恢復檢查")
                    
                    self.save_stock_status()
                
                # 清理過期數據
                self._cleanup_old_data()
                
                time.sleep(self.recovery_check_interval)
                
            except Exception as e:
                logger.error(f"監控循環發生錯誤: {e}")
                time.sleep(60)
    
    def _cleanup_old_data(self):
        """清理過期數據"""
        current_time = datetime.now()
        cleanup_threshold = timedelta(days=90)  # 90天前的數據
        
        to_remove = []
        for symbol, status in self.stock_status.items():
            if (status.last_check and 
                current_time - status.last_check > cleanup_threshold and
                status.status not in ['problematic', 'recovering']):
                to_remove.append(symbol)
        
        for symbol in to_remove:
            del self.stock_status[symbol]
            if symbol in self.response_times:
                del self.response_times[symbol]
        
        if to_remove:
            logger.info(f"清理 {len(to_remove)} 個過期股票數據")
            self.save_stock_status()
    
    def get_statistics(self) -> Dict:
        """獲取統計信息"""
        total_stocks = len(self.stock_status)
        
        status_counts = defaultdict(int)
        for status in self.stock_status.values():
            status_counts[status.status] += 1
        
        # 計算平均指標
        failure_rates = [s.failure_rate for s in self.stock_status.values() if s.failure_rate > 0]
        avg_failure_rate = statistics.mean(failure_rates) if failure_rates else 0
        
        confidence_scores = [s.confidence_score for s in self.stock_status.values() if s.confidence_score > 0]
        avg_confidence = statistics.mean(confidence_scores) if confidence_scores else 0
        
        return {
            'total_stocks': total_stocks,
            'status_distribution': dict(status_counts),
            'avg_failure_rate': avg_failure_rate,
            'avg_confidence_score': avg_confidence,
            'ready_for_retry': len(self.get_stocks_ready_for_retry()),
            'monitoring_active': self.monitoring
        }
