"""
統一回測系統模組

此模組整合了原本分散的回測功能，提供統一的回測服務接口。
整合了以下原始模組：
- src/core/backtest_service.py (主要服務層)
- src/core/backtest_handler.py (處理器邏輯)
- src/core/backtest_module/backtest_engine.py (執行引擎)

主要功能：
- 統一的回測服務接口
- 模組化的回測執行引擎
- 完整的配置管理
- 績效指標計算
- 結果管理和匯出

版本: v2.0 (整合版)
作者: AI Trading System Team
"""

from .service import BacktestService
from .engine import BacktestEngine
from .config import BacktestConfig, validate_backtest_config
from .metrics import BacktestMetrics, calculate_performance_metrics
from .specialized import FactorBacktester

# 版本信息
__version__ = "2.0.0"
__author__ = "AI Trading System Team"

# 主要導出
__all__ = [
    # 核心服務
    "BacktestService",
    "BacktestEngine",
    
    # 配置管理
    "BacktestConfig", 
    "validate_backtest_config",
    
    # 績效計算
    "BacktestMetrics",
    "calculate_performance_metrics",
    
    # 專門化工具
    "FactorBacktester",
    
    # 便利函數
    "create_backtest_service",
    "run_simple_backtest",
]

# 便利函數
def create_backtest_service(db_path: str = None, results_dir: str = None) -> BacktestService:
    """創建回測服務實例
    
    Args:
        db_path: 資料庫路徑
        results_dir: 結果保存目錄
        
    Returns:
        BacktestService: 回測服務實例
        
    Example:
        >>> service = create_backtest_service()
        >>> backtest_id = service.start_backtest(config)
    """
    return BacktestService(db_path=db_path, results_dir=results_dir)


def run_simple_backtest(
    strategy_name: str,
    symbols: list,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    **kwargs
) -> dict:
    """運行簡單回測
    
    Args:
        strategy_name: 策略名稱
        symbols: 股票代碼列表
        start_date: 開始日期
        end_date: 結束日期
        initial_capital: 初始資金
        **kwargs: 其他配置參數
        
    Returns:
        dict: 回測結果
        
    Example:
        >>> results = run_simple_backtest(
        ...     strategy_name="double_ma",
        ...     symbols=["AAPL", "GOOGL"],
        ...     start_date="2023-01-01",
        ...     end_date="2023-12-31"
        ... )
    """
    # 創建配置
    config = BacktestConfig(
        strategy_name=strategy_name,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        **kwargs
    )
    
    # 創建服務並運行
    service = create_backtest_service()
    backtest_id = service.start_backtest(config)
    
    # 等待完成並返回結果
    return service.get_backtest_results(backtest_id)


# 模組級別配置
BACKTEST_VERSION = "2.0.0"
SUPPORTED_FEATURES = [
    "unified_service",
    "modular_engine", 
    "config_management",
    "performance_metrics",
    "result_export",
    "factor_backtesting",
    "concurrent_execution",
    "progress_tracking",
]

def get_backtest_info() -> dict:
    """獲取回測系統信息
    
    Returns:
        dict: 系統版本和功能信息
    """
    return {
        "version": BACKTEST_VERSION,
        "features": SUPPORTED_FEATURES,
        "modules": ["service", "engine", "config", "metrics", "specialized"],
        "integration_status": "completed",
        "original_modules": [
            "backtest_service.py",
            "backtest_handler.py", 
            "backtest_engine.py"
        ]
    }
