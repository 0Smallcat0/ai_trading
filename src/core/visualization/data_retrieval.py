"""報表視覺化數據檢索模組

此模組負責從資料庫檢索報表所需的各種數據，包括：
- 交易績效數據
- 交易明細數據
- 策略比較數據
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import pandas as pd
import numpy as np
from sqlalchemy import and_, desc
from sqlalchemy.orm import sessionmaker

# 使用修復後的別名導入
from src.database.schema import TradingOrder, TradeExecution

logger = logging.getLogger(__name__)


class DataRetrievalService:
    """數據檢索服務"""

    def __init__(self, session_factory: sessionmaker):
        """初始化數據檢索服務

        Args:
            session_factory: SQLAlchemy session factory
        """
        self.session_factory = session_factory

    def get_trading_performance_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        strategy_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """獲取交易績效數據

        Args:
            start_date: 開始日期
            end_date: 結束日期
            strategy_name: 策略名稱

        Returns:
            包含交易績效數據的字典
        """
        try:
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=365)  # 預設一年

            with self.session_factory() as session:
                # 獲取交易執行記錄
                query = session.query(TradeExecution).filter(
                    and_(
                        TradeExecution.execution_time >= start_date,
                        TradeExecution.execution_time <= end_date,
                    )
                )

                if strategy_name:
                    # 通過訂單關聯策略
                    query = query.join(TradingOrder).filter(
                        TradingOrder.strategy_name == strategy_name
                    )

                executions = query.order_by(TradeExecution.execution_time).all()

                if not executions:
                    return {"message": "無交易數據"}

                # 轉換為 DataFrame
                data = []
                for execution in executions:
                    data.append(
                        {
                            "execution_time": execution.execution_time,
                            "symbol": execution.symbol,
                            "action": execution.action,
                            "quantity": execution.quantity,
                            "price": execution.price,
                            "amount": execution.amount,
                            "commission": execution.commission or 0,
                            "tax": execution.tax or 0,
                            "net_amount": execution.net_amount or execution.amount,
                        }
                    )

                df = pd.DataFrame(data)

                # 計算累積報酬
                df["cumulative_pnl"] = df["net_amount"].cumsum()
                df["daily_return"] = df.groupby(df["execution_time"].dt.date)[
                    "net_amount"
                ].sum()

                # 計算績效指標
                performance_metrics = self._calculate_performance_metrics(df)

                return {
                    "data": df.to_dict("records"),
                    "metrics": performance_metrics,
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                }

        except Exception as e:
            logger.error("獲取交易績效數據失敗: %s", e)
            return {"error": str(e)}

    def get_trade_details_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """獲取交易明細數據

        Args:
            start_date: 開始日期
            end_date: 結束日期
            symbol: 股票代碼
            limit: 限制筆數

        Returns:
            包含交易明細數據的字典
        """
        try:
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=90)  # 預設三個月

            with self.session_factory() as session:
                # 獲取交易訂單和執行記錄
                query = (
                    session.query(TradingOrder, TradeExecution)
                    .join(
                        TradeExecution, TradingOrder.order_id == TradeExecution.order_id
                    )
                    .filter(
                        and_(
                            TradingOrder.created_at >= start_date,
                            TradingOrder.created_at <= end_date,
                        )
                    )
                )

                if symbol:
                    query = query.filter(TradingOrder.symbol == symbol)

                results = (
                    query.order_by(desc(TradingOrder.created_at)).limit(limit).all()
                )

                if not results:
                    return {"message": "無交易明細數據"}

                # 轉換為詳細記錄
                details = []
                for order, execution in results:
                    holding_period = None
                    if order.filled_at and order.created_at:
                        holding_period = (
                            order.filled_at - order.created_at
                        ).total_seconds() / 3600  # 小時

                    details.append(
                        {
                            "order_id": order.order_id,
                            "symbol": order.symbol,
                            "action": order.action,
                            "order_time": order.created_at.isoformat(),
                            "execution_time": execution.execution_time.isoformat(),
                            "order_price": order.price,
                            "execution_price": execution.price,
                            "quantity": execution.quantity,
                            "amount": execution.amount,
                            "commission": execution.commission or 0,
                            "tax": execution.tax or 0,
                            "net_amount": execution.net_amount or execution.amount,
                            "holding_period_hours": (
                                round(holding_period, 2) if holding_period else None
                            ),
                            "strategy_name": order.strategy_name,
                            "signal_id": order.signal_id,
                        }
                    )

                # 計算統計資訊
                df = pd.DataFrame(details)
                statistics = self._calculate_trade_statistics(df)

                return {
                    "details": details,
                    "statistics": statistics,
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                    },
                }

        except Exception as e:
            logger.error("獲取交易明細數據失敗: %s", e)
            return {"error": str(e)}

    def compare_strategies_performance(
        self,
        strategy_names: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """比較策略績效

        Args:
            strategy_names: 策略名稱列表
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            包含策略比較數據的字典
        """
        try:
            if not strategy_names:
                return {"error": "未指定策略名稱"}

            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=365)

            strategies_data = {}

            for strategy_name in strategy_names:
                # 獲取策略績效數據
                strategy_data = self.get_trading_performance_data(
                    start_date=start_date,
                    end_date=end_date,
                    strategy_name=strategy_name,
                )

                if "error" not in strategy_data and "data" in strategy_data:
                    strategies_data[strategy_name] = strategy_data

            if not strategies_data:
                return {"message": "無策略數據可比較"}

            # 計算比較指標
            comparison_metrics = {}
            for strategy_name, data in strategies_data.items():
                metrics = data.get("metrics", {})
                comparison_metrics[strategy_name] = {
                    "total_return": metrics.get("total_pnl", 0),
                    "win_rate": metrics.get("win_rate", 0),
                    "sharpe_ratio": metrics.get("sharpe_ratio", 0),
                    "max_drawdown": metrics.get("max_drawdown", 0),
                    "profit_factor": metrics.get("profit_factor", 0),
                    "total_trades": metrics.get("total_trades", 0),
                }

            return {
                "strategies_data": strategies_data,
                "comparison_metrics": comparison_metrics,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            }

        except Exception as e:
            logger.error("比較策略績效失敗: %s", e)
            return {"error": str(e)}

    def _calculate_performance_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """計算績效指標

        Args:
            df: 交易數據 DataFrame

        Returns:
            績效指標字典
        """
        try:
            if df.empty:
                return {}

            # 基本統計
            total_trades = len(df)
            total_pnl = df["net_amount"].sum()

            # 勝率計算
            winning_trades = len(df[df["net_amount"] > 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            # 平均獲利/虧損
            avg_win = (
                df[df["net_amount"] > 0]["net_amount"].mean()
                if winning_trades > 0
                else 0
            )
            avg_loss = (
                df[df["net_amount"] < 0]["net_amount"].mean()
                if (total_trades - winning_trades) > 0
                else 0
            )

            # 獲利因子
            total_wins = df[df["net_amount"] > 0]["net_amount"].sum()
            total_losses = abs(df[df["net_amount"] < 0]["net_amount"].sum())
            profit_factor = (
                (total_wins / total_losses) if total_losses > 0 else float("inf")
            )

            # 最大回撤計算
            cumulative_pnl = df["net_amount"].cumsum()
            running_max = cumulative_pnl.expanding().max()
            drawdown = cumulative_pnl - running_max
            max_drawdown = drawdown.min()

            # 夏普比率計算（簡化版）
            daily_returns = df.groupby(df["execution_time"].dt.date)["net_amount"].sum()
            if len(daily_returns) > 1:
                sharpe_ratio = (
                    daily_returns.mean() / daily_returns.std() * np.sqrt(252)
                    if daily_returns.std() > 0
                    else 0
                )
            else:
                sharpe_ratio = 0

            return {
                "total_trades": total_trades,
                "total_pnl": round(total_pnl, 2),
                "win_rate": round(win_rate, 2),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_factor": (
                    round(profit_factor, 2) if profit_factor != float("inf") else "∞"
                ),
                "max_drawdown": round(max_drawdown, 2),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "total_commission": round(df["commission"].sum(), 2),
                "total_tax": round(df["tax"].sum(), 2),
            }

        except Exception as e:
            logger.error("計算績效指標失敗: %s", e)
            return {}

    def _calculate_trade_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """計算交易統計資訊

        Args:
            df: 交易明細 DataFrame

        Returns:
            交易統計資訊字典
        """
        try:
            if df.empty:
                return {}

            # 基本統計
            total_trades = len(df)
            total_volume = df["amount"].sum()
            total_commission = df["commission"].sum()
            total_tax = df["tax"].sum()

            # 持有期間統計
            holding_periods = df["holding_period_hours"].dropna()
            avg_holding_period = (
                holding_periods.mean() if not holding_periods.empty else 0
            )

            # 交易頻率（每日平均交易次數）
            if not df.empty:
                date_range = pd.to_datetime(df["execution_time"]).dt.date
                unique_days = len(date_range.unique())
                daily_trade_frequency = (
                    total_trades / unique_days if unique_days > 0 else 0
                )
            else:
                daily_trade_frequency = 0

            # 按股票分組統計
            symbol_stats = (
                df.groupby("symbol")
                .agg({"amount": "sum", "net_amount": "sum", "quantity": "sum"})
                .to_dict("index")
            )

            # 按策略分組統計
            strategy_stats = (
                df.groupby("strategy_name")
                .agg({"amount": "sum", "net_amount": "sum", "order_id": "count"})
                .rename(columns={"order_id": "trade_count"})
                .to_dict("index")
            )

            return {
                "total_trades": total_trades,
                "total_volume": round(total_volume, 2),
                "total_commission": round(total_commission, 2),
                "total_tax": round(total_tax, 2),
                "avg_holding_period_hours": round(avg_holding_period, 2),
                "daily_trade_frequency": round(daily_trade_frequency, 2),
                "symbol_statistics": symbol_stats,
                "strategy_statistics": strategy_stats,
            }

        except Exception as e:
            logger.error("計算交易統計資訊失敗: %s", e)
            return {}
