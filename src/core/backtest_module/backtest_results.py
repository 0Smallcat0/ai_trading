"""
回測結果管理模組

此模組包含回測結果的保存、查詢和導出功能。
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class BacktestResultsManager:
    """回測結果管理器"""

    def __init__(self, db_path: str, results_dir: Path):
        """
        初始化結果管理器

        Args:
            db_path: 數據庫路徑
            results_dir: 結果目錄
        """
        self.db_path = db_path
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def save_backtest_results(
        self, backtest_id: str, results: Dict[str, Any], metrics: Dict[str, float]
    ) -> bool:
        """
        保存回測結果

        Args:
            backtest_id: 回測ID
            results: 回測結果
            metrics: 績效指標

        Returns:
            bool: 是否保存成功
        """
        try:
            # 保存績效指標到資料庫
            self._save_metrics_to_db(backtest_id, metrics)

            # 保存交易記錄到資料庫
            self._save_trades_to_db(backtest_id, results.get("trades", []))

            # 保存權益曲線到資料庫
            self._save_equity_curve_to_db(
                backtest_id, results.get("equity_curve", []), results.get("dates", [])
            )

            # 保存完整結果到檔案
            self._save_results_to_file(backtest_id, results, metrics)

            # 更新結果路徑
            self._update_results_path(backtest_id)

            logger.info("回測結果已保存: %s", backtest_id)
            return True

        except Exception as e:
            logger.error("保存回測結果失敗: %s", e)
            return False

    def get_backtest_results(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取回測結果

        Args:
            backtest_id: 回測ID

        Returns:
            Optional[Dict[str, Any]]: 回測結果
        """
        try:
            # 先從檔案載入完整結果
            results_file = self.results_dir / f"{backtest_id}.json"
            if results_file.exists():
                with open(results_file, "r", encoding="utf-8") as f:
                    return json.load(f)

            # 如果檔案不存在，從資料庫重建結果
            return self._rebuild_results_from_db(backtest_id)

        except Exception as e:
            logger.error("獲取回測結果失敗: %s", e)
            return None

    def get_backtest_list(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        獲取回測列表

        Args:
            limit: 限制數量
            offset: 偏移量

        Returns:
            List[Dict[str, Any]]: 回測列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT r.id, r.strategy_id, r.strategy_name, r.symbols,
                           r.start_date, r.end_date, r.initial_capital, r.status,
                           r.progress, r.created_at, r.completed_at,
                           m.total_return, m.sharpe_ratio, m.max_drawdown, m.win_rate
                    FROM backtest_runs r
                    LEFT JOIN backtest_metrics m ON r.id = m.backtest_id
                    ORDER BY r.created_at DESC
                    LIMIT ? OFFSET ?
                """,
                    (limit, offset),
                )

                rows = cursor.fetchall()
                backtest_list = []

                for row in rows:
                    backtest_list.append(
                        {
                            "id": row[0],
                            "strategy_id": row[1],
                            "strategy_name": row[2],
                            "symbols": json.loads(row[3]) if row[3] else [],
                            "start_date": row[4],
                            "end_date": row[5],
                            "initial_capital": row[6],
                            "status": row[7],
                            "progress": row[8],
                            "created_at": row[9],
                            "completed_at": row[10],
                            "total_return": row[11],
                            "sharpe_ratio": row[12],
                            "max_drawdown": row[13],
                            "win_rate": row[14],
                        }
                    )

                return backtest_list

        except Exception as e:
            logger.error("查詢回測列表失敗: %s", e)
            return []

    def _save_metrics_to_db(self, backtest_id: str, metrics: Dict[str, float]):
        """保存績效指標到資料庫"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO backtest_metrics
                (backtest_id, initial_capital, final_capital, total_return,
                 annual_return, sharpe_ratio, max_drawdown, win_rate,
                 profit_ratio, total_trades, winning_trades, losing_trades,
                 avg_trade_duration, max_consecutive_wins, max_consecutive_losses,
                 calmar_ratio, sortino_ratio, var_95, beta, alpha, information_ratio)
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

    def _save_trades_to_db(self, backtest_id: str, trades: List[Dict[str, Any]]):
        """保存交易記錄到資料庫"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for trade in trades:
                cursor.execute(
                    """
                    INSERT INTO backtest_trades
                    (backtest_id, symbol, entry_date, exit_date, entry_price,
                     exit_price, quantity, position_size, trade_type, profit,
                     profit_pct, commission_paid, slippage_cost, tax_paid,
                     hold_days, signal_strength)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        backtest_id,
                        trade.get("symbol", ""),
                        trade.get("entry_date", ""),
                        trade.get("exit_date", ""),
                        trade.get("entry_price", 0),
                        trade.get("exit_price", 0),
                        trade.get("quantity", 0),
                        trade.get("position_size", 0),
                        trade.get("trade_type", ""),
                        trade.get("profit", 0),
                        trade.get("profit_pct", 0),
                        trade.get("commission_paid", 0),
                        trade.get("slippage_cost", 0),
                        trade.get("tax_paid", 0),
                        trade.get("hold_days", 0),
                        trade.get("signal_strength", 0),
                    ),
                )
            conn.commit()

    def _save_equity_curve_to_db(
        self, backtest_id: str, equity_curve: List[float], dates: List[Any]
    ):
        """保存權益曲線到資料庫"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for i, (date, equity) in enumerate(zip(dates, equity_curve)):
                daily_return = 0
                cumulative_return = 0
                drawdown = 0

                if i > 0:
                    daily_return = (equity / equity_curve[i - 1] - 1) * 100
                    cumulative_return = (equity / equity_curve[0] - 1) * 100

                    # 計算回撤
                    peak = max(equity_curve[: i + 1])
                    drawdown = (peak - equity) / peak * 100

                cursor.execute(
                    """
                    INSERT INTO backtest_equity
                    (backtest_id, date, equity_value, cash_value, position_value,
                     daily_return, cumulative_return, drawdown)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        backtest_id,
                        date.isoformat() if hasattr(date, "isoformat") else str(date),
                        equity,
                        equity * 0.1,  # 假設現金比例
                        equity * 0.9,  # 假設持倉比例
                        daily_return,
                        cumulative_return,
                        drawdown,
                    ),
                )
            conn.commit()

    def _save_results_to_file(
        self, backtest_id: str, results: Dict[str, Any], metrics: Dict[str, float]
    ):
        """保存完整結果到檔案"""
        results_file = self.results_dir / f"{backtest_id}.json"
        with open(results_file, "w", encoding="utf-8") as f:
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
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)

    def _update_results_path(self, backtest_id: str):
        """更新結果路徑"""
        results_file = self.results_dir / f"{backtest_id}.json"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE backtest_runs SET results_path = ? WHERE id = ?
            """,
                (str(results_file), backtest_id),
            )
            conn.commit()

    def _rebuild_results_from_db(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """從資料庫重建結果"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 獲取基本資訊和指標
            cursor.execute(
                """
                SELECT r.*, m.*
                FROM backtest_runs r
                LEFT JOIN backtest_metrics m ON r.id = m.backtest_id
                WHERE r.id = ?
            """,
                (backtest_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            # 重建結果結構（簡化版）
            return {
                "backtest_id": backtest_id,
                "status": "completed",
                "message": "從資料庫重建的結果",
            }
