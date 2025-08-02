"""
記憶體分析器

此模組提供記憶體使用監控和洩漏檢測功能。
"""

import gc
import time
import threading
import tracemalloc
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import psutil
import sys

try:
    from memory_profiler import profile as memory_profile

    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False
    memory_profile = lambda func: func


@dataclass
class MemorySnapshot:
    """記憶體快照"""

    timestamp: datetime
    rss_memory: float  # MB
    vms_memory: float  # MB
    heap_size: float  # MB
    object_count: int
    gc_collections: Dict[int, int] = field(default_factory=dict)


@dataclass
class MemoryLeakResult:
    """記憶體洩漏檢測結果"""

    test_name: str
    duration: float
    initial_memory: float
    final_memory: float
    peak_memory: float
    memory_growth: float
    memory_growth_rate: float  # MB/hour
    leak_detected: bool
    snapshots: List[MemorySnapshot] = field(default_factory=list)
    top_allocations: List[Tuple[str, int, float]] = field(default_factory=list)


class MemoryProfiler:
    """記憶體分析器類"""

    def __init__(self, leak_threshold: float = 10.0):
        """
        初始化記憶體分析器

        Args:
            leak_threshold: 記憶體洩漏閾值（MB/hour）
        """
        self.leak_threshold = leak_threshold
        self.snapshots: List[MemorySnapshot] = []
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.start_time: Optional[datetime] = None
        self.process = psutil.Process()
        self.tracemalloc_started = False

    def start_monitoring(self, interval: float = 5.0):
        """
        開始記憶體監控

        Args:
            interval: 監控間隔（秒）
        """
        if self.is_monitoring:
            return

        # 啟動 tracemalloc
        if not self.tracemalloc_started:
            tracemalloc.start()
            self.tracemalloc_started = True

        self.is_monitoring = True
        self.start_time = datetime.now()
        self.snapshots = []

        # 強制垃圾回收
        gc.collect()

        # 記錄初始快照
        self._take_snapshot()

        # 啟動監控線程
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(interval,), daemon=True
        )
        self.monitor_thread.start()

    def stop_monitoring(self) -> MemoryLeakResult:
        """
        停止記憶體監控並返回結果

        Returns:
            MemoryLeakResult: 記憶體洩漏檢測結果
        """
        self.is_monitoring = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=10.0)

        # 強制垃圾回收並記錄最終快照
        gc.collect()
        self._take_snapshot()

        return self._analyze_memory_usage()

    def _monitor_loop(self, interval: float):
        """監控循環"""
        while self.is_monitoring:
            try:
                self._take_snapshot()
                time.sleep(interval)
            except Exception as e:
                print(f"記憶體監控錯誤: {e}")
                break

    def _take_snapshot(self):
        """拍攝記憶體快照"""
        try:
            # 獲取進程記憶體資訊
            memory_info = self.process.memory_info()
            rss_memory = memory_info.rss / 1024 / 1024  # MB
            vms_memory = memory_info.vms / 1024 / 1024  # MB

            # 獲取 Python 堆記憶體
            heap_size = sys.getsizeof(gc.get_objects()) / 1024 / 1024  # MB

            # 獲取物件計數
            object_count = len(gc.get_objects())

            # 獲取垃圾回收統計
            gc_stats = {}
            for i in range(3):
                gc_stats[i] = gc.get_count()[i]

            snapshot = MemorySnapshot(
                timestamp=datetime.now(),
                rss_memory=rss_memory,
                vms_memory=vms_memory,
                heap_size=heap_size,
                object_count=object_count,
                gc_collections=gc_stats,
            )

            self.snapshots.append(snapshot)

        except Exception as e:
            print(f"記憶體快照錯誤: {e}")

    def _analyze_memory_usage(self) -> MemoryLeakResult:
        """分析記憶體使用情況"""
        if len(self.snapshots) < 2:
            raise ValueError("記憶體快照不足，無法進行分析")

        if not self.start_time:
            raise ValueError("監控尚未開始")

        duration = (datetime.now() - self.start_time).total_seconds()

        # 計算記憶體統計
        initial_memory = self.snapshots[0].rss_memory
        final_memory = self.snapshots[-1].rss_memory
        peak_memory = max(snapshot.rss_memory for snapshot in self.snapshots)
        memory_growth = final_memory - initial_memory

        # 計算記憶體增長率（MB/hour）
        memory_growth_rate = (memory_growth / duration) * 3600 if duration > 0 else 0

        # 檢測記憶體洩漏
        leak_detected = memory_growth_rate > self.leak_threshold

        # 獲取記憶體分配統計
        top_allocations = self._get_top_allocations()

        return MemoryLeakResult(
            test_name="Memory Leak Test",
            duration=duration,
            initial_memory=initial_memory,
            final_memory=final_memory,
            peak_memory=peak_memory,
            memory_growth=memory_growth,
            memory_growth_rate=memory_growth_rate,
            leak_detected=leak_detected,
            snapshots=self.snapshots.copy(),
            top_allocations=top_allocations,
        )

    def _get_top_allocations(self, top_n: int = 10) -> List[Tuple[str, int, float]]:
        """
        獲取記憶體分配統計

        Args:
            top_n: 返回前 N 個分配

        Returns:
            List[Tuple[str, int, float]]: (檔案:行號, 計數, 大小MB)
        """
        if not self.tracemalloc_started:
            return []

        try:
            current, peak = tracemalloc.get_traced_memory()
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics("lineno")

            allocations = []
            for stat in top_stats[:top_n]:
                size_mb = stat.size / 1024 / 1024
                allocations.append(
                    (f"{stat.traceback.format()[0]}", stat.count, size_mb)
                )

            return allocations

        except Exception as e:
            print(f"獲取記憶體分配統計錯誤: {e}")
            return []

    @memory_profile
    def profile_function(self, func, *args, **kwargs):
        """
        分析函數的記憶體使用

        Args:
            func: 要分析的函數
            *args: 函數參數
            **kwargs: 函數關鍵字參數

        Returns:
            函數返回值
        """
        if not MEMORY_PROFILER_AVAILABLE:
            print("警告: memory_profiler 不可用，跳過詳細分析")
            return func(*args, **kwargs)

        return func(*args, **kwargs)

    def measure_memory_usage(self, func, *args, **kwargs) -> Tuple[Any, float, float]:
        """
        測量函數執行的記憶體使用

        Args:
            func: 要測量的函數
            *args: 函數參數
            **kwargs: 函數關鍵字參數

        Returns:
            Tuple[Any, float, float]: (返回值, 記憶體增長MB, 峰值記憶體MB)
        """
        # 強制垃圾回收
        gc.collect()

        # 記錄初始記憶體
        initial_memory = self.process.memory_info().rss / 1024 / 1024

        # 啟動 tracemalloc
        if not self.tracemalloc_started:
            tracemalloc.start()
            self.tracemalloc_started = True

        tracemalloc_start = tracemalloc.get_traced_memory()[0]

        try:
            # 執行函數
            result = func(*args, **kwargs)

            # 記錄最終記憶體
            final_memory = self.process.memory_info().rss / 1024 / 1024
            tracemalloc_current, tracemalloc_peak = tracemalloc.get_traced_memory()

            memory_growth = final_memory - initial_memory
            peak_memory_growth = (tracemalloc_peak - tracemalloc_start) / 1024 / 1024

            return result, memory_growth, peak_memory_growth

        except Exception as e:
            # 即使出錯也要記錄記憶體使用
            final_memory = self.process.memory_info().rss / 1024 / 1024
            memory_growth = final_memory - initial_memory
            raise e
        finally:
            # 強制垃圾回收
            gc.collect()

    def detect_memory_leaks_in_loop(
        self, func, iterations: int = 100, args: tuple = (), kwargs: dict = None
    ) -> MemoryLeakResult:
        """
        在循環中檢測記憶體洩漏

        Args:
            func: 要測試的函數
            iterations: 迭代次數
            args: 函數參數
            kwargs: 函數關鍵字參數

        Returns:
            MemoryLeakResult: 記憶體洩漏檢測結果
        """
        if kwargs is None:
            kwargs = {}

        self.start_monitoring(interval=1.0)

        try:
            for i in range(iterations):
                func(*args, **kwargs)

                # 每 10 次迭代強制垃圾回收
                if i % 10 == 0:
                    gc.collect()

                # 短暫暫停讓監控器記錄
                time.sleep(0.1)

        finally:
            result = self.stop_monitoring()
            result.test_name = f"Memory Leak Test ({iterations} iterations)"
            return result

    def reset(self):
        """重置分析器狀態"""
        self.snapshots.clear()
        self.is_monitoring = False
        self.start_time = None

        if self.tracemalloc_started:
            tracemalloc.stop()
            self.tracemalloc_started = False

        # 強制垃圾回收
        gc.collect()
