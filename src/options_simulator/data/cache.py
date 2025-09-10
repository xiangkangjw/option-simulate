"""Advanced caching system for market data with TTL and persistence.

This module provides both in-memory and file-based caching with
intelligent cache invalidation and data quality validation.
"""

import time
import json
import pickle
import hashlib
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a single cache entry with metadata."""
    
    def __init__(self, data: Any, ttl_seconds: float, metadata: Optional[Dict] = None):
        self.data = data
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
        self.metadata = metadata or {}
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.created_at > self.ttl_seconds
    
    def is_stale(self, staleness_threshold: float = None) -> bool:
        """Check if the cache entry is stale based on custom threshold."""
        if staleness_threshold is None:
            return self.is_expired()
        return time.time() - self.created_at > staleness_threshold
    
    def access(self) -> Any:
        """Mark the entry as accessed and return data."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.data
    
    def age_seconds(self) -> float:
        """Get age of the cache entry in seconds."""
        return time.time() - self.created_at


class InMemoryCache:
    """High-performance in-memory cache with TTL and LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300):
        """Initialize in-memory cache.
        
        Args:
            max_size: Maximum number of entries to store
            default_ttl: Default TTL in seconds (5 minutes)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expires': 0
        }
    
    def _make_key(self, key: Union[str, tuple]) -> str:
        """Convert key to string format."""
        if isinstance(key, tuple):
            return hashlib.md5(str(key).encode()).hexdigest()
        return str(key)
    
    def get(self, key: Union[str, tuple], default: Any = None) -> Any:
        """Get value from cache."""
        str_key = self._make_key(key)
        
        if str_key not in self._cache:
            self._stats['misses'] += 1
            return default
        
        entry = self._cache[str_key]
        
        if entry.is_expired():
            del self._cache[str_key]
            self._stats['expires'] += 1
            self._stats['misses'] += 1
            return default
        
        self._stats['hits'] += 1
        return entry.access()
    
    def set(self, key: Union[str, tuple], value: Any, ttl: Optional[float] = None, metadata: Optional[Dict] = None) -> None:
        """Set value in cache."""
        str_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        
        # Evict if at capacity
        if len(self._cache) >= self.max_size and str_key not in self._cache:
            self._evict_lru()
        
        self._cache[str_key] = CacheEntry(value, ttl, metadata)
    
    def delete(self, key: Union[str, tuple]) -> bool:
        """Delete entry from cache."""
        str_key = self._make_key(key)
        if str_key in self._cache:
            del self._cache[str_key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._stats = {k: 0 for k in self._stats}
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries and return count removed."""
        expired_keys = [
            key for key, entry in self._cache.items() 
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self._stats['expires'] += 1
        
        return len(expired_keys)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
        del self._cache[lru_key]
        self._stats['evictions'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'entries': len(self._cache),
            'max_size': self.max_size,
            'hit_rate': hit_rate,
            'total_hits': self._stats['hits'],
            'total_misses': self._stats['misses'],
            'evictions': self._stats['evictions'],
            'expires': self._stats['expires']
        }
    
    def get_entry_info(self, key: Union[str, tuple]) -> Optional[Dict[str, Any]]:
        """Get detailed information about a cache entry."""
        str_key = self._make_key(key)
        
        if str_key not in self._cache:
            return None
        
        entry = self._cache[str_key]
        return {
            'age_seconds': entry.age_seconds(),
            'ttl_seconds': entry.ttl_seconds,
            'access_count': entry.access_count,
            'is_expired': entry.is_expired(),
            'metadata': entry.metadata,
            'created_at': datetime.fromtimestamp(entry.created_at).isoformat(),
            'last_accessed': datetime.fromtimestamp(entry.last_accessed).isoformat()
        }


class FileCacheBackend:
    """File-based cache backend for persistence across sessions."""
    
    def __init__(self, cache_dir: str = ".cache/market_data", max_file_age_days: int = 7):
        """Initialize file cache backend.
        
        Args:
            cache_dir: Directory to store cache files
            max_file_age_days: Maximum age for cache files before cleanup
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_age = timedelta(days=max_file_age_days)
        
        logger.info(f"Initialized file cache at {self.cache_dir}")
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"
    
    def get(self, key: str, max_age_seconds: Optional[float] = None) -> Optional[Any]:
        """Get value from file cache."""
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            return None
        
        try:
            # Check file age
            file_age = time.time() - file_path.stat().st_mtime
            if max_age_seconds and file_age > max_age_seconds:
                return None
            
            with open(file_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Validate cache structure
            if not isinstance(cache_data, dict) or 'data' not in cache_data:
                logger.warning(f"Invalid cache file structure: {file_path}")
                file_path.unlink()  # Remove corrupted file
                return None
            
            return cache_data['data']
            
        except Exception as e:
            logger.warning(f"Error reading cache file {file_path}: {e}")
            try:
                file_path.unlink()  # Remove corrupted file
            except Exception:
                pass
            return None
    
    def set(self, key: str, value: Any, metadata: Optional[Dict] = None) -> bool:
        """Set value in file cache."""
        file_path = self._get_file_path(key)
        
        try:
            cache_data = {
                'data': value,
                'key': key,
                'created_at': time.time(),
                'metadata': metadata or {}
            }
            
            with open(file_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            return True
            
        except Exception as e:
            logger.error(f"Error writing cache file {file_path}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete entry from file cache."""
        file_path = self._get_file_path(key)
        
        try:
            if file_path.exists():
                file_path.unlink()
                return True
        except Exception as e:
            logger.error(f"Error deleting cache file {file_path}: {e}")
        
        return False
    
    def cleanup_old_files(self) -> int:
        """Remove old cache files and return count removed."""
        removed_count = 0
        current_time = datetime.now()
        
        for file_path in self.cache_dir.glob("*.cache"):
            try:
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if current_time - file_time > self.max_file_age:
                    file_path.unlink()
                    removed_count += 1
            except Exception as e:
                logger.warning(f"Error processing cache file {file_path}: {e}")
        
        return removed_count
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the file cache."""
        cache_files = list(self.cache_dir.glob("*.cache"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'cache_dir': str(self.cache_dir),
            'file_count': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'oldest_file': min(cache_files, key=lambda f: f.stat().st_mtime) if cache_files else None,
            'newest_file': max(cache_files, key=lambda f: f.stat().st_mtime) if cache_files else None
        }


class HybridCache:
    """Hybrid cache combining in-memory and file-based storage.
    
    Provides fast in-memory access for frequently used data and
    persistent file-based storage for longer-term caching.
    """
    
    def __init__(self, 
                 memory_ttl: float = 300,      # 5 minutes for memory
                 file_ttl: float = 3600,       # 1 hour for file cache
                 max_memory_size: int = 1000):
        """Initialize hybrid cache.
        
        Args:
            memory_ttl: TTL for in-memory cache entries
            file_ttl: TTL for file cache entries  
            max_memory_size: Maximum entries in memory cache
        """
        self.memory_cache = InMemoryCache(max_memory_size, memory_ttl)
        self.file_cache = FileCacheBackend()
        self.memory_ttl = memory_ttl
        self.file_ttl = file_ttl
    
    def get(self, key: Union[str, tuple], default: Any = None) -> Any:
        """Get value from hybrid cache (memory first, then file)."""
        # Try memory cache first
        value = self.memory_cache.get(key, None)
        if value is not None:
            return value
        
        # Try file cache
        str_key = self.memory_cache._make_key(key)
        value = self.file_cache.get(str_key, self.file_ttl)
        
        if value is not None:
            # Promote to memory cache
            self.memory_cache.set(key, value, self.memory_ttl)
            return value
        
        return default
    
    def set(self, key: Union[str, tuple], value: Any, 
            memory_ttl: Optional[float] = None,
            persist_to_file: bool = True,
            metadata: Optional[Dict] = None) -> None:
        """Set value in hybrid cache."""
        # Always set in memory
        self.memory_cache.set(key, value, memory_ttl or self.memory_ttl, metadata)
        
        # Optionally persist to file
        if persist_to_file:
            str_key = self.memory_cache._make_key(key)
            self.file_cache.set(str_key, value, metadata)
    
    def delete(self, key: Union[str, tuple]) -> bool:
        """Delete from both memory and file cache."""
        str_key = self.memory_cache._make_key(key)
        
        memory_deleted = self.memory_cache.delete(key)
        file_deleted = self.file_cache.delete(str_key)
        
        return memory_deleted or file_deleted
    
    def clear(self) -> None:
        """Clear both memory and file caches."""
        self.memory_cache.clear()
        # Note: We don't clear file cache as it's meant for persistence
    
    def cleanup(self) -> Dict[str, int]:
        """Cleanup expired entries and return statistics."""
        memory_cleaned = self.memory_cache.cleanup_expired()
        file_cleaned = self.file_cache.cleanup_old_files()
        
        return {
            'memory_entries_cleaned': memory_cleaned,
            'file_entries_cleaned': file_cleaned
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        memory_stats = self.memory_cache.get_stats()
        file_stats = self.file_cache.get_cache_info()
        
        return {
            'memory_cache': memory_stats,
            'file_cache': file_stats,
            'configuration': {
                'memory_ttl': self.memory_ttl,
                'file_ttl': self.file_ttl
            }
        }


# Default cache instance for global use
default_cache = HybridCache()


def cache_key(*args, **kwargs) -> str:
    """Generate a cache key from arguments."""
    key_parts = list(args)
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return hashlib.md5(str(key_parts).encode()).hexdigest()


def cached_function(ttl: float = 300, use_file_cache: bool = True):
    """Decorator for caching function results.
    
    Args:
        ttl: Time to live for cache entries
        use_file_cache: Whether to persist results to file cache
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = default_cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            default_cache.set(key, result, ttl, use_file_cache)
            
            return result
        
        return wrapper
    return decorator