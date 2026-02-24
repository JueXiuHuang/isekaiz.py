"""Tests for bot/task_manager.py."""

from __future__ import annotations

import asyncio
import time

import pytest

from bot.task_manager import (
    Task,
    TaskManager,
    TaskType,
    TASK_SETTINGS,
    get_default_rank,
    get_task_limit,
)


class TestTaskType:
    """Tests for TaskType enum."""

    def test_all_types_exist(self):
        """Test that all expected task types exist."""
        types = [t.value for t in TaskType]
        assert "Verify" in types
        assert "NewBattle" in types
        assert "NewProfession" in types
        assert "Command" in types

    def test_settings_exist_for_all_types(self):
        """Test that settings exist for all task types."""
        for task_type in TaskType:
            assert task_type in TASK_SETTINGS


class TestTaskSettings:
    """Tests for task settings functions."""

    def test_get_default_rank_verify(self):
        """Test default rank for VERIFY type."""
        rank = get_default_rank(TaskType.VERIFY)
        assert rank == -999  # Highest priority

    def test_get_default_rank_command(self):
        """Test default rank for CMD type."""
        rank = get_default_rank(TaskType.CMD)
        assert rank == -998

    def test_get_default_rank_new_battle(self):
        """Test default rank for NB type."""
        rank = get_default_rank(TaskType.NB)
        assert rank == 3

    def test_get_task_limit_verify(self):
        """Test task limit for VERIFY type."""
        limit = get_task_limit(TaskType.VERIFY)
        assert limit == 999

    def test_get_task_limit_food(self):
        """Test task limit for FOOD type."""
        limit = get_task_limit(TaskType.FOOD)
        assert limit == 1


class TestTask:
    """Tests for Task class."""

    @pytest.fixture
    def simple_task(self):
        """Return a simple test task."""

        async def dummy_func():
            return {"result": "success"}

        return Task(
            func=dummy_func,
            expire_at=time.time() * 1000 + 60000,
            info="test task",
            tag=TaskType.CMD,
        )

    def test_task_creation(self, simple_task):
        """Test creating a task."""
        assert simple_task.info == "test task"
        assert simple_task.tag == TaskType.CMD
        assert simple_task.retry == 0

    def test_task_default_rank(self):
        """Test that default rank is set based on type."""

        async def dummy():
            pass

        task = Task(
            func=dummy,
            expire_at=time.time() * 1000 + 60000,
            info="test",
            tag=TaskType.VERIFY,
        )

        assert task.rank == -999

    def test_is_expired_false(self, simple_task):
        """Test is_expired returns False for future expiry."""
        assert simple_task.is_expired() is False

    def test_is_expired_true(self):
        """Test is_expired returns True for past expiry."""

        async def dummy():
            pass

        task = Task(
            func=dummy,
            expire_at=time.time() * 1000 - 1000,  # 1 second ago
            info="expired task",
            tag=TaskType.CMD,
        )

        assert task.is_expired() is True

    def test_task_comparison(self):
        """Test task comparison by rank."""

        async def dummy():
            pass

        task_high = Task(
            func=dummy,
            expire_at=time.time() * 1000 + 60000,
            info="high priority",
            tag=TaskType.VERIFY,  # rank -999
        )
        task_low = Task(
            func=dummy,
            expire_at=time.time() * 1000 + 60000,
            info="low priority",
            tag=TaskType.NBW,  # rank 4
        )

        assert task_high < task_low  # Lower rank = higher priority


class TestTaskManager:
    """Tests for TaskManager class."""

    @pytest.fixture
    def manager(self):
        """Return a fresh TaskManager."""
        return TaskManager(task_gap=100, task_bias=50, retry_count=2)

    def test_add_task_success(self, manager):
        """Test successfully adding a task."""

        async def dummy():
            pass

        task = Task(
            func=dummy,
            expire_at=time.time() * 1000 + 60000,
            info="test",
            tag=TaskType.CMD,
        )

        result = manager.add_task(task)

        assert result is True
        assert manager.queue_size == 1

    def test_add_task_limit_exceeded(self, manager):
        """Test that tasks are rejected when limit is exceeded."""

        async def dummy():
            pass

        # FOOD has limit of 1
        task1 = Task(
            func=dummy,
            expire_at=time.time() * 1000 + 60000,
            info="food 1",
            tag=TaskType.FOOD,
        )
        task2 = Task(
            func=dummy,
            expire_at=time.time() * 1000 + 60000,
            info="food 2",
            tag=TaskType.FOOD,
        )

        assert manager.add_task(task1) is True
        assert manager.add_task(task2) is False
        assert manager.queue_size == 1

    def test_clear(self, manager):
        """Test clearing the task queue."""

        async def dummy():
            pass

        task = Task(
            func=dummy,
            expire_at=time.time() * 1000 + 60000,
            info="test",
            tag=TaskType.CMD,
        )
        manager.add_task(task)

        manager.clear()

        assert manager.queue_size == 0

    def test_remove_by_type(self, manager):
        """Test removing tasks by type."""

        async def dummy():
            pass

        task_cmd = Task(
            func=dummy,
            expire_at=time.time() * 1000 + 60000,
            info="cmd task",
            tag=TaskType.CMD,
        )
        task_inv = Task(
            func=dummy,
            expire_at=time.time() * 1000 + 60000,
            info="inv task",
            tag=TaskType.INV,
        )

        manager.add_task(task_cmd)
        manager.add_task(task_inv)

        removed = manager.remove_by_type(TaskType.CMD)

        assert removed == 1
        assert manager.queue_size == 1

    @pytest.mark.asyncio
    async def test_check_and_execute(self, manager):
        """Test executing a task from the queue."""
        executed = []

        async def track_execution():
            executed.append(True)
            return {"done": True}

        task = Task(
            func=track_execution,
            expire_at=time.time() * 1000 + 60000,
            info="execute test",
            tag=TaskType.CMD,
        )
        manager.add_task(task)

        await manager.check_and_execute()

        assert len(executed) == 1
        assert manager.queue_size == 0

    @pytest.mark.asyncio
    async def test_expired_task_skipped(self, manager):
        """Test that expired tasks are skipped."""
        executed = []

        async def track_execution():
            executed.append(True)
            return {}

        task = Task(
            func=track_execution,
            expire_at=time.time() * 1000 - 1000,  # Already expired
            info="expired",
            tag=TaskType.CMD,
        )
        manager.add_task(task)

        await manager.check_and_execute()

        assert len(executed) == 0
        assert manager.queue_size == 0

    @pytest.mark.asyncio
    async def test_priority_order(self, manager):
        """Test that tasks are executed in priority order."""
        execution_order = []

        async def low_priority():
            execution_order.append("low")
            return {}

        async def high_priority():
            execution_order.append("high")
            return {}

        task_low = Task(
            func=low_priority,
            expire_at=time.time() * 1000 + 60000,
            info="low",
            tag=TaskType.NBW,  # rank 4
        )
        task_high = Task(
            func=high_priority,
            expire_at=time.time() * 1000 + 60000,
            info="high",
            tag=TaskType.VERIFY,  # rank -999
        )

        # Add low first, then high
        manager.add_task(task_low)
        manager.add_task(task_high)

        # Execute both
        await manager.check_and_execute()
        await manager.check_and_execute()

        # High priority should execute first
        assert execution_order == ["high", "low"]
