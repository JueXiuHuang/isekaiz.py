"""Battle handler cog."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot.event_manager import BotState
from bot.task_manager import Task, TaskType, get_default_rank
from utils.helpers import message_extractor, is_from_isekaid, is_in_channel
from utils.logging import get_logger

if TYPE_CHECKING:
    from main import ISeKaiZBot

logger = get_logger(__name__)


class Battle(commands.Cog):
    """Cog for handling battle messages.

    Handles battle start, victory, defeat, and already-in-battle scenarios.
    """

    def __init__(self, bot: "ISeKaiZBot") -> None:
        """Initialize the Battle cog.

        Args:
            bot: The bot instance.
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages for battles.

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
        await self._handle_battle_message(message, data)

    async def _handle_battle_message(
        self,
        message: discord.Message,
        data,
    ) -> bool:
        """Process battle-related messages.

        Args:
            message: The Discord message.
            data: Extracted embed data.

        Returns:
            True if the message was handled.
        """
        # Battle window opened (Current Floor message)
        if "Current Floor:" in data.title:
            logger.info("Open new battle window")
            self.bot.player.battle_msg = message

            async def start_battle() -> dict:
                try:
                    if self.bot.player.battle_msg and self.bot.player.battle_msg.components:
                        await self.bot.player.battle_msg.components[0].children[0].click()
                except Exception as e:
                    logger.error(f"Start new battle failed: {e}")
                return {}

            task = Task(
                func=start_battle,
                expire_at=time.time() * 1000 + 30000,
                info="start new battle",
                tag=TaskType.NB,
                rank=get_default_rank(TaskType.NB),
            )
            self.bot.controller.add_task(task, "map")
            return True

        # Battle victory
        if "You Defeated A" in data.title:
            logger.info("Battle finish, refresh battle timer")
            self.bot.controller.refresh_timer("map")
            self._log_item_gains(data)
            return True

        # Battle started
        if "BATTLE STARTED" in data.title:
            logger.info("Battle start, refresh battle timer")
            self.bot.controller.refresh_timer("map")
            return True

        # Battle defeat
        if "Better Luck Next Time!" in data.title:
            logger.warning("You died, stopping the bot")
            self.bot.controller.update_state(BotState.DEFEATED)
            return True

        # Already in battle
        if "You are already in a battle" in data.content:
            logger.info("Already in battle, attempting to leave...")

            async def leave_battle() -> dict:
                try:
                    if message.components:
                        await message.components[0].children[0].click()
                except Exception as e:
                    logger.error(f"Leave battle failed: {e}")
                return {}

            task = Task(
                func=leave_battle,
                expire_at=time.time() * 1000 + 30000,
                info="leave battle",
                tag=TaskType.NP,
                rank=get_default_rank(TaskType.NP),
            )
            self.bot.controller.add_task(task, "map")
            return True

        return False

    def _log_item_gains(self, data) -> None:
        """Log any item gains from the battle.

        Args:
            data: Extracted embed data.
        """
        # Parse item gains from embed fields
        for field in data.fields:
            logger.info(f"Gain: {field.get('name', '')} - {field.get('value', '')}")


async def setup(bot: "ISeKaiZBot") -> None:
    """Setup function for loading the cog.

    Args:
        bot: The bot instance.
    """
    await bot.add_cog(Battle(bot))
