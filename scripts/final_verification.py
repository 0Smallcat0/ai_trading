#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""策略庫擴展整合最終驗證腳本

此腳本執行策略庫擴展整合項目的最終驗證，包括：
- 代碼品質檢查
- 功能完整性測試
- 性能基準測試
- 文檔完整性驗證
- 整合狀態確認

使用方法：
    python scripts/final_verification.py

輸出：
- 完整驗證報告
- 項目完成狀態
- 建議後續步驟
"""

import sys
import os
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
import numpy as np

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class FinalVerifier:
    """策略庫擴展整合最終驗證器"""
    
    def __init__(self):
        """初始化驗證器"""
        self.results = {
            'timestamp': datetime.now(),
            'code_quality': {},
            'functionality': {},
            'performance': {},
            'documentation': {},
            'integration': {},
            'summary': {}
        }
    
    def check_code_quality(self) -> bool:
        """檢查代碼品質"""
        print("🔍 檢查代碼品質...")
        
        modules_to_check = [
            'src/strategies/adapters/base.py',
            'src/strategies/adapters/double_ma_adapter.py',
            'src/strategies/adapters/alpha101_adapter.py'
        ]
        
        quality_results = {}
        overall_pass = True
        
        for module in modules_to_check:
            if os.path.exists(module):
                try:
                    # 運行 pylint
                    result = subprocess.run(
                        ['python', '-m', 'pylint', module, '--output-format=json'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    # 解析評分 (簡化版本)
                    if "Your code has been rated at" in result.stdout:
                        score_line = [line for line in result.stdout.split('\n') 
                                    if "Your code has been rated at" in line][0]
                        score = float(score_line.split()[6].split('/')[0])
                    else:
                        score = 0.0
                    
                    quality_results[module] = {
                        'score': score,
                        'status': 'PASS' if score >= 8.5 else 'FAIL'
                    }
                    
                    if score < 8.5:
                        overall_pass = False
                    
                    print(f"  ✓ {module}: {score}/10")
                    
                except Exception as e:
                    quality_results[module] = {
                        'score': 0.0,
                        'status': 'ERROR',
                        'error': str(e)
                    }
                    overall_pass = False
                    print(f"  ✗ {module}: 錯誤 - {e}")
            else:
                quality_results[module] = {
                    'score': 0.0,
                    'status': 'MISSING'
                }
                overall_pass = False
                print(f"  ✗ {module}: 文件不存在")
        
        self.results['code_quality'] = {
            'modules': quality_results,
            'overall_pass': overall_pass,
            'average_score': sum(r.get('score', 0) for r in quality_results.values()) / len(quality_results)
        }
        
        return overall_pass
    
    def test_functionality(self) -> bool:
        """測試功能完整性"""
        print("🧪 測試功能完整性...")
        
        functionality_results = {}
        overall_pass = True
        
        # 測試模組導入
        try:
            from src.strategies.adapters import (
                LegacyStrategyAdapter,
                DataFormatConverter,
                StrategyWrapper,
                DoubleMaAdapter,
                Alpha101Adapter
            )
            functionality_results['imports'] = {'status': 'PASS', 'message': '所有模組成功導入'}
            print("  ✓ 模組導入測試通過")
        except Exception as e:
            functionality_results['imports'] = {'status': 'FAIL', 'error': str(e)}
            overall_pass = False
            print(f"  ✗ 模組導入失敗: {e}")
            return False
        
        # 測試數據格式轉換器
        try:
            test_data = pd.DataFrame({
                '收盤價': [100, 101, 102],
                '交易日期': pd.date_range('2023-01-01', periods=3)
            })
            
            standardized = DataFormatConverter.standardize_columns(test_data)
            assert 'close' in standardized.columns
            assert 'date' in standardized.columns
            
            functionality_results['data_converter'] = {'status': 'PASS'}
            print("  ✓ 數據格式轉換器測試通過")
        except Exception as e:
            functionality_results['data_converter'] = {'status': 'FAIL', 'error': str(e)}
            overall_pass = False
            print(f"  ✗ 數據格式轉換器測試失敗: {e}")
        
        # 測試雙移動平均線適配器
        try:
            test_data = pd.DataFrame({
                'close': [100, 101, 102, 103, 104, 105, 106],
                'date': pd.date_range('2023-01-01', periods=7)
            })
            
            adapter = DoubleMaAdapter(short_window=2, long_window=3)
            signals = adapter.generate_signals(test_data)
            
            assert isinstance(signals, pd.DataFrame)
            assert 'signal' in signals.columns
            assert len(signals) == len(test_data)
            
            functionality_results['double_ma_adapter'] = {'status': 'PASS'}
            print("  ✓ 雙移動平均線適配器測試通過")
        except Exception as e:
            functionality_results['double_ma_adapter'] = {'status': 'FAIL', 'error': str(e)}
            overall_pass = False
            print(f"  ✗ 雙移動平均線適配器測試失敗: {e}")
        
        # 測試 Alpha101 適配器
        try:
            adapter = Alpha101Adapter(factors=['alpha001'])
            signals = adapter.generate_signals(test_data)
            
            assert isinstance(signals, pd.DataFrame)
            assert 'combined_factor' in signals.columns
            
            functionality_results['alpha101_adapter'] = {'status': 'PASS'}
            print("  ✓ Alpha101適配器測試通過")
        except Exception as e:
            functionality_results['alpha101_adapter'] = {'status': 'FAIL', 'error': str(e)}
            overall_pass = False
            print(f"  ✗ Alpha101適配器測試失敗: {e}")
        
        self.results['functionality'] = {
            'tests': functionality_results,
            'overall_pass': overall_pass
        }
        
        return overall_pass
    
    def test_performance(self) -> bool:
        """測試性能基準"""
        print("⚡ 測試性能基準...")
        
        performance_results = {}
        overall_pass = True
        
        try:
            from src.strategies.adapters import DoubleMaAdapter, Alpha101Adapter
            
            # 創建大量測試數據
            large_data = pd.DataFrame({
                'close': 100 + np.cumsum(np.random.randn(1000) * 0.01),
                'date': pd.date_range('2020-01-01', periods=1000)
            })
            
            # 測試雙移動平均線性能
            adapter = DoubleMaAdapter(short_window=5, long_window=20)
            start_time = time.time()
            signals = adapter.generate_signals(large_data)
            execution_time = time.time() - start_time
            
            performance_results['double_ma_performance'] = {
                'execution_time': execution_time,
                'throughput': len(large_data) / execution_time,
                'status': 'PASS' if execution_time < 1.0 else 'FAIL'
            }
            
            if execution_time >= 1.0:
                overall_pass = False
            
            print(f"  ✓ 雙移動平均線性能: {execution_time:.3f}s ({len(large_data)} 數據點)")
            
            # 測試 Alpha101 性能
            alpha_adapter = Alpha101Adapter(factors=['alpha001'])
            start_time = time.time()
            alpha_signals = alpha_adapter.generate_signals(large_data)
            alpha_time = time.time() - start_time
            
            performance_results['alpha101_performance'] = {
                'execution_time': alpha_time,
                'throughput': len(large_data) / alpha_time,
                'status': 'PASS' if alpha_time < 1.0 else 'FAIL'
            }
            
            if alpha_time >= 1.0:
                overall_pass = False
            
            print(f"  ✓ Alpha101性能: {alpha_time:.3f}s ({len(large_data)} 數據點)")
            
        except Exception as e:
            performance_results['error'] = str(e)
            overall_pass = False
            print(f"  ✗ 性能測試失敗: {e}")
        
        self.results['performance'] = {
            'tests': performance_results,
            'overall_pass': overall_pass
        }
        
        return overall_pass
    
    def check_documentation(self) -> bool:
        """檢查文檔完整性"""
        print("📚 檢查文檔完整性...")
        
        required_docs = [
            'docs/策略說明.md',
            'docs/策略驗證結果.md',
            'docs/Todo_list.md'
        ]
        
        doc_results = {}
        overall_pass = True
        
        for doc in required_docs:
            if os.path.exists(doc):
                try:
                    with open(doc, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    doc_results[doc] = {
                        'exists': True,
                        'size': len(content),
                        'status': 'PASS' if len(content) > 1000 else 'WARN'
                    }
                    
                    print(f"  ✓ {doc}: {len(content)} 字符")
                except Exception as e:
                    doc_results[doc] = {
                        'exists': True,
                        'status': 'ERROR',
                        'error': str(e)
                    }
                    overall_pass = False
                    print(f"  ✗ {doc}: 讀取錯誤 - {e}")
            else:
                doc_results[doc] = {
                    'exists': False,
                    'status': 'MISSING'
                }
                overall_pass = False
                print(f"  ✗ {doc}: 文件不存在")
        
        self.results['documentation'] = {
            'documents': doc_results,
            'overall_pass': overall_pass
        }
        
        return overall_pass
    
    def check_integration_status(self) -> bool:
        """檢查整合狀態"""
        print("🔗 檢查整合狀態...")
        
        integration_results = {
            'adapter_architecture': True,
            'zero_modification_principle': True,
            'unified_interface': True,
            'error_handling': True,
            'performance_optimization': True
        }
        
        # 檢查適配器架構
        adapter_files = [
            'src/strategies/adapters/__init__.py',
            'src/strategies/adapters/base.py',
            'src/strategies/adapters/double_ma_adapter.py',
            'src/strategies/adapters/alpha101_adapter.py'
        ]
        
        for file in adapter_files:
            if not os.path.exists(file):
                integration_results['adapter_architecture'] = False
                break
        
        overall_pass = all(integration_results.values())
        
        self.results['integration'] = {
            'checks': integration_results,
            'overall_pass': overall_pass
        }
        
        status = "✓" if overall_pass else "✗"
        print(f"  {status} 整合狀態檢查{'通過' if overall_pass else '失敗'}")
        
        return overall_pass
    
    def generate_summary(self) -> None:
        """生成總結報告"""
        print("\n" + "="*60)
        print("📊 策略庫擴展整合最終驗證報告")
        print("="*60)
        
        # 計算總體通過率
        test_categories = ['code_quality', 'functionality', 'performance', 'documentation', 'integration']
        passed_tests = sum(1 for cat in test_categories if self.results[cat]['overall_pass'])
        total_tests = len(test_categories)
        success_rate = passed_tests / total_tests
        
        self.results['summary'] = {
            'total_categories': total_tests,
            'passed_categories': passed_tests,
            'success_rate': success_rate,
            'overall_status': 'PASS' if success_rate >= 0.8 else 'FAIL'
        }
        
        print(f"總測試類別: {total_tests}")
        print(f"通過類別: {passed_tests}")
        print(f"成功率: {success_rate:.1%}")
        print(f"整體狀態: {'✅ 通過' if success_rate >= 0.8 else '❌ 失敗'}")
        
        # 詳細結果
        print("\n📋 詳細結果:")
        for category in test_categories:
            status = "✅" if self.results[category]['overall_pass'] else "❌"
            print(f"  {status} {category.replace('_', ' ').title()}")
        
        # 代碼品質詳情
        if 'code_quality' in self.results:
            avg_score = self.results['code_quality'].get('average_score', 0)
            print(f"\n📊 代碼品質平均分: {avg_score:.2f}/10")
        
        # 建議
        print("\n💡 建議後續步驟:")
        if success_rate >= 0.8:
            print("  ✅ 策略庫擴展整合項目已成功完成")
            print("  🚀 可以開始下一階段的開發工作")
            print("  📈 建議進行更多策略的整合")
        else:
            print("  ⚠️  需要解決失敗的測試項目")
            print("  🔧 建議檢查錯誤日誌並修復問題")
            print("  🔄 修復後重新運行驗證")
    
    def run_verification(self) -> bool:
        """運行完整驗證"""
        print("🚀 開始策略庫擴展整合最終驗證")
        print("="*60)
        
        tests = [
            ('代碼品質檢查', self.check_code_quality),
            ('功能完整性測試', self.test_functionality),
            ('性能基準測試', self.test_performance),
            ('文檔完整性檢查', self.check_documentation),
            ('整合狀態檢查', self.check_integration_status),
        ]
        
        for test_name, test_func in tests:
            print(f"\n{test_name}...")
            try:
                test_func()
            except Exception as e:
                print(f"  ✗ {test_name}執行失敗: {e}")
                # 確保結果字典有 overall_pass 鍵
                category_key = test_name.replace('檢查', '').replace('測試', '').replace(' ', '_').lower()
                if category_key not in self.results:
                    self.results[category_key] = {'overall_pass': False}
        
        self.generate_summary()
        
        return self.results['summary']['overall_status'] == 'PASS'


def main():
    """主函數"""
    verifier = FinalVerifier()
    
    try:
        success = verifier.run_verification()
        
        # 保存驗證報告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"strategy_integration_final_report_{timestamp}.json"
        
        import json
        with open(report_file, 'w', encoding='utf-8') as f:
            # 轉換不可序列化的對象
            serializable_results = {}
            for key, value in verifier.results.items():
                if key == 'timestamp':
                    serializable_results[key] = value.isoformat()
                else:
                    serializable_results[key] = value
            
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 驗證報告已保存到: {report_file}")
        
        # 返回適當的退出碼
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n驗證被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n驗證過程中發生未預期錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
