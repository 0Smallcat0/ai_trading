"""
資料清理示例腳本

此腳本展示如何使用資料清理模組來處理股票資料，包括：
- 處理缺失值
- 處理異常值
- 標準化價格
- 使用完整的清理管道
"""

import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# 設定日誌
import logging

# 導入資料清理模組
from src.core.data_cleaning import (
    DataCleaningPipeline,
    MissingValueHandler,
    OutlierHandler,
    PriceStandardizer,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_sample_data(with_missing=True, with_outliers=True, with_adj_close=True):
    """
    創建示例資料

    Args:
        with_missing (bool): 是否包含缺失值
        with_outliers (bool): 是否包含異常值
        with_adj_close (bool): 是否包含調整後收盤價

    Returns:
        pd.DataFrame: 示例資料
    """
    # 創建日期範圍
    dates = pd.date_range(start="2023-01-01", end="2023-01-31", freq="D")

    # 創建基本價格資料
    np.random.seed(42)  # 設定隨機種子，確保結果可重現

    # 生成隨機價格
    close = 100 + np.cumsum(np.random.normal(0, 1, len(dates)))
    high = close + np.random.uniform(0, 2, len(dates))
    low = close - np.random.uniform(0, 2, len(dates))
    open_price = low + np.random.uniform(0, (high - low), len(dates))
    volume = np.random.uniform(1000, 5000, len(dates))

    # 創建 DataFrame
    df = pd.DataFrame(
        {
            "date": dates,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )

    # 設定日期為索引
    df.set_index("date", inplace=True)

    # 添加調整後收盤價
    if with_adj_close:
        # 假設有一個 0.9 的調整因子
        df["adj_close"] = df["close"] * 0.9

    # 添加缺失值
    if with_missing:
        # 隨機將 10% 的資料設為 NaN
        mask = np.random.random(df.shape) < 0.1
        df.mask(mask, inplace=True)

    # 添加異常值
    if with_outliers:
        # 逐列添加異常值
        for col in df.columns:
            # 隨機選擇 5% 的行添加異常值
            mask = np.random.random(len(df)) < 0.05
            # 計算異常值的大小
            factor = np.random.uniform(3, 5)
            # 添加異常值
            df.loc[mask, col] = df.loc[mask, col] + factor * df[col].std()

    return df


def demonstrate_missing_value_handling():
    """
    展示缺失值處理
    """
    logger.info("展示缺失值處理")

    # 創建包含缺失值的示例資料
    df = create_sample_data(with_missing=True, with_outliers=False)

    # 顯示原始資料的缺失值情況
    logger.info(f"原始資料缺失值數量:\n{df.isna().sum()}")

    # 使用不同的填補方法
    methods = ["interpolate", "mean", "median", "ffill", "bfill", "knn"]
    results = {}

    for method in methods:
        handler = MissingValueHandler(method=method)
        filled_df = handler.fit_transform(df)
        results[method] = filled_df
        logger.info(f"{method} 方法填補後的缺失值數量: {filled_df.isna().sum().sum()}")

    # 繪製不同填補方法的結果
    plt.figure(figsize=(12, 8))

    for i, method in enumerate(methods):
        plt.subplot(len(methods), 1, i + 1)
        plt.plot(
            df.index, df["close"], "o-", label="Original (with missing)", alpha=0.5
        )
        plt.plot(
            results[method].index,
            results[method]["close"],
            "o-",
            label=f"Filled ({method})",
        )
        plt.title(f"Missing Value Handling - {method}")
        plt.legend()

    plt.tight_layout()
    plt.savefig("missing_value_handling.png")
    logger.info("已保存缺失值處理結果圖表到 missing_value_handling.png")


def demonstrate_outlier_handling():
    """
    展示異常值處理
    """
    logger.info("展示異常值處理")

    # 創建包含異常值的示例資料
    df = create_sample_data(with_missing=False, with_outliers=True)

    # 使用不同的異常值檢測和處理方法
    treatment_methods = ["clip", "remove", "mean", "median", "winsorize"]

    # 選擇一個檢測方法和多個處理方法進行展示
    detection_method = "z-score"
    results = {}

    # 檢測異常值
    outlier_handler = OutlierHandler(detection_method=detection_method)
    outliers = outlier_handler.detect_outliers(df)

    # 計算每列的異常值數量
    outlier_counts = outliers.sum()
    logger.info(f"使用 {detection_method} 方法檢測到的異常值數量:\n{outlier_counts}")

    # 使用不同的處理方法
    for treatment_method in treatment_methods:
        handler = OutlierHandler(
            detection_method=detection_method, treatment_method=treatment_method
        )
        treated_df = handler.treat_outliers(df, outliers)
        results[treatment_method] = treated_df

    # 繪製不同處理方法的結果
    plt.figure(figsize=(12, 10))

    for i, method in enumerate(treatment_methods):
        plt.subplot(len(treatment_methods), 1, i + 1)
        plt.plot(
            df.index, df["close"], "o-", label="Original (with outliers)", alpha=0.5
        )
        plt.plot(
            results[method].index,
            results[method]["close"],
            "o-",
            label=f"Treated ({method})",
        )
        plt.title(f"Outlier Handling - {method}")
        plt.legend()

    plt.tight_layout()
    plt.savefig("outlier_handling.png")
    logger.info("已保存異常值處理結果圖表到 outlier_handling.png")


def demonstrate_price_standardization():
    """
    展示價格標準化
    """
    logger.info("展示價格標準化")

    # 創建包含調整後收盤價的示例資料
    df = create_sample_data(
        with_missing=False, with_outliers=False, with_adj_close=True
    )

    # 顯示原始價格
    logger.info(f"原始價格 (前 5 行):\n{df.head()}")

    # 使用調整後收盤價邏輯標準化價格
    standardizer = PriceStandardizer(adjust_method="adj_close")
    standardized_df = standardizer.standardize_prices(df)

    # 顯示標準化後的價格
    logger.info(f"標準化後的價格 (前 5 行):\n{standardized_df.head()}")

    # 繪製原始價格和標準化後的價格
    plt.figure(figsize=(12, 6))

    plt.subplot(1, 2, 1)
    plt.plot(df.index, df["close"], "o-", label="Original Close")
    plt.plot(df.index, df["adj_close"], "o-", label="Adjusted Close")
    plt.title("Original Prices")
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(
        standardized_df.index,
        standardized_df["close"],
        "o-",
        label="Standardized Close",
    )
    plt.title("Standardized Prices")
    plt.legend()

    plt.tight_layout()
    plt.savefig("price_standardization.png")
    logger.info("已保存價格標準化結果圖表到 price_standardization.png")


def demonstrate_full_pipeline():
    """
    展示完整的資料清理管道
    """
    logger.info("展示完整的資料清理管道")

    # 創建包含缺失值、異常值和調整後收盤價的示例資料
    df = create_sample_data(with_missing=True, with_outliers=True, with_adj_close=True)

    # 顯示原始資料的統計信息
    logger.info(f"原始資料統計信息:\n{df.describe()}")
    logger.info(f"原始資料缺失值數量:\n{df.isna().sum()}")

    # 創建資料清理管道
    pipeline = DataCleaningPipeline(
        missing_value_handler=MissingValueHandler(method="interpolate"),
        outlier_handler=OutlierHandler(
            detection_method="z-score", treatment_method="clip"
        ),
        price_standardizer=PriceStandardizer(adjust_method="adj_close"),
        process_order=["missing", "outlier", "price"],
        report=True,
    )

    # 執行清理
    cleaned_df, report = pipeline.clean(df, symbol="EXAMPLE")

    # 顯示清理報告
    logger.info(f"清理報告:\n{report}")

    # 顯示清理後的資料統計信息
    logger.info(f"清理後的資料統計信息:\n{cleaned_df.describe()}")

    # 繪製原始資料和清理後的資料
    plt.figure(figsize=(12, 8))

    plt.subplot(2, 1, 1)
    plt.plot(df.index, df["close"], "o-", label="Original Close")
    if "adj_close" in df.columns:
        plt.plot(df.index, df["adj_close"], "o-", label="Original Adjusted Close")
    plt.title("Original Data")
    plt.legend()

    plt.subplot(2, 1, 2)
    plt.plot(cleaned_df.index, cleaned_df["close"], "o-", label="Cleaned Close")
    plt.title("Cleaned Data")
    plt.legend()

    plt.tight_layout()
    plt.savefig("full_pipeline.png")
    logger.info("已保存完整清理管道結果圖表到 full_pipeline.png")


def main():
    """
    主函數
    """
    logger.info("開始資料清理示例")

    # 展示缺失值處理
    demonstrate_missing_value_handling()

    # 展示異常值處理
    demonstrate_outlier_handling()

    # 展示價格標準化
    demonstrate_price_standardization()

    # 展示完整的資料清理管道
    demonstrate_full_pipeline()

    logger.info("資料清理示例完成")


if __name__ == "__main__":
    main()
