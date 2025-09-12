"""
Memory Management for Agent Infrastructure
=========================================

Advanced memory management patterns for efficient message handling.
Inspired by Claude Code's memory management with weak references and smart caching.
"""

import gc
import logging
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from collections import OrderedDict, deque
import sys
import psutil
import asyncio
from abc import ABC, abstractmethod
import hashlib
import pickle
import gzip

from .message_types import AgentMessage

logger = logging.getLogger(__name__)

T = TypeVar('T')


class MemoryPressure(Enum):
    """Memory pressure levels"""
    LOW = "low"           # < 50% memory used
    MEDIUM = "medium"     # 50-70% memory used
    HIGH = "high"         # 70-85% memory used
    CRITICAL = "critical" # 85-95% memory used
    EMERGENCY = "emergency" # > 95% memory used


@dataclass
class MemoryStats:
    """Memory usage statistics"""
    total_memory: int = 0
    available_memory: int = 0
    used_memory: int = 0
    memory_percent: float = 0.0
    pressure_level: MemoryPressure = MemoryPressure.LOW
    
    # Process-specific stats
    process_memory: int = 0
    process_memory_percent: float = 0.0
    
    # Cache stats
    cache_hits: int = 0
    cache_misses: int = 0
    cache_size: int = 0
    cache_memory_usage: int = 0
    
    # GC stats
    gc_collections: Tuple[int, int, int] = field(default_factory=lambda: (0, 0, 0))
    gc_collected: Tuple[int, int, int] = field(default_factory=lambda: (0, 0, 0))
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_memory': self.total_memory,
            'available_memory': self.available_memory,
            'used_memory': self.used_memory,
            'memory_percent': self.memory_percent,
            'pressure_level': self.pressure_level.value,
            'process_memory': self.process_memory,
            'process_memory_percent': self.process_memory_percent,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_size': self.cache_size,
            'cache_memory_usage': self.cache_memory_usage,
            'gc_collections': self.gc_collections,
            'gc_collected': self.gc_collected,
            'timestamp': self.timestamp.isoformat()
        }


class LRUCache(Generic[T]):
    """
    LRU Cache with memory-aware eviction
    Inspired by Claude Code's memory management patterns
    """
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict[str, T] = OrderedDict()
        self.access_times: Dict[str, datetime] = {}
        self.memory_usage: Dict[str, int] = {}
        self.total_memory_usage = 0
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
        # Thread safety
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[T]:
        """Get item from cache"""
        
        with self._lock:
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                self.access_times[key] = datetime.now(timezone.utc)
                self.hits += 1
                return value
            else:
                self.misses += 1
                return None
    
    def put(self, key: str, value: T) -> bool:
        """Put item in cache"""
        
        with self._lock:
            # Calculate memory usage for this item
            try:
                item_memory = sys.getsizeof(value)
                if hasattr(value, '__dict__'):
                    item_memory += sys.getsizeof(value.__dict__)
            except (TypeError, AttributeError):
                item_memory = 1024  # Default estimate
            
            # Check if item is too large
            if item_memory > self.max_memory_bytes:
                logger.warning(f"Item too large for cache: {item_memory} bytes")
                return False
            
            # Remove existing item if updating
            if key in self.cache:
                old_memory = self.memory_usage.pop(key, 0)
                self.total_memory_usage -= old_memory
                self.cache.pop(key, None)
                self.access_times.pop(key, None)
            
            # Ensure we have space
            while (len(self.cache) >= self.max_size or 
                   self.total_memory_usage + item_memory > self.max_memory_bytes):
                if not self.cache:
                    break
                self._evict_lru()
            
            # Add new item
            self.cache[key] = value
            self.memory_usage[key] = item_memory
            self.total_memory_usage += item_memory
            self.access_times[key] = datetime.now(timezone.utc)
            
            return True
    
    def remove(self, key: str) -> bool:
        """Remove item from cache"""
        
        with self._lock:
            if key in self.cache:
                self.cache.pop(key, None)
                self.access_times.pop(key, None)
                item_memory = self.memory_usage.pop(key, 0)
                self.total_memory_usage -= item_memory
                return True
            return False
    
    def clear(self):
        """Clear all items from cache"""
        
        with self._lock:
            self.cache.clear()
            self.access_times.clear()
            self.memory_usage.clear()
            self.total_memory_usage = 0
    
    def _evict_lru(self):
        """Evict least recently used item"""
        
        if self.cache:
            # Find LRU item
            lru_key = next(iter(self.cache))  # First item is LRU in OrderedDict
            
            self.cache.pop(lru_key, None)
            self.access_times.pop(lru_key, None)
            item_memory = self.memory_usage.pop(lru_key, 0)
            self.total_memory_usage -= item_memory
            self.evictions += 1
            
            logger.debug(f"Evicted LRU item: {lru_key}, freed {item_memory} bytes")
    
    def cleanup_expired(self, max_age_seconds: int = 3600):
        """Clean up expired items"""
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
        expired_keys = []
        
        with self._lock:
            for key, access_time in self.access_times.items():
                if access_time < cutoff_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.remove(key)
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache items")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        
        hit_rate = self.hits / max(self.hits + self.misses, 1)
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'memory_usage_bytes': self.total_memory_usage,
            'memory_usage_mb': self.total_memory_usage / (1024 * 1024),
            'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'hit_rate': hit_rate
        }


class WeakMessageCache:
    """
    Weak reference cache for messages
    Automatically cleans up when messages are garbage collected
    """
    
    def __init__(self):
        self._cache: weakref.WeakValueDictionary[str, AgentMessage] = weakref.WeakValueDictionary()
        self._cleanup_callbacks: Dict[str, List[Callable]] = {}
        self._access_count = 0
        # Use FinalizationRegistry if available (Python 3.9+), otherwise use weakref.ref with callback
        try:
            self._cleanup_registry = weakref.finalization.FinalizationRegistry(self._on_message_finalized)
        except AttributeError:
            self._cleanup_registry = None
    
    def put(self, message: AgentMessage) -> str:
        """Store message in weak cache"""
        
        message_id = message.message_id
        self._cache[message_id] = message
        
        # Register for cleanup notification if registry is available
        if self._cleanup_registry:
            self._cleanup_registry.register(message, message_id)
        
        return message_id
    
    def get(self, message_id: str) -> Optional[AgentMessage]:
        """Get message from cache"""
        
        self._access_count += 1
        return self._cache.get(message_id)
    
    def exists(self, message_id: str) -> bool:
        """Check if message exists in cache"""
        return message_id in self._cache
    
    def remove(self, message_id: str) -> bool:
        """Remove message from cache"""
        if message_id in self._cache:
            del self._cache[message_id]
            return True
        return False
    
    def add_cleanup_callback(self, message_id: str, callback: Callable):
        """Add callback to be called when message is garbage collected"""
        if message_id not in self._cleanup_callbacks:
            self._cleanup_callbacks[message_id] = []
        self._cleanup_callbacks[message_id].append(callback)
    
    def _on_message_finalized(self, message_id: str):
        """Called when a message is garbage collected"""
        
        logger.debug(f"Message {message_id} was garbage collected")
        
        # Execute cleanup callbacks
        callbacks = self._cleanup_callbacks.pop(message_id, [])
        for callback in callbacks:
            try:
                callback(message_id)
            except Exception as e:
                logger.error(f"Cleanup callback error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'size': len(self._cache),
            'access_count': self._access_count,
            'pending_callbacks': len(self._cleanup_callbacks)
        }


class CompressedObjectStore:
    """
    Compressed object storage for large data
    Uses gzip compression to reduce memory usage
    """
    
    def __init__(self, compression_level: int = 6):
        self.compression_level = compression_level
        self.store: Dict[str, bytes] = {}
        self.original_sizes: Dict[str, int] = {}
        self.compressed_sizes: Dict[str, int] = {}
        self._lock = threading.RLock()
        
        # Statistics
        self.compression_ratio = 0.0
        self.total_original_size = 0
        self.total_compressed_size = 0
    
    def store_object(self, key: str, obj: Any) -> bool:
        """Store object with compression"""
        
        try:
            # Serialize object
            serialized = pickle.dumps(obj)
            original_size = len(serialized)
            
            # Compress
            compressed = gzip.compress(serialized, compresslevel=self.compression_level)
            compressed_size = len(compressed)
            
            with self._lock:
                # Remove old object if exists
                if key in self.store:
                    old_original = self.original_sizes.pop(key, 0)
                    old_compressed = self.compressed_sizes.pop(key, 0)
                    self.total_original_size -= old_original
                    self.total_compressed_size -= old_compressed
                
                # Store new object
                self.store[key] = compressed
                self.original_sizes[key] = original_size
                self.compressed_sizes[key] = compressed_size
                
                # Update totals
                self.total_original_size += original_size
                self.total_compressed_size += compressed_size
                
                # Update compression ratio
                if self.total_original_size > 0:
                    self.compression_ratio = self.total_compressed_size / self.total_original_size
            
            logger.debug(f"Stored object {key}: {original_size} -> {compressed_size} bytes "
                        f"({compressed_size/original_size:.2%} of original)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store object {key}: {e}")
            return False
    
    def retrieve_object(self, key: str) -> Optional[Any]:
        """Retrieve and decompress object"""
        
        with self._lock:
            compressed_data = self.store.get(key)
            if not compressed_data:
                return None
        
        try:
            # Decompress
            decompressed = gzip.decompress(compressed_data)
            
            # Deserialize
            obj = pickle.loads(decompressed)
            
            return obj
            
        except Exception as e:
            logger.error(f"Failed to retrieve object {key}: {e}")
            return None
    
    def remove_object(self, key: str) -> bool:
        """Remove object from store"""
        
        with self._lock:
            if key in self.store:
                del self.store[key]
                
                original_size = self.original_sizes.pop(key, 0)
                compressed_size = self.compressed_sizes.pop(key, 0)
                
                self.total_original_size -= original_size
                self.total_compressed_size -= compressed_size
                
                # Recalculate compression ratio
                if self.total_original_size > 0:
                    self.compression_ratio = self.total_compressed_size / self.total_original_size
                else:
                    self.compression_ratio = 0.0
                
                return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        
        return {
            'object_count': len(self.store),
            'total_original_size': self.total_original_size,
            'total_compressed_size': self.total_compressed_size,
            'compression_ratio': self.compression_ratio,
            'space_saved_bytes': self.total_original_size - self.total_compressed_size,
            'space_saved_percent': (1 - self.compression_ratio) * 100 if self.compression_ratio > 0 else 0
        }


class MemoryMonitor:
    """
    Memory usage monitor and pressure detection
    Inspired by Claude Code's memory pressure monitoring
    """
    
    def __init__(self, check_interval_seconds: int = 10):
        self.check_interval = check_interval_seconds
        self.pressure_callbacks: Dict[MemoryPressure, List[Callable]] = {
            level: [] for level in MemoryPressure
        }
        
        self.history: deque[MemoryStats] = deque(maxlen=1000)
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Thresholds (percentage)
        self.pressure_thresholds = {
            MemoryPressure.LOW: 50,
            MemoryPressure.MEDIUM: 70,
            MemoryPressure.HIGH: 85,
            MemoryPressure.CRITICAL: 95,
            MemoryPressure.EMERGENCY: 98
        }
        
        self.current_pressure = MemoryPressure.LOW
        self.last_gc_time = datetime.now(timezone.utc)
        
        logger.debug("MemoryMonitor initialized")
    
    def start_monitoring(self):
        """Start memory monitoring"""
        
        if not self._monitoring:
            self._monitoring = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("Memory monitoring started")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
        logger.info("Memory monitoring stopped")
    
    def add_pressure_callback(self, pressure_level: MemoryPressure, callback: Callable[[MemoryStats], None]):
        """Add callback for specific pressure level"""
        self.pressure_callbacks[pressure_level].append(callback)
    
    def get_current_stats(self) -> MemoryStats:
        """Get current memory statistics"""
        
        # System memory
        memory = psutil.virtual_memory()
        
        # Process memory
        process = psutil.Process()
        process_info = process.memory_info()
        
        # GC statistics
        gc_stats = gc.get_stats()
        gc_counts = gc.get_count()
        
        # Determine pressure level
        pressure = self._determine_pressure_level(memory.percent)
        
        stats = MemoryStats(
            total_memory=memory.total,
            available_memory=memory.available,
            used_memory=memory.used,
            memory_percent=memory.percent,
            pressure_level=pressure,
            process_memory=process_info.rss,
            process_memory_percent=(process_info.rss / memory.total) * 100,
            gc_collections=(
                gc_stats[0]['collections'] if gc_stats else 0,
                gc_stats[1]['collections'] if len(gc_stats) > 1 else 0,
                gc_stats[2]['collections'] if len(gc_stats) > 2 else 0
            ),
            gc_collected=gc_counts
        )
        
        return stats
    
    def _determine_pressure_level(self, memory_percent: float) -> MemoryPressure:
        """Determine memory pressure level"""
        
        if memory_percent >= self.pressure_thresholds[MemoryPressure.EMERGENCY]:
            return MemoryPressure.EMERGENCY
        elif memory_percent >= self.pressure_thresholds[MemoryPressure.CRITICAL]:
            return MemoryPressure.CRITICAL
        elif memory_percent >= self.pressure_thresholds[MemoryPressure.HIGH]:
            return MemoryPressure.HIGH
        elif memory_percent >= self.pressure_thresholds[MemoryPressure.MEDIUM]:
            return MemoryPressure.MEDIUM
        else:
            return MemoryPressure.LOW
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        
        while self._monitoring:
            try:
                stats = self.get_current_stats()
                self.history.append(stats)
                
                # Check for pressure level changes
                if stats.pressure_level != self.current_pressure:
                    old_pressure = self.current_pressure
                    self.current_pressure = stats.pressure_level
                    
                    logger.info(f"Memory pressure changed: {old_pressure.value} -> {stats.pressure_level.value}")
                    
                    # Notify callbacks
                    await self._notify_pressure_callbacks(stats)
                
                # Trigger automatic garbage collection under high pressure
                if stats.pressure_level in [MemoryPressure.HIGH, MemoryPressure.CRITICAL, MemoryPressure.EMERGENCY]:
                    await self._handle_memory_pressure(stats)
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def _notify_pressure_callbacks(self, stats: MemoryStats):
        """Notify pressure level callbacks"""
        
        callbacks = self.pressure_callbacks.get(stats.pressure_level, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(stats)
                else:
                    callback(stats)
            except Exception as e:
                logger.error(f"Pressure callback error: {e}")
    
    async def _handle_memory_pressure(self, stats: MemoryStats):
        """Handle high memory pressure"""
        
        current_time = datetime.now(timezone.utc)
        time_since_gc = (current_time - self.last_gc_time).total_seconds()
        
        # Only force GC if it's been a while since last one
        if time_since_gc > 30:  # At least 30 seconds between forced GCs
            logger.warning(f"High memory pressure ({stats.pressure_level.value}), forcing garbage collection")
            
            # Force garbage collection
            collected = gc.collect()
            self.last_gc_time = current_time
            
            logger.info(f"Garbage collection freed {collected} objects")
            
            # If still critical after GC, log warning
            new_stats = self.get_current_stats()
            if new_stats.pressure_level in [MemoryPressure.CRITICAL, MemoryPressure.EMERGENCY]:
                logger.warning(f"Memory pressure still {new_stats.pressure_level.value} after GC")


class MemoryManager:
    """
    Central memory management system for agent infrastructure
    Combines various memory management strategies and monitoring
    """
    
    def __init__(self, 
                 max_cache_size: int = 5000,
                 max_cache_memory_mb: int = 500,
                 enable_compression: bool = True,
                 enable_monitoring: bool = True):
        
        # Core components
        self.message_cache = LRUCache[AgentMessage](max_cache_size, max_cache_memory_mb)
        self.weak_cache = WeakMessageCache()
        self.compressed_store = CompressedObjectStore() if enable_compression else None
        self.monitor = MemoryMonitor() if enable_monitoring else None
        
        # Configuration
        self.enable_compression = enable_compression
        self.enable_monitoring = enable_monitoring
        
        # Memory cleanup strategies
        self.cleanup_strategies: List[Callable[[], None]] = []
        
        # Thread pool for background cleanup
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="MemoryCleanup")
        
        # Statistics
        self.cleanup_count = 0
        self.total_memory_freed = 0
        
        # Setup pressure callbacks
        if self.monitor:
            self.monitor.add_pressure_callback(MemoryPressure.HIGH, self._handle_high_pressure)
            self.monitor.add_pressure_callback(MemoryPressure.CRITICAL, self._handle_critical_pressure)
            self.monitor.add_pressure_callback(MemoryPressure.EMERGENCY, self._handle_emergency_pressure)
        
        # Register default cleanup strategies
        self._register_default_cleanup_strategies()
        
        logger.info("MemoryManager initialized")
    
    async def start(self):
        """Start memory management"""
        
        if self.monitor:
            self.monitor.start_monitoring()
        
        # Start periodic cleanup task
        asyncio.create_task(self._periodic_cleanup())
        
        logger.info("MemoryManager started")
    
    def stop(self):
        """Stop memory management"""
        
        if self.monitor:
            self.monitor.stop_monitoring()
        
        self._executor.shutdown(wait=True)
        
        logger.info("MemoryManager stopped")
    
    def cache_message(self, message: AgentMessage) -> bool:
        """Cache a message"""
        
        # Try main cache first
        if self.message_cache.put(message.message_id, message):
            return True
        
        # If main cache is full, try compressed storage
        if self.compressed_store:
            return self.compressed_store.store_object(message.message_id, message)
        
        return False
    
    def get_cached_message(self, message_id: str) -> Optional[AgentMessage]:
        """Get cached message"""
        
        # Try main cache first
        message = self.message_cache.get(message_id)
        if message:
            return message
        
        # Try weak cache
        message = self.weak_cache.get(message_id)
        if message:
            # Promote to main cache if possible
            self.message_cache.put(message_id, message)
            return message
        
        # Try compressed storage
        if self.compressed_store:
            message = self.compressed_store.retrieve_object(message_id)
            if message and isinstance(message, AgentMessage):
                # Promote to main cache
                self.message_cache.put(message_id, message)
                return message
        
        return None
    
    def store_weak_reference(self, message: AgentMessage) -> str:
        """Store weak reference to message"""
        return self.weak_cache.put(message)
    
    def add_cleanup_strategy(self, strategy: Callable[[], None]):
        """Add a memory cleanup strategy"""
        self.cleanup_strategies.append(strategy)
    
    def _register_default_cleanup_strategies(self):
        """Register default cleanup strategies"""
        
        def cleanup_expired_cache():
            self.message_cache.cleanup_expired()
        
        def force_garbage_collection():
            collected = gc.collect()
            logger.debug(f"Garbage collection freed {collected} objects")
        
        def cleanup_compressed_store():
            if self.compressed_store:
                # Simple cleanup - could be more sophisticated
                stats = self.compressed_store.get_stats()
                if stats['object_count'] > 10000:
                    logger.warning("Compressed store getting large, consider cleanup")
        
        self.add_cleanup_strategy(cleanup_expired_cache)
        self.add_cleanup_strategy(force_garbage_collection)
        self.add_cleanup_strategy(cleanup_compressed_store)
    
    async def _periodic_cleanup(self):
        """Periodic cleanup task"""
        
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await self._run_cleanup_strategies()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic cleanup error: {e}")
    
    async def _run_cleanup_strategies(self):
        """Run all cleanup strategies"""
        
        logger.debug("Running memory cleanup strategies")
        
        for strategy in self.cleanup_strategies:
            try:
                # Run in thread pool to avoid blocking
                await asyncio.get_event_loop().run_in_executor(self._executor, strategy)
            except Exception as e:
                logger.error(f"Cleanup strategy error: {e}")
        
        self.cleanup_count += 1
        logger.debug("Memory cleanup completed")
    
    async def _handle_high_pressure(self, stats: MemoryStats):
        """Handle high memory pressure"""
        
        logger.warning("High memory pressure detected, running cleanup strategies")
        await self._run_cleanup_strategies()
    
    async def _handle_critical_pressure(self, stats: MemoryStats):
        """Handle critical memory pressure"""
        
        logger.error("Critical memory pressure detected, aggressive cleanup")
        
        # Clear caches
        self.message_cache.clear()
        
        # Run cleanup strategies
        await self._run_cleanup_strategies()
        
        # Force additional garbage collection
        gc.collect()
    
    async def _handle_emergency_pressure(self, stats: MemoryStats):
        """Handle emergency memory pressure"""
        
        logger.critical("Emergency memory pressure detected, emergency cleanup")
        
        # Clear all caches
        self.message_cache.clear()
        
        if self.compressed_store:
            # Could clear compressed store if needed
            logger.warning("Consider clearing compressed storage under emergency conditions")
        
        # Force multiple garbage collections
        for _ in range(3):
            gc.collect()
        
        # Run cleanup strategies multiple times
        for _ in range(2):
            await self._run_cleanup_strategies()
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        
        stats = {
            'message_cache': self.message_cache.get_stats(),
            'weak_cache': self.weak_cache.get_stats(),
            'cleanup_count': self.cleanup_count,
            'total_memory_freed': self.total_memory_freed
        }
        
        if self.compressed_store:
            stats['compressed_store'] = self.compressed_store.get_stats()
        
        if self.monitor:
            current_stats = self.monitor.get_current_stats()
            stats['system_memory'] = current_stats.to_dict()
        
        return stats
    
    def get_recommendations(self) -> List[str]:
        """Get memory optimization recommendations"""
        
        recommendations = []
        stats = self.get_memory_stats()
        
        # Cache recommendations
        cache_stats = stats.get('message_cache', {})
        if cache_stats.get('hit_rate', 0) < 0.5:
            recommendations.append("Low cache hit rate - consider adjusting cache size or TTL")
        
        if cache_stats.get('memory_usage_mb', 0) > cache_stats.get('max_memory_mb', 0) * 0.9:
            recommendations.append("Cache memory usage high - consider increasing limits or cleanup")
        
        # System memory recommendations
        system_stats = stats.get('system_memory', {})
        memory_percent = system_stats.get('memory_percent', 0)
        
        if memory_percent > 80:
            recommendations.append("High system memory usage - consider scaling resources")
        
        # Compression recommendations
        if self.compressed_store:
            comp_stats = stats.get('compressed_store', {})
            compression_ratio = comp_stats.get('compression_ratio', 1.0)
            
            if compression_ratio > 0.8:
                recommendations.append("Low compression ratio - data may not benefit from compression")
        
        return recommendations


# Convenience functions

def create_memory_manager(max_cache_mb: int = 500) -> MemoryManager:
    """Create memory manager with reasonable defaults"""
    return MemoryManager(
        max_cache_memory_mb=max_cache_mb,
        enable_compression=True,
        enable_monitoring=True
    )

def get_memory_pressure() -> MemoryPressure:
    """Get current memory pressure level"""
    memory = psutil.virtual_memory()
    
    if memory.percent >= 98:
        return MemoryPressure.EMERGENCY
    elif memory.percent >= 95:
        return MemoryPressure.CRITICAL
    elif memory.percent >= 85:
        return MemoryPressure.HIGH
    elif memory.percent >= 70:
        return MemoryPressure.MEDIUM
    else:
        return MemoryPressure.LOW

def estimate_object_size(obj: Any) -> int:
    """Estimate memory size of an object"""
    try:
        size = sys.getsizeof(obj)
        
        # Add size of attributes for objects with __dict__
        if hasattr(obj, '__dict__'):
            size += sys.getsizeof(obj.__dict__)
            for value in obj.__dict__.values():
                size += sys.getsizeof(value)
        
        # Add size of items for containers
        if isinstance(obj, (list, tuple)):
            size += sum(sys.getsizeof(item) for item in obj)
        elif isinstance(obj, dict):
            size += sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in obj.items())
        elif isinstance(obj, set):
            size += sum(sys.getsizeof(item) for item in obj)
        
        return size
    except (TypeError, AttributeError):
        return 1024  # Default estimate


__all__ = [
    "MemoryPressure",
    "MemoryStats",
    "LRUCache",
    "WeakMessageCache", 
    "CompressedObjectStore",
    "MemoryMonitor",
    "MemoryManager",
    "create_memory_manager",
    "get_memory_pressure",
    "estimate_object_size",
]