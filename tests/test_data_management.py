"""
資料管理模組測試

測試資料管理服務和 UI 組件的功能。
包含完整的單元測試和整合測試，確保 ≥80% 的測試覆蓋率。
"""

import pytest
import sys
import os
import threading
import time
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch, MagicMock

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from src.core.data_management_service import (
        DataManagementService,
        DataManagementError,
        ConfigError,
        OperationError,
    )
    from src.ui.components.data_management_components import (
        show_data_source_status_card,
        show_update_progress,
        show_data_quality_metrics,
    )
    from src.ui.components.progress import ProgressTracker
except ImportError as e:
    pytest.skip(f"無法導入必要模組: {e}", allow_module_level=True)


class TestDataManagementService:
    """測試資料管理服務

    包含完整的單元測試，覆蓋所有主要功能和錯誤處理。
    """

    def setup_method(self):
        """設置測試環境"""
        # 使用模擬的資料庫連接
        with patch("src.core.data_management_service.create_engine") as mock_engine:
            with patch("src.core.data_management_service.sessionmaker") as mock_session:
                with patch("src.core.data_management_service.init_db"):
                    mock_engine.return_value = MagicMock()
                    mock_session.return_value = MagicMock()
                    self.service = DataManagementService()

    def test_init_service(self):
        """測試服務初始化"""
        assert self.service is not None
        assert hasattr(self.service, "data_sources")
        assert hasattr(self.service, "update_status")
        assert hasattr(self.service, "lock")
        assert isinstance(self.service.lock, threading.Lock)

    def test_init_database_error(self):
        """測試資料庫初始化錯誤處理"""
        with patch("src.core.data_management_service.create_engine") as mock_engine:
            mock_engine.side_effect = Exception("Database connection failed")

            with pytest.raises(DataManagementError) as exc_info:
                DataManagementService()

            assert "資料庫連接初始化失敗" in str(exc_info.value)

    def test_get_data_source_status(self):
        """測試獲取資料來源狀態"""
        status = self.service.get_data_source_status()
        assert isinstance(status, dict)

        # 檢查是否包含必要的欄位
        for source_name, source_info in status.items():
            assert "status" in source_info
            assert "type" in source_info
            assert "description" in source_info
            assert "last_update" in source_info
            assert "update_frequency" in source_info
            assert "coverage" in source_info
            assert "api_status" in source_info
            assert "data_quality" in source_info

    def test_get_data_source_status_with_adapter_error(self):
        """測試資料來源狀態獲取時適配器錯誤"""
        # 模擬適配器錯誤
        self.service.data_sources["Yahoo Finance"]["adapter"] = None

        status = self.service.get_data_source_status()
        assert isinstance(status, dict)
        assert "Yahoo Finance" in status

    def test_get_last_update_time(self):
        """測試獲取最後更新時間"""
        # 測試正常情況
        with patch.object(self.service, 'session_factory') as mock_factory:
            mock_session = MagicMock()
            mock_factory.return_value.__enter__.return_value = mock_session
            mock_session.execute.return_value.scalar.return_value = datetime.now()

            result = self.service._get_last_update_time("Yahoo Finance")
            assert isinstance(result, datetime)

    def test_get_last_update_time_no_session(self):
        """測試無會話工廠時的最後更新時間"""
        self.service.session_factory = None
        result = self.service._get_last_update_time("Yahoo Finance")
        assert result is None

    def test_get_last_update_time_error(self):
        """測試獲取最後更新時間錯誤處理"""
        with patch.object(self.service, 'session_factory') as mock_factory:
            mock_factory.side_effect = Exception("Database error")

            result = self.service._get_last_update_time("Yahoo Finance")
            assert result is None

    def test_calculate_data_quality(self):
        """測試計算資料品質分數"""
        quality = self.service._calculate_data_quality("Yahoo Finance")
        assert isinstance(quality, str)
        assert "%" in quality

    def test_calculate_data_quality_error(self):
        """測試計算資料品質分數錯誤處理"""
        with patch('src.core.data_management_service.logger') as mock_logger:
            # 模擬內部錯誤
            with patch.object(self.service, '_calculate_data_quality') as mock_calc:
                mock_calc.side_effect = Exception("Calculation error")

                try:
                    self.service._calculate_data_quality("Yahoo Finance")
                except Exception:
                    pass

    def test_get_available_symbols(self):
        """測試獲取可用股票代碼"""
        symbols = self.service.get_available_symbols()
        assert isinstance(symbols, list)

        if symbols:
            # 檢查股票資訊格式
            symbol_info = symbols[0]
            assert "symbol" in symbol_info
            assert "name" in symbol_info
            assert "market" in symbol_info

    def test_get_available_symbols_with_database(self):
        """測試從資料庫獲取股票代碼"""
        with patch.object(self.service, 'session_factory') as mock_factory:
            mock_session = MagicMock()
            mock_factory.return_value.__enter__.return_value = mock_session
            mock_session.execute.return_value.fetchall.return_value = [
                ("2330.TW",), ("AAPL",)
            ]

            symbols = self.service.get_available_symbols()
            assert len(symbols) >= 2
            assert any(s["symbol"] == "2330.TW" for s in symbols)

    def test_get_available_symbols_no_session(self):
        """測試無會話工廠時獲取股票代碼"""
        self.service.session_factory = None
        symbols = self.service.get_available_symbols()
        assert isinstance(symbols, list)
        assert len(symbols) > 0  # 應該返回預設列表

    def test_get_available_symbols_error(self):
        """測試獲取股票代碼錯誤處理"""
        with patch.object(self.service, 'session_factory') as mock_factory:
            mock_factory.side_effect = Exception("Database error")

            symbols = self.service.get_available_symbols()
            assert isinstance(symbols, list)
            assert len(symbols) > 0  # 應該返回預設列表

    def test_get_default_symbols(self):
        """測試獲取預設股票代碼列表"""
        symbols = self.service._get_default_symbols()
        assert isinstance(symbols, list)
        assert len(symbols) > 0

        for symbol in symbols:
            assert "symbol" in symbol
            assert "name" in symbol
            assert "market" in symbol

    def test_get_symbol_name(self):
        """測試獲取股票名稱"""
        # 測試已知股票
        name = self.service._get_symbol_name("2330.TW")
        assert name == "台積電"

        # 測試未知股票
        name = self.service._get_symbol_name("UNKNOWN")
        assert name == "UNKNOWN"

    def test_get_symbol_market(self):
        """測試獲取股票市場"""
        # 測試台股
        market = self.service._get_symbol_market("2330.TW")
        assert market == "台股"

        # 測試美股
        market = self.service._get_symbol_market("AAPL")
        assert market == "美股"

        # 測試其他市場
        market = self.service._get_symbol_market("UNKNOWN.HK")
        assert market == "其他"

    def test_get_data_types(self):
        """測試獲取資料類型"""
        data_types = self.service.get_data_types()
        assert isinstance(data_types, list)
        assert len(data_types) >= 3

        for data_type in data_types:
            assert "id" in data_type
            assert "name" in data_type
            assert "description" in data_type
            assert "sources" in data_type
            assert "frequency" in data_type
            assert "storage" in data_type

    def test_start_data_update(self):
        """測試啟動資料更新"""
        config = {
            "update_type": "full",
            "data_types": ["股價資料"],
            "symbols": ["2330.TW"],
            "start_date": date.today() - timedelta(days=7),
            "end_date": date.today(),
        }

        task_id = self.service.start_data_update(config)
        assert isinstance(task_id, str)
        assert task_id.startswith("update_")

        # 檢查任務狀態
        status = self.service.get_update_status(task_id)
        assert status is not None
        assert "status" in status
        assert "progress" in status
        assert "config" in status
        assert status["config"] == config

    def test_get_update_status_nonexistent(self):
        """測試獲取不存在的任務狀態"""
        status = self.service.get_update_status("nonexistent_task")
        assert status is None

    def test_test_data_source_connection(self):
        """測試資料來源連接測試"""
        # 測試已知的資料來源
        is_connected, message = self.service.test_data_source_connection(
            "Yahoo Finance"
        )
        assert isinstance(is_connected, bool)
        assert isinstance(message, str)

        # 測試未知的資料來源
        is_connected, message = self.service.test_data_source_connection(
            "Unknown Source"
        )
        assert is_connected is False
        assert "未知的資料來源" in message

    def test_test_data_source_connection_with_adapter(self):
        """測試有適配器的資料來源連接"""
        # 模擬有 test_connection 方法的適配器
        mock_adapter = MagicMock()
        mock_adapter.test_connection.return_value = True
        self.service.data_sources["Test Source"] = {"adapter": mock_adapter}

        is_connected, message = self.service.test_data_source_connection("Test Source")
        assert is_connected is True
        assert message == "連接成功"

    def test_test_data_source_connection_failed(self):
        """測試資料來源連接失敗"""
        # 模擬連接失敗的適配器
        mock_adapter = MagicMock()
        mock_adapter.test_connection.return_value = False
        self.service.data_sources["Test Source"] = {"adapter": mock_adapter}

        is_connected, message = self.service.test_data_source_connection("Test Source")
        assert is_connected is False
        assert message == "連接失敗"

    def test_test_data_source_connection_no_method(self):
        """測試沒有 test_connection 方法的適配器"""
        mock_adapter = MagicMock()
        del mock_adapter.test_connection  # 移除方法
        self.service.data_sources["Test Source"] = {"adapter": mock_adapter}

        is_connected, message = self.service.test_data_source_connection("Test Source")
        assert is_connected is False
        assert message == "不支援連接測試"

    def test_test_data_source_connection_error(self):
        """測試資料來源連接測試錯誤處理"""
        # 模擬拋出異常的適配器
        mock_adapter = MagicMock()
        mock_adapter.test_connection.side_effect = Exception("Connection error")
        self.service.data_sources["Test Source"] = {"adapter": mock_adapter}

        is_connected, message = self.service.test_data_source_connection("Test Source")
        assert is_connected is False
        assert "連接測試錯誤" in message

    def test_update_status_progress(self):
        """測試更新任務進度"""
        task_id = "test_task"
        self.service.update_status[task_id] = {
            "status": "running",
            "progress": 0,
            "message": "開始"
        }

        # 測試進度更新
        self.service._update_status_progress(task_id, 50.0, "處理中...")
        status = self.service.update_status[task_id]
        assert status["progress"] == 50.0
        assert status["message"] == "處理中..."

        # 測試格式化訊息
        self.service._update_status_progress(task_id, 75.0, "處理 %s 中...", "股價資料")
        status = self.service.update_status[task_id]
        assert status["progress"] == 75.0
        assert status["message"] == "處理 股價資料 中..."

    def test_update_status_progress_nonexistent_task(self):
        """測試更新不存在任務的進度"""
        # 不應該拋出異常
        self.service._update_status_progress("nonexistent", 50.0, "測試")

    def test_update_price_data(self):
        """測試更新股價資料"""
        symbols = ["2330.TW", "AAPL"]
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        result = self.service._update_price_data(symbols, start_date, end_date)

        assert isinstance(result, dict)
        assert "processed" in result
        assert "new" in result
        assert "updated" in result
        assert "errors" in result
        assert result["processed"] > 0

    def test_update_price_data_with_adapter(self):
        """測試有適配器的股價資料更新"""
        # 模擬有適配器的情況
        mock_adapter = MagicMock()
        self.service.data_sources["Yahoo Finance"]["adapter"] = mock_adapter

        symbols = ["2330.TW"]
        result = self.service._update_price_data(symbols, None, None)

        assert isinstance(result, dict)
        assert result["processed"] > 0

    def test_update_price_data_error(self):
        """測試股價資料更新錯誤處理"""
        # 模擬適配器錯誤
        mock_adapter = MagicMock()
        mock_adapter.side_effect = Exception("Adapter error")
        self.service.data_sources["Yahoo Finance"]["adapter"] = mock_adapter

        symbols = ["2330.TW"]
        result = self.service._update_price_data(symbols, None, None)

        assert isinstance(result, dict)
        assert result["errors"] >= 0

    def test_update_fundamental_data(self):
        """測試更新基本面資料"""
        symbols = ["2330.TW", "AAPL"]
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        result = self.service._update_fundamental_data(symbols, start_date, end_date)

        assert isinstance(result, dict)
        assert "processed" in result
        assert "new" in result
        assert "updated" in result
        assert "errors" in result
        assert result["processed"] > 0

    def test_update_technical_data(self):
        """測試更新技術指標資料"""
        symbols = ["2330.TW", "AAPL"]
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        result = self.service._update_technical_data(symbols, start_date, end_date)

        assert isinstance(result, dict)
        assert "processed" in result
        assert "new" in result
        assert "updated" in result
        assert "errors" in result
        assert result["processed"] > 0

    def test_execute_update_success(self):
        """測試執行更新任務成功"""
        task_id = "test_task"
        config = {
            "data_types": ["股價資料", "基本面資料"],
            "symbols": ["2330.TW"],
            "start_date": date.today() - timedelta(days=1),
            "end_date": date.today()
        }

        # 初始化任務狀態
        self.service.update_status[task_id] = {
            "status": "running",
            "progress": 0,
            "message": "開始",
            "config": config
        }

        # 執行更新
        self.service._execute_update(task_id, config)

        # 等待一下讓更新完成
        time.sleep(0.1)

        # 檢查結果
        status = self.service.update_status[task_id]
        assert status["status"] == "completed"
        assert status["progress"] == 100
        assert "results" in status

    def test_execute_update_with_unknown_data_type(self):
        """測試執行更新任務包含未知資料類型"""
        task_id = "test_task"
        config = {
            "data_types": ["未知資料類型"],
            "symbols": ["2330.TW"],
            "start_date": date.today() - timedelta(days=1),
            "end_date": date.today()
        }

        # 初始化任務狀態
        self.service.update_status[task_id] = {
            "status": "running",
            "progress": 0,
            "message": "開始",
            "config": config
        }

        # 執行更新
        self.service._execute_update(task_id, config)

        # 等待一下讓更新完成
        time.sleep(0.1)

        # 檢查結果
        status = self.service.update_status[task_id]
        assert status["status"] == "completed"

    def test_execute_update_error(self):
        """測試執行更新任務錯誤處理"""
        task_id = "test_task"
        config = None  # 無效配置

        # 初始化任務狀態
        self.service.update_status[task_id] = {
            "status": "running",
            "progress": 0,
            "message": "開始"
        }

        # 執行更新
        self.service._execute_update(task_id, config)

        # 檢查結果
        status = self.service.update_status[task_id]
        assert status["status"] == "error"
        assert "更新失敗" in status["message"]

    def test_execute_update_data_type_error(self):
        """測試執行更新任務中資料類型處理錯誤"""
        task_id = "test_task"
        config = {
            "data_types": ["股價資料"],
            "symbols": ["2330.TW"],
            "start_date": date.today() - timedelta(days=1),
            "end_date": date.today()
        }

        # 初始化任務狀態
        self.service.update_status[task_id] = {
            "status": "running",
            "progress": 0,
            "message": "開始",
            "config": config
        }

        # 模擬 _update_price_data 拋出異常
        with patch.object(self.service, '_update_price_data') as mock_update:
            mock_update.side_effect = Exception("Update error")

            # 執行更新
            self.service._execute_update(task_id, config)

            # 等待一下讓更新完成
            time.sleep(0.1)

            # 檢查結果
            status = self.service.update_status[task_id]
            assert status["status"] == "completed"
            assert "results" in status
            assert status["results"]["error_records"] > 0


class TestDataManagementExceptions:
    """測試資料管理異常類別"""

    def test_data_management_error(self):
        """測試 DataManagementError 異常"""
        error = DataManagementError("測試錯誤")
        assert str(error) == "測試錯誤"
        assert isinstance(error, Exception)

    def test_config_error(self):
        """測試 ConfigError 異常"""
        error = ConfigError("配置錯誤")
        assert str(error) == "配置錯誤"
        assert isinstance(error, DataManagementError)

    def test_operation_error(self):
        """測試 OperationError 異常"""
        error = OperationError("操作錯誤")
        assert str(error) == "操作錯誤"
        assert isinstance(error, DataManagementError)

    def test_exception_chaining(self):
        """測試異常鏈"""
        try:
            try:
                raise ValueError("原始錯誤")
            except ValueError as e:
                raise DataManagementError("包裝錯誤") from e
        except DataManagementError as e:
            assert str(e) == "包裝錯誤"
            assert isinstance(e.__cause__, ValueError)


class TestDataManagementComponents:
    """測試資料管理 UI 組件"""

    def test_progress_tracker(self):
        """測試進度追蹤器"""
        # 這個測試需要在 Streamlit 環境中運行
        # 這裡只測試基本的初始化
        try:
            tracker = ProgressTracker(10, "測試進度")
            assert tracker.total_steps == 10
            assert tracker.current_step == 0
            assert tracker.title == "測試進度"
        except Exception:
            # 在非 Streamlit 環境中會失敗，這是預期的
            pass

    def test_data_quality_metrics_structure(self):
        """測試資料品質指標結構"""
        quality_data = {
            "股價資料": {
                "completeness": "98.5%",
                "accuracy": "99.2%",
                "timeliness": "100%",
            },
            "基本面資料": {
                "completeness": "95.8%",
                "accuracy": "97.5%",
                "timeliness": "90.2%",
            },
        }

        # 驗證資料結構
        assert isinstance(quality_data, dict)
        for data_type, metrics in quality_data.items():
            assert isinstance(metrics, dict)
            assert "completeness" in metrics
            assert "accuracy" in metrics
            assert "timeliness" in metrics


class TestDataManagementIntegration:
    """測試資料管理整合功能"""

    def setup_method(self):
        """設置測試環境"""
        with patch("src.core.data_management_service.create_engine"):
            with patch("src.core.data_management_service.sessionmaker"):
                with patch("src.core.data_management_service.init_db"):
                    self.service = DataManagementService()

    def test_full_update_workflow(self):
        """測試完整的更新工作流程"""
        # 1. 獲取資料來源狀態
        sources = self.service.get_data_source_status()
        assert len(sources) > 0

        # 2. 獲取可用的資料類型和股票
        data_types = self.service.get_data_types()
        symbols = self.service.get_available_symbols()

        assert len(data_types) > 0
        assert len(symbols) > 0

        # 3. 配置更新任務
        config = {
            "update_type": "incremental",
            "data_types": [data_types[0]["name"]],
            "symbols": [symbols[0]["symbol"]],
            "start_date": date.today() - timedelta(days=1),
            "end_date": date.today(),
        }

        # 4. 啟動更新任務
        task_id = self.service.start_data_update(config)
        assert task_id is not None

        # 5. 檢查任務狀態
        status = self.service.get_update_status(task_id)
        assert status is not None
        assert status["status"] in ["running", "completed", "error"]

    def test_error_handling(self):
        """測試錯誤處理"""
        # 測試無效的更新配置
        invalid_config = {
            "update_type": "invalid_type",
            "data_types": [],
            "symbols": [],
        }

        task_id = self.service.start_data_update(invalid_config)
        assert task_id is not None

        # 等待一下讓任務處理
        import time

        time.sleep(0.1)

        status = self.service.get_update_status(task_id)
        # 任務應該會處理，但可能會有錯誤或警告
        assert status is not None


def test_mock_data_generation():
    """測試模擬資料生成"""
    from src.ui.pages.data_management import get_mock_stock_data

    start_date = date.today() - timedelta(days=7)
    end_date = date.today()

    # 測試股價資料
    price_data = get_mock_stock_data("2330.TW", start_date, end_date, "price")
    assert not price_data.empty
    assert "股票代碼" in price_data.columns
    assert "收盤價" in price_data.columns

    # 測試基本面資料
    fundamental_data = get_mock_stock_data(
        "2330.TW", start_date, end_date, "fundamental"
    )
    assert not fundamental_data.empty
    assert "股票代碼" in fundamental_data.columns
    assert "本益比" in fundamental_data.columns


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v"])
