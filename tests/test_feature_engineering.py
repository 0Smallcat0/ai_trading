"""
特徵工程測試模組

此模組測試特徵工程相關功能，包括特徵選擇、降維和特徵存儲。
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.features import FeatureCalculator, compute_features
from src.core.feature_store import FeatureStore


class TestFeatureEngineering(unittest.TestCase):
    """測試特徵工程功能"""

    def setUp(self):
        """設置測試環境"""
        # 創建測試資料
        np.random.seed(42)
        n_samples = 100
        n_features = 20
        
        # 創建特徵矩陣
        self.X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f'feature_{i}' for i in range(n_features)]
        )
        
        # 創建目標變數（只與前 5 個特徵相關）
        self.y = pd.Series(
            np.dot(self.X.iloc[:, :5], np.random.randn(5)) + np.random.randn(n_samples) * 0.1,
            name='target'
        )
        
        # 創建日期索引
        dates = [datetime.now() - timedelta(days=i) for i in range(n_samples)]
        self.X.index = dates
        self.y.index = dates
        
        # 創建測試用的價格資料
        self.price_data = pd.DataFrame({
            '收盤價': np.random.randn(n_samples).cumsum() + 100,  # 隨機漫步價格
            '開盤價': np.random.randn(n_samples).cumsum() + 100,
            '最高價': np.random.randn(n_samples).cumsum() + 102,
            '最低價': np.random.randn(n_samples).cumsum() + 98,
            '成交股數': np.random.randint(1000, 10000, n_samples)
        }, index=dates)
        
        # 創建測試用的資料字典
        self.data_dict = {
            'price': self.price_data
        }
        
        # 創建特徵計算器
        self.calculator = FeatureCalculator(self.data_dict)
        
        # 創建特徵存儲
        self.feature_store = FeatureStore(base_dir='tests/test_features')

    def tearDown(self):
        """清理測試環境"""
        # 刪除測試特徵存儲目錄
        if os.path.exists('tests/test_features'):
            import shutil
            shutil.rmtree('tests/test_features')

    def test_feature_selection_f_regression(self):
        """測試 F 檢定特徵選擇"""
        # 使用 F 檢定選擇特徵
        selected_df, selector = self.calculator.select_features(
            self.X, self.y, method='f_regression', k=5
        )
        
        # 檢查結果
        self.assertEqual(selected_df.shape[1], 5)
        self.assertIsNotNone(selector)
        
        # 檢查選擇的特徵是否包含前 5 個特徵（這些特徵與目標變數相關）
        selected_features = selected_df.columns.tolist()
        original_features = [f'feature_{i}' for i in range(5)]
        
        # 至少有一些相關特徵被選中
        self.assertTrue(any(f in selected_features for f in original_features))

    def test_feature_selection_rfe(self):
        """測試遞迴特徵消除"""
        # 使用遞迴特徵消除選擇特徵
        selected_df, selector = self.calculator.select_features(
            self.X, self.y, method='rfe', k=5
        )
        
        # 檢查結果
        self.assertEqual(selected_df.shape[1], 5)
        self.assertIsNotNone(selector)

    def test_feature_selection_lasso(self):
        """測試 Lasso 特徵選擇"""
        # 使用 Lasso 選擇特徵
        selected_df, selector = self.calculator.select_features(
            self.X, self.y, method='lasso', k=5
        )
        
        # 檢查結果
        self.assertLessEqual(selected_df.shape[1], 5)
        self.assertIsNotNone(selector)

    def test_dimensionality_reduction_pca(self):
        """測試 PCA 降維"""
        # 使用 PCA 降維
        reduced_df, reducer = self.calculator.reduce_dimensions(
            self.X, n_components=5, method='pca'
        )
        
        # 檢查結果
        self.assertEqual(reduced_df.shape[1], 5)
        self.assertIsNotNone(reducer)
        
        # 檢查解釋方差比例
        self.assertTrue(hasattr(reducer, 'explained_variance_ratio_'))
        self.assertGreater(sum(reducer.explained_variance_ratio_), 0.8)  # 至少解釋 80% 的方差

    def test_dimensionality_reduction_pca_auto_components(self):
        """測試 PCA 自動選擇組件數量"""
        # 使用 PCA 降維，自動選擇組件數量
        reduced_df, reducer = self.calculator.reduce_dimensions(
            self.X, n_components=None, method='pca', variance_ratio=0.9
        )
        
        # 檢查結果
        self.assertLessEqual(reduced_df.shape[1], self.X.shape[1])
        self.assertIsNotNone(reducer)
        
        # 檢查解釋方差比例
        self.assertTrue(hasattr(reducer, 'explained_variance_ratio_'))
        self.assertGreater(sum(reducer.explained_variance_ratio_), 0.9)  # 至少解釋 90% 的方差

    def test_feature_importance(self):
        """測試特徵重要性計算"""
        # 計算特徵重要性
        importance = self.calculator.calculate_feature_importance(
            self.X, self.y, method='random_forest'
        )
        
        # 檢查結果
        self.assertEqual(len(importance), self.X.shape[1])
        self.assertAlmostEqual(importance.sum(), 1.0, places=5)  # 重要性總和為 1
        
        # 檢查前 5 個重要特徵
        top_features = importance.nlargest(5).index.tolist()
        original_features = [f'feature_{i}' for i in range(5)]
        
        # 至少有一些相關特徵被識別為重要
        self.assertTrue(any(f in top_features for f in original_features))

    def test_feature_store(self):
        """測試特徵存儲"""
        # 保存特徵
        version = self.feature_store.save_features(
            self.X, 'test_features',
            metadata={'description': 'Test features'},
            tags=['test', 'features']
        )
        
        # 檢查版本
        self.assertIsNotNone(version)
        
        # 載入特徵
        loaded_df, metadata = self.feature_store.load_features('test_features', version)
        
        # 檢查載入的特徵
        pd.testing.assert_frame_equal(loaded_df, self.X)
        self.assertEqual(metadata['description'], 'Test features')
        
        # 測試列出特徵
        features = self.feature_store.list_features()
        self.assertIn('test_features', features)
        
        # 測試列出版本
        versions = self.feature_store.list_versions('test_features')
        self.assertIn(version, versions)
        
        # 測試獲取元數據
        metadata = self.feature_store.get_metadata('test_features', version)
        self.assertEqual(metadata['description'], 'Test features')
        
        # 測試搜索特徵
        results = self.feature_store.search_features(tags=['test'])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'test_features')

    def test_compute_features_with_selection_and_reduction(self):
        """測試計算特徵並進行選擇和降維"""
        # 使用 compute_features 函數計算特徵
        features = compute_features(
            normalize=True,
            remove_extremes=True,
            clean_data=True,
            feature_selection=True,
            feature_selection_method='f_regression',
            feature_selection_k=10,
            dimensionality_reduction=True,
            dimensionality_reduction_method='pca',
            n_components=5,
            save_to_feature_store=False
        )
        
        # 檢查結果
        self.assertIsNotNone(features)
        
        # 如果特徵不為空，則檢查維度
        if not features.empty:
            self.assertLessEqual(features.shape[1], 5)  # 降維後應該有 5 個特徵


if __name__ == '__main__':
    unittest.main()
