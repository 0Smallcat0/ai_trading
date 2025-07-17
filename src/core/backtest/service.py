"""
統一回測服務模組

此模組整合了原本的 backtest_service.py 和 backtest_handler.py，
提供完整的回測管理功能，包括：
- 回測參數設定和驗證
- 回測執行控制和進度管理
- 績效分析和指標計算
- 交易記錄管理和查詢
- 報表生成和匯出功能
"""

import os
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
import pandas as pd
import uuid
import time

from .config import BacktestConfig, validate_backtest_config
from .engine import BacktestEngine
from .metrics import calculate_performance_metrics
# 暫時註釋掉未實現的模組
# from .data_manager import BacktestDataManager
# from .status_manager import BacktestStatusManager
# from .results_manager import BacktestResultsManager
# from .export_manager import BacktestExportManager

logger = logging.getLogger(__name__)


class BacktestService:
    """統一回測服務
    
    整合了原本分散的回測功能，提供統一的服務接口。
    
    Attributes:
        data_manager: 數據管理器
        status_manager: 狀態管理器
        results_manager: 結果管理器
        export_manager: 匯出管理器
        engine: 回測引擎
    """

    def __init__(self, db_path: str = None, results_dir: str = None):
        """初始化回測服務
        
        Args:
            db_path: 資料庫路徑
            results_dir: 結果保存目錄
        """
        # 設置結果目錄
        self.results_dir = Path(results_dir or "data/backtest_results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化各個管理器 (暫時使用簡化版)
        # self.data_manager = BacktestDataManager(db_path)
        # self.status_manager = BacktestStatusManager()
        # self.results_manager = BacktestResultsManager(self.results_dir)
        # self.export_manager = BacktestExportManager()

        # 簡化版管理器
        self.data_manager = self._create_simple_data_manager()
        self.status_manager = self._create_simple_status_manager()
        self.results_manager = self._create_simple_results_manager()
        self.export_manager = self._create_simple_export_manager()
        
        # 初始化回測引擎
        self.engine = BacktestEngine()
        
        # 執行狀態管理
        self.running_backtests = {}
        self.backtest_threads = {}
        self._lock = threading.Lock()
        
        logger.info("回測服務已初始化")

    def get_available_strategies(self) -> List[Dict]:
        """獲取可用策略列表
        
        Returns:
            List[Dict]: 策略列表
        """
        return self.data_manager.get_available_strategies()

    def get_available_stocks(self) -> List[Dict]:
        """獲取可用股票列表
        
        Returns:
            List[Dict]: 股票列表
        """
        return self.data_manager.get_available_stocks()

    def start_backtest(self, config: BacktestConfig) -> str:
        """啟動回測
        
        Args:
            config: 回測配置
            
        Returns:
            str: 回測ID
            
        Raises:
            ValueError: 當配置無效時
        """
        # 驗證配置
        is_valid, error_msg = validate_backtest_config(config)
        if not is_valid:
            raise ValueError(error_msg)
        
        # 創建回測任務
        backtest_id = str(uuid.uuid4())
        self.status_manager.create_backtest_task(backtest_id, config)
        
        # 啟動回測線程
        thread = threading.Thread(
            target=self._run_backtest_thread,
            args=(backtest_id, config),
            daemon=True
        )
        
        with self._lock:
            self.backtest_threads[backtest_id] = thread
            self.running_backtests[backtest_id] = {
                "status": "created",
                "progress": 0,
                "message": "回測任務已創建",
                "config": config
            }
        
        thread.start()
        logger.info("回測任務已啟動: %s", backtest_id)
        return backtest_id

    def _run_backtest_thread(self, backtest_id: str, config: BacktestConfig) -> None:
        """執行回測線程
        
        Args:
            backtest_id: 回測ID
            config: 回測配置
        """
        try:
            # 更新狀態
            self.status_manager.update_backtest_status(
                backtest_id, "running", 10, "正在載入數據..."
            )
            
            # 載入市場數據
            market_data = self.data_manager.load_market_data(
                config.symbols, config.start_date, config.end_date
            )
            
            # 更新狀態
            self.status_manager.update_backtest_status(
                backtest_id, "running", 30, "正在生成訊號..."
            )
            
            # 載入策略
            strategy = self.data_manager.load_strategy(config.strategy_name, config.strategy_params)
            
            # 生成訊號
            signals = strategy.generate_signals(market_data)
            
            # 更新狀態
            self.status_manager.update_backtest_status(
                backtest_id, "running", 50, "正在執行回測..."
            )
            
            # 執行回測
            results = self.engine.run_backtest(
                signals=signals,
                market_data=market_data,
                initial_capital=config.initial_capital,
                commission=config.commission,
                slippage=config.slippage
            )
            
            # 計算績效指標
            self.status_manager.update_backtest_status(
                backtest_id, "running", 80, "正在計算績效指標..."
            )
            metrics = calculate_performance_metrics(results, config)
            
            # 保存結果
            self.status_manager.update_backtest_status(
                backtest_id, "running", 90, "正在保存結果..."
            )
            self.results_manager.save_backtest_results(
                backtest_id, results, metrics, config
            )
            
            # 完成回測
            self.status_manager.update_backtest_status(
                backtest_id, "completed", 100, "回測完成"
            )
            
            # 清理線程記錄
            with self._lock:
                if backtest_id in self.backtest_threads:
                    del self.backtest_threads[backtest_id]
            
        except Exception as e:
            logger.error("回測執行失敗: %s", e, exc_info=True)
            self.status_manager.update_backtest_status(
                backtest_id, "failed", 0, f"回測失敗: {str(e)}"
            )
            
            # 清理線程記錄
            with self._lock:
                if backtest_id in self.backtest_threads:
                    del self.backtest_threads[backtest_id]

    def get_backtest_status(self, backtest_id: str) -> Dict:
        """獲取回測狀態
        
        Args:
            backtest_id: 回測ID
            
        Returns:
            Dict: 回測狀態
            
        Raises:
            ValueError: 當回測ID不存在時
        """
        status = self.status_manager.get_backtest_status(backtest_id)
        if not status:
            raise ValueError(f"回測ID不存在: {backtest_id}")
        return status

    def get_backtest_results(self, backtest_id: str) -> Dict:
        """獲取回測結果
        
        Args:
            backtest_id: 回測ID
            
        Returns:
            Dict: 回測結果
            
        Raises:
            ValueError: 當回測ID不存在或回測未完成時
        """
        # 檢查回測是否完成
        status = self.get_backtest_status(backtest_id)
        if status["status"] != "completed":
            raise ValueError(f"回測尚未完成: {backtest_id}, 當前狀態: {status['status']}")
        
        # 獲取結果
        return self.results_manager.get_backtest_results(backtest_id)

    def export_backtest_report(self, backtest_id: str, format: str = "html") -> str:
        """匯出回測報告
        
        Args:
            backtest_id: 回測ID
            format: 報告格式 (html, pdf, csv)
            
        Returns:
            str: 報告文件路徑
            
        Raises:
            ValueError: 當回測ID不存在或格式不支援時
        """
        # 獲取結果
        results = self.get_backtest_results(backtest_id)
        
        # 匯出報告
        return self.export_manager.export_report(backtest_id, results, format)

    def cancel_backtest(self, backtest_id: str) -> bool:
        """取消回測
        
        Args:
            backtest_id: 回測ID
            
        Returns:
            bool: 是否成功取消
            
        Raises:
            ValueError: 當回測ID不存在時
        """
        with self._lock:
            if backtest_id not in self.running_backtests:
                raise ValueError(f"回測ID不存在: {backtest_id}")
            
            # 更新狀態
            self.status_manager.update_backtest_status(
                backtest_id, "cancelled", 0, "回測已取消"
            )
            
            # 清理線程記錄
            if backtest_id in self.backtest_threads:
                # 無法直接停止線程，但可以標記為取消
                del self.backtest_threads[backtest_id]
            
            return True

    def list_backtests(self, status: str = None, limit: int = 100) -> List[Dict]:
        """列出回測任務
        
        Args:
            status: 過濾狀態 (created, running, completed, failed, cancelled)
            limit: 最大返回數量
            
        Returns:
            List[Dict]: 回測任務列表
        """
        return self.status_manager.list_backtests(status, limit)

    def clean_old_backtests(self, days: int = 30) -> int:
        """清理舊的回測記錄

        Args:
            days: 保留天數

        Returns:
            int: 清理的記錄數量
        """
        return self.results_manager.clean_old_results(days)

    # 簡化版管理器實現
    def _create_simple_data_manager(self):
        """創建簡化版數據管理器"""
        class SimpleDataManager:
            def get_available_strategies(self):
                return [
                    {"name": "double_ma", "description": "雙移動平均線策略"},
                    {"name": "rsi", "description": "相對強弱指標策略"},
                    {"name": "alpha101", "description": "Alpha101 因子策略"}
                ]

            def get_available_stocks(self):
                return [
                    {"symbol": "AAPL", "name": "Apple Inc."},
                    {"symbol": "GOOGL", "name": "Alphabet Inc."},
                    {"symbol": "MSFT", "name": "Microsoft Corporation"}
                ]

            def load_market_data(self, symbols, start_date, end_date):
                # 生成模擬數據
                import pandas as pd
                import numpy as np
                from datetime import datetime, timedelta

                # 生成日期範圍
                if isinstance(start_date, str):
                    start_date = pd.to_datetime(start_date)
                if isinstance(end_date, str):
                    end_date = pd.to_datetime(end_date)

                date_range = pd.date_range(start=start_date, end=end_date, freq='B')

                # 生成模擬數據
                data = []
                for symbol in symbols:
                    # 設置隨機種子以獲得可重複的結果
                    np.random.seed(hash(symbol) % 10000)

                    # 生成價格序列
                    price = 100.0
                    prices = [price]
                    for _ in range(1, len(date_range)):
                        change = np.random.normal(0, 0.02)  # 2% 標準差
                        price *= (1 + change)
                        prices.append(price)

                    # 生成成交量
                    volumes = np.random.randint(1000, 10000, size=len(date_range))

                    # 添加到數據列表
                    for i, date in enumerate(date_range):
                        data.append({
                            'symbol': symbol,
                            'date': date,
                            'open': prices[i] * (1 - 0.005 + 0.01 * np.random.random()),
                            'high': prices[i] * (1 + 0.01 * np.random.random()),
                            'low': prices[i] * (1 - 0.01 * np.random.random()),
                            'close': prices[i],
                            'volume': volumes[i]
                        })

                return pd.DataFrame(data)

            def load_strategy(self, strategy_name, strategy_params=None):
                # 返回模擬策略
                class SimpleStrategy:
                    def __init__(self, name, params=None):
                        self.name = name
                        self.params = params or {}

                    def generate_signals(self, market_data):
                        # 生成隨機訊號
                        import pandas as pd
                        import numpy as np

                        # 獲取唯一日期和股票
                        dates = market_data['date'].unique()
                        symbols = market_data['symbol'].unique()

                        # 生成訊號
                        signals = []
                        for date in dates:
                            for symbol in symbols:
                                # 隨機訊號
                                signal = np.random.choice([-1, 0, 1], p=[0.2, 0.6, 0.2])
                                weight = abs(signal) * 0.2  # 20% 權重

                                signals.append({
                                    'date': date,
                                    'symbol': symbol,
                                    'signal': signal,
                                    'weight': weight
                                })

                        return pd.DataFrame(signals)

                return SimpleStrategy(strategy_name, strategy_params)

        return SimpleDataManager()

    def _create_simple_status_manager(self):
        """創建簡化版狀態管理器"""
        class SimpleStatusManager:
            def __init__(self):
                self.backtest_status = {}

            def create_backtest_task(self, backtest_id, config):
                self.backtest_status[backtest_id] = {
                    "status": "created",
                    "progress": 0,
                    "message": "回測任務已創建",
                    "config": config,
                    "created_at": pd.Timestamp.now()
                }
                return backtest_id

            def update_backtest_status(self, backtest_id, status, progress, message):
                if backtest_id in self.backtest_status:
                    self.backtest_status[backtest_id].update({
                        "status": status,
                        "progress": progress,
                        "message": message,
                        "updated_at": pd.Timestamp.now()
                    })

            def get_backtest_status(self, backtest_id):
                return self.backtest_status.get(backtest_id, None)

            def list_backtests(self, status=None, limit=100):
                result = []
                for backtest_id, info in self.backtest_status.items():
                    if status is None or info["status"] == status:
                        result.append({
                            "backtest_id": backtest_id,
                            **info
                        })

                        if len(result) >= limit:
                            break

                return result

            def start_backtest_thread(self, backtest_id, target, args):
                # 簡化版不需要實際啟動線程
                import threading
                thread = threading.Thread(target=target, args=args)
                thread.start()

        return SimpleStatusManager()

    def _create_simple_results_manager(self):
        """創建簡化版結果管理器"""
        class SimpleResultsManager:
            def __init__(self, results_dir=None):
                self.results_dir = results_dir
                self.results = {}

            def save_backtest_results(self, backtest_id, results, metrics, config):
                self.results[backtest_id] = {
                    "results": results,
                    "metrics": metrics,
                    "config": config,
                    "saved_at": pd.Timestamp.now()
                }

            def get_backtest_results(self, backtest_id):
                return self.results.get(backtest_id, {}).get("results", None)

            def generate_report(self, backtest_id):
                results = self.results.get(backtest_id, {})
                metrics = results.get("metrics", {})

                return {
                    "summary": metrics,
                    "backtest_id": backtest_id,
                    "generated_at": pd.Timestamp.now().isoformat()
                }

            def clean_old_results(self, days=30):
                # 簡化版不實際清理
                return 0

        return SimpleResultsManager(self.results_dir)

    def _create_simple_export_manager(self):
        """創建簡化版匯出管理器"""
        class SimpleExportManager:
            def export_report(self, backtest_id, results, format="html"):
                # 簡化版不實際匯出
                return f"report_{backtest_id}.{format}"

        return SimpleExportManager()

    # 整合自 backtest_handler.py 的功能
    def run_backtest_mode(self, config: Dict[str, Any]) -> Tuple[Dict, Dict]:
        """運行回測模式
        
        整合自 backtest_handler.py 的功能，提供完整的回測流程。
        
        Args:
            config: 回測配置字典
            
        Returns:
            Tuple[Dict, Dict]: (回測結果, 報告)
            
        Raises:
            ValueError: 當配置無效時
            RuntimeError: 當回測執行失敗時
        """
        logger.info("開始回測模式")
        
        try:
            # 轉換配置格式
            backtest_config = BacktestConfig(**config)
            
            # 啟動回測
            backtest_id = self.start_backtest(backtest_config)
            
            # 等待回測完成
            while True:
                status = self.get_backtest_status(backtest_id)
                if status["status"] in ["completed", "failed", "cancelled"]:
                    break
                time.sleep(0.5)
            
            # 檢查回測狀態
            if status["status"] != "completed":
                raise RuntimeError(f"回測失敗: {status['message']}")
            
            # 獲取結果
            results = self.get_backtest_results(backtest_id)
            
            # 生成報告
            report = self.results_manager.generate_report(backtest_id)
            
            logger.info("回測模式執行完成")
            return results, report
            
        except Exception as e:
            logger.error("回測模式執行失敗: %s", e, exc_info=True)
            raise RuntimeError(f"回測模式執行失敗: {e}") from e
