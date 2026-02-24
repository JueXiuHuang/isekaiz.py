"""Task management with priority queue for ISeKaiZ bot."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from utils.logging import get_logger

logger = get_logger(__name__)


class TaskType(str, Enum):
    """Types of tasks with their identifiers."""

    VERIFY = "Verify"
    EVB = "EmojiVerifyBattle"
    EVP = "EmojiVerifyProfession"
    TREASURE = "Treasure"
    INV = "Inventory"
    FOOD = "Food"
    RETAINER = "Retainer"
    NB = "NewBattle"
    NBW = "NewBattleWindow"
    NP = "NewProfession"
    NPW = "NewProfessionWindow"
    CMD = "Command"


@dataclass
class TaskSetting:
    """Configuration for a task type."""

    rank: int  # Lower rank = higher priority
    limit: int  # Maximum concurrent tasks of this type


# Default settings for each task type
TASK_SETTINGS: Dict[TaskType, TaskSetting] = {
    TaskType.VERIFY: TaskSetting(rank=-999, limit=999),
    TaskType.CMD: TaskSetting(rank=-998, limit=999),
    TaskType.EVB: TaskSetting(rank=2, limit=1),
    TaskType.EVP: TaskSetting(rank=2, limit=1),
    TaskType.TREASURE: TaskSetting(rank=1, limit=999),
    TaskType.INV: TaskSetting(rank=1, limit=2),
    TaskType.FOOD: TaskSetting(rank=1, limit=1),
    TaskType.RETAINER: TaskSetting(rank=1, limit=3),
    TaskType.NB: TaskSetting(rank=3, limit=1),
    TaskType.NP: TaskSetting(rank=3, limit=1),
    TaskType.NBW: TaskSetting(rank=4, limit=1),
    TaskType.NPW: TaskSetting(rank=4, limit=1),
}


def get_default_rank(task_type: TaskType) -> int:
    """Get the default rank for a task type.

    Args:
        task_type: The type of task.

    Returns:
        Default rank value (lower = higher priority).
    """
    setting = TASK_SETTINGS.get(task_type)
    return setting.rank if setting else 5


def get_task_limit(task_type: TaskType) -> int:
    """Get the maximum concurrent task limit for a type.

    Args:
        task_type: The type of task.

    Returns:
        Maximum number of concurrent tasks allowed.
    """
    setting = TASK_SETTINGS.get(task_type)
    return setting.limit if setting else 1


# Type alias for task functions
TaskFunc = Callable[[], Awaitable[Any]]


@dataclass
class Task:
    """A task to be executed by the TaskManager.

    Tasks are prioritized by rank (lower = higher priority) and can
    expire if not executed within their time limit.
    """

    func: TaskFunc
    expire_at: float  # Unix timestamp in milliseconds
    info: str = ""
    tag: TaskType = TaskType.CMD
    rank: int = field(default=5)
    retry: int = 0

    def __post_init__(self) -> None:
        """Set default rank based on task type if not specified."""
        if self.rank == 5:  # Default value
            self.rank = get_default_rank(self.tag)

    def is_expired(self, time_now_ms: Optional[float] = None) -> bool:
        """Check if the task has expired.

        Args:
            time_now_ms: Current time in milliseconds. Uses current time if None.

        Returns:
            True if the task has expired.
        """
        if time_now_ms is None:
            time_now_ms = time.time() * 1000
        return self.expire_at < time_now_ms

    def __lt__(self, other: "Task") -> bool:
        """Compare tasks by rank for priority queue ordering."""
        return self.rank < other.rank


class TaskManager:
    """Manager for executing prioritized tasks with rate limiting.

    Handles task queuing, priority aging, expiration, and retry logic.
    """

    def __init__(
        self,
        on_task_complete: Optional[Callable[[Any], Awaitable[None] | None]] = None,
        task_gap: int = 2000,
        task_bias: int = 3000,
        retry_count: int = 2,
    ) -> None:
        """Initialize the TaskManager.

        Args:
            on_task_complete: Callback when a task completes successfully.
            task_gap: Minimum milliseconds between task executions.
            task_bias: Random additional delay (0 to bias) between tasks.
            retry_count: Maximum retry attempts for failed tasks.
        """
        self._queue: List[Task] = []
        self._task_type_counter: Dict[TaskType, int] = {}
        self._last_execute_at: float = 0
        self._gap: int = task_gap
        self._bias: int = task_bias
        self._retry_count: int = retry_count
        self._callback = on_task_complete
        self._lock = asyncio.Lock()
        self._running = False

    @property
    def queue_size(self) -> int:
        """Get the current queue size."""
        return len(self._queue)

    @property
    def is_running(self) -> bool:
        """Check if the task processor is currently running."""
        return self._running

    def add_task(self, task: Task) -> bool:
        """Add a task to the queue.

        Args:
            task: The task to add.

        Returns:
            True if the task was added, False if rejected due to limits.
        """
        logger.info(f"Try add task: <{task.info}>")

        # Check task type limit
        current_count = self._task_type_counter.get(task.tag, 0)
        if current_count >= get_task_limit(task.tag):
            logger.warning(f"Add fail: task limit reached for {task.tag.value}")
            return False

        self._queue.append(task)
        self._task_type_counter[task.tag] = current_count + 1
        logger.info(f"Add task success: <{task.info}>")
        return True

    def _priority_aging(self) -> None:
        """Apply priority aging to all tasks (decrease rank by 1)."""
        for task in self._queue:
            task.rank -= 1

    def _log_queue_status(self) -> None:
        """Log the current queue status for debugging."""
        if not self._queue:
            return
        logger.debug("Task queue info:")
        for task in self._queue:
            logger.debug(f"> {task.rank:3d} - {task.info}")

    async def _delay(self, min_ms: int, max_delta_ms: int, reason: str = "") -> None:
        """Apply a random delay.

        Args:
            min_ms: Minimum delay in milliseconds.
            max_delta_ms: Maximum additional random delay.
            reason: Reason for the delay (for logging).
        """
        import random

        delay_ms = min_ms + random.randint(0, max_delta_ms)
        if delay_ms > 0:
            logger.debug(f"Delaying {delay_ms}ms {reason}")
            await asyncio.sleep(delay_ms / 1000)

    async def check_and_execute(self) -> None:
        """Check the queue and execute the highest priority task.

        This method is safe to call repeatedly; it uses a lock to prevent
        concurrent execution.
        """
        if self._lock.locked():
            return

        async with self._lock:
            self._running = True
            try:
                await self._execute_next()
            finally:
                self._running = False

    async def _execute_next(self) -> None:
        """Execute the next task in the queue."""
        while self._queue:
            # Sort by priority (rank)
            self._queue.sort()
            self._log_queue_status()

            # Apply priority aging
            self._priority_aging()

            # Get next task
            task = self._queue.pop(0)
            self._task_type_counter[task.tag] = max(
                0, self._task_type_counter.get(task.tag, 1) - 1
            )

            logger.info(f"Checking task <{task.info}>")

            # Check expiration
            time_now_ms = time.time() * 1000
            if task.is_expired(time_now_ms):
                logger.warning(f"Task expired: <{task.info}>")
                continue

            # Check if it will expire before expected execution
            expected_execute_time = self._last_execute_at + self._gap + self._bias / 2
            if task.is_expired(expected_execute_time):
                logger.warning(f"Task will expire before execution: <{task.info}>")
                continue

            # Apply task gap delay if needed
            time_since_last = time_now_ms - self._last_execute_at
            if time_since_last < self._gap:
                gap_delay = self._gap - time_since_last
                logger.debug(f"Task gap delay: {gap_delay}ms")
                await asyncio.sleep(gap_delay / 1000)

            # Apply random bias delay
            await self._delay(0, self._bias, "(Task Bias)")

            # Execute the task
            try:
                result = await task.func()
                self._last_execute_at = time.time() * 1000

                # Call completion callback if set
                if self._callback:
                    callback_result = self._callback(result)
                    if asyncio.iscoroutine(callback_result):
                        await callback_result

                logger.info(f"Task completed: <{task.info}>")

            except Exception as e:
                logger.error(f"Task failed: <{task.info}> - {e}")

                # Retry if attempts remaining
                if task.retry < self._retry_count:
                    task.retry += 1
                    logger.info(f"Retrying task (attempt {task.retry + 1}): <{task.info}>")
                    self.add_task(task)

            # Only execute one task per call
            break

    def clear(self) -> None:
        """Clear all tasks from the queue."""
        self._queue.clear()
        self._task_type_counter.clear()
        logger.info("Task queue cleared")

    def remove_by_type(self, task_type: TaskType) -> int:
        """Remove all tasks of a specific type.

        Args:
            task_type: The type of tasks to remove.

        Returns:
            Number of tasks removed.
        """
        initial_count = len(self._queue)
        self._queue = [t for t in self._queue if t.tag != task_type]
        removed = initial_count - len(self._queue)
        self._task_type_counter[task_type] = 0
        logger.info(f"Removed {removed} tasks of type {task_type.value}")
        return removed
