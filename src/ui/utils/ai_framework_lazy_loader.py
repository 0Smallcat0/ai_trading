#!/usr/bin/env python3
"""
AI Framework Lazy Loader - Phase 3 Performance Optimization

Advanced lazy loading system specifically for heavy AI frameworks like TensorFlow and PyTorch.
Implements module-level lazy loading to reduce baseline memory usage by 100-150MB.

Features:
- Conditional imports that only load AI frameworks when requested
- Memory-efficient framework initialization
- Framework availability detection without loading
- Fallback mechanisms for unavailable frameworks
- Performance monitoring and memory tracking
"""

import sys
import time
import logging
import threading
import weakref
from typing import Dict, Any, Optional, Callable, List, Union
from dataclasses import dataclass
from datetime import datetime
import importlib.util
import psutil

logger = logging.getLogger(__name__)


@dataclass
class FrameworkInfo:
    """AI framework information and status"""
    name: str
    module_name: str
    is_available: bool = False
    is_loaded: bool = False
    load_time: float = 0.0
    memory_usage: float = 0.0
    version: Optional[str] = None
    error: Optional[str] = None
    last_used: Optional[datetime] = None


class AIFrameworkLazyLoader:
    """Lazy loader for heavy AI frameworks"""
    
    def __init__(self):
        self.frameworks: Dict[str, FrameworkInfo] = {}
        self.loaded_modules: Dict[str, Any] = {}
        self.load_callbacks: Dict[str, List[Callable]] = {}
        self.memory_tracker = psutil.Process()
        self._lock = threading.RLock()
        
        # Initialize framework registry
        self._register_frameworks()
        
        logger.info("AI Framework Lazy Loader initialized")
    
    def _register_frameworks(self) -> None:
        """Register known AI frameworks"""
        frameworks = [
            ("tensorflow", "tensorflow"),
            ("torch", "torch"),
            ("sklearn", "sklearn"),
            ("optuna", "optuna"),
            ("transformers", "transformers"),
            ("xgboost", "xgboost"),
            ("lightgbm", "lightgbm"),
        ]
        
        for name, module_name in frameworks:
            self.frameworks[name] = FrameworkInfo(
                name=name,
                module_name=module_name
            )
            self.load_callbacks[name] = []
    
    def is_framework_available(self, framework_name: str) -> bool:
        """Check if framework is available without loading it"""
        if framework_name not in self.frameworks:
            return False
        
        framework = self.frameworks[framework_name]
        
        # Return cached result if already checked
        if framework.is_available is not None:
            return framework.is_available
        
        # Check if module can be imported without actually importing
        try:
            spec = importlib.util.find_spec(framework.module_name)
            framework.is_available = spec is not None
            if not framework.is_available:
                framework.error = f"Module {framework.module_name} not found"
        except (ImportError, ModuleNotFoundError, ValueError) as e:
            framework.is_available = False
            framework.error = f"Module {framework.module_name} not found: {str(e)}"
        
        return framework.is_available
    
    def load_framework(self, framework_name: str, force_reload: bool = False) -> Optional[Any]:
        """Load AI framework on demand"""
        if framework_name not in self.frameworks:
            logger.error(f"Unknown framework: {framework_name}")
            return None
        
        framework = self.frameworks[framework_name]
        
        # Return cached module if already loaded
        if framework.is_loaded and not force_reload:
            framework.last_used = datetime.now()
            return self.loaded_modules.get(framework_name)
        
        # Check availability first
        if not self.is_framework_available(framework_name):
            logger.warning(f"Framework {framework_name} is not available: {framework.error}")
            return None
        
        # Load the framework
        return self._load_framework_impl(framework_name)
    
    def _load_framework_impl(self, framework_name: str) -> Optional[Any]:
        """Internal framework loading implementation"""
        framework = self.frameworks[framework_name]
        
        with self._lock:
            # Double-check if already loaded (thread safety)
            if framework.is_loaded:
                return self.loaded_modules.get(framework_name)
            
            logger.info(f"Loading AI framework: {framework_name}")
            
            start_time = time.time()
            initial_memory = self.memory_tracker.memory_info().rss / 1024 / 1024
            
            try:
                # Import the framework
                module = importlib.import_module(framework.module_name)
                
                # Store loaded module
                self.loaded_modules[framework_name] = module
                
                # Update framework info
                framework.is_loaded = True
                framework.load_time = time.time() - start_time
                framework.last_used = datetime.now()
                
                # Get version if available
                if hasattr(module, '__version__'):
                    framework.version = module.__version__
                
                # Calculate memory usage
                final_memory = self.memory_tracker.memory_info().rss / 1024 / 1024
                framework.memory_usage = final_memory - initial_memory
                
                logger.info(
                    f"Framework {framework_name} loaded successfully "
                    f"(time: {framework.load_time:.2f}s, memory: +{framework.memory_usage:.1f}MB)"
                )
                
                # Call load callbacks
                for callback in self.load_callbacks[framework_name]:
                    try:
                        callback(module)
                    except Exception as e:
                        logger.error(f"Load callback failed for {framework_name}: {e}")
                
                return module
                
            except Exception as e:
                framework.error = str(e)
                framework.load_time = time.time() - start_time
                logger.error(f"Failed to load framework {framework_name}: {e}")
                return None
    
    def get_framework_info(self, framework_name: str) -> Optional[FrameworkInfo]:
        """Get framework information"""
        return self.frameworks.get(framework_name)
    
    def get_all_frameworks_info(self) -> Dict[str, FrameworkInfo]:
        """Get information about all frameworks"""
        return self.frameworks.copy()
    
    def register_load_callback(self, framework_name: str, callback: Callable) -> None:
        """Register callback to be called when framework is loaded"""
        if framework_name in self.load_callbacks:
            self.load_callbacks[framework_name].append(callback)
        else:
            logger.warning(f"Unknown framework for callback: {framework_name}")
    
    def unload_framework(self, framework_name: str) -> bool:
        """Unload framework from memory (limited effectiveness in Python)"""
        if framework_name not in self.frameworks:
            return False
        
        framework = self.frameworks[framework_name]
        
        if not framework.is_loaded:
            return True
        
        try:
            # Remove from loaded modules
            if framework_name in self.loaded_modules:
                del self.loaded_modules[framework_name]
            
            # Remove from sys.modules (limited effectiveness)
            modules_to_remove = [
                name for name in sys.modules.keys()
                if name.startswith(framework.module_name)
            ]
            
            for module_name in modules_to_remove:
                del sys.modules[module_name]
            
            # Update framework info
            framework.is_loaded = False
            framework.last_used = None
            
            logger.info(f"Framework {framework_name} unloaded")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload framework {framework_name}: {e}")
            return False
    
    def get_memory_usage_report(self) -> Dict[str, Any]:
        """Get memory usage report for all frameworks"""
        total_memory = sum(
            fw.memory_usage for fw in self.frameworks.values()
            if fw.is_loaded
        )
        
        loaded_frameworks = {
            name: {
                'memory_mb': fw.memory_usage,
                'load_time': fw.load_time,
                'version': fw.version,
                'last_used': fw.last_used.isoformat() if fw.last_used else None
            }
            for name, fw in self.frameworks.values()
            if fw.is_loaded
        }
        
        return {
            'total_memory_mb': total_memory,
            'loaded_frameworks': loaded_frameworks,
            'available_frameworks': [
                name for name, fw in self.frameworks.items()
                if fw.is_available
            ],
            'unavailable_frameworks': [
                name for name, fw in self.frameworks.items()
                if fw.is_available is False
            ]
        }


# Global instance
ai_framework_loader = AIFrameworkLazyLoader()


# Convenience functions for common frameworks
def load_tensorflow(force_reload: bool = False) -> Optional[Any]:
    """Load TensorFlow framework"""
    return ai_framework_loader.load_framework("tensorflow", force_reload)


def load_torch(force_reload: bool = False) -> Optional[Any]:
    """Load PyTorch framework"""
    return ai_framework_loader.load_framework("torch", force_reload)


def load_sklearn(force_reload: bool = False) -> Optional[Any]:
    """Load scikit-learn framework"""
    return ai_framework_loader.load_framework("sklearn", force_reload)


def load_optuna(force_reload: bool = False) -> Optional[Any]:
    """Load Optuna framework"""
    return ai_framework_loader.load_framework("optuna", force_reload)


def is_tensorflow_available() -> bool:
    """Check if TensorFlow is available"""
    return ai_framework_loader.is_framework_available("tensorflow")


def is_torch_available() -> bool:
    """Check if PyTorch is available"""
    return ai_framework_loader.is_framework_available("torch")


def is_sklearn_available() -> bool:
    """Check if scikit-learn is available"""
    return ai_framework_loader.is_framework_available("sklearn")


def is_optuna_available() -> bool:
    """Check if Optuna is available"""
    return ai_framework_loader.is_framework_available("optuna")


def get_framework_memory_report() -> Dict[str, Any]:
    """Get memory usage report for all AI frameworks"""
    return ai_framework_loader.get_memory_usage_report()


# Framework-specific lazy loading decorators
def lazy_tensorflow(func: Callable) -> Callable:
    """Decorator to lazy load TensorFlow before function execution"""
    def wrapper(*args, **kwargs):
        tf = load_tensorflow()
        if tf is None:
            raise ImportError("TensorFlow is not available")
        return func(*args, **kwargs)
    return wrapper


def lazy_torch(func: Callable) -> Callable:
    """Decorator to lazy load PyTorch before function execution"""
    def wrapper(*args, **kwargs):
        torch = load_torch()
        if torch is None:
            raise ImportError("PyTorch is not available")
        return func(*args, **kwargs)
    return wrapper


def lazy_sklearn(func: Callable) -> Callable:
    """Decorator to lazy load scikit-learn before function execution"""
    def wrapper(*args, **kwargs):
        sklearn = load_sklearn()
        if sklearn is None:
            raise ImportError("scikit-learn is not available")
        return func(*args, **kwargs)
    return wrapper


# Context managers for temporary framework loading
class FrameworkContext:
    """Context manager for temporary framework loading"""
    
    def __init__(self, framework_name: str):
        self.framework_name = framework_name
        self.framework = None
    
    def __enter__(self):
        self.framework = ai_framework_loader.load_framework(self.framework_name)
        if self.framework is None:
            raise ImportError(f"Framework {self.framework_name} is not available")
        return self.framework
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Framework remains loaded for performance
        # Could implement unloading here if needed
        pass


def tensorflow_context():
    """Context manager for TensorFlow"""
    return FrameworkContext("tensorflow")


def torch_context():
    """Context manager for PyTorch"""
    return FrameworkContext("torch")


def sklearn_context():
    """Context manager for scikit-learn"""
    return FrameworkContext("sklearn")
