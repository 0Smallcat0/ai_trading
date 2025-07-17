# -*- coding: utf-8 -*-
"""
索羅斯代理模組

此模組實現模擬喬治·索羅斯投資風格的AI代理。

投資哲學：
- 反身性理論（Reflexivity Theory）
- 宏觀經濟趨勢分析
- 市場情緒和心理學
- 高風險高收益策略
- 快速進出和靈活調整

核心特色：
- 關注宏觀經濟和政治事件
- 市場情緒分析和逆向思維
- 槓桿使用和風險管理
- 短中期投資策略
- 危機中尋找機會
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..base import TradingAgent, AgentDecision, InvestmentStyle, RiskPreference

# 設定日誌
logger = logging.getLogger(__name__)


class SorosAgent(TradingAgent):
    """
    索羅斯代理 - 模擬喬治·索羅斯的投資風格。
    
    基於反身性理論和宏觀分析進行投資決策：
    - 宏觀經濟趨勢分析
    - 市場情緒和反身性檢測
    - 政治和政策影響評估
    - 危機機會識別
    - 動態風險管理
    
    Attributes:
        reflexivity_sensitivity (float): 反身性敏感度
        macro_weight (float): 宏觀因素權重
        sentiment_weight (float): 市場情緒權重
        crisis_opportunity_threshold (float): 危機機會閾值
        max_leverage (float): 最大槓桿倍數
        volatility_target (float): 目標波動率
        holding_period_max (int): 最大持有期間
        political_risk_tolerance (float): 政治風險容忍度
    """
    
    def __init__(
        self,
        name: str = "SorosAgent",
        reflexivity_sensitivity: float = 0.8,
        macro_weight: float = 0.4,
        sentiment_weight: float = 0.3,
        crisis_opportunity_threshold: float = 0.7,
        max_leverage: float = 3.0,
        volatility_target: float = 0.25,
        holding_period_max: int = 180,  # 最多持有6個月
        political_risk_tolerance: float = 0.6,
        **parameters: Any
    ) -> None:
        """
        初始化索羅斯代理。
        
        Args:
            name: 代理名稱
            reflexivity_sensitivity: 反身性敏感度
            macro_weight: 宏觀因素權重
            sentiment_weight: 市場情緒權重
            crisis_opportunity_threshold: 危機機會閾值
            max_leverage: 最大槓桿倍數
            volatility_target: 目標波動率
            holding_period_max: 最大持有期間（天數）
            political_risk_tolerance: 政治風險容忍度
            **parameters: 其他策略參數
        """
        super().__init__(
            name=name,
            investment_style=InvestmentStyle.ARBITRAGE,  # 使用套利風格作為基礎
            risk_preference=RiskPreference.AGGRESSIVE,
            max_position_size=0.3,  # 允許較大倉位
            **parameters
        )
        
        # 索羅斯特有參數
        self.reflexivity_sensitivity = reflexivity_sensitivity
        self.macro_weight = macro_weight
        self.sentiment_weight = sentiment_weight
        self.crisis_opportunity_threshold = crisis_opportunity_threshold
        self.max_leverage = max_leverage
        self.volatility_target = volatility_target
        self.holding_period_max = holding_period_max
        self.political_risk_tolerance = political_risk_tolerance
        
        # 宏觀經濟指標關注
        self.macro_indicators = {
            'interest_rates': 0.0,
            'inflation_rate': 0.0,
            'gdp_growth': 0.0,
            'unemployment_rate': 0.0,
            'currency_strength': 0.0,
            'political_stability': 0.0
        }
        
        # 市場情緒指標
        self.sentiment_indicators = {
            'fear_greed_index': 50.0,
            'volatility_index': 20.0,
            'market_momentum': 0.0,
            'news_sentiment': 0.0,
            'institutional_flow': 0.0
        }
        
        # 反身性循環階段
        self.reflexivity_stages = [
            'initial_trend',      # 初始趨勢
            'acceleration',       # 加速階段
            'climax',            # 高潮階段
            'reversal',          # 反轉階段
            'collapse'           # 崩潰階段
        ]
        
        # 持倉追蹤
        self.current_positions: Dict[str, Dict] = {}
        self.macro_themes: List[str] = []
        
        logger.info(f"初始化索羅斯代理: {name} - 'Markets are constantly in a state of uncertainty and flux'")
    
    def make_decision(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """
        基於索羅斯投資哲學生成決策。
        
        Args:
            data: 市場數據
            market_context: 市場上下文信息
            
        Returns:
            AgentDecision: 索羅斯風格的投資決策
        """
        try:
            symbol = market_context.get('symbol', 'UNKNOWN') if market_context else 'UNKNOWN'
            
            # 檢查數據完整性
            if not self._validate_soros_data(data):
                return self._create_hold_decision(symbol, "索羅斯：'不確定性是投資的本質，但數據不足時保持謹慎'")
            
            # 宏觀經濟分析
            macro_analysis = self._analyze_macro_environment(data, market_context)
            
            # 市場情緒分析
            sentiment_analysis = self._analyze_market_sentiment(data, market_context)
            
            # 反身性分析
            reflexivity_analysis = self._analyze_reflexivity(data, macro_analysis, sentiment_analysis)
            
            # 危機機會檢測
            crisis_analysis = self._detect_crisis_opportunities(data, market_context)
            
            # 政治風險評估
            political_analysis = self._assess_political_risks(market_context)
            
            # 計算索羅斯綜合評分
            soros_score = self._calculate_soros_score(
                macro_analysis, sentiment_analysis, reflexivity_analysis,
                crisis_analysis, political_analysis
            )
            
            # 生成索羅斯風格決策
            decision = self._generate_soros_decision(
                symbol, soros_score, data, market_context
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"索羅斯代理決策生成失敗: {e}")
            return self._create_hold_decision(symbol, f"索羅斯：'當市場變得不可理解時，最好的策略是等待' - {e}")
    
    def _validate_soros_data(self, data: pd.DataFrame) -> bool:
        """驗證索羅斯分析所需數據"""
        if len(data) < 30:  # 需要足夠的歷史數據分析趨勢
            logger.warning("索羅斯分析需要至少30個週期的數據")
            return False
        
        required_columns = ['close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                logger.warning(f"索羅斯分析缺少必要數據欄位: {col}")
                return False
        
        return True
    
    def _analyze_macro_environment(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析宏觀經濟環境"""
        
        # 更新宏觀指標（從市場上下文獲取）
        if market_context:
            for indicator in self.macro_indicators:
                if indicator in market_context:
                    self.macro_indicators[indicator] = market_context[indicator]
        
        # 利率環境分析
        interest_rate_trend = self._analyze_interest_rate_trend()
        
        # 通脹環境分析
        inflation_impact = self._analyze_inflation_impact()
        
        # 經濟成長分析
        growth_outlook = self._analyze_growth_outlook()
        
        # 貨幣政策分析
        monetary_policy = self._analyze_monetary_policy()
        
        # 綜合宏觀評分
        macro_score = np.mean([
            interest_rate_trend['score'],
            inflation_impact['score'],
            growth_outlook['score'],
            monetary_policy['score']
        ])
        
        return {
            'macro_score': macro_score,
            'interest_rate_trend': interest_rate_trend,
            'inflation_impact': inflation_impact,
            'growth_outlook': growth_outlook,
            'monetary_policy': monetary_policy,
            'dominant_theme': self._identify_dominant_macro_theme()
        }
    
    def _analyze_interest_rate_trend(self) -> Dict[str, Any]:
        """分析利率趨勢"""
        interest_rate = self.macro_indicators['interest_rates']
        
        if interest_rate < 0.02:  # 超低利率
            score = 80.0
            trend = "ultra_low"
            impact = "positive"  # 有利於風險資產
        elif interest_rate < 0.05:  # 低利率
            score = 60.0
            trend = "low"
            impact = "positive"
        elif interest_rate < 0.08:  # 中等利率
            score = 40.0
            trend = "moderate"
            impact = "neutral"
        else:  # 高利率
            score = 20.0
            trend = "high"
            impact = "negative"  # 不利於風險資產
        
        return {
            'score': score,
            'trend': trend,
            'impact': impact,
            'rate_level': interest_rate
        }
    
    def _analyze_inflation_impact(self) -> Dict[str, Any]:
        """分析通脹影響"""
        inflation_rate = self.macro_indicators['inflation_rate']
        
        if inflation_rate < 0.01:  # 通縮風險
            score = 30.0
            regime = "deflation_risk"
            impact = "negative"
        elif inflation_rate < 0.03:  # 低通脹
            score = 70.0
            regime = "low_inflation"
            impact = "positive"
        elif inflation_rate < 0.05:  # 適度通脹
            score = 50.0
            regime = "moderate_inflation"
            impact = "neutral"
        else:  # 高通脹
            score = 20.0
            regime = "high_inflation"
            impact = "negative"
        
        return {
            'score': score,
            'regime': regime,
            'impact': impact,
            'inflation_level': inflation_rate
        }
    
    def _analyze_growth_outlook(self) -> Dict[str, Any]:
        """分析經濟成長前景"""
        gdp_growth = self.macro_indicators['gdp_growth']
        unemployment = self.macro_indicators['unemployment_rate']
        
        # 基於GDP成長率評分
        if gdp_growth > 0.04:  # 強勁成長
            growth_score = 80.0
            outlook = "strong"
        elif gdp_growth > 0.02:  # 適度成長
            growth_score = 60.0
            outlook = "moderate"
        elif gdp_growth > 0:  # 緩慢成長
            growth_score = 40.0
            outlook = "slow"
        else:  # 衰退
            growth_score = 20.0
            outlook = "recession"
        
        # 失業率調整
        if unemployment < 0.05:  # 低失業率
            employment_score = 80.0
        elif unemployment < 0.08:  # 適度失業率
            employment_score = 60.0
        else:  # 高失業率
            employment_score = 30.0
        
        overall_score = (growth_score + employment_score) / 2
        
        return {
            'score': overall_score,
            'outlook': outlook,
            'gdp_growth': gdp_growth,
            'unemployment_rate': unemployment
        }

    def _analyze_monetary_policy(self) -> Dict[str, Any]:
        """分析貨幣政策"""
        interest_rate = self.macro_indicators['interest_rates']
        inflation_rate = self.macro_indicators['inflation_rate']

        # 判斷政策立場
        if interest_rate < inflation_rate:  # 負實際利率
            policy_stance = "accommodative"
            score = 80.0
        elif interest_rate < inflation_rate + 0.02:  # 中性偏寬鬆
            policy_stance = "neutral_accommodative"
            score = 60.0
        elif interest_rate < inflation_rate + 0.04:  # 中性
            policy_stance = "neutral"
            score = 50.0
        else:  # 緊縮
            policy_stance = "restrictive"
            score = 30.0

        return {
            'score': score,
            'stance': policy_stance,
            'real_rate': interest_rate - inflation_rate
        }

    def _identify_dominant_macro_theme(self) -> str:
        """識別主導宏觀主題"""
        themes = []

        # 基於宏觀指標識別主題
        if self.macro_indicators['interest_rates'] < 0.02:
            themes.append("ultra_low_rates")

        if self.macro_indicators['inflation_rate'] > 0.05:
            themes.append("inflation_surge")

        if self.macro_indicators['gdp_growth'] < 0:
            themes.append("recession_risk")

        if self.macro_indicators['political_stability'] < 0.5:
            themes.append("political_uncertainty")

        return themes[0] if themes else "stable_environment"

    def _analyze_market_sentiment(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析市場情緒"""

        # 價格動量分析
        momentum_analysis = self._calculate_price_momentum(data)

        # 波動率分析
        volatility_analysis = self._analyze_volatility_regime(data)

        # 成交量分析
        volume_analysis = self._analyze_volume_patterns(data)

        # 市場廣度分析
        breadth_analysis = self._analyze_market_breadth(market_context)

        # 恐慌貪婪指數
        fear_greed_score = self._calculate_fear_greed_index(
            momentum_analysis, volatility_analysis, volume_analysis
        )

        # 綜合情緒評分
        sentiment_score = np.mean([
            momentum_analysis['score'],
            volatility_analysis['score'],
            volume_analysis['score'],
            fear_greed_score
        ])

        return {
            'sentiment_score': sentiment_score,
            'momentum_analysis': momentum_analysis,
            'volatility_analysis': volatility_analysis,
            'volume_analysis': volume_analysis,
            'fear_greed_score': fear_greed_score,
            'market_regime': self._identify_market_regime(sentiment_score)
        }

    def _calculate_price_momentum(self, data: pd.DataFrame) -> Dict[str, Any]:
        """計算價格動量"""
        if len(data) < 20:
            return {'score': 50.0, 'trend': 'neutral', 'strength': 0.0}

        # 多期間動量
        returns_5d = (data['close'].iloc[-1] / data['close'].iloc[-6] - 1)
        returns_20d = (data['close'].iloc[-1] / data['close'].iloc[-21] - 1)

        # 動量強度
        momentum_strength = (returns_5d + returns_20d) / 2

        if momentum_strength > 0.1:  # 強勁上漲
            score = 80.0
            trend = "strong_bullish"
        elif momentum_strength > 0.05:  # 適度上漲
            score = 65.0
            trend = "moderate_bullish"
        elif momentum_strength > 0:  # 小幅上漲
            score = 55.0
            trend = "weak_bullish"
        elif momentum_strength > -0.05:  # 小幅下跌
            score = 45.0
            trend = "weak_bearish"
        elif momentum_strength > -0.1:  # 適度下跌
            score = 35.0
            trend = "moderate_bearish"
        else:  # 大幅下跌
            score = 20.0
            trend = "strong_bearish"

        return {
            'score': score,
            'trend': trend,
            'strength': momentum_strength,
            'returns_5d': returns_5d,
            'returns_20d': returns_20d
        }

    def _analyze_volatility_regime(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析波動率制度"""
        if len(data) < 20:
            return {'score': 50.0, 'regime': 'normal', 'level': 0.2}

        # 計算滾動波動率
        returns = data['close'].pct_change().dropna()
        volatility = returns.rolling(window=20).std().iloc[-1] * np.sqrt(252)

        # 波動率制度分類
        if volatility > 0.4:  # 極高波動
            score = 20.0
            regime = "crisis"
        elif volatility > 0.3:  # 高波動
            score = 30.0
            regime = "high_volatility"
        elif volatility > 0.2:  # 正常波動
            score = 60.0
            regime = "normal"
        else:  # 低波動
            score = 80.0
            regime = "low_volatility"

        return {
            'score': score,
            'regime': regime,
            'level': volatility,
            'target_deviation': abs(volatility - self.volatility_target)
        }

    def _analyze_volume_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析成交量模式"""
        if len(data) < 20:
            return {'score': 50.0, 'pattern': 'normal', 'trend': 'stable'}

        # 成交量趨勢
        volume_ma_short = data['volume'].rolling(window=5).mean().iloc[-1]
        volume_ma_long = data['volume'].rolling(window=20).mean().iloc[-1]

        volume_trend_ratio = volume_ma_short / volume_ma_long

        # 價量關係
        price_change = data['close'].pct_change().iloc[-1]
        volume_change = data['volume'].pct_change().iloc[-1]

        if volume_trend_ratio > 1.5:  # 成交量激增
            if price_change > 0:
                score = 80.0
                pattern = "bullish_breakout"
            else:
                score = 20.0
                pattern = "bearish_breakdown"
        elif volume_trend_ratio > 1.2:  # 成交量增加
            score = 65.0
            pattern = "increasing_interest"
        elif volume_trend_ratio < 0.8:  # 成交量萎縮
            score = 40.0
            pattern = "declining_interest"
        else:  # 正常成交量
            score = 55.0
            pattern = "normal"

        return {
            'score': score,
            'pattern': pattern,
            'trend_ratio': volume_trend_ratio,
            'price_volume_correlation': np.corrcoef([price_change], [volume_change])[0, 1] if not np.isnan(volume_change) else 0
        }

    def _analyze_market_breadth(self, market_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """分析市場廣度"""
        if not market_context:
            return {'score': 50.0, 'breadth': 'neutral'}

        # 從市場上下文獲取廣度指標
        advance_decline_ratio = market_context.get('advance_decline_ratio', 1.0)
        new_highs_lows_ratio = market_context.get('new_highs_lows_ratio', 1.0)

        if advance_decline_ratio > 2.0:  # 強勁廣度
            breadth_score = 80.0
            breadth_signal = "strong_positive"
        elif advance_decline_ratio > 1.5:  # 良好廣度
            breadth_score = 65.0
            breadth_signal = "positive"
        elif advance_decline_ratio > 0.5:  # 中性廣度
            breadth_score = 50.0
            breadth_signal = "neutral"
        else:  # 疲弱廣度
            breadth_score = 30.0
            breadth_signal = "negative"

        return {
            'score': breadth_score,
            'breadth': breadth_signal,
            'advance_decline_ratio': advance_decline_ratio,
            'new_highs_lows_ratio': new_highs_lows_ratio
        }

    def _calculate_fear_greed_index(
        self,
        momentum_analysis: Dict[str, Any],
        volatility_analysis: Dict[str, Any],
        volume_analysis: Dict[str, Any]
    ) -> float:
        """計算恐慌貪婪指數"""

        # 權重分配
        weights = {
            'momentum': 0.4,
            'volatility': 0.3,
            'volume': 0.3
        }

        # 標準化評分到0-100
        momentum_score = momentum_analysis['score']
        volatility_score = volatility_analysis['score']
        volume_score = volume_analysis['score']

        fear_greed_index = (
            momentum_score * weights['momentum'] +
            volatility_score * weights['volatility'] +
            volume_score * weights['volume']
        )

        return fear_greed_index

    def _identify_market_regime(self, sentiment_score: float) -> str:
        """識別市場制度"""
        if sentiment_score >= 80:
            return "euphoria"
        elif sentiment_score >= 65:
            return "optimism"
        elif sentiment_score >= 50:
            return "neutral"
        elif sentiment_score >= 35:
            return "pessimism"
        else:
            return "panic"

    def _analyze_reflexivity(
        self,
        data: pd.DataFrame,
        macro_analysis: Dict[str, Any],
        sentiment_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析反身性循環"""

        # 識別反身性循環階段
        current_stage = self._identify_reflexivity_stage(data, sentiment_analysis)

        # 計算反身性強度
        reflexivity_strength = self._calculate_reflexivity_strength(
            macro_analysis, sentiment_analysis
        )

        # 預測循環方向
        cycle_direction = self._predict_cycle_direction(current_stage, reflexivity_strength)

        # 反身性機會評分
        opportunity_score = self._evaluate_reflexivity_opportunity(
            current_stage, cycle_direction, reflexivity_strength
        )

        return {
            'current_stage': current_stage,
            'reflexivity_strength': reflexivity_strength,
            'cycle_direction': cycle_direction,
            'opportunity_score': opportunity_score,
            'stage_confidence': self._calculate_stage_confidence(data, sentiment_analysis)
        }

    def _identify_reflexivity_stage(
        self,
        data: pd.DataFrame,
        sentiment_analysis: Dict[str, Any]
    ) -> str:
        """識別反身性循環階段"""

        momentum = sentiment_analysis['momentum_analysis']['strength']
        volatility = sentiment_analysis['volatility_analysis']['level']
        volume_pattern = sentiment_analysis['volume_analysis']['pattern']

        # 基於多個指標判斷階段
        if momentum > 0.05 and volatility < 0.2 and volume_pattern in ['normal', 'increasing_interest']:
            return 'initial_trend'
        elif momentum > 0.1 and volume_pattern in ['bullish_breakout', 'increasing_interest']:
            return 'acceleration'
        elif momentum > 0.15 and volatility > 0.3:
            return 'climax'
        elif momentum < 0 and volatility > 0.25:
            return 'reversal'
        elif momentum < -0.1 and volatility > 0.4:
            return 'collapse'
        else:
            return 'initial_trend'  # 默認階段

    def _calculate_reflexivity_strength(
        self,
        macro_analysis: Dict[str, Any],
        sentiment_analysis: Dict[str, Any]
    ) -> float:
        """計算反身性強度"""

        # 宏觀與市場情緒的背離程度
        macro_score = macro_analysis['macro_score']
        sentiment_score = sentiment_analysis['sentiment_score']

        # 背離越大，反身性越強
        divergence = abs(macro_score - sentiment_score) / 100.0

        # 波動率增強反身性
        volatility_factor = min(sentiment_analysis['volatility_analysis']['level'] / 0.3, 2.0)

        # 成交量確認反身性
        volume_factor = 1.0
        if sentiment_analysis['volume_analysis']['pattern'] in ['bullish_breakout', 'bearish_breakdown']:
            volume_factor = 1.5

        reflexivity_strength = divergence * volatility_factor * volume_factor

        return min(reflexivity_strength, 1.0)

    def _predict_cycle_direction(self, current_stage: str, reflexivity_strength: float) -> str:
        """預測循環方向"""

        stage_transitions = {
            'initial_trend': 'acceleration' if reflexivity_strength > 0.3 else 'stable',
            'acceleration': 'climax' if reflexivity_strength > 0.6 else 'continuation',
            'climax': 'reversal' if reflexivity_strength > 0.8 else 'peak',
            'reversal': 'collapse' if reflexivity_strength > 0.7 else 'stabilization',
            'collapse': 'bottom' if reflexivity_strength < 0.3 else 'continuation'
        }

        return stage_transitions.get(current_stage, 'uncertain')

    def _evaluate_reflexivity_opportunity(
        self,
        current_stage: str,
        cycle_direction: str,
        reflexivity_strength: float
    ) -> float:
        """評估反身性機會"""

        # 不同階段的機會評分
        stage_scores = {
            'initial_trend': 70.0,    # 早期趨勢，機會較好
            'acceleration': 60.0,     # 加速階段，仍有機會
            'climax': 30.0,          # 高潮階段，風險較高
            'reversal': 80.0,        # 反轉階段，逆向機會
            'collapse': 90.0         # 崩潰階段，最佳逆向機會
        }

        base_score = stage_scores.get(current_stage, 50.0)

        # 根據循環方向調整
        direction_adjustments = {
            'acceleration': 10.0,
            'continuation': 0.0,
            'reversal': 20.0,
            'collapse': 30.0,
            'bottom': 40.0,
            'stabilization': -10.0
        }

        direction_adjustment = direction_adjustments.get(cycle_direction, 0.0)

        # 反身性強度調整
        strength_adjustment = reflexivity_strength * 20.0

        opportunity_score = base_score + direction_adjustment + strength_adjustment

        return min(max(opportunity_score, 0.0), 100.0)

    def _calculate_stage_confidence(
        self,
        data: pd.DataFrame,
        sentiment_analysis: Dict[str, Any]
    ) -> float:
        """計算階段判斷信心度"""

        # 基於多個指標的一致性
        momentum_strength = abs(sentiment_analysis['momentum_analysis']['strength'])
        volatility_clarity = 1.0 - abs(sentiment_analysis['volatility_analysis']['target_deviation'])
        volume_clarity = 1.0 if sentiment_analysis['volume_analysis']['pattern'] != 'normal' else 0.5

        confidence = (momentum_strength * 2 + volatility_clarity + volume_clarity) / 4

        return min(max(confidence, 0.0), 1.0)

    def _detect_crisis_opportunities(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """檢測危機機會"""

        # 價格暴跌檢測
        crash_signals = self._detect_market_crash(data)

        # 流動性危機檢測
        liquidity_crisis = self._detect_liquidity_crisis(data, market_context)

        # 政策反應機會
        policy_response = self._analyze_policy_response_opportunity(market_context)

        # 結構性變化機會
        structural_change = self._detect_structural_changes(market_context)

        # 綜合危機機會評分
        crisis_score = np.mean([
            crash_signals['opportunity_score'],
            liquidity_crisis['opportunity_score'],
            policy_response['opportunity_score'],
            structural_change['opportunity_score']
        ])

        return {
            'crisis_score': crisis_score,
            'crash_signals': crash_signals,
            'liquidity_crisis': liquidity_crisis,
            'policy_response': policy_response,
            'structural_change': structural_change,
            'is_crisis_opportunity': crisis_score >= self.crisis_opportunity_threshold * 100
        }

    def _detect_market_crash(self, data: pd.DataFrame) -> Dict[str, Any]:
        """檢測市場崩盤"""
        if len(data) < 10:
            return {'opportunity_score': 0.0, 'crash_detected': False}

        # 短期大幅下跌
        recent_return = (data['close'].iloc[-1] / data['close'].iloc[-6] - 1)

        # 波動率激增
        returns = data['close'].pct_change().dropna()
        recent_volatility = returns.tail(5).std() * np.sqrt(252)

        crash_detected = recent_return < -0.15 and recent_volatility > 0.4

        if crash_detected:
            # 下跌越多，機會越大（索羅斯的逆向思維）
            opportunity_score = min(abs(recent_return) * 500, 100.0)
        else:
            opportunity_score = 0.0

        return {
            'opportunity_score': opportunity_score,
            'crash_detected': crash_detected,
            'recent_return': recent_return,
            'volatility_spike': recent_volatility > 0.4
        }

    def _detect_liquidity_crisis(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """檢測流動性危機"""

        # 成交量異常
        if len(data) >= 20:
            volume_ma = data['volume'].rolling(window=20).mean().iloc[-1]
            recent_volume = data['volume'].iloc[-1]
            volume_anomaly = recent_volume < volume_ma * 0.5  # 成交量大幅萎縮
        else:
            volume_anomaly = False

        # 價差擴大（從市場上下文獲取）
        bid_ask_spread = market_context.get('bid_ask_spread', 0.001) if market_context else 0.001
        spread_widening = bid_ask_spread > 0.005

        liquidity_crisis = volume_anomaly and spread_widening

        opportunity_score = 70.0 if liquidity_crisis else 20.0

        return {
            'opportunity_score': opportunity_score,
            'liquidity_crisis': liquidity_crisis,
            'volume_anomaly': volume_anomaly,
            'spread_widening': spread_widening
        }

    def _analyze_policy_response_opportunity(self, market_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """分析政策反應機會"""
        if not market_context:
            return {'opportunity_score': 50.0, 'policy_support': False}

        # 央行政策支持
        policy_support = market_context.get('central_bank_support', False)
        fiscal_stimulus = market_context.get('fiscal_stimulus', False)

        if policy_support and fiscal_stimulus:
            opportunity_score = 80.0
        elif policy_support or fiscal_stimulus:
            opportunity_score = 60.0
        else:
            opportunity_score = 30.0

        return {
            'opportunity_score': opportunity_score,
            'policy_support': policy_support,
            'fiscal_stimulus': fiscal_stimulus
        }

    def _detect_structural_changes(self, market_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """檢測結構性變化"""
        if not market_context:
            return {'opportunity_score': 50.0, 'structural_shift': False}

        # 技術革新、監管變化、地緣政治等
        tech_disruption = market_context.get('tech_disruption', False)
        regulatory_change = market_context.get('regulatory_change', False)
        geopolitical_shift = market_context.get('geopolitical_shift', False)

        structural_factors = sum([tech_disruption, regulatory_change, geopolitical_shift])

        if structural_factors >= 2:
            opportunity_score = 75.0
            structural_shift = True
        elif structural_factors == 1:
            opportunity_score = 55.0
            structural_shift = True
        else:
            opportunity_score = 30.0
            structural_shift = False

        return {
            'opportunity_score': opportunity_score,
            'structural_shift': structural_shift,
            'tech_disruption': tech_disruption,
            'regulatory_change': regulatory_change,
            'geopolitical_shift': geopolitical_shift
        }

    def _assess_political_risks(self, market_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """評估政治風險"""
        if not market_context:
            return {'political_risk_score': 50.0, 'risk_level': 'moderate'}

        # 政治穩定性指標
        political_stability = market_context.get('political_stability', 0.7)
        election_uncertainty = market_context.get('election_uncertainty', False)
        policy_uncertainty = market_context.get('policy_uncertainty', False)
        geopolitical_tension = market_context.get('geopolitical_tension', False)

        # 計算政治風險評分
        risk_factors = sum([election_uncertainty, policy_uncertainty, geopolitical_tension])
        base_risk = (1 - political_stability) * 100

        political_risk_score = base_risk + risk_factors * 15
        political_risk_score = min(political_risk_score, 100.0)

        # 風險等級
        if political_risk_score >= 70:
            risk_level = 'high'
        elif political_risk_score >= 40:
            risk_level = 'moderate'
        else:
            risk_level = 'low'

        return {
            'political_risk_score': political_risk_score,
            'risk_level': risk_level,
            'political_stability': political_stability,
            'election_uncertainty': election_uncertainty,
            'policy_uncertainty': policy_uncertainty,
            'geopolitical_tension': geopolitical_tension
        }

    def _calculate_soros_score(
        self,
        macro_analysis: Dict[str, Any],
        sentiment_analysis: Dict[str, Any],
        reflexivity_analysis: Dict[str, Any],
        crisis_analysis: Dict[str, Any],
        political_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """計算索羅斯綜合評分"""

        # 權重分配（反映索羅斯的投資重點）
        weights = {
            'macro_environment': self.macro_weight,           # 0.4
            'market_sentiment': self.sentiment_weight,        # 0.3
            'reflexivity': 0.15,                             # 反身性分析
            'crisis_opportunity': 0.1,                       # 危機機會
            'political_risk': 0.05                          # 政治風險
        }

        # 各組件評分
        macro_score = macro_analysis['macro_score']
        sentiment_score = sentiment_analysis['sentiment_score']
        reflexivity_score = reflexivity_analysis['opportunity_score']
        crisis_score = crisis_analysis['crisis_score']
        political_score = 100 - political_analysis['political_risk_score']  # 風險越低評分越高

        # 計算加權總分
        total_score = (
            macro_score * weights['macro_environment'] +
            sentiment_score * weights['market_sentiment'] +
            reflexivity_score * weights['reflexivity'] +
            crisis_score * weights['crisis_opportunity'] +
            political_score * weights['political_risk']
        )

        return {
            'total_score': total_score,
            'macro_score': macro_score,
            'sentiment_score': sentiment_score,
            'reflexivity_score': reflexivity_score,
            'crisis_score': crisis_score,
            'political_score': political_score,
            'weights': weights,
            'dominant_theme': macro_analysis.get('dominant_theme', 'unknown')
        }

    def _generate_soros_decision(
        self,
        symbol: str,
        soros_score: Dict[str, Any],
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]]
    ) -> AgentDecision:
        """生成索羅斯風格的投資決策"""
        current_time = datetime.now()
        total_score = soros_score['total_score']

        # 索羅斯的決策閾值（更激進）
        buy_threshold = 70.0    # 機會明確時果斷行動
        sell_threshold = 30.0   # 趨勢反轉時快速退出

        # 檢查是否已持有該股票
        is_holding = symbol in self.current_positions

        # 持有期間檢查（索羅斯較短期）
        if is_holding:
            position_info = self.current_positions[symbol]
            holding_days = (current_time - position_info['entry_time']).days

            if holding_days >= self.holding_period_max:
                # 達到最大持有期間，考慮退出
                action = -1
                confidence = 0.7
                reasoning = f"索羅斯：'市場總是錯的，要在錯誤被糾正前退出' - 持有{holding_days}天已達上限"
                if symbol in self.current_positions:
                    del self.current_positions[symbol]
            elif total_score <= sell_threshold:
                # 趨勢反轉，快速退出
                action = -1
                confidence = 0.8
                reasoning = self._generate_soros_sell_reasoning(soros_score, data)
                if symbol in self.current_positions:
                    del self.current_positions[symbol]
            else:
                # 繼續持有
                action = 0
                confidence = 0.6
                reasoning = self._generate_soros_hold_reasoning(soros_score, holding_days)

        elif total_score >= buy_threshold:
            # 機會明確，果斷進入
            action = 1
            confidence = min(0.95, total_score / 100.0)
            reasoning = self._generate_soros_buy_reasoning(soros_score, market_context)

            # 記錄持倉
            self.current_positions[symbol] = {
                'entry_time': current_time,
                'entry_score': total_score,
                'entry_price': data['close'].iloc[-1],
                'reflexivity_stage': soros_score.get('reflexivity_stage', 'unknown'),
                'macro_theme': soros_score.get('dominant_theme', 'unknown')
            }

        else:
            # 觀望
            action = 0
            confidence = 0.5
            reasoning = f"索羅斯：'不確定時保持靈活' - 評分{total_score:.1f}，等待更明確信號"

        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=current_time,
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            expected_return=self._estimate_soros_return(soros_score),
            risk_assessment=self._assess_soros_risk(soros_score),
            position_size=self._calculate_soros_position_size(total_score, soros_score),
            metadata={
                'soros_score': total_score,
                'reflexivity_stage': soros_score.get('reflexivity_stage', 'unknown'),
                'macro_theme': soros_score.get('dominant_theme', 'unknown'),
                'crisis_opportunity': soros_score.get('crisis_score', 0) >= 70,
                'political_risk': soros_score.get('political_score', 50),
                'investment_style': 'soros_macro',
                'max_holding_period_days': self.holding_period_max
            }
        )

    def _generate_soros_buy_reasoning(
        self,
        soros_score: Dict[str, Any],
        market_context: Optional[Dict[str, Any]]
    ) -> str:
        """生成索羅斯風格的買入推理"""
        reasons = []

        if soros_score['macro_score'] >= 70:
            reasons.append("宏觀環境有利")

        if soros_score['reflexivity_score'] >= 70:
            reasons.append("反身性機會明確")

        if soros_score['crisis_score'] >= 70:
            reasons.append("危機中發現機會")

        if soros_score.get('dominant_theme'):
            reasons.append(f"主題投資：{soros_score['dominant_theme']}")

        base_reason = f"索羅斯宏觀投資（評分{soros_score['total_score']:.1f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons) + " - '市場總是錯的，關鍵是比市場更早發現錯誤'"
        else:
            return base_reason + " - '在不確定性中尋找確定性'"

    def _generate_soros_sell_reasoning(self, soros_score: Dict[str, Any], data: pd.DataFrame) -> str:
        """生成索羅斯風格的賣出推理"""
        reasons = []

        if soros_score['reflexivity_score'] < 40:
            reasons.append("反身性循環反轉")

        if soros_score['macro_score'] < 40:
            reasons.append("宏觀環境惡化")

        if soros_score['political_score'] < 30:
            reasons.append("政治風險上升")

        base_reason = f"索羅斯退出決策（評分{soros_score['total_score']:.1f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons) + " - '承認錯誤是投資成功的關鍵'"
        else:
            return base_reason + " - '當趨勢改變時，要比市場更快行動'"

    def _generate_soros_hold_reasoning(self, soros_score: Dict[str, Any], holding_days: int) -> str:
        """生成索羅斯風格的持有推理"""
        return (f"索羅斯持有策略：已持有{holding_days}天，評分{soros_score['total_score']:.1f} - "
                "'保持靈活，隨時準備調整'")

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
            risk_assessment=0.6,  # 索羅斯風格風險較高
            position_size=0.0
        )

    def _estimate_soros_return(self, soros_score: Dict[str, Any]) -> float:
        """估算索羅斯風格的預期收益率"""
        # 索羅斯追求高收益
        base_return = 0.15  # 基準15%年化收益率

        # 基於綜合評分調整
        score_factor = soros_score['total_score'] / 100.0

        # 反身性機會獎勵
        reflexivity_bonus = (soros_score['reflexivity_score'] - 50) / 200.0

        # 危機機會獎勵
        crisis_bonus = (soros_score['crisis_score'] - 50) / 500.0

        expected_return = base_return * score_factor + reflexivity_bonus + crisis_bonus

        return max(0.0, min(expected_return, 0.5))  # 0-50%範圍

    def _assess_soros_risk(self, soros_score: Dict[str, Any]) -> float:
        """評估索羅斯風格的投資風險"""
        # 索羅斯風格風險較高
        base_risk = 0.6

        # 政治風險調整
        political_risk_adjustment = (100 - soros_score['political_score']) / 200.0

        # 反身性風險調整
        reflexivity_risk = 0.2 if soros_score['reflexivity_score'] > 80 else 0.0

        overall_risk = base_risk + political_risk_adjustment + reflexivity_risk

        return min(overall_risk, 1.0)

    def _calculate_soros_position_size(self, total_score: float, soros_score: Dict[str, Any]) -> float:
        """計算索羅斯風格的倉位大小"""
        # 索羅斯會根據信心度調整倉位
        base_size = self.max_position_size

        # 基於評分調整
        confidence_factor = total_score / 100.0

        # 危機機會時增加倉位
        crisis_factor = 1.2 if soros_score['crisis_score'] >= 70 else 1.0

        # 反身性機會時增加倉位
        reflexivity_factor = 1.1 if soros_score['reflexivity_score'] >= 70 else 1.0

        position_size = base_size * confidence_factor * crisis_factor * reflexivity_factor

        return min(position_size, self.max_position_size)

    def get_investment_philosophy(self) -> str:
        """獲取索羅斯投資哲學描述"""
        return (
            "索羅斯投資哲學：'市場總是錯的，關鍵是發現市場的錯誤並從中獲利。' "
            "基於反身性理論，關注宏觀經濟趨勢、市場情緒和政治事件的相互作用。"
            f"反身性敏感度：{self.reflexivity_sensitivity}；最大槓桿：{self.max_leverage}倍；"
            f"最大持有期：{self.holding_period_max}天。"
            "核心理念：'在不確定性中尋找確定性，在危機中發現機會。'"
        )

    def get_soros_insights(self) -> List[str]:
        """獲取索羅斯投資智慧"""
        return [
            "市場總是錯的，關鍵是發現錯誤並從中獲利。",
            "不確定性是投資的本質，要學會在不確定中尋找確定性。",
            "承認錯誤是投資成功的關鍵。",
            "市場參與者的認知會影響市場，而市場又會影響參與者的認知。",
            "在危機中尋找機會，在繁榮中保持警惕。",
            "保持靈活，隨時準備改變策略。",
            "當趨勢改變時，要比市場更快行動。",
            "投資不僅是分析，更是理解人性和市場心理。"
        ]

    def get_current_macro_themes(self) -> List[str]:
        """獲取當前宏觀主題"""
        return self.macro_themes.copy()

    def add_macro_theme(self, theme: str) -> None:
        """添加宏觀主題"""
        if theme not in self.macro_themes:
            self.macro_themes.append(theme)
            logger.info(f"索羅斯代理添加宏觀主題: {theme}")

    def remove_macro_theme(self, theme: str) -> None:
        """移除宏觀主題"""
        if theme in self.macro_themes:
            self.macro_themes.remove(theme)
            logger.info(f"索羅斯代理移除宏觀主題: {theme}")

    def __str__(self) -> str:
        """字符串表示"""
        return f"SorosAgent(positions={len(self.current_positions)}, themes={len(self.macro_themes)})"
