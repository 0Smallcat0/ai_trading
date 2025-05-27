"""
回測模組

此模組包含回測系統的所有核心功能。
"""

from .backtest_config import BacktestConfig, create_default_config
from .backtest_metrics import calculate_performance_metrics
from .backtest_validator import (
    validate_backtest_config,
    validate_market_data,
    validate_signals,
)
from .backtest_data_handler import (
    load_market_data,
    initialize_strategy,
    generate_signals,
    process_backtest_results,
    validate_data_integrity,
)
from .backtest_database import BacktestDatabaseManager
from .backtest_results import BacktestResultsManager
from .backtest_data_manager import BacktestDataManager
from .backtest_status_manager import BacktestStatusManager
from .backtest_query_manager import BacktestQueryManager
from .backtest_strategy_manager import BacktestStrategyManager
from .backtest_data_feed import BacktestDataFeed, PandasDataFeed
from .mock_backtest_engine import MockBacktest
from .backtest_performance_calculator import BacktestPerformanceCalculator
from .backtest_engine import BacktestExecutionEngine
from .backtest_reports import (
    generate_report,
    get_chart_data,
    export_to_csv,
    export_to_excel,
    export_to_html,
)

__all__ = [
    "BacktestConfig",
    "create_default_config",
    "calculate_performance_metrics",
    "validate_backtest_config",
    "validate_market_data",
    "validate_signals",
    "load_market_data",
    "initialize_strategy",
    "generate_signals",
    "process_backtest_results",
    "validate_data_integrity",
    "BacktestDatabaseManager",
    "BacktestResultsManager",
    "BacktestDataManager",
    "BacktestStatusManager",
    "BacktestQueryManager",
    "BacktestStrategyManager",
    "BacktestDataFeed",
    "PandasDataFeed",
    "MockBacktest",
    "BacktestPerformanceCalculator",
    "BacktestExecutionEngine",
    "generate_report",
    "get_chart_data",
    "export_to_csv",
    "export_to_excel",
    "export_to_html",
]
