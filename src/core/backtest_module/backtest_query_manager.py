"""回測查詢管理模組

此模組負責管理回測結果的查詢和匯出功能，包括：
- 回測列表查詢
- 回測結果查詢
- 績效指標查詢
- 交易記錄查詢
- 圖表數據查詢
- 結果匯出
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

# 設定日誌
logger = logging.getLogger(__name__)


class BacktestQueryManager:
    """回測查詢管理器"""

    def __init__(self, db_path: str, results_manager):
        """初始化查詢管理器

        Args:
            db_path: 資料庫路徑
            results_manager: 結果管理器實例
        """
        self.db_path = db_path
        self.results_manager = results_manager

    def get_backtest_list(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """獲取回測列表

        Args:
            limit: 限制數量
            offset: 偏移量

        Returns:
            List[Dict]: 回測列表
        """
        try:
            return self.results_manager.get_backtest_list(limit, offset)
        except Exception as e:
            logger.error("查詢回測列表失敗: %s", e)
            return []

    def get_backtest_results(self, backtest_id: str) -> Optional[Dict]:
        """獲取回測結果

        Args:
            backtest_id: 回測ID

        Returns:
            Optional[Dict]: 回測結果
        """
        try:
            return self.results_manager.get_backtest_results(backtest_id)
        except Exception as e:
            logger.error("獲取回測結果失敗: %s", e)
            return None

    def get_backtest_info(self, backtest_id: str) -> Optional[Dict]:
        """獲取回測基本資訊

        Args:
            backtest_id: 回測ID

        Returns:
            Optional[Dict]: 回測基本資訊
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, strategy_id, strategy_name, symbols, start_date, end_date,
                           initial_capital, status, progress, created_at, started_at, completed_at
                    FROM backtest_runs
                    WHERE id = ?
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
                    "status": row[7],
                    "progress": row[8],
                    "created_at": datetime.fromisoformat(row[9]) if row[9] else None,
                    "started_at": datetime.fromisoformat(row[10]) if row[10] else None,
                    "completed_at": (
                        datetime.fromisoformat(row[11]) if row[11] else None
                    ),
                }

        except Exception as e:
            logger.error("獲取回測資訊失敗: %s", e)
            return None

    def get_performance_metrics(self, backtest_id: str) -> Optional[Dict]:
        """獲取回測效能指標

        Args:
            backtest_id: 回測ID

        Returns:
            Optional[Dict]: 效能指標
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT initial_capital, final_capital, total_return, annual_return,
                           sharpe_ratio, max_drawdown, win_rate, profit_ratio, total_trades,
                           winning_trades, losing_trades, avg_trade_duration, max_consecutive_wins,
                           max_consecutive_losses, calmar_ratio, sortino_ratio, var_95, beta, alpha,
                           information_ratio
                    FROM backtest_metrics
                    WHERE backtest_id = ?
                """,
                    (backtest_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                return {
                    "total_return": row[2] or 0.0,
                    "annual_return": row[3] or 0.0,
                    "sharpe_ratio": row[4] or 0.0,
                    "max_drawdown": row[5] or 0.0,
                    "win_rate": row[6] or 0.0,
                    "profit_factor": row[7] or 0.0,
                    "total_trades": int(row[8] or 0),
                    "avg_trade_return": (
                        (row[2] / row[8]) if row[8] and row[8] > 0 else 0.0
                    ),
                    "volatility": 0.0,  # 需要從日收益率計算
                    "calmar_ratio": row[14] or 0.0,
                }

        except Exception as e:
            logger.error("獲取效能指標失敗: %s", e)
            return None

    def get_transaction_records(
        self, backtest_id: str, symbol: str = None, action: str = None
    ) -> List[Dict]:
        """獲取交易記錄

        Args:
            backtest_id: 回測ID
            symbol: 股票代碼篩選 (可選)
            action: 交易動作篩選 (可選)

        Returns:
            List[Dict]: 交易記錄列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 構建查詢條件
                where_conditions = ["backtest_id = ?"]
                params = [backtest_id]

                if symbol:
                    where_conditions.append("symbol = ?")
                    params.append(symbol)

                if action:
                    where_conditions.append("trade_type = ?")
                    params.append(action)

                where_clause = " AND ".join(where_conditions)

                cursor.execute(
                    f"""
                    SELECT symbol, entry_date, trade_type, quantity, entry_price,
                           entry_price * quantity as amount, commission_paid, tax_paid,
                           (entry_price * quantity + commission_paid + tax_paid) as net_amount,
                           0 as portfolio_value, 0 as cash_balance
                    FROM backtest_trades
                    WHERE {where_clause}
                    ORDER BY entry_date
                """,
                    params,
                )

                rows = cursor.fetchall()
                transactions = []

                for row in rows:
                    transactions.append(
                        {
                            "date": (
                                datetime.fromisoformat(row[1])
                                if row[1]
                                else datetime.now()
                            ),
                            "symbol": row[0],
                            "action": "buy" if row[2] == "long" else "sell",
                            "quantity": int(row[3] or 0),
                            "price": float(row[4] or 0),
                            "amount": float(row[5] or 0),
                            "commission": float(row[6] or 0),
                            "tax": float(row[7] or 0),
                            "net_amount": float(row[8] or 0),
                            "portfolio_value": float(row[9] or 0),
                            "cash_balance": float(row[10] or 0),
                        }
                    )

                return transactions

        except Exception as e:
            logger.error("獲取交易記錄失敗: %s", e)
            return []

    def get_chart_data(self, backtest_id: str) -> Optional[Dict]:
        """獲取圖表數據

        Args:
            backtest_id: 回測ID

        Returns:
            Optional[Dict]: 圖表數據
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT date, equity_value, daily_return, cumulative_return, drawdown
                    FROM backtest_equity
                    WHERE backtest_id = ?
                    ORDER BY date
                """,
                    (backtest_id,),
                )

                rows = cursor.fetchall()
                if not rows:
                    return None

                dates = [row[0] for row in rows]
                portfolio_values = [float(row[1] or 0) for row in rows]
                returns = [float(row[2] or 0) for row in rows]
                drawdown = [float(row[4] or 0) for row in rows]

                return {
                    "dates": dates,
                    "portfolio_values": portfolio_values,
                    "benchmark_values": None,  # 需要基準數據
                    "drawdown": drawdown,
                    "returns": returns,
                }

        except Exception as e:
            logger.error("獲取圖表數據失敗: %s", e)
            return None

    def export_results(
        self, backtest_id: str, export_format: str = "json"
    ) -> Optional[bytes]:
        """匯出回測結果

        Args:
            backtest_id: 回測ID
            export_format: 匯出格式 ('json', 'csv', 'excel', 'html')

        Returns:
            Optional[bytes]: 匯出的檔案內容
        """
        try:
            results = self.get_backtest_results(backtest_id)
            if not results:
                return None

            if export_format == "json":
                return json.dumps(results, ensure_ascii=False, indent=2).encode("utf-8")

            elif export_format == "csv":
                return self._export_to_csv(results)

            elif export_format == "excel":
                return self._export_to_excel(results)

            elif export_format == "html":
                return self._export_to_html(results)

            else:
                raise ValueError(f"不支援的匯出格式: {export_format}")

        except Exception as e:
            logger.error("匯出回測結果失敗: %s", e)
            return None

    def _export_to_csv(self, results: Dict) -> bytes:
        """匯出為CSV格式

        Args:
            results: 回測結果

        Returns:
            bytes: CSV內容
        """
        # 簡化實現，實際應該使用pandas
        csv_content = "metric,value\n"
        metrics = results.get("metrics", {})
        for key, value in metrics.items():
            csv_content += f"{key},{value}\n"

        return csv_content.encode("utf-8")

    def _export_to_excel(self, results: Dict) -> bytes:
        """匯出為Excel格式

        Args:
            results: 回測結果

        Returns:
            bytes: Excel內容
        """
        # 簡化實現，實際應該使用openpyxl或xlsxwriter
        return b"Excel export not implemented"

    def _export_to_html(self, results: Dict) -> bytes:
        """匯出為HTML格式

        Args:
            results: 回測結果

        Returns:
            bytes: HTML內容
        """
        # 簡化實現
        html_content = "<html><body><h1>Backtest Results</h1>"
        html_content += f"<pre>{json.dumps(results, indent=2)}</pre>"
        html_content += "</body></html>"

        return html_content.encode("utf-8")
