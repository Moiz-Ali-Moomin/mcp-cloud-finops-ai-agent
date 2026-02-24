"""
OpsYield Utility Library.

Common helper functions used across all modules.
"""

import asyncio
import functools
import time
import logging
from typing import Any, Callable, Dict, Optional, TypeVar
from datetime import datetime, timedelta, timezone


T = TypeVar("T")
logger = logging.getLogger("opsyield.utils")


# ─────────────────────────────────────────────────────────────
# Retry Decorator (Sync + Async)
# ─────────────────────────────────────────────────────────────

def retry(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Retry decorator with exponential backoff.
    Works for both sync and async functions.

    Usage:
        @retry(max_attempts=3, delay_seconds=1.0)
        async def fetch_data():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        wait = delay_seconds * (backoff_factor ** (attempt - 1))
                        logger.warning(
                            f"Retry {attempt}/{max_attempts} for {func.__name__} "
                            f"after {wait:.1f}s — {e}"
                        )
                        await asyncio.sleep(wait)
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        wait = delay_seconds * (backoff_factor ** (attempt - 1))
                        logger.warning(
                            f"Retry {attempt}/{max_attempts} for {func.__name__} "
                            f"after {wait:.1f}s — {e}"
                        )
                        time.sleep(wait)
            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ─────────────────────────────────────────────────────────────
# Date Helpers
# ─────────────────────────────────────────────────────────────

def utc_now() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def days_ago(days: int) -> datetime:
    """Return a UTC datetime N days in the past."""
    return utc_now() - timedelta(days=days)


def date_range_str(days: int) -> tuple:
    """
    Return (start_str, end_str) in YYYY-MM-DD format for billing queries.
    """
    end = utc_now()
    start = end - timedelta(days=days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def iso_now() -> str:
    """Return current UTC time as ISO-8601 string."""
    return utc_now().isoformat()


# ─────────────────────────────────────────────────────────────
# Safe Data Access
# ─────────────────────────────────────────────────────────────

def safe_get(data: Dict, *keys, default: Any = None) -> Any:
    """
    Safely traverse nested dicts.

    Usage:
        val = safe_get(response, "data", "results", 0, "cost", default=0.0)
    """
    current = data
    for key in keys:
        try:
            if isinstance(current, dict):
                current = current[key]
            elif isinstance(current, (list, tuple)) and isinstance(key, int):
                current = current[key]
            else:
                return default
        except (KeyError, IndexError, TypeError):
            return default
    return current


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float safely, returning default on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_round(value: Any, decimals: int = 2, default: float = 0.0) -> float:
    """Round a value safely."""
    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return default


# ─────────────────────────────────────────────────────────────
# Batch Processing
# ─────────────────────────────────────────────────────────────

def chunk_list(items: list, chunk_size: int) -> list:
    """
    Split a list into chunks of specified size.

    Usage:
        for batch in chunk_list(resources, 50):
            process_batch(batch)
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


async def gather_with_limit(coros, limit: int = 5):
    """
    Run coroutines with a concurrency limit.

    Usage:
        results = await gather_with_limit(
            [fetch(url) for url in urls],
            limit=10,
        )
    """
    semaphore = asyncio.Semaphore(limit)

    async def limited(coro):
        async with semaphore:
            return await coro

    return await asyncio.gather(*[limited(c) for c in coros], return_exceptions=True)
