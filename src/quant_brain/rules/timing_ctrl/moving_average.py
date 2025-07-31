# -*- coding: utf-8 -*-
"""
移動平均線時機控制模組

提供雙移動平均線交叉策略的基本實現。
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def double_ma_timing(data: pd.DataFrame, 
                    short_window: int = 5, 
                    long_window: int = 20,
                    **kwargs) -> Dict[str, Any]:
    """
    雙移動平均線交叉策略
    
    Args:
        data: 股價數據，包含 'close' 欄位
        short_window: 短期移動平均線窗口
        long_window: 長期移動平均線窗口
        **kwargs: 其他參數
    
    Returns:
        包含交易信號的字典
    """
    try:
        if data.empty or 'close' not in data.columns:
            logger.warning("數據為空或缺少 'close' 欄位")
            return {
                'signal': 0,
                'buy_signal': 0,
                'sell_signal': 0,
                'confidence': 0.0,
                'reasoning': "數據不足"
            }
        
        # 計算移動平均線
        data = data.copy()
        data[f'ma_{short_window}'] = data['close'].rolling(window=short_window).mean()
        data[f'ma_{long_window}'] = data['close'].rolling(window=long_window).mean()
        
        # 獲取最新的移動平均線值
        latest_short_ma = data[f'ma_{short_window}'].iloc[-1]
        latest_long_ma = data[f'ma_{long_window}'].iloc[-1]
        
        # 檢查是否有足夠的數據
        if pd.isna(latest_short_ma) or pd.isna(latest_long_ma):
            logger.warning("移動平均線計算結果為 NaN")
            return {
                'signal': 0,
                'buy_signal': 0,
                'sell_signal': 0,
                'confidence': 0.0,
                'reasoning': "移動平均線計算失敗"
            }
        
        # 生成交易信號
        if latest_short_ma > latest_long_ma:
            # 短期均線在長期均線之上，買入信號
            signal = 1
            buy_signal = 1
            sell_signal = 0
            confidence = min(abs(latest_short_ma - latest_long_ma) / latest_long_ma, 1.0)
            reasoning = f"短期均線({latest_short_ma:.2f})高於長期均線({latest_long_ma:.2f})，產生買入信號"
        elif latest_short_ma < latest_long_ma:
            # 短期均線在長期均線之下，賣出信號
            signal = -1
            buy_signal = 0
            sell_signal = 1
            confidence = min(abs(latest_long_ma - latest_short_ma) / latest_long_ma, 1.0)
            reasoning = f"短期均線({latest_short_ma:.2f})低於長期均線({latest_long_ma:.2f})，產生賣出信號"
        else:
            # 均線相等，觀望
            signal = 0
            buy_signal = 0
            sell_signal = 0
            confidence = 0.0
            reasoning = "短期均線與長期均線相等，保持觀望"
        
        result = {
            'signal': signal,
            'buy_signal': buy_signal,
            'sell_signal': sell_signal,
            'confidence': confidence,
            'reasoning': reasoning,
            'short_ma': latest_short_ma,
            'long_ma': latest_long_ma,
            'short_window': short_window,
            'long_window': long_window
        }
        
        logger.info(f"雙移動平均線策略執行完成: {reasoning}")
        return result
        
    except Exception as e:
        logger.error(f"雙移動平均線策略執行失敗: {e}")
        return {
            'signal': 0,
            'buy_signal': 0,
            'sell_signal': 0,
            'confidence': 0.0,
            'reasoning': f"策略執行失敗: {str(e)}"
        }
