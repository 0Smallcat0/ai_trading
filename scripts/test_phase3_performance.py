#!/usr/bin/env python3
"""
Phase 3 Performance Test - AI Framework Lazy Loading and Memory Optimization

This script tests the Phase 3 performance improvements including:
- AI framework lazy loading (TensorFlow, PyTorch, Optuna)
- Memory usage reduction through deferred loading
- Framework availability detection without loading
- Memory optimization effectiveness

Measures against Phase 3 success criteria:
- Memory usage: <200MB increase (currently 315.1MB)
- AI framework loading: Only when requested by users
- Framework detection: Without loading heavy dependencies
- Baseline memory: Reduced by 100-150MB through lazy loading
"""

import time
import sys
import os
import psutil
import json
import gc
from pathlib import Path
from typing import Dict, List, Tuple
import traceback
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Phase3PerformanceTest:
    """Performance test suite for Phase 3 AI framework lazy loading"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.process = psutil.Process()
        self.results = {}
        
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def test_baseline_memory_usage(self) -> Dict:
        """Test baseline memory usage without loading AI frameworks"""
        print("\n🔍 Testing Baseline Memory Usage (No AI Frameworks)...")
        
        results = {
            'test_name': 'baseline_memory',
            'success': False,
            'metrics': {},
            'errors': []
        }
        
        try:
            # Force garbage collection
            gc.collect()
            initial_memory = self.get_memory_usage()
            
            # Import basic modules only
            start_time = time.time()
            
            try:
                # Import data management without AI frameworks
                from src.ui.pages.data_management import get_core_modules
                
                # Get core modules (should not load AI frameworks)
                core_modules = get_core_modules()
                
                load_time = time.time() - start_time
                final_memory = self.get_memory_usage()
                memory_increase = final_memory - initial_memory
                
                results['metrics'] = {
                    'initial_memory_mb': initial_memory,
                    'final_memory_mb': final_memory,
                    'memory_increase_mb': memory_increase,
                    'load_time': load_time,
                    'core_modules_available': core_modules is not None
                }
                
                # Check if baseline memory is reasonable
                baseline_target_met = memory_increase < 50.0  # Should be very low without AI
                results['success'] = baseline_target_met
                
                print(f"  📊 Initial memory: {initial_memory:.1f}MB")
                print(f"  📊 Final memory: {final_memory:.1f}MB")
                print(f"  📊 Memory increase: {memory_increase:.1f}MB")
                print(f"  🎯 Baseline target (<50MB): {'✅ MET' if baseline_target_met else '❌ NOT MET'}")
                
            except ImportError as e:
                results['errors'].append(f"Failed to import core modules: {e}")
                print(f"  ❌ Import failed: {e}")
                
        except Exception as e:
            results['errors'].append(f"Baseline memory test failed: {e}")
            print(f"  ❌ Test failed: {e}")
            
        return results
    
    def test_framework_availability_detection(self) -> Dict:
        """Test framework availability detection without loading"""
        print("\n🔍 Testing Framework Availability Detection...")
        
        results = {
            'test_name': 'framework_availability',
            'success': False,
            'metrics': {},
            'errors': []
        }
        
        try:
            initial_memory = self.get_memory_usage()
            
            # Test lazy loader availability
            try:
                from src.ui.utils.ai_framework_lazy_loader import (
                    is_tensorflow_available,
                    is_torch_available,
                    is_sklearn_available,
                    is_optuna_available,
                    ai_framework_loader
                )
                
                lazy_loader_available = True
                
            except ImportError as e:
                results['errors'].append(f"Lazy loader not available: {e}")
                print(f"  ❌ Lazy loader not available: {e}")
                return results
            
            # Test availability detection
            start_time = time.time()
            
            availability_results = {
                'tensorflow': is_tensorflow_available(),
                'torch': is_torch_available(),
                'sklearn': is_sklearn_available(),
                'optuna': is_optuna_available()
            }
            
            detection_time = time.time() - start_time
            final_memory = self.get_memory_usage()
            memory_increase = final_memory - initial_memory
            
            # Get framework info
            framework_info = ai_framework_loader.get_all_frameworks_info()
            
            results['metrics'] = {
                'detection_time': detection_time,
                'memory_increase_mb': memory_increase,
                'availability_results': availability_results,
                'frameworks_registered': len(framework_info),
                'available_frameworks': sum(1 for fw in framework_info.values() if fw.is_available),
                'loaded_frameworks': sum(1 for fw in framework_info.values() if fw.is_loaded)
            }
            
            # Success criteria: Fast detection, minimal memory usage, no frameworks loaded
            detection_fast = detection_time < 1.0
            memory_minimal = memory_increase < 10.0
            no_frameworks_loaded = results['metrics']['loaded_frameworks'] == 0
            
            results['success'] = detection_fast and memory_minimal and no_frameworks_loaded
            
            print(f"  📊 Detection time: {detection_time:.3f}s")
            print(f"  📊 Memory increase: {memory_increase:.1f}MB")
            print(f"  📊 Available frameworks: {results['metrics']['available_frameworks']}")
            print(f"  📊 Loaded frameworks: {results['metrics']['loaded_frameworks']}")
            print(f"  🎯 Fast detection (<1s): {'✅' if detection_fast else '❌'}")
            print(f"  🎯 Minimal memory (<10MB): {'✅' if memory_minimal else '❌'}")
            print(f"  🎯 No frameworks loaded: {'✅' if no_frameworks_loaded else '❌'}")
            
        except Exception as e:
            results['errors'].append(f"Framework availability test failed: {e}")
            print(f"  ❌ Test failed: {e}")
            
        return results
    
    def test_lazy_framework_loading(self) -> Dict:
        """Test lazy loading of AI frameworks"""
        print("\n🔍 Testing Lazy Framework Loading...")
        
        results = {
            'test_name': 'lazy_framework_loading',
            'success': False,
            'metrics': {},
            'errors': []
        }
        
        try:
            # Import lazy loader
            from src.ui.utils.ai_framework_lazy_loader import (
                load_sklearn,
                load_optuna,
                ai_framework_loader
            )
            
            initial_memory = self.get_memory_usage()
            
            # Test loading sklearn (lighter framework)
            print("  🔄 Loading scikit-learn...")
            start_time = time.time()
            
            sklearn = load_sklearn()
            sklearn_load_time = time.time() - start_time
            sklearn_memory = self.get_memory_usage()
            
            sklearn_success = sklearn is not None
            sklearn_memory_increase = sklearn_memory - initial_memory
            
            # Test loading optuna (if available)
            print("  🔄 Loading Optuna...")
            optuna_start_time = time.time()
            
            optuna = load_optuna()
            optuna_load_time = time.time() - optuna_start_time
            optuna_memory = self.get_memory_usage()
            
            optuna_success = optuna is not None
            optuna_memory_increase = optuna_memory - sklearn_memory
            
            # Get memory report
            memory_report = ai_framework_loader.get_memory_usage_report()
            
            results['metrics'] = {
                'sklearn_load_time': sklearn_load_time,
                'sklearn_memory_increase_mb': sklearn_memory_increase,
                'sklearn_success': sklearn_success,
                'optuna_load_time': optuna_load_time,
                'optuna_memory_increase_mb': optuna_memory_increase,
                'optuna_success': optuna_success,
                'total_memory_increase_mb': optuna_memory - initial_memory,
                'memory_report': memory_report
            }
            
            # Success criteria: Successful loading, reasonable memory usage
            loading_successful = sklearn_success  # At least sklearn should work
            memory_reasonable = (optuna_memory - initial_memory) < 100.0  # Less than 100MB
            
            results['success'] = loading_successful and memory_reasonable
            
            print(f"  📊 Scikit-learn: {'✅' if sklearn_success else '❌'} ({sklearn_load_time:.2f}s, +{sklearn_memory_increase:.1f}MB)")
            print(f"  📊 Optuna: {'✅' if optuna_success else '❌'} ({optuna_load_time:.2f}s, +{optuna_memory_increase:.1f}MB)")
            print(f"  📊 Total memory increase: {optuna_memory - initial_memory:.1f}MB")
            print(f"  🎯 Loading successful: {'✅' if loading_successful else '❌'}")
            print(f"  🎯 Memory reasonable (<100MB): {'✅' if memory_reasonable else '❌'}")
            
        except Exception as e:
            results['errors'].append(f"Lazy framework loading test failed: {e}")
            print(f"  ❌ Test failed: {e}")
            
        return results
    
    def test_memory_optimization_effectiveness(self) -> Dict:
        """Test overall memory optimization effectiveness"""
        print("\n🔍 Testing Memory Optimization Effectiveness...")
        
        results = {
            'test_name': 'memory_optimization',
            'success': False,
            'metrics': {},
            'errors': []
        }
        
        try:
            # Compare with Phase 2 baseline
            phase2_memory_increase = 315.1  # From Phase 2 results
            phase3_target = 200.0  # Target memory increase
            
            # Test current memory usage with lazy loading
            initial_memory = self.get_memory_usage()
            
            # Load data management page with lazy loading
            from src.ui.pages.data_management import get_ai_modules
            
            ai_modules = get_ai_modules()
            
            final_memory = self.get_memory_usage()
            current_memory_increase = final_memory - initial_memory
            
            # Calculate improvement
            memory_improvement = phase2_memory_increase - current_memory_increase
            improvement_percentage = (memory_improvement / phase2_memory_increase) * 100
            
            # Check if target is met
            target_met = current_memory_increase < phase3_target
            
            results['metrics'] = {
                'phase2_memory_increase_mb': phase2_memory_increase,
                'phase3_memory_increase_mb': current_memory_increase,
                'memory_improvement_mb': memory_improvement,
                'improvement_percentage': improvement_percentage,
                'target_memory_mb': phase3_target,
                'target_met': target_met,
                'ai_modules_available': ai_modules is not None
            }
            
            results['success'] = target_met
            
            print(f"  📊 Phase 2 memory increase: {phase2_memory_increase:.1f}MB")
            print(f"  📊 Phase 3 memory increase: {current_memory_increase:.1f}MB")
            print(f"  📊 Memory improvement: {memory_improvement:.1f}MB ({improvement_percentage:.1f}%)")
            print(f"  🎯 Target (<200MB): {'✅ MET' if target_met else '❌ NOT MET'}")
            
        except Exception as e:
            results['errors'].append(f"Memory optimization test failed: {e}")
            print(f"  ❌ Test failed: {e}")
            
        return results
    
    def run_comprehensive_test(self) -> Dict:
        """Run comprehensive Phase 3 performance tests"""
        print("🚀 Phase 3 Performance Optimization Test")
        print("="*60)
        print(f"📂 Project root: {self.project_root}")
        print(f"💾 Initial memory: {self.get_memory_usage():.1f}MB")
        
        results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'phase': 'Phase 3',
            'initial_memory_mb': self.get_memory_usage(),
            'tests': {}
        }
        
        # Run all tests
        test_methods = [
            self.test_baseline_memory_usage,
            self.test_framework_availability_detection,
            self.test_lazy_framework_loading,
            self.test_memory_optimization_effectiveness
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
        print("📈 PHASE 3 PERFORMANCE TEST SUMMARY")
        print("="*80)
        
        total_tests = len(results['tests'])
        successful_tests = len([t for t in results['tests'].values() if t.get('success', False)])
        
        print(f"\n📊 Test Results:")
        print(f"   • Total tests: {total_tests}")
        print(f"   • Successful tests: {successful_tests}")
        print(f"   • Success rate: {(successful_tests/total_tests)*100:.1f}%")
        
        # Phase 3 Success Criteria Check
        print(f"\n🎯 Phase 3 Success Criteria:")
        
        criteria_met = 0
        total_criteria = 4
        
        # Memory optimization criterion
        memory_test = results['tests'].get('memory_optimization', {})
        memory_target_met = memory_test.get('success', False)
        if memory_target_met:
            criteria_met += 1
        current_memory = memory_test.get('metrics', {}).get('phase3_memory_increase_mb', 999)
        print(f"   • Memory usage (<200MB): {current_memory:.1f}MB {'✅' if memory_target_met else '❌'}")
        
        # Framework availability criterion
        availability_test = results['tests'].get('framework_availability', {})
        availability_success = availability_test.get('success', False)
        if availability_success:
            criteria_met += 1
        available_count = availability_test.get('metrics', {}).get('available_frameworks', 0)
        print(f"   • Framework availability: {available_count} frameworks {'✅' if availability_success else '❌'}")
        
        # Lazy loading criterion
        lazy_test = results['tests'].get('lazy_framework_loading', {})
        lazy_success = lazy_test.get('success', False)
        if lazy_success:
            criteria_met += 1
        print(f"   • Lazy loading: {'✅ Working' if lazy_success else '❌ Failed'}")
        
        # Baseline memory criterion
        baseline_test = results['tests'].get('baseline_memory', {})
        baseline_success = baseline_test.get('success', False)
        if baseline_success:
            criteria_met += 1
        baseline_memory = baseline_test.get('metrics', {}).get('memory_increase_mb', 999)
        print(f"   • Baseline memory (<50MB): {baseline_memory:.1f}MB {'✅' if baseline_success else '❌'}")
        
        # Overall assessment
        success_rate = (criteria_met / total_criteria) * 100
        print(f"\n🏆 Overall Phase 3 Success Rate: {criteria_met}/{total_criteria} ({success_rate:.1f}%)")
        
        if success_rate >= 75:
            print("   🎉 EXCELLENT: Phase 3 optimization successful!")
        elif success_rate >= 50:
            print("   ✅ GOOD: Most Phase 3 targets met")
        else:
            print("   ⚠️ NEEDS IMPROVEMENT: Several targets not met")
    
    def save_results(self, results: Dict, filename: str = "phase3_performance_test_results.json"):
        """Save test results to file"""
        output_path = self.project_root / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Test results saved to: {output_path}")


def main():
    """Main function"""
    project_root = os.getcwd()
    
    tester = Phase3PerformanceTest(project_root)
    
    try:
        # Run comprehensive tests
        results = tester.run_comprehensive_test()
        
        # Print summary
        tester.print_summary(results)
        
        # Save results
        tester.save_results(results)
        
        print(f"\n✅ Phase 3 performance test complete!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
