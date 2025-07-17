# -*- coding: utf-8 -*-
"""
動量交易代理模組

此模組實現基於動量因子的交易代理。

投資哲學：
- 追蹤價格和成交量動量
- 快速進出，高換手率
- 關注市場情緒和資金流向
- 趨勢跟隨策略

主要功能：
- 價格動量計算
- 成交量動量分析
- 相對強度排名
- 突破交易策略
- 動量衰減檢測
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

from ..base import TradingAgent, AgentDecision, InvestmentStyle, RiskPreference

# 設定日誌
logger = logging.getLogger(__name__)


class MomentumTrader(TradingAgent):
    """
    動量交易代理。
    
    基於動量因子進行交易決策，包括：
    - 價格動量（短期、中期、長期）
    - 成交量動量
    - 相對強度指標
    - 突破信號
    - 動量衰減檢測
    
    Attributes:
        momentum_periods (List[int]): 動量計算週期
        volume_momentum_period (int): 成交量動量週期
        breakout_period (int): 突破檢測週期
        momentum_threshold (float): 動量閾值
        volume_threshold (float): 成交量閾值
        relative_strength_period (int): 相對強度週期
        decay_detection_period (int): 衰減檢測週期
        max_holding_period (int): 最大持有期間
        momentum_stop_loss (float): 動量止損閾值
    """
    
    def __init__(
        self,
        name: str = "MomentumTrader",
        momentum_periods: List[int] = [5, 10, 20],
        volume_momentum_period: int = 10,
        breakout_period: int = 20,
        momentum_threshold: float = 0.02,
        volume_threshold: float = 1.5,
        relative_strength_period: int = 60,
        decay_detection_period: int = 5,
        max_holding_period: int = 30,
        momentum_stop_loss: float = 0.08,
        **parameters: Any
    ) -> None:
        """
        初始化動量交易代理。
        
        Args:
            name: 代理名稱
            momentum_periods: 動量計算週期列表
            volume_momentum_period: 成交量動量週期
            breakout_period: 突破檢測週期
            momentum_threshold: 動量閾值
            volume_threshold: 成交量閾值
            relative_strength_period: 相對強度週期
            decay_detection_period: 衰減檢測週期
            max_holding_period: 最大持有期間（天數）
            momentum_stop_loss: 動量止損閾值
            **parameters: 其他策略參數
        """
        super().__init__(
            name=name,
            investment_style=InvestmentStyle.MOMENTUM,
            risk_preference=RiskPreference.AGGRESSIVE,
            max_position_size=0.08,  # 動量交易通常分散持股
            **parameters
        )
        
        # 動量交易參數
        self.momentum_periods = momentum_periods
        self.volume_momentum_period = volume_momentum_period
        self.breakout_period = breakout_period
        self.momentum_threshold = momentum_threshold
        self.volume_threshold = volume_threshold
        self.relative_strength_period = relative_strength_period
        self.decay_detection_period = decay_detection_period
        self.max_holding_period = max_holding_period
        self.momentum_stop_loss = momentum_stop_loss
        
        # 持倉追蹤
        self.current_positions: Dict[str, Dict] = {}
        self.momentum_rankings: Dict[str, float] = {}
        
        logger.info(f"初始化動量交易代理: {name}")
    
    def make_decision(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """
        基於動量分析生成交易決策。
        
        Args:
            data: 市場數據，包含OHLCV數據
            market_context: 市場上下文信息
            
        Returns:
            AgentDecision: 交易決策
        """
        try:
            symbol = market_context.get('symbol', 'UNKNOWN') if market_context else 'UNKNOWN'
            
            # 檢查數據完整性
            if not self._validate_data(data):
                return self._create_hold_decision(symbol, "數據不完整")
            
            # 計算動量指標
            momentum_metrics = self._calculate_momentum_metrics(data)
            
            # 分析價格動量
            price_momentum = self._analyze_price_momentum(momentum_metrics)
            
            # 分析成交量動量
            volume_momentum = self._analyze_volume_momentum(momentum_metrics)
            
            # 檢測突破信號
            breakout_signal = self._detect_breakout(data, momentum_metrics)
            
            # 檢測動量衰減
            momentum_decay = self._detect_momentum_decay(momentum_metrics)
            
            # 計算綜合動量評分
            momentum_score = self._calculate_momentum_score(
                price_momentum, volume_momentum, breakout_signal, momentum_decay
            )
            
            # 生成交易決策
            decision = self._generate_momentum_decision(
                symbol, momentum_score, momentum_metrics, data
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"動量交易決策生成失敗: {e}")
            return self._create_hold_decision(symbol, f"決策生成錯誤: {e}")
    
    def _validate_data(self, data: pd.DataFrame) -> bool:
        """驗證數據完整性"""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        
        for col in required_columns:
            if col not in data.columns:
                logger.warning(f"缺少必要數據欄位: {col}")
                return False
        
        # 需要足夠的歷史數據來計算動量指標
        min_periods = max(max(self.momentum_periods), self.relative_strength_period) + 10
        if len(data) < min_periods:
            logger.warning(f"數據不足，需要至少{min_periods}個週期")
            return False
        
        return True
    
    def _calculate_momentum_metrics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """計算動量指標"""
        metrics = {}
        
        # 價格動量（不同週期）
        for period in self.momentum_periods:
            momentum_key = f'price_momentum_{period}'
            metrics[momentum_key] = data['close'].pct_change(periods=period)
        
        # 成交量動量
        metrics['volume_momentum'] = data['volume'].pct_change(periods=self.volume_momentum_period)
        
        # 相對強度（與自身歷史比較）
        metrics['relative_strength'] = self._calculate_relative_strength(data['close'])
        
        # 價格加速度（動量的變化率）
        short_momentum = metrics[f'price_momentum_{self.momentum_periods[0]}']
        metrics['price_acceleration'] = short_momentum.diff()
        
        # 成交量比率
        volume_ma = data['volume'].rolling(window=20).mean()
        metrics['volume_ratio'] = data['volume'] / volume_ma
        
        # 價格波動率
        metrics['volatility'] = data['close'].rolling(window=20).std()
        
        # 最高價和最低價動量
        metrics['high_momentum'] = data['high'].pct_change(periods=self.momentum_periods[1])
        metrics['low_momentum'] = data['low'].pct_change(periods=self.momentum_periods[1])
        
        # 價格範圍動量
        price_range = data['high'] - data['low']
        metrics['range_momentum'] = price_range.pct_change(periods=self.momentum_periods[1])
        
        return metrics
    
    def _calculate_relative_strength(self, prices: pd.Series) -> pd.Series:
        """計算相對強度指標"""
        # 計算當前價格相對於歷史價格的排名
        relative_strength = pd.Series(index=prices.index, dtype=float)
        
        for i in range(self.relative_strength_period, len(prices)):
            current_price = prices.iloc[i]
            historical_prices = prices.iloc[i-self.relative_strength_period:i]
            
            # 計算當前價格在歷史價格中的百分位排名
            rank = (historical_prices < current_price).sum() / len(historical_prices)
            relative_strength.iloc[i] = rank
        
        return relative_strength
    
    def _analyze_price_momentum(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """分析價格動量"""
        latest_idx = -1
        
        # 多週期動量分析
        momentum_signals = {}
        momentum_strengths = []
        
        for period in self.momentum_periods:
            momentum_key = f'price_momentum_{period}'
            momentum_value = metrics[momentum_key].iloc[latest_idx]
            
            if momentum_value >= self.momentum_threshold:
                signal = "strong_bullish"
                strength = min(momentum_value / self.momentum_threshold, 3.0)
            elif momentum_value >= self.momentum_threshold * 0.5:
                signal = "moderate_bullish"
                strength = momentum_value / self.momentum_threshold
            elif momentum_value <= -self.momentum_threshold:
                signal = "strong_bearish"
                strength = min(abs(momentum_value) / self.momentum_threshold, 3.0) * -1
            elif momentum_value <= -self.momentum_threshold * 0.5:
                signal = "moderate_bearish"
                strength = momentum_value / self.momentum_threshold
            else:
                signal = "neutral"
                strength = 0.0
            
            momentum_signals[f'period_{period}'] = signal
            momentum_strengths.append(strength)
        
        # 動量一致性檢查
        bullish_count = sum(1 for s in momentum_strengths if s > 0)
        bearish_count = sum(1 for s in momentum_strengths if s < 0)
        
        if bullish_count > bearish_count:
            overall_signal = "bullish"
            consistency = bullish_count / len(momentum_strengths)
        elif bearish_count > bullish_count:
            overall_signal = "bearish"
            consistency = bearish_count / len(momentum_strengths)
        else:
            overall_signal = "mixed"
            consistency = 0.5
        
        # 動量加速度
        acceleration = metrics['price_acceleration'].iloc[latest_idx]
        
        return {
            'signals': momentum_signals,
            'strengths': momentum_strengths,
            'overall_signal': overall_signal,
            'consistency': consistency,
            'average_strength': np.mean(momentum_strengths),
            'acceleration': acceleration
        }
    
    def _analyze_volume_momentum(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """分析成交量動量"""
        latest_idx = -1
        
        volume_momentum = metrics['volume_momentum'].iloc[latest_idx]
        volume_ratio = metrics['volume_ratio'].iloc[latest_idx]
        
        # 成交量動量信號
        if volume_momentum >= 0.5 and volume_ratio >= self.volume_threshold:
            volume_signal = "strong_expansion"
            volume_strength = 1.0
        elif volume_momentum >= 0.2 and volume_ratio >= 1.2:
            volume_signal = "moderate_expansion"
            volume_strength = 0.6
        elif volume_momentum <= -0.3:
            volume_signal = "contraction"
            volume_strength = -0.8
        else:
            volume_signal = "neutral"
            volume_strength = 0.0
        
        return {
            'signal': volume_signal,
            'strength': volume_strength,
            'momentum': volume_momentum,
            'ratio': volume_ratio
        }

    def _detect_breakout(self, data: pd.DataFrame, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """檢測突破信號"""
        latest_idx = -1

        # 計算突破參考價位
        high_breakout = data['high'].rolling(window=self.breakout_period).max()
        low_breakout = data['low'].rolling(window=self.breakout_period).min()

        current_price = data['close'].iloc[latest_idx]
        current_high = data['high'].iloc[latest_idx]
        current_low = data['low'].iloc[latest_idx]

        prev_high_breakout = high_breakout.iloc[latest_idx - 1]
        prev_low_breakout = low_breakout.iloc[latest_idx - 1]

        # 突破檢測
        if current_high > prev_high_breakout:
            breakout_type = "upward_breakout"
            breakout_strength = 1.0

            # 檢查成交量確認
            volume_ratio = metrics['volume_ratio'].iloc[latest_idx]
            if volume_ratio >= self.volume_threshold:
                breakout_strength = 1.5

        elif current_low < prev_low_breakout:
            breakout_type = "downward_breakout"
            breakout_strength = -1.0

            # 檢查成交量確認
            volume_ratio = metrics['volume_ratio'].iloc[latest_idx]
            if volume_ratio >= self.volume_threshold:
                breakout_strength = -1.5

        else:
            breakout_type = "no_breakout"
            breakout_strength = 0.0

        # 突破幅度
        if breakout_type == "upward_breakout":
            breakout_magnitude = (current_high - prev_high_breakout) / prev_high_breakout
        elif breakout_type == "downward_breakout":
            breakout_magnitude = (prev_low_breakout - current_low) / prev_low_breakout
        else:
            breakout_magnitude = 0.0

        return {
            'type': breakout_type,
            'strength': breakout_strength,
            'magnitude': breakout_magnitude,
            'high_level': prev_high_breakout,
            'low_level': prev_low_breakout
        }

    def _detect_momentum_decay(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """檢測動量衰減"""
        # 檢查最近幾期的動量變化
        decay_signals = []

        for period in self.momentum_periods:
            momentum_key = f'price_momentum_{period}'
            recent_momentum = metrics[momentum_key].iloc[-self.decay_detection_period:]

            # 檢查動量是否在衰減
            if len(recent_momentum) >= 3:
                trend = np.polyfit(range(len(recent_momentum)), recent_momentum, 1)[0]

                if trend < -0.001:  # 動量在衰減
                    decay_signals.append(True)
                else:
                    decay_signals.append(False)

        # 動量衰減評估
        decay_count = sum(decay_signals)
        total_signals = len(decay_signals)

        if decay_count >= total_signals * 0.7:
            decay_status = "strong_decay"
            decay_strength = -0.8
        elif decay_count >= total_signals * 0.5:
            decay_status = "moderate_decay"
            decay_strength = -0.5
        else:
            decay_status = "no_decay"
            decay_strength = 0.0

        return {
            'status': decay_status,
            'strength': decay_strength,
            'decay_ratio': decay_count / total_signals if total_signals > 0 else 0
        }

    def _calculate_momentum_score(
        self,
        price_momentum: Dict[str, Any],
        volume_momentum: Dict[str, Any],
        breakout_signal: Dict[str, Any],
        momentum_decay: Dict[str, Any]
    ) -> Dict[str, Any]:
        """計算綜合動量評分"""
        # 權重分配
        weights = {
            'price_momentum': 0.4,
            'volume_momentum': 0.2,
            'breakout': 0.3,
            'decay_penalty': 0.1
        }

        # 計算各組件評分
        price_score = price_momentum['average_strength'] * price_momentum['consistency']
        volume_score = volume_momentum['strength']
        breakout_score = breakout_signal['strength']
        decay_penalty = momentum_decay['strength']

        # 綜合評分
        overall_score = (
            price_score * weights['price_momentum'] +
            volume_score * weights['volume_momentum'] +
            breakout_score * weights['breakout'] +
            decay_penalty * weights['decay_penalty']
        )

        # 動量確認度
        confirmations = 0
        total_factors = 4

        if abs(price_score) > 0.5:
            confirmations += 1
        if abs(volume_score) > 0.5:
            confirmations += 1
        if abs(breakout_score) > 0.5:
            confirmations += 1
        if momentum_decay['status'] == 'no_decay':
            confirmations += 1

        confirmation_rate = confirmations / total_factors

        # 調整後的評分
        adjusted_score = overall_score * confirmation_rate

        return {
            'overall_score': overall_score,
            'adjusted_score': adjusted_score,
            'confirmation_rate': confirmation_rate,
            'price_component': price_score,
            'volume_component': volume_score,
            'breakout_component': breakout_score,
            'decay_component': decay_penalty
        }

    def _generate_momentum_decision(
        self,
        symbol: str,
        momentum_score: Dict[str, Any],
        metrics: Dict[str, Any],
        data: pd.DataFrame
    ) -> AgentDecision:
        """生成動量交易決策"""
        current_time = datetime.now()
        current_price = data['close'].iloc[-1]

        # 決策閾值
        buy_threshold = 0.7
        sell_threshold = -0.7

        adjusted_score = momentum_score['adjusted_score']
        confirmation_rate = momentum_score['confirmation_rate']

        # 檢查是否已持有該股票
        is_holding = symbol in self.current_positions

        # 持倉時間檢查
        holding_time_check = self._check_holding_time(symbol, current_time)

        if adjusted_score >= buy_threshold and not is_holding:
            # 買入決策
            action = 1
            confidence = min(0.95, abs(adjusted_score) * confirmation_rate)
            reasoning = self._generate_buy_reasoning(momentum_score, metrics)

            # 記錄持倉
            self.current_positions[symbol] = {
                'entry_time': current_time,
                'entry_price': current_price,
                'entry_score': adjusted_score,
                'momentum_stop_loss': current_price * (1 - self.momentum_stop_loss)
            }

        elif (adjusted_score <= sell_threshold and is_holding) or not holding_time_check['allow_hold']:
            # 賣出決策
            action = -1
            if not holding_time_check['allow_hold']:
                confidence = 0.8
                reasoning = holding_time_check['reason']
            else:
                confidence = min(0.9, abs(adjusted_score) * confirmation_rate)
                reasoning = self._generate_sell_reasoning(momentum_score, metrics)

            # 移除持倉記錄
            if symbol in self.current_positions:
                del self.current_positions[symbol]

        else:
            # 觀望決策
            action = 0
            confidence = 0.5 + abs(adjusted_score) * 0.3
            reasoning = self._generate_hold_reasoning(momentum_score, metrics)

        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=current_time,
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            expected_return=self._estimate_expected_return(momentum_score),
            risk_assessment=self._assess_risk(metrics),
            position_size=self._calculate_position_size(adjusted_score, confirmation_rate),
            metadata={
                'momentum_score': adjusted_score,
                'confirmation_rate': confirmation_rate,
                'price_momentum': momentum_score['price_component'],
                'volume_momentum': momentum_score['volume_component'],
                'breakout_signal': momentum_score['breakout_component'],
                'relative_strength': metrics['relative_strength'].iloc[-1] if not metrics['relative_strength'].empty else 0
            }
        )

    def _check_holding_time(self, symbol: str, current_time: datetime) -> Dict[str, Any]:
        """檢查持倉時間"""
        if symbol not in self.current_positions:
            return {'allow_hold': True, 'reason': ''}

        position = self.current_positions[symbol]
        holding_days = (current_time - position['entry_time']).days

        if holding_days >= self.max_holding_period:
            return {
                'allow_hold': False,
                'reason': f"達到最大持有期間{self.max_holding_period}天，動量交易平倉"
            }

        return {'allow_hold': True, 'reason': ''}

    def _generate_buy_reasoning(
        self,
        momentum_score: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> str:
        """生成買入推理"""
        reasons = []

        price_component = momentum_score['price_component']
        volume_component = momentum_score['volume_component']
        breakout_component = momentum_score['breakout_component']

        if price_component > 0.5:
            reasons.append("價格動量強勁")
        if volume_component > 0.5:
            reasons.append("成交量動量配合")
        if breakout_component > 0.5:
            reasons.append("突破信號確認")

        # 相對強度
        if 'relative_strength' in metrics and not metrics['relative_strength'].empty:
            rs_value = metrics['relative_strength'].iloc[-1]
            if rs_value >= 0.8:
                reasons.append(f"相對強度高({rs_value:.2f})")

        base_reason = f"動量交易買入信號（評分{momentum_score['adjusted_score']:.2f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons)
        else:
            return base_reason

    def _generate_sell_reasoning(
        self,
        momentum_score: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> str:
        """生成賣出推理"""
        reasons = []

        price_component = momentum_score['price_component']
        volume_component = momentum_score['volume_component']
        decay_component = momentum_score['decay_component']

        if price_component < -0.5:
            reasons.append("價格動量轉弱")
        if volume_component < -0.5:
            reasons.append("成交量萎縮")
        if decay_component < -0.5:
            reasons.append("動量衰減明顯")

        base_reason = f"動量交易賣出信號（評分{momentum_score['adjusted_score']:.2f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons)
        else:
            return base_reason

    def _generate_hold_reasoning(
        self,
        momentum_score: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> str:
        """生成持有推理"""
        score = momentum_score['adjusted_score']
        confirmation = momentum_score['confirmation_rate']

        return f"動量交易觀望（評分{score:.2f}，確認度{confirmation:.2f}），等待動量信號"

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
            risk_assessment=0.5,
            position_size=0.0
        )

    def _estimate_expected_return(self, momentum_score: Dict[str, Any]) -> float:
        """估算預期收益率"""
        # 基於動量評分估算短期預期收益率
        base_return = 0.03  # 基準3%短期收益率

        score = momentum_score['adjusted_score']
        confirmation = momentum_score['confirmation_rate']

        # 動量交易關注短期快速收益
        expected_return = base_return * abs(score) * confirmation * 2

        return min(expected_return, 0.15)  # 最高15%預期收益率

    def _assess_risk(self, metrics: Dict[str, Any]) -> float:
        """評估風險水平（0-1，越高風險越大）"""
        # 波動率風險
        volatility = metrics['volatility'].iloc[-1]
        # 假設平均價格為最近收盤價的近似值
        avg_price = 100  # 簡化處理，實際應該使用真實價格
        volatility_risk = min(volatility / avg_price / 0.03, 1.0)  # 標準化到0-1

        # 動量加速度風險
        acceleration = abs(metrics.get('price_acceleration', pd.Series([0])).iloc[-1])
        acceleration_risk = min(acceleration / 0.01, 1.0)

        # 成交量風險
        volume_ratio = metrics['volume_ratio'].iloc[-1]
        if volume_ratio < 0.5:  # 成交量過低
            volume_risk = 0.8
        elif volume_ratio > 3.0:  # 成交量過高
            volume_risk = 0.7
        else:
            volume_risk = 0.3

        # 綜合風險評估
        overall_risk = (volatility_risk * 0.4 + acceleration_risk * 0.3 + volume_risk * 0.3)

        return min(overall_risk, 1.0)

    def _calculate_position_size(self, score: float, confirmation: float) -> float:
        """計算倉位大小"""
        # 基於動量評分和確認度計算倉位
        base_size = self.max_position_size

        # 動量交易重視信號強度
        size_factor = abs(score) * confirmation

        # 動量交易通常使用較小倉位以分散風險
        position_size = base_size * size_factor * 0.8

        return min(position_size, self.max_position_size)

    def get_investment_philosophy(self) -> str:
        """獲取投資哲學描述"""
        return (
            "動量交易哲學：追蹤價格和成交量動量，快速捕捉趨勢機會。"
            f"動量週期：{self.momentum_periods}，突破週期：{self.breakout_period}，"
            f"動量閾值：{self.momentum_threshold:.1%}，成交量閾值：{self.volume_threshold}。"
            f"風險控制：最大持有期{self.max_holding_period}天，動量止損{self.momentum_stop_loss:.1%}。"
        )

    def get_current_positions(self) -> Dict[str, Dict]:
        """獲取當前持倉信息"""
        return self.current_positions.copy()

    def get_momentum_rankings(self) -> Dict[str, float]:
        """獲取動量排名"""
        return self.momentum_rankings.copy()

    def update_momentum_ranking(self, symbol: str, ranking: float) -> None:
        """更新動量排名"""
        self.momentum_rankings[symbol] = ranking
        logger.debug(f"更新 {symbol} 動量排名為 {ranking:.3f}")

    def __str__(self) -> str:
        """字符串表示"""
        return f"MomentumTrader(positions={len(self.current_positions)})"
