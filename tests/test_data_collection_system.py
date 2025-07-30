"""資料收集系統測試模組

此模組測試資料收集系統的各項功能，包括：
- 系統初始化
- 配置管理
- 收集器管理
- 排程設定
- 資料收集執行

Example:
    >>> pytest tests/test_data_collection_system.py -v
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch, MagicMock

from src.data_sources.data_collection_system import DataCollectionSystem
from src.data_sources.collection_config import CollectionConfigManager
from src.data_sources.collector_manager import CollectorManager
from src.data_sources.collection_executor import CollectionExecutor


class TestDataCollectionSystem:
    """資料收集系統測試類別"""

    def setup_method(self):
        """設定測試環境"""
        self.system = DataCollectionSystem()

    def test_system_initialization(self):
        """測試系統初始化"""
        assert self.system is not None
        assert hasattr(self.system, 'config_manager')
        assert hasattr(self.system, 'collector_manager')
        assert hasattr(self.system, 'executor')
        assert isinstance(self.system.config_manager, CollectionConfigManager)
        assert isinstance(self.system.collector_manager, CollectorManager)
        assert isinstance(self.system.executor, CollectionExecutor)

    def test_system_with_custom_config(self):
        """測試使用自定義配置初始化系統"""
        custom_symbols = ["2330.TW", "2317.TW"]
        system = DataCollectionSystem(symbols=custom_symbols)
        
        assert system.symbols == custom_symbols
        assert system.collector_manager.symbols == custom_symbols
        assert system.executor.symbols == custom_symbols

    def test_setup_schedules(self):
        """測試設定排程"""
        with patch.object(self.system.collector_manager, 'setup_schedules') as mock_setup:
            self.system.setup_schedules()
            mock_setup.assert_called_once()

    def test_start_system(self):
        """測試啟動系統"""
        with patch.object(self.system.collector_manager, 'start_all') as mock_start:
            self.system.start()
            mock_start.assert_called_once()

    def test_stop_system(self):
        """測試停止系統"""
        with patch.object(self.system.collector_manager, 'stop_all') as mock_stop:
            self.system.stop()
            mock_stop.assert_called_once()

    def test_collect_all_data(self):
        """測試收集所有資料"""
        with patch.object(self.system.executor, 'collect_all_data') as mock_collect:
            self.system.collect_all()
            mock_collect.assert_called_once()

    def test_get_status(self):
        """測試獲取系統狀態"""
        mock_status = {
            'running': False,
            'collectors': {},
            'symbols': ['2330.TW'],
            'symbol_count': 1
        }
        
        with patch.object(self.system.collector_manager, 'get_status', 
                         return_value=mock_status) as mock_get_status:
            status = self.system.get_status()
            mock_get_status.assert_called_once()
            assert status == mock_status

    def test_save_config(self):
        """測試儲存配置"""
        config_path = "test_config.json"
        
        with patch.object(self.system.config_manager, 'save_config', 
                         return_value=True) as mock_save:
            result = self.system.save_config(config_path)
            mock_save.assert_called_once_with(self.system.config, config_path)
            assert result is True

    def test_update_symbols(self):
        """測試更新股票代碼列表"""
        new_symbols = ["2454.TW", "2412.TW", "2308.TW"]
        
        self.system.update_symbols(new_symbols)
        
        assert self.system.symbols == new_symbols
        assert self.system.collector_manager.symbols == new_symbols
        assert self.system.executor.symbols == new_symbols


class TestCollectionConfigManager:
    """配置管理器測試類別"""

    def setup_method(self):
        """設定測試環境"""
        self.config_manager = CollectionConfigManager()

    def test_get_default_config(self):
        """測試獲取預設配置"""
        config = self.config_manager.get_default_config()
        
        assert 'symbols' in config
        assert 'collectors' in config
        assert isinstance(config['symbols'], list)
        assert isinstance(config['collectors'], dict)
        assert len(config['symbols']) > 0

    def test_load_config_default(self):
        """測試載入預設配置"""
        config = self.config_manager.load_config()
        
        assert 'symbols' in config
        assert 'collectors' in config

    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('json.load')
    def test_load_config_from_file(self, mock_json_load, mock_open, mock_exists):
        """測試從檔案載入配置"""
        mock_exists.return_value = True
        mock_config = {'symbols': ['TEST.TW'], 'collectors': {}}
        mock_json_load.return_value = mock_config
        
        config = self.config_manager.load_config("test_config.json")
        
        assert config == mock_config
        mock_exists.assert_called_once_with("test_config.json")
        mock_open.assert_called_once()

    def test_validate_config_valid(self):
        """測試驗證有效配置"""
        valid_config = {
            'symbols': ['2330.TW'],
            'collectors': {'market_data': {'enabled': True}}
        }
        
        result = self.config_manager.validate_config(valid_config)
        assert result is True

    def test_validate_config_invalid(self):
        """測試驗證無效配置"""
        invalid_config = {'symbols': 'not_a_list'}
        
        result = self.config_manager.validate_config(invalid_config)
        assert result is False

    @patch('builtins.open')
    @patch('json.dump')
    def test_save_config(self, mock_json_dump, mock_open):
        """測試儲存配置"""
        config = {'test': 'data'}
        config_path = "test_config.json"
        
        result = self.config_manager.save_config(config, config_path)
        
        assert result is True
        mock_open.assert_called_once_with(config_path, "w", encoding="utf-8")
        mock_json_dump.assert_called_once()


class TestCollectorManager:
    """收集器管理器測試類別"""

    def setup_method(self):
        """設定測試環境"""
        self.config = {
            'collectors': {
                'market_data': {'enabled': True, 'source': 'yahoo'},
                'news_sentiment': {'enabled': False}
            }
        }
        self.symbols = ['2330.TW', '2317.TW']
        self.manager = CollectorManager(self.config, self.symbols)

    @patch('src.data_sources.collector_manager.MarketDataCollector')
    def test_initialize_collectors(self, mock_market_collector):
        """測試初始化收集器"""
        self.manager.initialize_collectors()
        
        # 檢查啟用的收集器是否被初始化
        mock_market_collector.assert_called_once()

    def test_get_status(self):
        """測試獲取狀態"""
        status = self.manager.get_status()
        
        assert 'running' in status
        assert 'collectors' in status
        assert 'symbols' in status
        assert 'symbol_count' in status
        assert status['symbols'] == self.symbols
        assert status['symbol_count'] == len(self.symbols)


class TestCollectionExecutor:
    """收集執行器測試類別"""

    def setup_method(self):
        """設定測試環境"""
        self.config = {
            'collectors': {
                'market_data': {'enabled': True},
                'financial_statement': {'enabled': True},
                'news_sentiment': {'enabled': True}
            }
        }
        self.collectors = {
            'market_data': Mock(),
            'financial_statement': Mock(),
            'news_sentiment': Mock()
        }
        self.symbols = ['2330.TW', '2317.TW']
        self.executor = CollectionExecutor(self.config, self.collectors, self.symbols)

    def test_collect_all_data(self):
        """測試收集所有資料"""
        self.executor.collect_all_data()
        
        # 檢查所有收集器的 trigger_now 方法是否被調用
        self.collectors['market_data'].trigger_now.assert_called()
        self.collectors['financial_statement'].trigger_now.assert_called()
        self.collectors['news_sentiment'].trigger_now.assert_called()

    def test_collect_by_symbol(self):
        """測試收集特定股票資料"""
        symbol = '2330.TW'
        
        self.executor.collect_by_symbol(symbol)
        
        # 檢查所有收集器是否使用指定股票代碼
        for collector in self.collectors.values():
            collector.trigger_now.assert_called()

    def test_get_collection_statistics(self):
        """測試獲取收集統計"""
        stats = self.executor.get_collection_statistics()
        
        assert 'total_symbols' in stats
        assert 'enabled_collectors' in stats
        assert 'collector_stats' in stats
        assert stats['total_symbols'] == len(self.symbols)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
