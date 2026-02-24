"""Main controller orchestrating bot operations."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import discord

from bot.config import Config
from bot.player import Player, PlayerState
from bot.event_manager import BotEventManager, BotState
from bot.task_manager import Task, TaskManager, TaskType, get_default_rank
from utils.logging import get_logger

logger = get_logger(__name__)

# Timer interval in seconds
TIMER_INTERVAL = 60


class Controller:
    """Central controller that orchestrates all bot operations.

    Manages the player state, task queue, event transitions, and
    recurring timers (map, profession, verify).
    """

    def __init__(self, player: Player, config: Config) -> None:
        """Initialize the controller.

        Args:
            player: The player state object.
            config: Bot configuration.
        """
        self.player = player
        self.config = config

        # Initialize task manager with config values
        self.task_manager = TaskManager(
            on_task_complete=self._task_complete_callback,
            task_gap=config.task_gap,
            task_bias=config.task_bias,
            retry_count=config.retry_count,
        )

        # Initialize event manager
        self.event_manager = BotEventManager()
        self.event_manager.setup(
            on_init=self._on_init,
            on_running=self._on_running,
            on_defeated=self._on_defeat,
            on_blocked=self._on_blocked,
            on_banned=self._on_ban,
            on_stopped=self._on_stopped,
        )

        self._current_state: Optional[BotState] = None
        self._timers: Dict[str, asyncio.Task] = {}
        self._check_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the controller's task execution loop."""
        logger.info("Controller starting...")

        # Start periodic task checking
        self._check_task = asyncio.create_task(self._check_loop())

    async def stop(self) -> None:
        """Stop the controller and clean up."""
        logger.info("Controller stopping...")

        # Cancel all timers
        self._cancel_all_timers()

        # Cancel the check loop
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
            self._check_task = None

        # Clear task queue
        self.task_manager.clear()

    async def _check_loop(self) -> None:
        """Periodically check and execute tasks."""
        while True:
            try:
                await self.task_manager.check_and_execute()
                await asyncio.sleep(1)  # Check every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in check loop: {e}")
                await asyncio.sleep(1)

    async def _task_complete_callback(self, result: Any) -> None:
        """Handle task completion and state transitions.

        Args:
            result: The result from the completed task.
        """
        if isinstance(result, dict):
            new_state = result.get("state")
            if new_state and new_state != self._current_state:
                self._current_state = new_state
                await self.event_manager.emit(new_state)

    def add_task(self, task: Task, timer_key: Optional[str] = None) -> bool:
        """Add a task to the queue and optionally restart a timer.

        Args:
            task: The task to add.
            timer_key: Optional timer key to restart ('map', 'prof', 'verify').

        Returns:
            True if the task was added successfully.
        """
        success = self.task_manager.add_task(task)

        if timer_key:
            self._add_timer_from_key(timer_key)

        return success

    def update_state(self, new_state: BotState) -> None:
        """Update the player state and emit state change event.

        Args:
            new_state: The new state to transition to.
        """
        logger.info(f"Current player state: {self.player.state.value}")

        if self._current_state != new_state:
            logger.info(f"Changing state to: {new_state.value}")
            self.player.state = PlayerState(new_state.value)
            self._current_state = new_state
            # Create task to emit event (non-blocking)
            asyncio.create_task(self.event_manager.emit(new_state))

    # Timer management

    def _add_timer_from_key(self, key: str) -> None:
        """Add or restart a timer by its key.

        Args:
            key: Timer key ('map', 'prof', 'verify').
        """
        self._cancel_timer(key)

        if key == "map":
            self._timers[key] = asyncio.create_task(
                self._timer_wrapper(key, self._map_recursion)
            )
        elif key == "prof":
            self._timers[key] = asyncio.create_task(
                self._timer_wrapper(key, self._prof_recursion)
            )
        elif key == "verify":
            self._timers[key] = asyncio.create_task(
                self._timer_wrapper(key, self._verify_recursion)
            )

    async def _timer_wrapper(self, key: str, callback) -> None:
        """Wrapper for timer callbacks with delay.

        Args:
            key: Timer key for logging.
            callback: The async callback to execute.
        """
        await asyncio.sleep(TIMER_INTERVAL)
        await callback()

    def _cancel_timer(self, key: str) -> None:
        """Cancel a timer by its key.

        Args:
            key: Timer key to cancel.
        """
        timer = self._timers.pop(key, None)
        if timer:
            timer.cancel()

    def _cancel_all_timers(self) -> None:
        """Cancel all active timers."""
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()

    def refresh_timer(self, key: str) -> None:
        """Refresh (restart) a timer.

        Args:
            key: Timer key to refresh.
        """
        self._cancel_timer(key)
        self._add_timer_from_key(key)

    # Recurring task creators

    def _create_repeating_task(self, command: str, task_type: TaskType) -> Task:
        """Create a task that sends a command to the channel.

        Args:
            command: The command string to send.
            task_type: The type of task.

        Returns:
            A new Task instance.
        """
        async def task_func() -> dict:
            if self.player.channel:
                await self.player.channel.send(command)
            return {}

        import time

        return Task(
            func=task_func,
            expire_at=time.time() * 1000 + 180000,  # 3 minutes
            info=command,
            tag=task_type,
            rank=get_default_rank(task_type),
        )

    async def _map_recursion(self) -> None:
        """Send $map command recursively."""
        self._cancel_timer("map")
        self.add_task(self._create_repeating_task("$map", TaskType.NBW))
        self._timers["map"] = asyncio.create_task(
            self._timer_wrapper("map", self._map_recursion)
        )

    async def _prof_recursion(self) -> None:
        """Send profession command recursively."""
        if self.config.profession == "none":
            return

        self._cancel_timer("prof")
        command = f"${self.config.profession}"
        self.add_task(self._create_repeating_task(command, TaskType.NPW))
        self._timers["prof"] = asyncio.create_task(
            self._timer_wrapper("prof", self._prof_recursion)
        )

    async def _verify_recursion(self) -> None:
        """Send $verify command recursively."""
        self._cancel_timer("verify")
        self.add_task(self._create_repeating_task("$verify", TaskType.VERIFY))
        self._timers["verify"] = asyncio.create_task(
            self._timer_wrapper("verify", self._verify_recursion)
        )

    # State event handlers

    async def _on_init(self) -> None:
        """Handle INIT state - start main loops."""
        self.update_state(BotState.RUNNING)
        await self._map_recursion()
        await self._prof_recursion()

    async def _on_running(self) -> None:
        """Handle RUNNING state."""
        pass  # No specific action needed

    async def _on_defeat(self) -> None:
        """Handle DEFEATED state - clean up."""
        self.player.reset()
        self._cancel_all_timers()

    async def _on_blocked(self) -> None:
        """Handle BLOCKED state - start verify loop."""
        await self._verify_recursion()

    async def _on_ban(self) -> None:
        """Handle BANNED state - clean up."""
        self.player.reset()
        self._cancel_all_timers()

    async def _on_stopped(self) -> None:
        """Handle STOPPED state - clean up."""
        self.player.reset()
        self._cancel_all_timers()
