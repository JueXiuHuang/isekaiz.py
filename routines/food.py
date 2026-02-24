"""Food consumption routine."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from bot.task_manager import Task, TaskType, get_default_rank
from utils.logging import get_logger

if TYPE_CHECKING:
    from main import ISeKaiZBot

logger = get_logger(__name__)

# Minimum time between eating (3 hours in milliseconds)
EAT_COOLDOWN_MS = 3 * 60 * 60 * 1000


async def food_routine(bot: "ISeKaiZBot") -> None:
    """Execute the food consumption routine.

    Checks if enough time has passed since last eating and sends
    the eat command if appropriate.

    Args:
        bot: The bot instance.
    """
    player = bot.player
    config = bot.config

    # Check cooldown
    last_eat_at = player.user_data.last_eat_at
    now_ms = time.time() * 1000

    if now_ms - last_eat_at < EAT_COOLDOWN_MS:
        from datetime import datetime

        last_eat_str = datetime.fromtimestamp(last_eat_at / 1000).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Last eat at {last_eat_str}, skip...")
        return

    # Create eat task
    async def eat_food() -> dict:
        if player.channel:
            await player.channel.send(f"$eat {config.exp_food}")

            # Update last eat time
            player.user_data.last_eat_at = int(time.time() * 1000)
            player.save_user_data()

            from datetime import datetime
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Ate food at {now_str}")

        return {"user_data": player.user_data}

    task = Task(
        func=eat_food,
        expire_at=time.time() * 1000 + 180000,
        info="Eat food",
        tag=TaskType.FOOD,
        rank=get_default_rank(TaskType.FOOD),
    )
    bot.controller.add_task(task)
