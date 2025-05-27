"""指標收集模組

此模組提供系統指標的收集和統計功能。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

import pandas as pd

logger = logging.getLogger(__name__)


class MetricsCollectorError(Exception):
    """指標收集異常類別"""


class MetricsCollector:
    """指標收集器類別"""

    def __init__(self):
        """初始化指標收集器"""
        self.metrics_history = []
        self.collection_interval = 60  # 秒

    def collect_trading_metrics(self) -> Dict[str, Any]:
        """收集交易指標
        
        Returns:
            Dict[str, Any]: 交易指標字典
        """
        try:
            # 模擬交易指標收集
            metrics = {
                "timestamp": datetime.now(),
                "total_trades": self._get_total_trades(),
                "successful_trades": self._get_successful_trades(),
                "failed_trades": self._get_failed_trades(),
                "total_volume": self._get_total_volume(),
                "total_commission": self._get_total_commission(),
                "active_positions": self._get_active_positions(),
                "portfolio_value": self._get_portfolio_value(),
                "daily_pnl": self._get_daily_pnl(),
                "win_rate": self._calculate_win_rate(),
            }

            logger.info("交易指標收集完成")
            return metrics

        except Exception as e:
            logger.error("收集交易指標時發生錯誤: %s", e)
            return {}

    def collect_performance_metrics(self) -> Dict[str, Any]:
        """收集效能指標
        
        Returns:
            Dict[str, Any]: 效能指標字典
        """
        try:
            metrics = {
                "timestamp": datetime.now(),
                "api_response_time": self._get_api_response_time(),
                "database_query_time": self._get_database_query_time(),
                "strategy_execution_time": self._get_strategy_execution_time(),
                "data_processing_time": self._get_data_processing_time(),
                "memory_usage": self._get_memory_usage(),
                "cpu_usage": self._get_cpu_usage(),
                "active_connections": self._get_active_connections(),
                "error_rate": self._get_error_rate(),
            }

            logger.info("效能指標收集完成")
            return metrics

        except Exception as e:
            logger.error("收集效能指標時發生錯誤: %s", e)
            return {}

    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """獲取指標摘要
        
        Args:
            hours: 統計小時數
            
        Returns:
            Dict[str, Any]: 指標摘要字典
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [
                m for m in self.metrics_history
                if m.get("timestamp", datetime.min) >= cutoff_time
            ]

            if not recent_metrics:
                return {"message": "無可用指標數據"}

            # 計算統計摘要
            summary = {
                "period": "%d 小時" % hours,
                "total_records": len(recent_metrics),
                "trading_summary": self._calculate_trading_summary(recent_metrics),
                "performance_summary": self._calculate_performance_summary(recent_metrics),
                "trends": self._calculate_trends(recent_metrics),
            }

            logger.info("指標摘要計算完成，記錄數: %d", len(recent_metrics))
            return summary

        except Exception as e:
            logger.error("獲取指標摘要時發生錯誤: %s", e)
            return {}

    def store_metrics(self, metrics: Dict[str, Any]):
        """儲存指標數據
        
        Args:
            metrics: 指標數據字典
        """
        try:
            metrics["stored_at"] = datetime.now()
            self.metrics_history.append(metrics)

            # 保持歷史記錄在合理範圍內（最多保留 10000 條記錄）
            if len(self.metrics_history) > 10000:
                self.metrics_history = self.metrics_history[-10000:]

            logger.info("指標數據儲存成功")

        except Exception as e:
            logger.error("儲存指標數據時發生錯誤: %s", e)

    def export_metrics(self, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """匯出指標數據
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            
        Returns:
            pd.DataFrame: 指標數據 DataFrame
        """
        try:
            filtered_metrics = [
                m for m in self.metrics_history
                if start_time <= m.get("timestamp", datetime.min) <= end_time
            ]

            if not filtered_metrics:
                return pd.DataFrame()

            df = pd.DataFrame(filtered_metrics)
            logger.info("指標數據匯出完成，記錄數: %d", len(df))
            return df

        except Exception as e:
            logger.error("匯出指標數據時發生錯誤: %s", e)
            return pd.DataFrame()

    # 模擬數據獲取方法
    def _get_total_trades(self) -> int:
        """獲取總交易數（模擬）"""
        import random
        return random.randint(100, 1000)

    def _get_successful_trades(self) -> int:
        """獲取成功交易數（模擬）"""
        import random
        return random.randint(60, 800)

    def _get_failed_trades(self) -> int:
        """獲取失敗交易數（模擬）"""
        import random
        return random.randint(10, 200)

    def _get_total_volume(self) -> float:
        """獲取總交易量（模擬）"""
        import random
        return random.uniform(1000000, 10000000)

    def _get_total_commission(self) -> float:
        """獲取總手續費（模擬）"""
        import random
        return random.uniform(1000, 10000)

    def _get_active_positions(self) -> int:
        """獲取活躍部位數（模擬）"""
        import random
        return random.randint(5, 50)

    def _get_portfolio_value(self) -> float:
        """獲取投資組合價值（模擬）"""
        import random
        return random.uniform(500000, 2000000)

    def _get_daily_pnl(self) -> float:
        """獲取日損益（模擬）"""
        import random
        return random.uniform(-10000, 20000)

    def _calculate_win_rate(self) -> float:
        """計算勝率（模擬）"""
        import random
        return random.uniform(0.5, 0.8)

    def _get_api_response_time(self) -> float:
        """獲取 API 響應時間（模擬）"""
        import random
        return random.uniform(0.1, 2.0)

    def _get_database_query_time(self) -> float:
        """獲取資料庫查詢時間（模擬）"""
        import random
        return random.uniform(0.05, 1.0)

    def _get_strategy_execution_time(self) -> float:
        """獲取策略執行時間（模擬）"""
        import random
        return random.uniform(0.5, 5.0)

    def _get_data_processing_time(self) -> float:
        """獲取數據處理時間（模擬）"""
        import random
        return random.uniform(0.2, 3.0)

    def _get_memory_usage(self) -> float:
        """獲取記憶體使用率（模擬）"""
        import random
        return random.uniform(30, 80)

    def _get_cpu_usage(self) -> float:
        """獲取 CPU 使用率（模擬）"""
        import random
        return random.uniform(10, 70)

    def _get_active_connections(self) -> int:
        """獲取活躍連接數（模擬）"""
        import random
        return random.randint(10, 100)

    def _get_error_rate(self) -> float:
        """獲取錯誤率（模擬）"""
        import random
        return random.uniform(0.001, 0.05)

    def _calculate_trading_summary(self, metrics_list: List[Dict]) -> Dict:
        """計算交易摘要（內部方法）"""
        if not metrics_list:
            return {}

        total_trades = sum(m.get("total_trades", 0) for m in metrics_list)
        successful_trades = sum(m.get("successful_trades", 0) for m in metrics_list)
        total_volume = sum(m.get("total_volume", 0) for m in metrics_list)

        return {
            "total_trades": total_trades,
            "successful_trades": successful_trades,
            "success_rate": successful_trades / total_trades if total_trades > 0 else 0,
            "total_volume": total_volume,
            "avg_volume_per_trade": total_volume / total_trades if total_trades > 0 else 0,
        }

    def _calculate_performance_summary(self, metrics_list: List[Dict]) -> Dict:
        """計算效能摘要（內部方法）"""
        if not metrics_list:
            return {}

        api_times = [m.get("api_response_time", 0) for m in metrics_list if "api_response_time" in m]
        db_times = [m.get("database_query_time", 0) for m in metrics_list if "database_query_time" in m]

        return {
            "avg_api_response_time": sum(api_times) / len(api_times) if api_times else 0,
            "avg_database_query_time": sum(db_times) / len(db_times) if db_times else 0,
            "max_api_response_time": max(api_times) if api_times else 0,
            "max_database_query_time": max(db_times) if db_times else 0,
        }

    def _calculate_trends(self, metrics_list: List[Dict]) -> Dict:
        """計算趨勢（內部方法）"""
        if len(metrics_list) < 2:
            return {}

        # 簡單的趨勢計算
        first_half = metrics_list[:len(metrics_list)//2]
        second_half = metrics_list[len(metrics_list)//2:]

        first_avg_trades = sum(m.get("total_trades", 0) for m in first_half) / len(first_half)
        second_avg_trades = sum(m.get("total_trades", 0) for m in second_half) / len(second_half)

        trade_trend = "increasing" if second_avg_trades > first_avg_trades else "decreasing"

        return {
            "trade_volume_trend": trade_trend,
            "trend_strength": abs(second_avg_trades - first_avg_trades) / first_avg_trades if first_avg_trades > 0 else 0,
        }
