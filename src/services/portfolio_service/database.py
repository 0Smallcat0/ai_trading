"""投資組合服務資料庫操作模組

此模組提供投資組合服務的資料庫操作功能，包括：
- 投資組合 CRUD 操作
- 持倉資料管理
- 調整歷史記錄
- 資料匯出和匯入

這個模組專門處理資料庫相關的操作，將資料庫邏輯從核心服務中分離。
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging


from .core import PortfolioServiceCore, Portfolio, PortfolioHolding

# 設定日誌
logger = logging.getLogger(__name__)


class PortfolioDatabaseService:
    """投資組合資料庫服務"""

    def __init__(self, core_service: PortfolioServiceCore):
        """初始化資料庫服務

        Args:
            core_service: 核心服務實例
        """
        self.core = core_service
        self.db_path = core_service.db_path

    def get_portfolio_list(self, limit: int = 50) -> List[Dict]:
        """獲取投資組合列表

        Args:
            limit: 限制數量

        Returns:
            投資組合列表
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

    def update_portfolio(
        self,
        portfolio_id: str,
        name: str = None,
        description: str = None,
        benchmark: str = None,
        risk_free_rate: float = None,
    ) -> bool:
        """更新投資組合基本資訊

        Args:
            portfolio_id: 投資組合ID
            name: 新名稱
            description: 新描述
            benchmark: 新基準指數
            risk_free_rate: 新無風險利率

        Returns:
            是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 構建更新語句
                update_fields = []
                update_values = []

                if name is not None:
                    update_fields.append("name = ?")
                    update_values.append(name)

                if description is not None:
                    update_fields.append("description = ?")
                    update_values.append(description)

                if benchmark is not None:
                    update_fields.append("benchmark = ?")
                    update_values.append(benchmark)

                if risk_free_rate is not None:
                    update_fields.append("risk_free_rate = ?")
                    update_values.append(risk_free_rate)

                if not update_fields:
                    return True  # 沒有需要更新的欄位

                # 添加更新時間
                update_fields.append("updated_at = ?")
                update_values.append(datetime.now().isoformat())

                # 添加 WHERE 條件
                update_values.append(portfolio_id)

                sql = f"""
                    UPDATE portfolios
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """

                cursor.execute(sql, update_values)
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"投資組合已更新: {portfolio_id}")
                    return True
                else:
                    logger.warning(f"投資組合不存在: {portfolio_id}")
                    return False

        except Exception as e:
            logger.error(f"更新投資組合失敗: {e}")
            return False

    def delete_portfolio(self, portfolio_id: str) -> bool:
        """刪除投資組合（軟刪除）

        Args:
            portfolio_id: 投資組合ID

        Returns:
            是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 軟刪除：設定 is_active = 0
                cursor.execute(
                    """
                    UPDATE portfolios
                    SET is_active = 0, updated_at = ?
                    WHERE id = ?
                """,
                    (datetime.now().isoformat(), portfolio_id),
                )

                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"投資組合已刪除: {portfolio_id}")
                    return True
                else:
                    logger.warning(f"投資組合不存在: {portfolio_id}")
                    return False

        except Exception as e:
            logger.error(f"刪除投資組合失敗: {e}")
            return False

    def update_holdings(
        self,
        portfolio_id: str,
        holdings: List[PortfolioHolding]
    ) -> bool:
        """更新投資組合持倉

        Args:
            portfolio_id: 投資組合ID
            holdings: 新的持倉列表

        Returns:
            是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 刪除舊的持倉記錄
                cursor.execute(
                    "DELETE FROM portfolio_holdings WHERE portfolio_id = ?",
                    (portfolio_id,)
                )

                # 插入新的持倉記錄
                for holding in holdings:
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

                # 更新投資組合總價值和更新時間
                total_value = sum(h.market_value for h in holdings)
                cursor.execute(
                    """
                    UPDATE portfolios
                    SET total_value = ?, updated_at = ?
                    WHERE id = ?
                """,
                    (total_value, datetime.now().isoformat(), portfolio_id),
                )

                conn.commit()
                logger.info(f"投資組合持倉已更新: {portfolio_id}")
                return True

        except Exception as e:
            logger.error(f"更新持倉失敗: {e}")
            return False

    def get_adjustment_history(
        self,
        portfolio_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """獲取調整歷史

        Args:
            portfolio_id: 投資組合ID
            limit: 限制數量

        Returns:
            調整歷史列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT adjustment_type, old_weights, new_weights, reason, created_at
                    FROM portfolio_adjustments
                    WHERE portfolio_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (portfolio_id, limit),
                )

                history = []
                for row in cursor.fetchall():
                    try:
                        old_weights = json.loads(row[1]) if row[1] else {}
                        new_weights = json.loads(row[2]) if row[2] else {}
                    except json.JSONDecodeError:
                        old_weights = {}
                        new_weights = {}

                    history.append(
                        {
                            "adjustment_type": row[0],
                            "old_weights": old_weights,
                            "new_weights": new_weights,
                            "reason": row[3],
                            "created_at": row[4],
                        }
                    )

                return history

        except Exception as e:
            logger.error(f"獲取調整歷史失敗: {e}")
            return []

    def export_portfolio_data(
        self,
        portfolio_id: str,
        include_history: bool = True
    ) -> Dict[str, Any]:
        """匯出投資組合資料

        Args:
            portfolio_id: 投資組合ID
            include_history: 是否包含歷史記錄

        Returns:
            匯出的資料
        """
        try:
            # 獲取投資組合基本資訊
            portfolio = self.core.get_portfolio(portfolio_id)
            if not portfolio:
                return {"error": f"投資組合不存在: {portfolio_id}"}

            export_data = {
                "portfolio_info": portfolio.to_dict(),
                "holdings": [
                    {
                        "symbol": h.symbol,
                        "name": h.name,
                        "quantity": h.quantity,
                        "price": h.price,
                        "market_value": h.market_value,
                        "weight": h.weight,
                        "sector": h.sector,
                        "exchange": h.exchange,
                    }
                    for h in portfolio.holdings
                ],
                "export_date": datetime.now().isoformat(),
            }

            # 如果需要包含歷史記錄
            if include_history:
                export_data["adjustment_history"] = self.get_adjustment_history(portfolio_id)

            return export_data

        except Exception as e:
            logger.error(f"匯出投資組合資料失敗: {e}")
            return {"error": f"匯出失敗: {e}"}

    def import_portfolio_data(
        self,
        import_data: Dict[str, Any],
        overwrite: bool = False
    ) -> Optional[str]:
        """匯入投資組合資料

        Args:
            import_data: 匯入的資料
            overwrite: 是否覆蓋現有資料

        Returns:
            匯入的投資組合ID，失敗時返回 None
        """
        try:
            portfolio_info = import_data.get("portfolio_info", {})
            holdings_data = import_data.get("holdings", [])

            if not portfolio_info or not holdings_data:
                logger.error("匯入資料格式不正確")
                return None

            # 檢查投資組合是否已存在
            existing_portfolio = self.core.get_portfolio(portfolio_info["id"])
            if existing_portfolio and not overwrite:
                logger.error(f"投資組合已存在且不允許覆蓋: {portfolio_info['id']}")
                return None

            # 創建持倉物件
            holdings = []
            for holding_data in holdings_data:
                holding = PortfolioHolding(
                    symbol=holding_data["symbol"],
                    name=holding_data["name"],
                    quantity=holding_data["quantity"],
                    price=holding_data["price"],
                    market_value=holding_data["market_value"],
                    weight=holding_data["weight"],
                    sector=holding_data.get("sector", ""),
                    exchange=holding_data.get("exchange", ""),
                )
                holdings.append(holding)

            # 創建投資組合物件
            portfolio = Portfolio(
                id=portfolio_info["id"],
                name=portfolio_info["name"],
                description=portfolio_info["description"],
                created_at=datetime.fromisoformat(portfolio_info["created_at"]),
                updated_at=datetime.now(),  # 使用當前時間作為更新時間
                total_value=portfolio_info["total_value"],
                holdings=holdings,
                benchmark=portfolio_info.get("benchmark", "^TWII"),
                risk_free_rate=portfolio_info.get("risk_free_rate", 0.02),
            )

            # 如果是覆蓋模式，先刪除現有資料
            if existing_portfolio and overwrite:
                self.delete_portfolio(portfolio_info["id"])

            # 創建投資組合
            result = self.core.create_portfolio(portfolio)
            if result:
                logger.info(f"投資組合匯入成功: {portfolio_info['id']}")
                return portfolio_info["id"]
            else:
                logger.error("投資組合匯入失敗")
                return None

        except Exception as e:
            logger.error(f"匯入投資組合資料失敗: {e}")
            return None

    def get_portfolio_statistics(self) -> Dict[str, Any]:
        """獲取投資組合統計資訊

        Returns:
            統計資訊字典
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 總投資組合數量
                cursor.execute("SELECT COUNT(*) FROM portfolios WHERE is_active = 1")
                total_portfolios = cursor.fetchone()[0]

                # 總市值
                cursor.execute("SELECT SUM(total_value) FROM portfolios WHERE is_active = 1")
                total_value = cursor.fetchone()[0] or 0

                # 平均市值
                avg_value = total_value / total_portfolios if total_portfolios > 0 else 0

                # 最近創建的投資組合
                cursor.execute(
                    """
                    SELECT name, created_at
                    FROM portfolios
                    WHERE is_active = 1
                    ORDER BY created_at DESC
                    LIMIT 5
                """
                )
                recent_portfolios = [
                    {"name": row[0], "created_at": row[1]}
                    for row in cursor.fetchall()
                ]

                return {
                    "total_portfolios": total_portfolios,
                    "total_value": total_value,
                    "average_value": avg_value,
                    "recent_portfolios": recent_portfolios,
                    "statistics_date": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"獲取統計資訊失敗: {e}")
            return {}
