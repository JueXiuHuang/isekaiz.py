"""Event management for bot state transitions."""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Callable, Dict, List, Optional, Awaitable, Any

from utils.logging import get_logger

logger = get_logger(__name__)


class BotState(str, Enum):
    """Bot state enumeration matching player states."""

    INIT = "init"
    RUNNING = "running"
    DEFEATED = "defeated"
    BLOCKED = "blocked"
    BANNED = "banned"
    STOPPED = "stopped"


# Type alias for event callbacks
EventCallback = Callable[[], Awaitable[None] | None]


class BotEventManager:
    """Event manager for handling bot state transitions.

    Provides a simple event-driven architecture for state changes,
    allowing handlers to be registered and triggered for each state.
    """

    def __init__(self) -> None:
        """Initialize the event manager."""
        self._listeners: Dict[BotState, List[EventCallback]] = {
            state: [] for state in BotState
        }
        self._current_state: Optional[BotState] = None

    def on(self, state: BotState, callback: EventCallback) -> None:
        """Register a callback for a state event.

        Args:
            state: The state to listen for.
            callback: Function to call when state is triggered.
        """
        self._listeners[state].append(callback)

    def off(self, state: BotState, callback: EventCallback) -> None:
        """Remove a callback from a state event.

        Args:
            state: The state to remove listener from.
            callback: The callback function to remove.
        """
        if callback in self._listeners[state]:
            self._listeners[state].remove(callback)

    async def emit(self, state: BotState) -> None:
        """Emit a state event, triggering all registered callbacks.

        Args:
            state: The state event to emit.
        """
        logger.debug(f"Emitting state: {state.value}")
        self._current_state = state

        for callback in self._listeners[state]:
            try:
                result = callback()
                # Handle both sync and async callbacks
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error in {state.value} callback: {e}")

    def emit_sync(self, state: BotState) -> None:
        """Emit a state event synchronously (creates task for async callbacks).

        Args:
            state: The state event to emit.

        Note:
            This should be used carefully. Prefer emit() when in async context.
        """
        logger.debug(f"Emitting state (sync): {state.value}")
        self._current_state = state

        for callback in self._listeners[state]:
            try:
                result = callback()
                if asyncio.iscoroutine(result):
                    # Schedule coroutine to run
                    asyncio.create_task(result)
            except Exception as e:
                logger.error(f"Error in {state.value} callback: {e}")

    @property
    def current_state(self) -> Optional[BotState]:
        """Get the current state."""
        return self._current_state

    def clear_listeners(self, state: Optional[BotState] = None) -> None:
        """Clear all listeners for a state or all states.

        Args:
            state: Specific state to clear, or None to clear all.
        """
        if state is not None:
            self._listeners[state].clear()
        else:
            for s in BotState:
                self._listeners[s].clear()

    def setup(
        self,
        on_init: Optional[EventCallback] = None,
        on_running: Optional[EventCallback] = None,
        on_defeated: Optional[EventCallback] = None,
        on_blocked: Optional[EventCallback] = None,
        on_banned: Optional[EventCallback] = None,
        on_stopped: Optional[EventCallback] = None,
    ) -> None:
        """Convenience method to set up all state callbacks at once.

        Args:
            on_init: Callback for INIT state.
            on_running: Callback for RUNNING state.
            on_defeated: Callback for DEFEATED state.
            on_blocked: Callback for BLOCKED state.
            on_banned: Callback for BANNED state.
            on_stopped: Callback for STOPPED state.
        """
        callbacks = {
            BotState.INIT: on_init,
            BotState.RUNNING: on_running,
            BotState.DEFEATED: on_defeated,
            BotState.BLOCKED: on_blocked,
            BotState.BANNED: on_banned,
            BotState.STOPPED: on_stopped,
        }

        for state, callback in callbacks.items():
            if callback is not None:
                self.on(state, callback)
