# -*- coding: utf-8 -*-
"""
格雷厄姆代理模組

此模組實現模擬班傑明·格雷厄姆投資風格的AI代理。

投資哲學：
- 深度價值投資
- 安全邊際優先
- 量化篩選標準
- 防禦性投資
- 理性分析勝過市場情緒

核心特色：
- 嚴格的量化篩選條件
- 極度保守的安全邊際
- 關注資產負債表品質
- 忽視市場波動和情緒
- 長期持有優質便宜股
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


class GrahamAgent(ValueInvestor):
    """
    格雷厄姆代理 - 模擬班傑明·格雷厄姆的深度價值投資風格。
    
    繼承ValueInvestor並添加格雷厄姆特有的投資理念：
    - 更嚴格的量化篩選標準
    - 極度保守的安全邊際
    - 資產負債表深度分析
    - 防禦性投資策略
    - 完全忽視市場情緒
    
    Attributes:
        graham_number_enabled (bool): 是否啟用格雷厄姆數字
        net_current_asset_focus (bool): 是否關注淨流動資產
        earnings_stability_years (int): 盈利穩定性要求年數
        dividend_history_years (int): 股息歷史要求年數
        debt_equity_max (float): 最大負債權益比
        current_ratio_min (float): 最小流動比率
        book_value_discount_min (float): 最小帳面價值折扣
        margin_of_safety_min (float): 最小安全邊際
    """
    
    def __init__(
        self,
        name: str = "GrahamAgent",
        graham_number_enabled: bool = True,
        net_current_asset_focus: bool = True,
        earnings_stability_years: int = 10,
        dividend_history_years: int = 20,
        debt_equity_max: float = 0.5,
        current_ratio_min: float = 2.0,
        book_value_discount_min: float = 0.33,
        margin_of_safety_min: float = 0.5,
        **parameters: Any
    ) -> None:
        """
        初始化格雷厄姆代理。
        
        Args:
            name: 代理名稱
            graham_number_enabled: 是否啟用格雷厄姆數字
            net_current_asset_focus: 是否關注淨流動資產
            earnings_stability_years: 盈利穩定性要求年數
            dividend_history_years: 股息歷史要求年數
            debt_equity_max: 最大負債權益比
            current_ratio_min: 最小流動比率
            book_value_discount_min: 最小帳面價值折扣
            margin_of_safety_min: 最小安全邊際
            **parameters: 其他策略參數
        """
        # 設定格雷厄姆風格的價值投資參數（更嚴格）
        graham_params = {
            'pe_threshold': 15.0,     # 格雷厄姆建議P/E < 15
            'pb_threshold': 1.5,      # P/B < 1.5
            'roe_threshold': 0.10,    # 適度ROE要求
            'debt_ratio_threshold': 0.33,  # 更嚴格的負債要求
            'dividend_yield_min': 0.02,    # 要求有股息
            'safety_margin': margin_of_safety_min,  # 極高安全邊際
            'holding_period_min': 3 * 365,  # 至少3年持有
            'max_position_size': 0.05,      # 極度分散投資
        }
        
        # 合併參數
        graham_params.update(parameters)
        
        super().__init__(
            name=name,
            **graham_params
        )
        
        # 格雷厄姆特有參數
        self.graham_number_enabled = graham_number_enabled
        self.net_current_asset_focus = net_current_asset_focus
        self.earnings_stability_years = earnings_stability_years
        self.dividend_history_years = dividend_history_years
        self.debt_equity_max = debt_equity_max
        self.current_ratio_min = current_ratio_min
        self.book_value_discount_min = book_value_discount_min
        self.margin_of_safety_min = margin_of_safety_min
        
        # 格雷厄姆篩選標準
        self.graham_criteria = {
            'earnings_yield_min': 0.067,    # 盈利收益率 > 6.7% (P/E < 15)
            'debt_to_equity_max': 0.5,      # 負債權益比 < 50%
            'current_ratio_min': 2.0,       # 流動比率 > 2.0
            'pb_ratio_max': 1.5,            # P/B比率 < 1.5
            'dividend_yield_min': 0.02,     # 股息收益率 > 2%
            'earnings_growth_min': 0.03,    # 最低盈利成長率
            'revenue_size_min': 100_000_000  # 最小營收規模
        }
        
        # 防禦性股票特徵
        self.defensive_characteristics = [
            'stable_earnings',      # 穩定盈利
            'adequate_size',        # 足夠規模
            'strong_balance_sheet', # 強健資產負債表
            'dividend_history',     # 股息歷史
            'reasonable_pe',        # 合理P/E
            'moderate_debt'         # 適度負債
        ]
        
        # 投資組合追蹤
        self.current_positions: Dict[str, Dict] = {}
        self.rejected_stocks: Dict[str, str] = {}  # 記錄被拒絕的股票及原因
        
        logger.info(f"初始化格雷厄姆代理: {name} - 'The intelligent investor'")
    
    def make_decision(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """
        基於格雷厄姆投資哲學生成決策。
        
        Args:
            data: 市場數據
            market_context: 市場上下文信息
            
        Returns:
            AgentDecision: 格雷厄姆風格的投資決策
        """
        try:
            symbol = market_context.get('symbol', 'UNKNOWN') if market_context else 'UNKNOWN'
            
            # 檢查數據完整性
            if not self._validate_graham_data(data):
                return self._create_hold_decision(symbol, "格雷厄姆：'沒有足夠數據進行理性分析'")
            
            # 基礎價值投資分析
            fundamentals = self._extract_fundamentals(data)
            
            # 格雷厄姆量化篩選
            screening_result = self._apply_graham_screening(fundamentals, market_context)
            
            # 如果未通過篩選，直接拒絕
            if not screening_result['passed']:
                self.rejected_stocks[symbol] = screening_result['rejection_reason']
                return self._create_hold_decision(symbol, f"格雷厄姆篩選未通過：{screening_result['rejection_reason']}")
            
            # 深度價值分析
            value_analysis = self._perform_deep_value_analysis(fundamentals, market_context)
            
            # 安全邊際計算
            safety_margin_analysis = self._calculate_safety_margin(fundamentals, value_analysis)
            
            # 防禦性特徵評估
            defensive_analysis = self._evaluate_defensive_characteristics(fundamentals, market_context)
            
            # 格雷厄姆數字計算
            graham_number_analysis = self._calculate_graham_number(fundamentals) if self.graham_number_enabled else {}
            
            # 計算格雷厄姆綜合評分
            graham_score = self._calculate_graham_score(
                screening_result, value_analysis, safety_margin_analysis,
                defensive_analysis, graham_number_analysis
            )
            
            # 生成格雷厄姆風格決策
            decision = self._generate_graham_decision(
                symbol, graham_score, fundamentals, market_context
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"格雷厄姆代理決策生成失敗: {e}")
            return self._create_hold_decision(symbol, f"格雷厄姆：'分析過程出錯，保持謹慎' - {e}")
    
    def _validate_graham_data(self, data: pd.DataFrame) -> bool:
        """驗證格雷厄姆分析所需數據"""
        # 基礎價值投資數據驗證
        if not super()._validate_data(data):
            return False
        
        # 格雷厄姆特有數據要求
        graham_required = ['current_assets', 'current_liabilities', 'total_debt', 'shareholders_equity']
        
        latest_row = data.iloc[-1] if len(data) > 0 else None
        if latest_row is None:
            return False
        
        missing_data = []
        for col in graham_required:
            if col in data.columns and pd.isna(latest_row[col]):
                missing_data.append(col)
        
        if missing_data:
            logger.warning(f"格雷厄姆分析缺少關鍵財務數據: {missing_data}")
            # 不強制要求，可以使用估算值
        
        return True
    
    def _apply_graham_screening(
        self,
        fundamentals: Dict[str, float],
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """應用格雷厄姆量化篩選標準"""
        
        screening_results = {}
        rejection_reasons = []
        
        # 1. 盈利收益率檢查 (E/P > 6.7%)
        pe_ratio = fundamentals.get('pe_ratio', 999)
        earnings_yield = 1 / pe_ratio if pe_ratio > 0 else 0
        earnings_yield_pass = earnings_yield >= self.graham_criteria['earnings_yield_min']
        screening_results['earnings_yield'] = earnings_yield_pass
        if not earnings_yield_pass:
            rejection_reasons.append(f"盈利收益率{earnings_yield:.1%}過低")
        
        # 2. 負債權益比檢查
        debt_ratio = fundamentals.get('debt_ratio', 1.0)
        debt_equity_ratio = debt_ratio / (1 - debt_ratio) if debt_ratio < 1 else 999
        debt_equity_pass = debt_equity_ratio <= self.debt_equity_max
        screening_results['debt_equity'] = debt_equity_pass
        if not debt_equity_pass:
            rejection_reasons.append(f"負債權益比{debt_equity_ratio:.1f}過高")
        
        # 3. 流動比率檢查
        current_assets = fundamentals.get('current_assets', 0)
        current_liabilities = fundamentals.get('current_liabilities', 1)
        current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0
        current_ratio_pass = current_ratio >= self.current_ratio_min
        screening_results['current_ratio'] = current_ratio_pass
        if not current_ratio_pass:
            rejection_reasons.append(f"流動比率{current_ratio:.1f}不足")
        
        # 4. P/B比率檢查
        pb_ratio = fundamentals.get('pb_ratio', 999)
        pb_pass = pb_ratio <= self.graham_criteria['pb_ratio_max']
        screening_results['pb_ratio'] = pb_pass
        if not pb_pass:
            rejection_reasons.append(f"P/B比率{pb_ratio:.1f}過高")
        
        # 5. 股息收益率檢查
        dividend_yield = fundamentals.get('dividend_yield', 0)
        dividend_pass = dividend_yield >= self.graham_criteria['dividend_yield_min']
        screening_results['dividend_yield'] = dividend_pass
        if not dividend_pass:
            rejection_reasons.append(f"股息收益率{dividend_yield:.1%}不足")
        
        # 6. 企業規模檢查
        revenue = fundamentals.get('revenue', 0)
        size_pass = revenue >= self.graham_criteria['revenue_size_min']
        screening_results['company_size'] = size_pass
        if not size_pass:
            rejection_reasons.append(f"企業規模過小")
        
        # 7. 盈利成長檢查
        earnings_growth = fundamentals.get('earnings_growth', -1)
        growth_pass = earnings_growth >= self.graham_criteria['earnings_growth_min']
        screening_results['earnings_growth'] = growth_pass
        if not growth_pass:
            rejection_reasons.append(f"盈利成長{earnings_growth:.1%}不足")
        
        # 綜合篩選結果
        all_passed = all(screening_results.values())
        
        return {
            'passed': all_passed,
            'screening_results': screening_results,
            'rejection_reason': '; '.join(rejection_reasons) if rejection_reasons else '',
            'pass_rate': sum(screening_results.values()) / len(screening_results)
        }

    def _perform_deep_value_analysis(
        self,
        fundamentals: Dict[str, float],
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行深度價值分析"""

        # 淨流動資產價值 (NCAV)
        ncav_analysis = self._calculate_ncav(fundamentals)

        # 帳面價值分析
        book_value_analysis = self._analyze_book_value(fundamentals)

        # 盈利能力分析
        earning_power_analysis = self._analyze_earning_power(fundamentals)

        # 資產品質分析
        asset_quality_analysis = self._analyze_asset_quality(fundamentals)

        return {
            'ncav_analysis': ncav_analysis,
            'book_value_analysis': book_value_analysis,
            'earning_power_analysis': earning_power_analysis,
            'asset_quality_analysis': asset_quality_analysis
        }

    def _calculate_ncav(self, fundamentals: Dict[str, float]) -> Dict[str, Any]:
        """計算淨流動資產價值"""
        current_assets = fundamentals.get('current_assets', 0)
        current_liabilities = fundamentals.get('current_liabilities', 0)
        total_liabilities = fundamentals.get('total_debt', 0) + current_liabilities

        # 淨流動資產 = 流動資產 - 總負債
        ncav = current_assets - total_liabilities

        # 每股NCAV
        shares_outstanding = fundamentals.get('shares_outstanding', 1)
        ncav_per_share = ncav / shares_outstanding if shares_outstanding > 0 else 0

        # 當前股價
        current_price = fundamentals.get('price', 0)

        # NCAV折扣
        ncav_discount = (ncav_per_share - current_price) / ncav_per_share if ncav_per_share > 0 else -1

        # 格雷厄姆建議以NCAV的2/3價格買入
        graham_target_price = ncav_per_share * 0.67
        meets_ncav_criteria = current_price <= graham_target_price and ncav_per_share > 0

        return {
            'ncav': ncav,
            'ncav_per_share': ncav_per_share,
            'current_price': current_price,
            'ncav_discount': ncav_discount,
            'graham_target_price': graham_target_price,
            'meets_criteria': meets_ncav_criteria,
            'score': 100.0 if meets_ncav_criteria else max(0, ncav_discount * 100)
        }

    def _analyze_book_value(self, fundamentals: Dict[str, float]) -> Dict[str, Any]:
        """分析帳面價值"""
        book_value = fundamentals.get('book_value_per_share', 0)
        current_price = fundamentals.get('price', 0)
        pb_ratio = fundamentals.get('pb_ratio', 999)

        # 帳面價值折扣
        book_value_discount = (book_value - current_price) / book_value if book_value > 0 else -1

        # 格雷厄姆建議P/B < 1.5，最好 < 1.0
        meets_pb_criteria = pb_ratio <= 1.0
        moderate_pb = 1.0 < pb_ratio <= 1.5

        # 評分
        if meets_pb_criteria:
            score = 100.0
        elif moderate_pb:
            score = 70.0
        else:
            score = max(0, (2.0 - pb_ratio) * 50)  # P/B越高評分越低

        return {
            'book_value': book_value,
            'current_price': current_price,
            'pb_ratio': pb_ratio,
            'book_value_discount': book_value_discount,
            'meets_criteria': meets_pb_criteria,
            'moderate_criteria': moderate_pb,
            'score': score
        }

    def _analyze_earning_power(self, fundamentals: Dict[str, float]) -> Dict[str, Any]:
        """分析盈利能力"""
        eps = fundamentals.get('eps', 0)
        pe_ratio = fundamentals.get('pe_ratio', 999)
        roe = fundamentals.get('roe', 0)
        roa = fundamentals.get('roa', 0)

        # 盈利穩定性（簡化評估）
        earnings_stability = self._assess_earnings_stability(fundamentals)

        # 盈利收益率
        earnings_yield = 1 / pe_ratio if pe_ratio > 0 else 0

        # 格雷厄姆建議盈利收益率 > 6.7%（P/E < 15）
        meets_earnings_criteria = earnings_yield >= 0.067

        # 評分
        if meets_earnings_criteria and earnings_stability > 0.7:
            score = 90.0
        elif meets_earnings_criteria:
            score = 70.0
        elif earnings_yield > 0.05:  # 5%以上
            score = 50.0
        else:
            score = 20.0

        return {
            'eps': eps,
            'pe_ratio': pe_ratio,
            'earnings_yield': earnings_yield,
            'roe': roe,
            'roa': roa,
            'earnings_stability': earnings_stability,
            'meets_criteria': meets_earnings_criteria,
            'score': score
        }

    def _assess_earnings_stability(self, fundamentals: Dict[str, float]) -> float:
        """評估盈利穩定性"""
        # 簡化實現：基於ROE和成長率的穩定性
        roe = fundamentals.get('roe', 0)
        earnings_growth = fundamentals.get('earnings_growth', 0)

        # ROE穩定性（格雷厄姆偏好穩定而非高ROE）
        if 0.08 <= roe <= 0.20:  # 8-20%的穩定ROE
            roe_stability = 0.8
        elif 0.05 <= roe <= 0.25:
            roe_stability = 0.6
        else:
            roe_stability = 0.3

        # 成長穩定性（格雷厄姆偏好適度穩定成長）
        if 0.03 <= earnings_growth <= 0.10:  # 3-10%穩定成長
            growth_stability = 0.8
        elif 0 <= earnings_growth <= 0.15:
            growth_stability = 0.6
        else:
            growth_stability = 0.3

        return (roe_stability + growth_stability) / 2

    def _analyze_asset_quality(self, fundamentals: Dict[str, float]) -> Dict[str, Any]:
        """分析資產品質"""
        current_assets = fundamentals.get('current_assets', 0)
        total_assets = fundamentals.get('total_assets', 1)
        current_liabilities = fundamentals.get('current_liabilities', 1)
        total_debt = fundamentals.get('total_debt', 0)

        # 流動比率
        current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0

        # 資產負債比
        debt_to_assets = total_debt / total_assets if total_assets > 0 else 1

        # 流動資產比例
        current_asset_ratio = current_assets / total_assets if total_assets > 0 else 0

        # 資產品質評分
        quality_score = 0

        # 流動比率評分
        if current_ratio >= 2.0:
            quality_score += 30
        elif current_ratio >= 1.5:
            quality_score += 20
        elif current_ratio >= 1.0:
            quality_score += 10

        # 負債比例評分
        if debt_to_assets <= 0.3:
            quality_score += 30
        elif debt_to_assets <= 0.5:
            quality_score += 20
        elif debt_to_assets <= 0.7:
            quality_score += 10

        # 流動資產比例評分
        if current_asset_ratio >= 0.5:
            quality_score += 25
        elif current_asset_ratio >= 0.3:
            quality_score += 15
        elif current_asset_ratio >= 0.2:
            quality_score += 10

        # 綜合評分
        if quality_score >= 70:
            quality_level = "excellent"
        elif quality_score >= 50:
            quality_level = "good"
        elif quality_score >= 30:
            quality_level = "fair"
        else:
            quality_level = "poor"

        return {
            'current_ratio': current_ratio,
            'debt_to_assets': debt_to_assets,
            'current_asset_ratio': current_asset_ratio,
            'quality_score': quality_score,
            'quality_level': quality_level
        }

    def _calculate_safety_margin(
        self,
        fundamentals: Dict[str, float],
        value_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """計算安全邊際"""
        current_price = fundamentals.get('price', 0)

        # 多種內在價值估算
        intrinsic_values = {}

        # 1. NCAV內在價值
        ncav_per_share = value_analysis['ncav_analysis']['ncav_per_share']
        if ncav_per_share > 0:
            intrinsic_values['ncav'] = ncav_per_share * 0.67  # 格雷厄姆建議2/3價格

        # 2. 帳面價值內在價值
        book_value = value_analysis['book_value_analysis']['book_value']
        if book_value > 0:
            intrinsic_values['book_value'] = book_value

        # 3. 盈利價值（簡化DCF）
        eps = fundamentals.get('eps', 0)
        if eps > 0:
            # 使用保守的10倍P/E作為內在價值
            intrinsic_values['earnings'] = eps * 10

        # 4. 格雷厄姆數字
        if self.graham_number_enabled:
            graham_number = self._calculate_graham_number_value(fundamentals)
            if graham_number > 0:
                intrinsic_values['graham_number'] = graham_number

        # 選擇最保守的內在價值
        if intrinsic_values:
            conservative_intrinsic_value = min(intrinsic_values.values())
            optimistic_intrinsic_value = max(intrinsic_values.values())
            average_intrinsic_value = np.mean(list(intrinsic_values.values()))
        else:
            conservative_intrinsic_value = current_price
            optimistic_intrinsic_value = current_price
            average_intrinsic_value = current_price

        # 計算安全邊際
        conservative_margin = (conservative_intrinsic_value - current_price) / conservative_intrinsic_value if conservative_intrinsic_value > 0 else -1
        average_margin = (average_intrinsic_value - current_price) / average_intrinsic_value if average_intrinsic_value > 0 else -1

        # 格雷厄姆要求至少50%安全邊際
        meets_safety_criteria = conservative_margin >= self.margin_of_safety_min

        return {
            'intrinsic_values': intrinsic_values,
            'conservative_intrinsic_value': conservative_intrinsic_value,
            'optimistic_intrinsic_value': optimistic_intrinsic_value,
            'average_intrinsic_value': average_intrinsic_value,
            'conservative_margin': conservative_margin,
            'average_margin': average_margin,
            'meets_safety_criteria': meets_safety_criteria,
            'safety_score': max(0, conservative_margin * 100) if conservative_margin > 0 else 0
        }

    def _calculate_graham_number_value(self, fundamentals: Dict[str, float]) -> float:
        """計算格雷厄姆數字"""
        eps = fundamentals.get('eps', 0)
        book_value = fundamentals.get('book_value_per_share', 0)

        if eps > 0 and book_value > 0:
            # 格雷厄姆數字 = √(22.5 × EPS × BVPS)
            graham_number = np.sqrt(22.5 * eps * book_value)
            return graham_number

        return 0.0

    def _calculate_graham_number(self, fundamentals: Dict[str, float]) -> Dict[str, Any]:
        """計算格雷厄姆數字分析"""
        graham_number = self._calculate_graham_number_value(fundamentals)
        current_price = fundamentals.get('price', 0)

        if graham_number > 0:
            price_to_graham = current_price / graham_number
            graham_discount = (graham_number - current_price) / graham_number

            # 格雷厄姆數字評分
            if price_to_graham <= 0.8:  # 價格低於格雷厄姆數字80%
                score = 100.0
            elif price_to_graham <= 1.0:  # 價格低於格雷厄姆數字
                score = 80.0
            elif price_to_graham <= 1.2:  # 價格略高於格雷厄姆數字
                score = 60.0
            else:
                score = 20.0
        else:
            price_to_graham = 999
            graham_discount = -1
            score = 0.0

        return {
            'graham_number': graham_number,
            'current_price': current_price,
            'price_to_graham': price_to_graham,
            'graham_discount': graham_discount,
            'score': score
        }

    def _evaluate_defensive_characteristics(
        self,
        fundamentals: Dict[str, float],
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """評估防禦性特徵"""

        defensive_scores = {}

        # 1. 穩定盈利
        earnings_stability = self._assess_earnings_stability(fundamentals)
        defensive_scores['stable_earnings'] = earnings_stability * 100

        # 2. 足夠規模
        revenue = fundamentals.get('revenue', 0)
        size_score = 100.0 if revenue >= self.graham_criteria['revenue_size_min'] else 50.0
        defensive_scores['adequate_size'] = size_score

        # 3. 強健資產負債表
        debt_ratio = fundamentals.get('debt_ratio', 1.0)
        balance_sheet_score = max(0, (0.5 - debt_ratio) * 200) if debt_ratio <= 0.5 else 0
        defensive_scores['strong_balance_sheet'] = balance_sheet_score

        # 4. 股息歷史
        dividend_yield = fundamentals.get('dividend_yield', 0)
        dividend_score = 100.0 if dividend_yield >= 0.02 else 50.0
        defensive_scores['dividend_history'] = dividend_score

        # 5. 合理P/E
        pe_ratio = fundamentals.get('pe_ratio', 999)
        pe_score = 100.0 if pe_ratio <= 15 else max(0, (25 - pe_ratio) * 10)
        defensive_scores['reasonable_pe'] = pe_score

        # 6. 適度負債
        debt_equity_ratio = debt_ratio / (1 - debt_ratio) if debt_ratio < 1 else 999
        debt_score = 100.0 if debt_equity_ratio <= 0.5 else max(0, (1.0 - debt_equity_ratio) * 100)
        defensive_scores['moderate_debt'] = debt_score

        # 綜合防禦性評分
        overall_defensive_score = np.mean(list(defensive_scores.values()))

        # 防禦性等級
        if overall_defensive_score >= 80:
            defensive_level = "highly_defensive"
        elif overall_defensive_score >= 60:
            defensive_level = "moderately_defensive"
        elif overall_defensive_score >= 40:
            defensive_level = "somewhat_defensive"
        else:
            defensive_level = "not_defensive"

        return {
            'defensive_scores': defensive_scores,
            'overall_defensive_score': overall_defensive_score,
            'defensive_level': defensive_level,
            'meets_defensive_criteria': overall_defensive_score >= 70
        }

    def _calculate_graham_score(
        self,
        screening_result: Dict[str, Any],
        value_analysis: Dict[str, Any],
        safety_margin_analysis: Dict[str, Any],
        defensive_analysis: Dict[str, Any],
        graham_number_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """計算格雷厄姆綜合評分"""

        # 權重分配（反映格雷厄姆的投資重點）
        weights = {
            'screening': 0.30,        # 量化篩選最重要
            'safety_margin': 0.25,    # 安全邊際次之
            'defensive': 0.20,        # 防禦性特徵
            'value': 0.15,           # 深度價值分析
            'graham_number': 0.10     # 格雷厄姆數字
        }

        # 各組件評分
        screening_score = screening_result['pass_rate'] * 100
        safety_score = safety_margin_analysis['safety_score']
        defensive_score = defensive_analysis['overall_defensive_score']

        # 價值分析綜合評分
        value_scores = [
            value_analysis['ncav_analysis']['score'],
            value_analysis['book_value_analysis']['score'],
            value_analysis['earning_power_analysis']['score'],
            value_analysis['asset_quality_analysis']['quality_score']
        ]
        value_score = np.mean(value_scores)

        # 格雷厄姆數字評分
        graham_number_score = graham_number_analysis.get('score', 50.0)

        # 計算加權總分
        total_score = (
            screening_score * weights['screening'] +
            safety_score * weights['safety_margin'] +
            defensive_score * weights['defensive'] +
            value_score * weights['value'] +
            graham_number_score * weights['graham_number']
        )

        return {
            'total_score': total_score,
            'screening_score': screening_score,
            'safety_score': safety_score,
            'defensive_score': defensive_score,
            'value_score': value_score,
            'graham_number_score': graham_number_score,
            'weights': weights,
            'passed_screening': screening_result['passed'],
            'meets_safety_criteria': safety_margin_analysis['meets_safety_criteria'],
            'is_defensive': defensive_analysis['meets_defensive_criteria']
        }

    def _generate_graham_decision(
        self,
        symbol: str,
        graham_score: Dict[str, Any],
        fundamentals: Dict[str, float],
        market_context: Optional[Dict[str, Any]]
    ) -> AgentDecision:
        """生成格雷厄姆風格的投資決策"""
        current_time = datetime.now()
        total_score = graham_score['total_score']

        # 格雷厄姆的決策閾值（極其嚴格）
        buy_threshold = 85.0    # 只有最優秀的股票才買入
        sell_threshold = 50.0   # 基本面惡化或不再便宜時賣出

        # 檢查是否已持有該股票
        is_holding = symbol in self.current_positions

        # 必須通過所有關鍵檢查
        must_pass_checks = [
            graham_score['passed_screening'],
            graham_score['meets_safety_criteria'],
            graham_score['is_defensive']
        ]

        if is_holding:
            position_info = self.current_positions[symbol]
            holding_days = (current_time - position_info['entry_time']).days
            min_holding_days = 3 * 365  # 格雷厄姆建議長期持有

            if holding_days < min_holding_days and total_score > 60.0:
                # 未達最小持有期間且基本面尚可
                action = 0
                confidence = 0.8
                reasoning = self._generate_graham_hold_reasoning(symbol, total_score, holding_days)
            elif total_score <= sell_threshold or not all(must_pass_checks):
                # 基本面惡化或不再符合標準
                action = -1
                confidence = 0.9
                reasoning = self._generate_graham_sell_reasoning(symbol, graham_score)
                if symbol in self.current_positions:
                    del self.current_positions[symbol]
            else:
                # 繼續持有
                action = 0
                confidence = 0.8
                reasoning = self._generate_graham_hold_reasoning(symbol, total_score, holding_days)

        elif total_score >= buy_threshold and all(must_pass_checks):
            # 通過所有檢查，考慮買入
            action = 1
            confidence = 0.95  # 格雷厄姆風格信心度很高
            reasoning = self._generate_graham_buy_reasoning(symbol, graham_score, fundamentals)

            # 記錄持倉
            self.current_positions[symbol] = {
                'entry_time': current_time,
                'entry_score': total_score,
                'entry_price': fundamentals['price'],
                'graham_criteria_met': must_pass_checks,
                'safety_margin': graham_score.get('safety_score', 0)
            }

        else:
            # 不符合格雷厄姆標準
            action = 0
            confidence = 0.9  # 對拒絕的信心度很高
            reasoning = self._generate_graham_reject_reasoning(symbol, graham_score)

        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=current_time,
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            expected_return=self._estimate_graham_return(graham_score),
            risk_assessment=self._assess_graham_risk(graham_score),
            position_size=self.max_position_size if action == 1 else 0.0,
            metadata={
                'graham_score': total_score,
                'screening_passed': graham_score['passed_screening'],
                'safety_margin_met': graham_score['meets_safety_criteria'],
                'defensive_criteria_met': graham_score['is_defensive'],
                'safety_score': graham_score['safety_score'],
                'defensive_score': graham_score['defensive_score'],
                'investment_style': 'graham_deep_value',
                'min_holding_period_years': 3
            }
        )

    def _generate_graham_buy_reasoning(
        self,
        symbol: str,
        graham_score: Dict[str, Any],
        fundamentals: Dict[str, float]
    ) -> str:
        """生成格雷厄姆風格的買入推理"""
        reasons = []

        if graham_score['safety_score'] >= 50:
            reasons.append(f"安全邊際{graham_score['safety_score']:.0f}%")

        if graham_score['defensive_score'] >= 70:
            reasons.append("防禦性特徵優秀")

        if graham_score['screening_score'] >= 85:
            reasons.append("通過所有量化篩選")

        pe_ratio = fundamentals.get('pe_ratio', 999)
        pb_ratio = fundamentals.get('pb_ratio', 999)
        if pe_ratio <= 15 and pb_ratio <= 1.5:
            reasons.append(f"估值便宜(P/E:{pe_ratio:.1f}, P/B:{pb_ratio:.1f})")

        base_reason = f"格雷厄姆深度價值投資（評分{graham_score['total_score']:.1f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons) + " - '買入並持有優秀的便宜股'"
        else:
            return base_reason + " - '智慧投資者的選擇'"

    def _generate_graham_sell_reasoning(
        self,
        symbol: str,
        graham_score: Dict[str, Any]
    ) -> str:
        """生成格雷厄姆風格的賣出推理"""
        reasons = []

        if not graham_score['passed_screening']:
            reasons.append("不再通過量化篩選")

        if not graham_score['meets_safety_criteria']:
            reasons.append("安全邊際不足")

        if not graham_score['is_defensive']:
            reasons.append("防禦性特徵惡化")

        if graham_score['total_score'] < 50:
            reasons.append("綜合評分過低")

        base_reason = f"格雷厄姆賣出決策（評分{graham_score['total_score']:.1f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons) + " - '當投資論點不再成立時退出'"
        else:
            return base_reason + " - '理性分析勝過情感依戀'"

    def _generate_graham_hold_reasoning(
        self,
        symbol: str,
        total_score: float,
        holding_days: int
    ) -> str:
        """生成格雷厄姆風格的持有推理"""
        holding_years = holding_days / 365

        return (f"格雷厄姆長期持有：已持有{holding_years:.1f}年，"
                f"評分{total_score:.1f}，基本面穩定 - "
                "'市場短期是投票機，長期是稱重機'")

    def _generate_graham_reject_reasoning(
        self,
        symbol: str,
        graham_score: Dict[str, Any]
    ) -> str:
        """生成格雷厄姆風格的拒絕推理"""
        reasons = []

        if not graham_score['passed_screening']:
            reasons.append("未通過量化篩選")

        if not graham_score['meets_safety_criteria']:
            reasons.append("安全邊際不足")

        if not graham_score['is_defensive']:
            reasons.append("缺乏防禦性特徵")

        if graham_score['total_score'] < 85:
            reasons.append("評分未達標準")

        base_reason = f"格雷厄姆拒絕投資（評分{graham_score['total_score']:.1f}）"
        if reasons:
            return base_reason + "：" + "；".join(reasons) + " - '寧可錯過機會，不可承擔不必要風險'"
        else:
            return base_reason + " - '智慧投資者的謹慎'"

    def _create_hold_decision(self, symbol: str, reason: str) -> AgentDecision:
        """創建持有決策"""
        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            symbol=symbol,
            action=0,
            confidence=0.8,
            reasoning=reason,
            expected_return=0.0,
            risk_assessment=0.2,  # 格雷厄姆風格風險很低
            position_size=self.current_positions.get(symbol, {}).get('size', 0.0)
        )

    def _estimate_graham_return(self, graham_score: Dict[str, Any]) -> float:
        """估算格雷厄姆風格的預期收益率"""
        # 格雷厄姆追求穩定的合理收益
        base_return = 0.10  # 基準10%年化收益率

        # 基於安全邊際調整
        safety_bonus = graham_score['safety_score'] / 1000.0  # 安全邊際獎勵

        # 基於防禦性調整
        defensive_bonus = (graham_score['defensive_score'] - 50) / 1000.0

        expected_return = base_return + safety_bonus + defensive_bonus

        return max(0.06, min(expected_return, 0.18))  # 6-18%範圍

    def _assess_graham_risk(self, graham_score: Dict[str, Any]) -> float:
        """評估格雷厄姆風格的投資風險"""
        # 格雷厄姆風格風險最低
        base_risk = 0.15

        # 安全邊際降低風險
        safety_risk_reduction = graham_score['safety_score'] / 500.0

        # 防禦性降低風險
        defensive_risk_reduction = graham_score['defensive_score'] / 1000.0

        overall_risk = base_risk - safety_risk_reduction - defensive_risk_reduction

        return max(0.05, min(overall_risk, 0.4))

    def get_investment_philosophy(self) -> str:
        """獲取格雷厄姆投資哲學描述"""
        return (
            "格雷厄姆投資哲學：'智慧投資者通過深度分析和安全邊際來保護資本並獲得合理收益。' "
            "嚴格的量化篩選標準，極度保守的安全邊際，關注防禦性特徵。"
            f"最小安全邊際：{self.margin_of_safety_min:.0%}；最小流動比率：{self.current_ratio_min}；"
            f"最大負債權益比：{self.debt_equity_max}。"
            "核心理念：'寧可錯過機會，不可承擔不必要風險。'"
        )

    def get_graham_criteria(self) -> Dict[str, float]:
        """獲取格雷厄姆篩選標準"""
        return self.graham_criteria.copy()

    def get_rejected_stocks(self) -> Dict[str, str]:
        """獲取被拒絕的股票及原因"""
        return self.rejected_stocks.copy()

    def get_graham_insights(self) -> List[str]:
        """獲取格雷厄姆投資智慧"""
        return [
            "投資最重要的是保護本金，其次才是獲得收益。",
            "市場短期是投票機，長期是稱重機。",
            "智慧投資者通過分析而非投機來獲得收益。",
            "安全邊際是成功投資的基石。",
            "買入股票就像買入企業的一部分。",
            "寧可錯過機會，不可承擔不必要風險。",
            "防禦性投資勝過攻擊性投資。",
            "理性分析勝過市場情緒。"
        ]

    def clear_rejected_stocks(self) -> None:
        """清除被拒絕股票記錄"""
        self.rejected_stocks.clear()
        logger.info("格雷厄姆代理：清除被拒絕股票記錄")

    def __str__(self) -> str:
        """字符串表示"""
        return f"GrahamAgent(positions={len(self.current_positions)}, rejected={len(self.rejected_stocks)})"
