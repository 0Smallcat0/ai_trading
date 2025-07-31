# -*- coding: utf-8 -*-
"""
套利交易代理模組

此模組實現基於統計套利的交易代理。

投資哲學：
- 尋找價格差異機會
- 市場中性策略
- 低風險、穩定收益
- 統計套利和配對交易

主要功能：
- 配對交易策略
- 統計套利檢測
- 協整關係分析
- 價差回歸交易
- 風險中性對沖
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from scipy import stats
from sklearn.linear_model import LinearRegression

from ..base import TradingAgent, AgentDecision, InvestmentStyle, RiskPreference

# 設定日誌
logger = logging.getLogger(__name__)


class ArbitrageTrader(TradingAgent):
    """
    套利交易代理。
    
    基於統計套利進行交易決策，包括：
    - 配對交易
    - 價差分析
    - 協整檢測
    - 均值回歸策略
    - 風險中性對沖
    
    Attributes:
        lookback_period (int): 回望期間
        correlation_threshold (float): 相關性閾值
        cointegration_threshold (float): 協整檢驗閾值
        spread_entry_threshold (float): 價差進入閾值
        spread_exit_threshold (float): 價差退出閾值
        max_spread_deviation (float): 最大價差偏離
        hedge_ratio_window (int): 對沖比率計算窗口
        rebalance_frequency (int): 再平衡頻率
    """
    
    def __init__(
        self,
        name: str = "ArbitrageTrader",
        lookback_period: int = 60,
        correlation_threshold: float = 0.7,
        cointegration_threshold: float = 0.05,
        spread_entry_threshold: float = 2.0,
        spread_exit_threshold: float = 0.5,
        max_spread_deviation: float = 3.0,
        hedge_ratio_window: int = 30,
        rebalance_frequency: int = 5,
        **parameters: Any
    ) -> None:
        """
        初始化套利交易代理。
        
        Args:
            name: 代理名稱
            lookback_period: 回望期間
            correlation_threshold: 相關性閾值
            cointegration_threshold: 協整檢驗p值閾值
            spread_entry_threshold: 價差進入閾值（標準差倍數）
            spread_exit_threshold: 價差退出閾值（標準差倍數）
            max_spread_deviation: 最大價差偏離（標準差倍數）
            hedge_ratio_window: 對沖比率計算窗口
            rebalance_frequency: 再平衡頻率（天數）
            **parameters: 其他策略參數
        """
        super().__init__(
            name=name,
            investment_style=InvestmentStyle.ARBITRAGE,
            risk_preference=RiskPreference.CONSERVATIVE,
            max_position_size=0.2,  # 套利交易可以使用較大倉位
            **parameters
        )
        
        # 套利交易參數
        self.lookback_period = lookback_period
        self.correlation_threshold = correlation_threshold
        self.cointegration_threshold = cointegration_threshold
        self.spread_entry_threshold = spread_entry_threshold
        self.spread_exit_threshold = spread_exit_threshold
        self.max_spread_deviation = max_spread_deviation
        self.hedge_ratio_window = hedge_ratio_window
        self.rebalance_frequency = rebalance_frequency
        
        # 配對交易追蹤
        self.current_pairs: Dict[str, Dict] = {}
        self.pair_relationships: Dict[str, Dict] = {}
        self.spread_history: Dict[str, List[float]] = {}
        
        logger.info(f"初始化套利交易代理: {name}")
    
    def make_decision(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """
        基於套利分析生成交易決策。
        
        Args:
            data: 市場數據，包含多個標的的價格數據
            market_context: 市場上下文信息
            
        Returns:
            AgentDecision: 交易決策
        """
        try:
            symbol = market_context.get('symbol', 'UNKNOWN') if market_context else 'UNKNOWN'
            pair_symbol = market_context.get('pair_symbol') if market_context else None
            
            # 檢查數據完整性
            if not self._validate_data(data, pair_symbol):
                return self._create_hold_decision(symbol, "數據不完整或缺少配對標的")
            
            # 如果沒有指定配對標的，尋找最佳配對
            if pair_symbol is None:
                pair_symbol = self._find_best_pair(symbol, data)
                if pair_symbol is None:
                    return self._create_hold_decision(symbol, "未找到合適的配對標的")
            
            # 分析配對關係
            pair_analysis = self._analyze_pair_relationship(symbol, pair_symbol, data)
            
            # 計算價差指標
            spread_analysis = self._analyze_spread(symbol, pair_symbol, data, pair_analysis)
            
            # 檢測套利機會
            arbitrage_opportunity = self._detect_arbitrage_opportunity(
                symbol, pair_symbol, spread_analysis
            )
            
            # 生成套利決策
            decision = self._generate_arbitrage_decision(
                symbol, pair_symbol, arbitrage_opportunity, spread_analysis
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"套利交易決策生成失敗: {e}")
            return self._create_hold_decision(symbol, f"決策生成錯誤: {e}")
    
    def _validate_data(self, data: pd.DataFrame, pair_symbol: Optional[str]) -> bool:
        """驗證數據完整性"""
        if len(data) < self.lookback_period:
            logger.warning(f"數據不足，需要至少{self.lookback_period}個週期")
            return False
        
        # 檢查是否有足夠的價格欄位
        price_columns = [col for col in data.columns if 'close' in col.lower() or 'price' in col.lower()]
        if len(price_columns) < 2 and pair_symbol is None:
            logger.warning("需要至少兩個價格序列進行配對交易")
            return False
        
        return True
    
    def _find_best_pair(self, symbol: str, data: pd.DataFrame) -> Optional[str]:
        """尋找最佳配對標的"""
        # 簡化實現：假設數據包含多個標的的價格
        price_columns = [col for col in data.columns if 'close' in col.lower()]
        
        if len(price_columns) < 2:
            return None
        
        # 假設第一個是目標標的，尋找與其最相關的標的
        target_prices = data[price_columns[0]]
        best_correlation = 0
        best_pair = None
        
        for col in price_columns[1:]:
            correlation = target_prices.corr(data[col])
            if correlation > best_correlation and correlation >= self.correlation_threshold:
                best_correlation = correlation
                best_pair = col.replace('_close', '').replace('close_', '')
        
        return best_pair
    
    def _analyze_pair_relationship(
        self,
        symbol1: str,
        symbol2: str,
        data: pd.DataFrame
    ) -> Dict[str, Any]:
        """分析配對關係"""
        # 獲取價格數據
        price1 = self._get_price_series(symbol1, data)
        price2 = self._get_price_series(symbol2, data)
        
        if price1 is None or price2 is None:
            return {'valid': False}
        
        # 計算相關性
        correlation = price1.corr(price2)
        
        # 協整檢驗
        cointegration_result = self._test_cointegration(price1, price2)
        
        # 計算對沖比率
        hedge_ratio = self._calculate_hedge_ratio(price1, price2)
        
        # 計算價差
        spread = price1 - hedge_ratio * price2
        spread_mean = spread.mean()
        spread_std = spread.std()
        
        return {
            'valid': True,
            'correlation': correlation,
            'cointegration_pvalue': cointegration_result['pvalue'],
            'is_cointegrated': cointegration_result['pvalue'] < self.cointegration_threshold,
            'hedge_ratio': hedge_ratio,
            'spread_mean': spread_mean,
            'spread_std': spread_std,
            'current_spread': spread.iloc[-1],
            'spread_zscore': (spread.iloc[-1] - spread_mean) / spread_std if spread_std > 0 else 0
        }
    
    def _get_price_series(self, symbol: str, data: pd.DataFrame) -> Optional[pd.Series]:
        """獲取價格序列"""
        # 嘗試不同的欄位名稱格式
        possible_columns = [
            f'{symbol}_close',
            f'close_{symbol}',
            f'{symbol}',
            'close'  # 如果只有一個標的
        ]
        
        for col in possible_columns:
            if col in data.columns:
                return data[col]
        
        return None
    
    def _test_cointegration(self, price1: pd.Series, price2: pd.Series) -> Dict[str, float]:
        """協整檢驗"""
        try:
            # 簡化的協整檢驗（實際應使用更嚴格的檢驗如Engle-Granger或Johansen）
            # 這裡使用線性回歸殘差的平穩性檢驗
            
            # 線性回歸
            X = price2.values.reshape(-1, 1)
            y = price1.values
            
            reg = LinearRegression().fit(X, y)
            residuals = y - reg.predict(X)
            
            # 簡化的平穩性檢驗（實際應使用ADF檢驗）
            # 這裡使用殘差的自相關性作為代理
            residuals_series = pd.Series(residuals)
            autocorr = residuals_series.autocorr(lag=1)
            
            # 將自相關性轉換為p值的近似值
            pvalue = abs(autocorr)  # 簡化處理
            
            return {
                'pvalue': pvalue,
                'residuals': residuals
            }
            
        except Exception as e:
            logger.warning(f"協整檢驗失敗: {e}")
            return {'pvalue': 1.0, 'residuals': np.array([])}
    
    def _calculate_hedge_ratio(self, price1: pd.Series, price2: pd.Series) -> float:
        """計算對沖比率"""
        try:
            # 使用最近的數據計算對沖比率
            recent_data = min(self.hedge_ratio_window, len(price1))
            
            X = price2.iloc[-recent_data:].values.reshape(-1, 1)
            y = price1.iloc[-recent_data:].values
            
            reg = LinearRegression().fit(X, y)
            hedge_ratio = reg.coef_[0]
            
            return hedge_ratio
            
        except Exception as e:
            logger.warning(f"對沖比率計算失敗: {e}")
            return 1.0
    
    def _analyze_spread(
        self,
        symbol1: str,
        symbol2: str,
        data: pd.DataFrame,
        pair_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析價差"""
        if not pair_analysis['valid']:
            return {'valid': False}
        
        current_spread = pair_analysis['current_spread']
        spread_mean = pair_analysis['spread_mean']
        spread_std = pair_analysis['spread_std']
        spread_zscore = pair_analysis['spread_zscore']
        
        # 價差趨勢分析
        price1 = self._get_price_series(symbol1, data)
        price2 = self._get_price_series(symbol2, data)
        hedge_ratio = pair_analysis['hedge_ratio']
        
        spread_series = price1 - hedge_ratio * price2
        recent_spread = spread_series.iloc[-5:]  # 最近5期
        spread_trend = np.polyfit(range(len(recent_spread)), recent_spread, 1)[0]
        
        # 價差極值檢測
        spread_percentile_95 = spread_series.quantile(0.95)
        spread_percentile_5 = spread_series.quantile(0.05)
        
        return {
            'valid': True,
            'current_spread': current_spread,
            'spread_mean': spread_mean,
            'spread_std': spread_std,
            'spread_zscore': spread_zscore,
            'spread_trend': spread_trend,
            'spread_percentile_95': spread_percentile_95,
            'spread_percentile_5': spread_percentile_5,
            'is_extreme_high': current_spread >= spread_percentile_95,
            'is_extreme_low': current_spread <= spread_percentile_5
        }

    def _detect_arbitrage_opportunity(
        self,
        symbol1: str,
        symbol2: str,
        spread_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """檢測套利機會"""
        if not spread_analysis['valid']:
            return {'opportunity': False}

        spread_zscore = spread_analysis['spread_zscore']
        spread_trend = spread_analysis['spread_trend']

        pair_key = f"{symbol1}_{symbol2}"
        is_in_position = pair_key in self.current_pairs

        # 進入信號檢測
        if not is_in_position:
            if spread_zscore >= self.spread_entry_threshold:
                # 價差過高，做空價差（買入symbol2，賣出symbol1）
                opportunity_type = "short_spread"
                signal_strength = min(abs(spread_zscore) / self.spread_entry_threshold, 3.0)

            elif spread_zscore <= -self.spread_entry_threshold:
                # 價差過低，做多價差（買入symbol1，賣出symbol2）
                opportunity_type = "long_spread"
                signal_strength = min(abs(spread_zscore) / self.spread_entry_threshold, 3.0)

            else:
                opportunity_type = "no_opportunity"
                signal_strength = 0.0

        # 退出信號檢測
        else:
            current_position = self.current_pairs[pair_key]
            position_type = current_position['type']

            if abs(spread_zscore) <= self.spread_exit_threshold:
                # 價差回歸，平倉
                opportunity_type = "close_position"
                signal_strength = 1.0

            elif abs(spread_zscore) >= self.max_spread_deviation:
                # 價差偏離過大，止損
                opportunity_type = "stop_loss"
                signal_strength = 1.0

            else:
                opportunity_type = "hold_position"
                signal_strength = 0.5

        # 趨勢確認
        trend_confirmation = False
        if opportunity_type in ["long_spread", "short_spread"]:
            if opportunity_type == "long_spread" and spread_trend < 0:
                trend_confirmation = True  # 價差下降趨勢，支持做多價差
            elif opportunity_type == "short_spread" and spread_trend > 0:
                trend_confirmation = True  # 價差上升趨勢，支持做空價差

        return {
            'opportunity': opportunity_type != "no_opportunity",
            'type': opportunity_type,
            'signal_strength': signal_strength,
            'trend_confirmation': trend_confirmation,
            'spread_zscore': spread_zscore,
            'confidence': self._calculate_arbitrage_confidence(spread_analysis, trend_confirmation)
        }

    def _calculate_arbitrage_confidence(
        self,
        spread_analysis: Dict[str, Any],
        trend_confirmation: bool
    ) -> float:
        """計算套利信心度"""
        base_confidence = 0.7

        # 基於Z分數的信心度調整
        zscore = abs(spread_analysis['spread_zscore'])
        zscore_confidence = min(zscore / 3.0, 1.0)

        # 趨勢確認加成
        trend_bonus = 0.2 if trend_confirmation else 0.0

        # 極值情況加成
        extreme_bonus = 0.1 if (spread_analysis['is_extreme_high'] or spread_analysis['is_extreme_low']) else 0.0

        confidence = base_confidence * zscore_confidence + trend_bonus + extreme_bonus

        return min(confidence, 0.95)

    def _generate_arbitrage_decision(
        self,
        symbol1: str,
        symbol2: str,
        arbitrage_opportunity: Dict[str, Any],
        spread_analysis: Dict[str, Any]
    ) -> AgentDecision:
        """生成套利決策"""
        current_time = datetime.now()
        pair_key = f"{symbol1}_{symbol2}"

        if not arbitrage_opportunity['opportunity']:
            return self._create_hold_decision(symbol1, "無套利機會")

        opportunity_type = arbitrage_opportunity['type']
        signal_strength = arbitrage_opportunity['signal_strength']
        confidence = arbitrage_opportunity['confidence']

        if opportunity_type == "long_spread":
            # 做多價差：買入symbol1，賣出symbol2
            action = 1  # 對於symbol1
            reasoning = self._generate_long_spread_reasoning(arbitrage_opportunity, spread_analysis)

            # 記錄配對交易
            self.current_pairs[pair_key] = {
                'type': 'long_spread',
                'entry_time': current_time,
                'entry_spread': spread_analysis['current_spread'],
                'hedge_ratio': spread_analysis.get('hedge_ratio', 1.0),
                'symbol1': symbol1,
                'symbol2': symbol2
            }

        elif opportunity_type == "short_spread":
            # 做空價差：賣出symbol1，買入symbol2
            action = -1  # 對於symbol1
            reasoning = self._generate_short_spread_reasoning(arbitrage_opportunity, spread_analysis)

            # 記錄配對交易
            self.current_pairs[pair_key] = {
                'type': 'short_spread',
                'entry_time': current_time,
                'entry_spread': spread_analysis['current_spread'],
                'hedge_ratio': spread_analysis.get('hedge_ratio', 1.0),
                'symbol1': symbol1,
                'symbol2': symbol2
            }

        elif opportunity_type in ["close_position", "stop_loss"]:
            # 平倉
            current_position = self.current_pairs.get(pair_key, {})
            if current_position.get('type') == 'long_spread':
                action = -1  # 賣出symbol1
            else:
                action = 1   # 買入symbol1

            reasoning = self._generate_close_reasoning(opportunity_type, arbitrage_opportunity, spread_analysis)

            # 移除配對交易記錄
            if pair_key in self.current_pairs:
                del self.current_pairs[pair_key]

        else:
            # 持有
            action = 0
            reasoning = "套利交易持有中，等待價差回歸"

        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=current_time,
            symbol=symbol1,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            expected_return=self._estimate_arbitrage_return(arbitrage_opportunity, spread_analysis),
            risk_assessment=self._assess_arbitrage_risk(spread_analysis),
            position_size=self._calculate_arbitrage_position_size(signal_strength),
            metadata={
                'pair_symbol': symbol2,
                'opportunity_type': opportunity_type,
                'spread_zscore': spread_analysis['spread_zscore'],
                'signal_strength': signal_strength,
                'hedge_ratio': spread_analysis.get('hedge_ratio', 1.0),
                'is_pair_trade': True
            }
        )

    def _generate_long_spread_reasoning(
        self,
        opportunity: Dict[str, Any],
        spread_analysis: Dict[str, Any]
    ) -> str:
        """生成做多價差推理"""
        zscore = spread_analysis['spread_zscore']
        return f"套利交易做多價差：價差Z分數{zscore:.2f}低於閾值，預期價差回歸"

    def _generate_short_spread_reasoning(
        self,
        opportunity: Dict[str, Any],
        spread_analysis: Dict[str, Any]
    ) -> str:
        """生成做空價差推理"""
        zscore = spread_analysis['spread_zscore']
        return f"套利交易做空價差：價差Z分數{zscore:.2f}高於閾值，預期價差回歸"

    def _generate_close_reasoning(
        self,
        opportunity_type: str,
        opportunity: Dict[str, Any],
        spread_analysis: Dict[str, Any]
    ) -> str:
        """生成平倉推理"""
        zscore = spread_analysis['spread_zscore']
        if opportunity_type == "close_position":
            return f"套利交易平倉：價差Z分數{zscore:.2f}回歸正常範圍"
        else:  # stop_loss
            return f"套利交易止損：價差Z分數{zscore:.2f}偏離過大"

    def _create_hold_decision(self, symbol: str, reason: str) -> AgentDecision:
        """創建持有決策"""
        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            symbol=symbol,
            action=0,
            confidence=0.5,
            reasoning=reason,
            expected_return=0.0,
            risk_assessment=0.3,  # 套利交易風險較低
            position_size=0.0
        )

    def _estimate_arbitrage_return(
        self,
        opportunity: Dict[str, Any],
        spread_analysis: Dict[str, Any]
    ) -> float:
        """估算套利收益率"""
        # 基於價差回歸估算收益率
        zscore = abs(spread_analysis['spread_zscore'])

        # 套利收益通常較低但穩定
        base_return = 0.01  # 基準1%收益率

        # 基於Z分數調整收益預期
        return_multiplier = min(zscore / 2.0, 2.0)

        expected_return = base_return * return_multiplier

        return min(expected_return, 0.05)  # 最高5%預期收益率

    def _assess_arbitrage_risk(self, spread_analysis: Dict[str, Any]) -> float:
        """評估套利風險"""
        # 套利交易風險相對較低
        base_risk = 0.2

        # 基於價差波動性調整風險
        spread_std = spread_analysis.get('spread_std', 0)
        spread_mean = spread_analysis.get('spread_mean', 1)

        if spread_mean != 0:
            volatility_risk = min(spread_std / abs(spread_mean), 1.0)
        else:
            volatility_risk = 0.5

        overall_risk = base_risk + volatility_risk * 0.3

        return min(overall_risk, 0.8)

    def _calculate_arbitrage_position_size(self, signal_strength: float) -> float:
        """計算套利倉位大小"""
        # 套利交易可以使用較大倉位
        base_size = self.max_position_size

        # 基於信號強度調整
        size_factor = min(signal_strength / 2.0, 1.0)

        position_size = base_size * size_factor

        return min(position_size, self.max_position_size)

    def get_investment_philosophy(self) -> str:
        """獲取投資哲學描述"""
        return (
            "套利交易哲學：尋找價格差異機會，通過配對交易獲取穩定收益。"
            f"相關性閾值：{self.correlation_threshold}，價差進入閾值：{self.spread_entry_threshold}，"
            f"價差退出閾值：{self.spread_exit_threshold}，最大偏離：{self.max_spread_deviation}。"
            "策略特點：市場中性、低風險、穩定收益。"
        )

    def get_current_pairs(self) -> Dict[str, Dict]:
        """獲取當前配對交易"""
        return self.current_pairs.copy()

    def get_pair_relationships(self) -> Dict[str, Dict]:
        """獲取配對關係"""
        return self.pair_relationships.copy()

    def __str__(self) -> str:
        """字符串表示"""
        return f"ArbitrageTrader(pairs={len(self.current_pairs)})"
