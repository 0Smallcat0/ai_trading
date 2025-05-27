"""
投資組合管理服務

此模組提供完整的投資組合管理功能，包括：
- 投資組合 CRUD 操作
- 權重計算和最佳化演算法
- 績效指標計算和風險分析
- 回測引擎整合
- 資料存儲和版本管理
"""

import json
import uuid
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict

# 可選依賴
try:
    from scipy.optimize import minimize

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class PortfolioHolding:
    """投資組合持倉"""

    symbol: str
    name: str
    quantity: float
    price: float
    market_value: float
    weight: float
    sector: str = ""
    exchange: str = ""


@dataclass
class Portfolio:
    """投資組合"""

    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    total_value: float
    holdings: List[PortfolioHolding]
    benchmark: str = "^TWII"  # 預設基準指數
    risk_free_rate: float = 0.02  # 無風險利率

    def get_weights(self) -> np.ndarray:
        """獲取權重向量"""
        return np.array([h.weight for h in self.holdings])

    def get_symbols(self) -> List[str]:
        """獲取股票代碼列表"""
        return [h.symbol for h in self.holdings]

    def update_weights(self, new_weights: np.ndarray):
        """更新權重"""
        if len(new_weights) != len(self.holdings):
            raise ValueError("權重數量與持倉數量不符")

        # 正規化權重
        new_weights = new_weights / np.sum(new_weights)

        for i, holding in enumerate(self.holdings):
            holding.weight = float(new_weights[i])
            holding.market_value = holding.weight * self.total_value
            holding.quantity = (
                holding.market_value / holding.price if holding.price > 0 else 0
            )


@dataclass
class OptimizationConstraints:
    """最佳化約束條件"""

    min_weight: float = 0.0
    max_weight: float = 1.0
    sector_limits: Dict[str, Tuple[float, float]] = None
    target_return: Optional[float] = None
    max_risk: Optional[float] = None


class PortfolioService:
    """投資組合管理服務"""

    def __init__(self, db_path: str = None):
        """
        初始化投資組合服務

        Args:
            db_path: 資料庫路徑
        """
        self.db_path = db_path or "data/portfolio.db"
        self.data_dir = Path("data/portfolios")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化資料庫
        self._init_database()

    def _init_database(self):
        """初始化資料庫"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 創建投資組合表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS portfolios (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        total_value REAL NOT NULL,
                        benchmark TEXT DEFAULT '^TWII',
                        risk_free_rate REAL DEFAULT 0.02,
                        is_active INTEGER DEFAULT 1
                    )
                """
                )

                # 創建持倉表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS portfolio_holdings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        portfolio_id TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        name TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        price REAL NOT NULL,
                        market_value REAL NOT NULL,
                        weight REAL NOT NULL,
                        sector TEXT DEFAULT '',
                        exchange TEXT DEFAULT '',
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
                    )
                """
                )

                # 創建調整歷史表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS portfolio_adjustments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        portfolio_id TEXT NOT NULL,
                        adjustment_type TEXT NOT NULL,
                        old_weights TEXT,
                        new_weights TEXT,
                        reason TEXT,
                        created_at TEXT NOT NULL,
                        created_by TEXT DEFAULT 'system',
                        FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
                    )
                """
                )

                # 創建績效記錄表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS portfolio_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        portfolio_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        portfolio_value REAL NOT NULL,
                        daily_return REAL,
                        cumulative_return REAL,
                        benchmark_return REAL,
                        alpha REAL,
                        beta REAL,
                        sharpe_ratio REAL,
                        volatility REAL,
                        max_drawdown REAL,
                        FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
                    )
                """
                )

                # 創建配置建議表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS portfolio_suggestions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        portfolio_id TEXT NOT NULL,
                        suggestion_type TEXT NOT NULL,
                        suggested_weights TEXT NOT NULL,
                        expected_return REAL,
                        expected_risk REAL,
                        sharpe_ratio REAL,
                        created_at TEXT NOT NULL,
                        is_applied INTEGER DEFAULT 0,
                        FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
                    )
                """
                )

                conn.commit()
                logger.info("投資組合資料庫初始化完成")

        except Exception as e:
            logger.error(f"初始化投資組合資料庫時發生錯誤: {e}")
            raise

    def create_portfolio(self, portfolio: Portfolio) -> Optional[Portfolio]:
        """
        創建新的投資組合

        Args:
            portfolio: 投資組合對象

        Returns:
            Optional[Portfolio]: 創建的投資組合對象
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 插入投資組合
                cursor.execute(
                    """
                    INSERT INTO portfolios
                    (id, name, description, created_at, updated_at, total_value, benchmark, risk_free_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        portfolio.id,
                        portfolio.name,
                        portfolio.description,
                        portfolio.created_at.isoformat(),
                        portfolio.updated_at.isoformat(),
                        portfolio.total_value,
                        portfolio.benchmark,
                        portfolio.risk_free_rate,
                    ),
                )

                # 插入持倉
                for holding in portfolio.holdings:
                    cursor.execute(
                        """
                        INSERT INTO portfolio_holdings
                        (portfolio_id, symbol, name, quantity, price, market_value,
                         weight, sector, exchange, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            portfolio.id,
                            holding.symbol,
                            holding.name,
                            holding.quantity,
                            holding.price,
                            holding.market_value,
                            holding.weight,
                            holding.sector,
                            holding.exchange,
                            portfolio.created_at.isoformat(),
                        ),
                    )

                conn.commit()

                # 記錄創建歷史
                self._record_adjustment(
                    portfolio.id,
                    "create",
                    {},
                    {h.symbol: h.weight for h in portfolio.holdings},
                    f"創建投資組合: {portfolio.name}",
                )

                logger.info(f"投資組合已創建: {portfolio.id}")
                return portfolio

        except Exception as e:
            logger.error(f"創建投資組合失敗: {e}")
            return None

    def create_portfolio_legacy(
        self, name: str, description: str = "", holdings: List[Dict] = None
    ) -> str:
        """
        創建新的投資組合

        Args:
            name: 投資組合名稱
            description: 描述
            holdings: 初始持倉列表

        Returns:
            str: 投資組合ID
        """
        portfolio_id = str(uuid.uuid4())
        now = datetime.now()

        # 處理初始持倉
        portfolio_holdings = []
        total_value = 0

        if holdings:
            for holding_data in holdings:
                holding = PortfolioHolding(
                    symbol=holding_data["symbol"],
                    name=holding_data.get("name", holding_data["symbol"]),
                    quantity=holding_data["quantity"],
                    price=holding_data["price"],
                    market_value=holding_data["quantity"] * holding_data["price"],
                    weight=0,  # 稍後計算
                    sector=holding_data.get("sector", ""),
                    exchange=holding_data.get("exchange", ""),
                )
                portfolio_holdings.append(holding)
                total_value += holding.market_value

            # 計算權重
            for holding in portfolio_holdings:
                holding.weight = (
                    holding.market_value / total_value if total_value > 0 else 0
                )

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 插入投資組合
                cursor.execute(
                    """
                    INSERT INTO portfolios
                    (id, name, description, created_at, updated_at, total_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        portfolio_id,
                        name,
                        description,
                        now.isoformat(),
                        now.isoformat(),
                        total_value,
                    ),
                )

                # 插入持倉
                for holding in portfolio_holdings:
                    cursor.execute(
                        """
                        INSERT INTO portfolio_holdings
                        (portfolio_id, symbol, name, quantity, price, market_value,
                         weight, sector, exchange, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            portfolio_id,
                            holding.symbol,
                            holding.name,
                            holding.quantity,
                            holding.price,
                            holding.market_value,
                            holding.weight,
                            holding.sector,
                            holding.exchange,
                            now.isoformat(),
                        ),
                    )

                conn.commit()

                # 記錄創建歷史
                self._record_adjustment(
                    portfolio_id,
                    "create",
                    {},
                    {h.symbol: h.weight for h in portfolio_holdings},
                    f"創建投資組合: {name}",
                )

                logger.info(f"投資組合已創建: {portfolio_id}")
                return portfolio_id

        except Exception as e:
            logger.error(f"創建投資組合失敗: {e}")
            raise

    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """
        獲取投資組合

        Args:
            portfolio_id: 投資組合ID

        Returns:
            Optional[Portfolio]: 投資組合物件
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 獲取投資組合基本資訊
                cursor.execute(
                    """
                    SELECT id, name, description, created_at, updated_at,
                           total_value, benchmark, risk_free_rate
                    FROM portfolios
                    WHERE id = ? AND is_active = 1
                """,
                    (portfolio_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                # 獲取持倉
                cursor.execute(
                    """
                    SELECT symbol, name, quantity, price, market_value,
                           weight, sector, exchange
                    FROM portfolio_holdings
                    WHERE portfolio_id = ?
                    ORDER BY weight DESC
                """,
                    (portfolio_id,),
                )

                holdings = []
                for holding_row in cursor.fetchall():
                    holding = PortfolioHolding(
                        symbol=holding_row[0],
                        name=holding_row[1],
                        quantity=holding_row[2],
                        price=holding_row[3],
                        market_value=holding_row[4],
                        weight=holding_row[5],
                        sector=holding_row[6],
                        exchange=holding_row[7],
                    )
                    holdings.append(holding)

                portfolio = Portfolio(
                    id=row[0],
                    name=row[1],
                    description=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    updated_at=datetime.fromisoformat(row[4]),
                    total_value=row[5],
                    holdings=holdings,
                    benchmark=row[6],
                    risk_free_rate=row[7],
                )

                return portfolio

        except Exception as e:
            logger.error(f"獲取投資組合失敗: {e}")
            return None

    def get_portfolio_list(self, limit: int = 50) -> List[Dict]:
        """
        獲取投資組合列表

        Args:
            limit: 限制數量

        Returns:
            List[Dict]: 投資組合列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT p.id, p.name, p.description, p.created_at, p.updated_at,
                           p.total_value, COUNT(h.id) as holdings_count
                    FROM portfolios p
                    LEFT JOIN portfolio_holdings h ON p.id = h.portfolio_id
                    WHERE p.is_active = 1
                    GROUP BY p.id
                    ORDER BY p.updated_at DESC
                    LIMIT ?
                """,
                    (limit,),
                )

                portfolios = []
                for row in cursor.fetchall():
                    portfolios.append(
                        {
                            "id": row[0],
                            "name": row[1],
                            "description": row[2],
                            "created_at": row[3],
                            "updated_at": row[4],
                            "total_value": row[5],
                            "holdings_count": row[6],
                        }
                    )

                return portfolios

        except Exception as e:
            logger.error(f"獲取投資組合列表失敗: {e}")
            return []

    def list_portfolios(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Portfolio], int]:
        """
        獲取投資組合列表（支援分頁和搜尋）

        Args:
            page: 頁碼
            page_size: 每頁項目數
            search: 搜尋關鍵字
            sort_by: 排序欄位
            sort_order: 排序順序

        Returns:
            Tuple[List[Portfolio], int]: 投資組合列表和總數
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 構建查詢條件
                where_clause = "WHERE p.is_active = 1"
                params = []

                if search:
                    where_clause += " AND (p.name LIKE ? OR p.description LIKE ?)"
                    params.extend([f"%{search}%", f"%{search}%"])

                # 構建排序
                order_clause = f"ORDER BY p.{sort_by} {sort_order.upper()}"

                # 獲取總數
                count_query = f"""
                    SELECT COUNT(*)
                    FROM portfolios p
                    {where_clause}
                """
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]

                # 獲取分頁數據
                offset = (page - 1) * page_size
                data_query = f"""
                    SELECT p.id, p.name, p.description, p.created_at, p.updated_at,
                           p.total_value, p.benchmark, p.risk_free_rate
                    FROM portfolios p
                    {where_clause}
                    {order_clause}
                    LIMIT ? OFFSET ?
                """
                cursor.execute(data_query, params + [page_size, offset])

                portfolios = []
                for row in cursor.fetchall():
                    # 獲取持倉
                    cursor.execute(
                        """
                        SELECT symbol, name, quantity, price, market_value,
                               weight, sector, exchange
                        FROM portfolio_holdings
                        WHERE portfolio_id = ?
                        ORDER BY weight DESC
                    """,
                        (row[0],),
                    )

                    holdings = []
                    for holding_row in cursor.fetchall():
                        holding = PortfolioHolding(
                            symbol=holding_row[0],
                            name=holding_row[1],
                            quantity=holding_row[2],
                            price=holding_row[3],
                            market_value=holding_row[4],
                            weight=holding_row[5],
                            sector=holding_row[6],
                            exchange=holding_row[7],
                        )
                        holdings.append(holding)

                    portfolio = Portfolio(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        created_at=datetime.fromisoformat(row[3]),
                        updated_at=datetime.fromisoformat(row[4]),
                        total_value=row[5],
                        holdings=holdings,
                        benchmark=row[6],
                        risk_free_rate=row[7],
                    )
                    portfolios.append(portfolio)

                return portfolios, total_count

        except Exception as e:
            logger.error(f"獲取投資組合列表失敗: {e}")
            return [], 0

    def update_portfolio(
        self, portfolio_id: str, update_data: Dict
    ) -> Optional[Portfolio]:
        """
        更新投資組合

        Args:
            portfolio_id: 投資組合ID
            update_data: 更新資料

        Returns:
            Optional[Portfolio]: 更新後的投資組合
        """
        try:
            # 檢查投資組合是否存在
            existing_portfolio = self.get_portfolio(portfolio_id)
            if not existing_portfolio:
                return None

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 更新基本資訊
                update_fields = []
                params = []

                for field in [
                    "name",
                    "description",
                    "benchmark",
                    "risk_free_rate",
                    "total_value",
                ]:
                    if field in update_data:
                        update_fields.append(f"{field} = ?")
                        params.append(update_data[field])

                if update_fields:
                    update_fields.append("updated_at = ?")
                    params.append(datetime.now().isoformat())
                    params.append(portfolio_id)

                    query = (
                        f"UPDATE portfolios SET {', '.join(update_fields)} WHERE id = ?"
                    )
                    cursor.execute(query, params)

                # 更新持倉
                if "holdings" in update_data:
                    # 刪除舊持倉
                    cursor.execute(
                        "DELETE FROM portfolio_holdings WHERE portfolio_id = ?",
                        (portfolio_id,),
                    )

                    # 插入新持倉
                    for holding in update_data["holdings"]:
                        cursor.execute(
                            """
                            INSERT INTO portfolio_holdings
                            (portfolio_id, symbol, name, quantity, price, market_value,
                             weight, sector, exchange, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                portfolio_id,
                                holding.symbol,
                                holding.name,
                                holding.quantity,
                                holding.price,
                                holding.market_value,
                                holding.weight,
                                holding.sector,
                                holding.exchange,
                                datetime.now().isoformat(),
                            ),
                        )

                conn.commit()

                # 獲取更新後的投資組合
                return self.get_portfolio(portfolio_id)

        except Exception as e:
            logger.error(f"更新投資組合失敗: {e}")
            return None

    def update_portfolio_weights(
        self, portfolio_id: str, new_weights: Dict[str, float], reason: str = "手動調整"
    ) -> bool:
        """
        更新投資組合權重

        Args:
            portfolio_id: 投資組合ID
            new_weights: 新權重 {symbol: weight}
            reason: 調整原因

        Returns:
            bool: 是否成功
        """
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                return False

            # 記錄舊權重
            old_weights = {h.symbol: h.weight for h in portfolio.holdings}

            # 正規化新權重
            total_weight = sum(new_weights.values())
            if total_weight > 0:
                new_weights = {k: v / total_weight for k, v in new_weights.items()}

            # 更新權重
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for holding in portfolio.holdings:
                    if holding.symbol in new_weights:
                        new_weight = new_weights[holding.symbol]
                        new_market_value = new_weight * portfolio.total_value
                        new_quantity = (
                            new_market_value / holding.price if holding.price > 0 else 0
                        )

                        cursor.execute(
                            """
                            UPDATE portfolio_holdings
                            SET weight = ?, market_value = ?, quantity = ?
                            WHERE portfolio_id = ? AND symbol = ?
                        """,
                            (
                                new_weight,
                                new_market_value,
                                new_quantity,
                                portfolio_id,
                                holding.symbol,
                            ),
                        )

                # 更新投資組合更新時間
                cursor.execute(
                    """
                    UPDATE portfolios
                    SET updated_at = ?
                    WHERE id = ?
                """,
                    (datetime.now().isoformat(), portfolio_id),
                )

                conn.commit()

                # 記錄調整歷史
                self._record_adjustment(
                    portfolio_id, "weight_update", old_weights, new_weights, reason
                )

                logger.info(f"投資組合權重已更新: {portfolio_id}")
                return True

        except Exception as e:
            logger.error(f"更新投資組合權重失敗: {e}")
            return False

    def _record_adjustment(
        self,
        portfolio_id: str,
        adjustment_type: str,
        old_weights: Dict,
        new_weights: Dict,
        reason: str,
    ):
        """記錄調整歷史"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO portfolio_adjustments
                    (portfolio_id, adjustment_type, old_weights, new_weights, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        portfolio_id,
                        adjustment_type,
                        json.dumps(old_weights),
                        json.dumps(new_weights),
                        reason,
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"記錄調整歷史失敗: {e}")

    def rebalance_portfolio(
        self,
        portfolio_id: str,
        method: str = "equal_weight",
        target_weights: Dict[str, float] = None,
        constraints: Dict = None,
    ) -> Optional[Dict]:
        """
        執行投資組合再平衡

        Args:
            portfolio_id: 投資組合ID
            method: 再平衡方法
            target_weights: 目標權重
            constraints: 約束條件

        Returns:
            Optional[Dict]: 再平衡結果
        """
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                return None

            # 記錄舊權重
            old_weights = {h.symbol: h.weight for h in portfolio.holdings}
            symbols = portfolio.get_symbols()

            # 根據方法計算新權重
            if method == "custom" and target_weights:
                new_weights = target_weights
            elif method == "equal_weight":
                weight = 1.0 / len(symbols)
                new_weights = {symbol: weight for symbol in symbols}
            elif method == "mean_variance":
                new_weights = self.optimize_mean_variance(symbols, target_return=0.1)
            elif method == "risk_parity":
                new_weights = self.optimize_risk_parity(symbols)
            elif method == "max_sharpe":
                new_weights = self.optimize_maximum_sharpe(symbols)
            elif method == "min_variance":
                new_weights = self.optimize_minimum_variance(symbols)
            else:
                logger.error(f"不支援的再平衡方法: {method}")
                return None

            # 正規化權重
            total_weight = sum(new_weights.values())
            if total_weight > 0:
                new_weights = {k: v / total_weight for k, v in new_weights.items()}

            # 計算權重變化
            weight_changes = {}
            for symbol in symbols:
                old_weight = old_weights.get(symbol, 0.0)
                new_weight = new_weights.get(symbol, 0.0)
                weight_changes[symbol] = new_weight - old_weight

            # 更新權重
            success = self.update_portfolio_weights(
                portfolio_id, new_weights, f"再平衡: {method}"
            )

            if not success:
                return None

            # 計算預期回報和風險（模擬）
            expected_return = sum(new_weights.values()) * 0.08  # 模擬8%年化回報
            expected_risk = sum(new_weights.values()) * 0.15  # 模擬15%波動率

            # 計算再平衡成本（模擬）
            total_change = sum(abs(change) for change in weight_changes.values())
            rebalance_cost = (
                total_change * portfolio.total_value * 0.001
            )  # 0.1%交易成本

            return {
                "old_weights": old_weights,
                "new_weights": new_weights,
                "weight_changes": weight_changes,
                "expected_return": expected_return,
                "expected_risk": expected_risk,
                "rebalance_cost": rebalance_cost,
            }

        except Exception as e:
            logger.error(f"投資組合再平衡失敗: {e}")
            return None

    def calculate_performance_metrics(
        self,
        portfolio_id: str,
        start_date: datetime = None,
        end_date: datetime = None,
        benchmark: str = None,
    ) -> Optional[Dict]:
        """
        計算績效指標

        Args:
            portfolio_id: 投資組合ID
            start_date: 開始日期
            end_date: 結束日期
            benchmark: 基準指數

        Returns:
            Optional[Dict]: 績效指標
        """
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                return None

            # 生成模擬的績效數據
            # 在實際應用中，這裡應該從市場數據服務獲取真實數據
            returns_data = self._generate_mock_returns(portfolio.get_symbols())
            weights = portfolio.get_weights()

            # 計算投資組合報酬率
            portfolio_returns = (returns_data * weights).sum(axis=1)

            # 基本指標
            total_return = (1 + portfolio_returns).prod() - 1
            annual_return = portfolio_returns.mean() * 252
            volatility = portfolio_returns.std() * np.sqrt(252)
            sharpe_ratio = (
                (annual_return - portfolio.risk_free_rate) / volatility
                if volatility > 0
                else 0
            )

            # 最大回撤
            cumulative_returns = (1 + portfolio_returns).cumprod()
            peak = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - peak) / peak
            max_drawdown = drawdown.min()

            # 其他指標（模擬）
            calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
            sortino_ratio = (
                annual_return
                / (portfolio_returns[portfolio_returns < 0].std() * np.sqrt(252))
                if len(portfolio_returns[portfolio_returns < 0]) > 0
                else 0
            )

            # 相對指標（模擬）
            information_ratio = 0.5  # 模擬值
            beta = 1.0  # 模擬值
            alpha = annual_return - (
                portfolio.risk_free_rate + beta * 0.08
            )  # 模擬市場回報8%
            tracking_error = 0.03  # 模擬值

            return {
                "total_return": float(total_return),
                "annual_return": float(annual_return),
                "volatility": float(volatility),
                "sharpe_ratio": float(sharpe_ratio),
                "max_drawdown": float(max_drawdown),
                "calmar_ratio": float(calmar_ratio),
                "sortino_ratio": float(sortino_ratio),
                "information_ratio": float(information_ratio),
                "beta": float(beta),
                "alpha": float(alpha),
                "tracking_error": float(tracking_error),
            }

        except Exception as e:
            logger.error(f"計算績效指標失敗: {e}")
            return None

    def calculate_risk_metrics(
        self,
        portfolio_id: str,
        confidence_level: float = 0.95,
        lookback_days: int = 252,
    ) -> Optional[Dict]:
        """
        計算風險指標

        Args:
            portfolio_id: 投資組合ID
            confidence_level: 信心水準
            lookback_days: 回看天數

        Returns:
            Optional[Dict]: 風險指標
        """
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                return None

            # 生成模擬的報酬率數據
            returns_data = self._generate_mock_returns(
                portfolio.get_symbols(), lookback_days
            )
            weights = portfolio.get_weights()

            # 計算投資組合報酬率
            portfolio_returns = (returns_data * weights).sum(axis=1)

            # VaR 計算
            var_95 = np.percentile(portfolio_returns, (1 - 0.95) * 100)
            var_99 = np.percentile(portfolio_returns, (1 - 0.99) * 100)

            # CVaR 計算
            cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean()
            cvar_99 = portfolio_returns[portfolio_returns <= var_99].mean()

            # 波動率
            volatility = portfolio_returns.std() * np.sqrt(252)

            # 下行偏差
            downside_returns = portfolio_returns[portfolio_returns < 0]
            downside_deviation = (
                downside_returns.std() * np.sqrt(252)
                if len(downside_returns) > 0
                else 0
            )

            # 最大回撤
            cumulative_returns = (1 + portfolio_returns).cumprod()
            peak = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - peak) / peak
            max_drawdown = drawdown.min()

            # 相關性矩陣
            correlation_matrix = returns_data.corr().to_dict()

            # 集中度風險（赫芬達爾指數）
            concentration_risk = sum(w**2 for w in weights)

            return {
                "var_95": float(var_95),
                "var_99": float(var_99),
                "cvar_95": float(cvar_95),
                "cvar_99": float(cvar_99),
                "volatility": float(volatility),
                "downside_deviation": float(downside_deviation),
                "max_drawdown": float(max_drawdown),
                "correlation_matrix": correlation_matrix,
                "concentration_risk": float(concentration_risk),
            }

        except Exception as e:
            logger.error(f"計算風險指標失敗: {e}")
            return None

    def delete_portfolio(self, portfolio_id: str) -> bool:
        """
        刪除投資組合（軟刪除）

        Args:
            portfolio_id: 投資組合ID

        Returns:
            bool: 是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE portfolios
                    SET is_active = 0, updated_at = ?
                    WHERE id = ?
                """,
                    (datetime.now().isoformat(), portfolio_id),
                )
                conn.commit()

                logger.info(f"投資組合已刪除: {portfolio_id}")
                return True

        except Exception as e:
            logger.error(f"刪除投資組合失敗: {e}")
            return False

    def copy_portfolio(self, portfolio_id: str, new_name: str) -> Optional[str]:
        """
        複製投資組合

        Args:
            portfolio_id: 原投資組合ID
            new_name: 新投資組合名稱

        Returns:
            Optional[str]: 新投資組合ID
        """
        try:
            original = self.get_portfolio(portfolio_id)
            if not original:
                return None

            # 準備持倉資料
            holdings_data = []
            for holding in original.holdings:
                holdings_data.append(
                    {
                        "symbol": holding.symbol,
                        "name": holding.name,
                        "quantity": holding.quantity,
                        "price": holding.price,
                        "sector": holding.sector,
                        "exchange": holding.exchange,
                    }
                )

            # 創建新投資組合
            new_id = self.create_portfolio(
                name=new_name,
                description=f"複製自: {original.name}",
                holdings=holdings_data,
            )

            logger.info(f"投資組合已複製: {portfolio_id} -> {new_id}")
            return new_id

        except Exception as e:
            logger.error(f"複製投資組合失敗: {e}")
            return None

    def get_available_stocks(self) -> List[Dict]:
        """
        獲取可用股票列表

        Returns:
            List[Dict]: 股票列表
        """
        # 這裡應該從資料管理服務獲取股票列表
        # 目前返回模擬數據
        stocks = [
            {
                "symbol": "2330.TW",
                "name": "台積電",
                "exchange": "TWSE",
                "sector": "半導體",
                "price": 500.0,
            },
            {
                "symbol": "2317.TW",
                "name": "鴻海",
                "exchange": "TWSE",
                "sector": "電子零組件",
                "price": 100.0,
            },
            {
                "symbol": "2454.TW",
                "name": "聯發科",
                "exchange": "TWSE",
                "sector": "半導體",
                "price": 800.0,
            },
            {
                "symbol": "2308.TW",
                "name": "台達電",
                "exchange": "TWSE",
                "sector": "電子零組件",
                "price": 300.0,
            },
            {
                "symbol": "2412.TW",
                "name": "中華電",
                "exchange": "TWSE",
                "sector": "電信服務",
                "price": 120.0,
            },
            {
                "symbol": "2882.TW",
                "name": "國泰金",
                "exchange": "TWSE",
                "sector": "金融業",
                "price": 50.0,
            },
            {
                "symbol": "1301.TW",
                "name": "台塑",
                "exchange": "TWSE",
                "sector": "塑膠工業",
                "price": 80.0,
            },
            {
                "symbol": "2881.TW",
                "name": "富邦金",
                "exchange": "TWSE",
                "sector": "金融業",
                "price": 60.0,
            },
            {
                "symbol": "2303.TW",
                "name": "聯電",
                "exchange": "TWSE",
                "sector": "半導體",
                "price": 45.0,
            },
            {
                "symbol": "1303.TW",
                "name": "南亞",
                "exchange": "TWSE",
                "sector": "塑膠工業",
                "price": 70.0,
            },
            {
                "symbol": "AAPL",
                "name": "蘋果",
                "exchange": "NASDAQ",
                "sector": "科技",
                "price": 150.0,
            },
            {
                "symbol": "MSFT",
                "name": "微軟",
                "exchange": "NASDAQ",
                "sector": "科技",
                "price": 300.0,
            },
            {
                "symbol": "GOOGL",
                "name": "Alphabet",
                "exchange": "NASDAQ",
                "sector": "科技",
                "price": 120.0,
            },
            {
                "symbol": "AMZN",
                "name": "亞馬遜",
                "exchange": "NASDAQ",
                "sector": "電子商務",
                "price": 100.0,
            },
            {
                "symbol": "TSLA",
                "name": "特斯拉",
                "exchange": "NASDAQ",
                "sector": "汽車製造",
                "price": 200.0,
            },
        ]
        return stocks

    def calculate_portfolio_metrics(
        self, portfolio: Portfolio, returns_data: pd.DataFrame = None
    ) -> Dict:
        """
        計算投資組合績效指標

        Args:
            portfolio: 投資組合
            returns_data: 報酬率資料

        Returns:
            Dict: 績效指標
        """
        if returns_data is None:
            # 生成模擬報酬率資料
            returns_data = self._generate_mock_returns(portfolio.get_symbols())

        weights = portfolio.get_weights()

        # 計算投資組合報酬率
        portfolio_returns = (returns_data * weights).sum(axis=1)

        # 基本指標
        annual_return = portfolio_returns.mean() * 252
        volatility = portfolio_returns.std() * np.sqrt(252)
        sharpe_ratio = (
            (annual_return - portfolio.risk_free_rate) / volatility
            if volatility > 0
            else 0
        )

        # 最大回撤
        cumulative_returns = (1 + portfolio_returns).cumprod()
        peak = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = drawdown.min()

        # VaR
        var_95 = np.percentile(portfolio_returns, 5)

        # 相關性分析
        correlation_matrix = returns_data.corr()
        avg_correlation = correlation_matrix.values[
            np.triu_indices_from(correlation_matrix.values, k=1)
        ].mean()

        return {
            "annual_return": annual_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "var_95": var_95,
            "avg_correlation": avg_correlation,
            "total_return": (
                (cumulative_returns.iloc[-1] - 1) if len(cumulative_returns) > 0 else 0
            ),
        }

    def _generate_mock_returns(
        self, symbols: List[str], days: int = 252
    ) -> pd.DataFrame:
        """生成模擬報酬率資料"""
        np.random.seed(42)

        # 生成相關的報酬率
        n_assets = len(symbols)

        # 創建相關性矩陣
        correlation = np.random.uniform(0.1, 0.7, (n_assets, n_assets))
        correlation = (correlation + correlation.T) / 2
        np.fill_diagonal(correlation, 1.0)

        # 生成報酬率
        returns = np.random.multivariate_normal(
            mean=[0.0008] * n_assets,  # 日報酬率約0.08%
            cov=correlation * 0.02**2,  # 日波動率約2%
            size=days,
        )

        return pd.DataFrame(returns, columns=symbols)

    def optimize_equal_weight(self, symbols: List[str]) -> Dict[str, float]:
        """
        等權重配置

        Args:
            symbols: 股票代碼列表

        Returns:
            Dict[str, float]: 權重配置
        """
        n_assets = len(symbols)
        weight = 1.0 / n_assets
        return {symbol: weight for symbol in symbols}

    def optimize_risk_parity(
        self, symbols: List[str], returns_data: pd.DataFrame = None
    ) -> Dict[str, float]:
        """
        風險平衡配置

        Args:
            symbols: 股票代碼列表
            returns_data: 報酬率資料

        Returns:
            Dict[str, float]: 權重配置
        """
        if returns_data is None:
            returns_data = self._generate_mock_returns(symbols)

        # 計算協方差矩陣
        cov_matrix = returns_data.cov().values * 252  # 年化

        # 風險平衡目標函數
        def risk_parity_objective(weights):
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            marginal_contrib = np.dot(cov_matrix, weights) / portfolio_vol
            contrib = weights * marginal_contrib
            return np.sum((contrib - contrib.mean()) ** 2)

        # 約束條件
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bounds = tuple((0.01, 0.5) for _ in range(len(symbols)))

        # 初始權重
        x0 = np.array([1.0 / len(symbols)] * len(symbols))

        # 最佳化
        if not SCIPY_AVAILABLE:
            logger.warning("SciPy 不可用，使用等權重分配")
            return {symbol: 1.0 / len(symbols) for symbol in symbols}

        result = minimize(
            risk_parity_objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if result.success:
            weights = result.x / np.sum(result.x)  # 正規化
            return {symbol: weight for symbol, weight in zip(symbols, weights)}
        else:
            # 如果最佳化失敗，返回等權重
            return self.optimize_equal_weight(symbols)

    def optimize_minimum_variance(
        self, symbols: List[str], returns_data: pd.DataFrame = None
    ) -> Dict[str, float]:
        """
        最小變異數配置

        Args:
            symbols: 股票代碼列表
            returns_data: 報酬率資料

        Returns:
            Dict[str, float]: 權重配置
        """
        if returns_data is None:
            returns_data = self._generate_mock_returns(symbols)

        # 計算協方差矩陣
        cov_matrix = returns_data.cov().values * 252  # 年化

        # 目標函數：最小化變異數
        def objective(weights):
            return np.dot(weights, np.dot(cov_matrix, weights))

        # 約束條件
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bounds = tuple((0.01, 0.5) for _ in range(len(symbols)))

        # 初始權重
        x0 = np.array([1.0 / len(symbols)] * len(symbols))

        # 最佳化
        if not SCIPY_AVAILABLE:
            logger.warning("SciPy 不可用，使用等權重分配")
            return {symbol: 1.0 / len(symbols) for symbol in symbols}

        result = minimize(
            objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
        )

        if result.success:
            weights = result.x / np.sum(result.x)  # 正規化
            return {symbol: weight for symbol, weight in zip(symbols, weights)}
        else:
            return self.optimize_equal_weight(symbols)

    def optimize_maximum_sharpe(
        self,
        symbols: List[str],
        returns_data: pd.DataFrame = None,
        risk_free_rate: float = 0.02,
    ) -> Dict[str, float]:
        """
        最大夏普比率配置

        Args:
            symbols: 股票代碼列表
            returns_data: 報酬率資料
            risk_free_rate: 無風險利率

        Returns:
            Dict[str, float]: 權重配置
        """
        if returns_data is None:
            returns_data = self._generate_mock_returns(symbols)

        # 計算期望報酬率和協方差矩陣
        expected_returns = returns_data.mean().values * 252  # 年化
        cov_matrix = returns_data.cov().values * 252  # 年化

        # 目標函數：最大化夏普比率（最小化負夏普比率）
        def negative_sharpe(weights):
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            return -(portfolio_return - risk_free_rate) / portfolio_vol

        # 約束條件
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bounds = tuple((0.01, 0.5) for _ in range(len(symbols)))

        # 初始權重
        x0 = np.array([1.0 / len(symbols)] * len(symbols))

        # 最佳化
        if not SCIPY_AVAILABLE:
            logger.warning("SciPy 不可用，使用等權重分配")
            return {symbol: 1.0 / len(symbols) for symbol in symbols}

        result = minimize(
            negative_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints
        )

        if result.success:
            weights = result.x / np.sum(result.x)  # 正規化
            return {symbol: weight for symbol, weight in zip(symbols, weights)}
        else:
            return self.optimize_equal_weight(symbols)

    def optimize_mean_variance(
        self,
        symbols: List[str],
        target_return: float,
        returns_data: pd.DataFrame = None,
    ) -> Dict[str, float]:
        """
        均值變異數最佳化

        Args:
            symbols: 股票代碼列表
            target_return: 目標報酬率
            returns_data: 報酬率資料

        Returns:
            Dict[str, float]: 權重配置
        """
        if returns_data is None:
            returns_data = self._generate_mock_returns(symbols)

        # 計算期望報酬率和協方差矩陣
        expected_returns = returns_data.mean().values * 252  # 年化
        cov_matrix = returns_data.cov().values * 252  # 年化

        # 目標函數：最小化變異數
        def objective(weights):
            return np.dot(weights, np.dot(cov_matrix, weights))

        # 約束條件
        constraints = [
            {"type": "eq", "fun": lambda x: np.sum(x) - 1},  # 權重和為1
            {
                "type": "eq",
                "fun": lambda x: np.dot(x, expected_returns) - target_return,
            },  # 目標報酬率
        ]
        bounds = tuple((0.01, 0.5) for _ in range(len(symbols)))

        # 初始權重
        x0 = np.array([1.0 / len(symbols)] * len(symbols))

        # 最佳化
        if not SCIPY_AVAILABLE:
            logger.warning("SciPy 不可用，使用等權重分配")
            return {symbol: 1.0 / len(symbols) for symbol in symbols}

        result = minimize(
            objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
        )

        if result.success:
            weights = result.x / np.sum(result.x)  # 正規化
            return {symbol: weight for symbol, weight in zip(symbols, weights)}
        else:
            return self.optimize_equal_weight(symbols)

    def save_optimization_suggestion(
        self,
        portfolio_id: str,
        suggestion_type: str,
        suggested_weights: Dict[str, float],
    ) -> bool:
        """
        保存配置建議

        Args:
            portfolio_id: 投資組合ID
            suggestion_type: 建議類型
            suggested_weights: 建議權重

        Returns:
            bool: 是否成功
        """
        try:
            # 計算預期指標
            symbols = list(suggested_weights.keys())
            returns_data = self._generate_mock_returns(symbols)
            weights_array = np.array(list(suggested_weights.values()))

            portfolio_returns = (returns_data * weights_array).sum(axis=1)
            expected_return = portfolio_returns.mean() * 252
            expected_risk = portfolio_returns.std() * np.sqrt(252)
            sharpe_ratio = expected_return / expected_risk if expected_risk > 0 else 0

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO portfolio_suggestions
                    (portfolio_id, suggestion_type, suggested_weights, expected_return,
                     expected_risk, sharpe_ratio, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        portfolio_id,
                        suggestion_type,
                        json.dumps(suggested_weights),
                        expected_return,
                        expected_risk,
                        sharpe_ratio,
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()

                return True

        except Exception as e:
            logger.error(f"保存配置建議失敗: {e}")
            return False

    def get_optimization_suggestions(self, portfolio_id: str) -> List[Dict]:
        """
        獲取配置建議

        Args:
            portfolio_id: 投資組合ID

        Returns:
            List[Dict]: 建議列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT suggestion_type, suggested_weights, expected_return,
                           expected_risk, sharpe_ratio, created_at, is_applied
                    FROM portfolio_suggestions
                    WHERE portfolio_id = ?
                    ORDER BY created_at DESC
                """,
                    (portfolio_id,),
                )

                suggestions = []
                for row in cursor.fetchall():
                    suggestions.append(
                        {
                            "suggestion_type": row[0],
                            "suggested_weights": json.loads(row[1]),
                            "expected_return": row[2],
                            "expected_risk": row[3],
                            "sharpe_ratio": row[4],
                            "created_at": row[5],
                            "is_applied": bool(row[6]),
                        }
                    )

                return suggestions

        except Exception as e:
            logger.error(f"獲取配置建議失敗: {e}")
            return []

    def apply_optimization_suggestion(
        self, portfolio_id: str, suggestion_type: str
    ) -> bool:
        """
        應用配置建議

        Args:
            portfolio_id: 投資組合ID
            suggestion_type: 建議類型

        Returns:
            bool: 是否成功
        """
        try:
            # 獲取最新的建議
            suggestions = self.get_optimization_suggestions(portfolio_id)
            target_suggestion = None

            for suggestion in suggestions:
                if suggestion["suggestion_type"] == suggestion_type:
                    target_suggestion = suggestion
                    break

            if not target_suggestion:
                return False

            # 應用權重
            success = self.update_portfolio_weights(
                portfolio_id,
                target_suggestion["suggested_weights"],
                f"應用{suggestion_type}配置建議",
            )

            if success:
                # 標記為已應用
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        UPDATE portfolio_suggestions
                        SET is_applied = 1
                        WHERE portfolio_id = ? AND suggestion_type = ?
                    """,
                        (portfolio_id, suggestion_type),
                    )
                    conn.commit()

            return success

        except Exception as e:
            logger.error(f"應用配置建議失敗: {e}")
            return False

    def compare_portfolios(self, portfolio_ids: List[str]) -> Dict:
        """
        比較多個投資組合

        Args:
            portfolio_ids: 投資組合ID列表

        Returns:
            Dict: 比較結果
        """
        try:
            comparison_data = {
                "portfolios": [],
                "metrics_comparison": {},
                "correlation_matrix": None,
            }

            all_returns = []
            portfolio_names = []

            for portfolio_id in portfolio_ids:
                portfolio = self.get_portfolio(portfolio_id)
                if not portfolio:
                    continue

                # 計算績效指標
                metrics = self.calculate_portfolio_metrics(portfolio)

                portfolio_info = {
                    "id": portfolio.id,
                    "name": portfolio.name,
                    "total_value": portfolio.total_value,
                    "holdings_count": len(portfolio.holdings),
                    "metrics": metrics,
                }

                comparison_data["portfolios"].append(portfolio_info)

                # 生成報酬率用於相關性分析
                returns_data = self._generate_mock_returns(portfolio.get_symbols())
                portfolio_returns = (returns_data * portfolio.get_weights()).sum(axis=1)
                all_returns.append(portfolio_returns)
                portfolio_names.append(portfolio.name)

            # 計算投資組合間相關性
            if len(all_returns) > 1:
                returns_df = pd.DataFrame(all_returns).T
                returns_df.columns = portfolio_names
                comparison_data["correlation_matrix"] = returns_df.corr().to_dict()

            # 整理指標比較
            if comparison_data["portfolios"]:
                metrics_keys = comparison_data["portfolios"][0]["metrics"].keys()
                for metric in metrics_keys:
                    comparison_data["metrics_comparison"][metric] = {
                        p["name"]: p["metrics"][metric]
                        for p in comparison_data["portfolios"]
                    }

            return comparison_data

        except Exception as e:
            logger.error(f"比較投資組合失敗: {e}")
            return {}

    def get_adjustment_history(self, portfolio_id: str, limit: int = 20) -> List[Dict]:
        """
        獲取調整歷史

        Args:
            portfolio_id: 投資組合ID
            limit: 限制數量

        Returns:
            List[Dict]: 調整歷史
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT adjustment_type, old_weights, new_weights, reason,
                           created_at, created_by
                    FROM portfolio_adjustments
                    WHERE portfolio_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (portfolio_id, limit),
                )

                history = []
                for row in cursor.fetchall():
                    history.append(
                        {
                            "adjustment_type": row[0],
                            "old_weights": json.loads(row[1]) if row[1] else {},
                            "new_weights": json.loads(row[2]) if row[2] else {},
                            "reason": row[3],
                            "created_at": row[4],
                            "created_by": row[5],
                        }
                    )

                return history

        except Exception as e:
            logger.error(f"獲取調整歷史失敗: {e}")
            return []

    def export_portfolio_data(
        self, portfolio_id: str, format: str = "json"
    ) -> Optional[bytes]:
        """
        匯出投資組合資料

        Args:
            portfolio_id: 投資組合ID
            format: 匯出格式 ('json', 'csv', 'excel')

        Returns:
            Optional[bytes]: 匯出的檔案內容
        """
        try:
            portfolio = self.get_portfolio(portfolio_id)
            if not portfolio:
                return None

            # 準備匯出資料
            export_data = {
                "portfolio_info": {
                    "id": portfolio.id,
                    "name": portfolio.name,
                    "description": portfolio.description,
                    "created_at": portfolio.created_at.isoformat(),
                    "updated_at": portfolio.updated_at.isoformat(),
                    "total_value": portfolio.total_value,
                    "benchmark": portfolio.benchmark,
                    "risk_free_rate": portfolio.risk_free_rate,
                },
                "holdings": [asdict(holding) for holding in portfolio.holdings],
                "metrics": self.calculate_portfolio_metrics(portfolio),
                "adjustment_history": self.get_adjustment_history(portfolio_id),
            }

            if format == "json":
                return json.dumps(export_data, ensure_ascii=False, indent=2).encode(
                    "utf-8"
                )

            elif format == "csv":
                return self._export_portfolio_to_csv(export_data)

            elif format == "excel":
                return self._export_portfolio_to_excel(export_data)

            else:
                raise ValueError(f"不支援的匯出格式: {format}")

        except Exception as e:
            logger.error(f"匯出投資組合資料失敗: {e}")
            return None

    def _export_portfolio_to_csv(self, data: Dict) -> bytes:
        """匯出為CSV格式"""
        import io

        csv_buffer = io.StringIO()

        # 寫入基本資訊
        csv_buffer.write("# 投資組合資訊\n")
        portfolio_info = data["portfolio_info"]
        for key, value in portfolio_info.items():
            csv_buffer.write(f"{key},{value}\n")
        csv_buffer.write("\n")

        # 寫入持倉資訊
        csv_buffer.write("# 持倉明細\n")
        holdings_df = pd.DataFrame(data["holdings"])
        csv_buffer.write(holdings_df.to_csv(index=False))
        csv_buffer.write("\n")

        # 寫入績效指標
        csv_buffer.write("# 績效指標\n")
        metrics = data["metrics"]
        for key, value in metrics.items():
            csv_buffer.write(f"{key},{value}\n")

        return csv_buffer.getvalue().encode("utf-8")

    def _export_portfolio_to_excel(self, data: Dict) -> bytes:
        """匯出為Excel格式"""
        import io

        excel_buffer = io.BytesIO()

        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            # 基本資訊
            info_df = pd.DataFrame([data["portfolio_info"]]).T
            info_df.columns = ["值"]
            info_df.to_excel(writer, sheet_name="基本資訊")

            # 持倉明細
            holdings_df = pd.DataFrame(data["holdings"])
            holdings_df.to_excel(writer, sheet_name="持倉明細", index=False)

            # 績效指標
            metrics_df = pd.DataFrame([data["metrics"]]).T
            metrics_df.columns = ["值"]
            metrics_df.to_excel(writer, sheet_name="績效指標")

            # 調整歷史
            if data["adjustment_history"]:
                history_df = pd.DataFrame(data["adjustment_history"])
                history_df.to_excel(writer, sheet_name="調整歷史", index=False)

        excel_buffer.seek(0)
        return excel_buffer.getvalue()
