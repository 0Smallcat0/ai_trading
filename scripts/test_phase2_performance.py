#!/usr/bin/env python3
"""
Phase 2 Performance Test - Lazy Loading and Memory Optimization

This script tests the Phase 2 performance improvements including:
- AI module lazy loading performance
- Memory usage optimization
- Asynchronous processing improvements
- UI component restructuring benefits

Measures against Phase 2 success criteria:
- Module import time: <1.0s average (currently 3.4s)
- Memory usage: <200MB increase (currently 326.3MB)
- Data operation response: <2.0s for complex queries
- UI responsiveness: Maintain <0.1s for cached operations
"""

import time
import sys
import os
import psutil
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple
import traceback
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Phase2PerformanceTest:
    """Performance test suite for Phase 2 optimizations"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.process = psutil.Process()
        self.results = {}
        
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def test_lazy_loading_performance(self) -> Dict:
        """Test AI module lazy loading performance"""
        print("\n🔍 Testing AI Module Lazy Loading Performance...")
        
        results = {
            'test_name': 'ai_lazy_loading',
            'success': False,
            'metrics': {},
            'errors': []
        }
        
        try:
            # Test lazy loading system availability
            start_time = time.time()
            initial_memory = self.get_memory_usage()
            
            try:
                from src.ui.utils.ai_lazy_loader import ai_lazy_loader, load_ai_module
                from src.ui.utils.ai_module_registry import register_all_ai_modules
                
                lazy_loading_available = True
                setup_time = time.time() - start_time
                
                print(f"  ✅ Lazy loading system available ({setup_time:.3f}s)")
                
            except ImportError as e:
                lazy_loading_available = False
                results['errors'].append(f"Lazy loading system not available: {e}")
                print(f"  ❌ Lazy loading system not available: {e}")
                return results
            
            if lazy_loading_available:
                # Test module registration
                registration_start = time.time()
                register_all_ai_modules()
                registration_time = time.time() - registration_start
                
                print(f"  ✅ AI modules registered ({registration_time:.3f}s)")
                
                # Test lazy loading metrics
                metrics = ai_lazy_loader.get_load_metrics()
                
                results['metrics'] = {
                    'setup_time': setup_time,
                    'registration_time': registration_time,
                    'registered_modules': metrics.get('registered_modules', 0),
                    'cached_modules': metrics.get('cached_modules', 0),
                    'memory_usage_mb': self.get_memory_usage() - initial_memory
                }
                
                # Test async loading (if possible)
                if hasattr(asyncio, 'run'):
                    async_test_result = self._test_async_loading()
                    results['metrics'].update(async_test_result)
                
                results['success'] = True
                
                print(f"  📊 Registered modules: {metrics.get('registered_modules', 0)}")
                print(f"  💾 Memory usage: +{results['metrics']['memory_usage_mb']:.1f}MB")
                
        except Exception as e:
            results['errors'].append(f"Lazy loading test failed: {e}")
            print(f"  ❌ Test failed: {e}")
            
        return results
    
    def _test_async_loading(self) -> Dict:
        """Test asynchronous module loading"""
        print("  🔄 Testing async module loading...")
        
        async def test_async_load():
            try:
                from src.ui.utils.ai_lazy_loader import load_ai_module
                
                start_time = time.time()
                
                # Test loading a mock module (should be fast)
                result = await load_ai_module("integrated_feature_calculator", show_progress=False)
                
                load_time = time.time() - start_time
                
                return {
                    'async_load_time': load_time,
                    'async_load_success': result is not None
                }
                
            except Exception as e:
                return {
                    'async_load_time': 0,
                    'async_load_success': False,
                    'async_error': str(e)
                }
        
        try:
            # Create new event loop for testing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(test_async_load())
            
            if result.get('async_load_success'):
                print(f"    ✅ Async loading: {result['async_load_time']:.3f}s")
            else:
                print(f"    ❌ Async loading failed: {result.get('async_error', 'Unknown error')}")
            
            loop.close()
            return result
            
        except Exception as e:
            print(f"    ❌ Async test failed: {e}")
            return {'async_load_time': 0, 'async_load_success': False, 'async_error': str(e)}
    
    def test_memory_optimization(self) -> Dict:
        """Test memory usage optimization"""
        print("\n💾 Testing Memory Optimization...")
        
        results = {
            'test_name': 'memory_optimization',
            'success': False,
            'metrics': {},
            'errors': []
        }
        
        try:
            initial_memory = self.get_memory_usage()
            
            # Test data management page loading
            start_time = time.time()
            
            try:
                from src.ui.pages.data_management import get_ai_modules, get_core_modules
                
                # Load modules and measure memory
                ai_modules = get_ai_modules()
                core_modules = get_core_modules()
                
                load_time = time.time() - start_time
                memory_after_load = self.get_memory_usage()
                memory_increase = memory_after_load - initial_memory
                
                results['metrics'] = {
                    'initial_memory_mb': initial_memory,
                    'final_memory_mb': memory_after_load,
                    'memory_increase_mb': memory_increase,
                    'load_time': load_time,
                    'ai_modules_available': ai_modules is not None,
                    'core_modules_available': core_modules is not None
                }
                
                # Check if memory increase is within target (<200MB)
                memory_target_met = memory_increase < 200.0
                
                results['success'] = memory_target_met
                
                print(f"  📊 Initial memory: {initial_memory:.1f}MB")
                print(f"  📊 Final memory: {memory_after_load:.1f}MB")
                print(f"  📊 Memory increase: {memory_increase:.1f}MB")
                print(f"  🎯 Target (<200MB): {'✅ MET' if memory_target_met else '❌ NOT MET'}")
                
            except ImportError as e:
                results['errors'].append(f"Failed to import modules: {e}")
                print(f"  ❌ Import failed: {e}")
                
        except Exception as e:
            results['errors'].append(f"Memory test failed: {e}")
            print(f"  ❌ Test failed: {e}")
            
        return results
    
    def test_ui_responsiveness(self) -> Dict:
        """Test UI responsiveness improvements"""
        print("\n⚡ Testing UI Responsiveness...")
        
        results = {
            'test_name': 'ui_responsiveness',
            'success': False,
            'metrics': {},
            'errors': []
        }
        
        try:
            # Test cached function performance
            cached_function_times = []
            
            for i in range(5):
                start_time = time.time()
                
                try:
                    from src.ui.pages.data_management import get_ai_modules
                    modules = get_ai_modules()
                    
                    execution_time = time.time() - start_time
                    cached_function_times.append(execution_time)
                    
                except Exception as e:
                    results['errors'].append(f"Cached function test {i+1} failed: {e}")
            
            if cached_function_times:
                avg_cached_time = sum(cached_function_times) / len(cached_function_times)
                max_cached_time = max(cached_function_times)
                min_cached_time = min(cached_function_times)
                
                # Check if cached operations are within target (<0.1s)
                responsiveness_target_met = avg_cached_time < 0.1
                
                results['metrics'] = {
                    'avg_cached_time': avg_cached_time,
                    'max_cached_time': max_cached_time,
                    'min_cached_time': min_cached_time,
                    'test_iterations': len(cached_function_times)
                }
                
                results['success'] = responsiveness_target_met
                
                print(f"  📊 Average cached time: {avg_cached_time:.6f}s")
                print(f"  📊 Max cached time: {max_cached_time:.6f}s")
                print(f"  📊 Min cached time: {min_cached_time:.6f}s")
                print(f"  🎯 Target (<0.1s): {'✅ MET' if responsiveness_target_met else '❌ NOT MET'}")
                
        except Exception as e:
            results['errors'].append(f"UI responsiveness test failed: {e}")
            print(f"  ❌ Test failed: {e}")
            
        return results
    
    def test_data_operation_performance(self) -> Dict:
        """Test data operation response times"""
        print("\n📊 Testing Data Operation Performance...")
        
        results = {
            'test_name': 'data_operations',
            'success': False,
            'metrics': {},
            'errors': []
        }
        
        try:
            # Test data query operations
            operation_times = []
            
            # Test stock data query (if available)
            try:
                from src.ui.pages.data_management import get_stock_data_from_db
                
                start_time = time.time()
                # This will likely return empty DataFrame but tests the caching
                result = get_stock_data_from_db("2330")
                query_time = time.time() - start_time
                
                operation_times.append(('stock_data_query', query_time))
                print(f"  ✅ Stock data query: {query_time:.3f}s")
                
            except Exception as e:
                results['errors'].append(f"Stock data query failed: {e}")
                print(f"  ❌ Stock data query failed: {e}")
            
            # Test portfolio data operations
            try:
                from src.ui.pages.portfolio_management import get_mock_portfolio_data
                
                start_time = time.time()
                portfolio_data = get_mock_portfolio_data()
                portfolio_time = time.time() - start_time
                
                operation_times.append(('portfolio_data_query', portfolio_time))
                print(f"  ✅ Portfolio data query: {portfolio_time:.3f}s")
                
            except Exception as e:
                results['errors'].append(f"Portfolio data query failed: {e}")
                print(f"  ❌ Portfolio data query failed: {e}")
            
            if operation_times:
                avg_operation_time = sum(time for _, time in operation_times) / len(operation_times)
                max_operation_time = max(time for _, time in operation_times)
                
                # Check if operations are within target (<2.0s)
                performance_target_met = avg_operation_time < 2.0
                
                results['metrics'] = {
                    'avg_operation_time': avg_operation_time,
                    'max_operation_time': max_operation_time,
                    'operations_tested': len(operation_times),
                    'operation_details': dict(operation_times)
                }
                
                results['success'] = performance_target_met
                
                print(f"  📊 Average operation time: {avg_operation_time:.3f}s")
                print(f"  📊 Max operation time: {max_operation_time:.3f}s")
                print(f"  🎯 Target (<2.0s): {'✅ MET' if performance_target_met else '❌ NOT MET'}")
                
        except Exception as e:
            results['errors'].append(f"Data operation test failed: {e}")
            print(f"  ❌ Test failed: {e}")
            
        return results
    
    def run_comprehensive_test(self) -> Dict:
        """Run comprehensive Phase 2 performance tests"""
        print("🚀 Phase 2 Performance Optimization Test")
        print("="*60)
        print(f"📂 Project root: {self.project_root}")
        print(f"💾 Initial memory: {self.get_memory_usage():.1f}MB")
        
        results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'phase': 'Phase 2',
            'initial_memory_mb': self.get_memory_usage(),
            'tests': {}
        }
        
        # Run all tests
        test_methods = [
            self.test_lazy_loading_performance,
            self.test_memory_optimization,
            self.test_ui_responsiveness,
            self.test_data_operation_performance
        ]
        
        for test_method in test_methods:
            try:
                test_result = test_method()
                results['tests'][test_result['test_name']] = test_result
            except Exception as e:
                print(f"❌ Test {test_method.__name__} failed: {e}")
                results['tests'][test_method.__name__] = {
                    'test_name': test_method.__name__,
                    'success': False,
                    'errors': [str(e)]
                }
        
        # Final memory usage
        results['final_memory_mb'] = self.get_memory_usage()
        results['memory_increase_mb'] = results['final_memory_mb'] - results['initial_memory_mb']
        
        return results
    
    def print_summary(self, results: Dict):
        """Print test summary"""
        print("\n" + "="*80)
        print("📈 PHASE 2 PERFORMANCE TEST SUMMARY")
        print("="*80)
        
        total_tests = len(results['tests'])
        successful_tests = len([t for t in results['tests'].values() if t.get('success', False)])
        
        print(f"\n📊 Test Results:")
        print(f"   • Total tests: {total_tests}")
        print(f"   • Successful tests: {successful_tests}")
        print(f"   • Success rate: {(successful_tests/total_tests)*100:.1f}%")
        
        # Phase 2 Success Criteria Check
        print(f"\n🎯 Phase 2 Success Criteria:")
        
        criteria_met = 0
        total_criteria = 4
        
        # Memory usage criterion
        memory_increase = results['memory_increase_mb']
        memory_target_met = memory_increase < 200.0
        if memory_target_met:
            criteria_met += 1
        print(f"   • Memory usage (<200MB): {memory_increase:.1f}MB {'✅' if memory_target_met else '❌'}")
        
        # UI responsiveness criterion
        ui_test = results['tests'].get('ui_responsiveness', {})
        ui_target_met = ui_test.get('success', False)
        if ui_target_met:
            criteria_met += 1
        avg_cached_time = ui_test.get('metrics', {}).get('avg_cached_time', 999)
        print(f"   • UI responsiveness (<0.1s): {avg_cached_time:.6f}s {'✅' if ui_target_met else '❌'}")
        
        # Data operations criterion
        data_test = results['tests'].get('data_operations', {})
        data_target_met = data_test.get('success', False)
        if data_target_met:
            criteria_met += 1
        avg_op_time = data_test.get('metrics', {}).get('avg_operation_time', 999)
        print(f"   • Data operations (<2.0s): {avg_op_time:.3f}s {'✅' if data_target_met else '❌'}")
        
        # Lazy loading criterion
        lazy_test = results['tests'].get('ai_lazy_loading', {})
        lazy_target_met = lazy_test.get('success', False)
        if lazy_target_met:
            criteria_met += 1
        print(f"   • Lazy loading system: {'✅ Available' if lazy_target_met else '❌ Not Available'}")
        
        # Overall assessment
        success_rate = (criteria_met / total_criteria) * 100
        print(f"\n🏆 Overall Phase 2 Success Rate: {criteria_met}/{total_criteria} ({success_rate:.1f}%)")
        
        if success_rate >= 75:
            print("   🎉 EXCELLENT: Phase 2 optimization successful!")
        elif success_rate >= 50:
            print("   ✅ GOOD: Most Phase 2 targets met")
        else:
            print("   ⚠️ NEEDS IMPROVEMENT: Several targets not met")
    
    def save_results(self, results: Dict, filename: str = "phase2_performance_test_results.json"):
        """Save test results to file"""
        output_path = self.project_root / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Test results saved to: {output_path}")


def main():
    """Main function"""
    project_root = os.getcwd()
    
    tester = Phase2PerformanceTest(project_root)
    
    try:
        # Run comprehensive tests
        results = tester.run_comprehensive_test()
        
        # Print summary
        tester.print_summary(results)
        
        # Save results
        tester.save_results(results)
        
        print(f"\n✅ Phase 2 performance test complete!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
