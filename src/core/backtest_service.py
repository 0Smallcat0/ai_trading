"""回測服務

此模組提供完整的回測管理功能，包括：
- 回測參數設定和驗證
- 回測執行控制和進度管理
- 績效分析和指標計算
- 交易記錄管理和查詢
- 報表生成和匯出功能
"""

from pathlib import Path
from typing import Dict, List, Optional
import logging

# 導入回測相關模組
from .backtest_module import (
    BacktestConfig,
    validate_backtest_config,
    BacktestDatabaseManager,
    BacktestResultsManager,
    generate_report
)

# 導入新的模組化組件
from .backtest_module.backtest_data_manager import BacktestDataManager
from .backtest_module.backtest_status_manager import BacktestStatusManager
from .backtest_module.backtest_query_manager import BacktestQueryManager
from .backtest_module.mock_backtest_engine import MockBacktest
from .backtest_module.backtest_performance_calculator import BacktestPerformanceCalculator

# 設定日誌
logger = logging.getLogger(__name__)

# 導入回測引擎
try:
    import backtrader as bt
    BACKTRADER_AVAILABLE = True
except ImportError as e:
    logger.warning("Backtrader 未安裝: %s", e)
    BACKTRADER_AVAILABLE = False


class BacktestService:
    """回測服務類"""

    def __init__(self, db_path: str = None):
        """初始化回測服務

        Args:
            db_path: 資料庫路徑
        """
        self.db_path = db_path or "data/backtest.db"
        self.results_dir = Path("data/backtest_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # 初始化數據庫管理器
        self.db_manager = BacktestDatabaseManager(self.db_path)

        # 初始化結果管理器
        self.results_manager = BacktestResultsManager(self.db_path, self.results_dir)

        # 初始化模組化組件
        self.data_manager = BacktestDataManager()
        self.status_manager = BacktestStatusManager(self.db_path)
        self.query_manager = BacktestQueryManager(self.db_path, self.results_manager)
        self.performance_calculator = BacktestPerformanceCalculator()

    def get_available_strategies(self) -> List[Dict]:
        """獲取可用策略列表

        Returns:
            List[Dict]: 策略列表
        """
        return self.data_manager.get_available_strategies()

    def get_available_stocks(self) -> List[Dict]:
        """獲取可用股票列表

        Returns:
            List[Dict]: 股票列表
        """
        return self.data_manager.get_available_stocks()

    def start_backtest(self, config: BacktestConfig) -> str:
        """啟動回測

        Args:
            config: 回測配置

        Returns:
            str: 回測ID
        """
        # 驗證配置
        is_valid, error_msg = validate_backtest_config(config)
        if not is_valid:
            raise ValueError(error_msg)

        # 創建回測任務
        backtest_id = self.status_manager.create_backtest_task(config)

        # 啟動回測線程
        self.status_manager.start_backtest_thread(
            backtest_id, self._run_backtest_thread, (backtest_id, config)
        )

        logger.info("回測任務已啟動: %s", backtest_id)
        return backtest_id

    def _run_backtest_thread(self, backtest_id: str, config: BacktestConfig):
        """
        回測執行線程

        Args:
            backtest_id: 回測ID
            config: 回測配置
        """
        try:
            # 更新狀態為運行中
            self._update_backtest_status(
                backtest_id, "running", 0, "正在準備回測資料..."
            )

            # 載入市場資料
            self.status_manager.update_backtest_status(
                backtest_id, "running", 10, "正在載入市場資料..."
            )
            market_data = self.data_manager.load_market_data(
                config.symbols, config.start_date, config.end_date
            )

            # 初始化策略
            self.status_manager.update_backtest_status(
                backtest_id, "running", 20, "正在初始化策略..."
            )
            strategy = self.data_manager.initialize_strategy(config.strategy_id, config)

            # 生成交易信號
            self.status_manager.update_backtest_status(
                backtest_id, "running", 40, "正在生成交易信號..."
            )
            signals = self.data_manager.generate_signals(strategy, market_data)

            # 執行回測
            self.status_manager.update_backtest_status(
                backtest_id, "running", 60, "正在執行回測..."
            )

            # 執行回測 - 目前使用模擬引擎
            logger.info("使用模擬回測引擎")
            backtest_engine = MockBacktest(
                price_df=market_data,
                initial_capital=config.initial_capital,
                commission=config.commission,
                slippage=config.slippage,
            )
            results = backtest_engine.run(signals)

            # 計算績效指標
            self.status_manager.update_backtest_status(
                backtest_id, "running", 80, "正在計算績效指標..."
            )
            metrics = self.performance_calculator.calculate_performance_metrics(
                results, config
            )

            # 保存結果
            self.status_manager.update_backtest_status(
                backtest_id, "running", 90, "正在保存結果..."
            )
            self.results_manager.save_backtest_results(
                backtest_id, results, metrics, config
            )

            # 完成回測
            self.status_manager.update_backtest_status(
                backtest_id, "completed", 100, "回測完成"
            )

            # 標記完成
            self.status_manager.mark_completed(backtest_id)
            logger.info("回測完成: %s", backtest_id)

        except Exception as e:
            error_msg = f"回測執行失敗: {str(e)}"
            logger.error("回測 %s 失敗: %s", backtest_id, e)

            # 更新錯誤狀態
            self.status_manager.update_backtest_status(
                backtest_id, "failed", 0, error_msg
            )
            self.status_manager.mark_failed(backtest_id, error_msg)

        finally:
            # 清理線程記錄
            self.status_manager.cleanup_thread(backtest_id)

    def _update_backtest_status(
        self, backtest_id: str, status: str, progress: float, message: str
    ):
        """更新回測狀態（委託給狀態管理器）

        Args:
            backtest_id: 回測ID
            status: 狀態
            progress: 進度 (0-100)
            message: 狀態訊息
        """
        self.status_manager.update_backtest_status(
            backtest_id, status, progress, message
        )

    def get_backtest_status(self, backtest_id: str) -> Dict:
        """獲取回測狀態

        Args:
            backtest_id: 回測ID

        Returns:
            Dict: 回測狀態資訊
        """
        return self.status_manager.get_backtest_status(backtest_id)

    def get_backtest_list(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """獲取回測列表

        Args:
            limit: 限制數量
            offset: 偏移量

        Returns:
            List[Dict]: 回測列表
        """
        return self.query_manager.get_backtest_list(limit, offset)

    def get_backtest_results(self, backtest_id: str) -> Optional[Dict]:
        """獲取回測結果

        Args:
            backtest_id: 回測ID

        Returns:
            Optional[Dict]: 回測結果
        """
        return self.query_manager.get_backtest_results(backtest_id)

    def cancel_backtest(self, backtest_id: str) -> bool:
        """取消回測

        Args:
            backtest_id: 回測ID

        Returns:
            bool: 是否成功取消
        """
        return self.status_manager.cancel_backtest(backtest_id)

    def delete_backtest(self, backtest_id: str) -> bool:
        """
        刪除回測

        Args:
            backtest_id: 回測ID

        Returns:
            bool: 是否成功刪除
        """
        try:
            # 先取消如果正在運行
            if backtest_id in self.running_backtests:
                self.cancel_backtest(backtest_id)

            # 刪除資料庫記錄
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 刪除相關表的記錄
                cursor.execute(
                    "DELETE FROM backtest_equity WHERE backtest_id = ?", (backtest_id,)
                )
                cursor.execute(
                    "DELETE FROM backtest_trades WHERE backtest_id = ?", (backtest_id,)
                )
                cursor.execute(
                    "DELETE FROM backtest_metrics WHERE backtest_id = ?", (backtest_id,)
                )
                cursor.execute("DELETE FROM backtest_runs WHERE id = ?", (backtest_id,))

                conn.commit()

            # 刪除結果檔案
            results_file = self.results_dir / f"{backtest_id}.json"
            if results_file.exists():
                results_file.unlink()

            logger.info(f"回測已刪除: {backtest_id}")
            return True

        except Exception as e:
            logger.error(f"刪除回測失敗: {e}")
            return False

    def export_results(self, backtest_id: str, format: str = "json") -> Optional[bytes]:
        """
        匯出回測結果

        Args:
            backtest_id: 回測ID
            format: 匯出格式 ('json', 'csv', 'excel', 'html')

        Returns:
            Optional[bytes]: 匯出的檔案內容
        """
        try:
            results = self.get_backtest_results(backtest_id)
            if not results:
                return None

            if format == "json":
                return json.dumps(results, ensure_ascii=False, indent=2).encode("utf-8")

            elif format == "csv":
                return self._export_to_csv(results)

            elif format == "excel":
                return self._export_to_excel(results)

            elif format == "html":
                return self._export_to_html(results)

            else:
                raise ValueError(f"不支援的匯出格式: {format}")

        except Exception as e:
            logger.error(f"匯出回測結果失敗: {e}")
            return None

    def get_backtest_info(self, backtest_id: str) -> Optional[Dict]:
        """
        獲取回測基本資訊

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

                # 獲取當前狀態（如果正在運行）
                current_status = self.get_backtest_status(backtest_id)

                return {
                    "id": row[0],
                    "strategy_id": row[1],
                    "strategy_name": row[2],
                    "symbols": json.loads(row[3]) if row[3] else [],
                    "start_date": datetime.fromisoformat(row[4]) if row[4] else None,
                    "end_date": datetime.fromisoformat(row[5]) if row[5] else None,
                    "initial_capital": row[6],
                    "status": current_status.get("status", row[7]),
                    "progress": current_status.get("progress", row[8]),
                    "message": current_status.get("message", ""),
                    "created_at": datetime.fromisoformat(row[9]) if row[9] else None,
                    "started_at": datetime.fromisoformat(row[10]) if row[10] else None,
                    "completed_at": (
                        datetime.fromisoformat(row[11]) if row[11] else None
                    ),
                }

        except Exception as e:
            logger.error(f"獲取回測資訊失敗: {e}")
            return None

    def get_performance_metrics(self, backtest_id: str) -> Optional[Dict]:
        """
        獲取回測效能指標

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
            logger.error(f"獲取效能指標失敗: {e}")
            return None

    def get_transaction_records(
        self, backtest_id: str, symbol: str = None, action: str = None
    ) -> List[Dict]:
        """
        獲取交易記錄

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
            logger.error(f"獲取交易記錄失敗: {e}")
            return []

    def get_chart_data(self, backtest_id: str) -> Optional[Dict]:
        """
        獲取圖表數據

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
            logger.error(f"獲取圖表數據失敗: {e}")
            return None

    def generate_report(
        self,
        backtest_id: str,
        report_format: str = "html",
        include_charts: bool = False,
        include_transactions: bool = True,
    ) -> Optional[bytes]:
        """生成回測報表

        Args:
            backtest_id: 回測ID
            report_format: 報表格式
            include_charts: 是否包含圖表
            include_transactions: 是否包含交易明細

        Returns:
            Optional[bytes]: 報表內容
        """
        try:
            # 獲取回測結果
            results = self.results_manager.get_backtest_results(backtest_id)
            if not results:
                logger.error("找不到回測結果: %s", backtest_id)
                return None

            # 使用模組化的報表生成功能
            return generate_report(
                backtest_id,
                results,
                report_format,
                include_charts,
                include_transactions
            )

        except Exception as e:
            logger.error("生成回測報表失敗: %s", e)
            return None