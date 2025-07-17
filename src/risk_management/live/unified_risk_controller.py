"""
統一風險控制器

此模組整合所有風險控制功能，包括：
- 即時資金監控
- 動態停損機制
- 緊急風控措施
- 統一風險管理介面
"""

import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from src.execution.broker_base import BrokerBase
from .fund_monitor import FundMonitor
from .dynamic_stop_loss import DynamicStopLoss
from .emergency_risk_control import EmergencyRiskControl, EmergencyLevel, EmergencyAction
from .stop_loss_strategies import StopLossStrategy

# 設定日誌
logger = logging.getLogger("risk.live.unified_risk_controller")


class UnifiedRiskController:
    """統一風險控制器"""
    
    def __init__(self, broker: BrokerBase):
        """
        初始化統一風險控制器
        
        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
        
        # 初始化各個風險控制模組
        self.fund_monitor = FundMonitor(broker)
        self.dynamic_stop_loss = DynamicStopLoss(broker)
        self.emergency_control = EmergencyRiskControl(broker)
        
        # 風險控制狀態
        self.risk_control_active = False
        self.risk_level = "normal"  # normal, warning, critical, emergency
        
        # 風險控制參數
        self.risk_params = {
            "max_leverage": 3.0,
            "max_position_weight": 0.2,  # 單一持倉最大權重20%
            "max_daily_loss": 0.05,  # 最大日損失5%
            "margin_warning_threshold": 0.7,
            "margin_critical_threshold": 0.85,
            "auto_emergency_enabled": True,
        }
        
        # 線程安全
        self._control_lock = threading.Lock()
        
        # 回調函數
        self.on_risk_level_changed: Optional[Callable] = None
        self.on_emergency_triggered: Optional[Callable] = None
        
        # 設置模組間的回調
        self._setup_module_callbacks()
    
    def start_risk_control(self):
        """啟動風險控制"""
        try:
            with self._control_lock:
                if self.risk_control_active:
                    logger.warning("風險控制已經在運行")
                    return
                
                # 啟動各個模組
                self.fund_monitor.start_monitoring()
                self.dynamic_stop_loss.start_monitoring()
                
                self.risk_control_active = True
                logger.info("統一風險控制已啟動")
                
        except Exception as e:
            logger.exception(f"啟動風險控制失敗: {e}")
    
    def stop_risk_control(self):
        """停止風險控制"""
        try:
            with self._control_lock:
                if not self.risk_control_active:
                    return
                
                # 停止各個模組
                self.fund_monitor.stop_monitoring()
                self.dynamic_stop_loss.stop_monitoring()
                
                self.risk_control_active = False
                logger.info("統一風險控制已停止")
                
        except Exception as e:
            logger.exception(f"停止風險控制失敗: {e}")
    
    def get_overall_risk_status(self) -> Dict[str, Any]:
        """
        獲取整體風險狀態
        
        Returns:
            Dict[str, Any]: 整體風險狀態
        """
        try:
            # 獲取各模組狀態
            fund_summary = self.fund_monitor.get_fund_summary()
            fund_analysis = self.fund_monitor.get_detailed_fund_analysis()
            stop_loss_stops = self.dynamic_stop_loss.get_position_stops()
            emergency_status = self.emergency_control.get_emergency_status()
            
            # 計算整體風險級別
            overall_risk_level = self._calculate_overall_risk_level(fund_analysis, emergency_status)
            
            return {
                "risk_control_active": self.risk_control_active,
                "overall_risk_level": overall_risk_level,
                "fund_status": fund_summary,
                "risk_metrics": fund_analysis.get("risk_metrics", {}),
                "active_stop_losses": len(stop_loss_stops),
                "emergency_status": emergency_status,
                "risk_warnings": self._generate_risk_warnings(fund_analysis),
                "last_update": datetime.now(),
            }
            
        except Exception as e:
            logger.exception(f"獲取整體風險狀態失敗: {e}")
            return {
                "risk_control_active": self.risk_control_active,
                "overall_risk_level": "unknown",
                "error": str(e),
                "last_update": datetime.now(),
            }
    
    def validate_new_trade(
        self, 
        symbol: str, 
        quantity: float, 
        price: float,
        trade_type: str = "buy"
    ) -> Dict[str, Any]:
        """
        驗證新交易的風險
        
        Args:
            symbol (str): 股票代號
            quantity (float): 交易數量
            price (float): 交易價格
            trade_type (str): 交易類型
            
        Returns:
            Dict[str, Any]: 交易風險驗證結果
        """
        try:
            # 檢查緊急狀態
            if self.emergency_control.trading_suspended:
                return {
                    "approved": False,
                    "reason": "交易已暫停",
                    "risk_level": "emergency",
                }
            
            # 資金可行性檢查
            feasibility = self.fund_monitor.validate_trade_feasibility(symbol, quantity, price, trade_type)
            
            if not feasibility.get("feasible", False):
                return {
                    "approved": False,
                    "reason": "資金不足或保證金不夠",
                    "details": feasibility,
                    "risk_level": "high",
                }
            
            # 槓桿檢查
            leverage_check = self.fund_monitor.check_leverage_limits(self.risk_params["max_leverage"])
            if leverage_check.get("exceeds_limit", False):
                return {
                    "approved": False,
                    "reason": "槓桿比例超過限制",
                    "details": leverage_check,
                    "risk_level": "high",
                }
            
            # 持倉集中度檢查
            concentration_check = self._check_position_concentration(symbol, quantity, price)
            if not concentration_check.get("approved", True):
                return {
                    "approved": False,
                    "reason": "持倉集中度過高",
                    "details": concentration_check,
                    "risk_level": "medium",
                }
            
            return {
                "approved": True,
                "risk_level": "low",
                "feasibility": feasibility,
                "leverage_check": leverage_check,
                "concentration_check": concentration_check,
            }
            
        except Exception as e:
            logger.exception(f"驗證交易風險失敗: {e}")
            return {
                "approved": False,
                "reason": f"風險驗證失敗: {str(e)}",
                "risk_level": "unknown",
            }
    
    def set_position_stop_loss(
        self, 
        symbol: str, 
        strategy: StopLossStrategy,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """設置持倉停損（代理到動態停損模組）"""
        return self.dynamic_stop_loss.set_position_stop_loss(symbol, strategy, None, custom_params)
    
    def trigger_emergency_action(
        self, 
        level: EmergencyLevel, 
        reason: str,
        custom_actions: Optional[List[EmergencyAction]] = None
    ) -> Dict[str, Any]:
        """觸發緊急行動（代理到緊急控制模組）"""
        return self.emergency_control.trigger_emergency(level, reason, custom_actions)
    
    def get_risk_dashboard_data(self) -> Dict[str, Any]:
        """
        獲取風險控制儀表板數據
        
        Returns:
            Dict[str, Any]: 儀表板數據
        """
        try:
            overall_status = self.get_overall_risk_status()
            
            # 獲取詳細統計
            fund_history = self.fund_monitor.get_fund_history(24)  # 24小時歷史
            stop_loss_performance = self.dynamic_stop_loss.monitor.get_stop_loss_performance()
            emergency_events = self.emergency_control.get_emergency_events(20)
            
            return {
                "overall_status": overall_status,
                "fund_history": fund_history[-50:],  # 最近50個記錄
                "stop_loss_performance": stop_loss_performance,
                "recent_emergency_events": emergency_events,
                "risk_parameters": self.risk_params,
                "module_status": {
                    "fund_monitor": self.fund_monitor._monitoring,
                    "dynamic_stop_loss": self.dynamic_stop_loss.monitor._monitoring,
                    "emergency_control": self.emergency_control.emergency_active,
                },
            }
            
        except Exception as e:
            logger.exception(f"獲取風險儀表板數據失敗: {e}")
            return {
                "overall_status": {"error": str(e)},
                "fund_history": [],
                "stop_loss_performance": {},
                "recent_emergency_events": [],
                "risk_parameters": self.risk_params,
            }
    
    def update_risk_parameters(self, **kwargs) -> bool:
        """
        更新風險控制參數
        
        Args:
            **kwargs: 風險參數
            
        Returns:
            bool: 是否更新成功
        """
        try:
            for key, value in kwargs.items():
                if key in self.risk_params:
                    self.risk_params[key] = value
                    logger.info(f"已更新風險參數 {key}: {value}")
            
            # 同步更新到子模組
            if "margin_warning_threshold" in kwargs or "margin_critical_threshold" in kwargs:
                self.fund_monitor.update_monitor_params(**kwargs)
            
            return True
            
        except Exception as e:
            logger.exception(f"更新風險參數失敗: {e}")
            return False

    def _setup_module_callbacks(self):
        """設置模組間的回調"""
        try:
            # 資金監控警報回調
            def on_fund_alert(alert):
                if alert["level"] in ["critical", "emergency"]:
                    self._handle_critical_fund_alert(alert)

            self.fund_monitor.on_alert = on_fund_alert

            # 緊急控制回調
            def on_emergency_triggered(event):
                self._update_risk_level("emergency")
                if self.on_emergency_triggered:
                    self.on_emergency_triggered(event)

            self.emergency_control.on_emergency_triggered = on_emergency_triggered

        except Exception as e:
            logger.exception(f"設置模組回調失敗: {e}")

    def _calculate_overall_risk_level(
        self,
        fund_analysis: Dict[str, Any],
        emergency_status: Dict[str, Any]
    ) -> str:
        """計算整體風險級別"""
        try:
            if emergency_status.get("emergency_active", False):
                return "emergency"

            risk_metrics = fund_analysis.get("risk_metrics", {})

            # 檢查關鍵風險指標
            leverage_ratio = risk_metrics.get("leverage_ratio", 1.0)
            margin_utilization = risk_metrics.get("margin_utilization", 0.0)
            max_position_weight = risk_metrics.get("max_position_weight", 0.0)

            # 風險級別判斷
            if (leverage_ratio > self.risk_params["max_leverage"] or
                margin_utilization > self.risk_params["margin_critical_threshold"] or
                max_position_weight > self.risk_params["max_position_weight"] * 1.5):
                return "critical"

            elif (leverage_ratio > self.risk_params["max_leverage"] * 0.8 or
                  margin_utilization > self.risk_params["margin_warning_threshold"] or
                  max_position_weight > self.risk_params["max_position_weight"]):
                return "warning"

            else:
                return "normal"

        except Exception as e:
            logger.exception(f"計算整體風險級別失敗: {e}")
            return "unknown"

    def _generate_risk_warnings(self, fund_analysis: Dict[str, Any]) -> List[str]:
        """生成風險警告"""
        warnings = []

        try:
            risk_metrics = fund_analysis.get("risk_metrics", {})

            # 槓桿警告
            leverage_ratio = risk_metrics.get("leverage_ratio", 1.0)
            if leverage_ratio > self.risk_params["max_leverage"]:
                warnings.append(f"槓桿比例過高: {leverage_ratio:.2f}x (限制: {self.risk_params['max_leverage']}x)")

            # 保證金警告
            margin_utilization = risk_metrics.get("margin_utilization", 0.0)
            if margin_utilization > self.risk_params["margin_critical_threshold"]:
                warnings.append(f"保證金使用率危險: {margin_utilization:.1%}")
            elif margin_utilization > self.risk_params["margin_warning_threshold"]:
                warnings.append(f"保證金使用率偏高: {margin_utilization:.1%}")

            # 持倉集中度警告
            max_position_weight = risk_metrics.get("max_position_weight", 0.0)
            if max_position_weight > self.risk_params["max_position_weight"]:
                warnings.append(f"持倉集中度過高: {max_position_weight:.1%}")

            # 未實現損益警告
            unrealized_pnl_ratio = risk_metrics.get("unrealized_pnl_ratio", 0.0)
            if unrealized_pnl_ratio < -self.risk_params["max_daily_loss"]:
                warnings.append(f"未實現損失過大: {unrealized_pnl_ratio:.1%}")

        except Exception as e:
            logger.exception(f"生成風險警告失敗: {e}")
            warnings.append(f"風險警告生成失敗: {str(e)}")

        return warnings

    def _check_position_concentration(
        self,
        symbol: str,
        quantity: float,
        price: float
    ) -> Dict[str, Any]:
        """檢查持倉集中度"""
        try:
            trade_value = abs(quantity) * price
            fund_status = self.fund_monitor.get_fund_status()
            total_value = fund_status.get("total_value", 0)

            if total_value <= 0:
                return {"approved": True, "reason": "無法計算持倉比例"}

            # 計算交易後的持倉權重
            new_position_weight = trade_value / total_value

            if new_position_weight > self.risk_params["max_position_weight"]:
                return {
                    "approved": False,
                    "new_position_weight": new_position_weight,
                    "max_allowed_weight": self.risk_params["max_position_weight"],
                    "reason": f"持倉權重將達到 {new_position_weight:.1%}，超過限制 {self.risk_params['max_position_weight']:.1%}",
                }

            return {
                "approved": True,
                "new_position_weight": new_position_weight,
                "max_allowed_weight": self.risk_params["max_position_weight"],
            }

        except Exception as e:
            logger.exception(f"檢查持倉集中度失敗: {e}")
            return {
                "approved": False,
                "reason": f"持倉集中度檢查失敗: {str(e)}",
            }

    def _handle_critical_fund_alert(self, alert: Dict[str, Any]):
        """處理關鍵資金警報"""
        try:
            alert_level = alert.get("level", "info")

            if alert_level == "emergency" and self.risk_params["auto_emergency_enabled"]:
                # 自動觸發緊急措施
                self.trigger_emergency_action(
                    EmergencyLevel.CRITICAL,
                    f"自動觸發: {alert.get('title', '資金警報')}",
                    [EmergencyAction.SUSPEND_TRADING, EmergencyAction.CANCEL_ALL_ORDERS]
                )

            elif alert_level == "critical":
                # 觸發中等緊急措施
                self.trigger_emergency_action(
                    EmergencyLevel.HIGH,
                    f"資金警報: {alert.get('title', '保證金不足')}",
                    [EmergencyAction.REDUCE_POSITION_SIZE]
                )

            # 更新風險級別
            self._update_risk_level(alert_level)

        except Exception as e:
            logger.exception(f"處理關鍵資金警報失敗: {e}")

    def _update_risk_level(self, new_level: str):
        """更新風險級別"""
        try:
            old_level = self.risk_level
            self.risk_level = new_level

            if old_level != new_level:
                logger.warning(f"風險級別變更: {old_level} -> {new_level}")

                if self.on_risk_level_changed:
                    self.on_risk_level_changed({
                        "old_level": old_level,
                        "new_level": new_level,
                        "timestamp": datetime.now(),
                    })

        except Exception as e:
            logger.exception(f"更新風險級別失敗: {e}")
