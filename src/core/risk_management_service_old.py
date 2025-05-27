"""
風險管理服務模組

此模組提供風險管理的核心服務功能，包括：
- 風險參數管理
- 風險指標監控
- 風險事件處理
- 風控機制控制
- 風險日誌管理

整合各種風險管理模組，提供統一的風險管理介面。
"""

import logging
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 導入專案模組
try:
    from src.config import DB_URL
    from src.database.schema import (
        RiskParameter,
        RiskEvent,
        RiskMetric,
        RiskControlStatus,
        init_db,
    )
    from src.risk_management.risk_manager import risk_manager
    from src.risk_management.risk_metrics import RiskMetricsCalculator
except ImportError as e:
    logging.warning("無法導入部分模組: %s", e)

    # 定義一個簡單的 init_db 函數作為備用
    def init_db(engine):  # pylint: disable=unused-argument
        """簡單的資料庫初始化函數"""
        pass


logger = logging.getLogger(__name__)


class RiskManagementService:
    """風險管理服務類別"""

    def __init__(self):
        """初始化風險管理服務"""
        self.engine = None
        self.session_factory = None
        self.risk_parameters = {}
        self.control_status = {}
        self.lock = threading.Lock()

        # 初始化資料庫連接
        self._init_database()

        # 初始化預設風險參數
        self._init_default_parameters()

        # 初始化風控機制狀態
        self._init_control_status()

    def _init_database(self):
        """初始化資料庫連接"""
        try:
            self.engine = create_engine(DB_URL)
            self.session_factory = sessionmaker(bind=self.engine)
            # 初始化資料庫結構
            init_db(self.engine)
            logger.info("風險管理服務資料庫連接初始化成功")
        except Exception as e:
            logger.error("風險管理服務資料庫連接初始化失敗: %s", e)
            raise

    def _init_default_parameters(self):
        """初始化預設風險參數"""
        default_params = {
            # 停損/停利參數
            "stop_loss_enabled": {
                "value": "true",
                "type": "bool",
                "category": "stop_loss",
                "description": "啟用停損",
            },
            "stop_loss_percent": {
                "value": "5.0",
                "type": "float",
                "category": "stop_loss",
                "description": "停損百分比",
            },
            "take_profit_enabled": {
                "value": "true",
                "type": "bool",
                "category": "take_profit",
                "description": "啟用停利",
            },
            "take_profit_percent": {
                "value": "10.0",
                "type": "float",
                "category": "take_profit",
                "description": "停利百分比",
            },
            # 資金控管參數
            "max_portfolio_risk": {
                "value": "2.0",
                "type": "float",
                "category": "position",
                "description": "最大投資組合風險",
            },
            "max_position_size": {
                "value": "10.0",
                "type": "float",
                "category": "position",
                "description": "最大單一部位比例",
            },
            "max_daily_loss": {
                "value": "5.0",
                "type": "float",
                "category": "position",
                "description": "最大日損失",
            },
            # VaR 參數
            "var_confidence": {
                "value": "95.0",
                "type": "float",
                "category": "var",
                "description": "VaR 信心水準",
            },
            "var_method": {
                "value": "歷史模擬法",
                "type": "string",
                "category": "var",
                "description": "VaR 計算方法",
            },
            "var_lookback_days": {
                "value": "252",
                "type": "int",
                "category": "var",
                "description": "VaR 回顧天數",
            },
            # 監控參數
            "real_time_monitoring": {
                "value": "true",
                "type": "bool",
                "category": "monitoring",
                "description": "即時監控",
            },
            "alert_threshold_var": {
                "value": "2.0",
                "type": "float",
                "category": "monitoring",
                "description": "VaR 警報閾值",
            },
            "alert_threshold_drawdown": {
                "value": "10.0",
                "type": "float",
                "category": "monitoring",
                "description": "回撤警報閾值",
            },
        }

        try:
            with self.session_factory() as session:
                for param_name, param_info in default_params.items():
                    # 檢查參數是否已存在
                    existing = (
                        session.query(RiskParameter)
                        .filter_by(parameter_name=param_name)
                        .first()
                    )
                    if not existing:
                        param = RiskParameter(
                            parameter_name=param_name,
                            parameter_value=param_info["value"],
                            parameter_type=param_info["type"],
                            category=param_info["category"],
                            description=param_info["description"],
                            is_system=True,
                        )
                        session.add(param)

                session.commit()
                logger.info("預設風險參數初始化完成")
        except Exception as e:
            logger.error("初始化預設風險參數失敗: %s", e)

    def _init_control_status(self):
        """初始化風控機制狀態"""
        default_controls = {
            "stop_loss": {"type": "stop_loss", "enabled": True},
            "take_profit": {"type": "take_profit", "enabled": True},
            "position_limit": {"type": "position", "enabled": True},
            "var_monitoring": {"type": "var", "enabled": True},
            "drawdown_protection": {"type": "drawdown", "enabled": True},
            "correlation_check": {"type": "correlation", "enabled": True},
            "sector_limit": {"type": "sector", "enabled": True},
        }

        try:
            with self.session_factory() as session:
                for control_name, control_info in default_controls.items():
                    # 檢查控制機制是否已存在
                    existing = (
                        session.query(RiskControlStatus)
                        .filter_by(control_name=control_name)
                        .first()
                    )
                    if not existing:
                        control = RiskControlStatus(
                            control_name=control_name,
                            control_type=control_info["type"],
                            is_enabled=control_info["enabled"],
                            is_master_enabled=True,
                            emergency_stop=False,
                        )
                        session.add(control)

                session.commit()
                logger.info("風控機制狀態初始化完成")
        except Exception as e:
            logger.error("初始化風控機制狀態失敗: %s", e)

    def get_risk_parameters(self, category: Optional[str] = None) -> Dict[str, Any]:
        """獲取風險參數"""
        try:
            with self.session_factory() as session:
                query = session.query(RiskParameter).filter_by(is_active=True)
                if category:
                    query = query.filter_by(category=category)

                parameters = query.all()

                result = {}
                for param in parameters:
                    # 根據類型轉換值
                    value = param.parameter_value
                    if param.parameter_type == "float":
                        value = float(value)
                    elif param.parameter_type == "int":
                        value = int(value)
                    elif param.parameter_type == "bool":
                        value = value.lower() == "true"

                    result[param.parameter_name] = {
                        "value": value,
                        "type": param.parameter_type,
                        "category": param.category,
                        "description": param.description,
                        "min_value": param.min_value,
                        "max_value": param.max_value,
                        "default_value": param.default_value,
                    }

                return result
        except Exception as e:
            logger.error(f"獲取風險參數失敗: {e}")
            return {}

    def update_risk_parameter(self, parameter_name: str, value: Any) -> bool:
        """更新風險參數"""
        try:
            with self.session_factory() as session:
                param = (
                    session.query(RiskParameter)
                    .filter_by(parameter_name=parameter_name)
                    .first()
                )
                if not param:
                    logger.warning(f"風險參數 '{parameter_name}' 不存在")
                    return False

                # 轉換值為字串儲存
                param.parameter_value = str(value)
                param.updated_at = datetime.now()

                session.commit()
                logger.info(f"風險參數 '{parameter_name}' 已更新為 '{value}'")
                return True
        except Exception as e:
            logger.error(f"更新風險參數失敗: {e}")
            return False

    def get_control_status(self) -> Dict[str, Any]:
        """獲取風控機制狀態"""
        try:
            with self.session_factory() as session:
                controls = session.query(RiskControlStatus).all()

                result = {}
                for control in controls:
                    result[control.control_name] = {
                        "type": control.control_type,
                        "enabled": control.is_enabled,
                        "master_enabled": control.is_master_enabled,
                        "emergency_stop": control.emergency_stop,
                        "config": control.config_json,
                        "thresholds": control.threshold_values,
                        "last_check": control.last_check_time,
                        "last_trigger": control.last_trigger_time,
                        "trigger_count": control.trigger_count,
                    }

                return result
        except Exception as e:
            logger.error(f"獲取風控機制狀態失敗: {e}")
            return {}

    def update_control_status(
        self, control_name: str, enabled: bool, config: Optional[Dict] = None
    ) -> bool:
        """更新風控機制狀態"""
        try:
            with self.session_factory() as session:
                control = (
                    session.query(RiskControlStatus)
                    .filter_by(control_name=control_name)
                    .first()
                )
                if not control:
                    logger.warning(f"風控機制 '{control_name}' 不存在")
                    return False

                control.is_enabled = enabled
                if config:
                    control.config_json = config
                control.updated_at = datetime.now()

                session.commit()
                logger.info(f"風控機制 '{control_name}' 狀態已更新")
                return True
        except Exception as e:
            logger.error(f"更新風控機制狀態失敗: {e}")
            return False

    def set_emergency_stop(self, enabled: bool) -> bool:
        """設置緊急停止狀態"""
        try:
            with self.session_factory() as session:
                # 更新所有風控機制的緊急停止狀態
                session.query(RiskControlStatus).update({"emergency_stop": enabled})
                session.commit()

                # 同時更新風險管理器的交易狀態
                if enabled:
                    risk_manager.stop_trading("緊急停止啟動")
                else:
                    risk_manager.resume_trading("緊急停止解除")

                logger.info(f"緊急停止狀態已設置為: {enabled}")
                return True
        except Exception as e:
            logger.error(f"設置緊急停止狀態失敗: {e}")
            return False

    def create_risk_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        symbol: Optional[str] = None,
        strategy_name: Optional[str] = None,
        trigger_value: Optional[float] = None,
        threshold_value: Optional[float] = None,
        current_value: Optional[float] = None,
        details: Optional[Dict] = None,
    ) -> str:
        """創建風險事件"""
        try:
            event_id = str(uuid.uuid4())

            with self.session_factory() as session:
                event = RiskEvent(
                    event_id=event_id,
                    timestamp=datetime.now(),
                    event_type=event_type,
                    severity=severity,
                    symbol=symbol,
                    strategy_name=strategy_name,
                    trigger_value=trigger_value,
                    threshold_value=threshold_value,
                    current_value=current_value,
                    message=message,
                    details=details,
                    status="pending",
                )
                session.add(event)
                session.commit()

                logger.info(f"風險事件已創建: {event_id} - {event_type}")
                return event_id
        except Exception as e:
            logger.error(f"創建風險事件失敗: {e}")
            return ""

    def get_risk_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """獲取風險事件列表"""
        try:
            with self.session_factory() as session:
                query = session.query(RiskEvent)

                # 應用篩選條件
                if event_type:
                    query = query.filter(RiskEvent.event_type == event_type)
                if severity:
                    query = query.filter(RiskEvent.severity == severity)
                if status:
                    query = query.filter(RiskEvent.status == status)
                if symbol:
                    query = query.filter(RiskEvent.symbol == symbol)
                if start_date:
                    query = query.filter(RiskEvent.timestamp >= start_date)
                if end_date:
                    query = query.filter(RiskEvent.timestamp <= end_date)

                # 按時間降序排序並限制數量
                events = query.order_by(RiskEvent.timestamp.desc()).limit(limit).all()

                result = []
                for event in events:
                    result.append(
                        {
                            "event_id": event.event_id,
                            "timestamp": event.timestamp.isoformat(),
                            "event_type": event.event_type,
                            "severity": event.severity,
                            "symbol": event.symbol,
                            "strategy_name": event.strategy_name,
                            "trigger_value": event.trigger_value,
                            "threshold_value": event.threshold_value,
                            "current_value": event.current_value,
                            "message": event.message,
                            "details": event.details,
                            "status": event.status,
                            "action_taken": event.action_taken,
                            "resolved_at": (
                                event.resolved_at.isoformat()
                                if event.resolved_at
                                else None
                            ),
                            "resolved_by": event.resolved_by,
                        }
                    )

                return result
        except Exception as e:
            logger.error(f"獲取風險事件失敗: {e}")
            return []

    def resolve_risk_event(
        self, event_id: str, action_taken: str, resolved_by: str = "system"
    ) -> bool:
        """解決風險事件"""
        try:
            with self.session_factory() as session:
                event = session.query(RiskEvent).filter_by(event_id=event_id).first()
                if not event:
                    logger.warning(f"風險事件 '{event_id}' 不存在")
                    return False

                event.status = "resolved"
                event.action_taken = action_taken
                event.resolved_at = datetime.now()
                event.resolved_by = resolved_by
                event.updated_at = datetime.now()

                session.commit()
                logger.info(f"風險事件 '{event_id}' 已解決")
                return True
        except Exception as e:
            logger.error(f"解決風險事件失敗: {e}")
            return False

    def calculate_risk_metrics(
        self, symbol: Optional[str] = None, lookback_days: int = 252
    ) -> Dict[str, float]:
        """計算風險指標"""
        try:
            # 獲取歷史價格數據
            returns_data = self._get_returns_data(symbol, lookback_days)
            if returns_data.empty:
                logger.warning(f"無法獲取 {symbol} 的歷史數據")
                return {}

            # 計算風險指標
            calculator = RiskMetricsCalculator(
                returns_data["returns"], risk_free_rate=0.0
            )
            metrics = calculator.calculate_all_metrics()

            # 儲存到資料庫
            self._save_risk_metrics(symbol, metrics, lookback_days)

            return metrics
        except Exception as e:
            logger.error(f"計算風險指標失敗: {e}")
            return {}

    def _get_returns_data(
        self, symbol: Optional[str], lookback_days: int
    ) -> pd.DataFrame:
        """獲取收益率數據"""
        try:
            with self.session_factory() as session:
                # 計算開始日期
                end_date = datetime.now().date()
                start_date = end_date - timedelta(
                    days=lookback_days + 30
                )  # 多取一些數據以確保足夠

                if symbol:
                    # 獲取特定股票的數據
                    query = text(
                        """
                        SELECT date, close
                        FROM market_daily
                        WHERE symbol = :symbol
                        AND date BETWEEN :start_date AND :end_date
                        ORDER BY date
                    """
                    )
                    result = session.execute(
                        query,
                        {
                            "symbol": symbol,
                            "start_date": start_date,
                            "end_date": end_date,
                        },
                    ).fetchall()
                else:
                    # 獲取投資組合整體數據（這裡需要根據實際投資組合計算）
                    # 暫時使用模擬數據
                    np.random.seed(42)
                    dates = pd.date_range(end=end_date, periods=lookback_days, freq="D")
                    prices = 100 * np.cumprod(
                        1 + np.random.normal(0.0008, 0.015, lookback_days)
                    )
                    result = [
                        (date.date(), price) for date, price in zip(dates, prices)
                    ]

                if not result:
                    return pd.DataFrame()

                # 轉換為 DataFrame
                df = pd.DataFrame(result, columns=["date", "close"])
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date")

                # 計算收益率
                df["returns"] = df["close"].pct_change().dropna()

                return df.dropna()
        except Exception as e:
            logger.error(f"獲取收益率數據失敗: {e}")
            return pd.DataFrame()

    def _save_risk_metrics(
        self, symbol: Optional[str], metrics: Dict[str, float], lookback_days: int
    ):
        """儲存風險指標到資料庫"""
        try:
            with self.session_factory() as session:
                # 檢查今日是否已有記錄
                today = datetime.now().date()
                existing = (
                    session.query(RiskMetric)
                    .filter_by(date=today, symbol=symbol)
                    .first()
                )

                if existing:
                    # 更新現有記錄
                    for key, value in metrics.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.lookback_days = lookback_days
                    existing.updated_at = datetime.now()
                else:
                    # 創建新記錄
                    metric = RiskMetric(
                        date=today,
                        symbol=symbol,
                        lookback_days=lookback_days,
                        calculation_method="歷史模擬法",
                        confidence_level=95.0,
                        **{k: v for k, v in metrics.items() if hasattr(RiskMetric, k)},
                    )
                    session.add(metric)

                session.commit()
                logger.info(f"風險指標已儲存: {symbol or '投資組合'}")
        except Exception as e:
            logger.error(f"儲存風險指標失敗: {e}")

    def get_risk_metrics_history(
        self, symbol: Optional[str] = None, days: int = 30
    ) -> List[Dict[str, Any]]:
        """獲取風險指標歷史記錄"""
        try:
            with self.session_factory() as session:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days)

                query = session.query(RiskMetric).filter(
                    RiskMetric.date >= start_date, RiskMetric.date <= end_date
                )

                if symbol:
                    query = query.filter(RiskMetric.symbol == symbol)
                else:
                    query = query.filter(RiskMetric.symbol.is_(None))

                metrics = query.order_by(RiskMetric.date.desc()).all()

                result = []
                for metric in metrics:
                    result.append(
                        {
                            "date": metric.date.isoformat(),
                            "symbol": metric.symbol,
                            "var_95_1day": metric.var_95_1day,
                            "var_99_1day": metric.var_99_1day,
                            "cvar_95_1day": metric.cvar_95_1day,
                            "max_drawdown": metric.max_drawdown,
                            "current_drawdown": metric.current_drawdown,
                            "volatility": metric.volatility,
                            "sharpe_ratio": metric.sharpe_ratio,
                            "sortino_ratio": metric.sortino_ratio,
                            "beta": metric.beta,
                            "correlation_with_market": metric.correlation_with_market,
                            "position_concentration": metric.position_concentration,
                            "sector_concentration": metric.sector_concentration,
                        }
                    )

                return result
        except Exception as e:
            logger.error(f"獲取風險指標歷史記錄失敗: {e}")
            return []
