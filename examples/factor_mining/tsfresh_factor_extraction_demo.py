#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tsfresh 自動因子挖掘示例

此示例展示如何使用 tsfresh 從股票價格數據中自動提取大量特徵因子。
基於 ai_quant_trade-0.0.1 中的因子挖掘功能，提供完整的特徵提取和選擇流程。

功能特色：
- 自動從時間序列提取 5000+ 特徵
- 統計檢驗特徵選擇
- 並行處理和性能優化
- 因子評估和分析

使用前準備：
1. 安裝依賴：pip install tsfresh pandas numpy scikit-learn
2. 準備股票價格數據（OHLCV格式）
3. 配置並行處理參數

Example:
    python examples/factor_mining/tsfresh_factor_extraction_demo.py
"""

import os
import sys
import logging
import warnings
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.strategies.adapters.factor_mining_adapter import FactorMiningAdapter, FactorMiningConfig

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 抑制警告
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)


def generate_sample_data(n_symbols: int = 5, n_days: int = 252) -> pd.DataFrame:
    """生成示例股票數據
    
    Args:
        n_symbols: 股票數量
        n_days: 交易日數量
        
    Returns:
        pd.DataFrame: 示例股票數據
    """
    logger.info(f"生成示例數據: {n_symbols} 隻股票, {n_days} 個交易日")
    
    # 生成日期序列
    end_date = datetime.now()
    start_date = end_date - timedelta(days=int(n_days * 1.4))  # 考慮週末
    date_range = pd.bdate_range(start=start_date, end=end_date)[:n_days]
    
    data_list = []
    
    for i in range(n_symbols):
        symbol = f"STOCK_{i+1:03d}"
        
        # 生成隨機價格數據
        np.random.seed(42 + i)  # 確保可重現
        
        # 初始價格
        initial_price = 100 + np.random.normal(0, 20)
        
        # 生成收益率序列
        returns = np.random.normal(0.0005, 0.02, n_days)  # 日收益率
        
        # 計算價格序列
        prices = [initial_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # 生成 OHLCV 數據
        for j, (date, close) in enumerate(zip(date_range, prices)):
            # 生成開高低價
            volatility = 0.01 + np.random.exponential(0.005)
            
            open_price = close * (1 + np.random.normal(0, volatility/2))
            high_price = max(open_price, close) * (1 + np.random.exponential(volatility/2))
            low_price = min(open_price, close) * (1 - np.random.exponential(volatility/2))
            
            # 生成成交量
            base_volume = 1000000
            volume = base_volume * (1 + np.random.exponential(0.5))
            
            data_list.append({
                'symbol': symbol,
                'date': date,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close,
                'volume': volume
            })
    
    df = pd.DataFrame(data_list)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    logger.info(f"示例數據生成完成: {len(df)} 行數據")
    return df


def demo_basic_factor_extraction():
    """示例：基礎因子提取"""
    logger.info("=== 基礎因子提取示例 ===")
    
    try:
        # 生成示例數據
        data = generate_sample_data(n_symbols=3, n_days=100)
        
        # 配置因子挖掘
        config = FactorMiningConfig(
            method='tsfresh',
            n_jobs=2,  # 使用較少進程以避免內存問題
            cache_enabled=True,
            tsfresh_config={
                'minimal_features': True,  # 使用最小特徵集合
                'feature_selection': True,
                'impute_function': 'median'
            }
        )
        
        # 創建適配器
        adapter = FactorMiningAdapter(config)
        
        # 提取因子
        logger.info("開始提取因子...")
        factors = adapter.extract_factors(data, method='tsfresh')
        
        logger.info(f"因子提取完成: {factors.shape}")
        
        # 顯示結果
        print("\n" + "="*50)
        print("因子提取結果:")
        print("="*50)
        print(f"因子數量: {factors.shape[1]}")
        print(f"時間點數: {factors.shape[0]}")
        print(f"因子名稱示例: {list(factors.columns[:10])}")
        
        # 顯示統計信息
        print(f"\n因子統計信息:")
        print(f"平均值範圍: [{factors.mean().min():.4f}, {factors.mean().max():.4f}]")
        print(f"標準差範圍: [{factors.std().min():.4f}, {factors.std().max():.4f}]")
        print(f"缺失值比例: {factors.isnull().sum().sum() / factors.size:.2%}")
        
        return factors
        
    except Exception as e:
        logger.error(f"基礎因子提取失敗: {e}")
        return None


def demo_factor_selection():
    """示例：因子選擇"""
    logger.info("=== 因子選擇示例 ===")
    
    try:
        # 生成示例數據
        data = generate_sample_data(n_symbols=3, n_days=100)
        
        # 配置因子挖掘
        config = FactorMiningConfig(
            method='tsfresh',
            n_jobs=2,
            tsfresh_config={'minimal_features': True}
        )
        
        adapter = FactorMiningAdapter(config)
        
        # 提取因子
        factors = adapter.extract_factors(data, method='tsfresh')
        
        # 生成目標變量（未來收益率）
        target_returns = generate_target_returns(data)
        
        # 對齊數據
        aligned_factors, aligned_returns = align_data(factors, target_returns)
        
        # 因子選擇
        logger.info("開始因子選擇...")
        selected_factors = adapter.select_factors(
            aligned_factors, 
            aligned_returns,
            method='ic',  # 使用信息係數方法
            top_k=20
        )
        
        logger.info(f"因子選擇完成: {selected_factors.shape}")
        
        # 顯示結果
        print("\n" + "="*50)
        print("因子選擇結果:")
        print("="*50)
        print(f"原始因子數: {factors.shape[1]}")
        print(f"選擇因子數: {selected_factors.shape[1]}")
        print(f"選擇比例: {selected_factors.shape[1]/factors.shape[1]:.1%}")
        
        # 顯示選中的因子
        print(f"\n選中的因子:")
        for i, col in enumerate(selected_factors.columns[:10], 1):
            print(f"  {i}. {col}")
        if len(selected_factors.columns) > 10:
            print(f"  ... 還有 {len(selected_factors.columns)-10} 個因子")
            
        return selected_factors
        
    except Exception as e:
        logger.error(f"因子選擇失敗: {e}")
        return None


def demo_factor_evaluation():
    """示例：因子評估"""
    logger.info("=== 因子評估示例 ===")
    
    try:
        # 生成示例數據
        data = generate_sample_data(n_symbols=3, n_days=100)
        
        # 配置和提取因子
        config = FactorMiningConfig(
            method='tsfresh',
            n_jobs=2,
            tsfresh_config={'minimal_features': True}
        )
        
        adapter = FactorMiningAdapter(config)
        factors = adapter.extract_factors(data, method='tsfresh')
        
        # 生成目標變量
        target_returns = generate_target_returns(data)
        aligned_factors, aligned_returns = align_data(factors, target_returns)
        
        # 因子評估
        logger.info("開始因子評估...")
        evaluation_results = adapter.evaluate_factors(
            aligned_factors,
            aligned_returns,
            methods=['ic', 'rank_ic', 'ir']
        )
        
        # 顯示結果
        print("\n" + "="*50)
        print("因子評估結果:")
        print("="*50)
        
        # 顯示前10個因子的評估結果
        top_factors = evaluation_results.head(10)
        print(f"{'因子名稱':<30} {'IC':<8} {'Rank IC':<10} {'IR':<8}")
        print("-" * 60)
        
        for _, row in top_factors.iterrows():
            print(f"{row.name[:28]:<30} {row.get('ic', 0):<8.4f} "
                  f"{row.get('rank_ic', 0):<10.4f} {row.get('ir', 0):<8.4f}")
        
        # 統計信息
        print(f"\n評估統計:")
        print(f"平均 IC: {evaluation_results['ic'].mean():.4f}")
        print(f"IC 標準差: {evaluation_results['ic'].std():.4f}")
        print(f"正 IC 比例: {(evaluation_results['ic'] > 0).mean():.1%}")
        
        return evaluation_results
        
    except Exception as e:
        logger.error(f"因子評估失敗: {e}")
        return None


def demo_performance_optimization():
    """示例：性能優化"""
    logger.info("=== 性能優化示例 ===")
    
    try:
        # 生成較大的數據集
        data = generate_sample_data(n_symbols=5, n_days=200)
        
        # 測試不同配置的性能
        configs = [
            {
                'name': '單進程',
                'config': FactorMiningConfig(
                    method='tsfresh',
                    n_jobs=1,
                    tsfresh_config={'minimal_features': True}
                )
            },
            {
                'name': '多進程',
                'config': FactorMiningConfig(
                    method='tsfresh',
                    n_jobs=2,
                    tsfresh_config={'minimal_features': True}
                )
            },
            {
                'name': '快取啟用',
                'config': FactorMiningConfig(
                    method='tsfresh',
                    n_jobs=2,
                    cache_enabled=True,
                    tsfresh_config={'minimal_features': True}
                )
            }
        ]
        
        results = []
        
        for config_info in configs:
            logger.info(f"測試配置: {config_info['name']}")
            
            adapter = FactorMiningAdapter(config_info['config'])
            
            # 測量執行時間
            import time
            start_time = time.time()
            
            factors = adapter.extract_factors(data, method='tsfresh')
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            results.append({
                'config': config_info['name'],
                'time': execution_time,
                'factors': factors.shape[1],
                'memory_usage': factors.memory_usage(deep=True).sum() / 1024**2  # MB
            })
            
            logger.info(f"完成: {execution_time:.2f}秒, {factors.shape[1]} 個因子")
        
        # 顯示性能比較
        print("\n" + "="*50)
        print("性能比較結果:")
        print("="*50)
        print(f"{'配置':<10} {'時間(秒)':<10} {'因子數':<8} {'內存(MB)':<10}")
        print("-" * 40)
        
        for result in results:
            print(f"{result['config']:<10} {result['time']:<10.2f} "
                  f"{result['factors']:<8} {result['memory_usage']:<10.1f}")
        
        return results
        
    except Exception as e:
        logger.error(f"性能優化測試失敗: {e}")
        return None


def generate_target_returns(data: pd.DataFrame) -> pd.DataFrame:
    """生成目標收益率"""
    target_data = []
    
    for symbol in data['symbol'].unique():
        symbol_data = data[data['symbol'] == symbol].copy()
        symbol_data = symbol_data.sort_values('date')
        
        # 計算未來1日收益率
        symbol_data['future_return'] = symbol_data['close'].pct_change().shift(-1)
        
        for _, row in symbol_data.iterrows():
            if not pd.isna(row['future_return']):
                target_data.append({
                    'symbol': symbol,
                    'date': row['date'],
                    'target': row['future_return']
                })
    
    return pd.DataFrame(target_data)


def align_data(factors: pd.DataFrame, returns: pd.DataFrame) -> tuple:
    """對齊因子和收益率數據"""
    # 簡化的對齊邏輯
    common_index = factors.index.intersection(returns.set_index(['symbol', 'date']).index)
    
    aligned_factors = factors.loc[common_index]
    aligned_returns = returns.set_index(['symbol', 'date']).loc[common_index]['target']
    
    return aligned_factors, aligned_returns


def main():
    """主函數"""
    print("🔍 tsfresh 自動因子挖掘示例")
    print("=" * 50)
    
    try:
        # 1. 基礎因子提取
        demo_basic_factor_extraction()
        
        print("\n" + "="*50 + "\n")
        
        # 2. 因子選擇
        demo_factor_selection()
        
        print("\n" + "="*50 + "\n")
        
        # 3. 因子評估
        demo_factor_evaluation()
        
        print("\n" + "="*50 + "\n")
        
        # 4. 性能優化
        demo_performance_optimization()
        
        print("\n🎉 所有示例運行完成！")
        
    except KeyboardInterrupt:
        logger.info("用戶中斷執行")
    except Exception as e:
        logger.error(f"示例運行失敗: {e}")
        raise


if __name__ == "__main__":
    main()
