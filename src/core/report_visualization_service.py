"""報表視覺化服務 - 重構版本

此模組提供完整的報表視覺化功能，整合了各個子模組：
- 數據檢索服務
- 圖表生成服務
- 報表匯出服務
- 配置管理服務

採用模組化架構，提高代碼可維護性和可擴展性。
"""

import logging
from typing import Dict, List, Optional, Any, Union, Tuple

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import DB_URL
from .visualization import (
    DataRetrievalService,
    ChartGeneratorService,
    ReportExporterService,
    ConfigManagementService,
)

logger = logging.getLogger(__name__)


class ReportVisualizationService:
    """報表視覺化服務 - 重構版本

    整合各個子服務，提供統一的報表視覺化接口。
    """

    def __init__(self, db_url: Optional[str] = None):
        """初始化報表視覺化服務

        Args:
            db_url: 資料庫連接字串，如果為 None 則使用配置中的預設值
        """
        try:
            # 延遲初始化資料庫連接
            self._db_url = db_url or DB_URL
            self._engine = None
            self._session_factory = None

            # 延遲初始化子服務
            self._data_service = None
            self._chart_service = None
            self._export_service = None
            self._config_service = None

            # 預設配置
            self.cache_enabled = True
            self.default_cache_duration = 300
            self.default_chart_config = {
                "plotly": {"template": "plotly_white", "height": 400},
                "matplotlib": {"style": "seaborn-v0_8", "figsize": (12, 6)},
            }

            logger.info("報表視覺化服務初始化完成（延遲載入模式）")

        except Exception as e:
            logger.error("報表視覺化服務初始化失敗: %s", e)
            raise

    @property
    def engine(self):
        """獲取資料庫引擎（延遲初始化）"""
        if self._engine is None:
            self._engine = create_engine(self._db_url)
            logger.info("資料庫引擎初始化成功")
        return self._engine

    @property
    def session_factory(self):
        """獲取 session factory（延遲初始化）"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
            logger.info("Session factory 初始化成功")
        return self._session_factory

    @property
    def data_service(self):
        """獲取數據服務（延遲初始化）"""
        if self._data_service is None:
            self._data_service = DataRetrievalService(self.session_factory)
        return self._data_service

    @property
    def chart_service(self):
        """獲取圖表服務（延遲初始化）"""
        if self._chart_service is None:
            self._chart_service = ChartGeneratorService()
        return self._chart_service

    @property
    def export_service(self):
        """獲取匯出服務（延遲初始化）"""
        if self._export_service is None:
            self._export_service = ReportExporterService(self.session_factory)
        return self._export_service

    @property
    def config_service(self):
        """獲取配置服務（延遲初始化）"""
        if self._config_service is None:
            self._config_service = ConfigManagementService(self.session_factory)
            # 更新配置屬性
            self.cache_enabled = self._config_service.cache_enabled
            self.default_cache_duration = self._config_service.default_cache_duration
            self.default_chart_config = self._config_service.default_chart_config
        return self._config_service

    # ==================== 數據檢索方法 ====================

    def get_trading_performance_data(
        self,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        strategy_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """獲取交易績效數據

        Args:
            start_date: 開始日期
            end_date: 結束日期
            strategy_name: 策略名稱

        Returns:
            包含交易績效數據的字典
        """
        return self.data_service.get_trading_performance_data(
            start_date, end_date, strategy_name
        )

    def get_trade_details_data(
        self,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        symbol: Optional[str] = None,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """獲取交易明細數據

        Args:
            start_date: 開始日期
            end_date: 結束日期
            symbol: 股票代碼
            limit: 限制筆數

        Returns:
            包含交易明細數據的字典
        """
        return self.data_service.get_trade_details_data(
            start_date, end_date, symbol, limit
        )

    def compare_strategies_performance(
        self,
        strategy_names: List[str],
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """比較策略績效

        Args:
            strategy_names: 策略名稱列表
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            包含策略比較數據的字典
        """
        return self.data_service.compare_strategies_performance(
            strategy_names, start_date, end_date
        )

    # ==================== 圖表生成方法 ====================

    def generate_cumulative_return_chart(
        self, data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[Any, None]:
        """生成累積報酬圖表

        Args:
            data: 包含交易數據的字典
            chart_type: 圖表類型

        Returns:
            圖表對象或 None
        """
        return self.chart_service.generate_cumulative_return_chart(data, chart_type)

    def generate_drawdown_chart(
        self, data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[Any, None]:
        """生成回撤圖表

        Args:
            data: 包含交易數據的字典
            chart_type: 圖表類型

        Returns:
            圖表對象或 None
        """
        return self.chart_service.generate_drawdown_chart(data, chart_type)

    def generate_performance_dashboard(
        self, metrics: Dict[str, Any]
    ) -> Union[Any, None]:
        """生成績效儀表板

        Args:
            metrics: 績效指標字典

        Returns:
            Plotly 儀表板圖表或 None
        """
        return self.chart_service.generate_performance_dashboard(metrics)

    def generate_monthly_heatmap(
        self, data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[Any, None]:
        """生成月度績效熱力圖

        Args:
            data: 包含交易數據的字典
            chart_type: 圖表類型

        Returns:
            圖表對象或 None
        """
        return self.chart_service.generate_monthly_heatmap(data, chart_type)

    def generate_parameter_sensitivity_heatmap(
        self, param_results: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[Any, None]:
        """生成參數敏感度熱力圖

        Args:
            param_results: 參數測試結果
            chart_type: 圖表類型

        Returns:
            圖表對象或 None
        """
        return self.chart_service.generate_parameter_sensitivity_heatmap(
            param_results, chart_type
        )

    def generate_asset_allocation_chart(
        self, portfolio_data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[Any, None]:
        """生成資產配置圖表

        Args:
            portfolio_data: 投資組合數據
            chart_type: 圖表類型

        Returns:
            圖表對象或 None
        """
        return self.chart_service.generate_asset_allocation_chart(
            portfolio_data, chart_type
        )

    def generate_strategy_comparison_chart(
        self,
        comparison_data: Dict[str, Any],
        metric: str = "total_return",
        chart_type: str = "plotly",
    ) -> Union[Any, None]:
        """生成策略比較圖表

        Args:
            comparison_data: 策略比較數據
            metric: 比較指標
            chart_type: 圖表類型

        Returns:
            圖表對象或 None
        """
        return self.chart_service.generate_strategy_comparison_chart(
            comparison_data, metric, chart_type
        )

    # ==================== 報表匯出方法 ====================

    def export_report(
        self,
        report_data: Dict[str, Any],
        export_format: str = "pdf",
        template_id: Optional[str] = None,
        user_id: str = "system",
    ) -> Tuple[bool, str, Optional[str]]:
        """匯出報表

        Args:
            report_data: 報表數據
            export_format: 匯出格式
            template_id: 模板ID
            user_id: 用戶ID

        Returns:
            (成功標誌, 訊息, 檔案路徑)
        """
        return self.export_service.export_report(
            report_data, export_format, template_id, user_id
        )

    # ==================== 配置管理方法 ====================

    def save_chart_config(
        self,
        config_name: str,
        chart_type: str,
        config_data: Dict[str, Any],
        user_id: str = "system",
        description: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """保存圖表配置

        Args:
            config_name: 配置名稱
            chart_type: 圖表類型
            config_data: 配置數據
            user_id: 用戶ID
            description: 配置描述

        Returns:
            (成功標誌, 訊息)
        """
        return self.config_service.save_chart_config(
            config_name, chart_type, config_data, user_id, description
        )

    def get_chart_configs(
        self,
        chart_type: Optional[str] = None,
        user_id: Optional[str] = None,
        include_system: bool = True,
    ) -> List[Dict[str, Any]]:
        """獲取圖表配置列表

        Args:
            chart_type: 圖表類型篩選
            user_id: 用戶ID篩選
            include_system: 是否包含系統配置

        Returns:
            配置列表
        """
        return self.config_service.get_chart_configs(
            chart_type, user_id, include_system
        )

    def cleanup_cache(self, max_age_hours: int = 24) -> Tuple[bool, str]:
        """清理過期快取

        Args:
            max_age_hours: 最大保留時間（小時）

        Returns:
            (成功標誌, 訊息)
        """
        return self.config_service.cleanup_cache(max_age_hours)

    # ==================== 向後相容性方法 ====================

    def _calculate_performance_metrics(self, df) -> Dict[str, Any]:
        """計算績效指標 - 向後相容性方法"""
        return self.data_service._calculate_performance_metrics(df)

    # 為了保持向後相容性，添加一些別名方法
    def generate_monthly_performance_heatmap(
        self, data: Dict[str, Any], chart_type: str = "plotly"
    ) -> Union[Any, None]:
        """生成月度績效熱力圖 - 別名方法"""
        return self.generate_monthly_heatmap(data, chart_type)
