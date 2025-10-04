"""
Thread-safe bridge for streaming communication between Google ADK and Pipecat.
Supports concurrent invocations with isolated per-session queues.
"""
import asyncio
import uuid
from typing import Optional, Dict
import time
from loguru import logger

# Global registry of queues (keyed by unique ID)
_queues: Dict[str, Dict[str, any]] = {}
_cleanup_interval = 300  # 5 minutes


def create_streaming_queue() -> str:
    """
    Create a new streaming queue and return its unique ID.

    Returns:
        queue_id (str): Unique identifier to be stored in session state
    """
    queue_id = str(uuid.uuid4())
    _queues[queue_id] = {
        'queue': asyncio.Queue(),
        'created_at': time.time()
    }
    logger.debug(f"Created streaming queue: {queue_id[:8]}...")
    _cleanup_old_queues()
    return queue_id


def get_streaming_queue(queue_id: str) -> Optional[asyncio.Queue]:
    """
    Get queue by ID. Thread-safe retrieval.

    Args:
        queue_id: Unique queue identifier

    Returns:
        asyncio.Queue or None if not found
    """
    entry = _queues.get(queue_id)
    if entry:
        return entry['queue']
    logger.warning(f"Queue {queue_id[:8]}... not found")
    return None


def clear_streaming_queue(queue_id: str):
    """
    Remove queue by ID. Call after invocation completes.

    Args:
        queue_id: Unique queue identifier
    """
    if _queues.pop(queue_id, None):
        logger.debug(f"Cleared streaming queue: {queue_id[:8]}...")


def _cleanup_old_queues():
    """
    Remove queues older than cleanup interval.
    Prevents memory leaks from abandoned invocations.
    """
    now = time.time()
    to_remove = [
        qid for qid, entry in _queues.items()
        if now - entry['created_at'] > _cleanup_interval
    ]
    for qid in to_remove:
        _queues.pop(qid, None)
        logger.warning(f"Cleaned up stale queue: {qid[:8]}...")

    if to_remove:
        logger.info(f"Cleaned up {len(to_remove)} stale queues")


def get_active_queue_count() -> int:
    """Get number of active queues (for monitoring)."""
    return len(_queues)
