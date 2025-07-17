"""
風險管理器模組

此模組提供統一的風險管理介面，整合各種風險控制機制。

主要功能：
- 統一風險管理介面
- 風險參數管理
- 風險評估和控制
- 風險事件處理

Example:
    >>> risk_manager = RiskManager()
    >>> risk_assessment = risk_manager.assess_trade_risk(symbol="2330", quantity=1000)
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
import numpy as np

# 導入現有的風險控制模組
try:
    from .live.unified_risk_controller import UnifiedRiskController
    from .live.position_limiter import PositionLimiter
    from .live.stop_loss_monitor import StopLossMonitor
    from .live.fund_monitor import FundMonitor
    from .live.emergency_risk_control import EmergencyRiskControl
except ImportError:
    # 如果導入失敗，使用模擬實現
    UnifiedRiskController = None
    PositionLimiter = None
    StopLossMonitor = None
    FundMonitor = None
    EmergencyRiskControl = None

logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    """風險評估結果"""
    symbol: str
    risk_level: str  # "low", "medium", "high", "critical"
    risk_score: float  # 0-100
    max_position_size: float
    recommended_stop_loss: float
    recommended_take_profit: float
    warnings: List[str]
    restrictions: List[str]
    timestamp: datetime


@dataclass
class TradeRiskParams:
    """交易風險參數"""
    symbol: str
    quantity: int
    price: float
    direction: str  # "buy" or "sell"
    portfolio_value: float
    current_positions: Dict[str, Any]


class RiskManager:
    """風險管理器
    
    提供統一的風險管理介面，整合各種風險控制機制，
    包括部位限制、停損監控、資金管理等。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化風險管理器
        
        Args:
            config: 風險管理配置
        """
        self.config = config or self._get_default_config()
        self.controllers = {}
        
        # 初始化風險控制器
        self._initialize_controllers()
        
        # 風險參數
        self.risk_params = self._get_default_risk_params()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """獲取預設配置"""
        return {
            "max_portfolio_risk": 2.0,  # 最大投資組合風險 (%)
            "max_position_size": 10.0,  # 最大單一部位 (%)
            "max_daily_loss": 5.0,      # 最大日損失 (%)
            "max_drawdown": 15.0,       # 最大回撤 (%)
            "var_confidence": 95.0,     # VaR 信心水準 (%)
            "stop_loss_enabled": True,
            "take_profit_enabled": True,
            "real_time_monitoring": True
        }
    
    def _get_default_risk_params(self) -> Dict[str, Any]:
        """獲取預設風險參數"""
        return {
            "stop_loss_type": "百分比停損",
            "stop_loss_percent": 5.0,
            "take_profit_type": "百分比停利",
            "take_profit_percent": 15.0,
            "position_sizing_method": "固定比例",
            "max_positions": 10,
            "correlation_limit": 0.7,
            "var_method": "歷史模擬法",
            "var_holding_period": 1,
            "var_lookback_days": 252
        }
    
    def _initialize_controllers(self):
        """初始化風險控制器"""
        try:
            if UnifiedRiskController:
                self.controllers['unified'] = UnifiedRiskController()
            if PositionLimiter:
                self.controllers['position'] = PositionLimiter()
            if StopLossMonitor:
                self.controllers['stop_loss'] = StopLossMonitor()
            if FundMonitor:
                self.controllers['fund'] = FundMonitor()
            if EmergencyRiskControl:
                self.controllers['emergency'] = EmergencyRiskControl()
        except Exception as e:
            logger.warning(f"初始化風險控制器失敗: {e}")
    
    def assess_trade_risk(
        self,
        symbol: str,
        quantity: int,
        price: float,
        direction: str = "buy",
        portfolio_value: float = 1000000.0,
        current_positions: Optional[Dict[str, Any]] = None
    ) -> RiskAssessment:
        """評估交易風險
        
        Args:
            symbol: 股票代碼
            quantity: 交易數量
            price: 交易價格
            direction: 交易方向 ("buy" or "sell")
            portfolio_value: 投資組合總值
            current_positions: 當前持倉
            
        Returns:
            RiskAssessment: 風險評估結果
        """
        try:
            current_positions = current_positions or {}
            
            # 計算交易金額
            trade_value = quantity * price
            position_ratio = (trade_value / portfolio_value) * 100
            
            # 風險評估
            risk_score = 0.0
            risk_level = "low"
            warnings = []
            restrictions = []
            
            # 部位大小檢查
            if position_ratio > self.config["max_position_size"]:
                risk_score += 30
                warnings.append(f"部位過大: {position_ratio:.1f}% > {self.config['max_position_size']}%")
                
            # 投資組合風險檢查
            total_exposure = sum(pos.get('value', 0) for pos in current_positions.values())
            portfolio_risk = ((total_exposure + trade_value) / portfolio_value) * 100
            
            if portfolio_risk > self.config["max_portfolio_risk"] * 10:  # 假設10倍槓桿
                risk_score += 25
                warnings.append(f"投資組合風險過高: {portfolio_risk:.1f}%")
            
            # 集中度風險檢查
            if symbol in current_positions:
                existing_value = current_positions[symbol].get('value', 0)
                total_symbol_value = existing_value + trade_value
                concentration = (total_symbol_value / portfolio_value) * 100
                
                if concentration > self.config["max_position_size"] * 1.5:
                    risk_score += 20
                    warnings.append(f"單一股票集中度過高: {concentration:.1f}%")
            
            # 確定風險等級
            if risk_score >= 70:
                risk_level = "critical"
                restrictions.append("建議暫停交易")
            elif risk_score >= 50:
                risk_level = "high"
                restrictions.append("建議減少部位")
            elif risk_score >= 30:
                risk_level = "medium"
                warnings.append("建議謹慎操作")
            else:
                risk_level = "low"
            
            # 計算建議停損停利
            stop_loss_percent = self.risk_params["stop_loss_percent"]
            take_profit_percent = self.risk_params["take_profit_percent"]
            
            if direction == "buy":
                recommended_stop_loss = price * (1 - stop_loss_percent / 100)
                recommended_take_profit = price * (1 + take_profit_percent / 100)
            else:
                recommended_stop_loss = price * (1 + stop_loss_percent / 100)
                recommended_take_profit = price * (1 - take_profit_percent / 100)
            
            # 計算最大建議部位
            max_position_size = min(
                self.config["max_position_size"] / 100 * portfolio_value / price,
                quantity * 2  # 不超過請求數量的2倍
            )
            
            return RiskAssessment(
                symbol=symbol,
                risk_level=risk_level,
                risk_score=risk_score,
                max_position_size=max_position_size,
                recommended_stop_loss=recommended_stop_loss,
                recommended_take_profit=recommended_take_profit,
                warnings=warnings,
                restrictions=restrictions,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"風險評估失敗: {e}")
            return RiskAssessment(
                symbol=symbol,
                risk_level="critical",
                risk_score=100.0,
                max_position_size=0.0,
                recommended_stop_loss=price * 0.95,
                recommended_take_profit=price * 1.05,
                warnings=[f"風險評估錯誤: {str(e)}"],
                restrictions=["暫停交易"],
                timestamp=datetime.now()
            )
    
    def check_portfolio_risk(
        self,
        portfolio_value: float,
        positions: Dict[str, Any],
        market_data: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """檢查投資組合風險
        
        Args:
            portfolio_value: 投資組合總值
            positions: 持倉資訊
            market_data: 市場數據
            
        Returns:
            Dict[str, Any]: 投資組合風險報告
        """
        try:
            market_data = market_data or {}
            
            # 計算總曝險
            total_exposure = sum(pos.get('value', 0) for pos in positions.values())
            exposure_ratio = (total_exposure / portfolio_value) * 100
            
            # 計算集中度
            concentrations = {}
            for symbol, position in positions.items():
                value = position.get('value', 0)
                concentrations[symbol] = (value / portfolio_value) * 100
            
            # 風險指標
            max_concentration = max(concentrations.values()) if concentrations else 0
            num_positions = len(positions)
            
            # 風險評估
            risk_alerts = []
            if exposure_ratio > self.config["max_portfolio_risk"] * 10:
                risk_alerts.append(f"總曝險過高: {exposure_ratio:.1f}%")
            
            if max_concentration > self.config["max_position_size"]:
                risk_alerts.append(f"單一部位過大: {max_concentration:.1f}%")
            
            if num_positions > self.risk_params["max_positions"]:
                risk_alerts.append(f"持倉數量過多: {num_positions}")
            
            return {
                "portfolio_value": portfolio_value,
                "total_exposure": total_exposure,
                "exposure_ratio": exposure_ratio,
                "max_concentration": max_concentration,
                "num_positions": num_positions,
                "concentrations": concentrations,
                "risk_alerts": risk_alerts,
                "risk_level": "high" if risk_alerts else "normal",
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"投資組合風險檢查失敗: {e}")
            return {
                "error": str(e),
                "risk_level": "unknown",
                "timestamp": datetime.now()
            }
    
    def calculate_var(
        self,
        portfolio_returns: pd.Series,
        confidence_level: float = 0.95,
        holding_period: int = 1
    ) -> Dict[str, float]:
        """計算風險價值 (VaR)
        
        Args:
            portfolio_returns: 投資組合報酬率序列
            confidence_level: 信心水準
            holding_period: 持有期間
            
        Returns:
            Dict[str, float]: VaR 計算結果
        """
        try:
            if len(portfolio_returns) < 30:
                logger.warning("數據不足，無法計算可靠的 VaR")
                return {"var": 0.0, "cvar": 0.0, "method": "insufficient_data"}
            
            # 歷史模擬法
            sorted_returns = portfolio_returns.sort_values()
            var_index = int((1 - confidence_level) * len(sorted_returns))
            var = sorted_returns.iloc[var_index] * np.sqrt(holding_period)
            
            # 條件風險價值 (CVaR)
            cvar = sorted_returns.iloc[:var_index].mean() * np.sqrt(holding_period)
            
            return {
                "var": abs(var) * 100,  # 轉換為百分比
                "cvar": abs(cvar) * 100,
                "confidence_level": confidence_level,
                "holding_period": holding_period,
                "method": "historical_simulation",
                "sample_size": len(portfolio_returns)
            }
            
        except Exception as e:
            logger.error(f"VaR 計算失敗: {e}")
            return {"var": 0.0, "cvar": 0.0, "error": str(e)}
    
    def update_risk_parameters(self, params: Dict[str, Any]) -> bool:
        """更新風險參數
        
        Args:
            params: 新的風險參數
            
        Returns:
            bool: 更新是否成功
        """
        try:
            self.risk_params.update(params)
            logger.info("風險參數已更新")
            return True
        except Exception as e:
            logger.error(f"更新風險參數失敗: {e}")
            return False
    
    def get_risk_parameters(self) -> Dict[str, Any]:
        """獲取當前風險參數
        
        Returns:
            Dict[str, Any]: 當前風險參數
        """
        return self.risk_params.copy()
    
    def emergency_stop(self, reason: str = "手動觸發") -> bool:
        """緊急停止所有交易
        
        Args:
            reason: 停止原因
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if 'emergency' in self.controllers:
                return self.controllers['emergency'].emergency_stop(reason)
            else:
                logger.warning("緊急風險控制器不可用")
                return False
        except Exception as e:
            logger.error(f"緊急停止失敗: {e}")
            return False


# 創建全局實例
risk_manager = RiskManager()


__all__ = [
    'RiskManager',
    'RiskAssessment',
    'TradeRiskParams',
    'risk_manager'
]
