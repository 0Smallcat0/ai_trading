"""
訂單限制模組

此模組實現了訂單限制功能，用於控制交易訂單的數量、頻率和規模，
以符合風險管理和監管要求。
"""

import os
import json
import time
import logging
import threading
from enum import Enum
from typing import Dict, List, Set, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from collections import deque

from src.core.logger import logger

# Define Role enum here to avoid circular imports
class Role(str, Enum):
    """用戶角色枚舉"""
    ADMIN = "admin"  # 管理員
    MANAGER = "manager"  # 經理
    TRADER = "trader"  # 交易員
    ANALYST = "analyst"  # 分析師
    VIEWER = "viewer"  # 查看者


class LimitType(str, Enum):
    """限制類型枚舉"""
    DAILY_ORDER_COUNT = "daily_order_count"  # 每日訂單數量
    DAILY_TRADE_VOLUME = "daily_trade_volume"  # 每日交易量
    MAX_ORDER_SIZE = "max_order_size"  # 最大訂單規模
    MAX_POSITION_SIZE = "max_position_size"  # 最大持倉規模
    MAX_LEVERAGE = "max_leverage"  # 最大槓桿
    MAX_DRAWDOWN = "max_drawdown"  # 最大回撤
    RESTRICTED_SYMBOLS = "restricted_symbols"  # 限制交易的股票


class OrderLimits:
    """
    訂單限制類

    管理交易訂單的數量、頻率和規模限制。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(OrderLimits, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config_file: str = "config/order_limits.json"):
        """
        初始化訂單限制

        Args:
            config_file: 配置文件路徑
        """
        # 避免重複初始化
        if self._initialized:
            return

        self.config_file = config_file

        # 默認限制
        self.default_limits = {
            LimitType.DAILY_ORDER_COUNT: 100,  # 每日最多 100 筆訂單
            LimitType.DAILY_TRADE_VOLUME: 1000000,  # 每日最大交易量 100 萬
            LimitType.MAX_ORDER_SIZE: 100000,  # 單筆訂單最大 10 萬
            LimitType.MAX_POSITION_SIZE: 500000,  # 單一持倉最大 50 萬
            LimitType.MAX_LEVERAGE: 2.0,  # 最大槓桿 2 倍
            LimitType.MAX_DRAWDOWN: 0.1,  # 最大回撤 10%
            LimitType.RESTRICTED_SYMBOLS: [],  # 限制交易的股票
        }

        # 角色限制
        self.role_limits = {
            Role.ADMIN: {
                LimitType.DAILY_ORDER_COUNT: 1000,
                LimitType.DAILY_TRADE_VOLUME: 10000000,
                LimitType.MAX_ORDER_SIZE: 1000000,
                LimitType.MAX_POSITION_SIZE: 5000000,
                LimitType.MAX_LEVERAGE: 5.0,
                LimitType.MAX_DRAWDOWN: 0.2,
                LimitType.RESTRICTED_SYMBOLS: [],
            },
            Role.MANAGER: {
                LimitType.DAILY_ORDER_COUNT: 500,
                LimitType.DAILY_TRADE_VOLUME: 5000000,
                LimitType.MAX_ORDER_SIZE: 500000,
                LimitType.MAX_POSITION_SIZE: 2000000,
                LimitType.MAX_LEVERAGE: 3.0,
                LimitType.MAX_DRAWDOWN: 0.15,
                LimitType.RESTRICTED_SYMBOLS: [],
            },
            Role.TRADER: {
                LimitType.DAILY_ORDER_COUNT: 200,
                LimitType.DAILY_TRADE_VOLUME: 2000000,
                LimitType.MAX_ORDER_SIZE: 200000,
                LimitType.MAX_POSITION_SIZE: 1000000,
                LimitType.MAX_LEVERAGE: 2.0,
                LimitType.MAX_DRAWDOWN: 0.1,
                LimitType.RESTRICTED_SYMBOLS: [],
            },
            Role.ANALYST: {
                LimitType.DAILY_ORDER_COUNT: 50,
                LimitType.DAILY_TRADE_VOLUME: 500000,
                LimitType.MAX_ORDER_SIZE: 50000,
                LimitType.MAX_POSITION_SIZE: 200000,
                LimitType.MAX_LEVERAGE: 1.5,
                LimitType.MAX_DRAWDOWN: 0.05,
                LimitType.RESTRICTED_SYMBOLS: [],
            },
            Role.VIEWER: {
                LimitType.DAILY_ORDER_COUNT: 0,
                LimitType.DAILY_TRADE_VOLUME: 0,
                LimitType.MAX_ORDER_SIZE: 0,
                LimitType.MAX_POSITION_SIZE: 0,
                LimitType.MAX_LEVERAGE: 0,
                LimitType.MAX_DRAWDOWN: 0,
                LimitType.RESTRICTED_SYMBOLS: ["*"],  # 禁止所有交易
            },
        }

        # 用戶限制
        self.user_limits = {}

        # 用戶訂單計數
        self.user_order_counts = {}

        # 用戶交易量
        self.user_trade_volumes = {}

        # 加載配置
        self.load_config()

        self._initialized = True

    def load_config(self) -> bool:
        """
        加載配置

        Returns:
            bool: 是否成功
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # 加載默認限制
                if "default_limits" in config:
                    for limit_type, value in config["default_limits"].items():
                        self.default_limits[LimitType(limit_type)] = value

                # 加載角色限制
                if "role_limits" in config:
                    for role, limits in config["role_limits"].items():
                        self.role_limits[Role(role)] = {
                            LimitType(limit_type): value
                            for limit_type, value in limits.items()
                        }

                # 加載用戶限制
                if "user_limits" in config:
                    self.user_limits = {
                        username: {
                            LimitType(limit_type): value
                            for limit_type, value in limits.items()
                        }
                        for username, limits in config["user_limits"].items()
                    }

                logger.info(f"已加載訂單限制配置: {self.config_file}")
                return True
            else:
                logger.warning(f"訂單限制配置文件不存在: {self.config_file}")
                return False
        except Exception as e:
            logger.error(f"加載訂單限制配置時發生錯誤: {e}")
            return False

    def save_config(self) -> bool:
        """
        保存配置

        Returns:
            bool: 是否成功
        """
        try:
            # 創建目錄
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            # 準備數據
            config = {
                "default_limits": {
                    limit_type.value: value
                    for limit_type, value in self.default_limits.items()
                },
                "role_limits": {
                    role.value: {
                        limit_type.value: value
                        for limit_type, value in limits.items()
                    }
                    for role, limits in self.role_limits.items()
                },
                "user_limits": {
                    username: {
                        limit_type.value: value
                        for limit_type, value in limits.items()
                    }
                    for username, limits in self.user_limits.items()
                },
            }

            # 保存到文件
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"已保存訂單限制配置: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存訂單限制配置時發生錯誤: {e}")
            return False

    def get_user_limit(self, username: str, limit_type: LimitType, roles: List[Role] = None) -> Any:
        """
        獲取用戶限制

        Args:
            username: 用戶名
            limit_type: 限制類型
            roles: 用戶角色列表

        Returns:
            Any: 限制值
        """
        # 檢查用戶自定義限制
        if username in self.user_limits and limit_type in self.user_limits[username]:
            return self.user_limits[username][limit_type]

        # 檢查角色限制
        if roles:
            # 獲取最高權限角色的限制
            max_limit = None
            for role in roles:
                if role in self.role_limits and limit_type in self.role_limits[role]:
                    role_limit = self.role_limits[role][limit_type]
                    if max_limit is None or (
                        isinstance(role_limit, (int, float)) and
                        isinstance(max_limit, (int, float)) and
                        role_limit > max_limit
                    ):
                        max_limit = role_limit

            if max_limit is not None:
                return max_limit

        # 返回默認限制
        return self.default_limits.get(limit_type)

    def set_user_limit(self, username: str, limit_type: LimitType, value: Any) -> None:
        """
        設置用戶限制

        Args:
            username: 用戶名
            limit_type: 限制類型
            value: 限制值
        """
        if username not in self.user_limits:
            self.user_limits[username] = {}

        self.user_limits[username][limit_type] = value
        logger.info(f"已設置用戶 {username} 的 {limit_type} 限制: {value}")

        # 保存配置
        self.save_config()

    def reset_daily_counters(self) -> None:
        """重置每日計數器"""
        self.user_order_counts = {}
        self.user_trade_volumes = {}
        logger.info("已重置每日訂單計數器")

    def check_order(
        self,
        username: str,
        symbol: str,
        quantity: int,
        price: float,
        roles: List[Role] = None,
    ) -> Tuple[bool, str]:
        """
        檢查訂單是否符合限制

        Args:
            username: 用戶名
            symbol: 股票代碼
            quantity: 數量
            price: 價格
            roles: 用戶角色列表

        Returns:
            Tuple[bool, str]: (是否通過, 原因)
        """
        # 初始化用戶計數器
        if username not in self.user_order_counts:
            self.user_order_counts[username] = 0

        if username not in self.user_trade_volumes:
            self.user_trade_volumes[username] = 0

        # 計算訂單金額
        order_amount = quantity * price

        # 檢查限制交易的股票
        restricted_symbols = self.get_user_limit(username, LimitType.RESTRICTED_SYMBOLS, roles)
        if restricted_symbols:
            if "*" in restricted_symbols or symbol in restricted_symbols:
                return False, f"股票 {symbol} 被限制交易"

        # 檢查每日訂單數量
        daily_order_count = self.get_user_limit(username, LimitType.DAILY_ORDER_COUNT, roles)
        if self.user_order_counts[username] >= daily_order_count:
            return False, f"超過每日訂單數量限制 ({daily_order_count})"

        # 檢查每日交易量
        daily_trade_volume = self.get_user_limit(username, LimitType.DAILY_TRADE_VOLUME, roles)
        if self.user_trade_volumes[username] + order_amount > daily_trade_volume:
            return False, f"超過每日交易量限制 ({daily_trade_volume})"

        # 檢查最大訂單規模
        max_order_size = self.get_user_limit(username, LimitType.MAX_ORDER_SIZE, roles)
        if order_amount > max_order_size:
            return False, f"超過最大訂單規模限制 ({max_order_size})"

        # 更新計數器
        self.user_order_counts[username] += 1
        self.user_trade_volumes[username] += order_amount

        return True, "訂單符合限制"


# 創建全局訂單限制實例
order_limits = OrderLimits()
