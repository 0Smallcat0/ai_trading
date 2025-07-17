# -*- coding: utf-8 -*-
"""tsfresh 自動因子挖掘引擎

此模組封裝 tsfresh 庫的自動因子挖掘功能，提供統一的特徵提取、
特徵選擇和模型訓練接口。

主要功能：
- 自動時間序列特徵提取 (5000+ 特徵)
- 統計檢驗特徵選擇
- 批量處理和並行計算
- 內存優化和性能調優
- 結果快取和增量更新

支援的特徵類型：
- 統計特徵 (均值、方差、偏度、峰度等)
- 頻域特徵 (FFT、功率譜密度等)
- 時域特徵 (自相關、趨勢等)
- 複雜特徵 (近似熵、樣本熵等)

Example:
    >>> engine = TsfreshEngine({'n_jobs': 4})
    >>> features = engine.extract_features(data)
    >>> selected = engine.select_features(features, target)
"""

import logging
import warnings
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

# 設定日誌
logger = logging.getLogger(__name__)

# 抑制 tsfresh 的警告
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)


class TsfreshEngine:
    """tsfresh 自動因子挖掘引擎
    
    封裝 tsfresh 庫的功能，提供統一的特徵提取和選擇接口。
    
    Attributes:
        config: 引擎配置參數
        n_jobs: 並行處理進程數
        feature_settings: 特徵提取設定
        
    Example:
        >>> engine = TsfreshEngine({
        ...     'n_jobs': 4,
        ...     'feature_selection': True,
        ...     'impute_function': 'median'
        ... })
        >>> features = engine.extract_features(data)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化 tsfresh 引擎
        
        Args:
            config: 配置參數
                - n_jobs: 並行處理進程數
                - feature_selection: 是否啟用特徵選擇
                - impute_function: 缺失值填充方法
                - max_timeshift: 最大時間偏移
                - min_timeshift: 最小時間偏移
                
        Raises:
            ImportError: 當 tsfresh 庫未安裝時
        """
        self.config = config or {}
        
        # 基本配置
        self.n_jobs = self.config.get('n_jobs', mp.cpu_count())
        self.feature_selection = self.config.get('feature_selection', True)
        self.impute_function = self.config.get('impute_function', 'median')
        
        # 時間序列配置
        self.max_timeshift = self.config.get('max_timeshift', 20)
        self.min_timeshift = self.config.get('min_timeshift', 5)
        
        # 性能配置
        self.chunk_size = self.config.get('chunk_size', 1000)
        self.memory_limit_gb = self.config.get('memory_limit_gb', 4)
        
        # 初始化 tsfresh 組件
        self._initialize_tsfresh()
        
        logger.info(f"tsfresh 引擎初始化完成，並行數: {self.n_jobs}")
    
    def _initialize_tsfresh(self):
        """初始化 tsfresh 組件"""
        try:
            # 導入 tsfresh 模組
            import tsfresh
            from tsfresh import extract_features, select_features
            from tsfresh.utilities.dataframe_functions import roll_time_series, impute
            from tsfresh.feature_extraction import ComprehensiveFCParameters
            from tsfresh.feature_selection.relevance import calculate_relevance_table
            
            # 保存引用
            self.tsfresh = tsfresh
            self.extract_features = extract_features
            self.select_features = select_features
            self.roll_time_series = roll_time_series
            self.impute = impute
            self.ComprehensiveFCParameters = ComprehensiveFCParameters
            self.calculate_relevance_table = calculate_relevance_table
            
            # 設定特徵提取參數
            self.feature_settings = self._get_feature_settings()
            
            logger.info(f"tsfresh 版本: {tsfresh.__version__}")
            
        except ImportError as e:
            logger.error(f"tsfresh 庫導入失敗: {e}")
            raise ImportError("請安裝 tsfresh: pip install tsfresh") from e
    
    def _get_feature_settings(self) -> Dict[str, Any]:
        """獲取特徵提取設定
        
        Returns:
            特徵提取設定字典
        """
        # 使用綜合特徵參數集合
        settings = self.ComprehensiveFCParameters()
        
        # 根據配置調整設定
        if self.config.get('minimal_features', False):
            # 使用最小特徵集合以提升性能
            settings = self._get_minimal_feature_settings()
        
        return settings
    
    def _get_minimal_feature_settings(self) -> Dict[str, Any]:
        """獲取最小特徵設定
        
        Returns:
            最小特徵設定，用於快速計算
        """
        return {
            "mean": None,
            "median": None,
            "std": None,
            "var": None,
            "skewness": None,
            "kurtosis": None,
            "minimum": None,
            "maximum": None,
            "quantile": [{"q": 0.1}, {"q": 0.9}],
            "autocorrelation": [{"lag": 1}, {"lag": 2}, {"lag": 3}],
            "linear_trend": [{"attr": "slope"}, {"attr": "intercept"}],
            "agg_linear_trend": [
                {"attr": "slope", "chunk_len": 5, "f_agg": "mean"},
                {"attr": "slope", "chunk_len": 10, "f_agg": "mean"}
            ]
        }
    
    def extract_features(self,
                        data: pd.DataFrame,
                        column_id: str = 'id',
                        column_sort: str = 'time',
                        column_value: str = 'value',
                        **kwargs) -> pd.DataFrame:
        """提取時間序列特徵
        
        Args:
            data: 時間序列數據 (長格式)
            column_id: ID 欄位名稱
            column_sort: 時間欄位名稱
            column_value: 數值欄位名稱
            **kwargs: 其他參數
            
        Returns:
            提取的特徵數據框架
            
        Raises:
            ValueError: 當數據格式不正確時
            RuntimeError: 當特徵提取失敗時
        """
        try:
            # 數據驗證
            self._validate_data(data, column_id, column_sort, column_value)
            
            # 數據預處理
            processed_data = self._preprocess_data(data, column_id, column_sort, column_value)
            
            # 創建滾動時間序列
            if kwargs.get('use_rolling', True):
                rolled_data = self._create_rolling_series(processed_data, column_id, column_sort)
            else:
                rolled_data = processed_data
            
            # 提取特徵
            logger.info(f"開始提取特徵，數據量: {len(rolled_data)}")
            
            features = self.extract_features(
                rolled_data,
                column_id=column_id,
                column_sort=column_sort,
                default_fc_parameters=self.feature_settings,
                n_jobs=self.n_jobs,
                impute_function=self._get_impute_function(),
                disable_progressbar=True
            )
            
            # 後處理
            features = self._postprocess_features(features)
            
            logger.info(f"特徵提取完成，生成 {len(features.columns)} 個特徵")
            return features
            
        except Exception as e:
            logger.error(f"特徵提取失敗: {e}")
            raise RuntimeError(f"特徵提取失敗: {e}") from e
    
    def _validate_data(self, data: pd.DataFrame, column_id: str, 
                      column_sort: str, column_value: str):
        """驗證輸入數據"""
        if data.empty:
            raise ValueError("輸入數據為空")
        
        required_columns = [column_id, column_sort, column_value]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"缺少必要欄位: {missing_columns}")
        
        # 檢查數據類型
        if not pd.api.types.is_numeric_dtype(data[column_value]):
            raise ValueError(f"數值欄位 {column_value} 必須是數值類型")
        
        # 檢查時間欄位
        if not pd.api.types.is_datetime64_any_dtype(data[column_sort]):
            try:
                data[column_sort] = pd.to_datetime(data[column_sort])
            except:
                raise ValueError(f"時間欄位 {column_sort} 無法轉換為日期時間類型")
    
    def _preprocess_data(self, data: pd.DataFrame, column_id: str,
                        column_sort: str, column_value: str) -> pd.DataFrame:
        """數據預處理"""
        processed_data = data.copy()
        
        # 排序
        processed_data = processed_data.sort_values([column_id, column_sort])
        
        # 處理缺失值
        processed_data[column_value] = processed_data[column_value].fillna(method='ffill')
        processed_data = processed_data.dropna(subset=[column_value])
        
        # 處理異常值 (使用 3-sigma 規則)
        for id_val in processed_data[column_id].unique():
            mask = processed_data[column_id] == id_val
            values = processed_data.loc[mask, column_value]
            
            mean_val = values.mean()
            std_val = values.std()
            
            if std_val > 0:
                outlier_mask = np.abs(values - mean_val) > 3 * std_val
                processed_data.loc[mask & outlier_mask, column_value] = mean_val
        
        return processed_data
    
    def _create_rolling_series(self, data: pd.DataFrame, column_id: str,
                              column_sort: str) -> pd.DataFrame:
        """創建滾動時間序列"""
        try:
            rolled_data = self.roll_time_series(
                data,
                column_id=column_id,
                column_sort=column_sort,
                max_timeshift=self.max_timeshift,
                min_timeshift=self.min_timeshift
            )
            
            logger.debug(f"滾動序列創建完成，數據量: {len(rolled_data)}")
            return rolled_data
            
        except Exception as e:
            logger.warning(f"滾動序列創建失敗，使用原始數據: {e}")
            return data
    
    def _get_impute_function(self):
        """獲取缺失值填充函數"""
        if self.impute_function == 'median':
            return lambda x: x.fillna(x.median())
        elif self.impute_function == 'mean':
            return lambda x: x.fillna(x.mean())
        elif self.impute_function == 'zero':
            return lambda x: x.fillna(0)
        else:
            return self.impute
    
    def _postprocess_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """特徵後處理"""
        # 移除全為 NaN 的特徵
        features = features.dropna(axis=1, how='all')
        
        # 移除常數特徵
        constant_features = features.columns[features.nunique() <= 1]
        if len(constant_features) > 0:
            features = features.drop(columns=constant_features)
            logger.debug(f"移除 {len(constant_features)} 個常數特徵")
        
        # 處理無限值
        features = features.replace([np.inf, -np.inf], np.nan)
        
        # 填充剩餘的 NaN 值
        features = features.fillna(0)
        
        return features
    
    def select_features(self,
                       features: pd.DataFrame,
                       target: pd.Series,
                       test_for_binary_target_binary_feature: str = 'fisher',
                       test_for_binary_target_real_feature: str = 'mann',
                       test_for_real_target_binary_feature: str = 'mann',
                       test_for_real_target_real_feature: str = 'kendall',
                       fdr_level: float = 0.05,
                       **kwargs) -> pd.DataFrame:
        """特徵選擇
        
        Args:
            features: 特徵數據框架
            target: 目標變量
            test_for_binary_target_binary_feature: 二元目標-二元特徵檢驗
            test_for_binary_target_real_feature: 二元目標-連續特徵檢驗
            test_for_real_target_binary_feature: 連續目標-二元特徵檢驗
            test_for_real_target_real_feature: 連續目標-連續特徵檢驗
            fdr_level: 錯誤發現率水平
            **kwargs: 其他參數
            
        Returns:
            選擇後的特徵數據框架
        """
        try:
            if not self.feature_selection:
                logger.info("特徵選擇已禁用，返回所有特徵")
                return features
            
            # 對齊索引
            common_index = features.index.intersection(target.index)
            if len(common_index) == 0:
                raise ValueError("特徵和目標變量沒有共同的索引")
            
            features_aligned = features.loc[common_index]
            target_aligned = target.loc[common_index]
            
            # 移除目標變量中的 NaN 值
            valid_mask = ~target_aligned.isna()
            features_aligned = features_aligned[valid_mask]
            target_aligned = target_aligned[valid_mask]
            
            if len(features_aligned) == 0:
                raise ValueError("沒有有效的樣本進行特徵選擇")
            
            logger.info(f"開始特徵選擇，特徵數: {len(features_aligned.columns)}, 樣本數: {len(features_aligned)}")
            
            # 執行特徵選擇
            selected_features = self.select_features(
                features_aligned,
                target_aligned,
                test_for_binary_target_binary_feature=test_for_binary_target_binary_feature,
                test_for_binary_target_real_feature=test_for_binary_target_real_feature,
                test_for_real_target_binary_feature=test_for_real_target_binary_feature,
                test_for_real_target_real_feature=test_for_real_target_real_feature,
                fdr_level=fdr_level,
                n_jobs=self.n_jobs
            )
            
            logger.info(f"特徵選擇完成，保留 {len(selected_features.columns)} 個特徵")
            return selected_features
            
        except Exception as e:
            logger.error(f"特徵選擇失敗: {e}")
            # 如果特徵選擇失敗，返回原始特徵的子集
            logger.warning("特徵選擇失敗，返回前50個特徵")
            return features.iloc[:, :50] if len(features.columns) > 50 else features
    
    def calculate_relevance(self,
                           features: pd.DataFrame,
                           target: pd.Series,
                           **kwargs) -> pd.DataFrame:
        """計算特徵相關性
        
        Args:
            features: 特徵數據框架
            target: 目標變量
            **kwargs: 其他參數
            
        Returns:
            特徵相關性表
        """
        try:
            # 對齊數據
            common_index = features.index.intersection(target.index)
            features_aligned = features.loc[common_index]
            target_aligned = target.loc[common_index]
            
            # 計算相關性
            relevance_table = self.calculate_relevance_table(
                features_aligned,
                target_aligned,
                n_jobs=self.n_jobs
            )
            
            # 排序
            relevance_table = relevance_table.sort_values('p_value')
            
            logger.info(f"相關性計算完成，{len(relevance_table)} 個特徵")
            return relevance_table
            
        except Exception as e:
            logger.error(f"相關性計算失敗: {e}")
            raise RuntimeError(f"相關性計算失敗: {e}") from e
    
    def get_feature_importance(self,
                              features: pd.DataFrame,
                              target: pd.Series,
                              method: str = 'mutual_info') -> pd.Series:
        """計算特徵重要性
        
        Args:
            features: 特徵數據框架
            target: 目標變量
            method: 重要性計算方法
            
        Returns:
            特徵重要性序列
        """
        try:
            from sklearn.feature_selection import mutual_info_regression, f_regression
            from sklearn.ensemble import RandomForestRegressor
            
            # 對齊數據
            common_index = features.index.intersection(target.index)
            X = features.loc[common_index].fillna(0)
            y = target.loc[common_index].fillna(0)
            
            if method == 'mutual_info':
                importance = mutual_info_regression(X, y, random_state=42)
            elif method == 'f_test':
                importance, _ = f_regression(X, y)
            elif method == 'random_forest':
                rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=self.n_jobs)
                rf.fit(X, y)
                importance = rf.feature_importances_
            else:
                raise ValueError(f"不支援的重要性計算方法: {method}")
            
            # 創建重要性序列
            importance_series = pd.Series(importance, index=X.columns)
            importance_series = importance_series.sort_values(ascending=False)
            
            logger.info(f"特徵重要性計算完成，方法: {method}")
            return importance_series
            
        except Exception as e:
            logger.error(f"特徵重要性計算失敗: {e}")
            raise RuntimeError(f"特徵重要性計算失敗: {e}") from e
    
    def get_engine_info(self) -> Dict[str, Any]:
        """獲取引擎資訊
        
        Returns:
            引擎詳細資訊
        """
        return {
            'engine_name': 'TsfreshEngine',
            'version': getattr(self.tsfresh, '__version__', 'unknown'),
            'config': self.config,
            'n_jobs': self.n_jobs,
            'feature_selection': self.feature_selection,
            'max_timeshift': self.max_timeshift,
            'min_timeshift': self.min_timeshift,
            'supported_features': len(self.feature_settings),
            'memory_limit_gb': self.memory_limit_gb
        }
