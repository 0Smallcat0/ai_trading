"""AI模型訊號產生器

此模組實現基於機器學習模型的交易訊號生成功能。
"""

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .base_signal_generator import BaseSignalGenerator, LOG_MSGS, MODEL_INTEGRATION_AVAILABLE

logger = logging.getLogger(__name__)


class AIModelSignalGenerator(BaseSignalGenerator):
    """AI模型訊號產生器

    基於機器學習模型生成交易訊號。
    """

    def generate_signals(
        self,
        model_name: str = "default",
        confidence_threshold: float = 0.6,
        **kwargs  # pylint: disable=unused-argument
    ) -> pd.DataFrame:
        """生成AI模型策略訊號

        使用機器學習模型預測價格走勢並生成訊號

        Args:
            model_name (str): 模型名稱
            confidence_threshold (float): 信心度閾值，超過此值才生成訊號
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        # 驗證前置條件
        if not self._validate_model_prerequisites():
            return pd.DataFrame()

        try:
            # 準備特徵數據
            features = self._prepare_features()
            if features.empty:
                logger.warning("無法準備特徵數據")
                return pd.DataFrame()

            # 使用模型進行預測
            predictions = self.model_manager.predict(features, model_name)

            # 生成訊號
            signals = self._create_signals_from_predictions(
                predictions, features, confidence_threshold, model_name
            )

            # 儲存訊號
            self.signals["ai_model"] = signals
            return signals

        except Exception as e:
            logger.error(LOG_MSGS["model_error"], str(e))
            return pd.DataFrame()

    def _validate_model_prerequisites(self) -> bool:
        """驗證模型前置條件

        Returns:
            bool: 是否滿足前置條件
        """
        if not MODEL_INTEGRATION_AVAILABLE:
            logger.warning(LOG_MSGS["model_integration_missing"])
            return False

        if self.model_manager is None:
            logger.warning(LOG_MSGS["no_model"])
            return False

        if not self.validate_data('price'):
            logger.warning(LOG_MSGS["no_price"], "AI模型")
            return False

        return True

    def _create_signals_from_predictions(
        self,
        predictions: np.ndarray,
        features: pd.DataFrame,
        confidence_threshold: float,
        model_name: str
    ) -> pd.DataFrame:
        """從預測結果創建訊號

        Args:
            predictions: 模型預測結果
            features: 特徵數據
            confidence_threshold: 信心度閾值
            model_name: 模型名稱

        Returns:
            pd.DataFrame: 訊號數據
        """
        # 初始化訊號
        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0
        signals["confidence"] = 0.0

        if not isinstance(predictions, np.ndarray) or len(predictions) == 0:
            logger.warning("模型 %s 返回無效的預測結果", model_name)
            return signals

        # 確保預測結果與特徵索引對應
        min_length = min(len(predictions), len(features))

        for i in range(min_length):
            idx = features.index[i]
            prediction = float(predictions[i])
            confidence = abs(prediction)  # 使用絕對值作為信心度

            if confidence >= confidence_threshold:
                if prediction > 0.1:  # 預測上漲
                    signals.loc[idx, "signal"] = 1
                elif prediction < -0.1:  # 預測下跌
                    signals.loc[idx, "signal"] = -1

                signals.loc[idx, "confidence"] = confidence

        return signals

    def generate_ensemble_signals(
        self,
        model_names: Optional[List[str]] = None,
        voting_method: str = "weighted",
        **kwargs  # pylint: disable=unused-argument
    ) -> pd.DataFrame:
        """生成集成模型訊號

        使用多個模型的集成預測生成訊號

        Args:
            model_names (list): 模型名稱列表
            voting_method (str): 投票方法 ('majority', 'weighted', 'average')
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 集成訊號
        """
        if not MODEL_INTEGRATION_AVAILABLE or self.model_manager is None:
            logger.warning(LOG_MSGS["no_model"])
            return pd.DataFrame()

        if model_names is None:
            model_names = self.model_manager.list_models()

        if not model_names:
            logger.warning("沒有可用的模型")
            return pd.DataFrame()

        # 準備特徵數據
        features = self._prepare_features()
        if features.empty:
            return pd.DataFrame()

        # 收集所有模型的預測
        all_predictions = {}
        all_confidences = {}

        for model_name in model_names:
            try:
                predictions = self.model_manager.predict(features, model_name)
                all_predictions[model_name] = predictions

                # 獲取模型性能作為權重
                model_performance = self.model_manager.get_model_performance(model_name)
                all_confidences[model_name] = model_performance.get('accuracy', 0.5)

            except Exception as e:
                logger.warning("模型 %s 預測失敗: %s", model_name, e)

        if not all_predictions:
            logger.warning("所有模型預測都失敗")
            return pd.DataFrame()

        # 初始化訊號
        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0
        signals["confidence"] = 0.0

        # 根據投票方法合併預測
        if voting_method == "majority":
            signals = self._majority_voting(all_predictions, signals)
        elif voting_method == "weighted":
            signals = self._weighted_voting(all_predictions, all_confidences, signals)
        elif voting_method == "average":
            signals = self._average_voting(all_predictions, signals)

        # 儲存訊號
        self.signals["ensemble"] = signals

        return signals

    def generate_adaptive_signals(
        self,
        lookback_period: int = 30,
        rebalance_frequency: int = 5,
        **kwargs  # pylint: disable=unused-argument
    ) -> pd.DataFrame:
        """生成自適應模型訊號

        根據最近表現動態調整模型權重

        Args:
            lookback_period (int): 回看期間
            rebalance_frequency (int): 重新平衡頻率
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 自適應訊號
        """
        if not MODEL_INTEGRATION_AVAILABLE or self.model_manager is None:
            logger.warning(LOG_MSGS["no_model"])
            return pd.DataFrame()

        # 準備特徵數據
        features = self._prepare_features()
        if features.empty:
            return pd.DataFrame()

        # 獲取所有可用模型
        model_names = self.model_manager.list_models()
        if not model_names:
            return pd.DataFrame()

        # 初始化訊號
        signals = pd.DataFrame(index=self.price_data.index)
        signals["signal"] = 0
        signals["confidence"] = 0.0

        # 動態權重調整
        model_weights = {name: 1.0 / len(model_names) for name in model_names}

        for i, idx in enumerate(features.index):
            # 每隔一定期間重新計算權重
            if not i % rebalance_frequency and i > lookback_period:
                model_weights = self._update_model_weights(
                    model_names, features.iloc[max(0, i-lookback_period):i],
                    signals.iloc[max(0, i-lookback_period):i]
                )

            # 使用當前權重進行預測
            weighted_prediction = 0.0
            total_weight = 0.0

            for model_name in model_names:
                try:
                    prediction = self.model_manager.predict_single(
                        model_name, features.loc[idx:idx]
                    )
                    weight = model_weights.get(model_name, 0.0)
                    weighted_prediction += prediction * weight
                    total_weight += weight
                except Exception as e:
                    logger.warning("模型 %s 單次預測失敗: %s", model_name, e)

            # 生成訊號
            if total_weight > 0:
                final_prediction = weighted_prediction / total_weight
                if final_prediction > 0.3:
                    signals.loc[idx, "signal"] = 1
                elif final_prediction < -0.3:
                    signals.loc[idx, "signal"] = -1

                signals.loc[idx, "confidence"] = abs(final_prediction)

        # 儲存訊號
        self.signals["adaptive"] = signals

        return signals

    def _prepare_features(self) -> pd.DataFrame:
        """準備模型特徵數據

        Returns:
            pd.DataFrame: 特徵數據
        """
        features = pd.DataFrame(index=self.price_data.index)

        # 價格特徵
        if self.price_data is not None:
            price_data = self.price_data.copy()

            # 基本價格特徵
            features["close"] = price_data["close"]
            features["high"] = price_data["high"]
            features["low"] = price_data["low"]
            features["volume"] = price_data.get("volume", 0)

            # 技術指標特徵
            if self.tech_indicators is not None:
                try:
                    features["sma_20"] = self.tech_indicators.calculate_sma(20)
                    features["rsi_14"] = self.tech_indicators.calculate_rsi(14)
                    macd, signal, _ = self.tech_indicators.calculate_macd()
                    features["macd"] = macd
                    features["macd_signal"] = signal
                except Exception as e:
                    logger.warning("計算技術指標特徵時發生錯誤: %s", e)

        # 基本面特徵
        if self.fund_indicators is not None:
            try:
                features["pe_ratio"] = self.fund_indicators.calculate_pe_ratio()
                features["pb_ratio"] = self.fund_indicators.calculate_pb_ratio()
            except Exception as e:
                logger.warning("計算基本面特徵時發生錯誤: %s", e)

        # 情緒特徵
        if self.sent_indicators is not None:
            try:
                features["news_sentiment"] = self.sent_indicators.calculate_news_sentiment()
            except Exception as e:
                logger.warning("計算情緒特徵時發生錯誤: %s", e)

        # 移除包含 NaN 的行
        features = features.dropna()

        return features

    def _majority_voting(self, predictions: Dict[str, np.ndarray], signals: pd.DataFrame) -> pd.DataFrame:
        """多數投票法"""
        # 獲取所有模型預測的最小長度
        min_length = min(len(pred) for pred in predictions.values() if isinstance(pred, np.ndarray))

        for i in range(min_length):
            votes = []
            for model_predictions in predictions.values():
                if isinstance(model_predictions, np.ndarray) and i < len(model_predictions):
                    pred = float(model_predictions[i])
                    if pred > 0.1:
                        votes.append(1)
                    elif pred < -0.1:
                        votes.append(-1)
                    else:
                        votes.append(0)

            if votes and i < len(signals):
                idx = signals.index[i]
                signals.loc[idx, "signal"] = max(set(votes), key=votes.count)
                signals.loc[idx, "confidence"] = len(votes) / len(predictions)

        return signals

    def _weighted_voting(self, predictions: Dict[str, np.ndarray], weights: Dict[str, float], signals: pd.DataFrame) -> pd.DataFrame:
        """加權投票法"""
        # 獲取所有模型預測的最小長度
        min_length = min(len(pred) for pred in predictions.values() if isinstance(pred, np.ndarray))

        for i in range(min_length):
            weighted_sum = 0.0
            total_weight = 0.0

            for model_name, model_predictions in predictions.items():
                if isinstance(model_predictions, np.ndarray) and i < len(model_predictions):
                    pred = float(model_predictions[i])
                    conf = abs(pred)  # 使用絕對值作為信心度
                    weight = weights.get(model_name, 0.5)
                    weighted_sum += pred * weight * conf
                    total_weight += weight

            if total_weight > 0 and i < len(signals):
                idx = signals.index[i]
                final_pred = weighted_sum / total_weight
                if final_pred > 0.1:
                    signals.loc[idx, "signal"] = 1
                elif final_pred < -0.1:
                    signals.loc[idx, "signal"] = -1

                signals.loc[idx, "confidence"] = min(abs(final_pred), 1.0)

        return signals

    def _average_voting(self, predictions: Dict[str, np.ndarray], signals: pd.DataFrame) -> pd.DataFrame:
        """平均投票法"""
        # 獲取所有模型預測的最小長度
        min_length = min(len(pred) for pred in predictions.values() if isinstance(pred, np.ndarray))

        for i in range(min_length):
            pred_sum = 0.0
            count = 0

            for model_predictions in predictions.values():
                if isinstance(model_predictions, np.ndarray) and i < len(model_predictions):
                    pred = float(model_predictions[i])
                    pred_sum += pred
                    count += 1

            if count > 0 and i < len(signals):
                idx = signals.index[i]
                avg_pred = pred_sum / count
                if avg_pred > 0.1:
                    signals.loc[idx, "signal"] = 1
                elif avg_pred < -0.1:
                    signals.loc[idx, "signal"] = -1

                signals.loc[idx, "confidence"] = min(abs(avg_pred), 1.0)

        return signals

    def _update_model_weights(
        self,
        model_names: List[str],
        features: pd.DataFrame,  # pylint: disable=unused-argument
        historical_signals: pd.DataFrame  # pylint: disable=unused-argument
    ) -> Dict[str, float]:
        """更新模型權重"""
        # 簡化的權重更新邏輯
        # 實際應用中可以根據模型的歷史表現來調整
        weights = {}
        for model_name in model_names:
            try:
                # 獲取模型最近的表現
                performance = self.model_manager.get_model_performance(model_name)
                weights[model_name] = performance.get('accuracy', 0.5)
            except Exception:
                weights[model_name] = 0.5

        # 正規化權重
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        return weights

    def generate_all_ai_signals(self, **kwargs) -> Dict[str, pd.DataFrame]:
        """生成所有AI模型訊號

        Args:
            **kwargs: 各種策略的參數

        Returns:
            dict: 包含所有AI模型訊號的字典
        """
        signals_dict = {}

        # 生成基本AI模型訊號
        signals_dict["ai_model"] = self.generate_signals(**kwargs)

        # 生成集成模型訊號
        signals_dict["ensemble"] = self.generate_ensemble_signals(**kwargs)

        # 生成自適應模型訊號
        signals_dict["adaptive"] = self.generate_adaptive_signals(**kwargs)

        return signals_dict
