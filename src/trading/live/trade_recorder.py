"""
實時交易記錄器

此模組提供實時交易記錄功能，包括：
- 交易執行記錄
- 即時更新交易狀態
- 交易歷史查詢
- 績效統計
"""

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    """交易狀態枚舉"""
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class TradeRecord:
    """交易記錄數據類"""
    trade_id: str
    symbol: str
    action: str  # buy/sell
    quantity: float
    price: float
    timestamp: datetime
    status: TradeStatus
    order_id: Optional[str] = None
    commission: float = 0.0
    tax: float = 0.0
    net_amount: float = 0.0
    slippage: float = 0.0
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeRecord':
        """從字典創建交易記錄"""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['status'] = TradeStatus(data['status'])
        return cls(**data)


class TradeRecorder:
    """實時交易記錄器"""
    
    def __init__(self, storage_path: str = "logs/trades.json"):
        """
        初始化交易記錄器
        
        Args:
            storage_path: 交易記錄存儲路徑
        """
        self.storage_path = storage_path
        self.trades: List[TradeRecord] = []
        self.callbacks: List[Callable] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        
        # 確保存儲目錄存在
        import os
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        # 載入歷史記錄
        self._load_trades()
    
    def start_recording(self):
        """開始記錄"""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._recording_loop, daemon=True)
            self._thread.start()
            logger.info("交易記錄器已啟動")
    
    def stop_recording(self):
        """停止記錄"""
        if self._running:
            self._running = False
            if self._thread:
                self._thread.join(timeout=5)
            logger.info("交易記錄器已停止")
    
    def record_trade(self, trade_data: Dict[str, Any]) -> str:
        """
        記錄交易
        
        Args:
            trade_data: 交易數據
            
        Returns:
            str: 交易記錄 ID
        """
        try:
            # 生成交易 ID
            trade_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # 創建交易記錄
            trade_record = TradeRecord(
                trade_id=trade_id,
                symbol=trade_data.get('symbol', ''),
                action=trade_data.get('action', ''),
                quantity=float(trade_data.get('quantity', 0)),
                price=float(trade_data.get('price', 0)),
                timestamp=datetime.now(),
                status=TradeStatus(trade_data.get('status', 'pending')),
                order_id=trade_data.get('order_id'),
                commission=float(trade_data.get('commission', 0)),
                tax=float(trade_data.get('tax', 0)),
                net_amount=float(trade_data.get('net_amount', 0)),
                slippage=float(trade_data.get('slippage', 0)),
                notes=trade_data.get('notes', '')
            )
            
            # 添加到記錄列表
            with self._lock:
                self.trades.append(trade_record)
            
            # 保存到文件
            self._save_trades()
            
            # 觸發回調
            self._trigger_callbacks('trade_recorded', trade_record)
            
            logger.info(f"交易記錄已創建: {trade_id}")
            return trade_id
            
        except Exception as e:
            logger.error(f"記錄交易失敗: {e}")
            raise
    
    def update_trade_status(self, trade_id: str, status: TradeStatus, 
                           additional_data: Optional[Dict[str, Any]] = None):
        """
        更新交易狀態
        
        Args:
            trade_id: 交易記錄 ID
            status: 新狀態
            additional_data: 額外數據
        """
        try:
            with self._lock:
                for trade in self.trades:
                    if trade.trade_id == trade_id:
                        trade.status = status
                        
                        # 更新額外數據
                        if additional_data:
                            for key, value in additional_data.items():
                                if hasattr(trade, key):
                                    setattr(trade, key, value)
                        
                        # 保存更新
                        self._save_trades()
                        
                        # 觸發回調
                        self._trigger_callbacks('trade_updated', trade)
                        
                        logger.info(f"交易狀態已更新: {trade_id} -> {status.value}")
                        return
                
                logger.warning(f"未找到交易記錄: {trade_id}")
                
        except Exception as e:
            logger.error(f"更新交易狀態失敗: {e}")
    
    def get_trades(self, symbol: Optional[str] = None, 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   status: Optional[TradeStatus] = None) -> List[TradeRecord]:
        """
        查詢交易記錄
        
        Args:
            symbol: 股票代號篩選
            start_date: 開始日期
            end_date: 結束日期
            status: 狀態篩選
            
        Returns:
            List[TradeRecord]: 符合條件的交易記錄
        """
        with self._lock:
            filtered_trades = self.trades.copy()
        
        # 應用篩選條件
        if symbol:
            filtered_trades = [t for t in filtered_trades if t.symbol == symbol]
        
        if start_date:
            filtered_trades = [t for t in filtered_trades if t.timestamp >= start_date]
        
        if end_date:
            filtered_trades = [t for t in filtered_trades if t.timestamp <= end_date]
        
        if status:
            filtered_trades = [t for t in filtered_trades if t.status == status]
        
        return sorted(filtered_trades, key=lambda x: x.timestamp, reverse=True)
    
    def get_trade_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        獲取交易統計
        
        Args:
            days: 統計天數
            
        Returns:
            Dict[str, Any]: 統計數據
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        trades = self.get_trades(start_date=start_date, end_date=end_date)
        executed_trades = [t for t in trades if t.status == TradeStatus.EXECUTED]
        
        if not executed_trades:
            return {
                'total_trades': 0,
                'executed_trades': 0,
                'total_volume': 0,
                'total_commission': 0,
                'success_rate': 0
            }
        
        total_volume = sum(t.quantity * t.price for t in executed_trades)
        total_commission = sum(t.commission for t in executed_trades)
        
        return {
            'total_trades': len(trades),
            'executed_trades': len(executed_trades),
            'total_volume': total_volume,
            'total_commission': total_commission,
            'success_rate': len(executed_trades) / len(trades) if trades else 0
        }
    
    def add_callback(self, callback: Callable):
        """添加回調函數"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """移除回調函數"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def _load_trades(self):
        """載入交易記錄"""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.trades = [TradeRecord.from_dict(trade_data) for trade_data in data]
            logger.info(f"載入 {len(self.trades)} 條交易記錄")
        except FileNotFoundError:
            logger.info("交易記錄文件不存在，創建新文件")
            self.trades = []
        except Exception as e:
            logger.error(f"載入交易記錄失敗: {e}")
            self.trades = []
    
    def _save_trades(self):
        """保存交易記錄"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                data = [trade.to_dict() for trade in self.trades]
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存交易記錄失敗: {e}")
    
    def _trigger_callbacks(self, event_type: str, trade_record: TradeRecord):
        """觸發回調函數"""
        for callback in self.callbacks:
            try:
                callback(event_type, trade_record)
            except Exception as e:
                logger.error(f"回調函數執行失敗: {e}")
    
    def _recording_loop(self):
        """記錄循環"""
        while self._running:
            try:
                # 定期保存記錄
                time.sleep(60)  # 每分鐘保存一次
                if self.trades:
                    self._save_trades()
            except Exception as e:
                logger.error(f"記錄循環錯誤: {e}")
