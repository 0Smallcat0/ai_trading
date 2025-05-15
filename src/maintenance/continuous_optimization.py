# -*- coding: utf-8 -*-
"""
持續優化模組

此模組負責協調和執行系統的持續優化任務，包括：
- 模型重訓練
- 策略優化
- 性能瓶頸識別和優化
- API 兼容性維護

主要功能：
- 排程和執行優化任務
- 監控優化結果
- 記錄優化活動
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

import schedule

from src.core.logger import get_logger
from src.maintenance.api_compatibility import APICompatibilityChecker
from src.maintenance.model_retrainer import ModelRetrainer
from src.maintenance.performance_optimizer import PerformanceOptimizer
from src.maintenance.strategy_refiner import StrategyRefiner

# 設定日誌
logger = get_logger("continuous_optimization")


class ContinuousOptimization:
    """持續優化類"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        model_retrainer: Optional[ModelRetrainer] = None,
        strategy_refiner: Optional[StrategyRefiner] = None,
        performance_optimizer: Optional[PerformanceOptimizer] = None,
        api_compatibility_checker: Optional[APICompatibilityChecker] = None,
    ):
        """
        初始化持續優化類

        Args:
            config_path: 配置文件路徑
            model_retrainer: 模型重訓練器
            strategy_refiner: 策略優化器
            performance_optimizer: 性能優化器
            api_compatibility_checker: API 兼容性檢查器
        """
        # 載入配置
        self.config = self._load_config(config_path)

        # 初始化組件
        self.model_retrainer = model_retrainer or ModelRetrainer()
        self.strategy_refiner = strategy_refiner or StrategyRefiner()
        self.performance_optimizer = performance_optimizer or PerformanceOptimizer()
        self.api_compatibility_checker = (
            api_compatibility_checker or APICompatibilityChecker()
        )

        # 初始化排程器
        self.scheduler = schedule.Scheduler()
        self._setup_schedules()

        # 初始化狀態
        self.running = False
        self.last_run = {}

        logger.info("持續優化模組初始化完成")

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        載入配置

        Args:
            config_path: 配置文件路徑

        Returns:
            Dict[str, Any]: 配置
        """
        default_config = {
            "model_retraining": {
                "schedule": {
                    "ml_models": "monthly",  # 機器學習模型每月重訓練
                    "dl_models": "quarterly",  # 深度學習模型每季度重訓練
                },
                "thresholds": {
                    "accuracy_drop": 0.05,  # 準確率下降 5% 觸發重訓練
                    "sharpe_drop": 0.2,  # 夏普比率下降 0.2 觸發重訓練
                },
            },
            "strategy_refinement": {
                "schedule": {
                    "trend_following": "quarterly",  # 趨勢跟蹤策略每季度優化
                    "mean_reversion": "monthly",  # 均值回歸策略每月優化
                    "ml_based": "monthly",  # 機器學習策略每月優化
                },
                "thresholds": {
                    "sharpe_ratio": 0.8,  # 夏普比率低於 0.8 觸發優化
                    "max_drawdown": 0.2,  # 最大回撤超過 20% 觸發優化
                    "win_rate": 0.45,  # 勝率低於 45% 觸發優化
                },
            },
            "performance_optimization": {
                "schedule": "weekly",  # 每週執行性能優化
                "thresholds": {
                    "cpu_usage": 80,  # CPU 使用率超過 80% 觸發優化
                    "memory_usage": 80,  # 內存使用率超過 80% 觸發優化
                    "api_latency": 0.5,  # API 延遲超過 0.5 秒觸發優化
                    "db_query_time": 1.0,  # 數據庫查詢時間超過 1 秒觸發優化
                },
            },
            "api_compatibility": {
                "schedule": "weekly",  # 每週檢查 API 兼容性
                "apis": {
                    "n8n": "https://api.n8n.io/version",
                    "broker": "https://api.broker.com/version",
                },
            },
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 合併配置
                    for key, value in config.items():
                        if key in default_config:
                            if isinstance(value, dict) and isinstance(
                                default_config[key], dict
                            ):
                                default_config[key].update(value)
                            else:
                                default_config[key] = value
                        else:
                            default_config[key] = value
                logger.info(f"已載入配置文件: {config_path}")
            except Exception as e:
                logger.error(f"載入配置文件時發生錯誤: {e}")

        return default_config

    def _setup_schedules(self):
        """設置排程"""
        # 模型重訓練排程
        schedule.every().day.at("01:00").do(self.check_and_retrain_models)

        # 策略優化排程
        schedule.every().day.at("02:00").do(self.check_and_refine_strategies)

        # 性能優化排程
        schedule.every().monday.at("03:00").do(self.optimize_performance)

        # API 兼容性檢查排程
        schedule.every().monday.at("04:00").do(self.check_api_compatibility)

        logger.info("排程設置完成")

    def start(self):
        """啟動持續優化"""
        self.running = True
        logger.info("持續優化已啟動")

        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("收到中斷信號，停止持續優化")
            self.running = False
        except Exception as e:
            logger.error(f"持續優化執行時發生錯誤: {e}")
            self.running = False

    def stop(self):
        """停止持續優化"""
        self.running = False
        logger.info("持續優化已停止")

    def check_and_retrain_models(self):
        """檢查並重訓練模型"""
        logger.info("開始檢查模型性能")
        try:
            # 檢查模型性能
            models_to_retrain = self.model_retrainer.check_model_performance(
                accuracy_threshold=self.config["model_retraining"]["thresholds"][
                    "accuracy_drop"
                ],
                sharpe_threshold=self.config["model_retraining"]["thresholds"][
                    "sharpe_drop"
                ],
            )

            if models_to_retrain:
                logger.info(f"需要重訓練的模型: {models_to_retrain}")
                # 重訓練模型
                results = self.model_retrainer.retrain_models(models_to_retrain)
                # 記錄結果
                self.last_run["model_retraining"] = {
                    "timestamp": datetime.now().isoformat(),
                    "models": models_to_retrain,
                    "results": results,
                }
                logger.info(f"模型重訓練完成: {results}")
            else:
                logger.info("所有模型性能良好，無需重訓練")
        except Exception as e:
            logger.error(f"檢查並重訓練模型時發生錯誤: {e}")

    def check_and_refine_strategies(self):
        """檢查並優化策略"""
        logger.info("開始檢查策略性能")
        try:
            # 檢查策略性能
            strategies_to_refine = self.strategy_refiner.check_strategy_performance(
                sharpe_threshold=self.config["strategy_refinement"]["thresholds"][
                    "sharpe_ratio"
                ],
                drawdown_threshold=self.config["strategy_refinement"]["thresholds"][
                    "max_drawdown"
                ],
                win_rate_threshold=self.config["strategy_refinement"]["thresholds"][
                    "win_rate"
                ],
            )

            if strategies_to_refine:
                logger.info(f"需要優化的策略: {strategies_to_refine}")
                # 優化策略
                results = self.strategy_refiner.refine_strategies(strategies_to_refine)
                # 記錄結果
                self.last_run["strategy_refinement"] = {
                    "timestamp": datetime.now().isoformat(),
                    "strategies": strategies_to_refine,
                    "results": results,
                }
                logger.info(f"策略優化完成: {results}")
            else:
                logger.info("所有策略性能良好，無需優化")
        except Exception as e:
            logger.error(f"檢查並優化策略時發生錯誤: {e}")

    def optimize_performance(self):
        """優化系統性能"""
        logger.info("開始優化系統性能")
        try:
            # 檢查性能瓶頸
            bottlenecks = self.performance_optimizer.identify_bottlenecks(
                cpu_threshold=self.config["performance_optimization"]["thresholds"][
                    "cpu_usage"
                ],
                memory_threshold=self.config["performance_optimization"]["thresholds"][
                    "memory_usage"
                ],
                api_latency_threshold=self.config["performance_optimization"][
                    "thresholds"
                ]["api_latency"],
                db_query_time_threshold=self.config["performance_optimization"][
                    "thresholds"
                ]["db_query_time"],
            )

            if bottlenecks:
                logger.info(f"發現性能瓶頸: {bottlenecks}")
                # 優化性能
                results = self.performance_optimizer.optimize(bottlenecks)
                # 記錄結果
                self.last_run["performance_optimization"] = {
                    "timestamp": datetime.now().isoformat(),
                    "bottlenecks": bottlenecks,
                    "results": results,
                }
                logger.info(f"性能優化完成: {results}")
            else:
                logger.info("系統性能良好，無需優化")
        except Exception as e:
            logger.error(f"優化系統性能時發生錯誤: {e}")

    def check_api_compatibility(self):
        """檢查 API 兼容性"""
        logger.info("開始檢查 API 兼容性")
        try:
            # 檢查 API 兼容性
            compatibility_issues = self.api_compatibility_checker.check_compatibility(
                apis=self.config["api_compatibility"]["apis"]
            )

            if compatibility_issues:
                logger.info(f"發現 API 兼容性問題: {compatibility_issues}")
                # 解決兼容性問題
                results = self.api_compatibility_checker.resolve_compatibility_issues(
                    compatibility_issues
                )
                # 記錄結果
                self.last_run["api_compatibility"] = {
                    "timestamp": datetime.now().isoformat(),
                    "issues": compatibility_issues,
                    "results": results,
                }
                logger.info(f"API 兼容性問題解決完成: {results}")
            else:
                logger.info("所有 API 兼容性良好")
        except Exception as e:
            logger.error(f"檢查 API 兼容性時發生錯誤: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        獲取持續優化狀態

        Returns:
            Dict[str, Any]: 狀態信息
        """
        return {
            "running": self.running,
            "last_run": self.last_run,
            "next_runs": {
                "model_retraining": (
                    schedule.next_run().isoformat() if schedule.next_run() else None
                ),
                "strategy_refinement": (
                    schedule.next_run().isoformat() if schedule.next_run() else None
                ),
                "performance_optimization": (
                    schedule.next_run().isoformat() if schedule.next_run() else None
                ),
                "api_compatibility": (
                    schedule.next_run().isoformat() if schedule.next_run() else None
                ),
            },
        }


if __name__ == "__main__":
    # 創建持續優化實例
    optimizer = ContinuousOptimization()
    # 啟動持續優化
    optimizer.start()
