"""分散式計算模組測試

測試分散式計算接口的功能，包括 Dask、Ray 和本地計算引擎。
"""

import os
import sys
import unittest
import pandas as pd
from unittest.mock import patch, MagicMock

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.distributed_computing import (
    DistributedComputeManager,
    DaskComputeEngine,
    RayComputeEngine,
    LocalComputeEngine,
    get_compute_manager,
    initialize_distributed_computing,
    shutdown_distributed_computing
)


class TestLocalComputeEngine(unittest.TestCase):
    """測試本地計算引擎"""def setUp(self):
        """設置測試環境"""self.engine = LocalComputeEngine()
        self.test_data = pd.DataFrame({
            'A': np.random.randn(100),
            'B': np.random.randn(100),
            'C': np.random.randn(100)
        })

    def test_initialize(self):
        """測試初始化"""result = self.engine.initialize()
        self.assertTrue(result)
        self.assertTrue(self.engine.is_available())

    def test_map_partitions(self):
        """測試分區映射"""def test_func(df):
            return df.mean()

        result = self.engine.map_partitions(test_func, self.test_data)
        expected = test_func(self.test_data)

        pd.testing.assert_series_equal(result, expected)

    def test_parallel_apply(self):
        """測試並行應用"""def test_func(data):
            return data * 2

        data_list = [1, 2, 3, 4, 5]
        result = self.engine.parallel_apply(test_func, data_list)
        expected = [2, 4, 6, 8, 10]

        self.assertEqual(result, expected)

    def test_shutdown(self):
        """測試關閉"""# 本地引擎的關閉操作應該是無害的
        self.engine.shutdown()
        self.assertTrue(self.engine.is_available())


class TestDaskComputeEngine(unittest.TestCase):
    """測試 Dask 計算引擎"""def setUp(self):
        """設置測試環境"""self.engine = DaskComputeEngine()
        self.test_data = pd.DataFrame({
            'A': np.random.randn(100),
            'B': np.random.randn(100),
            'C': np.random.randn(100)
        })

    def test_initialize_without_dask(self):
        """測試在沒有 Dask 的情況下初始化"""with patch('src.core.distributed_computing.DASK_AVAILABLE', False):
            result = self.engine.initialize()
            self.assertFalse(result)
            self.assertFalse(self.engine.is_available())

    @patch('src.core.distributed_computing.DASK_AVAILABLE', True)
    @patch('src.core.distributed_computing.Client')
    def test_initialize_with_dask(self, mock_client):
        """測試在有 Dask 的情況下初始化"""mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance

        result = self.engine.initialize()
        self.assertTrue(result)
        self.assertTrue(self.engine.is_available())

        # 測試關閉
        self.engine.shutdown()
        mock_client_instance.close.assert_called_once()

    def test_map_partitions_unavailable(self):
        """測試在引擎不可用時調用 map_partitions"""with self.assertRaises(RuntimeError):
            self.engine.map_partitions(lambda x: x, self.test_data)

    def test_parallel_apply_unavailable(self):
        """測試在引擎不可用時調用 parallel_apply"""with self.assertRaises(RuntimeError):
            self.engine.parallel_apply(lambda x: x, [1, 2, 3])


class TestRayComputeEngine(unittest.TestCase):
    """測試 Ray 計算引擎"""def setUp(self):
        """設置測試環境"""self.engine = RayComputeEngine()
        self.test_data = pd.DataFrame({
            'A': np.random.randn(100),
            'B': np.random.randn(100),
            'C': np.random.randn(100)
        })

    def test_initialize_without_ray(self):
        """測試在沒有 Ray 的情況下初始化"""with patch('src.core.distributed_computing.RAY_AVAILABLE', False):
            result = self.engine.initialize()
            self.assertFalse(result)
            self.assertFalse(self.engine.is_available())

    @patch('src.core.distributed_computing.RAY_AVAILABLE', True)
    @patch('src.core.distributed_computing.ray')
    def test_initialize_with_ray(self, mock_ray):
        """測試在有 Ray 的情況下初始化"""mock_ray.is_initialized.return_value = False
        mock_ray.init.return_value = None

        result = self.engine.initialize()
        self.assertTrue(result)

        # 測試關閉
        mock_ray.is_initialized.return_value = True
        self.engine.shutdown()
        mock_ray.shutdown.assert_called_once()

    def test_map_partitions_unavailable(self):
        """測試在引擎不可用時調用 map_partitions"""with self.assertRaises(RuntimeError):
            self.engine.map_partitions(lambda x: x, self.test_data)

    def test_parallel_apply_unavailable(self):
        """測試在引擎不可用時調用 parallel_apply"""with self.assertRaises(RuntimeError):
            self.engine.parallel_apply(lambda x: x, [1, 2, 3])


class TestDistributedComputeManager(unittest.TestCase):
    """測試分散式計算管理器"""def setUp(self):
        """設置測試環境"""self.manager = DistributedComputeManager()
        self.test_data = pd.DataFrame({
            'A': np.random.randn(100),
            'B': np.random.randn(100),
            'C': np.random.randn(100)
        })

    def test_initialize_auto(self):
        """測試自動初始化"""result = self.manager.initialize()
        self.assertTrue(result)
        self.assertTrue(self.manager.is_available())

        # 檢查引擎信息
        engine_info = self.manager.get_engine_info()
        self.assertIn("engine", engine_info)
        self.assertTrue(engine_info["available"])

    def test_initialize_local(self):
        """測試指定本地引擎初始化"""manager = DistributedComputeManager(preferred_engine="local")
        result = manager.initialize()
        self.assertTrue(result)

        engine_info = manager.get_engine_info()
        self.assertEqual(engine_info["engine"], "local")

    def test_initialize_invalid_engine(self):
        """測試指定無效引擎"""manager = DistributedComputeManager(preferred_engine="invalid")
        result = manager.initialize()
        # 應該回退到本地計算
        self.assertTrue(result)

        engine_info = manager.get_engine_info()
        self.assertEqual(engine_info["engine"], "local")

    def test_map_partitions(self):
        """測試分區映射"""self.manager.initialize()

        def test_func(df):
            return df.mean()

        result = self.manager.map_partitions(test_func, self.test_data)
        expected = test_func(self.test_data)

        pd.testing.assert_series_equal(result, expected)

    def test_parallel_apply(self):
        """測試並行應用"""self.manager.initialize()

        def test_func(data):
            return data * 2

        data_list = [1, 2, 3, 4, 5]
        result = self.manager.parallel_apply(test_func, data_list)
        expected = [2, 4, 6, 8, 10]

        self.assertEqual(result, expected)

    def test_unavailable_operations(self):
        """測試在管理器不可用時的操作"""# 不初始化管理器
        with self.assertRaises(RuntimeError):
            self.manager.map_partitions(lambda x: x, self.test_data)

        with self.assertRaises(RuntimeError):
            self.manager.parallel_apply(lambda x: x, [1, 2, 3])

    def test_shutdown(self):
        """測試關閉"""self.manager.initialize()
        self.assertTrue(self.manager.is_available())

        self.manager.shutdown()
        self.assertFalse(self.manager.is_available())


class TestGlobalFunctions(unittest.TestCase):
    """測試全局函數"""def setUp(self):
        """設置測試環境"""# 確保全局管理器被重置
        shutdown_distributed_computing()

    def tearDown(self):
        """清理測試環境"""shutdown_distributed_computing()

    def test_get_compute_manager(self):
        """測試獲取計算管理器"""manager1 = get_compute_manager()
        manager2 = get_compute_manager()

        # 應該返回同一個實例
        self.assertIs(manager1, manager2)

    def test_initialize_distributed_computing(self):
        """測試初始化分散式計算"""result = initialize_distributed_computing()
        self.assertTrue(result)

        manager = get_compute_manager()
        self.assertTrue(manager.is_available())

    def test_shutdown_distributed_computing(self):
        """測試關閉分散式計算"""
        initialize_distributed_computing()
        manager = get_compute_manager()
        self.assertTrue(manager.is_available())

        shutdown_distributed_computing()

        # 獲取新的管理器應該是未初始化的
        new_manager = get_compute_manager()
        self.assertFalse(new_manager.is_available())


if __name__ == "__main__":
    unittest.main()
