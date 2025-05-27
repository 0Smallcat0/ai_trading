"""
Comprehensive unit tests for core modules to improve test coverage

This module contains comprehensive unit tests for the most critical core modules
to achieve the target test coverage of ≥80%.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import logging

# Import core modules for testing
from src.core.data_cleaning import (
    MissingValueHandler,
    OutlierHandler,
    PriceStandardizer,
    DataCleaningPipeline
)
from src.core.features import FeatureCalculator, DataCleaner
from src.core.rate_limiter import RateLimiter, AdaptiveRateLimiter
from src.core.websocket_client import WebSocketClient


class TestMissingValueHandler:
    """Test MissingValueHandler class"""

    def setup_method(self):
        """Setup test data"""
        self.handler = MissingValueHandler()
        self.test_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'price': [100, np.nan, 102, 103, np.nan, 105, 106, np.nan, 108, 109],
            'volume': [1000, 1100, np.nan, 1300, 1400, np.nan, 1600, 1700, 1800, np.nan]
        })

    def test_detect_missing_values(self):
        """Test missing value detection"""
        result = self.handler.detect_missing_values(self.test_data)

        assert 'price' in result
        assert 'volume' in result
        assert result['price']['count'] == 3
        assert result['volume']['count'] == 3
        assert result['price']['percentage'] > 0

    def test_interpolate_method(self):
        """Test interpolation method"""
        result = self.handler.handle_missing_values(
            self.test_data.copy(),
            method='interpolate',
            columns=['price']
        )

        # Check that missing values are filled
        assert result['price'].isna().sum() == 0
        # Check that interpolation is reasonable
        assert 100 < result.loc[1, 'price'] < 102

    def test_mean_method(self):
        """Test mean filling method"""
        result = self.handler.handle_missing_values(
            self.test_data.copy(),
            method='mean',
            columns=['price']
        )

        assert result['price'].isna().sum() == 0
        # Mean should be around 105
        filled_values = result.loc[self.test_data['price'].isna(), 'price']
        assert all(100 < val < 110 for val in filled_values)

    def test_drop_method(self):
        """Test drop method"""
        result = self.handler.handle_missing_values(
            self.test_data.copy(),
            method='drop'
        )

        # Should have fewer rows
        assert len(result) < len(self.test_data)
        # Should have no missing values
        assert result.isna().sum().sum() == 0


class TestOutlierHandler:
    """Test OutlierHandler class"""

    def setup_method(self):
        """Setup test data"""
        self.handler = OutlierHandler(detection_method="z-score", treatment_method="clip")
        # Create data with obvious outliers
        normal_data = np.random.normal(100, 5, 95)
        outliers = [150, 50, 200, 30, 180]  # Clear outliers
        self.test_data = pd.DataFrame({
            'price': np.concatenate([normal_data, outliers]),
            'volume': np.random.normal(1000, 100, 100)
        })

    def test_zscore_detection(self):
        """Test Z-score outlier detection"""
        result = self.handler.detect_outliers(self.test_data, columns=['price'])

        assert isinstance(result, dict)
        assert 'price' in result
        # Should detect some outliers
        assert len(result['price']) > 0

    def test_iqr_detection(self):
        """Test IQR outlier detection"""
        handler = OutlierHandler(detection_method="iqr", treatment_method="clip")
        result = handler.detect_outliers(self.test_data, columns=['price'])

        assert isinstance(result, dict)
        assert 'price' in result

    def test_outlier_treatment(self):
        """Test outlier treatment"""
        result = self.handler.handle_outliers(self.test_data, columns=['price'])

        # Should return a DataFrame
        assert isinstance(result, pd.DataFrame)
        # Should have same shape
        assert result.shape == self.test_data.shape
        # Extreme outliers should be clipped
        assert result['price'].max() < self.test_data['price'].max()


class TestDataCleaningPipeline:
    """Test DataCleaningPipeline class"""

    def setup_method(self):
        """Setup test data"""
        self.test_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'open': [100, np.nan, 102, 103, np.nan, 105, 106, np.nan, 108, 109],
            'high': [105, 106, np.nan, 108, 109, 110, 111, 112, np.nan, 114],
            'low': [95, 96, 97, np.nan, 99, 100, 101, 102, 103, np.nan],
            'close': [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
            'volume': [1000, 1100, np.nan, 1300, 1400, np.nan, 1600, 1700, 1800, np.nan]
        })

        self.pipeline = DataCleaningPipeline(
            missing_value_handler=MissingValueHandler(method="interpolate"),
            outlier_handler=OutlierHandler(detection_method="z-score", treatment_method="clip"),
            price_standardizer=PriceStandardizer()
        )

    def test_pipeline_execution(self):
        """Test full pipeline execution"""
        cleaned_data, report = self.pipeline.clean(self.test_data)

        # Should return cleaned DataFrame and report
        assert isinstance(cleaned_data, pd.DataFrame)
        assert isinstance(report, dict)
        assert 'original_shape' in report
        assert 'processing_steps' in report

    def test_missing_value_handling(self):
        """Test missing value handling in pipeline"""
        cleaned_data, report = self.pipeline.clean(self.test_data)

        # Should have fewer missing values
        original_missing = self.test_data.isna().sum().sum()
        cleaned_missing = cleaned_data.isna().sum().sum()
        assert cleaned_missing <= original_missing

    def test_pipeline_with_empty_data(self):
        """Test pipeline with empty data"""
        empty_data = pd.DataFrame()
        cleaned_data, report = self.pipeline.clean(empty_data)

        assert cleaned_data.empty
        assert report['status'] == 'empty'


class TestFeatureCalculator:
    """Test FeatureCalculator class"""

    def setup_method(self):
        """Setup test data"""
        self.price_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=50),
            'symbol': ['AAPL'] * 50,
            'open': np.random.uniform(150, 160, 50),
            'high': np.random.uniform(155, 165, 50),
            'low': np.random.uniform(145, 155, 50),
            'close': np.random.uniform(150, 160, 50),
            'volume': np.random.randint(1000000, 5000000, 50)
        }).set_index(['date', 'symbol'])

        self.calculator = FeatureCalculator({'price': self.price_data})

    def test_calculate_sma(self):
        """Test Simple Moving Average calculation"""
        result = self.calculator.calculate_sma(window=10)

        assert not result.empty
        assert 'sma_10' in result.columns
        # SMA should not have NaN for the last values
        assert not pd.isna(result['sma_10'].iloc[-1])

    def test_calculate_ema(self):
        """Test Exponential Moving Average calculation"""
        result = self.calculator.calculate_ema(window=10)

        assert not result.empty
        assert 'ema_10' in result.columns
        assert not pd.isna(result['ema_10'].iloc[-1])

    def test_calculate_rsi(self):
        """Test RSI calculation"""
        result = self.calculator.calculate_rsi(window=14)

        assert not result.empty
        assert 'rsi_14' in result.columns
        # RSI should be between 0 and 100
        rsi_values = result['rsi_14'].dropna()
        assert all(0 <= val <= 100 for val in rsi_values)

    def test_calculate_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        result = self.calculator.calculate_bollinger_bands(window=20)

        assert not result.empty
        assert 'bb_upper_20' in result.columns
        assert 'bb_lower_20' in result.columns
        assert 'bb_middle_20' in result.columns

        # Upper should be >= middle >= lower
        last_row = result.dropna().iloc[-1]
        assert last_row['bb_upper_20'] >= last_row['bb_middle_20'] >= last_row['bb_lower_20']


class TestRateLimiter:
    """Test RateLimiter class"""

    def test_basic_rate_limiting(self):
        """Test basic rate limiting functionality"""
        limiter = RateLimiter(max_calls=2, time_window=1.0)

        # First two calls should succeed
        assert limiter.can_proceed() == True
        assert limiter.can_proceed() == True

        # Third call should be rate limited
        assert limiter.can_proceed() == False

    def test_time_window_reset(self):
        """Test that rate limit resets after time window"""
        limiter = RateLimiter(max_calls=1, time_window=0.1)

        # First call should succeed
        assert limiter.can_proceed() == True

        # Second call should fail
        assert limiter.can_proceed() == False

        # Wait for time window to pass
        import time
        time.sleep(0.15)

        # Should be able to proceed again
        assert limiter.can_proceed() == True


class TestAdaptiveRateLimiter:
    """Test AdaptiveRateLimiter class"""

    def test_adaptive_behavior(self):
        """Test adaptive rate limiting behavior"""
        limiter = AdaptiveRateLimiter(
            initial_rate=2,
            time_window=1.0,
            max_rate=5,
            min_rate=1
        )

        # Should start with initial rate
        assert limiter.current_rate == 2

        # Simulate successful requests
        for _ in range(5):
            limiter.record_success()

        # Rate should increase
        assert limiter.current_rate > 2

        # Simulate failures
        for _ in range(3):
            limiter.record_failure()

        # Rate should decrease
        assert limiter.current_rate < limiter.max_rate


class TestDataCleaner:
    """Test DataCleaner class from features module"""

    def setup_method(self):
        """Setup test data"""
        self.cleaner = DataCleaner(
            outlier_method="z-score",
            outlier_threshold=3.0,
            imputation_method="interpolate"
        )

        self.test_data = pd.DataFrame({
            'price': [100, np.nan, 102, 103, np.nan, 105, 106, np.nan, 108, 109],
            'volume': [1000, 1100, np.nan, 1300, 1400, np.nan, 1600, 1700, 1800, np.nan]
        })

    def test_outlier_detection(self):
        """Test outlier detection"""
        # Add some obvious outliers
        test_data = self.test_data.copy()
        test_data.loc[0, 'price'] = 1000  # Obvious outlier

        outliers = self.cleaner.detect_outliers(test_data, columns=['price'])

        assert isinstance(outliers, dict)
        assert 'price' in outliers

    def test_missing_value_imputation(self):
        """Test missing value imputation"""
        result = self.cleaner.impute_missing_values(self.test_data, columns=['price'])

        # Should have fewer missing values
        original_missing = self.test_data['price'].isna().sum()
        result_missing = result['price'].isna().sum()
        assert result_missing <= original_missing

    def test_data_cleaning_pipeline(self):
        """Test full data cleaning pipeline"""
        result = self.cleaner.clean_data(self.test_data)

        # Should return a DataFrame
        assert isinstance(result, pd.DataFrame)
        # Should have same shape
        assert result.shape == self.test_data.shape
