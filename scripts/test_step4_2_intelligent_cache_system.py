#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步驟 4.2 智能快取系統測試腳本

此腳本用於測試智能快取系統的功能，包括：
1. 快取系統初始化測試
2. 基本快取操作測試
3. 快取策略測試
4. 快取統計和監控測試
5. 快取預熱和優化測試

Usage:
    python scripts/test_step4_2_intelligent_cache_system.py
"""

import sys
import os
import logging
import time
import random
from datetime import datetime, timedelta
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/test_step4_2_intelligent_cache_system.log')
    ]
)
logger = logging.getLogger(__name__)

# 確保日誌目錄存在
os.makedirs('logs', exist_ok=True)

def test_cache_initialization():
    """測試快取系統初始化"""
    logger.info("=== 測試快取系統初始化 ===")
    
    try:
        from src.core.intelligent_cache_system import IntelligentCacheSystem, CacheConfig, CacheStrategy
        
        # 測試預設初始化
        cache1 = IntelligentCacheSystem()
        assert cache1.config.max_size == 1000
        assert cache1.config.strategy == CacheStrategy.LRU
        
        # 測試自定義配置初始化
        config = CacheConfig(
            max_size=500,
            max_memory=50 * 1024 * 1024,  # 50MB
            strategy=CacheStrategy.LFU,
            default_ttl=1800
        )
        cache2 = IntelligentCacheSystem(config)
        assert cache2.config.max_size == 500
        assert cache2.config.strategy == CacheStrategy.LFU
        assert cache2.config.default_ttl == 1800
        
        logger.info("快取系統初始化測試通過")
        logger.info("  預設配置: 最大大小=%d, 策略=%s", cache1.config.max_size, cache1.config.strategy.value)
        logger.info("  自定義配置: 最大大小=%d, 策略=%s", cache2.config.max_size, cache2.config.strategy.value)
        
        # 關閉第一個快取
        cache1.shutdown()
        
        return True, cache2
        
    except Exception as e:
        logger.error("快取系統初始化測試失敗: %s", e)
        return False, None


def test_basic_cache_operations(cache):
    """測試基本快取操作"""
    logger.info("=== 測試基本快取操作 ===")
    
    try:
        # 測試設定和獲取
        success = cache.set('key1', 'value1', ttl=3600)
        assert success
        
        value = cache.get('key1')
        assert value == 'value1'
        
        # 測試不存在的鍵
        missing_value = cache.get('non_existent_key', 'default')
        assert missing_value == 'default'
        
        # 測試存在性檢查
        assert cache.exists('key1')
        assert not cache.exists('non_existent_key')
        
        # 測試不同資料類型
        cache.set('int_key', 42)
        cache.set('list_key', [1, 2, 3, 4, 5])
        cache.set('dict_key', {'name': 'test', 'value': 100})
        
        assert cache.get('int_key') == 42
        assert cache.get('list_key') == [1, 2, 3, 4, 5]
        assert cache.get('dict_key')['name'] == 'test'
        
        # 測試刪除
        deleted = cache.delete('key1')
        assert deleted
        assert not cache.exists('key1')
        
        logger.info("基本快取操作測試通過")
        return True
        
    except Exception as e:
        logger.error("基本快取操作測試失敗: %s", e)
        return False


def test_cache_expiration(cache):
    """測試快取過期功能"""
    logger.info("=== 測試快取過期功能 ===")
    
    try:
        # 設定短期快取
        cache.set('short_lived', 'expires_soon', ttl=2)  # 2秒過期
        
        # 立即檢查
        assert cache.exists('short_lived')
        assert cache.get('short_lived') == 'expires_soon'
        
        # 等待過期
        time.sleep(3)
        
        # 檢查是否過期
        assert not cache.exists('short_lived')
        assert cache.get('short_lived', 'expired') == 'expired'
        
        logger.info("快取過期功能測試通過")
        return True
        
    except Exception as e:
        logger.error("快取過期功能測試失敗: %s", e)
        return False


def test_cache_tags(cache):
    """測試快取標籤功能"""
    logger.info("=== 測試快取標籤功能 ===")
    
    try:
        # 設定帶標籤的快取
        cache.set('user:1', {'name': 'Alice', 'age': 25}, tags={'user', 'profile'})
        cache.set('user:2', {'name': 'Bob', 'age': 30}, tags={'user', 'profile'})
        cache.set('post:1', {'title': 'Hello World', 'author': 'Alice'}, tags={'post', 'content'})
        cache.set('post:2', {'title': 'Python Tips', 'author': 'Bob'}, tags={'post', 'content'})
        
        # 根據標籤獲取
        user_data = cache.get_by_tags({'user'})
        assert len(user_data) == 2
        assert 'user:1' in user_data
        assert 'user:2' in user_data
        
        post_data = cache.get_by_tags({'post'})
        assert len(post_data) == 2
        assert 'post:1' in post_data
        assert 'post:2' in post_data
        
        # 根據標籤失效
        invalidated = cache.invalidate_by_tags({'user'})
        assert invalidated == 2
        
        # 檢查失效結果
        assert not cache.exists('user:1')
        assert not cache.exists('user:2')
        assert cache.exists('post:1')  # 不同標籤，應該還存在
        
        logger.info("快取標籤功能測試通過")
        return True
        
    except Exception as e:
        logger.error("快取標籤功能測試失敗: %s", e)
        return False


def test_cache_statistics(cache):
    """測試快取統計功能"""
    logger.info("=== 測試快取統計功能 ===")
    
    try:
        # 清空快取
        cache.clear()

        # 記錄清空前的統計
        initial_stats = cache.get_stats()
        initial_sets = initial_stats.sets
        initial_hits = initial_stats.hits
        initial_misses = initial_stats.misses

        # 執行一些操作來產生統計資料
        for i in range(10):
            cache.set(f'stat_key_{i}', f'value_{i}')

        # 產生一些命中和失誤
        for i in range(5):
            cache.get(f'stat_key_{i}')  # 命中

        for i in range(3):
            cache.get(f'missing_key_{i}', 'default')  # 失誤

        # 獲取統計資訊
        stats = cache.get_stats()

        # 驗證統計資料（考慮累積統計）
        assert stats.sets >= initial_sets + 10
        assert stats.hits >= initial_hits + 5
        assert stats.misses >= initial_misses + 3
        assert stats.entry_count == 10  # 當前條目數應該是10
        assert stats.hit_rate > 0
        assert stats.miss_rate > 0
        
        logger.info("快取統計資訊:")
        logger.info("  設定操作: %d", stats.sets)
        logger.info("  命中次數: %d", stats.hits)
        logger.info("  失誤次數: %d", stats.misses)
        logger.info("  條目數量: %d", stats.entry_count)
        logger.info("  命中率: %.2f%%", stats.hit_rate * 100)
        logger.info("  失誤率: %.2f%%", stats.miss_rate * 100)
        
        # 測試記憶體使用情況
        memory_usage = cache.get_memory_usage()
        assert 'total_size_bytes' in memory_usage
        assert 'entry_count' in memory_usage
        assert memory_usage['entry_count'] == 10
        
        logger.info("記憶體使用情況:")
        logger.info("  總大小: %.2f MB", memory_usage['total_size_mb'])
        logger.info("  條目數量: %d", memory_usage['entry_count'])
        logger.info("  平均條目大小: %.2f bytes", memory_usage['average_entry_size'])
        
        logger.info("快取統計功能測試通過")
        return True

    except Exception as e:
        import traceback
        logger.error("快取統計功能測試失敗: %s", e)
        logger.error("詳細錯誤: %s", traceback.format_exc())
        return False


def test_cache_eviction(cache):
    """測試快取淘汰功能"""
    logger.info("=== 測試快取淘汰功能 ===")
    
    try:
        # 清空快取
        cache.clear()
        
        # 設定較小的最大大小來測試淘汰
        original_max_size = cache.config.max_size
        cache.config.max_size = 5
        
        # 添加超過最大大小的條目
        for i in range(8):
            cache.set(f'evict_key_{i}', f'value_{i}')
        
        # 檢查是否有條目被淘汰
        keys = cache.get_keys()
        assert len(keys) <= 5  # 不應該超過最大大小
        
        # 檢查統計中的淘汰次數
        stats = cache.get_stats()
        assert stats.evictions > 0
        
        logger.info("淘汰統計: %d 次淘汰", stats.evictions)
        logger.info("當前條目數: %d", len(keys))
        
        # 恢復原始設定
        cache.config.max_size = original_max_size
        
        logger.info("快取淘汰功能測試通過")
        return True
        
    except Exception as e:
        logger.error("快取淘汰功能測試失敗: %s", e)
        return False


def test_cache_preload(cache):
    """測試快取預熱功能"""
    logger.info("=== 測試快取預熱功能 ===")
    
    try:
        # 定義預熱函數
        def preload_user_data(cache_instance):
            """預熱用戶資料"""
            users = [
                {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
                {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
                {'id': 3, 'name': 'Charlie', 'email': 'charlie@example.com'}
            ]
            
            for user in users:
                cache_instance.set(f"preload_user:{user['id']}", user, ttl=7200)
        
        # 註冊預熱函數
        cache.register_preload_function('user_data', preload_user_data, interval=3600)
        
        # 手動執行預熱（模擬）
        preload_user_data(cache)
        
        # 檢查預熱結果
        assert cache.exists('preload_user:1')
        assert cache.exists('preload_user:2')
        assert cache.exists('preload_user:3')
        
        user1 = cache.get('preload_user:1')
        assert user1['name'] == 'Alice'
        
        logger.info("快取預熱功能測試通過")
        return True
        
    except Exception as e:
        logger.error("快取預熱功能測試失敗: %s", e)
        return False


def test_cache_optimization(cache):
    """測試快取優化功能"""
    logger.info("=== 測試快取優化功能 ===")
    
    try:
        # 添加一些測試資料
        for i in range(20):
            cache.set(f'opt_key_{i}', f'value_{i}', ttl=1 if i % 5 == 0 else 3600)
        
        # 等待部分條目過期
        time.sleep(2)
        
        # 執行優化
        cache.optimize_cache()
        
        # 檢查優化結果
        stats = cache.get_stats()
        logger.info("優化後統計:")
        logger.info("  條目數量: %d", stats.entry_count)
        logger.info("  過期清理: %d", stats.expires)
        
        logger.info("快取優化功能測試通過")
        return True
        
    except Exception as e:
        logger.error("快取優化功能測試失敗: %s", e)
        return False


def main():
    """主測試函數"""
    logger.info("開始執行步驟 4.2 智能快取系統測試")
    
    # 初始化快取系統
    init_success, cache = test_cache_initialization()
    if not init_success:
        logger.error("快取系統初始化失敗，終止測試")
        return False
    
    test_results = []
    
    # 執行各項測試
    test_functions = [
        ("基本快取操作", lambda: test_basic_cache_operations(cache)),
        ("快取過期功能", lambda: test_cache_expiration(cache)),
        ("快取標籤功能", lambda: test_cache_tags(cache)),
        ("快取統計功能", lambda: test_cache_statistics(cache)),
        ("快取淘汰功能", lambda: test_cache_eviction(cache)),
        ("快取預熱功能", lambda: test_cache_preload(cache)),
        ("快取優化功能", lambda: test_cache_optimization(cache))
    ]
    
    for test_name, test_func in test_functions:
        logger.info("\n" + "="*50)
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            logger.error("測試 %s 時發生未預期錯誤: %s", test_name, e)
            test_results.append((test_name, False))
    
    # 關閉快取系統
    cache.shutdown()
    
    # 輸出測試結果摘要
    logger.info("\n" + "="*50)
    logger.info("測試結果摘要:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "通過" if result else "失敗"
        logger.info("  %s: %s", test_name, status)
        if result:
            passed += 1
    
    logger.info("\n總計: %d/%d 測試通過 (%.1f%%)", passed, total, (passed/total)*100)
    
    if passed == total:
        logger.info("所有測試都通過！步驟 4.2 智能快取系統實現成功")
        return True
    else:
        logger.warning("部分測試失敗，需要進一步檢查和修正")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
