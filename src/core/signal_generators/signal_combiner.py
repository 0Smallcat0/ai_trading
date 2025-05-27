"""訊號合併器

此模組實現多種策略訊號的合併功能。
"""

import logging
from typing import Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class SignalCombiner:
    """訊號合併器

    將多種策略的訊號合併為最終的交易訊號。
    """

    def __init__(self):
        """初始化訊號合併器"""
        self.signals: Dict[str, pd.DataFrame] = {}
        self.combined_signals: Optional[pd.DataFrame] = None

    def add_signals(self, strategy_name: str, signals: pd.DataFrame):
        """添加策略訊號

        Args:
            strategy_name (str): 策略名稱
            signals (pd.DataFrame): 訊號資料
        """
        if not isinstance(signals, pd.DataFrame):
            raise ValueError("訊號必須是 pandas DataFrame")

        if "signal" not in signals.columns:
            raise ValueError("訊號資料必須包含 'signal' 欄位")

        self.signals[strategy_name] = signals.copy()
        logger.info("已添加策略訊號: %s", strategy_name)

    def combine_signals(
        self,
        weights: Optional[Dict[str, float]] = None,
        method: str = "weighted_average",
        threshold: float = 0.5,
    ) -> pd.DataFrame:
        """合併多種策略訊號

        Args:
            weights (Dict[str, float], optional): 策略權重字典
            method (str): 合併方法 ('weighted_average', 'majority_vote', 'consensus')
            threshold (float): 訊號閾值

        Returns:
            pd.DataFrame: 合併後的訊號

        Raises:
            ValueError: 當沒有可用訊號或權重包含未知策略時
        """
        if not self.signals:
            raise ValueError("沒有可用的訊號，請先添加訊號")

        # 設定預設權重
        if weights is None:
            weights = {strategy: 1.0 for strategy in self.signals.keys()}

        # 檢查權重中的策略是否存在
        unknown_strategies = set(weights.keys()) - set(self.signals.keys())
        if unknown_strategies:
            raise ValueError(f"權重中包含未知的策略: {unknown_strategies}")

        # 獲取所有訊號的聯合索引
        all_indices = set()
        for signals in self.signals.values():
            if not signals.empty:
                all_indices.update(signals.index)

        # 轉換為排序列表
        if all_indices:
            combined_index = sorted(list(all_indices))
        else:
            combined_index = []

        # 初始化合併訊號
        combined_signals = pd.DataFrame(index=combined_index)
        combined_signals["signal"] = 0
        combined_signals["confidence"] = 0.0

        # 根據方法合併訊號
        if method == "weighted_average":
            combined_signals = self._weighted_average_combination(
                combined_signals, weights, threshold
            )
        elif method == "majority_vote":
            combined_signals = self._majority_vote_combination(
                combined_signals, weights
            )
        elif method == "consensus":
            combined_signals = self._consensus_combination(
                combined_signals, weights, threshold
            )
        else:
            raise ValueError(f"未知的合併方法: {method}")

        self.combined_signals = combined_signals
        logger.info("訊號合併完成，使用方法: %s", method)

        return combined_signals

    def _weighted_average_combination(
        self,
        combined_signals: pd.DataFrame,
        weights: Dict[str, float],
        threshold: float,
    ) -> pd.DataFrame:
        """加權平均合併法

        Args:
            combined_signals (pd.DataFrame): 合併訊號容器
            weights (Dict[str, float]): 策略權重
            threshold (float): 訊號閾值

        Returns:
            pd.DataFrame: 合併後的訊號
        """
        for idx in combined_signals.index:
            weighted_sum = 0.0
            total_weight = 0.0
            confidence_sum = 0.0
            confidence_count = 0

            for strategy, weight in weights.items():
                if strategy in self.signals:
                    strategy_signals = self.signals[strategy]

                    # 檢查索引是否存在，處理多層索引的情況
                    try:
                        if idx in strategy_signals.index:
                            signal_value = strategy_signals.loc[idx, "signal"]
                            if pd.notna(signal_value):
                                weighted_sum += signal_value * weight
                                total_weight += weight

                                # 計算信心度
                                if "confidence" in strategy_signals.columns:
                                    confidence = strategy_signals.loc[idx, "confidence"]
                                    if pd.notna(confidence):
                                        confidence_sum += confidence
                                        confidence_count += 1
                    except (KeyError, TypeError):
                        # 索引不匹配時跳過
                        continue

            # 計算最終訊號
            try:
                if total_weight > 0:
                    avg_signal = weighted_sum / total_weight

                    if avg_signal > threshold:
                        combined_signals.loc[idx, "signal"] = 1
                    elif avg_signal < -threshold:
                        combined_signals.loc[idx, "signal"] = -1
                    else:
                        combined_signals.loc[idx, "signal"] = 0

                    # 計算平均信心度
                    if confidence_count > 0:
                        combined_signals.loc[idx, "confidence"] = (
                            confidence_sum / confidence_count
                        )
                    else:
                        combined_signals.loc[idx, "confidence"] = abs(avg_signal)
                else:
                    # 如果沒有有效權重，設置為 0
                    combined_signals.loc[idx, "signal"] = 0
                    combined_signals.loc[idx, "confidence"] = 0.0
            except (KeyError, IndexError):
                # 如果索引不存在，跳過
                continue

        return combined_signals

    def _majority_vote_combination(
        self, combined_signals: pd.DataFrame, weights: Dict[str, float]
    ) -> pd.DataFrame:
        """多數投票合併法

        Args:
            combined_signals (pd.DataFrame): 合併訊號容器
            weights (Dict[str, float]): 策略權重

        Returns:
            pd.DataFrame: 合併後的訊號
        """
        for idx in combined_signals.index:
            votes = {"buy": 0, "sell": 0, "hold": 0}
            total_weight = 0.0

            for strategy, weight in weights.items():
                if strategy in self.signals:
                    strategy_signals = self.signals[strategy]

                    try:
                        if idx in strategy_signals.index:
                            signal_value = strategy_signals.loc[idx, "signal"]

                            if pd.notna(signal_value):
                                if signal_value > 0:
                                    votes["buy"] += weight
                                elif signal_value < 0:
                                    votes["sell"] += weight
                                else:
                                    votes["hold"] += weight

                                total_weight += weight
                    except (KeyError, TypeError):
                        continue

            # 決定最終訊號
            if total_weight > 0:
                max_vote = max(votes.values())

                if votes["buy"] == max_vote and votes["buy"] > votes["sell"]:
                    combined_signals.loc[idx, "signal"] = 1
                elif votes["sell"] == max_vote and votes["sell"] > votes["buy"]:
                    combined_signals.loc[idx, "signal"] = -1
                else:
                    combined_signals.loc[idx, "signal"] = 0

                # 計算信心度為最高票數的比例
                combined_signals.loc[idx, "confidence"] = max_vote / total_weight

        return combined_signals

    def _consensus_combination(
        self,
        combined_signals: pd.DataFrame,
        weights: Dict[str, float],
        threshold: float,
    ) -> pd.DataFrame:
        """共識合併法（需要多數策略同意才生成訊號）

        Args:
            combined_signals (pd.DataFrame): 合併訊號容器
            weights (Dict[str, float]): 策略權重
            threshold (float): 共識閾值

        Returns:
            pd.DataFrame: 合併後的訊號
        """
        for idx in combined_signals.index:
            buy_weight = 0.0
            sell_weight = 0.0
            total_weight = 0.0

            for strategy, weight in weights.items():
                if strategy in self.signals:
                    strategy_signals = self.signals[strategy]

                    try:
                        if idx in strategy_signals.index:
                            signal_value = strategy_signals.loc[idx, "signal"]

                            if pd.notna(signal_value):
                                if signal_value > 0:
                                    buy_weight += weight
                                elif signal_value < 0:
                                    sell_weight += weight

                                total_weight += weight
                    except (KeyError, TypeError):
                        continue

            # 需要達到共識閾值才生成訊號
            if total_weight > 0:
                buy_ratio = buy_weight / total_weight
                sell_ratio = sell_weight / total_weight

                if buy_ratio >= threshold:
                    combined_signals.loc[idx, "signal"] = 1
                    combined_signals.loc[idx, "confidence"] = buy_ratio
                elif sell_ratio >= threshold:
                    combined_signals.loc[idx, "signal"] = -1
                    combined_signals.loc[idx, "confidence"] = sell_ratio
                else:
                    combined_signals.loc[idx, "signal"] = 0
                    combined_signals.loc[idx, "confidence"] = max(buy_ratio, sell_ratio)

        return combined_signals

    def get_signal_statistics(self) -> Dict[str, Dict]:
        """獲取訊號統計資訊

        Returns:
            Dict[str, Dict]: 各策略的訊號統計
        """
        statistics = {}

        for strategy, signals in self.signals.items():
            signal_counts = signals["signal"].value_counts()

            statistics[strategy] = {
                "total_signals": len(signals),
                "buy_signals": signal_counts.get(1, 0),
                "sell_signals": signal_counts.get(-1, 0),
                "hold_signals": signal_counts.get(0, 0),
                "buy_ratio": signal_counts.get(1, 0) / len(signals),
                "sell_ratio": signal_counts.get(-1, 0) / len(signals),
                "hold_ratio": signal_counts.get(0, 0) / len(signals),
            }

            # 如果有信心度資訊
            if "confidence" in signals.columns:
                statistics[strategy]["avg_confidence"] = signals["confidence"].mean()
                statistics[strategy]["max_confidence"] = signals["confidence"].max()
                statistics[strategy]["min_confidence"] = signals["confidence"].min()

        return statistics

    def export_combined_signals(self, file_path: str):
        """匯出合併後的訊號

        Args:
            file_path (str): 檔案路徑
        """
        if self.combined_signals is None:
            raise ValueError("尚未合併訊號，請先調用 combine_signals 方法")

        try:
            self.combined_signals.to_csv(file_path)
            logger.info("合併訊號已匯出到: %s", file_path)
        except Exception as e:
            logger.error("匯出合併訊號時發生錯誤: %s", e)

    def clear_signals(self):
        """清除所有訊號"""
        self.signals.clear()
        self.combined_signals = None
        logger.info("已清除所有訊號")

    def remove_signal(self, strategy_name: str):
        """移除指定策略的訊號

        Args:
            strategy_name (str): 策略名稱
        """
        if strategy_name in self.signals:
            del self.signals[strategy_name]
            logger.info("已移除策略訊號: %s", strategy_name)
        else:
            logger.warning("策略 '%s' 不存在", strategy_name)

    def list_strategies(self) -> list:
        """列出所有策略名稱

        Returns:
            list: 策略名稱列表
        """
        return list(self.signals.keys())
