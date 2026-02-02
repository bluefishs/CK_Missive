"""
API 快取管理器 - 使用記憶體快取
"""
import time
import json
import hashlib
from typing import Any, Optional, Dict, Callable
from functools import wraps
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

class MemoryCache:
    """記憶體快取實現"""

    def __init__(self, default_ttl: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """獲取快取值"""
        async with self._lock:
            if key not in self.cache:
                return None

            cache_entry = self.cache[key]

            # 檢查是否過期
            if time.time() > cache_entry['expires_at']:
                del self.cache[key]
                return None

            cache_entry['last_accessed'] = time.time()
            cache_entry['access_count'] += 1
            return cache_entry['value']

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """設置快取值"""
        if ttl is None:
            ttl = self.default_ttl

        async with self._lock:
            self.cache[key] = {
                'value': value,
                'created_at': time.time(),
                'expires_at': time.time() + ttl,
                'last_accessed': time.time(),
                'access_count': 1,
                'ttl': ttl
            }

    async def delete(self, key: str) -> bool:
        """刪除快取項目"""
        async with self._lock:
            return self.cache.pop(key, None) is not None

    async def clear(self, pattern: Optional[str] = None) -> int:
        """清空快取"""
        async with self._lock:
            if pattern is None:
                count = len(self.cache)
                self.cache.clear()
                return count
            else:
                # 簡單的模式匹配
                keys_to_delete = [key for key in self.cache.keys() if pattern in key]
                for key in keys_to_delete:
                    del self.cache[key]
                return len(keys_to_delete)

    async def cleanup_expired(self) -> int:
        """清理過期的快取項目"""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.cache.items()
                if current_time > entry['expires_at']
            ]

            for key in expired_keys:
                del self.cache[key]

            return len(expired_keys)

    async def get_stats(self) -> Dict[str, Any]:
        """獲取快取統計"""
        async with self._lock:
            current_time = time.time()
            total_entries = len(self.cache)
            expired_entries = sum(
                1 for entry in self.cache.values()
                if current_time > entry['expires_at']
            )

            total_access = sum(entry['access_count'] for entry in self.cache.values())

            return {
                'total_entries': total_entries,
                'active_entries': total_entries - expired_entries,
                'expired_entries': expired_entries,
                'total_access_count': total_access,
                'memory_usage_kb': self._estimate_memory_usage(),
                'hit_rate': self._calculate_hit_rate()
            }

    def _estimate_memory_usage(self) -> float:
        """估算記憶體使用量 (KB)"""
        try:
            import sys
            total_size = 0
            for entry in self.cache.values():
                total_size += sys.getsizeof(entry['value'])
                total_size += sys.getsizeof(entry)
            return total_size / 1024
        except Exception as e:
            logger.debug(f"估算記憶體使用量失敗: {e}")
            return 0.0

    def _calculate_hit_rate(self) -> float:
        """計算命中率"""
        if not hasattr(self, '_hit_count'):
            self._hit_count = 0
            self._miss_count = 0

        total = self._hit_count + self._miss_count
        return (self._hit_count / total * 100) if total > 0 else 0.0

# 全域快取實例
cache = MemoryCache(default_ttl=300)  # 5分鐘默認過期時間

def generate_cache_key(*args, prefix: str = "api", **kwargs) -> str:
    """生成快取鍵"""
    # 將參數轉換為字符串並創建哈希
    key_parts = [prefix]

    for arg in args:
        if hasattr(arg, 'model_dump'):  # Pydantic v2 模型
            key_parts.append(json.dumps(arg.model_dump(), sort_keys=True, default=str))
        elif hasattr(arg, 'dict'):  # Pydantic v1 模型
            key_parts.append(json.dumps(arg.dict(), sort_keys=True, default=str))
        else:
            key_parts.append(str(arg))

    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")

    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def cache_result(ttl: int = 300, prefix: str = "api", key_generator: Optional[Callable] = None):
    """
    API 結果快取裝飾器

    Args:
        ttl: 快取存活時間 (秒)
        prefix: 快取鍵前綴
        key_generator: 自定義鍵生成函數
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成快取鍵
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                cache_key = generate_cache_key(*args, prefix=f"{prefix}:{func.__name__}", **kwargs)

            # 嘗試從快取獲取
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_result

            # 執行原始函數
            logger.debug(f"Cache miss for key: {cache_key}")
            result = await func(*args, **kwargs)

            # 儲存到快取
            await cache.set(cache_key, result, ttl)

            return result

        # 添加快取管理方法
        wrapper.clear_cache = lambda pattern=None: cache.clear(pattern or f"{prefix}:{func.__name__}")
        wrapper.cache_key = lambda *args, **kwargs: (
            key_generator(*args, **kwargs) if key_generator
            else generate_cache_key(*args, prefix=f"{prefix}:{func.__name__}", **kwargs)
        )

        return wrapper
    return decorator

# 特定用途的快取裝飾器
def cache_documents(ttl: int = 180):
    """公文查詢結果快取 (3分鐘)"""
    return cache_result(ttl=ttl, prefix="documents")

def cache_statistics(ttl: int = 600):
    """統計資料快取 (10分鐘)"""
    return cache_result(ttl=ttl, prefix="stats")

def cache_dropdown_data(ttl: int = 1800):
    """下拉選項資料快取 (30分鐘)"""
    return cache_result(ttl=ttl, prefix="dropdown")

def cache_user_data(ttl: int = 900):
    """用戶資料快取 (15分鐘)"""
    return cache_result(ttl=ttl, prefix="user")

def cache_search_results(ttl: int = 120):
    """搜尋結果快取 (2分鐘，較短以保持即時性)"""
    return cache_result(ttl=ttl, prefix="search")

def cache_suggestions(ttl: int = 300):
    """搜尋建議快取 (5分鐘)"""
    return cache_result(ttl=ttl, prefix="suggestions")

# 快取清理任務
async def cleanup_cache_task():
    """定期清理過期快取的後台任務"""
    while True:
        try:
            expired_count = await cache.cleanup_expired()
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired cache entries")

            # 每5分鐘執行一次清理
            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            await asyncio.sleep(60)  # 錯誤時等待1分鐘後重試

# 快取統計 API 函數
async def get_cache_statistics() -> Dict[str, Any]:
    """獲取快取統計資訊"""
    stats = await cache.get_stats()

    # 添加額外的統計資訊
    stats.update({
        'cache_type': 'memory',
        'default_ttl': cache.default_ttl,
        'timestamp': datetime.now().isoformat()
    })

    return stats

async def invalidate_cache_pattern(pattern: str) -> Dict[str, Any]:
    """根據模式清理快取"""
    cleared_count = await cache.clear(pattern)

    return {
        'pattern': pattern,
        'cleared_count': cleared_count,
        'timestamp': datetime.now().isoformat()
    }

# 快取預熱函數
async def warmup_cache():
    """系統啟動時預熱重要快取"""
    logger.info("Starting cache warmup...")

    try:
        # 這裡可以添加預熱邏輯，例如：
        # - 載入常用的下拉選項
        # - 載入首頁統計資料
        # - 載入用戶權限資料等

        logger.info("Cache warmup completed")
    except Exception as e:
        logger.error(f"Cache warmup failed: {e}")

# 快取管理工具類
class CacheManager:
    """快取管理工具類"""

    @staticmethod
    async def get_all_stats() -> Dict[str, Any]:
        """獲取所有快取統計"""
        return await get_cache_statistics()

    @staticmethod
    async def clear_all() -> Dict[str, Any]:
        """清空所有快取"""
        cleared_count = await cache.clear()
        return {
            'cleared_count': cleared_count,
            'timestamp': datetime.now().isoformat()
        }

    @staticmethod
    async def clear_by_pattern(pattern: str) -> Dict[str, Any]:
        """按模式清理快取"""
        return await invalidate_cache_pattern(pattern)

    @staticmethod
    async def get_cache_health() -> Dict[str, Any]:
        """獲取快取健康狀態"""
        stats = await cache.get_stats()

        # 評估快取健康狀態
        health_status = "healthy"
        warnings = []

        if stats['memory_usage_kb'] > 100 * 1024:  # 100MB
            health_status = "warning"
            warnings.append("High memory usage")

        if stats['hit_rate'] < 50:
            health_status = "warning"
            warnings.append("Low hit rate")

        if stats['expired_entries'] > stats['active_entries']:
            health_status = "warning"
            warnings.append("Too many expired entries")

        return {
            'status': health_status,
            'warnings': warnings,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        }