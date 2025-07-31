"""投資組合服務核心模組

此模組提供投資組合管理的核心服務功能，包括：
- 投資組合 CRUD 操作
- 基本資料管理
- 服務初始化和配置

這是投資組合服務的主要入口點。
"""

import json
import uuid
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging
import numpy as np
from dataclasses import dataclass, asdict

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

    def get_holdings_dict(self) -> Dict[str, Dict]:
        """獲取持倉字典"""
        return {
            h.symbol: {
                "name": h.name,
                "quantity": h.quantity,
                "price": h.price,
                "market_value": h.market_value,
                "weight": h.weight,
                "sector": h.sector,
                "exchange": h.exchange,
            }
            for h in self.holdings
        }

    def to_dict(self) -> Dict:
        """轉換為字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "total_value": self.total_value,
            "benchmark": self.benchmark,
            "risk_free_rate": self.risk_free_rate,
            "holdings": [asdict(h) for h in self.holdings],
        }


class PortfolioServiceCore:
    """投資組合服務核心類別"""

    def __init__(self, db_path: str = None):
        """初始化投資組合服務

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
                        FOREIGN KEY (portfolio_id) REFERENCES portfolios (id)
                    )
                """
                )

                conn.commit()
                logger.info("資料庫初始化完成")

        except Exception as e:
            logger.error(f"資料庫初始化失敗: {e}")
            raise

    def create_portfolio(self, portfolio: Portfolio) -> Optional[Portfolio]:
        """創建投資組合

        Args:
            portfolio: 投資組合物件

        Returns:
            創建的投資組合，失敗時返回 None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 插入投資組合基本資訊
                cursor.execute(
                    """
                    INSERT INTO portfolios
                    (id, name, description, created_at, updated_at, total_value,
                     benchmark, risk_free_rate)
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

    def create_portfolio_simple(
        self,
        name: str,
        description: str = "",
        holdings: List[Dict] = None,
        benchmark: str = "^TWII",
        risk_free_rate: float = 0.02,
    ) -> str:
        """創建投資組合（簡化版本）

        Args:
            name: 投資組合名稱
            description: 描述
            holdings: 初始持倉列表
            benchmark: 基準指數
            risk_free_rate: 無風險利率

        Returns:
            投資組合ID
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

        # 創建投資組合物件
        portfolio = Portfolio(
            id=portfolio_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
            total_value=total_value,
            holdings=portfolio_holdings,
            benchmark=benchmark,
            risk_free_rate=risk_free_rate,
        )

        # 保存到資料庫
        result = self.create_portfolio(portfolio)
        return portfolio_id if result else None

    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """獲取投資組合

        Args:
            portfolio_id: 投資組合ID

        Returns:
            投資組合物件，不存在時返回 None
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

                # 獲取持倉資訊
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

    def _record_adjustment(
        self,
        portfolio_id: str,
        adjustment_type: str,
        old_weights: Dict[str, float],
        new_weights: Dict[str, float],
        reason: str,
    ):
        """記錄調整歷史

        Args:
            portfolio_id: 投資組合ID
            adjustment_type: 調整類型
            old_weights: 舊權重
            new_weights: 新權重
            reason: 調整原因
        """
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
