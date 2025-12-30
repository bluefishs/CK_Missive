"""
API 快取機制 - Phase 2 性能優化
支持內存快取和 Redis 快取（可選）
"""
import hashlib
import json
import time
from typing import Any, Optional, Dict
from functools import wraps
import asyncio

class InMemoryCache:
    """內存快取類"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.access_times: Dict[str, float] = {}
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """生成快取鍵"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        hash_object = hashlib.md5(key_string.encode())
        return f"{prefix}:{hash_object.hexdigest()}"
    
    def _is_expired(self, cache_data: Dict[str, Any]) -> bool:
        """檢查快取是否過期"""
        if cache_data['ttl'] == -1:  # 永不過期
            return False
        return time.time() > cache_data['created_at'] + cache_data['ttl']
    
    def _cleanup_expired(self):
        """清理過期的快取項目"""
        current_time = time.time()
        expired_keys = [
            key for key, data in self.cache.items()
            if self._is_expired(data)
        ]
        for key in expired_keys:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def _enforce_size_limit(self):
        """強制執行大小限制（LRU 策略）"""
        if len(self.cache) <= self.max_size:
            return
        
        # 根據存取時間排序，移除最少使用的項目
        sorted_keys = sorted(
            self.access_times.keys(), 
            key=lambda k: self.access_times[k]
        )
        
        keys_to_remove = sorted_keys[:len(self.cache) - self.max_size]
        for key in keys_to_remove:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """獲取快取值"""
        if key not in self.cache:
            return None
        
        cache_data = self.cache[key]
        if self._is_expired(cache_data):
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
            return None
        
        # 更新存取時間
        self.access_times[key] = time.time()
        return cache_data['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """設置快取值"""
        if ttl is None:
            ttl = self.default_ttl
        
        cache_data = {
            'value': value,
            'created_at': time.time(),
            'ttl': ttl
        }
        
        self.cache[key] = cache_data
        self.access_times[key] = time.time()
        
        # 清理過期項目和強制大小限制
        if len(self.cache) % 100 == 0:  # 每 100 次插入清理一次
            self._cleanup_expired()
        
        self._enforce_size_limit()
    
    def delete(self, key: str) -> bool:
        """刪除快取項目"""
        if key in self.cache:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)
            return True
        return False
    
    def clear(self) -> None:
        """清空所有快取"""
        self.cache.clear()
        self.access_times.clear()
    
    def stats(self) -> Dict[str, Any]:
        """獲取快取統計信息"""
        current_time = time.time()
        expired_count = sum(
            1 for data in self.cache.values()
            if self._is_expired(data)
        )
        
        return {
            'total_items': len(self.cache),
            'expired_items': expired_count,
            'active_items': len(self.cache) - expired_count,
            'max_size': self.max_size,
            'hit_ratio': getattr(self, '_hit_count', 0) / max(getattr(self, '_total_requests', 1), 1)
        }

# 全局快取實例
cache = InMemoryCache(max_size=2000, default_ttl=300)  # 5 分鐘預設TTL

def cached(ttl: int = 300, prefix: str = "api"):
    """
    快取裝飾器
    
    Args:
        ttl: 快取生存時間（秒）
        prefix: 快取鍵前綴
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成快取鍵
            cache_key = cache._generate_key(prefix, func.__name__, *args, **kwargs)
            
            # 嘗試從快取獲取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 執行原函數
            result = await func(*args, **kwargs)
            
            # 存儲到快取
            cache.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成快取鍵
            cache_key = cache._generate_key(prefix, func.__name__, *args, **kwargs)
            
            # 嘗試從快取獲取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 執行原函數
            result = func(*args, **kwargs)
            
            # 存儲到快取
            cache.set(cache_key, result, ttl)
            
            return result
        
        # 根據函數類型返回相應的包裝器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def cache_invalidate(prefix: str = "api", pattern: str = None):
    """
    快取無效化裝飾器
    在資料更新時自動清理相關快取
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # 清理相關快取
            keys_to_delete = []
            for key in cache.cache.keys():
                if key.startswith(f"{prefix}:"):
                    if pattern is None or pattern in key:
                        keys_to_delete.append(key)
            
            for key in keys_to_delete:
                cache.delete(key)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # 清理相關快取
            keys_to_delete = []
            for key in cache.cache.keys():
                if key.startswith(f"{prefix}:"):
                    if pattern is None or pattern in key:
                        keys_to_delete.append(key)
            
            for key in keys_to_delete:
                cache.delete(key)
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# 清理任務（可選，用於定期清理過期快取）
async def periodic_cleanup():
    """定期清理過期快取的後台任務"""
    while True:
        cache._cleanup_expired()
        await asyncio.sleep(300)  # 每 5 分鐘清理一次