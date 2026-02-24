"""System message handler cog (energy, suspension detection)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot.event_manager import BotState
from utils.helpers import message_extractor, is_from_isekaid, is_in_channel
from utils.logging import get_logger

if TYPE_CHECKING:
    from main import ISeKaiZBot

logger = get_logger(__name__)


class System(commands.Cog):
    """Cog for handling system messages.

    Detects energy depletion and account suspension.
    """

    def __init__(self, bot: "ISeKaiZBot") -> None:
        """Initialize the System cog.

        Args:
            bot: The bot instance.
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages for system events.

        Args:
            message: The received message.
        """
        # Only process Isekaid messages in our channel
        if not is_from_isekaid(message):
            return
        if not is_in_channel(message, self.bot.config.channel_id):
            return

        data = message_extractor(message)
        await self._handle_system_message(data)

    async def _handle_system_message(self, data) -> bool:
        """Process system-related messages.

        Args:
            data: Extracted embed data.

        Returns:
            True if the message was handled.
        """
        # No energy
        if data.desc == "You don't have enough energy to battle!":
            logger.info(">>>NO ENERGY<<< Refreshing map and profession timers.")
            self.bot.controller.refresh_timer("map")
            self.bot.controller.refresh_timer("prof")
            return True

        # Account suspended
        if data.title == "Suspended":
            logger.warning(">>>ACCOUNT SUSPENDED<<< Bot stopping.")
            self.bot.controller.update_state(BotState.BANNED)
            return True

        return False


async def setup(bot: "ISeKaiZBot") -> None:
    """Setup function for loading the cog.

    Args:
        bot: The bot instance.
    """
    await bot.add_cog(System(bot))
