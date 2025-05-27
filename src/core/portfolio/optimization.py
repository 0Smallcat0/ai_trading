"""投資組合最佳化模組

此模組包含各種投資組合最佳化演算法和相關函數。

主要功能：
- 均值方差最佳化
- 風險平價最佳化
- 最大夏普比率最佳化
- 最小方差最佳化
- 效率前緣計算
"""

import logging
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd

from .utils import SCIPY_AVAILABLE, PYPFOPT_AVAILABLE, sco, EfficientFrontier, expected_returns, risk_models
from .base import DependencyError

# 設定日誌
logger = logging.getLogger(__name__)


def optimize_mean_variance(
    expected_returns: pd.Series, 
    cov_matrix: pd.DataFrame, 
    risk_aversion: float = 1.0
) -> np.ndarray:
    """均值方差最佳化

    Args:
        expected_returns: 預期收益率
        cov_matrix: 協方差矩陣
        risk_aversion: 風險厭惡係數

    Returns:
        最佳化權重

    Raises:
        DependencyError: 當scipy不可用時
    """
    if not SCIPY_AVAILABLE:
        raise DependencyError("scipy套件不可用，無法進行投資組合最佳化")
    
    n = len(expected_returns)
    
    # 定義目標函數
    def objective(weights):
        """計算目標函數值

        Args:
            weights: 投資組合權重
        """
        portfolio_return = np.sum(expected_returns * weights)
        portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
        return -portfolio_return + risk_aversion * portfolio_variance
    
    # 定義約束條件
    constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}  # 權重和為 1
    bounds = tuple((0, 1) for _ in range(n))  # 權重介於 0 和 1 之間
    
    # 初始猜測
    initial_weights = np.ones(n) / n
    
    try:
        # 最佳化
        result = sco.minimize(
            objective,
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
        
        if not result.success:
            logger.warning(f"最佳化未收斂: {result.message}")
            # 返回等權重作為備選方案
            return np.ones(n) / n
        
        return result["x"]
    except Exception as e:
        logger.error(f"最佳化過程中發生錯誤: {e}")
        # 返回等權重作為備選方案
        return np.ones(n) / n


def optimize_risk_parity(cov_matrix: pd.DataFrame) -> np.ndarray:
    """風險平價最佳化

    Args:
        cov_matrix: 協方差矩陣

    Returns:
        最佳化權重

    Raises:
        DependencyError: 當scipy不可用時
    """
    if not SCIPY_AVAILABLE:
        raise DependencyError("scipy套件不可用，無法進行風險平價最佳化")
    
    n = cov_matrix.shape[0]
    
    # 定義目標函數
    def objective(weights):
        """計算每個資產的風險貢獻

        Args:
            weights: 投資組合權重
        """
        portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
        risk_contribution = (
            weights * np.dot(cov_matrix, weights) / portfolio_variance
        )
        
        # 計算風險貢獻的標準差
        target_risk = 1.0 / n
        risk_deviation = np.sum((risk_contribution - target_risk) ** 2)
        
        return risk_deviation
    
    # 定義約束條件
    constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}  # 權重和為 1
    bounds = tuple((0, 1) for _ in range(n))  # 權重介於 0 和 1 之間
    
    # 初始猜測
    initial_weights = np.ones(n) / n
    
    try:
        # 最佳化
        result = sco.minimize(
            objective,
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
        
        if not result.success:
            logger.warning(f"風險平價最佳化未收斂: {result.message}")
            return np.ones(n) / n
        
        return result["x"]
    except Exception as e:
        logger.error(f"風險平價最佳化過程中發生錯誤: {e}")
        return np.ones(n) / n


def optimize_max_sharpe(
    expected_returns: pd.Series, 
    cov_matrix: pd.DataFrame, 
    risk_free_rate: float = 0.0
) -> np.ndarray:
    """最大夏普比率最佳化

    Args:
        expected_returns: 預期收益率
        cov_matrix: 協方差矩陣
        risk_free_rate: 無風險利率

    Returns:
        最佳化權重

    Raises:
        DependencyError: 當scipy不可用時
    """
    if not SCIPY_AVAILABLE:
        raise DependencyError("scipy套件不可用，無法進行最大夏普比率最佳化")
    
    n = len(expected_returns)
    
    # 定義目標函數 (負的夏普比率，因為我們要最大化)
    def objective(weights):
        """計算負的夏普比率

        Args:
            weights: 投資組合權重
        """
        portfolio_return = np.sum(expected_returns * weights)
        portfolio_volatility = np.sqrt(
            np.dot(weights.T, np.dot(cov_matrix, weights))
        )
        
        # 避免除以零
        if portfolio_volatility == 0:
            return -999999  # 一個非常小的數，表示這不是一個好的解
        
        sharpe_ratio = (
            portfolio_return - risk_free_rate
        ) / portfolio_volatility
        return -sharpe_ratio  # 負號是因為我們要最大化夏普比率
    
    # 定義約束條件
    constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}  # 權重和為 1
    bounds = tuple((0, 1) for _ in range(n))  # 權重介於 0 和 1 之間
    
    # 初始猜測
    initial_weights = np.ones(n) / n
    
    try:
        # 最佳化
        result = sco.minimize(
            objective,
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
        
        if not result.success:
            logger.warning(f"最大夏普比率最佳化未收斂: {result.message}")
            return np.ones(n) / n
        
        return result["x"]
    except Exception as e:
        logger.error(f"最大夏普比率最佳化過程中發生錯誤: {e}")
        return np.ones(n) / n


def optimize_min_variance(cov_matrix: pd.DataFrame) -> np.ndarray:
    """最小方差最佳化

    Args:
        cov_matrix: 協方差矩陣

    Returns:
        最佳化權重

    Raises:
        DependencyError: 當scipy不可用時
    """
    if not SCIPY_AVAILABLE:
        raise DependencyError("scipy套件不可用，無法進行最小方差最佳化")
    
    n = cov_matrix.shape[0]
    
    # 定義目標函數 (投資組合方差)
    def objective(weights):
        """計算投資組合方差

        Args:
            weights: 投資組合權重
        """
        return np.dot(weights.T, np.dot(cov_matrix, weights))
    
    # 定義約束條件
    constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}  # 權重和為 1
    bounds = tuple((0, 1) for _ in range(n))  # 權重介於 0 和 1 之間
    
    # 初始猜測
    initial_weights = np.ones(n) / n
    
    try:
        # 最佳化
        result = sco.minimize(
            objective,
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
        
        if not result.success:
            logger.warning(f"最小方差最佳化未收斂: {result.message}")
            return np.ones(n) / n
        
        return result["x"]
    except Exception as e:
        logger.error(f"最小方差最佳化過程中發生錯誤: {e}")
        return np.ones(n) / n


def calculate_efficient_frontier(
    expected_returns: pd.Series, 
    cov_matrix: pd.DataFrame, 
    num_points: int = 100
) -> Tuple[np.ndarray, np.ndarray]:
    """計算效率前緣

    Args:
        expected_returns: 預期收益率
        cov_matrix: 協方差矩陣
        num_points: 效率前緣點數

    Returns:
        (風險, 收益) 的元組

    Raises:
        DependencyError: 當pypfopt不可用時
    """
    if not PYPFOPT_AVAILABLE:
        raise DependencyError("pypfopt套件不可用，無法計算效率前緣")
    
    try:
        # 創建效率前緣物件
        ef = EfficientFrontier(expected_returns, cov_matrix)
        
        # 計算效率前緣
        risks = []
        returns = []
        
        # 獲取最小和最大收益率
        min_ret = expected_returns.min()
        max_ret = expected_returns.max()
        
        # 在收益率範圍內生成點
        target_returns = np.linspace(min_ret, max_ret, num_points)
        
        for target_return in target_returns:
            try:
                # 重新創建效率前緣物件（因為每次最佳化會修改狀態）
                ef = EfficientFrontier(expected_returns, cov_matrix)
                
                # 針對目標收益率進行最佳化
                ef.efficient_return(target_return)
                
                # 獲取績效指標
                ret, vol, _ = ef.portfolio_performance()
                
                returns.append(ret)
                risks.append(vol)
                
            except Exception:
                # 如果某個點最佳化失敗，跳過
                continue
        
        return np.array(risks), np.array(returns)
        
    except Exception as e:
        logger.error(f"計算效率前緣時發生錯誤: {e}")
        # 返回空陣列
        return np.array([]), np.array([])


def optimize_with_pypfopt(
    price_df: pd.DataFrame, 
    method: str = "min_volatility"
) -> Dict[str, float]:
    """使用PyPortfolioOpt進行最佳化

    Args:
        price_df: 價格資料
        method: 最佳化方法

    Returns:
        最佳化權重字典

    Raises:
        DependencyError: 當pypfopt不可用時
    """
    if not PYPFOPT_AVAILABLE:
        raise DependencyError("pypfopt套件不可用，無法使用PyPortfolioOpt最佳化")
    
    try:
        # 計算預期收益率
        mu = expected_returns.mean_historical_return(price_df)
        
        # 計算協方差矩陣
        S = risk_models.sample_cov(price_df)
        
        # 設置有效前沿
        ef = EfficientFrontier(mu, S)
        
        # 根據方法進行最佳化
        if method == "min_volatility":
            ef.min_volatility()
        elif method == "max_sharpe":
            ef.max_sharpe()
        elif method == "efficient_risk":
            ef.efficient_risk(0.1)  # 目標風險為10%
        elif method == "efficient_return":
            ef.efficient_return(0.1)  # 目標收益率為10%
        else:
            raise ValueError(f"不支援的最佳化方法: {method}")
        
        # 清理權重
        cleaned_weights = ef.clean_weights()
        
        # 轉換為字典並過濾小權重
        weights_dict = {
            stock: weight for stock, weight in cleaned_weights.items() if weight > 0.01
        }
        
        # 標準化權重
        total_weight = sum(weights_dict.values())
        if total_weight > 0:
            weights_dict = {
                stock: weight / total_weight for stock, weight in weights_dict.items()
            }
        
        return weights_dict
        
    except Exception as e:
        logger.error(f"PyPortfolioOpt最佳化失敗: {e}")
        return {}
