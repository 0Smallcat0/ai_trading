"""
倉位大小控制模組

此模組實現了各種倉位大小計算策略，用於控制交易風險。
"""

import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple

from src.core.logger import logger


class PositionSizingStrategy(ABC):
    """
    倉位大小策略抽象基類
    
    所有倉位大小策略都應繼承此類並實現其抽象方法。
    """
    
    def __init__(self, name: str):
        """
        初始化倉位大小策略
        
        Args:
            name: 策略名稱
        """
        self.name = name
        logger.info(f"初始化倉位大小策略: {name}")
    
    @abstractmethod
    def calculate_position_size(self, portfolio_value: float, **kwargs) -> float:
        """
        計算倉位大小
        
        Args:
            portfolio_value: 投資組合價值
            **kwargs: 其他參數
            
        Returns:
            float: 倉位大小（金額）
        """
        pass
    
    def calculate_shares(self, portfolio_value: float, price: float, **kwargs) -> int:
        """
        計算股數
        
        Args:
            portfolio_value: 投資組合價值
            price: 股票價格
            **kwargs: 其他參數
            
        Returns:
            int: 股數
        """
        # 計算倉位大小（金額）
        position_size = self.calculate_position_size(portfolio_value, **kwargs)
        
        # 計算股數
        shares = int(position_size / price) if price > 0 else 0
        
        return shares


class FixedAmountPositionSizing(PositionSizingStrategy):
    """
    固定金額倉位大小策略
    
    使用固定金額作為倉位大小。
    """
    
    def __init__(self, fixed_amount: float):
        """
        初始化固定金額倉位大小策略
        
        Args:
            fixed_amount: 固定金額
        """
        super().__init__("固定金額倉位")
        self.fixed_amount = fixed_amount
        logger.info(f"初始化固定金額倉位大小策略: {self.fixed_amount}")
    
    def calculate_position_size(self, portfolio_value: float, **kwargs) -> float:
        """
        計算倉位大小
        
        Args:
            portfolio_value: 投資組合價值
            **kwargs: 其他參數
            
        Returns:
            float: 倉位大小（金額）
        """
        # 確保倉位大小不超過投資組合價值
        return min(self.fixed_amount, portfolio_value)


class PercentPositionSizing(PositionSizingStrategy):
    """
    百分比倉位大小策略
    
    使用投資組合價值的百分比作為倉位大小。
    """
    
    def __init__(self, percent: float):
        """
        初始化百分比倉位大小策略
        
        Args:
            percent: 百分比，例如 0.1 表示 10%
        """
        super().__init__("百分比倉位")
        self.percent = min(abs(percent), 1.0)  # 確保百分比不超過 100%
        logger.info(f"初始化百分比倉位大小策略: {self.percent:.2%}")
    
    def calculate_position_size(self, portfolio_value: float, **kwargs) -> float:
        """
        計算倉位大小
        
        Args:
            portfolio_value: 投資組合價值
            **kwargs: 其他參數
            
        Returns:
            float: 倉位大小（金額）
        """
        return portfolio_value * self.percent


class RiskBasedPositionSizing(PositionSizingStrategy):
    """
    基於風險的倉位大小策略
    
    根據風險金額和止損點計算倉位大小。
    """
    
    def __init__(self, risk_percent: float):
        """
        初始化基於風險的倉位大小策略
        
        Args:
            risk_percent: 風險百分比，例如 0.01 表示 1%
        """
        super().__init__("基於風險倉位")
        self.risk_percent = min(abs(risk_percent), 0.1)  # 限制風險百分比不超過 10%
        logger.info(f"初始化基於風險的倉位大小策略: {self.risk_percent:.2%}")
    
    def calculate_position_size(self, portfolio_value: float, **kwargs) -> float:
        """
        計算倉位大小
        
        Args:
            portfolio_value: 投資組合價值
            **kwargs: 其他參數，必須包含 'entry_price' 和 'stop_loss_price'
            
        Returns:
            float: 倉位大小（金額）
        """
        entry_price = kwargs.get('entry_price')
        stop_loss_price = kwargs.get('stop_loss_price')
        
        if entry_price is None or stop_loss_price is None:
            raise ValueError("必須提供 'entry_price' 和 'stop_loss_price' 參數")
        
        # 計算風險金額
        risk_amount = portfolio_value * self.risk_percent
        
        # 計算每股風險
        is_long = kwargs.get('is_long', True)
        if is_long:
            # 多頭倉位
            per_share_risk = entry_price - stop_loss_price
        else:
            # 空頭倉位
            per_share_risk = stop_loss_price - entry_price
        
        # 確保每股風險為正數
        per_share_risk = abs(per_share_risk)
        
        # 計算倉位大小（股數）
        if per_share_risk > 0:
            shares = risk_amount / per_share_risk
            # 計算倉位大小（金額）
            position_size = shares * entry_price
            # 確保倉位大小不超過投資組合價值
            return min(position_size, portfolio_value)
        else:
            logger.warning("每股風險為零，無法計算倉位大小")
            return 0.0


class KellyPositionSizing(PositionSizingStrategy):
    """
    凱利公式倉位大小策略
    
    使用凱利公式計算最優倉位大小。
    """
    
    def __init__(self, win_rate: float, win_loss_ratio: float, fraction: float = 1.0):
        """
        初始化凱利公式倉位大小策略
        
        Args:
            win_rate: 勝率，例如 0.6 表示 60%
            win_loss_ratio: 獲利/虧損比率
            fraction: 凱利比例，用於調整倉位大小，例如 0.5 表示使用半凱利
        """
        super().__init__("凱利公式倉位")
        self.win_rate = min(max(win_rate, 0.0), 1.0)  # 確保勝率在 0-1 之間
        self.win_loss_ratio = max(win_loss_ratio, 0.0)  # 確保獲利/虧損比率為正數
        self.fraction = min(max(fraction, 0.0), 1.0)  # 確保凱利比例在 0-1 之間
        logger.info(f"初始化凱利公式倉位大小策略: 勝率 {self.win_rate:.2%}, 獲利/虧損比率 {self.win_loss_ratio}, 凱利比例 {self.fraction}")
    
    def calculate_position_size(self, portfolio_value: float, **kwargs) -> float:
        """
        計算倉位大小
        
        Args:
            portfolio_value: 投資組合價值
            **kwargs: 其他參數，可以包含 'win_rate' 和 'win_loss_ratio' 來覆蓋初始設置
            
        Returns:
            float: 倉位大小（金額）
        """
        # 獲取勝率和獲利/虧損比率，可以覆蓋初始設置
        win_rate = kwargs.get('win_rate', self.win_rate)
        win_loss_ratio = kwargs.get('win_loss_ratio', self.win_loss_ratio)
        
        # 計算凱利比例
        kelly = win_rate - ((1 - win_rate) / win_loss_ratio) if win_loss_ratio > 0 else 0
        
        # 應用凱利比例調整
        kelly = kelly * self.fraction
        
        # 確保凱利比例在 0-1 之間
        kelly = min(max(kelly, 0.0), 1.0)
        
        # 計算倉位大小
        position_size = portfolio_value * kelly
        
        return position_size


class VolatilityPositionSizing(PositionSizingStrategy):
    """
    波動率倉位大小策略
    
    根據價格波動率調整倉位大小。
    """
    
    def __init__(self, base_percent: float, volatility_factor: float = 1.0):
        """
        初始化波動率倉位大小策略
        
        Args:
            base_percent: 基礎百分比，例如 0.1 表示 10%
            volatility_factor: 波動率因子，用於調整倉位大小
        """
        super().__init__("波動率倉位")
        self.base_percent = min(abs(base_percent), 1.0)  # 確保基礎百分比不超過 100%
        self.volatility_factor = abs(volatility_factor)
        logger.info(f"初始化波動率倉位大小策略: 基礎百分比 {self.base_percent:.2%}, 波動率因子 {self.volatility_factor}")
    
    def calculate_position_size(self, portfolio_value: float, **kwargs) -> float:
        """
        計算倉位大小
        
        Args:
            portfolio_value: 投資組合價值
            **kwargs: 其他參數，必須包含 'volatility' 或 'price_data'
            
        Returns:
            float: 倉位大小（金額）
        """
        # 獲取波動率
        volatility = kwargs.get('volatility')
        if volatility is None:
            price_data = kwargs.get('price_data')
            if price_data is None:
                raise ValueError("必須提供 'volatility' 或 'price_data' 參數")
            
            # 計算波動率
            volatility = self._calculate_volatility(price_data)
        
        # 計算波動率調整因子
        volatility_adjustment = 1.0 / (volatility * self.volatility_factor) if volatility > 0 else 1.0
        
        # 計算倉位大小
        position_size = portfolio_value * self.base_percent * volatility_adjustment
        
        # 確保倉位大小不超過投資組合價值
        return min(position_size, portfolio_value)
    
    def _calculate_volatility(self, price_data: pd.DataFrame) -> float:
        """
        計算波動率
        
        Args:
            price_data: 價格資料，必須包含 'close' 欄位
            
        Returns:
            float: 波動率
        """
        # 確保價格資料包含必要欄位
        if 'close' not in price_data.columns:
            raise ValueError("價格資料必須包含 'close' 欄位")
        
        # 計算收益率
        returns = price_data['close'].pct_change().dropna()
        
        # 計算波動率
        volatility = returns.std()
        
        return volatility


class OptimalFPositionSizing(PositionSizingStrategy):
    """
    最優 f 倉位大小策略
    
    使用最優 f 值計算倉位大小。
    """
    
    def __init__(self, optimal_f: float):
        """
        初始化最優 f 倉位大小策略
        
        Args:
            optimal_f: 最優 f 值，例如 0.2 表示 20%
        """
        super().__init__("最優f倉位")
        self.optimal_f = min(abs(optimal_f), 1.0)  # 確保最優 f 值不超過 100%
        logger.info(f"初始化最優 f 倉位大小策略: {self.optimal_f:.2%}")
    
    def calculate_position_size(self, portfolio_value: float, **kwargs) -> float:
        """
        計算倉位大小
        
        Args:
            portfolio_value: 投資組合價值
            **kwargs: 其他參數
            
        Returns:
            float: 倉位大小（金額）
        """
        # 計算倉位大小
        position_size = portfolio_value * self.optimal_f
        
        return position_size


class PyramidingPositionSizing(PositionSizingStrategy):
    """
    金字塔倉位大小策略
    
    使用金字塔方式逐步增加倉位。
    """
    
    def __init__(self, initial_percent: float, reduction_factor: float = 0.5, max_levels: int = 3):
        """
        初始化金字塔倉位大小策略
        
        Args:
            initial_percent: 初始百分比，例如 0.1 表示 10%
            reduction_factor: 縮減因子，例如 0.5 表示每次減半
            max_levels: 最大層級數
        """
        super().__init__("金字塔倉位")
        self.initial_percent = min(abs(initial_percent), 1.0)  # 確保初始百分比不超過 100%
        self.reduction_factor = min(max(abs(reduction_factor), 0.1), 0.9)  # 確保縮減因子在 0.1-0.9 之間
        self.max_levels = max(int(max_levels), 1)  # 確保最大層級數至少為 1
        logger.info(f"初始化金字塔倉位大小策略: 初始百分比 {self.initial_percent:.2%}, 縮減因子 {self.reduction_factor}, 最大層級數 {self.max_levels}")
    
    def calculate_position_size(self, portfolio_value: float, **kwargs) -> float:
        """
        計算倉位大小
        
        Args:
            portfolio_value: 投資組合價值
            **kwargs: 其他參數，必須包含 'level'
            
        Returns:
            float: 倉位大小（金額）
        """
        # 獲取當前層級
        level = kwargs.get('level', 1)
        
        # 確保層級在有效範圍內
        level = min(max(int(level), 1), self.max_levels)
        
        # 計算當前層級的百分比
        current_percent = self.initial_percent * (self.reduction_factor ** (level - 1))
        
        # 計算倉位大小
        position_size = portfolio_value * current_percent
        
        return position_size
