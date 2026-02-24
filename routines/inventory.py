"""Inventory selling routine."""

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


async def inventory_routine(bot: "ISeKaiZBot") -> None:
    """Execute the inventory selling routine.

    Starts selling equipment of the configured tiers.

    Args:
        bot: The bot instance.
    """
    player = bot.player
    config = bot.config

    # Don't run if no channel or blocked
    if player.channel is None:
        return
    if _is_blocked(player.state):
        return

    # Reset sell counter
    player.sell = 0

    # Create sell task
    async def sell_equipment() -> dict:
        if player.channel and config.sell_equip:
            first_tier = config.sell_equip[0]
            await player.channel.send(f"$sell equipment all {first_tier}")
        return {}

    task = Task(
        func=sell_equipment,
        expire_at=time.time() * 1000 + 120000,
        info="Sell equipment",
        tag=TaskType.INV,
        rank=get_default_rank(TaskType.INV),
    )
    bot.controller.add_task(task)
