"""
Test script for ML models (Section 3.2)
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

try:
    from src.models.ml_models import (
        RandomForestModel,
        XGBoostModel,
        LightGBMModel,
        SVMModel,
    )

    print("Successfully imported ML models")
except ImportError as e:
    print(f"Error importing ML models: {e}")
    sys.exit(1)


def create_test_data():
    """Create test data for ML models"""
    # Create date range
    dates = pd.date_range(start="2020-01-01", end="2022-12-31", freq="D")

    # Create random features
    np.random.seed(42)
    n = len(dates)

    # Create features
    X = pd.DataFrame(
        {
            "feature1": np.random.normal(0, 1, n),
            "feature2": np.random.normal(0, 1, n),
            "feature3": np.random.normal(0, 1, n),
            "feature4": np.random.normal(0, 1, n),
            "feature5": np.random.normal(0, 1, n),
        },
        index=dates,
    )

    # Create target (classification)
    y_class = pd.Series(np.random.randint(0, 2, n), index=dates, name="target_class")

    # Create target (regression)
    y_reg = pd.Series(np.random.normal(0, 1, n), index=dates, name="target_reg")

    return X, y_class, y_reg


def test_random_forest():
    """Test RandomForestModel"""
    print("\nTesting RandomForestModel...")

    # Create test data
    X, y_class, y_reg = create_test_data()

    try:
        # Test classification
        print("Testing classification...")
        rf_clf = RandomForestModel(
            name="rf_clf", is_classifier=True, n_estimators=10, max_depth=5
        )
        metrics = rf_clf.train(X, y_class)
        print(f"Classification metrics: {metrics}")

        # Test prediction
        y_pred = rf_clf.predict(X.head(5))
        print(f"Predictions: {y_pred}")

        # Test regression
        print("\nTesting regression...")
        rf_reg = RandomForestModel(
            name="rf_reg", is_classifier=False, n_estimators=10, max_depth=5
        )
        metrics = rf_reg.train(X, y_reg)
        print(f"Regression metrics: {metrics}")

        # Test prediction
        y_pred = rf_reg.predict(X.head(5))
        print(f"Predictions: {y_pred}")

        return rf_clf, rf_reg

    except ImportError as e:
        print(f"RandomForest 測試跳過: {e}")
        return None, None


def test_xgboost():
    """Test XGBoostModel"""
    print("\nTesting XGBoostModel...")

    # Create test data
    X, y_class, y_reg = create_test_data()

    try:
        # Test classification
        print("Testing classification...")
        xgb_clf = XGBoostModel(
            name="xgb_clf", is_classifier=True, n_estimators=10, max_depth=5
        )
        metrics = xgb_clf.train(X, y_class)
        print(f"Classification metrics: {metrics}")

        # Test prediction
        y_pred = xgb_clf.predict(X.head(5))
        print(f"Predictions: {y_pred}")

        # Test regression
        print("\nTesting regression...")
        xgb_reg = XGBoostModel(
            name="xgb_reg", is_classifier=False, n_estimators=10, max_depth=5
        )
        metrics = xgb_reg.train(X, y_reg)
        print(f"Regression metrics: {metrics}")

        # Test prediction
        y_pred = xgb_reg.predict(X.head(5))
        print(f"Predictions: {y_pred}")

        return xgb_clf, xgb_reg

    except ImportError as e:
        print(f"XGBoost 測試跳過: {e}")
        return None, None


def test_lightgbm():
    """Test LightGBMModel"""
    print("\nTesting LightGBMModel...")

    # Create test data
    X, y_class, y_reg = create_test_data()

    try:
        # Test classification
        print("Testing classification...")
        lgb_clf = LightGBMModel(
            name="lgb_clf", is_classifier=True, n_estimators=10, max_depth=5
        )
        metrics = lgb_clf.train(X, y_class)
        print(f"Classification metrics: {metrics}")

        # Test prediction
        y_pred = lgb_clf.predict(X.head(5))
        print(f"Predictions: {y_pred}")

        # Test regression
        print("\nTesting regression...")
        lgb_reg = LightGBMModel(
            name="lgb_reg", is_classifier=False, n_estimators=10, max_depth=5
        )
        metrics = lgb_reg.train(X, y_reg)
        print(f"Regression metrics: {metrics}")

        # Test prediction
        y_pred = lgb_reg.predict(X.head(5))
        print(f"Predictions: {y_pred}")

        return lgb_clf, lgb_reg

    except ImportError as e:
        print(f"LightGBM 測試跳過: {e}")
        return None, None


def test_svm():
    """Test SVMModel"""
    print("\nTesting SVMModel...")

    # Create test data
    X, y_class, y_reg = create_test_data()

    # Use a smaller subset for SVM (faster)
    X_small = X.iloc[:100]
    y_class_small = y_class.iloc[:100]
    y_reg_small = y_reg.iloc[:100]

    try:
        # Test classification
        print("Testing classification...")
        svm_clf = SVMModel(name="svm_clf", is_classifier=True, kernel="linear")
        metrics = svm_clf.train(X_small, y_class_small)
        print(f"Classification metrics: {metrics}")

        # Test prediction
        y_pred = svm_clf.predict(X_small.head(5))
        print(f"Predictions: {y_pred}")

        # Test regression
        print("\nTesting regression...")
        svm_reg = SVMModel(name="svm_reg", is_classifier=False, kernel="linear")
        metrics = svm_reg.train(X_small, y_reg_small)
        print(f"Regression metrics: {metrics}")

        # Test prediction
        y_pred = svm_reg.predict(X_small.head(5))
        print(f"Predictions: {y_pred}")

        return svm_clf, svm_reg

    except ImportError as e:
        print(f"SVM 測試跳過: {e}")
        return None, None


if __name__ == "__main__":
    print("Testing ML Models (Section 3.2)")

    # Test RandomForest
    rf_clf, rf_reg = test_random_forest()

    # Test XGBoost
    xgb_clf, xgb_reg = test_xgboost()

    # Test LightGBM
    lgb_clf, lgb_reg = test_lightgbm()

    # Test SVM
    svm_clf, svm_reg = test_svm()

    print("\nAll tests completed!")

    # 檢查哪些模型成功測試
    successful_models = []
    if rf_clf is not None:
        successful_models.append("RandomForest")
    if xgb_clf is not None:
        successful_models.append("XGBoost")
    if lgb_clf is not None:
        successful_models.append("LightGBM")
    if svm_clf is not None:
        successful_models.append("SVM")

    print(f"成功測試的模型: {', '.join(successful_models)}")
