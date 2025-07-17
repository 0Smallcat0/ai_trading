"""實時通知 API

此模組實現實時通知相關的 API 端點，包括交易通知、風險警報、
系統狀態通知等功能。支援 WebSocket 實時推送和 HTTP 輪詢。

主要功能：
- WebSocket 實時通知
- 交易通知管理
- 風險警報系統
- 系統狀態通知
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status

from src.api.models.responses import APIResponse
from src.api.utils.security import get_current_user
from .models import (
    TradeNotification,
    RiskAlert,
    SystemStatusNotification,
    NotificationType,
    RiskLevel,
    OrderStatus,
    OrderSide,
)

logger = logging.getLogger(__name__)

# 創建路由器
router = APIRouter()

# WebSocket 連接管理
class ConnectionManager:
    """WebSocket 連接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str):
        """建立 WebSocket 連接"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        logger.info("WebSocket 連接建立: %s (用戶: %s)", connection_id, user_id)
    
    def disconnect(self, connection_id: str, user_id: str):
        """斷開 WebSocket 連接"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info("WebSocket 連接斷開: %s (用戶: %s)", connection_id, user_id)
    
    async def send_personal_message(self, message: str, connection_id: str):
        """發送個人訊息"""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(message)
            except Exception as e:
                logger.error("發送訊息失敗: %s", e)
                # 移除失效連接
                for user_id, connections in self.user_connections.items():
                    if connection_id in connections:
                        self.disconnect(connection_id, user_id)
                        break
    
    async def send_user_message(self, message: str, user_id: str):
        """發送用戶訊息到所有連接"""
        if user_id in self.user_connections:
            disconnected_connections = []
            for connection_id in self.user_connections[user_id]:
                try:
                    await self.active_connections[connection_id].send_text(message)
                except Exception as e:
                    logger.error("發送用戶訊息失敗: %s", e)
                    disconnected_connections.append(connection_id)
            
            # 清理失效連接
            for connection_id in disconnected_connections:
                self.disconnect(connection_id, user_id)
    
    async def broadcast(self, message: str):
        """廣播訊息"""
        disconnected_connections = []
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error("廣播訊息失敗: %s", e)
                disconnected_connections.append(connection_id)
        
        # 清理失效連接
        for connection_id in disconnected_connections:
            for user_id, connections in self.user_connections.items():
                if connection_id in connections:
                    self.disconnect(connection_id, user_id)
                    break

# 全域連接管理器
manager = ConnectionManager()

# 通知歷史存儲
_notification_history: Dict[str, List[Dict[str, Any]]] = {}


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket 端點
    
    建立實時通知的 WebSocket 連接。
    
    Args:
        websocket: WebSocket 連接
        user_id: 用戶 ID
    """
    connection_id = f"{user_id}_{datetime.now().timestamp()}"
    
    try:
        await manager.connect(websocket, connection_id, user_id)
        
        # 發送歡迎訊息
        welcome_message = {
            "type": "system",
            "message": "實時通知連接已建立",
            "timestamp": datetime.now().isoformat(),
            "connection_id": connection_id
        }
        await manager.send_personal_message(json.dumps(welcome_message), connection_id)
        
        # 發送歷史通知（最近 10 條）
        if user_id in _notification_history:
            recent_notifications = _notification_history[user_id][-10:]
            for notification in recent_notifications:
                await manager.send_personal_message(json.dumps(notification), connection_id)
        
        # 保持連接
        while True:
            try:
                # 接收客戶端訊息（心跳檢測）
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    pong_message = {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }
                    await manager.send_personal_message(json.dumps(pong_message), connection_id)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("WebSocket 處理訊息時發生錯誤: %s", e)
                break
    
    except Exception as e:
        logger.error("WebSocket 連接錯誤: %s", e)
    
    finally:
        manager.disconnect(connection_id, user_id)


@router.post("/send-trade-notification", response_model=APIResponse[Dict[str, Any]])
async def send_trade_notification(
    notification: TradeNotification,
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """發送交易通知 API
    
    發送交易相關的實時通知。
    
    Args:
        notification: 交易通知內容
        user_id: 目標用戶 ID
        current_user: 當前用戶
        
    Returns:
        APIResponse[Dict[str, Any]]: 發送結果
        
    Raises:
        HTTPException: 發送失敗時拋出
    """
    try:
        # 檢查權限（只能發送給自己或管理員可發送給任何人）
        if current_user["user_id"] != user_id and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="無權限發送通知給其他用戶"
            )
        
        # 構建通知訊息
        message = {
            "type": "trade_notification",
            "data": notification.dict(),
            "timestamp": datetime.now().isoformat()
        }
        
        # 發送實時通知
        await manager.send_user_message(json.dumps(message), user_id)
        
        # 儲存通知歷史
        if user_id not in _notification_history:
            _notification_history[user_id] = []
        _notification_history[user_id].append(message)
        
        # 限制歷史記錄數量
        if len(_notification_history[user_id]) > 100:
            _notification_history[user_id] = _notification_history[user_id][-100:]
        
        logger.info(
            "交易通知已發送 - 用戶: %s, 訂單: %s, 狀態: %s",
            user_id,
            notification.order_id,
            notification.status.value
        )
        
        return APIResponse(
            success=True,
            data={"message": "交易通知發送成功", "notification_id": notification.order_id},
            message="通知發送成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("發送交易通知時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="通知服務暫時不可用"
        )


@router.post("/send-risk-alert", response_model=APIResponse[Dict[str, Any]])
async def send_risk_alert(
    alert: RiskAlert,
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """發送風險警報 API
    
    發送風險相關的警報通知。
    
    Args:
        alert: 風險警報內容
        user_id: 目標用戶 ID
        current_user: 當前用戶
        
    Returns:
        APIResponse[Dict[str, Any]]: 發送結果
        
    Raises:
        HTTPException: 發送失敗時拋出
    """
    try:
        # 檢查權限
        if current_user["user_id"] != user_id and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="無權限發送警報給其他用戶"
            )
        
        # 構建警報訊息
        message = {
            "type": "risk_alert",
            "data": alert.dict(),
            "timestamp": datetime.now().isoformat(),
            "priority": "high" if alert.alert_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] else "normal"
        }
        
        # 發送實時警報
        await manager.send_user_message(json.dumps(message), user_id)
        
        # 儲存警報歷史
        if user_id not in _notification_history:
            _notification_history[user_id] = []
        _notification_history[user_id].append(message)
        
        # 如果是高風險警報，同時記錄到系統日誌
        if alert.alert_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            logger.warning(
                "高風險警報 - 用戶: %s, 等級: %s, 訊息: %s",
                user_id,
                alert.alert_level.value,
                alert.message
            )
        
        return APIResponse(
            success=True,
            data={"message": "風險警報發送成功", "alert_level": alert.alert_level.value},
            message="警報發送成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("發送風險警報時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="警報服務暫時不可用"
        )


@router.post("/send-system-notification", response_model=APIResponse[Dict[str, Any]])
async def send_system_notification(
    notification: SystemStatusNotification,
    broadcast: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """發送系統狀態通知 API
    
    發送系統狀態相關的通知。
    
    Args:
        notification: 系統狀態通知內容
        broadcast: 是否廣播給所有用戶
        current_user: 當前用戶
        
    Returns:
        APIResponse[Dict[str, Any]]: 發送結果
        
    Raises:
        HTTPException: 發送失敗時拋出
    """
    try:
        # 檢查廣播權限
        if broadcast and current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="無權限廣播系統通知"
            )
        
        # 構建通知訊息
        message = {
            "type": "system_notification",
            "data": notification.dict(),
            "timestamp": datetime.now().isoformat(),
            "broadcast": broadcast
        }
        
        if broadcast:
            # 廣播給所有用戶
            await manager.broadcast(json.dumps(message))
            
            # 記錄到所有用戶的歷史
            for user_id in _notification_history:
                _notification_history[user_id].append(message)
            
            logger.info(
                "系統通知已廣播 - 組件: %s, 狀態: %s",
                notification.component,
                notification.status
            )
        else:
            # 只發送給當前用戶
            user_id = current_user["user_id"]
            await manager.send_user_message(json.dumps(message), user_id)
            
            if user_id not in _notification_history:
                _notification_history[user_id] = []
            _notification_history[user_id].append(message)
        
        return APIResponse(
            success=True,
            data={"message": "系統通知發送成功", "broadcast": broadcast},
            message="通知發送成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("發送系統通知時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="系統通知服務暫時不可用"
        )


@router.get("/history", response_model=APIResponse[List[Dict[str, Any]]])
async def get_notification_history(
    limit: int = 50,
    notification_type: Optional[NotificationType] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """獲取通知歷史 API
    
    獲取用戶的通知歷史記錄。
    
    Args:
        limit: 返回數量限制
        notification_type: 通知類型過濾
        current_user: 當前用戶
        
    Returns:
        APIResponse[List[Dict[str, Any]]]: 通知歷史列表
        
    Raises:
        HTTPException: 獲取失敗時拋出
    """
    try:
        user_id = current_user["user_id"]
        
        # 獲取用戶通知歷史
        notifications = _notification_history.get(user_id, [])
        
        # 按類型過濾
        if notification_type:
            notifications = [
                n for n in notifications 
                if n.get("type") == notification_type.value or 
                   (n.get("data", {}).get("notification_type") == notification_type.value)
            ]
        
        # 限制數量並按時間倒序
        notifications = notifications[-limit:]
        notifications.reverse()
        
        return APIResponse(
            success=True,
            data=notifications,
            message=f"通知歷史獲取成功，共 {len(notifications)} 筆"
        )
        
    except Exception as e:
        logger.error("獲取通知歷史時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="通知歷史服務暫時不可用"
        )


@router.get("/connection-status", response_model=APIResponse[Dict[str, Any]])
async def get_connection_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """獲取連接狀態 API
    
    獲取當前用戶的 WebSocket 連接狀態。
    
    Args:
        current_user: 當前用戶
        
    Returns:
        APIResponse[Dict[str, Any]]: 連接狀態資訊
    """
    try:
        user_id = current_user["user_id"]
        
        # 檢查用戶連接狀態
        active_connections = len(manager.user_connections.get(user_id, set()))
        
        status_info = {
            "user_id": user_id,
            "active_connections": active_connections,
            "is_connected": active_connections > 0,
            "total_connections": len(manager.active_connections),
            "last_check": datetime.now().isoformat()
        }
        
        return APIResponse(
            success=True,
            data=status_info,
            message="連接狀態獲取成功"
        )
        
    except Exception as e:
        logger.error("獲取連接狀態時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="連接狀態服務暫時不可用"
        )


# 自動通知任務
async def auto_send_notifications():
    """自動發送通知的後台任務"""
    while True:
        try:
            # 每 30 秒檢查一次系統狀態
            await asyncio.sleep(30)
            
            # 模擬系統狀態檢查
            system_status = await _check_system_status()
            
            if system_status["alerts"]:
                # 發送系統警報
                for alert in system_status["alerts"]:
                    notification = SystemStatusNotification(
                        component=alert["component"],
                        status=alert["status"],
                        timestamp=datetime.now(),
                        message=alert["message"],
                        severity=alert["severity"]
                    )
                    
                    # 廣播系統通知
                    message = {
                        "type": "system_notification",
                        "data": notification.dict(),
                        "timestamp": datetime.now().isoformat(),
                        "auto_generated": True
                    }
                    
                    await manager.broadcast(json.dumps(message))
                    
        except Exception as e:
            logger.error("自動通知任務錯誤: %s", e)


async def _check_system_status() -> Dict[str, Any]:
    """檢查系統狀態（模擬）"""
    # 模擬系統狀態檢查
    # 在實際實現中，這裡會檢查各個系統組件的狀態
    return {
        "alerts": []  # 暫時沒有警報
    }


# 自動通知任務將在應用啟動時啟動
# asyncio.create_task(auto_send_notifications())
