"""重構後的回測服務模組

此模組提供重構後的回測服務，使用模組化設計提高可維護性和可測試性。
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import logging

from .backtest_config import BacktestConfig, BacktestConfigManager
from .backtest_database import BacktestDatabaseManager
from .backtest_engine import BacktestExecutionEngine
from .backtest_export import BacktestExportManager

logger = logging.getLogger(__name__)


class BacktestServiceRefactored:
    """重構後的回測服務類

    使用模組化設計，將原本的大型服務類拆分為多個專責模組：
    - BacktestConfigManager: 配置管理
    - BacktestDatabaseManager: 資料庫操作
    - BacktestExecutionEngine: 回測執行
    - BacktestExportManager: 報表匯出
    """

    def __init__(self, db_path: str = None, results_dir: str = None):
        """初始化回測服務

        Args:
            db_path: 資料庫路徑
            results_dir: 結果保存目錄
        """
        # 初始化各個管理器
        self.config_manager = BacktestConfigManager()
        self.db_manager = BacktestDatabaseManager(db_path)
        self.execution_engine = BacktestExecutionEngine(self.db_manager, results_dir)
        self.export_manager = BacktestExportManager()

        # 設置結果目錄
        self.results_dir = Path(results_dir or "data/backtest_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        logger.info("回測服務已初始化")

    def get_available_strategies(self) -> List[Dict[str, str]]:
        """獲取可用策略列表

        Returns:
            List[Dict[str, str]]: 策略列表
        """
        return [
            {"id": "ma_cross", "name": "移動平均線交叉策略"},
            {"id": "buy_hold", "name": "買入持有策略"},
            {"id": "mean_reversion", "name": "均值回歸策略"},
        ]

    def get_available_stocks(self) -> List[Dict[str, str]]:
        """獲取可用股票列表

        Returns:
            List[Dict[str, str]]: 股票列表
        """
        return [
            {"symbol": "2330.TW", "name": "台積電"},
            {"symbol": "2317.TW", "name": "鴻海"},
            {"symbol": "2454.TW", "name": "聯發科"},
            {"symbol": "2881.TW", "name": "富邦金"},
            {"symbol": "2882.TW", "name": "國泰金"},
            {"symbol": "2886.TW", "name": "兆豐金"},
            {"symbol": "2891.TW", "name": "中信金"},
            {"symbol": "2892.TW", "name": "第一金"},
            {"symbol": "2884.TW", "name": "玉山金"},
            {"symbol": "2885.TW", "name": "元大金"},
        ]

    def validate_backtest_config(self, config: BacktestConfig) -> tuple:
        """驗證回測配置

        Args:
            config: 回測配置

        Returns:
            tuple: (是否有效, 錯誤訊息)
        """
        return self.config_manager.validate_config(config)

    def start_backtest(
        self, config: BacktestConfig, progress_callback: Callable = None
    ) -> str:
        """啟動回測

        Args:
            config: 回測配置
            progress_callback: 進度回調函數

        Returns:
            str: 回測ID

        Raises:
            ValueError: 配置驗證失敗
            RuntimeError: 啟動失敗
        """
        # 驗證配置
        is_valid, error_msg = self.validate_backtest_config(config)
        if not is_valid:
            raise ValueError(error_msg)

        # 啟動回測
        return self.execution_engine.start_backtest(config, progress_callback)

    def get_backtest_status(self, backtest_id: str) -> Dict[str, Any]:
        """獲取回測狀態

        Args:
            backtest_id: 回測ID

        Returns:
            Dict[str, Any]: 狀態資訊
        """
        return self.execution_engine.get_backtest_status(backtest_id)

    def cancel_backtest(self, backtest_id: str) -> bool:
        """取消回測

        Args:
            backtest_id: 回測ID

        Returns:
            bool: 是否成功
        """
        return self.execution_engine.cancel_backtest(backtest_id)

    def get_backtest_results(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """獲取回測結果

        Args:
            backtest_id: 回測ID

        Returns:
            Optional[Dict[str, Any]]: 回測結果
        """
        try:
            # 先從檔案載入完整結果
            results_file = self.results_dir / f"{backtest_id}.json"
            if results_file.exists():
                with open(results_file, "r", encoding="utf-8") as f:
                    return json.load(f)

            # 如果檔案不存在，從資料庫重建結果
            run_info = self.db_manager.get_backtest_run(backtest_id)
            if not run_info:
                return None

            trades = self.db_manager.get_backtest_trades(backtest_id)

            # 重建結果結構
            result = {
                "backtest_id": backtest_id,
                "metrics": {
                    key: run_info.get(key)
                    for key in [
                        "initial_capital",
                        "final_capital",
                        "total_return",
                        "annual_return",
                        "sharpe_ratio",
                        "max_drawdown",
                        "win_rate",
                        "total_trades",
                    ]
                    if key in run_info
                },
                "trades": trades,
                "equity_curve": [],  # 需要從其他地方重建
                "dates": [],
            }

            return result

        except Exception as e:
            logger.error("獲取回測結果失敗: %s", e)
            return None

    def get_backtest_list(
        self, limit: int = 50, offset: int = 0, status_filter: str = None
    ) -> List[Dict[str, Any]]:
        """獲取回測列表

        Args:
            limit: 限制數量
            offset: 偏移量
            status_filter: 狀態篩選

        Returns:
            List[Dict[str, Any]]: 回測列表
        """
        return self.db_manager.get_backtest_list(limit, offset, status_filter)

    def delete_backtest(self, backtest_id: str) -> bool:
        """刪除回測

        Args:
            backtest_id: 回測ID

        Returns:
            bool: 是否成功
        """
        try:
            # 刪除資料庫記錄
            if not self.db_manager.delete_backtest(backtest_id):
                return False

            # 刪除結果檔案
            results_file = self.results_dir / f"{backtest_id}.json"
            if results_file.exists():
                results_file.unlink()

            return True

        except Exception as e:
            logger.error("刪除回測失敗: %s", e)
            return False

    def export_results(
        self, backtest_id: str, export_format: str = "json"
    ) -> Optional[bytes]:
        """匯出回測結果

        Args:
            backtest_id: 回測ID
            export_format: 匯出格式 ('json', 'csv', 'excel', 'html')

        Returns:
            Optional[bytes]: 匯出的檔案內容
        """
        results = self.get_backtest_results(backtest_id)
        if not results:
            return None

        return self.export_manager.export_results(results, export_format)

    def generate_report(
        self,
        backtest_id: str,
        export_format: str = "html",
        include_charts: bool = False,
        include_transactions: bool = True,
    ) -> Optional[bytes]:
        """生成回測報表

        Args:
            backtest_id: 回測ID
            export_format: 報表格式
            include_charts: 是否包含圖表（暫未使用）
            include_transactions: 是否包含交易明細（暫未使用）

        Returns:
            Optional[bytes]: 報表內容
        """
        results = self.get_backtest_results(backtest_id)
        if not results:
            return None

        return self.export_manager.generate_report(
            backtest_id, results, export_format, include_charts, include_transactions
        )

    def create_config_from_dict(self, config_dict: Dict[str, Any]) -> BacktestConfig:
        """從字典創建配置

        Args:
            config_dict: 配置字典

        Returns:
            BacktestConfig: 配置物件

        Raises:
            ValueError: 配置參數無效
        """
        return self.config_manager.create_config(**config_dict)

    def get_default_config(self) -> Dict[str, Any]:
        """獲取預設配置

        Returns:
            Dict[str, Any]: 預設配置字典
        """
        return self.config_manager.get_default_config()

    def get_service_info(self) -> Dict[str, Any]:
        """獲取服務資訊

        Returns:
            Dict[str, Any]: 服務資訊
        """
        return {
            "service_name": "BacktestServiceRefactored",
            "version": "2.0.0",
            "description": "重構後的回測服務，使用模組化設計",
            "modules": {
                "config_manager": "BacktestConfigManager",
                "database_manager": "BacktestDatabaseManager",
                "execution_engine": "BacktestExecutionEngine",
                "export_manager": "BacktestExportManager",
            },
            "supported_formats": ["json", "csv", "excel", "html"],
            "supported_strategies": [s["id"] for s in self.get_available_strategies()],
        }
