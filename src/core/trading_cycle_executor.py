"""
交易週期執行器模組

此模組負責處理交易週期的執行邏輯，包括：
- 即時特徵計算
- 交易訊號生成
- 風險控制和訂單生成
- 訂單執行

主要功能：
- 執行完整的交易週期
- 處理即時資料和訊號
- 實施風險控制機制
- 生成和執行交易訂單

Example:
    >>> from src.core.trading_cycle_executor import execute_trading_cycle
    >>> config = {"strategy": {...}, "risk_control": {...}}
    >>> order_ids = execute_trading_cycle(config)
    >>> print(f"執行了 {len(order_ids)} 個訂單")
"""

import logging
from typing import Dict, Any, List, Optional

from .executor import place_orders
from .features import compute_features
from .portfolio import optimize
from .risk_control import filter_signals
from .strategy import generate_signals

logger = logging.getLogger(__name__)


def compute_realtime_features() -> Any:
    """計算即時技術特徵.

    Returns:
        Any: 計算後的即時特徵資料

    Raises:
        RuntimeError: 當特徵計算失敗時

    Example:
        >>> features = compute_realtime_features()
        >>> print(f"特徵計算完成")
    """
    try:
        logger.debug("計算即時特徵...")
        features = compute_features()
        logger.debug("即時特徵計算完成")
        return features
        
    except Exception as e:
        logger.error("計算即時特徵失敗: %s", e, exc_info=True)
        raise RuntimeError(f"計算即時特徵失敗: {e}") from e


def generate_realtime_signals(features: Any, config: Dict[str, Any]) -> Any:
    """生成即時交易訊號.

    Args:
        features: 技術特徵資料
        config: 系統配置字典

    Returns:
        Any: 生成的交易訊號

    Raises:
        RuntimeError: 當訊號生成失敗時

    Example:
        >>> features = compute_realtime_features()
        >>> signals = generate_realtime_signals(features, config)
    """
    try:
        logger.debug("生成交易訊號...")
        strategy_config = config["strategy"]
        signals = generate_signals(
            features, 
            strategy_config["name"], 
            **strategy_config["params"]
        )
        logger.debug("交易訊號生成完成")
        return signals
        
    except Exception as e:
        logger.error("生成交易訊號失敗: %s", e, exc_info=True)
        raise RuntimeError(f"生成交易訊號失敗: {e}") from e


def optimize_realtime_portfolio(signals: Any, config: Dict[str, Any]) -> Any:
    """最佳化即時投資組合.

    Args:
        signals: 交易訊號
        config: 系統配置字典

    Returns:
        Any: 最佳化後的投資組合權重

    Raises:
        RuntimeError: 當投資組合最佳化失敗時

    Example:
        >>> signals = generate_realtime_signals(features, config)
        >>> weights = optimize_realtime_portfolio(signals, config)
    """
    try:
        logger.debug("最佳化投資組合...")
        portfolio_config = config["portfolio"]
        weights = optimize(
            signals, 
            portfolio_config["name"], 
            **portfolio_config["params"]
        )
        logger.debug("投資組合最佳化完成")
        return weights
        
    except Exception as e:
        logger.error("投資組合最佳化失敗: %s", e, exc_info=True)
        raise RuntimeError(f"投資組合最佳化失敗: {e}") from e


def apply_risk_control(signals: Any, config: Dict[str, Any]) -> Any:
    """應用風險控制.

    Args:
        signals: 交易訊號
        config: 系統配置字典

    Returns:
        Any: 過濾後的交易訊號

    Raises:
        RuntimeError: 當風險控制失敗時

    Example:
        >>> signals = generate_realtime_signals(features, config)
        >>> filtered_signals = apply_risk_control(signals, config)
    """
    try:
        logger.debug("執行風險控制...")
        
        # 簡化處理：使用初始資金作為投資組合價值
        portfolio_value = config.get("backtest", {}).get("initial_capital", 1000000.0)
        risk_config = config["risk_control"]
        
        filtered_signals = filter_signals(
            signals,
            portfolio_value,
            max_position_size=risk_config["max_position_size"],
            max_portfolio_risk=risk_config["max_portfolio_risk"],
            stop_loss_pct=risk_config["stop_loss"],
            stop_profit_pct=risk_config["stop_profit"],
        )
        
        logger.debug("風險控制完成")
        return filtered_signals
        
    except Exception as e:
        logger.error("風險控制失敗: %s", e, exc_info=True)
        raise RuntimeError(f"風險控制失敗: {e}") from e


def generate_orders_from_signals(
    filtered_signals, 
    default_quantity: int = 1000
) -> List[Dict[str, Any]]:
    """從過濾後的訊號生成訂單.

    Args:
        filtered_signals: 過濾後的交易訊號
        default_quantity: 預設交易數量

    Returns:
        List[Dict[str, Any]]: 訂單列表

    Example:
        >>> filtered_signals = apply_risk_control(signals, config)
        >>> orders = generate_orders_from_signals(filtered_signals)
        >>> print(f"生成 {len(orders)} 個訂單")
    """
    orders = []
    
    try:
        for (stock_id, date), row in filtered_signals.iterrows():
            if row.get("buy_signal", 0) == 1:
                # 買入訂單
                orders.append({
                    "stock_id": stock_id,
                    "action": "buy",
                    "quantity": default_quantity,
                    "order_type": "market",
                    "timestamp": date,
                })
            elif row.get("sell_signal", 0) == 1:
                # 賣出訂單
                orders.append({
                    "stock_id": stock_id,
                    "action": "sell",
                    "quantity": default_quantity,
                    "order_type": "market",
                    "timestamp": date,
                })
        
        logger.debug("從訊號生成 %d 個訂單", len(orders))
        
    except Exception as e:
        logger.error("從訊號生成訂單失敗: %s", e, exc_info=True)
        # 返回空列表而不是拋出異常，讓系統繼續運行
        orders = []
    
    return orders


def execute_orders(orders: List[Dict[str, Any]]) -> Optional[List[str]]:
    """執行訂單.

    Args:
        orders: 訂單列表

    Returns:
        Optional[List[str]]: 執行的訂單 ID 列表，如果沒有訂單則返回 None

    Raises:
        RuntimeError: 當訂單執行失敗時

    Example:
        >>> orders = generate_orders_from_signals(filtered_signals)
        >>> order_ids = execute_orders(orders)
        >>> print(f"執行了 {len(order_ids)} 個訂單")
    """
    if not orders:
        logger.debug("沒有訂單需要執行")
        return None
    
    try:
        logger.info("執行 %d 個訂單", len(orders))
        order_ids = place_orders(orders)
        logger.info("訂單執行完成，ID: %s", order_ids)
        return order_ids
        
    except Exception as e:
        logger.error("訂單執行失敗: %s", e, exc_info=True)
        raise RuntimeError(f"訂單執行失敗: {e}") from e


def execute_trading_cycle(config: Dict[str, Any]) -> Optional[List[str]]:
    """執行一個完整的交易週期.

    Args:
        config: 系統配置字典

    Returns:
        Optional[List[str]]: 執行的訂單 ID 列表，如果沒有訂單則返回 None

    Raises:
        RuntimeError: 當交易週期執行失敗時

    Example:
        >>> config = {"strategy": {...}, "portfolio": {...}, "risk_control": {...}}
        >>> order_ids = execute_trading_cycle(config)
        >>> if order_ids:
        ...     print(f"執行了 {len(order_ids)} 個訂單")
        ... else:
        ...     print("本週期無交易訊號")
    """
    try:
        logger.debug("開始執行交易週期")
        
        # 1. 計算即時特徵
        features = compute_realtime_features()

        # 2. 生成交易訊號
        signals = generate_realtime_signals(features, config)

        # 3. 最佳化投資組合
        weights = optimize_realtime_portfolio(signals, config)

        # 4. 應用風險控制
        filtered_signals = apply_risk_control(signals, config)

        # 5. 生成訂單
        orders = generate_orders_from_signals(filtered_signals)

        # 6. 執行訂單
        order_ids = execute_orders(orders)
        
        if order_ids:
            logger.debug("交易週期執行完成，執行了 %d 個訂單", len(order_ids))
        else:
            logger.debug("交易週期執行完成，本週期無交易訊號")
        
        return order_ids

    except RuntimeError:
        raise
    except Exception as e:
        logger.error("交易週期執行失敗: %s", e, exc_info=True)
        raise RuntimeError(f"交易週期執行失敗: {e}") from e


def validate_trading_cycle_config(config: Dict[str, Any]) -> None:
    """驗證交易週期配置.

    Args:
        config: 系統配置字典

    Raises:
        ValueError: 當配置參數不正確時

    Example:
        >>> config = {"strategy": {...}, "portfolio": {...}, "risk_control": {...}}
        >>> validate_trading_cycle_config(config)  # 不會拋出異常
    """
    required_keys = ["strategy", "portfolio", "risk_control"]
    
    for key in required_keys:
        if key not in config:
            raise ValueError(f"交易週期配置缺少必要項目: {key}")
    
    # 驗證策略配置
    strategy_config = config["strategy"]
    if "name" not in strategy_config:
        raise ValueError("策略配置缺少名稱")
    
    # 驗證投資組合配置
    portfolio_config = config["portfolio"]
    if "name" not in portfolio_config:
        raise ValueError("投資組合配置缺少名稱")
    
    # 驗證風險控制配置
    risk_config = config["risk_control"]
    required_risk_keys = ["max_position_size", "max_portfolio_risk", "stop_loss", "stop_profit"]
    
    for key in required_risk_keys:
        if key not in risk_config:
            raise ValueError(f"風險控制配置缺少參數: {key}")


def get_trading_cycle_status() -> Dict[str, Any]:
    """獲取交易週期狀態.

    Returns:
        Dict[str, Any]: 交易週期狀態資訊

    Example:
        >>> status = get_trading_cycle_status()
        >>> print(f"系統狀態: {status['system_status']}")
    """
    # 這裡可以添加更多的狀態檢查邏輯
    return {
        "system_status": "ready",
        "last_execution": None,
        "next_execution": None,
        "active_orders": 0,
    }
