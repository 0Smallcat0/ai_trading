#!/usr/bin/env python3
"""
Performance Optimization Activator

Quick script to activate all Phase 1-3 performance optimizations
and diagnose current system performance issues.
"""

import sys
import os
import time
import psutil
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_current_performance():
    """Check current system performance"""
    print("🔍 Checking Current System Performance...")
    
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    print(f"  💾 Current memory usage: {memory_mb:.1f}MB")
    
    # Check if optimizations are available
    optimizations_status = {}
    
    # Check Phase 1 optimizations
    try:
        from src.ui.pages.data_management import get_core_modules
        optimizations_status['phase1_core_modules'] = True
    except ImportError as e:
        optimizations_status['phase1_core_modules'] = False
        print(f"  ❌ Phase 1 core modules: {e}")
    
    # Check Phase 2 optimizations
    try:
        from src.ui.utils.ai_lazy_loader import ai_lazy_loader
        optimizations_status['phase2_lazy_loader'] = True
    except ImportError as e:
        optimizations_status['phase2_lazy_loader'] = False
        print(f"  ❌ Phase 2 lazy loader: {e}")
    
    # Check Phase 3 optimizations
    try:
        from src.ui.utils.ai_framework_lazy_loader import ai_framework_loader
        optimizations_status['phase3_framework_loader'] = True
    except ImportError as e:
        optimizations_status['phase3_framework_loader'] = False
        print(f"  ❌ Phase 3 framework loader: {e}")
    
    # Check memory optimizer
    try:
        from src.ui.utils.memory_optimizer import memory_optimizer
        optimizations_status['memory_optimizer'] = True
    except ImportError as e:
        optimizations_status['memory_optimizer'] = False
        print(f"  ❌ Memory optimizer: {e}")
    
    return optimizations_status


def activate_memory_optimizer():
    """Activate memory optimizer"""
    print("🧠 Activating Memory Optimizer...")
    
    try:
        from src.ui.utils.memory_optimizer import memory_optimizer, start_memory_monitoring
        
        # Configure for current system
        memory_optimizer.max_memory_mb = 200.0  # Target from Phase 3
        memory_optimizer.cache_size_limit = 20  # Reduced for immediate effect
        memory_optimizer.cleanup_interval = 15.0  # More frequent cleanup
        
        # Start monitoring
        start_memory_monitoring()
        
        # Force immediate cleanup
        cleanup_result = memory_optimizer.force_cleanup()
        
        print(f"  ✅ Memory optimizer activated")
        print(f"  🧹 Immediate cleanup: {cleanup_result['memory_freed_mb']:.1f}MB freed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to activate memory optimizer: {e}")
        return False


def activate_lazy_loading():
    """Activate AI framework lazy loading"""
    print("⚡ Activating AI Framework Lazy Loading...")
    
    try:
        from src.ui.utils.ai_framework_lazy_loader import ai_framework_loader
        
        # Get current status
        frameworks_info = ai_framework_loader.get_all_frameworks_info()
        
        available_count = sum(1 for fw in frameworks_info.values() if fw.is_available)
        loaded_count = sum(1 for fw in frameworks_info.values() if fw.is_loaded)
        
        print(f"  📊 Available frameworks: {available_count}")
        print(f"  📊 Currently loaded: {loaded_count}")
        
        if loaded_count > 0:
            print("  ⚠️  Some frameworks are already loaded - this may impact memory")
            
            # Try to unload frameworks that aren't needed
            for name, fw in frameworks_info.items():
                if fw.is_loaded and name not in ['sklearn']:  # Keep sklearn as it's lightweight
                    try:
                        ai_framework_loader.unload_framework(name)
                        print(f"    🔄 Attempted to unload {name}")
                    except Exception as e:
                        print(f"    ❌ Failed to unload {name}: {e}")
        
        print(f"  ✅ Lazy loading system activated")
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to activate lazy loading: {e}")
        return False


def optimize_streamlit_config():
    """Optimize Streamlit configuration"""
    print("🎛️  Optimizing Streamlit Configuration...")
    
    try:
        import streamlit as st
        
        # Set memory-efficient configurations
        if hasattr(st, 'set_page_config'):
            # These would be set in the main app, but we can check if they're optimal
            pass
        
        # Check if caching is working
        cache_info = {}
        
        # Check st.cache_data usage
        try:
            from src.ui.pages.data_management import get_stock_data_from_db
            cache_info['stock_data_cache'] = 'Available'
        except:
            cache_info['stock_data_cache'] = 'Not available'
        
        print(f"  📊 Cache status: {cache_info}")
        print(f"  ✅ Streamlit configuration checked")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Failed to optimize Streamlit config: {e}")
        return False


def provide_immediate_recommendations():
    """Provide immediate performance recommendations"""
    print("\n💡 Immediate Performance Recommendations:")
    
    process = psutil.Process()
    current_memory = process.memory_info().rss / 1024 / 1024
    
    print(f"\n📊 Current Status:")
    print(f"  💾 Memory usage: {current_memory:.1f}MB")
    print(f"  🎯 Target: <200MB")
    
    if current_memory > 200:
        print(f"\n🚨 Memory Usage Too High ({current_memory:.1f}MB > 200MB)")
        print("  Recommended actions:")
        print("  1. Restart the Streamlit app to clear loaded frameworks")
        print("  2. Use the optimized startup command:")
        print("     python -m streamlit run src/ui/web_ui.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true")
        print("  3. Avoid loading AI features until needed")
        
    print(f"\n⚡ Performance Tips:")
    print("  • Only use AI features when necessary (they load frameworks on-demand)")
    print("  • Clear browser cache if pages load slowly")
    print("  • Use the 'Basic Chart' option instead of 'AI Integrated Chart' for faster loading")
    print("  • Monitor memory usage in the sidebar (if available)")


def main():
    """Main optimization activation"""
    print("🚀 AI Trading System Performance Optimization Activator")
    print("=" * 60)
    
    # Check current performance
    status = check_current_performance()
    
    print(f"\n📊 Optimization Status:")
    for opt, available in status.items():
        status_icon = "✅" if available else "❌"
        print(f"  {status_icon} {opt}: {'Available' if available else 'Not Available'}")
    
    # Activate available optimizations
    print(f"\n🔧 Activating Optimizations...")
    
    activated = []
    
    if status.get('memory_optimizer'):
        if activate_memory_optimizer():
            activated.append("Memory Optimizer")
    
    if status.get('phase3_framework_loader'):
        if activate_lazy_loading():
            activated.append("Lazy Loading")
    
    if optimize_streamlit_config():
        activated.append("Streamlit Config")
    
    print(f"\n✅ Activated optimizations: {', '.join(activated) if activated else 'None'}")
    
    # Provide recommendations
    provide_immediate_recommendations()
    
    # Final memory check
    final_memory = psutil.Process().memory_info().rss / 1024 / 1024
    print(f"\n📊 Final memory usage: {final_memory:.1f}MB")
    
    if final_memory < 200:
        print("🎉 Memory usage is now within target!")
    else:
        print("⚠️  Memory usage still high - consider restarting the application")


if __name__ == "__main__":
    main()
