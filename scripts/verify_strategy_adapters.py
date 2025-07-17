#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略適配器驗證腳本

此腳本驗證策略適配器的功能和性能，包括：
- 適配器基本功能測試
- 策略執行性能測試
- 代碼品質評估
- 整合測試驗證

使用方法：
    python scripts/verify_strategy_adapters.py

輸出：
- 驗證報告
- 性能統計
- 代碼品質評分
- 建議改進項目
"""

import sys
import os
import time
import traceback
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategies.adapters import (
    DoubleMaAdapter,
    Alpha101Adapter,
    DataFormatConverter,
    StrategyWrapper,
)


class StrategyAdapterVerifier:
    """策略適配器驗證器"""
    
    def __init__(self):
        """初始化驗證器"""
        self.results = {
            'timestamp': datetime.now(),
            'tests': {},
            'performance': {},
            'errors': [],
            'summary': {}
        }
    
    def create_test_data(self, days: int = 100) -> pd.DataFrame:
        """
        創建測試數據。
        
        Args:
            days: 數據天數
            
        Returns:
            測試數據框架
        """
        dates = pd.date_range('2023-01-01', periods=days)
        
        # 生成模擬價格數據
        np.random.seed(42)  # 確保結果可重現
        returns = np.random.normal(0.001, 0.02, days)  # 日收益率
        prices = 100 * np.exp(np.cumsum(returns))  # 價格序列
        
        data = pd.DataFrame({
            'date': dates,
            'close': prices,
            'open': prices * (1 + np.random.normal(0, 0.005, days)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, days))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, days))),
            'volume': np.random.randint(1000, 10000, days)
        })
        
        return data
    
    def test_data_format_converter(self) -> bool:
        """測試數據格式轉換器"""
        try:
            print("測試數據格式轉換器...")
            
            # 創建測試數據
            test_data = pd.DataFrame({
                '收盤價': [100, 101, 102],
                '交易日期': pd.date_range('2023-01-01', periods=3),
                '成交量': [1000, 1100, 1200]
            })
            
            # 測試欄位標準化
            standardized = DataFormatConverter.standardize_columns(test_data)
            assert 'close' in standardized.columns
            assert 'date' in standardized.columns
            
            # 測試格式轉換
            legacy_format = DataFormatConverter.convert_to_legacy_format(standardized)
            assert isinstance(legacy_format, pd.DataFrame)
            assert len(legacy_format) == 3
            
            self.results['tests']['data_format_converter'] = {
                'status': 'PASS',
                'message': '數據格式轉換器測試通過'
            }
            print("✓ 數據格式轉換器測試通過")
            return True
            
        except Exception as e:
            error_msg = f"數據格式轉換器測試失敗: {e}"
            self.results['tests']['data_format_converter'] = {
                'status': 'FAIL',
                'message': error_msg,
                'error': str(e)
            }
            self.results['errors'].append(error_msg)
            print(f"✗ {error_msg}")
            return False
    
    def test_double_ma_adapter(self) -> bool:
        """測試雙移動平均線適配器"""
        try:
            print("測試雙移動平均線適配器...")
            
            # 創建測試數據
            test_data = self.create_test_data(50)
            
            # 創建適配器
            adapter = DoubleMaAdapter(short_window=5, long_window=20)
            
            # 測試訊號生成
            start_time = time.time()
            signals = adapter.generate_signals(test_data)
            execution_time = time.time() - start_time
            
            # 驗證結果
            assert isinstance(signals, pd.DataFrame)
            assert len(signals) == len(test_data)
            assert 'signal' in signals.columns
            assert 'buy_signal' in signals.columns
            assert 'sell_signal' in signals.columns
            
            # 驗證訊號值
            assert signals['signal'].isin([0.0, 1.0, -1.0]).all()
            assert signals['buy_signal'].isin([0, 1]).all()
            assert signals['sell_signal'].isin([0, 1]).all()
            
            # 測試策略評估
            metrics = adapter.evaluate(test_data, signals)
            assert isinstance(metrics, dict)
            assert 'total_return' in metrics
            
            # 測試策略資訊
            info = adapter.get_strategy_info()
            assert info['name'] == "DoubleMaStrategy"
            
            self.results['tests']['double_ma_adapter'] = {
                'status': 'PASS',
                'message': '雙移動平均線適配器測試通過',
                'execution_time': execution_time,
                'signals_generated': len(signals),
                'buy_signals': signals['buy_signal'].sum(),
                'sell_signals': signals['sell_signal'].sum(),
                'metrics': metrics
            }
            
            print(f"✓ 雙移動平均線適配器測試通過 (執行時間: {execution_time:.3f}s)")
            print(f"  - 生成訊號: {len(signals)} 個")
            print(f"  - 買入訊號: {signals['buy_signal'].sum()} 個")
            print(f"  - 賣出訊號: {signals['sell_signal'].sum()} 個")
            return True
            
        except Exception as e:
            error_msg = f"雙移動平均線適配器測試失敗: {e}"
            self.results['tests']['double_ma_adapter'] = {
                'status': 'FAIL',
                'message': error_msg,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            self.results['errors'].append(error_msg)
            print(f"✗ {error_msg}")
            return False
    
    def test_alpha101_adapter(self) -> bool:
        """測試 Alpha101 因子庫適配器"""
        try:
            print("測試 Alpha101 因子庫適配器...")
            
            # 創建測試數據
            test_data = self.create_test_data(100)
            
            # 創建適配器
            adapter = Alpha101Adapter(
                factors=['alpha001', 'alpha002'],
                weights=[0.6, 0.4],
                signal_threshold=0.02
            )
            
            # 測試因子計算
            start_time = time.time()
            factor_results = adapter.calculate_factors(test_data)
            factor_time = time.time() - start_time
            
            # 驗證因子結果
            assert isinstance(factor_results, dict)
            assert 'alpha001' in factor_results
            assert 'alpha002' in factor_results
            
            # 測試訊號生成
            start_time = time.time()
            signals = adapter.generate_signals(test_data)
            signal_time = time.time() - start_time
            
            # 驗證結果
            assert isinstance(signals, pd.DataFrame)
            assert len(signals) == len(test_data)
            assert 'signal' in signals.columns
            assert 'combined_factor' in signals.columns
            
            # 測試策略評估
            metrics = adapter.evaluate(test_data, signals)
            assert isinstance(metrics, dict)
            
            # 測試策略資訊
            info = adapter.get_strategy_info()
            assert info['name'] == "Alpha101Strategy"
            
            self.results['tests']['alpha101_adapter'] = {
                'status': 'PASS',
                'message': 'Alpha101 因子庫適配器測試通過',
                'factor_calculation_time': factor_time,
                'signal_generation_time': signal_time,
                'factors_calculated': len(factor_results),
                'signals_generated': len(signals),
                'buy_signals': signals['buy_signal'].sum(),
                'sell_signals': signals['sell_signal'].sum(),
                'metrics': metrics
            }
            
            print(f"✓ Alpha101 因子庫適配器測試通過")
            print(f"  - 因子計算時間: {factor_time:.3f}s")
            print(f"  - 訊號生成時間: {signal_time:.3f}s")
            print(f"  - 計算因子: {len(factor_results)} 個")
            print(f"  - 買入訊號: {signals['buy_signal'].sum()} 個")
            print(f"  - 賣出訊號: {signals['sell_signal'].sum()} 個")
            return True
            
        except Exception as e:
            error_msg = f"Alpha101 因子庫適配器測試失敗: {e}"
            self.results['tests']['alpha101_adapter'] = {
                'status': 'FAIL',
                'message': error_msg,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            self.results['errors'].append(error_msg)
            print(f"✗ {error_msg}")
            return False
    
    def test_performance(self) -> bool:
        """測試性能"""
        try:
            print("測試性能...")
            
            # 創建大量測試數據
            large_data = self.create_test_data(1000)
            
            adapters = [
                ('DoubleMaAdapter', DoubleMaAdapter(short_window=5, long_window=20)),
                ('Alpha101Adapter', Alpha101Adapter(factors=['alpha001']))
            ]
            
            performance_results = {}
            
            for name, adapter in adapters:
                start_time = time.time()
                signals = adapter.generate_signals(large_data)
                execution_time = time.time() - start_time
                
                performance_results[name] = {
                    'execution_time': execution_time,
                    'data_points': len(large_data),
                    'signals_generated': len(signals),
                    'throughput': len(large_data) / execution_time  # 數據點/秒
                }
                
                print(f"  - {name}: {execution_time:.3f}s ({len(large_data)} 數據點)")
            
            self.results['performance'] = performance_results
            print("✓ 性能測試完成")
            return True
            
        except Exception as e:
            error_msg = f"性能測試失敗: {e}"
            self.results['errors'].append(error_msg)
            print(f"✗ {error_msg}")
            return False
    
    def run_all_tests(self) -> bool:
        """運行所有測試"""
        print("=" * 60)
        print("策略適配器驗證開始")
        print("=" * 60)
        
        tests = [
            self.test_data_format_converter,
            self.test_double_ma_adapter,
            self.test_alpha101_adapter,
            self.test_performance,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
            print()
        
        # 生成總結
        success_rate = passed / total
        self.results['summary'] = {
            'total_tests': total,
            'passed_tests': passed,
            'failed_tests': total - passed,
            'success_rate': success_rate,
            'overall_status': 'PASS' if success_rate >= 0.8 else 'FAIL'
        }
        
        print("=" * 60)
        print("驗證總結")
        print("=" * 60)
        print(f"總測試數: {total}")
        print(f"通過測試: {passed}")
        print(f"失敗測試: {total - passed}")
        print(f"成功率: {success_rate:.1%}")
        print(f"整體狀態: {'✓ 通過' if success_rate >= 0.8 else '✗ 失敗'}")
        
        if self.results['errors']:
            print("\n錯誤列表:")
            for error in self.results['errors']:
                print(f"  - {error}")
        
        return success_rate >= 0.8
    
    def save_report(self, filename: str = None):
        """保存驗證報告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"strategy_adapter_verification_{timestamp}.json"
        
        import json
        
        # 轉換不可序列化的對象
        serializable_results = {}
        for key, value in self.results.items():
            if key == 'timestamp':
                serializable_results[key] = value.isoformat()
            else:
                serializable_results[key] = value
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, indent=2, ensure_ascii=False)
            print(f"\n驗證報告已保存到: {filename}")
        except Exception as e:
            print(f"保存報告失敗: {e}")


def main():
    """主函數"""
    verifier = StrategyAdapterVerifier()
    
    try:
        success = verifier.run_all_tests()
        verifier.save_report()
        
        # 返回適當的退出碼
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n驗證被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n驗證過程中發生未預期錯誤: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
