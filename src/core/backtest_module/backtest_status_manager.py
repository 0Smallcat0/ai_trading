"""回測狀態管理模組

此模組負責管理回測的狀態和線程控制，包括：
- 回測狀態追蹤
- 線程管理
- 進度更新
- 狀態查詢
"""

import sqlite3
import threading
import uuid
from datetime import datetime
from typing import Dict
import logging

# 設定日誌
logger = logging.getLogger(__name__)


class BacktestStatusManager:
    """回測狀態管理器"""

    def __init__(self, db_path: str):
        """初始化狀態管理器

        Args:
            db_path: 資料庫路徑
        """
        self.db_path = db_path
        self.running_backtests = {}
        self.backtest_threads = {}

    def create_backtest_task(self, config) -> str:
        """創建回測任務

        Args:
            config: 回測配置

        Returns:
            str: 回測ID

        Raises:
            Exception: 當記錄任務失敗時
        """
        # 生成回測ID
        backtest_id = str(uuid.uuid4())

        # 記錄回測任務
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO backtest_runs
                    (id, strategy_id, strategy_name, symbols, start_date, end_date,
                     initial_capital, commission, slippage, tax, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        backtest_id,
                        config.strategy_id,
                        config.strategy_name,
                        str(config.symbols),  # 簡化處理
                        config.start_date.isoformat(),
                        config.end_date.isoformat(),
                        config.initial_capital,
                        config.commission,
                        config.slippage,
                        config.tax,
                        "created",
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error("記錄回測任務失敗: %s", e)
            raise

        # 初始化狀態
        self.running_backtests[backtest_id] = {
            "status": "created",
            "progress": 0,
            "message": "回測任務已創建",
        }

        logger.info("回測任務已創建: %s", backtest_id)
        return backtest_id

    def start_backtest_thread(self, backtest_id: str, target_func, args):
        """啟動回測線程

        Args:
            backtest_id: 回測ID
            target_func: 目標函數
            args: 函數參數
        """
        thread = threading.Thread(target=target_func, args=args, daemon=True)

        self.backtest_threads[backtest_id] = thread
        thread.start()

        logger.info("回測線程已啟動: %s", backtest_id)

    def update_backtest_status(
        self, backtest_id: str, status: str, progress: float, message: str
    ):
        """更新回測狀態

        Args:
            backtest_id: 回測ID
            status: 狀態
            progress: 進度 (0-100)
            message: 狀態訊息
        """
        # 更新內存狀態
        self.running_backtests[backtest_id] = {
            "status": status,
            "progress": progress,
            "message": message,
        }

        # 更新資料庫
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE backtest_runs
                    SET status = ?, progress = ?
                    WHERE id = ?
                """,
                    (status, progress, backtest_id),
                )
                conn.commit()
        except Exception as e:
            logger.error("更新回測狀態失敗: %s", e)

    def get_backtest_status(self, backtest_id: str) -> Dict:
        """獲取回測狀態

        Args:
            backtest_id: 回測ID

        Returns:
            Dict: 回測狀態資訊
        """
        # 檢查內存中的狀態
        if backtest_id in self.running_backtests:
            return self.running_backtests[backtest_id]

        # 從資料庫查詢
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT status, progress, error_message
                    FROM backtest_runs
                    WHERE id = ?
                """,
                    (backtest_id,),
                )

                row = cursor.fetchone()
                if row:
                    return {
                        "status": row[0],
                        "progress": row[1],
                        "message": row[2] or "",
                    }
                else:
                    return {
                        "status": "not_found",
                        "progress": 0,
                        "message": "回測不存在",
                    }

        except Exception as e:
            logger.error("查詢回測狀態失敗: %s", e)
            return {"status": "error", "progress": 0, "message": str(e)}

    def cancel_backtest(self, backtest_id: str) -> bool:
        """取消回測

        Args:
            backtest_id: 回測ID

        Returns:
            bool: 是否成功取消
        """
        try:
            # 檢查是否正在運行
            if backtest_id not in self.running_backtests:
                return False

            # 更新狀態為已取消
            self.update_backtest_status(backtest_id, "cancelled", 0, "回測已取消")

            # 清理線程記錄
            if backtest_id in self.backtest_threads:
                del self.backtest_threads[backtest_id]

            if backtest_id in self.running_backtests:
                del self.running_backtests[backtest_id]

            logger.info("回測已取消: %s", backtest_id)
            return True

        except Exception as e:
            logger.error("取消回測失敗: %s", e)
            return False

    def cleanup_thread(self, backtest_id: str):
        """清理線程記錄

        Args:
            backtest_id: 回測ID
        """
        if backtest_id in self.backtest_threads:
            del self.backtest_threads[backtest_id]

    def mark_completed(self, backtest_id: str):
        """標記回測完成

        Args:
            backtest_id: 回測ID
        """
        try:
            # 更新完成時間
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE backtest_runs
                    SET completed_at = ?, started_at = ?
                    WHERE id = ?
                """,
                    (
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        backtest_id,
                    ),
                )
                conn.commit()

            logger.info("回測完成標記: %s", backtest_id)

        except Exception as e:
            logger.error("標記回測完成失敗: %s", e)

    def mark_failed(self, backtest_id: str, error_msg: str):
        """標記回測失敗

        Args:
            backtest_id: 回測ID
            error_msg: 錯誤訊息
        """
        try:
            # 記錄錯誤
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE backtest_runs
                    SET error_message = ?
                    WHERE id = ?
                """,
                    (error_msg, backtest_id),
                )
                conn.commit()

            logger.error("回測失敗標記: %s - %s", backtest_id, error_msg)

        except Exception as e:
            logger.error("標記回測失敗失敗: %s", e)

    def get_running_backtests(self) -> Dict:
        """獲取正在運行的回測

        Returns:
            Dict: 正在運行的回測字典
        """
        return self.running_backtests.copy()

    def is_backtest_running(self, backtest_id: str) -> bool:
        """檢查回測是否正在運行

        Args:
            backtest_id: 回測ID

        Returns:
            bool: 是否正在運行
        """
        return backtest_id in self.running_backtests
