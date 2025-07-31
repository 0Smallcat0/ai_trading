# -*- coding: utf-8 -*-
"""
數據驗證器

此模組提供完整的數據質量檢查和驗證功能，
確保數據的準確性、完整性和一致性。

主要功能：
- 數據格式驗證
- 數據完整性檢查
- 數據一致性驗證
- 異常值檢測
- 數據質量評分

驗證類型：
- 實時行情數據驗證
- 歷史數據驗證
- 財務數據驗證
- 技術指標驗證
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """驗證結果數據類"""
    is_valid: bool
    quality_score: float  # 0-1之間的質量評分
    errors: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]
    
    def add_error(self, error: str):
        """添加錯誤"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)
    
    def calculate_quality_score(self):
        """計算質量評分"""
        # 基礎分數
        base_score = 1.0
        
        # 錯誤扣分
        error_penalty = len(self.errors) * 0.2
        warning_penalty = len(self.warnings) * 0.05
        
        # 計算最終分數
        self.quality_score = max(0.0, base_score - error_penalty - warning_penalty)


class DataValidator:
    """
    數據驗證器
    
    提供各種數據類型的驗證功能
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化數據驗證器
        
        Args:
            config: 驗證配置
        """
        self.config = config or {}
        
        # 驗證閾值
        self.thresholds = {
            'min_data_points': self.config.get('min_data_points', 10),
            'max_missing_ratio': self.config.get('max_missing_ratio', 0.1),
            'max_outlier_ratio': self.config.get('max_outlier_ratio', 0.05),
            'min_price': self.config.get('min_price', 0.01),
            'max_price_change': self.config.get('max_price_change', 0.5),  # 50%
            'max_volume_change': self.config.get('max_volume_change', 10.0)  # 10倍
        }
        
        logger.info("數據驗證器初始化完成")
    
    def validate_realtime_data(self, data: pd.DataFrame) -> ValidationResult:
        """
        驗證實時行情數據
        
        Args:
            data: 實時行情數據
            
        Returns:
            驗證結果
        """
        result = ValidationResult(
            is_valid=True,
            quality_score=1.0,
            errors=[],
            warnings=[],
            metrics={}
        )
        
        try:
            # 基本格式檢查
            self._check_basic_format(data, result)
            
            # 必需列檢查
            required_columns = ['symbol', 'price']
            self._check_required_columns(data, required_columns, result)
            
            # 數據類型檢查
            if 'price' in data.columns:
                self._check_numeric_column(data, 'price', result)
                self._check_price_validity(data, 'price', result)
            
            if 'volume' in data.columns:
                self._check_numeric_column(data, 'volume', result)
                self._check_volume_validity(data, 'volume', result)
            
            # 時間戳檢查
            if 'timestamp' in data.columns:
                self._check_timestamp_validity(data, 'timestamp', result)
            
            # 計算質量評分
            result.calculate_quality_score()
            
            # 記錄指標
            result.metrics.update({
                'total_records': len(data),
                'missing_values': data.isnull().sum().sum(),
                'duplicate_records': data.duplicated().sum()
            })
            
            logger.debug(f"實時數據驗證完成，質量評分: {result.quality_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"實時數據驗證失敗: {e}")
            result.add_error(f"驗證過程出錯: {str(e)}")
            result.calculate_quality_score()
            return result
    
    def validate_historical_data(self, data: pd.DataFrame) -> ValidationResult:
        """
        驗證歷史K線數據
        
        Args:
            data: 歷史K線數據
            
        Returns:
            驗證結果
        """
        result = ValidationResult(
            is_valid=True,
            quality_score=1.0,
            errors=[],
            warnings=[],
            metrics={}
        )
        
        try:
            # 基本格式檢查
            self._check_basic_format(data, result)
            
            # 必需列檢查
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            self._check_required_columns(data, required_columns, result)
            
            # OHLC數據邏輯檢查
            self._check_ohlc_logic(data, result)
            
            # 價格連續性檢查
            self._check_price_continuity(data, result)
            
            # 成交量合理性檢查
            if 'volume' in data.columns:
                self._check_volume_reasonableness(data, result)
            
            # 時間序列完整性檢查
            self._check_time_series_completeness(data, result)
            
            # 異常值檢測
            self._detect_outliers(data, result)
            
            # 計算質量評分
            result.calculate_quality_score()
            
            # 記錄指標
            result.metrics.update({
                'total_records': len(data),
                'date_range': self._get_date_range(data),
                'missing_values': data.isnull().sum().sum(),
                'zero_volume_days': (data.get('volume', pd.Series()) == 0).sum()
            })
            
            logger.debug(f"歷史數據驗證完成，質量評分: {result.quality_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"歷史數據驗證失敗: {e}")
            result.add_error(f"驗證過程出錯: {str(e)}")
            result.calculate_quality_score()
            return result
    
    def validate_financial_data(self, data: pd.DataFrame) -> ValidationResult:
        """
        驗證財務數據
        
        Args:
            data: 財務數據
            
        Returns:
            驗證結果
        """
        result = ValidationResult(
            is_valid=True,
            quality_score=1.0,
            errors=[],
            warnings=[],
            metrics={}
        )
        
        try:
            # 基本格式檢查
            self._check_basic_format(data, result)
            
            # 必需列檢查
            required_columns = ['symbol']
            self._check_required_columns(data, required_columns, result)
            
            # 財務比率合理性檢查
            self._check_financial_ratios(data, result)
            
            # 計算質量評分
            result.calculate_quality_score()
            
            # 記錄指標
            result.metrics.update({
                'total_records': len(data),
                'missing_values': data.isnull().sum().sum()
            })
            
            logger.debug(f"財務數據驗證完成，質量評分: {result.quality_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"財務數據驗證失敗: {e}")
            result.add_error(f"驗證過程出錯: {str(e)}")
            result.calculate_quality_score()
            return result
    
    def _check_basic_format(self, data: pd.DataFrame, result: ValidationResult):
        """檢查基本格式"""
        if data is None:
            result.add_error("數據為空")
            return
        
        if not isinstance(data, pd.DataFrame):
            result.add_error("數據不是DataFrame格式")
            return
        
        if len(data) == 0:
            result.add_error("數據為空DataFrame")
            return
        
        if len(data) < self.thresholds['min_data_points']:
            result.add_warning(f"數據點數量過少: {len(data)}")
    
    def _check_required_columns(self, data: pd.DataFrame, required_columns: List[str], result: ValidationResult):
        """檢查必需列"""
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            result.add_error(f"缺少必需列: {missing_columns}")
    
    def _check_numeric_column(self, data: pd.DataFrame, column: str, result: ValidationResult):
        """檢查數值列"""
        if column not in data.columns:
            return
        
        # 檢查數據類型
        if not pd.api.types.is_numeric_dtype(data[column]):
            result.add_error(f"列 {column} 不是數值類型")
            return
        
        # 檢查缺失值
        missing_count = data[column].isnull().sum()
        missing_ratio = missing_count / len(data)
        
        if missing_ratio > self.thresholds['max_missing_ratio']:
            result.add_error(f"列 {column} 缺失值過多: {missing_ratio:.2%}")
        elif missing_count > 0:
            result.add_warning(f"列 {column} 有 {missing_count} 個缺失值")
    
    def _check_price_validity(self, data: pd.DataFrame, price_column: str, result: ValidationResult):
        """檢查價格有效性"""
        if price_column not in data.columns:
            return
        
        prices = data[price_column].dropna()
        
        # 檢查負價格
        negative_prices = (prices < 0).sum()
        if negative_prices > 0:
            result.add_error(f"發現 {negative_prices} 個負價格")
        
        # 檢查過低價格
        low_prices = (prices < self.thresholds['min_price']).sum()
        if low_prices > 0:
            result.add_warning(f"發現 {low_prices} 個過低價格 (< {self.thresholds['min_price']})")
        
        # 檢查零價格
        zero_prices = (prices == 0).sum()
        if zero_prices > 0:
            result.add_warning(f"發現 {zero_prices} 個零價格")
    
    def _check_volume_validity(self, data: pd.DataFrame, volume_column: str, result: ValidationResult):
        """檢查成交量有效性"""
        if volume_column not in data.columns:
            return
        
        volumes = data[volume_column].dropna()
        
        # 檢查負成交量
        negative_volumes = (volumes < 0).sum()
        if negative_volumes > 0:
            result.add_error(f"發現 {negative_volumes} 個負成交量")
    
    def _check_timestamp_validity(self, data: pd.DataFrame, timestamp_column: str, result: ValidationResult):
        """檢查時間戳有效性"""
        if timestamp_column not in data.columns:
            return
        
        try:
            timestamps = pd.to_datetime(data[timestamp_column])
            
            # 檢查未來時間
            future_times = (timestamps > datetime.now()).sum()
            if future_times > 0:
                result.add_warning(f"發現 {future_times} 個未來時間戳")
            
        except Exception as e:
            result.add_error(f"時間戳格式錯誤: {str(e)}")
    
    def _check_ohlc_logic(self, data: pd.DataFrame, result: ValidationResult):
        """檢查OHLC邏輯"""
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in data.columns for col in required_cols):
            return
        
        # 檢查 high >= max(open, close) 和 low <= min(open, close)
        invalid_high = (data['high'] < data[['open', 'close']].max(axis=1)).sum()
        invalid_low = (data['low'] > data[['open', 'close']].min(axis=1)).sum()
        
        if invalid_high > 0:
            result.add_error(f"發現 {invalid_high} 個無效的最高價")
        
        if invalid_low > 0:
            result.add_error(f"發現 {invalid_low} 個無效的最低價")
    
    def _check_price_continuity(self, data: pd.DataFrame, result: ValidationResult):
        """檢查價格連續性"""
        if 'close' not in data.columns or len(data) < 2:
            return
        
        # 計算價格變化率
        price_changes = data['close'].pct_change().dropna()
        
        # 檢查異常大的價格變化
        large_changes = (abs(price_changes) > self.thresholds['max_price_change']).sum()
        if large_changes > 0:
            result.add_warning(f"發現 {large_changes} 個異常大的價格變化")
    
    def _check_volume_reasonableness(self, data: pd.DataFrame, result: ValidationResult):
        """檢查成交量合理性"""
        if 'volume' not in data.columns or len(data) < 2:
            return
        
        volumes = data['volume'].dropna()
        if len(volumes) < 2:
            return
        
        # 計算成交量變化倍數
        volume_ratios = volumes / volumes.shift(1)
        volume_ratios = volume_ratios.dropna()
        
        # 檢查異常大的成交量變化
        large_volume_changes = (volume_ratios > self.thresholds['max_volume_change']).sum()
        if large_volume_changes > 0:
            result.add_warning(f"發現 {large_volume_changes} 個異常大的成交量變化")
    
    def _check_time_series_completeness(self, data: pd.DataFrame, result: ValidationResult):
        """檢查時間序列完整性"""
        if not isinstance(data.index, pd.DatetimeIndex):
            return
        
        # 檢查時間序列是否有重複
        duplicated_dates = data.index.duplicated().sum()
        if duplicated_dates > 0:
            result.add_error(f"發現 {duplicated_dates} 個重複日期")
        
        # 檢查時間序列是否有大的間隔
        if len(data) > 1:
            time_diffs = data.index.to_series().diff().dropna()
            median_diff = time_diffs.median()
            large_gaps = (time_diffs > median_diff * 5).sum()
            
            if large_gaps > 0:
                result.add_warning(f"發現 {large_gaps} 個較大的時間間隔")
    
    def _detect_outliers(self, data: pd.DataFrame, result: ValidationResult):
        """檢測異常值"""
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            if column in ['volume']:  # 跳過成交量，因為它的分佈通常很不均勻
                continue
            
            values = data[column].dropna()
            if len(values) < 10:
                continue
            
            # 使用IQR方法檢測異常值
            Q1 = values.quantile(0.25)
            Q3 = values.quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = ((values < lower_bound) | (values > upper_bound)).sum()
            outlier_ratio = outliers / len(values)
            
            if outlier_ratio > self.thresholds['max_outlier_ratio']:
                result.add_warning(f"列 {column} 異常值比例過高: {outlier_ratio:.2%}")
    
    def _check_financial_ratios(self, data: pd.DataFrame, result: ValidationResult):
        """檢查財務比率合理性"""
        # 檢查市盈率
        if 'pe_ratio' in data.columns:
            pe_ratios = data['pe_ratio'].dropna()
            negative_pe = (pe_ratios < 0).sum()
            extreme_pe = (pe_ratios > 1000).sum()
            
            if negative_pe > 0:
                result.add_warning(f"發現 {negative_pe} 個負市盈率")
            
            if extreme_pe > 0:
                result.add_warning(f"發現 {extreme_pe} 個極端市盈率 (>1000)")
        
        # 檢查市淨率
        if 'pb_ratio' in data.columns:
            pb_ratios = data['pb_ratio'].dropna()
            negative_pb = (pb_ratios < 0).sum()
            
            if negative_pb > 0:
                result.add_warning(f"發現 {negative_pb} 個負市淨率")
    
    def _get_date_range(self, data: pd.DataFrame) -> Dict[str, str]:
        """獲取日期範圍"""
        if isinstance(data.index, pd.DatetimeIndex):
            return {
                'start': data.index.min().strftime('%Y-%m-%d'),
                'end': data.index.max().strftime('%Y-%m-%d'),
                'days': (data.index.max() - data.index.min()).days
            }
        else:
            return {'start': 'N/A', 'end': 'N/A', 'days': 0}
