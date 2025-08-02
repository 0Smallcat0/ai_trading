"""
回測配置模組

此模組包含回測系統的配置類別和相關功能。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class BacktestConfig:
    """
    回測配置類別

    包含回測執行所需的所有配置參數。

    Attributes:
        strategy_id: 策略ID
        strategy_name: 策略名稱
        symbols: 股票代碼列表
        start_date: 開始日期
        end_date: 結束日期
        initial_capital: 初始資金
        commission: 手續費率
        slippage: 滑價
        tax: 稅率
        benchmark: 基準指標
        strategy_params: 策略參數
    """

    strategy_id: str
    strategy_name: str
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    initial_capital: float
    commission: float = 0.001425
    slippage: float = 0.001
    tax: float = 0.003
    benchmark: Optional[str] = None
    strategy_params: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化後處理"""
        if self.strategy_params is None:
            self.strategy_params = {}

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式

        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "symbols": self.symbols,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "initial_capital": self.initial_capital,
            "commission": self.commission,
            "slippage": self.slippage,
            "tax": self.tax,
            "benchmark": self.benchmark,
            "strategy_params": self.strategy_params,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacktestConfig":
        """
        從字典創建配置對象

        Args:
            data: 配置字典

        Returns:
            BacktestConfig: 配置對象
        """
        # 處理日期字段
        start_date = None
        if data.get("start_date"):
            start_date = datetime.fromisoformat(data["start_date"])

        end_date = None
        if data.get("end_date"):
            end_date = datetime.fromisoformat(data["end_date"])

        return cls(
            strategy_id=data["strategy_id"],
            strategy_name=data["strategy_name"],
            symbols=data["symbols"],
            start_date=start_date,
            end_date=end_date,
            initial_capital=data["initial_capital"],
            commission=data.get("commission", 0.001425),
            slippage=data.get("slippage", 0.001),
            tax=data.get("tax", 0.003),
            benchmark=data.get("benchmark"),
            strategy_params=data.get("strategy_params", {}),
        )

    def validate(self) -> tuple[bool, str]:
        """
        驗證配置有效性

        Returns:
            tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        if not self.strategy_id:
            return False, "策略ID不能為空"

        if not self.strategy_name:
            return False, "策略名稱不能為空"

        if not self.symbols:
            return False, "股票代碼列表不能為空"

        if not self.start_date:
            return False, "開始日期不能為空"

        if not self.end_date:
            return False, "結束日期不能為空"

        if self.start_date >= self.end_date:
            return False, "開始日期必須早於結束日期"

        if self.initial_capital <= 0:
            return False, "初始資金必須大於0"

        if self.commission < 0:
            return False, "手續費率不能為負數"

        if self.slippage < 0:
            return False, "滑價不能為負數"

        if self.tax < 0:
            return False, "稅率不能為負數"

        return True, ""


def create_default_config() -> BacktestConfig:
    """
    創建默認配置

    Returns:
        BacktestConfig: 默認配置對象
    """
    return BacktestConfig(
        strategy_id="default_strategy",
        strategy_name="默認策略",
        symbols=["2330.TW"],
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        initial_capital=100000.0,
        commission=0.001425,
        slippage=0.001,
        tax=0.003,
    )


def validate_symbols(symbols: List[str]) -> tuple[bool, str]:
    """
    驗證股票代碼格式

    Args:
        symbols: 股票代碼列表

    Returns:
        tuple[bool, str]: (是否有效, 錯誤訊息)
    """
    if not symbols:
        return False, "股票代碼列表不能為空"

    for symbol in symbols:
        if not symbol or not isinstance(symbol, str):
            return False, f"無效的股票代碼: {symbol}"

        # 基本格式檢查
        if len(symbol) < 4:
            return False, f"股票代碼長度不足: {symbol}"

    return True, ""


def validate_date_range(start_date: datetime, end_date: datetime) -> tuple[bool, str]:
    """
    驗證日期範圍

    Args:
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        tuple[bool, str]: (是否有效, 錯誤訊息)
    """
    if not start_date or not end_date:
        return False, "開始日期和結束日期不能為空"

    if start_date >= end_date:
        return False, "開始日期必須早於結束日期"

    # 檢查日期範圍是否合理（不超過10年）
    max_days = 365 * 10
    if (end_date - start_date).days > max_days:
        return False, f"日期範圍過長，最多支援{max_days}天"

    return True, ""
