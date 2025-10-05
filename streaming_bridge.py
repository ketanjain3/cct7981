"""
Simple task registry for ADK-Pipecat integration.
Allows ADK tools to call Pipecat task methods directly.
"""
import uuid
from typing import Optional, Dict
from loguru import logger

# Global registry of tasks (keyed by unique ID)
_tasks: Dict[str, any] = {}


def register_task(task) -> str:
    """
    Register a Pipecat task and return its unique ID.

    Args:
        task: PipelineTask instance to register

    Returns:
        str: Unique task ID to pass via session state
    """
    task_id = str(uuid.uuid4())
    _tasks[task_id] = task
    logger.debug(f"Registered task: {task_id[:8]}...")
    return task_id


def get_task(task_id: str):
    """
    Get task by ID.

    Args:
        task_id: Unique task identifier

    Returns:
        PipelineTask or None if not found
    """
    task = _tasks.get(task_id)
    if not task:
        logger.warning(f"Task {task_id[:8]}... not found")
    return task


def unregister_task(task_id: str):
    """
    Remove task by ID. Call after invocation completes.

    Args:
        task_id: Unique task identifier
    """
    if _tasks.pop(task_id, None):
        logger.debug(f"Unregistered task: {task_id[:8]}...")


def get_active_task_count() -> int:
    """Get number of registered tasks (for monitoring)."""
    return len(_tasks)
