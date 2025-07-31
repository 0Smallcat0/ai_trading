#!/usr/bin/env python3
"""
Import Optimization Performance Test

This script tests the performance improvements from the import optimization
by measuring module loading times and cached function execution times.

Based on the performance optimization requirements to measure:
- Module import times before and after optimization
- Cached function execution times
- Memory usage improvements
- Page load simulation times
"""

import time
import sys
import os
import importlib
import psutil
import json
from pathlib import Path
from typing import Dict, List, Tuple
import traceback


class ImportOptimizationTest:
    """Test suite for import optimization performance"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.process = psutil.Process()
        self.results = {}
        
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def test_module_import_time(self, module_name: str, iterations: int = 3) -> Dict:
        """Test module import time"""
        print(f"🔍 Testing import: {module_name}")
        
        times = []
        memory_before = self.get_memory_usage()
        
        for i in range(iterations):
            # Clear module from cache if it exists
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            start_time = time.time()
            try:
                importlib.import_module(module_name)
                end_time = time.time()
                import_time = end_time - start_time
                times.append(import_time)
                print(f"  Iteration {i+1}: {import_time:.4f}s")
            except Exception as e:
                print(f"  Iteration {i+1}: FAILED - {e}")
                return {
                    'module': module_name,
                    'success': False,
                    'error': str(e),
                    'avg_time': 0,
                    'memory_usage': 0
                }
        
        memory_after = self.get_memory_usage()
        avg_time = sum(times) / len(times) if times else 0
        
        result = {
            'module': module_name,
            'success': True,
            'avg_time': avg_time,
            'min_time': min(times) if times else 0,
            'max_time': max(times) if times else 0,
            'memory_usage': memory_after - memory_before,
            'iterations': iterations
        }
        
        print(f"  ✅ Average: {avg_time:.4f}s, Memory: +{result['memory_usage']:.2f}MB")
        return result
    
    def test_cached_functions(self) -> Dict:
        """Test cached import functions performance"""
        print("\n🔍 Testing cached import functions...")
        
        try:
            from src.ui.pages.data_management import (
                get_core_modules, get_ai_modules, get_visualization_modules,
                get_enhanced_modules, get_batch_updater_modules, get_talib_module
            )
            
            cached_functions = [
                ('get_core_modules', get_core_modules),
                ('get_ai_modules', get_ai_modules),
                ('get_visualization_modules', get_visualization_modules),
                ('get_enhanced_modules', get_enhanced_modules),
                ('get_batch_updater_modules', get_batch_updater_modules),
                ('get_talib_module', get_talib_module)
            ]
            
            results = {}
            
            for func_name, func in cached_functions:
                print(f"  Testing {func_name}...")
                times = []
                
                for i in range(5):
                    start_time = time.time()
                    try:
                        result = func()
                        end_time = time.time()
                        execution_time = end_time - start_time
                        times.append(execution_time)
                    except Exception as e:
                        print(f"    Iteration {i+1}: FAILED - {e}")
                        break
                
                if times:
                    avg_time = sum(times) / len(times)
                    results[func_name] = {
                        'avg_time': avg_time,
                        'min_time': min(times),
                        'max_time': max(times),
                        'success': True
                    }
                    print(f"    ✅ Average: {avg_time:.6f}s")
                else:
                    results[func_name] = {
                        'avg_time': 0,
                        'success': False
                    }
            
            return results
            
        except ImportError as e:
            print(f"❌ Could not import cached functions: {e}")
            return {}
    
    def test_page_load_simulation(self) -> Dict:
        """Simulate page load performance"""
        print("\n🔍 Testing page load simulation...")
        
        def simulate_data_management_page_load():
            """Simulate loading the data management page"""
            try:
                # Import the main module
                from src.ui.pages.data_management import initialize_session_state
                
                # Import cached modules
                from src.ui.pages.data_management import (
                    get_core_modules, get_ai_modules, get_visualization_modules
                )
                
                # Simulate session state initialization
                # Note: This won't actually work without Streamlit context,
                # but we can measure the import and function call times
                
                # Call cached functions to simulate page load
                get_core_modules()
                get_ai_modules() 
                get_visualization_modules()
                
                return True
                
            except Exception as e:
                print(f"Page load simulation error: {e}")
                return False
        
        times = []
        memory_before = self.get_memory_usage()
        
        for i in range(3):
            start_time = time.time()
            success = simulate_data_management_page_load()
            end_time = time.time()
            
            if success:
                load_time = end_time - start_time
                times.append(load_time)
                print(f"  Iteration {i+1}: {load_time:.4f}s")
            else:
                print(f"  Iteration {i+1}: FAILED")
        
        memory_after = self.get_memory_usage()
        
        if times:
            avg_time = sum(times) / len(times)
            result = {
                'success': True,
                'avg_time': avg_time,
                'min_time': min(times),
                'max_time': max(times),
                'memory_usage': memory_after - memory_before,
                'target_met': avg_time < 2.0  # Target: < 2.0s
            }
            print(f"  ✅ Average page load: {avg_time:.4f}s")
            print(f"  🎯 Target (<2.0s): {'✅ MET' if result['target_met'] else '❌ NOT MET'}")
        else:
            result = {
                'success': False,
                'avg_time': 0,
                'target_met': False
            }
        
        return result
    
    def run_comprehensive_test(self) -> Dict:
        """Run comprehensive import optimization tests"""
        print("🚀 Import Optimization Performance Test")
        print("="*60)
        print(f"📂 Project root: {self.project_root}")
        print(f"💾 Initial memory: {self.get_memory_usage():.1f}MB")
        
        results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'initial_memory_mb': self.get_memory_usage(),
            'module_imports': {},
            'cached_functions': {},
            'page_load_simulation': {}
        }
        
        # Test critical module imports
        critical_modules = [
            'src.ui.pages.data_management',
            'src.ai.self_learning_agent',
            'src.core.integrated_feature_calculator',
            'src.ui.components.interactive_charts',
            'src.core.data_management_service'
        ]
        
        print(f"\n📊 Testing {len(critical_modules)} critical module imports...")
        for module in critical_modules:
            try:
                result = self.test_module_import_time(module)
                results['module_imports'][module] = result
            except Exception as e:
                print(f"❌ Failed to test {module}: {e}")
                results['module_imports'][module] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Test cached functions
        results['cached_functions'] = self.test_cached_functions()
        
        # Test page load simulation
        results['page_load_simulation'] = self.test_page_load_simulation()
        
        # Final memory usage
        results['final_memory_mb'] = self.get_memory_usage()
        results['memory_increase_mb'] = results['final_memory_mb'] - results['initial_memory_mb']
        
        return results
    
    def print_summary(self, results: Dict):
        """Print test summary"""
        print("\n" + "="*80)
        print("📈 IMPORT OPTIMIZATION TEST SUMMARY")
        print("="*80)
        
        # Module import summary
        successful_imports = [r for r in results['module_imports'].values() if r.get('success', False)]
        if successful_imports:
            avg_import_time = sum(r['avg_time'] for r in successful_imports) / len(successful_imports)
            print(f"\n📊 Module Import Performance:")
            print(f"   • Successful imports: {len(successful_imports)}/{len(results['module_imports'])}")
            print(f"   • Average import time: {avg_import_time:.4f}s")
            print(f"   • Target (<1.0s): {'✅ MET' if avg_import_time < 1.0 else '❌ NOT MET'}")
        
        # Cached function summary
        cached_results = results['cached_functions']
        if cached_results:
            successful_cached = [r for r in cached_results.values() if r.get('success', False)]
            if successful_cached:
                avg_cached_time = sum(r['avg_time'] for r in successful_cached) / len(successful_cached)
                print(f"\n⚡ Cached Function Performance:")
                print(f"   • Successful cached calls: {len(successful_cached)}/{len(cached_results)}")
                print(f"   • Average cached time: {avg_cached_time:.6f}s")
                print(f"   • Target (<0.1s): {'✅ MET' if avg_cached_time < 0.1 else '❌ NOT MET'}")
        
        # Page load summary
        page_load = results['page_load_simulation']
        if page_load.get('success', False):
            print(f"\n🚀 Page Load Performance:")
            print(f"   • Average load time: {page_load['avg_time']:.4f}s")
            print(f"   • Target (<2.0s): {'✅ MET' if page_load['target_met'] else '❌ NOT MET'}")
        
        # Memory usage
        print(f"\n💾 Memory Usage:")
        print(f"   • Initial: {results['initial_memory_mb']:.1f}MB")
        print(f"   • Final: {results['final_memory_mb']:.1f}MB")
        print(f"   • Increase: {results['memory_increase_mb']:.1f}MB")
        
        print(f"\n🎯 Performance Optimization Status:")
        targets_met = 0
        total_targets = 0
        
        if successful_imports:
            total_targets += 1
            if avg_import_time < 1.0:
                targets_met += 1
        
        if successful_cached:
            total_targets += 1
            if avg_cached_time < 0.1:
                targets_met += 1
        
        if page_load.get('success', False):
            total_targets += 1
            if page_load['target_met']:
                targets_met += 1
        
        if total_targets > 0:
            success_rate = (targets_met / total_targets) * 100
            print(f"   • Targets met: {targets_met}/{total_targets} ({success_rate:.1f}%)")
            
            if success_rate >= 80:
                print("   🎉 EXCELLENT: Performance optimization successful!")
            elif success_rate >= 60:
                print("   ✅ GOOD: Most performance targets met")
            else:
                print("   ⚠️ NEEDS IMPROVEMENT: Several targets not met")
    
    def save_results(self, results: Dict, filename: str = "import_optimization_test_results.json"):
        """Save test results to file"""
        output_path = self.project_root / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Test results saved to: {output_path}")


def main():
    """Main function"""
    project_root = os.getcwd()
    
    tester = ImportOptimizationTest(project_root)
    
    try:
        # Run comprehensive tests
        results = tester.run_comprehensive_test()
        
        # Print summary
        tester.print_summary(results)
        
        # Save results
        tester.save_results(results)
        
        print(f"\n✅ Import optimization test complete!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
