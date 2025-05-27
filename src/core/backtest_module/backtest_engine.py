"""回測執行引擎模組

此模組提供回測執行的核心邏輯，整合策略管理、數據饋送和績效計算。
"""

import threading
import uuid
from pathlib import Path
from typing import Dict, Any, Callable
import logging
import pandas as pd

from .backtest_config import BacktestConfig
from .backtest_database import BacktestDatabaseManager
from .backtest_metrics import calculate_performance_metrics
from .backtest_strategy_manager import BacktestStrategyManager
from .backtest_data_feed import BacktestDataFeed
from .mock_backtest_engine import MockBacktest

logger = logging.getLogger(__name__)


class BacktestExecutionEngine:
    """回測執行引擎

    負責管理回測任務的執行，包含線程管理、進度追蹤和結果保存。
    """

    def __init__(self, db_manager: BacktestDatabaseManager, results_dir: str = None):
        """初始化回測執行引擎

        Args:
            db_manager: 資料庫管理器
            results_dir: 結果保存目錄
        """
        self.db_manager = db_manager
        self.results_dir = Path(results_dir or "data/backtest_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # 初始化模組化組件
        self.strategy_manager = BacktestStrategyManager()
        self.data_feed = BacktestDataFeed()

        # 執行狀態管理
        self.running_backtests = {}
        self.backtest_threads = {}
        self._lock = threading.Lock()

    def start_backtest(self, config: BacktestConfig, progress_callback: Callable = None) -> str:
        """啟動回測任務

        Args:
            config: 回測配置
            progress_callback: 進度回調函數

        Returns:
            str: 回測ID
        """
        # 生成回測ID
        backtest_id = str(uuid.uuid4())

        # 創建資料庫記錄
        if not self.db_manager.create_backtest_run(backtest_id, config):
            raise RuntimeError("創建回測記錄失敗")

        # 啟動回測線程
        thread = threading.Thread(
            target=self._run_backtest_thread,
            args=(backtest_id, config, progress_callback),
            daemon=True
        )

        with self._lock:
            self.backtest_threads[backtest_id] = thread
            self.running_backtests[backtest_id] = {
                "status": "created",
                "progress": 0,
                "message": "回測任務已創建",
            }

        thread.start()
        logger.info("回測任務已啟動: %s", backtest_id)

        return backtest_id

    def get_backtest_status(self, backtest_id: str) -> Dict[str, Any]:
        """獲取回測狀態

        Args:
            backtest_id: 回測ID

        Returns:
            Dict[str, Any]: 狀態資訊
        """
        with self._lock:
            if backtest_id in self.running_backtests:
                return self.running_backtests[backtest_id].copy()

        # 從資料庫獲取狀態
        run_info = self.db_manager.get_backtest_run(backtest_id)
        if run_info:
            return {
                "status": run_info.get("status", "unknown"),
                "progress": run_info.get("progress", 0),
                "message": run_info.get("error_message", ""),
            }

        return {"status": "not_found", "progress": 0, "message": "回測不存在"}

    def cancel_backtest(self, backtest_id: str) -> bool:
        """取消回測任務

        Args:
            backtest_id: 回測ID

        Returns:
            bool: 是否成功
        """
        with self._lock:
            if backtest_id in self.running_backtests:
                self.running_backtests[backtest_id]["status"] = "cancelled"

        # 更新資料庫狀態
        return self.db_manager.update_backtest_status(backtest_id, "cancelled")

    def _run_backtest_thread(
        self,
        backtest_id: str,
        config: BacktestConfig,
        progress_callback: Callable = None
    ):
        """回測執行線程

        Args:
            backtest_id: 回測ID
            config: 回測配置
            progress_callback: 進度回調函數
        """
        try:
            # 更新狀態為運行中
            self._update_status(backtest_id, "running", 0, "正在準備回測資料...")

            # 載入市場資料
            self._update_status(backtest_id, "running", 10, "正在載入市場資料...")
            market_data = self.data_feed.load_market_data(
                config.symbols, config.start_date, config.end_date
            )

            # 檢查是否被取消
            if self._is_cancelled(backtest_id):
                return

            # 初始化策略
            self._update_status(backtest_id, "running", 20, "正在初始化策略...")
            strategy = self.strategy_manager.initialize_strategy(config.strategy_id, config)

            # 生成交易信號
            self._update_status(backtest_id, "running", 40, "正在生成交易信號...")
            signals = self.strategy_manager.generate_signals(strategy, market_data)

            # 檢查是否被取消
            if self._is_cancelled(backtest_id):
                return

            # 執行回測
            self._update_status(backtest_id, "running", 60, "正在執行回測...")
            backtest_engine = MockBacktest(
                price_df=market_data,
                initial_capital=config.initial_capital,
                commission=config.commission,
                slippage=config.slippage,
            )

            results = backtest_engine.run(signals)

            # 計算績效指標
            self._update_status(backtest_id, "running", 80, "正在計算績效指標...")
            equity_curve = results.get("equity_curve", pd.Series())
            trades = results.get("trades", [])
            metrics = calculate_performance_metrics(equity_curve, trades)

            # 保存結果
            self._update_status(backtest_id, "running", 90, "正在保存結果...")
            self._save_results(backtest_id, results, metrics)

            # 完成
            self._update_status(backtest_id, "completed", 100, "回測完成")
            logger.info("回測完成: %s", backtest_id)

            # 調用進度回調
            if progress_callback:
                progress_callback(backtest_id, "completed", 100, "回測完成")

        except Exception as e:
            error_msg = f"回測執行失敗: {str(e)}"
            logger.error("回測 %s 失敗: %s", backtest_id, e)

            # 更新錯誤狀態
            self._update_status(backtest_id, "failed", 0, error_msg)

            # 調用進度回調
            if progress_callback:
                progress_callback(backtest_id, "failed", 0, error_msg)

        finally:
            # 清理線程記錄
            with self._lock:
                self.backtest_threads.pop(backtest_id, None)
                # 保留狀態記錄一段時間，供查詢使用

    def _update_status(self, backtest_id: str, status: str, progress: float, message: str):
        """更新回測狀態"""
        # 更新內存狀態
        with self._lock:
            self.running_backtests[backtest_id] = {
                "status": status,
                "progress": progress,
                "message": message,
            }

        # 更新資料庫
        self.db_manager.update_backtest_status(backtest_id, status, progress, message if status == "failed" else None)

    def _is_cancelled(self, backtest_id: str) -> bool:
        """檢查是否被取消"""
        with self._lock:
            status = self.running_backtests.get(backtest_id, {}).get("status")
            return status == "cancelled"

    def _save_results(self, backtest_id: str, results: Dict[str, Any], metrics: Dict[str, Any]):
        """保存回測結果"""
        # 保存到資料庫
        self.db_manager.save_backtest_metrics(backtest_id, metrics)
        self.db_manager.save_backtest_trades(backtest_id, results.get("trades", []))

        # 保存到檔案
        results_file = self.results_dir / f"{backtest_id}.json"
        import json

        serializable_results = {
            "backtest_id": backtest_id,
            "metrics": metrics,
            "trades": results.get("trades", []),
            "equity_curve": results.get("equity_curve", []),
            "dates": [
                d.isoformat() if hasattr(d, "isoformat") else str(d)
                for d in results.get("dates", [])
            ],
        }

        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)

        # 更新結果路徑
        self.db_manager.update_results_path(backtest_id, str(results_file))
