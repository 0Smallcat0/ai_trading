"""
特徵工程示例腳本

此腳本展示如何使用特徵工程模組進行特徵選擇、降維和特徵存儲。
"""

import logging
import os
import sys
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.feature_store import FeatureStore
from src.core.features import FeatureCalculator, compute_features


def create_sample_data():
    """創建示例資料"""
    logger.info("創建示例資料")

    # 設定隨機種子
    np.random.seed(42)

    # 創建日期範圍
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2022, 12, 31)
    dates = pd.date_range(start=start_date, end=end_date, freq="D")

    # 創建股票代號
    stocks = ["2330", "2317", "2454", "2412", "2308"]

    # 創建多層索引
    index = pd.MultiIndex.from_product([stocks, dates], names=["stock_id", "date"])

    # 創建價格資料
    len(index)

    # 基礎價格（隨機漫步）
    base_prices = {}
    for stock in stocks:
        # 起始價格在 100 到 500 之間
        start_price = np.random.randint(100, 500)
        # 生成隨機漫步
        steps = (
            np.random.normal(0, 1, len(dates)) * start_price * 0.01
        )  # 每日波動約為 1%
        # 累積步驟得到價格序列
        prices = start_price + np.cumsum(steps)
        # 確保價格為正
        prices = np.maximum(prices, 1)
        base_prices[stock] = prices

    # 創建 OHLCV 資料
    price_data = pd.DataFrame(index=index)

    # 填充價格資料
    for i, (stock, date) in enumerate(index):
        stock_idx = dates.get_loc(date)
        base_price = base_prices[stock][stock_idx]

        # 生成當日價格
        daily_volatility = base_price * 0.02  # 日內波動約為 2%
        open_price = base_price * (1 + np.random.normal(0, 0.005))
        high_price = max(open_price, base_price) * (1 + abs(np.random.normal(0, 0.01)))
        low_price = min(open_price, base_price) * (1 - abs(np.random.normal(0, 0.01)))
        close_price = base_price
        volume = int(np.random.lognormal(10, 1))  # 成交量

        # 添加到資料框架
        price_data.loc[(stock, date), "開盤價"] = open_price
        price_data.loc[(stock, date), "最高價"] = high_price
        price_data.loc[(stock, date), "最低價"] = low_price
        price_data.loc[(stock, date), "收盤價"] = close_price
        price_data.loc[(stock, date), "成交股數"] = volume

    # 創建資料字典
    data_dict = {"price": price_data}

    return data_dict


def demonstrate_feature_selection(calculator, features_df):
    """展示特徵選擇"""
    logger.info("展示特徵選擇")

    # 使用 F 檢定選擇特徵
    logger.info("使用 F 檢定選擇特徵")
    selected_df_f, _ = calculator.select_features(
        features_df, method="f_regression", k=10
    )
    logger.info(f"F 檢定選擇的特徵: {selected_df_f.columns.tolist()}")

    # 使用遞迴特徵消除選擇特徵
    logger.info("使用遞迴特徵消除選擇特徵")
    selected_df_rfe, _ = calculator.select_features(features_df, method="rfe", k=10)
    logger.info(f"RFE 選擇的特徵: {selected_df_rfe.columns.tolist()}")

    # 使用 Lasso 選擇特徵
    logger.info("使用 Lasso 選擇特徵")
    selected_df_lasso, _ = calculator.select_features(features_df, method="lasso", k=10)
    logger.info(f"Lasso 選擇的特徵: {selected_df_lasso.columns.tolist()}")

    # 比較不同方法選擇的特徵
    all_selected = (
        set(selected_df_f.columns)
        | set(selected_df_rfe.columns)
        | set(selected_df_lasso.columns)
    )
    common_selected = (
        set(selected_df_f.columns)
        & set(selected_df_rfe.columns)
        & set(selected_df_lasso.columns)
    )

    logger.info(f"所有方法選擇的特徵總數: {len(all_selected)}")
    logger.info(f"所有方法共同選擇的特徵: {common_selected}")

    return selected_df_f


def demonstrate_dimensionality_reduction(calculator, features_df):
    """展示降維"""
    logger.info("展示降維")

    # 使用 PCA 降維
    logger.info("使用 PCA 降維")
    reduced_df, reducer = calculator.reduce_dimensions(
        features_df, n_components=5, method="pca"
    )

    # 顯示解釋方差比例
    explained_variance = reducer.explained_variance_ratio_
    logger.info(f"各主成分解釋方差比例: {explained_variance}")
    logger.info(f"累積解釋方差比例: {np.cumsum(explained_variance)}")

    # 繪製解釋方差比例圖
    plt.figure(figsize=(10, 6))
    plt.bar(
        range(1, len(explained_variance) + 1),
        explained_variance,
        alpha=0.7,
        label="Individual",
    )
    plt.step(
        range(1, len(explained_variance) + 1),
        np.cumsum(explained_variance),
        where="mid",
        label="Cumulative",
    )
    plt.xlabel("Principal Components")
    plt.ylabel("Explained Variance Ratio")
    plt.title("Explained Variance by Principal Components")
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig("pca_explained_variance.png", dpi=300)
    logger.info("已保存 PCA 解釋方差圖到 pca_explained_variance.png")

    return reduced_df


def demonstrate_feature_importance(calculator, features_df):
    """展示特徵重要性"""
    logger.info("展示特徵重要性")

    # 計算特徵重要性
    importance_rf = calculator.calculate_feature_importance(
        features_df, method="random_forest"
    )
    logger.info(f"隨機森林特徵重要性 (前 10): {importance_rf.nlargest(10)}")

    importance_linear = calculator.calculate_feature_importance(
        features_df, method="linear"
    )
    logger.info(f"線性回歸特徵重要性 (前 10): {importance_linear.nlargest(10)}")

    importance_corr = calculator.calculate_feature_importance(
        features_df, method="correlation"
    )
    logger.info(f"相關性特徵重要性 (前 10): {importance_corr.nlargest(10)}")

    # 繪製特徵重要性圖
    fig = calculator.plot_feature_importance(importance_rf, top_n=20)
    plt.savefig("feature_importance_rf.png", dpi=300)
    logger.info("已保存隨機森林特徵重要性圖到 feature_importance_rf.png")

    return importance_rf


def demonstrate_feature_store(features_df):
    """展示特徵存儲"""
    logger.info("展示特徵存儲")

    # 創建特徵存儲
    feature_store = FeatureStore(base_dir="data/features")

    # 保存特徵
    version = feature_store.save_features(
        features_df,
        "demo_features",
        metadata={"description": "示例特徵"},
        tags=["demo", "example"],
    )
    logger.info(f"特徵已保存，版本: {version}")

    # 列出所有特徵
    features = feature_store.list_features()
    logger.info(f"所有特徵: {features}")

    # 列出特徵版本
    versions = feature_store.list_versions("demo_features")
    logger.info(f"特徵 'demo_features' 的所有版本: {versions}")

    # 載入特徵
    loaded_df, metadata = feature_store.load_features("demo_features", version)
    logger.info(f"已載入特徵，形狀: {loaded_df.shape}")
    logger.info(f"特徵元數據: {metadata}")

    # 搜索特徵
    results = feature_store.search_features(tags=["demo"])
    logger.info(f"搜索結果: {[r['name'] for r in results]}")

    return version


def main():
    """主函數"""
    logger.info("開始特徵工程示例")

    # 創建示例資料
    data_dict = create_sample_data()

    # 創建特徵計算器
    calculator = FeatureCalculator(data_dict)

    # 計算技術指標
    logger.info("計算技術指標")
    tech_features = calculator.calculate_technical_indicators()
    logger.info(f"技術指標形狀: {tech_features.shape}")

    # 計算自定義特徵
    logger.info("計算自定義特徵")
    custom_features = calculator.calculate_custom_features()
    logger.info(f"自定義特徵形狀: {custom_features.shape}")

    # 合併特徵
    logger.info("合併特徵")
    features = calculator.combine_features()
    logger.info(f"合併後特徵形狀: {features.shape}")

    # 清理資料
    logger.info("清理資料")
    features, _ = calculator.data_cleaner.clean_data(features)
    logger.info(f"清理後特徵形狀: {features.shape}")

    # 標準化特徵
    logger.info("標準化特徵")
    _, features = calculator.normalize_features(features)
    logger.info(f"標準化後特徵形狀: {features.shape}")

    # 展示特徵選擇
    demonstrate_feature_selection(calculator, features)

    # 展示降維
    demonstrate_dimensionality_reduction(calculator, features)

    # 展示特徵重要性
    demonstrate_feature_importance(calculator, features)

    # 展示特徵存儲
    demonstrate_feature_store(features)

    # 使用 compute_features 函數
    logger.info("使用 compute_features 函數")
    computed_features = compute_features(
        normalize=True,
        remove_extremes=True,
        clean_data=True,
        feature_selection=True,
        feature_selection_method="f_regression",
        feature_selection_k=10,
        dimensionality_reduction=True,
        dimensionality_reduction_method="pca",
        n_components=5,
        save_to_feature_store=True,
        feature_name="computed_features",
        feature_tags=["computed", "example"],
    )
    logger.info(f"compute_features 結果形狀: {computed_features.shape}")

    logger.info("特徵工程示例完成")


if __name__ == "__main__":
    main()
