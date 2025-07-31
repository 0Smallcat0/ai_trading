#!/usr/bin/env python3
"""
AI Lazy Loader - Phase 2 Performance Optimization

Advanced lazy loading system specifically designed for heavy AI modules.
Implements asyncio patterns, progress indicators, and background preloading
to reduce the 15.6s AI module import time to <5s target.

Features:
- Asynchronous AI module loading with progress indicators
- Background preloading based on user behavior patterns
- Memory-efficient module caching with automatic cleanup
- Fallback mechanisms for failed imports
- Performance monitoring and metrics collection
"""

import asyncio
import time
import threading
import logging
from typing import Dict, Any, Optional, Callable, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st

logger = logging.getLogger(__name__)


@dataclass
class AIModuleInfo:
    """AI module information and metadata"""
    module_name: str
    import_path: str
    loader_func: Callable
    priority: int = 5
    estimated_load_time: float = 1.0
    dependencies: List[str] = field(default_factory=list)
    fallback_available: bool = False
    last_used: Optional[datetime] = None
    load_count: int = 0
    avg_load_time: float = 0.0
    memory_usage: float = 0.0


class AILazyLoader:
    """Advanced lazy loader for AI modules with async support"""
    
    def __init__(self, max_workers: int = 3, cache_size: int = 10):
        self.max_workers = max_workers
        self.cache_size = cache_size
        
        # Module registry and cache
        self.ai_modules: Dict[str, AIModuleInfo] = {}
        self.module_cache: Dict[str, Any] = {}
        self.loading_futures: Dict[str, asyncio.Future] = {}
        
        # Performance tracking
        self.load_metrics = {
            'total_loads': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'failed_loads': 0,
            'avg_load_time': 0.0,
            'memory_saved': 0.0
        }
        
        # User behavior tracking for preloading
        self.usage_patterns: Dict[str, List[datetime]] = {}
        self.preload_candidates: Set[str] = set()
        
        # Thread pool for background operations
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.background_tasks: Set[asyncio.Task] = set()
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        logger.info(f"AI Lazy Loader initialized with {max_workers} workers")
    
    def register_ai_module(
        self,
        module_name: str,
        import_path: str,
        loader_func: Callable,
        priority: int = 5,
        estimated_load_time: float = 1.0,
        dependencies: List[str] = None,
        fallback_available: bool = False
    ) -> None:
        """Register an AI module for lazy loading"""
        
        module_info = AIModuleInfo(
            module_name=module_name,
            import_path=import_path,
            loader_func=loader_func,
            priority=priority,
            estimated_load_time=estimated_load_time,
            dependencies=dependencies or [],
            fallback_available=fallback_available
        )
        
        with self._lock:
            self.ai_modules[module_name] = module_info
        
        logger.debug(f"Registered AI module: {module_name} (priority: {priority})")
    
    async def load_ai_module_async(
        self,
        module_name: str,
        show_progress: bool = True,
        timeout: float = 30.0
    ) -> Optional[Any]:
        """Asynchronously load an AI module with progress indication"""
        
        if module_name not in self.ai_modules:
            logger.error(f"AI module {module_name} not registered")
            return None
        
        # Check cache first
        with self._lock:
            if module_name in self.module_cache:
                self.load_metrics['cache_hits'] += 1
                self._update_usage_pattern(module_name)
                return self.module_cache[module_name]
        
        # Check if already loading
        if module_name in self.loading_futures:
            logger.debug(f"AI module {module_name} already loading, waiting...")
            try:
                return await asyncio.wait_for(
                    self.loading_futures[module_name], 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout loading AI module {module_name}")
                return None
        
        # Start loading
        module_info = self.ai_modules[module_name]
        
        # Create progress indicator
        progress_container = None
        progress_bar = None
        status_text = None
        
        if show_progress and 'streamlit' in globals():
            progress_container = st.empty()
            with progress_container.container():
                st.info(f"🤖 Loading AI module: {module_name}")
                progress_bar = st.progress(0)
                status_text = st.empty()
        
        # Create loading future
        future = asyncio.create_task(
            self._load_module_with_progress(
                module_info, progress_bar, status_text, timeout
            )
        )
        
        self.loading_futures[module_name] = future
        
        try:
            # Wait for loading to complete
            result = await future
            
            # Update cache and metrics
            with self._lock:
                if result is not None:
                    self.module_cache[module_name] = result
                    self._cleanup_cache_if_needed()
                    self.load_metrics['cache_misses'] += 1
                    self.load_metrics['total_loads'] += 1
                    self._update_usage_pattern(module_name)
                else:
                    self.load_metrics['failed_loads'] += 1
            
            # Clear progress indicator
            if progress_container:
                progress_container.empty()
            
            return result
            
        except Exception as e:
            logger.error(f"Error loading AI module {module_name}: {e}")
            if progress_container:
                progress_container.error(f"❌ Failed to load {module_name}: {str(e)}")
            return None
            
        finally:
            # Cleanup
            if module_name in self.loading_futures:
                del self.loading_futures[module_name]
    
    async def _load_module_with_progress(
        self,
        module_info: AIModuleInfo,
        progress_bar: Optional[Any],
        status_text: Optional[Any],
        timeout: float
    ) -> Optional[Any]:
        """Load module with progress updates"""
        
        start_time = time.time()
        
        try:
            # Update progress: Starting
            if progress_bar:
                progress_bar.progress(0.1)
            if status_text:
                status_text.text("Initializing...")
            
            # Check dependencies
            if progress_bar:
                progress_bar.progress(0.2)
            if status_text:
                status_text.text("Checking dependencies...")
            
            await asyncio.sleep(0.1)  # Allow UI update
            
            # Load dependencies first
            for dep in module_info.dependencies:
                if dep in self.ai_modules:
                    await self.load_ai_module_async(dep, show_progress=False)
            
            # Update progress: Loading
            if progress_bar:
                progress_bar.progress(0.5)
            if status_text:
                status_text.text(f"Loading {module_info.module_name}...")
            
            # Execute the actual loading in thread pool
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    self.executor,
                    module_info.loader_func
                ),
                timeout=timeout
            )
            
            # Update progress: Finalizing
            if progress_bar:
                progress_bar.progress(0.9)
            if status_text:
                status_text.text("Finalizing...")
            
            await asyncio.sleep(0.1)  # Allow UI update
            
            # Update module statistics
            load_time = time.time() - start_time
            with self._lock:
                module_info.last_used = datetime.now()
                module_info.load_count += 1
                module_info.avg_load_time = (
                    (module_info.avg_load_time * (module_info.load_count - 1) + load_time)
                    / module_info.load_count
                )
            
            # Complete progress
            if progress_bar:
                progress_bar.progress(1.0)
            if status_text:
                status_text.text("✅ Loaded successfully!")
            
            logger.info(f"AI module {module_info.module_name} loaded in {load_time:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout loading {module_info.module_name}")
            if status_text:
                status_text.text("❌ Loading timeout")
            return None
            
        except Exception as e:
            logger.error(f"Error loading {module_info.module_name}: {e}")
            if status_text:
                status_text.text(f"❌ Error: {str(e)}")
            
            # Try fallback if available
            if module_info.fallback_available:
                if status_text:
                    status_text.text("🔄 Trying fallback...")
                return await self._try_fallback(module_info)
            
            return None
    
    async def _try_fallback(self, module_info: AIModuleInfo) -> Optional[Any]:
        """Try fallback loading mechanism"""
        try:
            # Implement fallback logic here
            logger.info(f"Using fallback for {module_info.module_name}")
            return None  # Placeholder for fallback implementation
        except Exception as e:
            logger.error(f"Fallback failed for {module_info.module_name}: {e}")
            return None
    
    def _update_usage_pattern(self, module_name: str) -> None:
        """Update usage patterns for preloading optimization"""
        now = datetime.now()
        
        if module_name not in self.usage_patterns:
            self.usage_patterns[module_name] = []
        
        self.usage_patterns[module_name].append(now)
        
        # Keep only recent usage (last 7 days)
        cutoff = now - timedelta(days=7)
        self.usage_patterns[module_name] = [
            usage_time for usage_time in self.usage_patterns[module_name]
            if usage_time > cutoff
        ]
        
        # Update preload candidates based on usage frequency
        recent_usage_count = len(self.usage_patterns[module_name])
        if recent_usage_count >= 3:  # Used 3+ times in last 7 days
            self.preload_candidates.add(module_name)
    
    def _cleanup_cache_if_needed(self) -> None:
        """Clean up cache if it exceeds size limit"""
        if len(self.module_cache) <= self.cache_size:
            return
        
        # Remove least recently used modules
        module_usage = []
        for module_name in self.module_cache:
            if module_name in self.ai_modules:
                last_used = self.ai_modules[module_name].last_used
                module_usage.append((module_name, last_used or datetime.min))
        
        # Sort by last used time and remove oldest
        module_usage.sort(key=lambda x: x[1])
        modules_to_remove = len(self.module_cache) - self.cache_size + 1
        
        for i in range(modules_to_remove):
            module_to_remove = module_usage[i][0]
            del self.module_cache[module_to_remove]
            logger.debug(f"Removed {module_to_remove} from cache (LRU cleanup)")
    
    async def preload_frequent_modules(self) -> None:
        """Preload frequently used modules in background"""
        if not self.preload_candidates:
            return
        
        logger.info(f"Preloading {len(self.preload_candidates)} frequent AI modules")
        
        # Sort by priority and usage frequency
        modules_to_preload = []
        for module_name in self.preload_candidates:
            if module_name not in self.module_cache:
                module_info = self.ai_modules[module_name]
                usage_count = len(self.usage_patterns.get(module_name, []))
                modules_to_preload.append((module_name, module_info.priority, usage_count))
        
        # Sort by priority (higher first) then usage count (higher first)
        modules_to_preload.sort(key=lambda x: (-x[1], -x[2]))
        
        # Preload top modules
        preload_tasks = []
        for module_name, _, _ in modules_to_preload[:3]:  # Limit to top 3
            task = asyncio.create_task(
                self.load_ai_module_async(module_name, show_progress=False)
            )
            preload_tasks.append(task)
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)
        
        if preload_tasks:
            await asyncio.gather(*preload_tasks, return_exceptions=True)
    
    def get_load_metrics(self) -> Dict[str, Any]:
        """Get loading performance metrics"""
        with self._lock:
            total_loads = self.load_metrics['total_loads']
            if total_loads > 0:
                cache_hit_rate = self.load_metrics['cache_hits'] / total_loads
                failure_rate = self.load_metrics['failed_loads'] / total_loads
            else:
                cache_hit_rate = 0.0
                failure_rate = 0.0
            
            return {
                **self.load_metrics,
                'cache_hit_rate': cache_hit_rate,
                'failure_rate': failure_rate,
                'cached_modules': len(self.module_cache),
                'registered_modules': len(self.ai_modules),
                'preload_candidates': len(self.preload_candidates)
            }
    
    def cleanup(self) -> None:
        """Cleanup resources"""
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Shutdown executor
        self.executor.shutdown(wait=False)
        
        logger.info("AI Lazy Loader cleanup completed")


# Global instance
ai_lazy_loader = AILazyLoader()


def register_ai_module(
    module_name: str,
    import_path: str,
    loader_func: Callable,
    **kwargs
) -> None:
    """Convenience function to register AI module"""
    ai_lazy_loader.register_ai_module(
        module_name, import_path, loader_func, **kwargs
    )


async def load_ai_module(module_name: str, **kwargs) -> Optional[Any]:
    """Convenience function to load AI module"""
    return await ai_lazy_loader.load_ai_module_async(module_name, **kwargs)
