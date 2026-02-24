"""Inventory handler cog (equipment selling)."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot.task_manager import Task, TaskType, get_default_rank
from utils.helpers import message_extractor, is_from_isekaid, is_in_channel
from utils.logging import get_logger

if TYPE_CHECKING:
    from main import ISeKaiZBot

logger = get_logger(__name__)


class Inventory(commands.Cog):
    """Cog for handling inventory messages.

    Handles equipment selling automation.
    """

    def __init__(self, bot: "ISeKaiZBot") -> None:
        """Initialize the Inventory cog.

        Args:
            bot: The bot instance.
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages for inventory.

        Args:
            message: The received message.
        """
        if self.bot.player.is_stopped():
            return
        if not is_from_isekaid(message):
            return
        if not is_in_channel(message, self.bot.config.channel_id):
            return

        data = message_extractor(message)
        await self._handle_inventory(data)

    async def _handle_inventory(self, data) -> bool:
        """Process inventory-related messages.

        Args:
            data: Extracted embed data.

        Returns:
            True if the message was handled.
        """
        # Equipment sold message
        if "Equipment Sold" not in data.title:
            return False

        # Log gains
        self._log_sell_gains(data)

        # Extract gold gained
        gold_match = re.search(r"You gained ([\d,]+)", data.desc.replace(",", ""))
        gold_gained = int(gold_match.group(1).replace(",", "")) if gold_match else 0

        # If low gold gained, move to next tier
        if gold_gained < 10000:
            self.bot.player.sell += 1

        # Check if all tiers sold
        sell_equip = self.bot.config.sell_equip
        if self.bot.player.sell >= len(sell_equip):
            logger.info("All equipment tiers sold")
            return True

        # Sell next tier
        next_tier = sell_equip[self.bot.player.sell]

        async def sell_next() -> dict:
            if self.bot.player.channel:
                await self.bot.player.channel.send(f"$sell equipment all {next_tier}")
            return {}

        task = Task(
            func=sell_next,
            expire_at=time.time() * 1000 + 120000,
            info="Sell equipment (next tier)",
            tag=TaskType.INV,
            rank=get_default_rank(TaskType.INV),
        )
        self.bot.controller.add_task(task)

        return True

    def _log_sell_gains(self, data) -> None:
        """Log gold gained from selling.

        Args:
            data: Extracted embed data.
        """
        logger.info(f"Sold equipment: {data.desc}")


async def setup(bot: "ISeKaiZBot") -> None:
    """Setup function for loading the cog.

    Args:
        bot: The bot instance.
    """
    await bot.add_cog(Inventory(bot))
