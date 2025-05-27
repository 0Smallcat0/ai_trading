"""警報管理模組

此模組提供警報規則管理和警報觸發功能。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class AlertManagerError(Exception):
    """警報管理異常類別"""


class AlertManager:
    """警報管理器類別"""

    def __init__(self):
        """初始化警報管理器"""
        self.alert_rules = {}
        self.alert_history = []
        self.active_alerts = {}

    def create_alert_rule(self, rule_data: Dict) -> str:
        """創建警報規則

        Args:
            rule_data: 規則數據字典，包含 name, condition, threshold, action

        Returns:
            str: 規則ID
        """
        try:
            rule_id = "rule_%d" % (len(self.alert_rules) + 1)

            rule = {
                "id": rule_id,
                "name": rule_data.get("name"),
                "condition": rule_data.get("condition"),
                "threshold": rule_data.get("threshold"),
                "action": rule_data.get("action", "log"),
                "enabled": rule_data.get("enabled", True),
                "created_at": datetime.now(),
                "trigger_count": 0,
                "last_triggered": None,
            }

            self.alert_rules[rule_id] = rule
            logger.info("警報規則創建成功: %s", rule_data.get("name"))
            return rule_id

        except Exception as e:
            logger.error("創建警報規則時發生錯誤: %s", e)
            raise AlertManagerError("創建警報規則失敗") from e

    def update_alert_rule(self, rule_id: str, updates: Dict) -> bool:
        """更新警報規則

        Args:
            rule_id: 規則ID
            updates: 更新數據字典

        Returns:
            bool: 是否成功更新
        """
        try:
            if rule_id not in self.alert_rules:
                logger.warning("警報規則不存在: %s", rule_id)
                return False

            rule = self.alert_rules[rule_id]
            for key, value in updates.items():
                if key in rule:
                    rule[key] = value

            rule["updated_at"] = datetime.now()
            logger.info("警報規則更新成功: %s", rule_id)
            return True

        except Exception as e:
            logger.error("更新警報規則時發生錯誤: %s", e)
            return False

    def delete_alert_rule(self, rule_id: str) -> bool:
        """刪除警報規則

        Args:
            rule_id: 規則ID

        Returns:
            bool: 是否成功刪除
        """
        try:
            if rule_id not in self.alert_rules:
                logger.warning("警報規則不存在: %s", rule_id)
                return False

            del self.alert_rules[rule_id]
            logger.info("警報規則刪除成功: %s", rule_id)
            return True

        except Exception as e:
            logger.error("刪除警報規則時發生錯誤: %s", e)
            return False

    def check_alerts(self, metrics: Dict[str, Any]) -> List[Dict]:
        """檢查警報條件

        Args:
            metrics: 指標數據字典

        Returns:
            List[Dict]: 觸發的警報列表
        """
        try:
            triggered_alerts = []

            for rule_id, rule in self.alert_rules.items():
                if not rule.get("enabled", True):
                    continue

                if self._evaluate_condition(rule, metrics):
                    alert = self._trigger_alert(rule_id, rule, metrics)
                    triggered_alerts.append(alert)

            logger.info("警報檢查完成，觸發 %d 個警報", len(triggered_alerts))
            return triggered_alerts

        except Exception as e:
            logger.error("檢查警報條件時發生錯誤: %s", e)
            return []

    def get_active_alerts(self) -> List[Dict]:
        """獲取活躍警報

        Returns:
            List[Dict]: 活躍警報列表
        """
        try:
            active_list = []
            current_time = datetime.now()

            for alert_id, alert in self.active_alerts.items():
                # 檢查警報是否仍然活躍（24小時內）
                if current_time - alert["triggered_at"] < timedelta(hours=24):
                    active_list.append(alert)
                else:
                    # 移除過期的警報
                    del self.active_alerts[alert_id]

            logger.info("獲取活躍警報成功，數量: %d", len(active_list))
            return active_list

        except Exception as e:
            logger.error("獲取活躍警報時發生錯誤: %s", e)
            return []

    def get_alert_history(self, hours: int = 24) -> List[Dict]:
        """獲取警報歷史

        Args:
            hours: 查詢小時數

        Returns:
            List[Dict]: 警報歷史列表
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            filtered_history = [
                alert
                for alert in self.alert_history
                if alert.get("triggered_at", datetime.min) >= cutoff_time
            ]

            logger.info("獲取警報歷史成功，記錄數: %d", len(filtered_history))
            return filtered_history

        except Exception as e:
            logger.error("獲取警報歷史時發生錯誤: %s", e)
            return []

    def resolve_alert(self, alert_id: str, resolution: str = "") -> bool:
        """解決警報

        Args:
            alert_id: 警報ID
            resolution: 解決方案描述

        Returns:
            bool: 是否成功解決
        """
        try:
            if alert_id not in self.active_alerts:
                logger.warning("活躍警報不存在: %s", alert_id)
                return False

            alert = self.active_alerts[alert_id]
            alert["resolved_at"] = datetime.now()
            alert["resolution"] = resolution
            alert["status"] = "resolved"

            # 移動到歷史記錄
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]

            logger.info("警報解決成功: %s", alert_id)
            return True

        except Exception as e:
            logger.error("解決警報時發生錯誤: %s", e)
            return False

    def _evaluate_condition(self, rule: Dict, metrics: Dict) -> bool:
        """評估警報條件（內部方法）"""
        try:
            condition = rule.get("condition", "")
            threshold = rule.get("threshold", 0)

            # 簡單的條件評估
            if "cpu_percent" in condition:
                cpu_percent = metrics.get("cpu", {}).get("percent", 0)
                if ">" in condition:
                    return cpu_percent > threshold
                elif "<" in condition:
                    return cpu_percent < threshold

            elif "memory_percent" in condition:
                memory_percent = metrics.get("memory", {}).get("percent", 0)
                if ">" in condition:
                    return memory_percent > threshold
                elif "<" in condition:
                    return memory_percent < threshold

            elif "disk_percent" in condition:
                disk_percent = metrics.get("disk", {}).get("percent", 0)
                if ">" in condition:
                    return disk_percent > threshold
                elif "<" in condition:
                    return disk_percent < threshold

            elif "health_score" in condition:
                health_score = metrics.get("score", 100)
                if ">" in condition:
                    return health_score > threshold
                elif "<" in condition:
                    return health_score < threshold

            return False

        except Exception as e:
            logger.error("評估警報條件時發生錯誤: %s", e)
            return False

    def _trigger_alert(self, rule_id: str, rule: Dict, metrics: Dict) -> Dict:
        """觸發警報（內部方法）"""
        try:
            alert_id = "alert_%s_%d" % (rule_id, int(datetime.now().timestamp()))

            alert = {
                "id": alert_id,
                "rule_id": rule_id,
                "rule_name": rule.get("name"),
                "condition": rule.get("condition"),
                "threshold": rule.get("threshold"),
                "triggered_at": datetime.now(),
                "status": "active",
                "metrics": metrics,
                "message": self._generate_alert_message(rule, metrics),
            }

            # 更新規則統計
            rule["trigger_count"] += 1
            rule["last_triggered"] = datetime.now()

            # 添加到活躍警報
            self.active_alerts[alert_id] = alert

            # 執行警報動作
            self._execute_alert_action(rule, alert)

            logger.warning("警報觸發: %s", alert["message"])
            return alert

        except Exception as e:
            logger.error("觸發警報時發生錯誤: %s", e)
            return {}

    def _generate_alert_message(self, rule: Dict, metrics: Dict) -> str:
        """生成警報訊息（內部方法）"""
        condition = rule.get("condition", "")
        threshold = rule.get("threshold", 0)

        if "cpu_percent" in condition:
            current_value = metrics.get("cpu", {}).get("percent", 0)
            return "CPU 使用率警報: 當前 %.1f%%, 閾值 %.1f%%" % (
                current_value,
                threshold,
            )
        elif "memory_percent" in condition:
            current_value = metrics.get("memory", {}).get("percent", 0)
            return "記憶體使用率警報: 當前 %.1f%%, 閾值 %.1f%%" % (
                current_value,
                threshold,
            )
        elif "disk_percent" in condition:
            current_value = metrics.get("disk", {}).get("percent", 0)
            return "磁碟使用率警報: 當前 %.1f%%, 閾值 %.1f%%" % (
                current_value,
                threshold,
            )
        elif "health_score" in condition:
            current_value = metrics.get("score", 100)
            return "系統健康評分警報: 當前 %.1f, 閾值 %.1f" % (current_value, threshold)
        else:
            return "系統警報: %s" % rule.get("name", "未知警報")

    def _execute_alert_action(self, rule: Dict, alert: Dict):
        """執行警報動作（內部方法）"""
        try:
            action = rule.get("action", "log")

            if action == "log":
                logger.warning("警報動作 - 記錄: %s", alert["message"])
            elif action == "email":
                logger.info("警報動作 - 發送郵件: %s", alert["message"])
                # 這裡可以實作實際的郵件發送邏輯
            elif action == "sms":
                logger.info("警報動作 - 發送簡訊: %s", alert["message"])
                # 這裡可以實作實際的簡訊發送邏輯
            else:
                logger.info("警報動作 - 自定義: %s", alert["message"])

        except Exception as e:
            logger.error("執行警報動作時發生錯誤: %s", e)
