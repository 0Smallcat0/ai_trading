# -*- coding: utf-8 -*-
"""
價值投資代理模組

此模組實現基於基本面分析的價值投資代理。

投資哲學：
- 尋找被市場低估的優質股票
- 關注企業內在價值和安全邊際
- 長期持有，低換手率
- 重視財務健康和盈利能力

主要功能：
- 基本面指標分析（P/E、P/B、ROE、ROA等）
- DCF估值模型
- 財務健康評估
- 安全邊際計算
- 長期投資決策
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..base import TradingAgent, AgentDecision, InvestmentStyle, RiskPreference

# 設定日誌
logger = logging.getLogger(__name__)


class ValueInvestor(TradingAgent):
    """
    價值投資代理。
    
    基於基本面分析進行價值投資決策，關注：
    - 估值指標（P/E、P/B、PEG等）
    - 財務健康指標（ROE、ROA、負債比率等）
    - 成長指標（營收成長率、盈利成長率等）
    - 股息收益率和穩定性
    
    Attributes:
        pe_threshold (float): P/E比率閾值
        pb_threshold (float): P/B比率閾值
        roe_threshold (float): ROE閾值
        debt_ratio_threshold (float): 負債比率閾值
        dividend_yield_min (float): 最小股息收益率
        safety_margin (float): 安全邊際要求
        holding_period_min (int): 最小持有期間（天數）
    """
    
    def __init__(
        self,
        name: str = "ValueInvestor",
        pe_threshold: float = 15.0,
        pb_threshold: float = 1.5,
        roe_threshold: float = 0.15,
        debt_ratio_threshold: float = 0.5,
        dividend_yield_min: float = 0.02,
        safety_margin: float = 0.2,
        holding_period_min: int = 90,
        **parameters: Any
    ) -> None:
        """
        初始化價值投資代理。
        
        Args:
            name: 代理名稱
            pe_threshold: P/E比率閾值（低於此值考慮買入）
            pb_threshold: P/B比率閾值（低於此值考慮買入）
            roe_threshold: ROE閾值（高於此值考慮買入）
            debt_ratio_threshold: 負債比率閾值（低於此值考慮買入）
            dividend_yield_min: 最小股息收益率要求
            safety_margin: 安全邊際要求（估值折扣）
            holding_period_min: 最小持有期間（天數）
            **parameters: 其他策略參數
        """
        super().__init__(
            name=name,
            investment_style=InvestmentStyle.VALUE,
            risk_preference=RiskPreference.CONSERVATIVE,
            max_position_size=0.15,  # 價值投資通常集中持股
            **parameters
        )
        
        # 價值投資參數
        self.pe_threshold = pe_threshold
        self.pb_threshold = pb_threshold
        self.roe_threshold = roe_threshold
        self.debt_ratio_threshold = debt_ratio_threshold
        self.dividend_yield_min = dividend_yield_min
        self.safety_margin = safety_margin
        self.holding_period_min = holding_period_min
        
        # 持倉追蹤
        self.current_positions: Dict[str, Dict] = {}
        self.watchlist: List[str] = []
        
        logger.info(f"初始化價值投資代理: {name}")
    
    def make_decision(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """
        基於基本面分析生成投資決策。
        
        Args:
            data: 市場數據，包含價格和基本面數據
            market_context: 市場上下文信息
            
        Returns:
            AgentDecision: 投資決策
        """
        try:
            symbol = market_context.get('symbol', 'UNKNOWN') if market_context else 'UNKNOWN'
            
            # 檢查數據完整性
            if not self._validate_data(data):
                return self._create_hold_decision(symbol, "數據不完整")
            
            # 提取基本面數據
            fundamentals = self._extract_fundamentals(data)
            
            # 計算估值指標
            valuation_score = self._calculate_valuation_score(fundamentals)
            
            # 評估財務健康
            financial_health_score = self._calculate_financial_health_score(fundamentals)
            
            # 評估成長性
            growth_score = self._calculate_growth_score(fundamentals)
            
            # 計算綜合評分
            overall_score = self._calculate_overall_score(
                valuation_score, financial_health_score, growth_score
            )
            
            # 生成決策
            decision = self._generate_investment_decision(
                symbol, overall_score, fundamentals
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"價值投資決策生成失敗: {e}")
            return self._create_hold_decision(symbol, f"決策生成錯誤: {e}")
    
    def _validate_data(self, data: pd.DataFrame) -> bool:
        """驗證數據完整性"""
        required_columns = ['close', 'pe_ratio', 'pb_ratio', 'roe', 'debt_ratio']
        
        for col in required_columns:
            if col not in data.columns:
                logger.warning(f"缺少必要數據欄位: {col}")
                return False
        
        # 檢查最新數據是否存在
        if len(data) == 0:
            return False
        
        latest_row = data.iloc[-1]
        for col in required_columns:
            if pd.isna(latest_row[col]):
                logger.warning(f"最新數據中 {col} 為空值")
                return False
        
        return True
    
    def _extract_fundamentals(self, data: pd.DataFrame) -> Dict[str, float]:
        """提取基本面數據"""
        latest = data.iloc[-1]
        
        fundamentals = {
            'price': float(latest['close']),
            'pe_ratio': float(latest.get('pe_ratio', 0)),
            'pb_ratio': float(latest.get('pb_ratio', 0)),
            'roe': float(latest.get('roe', 0)),
            'roa': float(latest.get('roa', 0)),
            'debt_ratio': float(latest.get('debt_ratio', 0)),
            'dividend_yield': float(latest.get('dividend_yield', 0)),
            'revenue_growth': float(latest.get('revenue_growth', 0)),
            'earnings_growth': float(latest.get('earnings_growth', 0)),
            'book_value': float(latest.get('book_value', 0)),
            'market_cap': float(latest.get('market_cap', 0)),
        }
        
        return fundamentals
    
    def _calculate_valuation_score(self, fundamentals: Dict[str, float]) -> float:
        """計算估值評分（0-100，越高越好）"""
        score = 0.0
        max_score = 100.0
        
        # P/E比率評分（30分）
        pe_ratio = fundamentals['pe_ratio']
        if pe_ratio > 0:
            if pe_ratio <= self.pe_threshold * 0.7:  # 非常便宜
                score += 30
            elif pe_ratio <= self.pe_threshold:  # 便宜
                score += 20
            elif pe_ratio <= self.pe_threshold * 1.5:  # 合理
                score += 10
            # 否則不加分
        
        # P/B比率評分（25分）
        pb_ratio = fundamentals['pb_ratio']
        if pb_ratio > 0:
            if pb_ratio <= self.pb_threshold * 0.7:  # 非常便宜
                score += 25
            elif pb_ratio <= self.pb_threshold:  # 便宜
                score += 18
            elif pb_ratio <= self.pb_threshold * 1.5:  # 合理
                score += 10
            # 否則不加分
        
        # 股息收益率評分（20分）
        dividend_yield = fundamentals['dividend_yield']
        if dividend_yield >= self.dividend_yield_min * 2:  # 高股息
            score += 20
        elif dividend_yield >= self.dividend_yield_min:  # 符合要求
            score += 15
        elif dividend_yield > 0:  # 有股息但不足
            score += 5
        
        # DCF估值評分（25分）
        dcf_score = self._calculate_dcf_score(fundamentals)
        score += dcf_score * 0.25
        
        return min(score, max_score)
    
    def _calculate_financial_health_score(self, fundamentals: Dict[str, float]) -> float:
        """計算財務健康評分（0-100，越高越好）"""
        score = 0.0
        max_score = 100.0
        
        # ROE評分（40分）
        roe = fundamentals['roe']
        if roe >= self.roe_threshold * 1.5:  # 優秀
            score += 40
        elif roe >= self.roe_threshold:  # 良好
            score += 30
        elif roe >= self.roe_threshold * 0.7:  # 一般
            score += 15
        # 否則不加分
        
        # ROA評分（30分）
        roa = fundamentals['roa']
        if roa >= 0.1:  # 優秀
            score += 30
        elif roa >= 0.05:  # 良好
            score += 20
        elif roa > 0:  # 正值
            score += 10
        # 否則不加分
        
        # 負債比率評分（30分）
        debt_ratio = fundamentals['debt_ratio']
        if debt_ratio <= self.debt_ratio_threshold * 0.5:  # 低負債
            score += 30
        elif debt_ratio <= self.debt_ratio_threshold:  # 合理負債
            score += 20
        elif debt_ratio <= self.debt_ratio_threshold * 1.5:  # 稍高負債
            score += 10
        # 否則不加分
        
        return min(score, max_score)
    
    def _calculate_growth_score(self, fundamentals: Dict[str, float]) -> float:
        """計算成長性評分（0-100，越高越好）"""
        score = 0.0
        max_score = 100.0
        
        # 營收成長率評分（50分）
        revenue_growth = fundamentals['revenue_growth']
        if revenue_growth >= 0.2:  # 高成長
            score += 50
        elif revenue_growth >= 0.1:  # 中等成長
            score += 35
        elif revenue_growth >= 0.05:  # 低成長
            score += 20
        elif revenue_growth > 0:  # 正成長
            score += 10
        # 否則不加分
        
        # 盈利成長率評分（50分）
        earnings_growth = fundamentals['earnings_growth']
        if earnings_growth >= 0.2:  # 高成長
            score += 50
        elif earnings_growth >= 0.1:  # 中等成長
            score += 35
        elif earnings_growth >= 0.05:  # 低成長
            score += 20
        elif earnings_growth > 0:  # 正成長
            score += 10
        # 否則不加分
        
        return min(score, max_score)
    
    def _calculate_dcf_score(self, fundamentals: Dict[str, float]) -> float:
        """簡化的DCF估值評分（0-100）"""
        try:
            # 簡化的DCF計算
            # 假設未來5年的現金流成長率
            growth_rate = min(fundamentals['earnings_growth'], 0.15)  # 最高15%
            discount_rate = 0.1  # 10%折現率
            terminal_growth = 0.03  # 3%永續成長率
            
            # 當前每股收益（簡化計算）
            current_eps = fundamentals['price'] / max(fundamentals['pe_ratio'], 1)
            
            # 計算未來5年現金流現值
            dcf_value = 0
            for year in range(1, 6):
                future_eps = current_eps * ((1 + growth_rate) ** year)
                present_value = future_eps / ((1 + discount_rate) ** year)
                dcf_value += present_value
            
            # 終值計算
            terminal_eps = current_eps * ((1 + growth_rate) ** 5) * (1 + terminal_growth)
            terminal_value = terminal_eps / (discount_rate - terminal_growth)
            terminal_present_value = terminal_value / ((1 + discount_rate) ** 5)
            
            dcf_value += terminal_present_value
            
            # 計算安全邊際
            current_price = fundamentals['price']
            fair_value = dcf_value
            
            if fair_value > 0:
                margin = (fair_value - current_price) / fair_value
                if margin >= self.safety_margin:
                    return 100  # 有足夠安全邊際
                elif margin > 0:
                    return margin / self.safety_margin * 100
                else:
                    return 0  # 高估
            
            return 0
            
        except Exception as e:
            logger.warning(f"DCF計算失敗: {e}")
            return 0
    
    def _calculate_overall_score(
        self,
        valuation_score: float,
        financial_health_score: float,
        growth_score: float
    ) -> float:
        """計算綜合評分"""
        # 價值投資權重分配
        weights = {
            'valuation': 0.5,      # 估值最重要
            'financial_health': 0.3,  # 財務健康次之
            'growth': 0.2          # 成長性相對較低權重
        }
        
        overall_score = (
            valuation_score * weights['valuation'] +
            financial_health_score * weights['financial_health'] +
            growth_score * weights['growth']
        )
        
        return overall_score

    def _generate_investment_decision(
        self,
        symbol: str,
        overall_score: float,
        fundamentals: Dict[str, float]
    ) -> AgentDecision:
        """生成投資決策"""
        current_time = datetime.now()

        # 決策閾值
        buy_threshold = 70.0    # 綜合評分70以上考慮買入
        sell_threshold = 30.0   # 綜合評分30以下考慮賣出

        # 檢查是否已持有該股票
        is_holding = symbol in self.current_positions

        if overall_score >= buy_threshold and not is_holding:
            # 買入決策
            action = 1
            confidence = min(0.9, overall_score / 100.0)
            reasoning = self._generate_buy_reasoning(overall_score, fundamentals)

            # 記錄持倉
            self.current_positions[symbol] = {
                'entry_time': current_time,
                'entry_score': overall_score,
                'entry_price': fundamentals['price']
            }

        elif overall_score <= sell_threshold and is_holding:
            # 賣出決策
            action = -1
            confidence = min(0.8, (100 - overall_score) / 100.0)
            reasoning = self._generate_sell_reasoning(overall_score, fundamentals)

            # 移除持倉記錄
            if symbol in self.current_positions:
                del self.current_positions[symbol]

        elif is_holding:
            # 持有決策 - 檢查是否需要調整
            position_info = self.current_positions[symbol]
            holding_days = (current_time - position_info['entry_time']).days

            if holding_days < self.holding_period_min and overall_score > 40:
                # 未達最小持有期間且評分尚可，繼續持有
                action = 0
                confidence = 0.6
                reasoning = f"持有中（{holding_days}天），未達最小持有期間"
            else:
                # 重新評估持有決策
                action = 0
                confidence = overall_score / 100.0
                reasoning = self._generate_hold_reasoning(overall_score, fundamentals)
        else:
            # 觀望決策
            action = 0
            confidence = 0.5
            reasoning = f"綜合評分{overall_score:.1f}，暫時觀望"

        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=current_time,
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            expected_return=self._estimate_expected_return(fundamentals, overall_score),
            risk_assessment=self._assess_risk(fundamentals),
            position_size=self._calculate_position_size(overall_score),
            metadata={
                'overall_score': overall_score,
                'valuation_attractive': overall_score >= buy_threshold,
                'financial_health': fundamentals.get('roe', 0) >= self.roe_threshold,
                'safety_margin_met': self._check_safety_margin(fundamentals)
            }
        )

    def _generate_buy_reasoning(self, score: float, fundamentals: Dict[str, float]) -> str:
        """生成買入推理"""
        reasons = []

        if fundamentals['pe_ratio'] <= self.pe_threshold:
            reasons.append(f"P/E比率{fundamentals['pe_ratio']:.1f}低於閾值{self.pe_threshold}")

        if fundamentals['pb_ratio'] <= self.pb_threshold:
            reasons.append(f"P/B比率{fundamentals['pb_ratio']:.1f}低於閾值{self.pb_threshold}")

        if fundamentals['roe'] >= self.roe_threshold:
            reasons.append(f"ROE {fundamentals['roe']:.1%}優於閾值{self.roe_threshold:.1%}")

        if fundamentals['debt_ratio'] <= self.debt_ratio_threshold:
            reasons.append(f"負債比率{fundamentals['debt_ratio']:.1%}健康")

        if fundamentals['dividend_yield'] >= self.dividend_yield_min:
            reasons.append(f"股息收益率{fundamentals['dividend_yield']:.1%}吸引")

        base_reason = f"價值投資買入信號（評分{score:.1f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons)
        else:
            return base_reason

    def _generate_sell_reasoning(self, score: float, fundamentals: Dict[str, float]) -> str:
        """生成賣出推理"""
        reasons = []

        if fundamentals['pe_ratio'] > self.pe_threshold * 2:
            reasons.append(f"P/E比率{fundamentals['pe_ratio']:.1f}過高")

        if fundamentals['pb_ratio'] > self.pb_threshold * 2:
            reasons.append(f"P/B比率{fundamentals['pb_ratio']:.1f}過高")

        if fundamentals['roe'] < self.roe_threshold * 0.5:
            reasons.append(f"ROE {fundamentals['roe']:.1%}惡化")

        if fundamentals['debt_ratio'] > self.debt_ratio_threshold * 1.5:
            reasons.append(f"負債比率{fundamentals['debt_ratio']:.1%}過高")

        base_reason = f"價值投資賣出信號（評分{score:.1f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons)
        else:
            return base_reason

    def _generate_hold_reasoning(self, score: float, fundamentals: Dict[str, float]) -> str:
        """生成持有推理"""
        return f"價值投資持有（評分{score:.1f}），基本面穩定，繼續觀察"

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

    def _estimate_expected_return(self, fundamentals: Dict[str, float], score: float) -> float:
        """估算預期收益率"""
        # 基於評分和基本面估算年化預期收益率
        base_return = 0.08  # 基準8%年化收益率

        # 根據評分調整
        score_multiplier = score / 100.0

        # 根據成長性調整
        growth_bonus = min(fundamentals.get('earnings_growth', 0), 0.1)

        # 根據股息收益率調整
        dividend_bonus = fundamentals.get('dividend_yield', 0)

        expected_return = base_return * score_multiplier + growth_bonus + dividend_bonus

        return min(expected_return, 0.25)  # 最高25%預期收益率

    def _assess_risk(self, fundamentals: Dict[str, float]) -> float:
        """評估風險水平（0-1，越高風險越大）"""
        risk_factors = []

        # 估值風險
        pe_risk = max(0, (fundamentals['pe_ratio'] - self.pe_threshold) / self.pe_threshold)
        risk_factors.append(min(pe_risk, 1.0))

        # 財務風險
        debt_risk = max(0, (fundamentals['debt_ratio'] - self.debt_ratio_threshold) / self.debt_ratio_threshold)
        risk_factors.append(min(debt_risk, 1.0))

        # 盈利能力風險
        roe_risk = max(0, (self.roe_threshold - fundamentals['roe']) / self.roe_threshold)
        risk_factors.append(min(roe_risk, 1.0))

        # 計算平均風險
        avg_risk = np.mean(risk_factors) if risk_factors else 0.5

        return min(avg_risk, 1.0)

    def _calculate_position_size(self, score: float) -> float:
        """計算倉位大小"""
        # 基於評分和風險偏好計算倉位
        base_size = self.max_position_size
        score_factor = score / 100.0

        # 價值投資傾向於集中持股，但仍要控制風險
        position_size = base_size * score_factor

        return min(position_size, self.max_position_size)

    def _check_safety_margin(self, fundamentals: Dict[str, float]) -> bool:
        """檢查是否滿足安全邊際要求"""
        # 簡化的安全邊際檢查
        pe_margin = fundamentals['pe_ratio'] <= self.pe_threshold * (1 - self.safety_margin)
        pb_margin = fundamentals['pb_ratio'] <= self.pb_threshold * (1 - self.safety_margin)

        return pe_margin or pb_margin

    def get_investment_philosophy(self) -> str:
        """獲取投資哲學描述"""
        return (
            "價值投資哲學：尋找被市場低估的優質企業，關注內在價值和安全邊際。"
            f"重點指標：P/E<{self.pe_threshold}、P/B<{self.pb_threshold}、"
            f"ROE>{self.roe_threshold:.1%}、負債比率<{self.debt_ratio_threshold:.1%}。"
            "投資策略：長期持有，低換手率，重視財務健康和股息收益。"
        )

    def get_current_positions(self) -> Dict[str, Dict]:
        """獲取當前持倉信息"""
        return self.current_positions.copy()

    def add_to_watchlist(self, symbol: str) -> None:
        """添加到觀察清單"""
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
            logger.info(f"添加 {symbol} 到價值投資觀察清單")

    def remove_from_watchlist(self, symbol: str) -> None:
        """從觀察清單移除"""
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            logger.info(f"從價值投資觀察清單移除 {symbol}")

    def get_watchlist(self) -> List[str]:
        """獲取觀察清單"""
        return self.watchlist.copy()

    def __str__(self) -> str:
        """字符串表示"""
        return f"ValueInvestor(positions={len(self.current_positions)}, watchlist={len(self.watchlist)})"
