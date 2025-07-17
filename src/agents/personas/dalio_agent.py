# -*- coding: utf-8 -*-
"""
達里奧代理模組

此模組實現模擬雷·達里奧投資風格的AI代理。

投資哲學：
- 全天候投資策略（All Weather）
- 風險平價和分散投資
- 經濟機器理解
- 債務週期分析
- 原則導向決策

核心特色：
- 跨資產類別配置
- 風險平衡而非資本平衡
- 長期經濟週期視角
- 系統性風險管理
- 透明的決策原則
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

from ..base import TradingAgent, AgentDecision, InvestmentStyle, RiskPreference
from ..styles.risk_parity_agent import RiskParityAgent

# 設定日誌
logger = logging.getLogger(__name__)


class DalioAgent(RiskParityAgent):
    """
    達里奧代理 - 模擬雷·達里奧的全天候投資風格。
    
    繼承RiskParityAgent並添加達里奧特有的投資理念：
    - 經濟機器分析
    - 債務週期識別
    - 四季投資環境
    - 原則化決策
    - 透明度和可解釋性
    
    Attributes:
        economic_cycle_analysis (bool): 是否啟用經濟週期分析
        debt_cycle_weight (float): 債務週期權重
        inflation_sensitivity (float): 通脹敏感度
        growth_sensitivity (float): 成長敏感度
        season_weights (Dict): 四季權重配置
        transparency_level (float): 透明度水平
        principle_adherence (float): 原則遵循度
    """
    
    def __init__(
        self,
        name: str = "DalioAgent",
        economic_cycle_analysis: bool = True,
        debt_cycle_weight: float = 0.3,
        inflation_sensitivity: float = 0.8,
        growth_sensitivity: float = 0.7,
        season_weights: Optional[Dict[str, float]] = None,
        transparency_level: float = 0.9,
        principle_adherence: float = 0.95,
        **parameters: Any
    ) -> None:
        """
        初始化達里奧代理。
        
        Args:
            name: 代理名稱
            economic_cycle_analysis: 是否啟用經濟週期分析
            debt_cycle_weight: 債務週期權重
            inflation_sensitivity: 通脹敏感度
            growth_sensitivity: 成長敏感度
            season_weights: 四季權重配置
            transparency_level: 透明度水平
            principle_adherence: 原則遵循度
            **parameters: 其他策略參數
        """
        # 設定達里奧風格的風險平價參數
        dalio_params = {
            'lookback_period': 120,  # 更長的回望期間
            'rebalance_frequency': 30,  # 月度再平衡
            'volatility_target': 0.10,  # 10%目標波動率
            'min_weight': 0.05,
            'max_weight': 0.30,
            'risk_tolerance': 0.12
        }
        
        # 合併參數
        dalio_params.update(parameters)
        
        super().__init__(
            name=name,
            **dalio_params
        )
        
        # 達里奧特有參數
        self.economic_cycle_analysis = economic_cycle_analysis
        self.debt_cycle_weight = debt_cycle_weight
        self.inflation_sensitivity = inflation_sensitivity
        self.growth_sensitivity = growth_sensitivity
        self.transparency_level = transparency_level
        self.principle_adherence = principle_adherence
        
        # 四季投資環境權重
        self.season_weights = season_weights or {
            'growth_rising_inflation_rising': 0.25,    # 春季：成長上升，通脹上升
            'growth_rising_inflation_falling': 0.25,   # 夏季：成長上升，通脹下降
            'growth_falling_inflation_falling': 0.25,  # 秋季：成長下降，通脹下降
            'growth_falling_inflation_rising': 0.25    # 冬季：成長下降，通脹上升
        }
        
        # 經濟機器組件
        self.economic_machine = {
            'productivity_growth': 0.02,    # 生產力成長
            'short_term_debt_cycle': 0.0,   # 短期債務週期
            'long_term_debt_cycle': 0.0,    # 長期債務週期
            'current_season': 'unknown'     # 當前季節
        }
        
        # 資產類別配置
        self.asset_classes = {
            'stocks': {'weight': 0.30, 'risk_contribution': 0.25},
            'bonds': {'weight': 0.40, 'risk_contribution': 0.25},
            'commodities': {'weight': 0.15, 'risk_contribution': 0.25},
            'tips': {'weight': 0.15, 'risk_contribution': 0.25}  # 通脹保護債券
        }
        
        # 達里奧原則
        self.principles = [
            "透明度帶來信任",
            "多元化是唯一的免費午餐",
            "理解經濟機器的運作",
            "債務週期決定長期趨勢",
            "風險平衡勝過資本平衡",
            "原則高於個人判斷"
        ]
        
        logger.info(f"初始化達里奧代理: {name} - 'Principles over personalities'")
    
    def make_decision(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """
        基於達里奧投資哲學生成決策。
        
        Args:
            data: 市場數據
            market_context: 市場上下文信息
            
        Returns:
            AgentDecision: 達里奧風格的投資決策
        """
        try:
            symbol = market_context.get('symbol', 'UNKNOWN') if market_context else 'UNKNOWN'
            
            # 檢查數據完整性
            if not self._validate_dalio_data(data, market_context):
                return self._create_hold_decision(symbol, "達里奧：'沒有足夠信息時，保持謹慎'")
            
            # 經濟機器分析
            economic_analysis = self._analyze_economic_machine(data, market_context)
            
            # 四季環境識別
            season_analysis = self._identify_economic_season(economic_analysis)
            
            # 債務週期分析
            debt_cycle_analysis = self._analyze_debt_cycles(economic_analysis)
            
            # 風險平價分析（使用父類方法）
            risk_parity_analysis = self._perform_risk_parity_analysis(data, market_context)
            
            # 資產配置優化
            allocation_analysis = self._optimize_all_weather_allocation(
                season_analysis, debt_cycle_analysis, risk_parity_analysis
            )
            
            # 原則檢查
            principle_check = self._check_principles_compliance(allocation_analysis)
            
            # 生成達里奧風格決策
            decision = self._generate_dalio_decision(
                symbol, allocation_analysis, principle_check, market_context
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"達里奧代理決策生成失敗: {e}")
            return self._create_hold_decision(symbol, f"達里奧：'當系統出錯時，回歸基本原則' - {e}")
    
    def _validate_dalio_data(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]]
    ) -> bool:
        """驗證達里奧分析所需數據"""
        # 基礎風險平價數據驗證
        if not super()._validate_data(data, market_context.get('portfolio_assets', []) if market_context else []):
            return False
        
        # 達里奧特有數據要求
        if market_context:
            required_macro_data = ['gdp_growth', 'inflation_rate', 'interest_rates']
            missing_data = [key for key in required_macro_data if key not in market_context]
            
            if missing_data:
                logger.warning(f"達里奧分析缺少宏觀數據: {missing_data}")
                # 不強制要求，可以使用默認值
        
        return True
    
    def _analyze_economic_machine(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析經濟機器"""
        
        # 從市場上下文獲取宏觀數據
        gdp_growth = market_context.get('gdp_growth', 0.02) if market_context else 0.02
        inflation_rate = market_context.get('inflation_rate', 0.02) if market_context else 0.02
        interest_rates = market_context.get('interest_rates', 0.03) if market_context else 0.03
        unemployment = market_context.get('unemployment_rate', 0.05) if market_context else 0.05
        
        # 生產力成長分析
        productivity_analysis = self._analyze_productivity_growth(gdp_growth, inflation_rate)
        
        # 短期債務週期分析
        short_term_cycle = self._analyze_short_term_debt_cycle(interest_rates, inflation_rate)
        
        # 長期債務週期分析
        long_term_cycle = self._analyze_long_term_debt_cycle(market_context)
        
        # 更新經濟機器狀態
        self.economic_machine.update({
            'productivity_growth': productivity_analysis['trend'],
            'short_term_debt_cycle': short_term_cycle['position'],
            'long_term_debt_cycle': long_term_cycle['position']
        })
        
        return {
            'gdp_growth': gdp_growth,
            'inflation_rate': inflation_rate,
            'interest_rates': interest_rates,
            'unemployment': unemployment,
            'productivity_analysis': productivity_analysis,
            'short_term_cycle': short_term_cycle,
            'long_term_cycle': long_term_cycle,
            'machine_health': self._assess_machine_health(productivity_analysis, short_term_cycle, long_term_cycle)
        }
    
    def _analyze_productivity_growth(self, gdp_growth: float, inflation_rate: float) -> Dict[str, Any]:
        """分析生產力成長"""
        # 實際GDP成長率（扣除通脹）
        real_gdp_growth = gdp_growth - inflation_rate
        
        # 生產力成長趨勢
        if real_gdp_growth > 0.03:  # 3%以上
            trend = "strong"
            score = 80.0
        elif real_gdp_growth > 0.015:  # 1.5-3%
            trend = "moderate"
            score = 60.0
        elif real_gdp_growth > 0:  # 0-1.5%
            trend = "weak"
            score = 40.0
        else:  # 負成長
            trend = "declining"
            score = 20.0
        
        return {
            'trend': real_gdp_growth,
            'classification': trend,
            'score': score,
            'real_gdp_growth': real_gdp_growth
        }
    
    def _analyze_short_term_debt_cycle(self, interest_rates: float, inflation_rate: float) -> Dict[str, Any]:
        """分析短期債務週期（5-8年）"""
        # 實際利率
        real_interest_rate = interest_rates - inflation_rate
        
        # 短期債務週期位置
        if real_interest_rate < -0.02:  # 負實際利率
            position = "expansion"
            phase = "late_expansion"
            score = 70.0
        elif real_interest_rate < 0.01:  # 低實際利率
            position = "mid_expansion"
            phase = "mid_expansion"
            score = 60.0
        elif real_interest_rate < 0.03:  # 適度實際利率
            position = "early_expansion"
            phase = "early_expansion"
            score = 50.0
        else:  # 高實際利率
            position = "contraction"
            phase = "contraction"
            score = 30.0
        
        return {
            'position': position,
            'phase': phase,
            'score': score,
            'real_interest_rate': real_interest_rate
        }
    
    def _analyze_long_term_debt_cycle(self, market_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """分析長期債務週期（50-75年）"""
        if not market_context:
            return {'position': 0.5, 'phase': 'unknown', 'score': 50.0}
        
        # 債務水平指標
        debt_to_gdp = market_context.get('debt_to_gdp', 0.8)
        debt_service_ratio = market_context.get('debt_service_ratio', 0.15)
        
        # 長期債務週期位置
        if debt_to_gdp > 1.2 and debt_service_ratio > 0.25:  # 高債務
            position = "late_cycle"
            phase = "deleveraging_risk"
            score = 20.0
        elif debt_to_gdp > 0.9 and debt_service_ratio > 0.2:  # 中高債務
            position = "mid_late_cycle"
            phase = "debt_burden_rising"
            score = 40.0
        elif debt_to_gdp > 0.6:  # 適度債務
            position = "mid_cycle"
            phase = "healthy_leverage"
            score = 70.0
        else:  # 低債務
            position = "early_cycle"
            phase = "low_leverage"
            score = 80.0
        
        return {
            'position': position,
            'phase': phase,
            'score': score,
            'debt_to_gdp': debt_to_gdp,
            'debt_service_ratio': debt_service_ratio
        }

    def _assess_machine_health(
        self,
        productivity_analysis: Dict[str, Any],
        short_term_cycle: Dict[str, Any],
        long_term_cycle: Dict[str, Any]
    ) -> Dict[str, Any]:
        """評估經濟機器健康度"""

        # 各組件評分
        productivity_score = productivity_analysis['score']
        short_term_score = short_term_cycle['score']
        long_term_score = long_term_cycle['score']

        # 權重分配
        weights = {
            'productivity': 0.4,
            'short_term': 0.3,
            'long_term': 0.3
        }

        # 綜合健康評分
        overall_health = (
            productivity_score * weights['productivity'] +
            short_term_score * weights['short_term'] +
            long_term_score * weights['long_term']
        )

        # 健康等級
        if overall_health >= 70:
            health_level = "healthy"
        elif overall_health >= 50:
            health_level = "moderate"
        elif overall_health >= 30:
            health_level = "stressed"
        else:
            health_level = "crisis"

        return {
            'overall_health': overall_health,
            'health_level': health_level,
            'productivity_score': productivity_score,
            'short_term_score': short_term_score,
            'long_term_score': long_term_score
        }

    def _identify_economic_season(self, economic_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """識別經濟四季"""

        gdp_growth = economic_analysis['gdp_growth']
        inflation_rate = economic_analysis['inflation_rate']

        # 成長趨勢
        growth_rising = gdp_growth > 0.02  # 假設2%為中性成長率

        # 通脹趨勢
        inflation_rising = inflation_rate > 0.025  # 假設2.5%為中性通脹率

        # 四季判斷
        if growth_rising and inflation_rising:
            season = "spring"  # 春季：成長上升，通脹上升
            description = "經濟擴張，通脹壓力"
        elif growth_rising and not inflation_rising:
            season = "summer"  # 夏季：成長上升，通脹下降
            description = "理想成長環境"
        elif not growth_rising and not inflation_rising:
            season = "autumn"  # 秋季：成長下降，通脹下降
            description = "經濟放緩，通縮風險"
        else:  # not growth_rising and inflation_rising
            season = "winter"  # 冬季：成長下降，通脹上升
            description = "滯脹環境"

        # 更新經濟機器狀態
        self.economic_machine['current_season'] = season

        # 季節評分
        season_scores = {
            "summer": 80.0,   # 最佳環境
            "spring": 65.0,   # 成長但有通脹壓力
            "autumn": 45.0,   # 成長放緩
            "winter": 25.0    # 最差環境
        }

        return {
            'season': season,
            'description': description,
            'score': season_scores[season],
            'growth_rising': growth_rising,
            'inflation_rising': inflation_rising,
            'optimal_allocation': self._get_season_allocation(season)
        }

    def _get_season_allocation(self, season: str) -> Dict[str, float]:
        """獲取季節性資產配置"""

        allocations = {
            "spring": {  # 成長上升，通脹上升
                'stocks': 0.25,      # 股票受益於成長
                'bonds': 0.25,       # 債券受通脹影響
                'commodities': 0.35, # 商品受益於通脹
                'tips': 0.15         # 通脹保護債券
            },
            "summer": {  # 成長上升，通脹下降
                'stocks': 0.40,      # 股票最佳環境
                'bonds': 0.35,       # 債券表現良好
                'commodities': 0.15, # 商品需求減少
                'tips': 0.10         # 通脹保護需求低
            },
            "autumn": {  # 成長下降，通脹下降
                'stocks': 0.20,      # 股票面臨壓力
                'bonds': 0.50,       # 債券避險需求
                'commodities': 0.15, # 商品需求疲軟
                'tips': 0.15         # 適度通脹保護
            },
            "winter": {  # 成長下降，通脹上升
                'stocks': 0.15,      # 股票最差環境
                'bonds': 0.30,       # 債券受通脹影響
                'commodities': 0.30, # 商品通脹對沖
                'tips': 0.25         # 高通脹保護需求
            }
        }

        return allocations.get(season, self.asset_classes)

    def _analyze_debt_cycles(self, economic_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """分析債務週期影響"""

        short_term_cycle = economic_analysis['short_term_cycle']
        long_term_cycle = economic_analysis['long_term_cycle']

        # 債務週期綜合評分
        debt_cycle_score = (
            short_term_cycle['score'] * 0.6 +  # 短期週期影響更直接
            long_term_cycle['score'] * 0.4
        )

        # 債務週期階段
        if short_term_cycle['phase'] == 'contraction' and long_term_cycle['phase'] in ['deleveraging_risk', 'debt_burden_rising']:
            cycle_stage = "deleveraging"
            risk_level = "high"
        elif short_term_cycle['phase'] in ['late_expansion'] and long_term_cycle['phase'] == 'deleveraging_risk':
            cycle_stage = "peak_debt"
            risk_level = "very_high"
        elif short_term_cycle['phase'] in ['early_expansion', 'mid_expansion'] and long_term_cycle['phase'] == 'healthy_leverage':
            cycle_stage = "healthy_expansion"
            risk_level = "low"
        else:
            cycle_stage = "transition"
            risk_level = "moderate"

        # 投資建議
        debt_cycle_allocation = self._get_debt_cycle_allocation(cycle_stage)

        return {
            'debt_cycle_score': debt_cycle_score,
            'cycle_stage': cycle_stage,
            'risk_level': risk_level,
            'short_term_position': short_term_cycle['position'],
            'long_term_position': long_term_cycle['position'],
            'recommended_allocation': debt_cycle_allocation
        }

    def _get_debt_cycle_allocation(self, cycle_stage: str) -> Dict[str, float]:
        """獲取債務週期配置建議"""

        allocations = {
            "healthy_expansion": {
                'stocks': 0.35,
                'bonds': 0.35,
                'commodities': 0.20,
                'tips': 0.10
            },
            "peak_debt": {
                'stocks': 0.20,
                'bonds': 0.40,
                'commodities': 0.25,
                'tips': 0.15
            },
            "deleveraging": {
                'stocks': 0.15,
                'bonds': 0.50,
                'commodities': 0.20,
                'tips': 0.15
            },
            "transition": {
                'stocks': 0.25,
                'bonds': 0.40,
                'commodities': 0.20,
                'tips': 0.15
            }
        }

        return allocations.get(cycle_stage, self.asset_classes)

    def _perform_risk_parity_analysis(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行風險平價分析"""

        # 使用父類的風險平價方法
        try:
            # 準備資產數據
            portfolio_assets = market_context.get('portfolio_assets', ['stocks', 'bonds', 'commodities', 'tips']) if market_context else ['stocks', 'bonds', 'commodities', 'tips']

            # 簡化的風險平價分析
            risk_parity_weights = {}
            for asset in portfolio_assets:
                risk_parity_weights[asset] = 1.0 / len(portfolio_assets)  # 等權重作為簡化

            return {
                'risk_parity_weights': risk_parity_weights,
                'portfolio_volatility': 0.10,  # 簡化假設
                'diversification_ratio': 1.5,
                'risk_contributions': {asset: 0.25 for asset in portfolio_assets}
            }

        except Exception as e:
            logger.warning(f"風險平價分析失敗: {e}")
            return {
                'risk_parity_weights': self.asset_classes,
                'portfolio_volatility': 0.12,
                'diversification_ratio': 1.0,
                'risk_contributions': {}
            }

    def _optimize_all_weather_allocation(
        self,
        season_analysis: Dict[str, Any],
        debt_cycle_analysis: Dict[str, Any],
        risk_parity_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """優化全天候資產配置"""

        # 獲取各種配置建議
        season_allocation = season_analysis['optimal_allocation']
        debt_cycle_allocation = debt_cycle_analysis['recommended_allocation']
        risk_parity_allocation = risk_parity_analysis['risk_parity_weights']

        # 權重分配
        weights = {
            'season': 0.4,
            'debt_cycle': 0.3,
            'risk_parity': 0.3
        }

        # 綜合配置
        optimized_allocation = {}
        all_assets = set(season_allocation.keys()) | set(debt_cycle_allocation.keys()) | set(risk_parity_allocation.keys())

        for asset in all_assets:
            season_weight = season_allocation.get(asset, 0.0)
            debt_weight = debt_cycle_allocation.get(asset, 0.0)
            risk_weight = risk_parity_allocation.get(asset, 0.0)

            optimized_weight = (
                season_weight * weights['season'] +
                debt_weight * weights['debt_cycle'] +
                risk_weight * weights['risk_parity']
            )

            optimized_allocation[asset] = optimized_weight

        # 標準化權重
        total_weight = sum(optimized_allocation.values())
        if total_weight > 0:
            optimized_allocation = {asset: weight/total_weight for asset, weight in optimized_allocation.items()}

        return {
            'optimized_allocation': optimized_allocation,
            'season_allocation': season_allocation,
            'debt_cycle_allocation': debt_cycle_allocation,
            'risk_parity_allocation': risk_parity_allocation,
            'allocation_confidence': self._calculate_allocation_confidence(season_analysis, debt_cycle_analysis)
        }

    def _calculate_allocation_confidence(
        self,
        season_analysis: Dict[str, Any],
        debt_cycle_analysis: Dict[str, Any]
    ) -> float:
        """計算配置信心度"""

        # 季節分析信心度
        season_confidence = season_analysis['score'] / 100.0

        # 債務週期分析信心度
        debt_confidence = debt_cycle_analysis['debt_cycle_score'] / 100.0

        # 綜合信心度
        overall_confidence = (season_confidence + debt_confidence) / 2

        return min(max(overall_confidence, 0.3), 0.9)  # 限制在30%-90%

    def _check_principles_compliance(self, allocation_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """檢查原則遵循度"""

        optimized_allocation = allocation_analysis['optimized_allocation']

        # 原則檢查
        principles_check = {}

        # 1. 多元化原則
        asset_count = len([w for w in optimized_allocation.values() if w > 0.05])
        diversification_score = min(asset_count / 4.0, 1.0)  # 至少4個資產類別
        principles_check['diversification'] = diversification_score

        # 2. 風險平衡原則
        max_weight = max(optimized_allocation.values()) if optimized_allocation else 0
        risk_balance_score = 1.0 - max(0, (max_weight - 0.4) / 0.4)  # 單一資產不超過40%
        principles_check['risk_balance'] = risk_balance_score

        # 3. 透明度原則
        transparency_score = self.transparency_level
        principles_check['transparency'] = transparency_score

        # 4. 原則一致性
        consistency_score = self.principle_adherence
        principles_check['consistency'] = consistency_score

        # 綜合原則評分
        overall_compliance = np.mean(list(principles_check.values()))

        return {
            'overall_compliance': overall_compliance,
            'principles_check': principles_check,
            'compliant': overall_compliance >= 0.8
        }

    def _generate_dalio_decision(
        self,
        symbol: str,
        allocation_analysis: Dict[str, Any],
        principle_check: Dict[str, Any],
        market_context: Optional[Dict[str, Any]]
    ) -> AgentDecision:
        """生成達里奧風格的投資決策"""
        current_time = datetime.now()

        optimized_allocation = allocation_analysis['optimized_allocation']
        allocation_confidence = allocation_analysis['allocation_confidence']

        # 檢查symbol是否在配置中
        if symbol not in optimized_allocation:
            return self._create_hold_decision(symbol, "達里奧：'該資產不在全天候配置範圍內'")

        target_weight = optimized_allocation[symbol]
        current_weight = self.current_weights.get(symbol, 0.0)
        weight_change = target_weight - current_weight

        # 決定操作方向
        if abs(weight_change) < 0.02:  # 權重變化小於2%
            action = 0
            confidence = 0.7
            reasoning = self._generate_dalio_hold_reasoning(symbol, target_weight, allocation_analysis)
        elif weight_change > 0.02:  # 增加權重
            action = 1
            confidence = min(0.9, allocation_confidence + 0.1)
            reasoning = self._generate_dalio_buy_reasoning(symbol, target_weight, allocation_analysis)
        else:  # 減少權重
            action = -1
            confidence = min(0.9, allocation_confidence + 0.1)
            reasoning = self._generate_dalio_sell_reasoning(symbol, target_weight, allocation_analysis)

        # 原則合規性調整
        if not principle_check['compliant']:
            confidence *= 0.8  # 降低信心度

        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=current_time,
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            expected_return=self._estimate_dalio_return(allocation_analysis),
            risk_assessment=self._assess_dalio_risk(allocation_analysis),
            position_size=target_weight,
            metadata={
                'target_weight': target_weight,
                'current_weight': current_weight,
                'weight_change': weight_change,
                'economic_season': self.economic_machine.get('current_season', 'unknown'),
                'allocation_confidence': allocation_confidence,
                'principles_compliance': principle_check['overall_compliance'],
                'investment_style': 'dalio_all_weather',
                'transparency_level': self.transparency_level
            }
        )

    def _generate_dalio_buy_reasoning(
        self,
        symbol: str,
        target_weight: float,
        allocation_analysis: Dict[str, Any]
    ) -> str:
        """生成達里奧風格的買入推理"""
        season = self.economic_machine.get('current_season', 'unknown')

        return (f"達里奧全天候配置：增加{symbol}權重至{target_weight:.1%}，"
                f"當前經濟季節為{season}，符合多元化和風險平衡原則 - "
                "'多元化是唯一的免費午餐'")

    def _generate_dalio_sell_reasoning(
        self,
        symbol: str,
        target_weight: float,
        allocation_analysis: Dict[str, Any]
    ) -> str:
        """生成達里奧風格的賣出推理"""
        season = self.economic_machine.get('current_season', 'unknown')

        return (f"達里奧全天候配置：調整{symbol}權重至{target_weight:.1%}，"
                f"當前經濟季節為{season}，維持風險平衡 - "
                "'風險平衡勝過資本平衡'")

    def _generate_dalio_hold_reasoning(
        self,
        symbol: str,
        target_weight: float,
        allocation_analysis: Dict[str, Any]
    ) -> str:
        """生成達里奧風格的持有推理"""
        return (f"達里奧全天候持有：{symbol}權重{target_weight:.1%}接近目標，"
                "維持當前配置 - '原則高於個人判斷'")

    def _create_hold_decision(self, symbol: str, reason: str) -> AgentDecision:
        """創建持有決策"""
        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            symbol=symbol,
            action=0,
            confidence=0.6,
            reasoning=reason,
            expected_return=0.0,
            risk_assessment=0.3,  # 達里奧風格風險較低
            position_size=self.current_weights.get(symbol, 0.0)
        )

    def _estimate_dalio_return(self, allocation_analysis: Dict[str, Any]) -> float:
        """估算達里奧風格的預期收益率"""
        # 全天候策略追求穩定收益
        base_return = 0.08  # 基準8%年化收益率

        # 基於配置信心度調整
        confidence_factor = allocation_analysis['allocation_confidence']

        # 經濟季節調整
        season = self.economic_machine.get('current_season', 'unknown')
        season_adjustments = {
            'summer': 0.02,   # 最佳環境
            'spring': 0.01,   # 良好環境
            'autumn': -0.01,  # 一般環境
            'winter': -0.02   # 困難環境
        }
        season_adjustment = season_adjustments.get(season, 0.0)

        expected_return = base_return * confidence_factor + season_adjustment

        return max(0.03, min(expected_return, 0.15))  # 3-15%範圍

    def _assess_dalio_risk(self, allocation_analysis: Dict[str, Any]) -> float:
        """評估達里奧風格的投資風險"""
        # 全天候策略風險較低
        base_risk = 0.25

        # 多元化降低風險
        diversification_benefit = 0.1  # 多元化降低10%風險

        # 經濟週期風險調整
        season = self.economic_machine.get('current_season', 'unknown')
        season_risks = {
            'summer': 0.0,    # 最低風險
            'spring': 0.05,   # 低風險
            'autumn': 0.1,    # 中等風險
            'winter': 0.15    # 較高風險
        }
        season_risk = season_risks.get(season, 0.1)

        overall_risk = base_risk - diversification_benefit + season_risk

        return min(max(overall_risk, 0.1), 0.6)

    def get_investment_philosophy(self) -> str:
        """獲取達里奧投資哲學描述"""
        return (
            "達里奧投資哲學：'理解經濟機器的運作，通過風險平衡而非資本平衡實現全天候投資。' "
            "基於經濟週期和債務週期分析，構建能在各種經濟環境下表現穩定的投資組合。"
            f"透明度水平：{self.transparency_level:.1%}；原則遵循度：{self.principle_adherence:.1%}；"
            f"目標波動率：{self.volatility_target:.1%}。"
            "核心理念：'原則高於個人判斷，多元化是唯一的免費午餐。'"
        )

    def get_economic_machine_status(self) -> Dict[str, Any]:
        """獲取經濟機器狀態"""
        return self.economic_machine.copy()

    def get_dalio_principles(self) -> List[str]:
        """獲取達里奧原則"""
        return self.principles.copy()

    def get_current_season(self) -> str:
        """獲取當前經濟季節"""
        return self.economic_machine.get('current_season', 'unknown')

    def get_asset_allocation(self) -> Dict[str, Dict[str, float]]:
        """獲取資產配置"""
        return self.asset_classes.copy()

    def __str__(self) -> str:
        """字符串表示"""
        season = self.get_current_season()
        return f"DalioAgent(season={season}, assets={len(self.current_weights)})"
