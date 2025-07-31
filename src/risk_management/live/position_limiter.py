"""
部位大小限制器

此模組提供部位大小限制功能，包括：
- 單一股票持倉限制
- 總體部位限制
- 行業集中度限制
- 相關性風險控制
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from src.execution.broker_base import BrokerBase, Order

# 設定日誌
logger = logging.getLogger("risk.live.position_limiter")


class LimitType(Enum):
    """限制類型枚舉"""
    SINGLE_POSITION = "single_position"  # 單一持倉限制
    TOTAL_EXPOSURE = "total_exposure"  # 總體曝險限制
    SECTOR_CONCENTRATION = "sector_concentration"  # 行業集中度限制
    CORRELATION_RISK = "correlation_risk"  # 相關性風險限制


class PositionLimiter:
    """部位大小限制器"""
    
    def __init__(self, broker: BrokerBase):
        """
        初始化部位大小限制器
        
        Args:
            broker (BrokerBase): 券商適配器
        """
        self.broker = broker
        
        # 限制參數
        self.limit_params = {
            "max_single_position_percent": 0.1,  # 單一持倉最大比例 10%
            "max_single_position_value": 500000,  # 單一持倉最大價值
            "max_total_exposure_percent": 0.8,  # 總體曝險最大比例 80%
            "max_sector_concentration": 0.3,  # 行業集中度最大比例 30%
            "max_correlation_exposure": 0.5,  # 相關性曝險最大比例 50%
            "correlation_threshold": 0.7,  # 相關性閾值
        }
        
        # 行業分類 (簡化版本)
        self.sector_mapping = {
            # 台股
            "2330": "科技",  # 台積電
            "2317": "科技",  # 鴻海
            "2454": "科技",  # 聯發科
            "2881": "金融",  # 富邦金
            "2882": "金融",  # 國泰金
            "2412": "科技",  # 中華電
            "1301": "傳產",  # 台塑
            "1303": "傳產",  # 南亞
            "2002": "傳產",  # 中鋼
            # 美股
            "AAPL": "科技",
            "MSFT": "科技",
            "GOOGL": "科技",
            "AMZN": "科技",
            "TSLA": "汽車",
            "JPM": "金融",
            "BAC": "金融",
            "XOM": "能源",
            "JNJ": "醫療",
            "PG": "消費",
        }
        
        # 相關性矩陣 (簡化版本)
        self.correlation_matrix = {
            ("2330", "2454"): 0.8,  # 台積電與聯發科
            ("2881", "2882"): 0.9,  # 富邦金與國泰金
            ("AAPL", "MSFT"): 0.7,  # 蘋果與微軟
            ("GOOGL", "AMZN"): 0.6,  # Google 與亞馬遜
        }
        
        # 限制檢查記錄
        self.limit_checks: List[Dict[str, Any]] = []
        self.max_checks_size = 1000
        
        # 回調函數
        self.on_limit_exceeded: Optional[Callable] = None
        self.on_limit_warning: Optional[Callable] = None
    
    def check_order_limits(self, order: Order) -> Dict[str, Any]:
        """
        檢查訂單是否超過限制
        
        Args:
            order (Order): 訂單物件
            
        Returns:
            Dict[str, Any]: 檢查結果
        """
        try:
            check_result = {
                "allowed": True,
                "warnings": [],
                "violations": [],
                "limits_checked": [],
            }
            
            # 獲取當前帳戶和持倉資訊
            account_info = self.broker.get_account_info()
            positions = self.broker.get_positions()
            
            if not account_info:
                return {
                    "allowed": False,
                    "error": "無法獲取帳戶資訊",
                }
            
            # 計算訂單價值
            order_value = 0
            if order.price and order.quantity:
                order_value = order.price * order.quantity
            
            # 檢查單一持倉限制
            single_position_result = self._check_single_position_limit(
                order, account_info, positions, order_value
            )
            check_result["limits_checked"].append(single_position_result)
            
            if not single_position_result["passed"]:
                check_result["allowed"] = False
                check_result["violations"].extend(single_position_result["violations"])
            
            check_result["warnings"].extend(single_position_result["warnings"])
            
            # 檢查總體曝險限制
            total_exposure_result = self._check_total_exposure_limit(
                order, account_info, positions, order_value
            )
            check_result["limits_checked"].append(total_exposure_result)
            
            if not total_exposure_result["passed"]:
                check_result["allowed"] = False
                check_result["violations"].extend(total_exposure_result["violations"])
            
            check_result["warnings"].extend(total_exposure_result["warnings"])
            
            # 檢查行業集中度限制
            sector_result = self._check_sector_concentration_limit(
                order, account_info, positions, order_value
            )
            check_result["limits_checked"].append(sector_result)
            
            if not sector_result["passed"]:
                check_result["allowed"] = False
                check_result["violations"].extend(sector_result["violations"])
            
            check_result["warnings"].extend(sector_result["warnings"])
            
            # 檢查相關性風險限制
            correlation_result = self._check_correlation_risk_limit(
                order, account_info, positions, order_value
            )
            check_result["limits_checked"].append(correlation_result)
            
            if not correlation_result["passed"]:
                check_result["allowed"] = False
                check_result["violations"].extend(correlation_result["violations"])
            
            check_result["warnings"].extend(correlation_result["warnings"])
            
            # 記錄檢查結果
            self._record_limit_check(order, check_result)
            
            # 調用回調函數
            if not check_result["allowed"] and self.on_limit_exceeded:
                self.on_limit_exceeded(order, check_result)
            elif check_result["warnings"] and self.on_limit_warning:
                self.on_limit_warning(order, check_result)
            
            return check_result
            
        except Exception as e:
            logger.exception(f"檢查訂單限制失敗: {e}")
            return {
                "allowed": False,
                "error": f"檢查訂單限制失敗: {e}",
            }
    
    def get_position_summary(self) -> Dict[str, Any]:
        """
        獲取持倉摘要
        
        Returns:
            Dict[str, Any]: 持倉摘要
        """
        try:
            account_info = self.broker.get_account_info()
            positions = self.broker.get_positions()
            
            if not account_info or not positions:
                return {
                    "total_value": 0,
                    "position_count": 0,
                    "sector_breakdown": {},
                    "largest_position": {},
                    "risk_metrics": {},
                }
            
            total_value = account_info.get("total_value", 0)
            
            # 計算持倉統計
            position_values = {}
            sector_values = {}
            
            for symbol, position in positions.items():
                market_value = position.get("market_value", 0)
                position_values[symbol] = market_value
                
                # 行業分類
                sector = self.sector_mapping.get(symbol, "其他")
                sector_values[sector] = sector_values.get(sector, 0) + market_value
            
            # 找出最大持倉
            largest_position = {}
            if position_values:
                largest_symbol = max(position_values, key=position_values.get)
                largest_value = position_values[largest_symbol]
                largest_position = {
                    "symbol": largest_symbol,
                    "value": largest_value,
                    "percentage": (largest_value / total_value * 100) if total_value > 0 else 0,
                }
            
            # 計算行業分布
            sector_breakdown = {}
            for sector, value in sector_values.items():
                sector_breakdown[sector] = {
                    "value": value,
                    "percentage": (value / total_value * 100) if total_value > 0 else 0,
                }
            
            # 計算風險指標
            risk_metrics = self._calculate_risk_metrics(position_values, total_value)
            
            return {
                "total_value": total_value,
                "position_count": len(positions),
                "sector_breakdown": sector_breakdown,
                "largest_position": largest_position,
                "risk_metrics": risk_metrics,
            }
            
        except Exception as e:
            logger.exception(f"獲取持倉摘要失敗: {e}")
            return {
                "error": str(e),
                "total_value": 0,
                "position_count": 0,
            }
    
    def update_limit_params(self, **kwargs) -> bool:
        """
        更新限制參數
        
        Args:
            **kwargs: 參數
            
        Returns:
            bool: 是否更新成功
        """
        try:
            for key, value in kwargs.items():
                if key in self.limit_params:
                    self.limit_params[key] = value
                    logger.info(f"已更新部位限制參數 {key}: {value}")
            return True
        except Exception as e:
            logger.exception(f"更新部位限制參數失敗: {e}")
            return False
    
    def update_sector_mapping(self, symbol: str, sector: str) -> bool:
        """
        更新行業分類
        
        Args:
            symbol (str): 股票代號
            sector (str): 行業
            
        Returns:
            bool: 是否更新成功
        """
        try:
            self.sector_mapping[symbol] = sector
            logger.info(f"已更新 {symbol} 的行業分類: {sector}")
            return True
        except Exception as e:
            logger.exception(f"更新行業分類失敗: {e}")
            return False
    
    def get_limit_check_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        獲取限制檢查歷史
        
        Args:
            limit (int): 限制數量
            
        Returns:
            List[Dict[str, Any]]: 檢查歷史
        """
        return self.limit_checks[-limit:] if self.limit_checks else []

    def _check_single_position_limit(self, order: Order, account_info: Dict[str, Any],
                                   positions: Dict[str, Any], order_value: float) -> Dict[str, Any]:
        """檢查單一持倉限制"""
        try:
            result = {
                "limit_type": LimitType.SINGLE_POSITION.value,
                "passed": True,
                "warnings": [],
                "violations": [],
            }

            total_value = account_info.get("total_value", 0)
            if total_value <= 0:
                return result

            # 計算執行後的持倉價值
            current_position = positions.get(order.stock_id, {})
            current_value = current_position.get("market_value", 0)

            if order.action.lower() == "buy":
                new_value = current_value + order_value
            else:
                new_value = max(0, current_value - order_value)

            # 檢查比例限制
            new_percentage = new_value / total_value
            max_percentage = self.limit_params["max_single_position_percent"]

            if new_percentage > max_percentage:
                result["passed"] = False
                result["violations"].append(
                    f"單一持倉比例 {new_percentage:.1%} 超過限制 {max_percentage:.1%}"
                )
            elif new_percentage > max_percentage * 0.8:  # 80% 警告
                result["warnings"].append(
                    f"單一持倉比例 {new_percentage:.1%} 接近限制 {max_percentage:.1%}"
                )

            # 檢查價值限制
            max_value = self.limit_params["max_single_position_value"]

            if new_value > max_value:
                result["passed"] = False
                result["violations"].append(
                    f"單一持倉價值 {new_value:,.0f} 超過限制 {max_value:,.0f}"
                )
            elif new_value > max_value * 0.8:  # 80% 警告
                result["warnings"].append(
                    f"單一持倉價值 {new_value:,.0f} 接近限制 {max_value:,.0f}"
                )

            return result

        except Exception as e:
            logger.exception(f"檢查單一持倉限制失敗: {e}")
            return {
                "limit_type": LimitType.SINGLE_POSITION.value,
                "passed": False,
                "error": str(e),
            }

    def _check_total_exposure_limit(self, order: Order, account_info: Dict[str, Any],
                                  positions: Dict[str, Any], order_value: float) -> Dict[str, Any]:
        """檢查總體曝險限制"""
        try:
            result = {
                "limit_type": LimitType.TOTAL_EXPOSURE.value,
                "passed": True,
                "warnings": [],
                "violations": [],
            }

            total_value = account_info.get("total_value", 0)
            if total_value <= 0:
                return result

            # 計算當前總曝險
            current_exposure = sum(pos.get("market_value", 0) for pos in positions.values())

            # 計算執行後的總曝險
            if order.action.lower() == "buy":
                new_exposure = current_exposure + order_value
            else:
                new_exposure = max(0, current_exposure - order_value)

            # 檢查曝險限制
            new_exposure_percentage = new_exposure / total_value
            max_exposure = self.limit_params["max_total_exposure_percent"]

            if new_exposure_percentage > max_exposure:
                result["passed"] = False
                result["violations"].append(
                    f"總體曝險比例 {new_exposure_percentage:.1%} 超過限制 {max_exposure:.1%}"
                )
            elif new_exposure_percentage > max_exposure * 0.9:  # 90% 警告
                result["warnings"].append(
                    f"總體曝險比例 {new_exposure_percentage:.1%} 接近限制 {max_exposure:.1%}"
                )

            return result

        except Exception as e:
            logger.exception(f"檢查總體曝險限制失敗: {e}")
            return {
                "limit_type": LimitType.TOTAL_EXPOSURE.value,
                "passed": False,
                "error": str(e),
            }

    def _check_sector_concentration_limit(self, order: Order, account_info: Dict[str, Any],
                                        positions: Dict[str, Any], order_value: float) -> Dict[str, Any]:
        """檢查行業集中度限制"""
        try:
            result = {
                "limit_type": LimitType.SECTOR_CONCENTRATION.value,
                "passed": True,
                "warnings": [],
                "violations": [],
            }

            total_value = account_info.get("total_value", 0)
            if total_value <= 0:
                return result

            # 獲取訂單股票的行業
            order_sector = self.sector_mapping.get(order.stock_id, "其他")

            # 計算各行業當前價值
            sector_values = {}
            for symbol, position in positions.items():
                sector = self.sector_mapping.get(symbol, "其他")
                market_value = position.get("market_value", 0)
                sector_values[sector] = sector_values.get(sector, 0) + market_value

            # 計算執行後的行業價值
            current_sector_value = sector_values.get(order_sector, 0)

            if order.action.lower() == "buy":
                new_sector_value = current_sector_value + order_value
            else:
                new_sector_value = max(0, current_sector_value - order_value)

            # 檢查行業集中度限制
            new_sector_percentage = new_sector_value / total_value
            max_concentration = self.limit_params["max_sector_concentration"]

            if new_sector_percentage > max_concentration:
                result["passed"] = False
                result["violations"].append(
                    f"{order_sector} 行業集中度 {new_sector_percentage:.1%} 超過限制 {max_concentration:.1%}"
                )
            elif new_sector_percentage > max_concentration * 0.8:  # 80% 警告
                result["warnings"].append(
                    f"{order_sector} 行業集中度 {new_sector_percentage:.1%} 接近限制 {max_concentration:.1%}"
                )

            return result

        except Exception as e:
            logger.exception(f"檢查行業集中度限制失敗: {e}")
            return {
                "limit_type": LimitType.SECTOR_CONCENTRATION.value,
                "passed": False,
                "error": str(e),
            }

    def _check_correlation_risk_limit(self, order: Order, account_info: Dict[str, Any],
                                    positions: Dict[str, Any], order_value: float) -> Dict[str, Any]:
        """檢查相關性風險限制"""
        try:
            result = {
                "limit_type": LimitType.CORRELATION_RISK.value,
                "passed": True,
                "warnings": [],
                "violations": [],
            }

            total_value = account_info.get("total_value", 0)
            if total_value <= 0:
                return result

            # 找出與訂單股票相關的持倉
            correlated_symbols = []
            for (symbol1, symbol2), correlation in self.correlation_matrix.items():
                if correlation >= self.limit_params["correlation_threshold"]:
                    if symbol1 == order.stock_id and symbol2 in positions:
                        correlated_symbols.append(symbol2)
                    elif symbol2 == order.stock_id and symbol1 in positions:
                        correlated_symbols.append(symbol1)

            if not correlated_symbols:
                return result

            # 計算相關持倉的總價值
            correlated_value = sum(
                positions[symbol].get("market_value", 0)
                for symbol in correlated_symbols
            )

            # 計算執行後的相關曝險
            current_order_value = positions.get(order.stock_id, {}).get("market_value", 0)

            if order.action.lower() == "buy":
                new_order_value = current_order_value + order_value
            else:
                new_order_value = max(0, current_order_value - order_value)

            total_correlated_exposure = correlated_value + new_order_value

            # 檢查相關性曝險限制
            correlation_percentage = total_correlated_exposure / total_value
            max_correlation = self.limit_params["max_correlation_exposure"]

            if correlation_percentage > max_correlation:
                result["passed"] = False
                result["violations"].append(
                    f"相關性曝險 {correlation_percentage:.1%} 超過限制 {max_correlation:.1%}"
                )
            elif correlation_percentage > max_correlation * 0.8:  # 80% 警告
                result["warnings"].append(
                    f"相關性曝險 {correlation_percentage:.1%} 接近限制 {max_correlation:.1%}"
                )

            return result

        except Exception as e:
            logger.exception(f"檢查相關性風險限制失敗: {e}")
            return {
                "limit_type": LimitType.CORRELATION_RISK.value,
                "passed": False,
                "error": str(e),
            }

    def _calculate_risk_metrics(self, position_values: Dict[str, float],
                              total_value: float) -> Dict[str, Any]:
        """計算風險指標"""
        try:
            if not position_values or total_value <= 0:
                return {
                    "concentration_ratio": 0,
                    "herfindahl_index": 0,
                    "max_position_weight": 0,
                    "position_count": 0,
                }

            # 計算持倉權重
            weights = [value / total_value for value in position_values.values()]

            # 計算集中度比率 (前5大持倉比例)
            sorted_weights = sorted(weights, reverse=True)
            concentration_ratio = sum(sorted_weights[:5])

            # 計算 Herfindahl 指數 (集中度指標)
            herfindahl_index = sum(w ** 2 for w in weights)

            # 最大持倉權重
            max_position_weight = max(weights) if weights else 0

            return {
                "concentration_ratio": concentration_ratio,
                "herfindahl_index": herfindahl_index,
                "max_position_weight": max_position_weight,
                "position_count": len(position_values),
            }

        except Exception as e:
            logger.exception(f"計算風險指標失敗: {e}")
            return {
                "concentration_ratio": 0,
                "herfindahl_index": 0,
                "max_position_weight": 0,
                "position_count": 0,
            }

    def _record_limit_check(self, order: Order, check_result: Dict[str, Any]):
        """記錄限制檢查"""
        try:
            record = {
                "timestamp": datetime.now(),
                "symbol": order.stock_id,
                "action": order.action,
                "quantity": order.quantity,
                "price": order.price,
                "allowed": check_result["allowed"],
                "warnings_count": len(check_result["warnings"]),
                "violations_count": len(check_result["violations"]),
                "limits_checked": [limit["limit_type"] for limit in check_result["limits_checked"]],
            }

            self.limit_checks.append(record)

            # 保持記錄在合理範圍內
            if len(self.limit_checks) > self.max_checks_size:
                self.limit_checks = self.limit_checks[-self.max_checks_size//2:]

        except Exception as e:
            logger.exception(f"記錄限制檢查失敗: {e}")
