"""Treasure hunter cog (cross-guild treasure chest collection)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot.task_manager import Task, TaskType, get_default_rank
from utils.helpers import message_extractor, is_from_isekaid
from utils.logging import get_logger

if TYPE_CHECKING:
    from main import ISeKaiZBot

logger = get_logger(__name__)


class Treasure(commands.Cog):
    """Cog for handling treasure chest spawns.

    Listens for treasure chests in a specific guild and claims them.
    """

    def __init__(self, bot: "ISeKaiZBot") -> None:
        """Initialize the Treasure cog.

        Args:
            bot: The bot instance.
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages for treasure chests.

        Args:
            message: The received message.
        """
        # Check if treasure hunting is enabled
        if not self.bot.config.treasure_hunter:
            return
        if not self.bot.config.treasure_guild:
            return

        # Check if message is from treasure guild
        if not message.guild or str(message.guild.id) != self.bot.config.treasure_guild:
            return

        if not is_from_isekaid(message):
            return

        data = message_extractor(message)
        await self._handle_treasure(message, data)

    async def _handle_treasure(
        self,
        message: discord.Message,
        data,
    ) -> bool:
        """Process treasure chest messages.

        Args:
            message: The Discord message.
            data: Extracted embed data.

        Returns:
            True if the message was handled.
        """
        # Treasure chest spawned
        if "Chest Spawned!" not in data.title:
            return False

        logger.info("Treasure chest spawned! Attempting to claim.")

        async def claim_chest() -> dict:
            try:
                if message.components:
                    await message.components[0].children[0].click()
            except Exception as e:
                logger.error(f"Claim chest failed: {e}")
            return {}

        task = Task(
            func=claim_chest,
            expire_at=time.time() * 1000 + 10000,
            info="collect treasure",
            tag=TaskType.TREASURE,
            rank=get_default_rank(TaskType.TREASURE),
        )
        self.bot.controller.add_task(task)

        return True


async def setup(bot: "ISeKaiZBot") -> None:
    """Setup function for loading the cog.

    Args:
        bot: The bot instance.
    """
    await bot.add_cog(Treasure(bot))
