"""Tests for bot/event_manager.py."""

from __future__ import annotations

import asyncio

import pytest

from bot.event_manager import BotEventManager, BotState


class TestBotState:
    """Tests for BotState enum."""

    def test_all_states_exist(self):
        """Test that all expected states exist."""
        states = [s.value for s in BotState]
        assert "init" in states
        assert "running" in states
        assert "defeated" in states
        assert "blocked" in states
        assert "banned" in states
        assert "stopped" in states


class TestBotEventManager:
    """Tests for BotEventManager class."""

    @pytest.fixture
    def manager(self):
        """Return a fresh BotEventManager."""
        return BotEventManager()

    def test_register_callback(self, manager):
        """Test registering a callback."""
        callback_called = []

        def callback():
            callback_called.append(True)

        manager.on(BotState.INIT, callback)

        # Verify it's registered (internal check)
        assert len(manager._listeners[BotState.INIT]) == 1

    def test_remove_callback(self, manager):
        """Test removing a callback."""

        def callback():
            pass

        manager.on(BotState.INIT, callback)
        manager.off(BotState.INIT, callback)

        assert len(manager._listeners[BotState.INIT]) == 0

    @pytest.mark.asyncio
    async def test_emit_sync_callback(self, manager):
        """Test emitting event triggers sync callback."""
        callback_called = []

        def callback():
            callback_called.append(True)

        manager.on(BotState.INIT, callback)
        await manager.emit(BotState.INIT)

        assert len(callback_called) == 1

    @pytest.mark.asyncio
    async def test_emit_async_callback(self, manager):
        """Test emitting event triggers async callback."""
        callback_called = []

        async def callback():
            callback_called.append(True)

        manager.on(BotState.RUNNING, callback)
        await manager.emit(BotState.RUNNING)

        assert len(callback_called) == 1

    @pytest.mark.asyncio
    async def test_emit_multiple_callbacks(self, manager):
        """Test emitting triggers all registered callbacks."""
        results = []

        def callback1():
            results.append("cb1")

        def callback2():
            results.append("cb2")

        manager.on(BotState.STOPPED, callback1)
        manager.on(BotState.STOPPED, callback2)
        await manager.emit(BotState.STOPPED)

        assert "cb1" in results
        assert "cb2" in results

    @pytest.mark.asyncio
    async def test_emit_updates_current_state(self, manager):
        """Test that emitting updates current_state."""
        await manager.emit(BotState.RUNNING)

        assert manager.current_state == BotState.RUNNING

    def test_clear_listeners_specific_state(self, manager):
        """Test clearing listeners for specific state."""

        def callback():
            pass

        manager.on(BotState.INIT, callback)
        manager.on(BotState.RUNNING, callback)

        manager.clear_listeners(BotState.INIT)

        assert len(manager._listeners[BotState.INIT]) == 0
        assert len(manager._listeners[BotState.RUNNING]) == 1

    def test_clear_all_listeners(self, manager):
        """Test clearing all listeners."""

        def callback():
            pass

        for state in BotState:
            manager.on(state, callback)

        manager.clear_listeners()

        for state in BotState:
            assert len(manager._listeners[state]) == 0

    def test_setup(self, manager):
        """Test setup method registers all callbacks."""
        callbacks_called = set()

        def on_init():
            callbacks_called.add("init")

        def on_running():
            callbacks_called.add("running")

        manager.setup(on_init=on_init, on_running=on_running)

        assert len(manager._listeners[BotState.INIT]) == 1
        assert len(manager._listeners[BotState.RUNNING]) == 1
        # Others should be empty
        assert len(manager._listeners[BotState.DEFEATED]) == 0

    @pytest.mark.asyncio
    async def test_callback_error_handling(self, manager):
        """Test that errors in callbacks don't break emission."""
        results = []

        def bad_callback():
            raise ValueError("Test error")

        def good_callback():
            results.append("good")

        manager.on(BotState.INIT, bad_callback)
        manager.on(BotState.INIT, good_callback)

        # Should not raise
        await manager.emit(BotState.INIT)

        # Good callback should still run
        assert "good" in results
