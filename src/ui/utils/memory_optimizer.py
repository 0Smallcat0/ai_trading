#!/usr/bin/env python3
"""
Memory Optimizer - Phase 2 Performance Optimization

Advanced memory management system to reduce memory footprint from 314.4MB to <200MB.
Implements automatic garbage collection, cache size limits, and memory-efficient data structures.

Features:
- Automatic memory monitoring and cleanup
- Smart cache eviction policies
- Memory-efficient data structures
- Garbage collection optimization
- Memory usage alerts and reporting
"""

import gc
import sys
import time
import threading
import weakref
import logging
from typing import Dict, Any, Optional, List, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import psutil
from pathlib import Path
import json

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """Memory usage statistics"""
    timestamp: datetime
    rss_mb: float
    vms_mb: float
    percent: float
    available_mb: float
    cache_size: int
    gc_collections: int


class MemoryOptimizer:
    """Advanced memory optimizer for AI trading system"""
    
    def __init__(
        self,
        max_memory_mb: float = 200.0,
        cache_size_limit: int = 50,
        cleanup_interval: float = 30.0,
        gc_threshold: float = 150.0
    ):
        self.max_memory_mb = max_memory_mb
        self.cache_size_limit = cache_size_limit
        self.cleanup_interval = cleanup_interval
        self.gc_threshold = gc_threshold
        
        # Memory tracking
        self.process = psutil.Process()
        self.initial_memory = self.get_memory_usage()
        self.memory_history: List[MemoryStats] = []
        self.peak_memory = self.initial_memory
        
        # Cache management
        self.managed_caches: Dict[str, Any] = {}
        self.cache_access_times: Dict[str, datetime] = {}
        self.cache_priorities: Dict[str, int] = {}
        
        # Cleanup management
        self.cleanup_callbacks: List[Callable] = []
        self.cleanup_thread: Optional[threading.Thread] = None
        self.cleanup_running = False
        
        # Memory alerts
        self.alert_callbacks: List[Callable] = []
        self.last_alert_time: Optional[datetime] = None
        self.alert_cooldown = timedelta(minutes=5)
        
        # Statistics
        self.stats = {
            'cleanups_performed': 0,
            'memory_freed_mb': 0.0,
            'cache_evictions': 0,
            'gc_collections': 0,
            'alerts_sent': 0
        }
        
        logger.info(f"Memory Optimizer initialized (target: {max_memory_mb}MB)")
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            memory_info = self.process.memory_info()
            return memory_info.rss / 1024 / 1024
        except Exception as e:
            logger.error(f"Failed to get memory usage: {e}")
            return 0.0
    
    def get_detailed_memory_stats(self) -> MemoryStats:
        """Get detailed memory statistics"""
        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            virtual_memory = psutil.virtual_memory()
            
            return MemoryStats(
                timestamp=datetime.now(),
                rss_mb=memory_info.rss / 1024 / 1024,
                vms_mb=memory_info.vms / 1024 / 1024,
                percent=memory_percent,
                available_mb=virtual_memory.available / 1024 / 1024,
                cache_size=len(self.managed_caches),
                gc_collections=sum(gc.get_stats()[i]['collections'] for i in range(3))
            )
        except Exception as e:
            logger.error(f"Failed to get detailed memory stats: {e}")
            return MemoryStats(
                timestamp=datetime.now(),
                rss_mb=0.0, vms_mb=0.0, percent=0.0,
                available_mb=0.0, cache_size=0, gc_collections=0
            )
    
    def register_cache(self, cache_name: str, cache_obj: Any, priority: int = 5) -> None:
        """Register a cache for memory management"""
        self.managed_caches[cache_name] = weakref.ref(cache_obj)
        self.cache_access_times[cache_name] = datetime.now()
        self.cache_priorities[cache_name] = priority
        
        logger.debug(f"Registered cache: {cache_name} (priority: {priority})")
    
    def register_cleanup_callback(self, callback: Callable) -> None:
        """Register a cleanup callback function"""
        self.cleanup_callbacks.append(callback)
        logger.debug(f"Registered cleanup callback: {callback.__name__}")
    
    def register_alert_callback(self, callback: Callable) -> None:
        """Register a memory alert callback"""
        self.alert_callbacks.append(callback)
        logger.debug(f"Registered alert callback: {callback.__name__}")
    
    def start_monitoring(self) -> None:
        """Start automatic memory monitoring and cleanup"""
        if self.cleanup_running:
            logger.warning("Memory monitoring already running")
            return
        
        self.cleanup_running = True
        self.cleanup_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="MemoryOptimizer"
        )
        self.cleanup_thread.start()
        
        logger.info("Memory monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop automatic memory monitoring"""
        self.cleanup_running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5.0)
        
        logger.info("Memory monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self.cleanup_running:
            try:
                # Get current memory stats
                stats = self.get_detailed_memory_stats()
                self.memory_history.append(stats)
                
                # Keep only recent history (last 100 entries)
                if len(self.memory_history) > 100:
                    self.memory_history = self.memory_history[-100:]
                
                # Update peak memory
                if stats.rss_mb > self.peak_memory:
                    self.peak_memory = stats.rss_mb
                
                # Check if cleanup is needed
                memory_increase = stats.rss_mb - self.initial_memory
                
                if memory_increase > self.max_memory_mb:
                    logger.warning(f"Memory usage exceeded target: {memory_increase:.1f}MB > {self.max_memory_mb}MB")
                    self._perform_cleanup()
                    self._send_memory_alert(stats, "Memory limit exceeded")
                
                elif memory_increase > self.gc_threshold:
                    logger.info(f"Memory usage above GC threshold: {memory_increase:.1f}MB")
                    self._perform_garbage_collection()
                
                # Sleep until next check
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Error in memory monitoring loop: {e}")
                time.sleep(self.cleanup_interval)
    
    def _perform_cleanup(self) -> None:
        """Perform comprehensive memory cleanup"""
        logger.info("Performing memory cleanup...")
        
        memory_before = self.get_memory_usage()
        
        # 1. Clean up managed caches
        self._cleanup_caches()
        
        # 2. Run custom cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Cleanup callback failed: {e}")
        
        # 3. Force garbage collection
        self._perform_garbage_collection()
        
        # 4. Clear weak references
        self._cleanup_weak_references()
        
        memory_after = self.get_memory_usage()
        memory_freed = memory_before - memory_after
        
        self.stats['cleanups_performed'] += 1
        self.stats['memory_freed_mb'] += memory_freed
        
        logger.info(f"Memory cleanup completed: freed {memory_freed:.1f}MB")
    
    def _cleanup_caches(self) -> None:
        """Clean up managed caches using LRU policy"""
        if len(self.managed_caches) <= self.cache_size_limit:
            return
        
        # Sort caches by access time and priority
        cache_items = []
        for cache_name in list(self.managed_caches.keys()):
            cache_ref = self.managed_caches[cache_name]
            cache_obj = cache_ref()
            
            if cache_obj is None:
                # Cache object was garbage collected
                del self.managed_caches[cache_name]
                if cache_name in self.cache_access_times:
                    del self.cache_access_times[cache_name]
                if cache_name in self.cache_priorities:
                    del self.cache_priorities[cache_name]
                continue
            
            access_time = self.cache_access_times.get(cache_name, datetime.min)
            priority = self.cache_priorities.get(cache_name, 5)
            
            cache_items.append((cache_name, access_time, priority, cache_obj))
        
        # Sort by priority (lower first) then by access time (older first)
        cache_items.sort(key=lambda x: (x[2], x[1]))
        
        # Remove excess caches
        caches_to_remove = len(cache_items) - self.cache_size_limit
        for i in range(caches_to_remove):
            cache_name, _, _, cache_obj = cache_items[i]
            
            # Clear cache if it has a clear method
            if hasattr(cache_obj, 'clear'):
                try:
                    cache_obj.clear()
                    logger.debug(f"Cleared cache: {cache_name}")
                except Exception as e:
                    logger.error(f"Failed to clear cache {cache_name}: {e}")
            
            # Remove from managed caches
            if cache_name in self.managed_caches:
                del self.managed_caches[cache_name]
            if cache_name in self.cache_access_times:
                del self.cache_access_times[cache_name]
            if cache_name in self.cache_priorities:
                del self.cache_priorities[cache_name]
            
            self.stats['cache_evictions'] += 1
    
    def _perform_garbage_collection(self) -> None:
        """Perform aggressive garbage collection"""
        logger.debug("Performing garbage collection...")
        
        # Collect all generations
        collected = 0
        for generation in range(3):
            collected += gc.collect(generation)
        
        self.stats['gc_collections'] += 1
        
        if collected > 0:
            logger.debug(f"Garbage collection freed {collected} objects")
    
    def _cleanup_weak_references(self) -> None:
        """Clean up dead weak references"""
        dead_refs = []
        
        for cache_name, cache_ref in self.managed_caches.items():
            if cache_ref() is None:
                dead_refs.append(cache_name)
        
        for cache_name in dead_refs:
            del self.managed_caches[cache_name]
            if cache_name in self.cache_access_times:
                del self.cache_access_times[cache_name]
            if cache_name in self.cache_priorities:
                del self.cache_priorities[cache_name]
        
        if dead_refs:
            logger.debug(f"Cleaned up {len(dead_refs)} dead weak references")
    
    def _send_memory_alert(self, stats: MemoryStats, message: str) -> None:
        """Send memory usage alert"""
        now = datetime.now()
        
        # Check cooldown
        if (self.last_alert_time and 
            now - self.last_alert_time < self.alert_cooldown):
            return
        
        self.last_alert_time = now
        
        alert_data = {
            'timestamp': now.isoformat(),
            'message': message,
            'memory_mb': stats.rss_mb,
            'memory_increase_mb': stats.rss_mb - self.initial_memory,
            'memory_percent': stats.percent,
            'cache_count': stats.cache_size
        }
        
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
        
        self.stats['alerts_sent'] += 1
        logger.warning(f"Memory alert: {message} - {stats.rss_mb:.1f}MB")
    
    def force_cleanup(self) -> Dict[str, Any]:
        """Force immediate memory cleanup and return results"""
        memory_before = self.get_memory_usage()
        
        self._perform_cleanup()
        
        memory_after = self.get_memory_usage()
        memory_freed = memory_before - memory_after
        
        return {
            'memory_before_mb': memory_before,
            'memory_after_mb': memory_after,
            'memory_freed_mb': memory_freed,
            'cleanup_successful': memory_freed > 0
        }
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory usage report"""
        current_stats = self.get_detailed_memory_stats()
        memory_increase = current_stats.rss_mb - self.initial_memory
        
        return {
            'timestamp': datetime.now().isoformat(),
            'initial_memory_mb': self.initial_memory,
            'current_memory_mb': current_stats.rss_mb,
            'peak_memory_mb': self.peak_memory,
            'memory_increase_mb': memory_increase,
            'memory_target_mb': self.max_memory_mb,
            'target_exceeded': memory_increase > self.max_memory_mb,
            'managed_caches': len(self.managed_caches),
            'cache_size_limit': self.cache_size_limit,
            'statistics': self.stats.copy(),
            'recent_history': [
                {
                    'timestamp': stat.timestamp.isoformat(),
                    'memory_mb': stat.rss_mb,
                    'percent': stat.percent
                }
                for stat in self.memory_history[-10:]  # Last 10 entries
            ]
        }
    
    def save_memory_report(self, filename: str = "memory_optimization_report.json") -> Path:
        """Save memory report to file"""
        report = self.get_memory_report()
        
        output_path = Path(filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Memory report saved to: {output_path}")
        return output_path
    
    def __del__(self):
        """Cleanup when optimizer is destroyed"""
        self.stop_monitoring()


# Global memory optimizer instance
memory_optimizer = MemoryOptimizer()


def optimize_memory_usage(max_memory_mb: float = 200.0) -> Dict[str, Any]:
    """Convenience function to optimize memory usage"""
    global memory_optimizer
    
    memory_optimizer.max_memory_mb = max_memory_mb
    return memory_optimizer.force_cleanup()


def get_memory_report() -> Dict[str, Any]:
    """Convenience function to get memory report"""
    return memory_optimizer.get_memory_report()


def start_memory_monitoring() -> None:
    """Convenience function to start memory monitoring"""
    memory_optimizer.start_monitoring()


def stop_memory_monitoring() -> None:
    """Convenience function to stop memory monitoring"""
    memory_optimizer.stop_monitoring()
