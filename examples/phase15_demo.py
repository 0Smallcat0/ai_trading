"""Phase 1.5 資料清洗與預處理模組示例

此示例展示如何使用新實作的功能：
1. Dask/Ray 框架整合預留接口
2. 記憶體分塊處理機制

以及已完成的功能：
3. 模組化技術指標計算
4. 滾動窗口特徵生成器
5. 離群值檢測與處理
6. 缺失值插補策略
"""

import os
import sys
import pandas as pd
import numpy as np

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.distributed_computing import (
    get_compute_manager,
    initialize_distributed_computing,
    shutdown_distributed_computing
)
from src.core.memory_management import (
    MemoryMonitor,
    ChunkProcessor,
    MemoryEfficientProcessor
)
from src.core.data_cleaning import (
    MissingValueHandler,
    OutlierHandler,
    DataCleaningPipeline
)
from src.core.features import RollingWindowFeatureGenerator
from src.core.indicators import TechnicalIndicators


def create_sample_data(n_rows=10000, n_cols=10):
    """創建示例數據"""
    print(f"創建示例數據: {n_rows} 行 x {n_cols} 列")

    # 創建基礎價格數據
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=n_rows, freq='D')

    # 模擬股價數據
    initial_price = 100
    returns = np.random.normal(0.001, 0.02, n_rows)  # 日收益率
    prices = [initial_price]

    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))

    # 創建 OHLCV 數據
    close_prices = np.array(prices)
    open_prices = close_prices * (1 + np.random.normal(0, 0.005, n_rows))
    high_prices = np.maximum(open_prices,
        close_prices) * (1 + np.random.uniform(0,
        0.01,
        n_rows))
    low_prices = np.minimum(open_prices,
        close_prices) * (1 - np.random.uniform(0,
        0.01,
        n_rows))
    volumes = np.random.randint(100000, 1000000, n_rows)

    data = pd.DataFrame({
        'date': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    })

    # 添加額外的特徵列
    for i in range(n_cols - 6):
        data[f'feature_{i}'] = np.random.randn(n_rows)

    # 人為添加一些缺失值和異常值
    missing_mask = np.random.random(data.shape) < 0.05  # 5% 缺失值
    data = data.mask(missing_mask)

    # 添加異常值
    outlier_indices = np.random.choice(n_rows, size=int(n_rows * 0.02), replace=False)
    for idx in outlier_indices:
        col = np.random.choice(data.select_dtypes(include=[np.number]).columns)
        data.loc[idx, col] = data[col].mean() + 5 * data[col].std()

    return data


def demo_distributed_computing():
    """演示分散式計算功能"""
    print("\n=== 分散式計算演示 ===")

    # 初始化分散式計算環境
    success = initialize_distributed_computing()
    print(f"分散式計算初始化: {'成功' if success else '失敗'}")

    # 獲取計算管理器
    manager = get_compute_manager()
    engine_info = manager.get_engine_info()
    print(f"當前使用的計算引擎: {engine_info['engine']}")
    print(f"引擎可用性: {engine_info['available']}")

    # 創建測試數據
    test_data = pd.DataFrame({
        'A': np.random.randn(1000),
        'B': np.random.randn(1000),
        'C': np.random.randn(1000)
    })

    # 測試分區映射
    def calculate_stats(df):
        return pd.Series({
            'mean': df.mean().mean(),
            'std': df.std().mean(),
            'count': len(df)
        })

    try:
        result = manager.map_partitions(calculate_stats, test_data)
        print(f"分區映射結果: {result.to_dict()}")
    except Exception as e:
        print(f"分區映射失敗: {e}")

    # 測試並行應用
    def square_function(x):
        return x ** 2

    try:
        data_list = [1, 2, 3, 4, 5]
        results = manager.parallel_apply(square_function, data_list)
        print(f"並行應用結果: {results}")
    except Exception as e:
        print(f"並行應用失敗: {e}")

    # 關閉分散式計算環境
    shutdown_distributed_computing()
    print("分散式計算環境已關閉")


def demo_memory_management():
    """演示記憶體管理功能"""
    print("\n=== 記憶體管理演示 ===")

    # 記憶體監控
    monitor = MemoryMonitor()
    initial_memory = monitor.get_memory_usage()
    print(f"初始記憶體使用: {initial_memory['process_rss']:.2f} MB")

    # 創建大數據集
    large_data = create_sample_data(n_rows=50000, n_cols=20)
    print(f"創建大數據集: {large_data.shape}")

    current_memory = monitor.get_memory_usage()
    memory_growth = monitor.get_memory_growth()
    print(f"當前記憶體使用: {current_memory['process_rss']:.2f} MB")
    print(f"記憶體增長: {memory_growth:.2f} MB")

    # 分塊處理
    chunk_processor = ChunkProcessor(max_memory_mb=100)

    def process_chunk(df):
        """處理單個數據塊"""
        return {
            'mean': df.select_dtypes(include=[np.number]).mean().mean(),
            'rows': len(df)
        }

    print("\n開始分塊處理...")
    results = chunk_processor.process_dataframe_chunks(
        large_data,
        process_chunk,
        chunk_size=5000,
        progress_callback=lambda current, total: print(f"進度: {current}/{total}")
    )

    print(f"分塊處理完成，共 {len(results)} 個結果")
    total_rows = sum(r['rows'] for r in results)
    avg_mean = np.mean([r['mean'] for r in results])
    print(f"總處理行數: {total_rows}")
    print(f"平均值: {avg_mean:.4f}")

    # 記憶體高效處理
    efficient_processor = MemoryEfficientProcessor(max_memory_mb=50)

    def calculate_correlation(df):
        """計算相關性矩陣"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        return df[numeric_cols].corr()

    print("\n使用記憶體高效處理器...")
    try:
        correlation_result = efficient_processor.process_with_memory_management(
            large_data, calculate_correlation
        )
        print(f"相關性矩陣計算完成，形狀: {correlation_result.shape}")
    except Exception as e:
        print(f"記憶體高效處理失敗: {e}")

    final_memory = monitor.get_memory_usage()
    final_growth = monitor.get_memory_growth()
    print(f"最終記憶體使用: {final_memory['process_rss']:.2f} MB")
    print(f"總記憶體增長: {final_growth:.2f} MB")


def demo_data_cleaning():
    """演示資料清洗功能"""
    print("\n=== 資料清洗演示 ===")

    # 創建測試數據
    test_data = create_sample_data(n_rows=5000, n_cols=8)
    print(f"原始數據形狀: {test_data.shape}")
    print(f"缺失值數量: {test_data.isnull().sum().sum()}")

    # 缺失值處理
    missing_handler = MissingValueHandler(method="interpolate")
    cleaned_data = missing_handler.fit_transform(test_data)
    print(f"缺失值處理後: {cleaned_data.isnull().sum().sum()}")

    # 異常值處理
    outlier_handler = OutlierHandler(detection_method="z-score", treatment_method="clip")
    outliers = outlier_handler.detect_outliers(cleaned_data)
    print(f"檢測到的異常值數量: {outliers.sum().sum()}")

    treated_data = outlier_handler.treat_outliers(cleaned_data, outliers)
    print(f"異常值處理完成")

    # 完整清洗流程
    pipeline = DataCleaningPipeline()
    final_data, report = pipeline.clean(test_data)

    print(f"\n清洗報告:")
    print(f"原始形狀: {report['original_shape']}")
    print(f"最終形狀: {report['final_shape']}")
    print(f"處理步驟: {report['processing_steps']}")


def demo_feature_engineering():
    """演示特徵工程功能"""
    print("\n=== 特徵工程演示 ===")

    # 創建價格數據
    price_data = create_sample_data(n_rows=1000,
        n_cols=6)[['open',
        'high',
        'low',
        'close',
        'volume']]
    print(f"價格數據形狀: {price_data.shape}")

    # 技術指標計算
    indicators = TechnicalIndicators(price_data)

    # 計算各種技術指標
    sma_20 = indicators.calculate_sma(period=20)
    ema_12 = indicators.calculate_ema(period=12)
    macd, signal, hist = indicators.calculate_macd()
    rsi = indicators.calculate_rsi(period=14)
    bb_upper, bb_middle, bb_lower = indicators.calculate_bollinger_bands()

    print(f"SMA(20) 最後5個值: {sma_20.tail().values}")
    print(f"RSI 最後5個值: {rsi.tail().values}")
    print(f"MACD 最後5個值: {macd.tail().values}")

    # 滾動窗口特徵生成
    rolling_generator = RollingWindowFeatureGenerator(
        window_sizes=[5, 10, 20],
        functions={
            'mean': lambda x: x.mean(),
            'std': lambda x: x.std(),
            'max': lambda x: x.max(),
            'min': lambda x: x.min()
        }
    )

    rolling_features = rolling_generator.generate(price_data[['close', 'volume']])
    print(f"滾動窗口特徵形狀: {rolling_features.shape}")
    print(f"特徵列名: {list(rolling_features.columns[:10])}")  # 顯示前10個特徵名


def main():
    """主函數"""
    print("Phase 1.5 資料清洗與預處理模組功能演示")
    print("=" * 50)

    try:
        # 演示各個功能模組
        demo_distributed_computing()
        demo_memory_management()
        demo_data_cleaning()
        demo_feature_engineering()

        print("\n" + "=" * 50)
        print("所有演示完成！")

    except Exception as e:
        print(f"演示過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
