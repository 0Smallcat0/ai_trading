"""
訊號處理器模組

此模組負責將策略產生的交易訊號轉換為可執行的訂單參數，包括：
- 訊號解析和驗證
- 訊號類型轉換
- 訂單類型選擇
- 訊號過濾和去重
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from .models import (
    ExecutionOrder,
    SignalData,
    SignalType,
    TradingSignal,
    ExecutionMode,
)

logger = logging.getLogger(__name__)


class SignalProcessor:
    """訊號處理器
    
    負責處理和轉換策略訊號為執行訂單。
    
    Attributes:
        signal_filters: 訊號過濾器列表
        order_type_mapping: 訊號到訂單類型的映射
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化訊號處理器
        
        Args:
            config: 配置參數
        """
        self.config = config or {}
        self.signal_filters = self.config.get("signal_filters", [])
        self.order_type_mapping = self._init_order_type_mapping()
        self._processed_signals = set()  # 用於去重
        
        logger.info("訊號處理器初始化完成")
    
    def _init_order_type_mapping(self) -> Dict[SignalType, str]:
        """初始化訊號到訂單類型的映射
        
        Returns:
            Dict[SignalType, str]: 映射字典
        """
        default_mapping = {
            SignalType.BUY: "market",
            SignalType.SELL: "market", 
            SignalType.HOLD: None,
            SignalType.CLOSE_LONG: "market",
            SignalType.CLOSE_SHORT: "market",
        }
        
        # 允許配置覆蓋預設映射
        custom_mapping = self.config.get("order_type_mapping", {})
        default_mapping.update(custom_mapping)
        
        return default_mapping
    
    def process_signal(self, signal_data: SignalData) -> Optional[ExecutionOrder]:
        """處理單個交易訊號
        
        Args:
            signal_data: 交易訊號數據
            
        Returns:
            Optional[ExecutionOrder]: 轉換後的執行訂單，如果訊號無效則返回 None
            
        Raises:
            ValueError: 當訊號數據格式不正確時
        """
        try:
            # 標準化訊號數據
            signal = self._normalize_signal(signal_data)
            
            # 驗證訊號
            if not self._validate_signal(signal):
                logger.warning("訊號驗證失敗: %s", signal)
                return None
            
            # 檢查是否已處理過
            signal_hash = self._generate_signal_hash(signal)
            if signal_hash in self._processed_signals:
                logger.debug("訊號已處理過，跳過: %s", signal_hash)
                return None
            
            # 應用過濾器
            if not self._apply_filters(signal):
                logger.debug("訊號被過濾器排除: %s", signal)
                return None
            
            # 轉換為執行訂單
            order = self._convert_to_order(signal)
            
            # 記錄已處理的訊號
            self._processed_signals.add(signal_hash)
            
            logger.info("訊號處理完成: %s -> %s", signal.symbol, order.order_id)
            return order
            
        except Exception as e:
            logger.error("處理訊號時發生錯誤: %s", e, exc_info=True)
            return None
    
    def process_signals_batch(self, signals: List[SignalData]) -> List[ExecutionOrder]:
        """批量處理交易訊號
        
        Args:
            signals: 交易訊號列表
            
        Returns:
            List[ExecutionOrder]: 轉換後的執行訂單列表
        """
        orders = []
        
        for signal_data in signals:
            order = self.process_signal(signal_data)
            if order:
                orders.append(order)
        
        logger.info("批量處理完成: %d 個訊號 -> %d 個訂單", len(signals), len(orders))
        return orders
    
    def _normalize_signal(self, signal_data: SignalData) -> TradingSignal:
        """標準化訊號數據
        
        Args:
            signal_data: 原始訊號數據
            
        Returns:
            TradingSignal: 標準化後的訊號
            
        Raises:
            ValueError: 當數據格式不正確時
        """
        if isinstance(signal_data, TradingSignal):
            return signal_data
        
        if isinstance(signal_data, dict):
            # 從字典創建 TradingSignal
            required_fields = ["symbol", "signal_type", "confidence"]
            for field in required_fields:
                if field not in signal_data:
                    raise ValueError(f"缺少必要欄位: {field}")
            
            # 處理訊號類型
            signal_type = signal_data["signal_type"]
            if isinstance(signal_type, str):
                signal_type = SignalType(signal_type.lower())
            
            return TradingSignal(
                symbol=signal_data["symbol"],
                signal_type=signal_type,
                confidence=signal_data["confidence"],
                timestamp=signal_data.get("timestamp", datetime.now()),
                price=signal_data.get("price"),
                quantity=signal_data.get("quantity"),
                strategy_name=signal_data.get("strategy_name"),
                metadata=signal_data.get("metadata", {}),
            )
        
        raise ValueError(f"不支援的訊號數據類型: {type(signal_data)}")
    
    def _validate_signal(self, signal: TradingSignal) -> bool:
        """驗證訊號有效性
        
        Args:
            signal: 交易訊號
            
        Returns:
            bool: 是否有效
        """
        # 基本驗證
        if not signal.symbol:
            logger.warning("訊號缺少股票代碼")
            return False
        
        if signal.signal_type == SignalType.HOLD:
            logger.debug("持有訊號，不需要執行")
            return False
        
        if signal.confidence < self.config.get("min_confidence", 0.5):
            logger.debug("訊號信心度過低: %f", signal.confidence)
            return False
        
        return True
    
    def _apply_filters(self, signal: TradingSignal) -> bool:
        """應用訊號過濾器
        
        Args:
            signal: 交易訊號
            
        Returns:
            bool: 是否通過過濾
        """
        for filter_func in self.signal_filters:
            if not filter_func(signal):
                return False
        return True
    
    def _convert_to_order(self, signal: TradingSignal) -> ExecutionOrder:
        """將訊號轉換為執行訂單
        
        Args:
            signal: 交易訊號
            
        Returns:
            ExecutionOrder: 執行訂單
        """
        order_id = str(uuid.uuid4())
        
        # 確定交易動作
        action = self._determine_action(signal.signal_type)
        
        # 確定訂單類型
        order_type = self.order_type_mapping.get(signal.signal_type, "market")
        
        # 確定執行模式
        execution_mode = self._determine_execution_mode(signal)
        
        return ExecutionOrder(
            order_id=order_id,
            symbol=signal.symbol,
            action=action,
            quantity=signal.quantity or 0,  # 數量將由部位管理器計算
            order_type=order_type,
            price=signal.price,
            execution_mode=execution_mode,
            signal_id=self._generate_signal_hash(signal),
            strategy_name=signal.strategy_name,
            risk_params=signal.metadata,
        )
    
    def _determine_action(self, signal_type: SignalType) -> str:
        """確定交易動作
        
        Args:
            signal_type: 訊號類型
            
        Returns:
            str: 交易動作
        """
        action_mapping = {
            SignalType.BUY: "buy",
            SignalType.SELL: "sell",
            SignalType.CLOSE_LONG: "sell",
            SignalType.CLOSE_SHORT: "buy",
        }
        return action_mapping.get(signal_type, "buy")
    
    def _determine_execution_mode(self, signal: TradingSignal) -> ExecutionMode:
        """確定執行模式
        
        Args:
            signal: 交易訊號
            
        Returns:
            ExecutionMode: 執行模式
        """
        # 根據訊號的元數據或配置確定執行模式
        mode = signal.metadata.get("execution_mode", "immediate")
        
        try:
            return ExecutionMode(mode)
        except ValueError:
            logger.warning("未知的執行模式: %s，使用預設模式", mode)
            return ExecutionMode.IMMEDIATE
    
    def _generate_signal_hash(self, signal: TradingSignal) -> str:
        """生成訊號雜湊值用於去重
        
        Args:
            signal: 交易訊號
            
        Returns:
            str: 雜湊值
        """
        # 使用關鍵欄位生成雜湊
        key_data = f"{signal.symbol}_{signal.signal_type.value}_{signal.timestamp.isoformat()}"
        return str(hash(key_data))
    
    def clear_processed_signals(self):
        """清除已處理訊號記錄"""
        self._processed_signals.clear()
        logger.info("已清除處理記錄")
    
    def get_processed_count(self) -> int:
        """獲取已處理訊號數量
        
        Returns:
            int: 已處理訊號數量
        """
        return len(self._processed_signals)
