#!/usr/bin/env python3
"""
智能推薦服務
提供策略推薦、參數優化建議、風險提醒功能
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)

class RecommendationType(Enum):
    """推薦類型"""
    STRATEGY = "strategy"
    PARAMETER = "parameter"
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    PORTFOLIO = "portfolio"

class RecommendationPriority(Enum):
    """推薦優先級"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IntelligentRecommendationService:
    """智能推薦服務"""
    
    def __init__(self):
        """初始化推薦服務"""
        self.recommendation_history = []
        self.user_preferences = {}
        self.market_conditions = {}
        
        # 策略模板庫
        self.strategy_templates = self._initialize_strategy_templates()
        
        # 風險閾值配置
        self.risk_thresholds = {
            "max_drawdown": 0.15,
            "volatility": 0.25,
            "sharpe_ratio": 1.0,
            "var_95": 0.05
        }
        
        logger.info("智能推薦服務初始化完成")
    
    def _initialize_strategy_templates(self) -> Dict[str, Dict[str, Any]]:
        """初始化策略模板"""
        return {
            "momentum": {
                "name": "動量策略",
                "description": "基於價格動量的趨勢跟隨策略",
                "risk_level": "medium",
                "expected_return": 0.12,
                "max_drawdown": 0.08,
                "parameters": {
                    "lookback_period": 20,
                    "momentum_threshold": 0.02,
                    "stop_loss": 0.05
                },
                "suitable_conditions": ["trending_market", "high_volatility"]
            },
            "mean_reversion": {
                "name": "均值回歸策略",
                "description": "基於價格均值回歸的反轉策略",
                "risk_level": "low",
                "expected_return": 0.08,
                "max_drawdown": 0.05,
                "parameters": {
                    "lookback_period": 30,
                    "deviation_threshold": 2.0,
                    "holding_period": 5
                },
                "suitable_conditions": ["sideways_market", "low_volatility"]
            },
            "ai_prediction": {
                "name": "AI預測策略",
                "description": "基於機器學習模型的預測策略",
                "risk_level": "high",
                "expected_return": 0.18,
                "max_drawdown": 0.12,
                "parameters": {
                    "model_type": "lstm",
                    "prediction_horizon": 5,
                    "confidence_threshold": 0.7
                },
                "suitable_conditions": ["any_market", "sufficient_data"]
            },
            "value_investing": {
                "name": "價值投資策略",
                "description": "基於基本面分析的長期投資策略",
                "risk_level": "low",
                "expected_return": 0.10,
                "max_drawdown": 0.06,
                "parameters": {
                    "pe_threshold": 15,
                    "pb_threshold": 1.5,
                    "holding_period": 90
                },
                "suitable_conditions": ["bear_market", "undervalued_stocks"]
            }
        }
    
    def analyze_user_profile(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析用戶畫像"""
        profile = {
            "risk_tolerance": "medium",
            "investment_horizon": "medium_term",
            "experience_level": "intermediate",
            "preferred_strategies": [],
            "capital_size": "medium"
        }
        
        # 根據歷史交易分析風險偏好
        if "trading_history" in user_data:
            trades = user_data["trading_history"]
            if trades:
                avg_position_size = np.mean([t.get("position_size", 0) for t in trades])
                max_loss = max([t.get("pnl", 0) for t in trades if t.get("pnl", 0) < 0], default=0)
                
                if avg_position_size > 0.1:  # 大倉位
                    profile["risk_tolerance"] = "high"
                elif avg_position_size < 0.05:  # 小倉位
                    profile["risk_tolerance"] = "low"
                
                if abs(max_loss) > 0.1:  # 能承受大虧損
                    profile["risk_tolerance"] = "high"
        
        # 根據投資組合分析投資期限
        if "portfolio" in user_data:
            portfolio = user_data["portfolio"]
            if portfolio:
                avg_holding_period = np.mean([p.get("holding_days", 30) for p in portfolio])
                
                if avg_holding_period > 90:
                    profile["investment_horizon"] = "long_term"
                elif avg_holding_period < 7:
                    profile["investment_horizon"] = "short_term"
        
        return profile
    
    def get_strategy_recommendations(self, user_profile: Dict[str, Any], 
                                   market_conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """獲取策略推薦"""
        recommendations = []
        
        # 分析市場條件
        market_trend = market_conditions.get("trend", "sideways")
        volatility_level = market_conditions.get("volatility", "medium")
        
        # 為每個策略計算適合度分數
        for strategy_id, strategy in self.strategy_templates.items():
            score = self._calculate_strategy_score(strategy, user_profile, market_conditions)
            
            if score > 0.6:  # 只推薦分數較高的策略
                recommendation = {
                    "type": RecommendationType.STRATEGY,
                    "strategy_id": strategy_id,
                    "strategy_name": strategy["name"],
                    "description": strategy["description"],
                    "score": score,
                    "priority": self._determine_priority(score),
                    "reasons": self._generate_strategy_reasons(strategy, user_profile, market_conditions),
                    "expected_return": strategy["expected_return"],
                    "risk_level": strategy["risk_level"],
                    "recommended_parameters": strategy["parameters"].copy()
                }
                
                recommendations.append(recommendation)
        
        # 按分數排序
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return recommendations[:5]  # 返回前5個推薦
    
    def _calculate_strategy_score(self, strategy: Dict[str, Any], 
                                user_profile: Dict[str, Any], 
                                market_conditions: Dict[str, Any]) -> float:
        """計算策略適合度分數"""
        score = 0.5  # 基礎分數
        
        # 風險匹配度 (30%)
        risk_match = self._calculate_risk_match(strategy["risk_level"], user_profile["risk_tolerance"])
        score += risk_match * 0.3
        
        # 市場條件匹配度 (40%)
        market_match = self._calculate_market_match(strategy["suitable_conditions"], market_conditions)
        score += market_match * 0.4
        
        # 收益期望匹配度 (20%)
        return_match = self._calculate_return_match(strategy["expected_return"], user_profile)
        score += return_match * 0.2
        
        # 經驗水平匹配度 (10%)
        experience_match = self._calculate_experience_match(strategy, user_profile["experience_level"])
        score += experience_match * 0.1
        
        return min(score, 1.0)
    
    def _calculate_risk_match(self, strategy_risk: str, user_risk: str) -> float:
        """計算風險匹配度"""
        risk_levels = {"low": 1, "medium": 2, "high": 3}
        
        strategy_level = risk_levels.get(strategy_risk, 2)
        user_level = risk_levels.get(user_risk, 2)
        
        diff = abs(strategy_level - user_level)
        
        if diff == 0:
            return 1.0
        elif diff == 1:
            return 0.7
        else:
            return 0.3
    
    def _calculate_market_match(self, suitable_conditions: List[str], 
                              market_conditions: Dict[str, Any]) -> float:
        """計算市場條件匹配度"""
        if "any_market" in suitable_conditions:
            return 1.0
        
        current_trend = market_conditions.get("trend", "sideways")
        current_volatility = market_conditions.get("volatility", "medium")
        
        match_score = 0.0
        
        # 趨勢匹配
        if f"{current_trend}_market" in suitable_conditions:
            match_score += 0.6
        
        # 波動性匹配
        if f"{current_volatility}_volatility" in suitable_conditions:
            match_score += 0.4
        
        return min(match_score, 1.0)
    
    def _calculate_return_match(self, expected_return: float, user_profile: Dict[str, Any]) -> float:
        """計算收益期望匹配度"""
        # 根據風險偏好調整收益期望
        risk_return_mapping = {
            "low": 0.08,
            "medium": 0.12,
            "high": 0.18
        }
        
        user_expected = risk_return_mapping.get(user_profile["risk_tolerance"], 0.12)
        
        diff = abs(expected_return - user_expected)
        
        if diff < 0.02:
            return 1.0
        elif diff < 0.05:
            return 0.8
        elif diff < 0.08:
            return 0.6
        else:
            return 0.3
    
    def _calculate_experience_match(self, strategy: Dict[str, Any], experience_level: str) -> float:
        """計算經驗水平匹配度"""
        complex_strategies = ["ai_prediction"]
        simple_strategies = ["mean_reversion", "value_investing"]
        
        strategy_id = strategy.get("id", "")
        
        if experience_level == "beginner":
            return 1.0 if strategy_id in simple_strategies else 0.5
        elif experience_level == "intermediate":
            return 0.8
        else:  # advanced
            return 1.0 if strategy_id in complex_strategies else 0.9
    
    def _determine_priority(self, score: float) -> RecommendationPriority:
        """確定推薦優先級"""
        if score >= 0.9:
            return RecommendationPriority.CRITICAL
        elif score >= 0.8:
            return RecommendationPriority.HIGH
        elif score >= 0.7:
            return RecommendationPriority.MEDIUM
        else:
            return RecommendationPriority.LOW
    
    def _generate_strategy_reasons(self, strategy: Dict[str, Any], 
                                 user_profile: Dict[str, Any], 
                                 market_conditions: Dict[str, Any]) -> List[str]:
        """生成策略推薦理由"""
        reasons = []
        
        # 風險匹配理由
        if strategy["risk_level"] == user_profile["risk_tolerance"]:
            reasons.append(f"風險水平與您的偏好({user_profile['risk_tolerance']})完全匹配")
        
        # 市場條件理由
        market_trend = market_conditions.get("trend", "sideways")
        if f"{market_trend}_market" in strategy["suitable_conditions"]:
            reasons.append(f"適合當前{market_trend}市場環境")
        
        # 收益期望理由
        if strategy["expected_return"] > 0.15:
            reasons.append("具有較高的預期收益潛力")
        elif strategy["max_drawdown"] < 0.08:
            reasons.append("具有較低的最大回撤風險")
        
        return reasons
    
    def get_parameter_optimization_suggestions(self, strategy_id: str, 
                                             current_params: Dict[str, Any],
                                             performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """獲取參數優化建議"""
        suggestions = []
        
        if strategy_id not in self.strategy_templates:
            return suggestions
        
        template = self.strategy_templates[strategy_id]
        current_performance = performance_data.get("sharpe_ratio", 0)
        
        # 分析當前參數表現
        if current_performance < 1.0:
            # 表現不佳，建議調整參數
            
            if strategy_id == "momentum":
                # 動量策略參數優化
                current_lookback = current_params.get("lookback_period", 20)
                
                if current_performance < 0.5:
                    suggestions.append({
                        "type": RecommendationType.PARAMETER,
                        "parameter": "lookback_period",
                        "current_value": current_lookback,
                        "suggested_value": max(10, current_lookback - 5),
                        "reason": "縮短回看期間可能提高策略敏感度",
                        "expected_improvement": 0.15
                    })
                
                current_threshold = current_params.get("momentum_threshold", 0.02)
                suggestions.append({
                    "type": RecommendationType.PARAMETER,
                    "parameter": "momentum_threshold",
                    "current_value": current_threshold,
                    "suggested_value": current_threshold * 1.2,
                    "reason": "提高動量閾值可以過濾噪音信號",
                    "expected_improvement": 0.10
                })
            
            elif strategy_id == "mean_reversion":
                # 均值回歸策略參數優化
                current_deviation = current_params.get("deviation_threshold", 2.0)
                
                suggestions.append({
                    "type": RecommendationType.PARAMETER,
                    "parameter": "deviation_threshold",
                    "current_value": current_deviation,
                    "suggested_value": current_deviation * 0.9,
                    "reason": "降低偏差閾值可以增加交易機會",
                    "expected_improvement": 0.12
                })
        
        return suggestions
    
    def get_risk_alerts(self, portfolio_data: Dict[str, Any], 
                       market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """獲取風險提醒"""
        alerts = []
        
        # 檢查投資組合風險指標
        current_drawdown = portfolio_data.get("current_drawdown", 0)
        if current_drawdown > self.risk_thresholds["max_drawdown"]:
            alerts.append({
                "type": RecommendationType.RISK,
                "priority": RecommendationPriority.HIGH,
                "title": "最大回撤警告",
                "message": f"當前回撤({current_drawdown:.2%})超過風險閾值({self.risk_thresholds['max_drawdown']:.2%})",
                "suggestions": [
                    "考慮減少倉位",
                    "調整止損策略",
                    "分散投資風險"
                ]
            })
        
        # 檢查波動性
        current_volatility = portfolio_data.get("volatility", 0)
        if current_volatility > self.risk_thresholds["volatility"]:
            alerts.append({
                "type": RecommendationType.RISK,
                "priority": RecommendationPriority.MEDIUM,
                "title": "波動性過高",
                "message": f"投資組合波動性({current_volatility:.2%})過高",
                "suggestions": [
                    "增加穩定性資產配置",
                    "使用對沖策略",
                    "調整倉位大小"
                ]
            })
        
        # 檢查集中度風險
        holdings = portfolio_data.get("holdings", [])
        if holdings:
            max_weight = max([h.get("weight", 0) for h in holdings])
            if max_weight > 0.3:
                alerts.append({
                    "type": RecommendationType.RISK,
                    "priority": RecommendationPriority.MEDIUM,
                    "title": "集中度風險",
                    "message": f"單一持股權重({max_weight:.2%})過高",
                    "suggestions": [
                        "分散投資組合",
                        "減少大權重持股",
                        "增加不同行業配置"
                    ]
                })
        
        return alerts
    
    def get_opportunity_alerts(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """獲取機會提醒"""
        opportunities = []
        
        # 模擬市場機會檢測
        market_sentiment = market_data.get("sentiment", 0.5)
        volatility_index = market_data.get("vix", 20)
        
        # 低波動性機會
        if volatility_index < 15:
            opportunities.append({
                "type": RecommendationType.OPPORTUNITY,
                "priority": RecommendationPriority.MEDIUM,
                "title": "低波動性投資機會",
                "message": "市場波動性較低，適合建立長期倉位",
                "suggestions": [
                    "考慮增加股票配置",
                    "實施價值投資策略",
                    "建立核心持倉"
                ]
            })
        
        # 超賣機會
        if market_sentiment < 0.3:
            opportunities.append({
                "type": RecommendationType.OPPORTUNITY,
                "priority": RecommendationPriority.HIGH,
                "title": "市場超賣機會",
                "message": "市場情緒過度悲觀，可能存在反彈機會",
                "suggestions": [
                    "關注優質股票的買入機會",
                    "考慮逆向投資策略",
                    "分批建倉降低風險"
                ]
            })
        
        return opportunities
    
    def generate_comprehensive_recommendations(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成綜合推薦報告"""
        # 分析用戶畫像
        user_profile = self.analyze_user_profile(user_data)
        
        # 模擬市場條件
        market_conditions = {
            "trend": "trending",
            "volatility": "medium",
            "sentiment": 0.6
        }
        
        # 生成各類推薦
        strategy_recommendations = self.get_strategy_recommendations(user_profile, market_conditions)
        risk_alerts = self.get_risk_alerts(user_data.get("portfolio", {}), market_conditions)
        opportunities = self.get_opportunity_alerts(market_conditions)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "user_profile": user_profile,
            "market_conditions": market_conditions,
            "recommendations": {
                "strategies": strategy_recommendations,
                "risk_alerts": risk_alerts,
                "opportunities": opportunities
            },
            "summary": {
                "total_recommendations": len(strategy_recommendations) + len(risk_alerts) + len(opportunities),
                "high_priority_count": len([r for r in strategy_recommendations + risk_alerts + opportunities 
                                          if r.get("priority") == RecommendationPriority.HIGH]),
                "top_strategy": strategy_recommendations[0]["strategy_name"] if strategy_recommendations else None
            }
        }
