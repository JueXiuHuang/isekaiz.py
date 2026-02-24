"""Retainer collection routine."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bot.player import PlayerState
from bot.task_manager import Task, TaskType, get_default_rank
from utils.logging import get_logger

if TYPE_CHECKING:
    from main import ISeKaiZBot

logger = get_logger(__name__)


def _is_blocked(state: PlayerState) -> bool:
    """Check if player is in a blocked state.

    Args:
        state: Current player state.

    Returns:
        True if player is blocked.
    """
    return state == PlayerState.BLOCKED


async def retainer_routine(bot: "ISeKaiZBot") -> None:
    """Execute the retainer collection routine.

    Sends the $hired command to check for materials to collect.

    Args:
        bot: The bot instance.
    """
    player = bot.player

    # Don't run if no channel or blocked
    if player.channel is None:
        return
    if _is_blocked(player.state):
        return

    # Create hired task
    async def check_hired() -> dict:
        if player.channel:
            await player.channel.send("$hired")
        return {}

    task = Task(
        func=check_hired,
        expire_at=time.time() * 1000 + 120000,
        info="$hired",
        tag=TaskType.RETAINER,
        rank=get_default_rank(TaskType.RETAINER),
    )
    bot.controller.add_task(task)
