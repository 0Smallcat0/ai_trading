"""風險控制 API

此模組實現風險控制相關的 API 端點，包括風險檢查、緊急停損、
資金監控等關鍵風險管理功能。

主要功能：
- 風險檢查 API
- 緊急停損 API
- 資金監控 API
- 風險參數設定 API
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, status

from src.api.models.responses import APIResponse
from src.api.utils.security import get_current_user
from .models import (
    RiskCheckRequest,
    RiskCheckResponse,
    EmergencyStopRequest,
    FundMonitorResponse,
    RiskLevel,
    OrderSide,
)

logger = logging.getLogger(__name__)

# 創建路由器
router = APIRouter()

# 風險參數配置
RISK_PARAMETERS = {
    "max_single_order_value": 1000000,  # 單筆訂單最大金額
    "max_daily_loss": 50000,  # 單日最大虧損
    "max_position_concentration": 0.3,  # 單一股票最大持倉比例
    "margin_call_threshold": 0.7,  # 保證金追繳閾值
    "max_leverage": 2.0,  # 最大槓桿倍數
    "stop_loss_threshold": 0.05,  # 停損閾值 (5%)
}

# 模擬用戶風險狀態
_user_risk_status: Dict[str, Dict[str, Any]] = {}


@router.post("/check", response_model=APIResponse[RiskCheckResponse])
async def risk_check(
    request: RiskCheckRequest,
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """風險檢查 API
    
    對交易請求進行全面的風險評估，包括資金充足性、
    持倉集中度、槓桿比例等多維度風險檢查。
    
    Args:
        request: 風險檢查請求
        session_id: 券商會話 ID
        current_user: 當前用戶
        
    Returns:
        APIResponse[RiskCheckResponse]: 風險檢查結果
        
    Raises:
        HTTPException: 檢查失敗時拋出
    """
    try:
        logger.info(
            "執行風險檢查 - 用戶: %s, 標的: %s, 方向: %s, 數量: %d",
            current_user.get("username"),
            request.symbol,
            request.side.value,
            request.quantity
        )
        
        # 獲取用戶帳戶資訊
        account_info = await _get_account_info(session_id, current_user)
        
        # 獲取當前持倉
        positions = await _get_positions(session_id, current_user)
        
        # 執行多維度風險檢查
        risk_checks = [
            _check_order_value_limit(request, account_info),
            _check_fund_sufficiency(request, account_info),
            _check_position_concentration(request, positions, account_info),
            _check_leverage_limit(request, account_info, positions),
            _check_daily_loss_limit(current_user["user_id"], account_info),
            _check_margin_requirement(request, account_info),
        ]
        
        # 彙總風險檢查結果
        warnings = []
        max_risk_level = RiskLevel.LOW
        approved = True
        max_allowed_quantity = request.quantity
        
        for check_result in risk_checks:
            if not check_result["passed"]:
                approved = False
            
            if check_result["warnings"]:
                warnings.extend(check_result["warnings"])
            
            # 更新風險等級
            if check_result["risk_level"] == RiskLevel.CRITICAL:
                max_risk_level = RiskLevel.CRITICAL
            elif check_result["risk_level"] == RiskLevel.HIGH and max_risk_level != RiskLevel.CRITICAL:
                max_risk_level = RiskLevel.HIGH
            elif check_result["risk_level"] == RiskLevel.MEDIUM and max_risk_level == RiskLevel.LOW:
                max_risk_level = RiskLevel.MEDIUM
            
            # 更新最大允許數量
            if check_result.get("max_quantity"):
                max_allowed_quantity = min(max_allowed_quantity, check_result["max_quantity"])
        
        # 計算所需保證金
        required_margin = _calculate_required_margin(request)
        
        # 生成檢查結果
        message = "風險檢查通過" if approved else "風險檢查未通過"
        if warnings:
            message += f"，發現 {len(warnings)} 項風險警告"
        
        response = RiskCheckResponse(
            approved=approved,
            risk_level=max_risk_level,
            warnings=warnings,
            max_allowed_quantity=max_allowed_quantity if max_allowed_quantity != request.quantity else None,
            required_margin=required_margin,
            message=message
        )
        
        logger.info(
            "風險檢查完成 - 用戶: %s, 結果: %s, 風險等級: %s",
            current_user.get("username"),
            "通過" if approved else "未通過",
            max_risk_level.value
        )
        
        return APIResponse(
            success=True,
            data=response,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("風險檢查過程中發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="風險檢查服務暫時不可用"
        )


@router.post("/emergency-stop", response_model=APIResponse[Dict[str, Any]])
async def emergency_stop(
    request: EmergencyStopRequest,
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """緊急停損 API
    
    執行緊急停損操作，立即平倉所有或指定的持倉部位。
    
    Args:
        request: 緊急停損請求
        session_id: 券商會話 ID
        current_user: 當前用戶
        
    Returns:
        APIResponse[Dict[str, Any]]: 緊急停損結果
        
    Raises:
        HTTPException: 停損失敗時拋出
    """
    try:
        logger.warning(
            "執行緊急停損 - 用戶: %s, 原因: %s",
            current_user.get("username"),
            request.reason
        )
        
        # 獲取需要停損的持倉
        positions = await _get_positions(session_id, current_user)
        
        if request.symbols:
            positions = [pos for pos in positions if pos["symbol"] in request.symbols]
        
        if not positions:
            return APIResponse(
                success=True,
                data={"closed_positions": 0, "message": "沒有需要停損的持倉"},
                message="緊急停損完成"
            )
        
        # 執行緊急平倉
        closed_positions = []
        failed_positions = []
        
        for position in positions:
            try:
                # 執行市價平倉
                close_result = await _execute_emergency_close(position, session_id)
                if close_result["success"]:
                    closed_positions.append({
                        "symbol": position["symbol"],
                        "quantity": position["quantity"],
                        "order_id": close_result["order_id"]
                    })
                else:
                    failed_positions.append({
                        "symbol": position["symbol"],
                        "error": close_result["error"]
                    })
            except Exception as e:
                logger.error("緊急平倉 %s 失敗: %s", position["symbol"], e)
                failed_positions.append({
                    "symbol": position["symbol"],
                    "error": str(e)
                })
        
        # 記錄緊急停損事件
        await _log_emergency_stop_event(current_user["user_id"], request.reason, closed_positions, failed_positions)
        
        result = {
            "closed_positions": len(closed_positions),
            "failed_positions": len(failed_positions),
            "closed_details": closed_positions,
            "failed_details": failed_positions,
            "reason": request.reason,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.warning(
            "緊急停損完成 - 用戶: %s, 成功: %d, 失敗: %d",
            current_user.get("username"),
            len(closed_positions),
            len(failed_positions)
        )
        
        return APIResponse(
            success=True,
            data=result,
            message=f"緊急停損完成，成功平倉 {len(closed_positions)} 筆"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("緊急停損過程中發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="緊急停損服務暫時不可用"
        )


@router.get("/fund-monitor", response_model=APIResponse[FundMonitorResponse])
async def fund_monitor(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """資金監控 API
    
    監控帳戶資金狀況，包括權益、保證金比率、損益等關鍵指標。
    
    Args:
        session_id: 券商會話 ID
        current_user: 當前用戶
        
    Returns:
        APIResponse[FundMonitorResponse]: 資金監控結果
        
    Raises:
        HTTPException: 監控失敗時拋出
    """
    try:
        # 獲取帳戶資訊
        account_info = await _get_account_info(session_id, current_user)
        
        # 計算風險指標
        margin_ratio = account_info["margin_used"] / account_info["total_equity"] if account_info["total_equity"] > 0 else 0
        daily_pnl = account_info["unrealized_pnl"] + account_info["realized_pnl"]
        daily_pnl_percent = daily_pnl / account_info["total_equity"] * 100 if account_info["total_equity"] > 0 else 0
        
        # 計算最大回撤（模擬）
        max_drawdown = await _calculate_max_drawdown(current_user["user_id"])
        
        # 評估風險等級
        risk_level = _assess_fund_risk_level(margin_ratio, daily_pnl_percent, max_drawdown)
        
        # 生成警報
        alerts = []
        if margin_ratio > RISK_PARAMETERS["margin_call_threshold"]:
            alerts.append(f"保證金比率過高: {margin_ratio:.2%}")
        
        if daily_pnl < -RISK_PARAMETERS["max_daily_loss"]:
            alerts.append(f"單日虧損超過限制: {daily_pnl:,.0f}")
        
        if max_drawdown > 0.15:  # 15% 回撤警告
            alerts.append(f"最大回撤過大: {max_drawdown:.2%}")
        
        response = FundMonitorResponse(
            total_equity=Decimal(str(account_info["total_equity"])),
            available_cash=Decimal(str(account_info["available_cash"])),
            margin_ratio=Decimal(str(margin_ratio)),
            risk_level=risk_level,
            daily_pnl=Decimal(str(daily_pnl)),
            daily_pnl_percent=Decimal(str(daily_pnl_percent)),
            max_drawdown=Decimal(str(max_drawdown)),
            alerts=alerts
        )
        
        return APIResponse(
            success=True,
            data=response,
            message="資金監控數據獲取成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("資金監控過程中發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="資金監控服務暫時不可用"
        )


def _check_order_value_limit(request: RiskCheckRequest, account_info: Dict[str, Any]) -> Dict[str, Any]:
    """檢查訂單金額限制"""
    order_value = request.quantity * (request.price or 100)
    max_value = RISK_PARAMETERS["max_single_order_value"]
    
    if order_value > max_value:
        return {
            "passed": False,
            "risk_level": RiskLevel.HIGH,
            "warnings": [f"訂單金額 {order_value:,.0f} 超過單筆限制 {max_value:,.0f}"],
            "max_quantity": int(max_value / (request.price or 100))
        }
    
    return {"passed": True, "risk_level": RiskLevel.LOW, "warnings": []}


def _check_fund_sufficiency(request: RiskCheckRequest, account_info: Dict[str, Any]) -> Dict[str, Any]:
    """檢查資金充足性"""
    required_amount = request.quantity * (request.price or 100)
    available_cash = account_info["available_cash"]
    
    if request.side == OrderSide.BUY and required_amount > available_cash:
        return {
            "passed": False,
            "risk_level": RiskLevel.CRITICAL,
            "warnings": [f"資金不足，需要 {required_amount:,.0f}，可用 {available_cash:,.0f}"],
            "max_quantity": int(available_cash / (request.price or 100))
        }
    
    return {"passed": True, "risk_level": RiskLevel.LOW, "warnings": []}


def _check_position_concentration(request: RiskCheckRequest, positions: List[Dict], account_info: Dict[str, Any]) -> Dict[str, Any]:
    """檢查持倉集中度"""
    total_equity = account_info["total_equity"]
    current_position_value = 0
    
    # 計算當前該股票的持倉價值
    for pos in positions:
        if pos["symbol"] == request.symbol:
            current_position_value = pos["quantity"] * pos["current_price"]
            break
    
    # 計算交易後的持倉價值
    if request.side == OrderSide.BUY:
        new_position_value = current_position_value + request.quantity * (request.price or 100)
    else:
        new_position_value = max(0, current_position_value - request.quantity * (request.price or 100))
    
    concentration = new_position_value / total_equity if total_equity > 0 else 0
    max_concentration = RISK_PARAMETERS["max_position_concentration"]
    
    if concentration > max_concentration:
        return {
            "passed": False,
            "risk_level": RiskLevel.HIGH,
            "warnings": [f"持倉集中度 {concentration:.2%} 超過限制 {max_concentration:.2%}"]
        }
    
    return {"passed": True, "risk_level": RiskLevel.LOW, "warnings": []}


def _check_leverage_limit(request: RiskCheckRequest, account_info: Dict[str, Any], positions: List[Dict]) -> Dict[str, Any]:
    """檢查槓桿限制"""
    total_equity = account_info["total_equity"]
    total_position_value = sum(pos["quantity"] * pos["current_price"] for pos in positions)
    
    if request.side == OrderSide.BUY:
        new_total_value = total_position_value + request.quantity * (request.price or 100)
    else:
        new_total_value = total_position_value
    
    leverage = new_total_value / total_equity if total_equity > 0 else 0
    max_leverage = RISK_PARAMETERS["max_leverage"]
    
    if leverage > max_leverage:
        return {
            "passed": False,
            "risk_level": RiskLevel.HIGH,
            "warnings": [f"槓桿倍數 {leverage:.2f} 超過限制 {max_leverage:.2f}"]
        }
    
    return {"passed": True, "risk_level": RiskLevel.LOW, "warnings": []}


def _check_daily_loss_limit(user_id: str, account_info: Dict[str, Any]) -> Dict[str, Any]:
    """檢查單日虧損限制"""
    daily_pnl = account_info["unrealized_pnl"] + account_info["realized_pnl"]
    max_loss = RISK_PARAMETERS["max_daily_loss"]
    
    if daily_pnl < -max_loss:
        return {
            "passed": False,
            "risk_level": RiskLevel.CRITICAL,
            "warnings": [f"單日虧損 {abs(daily_pnl):,.0f} 超過限制 {max_loss:,.0f}"]
        }
    
    return {"passed": True, "risk_level": RiskLevel.LOW, "warnings": []}


def _check_margin_requirement(request: RiskCheckRequest, account_info: Dict[str, Any]) -> Dict[str, Any]:
    """檢查保證金要求"""
    required_margin = _calculate_required_margin(request)
    available_margin = account_info["margin_available"]
    
    if required_margin > available_margin:
        return {
            "passed": False,
            "risk_level": RiskLevel.HIGH,
            "warnings": [f"保證金不足，需要 {required_margin:,.0f}，可用 {available_margin:,.0f}"]
        }
    
    return {"passed": True, "risk_level": RiskLevel.LOW, "warnings": []}


def _calculate_required_margin(request: RiskCheckRequest) -> Decimal:
    """計算所需保證金"""
    # 簡化的保證金計算
    order_value = request.quantity * (request.price or 100)
    margin_rate = 0.166  # 6 倍槓桿，保證金比率 16.6%
    return Decimal(str(order_value * margin_rate))


def _assess_fund_risk_level(margin_ratio: float, daily_pnl_percent: float, max_drawdown: float) -> RiskLevel:
    """評估資金風險等級"""
    if margin_ratio > 0.8 or daily_pnl_percent < -10 or max_drawdown > 0.2:
        return RiskLevel.CRITICAL
    elif margin_ratio > 0.6 or daily_pnl_percent < -5 or max_drawdown > 0.15:
        return RiskLevel.HIGH
    elif margin_ratio > 0.4 or daily_pnl_percent < -2 or max_drawdown > 0.1:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.LOW


async def _get_account_info(session_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
    """獲取帳戶資訊（模擬）"""
    return {
        "total_equity": 1000000.0,
        "available_cash": 500000.0,
        "margin_used": 200000.0,
        "margin_available": 300000.0,
        "unrealized_pnl": 15000.0,
        "realized_pnl": 25000.0
    }


async def _get_positions(session_id: str, user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """獲取持倉資訊（模擬）"""
    return [
        {"symbol": "2330.TW", "quantity": 1000, "current_price": 595.0},
        {"symbol": "0050.TW", "quantity": 500, "current_price": 141.8}
    ]


async def _execute_emergency_close(position: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """執行緊急平倉（模擬）"""
    return {
        "success": True,
        "order_id": f"EMERGENCY_{position['symbol']}_{datetime.now().timestamp()}"
    }


async def _log_emergency_stop_event(user_id: str, reason: str, closed: List, failed: List):
    """記錄緊急停損事件"""
    logger.critical(
        "緊急停損事件 - 用戶: %s, 原因: %s, 成功: %d, 失敗: %d",
        user_id, reason, len(closed), len(failed)
    )


async def _calculate_max_drawdown(user_id: str) -> float:
    """計算最大回撤（模擬）"""
    return 0.08  # 模擬 8% 的最大回撤
