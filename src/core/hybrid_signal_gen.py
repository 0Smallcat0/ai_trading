# -*- coding: utf-8 -*-
"""
混合訊號產生模組

此模組提供 AI 模型與規則型策略的混合訊號生成功能，包括：
- AI 模型訊號與規則型訊號的組合
- 訊號衝突解決
- 訊號強度調整
- 訊號時機優化
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
import warnings

from src.config import LOG_LEVEL
from src.core.signal_gen import SignalGenerator
from src.core.model_integration import ModelManager

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class HybridSignalGenerator(SignalGenerator):
    """
    混合訊號產生器

    結合 AI 模型與規則型策略生成交易訊號。
    """

    def __init__(
        self,
        price_data=None,
        volume_data=None,
        financial_data=None,
        news_data=None,
        model_manager=None,
        ai_weight=0.6,
        rule_weight=0.4,
        conflict_resolution="ai_priority"
    ):
        """
        初始化混合訊號產生器

        Args:
            price_data (pandas.DataFrame, optional): 價格資料，索引為 (股票代號, 日期)
            volume_data (pandas.DataFrame, optional): 成交量資料，索引為 (股票代號, 日期)
            financial_data (pandas.DataFrame, optional): 財務資料，索引為 (股票代號, 日期)
            news_data (pandas.DataFrame, optional): 新聞資料，索引為 (股票代號, 日期)
            model_manager (ModelManager, optional): 模型管理器，用於 AI 模型整合
            ai_weight (float): AI 模型訊號權重
            rule_weight (float): 規則型策略訊號權重
            conflict_resolution (str): 衝突解決方式，可選 'ai_priority', 'rule_priority', 'weighted'
        """
        super().__init__(price_data, volume_data, financial_data, news_data, model_manager)
        
        self.ai_weight = ai_weight
        self.rule_weight = rule_weight
        self.conflict_resolution = conflict_resolution
        
        # 初始化混合訊號
        self.hybrid_signals = {}

    def generate_hybrid_signals(
        self,
        model_name: str,
        rule_strategies: List[str] = None,
        version: Optional[str] = None,
        signal_threshold: float = 0.5
    ) -> pd.DataFrame:
        """
        生成混合訊號

        Args:
            model_name (str): 模型名稱
            rule_strategies (List[str]): 規則型策略列表，如果為 None，則使用所有可用策略
            version (Optional[str]): 模型版本，如果為 None，則使用最新版本
            signal_threshold (float): 訊號閾值

        Returns:
            pd.DataFrame: 混合訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        # 生成 AI 模型訊號
        ai_signals = self.generate_ai_model_signals(model_name, version, signal_threshold)
        
        # 如果沒有指定規則型策略，使用所有基本策略
        if rule_strategies is None:
            rule_strategies = ["basic", "momentum", "reversion", "sentiment"]
        
        # 生成規則型策略訊號
        rule_signals = {}
        for strategy in rule_strategies:
            if strategy == "basic":
                rule_signals[strategy] = self.generate_basic()
            elif strategy == "momentum":
                rule_signals[strategy] = self.generate_momentum()
            elif strategy == "reversion":
                rule_signals[strategy] = self.generate_reversion()
            elif strategy == "sentiment":
                rule_signals[strategy] = self.generate_sentiment()
            elif strategy == "breakout":
                rule_signals[strategy] = self.generate_breakout_signals()
            elif strategy == "crossover":
                rule_signals[strategy] = self.generate_crossover_signals()
            elif strategy == "divergence":
                rule_signals[strategy] = self.generate_divergence_signals()
        
        # 合併規則型策略訊號
        combined_rule_signals = self.combine_signals({strategy: 1.0 / len(rule_strategies) for strategy in rule_strategies})
        
        # 生成混合訊號
        hybrid_signals = self._combine_ai_rule_signals(ai_signals, combined_rule_signals)
        
        # 儲存混合訊號
        self.hybrid_signals[f"hybrid_{model_name}"] = hybrid_signals
        
        return hybrid_signals

    def _combine_ai_rule_signals(
        self,
        ai_signals: pd.DataFrame,
        rule_signals: pd.DataFrame
    ) -> pd.DataFrame:
        """
        合併 AI 模型訊號與規則型策略訊號

        Args:
            ai_signals (pd.DataFrame): AI 模型訊號
            rule_signals (pd.DataFrame): 規則型策略訊號

        Returns:
            pd.DataFrame: 混合訊號
        """
        if ai_signals.empty or rule_signals.empty:
            logger.warning("AI 模型訊號或規則型策略訊號為空，無法合併")
            return ai_signals if not ai_signals.empty else rule_signals
        
        # 確保索引一致
        common_index = ai_signals.index.intersection(rule_signals.index)
        ai_signals = ai_signals.loc[common_index]
        rule_signals = rule_signals.loc[common_index]
        
        # 初始化混合訊號
        hybrid_signals = pd.DataFrame(index=common_index)
        hybrid_signals["signal"] = 0
        
        # 根據衝突解決方式合併訊號
        if self.conflict_resolution == "ai_priority":
            # AI 優先
            hybrid_signals["signal"] = ai_signals["signal"]
            # 只在 AI 訊號為 0 時使用規則型訊號
            hybrid_signals.loc[ai_signals["signal"] == 0, "signal"] = rule_signals.loc[ai_signals["signal"] == 0, "signal"]
        elif self.conflict_resolution == "rule_priority":
            # 規則型優先
            hybrid_signals["signal"] = rule_signals["signal"]
            # 只在規則型訊號為 0 時使用 AI 訊號
            hybrid_signals.loc[rule_signals["signal"] == 0, "signal"] = ai_signals.loc[rule_signals["signal"] == 0, "signal"]
        else:
            # 加權合併
            # 標準化權重
            total_weight = self.ai_weight + self.rule_weight
            ai_norm_weight = self.ai_weight / total_weight
            rule_norm_weight = self.rule_weight / total_weight
            
            # 加權合併
            hybrid_signals["signal"] = ai_signals["signal"] * ai_norm_weight + rule_signals["signal"] * rule_norm_weight
            
            # 標準化訊號
            hybrid_signals["signal"] = hybrid_signals["signal"].apply(
                lambda x: 1 if x > 0.5 else (-1 if x < -0.5 else 0)
            )
        
        return hybrid_signals

    def optimize_signal_timing(
        self,
        signals: pd.DataFrame,
        lookback_window: int = 5,
        confirmation_threshold: int = 3
    ) -> pd.DataFrame:
        """
        優化訊號時機

        Args:
            signals (pd.DataFrame): 訊號資料
            lookback_window (int): 回顧窗口大小
            confirmation_threshold (int): 確認閾值，需要多少個相同訊號才確認

        Returns:
            pd.DataFrame: 優化後的訊號資料
        """
        if signals.empty:
            return signals
        
        # 複製訊號
        optimized_signals = signals.copy()
        
        # 對每個股票分別處理
        for stock_id in signals.index.get_level_values(0).unique():
            stock_signals = signals.loc[stock_id]["signal"]
            
            # 使用滾動窗口計算訊號確認
            for i in range(lookback_window, len(stock_signals)):
                # 獲取窗口內的訊號
                window_signals = stock_signals.iloc[i-lookback_window:i]
                
                # 計算買入和賣出訊號的數量
                buy_count = (window_signals == 1).sum()
                sell_count = (window_signals == -1).sum()
                
                # 根據確認閾值生成訊號
                if buy_count >= confirmation_threshold:
                    optimized_signals.loc[(stock_id, stock_signals.index[i]), "signal"] = 1
                elif sell_count >= confirmation_threshold:
                    optimized_signals.loc[(stock_id, stock_signals.index[i]), "signal"] = -1
                else:
                    optimized_signals.loc[(stock_id, stock_signals.index[i]), "signal"] = 0
        
        return optimized_signals

    def adjust_signal_strength(
        self,
        signals: pd.DataFrame,
        price_data: pd.DataFrame = None,
        volume_data: pd.DataFrame = None,
        strength_factors: Dict[str, float] = None
    ) -> pd.DataFrame:
        """
        調整訊號強度

        Args:
            signals (pd.DataFrame): 訊號資料
            price_data (pd.DataFrame, optional): 價格資料
            volume_data (pd.DataFrame, optional): 成交量資料
            strength_factors (Dict[str, float], optional): 強度因子，如 {'price_trend': 0.3, 'volume': 0.2, 'volatility': 0.5}

        Returns:
            pd.DataFrame: 調整後的訊號資料
        """
        if signals.empty:
            return signals
        
        # 使用類的價格和成交量資料（如果沒有提供）
        price_data = price_data or self.price_data
        volume_data = volume_data or self.volume_data
        
        if price_data is None:
            logger.warning("缺少價格資料，無法調整訊號強度")
            return signals
        
        # 預設強度因子
        if strength_factors is None:
            strength_factors = {
                "price_trend": 0.4,  # 價格趨勢
                "volume": 0.3,       # 成交量
                "volatility": 0.3    # 波動率
            }
        
        # 複製訊號
        adjusted_signals = signals.copy()
        
        # 對每個股票分別處理
        for stock_id in signals.index.get_level_values(0).unique():
            stock_signals = signals.loc[stock_id]["signal"]
            stock_prices = price_data.loc[stock_id]["close"]
            
            # 計算價格趨勢因子
            price_ma_short = stock_prices.rolling(window=5).mean()
            price_ma_long = stock_prices.rolling(window=20).mean()
            price_trend = (price_ma_short / price_ma_long - 1) * 10  # 標準化
            price_trend = price_trend.clip(-1, 1)  # 限制在 [-1, 1] 範圍內
            
            # 計算成交量因子
            if volume_data is not None and stock_id in volume_data.index:
                stock_volume = volume_data.loc[stock_id]["volume"]
                volume_ma = stock_volume.rolling(window=20).mean()
                volume_ratio = stock_volume / volume_ma
                volume_factor = (volume_ratio - 1).clip(-1, 1)  # 限制在 [-1, 1] 範圍內
            else:
                volume_factor = pd.Series(0, index=stock_signals.index)
            
            # 計算波動率因子
            volatility = stock_prices.pct_change().rolling(window=20).std() * np.sqrt(252)  # 年化波動率
            volatility_factor = (volatility / volatility.mean() - 1).clip(-1, 1)  # 限制在 [-1, 1] 範圍內
            
            # 計算綜合強度因子
            strength = (
                price_trend * strength_factors.get("price_trend", 0) +
                volume_factor * strength_factors.get("volume", 0) +
                volatility_factor * strength_factors.get("volatility", 0)
            )
            
            # 調整訊號強度
            for i in range(len(stock_signals)):
                if stock_signals.iloc[i] != 0:
                    # 只調整非零訊號
                    signal_idx = stock_signals.index[i]
                    if signal_idx in strength.index:
                        # 訊號方向不變，但強度可能增強或減弱
                        direction = 1 if stock_signals.iloc[i] > 0 else -1
                        strength_value = strength.loc[signal_idx]
                        
                        # 如果強度因子與訊號方向一致，則增強訊號；否則減弱訊號
                        if (direction > 0 and strength_value > 0) or (direction < 0 and strength_value < 0):
                            # 訊號增強，但仍保持原方向
                            adjusted_signals.loc[(stock_id, signal_idx), "signal"] = direction
                        elif abs(strength_value) > 0.7:
                            # 強度因子很強且與訊號方向相反，可能需要反轉訊號
                            adjusted_signals.loc[(stock_id, signal_idx), "signal"] = 0
                        else:
                            # 保持原訊號但減弱
                            adjusted_signals.loc[(stock_id, signal_idx), "signal"] = direction
        
        return adjusted_signals

    def generate_all_hybrid_signals(
        self,
        ai_models: List[str] = None,
        rule_strategies: List[str] = None,
        optimize_timing: bool = True,
        adjust_strength: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        生成所有混合訊號

        Args:
            ai_models (List[str], optional): AI 模型列表，如果為 None，則使用所有可用模型
            rule_strategies (List[str], optional): 規則型策略列表，如果為 None，則使用所有基本策略
            optimize_timing (bool): 是否優化訊號時機
            adjust_strength (bool): 是否調整訊號強度

        Returns:
            Dict[str, pd.DataFrame]: 包含所有混合訊號的字典
        """
        # 如果沒有指定 AI 模型，使用所有可用模型
        if ai_models is None and self.model_manager is not None:
            ai_models = self.model_manager.get_all_models()
        
        # 如果沒有指定規則型策略，使用所有基本策略
        if rule_strategies is None:
            rule_strategies = ["basic", "momentum", "reversion", "sentiment"]
        
        # 生成混合訊號
        for model_name in ai_models:
            hybrid_signals = self.generate_hybrid_signals(model_name, rule_strategies)
            
            # 優化訊號時機
            if optimize_timing:
                hybrid_signals = self.optimize_signal_timing(hybrid_signals)
            
            # 調整訊號強度
            if adjust_strength:
                hybrid_signals = self.adjust_signal_strength(hybrid_signals)
            
            # 更新混合訊號
            self.hybrid_signals[f"hybrid_{model_name}"] = hybrid_signals
        
        return self.hybrid_signals
