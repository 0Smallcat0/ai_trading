"""
回測數據庫操作模組

此模組包含回測系統的數據庫操作功能。
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class BacktestDatabaseManager:
    """回測數據庫管理器"""

    def __init__(self, db_path: str = None):
        """
        初始化數據庫管理器

        Args:
            db_path: 數據庫路徑
        """
        self.db_path = db_path or "data/backtest.db"
        self._ensure_db_directory()
        self._init_database()

    def _ensure_db_directory(self):
        """確保數據庫目錄存在"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _init_database(self):
        """初始化數據庫表結構"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 創建回測記錄表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS backtest_runs (
                        id TEXT PRIMARY KEY,
                        strategy_id TEXT NOT NULL,
                        strategy_name TEXT NOT NULL,
                        symbols TEXT NOT NULL,
                        start_date TEXT NOT NULL,
                        end_date TEXT NOT NULL,
                        initial_capital REAL NOT NULL,
                        commission REAL NOT NULL,
                        slippage REAL NOT NULL,
                        tax REAL NOT NULL,
                        status TEXT NOT NULL,
                        progress REAL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        started_at TEXT,
                        completed_at TEXT,
                        error_message TEXT,
                        results_path TEXT
                    )
                """
                )

                # 創建績效指標表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS backtest_metrics (
                        backtest_id TEXT PRIMARY KEY,
                        initial_capital REAL,
                        final_capital REAL,
                        total_return REAL,
                        annual_return REAL,
                        sharpe_ratio REAL,
                        max_drawdown REAL,
                        win_rate REAL,
                        profit_ratio REAL,
                        total_trades INTEGER,
                        winning_trades INTEGER,
                        losing_trades INTEGER,
                        avg_trade_duration REAL,
                        max_consecutive_wins INTEGER,
                        max_consecutive_losses INTEGER,
                        calmar_ratio REAL,
                        sortino_ratio REAL,
                        var_95 REAL,
                        beta REAL,
                        alpha REAL,
                        information_ratio REAL,
                        FOREIGN KEY (backtest_id) REFERENCES backtest_runs (id)
                    )
                """
                )

                # 創建交易記錄表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS backtest_trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        backtest_id TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        entry_date TEXT NOT NULL,
                        exit_date TEXT,
                        entry_price REAL NOT NULL,
                        exit_price REAL,
                        quantity REAL NOT NULL,
                        position_size REAL NOT NULL,
                        trade_type TEXT NOT NULL,
                        profit REAL,
                        profit_pct REAL,
                        commission_paid REAL,
                        slippage_cost REAL,
                        tax_paid REAL,
                        hold_days INTEGER,
                        signal_strength REAL,
                        FOREIGN KEY (backtest_id) REFERENCES backtest_runs (id)
                    )
                """
                )

                # 創建權益曲線表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS backtest_equity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        backtest_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        equity_value REAL NOT NULL,
                        cash_value REAL NOT NULL,
                        position_value REAL NOT NULL,
                        daily_return REAL,
                        cumulative_return REAL,
                        drawdown REAL,
                        FOREIGN KEY (backtest_id) REFERENCES backtest_runs (id)
                    )
                """
                )

                conn.commit()
                logger.info("回測數據庫初始化完成")

        except Exception as e:
            logger.error("初始化回測數據庫失敗: %s", e)
            raise

    def save_backtest_run(self, backtest_data: Dict[str, Any]) -> bool:
        """
        保存回測運行記錄

        Args:
            backtest_data: 回測數據

        Returns:
            bool: 是否保存成功
        """
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
                        backtest_data["id"],
                        backtest_data["strategy_id"],
                        backtest_data["strategy_name"],
                        json.dumps(backtest_data["symbols"]),
                        backtest_data["start_date"],
                        backtest_data["end_date"],
                        backtest_data["initial_capital"],
                        backtest_data["commission"],
                        backtest_data["slippage"],
                        backtest_data["tax"],
                        backtest_data["status"],
                        backtest_data["created_at"],
                    ),
                )
                conn.commit()

            logger.info("回測運行記錄已保存: %s", backtest_data["id"])
            return True

        except Exception as e:
            logger.error("保存回測運行記錄失敗: %s", e)
            return False

    def update_backtest_status(
        self,
        backtest_id: str,
        status: str,
        progress: float = None,
        error_message: str = None,
    ) -> bool:
        """
        更新回測狀態

        Args:
            backtest_id: 回測ID
            status: 狀態
            progress: 進度
            error_message: 錯誤訊息

        Returns:
            bool: 是否更新成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                update_fields = ["status = ?"]
                params = [status]

                if progress is not None:
                    update_fields.append("progress = ?")
                    params.append(progress)

                if error_message is not None:
                    update_fields.append("error_message = ?")
                    params.append(error_message)

                if status == "running" and progress == 0:
                    update_fields.append("started_at = ?")
                    params.append(datetime.now().isoformat())
                elif status in ["completed", "failed"]:
                    update_fields.append("completed_at = ?")
                    params.append(datetime.now().isoformat())

                params.append(backtest_id)

                cursor.execute(
                    f"""
                    UPDATE backtest_runs
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """,
                    params,
                )

                conn.commit()

            logger.debug("回測狀態已更新: %s -> %s", backtest_id, status)
            return True

        except Exception as e:
            logger.error("更新回測狀態失敗: %s", e)
            return False

    def save_backtest_metrics(
        self, backtest_id: str, metrics: Dict[str, float]
    ) -> bool:
        """
        保存回測績效指標

        Args:
            backtest_id: 回測ID
            metrics: 績效指標

        Returns:
            bool: 是否保存成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 先刪除舊記錄
                cursor.execute(
                    "DELETE FROM backtest_metrics WHERE backtest_id = ?", (backtest_id,)
                )

                # 插入新記錄
                cursor.execute(
                    """
                    INSERT INTO backtest_metrics
                    (backtest_id, initial_capital, final_capital, total_return, annual_return,
                     sharpe_ratio, max_drawdown, win_rate, profit_ratio, total_trades,
                     winning_trades, losing_trades, avg_trade_duration, max_consecutive_wins,
                     max_consecutive_losses, calmar_ratio, sortino_ratio, var_95, beta, alpha,
                     information_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        backtest_id,
                        metrics.get("initial_capital", 0),
                        metrics.get("final_capital", 0),
                        metrics.get("total_return", 0),
                        metrics.get("annual_return", 0),
                        metrics.get("sharpe_ratio", 0),
                        metrics.get("max_drawdown", 0),
                        metrics.get("win_rate", 0),
                        metrics.get("profit_ratio", 0),
                        metrics.get("total_trades", 0),
                        metrics.get("winning_trades", 0),
                        metrics.get("losing_trades", 0),
                        metrics.get("avg_trade_duration", 0),
                        metrics.get("max_consecutive_wins", 0),
                        metrics.get("max_consecutive_losses", 0),
                        metrics.get("calmar_ratio", 0),
                        metrics.get("sortino_ratio", 0),
                        metrics.get("var_95", 0),
                        metrics.get("beta", 0),
                        metrics.get("alpha", 0),
                        metrics.get("information_ratio", 0),
                    ),
                )

                conn.commit()

            logger.info("回測績效指標已保存: %s", backtest_id)
            return True

        except Exception as e:
            logger.error("保存回測績效指標失敗: %s", e)
            return False

    def get_backtest_info(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取回測信息

        Args:
            backtest_id: 回測ID

        Returns:
            Optional[Dict[str, Any]]: 回測信息
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT r.*, m.total_return, m.sharpe_ratio, m.max_drawdown, m.win_rate
                    FROM backtest_runs r
                    LEFT JOIN backtest_metrics m ON r.id = m.backtest_id
                    WHERE r.id = ?
                """,
                    (backtest_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                return {
                    "id": row[0],
                    "strategy_id": row[1],
                    "strategy_name": row[2],
                    "symbols": json.loads(row[3]) if row[3] else [],
                    "start_date": datetime.fromisoformat(row[4]) if row[4] else None,
                    "end_date": datetime.fromisoformat(row[5]) if row[5] else None,
                    "initial_capital": row[6],
                    "commission": row[7],
                    "slippage": row[8],
                    "tax": row[9],
                    "status": row[10],
                    "progress": row[11] or 0,
                    "created_at": datetime.fromisoformat(row[12]) if row[12] else None,
                    "started_at": datetime.fromisoformat(row[13]) if row[13] else None,
                    "completed_at": (
                        datetime.fromisoformat(row[14]) if row[14] else None
                    ),
                    "error_message": row[15],
                    "results_path": row[16],
                    "total_return": row[17],
                    "sharpe_ratio": row[18],
                    "max_drawdown": row[19],
                    "win_rate": row[20],
                }

        except Exception as e:
            logger.error("獲取回測信息失敗: %s", e)
            return None
