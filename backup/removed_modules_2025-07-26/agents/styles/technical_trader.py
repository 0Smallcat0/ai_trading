# -*- coding: utf-8 -*-
"""
技術分析代理模組

此模組實現基於技術指標的交易代理。

投資哲學：
- 基於技術指標和圖形模式進行交易
- 關注價格趨勢和動量
- 短中期交易策略
- 重視風險控制和止損

主要功能：
- 技術指標計算（MA、RSI、MACD、布林帶等）
- 趨勢識別和信號生成
- 支撐阻力位分析
- 風險管理和止損設置
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from ..base import TradingAgent, AgentDecision, InvestmentStyle, RiskPreference

# 設定日誌
logger = logging.getLogger(__name__)


class TechnicalTrader(TradingAgent):
    """
    技術分析代理。
    
    基於技術指標進行交易決策，包括：
    - 移動平均線系統
    - RSI相對強弱指標
    - MACD指標
    - 布林帶
    - 成交量分析
    - 支撐阻力位
    
    Attributes:
        ma_short_period (int): 短期移動平均週期
        ma_long_period (int): 長期移動平均週期
        rsi_period (int): RSI計算週期
        rsi_overbought (float): RSI超買閾值
        rsi_oversold (float): RSI超賣閾值
        macd_fast (int): MACD快線週期
        macd_slow (int): MACD慢線週期
        macd_signal (int): MACD信號線週期
        bb_period (int): 布林帶週期
        bb_std (float): 布林帶標準差倍數
        volume_ma_period (int): 成交量移動平均週期
        stop_loss_pct (float): 止損百分比
        take_profit_pct (float): 止盈百分比
    """
    
    def __init__(
        self,
        name: str = "TechnicalTrader",
        ma_short_period: int = 10,
        ma_long_period: int = 30,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        bb_period: int = 20,
        bb_std: float = 2.0,
        volume_ma_period: int = 20,
        stop_loss_pct: float = 0.05,
        take_profit_pct: float = 0.15,
        **parameters: Any
    ) -> None:
        """
        初始化技術分析代理。
        
        Args:
            name: 代理名稱
            ma_short_period: 短期移動平均週期
            ma_long_period: 長期移動平均週期
            rsi_period: RSI計算週期
            rsi_overbought: RSI超買閾值
            rsi_oversold: RSI超賣閾值
            macd_fast: MACD快線週期
            macd_slow: MACD慢線週期
            macd_signal: MACD信號線週期
            bb_period: 布林帶週期
            bb_std: 布林帶標準差倍數
            volume_ma_period: 成交量移動平均週期
            stop_loss_pct: 止損百分比
            take_profit_pct: 止盈百分比
            **parameters: 其他策略參數
        """
        super().__init__(
            name=name,
            investment_style=InvestmentStyle.TECHNICAL,
            risk_preference=RiskPreference.MODERATE,
            max_position_size=0.1,  # 技術分析通常分散持股
            **parameters
        )
        
        # 技術指標參數
        self.ma_short_period = ma_short_period
        self.ma_long_period = ma_long_period
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.volume_ma_period = volume_ma_period
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        # 持倉追蹤
        self.current_positions: Dict[str, Dict] = {}
        self.support_resistance_levels: Dict[str, Dict] = {}
        
        logger.info(f"初始化技術分析代理: {name}")
    
    def make_decision(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """
        基於技術分析生成交易決策。
        
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
            
            # 計算技術指標
            indicators = self._calculate_technical_indicators(data)
            
            # 分析趨勢
            trend_analysis = self._analyze_trend(indicators)
            
            # 分析動量
            momentum_analysis = self._analyze_momentum(indicators)
            
            # 分析成交量
            volume_analysis = self._analyze_volume(data, indicators)
            
            # 計算綜合信號強度
            signal_strength = self._calculate_signal_strength(
                trend_analysis, momentum_analysis, volume_analysis
            )
            
            # 生成交易決策
            decision = self._generate_trading_decision(
                symbol, signal_strength, indicators, data
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"技術分析決策生成失敗: {e}")
            return self._create_hold_decision(symbol, f"決策生成錯誤: {e}")
    
    def _validate_data(self, data: pd.DataFrame) -> bool:
        """驗證數據完整性"""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        
        for col in required_columns:
            if col not in data.columns:
                logger.warning(f"缺少必要數據欄位: {col}")
                return False
        
        # 需要足夠的歷史數據來計算技術指標
        min_periods = max(self.ma_long_period, self.bb_period, self.rsi_period) + 10
        if len(data) < min_periods:
            logger.warning(f"數據不足，需要至少{min_periods}個週期")
            return False
        
        return True
    
    def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """計算技術指標"""
        indicators = {}
        
        # 移動平均線
        indicators['ma_short'] = data['close'].rolling(window=self.ma_short_period).mean()
        indicators['ma_long'] = data['close'].rolling(window=self.ma_long_period).mean()
        
        # RSI
        indicators['rsi'] = self._calculate_rsi(data['close'], self.rsi_period)
        
        # MACD
        macd_data = self._calculate_macd(
            data['close'], self.macd_fast, self.macd_slow, self.macd_signal
        )
        indicators.update(macd_data)
        
        # 布林帶
        bb_data = self._calculate_bollinger_bands(
            data['close'], self.bb_period, self.bb_std
        )
        indicators.update(bb_data)
        
        # 成交量指標
        indicators['volume_ma'] = data['volume'].rolling(window=self.volume_ma_period).mean()
        indicators['volume_ratio'] = data['volume'] / indicators['volume_ma']
        
        # 價格變化
        indicators['price_change'] = data['close'].pct_change()
        indicators['price_change_ma'] = indicators['price_change'].rolling(window=5).mean()
        
        # 波動率
        indicators['volatility'] = data['close'].rolling(window=20).std()
        
        return indicators
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """計算RSI指標"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(
        self,
        prices: pd.Series,
        fast_period: int,
        slow_period: int,
        signal_period: int
    ) -> Dict[str, pd.Series]:
        """計算MACD指標"""
        ema_fast = prices.ewm(span=fast_period).mean()
        ema_slow = prices.ewm(span=slow_period).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd_line': macd_line,
            'macd_signal': signal_line,
            'macd_histogram': histogram
        }
    
    def _calculate_bollinger_bands(
        self,
        prices: pd.Series,
        period: int,
        std_multiplier: float
    ) -> Dict[str, pd.Series]:
        """計算布林帶"""
        ma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper_band = ma + (std * std_multiplier)
        lower_band = ma - (std * std_multiplier)
        
        # 計算布林帶位置（0-1之間）
        bb_position = (prices - lower_band) / (upper_band - lower_band)
        
        return {
            'bb_upper': upper_band,
            'bb_middle': ma,
            'bb_lower': lower_band,
            'bb_position': bb_position
        }
    
    def _analyze_trend(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """分析趨勢"""
        latest_idx = -1
        
        # 移動平均線趨勢
        ma_short_current = indicators['ma_short'].iloc[latest_idx]
        ma_long_current = indicators['ma_long'].iloc[latest_idx]
        ma_short_prev = indicators['ma_short'].iloc[latest_idx - 1]
        ma_long_prev = indicators['ma_long'].iloc[latest_idx - 1]
        
        # 趨勢方向
        if ma_short_current > ma_long_current:
            if ma_short_prev <= ma_long_prev:
                trend_signal = "golden_cross"  # 黃金交叉
                trend_strength = 1.0
            else:
                trend_signal = "uptrend"
                trend_strength = 0.7
        elif ma_short_current < ma_long_current:
            if ma_short_prev >= ma_long_prev:
                trend_signal = "death_cross"  # 死亡交叉
                trend_strength = -1.0
            else:
                trend_signal = "downtrend"
                trend_strength = -0.7
        else:
            trend_signal = "sideways"
            trend_strength = 0.0
        
        # 趨勢強度（基於移動平均線斜率）
        ma_short_slope = (ma_short_current - ma_short_prev) / ma_short_prev
        ma_long_slope = (ma_long_current - ma_long_prev) / ma_long_prev
        
        return {
            'signal': trend_signal,
            'strength': trend_strength,
            'ma_short_slope': ma_short_slope,
            'ma_long_slope': ma_long_slope
        }

    def _analyze_momentum(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """分析動量"""
        latest_idx = -1

        # RSI分析
        rsi_current = indicators['rsi'].iloc[latest_idx]
        rsi_prev = indicators['rsi'].iloc[latest_idx - 1]

        if rsi_current >= self.rsi_overbought:
            rsi_signal = "overbought"
            rsi_strength = -0.8
        elif rsi_current <= self.rsi_oversold:
            rsi_signal = "oversold"
            rsi_strength = 0.8
        elif rsi_current > 50 and rsi_prev <= 50:
            rsi_signal = "bullish_crossover"
            rsi_strength = 0.6
        elif rsi_current < 50 and rsi_prev >= 50:
            rsi_signal = "bearish_crossover"
            rsi_strength = -0.6
        else:
            rsi_signal = "neutral"
            rsi_strength = 0.0

        # MACD分析
        macd_line = indicators['macd_line'].iloc[latest_idx]
        macd_signal = indicators['macd_signal'].iloc[latest_idx]
        macd_histogram = indicators['macd_histogram'].iloc[latest_idx]
        macd_histogram_prev = indicators['macd_histogram'].iloc[latest_idx - 1]

        if macd_line > macd_signal and macd_histogram > macd_histogram_prev:
            macd_signal_type = "bullish_momentum"
            macd_strength = 0.7
        elif macd_line < macd_signal and macd_histogram < macd_histogram_prev:
            macd_signal_type = "bearish_momentum"
            macd_strength = -0.7
        elif macd_line > macd_signal:
            macd_signal_type = "bullish"
            macd_strength = 0.4
        elif macd_line < macd_signal:
            macd_signal_type = "bearish"
            macd_strength = -0.4
        else:
            macd_signal_type = "neutral"
            macd_strength = 0.0

        # 綜合動量評分
        momentum_score = (rsi_strength + macd_strength) / 2

        return {
            'rsi_signal': rsi_signal,
            'rsi_strength': rsi_strength,
            'rsi_value': rsi_current,
            'macd_signal': macd_signal_type,
            'macd_strength': macd_strength,
            'momentum_score': momentum_score
        }

    def _analyze_volume(self, data: pd.DataFrame, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """分析成交量"""
        latest_idx = -1

        # 成交量比率
        volume_ratio = indicators['volume_ratio'].iloc[latest_idx]
        price_change = indicators['price_change'].iloc[latest_idx]

        # 成交量確認
        if volume_ratio > 1.5:  # 高成交量
            if price_change > 0:
                volume_signal = "bullish_volume"
                volume_strength = 0.8
            else:
                volume_signal = "bearish_volume"
                volume_strength = -0.8
        elif volume_ratio > 1.2:  # 中等成交量
            if price_change > 0:
                volume_signal = "moderate_bullish"
                volume_strength = 0.5
            else:
                volume_signal = "moderate_bearish"
                volume_strength = -0.5
        else:  # 低成交量
            volume_signal = "low_volume"
            volume_strength = 0.0

        # 成交量趨勢
        volume_ma_current = indicators['volume_ma'].iloc[latest_idx]
        volume_ma_prev = indicators['volume_ma'].iloc[latest_idx - 5]
        volume_trend = (volume_ma_current - volume_ma_prev) / volume_ma_prev

        return {
            'signal': volume_signal,
            'strength': volume_strength,
            'ratio': volume_ratio,
            'trend': volume_trend
        }

    def _calculate_signal_strength(
        self,
        trend_analysis: Dict[str, Any],
        momentum_analysis: Dict[str, Any],
        volume_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """計算綜合信號強度"""
        # 權重分配
        weights = {
            'trend': 0.4,
            'momentum': 0.4,
            'volume': 0.2
        }

        # 計算加權信號強度
        trend_strength = trend_analysis['strength']
        momentum_strength = momentum_analysis['momentum_score']
        volume_strength = volume_analysis['strength']

        overall_strength = (
            trend_strength * weights['trend'] +
            momentum_strength * weights['momentum'] +
            volume_strength * weights['volume']
        )

        # 信號確認度
        confirmations = 0
        total_signals = 3

        if abs(trend_strength) > 0.5:
            confirmations += 1
        if abs(momentum_strength) > 0.5:
            confirmations += 1
        if abs(volume_strength) > 0.5:
            confirmations += 1

        confirmation_rate = confirmations / total_signals

        # 調整信號強度
        adjusted_strength = overall_strength * confirmation_rate

        return {
            'overall_strength': overall_strength,
            'adjusted_strength': adjusted_strength,
            'confirmation_rate': confirmation_rate,
            'trend_component': trend_strength,
            'momentum_component': momentum_strength,
            'volume_component': volume_strength
        }

    def _generate_trading_decision(
        self,
        symbol: str,
        signal_strength: Dict[str, Any],
        indicators: Dict[str, Any],
        data: pd.DataFrame
    ) -> AgentDecision:
        """生成交易決策"""
        current_time = datetime.now()
        current_price = data['close'].iloc[-1]

        # 決策閾值
        buy_threshold = 0.6
        sell_threshold = -0.6

        adjusted_strength = signal_strength['adjusted_strength']
        confirmation_rate = signal_strength['confirmation_rate']

        # 檢查是否已持有該股票
        is_holding = symbol in self.current_positions

        # 風險管理檢查
        risk_check = self._check_risk_management(symbol, current_price, indicators)

        if adjusted_strength >= buy_threshold and not is_holding and risk_check['allow_buy']:
            # 買入決策
            action = 1
            confidence = min(0.9, abs(adjusted_strength) * confirmation_rate)
            reasoning = self._generate_buy_reasoning(signal_strength, indicators)

            # 記錄持倉
            self.current_positions[symbol] = {
                'entry_time': current_time,
                'entry_price': current_price,
                'stop_loss': current_price * (1 - self.stop_loss_pct),
                'take_profit': current_price * (1 + self.take_profit_pct),
                'entry_strength': adjusted_strength
            }

        elif adjusted_strength <= sell_threshold and is_holding:
            # 賣出決策
            action = -1
            confidence = min(0.9, abs(adjusted_strength) * confirmation_rate)
            reasoning = self._generate_sell_reasoning(signal_strength, indicators)

            # 移除持倉記錄
            if symbol in self.current_positions:
                del self.current_positions[symbol]

        elif is_holding and not risk_check['allow_hold']:
            # 風險管理賣出
            action = -1
            confidence = 0.8
            reasoning = risk_check['reason']

            if symbol in self.current_positions:
                del self.current_positions[symbol]

        else:
            # 觀望決策
            action = 0
            confidence = 0.5 + abs(adjusted_strength) * 0.3
            reasoning = self._generate_hold_reasoning(signal_strength, indicators)

        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=current_time,
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            expected_return=self._estimate_expected_return(signal_strength),
            risk_assessment=self._assess_risk(indicators),
            position_size=self._calculate_position_size(adjusted_strength, confirmation_rate),
            metadata={
                'signal_strength': adjusted_strength,
                'confirmation_rate': confirmation_rate,
                'trend_signal': signal_strength['trend_component'],
                'momentum_signal': signal_strength['momentum_component'],
                'volume_signal': signal_strength['volume_component'],
                'rsi_value': indicators['rsi'].iloc[-1],
                'bb_position': indicators['bb_position'].iloc[-1]
            }
        )

    def _check_risk_management(
        self,
        symbol: str,
        current_price: float,
        indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """檢查風險管理規則"""
        if symbol not in self.current_positions:
            return {'allow_buy': True, 'allow_hold': True, 'reason': ''}

        position = self.current_positions[symbol]

        # 止損檢查
        if current_price <= position['stop_loss']:
            return {
                'allow_buy': False,
                'allow_hold': False,
                'reason': f"觸發止損：當前價格{current_price:.2f} <= 止損價{position['stop_loss']:.2f}"
            }

        # 止盈檢查
        if current_price >= position['take_profit']:
            return {
                'allow_buy': False,
                'allow_hold': False,
                'reason': f"觸發止盈：當前價格{current_price:.2f} >= 止盈價{position['take_profit']:.2f}"
            }

        # 波動率檢查
        volatility = indicators['volatility'].iloc[-1]
        if volatility > current_price * 0.1:  # 波動率超過10%
            return {
                'allow_buy': False,
                'allow_hold': True,
                'reason': f"波動率過高：{volatility:.2f}"
            }

        return {'allow_buy': True, 'allow_hold': True, 'reason': ''}

    def _generate_buy_reasoning(
        self,
        signal_strength: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> str:
        """生成買入推理"""
        reasons = []

        trend_strength = signal_strength['trend_component']
        momentum_strength = signal_strength['momentum_component']
        volume_strength = signal_strength['volume_component']

        if trend_strength > 0.5:
            reasons.append("趨勢向上")
        if momentum_strength > 0.5:
            reasons.append("動量強勁")
        if volume_strength > 0.5:
            reasons.append("成交量配合")

        rsi_value = indicators['rsi'].iloc[-1]
        if rsi_value <= self.rsi_oversold:
            reasons.append(f"RSI超賣({rsi_value:.1f})")

        bb_position = indicators['bb_position'].iloc[-1]
        if bb_position <= 0.2:
            reasons.append("接近布林帶下軌")

        base_reason = f"技術分析買入信號（強度{signal_strength['adjusted_strength']:.2f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons)
        else:
            return base_reason

    def _generate_sell_reasoning(
        self,
        signal_strength: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> str:
        """生成賣出推理"""
        reasons = []

        trend_strength = signal_strength['trend_component']
        momentum_strength = signal_strength['momentum_component']
        volume_strength = signal_strength['volume_component']

        if trend_strength < -0.5:
            reasons.append("趨勢向下")
        if momentum_strength < -0.5:
            reasons.append("動量轉弱")
        if volume_strength < -0.5:
            reasons.append("成交量萎縮")

        rsi_value = indicators['rsi'].iloc[-1]
        if rsi_value >= self.rsi_overbought:
            reasons.append(f"RSI超買({rsi_value:.1f})")

        bb_position = indicators['bb_position'].iloc[-1]
        if bb_position >= 0.8:
            reasons.append("接近布林帶上軌")

        base_reason = f"技術分析賣出信號（強度{signal_strength['adjusted_strength']:.2f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons)
        else:
            return base_reason

    def _generate_hold_reasoning(
        self,
        signal_strength: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> str:
        """生成持有推理"""
        strength = signal_strength['adjusted_strength']
        confirmation = signal_strength['confirmation_rate']

        return f"技術分析觀望（信號強度{strength:.2f}，確認度{confirmation:.2f}），等待更明確信號"

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

    def _estimate_expected_return(self, signal_strength: Dict[str, Any]) -> float:
        """估算預期收益率"""
        # 基於信號強度估算短期預期收益率
        base_return = 0.02  # 基準2%短期收益率

        strength = signal_strength['adjusted_strength']
        confirmation = signal_strength['confirmation_rate']

        # 技術分析通常關注短期收益
        expected_return = base_return * abs(strength) * confirmation

        return min(expected_return, 0.1)  # 最高10%預期收益率

    def _assess_risk(self, indicators: Dict[str, Any]) -> float:
        """評估風險水平（0-1，越高風險越大）"""
        # 波動率風險
        volatility = indicators['volatility'].iloc[-1]
        current_price = indicators['bb_middle'].iloc[-1]  # 使用布林帶中軌作為參考價格
        volatility_risk = min(volatility / current_price / 0.05, 1.0)  # 標準化到0-1

        # RSI極值風險
        rsi_value = indicators['rsi'].iloc[-1]
        if rsi_value >= self.rsi_overbought or rsi_value <= self.rsi_oversold:
            rsi_risk = 0.8
        else:
            rsi_risk = 0.3

        # 布林帶位置風險
        bb_position = indicators['bb_position'].iloc[-1]
        if bb_position >= 0.9 or bb_position <= 0.1:
            bb_risk = 0.7
        else:
            bb_risk = 0.3

        # 綜合風險評估
        overall_risk = (volatility_risk * 0.4 + rsi_risk * 0.3 + bb_risk * 0.3)

        return min(overall_risk, 1.0)

    def _calculate_position_size(self, strength: float, confirmation: float) -> float:
        """計算倉位大小"""
        # 基於信號強度和確認度計算倉位
        base_size = self.max_position_size

        # 技術分析重視信號確認度
        size_factor = abs(strength) * confirmation

        position_size = base_size * size_factor

        return min(position_size, self.max_position_size)

    def get_investment_philosophy(self) -> str:
        """獲取投資哲學描述"""
        return (
            "技術分析哲學：基於價格和成交量數據進行交易，關注趨勢和動量。"
            f"主要指標：MA({self.ma_short_period}/{self.ma_long_period})、"
            f"RSI({self.rsi_period})、MACD({self.macd_fast}/{self.macd_slow}/{self.macd_signal})、"
            f"布林帶({self.bb_period})。"
            f"風險控制：止損{self.stop_loss_pct:.1%}、止盈{self.take_profit_pct:.1%}。"
        )

    def get_current_positions(self) -> Dict[str, Dict]:
        """獲取當前持倉信息"""
        return self.current_positions.copy()

    def update_stop_loss(self, symbol: str, new_stop_loss: float) -> bool:
        """更新止損價格"""
        if symbol in self.current_positions:
            self.current_positions[symbol]['stop_loss'] = new_stop_loss
            logger.info(f"更新 {symbol} 止損價格為 {new_stop_loss:.2f}")
            return True
        return False

    def update_take_profit(self, symbol: str, new_take_profit: float) -> bool:
        """更新止盈價格"""
        if symbol in self.current_positions:
            self.current_positions[symbol]['take_profit'] = new_take_profit
            logger.info(f"更新 {symbol} 止盈價格為 {new_take_profit:.2f}")
            return True
        return False

    def __str__(self) -> str:
        """字符串表示"""
        return f"TechnicalTrader(positions={len(self.current_positions)})"
