"""Scheduler cog for periodic routines."""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands, tasks

from routines.food import food_routine
from routines.inventory import inventory_routine
from routines.retainer import retainer_routine
from utils.logging import get_logger

if TYPE_CHECKING:
    from main import ISeKaiZBot

logger = get_logger(__name__)

# Intervals in seconds
ONE_HOUR = 60 * 60 + 20  # 1 hour + 20 seconds buffer
THREE_HOURS = 3 * 60 * 60 + 20  # 3 hours + 20 seconds buffer


class Scheduler(commands.Cog):
    """Cog for scheduling periodic routines.

    Manages timed routines for inventory selling, retainer collection,
    and food consumption.
    """

    def __init__(self, bot: "ISeKaiZBot") -> None:
        """Initialize the Scheduler cog.

        Args:
            bot: The bot instance.
        """
        self.bot = bot

    async def cog_load(self) -> None:
        """Called when cog is loaded - start routines."""
        logger.info("Starting scheduled routines...")

        # Run initial routines
        await self._one_hour_routine()
        await self._three_hour_routine()

        # Start loops
        self.one_hour_task.start()
        self.three_hour_task.start()

        logger.info("All routines started.")

    async def cog_unload(self) -> None:
        """Called when cog is unloaded - stop routines."""
        logger.info("Stopping scheduled routines...")
        self.one_hour_task.cancel()
        self.three_hour_task.cancel()

    @tasks.loop(seconds=ONE_HOUR)
    async def one_hour_task(self) -> None:
        """One hour routine task."""
        await self._one_hour_routine()

    @tasks.loop(seconds=THREE_HOURS)
    async def three_hour_task(self) -> None:
        """Three hour routine task."""
        await self._three_hour_routine()

    @one_hour_task.before_loop
    async def before_one_hour_task(self) -> None:
        """Wait for bot to be ready before starting one hour task."""
        await self.bot.wait_until_ready()

    @three_hour_task.before_loop
    async def before_three_hour_task(self) -> None:
        """Wait for bot to be ready before starting three hour task."""
        await self.bot.wait_until_ready()

    async def _one_hour_routine(self) -> None:
        """Execute one-hour scheduled tasks."""
        logger.info("Do 1-hour scheduling task")
        try:
            await retainer_routine(self.bot)
            await inventory_routine(self.bot)
        except Exception as e:
            logger.error(f"One hour routine error: {e}")

    async def _three_hour_routine(self) -> None:
        """Execute three-hour scheduled tasks."""
        logger.info("Do 3-hour scheduling task (Food)")
        try:
            await food_routine(self.bot)
        except Exception as e:
            logger.error(f"Three hour routine error: {e}")


async def setup(bot: "ISeKaiZBot") -> None:
    """Setup function for loading the cog.

    Args:
        bot: The bot instance.
    """
    await bot.add_cog(Scheduler(bot))
