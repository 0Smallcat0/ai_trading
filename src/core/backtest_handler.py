"""
回測模式處理器模組

此模組專門負責處理回測模式的執行邏輯，包括：
- 歷史資料載入和處理
- 回測流程執行
- 結果生成和報告

主要功能：
- 執行完整的回測流程
- 處理回測特有的資料和配置
- 生成回測結果和績效報告

Example:
    >>> from src.core.backtest_handler import run_backtest_mode
    >>> config = {"start_date": "2023-01-01", "end_date": "2023-12-31", ...}
    >>> results, report = run_backtest_mode(config)
    >>> print(f"總收益率: {report['returns']['total_return']:.2%}")
"""

import logging
from typing import Dict, Any, Tuple

from .backtest import run_backtest
from .data_ingest import load_data, update_data
from .features import compute_features
from .logger import record
from .portfolio import optimize
from .strategy import generate_signals

logger = logging.getLogger(__name__)


def validate_backtest_config(config: Dict[str, Any]) -> None:
    """驗證回測配置.

    Args:
        config: 系統配置字典

    Raises:
        ValueError: 當配置參數不正確時

    Example:
        >>> config = {"start_date": "2023-01-01", "end_date": "2023-12-31", ...}
        >>> validate_backtest_config(config)  # 不會拋出異常
    """
    required_keys = ["start_date", "end_date", "strategy", "portfolio", "backtest"]
    
    for key in required_keys:
        if key not in config:
            raise ValueError(f"回測配置缺少必要項目: {key}")
    
    if config["start_date"] is None or config["end_date"] is None:
        raise ValueError("回測模式需要指定開始和結束日期")
    
    backtest_config = config.get("backtest", {})
    required_backtest_keys = ["initial_capital", "transaction_cost", "slippage", "tax"]
    
    for key in required_backtest_keys:
        if key not in backtest_config:
            raise ValueError(f"回測配置缺少參數: {key}")


def load_backtest_data(config: Dict[str, Any]) -> None:
    """載入回測所需的資料.

    Args:
        config: 系統配置字典

    Raises:
        RuntimeError: 當資料載入失敗時

    Example:
        >>> config = {"start_date": "2023-01-01", "end_date": "2023-12-31", ...}
        >>> load_backtest_data(config)
    """
    try:
        logger.info("載入歷史資料...")
        load_data(config["start_date"], config["end_date"])

        # 更新資料（如果需要）
        if config.get("update_data", False):
            logger.info("更新資料...")
            update_data(config["start_date"], config["end_date"])
            
        logger.info("回測資料載入完成")
        
    except Exception as e:
        logger.error("載入回測資料失敗: %s", e, exc_info=True)
        raise RuntimeError(f"載入回測資料失敗: {e}") from e


def compute_backtest_features(config: Dict[str, Any]) -> Any:
    """計算回測所需的技術特徵.

    Args:
        config: 系統配置字典

    Returns:
        Any: 計算後的特徵資料

    Raises:
        RuntimeError: 當特徵計算失敗時

    Example:
        >>> config = {"start_date": "2023-01-01", "end_date": "2023-12-31"}
        >>> features = compute_backtest_features(config)
    """
    try:
        logger.info("計算技術特徵...")
        features = compute_features(config["start_date"], config["end_date"])
        logger.info("技術特徵計算完成")
        return features
        
    except Exception as e:
        logger.error("計算技術特徵失敗: %s", e, exc_info=True)
        raise RuntimeError(f"計算技術特徵失敗: {e}") from e


def generate_backtest_signals(features: Any, config: Dict[str, Any]) -> Any:
    """生成回測交易訊號.

    Args:
        features: 技術特徵資料
        config: 系統配置字典

    Returns:
        Any: 生成的交易訊號

    Raises:
        RuntimeError: 當訊號生成失敗時

    Example:
        >>> features = compute_backtest_features(config)
        >>> signals = generate_backtest_signals(features, config)
    """
    try:
        logger.info("生成交易訊號...")
        strategy_config = config["strategy"]
        signals = generate_signals(
            features, 
            strategy_config["name"], 
            **strategy_config["params"]
        )
        logger.info("交易訊號生成完成")
        return signals
        
    except Exception as e:
        logger.error("生成交易訊號失敗: %s", e, exc_info=True)
        raise RuntimeError(f"生成交易訊號失敗: {e}") from e


def optimize_backtest_portfolio(signals: Any, config: Dict[str, Any]) -> Any:
    """最佳化回測投資組合.

    Args:
        signals: 交易訊號
        config: 系統配置字典

    Returns:
        Any: 最佳化後的投資組合權重

    Raises:
        RuntimeError: 當投資組合最佳化失敗時

    Example:
        >>> signals = generate_backtest_signals(features, config)
        >>> weights = optimize_backtest_portfolio(signals, config)
    """
    try:
        logger.info("最佳化投資組合...")
        portfolio_config = config["portfolio"]
        weights = optimize(
            signals, 
            portfolio_config["name"], 
            **portfolio_config["params"]
        )
        logger.info("投資組合最佳化完成")
        return weights
        
    except Exception as e:
        logger.error("投資組合最佳化失敗: %s", e, exc_info=True)
        raise RuntimeError(f"投資組合最佳化失敗: {e}") from e


def execute_backtest_simulation(
    signals: Any, 
    weights: Any, 
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """執行回測模擬.

    Args:
        signals: 交易訊號
        weights: 投資組合權重
        config: 系統配置字典

    Returns:
        Dict[str, Any]: 回測結果

    Raises:
        RuntimeError: 當回測執行失敗時

    Example:
        >>> results = execute_backtest_simulation(signals, weights, config)
        >>> print(f"最終資產: {results['final_value']}")
    """
    try:
        logger.info("執行回測計算...")
        backtest_config = config["backtest"]
        
        results = run_backtest(
            signals,
            weights,
            config["start_date"],
            config["end_date"],
            backtest_config["initial_capital"],
            backtest_config["transaction_cost"],
            backtest_config["slippage"],
            backtest_config["tax"],
        )
        
        logger.info("回測計算完成")
        return results
        
    except Exception as e:
        logger.error("回測執行失敗: %s", e, exc_info=True)
        raise RuntimeError(f"回測執行失敗: {e}") from e


def generate_backtest_report(results: Dict[str, Any]) -> Dict[str, Any]:
    """生成回測報告.

    Args:
        results: 回測結果

    Returns:
        Dict[str, Any]: 回測報告

    Raises:
        RuntimeError: 當報告生成失敗時

    Example:
        >>> results = execute_backtest_simulation(signals, weights, config)
        >>> report = generate_backtest_report(results)
        >>> print(f"夏普比率: {report['sharpe_ratio']}")
    """
    try:
        logger.info("生成回測報告...")
        report = record(results)
        logger.info("回測報告生成完成")
        return report
        
    except Exception as e:
        logger.error("生成回測報告失敗: %s", e, exc_info=True)
        raise RuntimeError(f"生成回測報告失敗: {e}") from e


def run_backtest_mode(config: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """執行回測模式.

    Args:
        config: 系統配置字典，包含回測所需的所有參數

    Returns:
        Tuple[Dict[str, Any], Dict[str, Any]]: 回測結果和報告

    Raises:
        ValueError: 當配置參數不正確時
        RuntimeError: 當回測執行失敗時

    Example:
        >>> config = {"start_date": "2023-01-01", "end_date": "2023-12-31", ...}
        >>> results, report = run_backtest_mode(config)
        >>> print(f"總收益率: {report['returns']['total_return']:.2%}")
    """
    logger.info("開始回測模式")

    try:
        # 驗證配置
        validate_backtest_config(config)

        # 載入資料
        load_backtest_data(config)

        # 計算特徵
        features = compute_backtest_features(config)

        # 生成交易訊號
        signals = generate_backtest_signals(features, config)

        # 最佳化投資組合
        weights = optimize_backtest_portfolio(signals, config)

        # 執行回測
        results = execute_backtest_simulation(signals, weights, config)

        # 生成報告
        report = generate_backtest_report(results)

        logger.info("回測模式執行完成")
        return results, report

    except (ValueError, RuntimeError):
        raise
    except Exception as e:
        logger.error("回測模式執行失敗: %s", e, exc_info=True)
        raise RuntimeError(f"回測執行失敗: {e}") from e


def get_backtest_summary(results: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
    """獲取回測摘要資訊.

    Args:
        results: 回測結果
        report: 回測報告

    Returns:
        Dict[str, Any]: 回測摘要

    Example:
        >>> results, report = run_backtest_mode(config)
        >>> summary = get_backtest_summary(results, report)
        >>> print(f"總收益率: {summary['total_return']:.2%}")
    """
    try:
        returns = report.get("returns", {})
        risk = report.get("risk", {})
        trade = report.get("trade", {})
        
        summary = {
            "total_return": returns.get("total_return", 0),
            "annual_return": returns.get("annual_return", 0),
            "sharpe_ratio": risk.get("sharpe_ratio", 0),
            "max_drawdown": risk.get("max_drawdown", 0),
            "win_rate": trade.get("win_rate", 0),
            "profit_loss_ratio": trade.get("profit_loss_ratio", 0),
            "total_trades": trade.get("total_trades", 0),
            "final_value": results.get("final_value", 0),
        }
        
        return summary
        
    except Exception as e:
        logger.warning("生成回測摘要時發生錯誤: %s", e)
        return {}
