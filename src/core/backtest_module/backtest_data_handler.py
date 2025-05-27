"""
回測數據處理模組

此模組包含回測系統的數據載入、處理和管理功能。
"""

import logging
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def load_market_data(
    symbols: List[str],
    start_date: datetime,
    end_date: datetime
) -> pd.DataFrame:
    """
    載入市場數據

    Args:
        symbols: 股票代碼列表
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        pd.DataFrame: 市場數據
    """
    try:
        # 目前使用模擬數據
        logger.info("載入市場數據: %s, %s 至 %s", symbols, start_date, end_date)

        # 生成日期範圍
        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        dates = dates[dates.weekday < 5]  # 只保留工作日

        # 生成模擬價格數據
        np.random.seed(42)
        data = []

        for symbol in symbols:
            base_price = np.random.uniform(100, 500)
            prices = [base_price]

            for _ in range(len(dates) - 1):
                # 生成隨機價格變動
                change = np.random.normal(0, 0.02)
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, 1.0))  # 確保價格不為負

            for i, date in enumerate(dates):
                price = prices[i]
                # 生成 OHLCV 數據
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = price * (1 + np.random.normal(0, 0.005))
                volume = np.random.randint(1000, 100000)

                data.append({
                    "symbol": symbol,
                    "date": date,
                    "open": open_price,
                    "high": max(high, open_price, price),
                    "low": min(low, open_price, price),
                    "close": price,
                    "volume": volume,
                })

        df = pd.DataFrame(data)
        df.set_index("date", inplace=True)

        logger.info("成功載入 %d 筆市場數據", len(df))
        return df

    except Exception as e:
        logger.error("載入市場數據失敗: %s", e)
        raise


def initialize_strategy(strategy_id: str, config: Any) -> Dict[str, Any]:
    """
    初始化策略

    Args:
        strategy_id: 策略ID
        config: 回測配置

    Returns:
        Dict[str, Any]: 策略對象
    """
    try:
        logger.info("初始化策略: %s", strategy_id)

        # 目前返回模擬策略配置
        strategy_configs = {
            "ma_cross": {
                "name": "移動平均線交叉策略",
                "short_window": 5,
                "long_window": 20,
            },
            "rsi_strategy": {
                "name": "RSI策略",
                "window": 14,
                "overbought": 70,
                "oversold": 30,
            },
            "bollinger_bands": {
                "name": "布林通道策略",
                "window": 20,
                "num_std": 2.0,
            },
        }

        strategy = strategy_configs.get(strategy_id, {
            "name": "默認策略",
            "type": "simple",
        })

        # 合併用戶自定義參數
        if hasattr(config, 'strategy_params') and config.strategy_params:
            strategy.update(config.strategy_params)

        logger.info("策略初始化完成: %s", strategy.get("name", strategy_id))
        return strategy

    except Exception as e:
        logger.error("初始化策略失敗: %s", e)
        raise


def generate_signals(strategy: Dict[str, Any], market_data: pd.DataFrame) -> pd.DataFrame:
    """
    生成交易信號

    Args:
        strategy: 策略配置
        market_data: 市場數據

    Returns:
        pd.DataFrame: 交易信號
    """
    try:
        logger.info("生成交易信號，策略: %s", strategy.get("name", "未知"))

        if market_data.empty:
            logger.warning("市場數據為空，返回空信號")
            return pd.DataFrame()

        # 生成模擬信號
        signals = []
        dates = market_data.index.unique()

        # 簡單的隨機信號生成（實際應該根據策略邏輯）
        np.random.seed(42)
        for date in dates:
            # 生成 -1 (賣出), 0 (持有), 1 (買入) 信號
            signal = np.random.choice([-1, 0, 1], p=[0.1, 0.8, 0.1])
            signals.append({
                "date": date,
                "signal": signal,
                "strength": np.random.uniform(0.5, 1.0),
            })

        signals_df = pd.DataFrame(signals)
        signals_df.set_index("date", inplace=True)

        logger.info("成功生成 %d 個交易信號", len(signals_df))
        return signals_df

    except Exception as e:
        logger.error("生成交易信號失敗: %s", e)
        raise


def process_backtest_results(
    raw_results: Dict[str, Any],
    config: Any
) -> Dict[str, Any]:
    """
    處理回測結果

    Args:
        raw_results: 原始回測結果
        config: 回測配置

    Returns:
        Dict[str, Any]: 處理後的結果
    """
    try:
        logger.info("處理回測結果")

        # 提取基本信息
        processed_results = {
            "backtest_id": getattr(config, 'backtest_id', 'unknown'),
            "strategy_id": config.strategy_id,
            "strategy_name": config.strategy_name,
            "symbols": config.symbols,
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat(),
            "initial_capital": config.initial_capital,
            "commission": config.commission,
            "slippage": config.slippage,
            "tax": config.tax,
        }

        # 處理權益曲線
        equity_curve = raw_results.get("equity_curve", [])
        if equity_curve:
            processed_results["final_capital"] = equity_curve[-1]
            processed_results["equity_curve"] = equity_curve
        else:
            processed_results["final_capital"] = config.initial_capital
            processed_results["equity_curve"] = [config.initial_capital]

        # 處理交易記錄
        trades = raw_results.get("trades", [])
        processed_results["trades"] = trades
        processed_results["total_trades"] = len(trades)

        # 處理日期
        dates = raw_results.get("dates", [])
        processed_results["dates"] = dates

        # 計算基本統計
        if trades:
            winning_trades = [t for t in trades if t.get("profit", 0) > 0]
            losing_trades = [t for t in trades if t.get("profit", 0) < 0]

            processed_results.update({
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": len(winning_trades) / len(trades) * 100 if trades else 0,
                "total_profit": sum(t.get("profit", 0) for t in trades),
                "avg_profit_per_trade": sum(t.get("profit", 0) for t in trades) / len(trades) if trades else 0,
            })
        else:
            processed_results.update({
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_profit": 0,
                "avg_profit_per_trade": 0,
            })

        logger.info("回測結果處理完成")
        return processed_results

    except Exception as e:
        logger.error("處理回測結果失敗: %s", e)
        raise


def validate_data_integrity(data: pd.DataFrame) -> bool:
    """
    驗證數據完整性

    Args:
        data: 待驗證的數據

    Returns:
        bool: 是否通過驗證
    """
    try:
        if data.empty:
            logger.warning("數據為空")
            return False

        # 檢查必要欄位
        required_columns = ["open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in data.columns]

        if missing_columns:
            logger.error("缺少必要欄位: %s", missing_columns)
            return False

        # 檢查數據類型
        for col in required_columns:
            if not pd.api.types.is_numeric_dtype(data[col]):
                logger.error("欄位 %s 不是數值類型", col)
                return False

        # 檢查空值
        if data.isnull().any().any():
            logger.warning("數據包含空值")
            return False

        # 檢查價格邏輯
        invalid_prices = (
            (data["high"] < data["low"]) |
            (data["high"] < data["open"]) |
            (data["high"] < data["close"]) |
            (data["low"] > data["open"]) |
            (data["low"] > data["close"])
        )

        if invalid_prices.any():
            logger.error("發現無效的價格數據")
            return False

        logger.info("數據完整性驗證通過")
        return True

    except Exception as e:
        logger.error("數據完整性驗證失敗: %s", e)
        return False
