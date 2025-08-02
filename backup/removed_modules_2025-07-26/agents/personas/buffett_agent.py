# -*- coding: utf-8 -*-
"""
巴菲特代理模組

此模組實現模擬華倫·巴菲特投資風格的AI代理。

投資哲學：
- "買入並持有"長期投資策略
- 關注企業內在價值和護城河
- 重視管理層品質和企業文化
- 集中投資於理解的企業
- 安全邊際和價值投資原則

核心特色：
- 長期投資視角（5-10年以上）
- 關注企業競爭優勢和護城河
- 重視現金流和盈利能力
- 偏好簡單易懂的商業模式
- 注重管理層誠信和能力
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..base import TradingAgent, AgentDecision, InvestmentStyle, RiskPreference
from ..styles.value_investor import ValueInvestor

# 設定日誌
logger = logging.getLogger(__name__)


class BuffettAgent(ValueInvestor):
    """
    巴菲特代理 - 模擬華倫·巴菲特的投資風格。
    
    繼承ValueInvestor並添加巴菲特特有的投資理念：
    - 極長期投資視角
    - 護城河分析
    - 管理層評估
    - 集中投資策略
    - 簡單商業模式偏好
    
    Attributes:
        moat_analysis_enabled (bool): 是否啟用護城河分析
        management_score_weight (float): 管理層評分權重
        business_simplicity_weight (float): 商業模式簡單性權重
        concentration_threshold (float): 集中投資閾值
        min_holding_years (int): 最小持有年數
        cash_preference_threshold (float): 現金偏好閾值
        brand_value_multiplier (float): 品牌價值乘數
    """
    
    def __init__(
        self,
        name: str = "BuffettAgent",
        moat_analysis_enabled: bool = True,
        management_score_weight: float = 0.25,
        business_simplicity_weight: float = 0.15,
        concentration_threshold: float = 0.25,
        min_holding_years: int = 5,
        cash_preference_threshold: float = 0.15,
        brand_value_multiplier: float = 1.2,
        **parameters: Any
    ) -> None:
        """
        初始化巴菲特代理。
        
        Args:
            name: 代理名稱
            moat_analysis_enabled: 是否啟用護城河分析
            management_score_weight: 管理層評分權重
            business_simplicity_weight: 商業模式簡單性權重
            concentration_threshold: 集中投資閾值
            min_holding_years: 最小持有年數
            cash_preference_threshold: 現金偏好閾值
            brand_value_multiplier: 品牌價值乘數
            **parameters: 其他策略參數
        """
        # 設定巴菲特風格的價值投資參數
        buffett_params = {
            'pe_threshold': 20.0,  # 相對寬鬆的P/E要求
            'pb_threshold': 3.0,   # 關注品牌價值，P/B可以較高
            'roe_threshold': 0.15, # 高ROE要求
            'debt_ratio_threshold': 0.4,  # 適度負債容忍
            'dividend_yield_min': 0.0,    # 不強制要求股息
            'safety_margin': 0.3,  # 高安全邊際要求
            'holding_period_min': min_holding_years * 365,  # 極長期持有
            'max_position_size': concentration_threshold,   # 允許集中投資
        }
        
        # 合併參數
        buffett_params.update(parameters)
        
        super().__init__(
            name=name,
            **buffett_params
        )
        
        # 巴菲特特有參數
        self.moat_analysis_enabled = moat_analysis_enabled
        self.management_score_weight = management_score_weight
        self.business_simplicity_weight = business_simplicity_weight
        self.concentration_threshold = concentration_threshold
        self.min_holding_years = min_holding_years
        self.cash_preference_threshold = cash_preference_threshold
        self.brand_value_multiplier = brand_value_multiplier
        
        # 巴菲特投資組合特徵
        self.preferred_sectors = [
            'consumer_goods', 'financial_services', 'insurance',
            'utilities', 'railroads', 'food_beverage'
        ]
        self.avoided_sectors = [
            'technology', 'biotech', 'mining', 'airlines'  # 歷史上較少投資的領域
        ]
        
        # 護城河類型
        self.moat_types = {
            'brand_moat': 0.0,      # 品牌護城河
            'cost_moat': 0.0,       # 成本護城河
            'network_moat': 0.0,    # 網絡效應護城河
            'switching_moat': 0.0,  # 轉換成本護城河
            'regulatory_moat': 0.0  # 監管護城河
        }
        
        logger.info(f"初始化巴菲特代理: {name} - 'Be fearful when others are greedy'")
    
    def make_decision(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """
        基於巴菲特投資哲學生成決策。
        
        Args:
            data: 市場數據
            market_context: 市場上下文信息
            
        Returns:
            AgentDecision: 巴菲特風格的投資決策
        """
        try:
            symbol = market_context.get('symbol', 'UNKNOWN') if market_context else 'UNKNOWN'
            
            # 檢查數據完整性
            if not self._validate_buffett_data(data):
                return self._create_hold_decision(symbol, "數據不完整，巴菲特：'投資你不了解的東西是危險的'")
            
            # 基礎價值投資分析
            fundamentals = self._extract_fundamentals(data)
            
            # 巴菲特特有分析
            buffett_analysis = self._perform_buffett_analysis(fundamentals, market_context)
            
            # 護城河分析
            moat_analysis = self._analyze_economic_moat(fundamentals, market_context)
            
            # 管理層評估
            management_analysis = self._evaluate_management(fundamentals, market_context)
            
            # 商業模式評估
            business_model_analysis = self._evaluate_business_model(fundamentals, market_context)
            
            # 市場情緒分析（逆向投資）
            market_sentiment = self._analyze_market_sentiment(data, market_context)
            
            # 計算巴菲特綜合評分
            buffett_score = self._calculate_buffett_score(
                buffett_analysis, moat_analysis, management_analysis,
                business_model_analysis, market_sentiment
            )
            
            # 生成巴菲特風格決策
            decision = self._generate_buffett_decision(
                symbol, buffett_score, fundamentals, market_context
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"巴菲特代理決策生成失敗: {e}")
            return self._create_hold_decision(symbol, f"巴菲特：'當你不確定時，什麼都不做是最好的選擇' - {e}")
    
    def _validate_buffett_data(self, data: pd.DataFrame) -> bool:
        """驗證巴菲特分析所需數據"""
        # 基礎價值投資數據驗證
        if not super()._validate_data(data):
            return False
        
        # 巴菲特特有數據要求
        buffett_required = ['market_cap', 'free_cash_flow', 'revenue_stability']
        
        latest_row = data.iloc[-1] if len(data) > 0 else None
        if latest_row is None:
            return False
        
        for col in buffett_required:
            if col in data.columns and pd.isna(latest_row[col]):
                logger.warning(f"巴菲特分析缺少關鍵數據: {col}")
        
        return True
    
    def _perform_buffett_analysis(
        self,
        fundamentals: Dict[str, float],
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行巴菲特特有分析"""
        
        # 企業規模分析（巴菲特偏好大型企業）
        market_cap = fundamentals.get('market_cap', 0)
        size_score = self._evaluate_company_size(market_cap)
        
        # 現金流分析（巴菲特重視自由現金流）
        free_cash_flow = fundamentals.get('free_cash_flow', 0)
        cash_flow_score = self._evaluate_cash_flow_quality(free_cash_flow, fundamentals)
        
        # 盈利穩定性分析
        earnings_stability = self._evaluate_earnings_stability(fundamentals)
        
        # 資本配置效率
        capital_allocation_score = self._evaluate_capital_allocation(fundamentals)
        
        # 長期成長潛力
        long_term_growth_score = self._evaluate_long_term_growth(fundamentals)
        
        return {
            'size_score': size_score,
            'cash_flow_score': cash_flow_score,
            'earnings_stability': earnings_stability,
            'capital_allocation_score': capital_allocation_score,
            'long_term_growth_score': long_term_growth_score
        }
    
    def _evaluate_company_size(self, market_cap: float) -> float:
        """評估企業規模（巴菲特偏好大型企業）"""
        if market_cap >= 50_000_000_000:  # 500億以上
            return 100.0
        elif market_cap >= 10_000_000_000:  # 100億以上
            return 80.0
        elif market_cap >= 1_000_000_000:   # 10億以上
            return 60.0
        else:
            return 20.0  # 小型企業評分較低
    
    def _evaluate_cash_flow_quality(self, free_cash_flow: float, fundamentals: Dict[str, float]) -> float:
        """評估現金流品質"""
        revenue = fundamentals.get('revenue', 1)
        if revenue <= 0:
            return 0.0
        
        # 自由現金流佔營收比率
        fcf_margin = free_cash_flow / revenue
        
        if fcf_margin >= 0.15:  # 15%以上優秀
            return 100.0
        elif fcf_margin >= 0.10:  # 10%以上良好
            return 80.0
        elif fcf_margin >= 0.05:  # 5%以上一般
            return 60.0
        elif fcf_margin > 0:     # 正值
            return 40.0
        else:
            return 0.0  # 負現金流
    
    def _evaluate_earnings_stability(self, fundamentals: Dict[str, float]) -> float:
        """評估盈利穩定性"""
        # 簡化實現：基於ROE穩定性和成長率
        roe = fundamentals.get('roe', 0)
        earnings_growth = fundamentals.get('earnings_growth', 0)
        
        # ROE穩定性評分
        if roe >= 0.15 and roe <= 0.30:  # 穩定的高ROE
            roe_stability = 80.0
        elif roe >= 0.10:
            roe_stability = 60.0
        else:
            roe_stability = 20.0
        
        # 成長穩定性評分
        if 0.05 <= earnings_growth <= 0.15:  # 穩定成長
            growth_stability = 80.0
        elif earnings_growth > 0:
            growth_stability = 60.0
        else:
            growth_stability = 20.0
        
        return (roe_stability + growth_stability) / 2
    
    def _evaluate_capital_allocation(self, fundamentals: Dict[str, float]) -> float:
        """評估資本配置效率"""
        roe = fundamentals.get('roe', 0)
        debt_ratio = fundamentals.get('debt_ratio', 0)
        dividend_yield = fundamentals.get('dividend_yield', 0)
        
        # 高ROE + 適度負債 + 合理股息 = 良好資本配置
        score = 0.0
        
        # ROE評分
        if roe >= 0.20:
            score += 40.0
        elif roe >= 0.15:
            score += 30.0
        elif roe >= 0.10:
            score += 20.0
        
        # 負債評分
        if debt_ratio <= 0.3:
            score += 30.0
        elif debt_ratio <= 0.5:
            score += 20.0
        else:
            score += 10.0
        
        # 股息政策評分
        if 0.01 <= dividend_yield <= 0.04:  # 合理股息
            score += 30.0
        elif dividend_yield > 0:
            score += 20.0
        else:
            score += 10.0  # 不分紅也可以接受（如果有更好的投資機會）
        
        return score
    
    def _evaluate_long_term_growth(self, fundamentals: Dict[str, float]) -> float:
        """評估長期成長潛力"""
        revenue_growth = fundamentals.get('revenue_growth', 0)
        earnings_growth = fundamentals.get('earnings_growth', 0)
        roe = fundamentals.get('roe', 0)
        
        # 巴菲特偏好穩定而非爆發性成長
        score = 0.0
        
        # 營收成長評分
        if 0.05 <= revenue_growth <= 0.12:  # 穩定成長
            score += 35.0
        elif revenue_growth > 0:
            score += 25.0
        
        # 盈利成長評分
        if 0.08 <= earnings_growth <= 0.15:  # 穩定盈利成長
            score += 35.0
        elif earnings_growth > 0:
            score += 25.0
        
        # ROE趨勢評分
        if roe >= 0.15:  # 高ROE支撐長期成長
            score += 30.0
        elif roe >= 0.10:
            score += 20.0
        
        return score

    def _analyze_economic_moat(
        self,
        fundamentals: Dict[str, float],
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析經濟護城河"""
        if not self.moat_analysis_enabled:
            return {'total_moat_score': 50.0, 'moat_types': {}}

        moat_scores = {}

        # 品牌護城河（基於毛利率和市場地位）
        gross_margin = fundamentals.get('gross_margin', 0)
        brand_score = min(gross_margin * 200, 100.0) if gross_margin > 0.3 else 0.0
        moat_scores['brand_moat'] = brand_score

        # 成本護城河（基於成本效率）
        operating_margin = fundamentals.get('operating_margin', 0)
        cost_score = min(operating_margin * 250, 100.0) if operating_margin > 0.2 else 0.0
        moat_scores['cost_moat'] = cost_score

        # 網絡效應護城河（基於市場份額和用戶黏性）
        market_share = market_context.get('market_share', 0.1) if market_context else 0.1
        network_score = min(market_share * 500, 100.0) if market_share > 0.2 else 0.0
        moat_scores['network_moat'] = network_score

        # 轉換成本護城河（基於客戶忠誠度）
        customer_retention = market_context.get('customer_retention', 0.8) if market_context else 0.8
        switching_score = min((customer_retention - 0.7) * 333, 100.0) if customer_retention > 0.7 else 0.0
        moat_scores['switching_moat'] = switching_score

        # 監管護城河（基於行業特性）
        sector = market_context.get('sector', '') if market_context else ''
        regulatory_score = 80.0 if sector in ['utilities', 'financial_services', 'insurance'] else 20.0
        moat_scores['regulatory_moat'] = regulatory_score

        # 計算總護城河評分
        total_moat_score = np.mean(list(moat_scores.values()))

        return {
            'total_moat_score': total_moat_score,
            'moat_types': moat_scores,
            'dominant_moat': max(moat_scores.items(), key=lambda x: x[1])[0] if moat_scores else 'none'
        }

    def _evaluate_management(
        self,
        fundamentals: Dict[str, float],
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """評估管理層品質"""
        # 簡化的管理層評估（實際應包含更多定性分析）

        # 資本配置能力（基於ROE趨勢）
        roe = fundamentals.get('roe', 0)
        capital_allocation_score = min(roe * 500, 100.0) if roe > 0.15 else 50.0

        # 誠信度（基於財務透明度）
        debt_ratio = fundamentals.get('debt_ratio', 0)
        transparency_score = 100.0 - min(debt_ratio * 100, 50.0)  # 低負債暗示保守管理

        # 股東導向（基於股息政策和回購）
        dividend_yield = fundamentals.get('dividend_yield', 0)
        shareholder_focus_score = 70.0 if dividend_yield > 0 else 60.0

        # 長期視野（基於R&D投資）
        rd_intensity = market_context.get('rd_intensity', 0.02) if market_context else 0.02
        long_term_vision_score = min(rd_intensity * 2000, 100.0) if rd_intensity > 0.03 else 50.0

        management_score = np.mean([
            capital_allocation_score,
            transparency_score,
            shareholder_focus_score,
            long_term_vision_score
        ])

        return {
            'management_score': management_score,
            'capital_allocation_score': capital_allocation_score,
            'transparency_score': transparency_score,
            'shareholder_focus_score': shareholder_focus_score,
            'long_term_vision_score': long_term_vision_score
        }

    def _evaluate_business_model(
        self,
        fundamentals: Dict[str, float],
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """評估商業模式"""
        sector = market_context.get('sector', '') if market_context else ''

        # 商業模式簡單性評分
        simplicity_score = 100.0 if sector in self.preferred_sectors else 30.0
        if sector in self.avoided_sectors:
            simplicity_score = 10.0

        # 可預測性評分（基於收入穩定性）
        revenue_stability = fundamentals.get('revenue_stability', 0.8)
        predictability_score = min(revenue_stability * 125, 100.0)

        # 競爭優勢評分（基於毛利率）
        gross_margin = fundamentals.get('gross_margin', 0)
        competitive_advantage_score = min(gross_margin * 200, 100.0) if gross_margin > 0.3 else 50.0

        # 現金生成能力評分
        free_cash_flow = fundamentals.get('free_cash_flow', 0)
        revenue = fundamentals.get('revenue', 1)
        cash_generation_score = min((free_cash_flow / revenue) * 500, 100.0) if revenue > 0 and free_cash_flow > 0 else 20.0

        business_model_score = np.mean([
            simplicity_score,
            predictability_score,
            competitive_advantage_score,
            cash_generation_score
        ])

        return {
            'business_model_score': business_model_score,
            'simplicity_score': simplicity_score,
            'predictability_score': predictability_score,
            'competitive_advantage_score': competitive_advantage_score,
            'cash_generation_score': cash_generation_score
        }

    def _analyze_market_sentiment(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析市場情緒（巴菲特的逆向投資思維）"""
        # 價格動量分析（巴菲特喜歡在下跌時買入）
        if len(data) >= 20:
            recent_return = (data['close'].iloc[-1] / data['close'].iloc[-20] - 1)

            # 逆向投資評分：下跌越多，評分越高
            if recent_return <= -0.2:  # 下跌20%以上
                sentiment_score = 100.0
                sentiment_signal = "extreme_fear"
            elif recent_return <= -0.1:  # 下跌10-20%
                sentiment_score = 80.0
                sentiment_signal = "fear"
            elif recent_return <= 0:    # 小幅下跌
                sentiment_score = 60.0
                sentiment_signal = "neutral_negative"
            elif recent_return <= 0.1:  # 小幅上漲
                sentiment_score = 40.0
                sentiment_signal = "neutral_positive"
            else:                       # 大幅上漲
                sentiment_score = 20.0
                sentiment_signal = "greed"
        else:
            sentiment_score = 50.0
            sentiment_signal = "insufficient_data"
            recent_return = 0.0

        # 估值水平分析
        pe_ratio = data['pe_ratio'].iloc[-1] if 'pe_ratio' in data.columns and len(data) > 0 else 15.0
        valuation_sentiment = "cheap" if pe_ratio < 15 else "expensive" if pe_ratio > 25 else "fair"

        return {
            'sentiment_score': sentiment_score,
            'sentiment_signal': sentiment_signal,
            'recent_return': recent_return,
            'valuation_sentiment': valuation_sentiment,
            'contrarian_opportunity': sentiment_score >= 80.0
        }

    def _calculate_buffett_score(
        self,
        buffett_analysis: Dict[str, Any],
        moat_analysis: Dict[str, Any],
        management_analysis: Dict[str, Any],
        business_model_analysis: Dict[str, Any],
        market_sentiment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """計算巴菲特綜合評分"""

        # 權重分配（反映巴菲特的投資重點）
        weights = {
            'business_quality': 0.30,    # 商業品質最重要
            'moat_strength': 0.25,       # 護城河次之
            'management_quality': 0.20,  # 管理層品質
            'valuation': 0.15,          # 估值
            'market_timing': 0.10       # 市場時機（逆向投資）
        }

        # 各組件評分
        business_quality_score = np.mean([
            buffett_analysis['cash_flow_score'],
            buffett_analysis['earnings_stability'],
            business_model_analysis['business_model_score']
        ])

        moat_strength_score = moat_analysis['total_moat_score']
        management_quality_score = management_analysis['management_score']

        # 估值評分（使用父類方法）
        valuation_score = 75.0  # 簡化處理，實際應調用父類方法

        market_timing_score = market_sentiment['sentiment_score']

        # 計算加權總分
        total_score = (
            business_quality_score * weights['business_quality'] +
            moat_strength_score * weights['moat_strength'] +
            management_quality_score * weights['management_quality'] +
            valuation_score * weights['valuation'] +
            market_timing_score * weights['market_timing']
        )

        return {
            'total_score': total_score,
            'business_quality_score': business_quality_score,
            'moat_strength_score': moat_strength_score,
            'management_quality_score': management_quality_score,
            'valuation_score': valuation_score,
            'market_timing_score': market_timing_score,
            'weights': weights
        }

    def _generate_buffett_decision(
        self,
        symbol: str,
        buffett_score: Dict[str, Any],
        fundamentals: Dict[str, float],
        market_context: Optional[Dict[str, Any]]
    ) -> AgentDecision:
        """生成巴菲特風格的投資決策"""
        current_time = datetime.now()
        total_score = buffett_score['total_score']

        # 巴菲特的決策閾值（更嚴格）
        buy_threshold = 80.0    # 只有優秀企業才買入
        sell_threshold = 40.0   # 基本面惡化才賣出

        # 檢查是否已持有該股票
        is_holding = symbol in self.current_positions

        # 長期持有檢查
        if is_holding:
            position_info = self.current_positions[symbol]
            holding_days = (current_time - position_info['entry_time']).days
            min_holding_days = self.min_holding_years * 365

            if holding_days < min_holding_days and total_score > 60.0:
                # 未達最小持有期間且基本面尚可，繼續持有
                action = 0
                confidence = 0.8
                reasoning = self._generate_buffett_hold_reasoning(total_score, holding_days, min_holding_days)
            elif total_score <= sell_threshold:
                # 基本面嚴重惡化，考慮賣出
                action = -1
                confidence = 0.7
                reasoning = self._generate_buffett_sell_reasoning(buffett_score, fundamentals)
                if symbol in self.current_positions:
                    del self.current_positions[symbol]
            else:
                # 繼續持有
                action = 0
                confidence = 0.7
                reasoning = self._generate_buffett_hold_reasoning(total_score, holding_days, min_holding_days)

        elif total_score >= buy_threshold:
            # 優秀企業，考慮買入
            action = 1
            confidence = min(0.9, total_score / 100.0)
            reasoning = self._generate_buffett_buy_reasoning(buffett_score, fundamentals, market_context)

            # 記錄持倉
            self.current_positions[symbol] = {
                'entry_time': current_time,
                'entry_score': total_score,
                'entry_price': fundamentals['price'],
                'investment_thesis': reasoning
            }

        else:
            # 觀望
            action = 0
            confidence = 0.6
            reasoning = f"巴菲特：'只投資你完全理解的企業' - 評分{total_score:.1f}未達標準"

        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=current_time,
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            expected_return=self._estimate_buffett_return(buffett_score),
            risk_assessment=self._assess_buffett_risk(buffett_score),
            position_size=self._calculate_buffett_position_size(total_score),
            metadata={
                'buffett_score': total_score,
                'moat_strength': buffett_score['moat_strength_score'],
                'management_quality': buffett_score['management_quality_score'],
                'business_quality': buffett_score['business_quality_score'],
                'is_contrarian_opportunity': market_context.get('contrarian_opportunity', False) if market_context else False,
                'investment_style': 'buffett_value',
                'min_holding_period_years': self.min_holding_years
            }
        )

    def _generate_buffett_buy_reasoning(
        self,
        buffett_score: Dict[str, Any],
        fundamentals: Dict[str, float],
        market_context: Optional[Dict[str, Any]]
    ) -> str:
        """生成巴菲特風格的買入推理"""
        reasons = []

        # 護城河優勢
        if buffett_score['moat_strength_score'] >= 80.0:
            reasons.append("具備強大經濟護城河")

        # 管理層品質
        if buffett_score['management_quality_score'] >= 80.0:
            reasons.append("優秀管理層")

        # 商業品質
        if buffett_score['business_quality_score'] >= 80.0:
            reasons.append("卓越商業模式")

        # 估值吸引力
        if buffett_score['valuation_score'] >= 70.0:
            reasons.append("估值合理")

        # 逆向投資機會
        if buffett_score['market_timing_score'] >= 80.0:
            reasons.append("市場恐慌提供機會")

        # 財務指標
        roe = fundamentals.get('roe', 0)
        if roe >= 0.20:
            reasons.append(f"優異ROE({roe:.1%})")

        base_reason = f"巴菲特投資決策（評分{buffett_score['total_score']:.1f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons) + " - '價格是你付出的，價值是你得到的'"
        else:
            return base_reason + " - '投資最重要的是找到優秀的企業'"

    def _generate_buffett_sell_reasoning(
        self,
        buffett_score: Dict[str, Any],
        fundamentals: Dict[str, float]
    ) -> str:
        """生成巴菲特風格的賣出推理"""
        reasons = []

        if buffett_score['business_quality_score'] < 50.0:
            reasons.append("商業品質惡化")

        if buffett_score['management_quality_score'] < 50.0:
            reasons.append("管理層問題")

        if buffett_score['moat_strength_score'] < 40.0:
            reasons.append("護城河受損")

        debt_ratio = fundamentals.get('debt_ratio', 0)
        if debt_ratio > 0.6:
            reasons.append("負債過高")

        base_reason = f"巴菲特賣出決策（評分{buffett_score['total_score']:.1f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons) + " - '當基本面改變時，改變想法是明智的'"
        else:
            return base_reason + " - '有時候最好的投資就是不投資'"

    def _generate_buffett_hold_reasoning(
        self,
        total_score: float,
        holding_days: int,
        min_holding_days: int
    ) -> str:
        """生成巴菲特風格的持有推理"""
        holding_years = holding_days / 365
        min_years = min_holding_days / 365

        if holding_days < min_holding_days:
            return (f"巴菲特長期持有策略：已持有{holding_years:.1f}年，"
                   f"目標{min_years:.0f}年以上 - '我們最喜歡的持有期是永遠'")
        else:
            return (f"巴菲特持有中（評分{total_score:.1f}）：已持有{holding_years:.1f}年，"
                   "基本面穩定 - '時間是優秀企業的朋友'")

    def _estimate_buffett_return(self, buffett_score: Dict[str, Any]) -> float:
        """估算巴菲特風格的預期收益率"""
        # 巴菲特追求長期穩定收益
        base_return = 0.12  # 基準12%年化收益率（巴菲特長期平均）

        # 基於綜合評分調整
        score_factor = buffett_score['total_score'] / 100.0

        # 護城河獎勵
        moat_bonus = (buffett_score['moat_strength_score'] - 50) / 500.0

        # 管理層獎勵
        management_bonus = (buffett_score['management_quality_score'] - 50) / 1000.0

        expected_return = base_return * score_factor + moat_bonus + management_bonus

        return max(0.05, min(expected_return, 0.25))  # 5-25%範圍

    def _assess_buffett_risk(self, buffett_score: Dict[str, Any]) -> float:
        """評估巴菲特風格的投資風險"""
        # 巴菲特風格風險較低
        base_risk = 0.25

        # 護城河降低風險
        moat_risk_reduction = buffett_score['moat_strength_score'] / 500.0

        # 管理層品質降低風險
        management_risk_reduction = buffett_score['management_quality_score'] / 1000.0

        # 商業品質降低風險
        business_risk_reduction = buffett_score['business_quality_score'] / 1000.0

        overall_risk = base_risk - moat_risk_reduction - management_risk_reduction - business_risk_reduction

        return max(0.1, min(overall_risk, 0.8))

    def _calculate_buffett_position_size(self, total_score: float) -> float:
        """計算巴菲特風格的倉位大小"""
        # 巴菲特偏好集中投資
        base_size = self.concentration_threshold

        # 基於評分調整倉位
        if total_score >= 90.0:
            size_factor = 1.0  # 最大倉位
        elif total_score >= 80.0:
            size_factor = 0.8
        elif total_score >= 70.0:
            size_factor = 0.6
        else:
            size_factor = 0.4

        position_size = base_size * size_factor

        return min(position_size, self.max_position_size)

    def get_investment_philosophy(self) -> str:
        """獲取巴菲特投資哲學描述"""
        return (
            "巴菲特投資哲學：'買入並持有優秀企業的股票，就像買入整個企業一樣。' "
            "關注企業內在價值、經濟護城河、優秀管理層和長期競爭優勢。"
            f"投資偏好：{', '.join(self.preferred_sectors)}；"
            f"避免領域：{', '.join(self.avoided_sectors)}。"
            f"最小持有期：{self.min_holding_years}年；集中投資閾值：{self.concentration_threshold:.1%}。"
            "核心理念：'價格是你付出的，價值是你得到的；時間是優秀企業的朋友。'"
        )

    def get_buffett_insights(self) -> List[str]:
        """獲取巴菲特投資智慧"""
        return [
            "規則一：永遠不要虧錢。規則二：永遠不要忘記規則一。",
            "只有在潮水退去時，你才知道誰在裸泳。",
            "我們最喜歡的持有期是永遠。",
            "價格是你付出的，價值是你得到的。",
            "在別人貪婪時恐懼，在別人恐懼時貪婪。",
            "投資最重要的是找到優秀的企業，然後在合理的價格買入。",
            "時間是優秀企業的朋友，是平庸企業的敵人。",
            "買股票就是買企業的一部分。"
        ]

    def __str__(self) -> str:
        """字符串表示"""
        return f"BuffettAgent(positions={len(self.current_positions)}, min_holding={self.min_holding_years}years)"
