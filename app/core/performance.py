"""
Performance optimization utilities for production environments.

This module provides performance enhancements including:
- Async database operations
- Caching helpers
- Query optimization
- Batch operations
- Background task management
"""

import asyncio
import functools
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, TypeVar

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class AsyncHelper:
    """Utilities for async operations and performance optimization."""

    # Thread pool for CPU-bound tasks
    _thread_pool: Optional[ThreadPoolExecutor] = None

    @classmethod
    def get_thread_pool(cls) -> ThreadPoolExecutor:
        """Get or create thread pool for CPU-bound operations."""
        if cls._thread_pool is None:
            cls._thread_pool = ThreadPoolExecutor(
                max_workers=4,  # Adjust based on CPU cores
                thread_name_prefix="uddhava_worker",
            )
        return cls._thread_pool

    @staticmethod
    async def run_in_thread(func: Callable[..., T], *args, **kwargs) -> T:
        """Run a blocking function in a thread pool."""
        loop = asyncio.get_event_loop()
        thread_pool = AsyncHelper.get_thread_pool()

        return await loop.run_in_executor(
            thread_pool, functools.partial(func, *args, **kwargs)
        )

    @staticmethod
    async def gather_with_concurrency(tasks: List[Callable], max_concurrency: int = 10):
        """
        Run multiple async tasks with concurrency limit.

        Args:
            tasks: List of async callables
            max_concurrency: Maximum concurrent tasks

        Returns:
            List of results
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        async def limited_task(task):
            async with semaphore:
                return await task()

        return await asyncio.gather(*[limited_task(task) for task in tasks])


class SimpleCache:
    """
    Simple in-memory cache with TTL support.

    For production, consider using Redis or Memcached.
    This is suitable for development and small deployments.
    """

    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict] = {}
        self._last_cleanup = time.time()
        self.cleanup_interval = 60  # Cleanup every minute

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments."""
        key_data = {"args": args, "kwargs": sorted(kwargs.items())}
        key_string = f"{prefix}:{json.dumps(key_data, sort_keys=True, default=str)}"
        # nosec: B324 - Used for cache key generation, not security
        return hashlib.md5(key_string.encode(), usedforsecurity=False).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        self._cleanup_expired()

        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry["expires_at"]:
                logger.debug(f"Cache hit: {key}")
                return entry["value"]
            else:
                # Expired
                del self._cache[key]
                logger.debug(f"Cache expired: {key}")

        logger.debug(f"Cache miss: {key}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time(),
        }
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache deleted: {key}")
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.debug("Cache cleared")

    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        now = time.time()

        # Only cleanup periodically to avoid overhead
        if now - self._last_cleanup < self.cleanup_interval:
            return

        expired_keys = [
            key for key, entry in self._cache.items() if now >= entry["expires_at"]
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        self._last_cleanup = now

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        self._cleanup_expired()
        total_size = sum(len(str(entry["value"])) for entry in self._cache.values())

        return {
            "entries": len(self._cache),
            "estimated_size_bytes": total_size,
            "oldest_entry_age_seconds": (
                (
                    time.time()
                    - min(
                        (entry["created_at"] for entry in self._cache.values()),
                        default=time.time(),
                    )
                )
                if self._cache
                else 0
            ),
        }


# Global cache instance
cache = SimpleCache(default_ttl=300)  # 5 minutes


def cached(ttl: int = 300, prefix: str = ""):
    """
    Decorator for caching function results.

    Args:
        ttl: Time to live in seconds
        prefix: Cache key prefix

    Usage:
        @cached(ttl=600, prefix="user")
        def get_user_by_id(db: Session, user_id: int):
            return db.query(User).filter(User.id == user_id).first()
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_prefix = prefix or func.__name__
            cache_key = cache._generate_key(cache_prefix, *args, **kwargs)

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            # Only cache if execution was successful
            if result is not None:
                cache.set(cache_key, result, ttl)
                logger.debug(
                    f"Function {func.__name__} executed in {execution_time:.3f}s, "
                    "result cached"
                )

            return result

        return wrapper

    return decorator


class BatchProcessor:
    """Utility for batch processing operations to improve performance."""

    @staticmethod
    def batch_database_inserts(
        session: Session,
        model_class,
        data_list: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> None:
        """
        Perform batch database inserts for better performance.

        Args:
            session: SQLAlchemy session
            model_class: SQLAlchemy model class
            data_list: List of data dictionaries to insert
            batch_size: Number of records per batch
        """
        total_records = len(data_list)
        logger.info(f"Starting batch insert of {total_records} records")

        for i in range(0, total_records, batch_size):
            batch = data_list[i : i + batch_size]

            try:
                # Use bulk_insert_mappings for performance
                session.bulk_insert_mappings(model_class, batch)
                session.commit()

                logger.debug(
                    f"Inserted batch {i//batch_size + 1}: {len(batch)} records"
                )

            except Exception as e:
                logger.error(f"Batch insert failed at batch {i//batch_size + 1}: {e}")
                session.rollback()
                raise

        logger.info(f"Completed batch insert of {total_records} records")

    @staticmethod
    async def async_batch_process(
        items: List[T],
        processor: Callable[[T], Any],
        batch_size: int = 10,
        max_workers: int = 4,
    ) -> List[Any]:
        """
        Process items in batches asynchronously.

        Args:
            items: Items to process
            processor: Function to process each item
            batch_size: Items per batch
            max_workers: Maximum concurrent workers

        Returns:
            List of processed results
        """
        results = []

        # Split items into batches
        batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

        async def process_batch(batch: List[T]) -> List[Any]:
            """Process a single batch."""
            return await AsyncHelper.run_in_thread(
                lambda: [processor(item) for item in batch]
            )

        # Process batches concurrently
        batch_results = await AsyncHelper.gather_with_concurrency(
            [lambda b=batch: process_batch(b) for batch in batches],
            max_concurrency=max_workers,
        )

        # Flatten results
        for batch_result in batch_results:
            results.extend(batch_result)

        return results


class DatabaseOptimizer:
    """Database query optimization utilities."""

    @staticmethod
    def get_query_stats(session: Session) -> Dict[str, Any]:
        """Get database performance statistics."""
        try:
            # MySQL specific queries
            queries = {
                "active_connections": "SHOW STATUS LIKE 'Threads_connected'",
                "slow_queries": "SHOW STATUS LIKE 'Slow_queries'",
                "queries_per_second": "SHOW STATUS LIKE 'Queries'",
            }

            stats = {}
            for name, query in queries.items():
                try:
                    result = session.execute(text(query)).fetchone()
                    if result:
                        stats[name] = result[1]
                except Exception as e:
                    logger.debug(f"Could not get {name}: {e}")
                    stats[name] = "N/A"

            return stats

        except Exception as e:
            logger.warning(f"Could not get database stats: {e}")
            return {"error": "Database stats unavailable"}

    @staticmethod
    def analyze_query_performance(session: Session, query: str) -> Dict[str, Any]:
        """Analyze query performance using EXPLAIN."""
        try:
            explain_result = session.execute(text(f"EXPLAIN {query}")).fetchall()
            return {
                "query": query,
                "execution_plan": [dict(row._mapping) for row in explain_result],
                "analyzed_at": time.time(),
            }
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return {"error": str(e)}
