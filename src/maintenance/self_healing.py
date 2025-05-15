"""
自我修復模組

此模組提供系統自我修復功能，用於自動檢測和修復系統問題。
"""

import logging
import threading
import time
import traceback
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

# 導入日誌模組
try:
    from src.logging import LogCategory, get_logger

    logger = get_logger("self_healing", category=LogCategory.SYSTEM)
except ImportError:
    # 如果無法導入自定義日誌模組，則使用標準日誌模組
    logger = logging.getLogger("self_healing")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)

# 導入健康檢查模組
try:
    from src.monitoring.health_check import HealthStatus, health_check_registry
except ImportError:
    # 如果無法導入健康檢查模組，則創建模擬類
    class HealthStatus(Enum):
    """
    HealthStatus
    
    """
        HEALTHY = "healthy"
        DEGRADED = "degraded"
        UNHEALTHY = "unhealthy"
        UNKNOWN = "unknown"

    health_check_registry = None
    logger.warning("無法導入健康檢查模組，自我修復功能將受限")


class HealingAction:
    """修復動作類"""

    def __init__(
        self,
        name: str,
        action_func: Callable[[], bool],
        description: str = "",
        max_attempts: int = 3,
        cooldown_period: float = 300.0,
        tags: Optional[List[str]] = None,
    ):
        """
        初始化修復動作

        Args:
            name: 修復動作名稱
            action_func: 修復函數，返回是否修復成功
            description: 修復動作描述
            max_attempts: 最大嘗試次數
            cooldown_period: 冷卻期（秒）
            tags: 標籤列表
        """
        self.name = name
        self.action_func = action_func
        self.description = description
        self.max_attempts = max_attempts
        self.cooldown_period = cooldown_period
        self.tags = tags or []

        self.last_attempt_time = 0
        self.last_success_time = 0
        self.attempts = 0
        self.successes = 0
        self.failures = 0
        self.consecutive_failures = 0
        self.is_cooling_down = False

        logger.info(
            f"初始化修復動作 '{name}': 最大嘗試次數={max_attempts}, 冷卻期={cooldown_period}秒"
        )

    def execute(self, force: bool = False) -> bool:
        """
        執行修復動作

        Args:
            force: 是否強制執行，忽略冷卻期和最大嘗試次數

        Returns:
            bool: 是否修復成功
        """
        current_time = time.time()

        # 檢查冷卻期
        if not force and self.is_cooling_down:
            if current_time - self.last_attempt_time < self.cooldown_period:
                logger.info(f"修復動作 '{self.name}' 正在冷卻中，跳過執行")
                return False
            else:
                self.is_cooling_down = False

        # 檢查最大嘗試次數
        if not force and self.consecutive_failures >= self.max_attempts:
            logger.warning(
                f"修復動作 '{self.name}' 已達最大嘗試次數 ({self.max_attempts})，進入冷卻期"
            )
            self.is_cooling_down = True
            return False

        # 執行修復動作
        self.last_attempt_time = current_time
        self.attempts += 1

        logger.info(f"執行修復動作 '{self.name}' (第 {self.attempts} 次嘗試)")

        try:
            success = self.action_func()

            if success:
                self.last_success_time = current_time
                self.successes += 1
                self.consecutive_failures = 0
                logger.info(f"修復動作 '{self.name}' 執行成功")
                return True
            else:
                self.failures += 1
                self.consecutive_failures += 1
                logger.warning(
                    f"修復動作 '{self.name}' 執行失敗 (連續失敗: {self.consecutive_failures})"
                )

                # 如果達到最大嘗試次數，則進入冷卻期
                if self.consecutive_failures >= self.max_attempts:
                    logger.warning(
                        f"修復動作 '{self.name}' 已達最大嘗試次數 ({self.max_attempts})，進入冷卻期"
                    )
                    self.is_cooling_down = True

                return False
        except Exception as e:
            self.failures += 1
            self.consecutive_failures += 1
            logger.error(
                f"修復動作 '{self.name}' 執行異常: {str(e)}\n{traceback.format_exc()}"
            )

            # 如果達到最大嘗試次數，則進入冷卻期
            if self.consecutive_failures >= self.max_attempts:
                logger.warning(
                    f"修復動作 '{self.name}' 已達最大嘗試次數 ({self.max_attempts})，進入冷卻期"
                )
                self.is_cooling_down = True

            return False

    def reset(self) -> None:
        """重置修復動作"""
        self.last_attempt_time = 0
        self.last_success_time = 0
        self.attempts = 0
        self.successes = 0
        self.failures = 0
        self.consecutive_failures = 0
        self.is_cooling_down = False

        logger.info(f"重置修復動作 '{self.name}'")

    def get_metrics(self) -> Dict[str, Any]:
        """
        獲取修復動作指標

        Returns:
            Dict[str, Any]: 修復動作指標
        """
        return {
            "name": self.name,
            "description": self.description,
            "last_attempt_time": self.last_attempt_time,
            "last_success_time": self.last_success_time,
            "attempts": self.attempts,
            "successes": self.successes,
            "failures": self.failures,
            "consecutive_failures": self.consecutive_failures,
            "is_cooling_down": self.is_cooling_down,
            "max_attempts": self.max_attempts,
            "cooldown_period": self.cooldown_period,
            "tags": self.tags,
        }


class HealingRule:
    """修復規則類"""

    def __init__(
        self,
        name: str,
        condition_func: Callable[[], bool],
        actions: List[Union[str, HealingAction]],
        description: str = "",
        enabled: bool = True,
        tags: Optional[List[str]] = None,
    ):
        """
        初始化修復規則

        Args:
            name: 修復規則名稱
            condition_func: 條件函數，返回是否滿足條件
            actions: 修復動作列表，可以是修復動作名稱或修復動作對象
            description: 修復規則描述
            enabled: 是否啟用
            tags: 標籤列表
        """
        self.name = name
        self.condition_func = condition_func
        self.actions = actions
        self.description = description
        self.enabled = enabled
        self.tags = tags or []

        self.last_check_time = 0
        self.last_triggered_time = 0
        self.check_count = 0
        self.trigger_count = 0

        logger.info(f"初始化修復規則 '{name}': 啟用={enabled}")

    def check(self) -> bool:
        """
        檢查是否滿足條件

        Returns:
            bool: 是否滿足條件
        """
        if not self.enabled:
            return False

        self.last_check_time = time.time()
        self.check_count += 1

        try:
            result = self.condition_func()

            if result:
                self.last_triggered_time = time.time()
                self.trigger_count += 1
                logger.info(f"修復規則 '{self.name}' 條件滿足，觸發修復動作")

            return result
        except Exception as e:
            logger.error(
                f"修復規則 '{self.name}' 條件檢查異常: {str(e)}\n{traceback.format_exc()}"
            )
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """
        獲取修復規則指標

        Returns:
            Dict[str, Any]: 修復規則指標
        """
        return {
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "last_check_time": self.last_check_time,
            "last_triggered_time": self.last_triggered_time,
            "check_count": self.check_count,
            "trigger_count": self.trigger_count,
            "actions": [
                action.name if isinstance(action, HealingAction) else action
                for action in self.actions
            ],
            "tags": self.tags,
        }


class SelfHealingManager:
    """自我修復管理器"""

    def __init__(self):
        """初始化自我修復管理器"""
        self.actions: Dict[str, HealingAction] = {}
        self.rules: Dict[str, HealingRule] = {}
        self.lock = threading.RLock()
        self.running = False
        self.healing_thread = None
        self.last_healing_time = 0
        self.healing_count = 0
        self.successful_healing_count = 0
        self.failed_healing_count = 0

    def register_action(self, action: HealingAction) -> None:
        """
        註冊修復動作

        Args:
            action: 修復動作
        """
        with self.lock:
            self.actions[action.name] = action
            logger.info(f"註冊修復動作 '{action.name}'")

    def register_rule(self, rule: HealingRule) -> None:
        """
        註冊修復規則

        Args:
            rule: 修復規則
        """
        with self.lock:
            self.rules[rule.name] = rule
            logger.info(f"註冊修復規則 '{rule.name}'")

    def get_action(self, name: str) -> Optional[HealingAction]:
        """
        獲取修復動作

        Args:
            name: 修復動作名稱

        Returns:
            Optional[HealingAction]: 修復動作，如果不存在則返回 None
        """
        return self.actions.get(name)

    def get_rule(self, name: str) -> Optional[HealingRule]:
        """
        獲取修復規則

        Args:
            name: 修復規則名稱

        Returns:
            Optional[HealingRule]: 修復規則，如果不存在則返回 None
        """
        return self.rules.get(name)

    def execute_action(self, name: str, force: bool = False) -> bool:
        """
        執行修復動作

        Args:
            name: 修復動作名稱
            force: 是否強制執行

        Returns:
            bool: 是否修復成功

        Raises:
            ValueError: 如果找不到指定的修復動作
        """
        action = self.get_action(name)
        if action is None:
            raise ValueError(f"找不到修復動作: {name}")

        return action.execute(force)

    def check_rule(self, name: str) -> bool:
        """
        檢查修復規則

        Args:
            name: 修復規則名稱

        Returns:
            bool: 是否滿足條件

        Raises:
            ValueError: 如果找不到指定的修復規則
        """
        rule = self.get_rule(name)
        if rule is None:
            raise ValueError(f"找不到修復規則: {name}")

        return rule.check()

    def heal(self, rule_name: Optional[str] = None) -> bool:
        """
        執行修復

        Args:
            rule_name: 修復規則名稱，如果為 None 則檢查所有規則

        Returns:
            bool: 是否有任何修復成功
        """
        with self.lock:
            self.last_healing_time = time.time()
            self.healing_count += 1

            if rule_name:
                # 檢查指定規則
                rule = self.get_rule(rule_name)
                if rule is None:
                    logger.warning(f"找不到修復規則: {rule_name}")
                    self.failed_healing_count += 1
                    return False

                rules_to_check = [rule]
            else:
                # 檢查所有規則
                rules_to_check = list(self.rules.values())

            any_success = False

            for rule in rules_to_check:
                if not rule.enabled:
                    continue

                if rule.check():
                    # 執行修復動作
                    for action in rule.actions:
                        if isinstance(action, str):
                            action_obj = self.get_action(action)
                            if action_obj is None:
                                logger.warning(f"找不到修復動作: {action}")
                                continue
                        else:
                            action_obj = action

                        success = action_obj.execute()
                        if success:
                            any_success = True

            if any_success:
                self.successful_healing_count += 1
            else:
                self.failed_healing_count += 1

            return any_success

    def start_background_healing(self, check_interval: float = 60.0) -> None:
        """
        啟動背景修復

        Args:
            check_interval: 檢查間隔（秒）
        """
        with self.lock:
            if self.running:
                logger.warning("背景修復已在運行")
                return

            self.running = True
            self.healing_thread = threading.Thread(
                target=self._background_healing_loop,
                args=(check_interval,),
                daemon=True,
            )
            self.healing_thread.start()
            logger.info(f"啟動背景修復，間隔={check_interval}秒")

    def stop_background_healing(self) -> None:
        """停止背景修復"""
        with self.lock:
            self.running = False
            logger.info("停止背景修復")

    def _background_healing_loop(self, check_interval: float) -> None:
        """
        背景修復循環

        Args:
            check_interval: 檢查間隔（秒）
        """
        while self.running:
            try:
                self.heal()
            except Exception as e:
                logger.error(f"背景修復異常: {str(e)}\n{traceback.format_exc()}")

            # 等待下一次檢查
            for _ in range(int(check_interval)):
                if not self.running:
                    break
                time.sleep(1)

    def get_metrics(self) -> Dict[str, Any]:
        """
        獲取自我修復指標

        Returns:
            Dict[str, Any]: 自我修復指標
        """
        with self.lock:
            return {
                "running": self.running,
                "last_healing_time": self.last_healing_time,
                "healing_count": self.healing_count,
                "successful_healing_count": self.successful_healing_count,
                "failed_healing_count": self.failed_healing_count,
                "actions": {
                    name: action.get_metrics() for name, action in self.actions.items()
                },
                "rules": {
                    name: rule.get_metrics() for name, rule in self.rules.items()
                },
            }


# 創建全局自我修復管理器
self_healing_manager = SelfHealingManager()


# 導出模組內容
__all__ = [
    "HealingAction",
    "HealingRule",
    "SelfHealingManager",
    "self_healing_manager",
]
