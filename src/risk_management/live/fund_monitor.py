"""
實時資金監控

此模組提供實時資金監控功能，包括：
- 可用資金追蹤
- 已用保證金監控
- 總資產價值計算
- 資金使用率警報

重構後的模組，繼承自 fund_monitor_base.py，計算邏輯分離到 fund_calculator.py
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from src.execution.broker_base import BrokerBase
from .fund_monitor_base import FundMonitorBase
from .fund_calculator import FundCalculator, FundAlertLevel

# 設定日誌
logger = logging.getLogger("risk.live.fund_monitor")


class FundMonitor(FundMonitorBase):
    """實時資金監控器"""

    def __init__(self, broker: BrokerBase):
        """
        初始化資金監控器

        Args:
            broker (BrokerBase): 券商適配器
        """
        super().__init__(broker)

        # 監控參數
        self.monitor_params = {
            "update_interval": 5,  # 更新間隔 (秒)
            "margin_warning_threshold": 0.7,  # 保證金警告閾值 70%
            "margin_critical_threshold": 0.85,  # 保證金危險閾值 85%
            "margin_emergency_threshold": 0.95,  # 保證金緊急閾值 95%
            "cash_warning_threshold": 10000,  # 現金警告閾值
            "cash_critical_threshold": 5000,  # 現金危險閾值
        }

        # 初始化計算器
        self.calculator = FundCalculator(self.monitor_params)

    def start_monitoring(self):
        """開始監控"""
        super().start_monitoring(self.monitor_params["update_interval"])
    
    def get_fund_summary(self) -> Dict[str, Any]:
        """
        獲取資金摘要

        Returns:
            Dict[str, Any]: 資金摘要
        """
        with self._monitor_lock:
            status = self.fund_status.copy()

            # 計算風險指標
            risk_indicators = self.calculator.calculate_risk_indicators(status)

            return {
                "basic_info": {
                    "cash": status["cash"],
                    "buying_power": status["buying_power"],
                    "total_value": status["total_value"],
                    "positions_value": status["positions_value"],
                    "unrealized_pnl": status["unrealized_pnl"],
                },
                "margin_info": {
                    "margin_used": status["margin_used"],
                    "margin_available": status["margin_available"],
                    "margin_usage_rate": status["margin_usage_rate"],
                    "margin_alert_level": risk_indicators["margin_alert_level"],
                },
                "risk_indicators": risk_indicators,
                "last_update": status["last_update"],
            }
    

    
    def update_monitor_params(self, **kwargs) -> bool:
        """
        更新監控參數

        Args:
            **kwargs: 參數

        Returns:
            bool: 是否更新成功
        """
        try:
            for key, value in kwargs.items():
                if key in self.monitor_params:
                    self.monitor_params[key] = value
                    # 同時更新計算器的參數
                    self.calculator.monitor_params[key] = value
                    logger.info(f"已更新資金監控參數 {key}: {value}")
            return True
        except Exception as e:
            logger.exception(f"更新資金監控參數失敗: {e}")
            return False
    
    def _check_alert_conditions(self, old_status: Dict[str, Any]):
        """
        檢查警報條件

        Args:
            old_status (Dict[str, Any]): 舊的資金狀態
        """
        try:
            current_status = self.fund_status

            # 使用計算器檢查警報條件
            alerts_to_create = self.calculator.check_alert_conditions(current_status, old_status)

            # 創建所有需要的警報
            for alert_info in alerts_to_create:
                self._create_alert(
                    alert_info["level"],
                    alert_info["title"],
                    alert_info["message"],
                    alert_info["data"]
                )

        except Exception as e:
            logger.exception(f"檢查警報條件失敗: {e}")

    def _create_alert(self, level: FundAlertLevel, title: str,
                     message: str, data: Dict[str, Any]):
        """
        創建警報

        Args:
            level (FundAlertLevel): 警報級別
            title (str): 警報標題
            message (str): 警報訊息
            data (Dict[str, Any]): 警報數據
        """
        try:
            # 使用計算器創建警報記錄
            alert = self.calculator.create_alert_record(level, title, message, data)

            self.alerts.append(alert)

            # 保持警報記錄在合理範圍內
            if len(self.alerts) > self.max_alerts_size:
                self.alerts = self.alerts[-self.max_alerts_size//2:]

            # 調用相應的回調函數
            if self.on_alert:
                self.on_alert(alert)

            if level in [FundAlertLevel.WARNING, FundAlertLevel.CRITICAL, FundAlertLevel.EMERGENCY]:
                if "margin_usage_rate" in data and self.on_margin_warning:
                    self.on_margin_warning(alert)
                elif "cash" in data and self.on_cash_warning:
                    self.on_cash_warning(alert)

        except Exception as e:
            logger.exception(f"創建警報失敗: {e}")

    # 新增便利方法，使用計算器的功能
    def calculate_leverage_ratio(self) -> float:
        """計算當前槓桿比例"""
        with self._monitor_lock:
            return self.calculator.calculate_leverage_ratio(self.fund_status)

    def calculate_available_buying_power(self) -> float:
        """計算可用購買力"""
        with self._monitor_lock:
            return self.calculator.calculate_available_buying_power(self.fund_status)

    def check_margin_requirements(self, required_margin: float) -> Dict[str, Any]:
        """檢查保證金需求"""
        with self._monitor_lock:
            return self.calculator.check_margin_requirements(self.fund_status, required_margin)

    def get_detailed_fund_analysis(self) -> Dict[str, Any]:
        """
        獲取詳細的資金分析

        Returns:
            Dict[str, Any]: 詳細資金分析
        """
        try:
            with self._monitor_lock:
                # 獲取持倉資訊
                positions = self.broker.get_positions()

                # 計算風險指標
                risk_metrics = self.calculator.calculate_risk_metrics(self.fund_status, positions)

                # 計算持倉價值分解
                position_breakdown = self.calculator.calculate_position_value_breakdown(positions)

                # 基本資金摘要
                fund_summary = self.get_fund_summary()

                return {
                    "fund_summary": fund_summary,
                    "risk_metrics": risk_metrics,
                    "position_breakdown": position_breakdown,
                    "analysis_timestamp": datetime.now(),
                }

        except Exception as e:
            logger.exception(f"獲取詳細資金分析失敗: {e}")
            return {
                "fund_summary": {},
                "risk_metrics": {},
                "position_breakdown": {},
                "analysis_timestamp": datetime.now(),
                "error": str(e),
            }

    def check_leverage_limits(self, max_leverage: float = 3.0) -> Dict[str, Any]:
        """
        檢查槓桿限制

        Args:
            max_leverage (float): 最大槓桿比例

        Returns:
            Dict[str, Any]: 槓桿檢查結果
        """
        try:
            current_leverage = self.calculate_leverage_ratio()

            exceeds_limit = current_leverage > max_leverage
            leverage_buffer = max_leverage - current_leverage

            # 計算可用的額外購買力
            if not exceeds_limit:
                additional_buying_power = self.fund_status.get("cash", 0) * leverage_buffer
            else:
                additional_buying_power = 0.0

            return {
                "current_leverage": current_leverage,
                "max_leverage": max_leverage,
                "exceeds_limit": exceeds_limit,
                "leverage_buffer": leverage_buffer,
                "additional_buying_power": additional_buying_power,
                "leverage_utilization": current_leverage / max_leverage,
            }

        except Exception as e:
            logger.exception(f"檢查槓桿限制失敗: {e}")
            return {
                "current_leverage": 0.0,
                "max_leverage": max_leverage,
                "exceeds_limit": False,
                "leverage_buffer": max_leverage,
                "additional_buying_power": 0.0,
                "leverage_utilization": 0.0,
                "error": str(e),
            }

    def validate_trade_feasibility(
        self,
        symbol: str,
        quantity: float,
        price: float,
        trade_type: str = "buy"
    ) -> Dict[str, Any]:
        """
        驗證交易可行性

        Args:
            symbol (str): 股票代號
            quantity (float): 交易數量
            price (float): 交易價格
            trade_type (str): 交易類型 ("buy" 或 "sell")

        Returns:
            Dict[str, Any]: 交易可行性檢查結果
        """
        try:
            trade_value = abs(quantity) * price

            # 檢查現金充足性
            cash = self.fund_status.get("cash", 0)
            buying_power = self.fund_status.get("buying_power", 0)

            if trade_type.lower() == "buy":
                cash_sufficient = cash >= trade_value
                buying_power_sufficient = buying_power >= trade_value

                # 估算所需保證金（假設50%保證金要求）
                estimated_margin = trade_value * 0.5
                margin_check = self.check_margin_requirements(estimated_margin)

                # 檢查槓桿限制
                leverage_check = self.check_leverage_limits()

                return {
                    "feasible": cash_sufficient and margin_check["sufficient"],
                    "trade_value": trade_value,
                    "cash_sufficient": cash_sufficient,
                    "buying_power_sufficient": buying_power_sufficient,
                    "margin_check": margin_check,
                    "leverage_check": leverage_check,
                    "estimated_margin": estimated_margin,
                    "cash_after_trade": cash - trade_value,
                    "warnings": self._generate_trade_warnings(
                        cash_sufficient, margin_check, leverage_check
                    ),
                }
            else:  # sell
                # 賣出交易通常不需要額外資金
                return {
                    "feasible": True,
                    "trade_value": trade_value,
                    "cash_after_trade": cash + trade_value,
                    "warnings": [],
                }

        except Exception as e:
            logger.exception(f"驗證交易可行性失敗: {e}")
            return {
                "feasible": False,
                "error": str(e),
                "warnings": [f"交易可行性檢查失敗: {str(e)}"],
            }

    def _generate_trade_warnings(
        self,
        cash_sufficient: bool,
        margin_check: Dict[str, Any],
        leverage_check: Dict[str, Any]
    ) -> List[str]:
        """生成交易警告"""
        warnings = []

        if not cash_sufficient:
            warnings.append("現金不足以完成交易")

        if not margin_check.get("sufficient", False):
            shortage = margin_check.get("shortage", 0)
            warnings.append(f"保證金不足，缺少: {shortage:,.0f}")

        if margin_check.get("exceeds_warning", False):
            warnings.append("交易後保證金使用率將達到警告水平")

        if margin_check.get("exceeds_critical", False):
            warnings.append("交易後保證金使用率將達到危險水平")

        if leverage_check.get("exceeds_limit", False):
            warnings.append("交易後槓桿比例將超過限制")

        return warnings
