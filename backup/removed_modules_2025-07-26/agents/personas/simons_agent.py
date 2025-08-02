# -*- coding: utf-8 -*-
"""
西蒙斯代理模組

此模組實現模擬詹姆斯·西蒙斯投資風格的AI代理。

投資哲學：
- 純量化數據驅動決策
- 數學模型和統計分析
- 高頻交易和短期策略
- 機器學習和人工智能
- 風險控制和系統化管理

核心特色：
- 完全依賴數據和模型
- 複雜的數學算法
- 高度自動化交易
- 嚴格的風險管理
- 持續的模型優化
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
import warnings

from ..base import TradingAgent, AgentDecision, InvestmentStyle, RiskPreference

# 設定日誌
logger = logging.getLogger(__name__)

# 忽略sklearn警告
warnings.filterwarnings('ignore', category=UserWarning)


class SimonsAgent(TradingAgent):
    """
    西蒙斯代理 - 模擬詹姆斯·西蒙斯的量化投資風格。
    
    基於純量化方法進行投資決策：
    - 機器學習模型預測
    - 統計套利策略
    - 高頻交易信號
    - 風險因子模型
    - 系統化執行
    
    Attributes:
        model_complexity (int): 模型複雜度
        feature_count (int): 特徵數量
        prediction_horizon (int): 預測時間範圍
        confidence_threshold (float): 信心度閾值
        max_drawdown_limit (float): 最大回撤限制
        rebalance_frequency (int): 再平衡頻率
        model_update_frequency (int): 模型更新頻率
        risk_budget (float): 風險預算
    """
    
    def __init__(
        self,
        name: str = "SimonsAgent",
        model_complexity: int = 100,
        feature_count: int = 50,
        prediction_horizon: int = 5,
        confidence_threshold: float = 0.6,
        max_drawdown_limit: float = 0.05,
        rebalance_frequency: int = 1,  # 每日再平衡
        model_update_frequency: int = 20,  # 每20天更新模型
        risk_budget: float = 0.02,  # 每日2%風險預算
        **parameters: Any
    ) -> None:
        """
        初始化西蒙斯代理。
        
        Args:
            name: 代理名稱
            model_complexity: 模型複雜度（樹的數量）
            feature_count: 特徵數量
            prediction_horizon: 預測時間範圍（天數）
            confidence_threshold: 信心度閾值
            max_drawdown_limit: 最大回撤限制
            rebalance_frequency: 再平衡頻率（天數）
            model_update_frequency: 模型更新頻率（天數）
            risk_budget: 風險預算（日收益率標準差）
            **parameters: 其他策略參數
        """
        super().__init__(
            name=name,
            investment_style=InvestmentStyle.TECHNICAL,  # 使用技術分析作為基礎
            risk_preference=RiskPreference.MODERATE,
            max_position_size=0.1,  # 分散投資
            **parameters
        )
        
        # 西蒙斯特有參數
        self.model_complexity = model_complexity
        self.feature_count = feature_count
        self.prediction_horizon = prediction_horizon
        self.confidence_threshold = confidence_threshold
        self.max_drawdown_limit = max_drawdown_limit
        self.rebalance_frequency = rebalance_frequency
        self.model_update_frequency = model_update_frequency
        self.risk_budget = risk_budget
        
        # 機器學習模型
        self.prediction_model = RandomForestRegressor(
            n_estimators=model_complexity,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.feature_scaler = StandardScaler()
        self.model_trained = False
        self.last_model_update = None
        
        # 特徵工程
        self.feature_names = []
        self.feature_importance = {}
        
        # 風險管理
        self.current_positions: Dict[str, Dict] = {}
        self.portfolio_risk = 0.0
        self.daily_pnl_history = []
        self.max_drawdown_current = 0.0
        
        # 性能追蹤
        self.model_performance = {
            'accuracy': 0.0,
            'sharpe_ratio': 0.0,
            'hit_rate': 0.0,
            'avg_prediction_error': 0.0
        }
        
        logger.info(f"初始化西蒙斯代理: {name} - 'The market is driven by mathematics'")
    
    def make_decision(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """
        基於西蒙斯量化投資哲學生成決策。
        
        Args:
            data: 市場數據
            market_context: 市場上下文信息
            
        Returns:
            AgentDecision: 西蒙斯風格的投資決策
        """
        try:
            symbol = market_context.get('symbol', 'UNKNOWN') if market_context else 'UNKNOWN'
            
            # 檢查數據完整性
            if not self._validate_simons_data(data):
                return self._create_hold_decision(symbol, "西蒙斯：'數據不足，模型無法運行'")
            
            # 特徵工程
            features = self._engineer_features(data)
            
            # 檢查是否需要更新模型
            if self._should_update_model():
                self._update_prediction_model(data)
            
            # 生成預測
            prediction_result = self._generate_predictions(features)
            
            # 風險檢查
            risk_check = self._check_risk_constraints(symbol)
            
            # 信號過濾
            filtered_signals = self._filter_signals(prediction_result, risk_check)
            
            # 倉位計算
            position_sizing = self._calculate_optimal_position(filtered_signals, risk_check)
            
            # 生成西蒙斯風格決策
            decision = self._generate_simons_decision(
                symbol, prediction_result, position_sizing, data
            )
            
            # 更新內部狀態
            self._update_portfolio_state(symbol, decision)
            
            return decision
            
        except Exception as e:
            logger.error(f"西蒙斯代理決策生成失敗: {e}")
            return self._create_hold_decision(symbol, f"西蒙斯：'模型異常，暫停交易' - {e}")
    
    def _validate_simons_data(self, data: pd.DataFrame) -> bool:
        """驗證西蒙斯分析所需數據"""
        # 需要足夠的歷史數據進行特徵工程和模型訓練
        min_periods = max(100, self.feature_count * 2)
        if len(data) < min_periods:
            logger.warning(f"西蒙斯分析需要至少{min_periods}個週期的數據")
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                logger.warning(f"西蒙斯分析缺少必要數據欄位: {col}")
                return False
        
        return True
    
    def _engineer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """特徵工程"""
        features = pd.DataFrame(index=data.index)
        
        # 價格特徵
        features['returns_1d'] = data['close'].pct_change()
        features['returns_5d'] = data['close'].pct_change(5)
        features['returns_20d'] = data['close'].pct_change(20)
        
        # 技術指標特徵
        features['rsi_14'] = self._calculate_rsi(data['close'], 14)
        features['ma_5'] = data['close'].rolling(5).mean()
        features['ma_20'] = data['close'].rolling(20).mean()
        features['ma_ratio'] = features['ma_5'] / features['ma_20']
        
        # 波動率特徵
        features['volatility_5d'] = features['returns_1d'].rolling(5).std()
        features['volatility_20d'] = features['returns_1d'].rolling(20).std()
        features['volatility_ratio'] = features['volatility_5d'] / features['volatility_20d']
        
        # 成交量特徵
        features['volume_ma_5'] = data['volume'].rolling(5).mean()
        features['volume_ma_20'] = data['volume'].rolling(20).mean()
        features['volume_ratio'] = features['volume_ma_5'] / features['volume_ma_20']
        features['volume_price_trend'] = (data['volume'] * data['close']).rolling(5).mean()
        
        # 價格位置特徵
        features['high_low_ratio'] = data['high'] / data['low']
        features['close_position'] = (data['close'] - data['low']) / (data['high'] - data['low'])
        
        # 動量特徵
        features['momentum_5d'] = data['close'] / data['close'].shift(5)
        features['momentum_20d'] = data['close'] / data['close'].shift(20)
        
        # 統計特徵
        features['skewness_20d'] = features['returns_1d'].rolling(20).skew()
        features['kurtosis_20d'] = features['returns_1d'].rolling(20).kurt()
        
        # 相對強度特徵
        features['rs_5d'] = self._calculate_relative_strength(data['close'], 5)
        features['rs_20d'] = self._calculate_relative_strength(data['close'], 20)
        
        # 布林帶特徵
        bb_middle = data['close'].rolling(20).mean()
        bb_std = data['close'].rolling(20).std()
        features['bb_upper'] = bb_middle + 2 * bb_std
        features['bb_lower'] = bb_middle - 2 * bb_std
        features['bb_position'] = (data['close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        
        # MACD特徵
        ema_12 = data['close'].ewm(span=12).mean()
        ema_26 = data['close'].ewm(span=26).mean()
        features['macd'] = ema_12 - ema_26
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        features['macd_histogram'] = features['macd'] - features['macd_signal']
        
        # 清理特徵
        features = features.fillna(method='ffill').fillna(0)
        
        # 限制特徵數量
        if len(features.columns) > self.feature_count:
            # 選擇最重要的特徵
            features = features.iloc[:, :self.feature_count]
        
        self.feature_names = list(features.columns)
        
        return features

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """計算RSI指標"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_relative_strength(self, prices: pd.Series, period: int) -> pd.Series:
        """計算相對強度"""
        return prices / prices.rolling(window=period).mean()

    def _should_update_model(self) -> bool:
        """檢查是否需要更新模型"""
        if not self.model_trained:
            return True

        if self.last_model_update is None:
            return True

        days_since_update = (datetime.now() - self.last_model_update).days
        return days_since_update >= self.model_update_frequency

    def _update_prediction_model(self, data: pd.DataFrame) -> None:
        """更新預測模型"""
        try:
            # 準備訓練數據
            features = self._engineer_features(data)

            # 創建目標變量（未來收益率）
            target = data['close'].pct_change(self.prediction_horizon).shift(-self.prediction_horizon)

            # 對齊數據
            valid_idx = ~(features.isna().any(axis=1) | target.isna())
            X = features[valid_idx]
            y = target[valid_idx]

            if len(X) < 50:  # 需要足夠的訓練數據
                logger.warning("訓練數據不足，跳過模型更新")
                return

            # 標準化特徵
            X_scaled = self.feature_scaler.fit_transform(X)

            # 訓練模型
            self.prediction_model.fit(X_scaled, y)

            # 計算特徵重要性
            self.feature_importance = dict(zip(
                self.feature_names,
                self.prediction_model.feature_importances_
            ))

            # 評估模型性能
            y_pred = self.prediction_model.predict(X_scaled)
            mse = mean_squared_error(y, y_pred)
            correlation = np.corrcoef(y, y_pred)[0, 1] if len(y) > 1 else 0

            self.model_performance.update({
                'accuracy': max(0, correlation),
                'avg_prediction_error': np.sqrt(mse),
                'last_update': datetime.now()
            })

            self.model_trained = True
            self.last_model_update = datetime.now()

            logger.info(f"西蒙斯模型更新完成，準確率: {correlation:.3f}")

        except Exception as e:
            logger.error(f"模型更新失敗: {e}")

    def _generate_predictions(self, features: pd.DataFrame) -> Dict[str, Any]:
        """生成預測"""
        if not self.model_trained or len(features) == 0:
            return {
                'prediction': 0.0,
                'confidence': 0.0,
                'signal_strength': 0.0,
                'prediction_valid': False
            }

        try:
            # 使用最新數據進行預測
            latest_features = features.iloc[-1:].fillna(0)
            X_scaled = self.feature_scaler.transform(latest_features)

            # 生成預測
            prediction = self.prediction_model.predict(X_scaled)[0]

            # 計算預測信心度（基於特徵重要性和模型性能）
            confidence = self._calculate_prediction_confidence(latest_features)

            # 信號強度
            signal_strength = abs(prediction) * confidence

            return {
                'prediction': prediction,
                'confidence': confidence,
                'signal_strength': signal_strength,
                'prediction_valid': confidence >= self.confidence_threshold
            }

        except Exception as e:
            logger.error(f"預測生成失敗: {e}")
            return {
                'prediction': 0.0,
                'confidence': 0.0,
                'signal_strength': 0.0,
                'prediction_valid': False
            }

    def _calculate_prediction_confidence(self, features: pd.DataFrame) -> float:
        """計算預測信心度"""
        # 基於模型性能
        model_confidence = self.model_performance.get('accuracy', 0.0)

        # 基於特徵品質
        feature_quality = self._assess_feature_quality(features)

        # 基於市場制度穩定性
        regime_stability = 0.8  # 簡化實現

        # 綜合信心度
        confidence = (model_confidence * 0.5 + feature_quality * 0.3 + regime_stability * 0.2)

        return min(max(confidence, 0.0), 1.0)

    def _assess_feature_quality(self, features: pd.DataFrame) -> float:
        """評估特徵品質"""
        if features.empty:
            return 0.0

        # 檢查特徵的完整性和穩定性
        feature_completeness = 1.0 - features.isna().sum().sum() / (len(features) * len(features.columns))

        # 檢查特徵值是否在合理範圍內
        feature_stability = 1.0  # 簡化實現

        return (feature_completeness + feature_stability) / 2

    def _check_risk_constraints(self, symbol: str) -> Dict[str, Any]:
        """檢查風險約束"""
        # 檢查當前回撤
        current_drawdown = self._calculate_current_drawdown()

        # 檢查投資組合風險
        portfolio_risk = self._calculate_portfolio_risk()

        # 檢查個股集中度
        position_concentration = self._calculate_position_concentration(symbol)

        # 風險限制檢查
        risk_constraints = {
            'max_drawdown_ok': current_drawdown <= self.max_drawdown_limit,
            'portfolio_risk_ok': portfolio_risk <= self.risk_budget,
            'concentration_ok': position_concentration <= self.max_position_size,
            'overall_risk_ok': True
        }

        risk_constraints['overall_risk_ok'] = all([
            risk_constraints['max_drawdown_ok'],
            risk_constraints['portfolio_risk_ok'],
            risk_constraints['concentration_ok']
        ])

        return {
            'constraints': risk_constraints,
            'current_drawdown': current_drawdown,
            'portfolio_risk': portfolio_risk,
            'position_concentration': position_concentration
        }

    def _calculate_current_drawdown(self) -> float:
        """計算當前回撤"""
        if len(self.daily_pnl_history) < 2:
            return 0.0

        cumulative_pnl = np.cumsum(self.daily_pnl_history)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdowns = (cumulative_pnl - running_max) / np.maximum(running_max, 1)

        return abs(drawdowns[-1]) if len(drawdowns) > 0 else 0.0

    def _calculate_portfolio_risk(self) -> float:
        """計算投資組合風險"""
        if not self.current_positions:
            return 0.0

        # 簡化的風險計算（實際應使用協方差矩陣）
        position_risks = []
        for position_info in self.current_positions.values():
            position_size = position_info.get('size', 0.0)
            position_volatility = position_info.get('volatility', 0.02)
            position_risk = position_size * position_volatility
            position_risks.append(position_risk)

        # 假設相關性為0.5
        portfolio_risk = np.sqrt(np.sum(np.array(position_risks) ** 2) * 1.5)

        return portfolio_risk

    def _calculate_position_concentration(self, symbol: str) -> float:
        """計算個股集中度"""
        if symbol not in self.current_positions:
            return 0.0

        return self.current_positions[symbol].get('size', 0.0)

    def _filter_signals(
        self,
        prediction_result: Dict[str, Any],
        risk_check: Dict[str, Any]
    ) -> Dict[str, Any]:
        """信號過濾"""

        # 基本信號檢查
        signal_valid = prediction_result['prediction_valid']

        # 風險檢查
        risk_ok = risk_check['constraints']['overall_risk_ok']

        # 信號強度檢查
        signal_strong_enough = prediction_result['signal_strength'] > 0.1

        # 綜合過濾結果
        filtered_signal = {
            'signal_valid': signal_valid and risk_ok and signal_strong_enough,
            'prediction': prediction_result['prediction'],
            'confidence': prediction_result['confidence'],
            'signal_strength': prediction_result['signal_strength'],
            'risk_adjusted_strength': prediction_result['signal_strength'] * (1.0 if risk_ok else 0.5)
        }

        return filtered_signal

    def _calculate_optimal_position(
        self,
        filtered_signals: Dict[str, Any],
        risk_check: Dict[str, Any]
    ) -> Dict[str, Any]:
        """計算最優倉位"""

        if not filtered_signals['signal_valid']:
            return {
                'target_position': 0.0,
                'position_change': 0.0,
                'sizing_method': 'no_signal'
            }

        # Kelly公式倉位計算
        kelly_position = self._calculate_kelly_position(filtered_signals)

        # 風險預算倉位計算
        risk_budget_position = self._calculate_risk_budget_position(filtered_signals, risk_check)

        # 取較小值（保守）
        target_position = min(kelly_position, risk_budget_position, self.max_position_size)

        # 確保不超過風險限制
        if not risk_check['constraints']['overall_risk_ok']:
            target_position *= 0.5  # 風險過高時減半

        return {
            'target_position': target_position,
            'kelly_position': kelly_position,
            'risk_budget_position': risk_budget_position,
            'sizing_method': 'quantitative_optimal'
        }

    def _calculate_kelly_position(self, signals: Dict[str, Any]) -> float:
        """Kelly公式倉位計算"""
        prediction = signals['prediction']
        confidence = signals['confidence']

        # 簡化的Kelly公式
        # f = (bp - q) / b，其中b是賠率，p是勝率，q是敗率

        # 估算勝率
        win_prob = 0.5 + confidence * 0.3  # 基於信心度調整勝率

        # 估算賠率
        expected_return = abs(prediction)
        odds = expected_return / 0.01  # 假設風險為1%

        # Kelly比例
        kelly_fraction = (odds * win_prob - (1 - win_prob)) / odds
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # 限制在0-25%

        return kelly_fraction

    def _calculate_risk_budget_position(
        self,
        signals: Dict[str, Any],
        risk_check: Dict[str, Any]
    ) -> float:
        """風險預算倉位計算"""

        # 可用風險預算
        available_risk_budget = self.risk_budget - risk_check['portfolio_risk']
        available_risk_budget = max(0, available_risk_budget)

        # 預期波動率
        expected_volatility = 0.02  # 簡化假設2%日波動率

        # 基於風險預算的倉位
        risk_budget_position = available_risk_budget / expected_volatility

        return min(risk_budget_position, self.max_position_size)

    def _generate_simons_decision(
        self,
        symbol: str,
        prediction_result: Dict[str, Any],
        position_sizing: Dict[str, Any],
        data: pd.DataFrame
    ) -> AgentDecision:
        """生成西蒙斯風格的投資決策"""
        current_time = datetime.now()

        target_position = position_sizing['target_position']
        current_position = self.current_positions.get(symbol, {}).get('size', 0.0)

        # 決定操作方向
        if target_position > current_position + 0.01:  # 增加倉位
            action = 1
            confidence = prediction_result['confidence']
            reasoning = self._generate_simons_buy_reasoning(prediction_result, position_sizing)
        elif target_position < current_position - 0.01:  # 減少倉位
            action = -1
            confidence = prediction_result['confidence']
            reasoning = self._generate_simons_sell_reasoning(prediction_result, position_sizing)
        else:  # 維持倉位
            action = 0
            confidence = 0.6
            reasoning = self._generate_simons_hold_reasoning(prediction_result, position_sizing)

        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=current_time,
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            expected_return=abs(prediction_result['prediction']),
            risk_assessment=self._assess_simons_risk(prediction_result),
            position_size=target_position,
            metadata={
                'prediction': prediction_result['prediction'],
                'model_confidence': prediction_result['confidence'],
                'signal_strength': prediction_result['signal_strength'],
                'kelly_position': position_sizing.get('kelly_position', 0.0),
                'risk_budget_position': position_sizing.get('risk_budget_position', 0.0),
                'model_accuracy': self.model_performance.get('accuracy', 0.0),
                'investment_style': 'simons_quant',
                'feature_count': len(self.feature_names),
                'model_last_update': self.last_model_update
            }
        )

    def _generate_simons_buy_reasoning(
        self,
        prediction_result: Dict[str, Any],
        position_sizing: Dict[str, Any]
    ) -> str:
        """生成西蒙斯風格的買入推理"""
        prediction = prediction_result['prediction']
        confidence = prediction_result['confidence']
        model_accuracy = self.model_performance.get('accuracy', 0.0)

        return (f"西蒙斯量化買入：模型預測{prediction:.3f}，"
                f"信心度{confidence:.2f}，模型準確率{model_accuracy:.2f} - "
                "'數學不會說謊，跟隨模型信號'")

    def _generate_simons_sell_reasoning(
        self,
        prediction_result: Dict[str, Any],
        position_sizing: Dict[str, Any]
    ) -> str:
        """生成西蒙斯風格的賣出推理"""
        prediction = prediction_result['prediction']
        confidence = prediction_result['confidence']

        return (f"西蒙斯量化賣出：模型預測{prediction:.3f}，"
                f"信心度{confidence:.2f} - "
                "'嚴格執行模型信號，情緒不干擾決策'")

    def _generate_simons_hold_reasoning(
        self,
        prediction_result: Dict[str, Any],
        position_sizing: Dict[str, Any]
    ) -> str:
        """生成西蒙斯風格的持有推理"""
        signal_strength = prediction_result['signal_strength']

        return (f"西蒙斯量化持有：信號強度{signal_strength:.3f}不足，"
                "維持當前倉位 - '等待明確的數學信號'")

    def _update_portfolio_state(self, symbol: str, decision: AgentDecision) -> None:
        """更新投資組合狀態"""
        if decision.action != 0:  # 有交易行為
            # 更新持倉信息
            if symbol not in self.current_positions:
                self.current_positions[symbol] = {}

            self.current_positions[symbol].update({
                'size': decision.position_size,
                'last_update': datetime.now(),
                'entry_prediction': decision.metadata.get('prediction', 0.0),
                'volatility': 0.02  # 簡化假設
            })

            # 如果倉位為0，移除記錄
            if decision.position_size <= 0.001:
                if symbol in self.current_positions:
                    del self.current_positions[symbol]

    def _create_hold_decision(self, symbol: str, reason: str) -> AgentDecision:
        """創建持有決策"""
        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            symbol=symbol,
            action=0,
            confidence=0.5,
            reasoning=reason,
            expected_return=0.0,
            risk_assessment=0.4,  # 西蒙斯風格風險適中
            position_size=0.0
        )

    def _assess_simons_risk(self, prediction_result: Dict[str, Any]) -> float:
        """評估西蒙斯風格的投資風險"""
        # 基於模型不確定性的風險評估
        model_uncertainty = 1.0 - prediction_result['confidence']

        # 基於預測幅度的風險
        prediction_magnitude_risk = min(abs(prediction_result['prediction']) * 10, 0.5)

        # 基於模型性能的風險
        model_performance_risk = 1.0 - self.model_performance.get('accuracy', 0.5)

        overall_risk = (model_uncertainty * 0.4 +
                       prediction_magnitude_risk * 0.3 +
                       model_performance_risk * 0.3)

        return min(max(overall_risk, 0.1), 0.8)

    def get_investment_philosophy(self) -> str:
        """獲取西蒙斯投資哲學描述"""
        return (
            "西蒙斯投資哲學：'市場是由數學驅動的，通過數據和模型可以發現市場的規律。' "
            "完全依賴量化模型和統計分析，排除人為情緒干擾。"
            f"模型複雜度：{self.model_complexity}；特徵數量：{self.feature_count}；"
            f"預測範圍：{self.prediction_horizon}天；風險預算：{self.risk_budget:.1%}。"
            "核心理念：'數學不會說謊，嚴格執行模型信號。'"
        )

    def get_model_performance(self) -> Dict[str, Any]:
        """獲取模型性能指標"""
        return self.model_performance.copy()

    def get_feature_importance(self) -> Dict[str, float]:
        """獲取特徵重要性"""
        return self.feature_importance.copy()

    def get_simons_insights(self) -> List[str]:
        """獲取西蒙斯投資智慧"""
        return [
            "市場是由數學驅動的，數據中隱藏著規律。",
            "情緒是投資的敵人，只相信數學和統計。",
            "模型比人類更客觀，嚴格執行模型信號。",
            "風險管理是量化投資的核心。",
            "持續優化模型，適應市場變化。",
            "分散投資，不把雞蛋放在一個籃子裡。",
            "數學不會說謊，但要確保數據的品質。",
            "量化投資的優勢在於紀律性和一致性。"
        ]

    def update_daily_pnl(self, pnl: float) -> None:
        """更新每日損益"""
        self.daily_pnl_history.append(pnl)

        # 保持歷史記錄在合理範圍內
        if len(self.daily_pnl_history) > 252:  # 保留一年數據
            self.daily_pnl_history = self.daily_pnl_history[-252:]

    def __str__(self) -> str:
        """字符串表示"""
        return f"SimonsAgent(positions={len(self.current_positions)}, model_trained={self.model_trained})"
