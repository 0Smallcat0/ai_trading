"""
資金計算模組

此模組提供資金相關的計算功能，包括：
- 風險指標計算
- 警報條件檢查
- 警報創建和管理
"""

import logging
from datetime import datetime
from typing import Any, Dict
from enum import Enum

# 設定日誌
logger = logging.getLogger("risk.live.fund_calculator")


class FundAlertLevel(Enum):
    """資金警報級別枚舉"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class FundCalculator:
    """資金計算器"""
    
    def __init__(self, monitor_params: Dict[str, Any]):
        """
        初始化資金計算器
        
        Args:
            monitor_params (Dict[str, Any]): 監控參數
        """
        self.monitor_params = monitor_params
    
    def calculate_risk_indicators(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """
        計算風險指標
        
        Args:
            status (Dict[str, Any]): 資金狀態
            
        Returns:
            Dict[str, Any]: 風險指標
        """
        try:
            margin_rate = status["margin_usage_rate"]
            cash = status["cash"]
            
            # 保證金警報級別
            if margin_rate >= self.monitor_params["margin_emergency_threshold"]:
                margin_alert_level = FundAlertLevel.EMERGENCY.value
            elif margin_rate >= self.monitor_params["margin_critical_threshold"]:
                margin_alert_level = FundAlertLevel.CRITICAL.value
            elif margin_rate >= self.monitor_params["margin_warning_threshold"]:
                margin_alert_level = FundAlertLevel.WARNING.value
            else:
                margin_alert_level = FundAlertLevel.INFO.value
            
            # 現金警報級別
            if cash <= self.monitor_params["cash_critical_threshold"]:
                cash_alert_level = FundAlertLevel.CRITICAL.value
            elif cash <= self.monitor_params["cash_warning_threshold"]:
                cash_alert_level = FundAlertLevel.WARNING.value
            else:
                cash_alert_level = FundAlertLevel.INFO.value
            
            # 整體風險級別
            if margin_alert_level == FundAlertLevel.EMERGENCY.value or cash_alert_level == FundAlertLevel.CRITICAL.value:
                overall_risk_level = FundAlertLevel.EMERGENCY.value
            elif margin_alert_level == FundAlertLevel.CRITICAL.value:
                overall_risk_level = FundAlertLevel.CRITICAL.value
            elif margin_alert_level == FundAlertLevel.WARNING.value or cash_alert_level == FundAlertLevel.WARNING.value:
                overall_risk_level = FundAlertLevel.WARNING.value
            else:
                overall_risk_level = FundAlertLevel.INFO.value
            
            return {
                "margin_alert_level": margin_alert_level,
                "cash_alert_level": cash_alert_level,
                "overall_risk_level": overall_risk_level,
                "margin_safety_buffer": max(0, self.monitor_params["margin_warning_threshold"] - margin_rate),
                "cash_safety_buffer": max(0, cash - self.monitor_params["cash_warning_threshold"]),
            }
            
        except Exception as e:
            logger.exception(f"計算風險指標失敗: {e}")
            return {
                "margin_alert_level": FundAlertLevel.INFO.value,
                "cash_alert_level": FundAlertLevel.INFO.value,
                "overall_risk_level": FundAlertLevel.INFO.value,
                "margin_safety_buffer": 0,
                "cash_safety_buffer": 0,
            }
    
    def check_alert_conditions(
        self, 
        current_status: Dict[str, Any], 
        old_status: Dict[str, Any]
    ) -> list:
        """
        檢查警報條件
        
        Args:
            current_status (Dict[str, Any]): 當前資金狀態
            old_status (Dict[str, Any]): 舊的資金狀態
            
        Returns:
            list: 需要創建的警報列表
        """
        alerts_to_create = []
        
        try:
            # 檢查保證金使用率
            margin_rate = current_status["margin_usage_rate"]
            old_margin_rate = old_status.get("margin_usage_rate", 0)
            
            if margin_rate >= self.monitor_params["margin_emergency_threshold"]:
                if old_margin_rate < self.monitor_params["margin_emergency_threshold"]:
                    alerts_to_create.append({
                        "level": FundAlertLevel.EMERGENCY,
                        "title": "保證金使用率達到緊急水平",
                        "message": f"保證金使用率: {margin_rate:.1%}",
                        "data": {"margin_usage_rate": margin_rate}
                    })
            elif margin_rate >= self.monitor_params["margin_critical_threshold"]:
                if old_margin_rate < self.monitor_params["margin_critical_threshold"]:
                    alerts_to_create.append({
                        "level": FundAlertLevel.CRITICAL,
                        "title": "保證金使用率達到危險水平",
                        "message": f"保證金使用率: {margin_rate:.1%}",
                        "data": {"margin_usage_rate": margin_rate}
                    })
            elif margin_rate >= self.monitor_params["margin_warning_threshold"]:
                if old_margin_rate < self.monitor_params["margin_warning_threshold"]:
                    alerts_to_create.append({
                        "level": FundAlertLevel.WARNING,
                        "title": "保證金使用率達到警告水平",
                        "message": f"保證金使用率: {margin_rate:.1%}",
                        "data": {"margin_usage_rate": margin_rate}
                    })
            
            # 檢查現金餘額
            cash = current_status["cash"]
            old_cash = old_status.get("cash", 0)
            
            if cash <= self.monitor_params["cash_critical_threshold"]:
                if old_cash > self.monitor_params["cash_critical_threshold"]:
                    alerts_to_create.append({
                        "level": FundAlertLevel.CRITICAL,
                        "title": "現金餘額不足",
                        "message": f"現金餘額: {cash:,.0f}",
                        "data": {"cash": cash}
                    })
            elif cash <= self.monitor_params["cash_warning_threshold"]:
                if old_cash > self.monitor_params["cash_warning_threshold"]:
                    alerts_to_create.append({
                        "level": FundAlertLevel.WARNING,
                        "title": "現金餘額偏低",
                        "message": f"現金餘額: {cash:,.0f}",
                        "data": {"cash": cash}
                    })
            
            return alerts_to_create
            
        except Exception as e:
            logger.exception(f"檢查警報條件失敗: {e}")
            return []
    
    def create_alert_record(
        self, 
        level: FundAlertLevel, 
        title: str,
        message: str, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        創建警報記錄
        
        Args:
            level (FundAlertLevel): 警報級別
            title (str): 警報標題
            message (str): 警報訊息
            data (Dict[str, Any]): 警報數據
            
        Returns:
            Dict[str, Any]: 警報記錄
        """
        try:
            alert = {
                "timestamp": datetime.now(),
                "level": level.value,
                "title": title,
                "message": message,
                "data": data,
            }
            
            logger.warning(f"資金警報 [{level.value.upper()}]: {title} - {message}")
            
            return alert
            
        except Exception as e:
            logger.exception(f"創建警報記錄失敗: {e}")
            return {
                "timestamp": datetime.now(),
                "level": FundAlertLevel.INFO.value,
                "title": "警報創建失敗",
                "message": str(e),
                "data": {},
            }
    
    def calculate_leverage_ratio(self, fund_status: Dict[str, Any]) -> float:
        """
        計算槓桿比例
        
        Args:
            fund_status (Dict[str, Any]): 資金狀態
            
        Returns:
            float: 槓桿比例
        """
        try:
            total_value = fund_status.get("total_value", 0)
            cash = fund_status.get("cash", 0)
            
            if cash <= 0:
                return 0.0
            
            leverage_ratio = total_value / cash
            return max(1.0, leverage_ratio)  # 最小槓桿比例為1
            
        except Exception as e:
            logger.exception(f"計算槓桿比例失敗: {e}")
            return 1.0
    
    def calculate_available_buying_power(self, fund_status: Dict[str, Any]) -> float:
        """
        計算可用購買力
        
        Args:
            fund_status (Dict[str, Any]): 資金狀態
            
        Returns:
            float: 可用購買力
        """
        try:
            cash = fund_status.get("cash", 0)
            margin_available = fund_status.get("margin_available", 0)
            
            # 可用購買力 = 現金 + 可用保證金
            buying_power = cash + margin_available
            
            return max(0.0, buying_power)
            
        except Exception as e:
            logger.exception(f"計算可用購買力失敗: {e}")
            return 0.0
    
    def check_margin_requirements(
        self, 
        fund_status: Dict[str, Any], 
        required_margin: float
    ) -> Dict[str, Any]:
        """
        檢查保證金需求
        
        Args:
            fund_status (Dict[str, Any]): 資金狀態
            required_margin (float): 所需保證金
            
        Returns:
            Dict[str, Any]: 檢查結果
        """
        try:
            margin_available = fund_status.get("margin_available", 0)
            margin_used = fund_status.get("margin_used", 0)
            total_margin = margin_used + margin_available
            
            # 檢查是否有足夠保證金
            sufficient = margin_available >= required_margin
            
            # 計算使用率
            if total_margin > 0:
                usage_rate_after = (margin_used + required_margin) / total_margin
            else:
                usage_rate_after = 1.0
            
            return {
                "sufficient": sufficient,
                "available_margin": margin_available,
                "required_margin": required_margin,
                "shortage": max(0, required_margin - margin_available),
                "usage_rate_after": usage_rate_after,
                "exceeds_warning": usage_rate_after >= self.monitor_params["margin_warning_threshold"],
                "exceeds_critical": usage_rate_after >= self.monitor_params["margin_critical_threshold"],
                "exceeds_emergency": usage_rate_after >= self.monitor_params["margin_emergency_threshold"],
            }

        except Exception as e:
            logger.exception(f"檢查保證金需求失敗: {e}")
            return {
                "sufficient": False,
                "available_margin": 0,
                "required_margin": required_margin,
                "shortage": required_margin,
                "usage_rate_after": 1.0,
                "exceeds_warning": True,
                "exceeds_critical": True,
                "exceeds_emergency": True,
            }

    def calculate_position_value_breakdown(self, positions: Dict[str, Any]) -> Dict[str, Any]:
        """
        計算持倉價值分解

        Args:
            positions (Dict[str, Any]): 持倉資訊

        Returns:
            Dict[str, Any]: 持倉價值分解
        """
        try:
            total_long_value = 0.0
            total_short_value = 0.0
            total_unrealized_pnl = 0.0
            position_count = 0

            position_details = []

            for symbol, position in positions.items():
                quantity = position.get("quantity", 0)
                market_value = position.get("market_value", 0)
                unrealized_pnl = position.get("unrealized_pnl", 0)
                avg_price = position.get("avg_price", 0)
                current_price = position.get("current_price", 0)

                if quantity != 0:
                    position_count += 1

                    if quantity > 0:  # 多頭
                        total_long_value += market_value
                    else:  # 空頭
                        total_short_value += abs(market_value)

                    total_unrealized_pnl += unrealized_pnl

                    # 計算持倉收益率
                    if avg_price > 0:
                        return_rate = (current_price - avg_price) / avg_price
                        if quantity < 0:  # 空頭收益率相反
                            return_rate = -return_rate
                    else:
                        return_rate = 0.0

                    position_details.append({
                        "symbol": symbol,
                        "quantity": quantity,
                        "market_value": market_value,
                        "unrealized_pnl": unrealized_pnl,
                        "return_rate": return_rate,
                        "weight": 0.0,  # 將在後面計算
                    })

            total_position_value = total_long_value + total_short_value

            # 計算各持倉權重
            for detail in position_details:
                if total_position_value > 0:
                    detail["weight"] = abs(detail["market_value"]) / total_position_value
                else:
                    detail["weight"] = 0.0

            return {
                "total_position_value": total_position_value,
                "total_long_value": total_long_value,
                "total_short_value": total_short_value,
                "total_unrealized_pnl": total_unrealized_pnl,
                "position_count": position_count,
                "long_short_ratio": total_long_value / total_short_value if total_short_value > 0 else float('inf'),
                "position_details": position_details,
            }

        except Exception as e:
            logger.exception(f"計算持倉價值分解失敗: {e}")
            return {
                "total_position_value": 0.0,
                "total_long_value": 0.0,
                "total_short_value": 0.0,
                "total_unrealized_pnl": 0.0,
                "position_count": 0,
                "long_short_ratio": 0.0,
                "position_details": [],
            }

    def calculate_risk_metrics(self, fund_status: Dict[str, Any], positions: Dict[str, Any]) -> Dict[str, Any]:
        """
        計算風險指標

        Args:
            fund_status (Dict[str, Any]): 資金狀態
            positions (Dict[str, Any]): 持倉資訊

        Returns:
            Dict[str, Any]: 風險指標
        """
        try:
            total_value = fund_status.get("total_value", 0)
            cash = fund_status.get("cash", 0)
            margin_used = fund_status.get("margin_used", 0)
            margin_available = fund_status.get("margin_available", 0)

            # 計算持倉價值分解
            position_breakdown = self.calculate_position_value_breakdown(positions)

            # 資金使用效率
            if total_value > 0:
                cash_ratio = cash / total_value
                position_ratio = position_breakdown["total_position_value"] / total_value
            else:
                cash_ratio = 1.0
                position_ratio = 0.0

            # 槓桿相關指標
            leverage_ratio = self.calculate_leverage_ratio(fund_status)
            effective_leverage = position_breakdown["total_position_value"] / cash if cash > 0 else 0.0

            # 保證金相關指標
            total_margin = margin_used + margin_available
            margin_utilization = margin_used / total_margin if total_margin > 0 else 0.0
            margin_buffer = margin_available / total_margin if total_margin > 0 else 0.0

            # 風險集中度
            max_position_weight = 0.0
            if position_breakdown["position_details"]:
                max_position_weight = max(detail["weight"] for detail in position_breakdown["position_details"])

            return {
                "cash_ratio": cash_ratio,
                "position_ratio": position_ratio,
                "leverage_ratio": leverage_ratio,
                "effective_leverage": effective_leverage,
                "margin_utilization": margin_utilization,
                "margin_buffer": margin_buffer,
                "max_position_weight": max_position_weight,
                "position_count": position_breakdown["position_count"],
                "long_short_ratio": position_breakdown["long_short_ratio"],
                "total_unrealized_pnl": position_breakdown["total_unrealized_pnl"],
                "unrealized_pnl_ratio": position_breakdown["total_unrealized_pnl"] / total_value if total_value > 0 else 0.0,
            }

        except Exception as e:
            logger.exception(f"計算風險指標失敗: {e}")
            return {
                "cash_ratio": 0.0,
                "position_ratio": 0.0,
                "leverage_ratio": 1.0,
                "effective_leverage": 0.0,
                "margin_utilization": 0.0,
                "margin_buffer": 1.0,
                "max_position_weight": 0.0,
                "position_count": 0,
                "long_short_ratio": 0.0,
                "total_unrealized_pnl": 0.0,
                "unrealized_pnl_ratio": 0.0,
            }
