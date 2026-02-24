"""Profession handler cog (mining, fishing, foraging)."""

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

# Profession window titles
PROFESSION_TITLES = ["Mining", "Fishing", "Foraging"]

# Profession completion titles
PROFESSION_DONE_TITLES = ["You caught a", "Mining Complete!", "You found a"]

# Profession start titles
PROFESSION_START_TITLES = ["You started mining!", "You cast your rod!", "You start foraging!"]

# Already in profession pattern
ALREADY_REGEX = re.compile(r"You are already (mining|foraging|fishing)", re.IGNORECASE)


class Profession(commands.Cog):
    """Cog for handling profession messages.

    Handles mining, fishing, and foraging activities.
    """

    def __init__(self, bot: "ISeKaiZBot") -> None:
        """Initialize the Profession cog.

        Args:
            bot: The bot instance.
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages for professions.

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
        await self._handle_profession_message(message, data, "create")

    @commands.Cog.listener()
    async def on_isekaid_message_edit(self, message: discord.Message) -> None:
        """Handle message edits for professions.

        Args:
            message: The edited message.
        """
        if self.bot.player.is_stopped():
            return

        data = message_extractor(message)
        await self._handle_profession_message(message, data, "update")

    async def _handle_profession_message(
        self,
        message: discord.Message,
        data,
        event_type: str,
    ) -> bool:
        """Process profession-related messages.

        Args:
            message: The Discord message.
            data: Extracted embed data.
            event_type: Either "create" or "update".

        Returns:
            True if the message was handled.
        """
        # Profession window opened (only on create)
        if data.title in PROFESSION_TITLES and event_type != "update":
            logger.info("Open new profession window")
            self.bot.player.prof_msg = message

            async def start_profession() -> dict:
                try:
                    if self.bot.player.prof_msg and self.bot.player.prof_msg.components:
                        await self.bot.player.prof_msg.components[0].children[0].click()
                except Exception as e:
                    logger.error(f"Click profession button failed: {e}")
                return {}

            task = Task(
                func=start_profession,
                expire_at=time.time() * 1000 + 30000,
                info="start profession",
                tag=TaskType.NP,
                rank=get_default_rank(TaskType.NP),
            )
            self.bot.controller.add_task(task, "prof")
            return True

        # Profession completed
        if any(title in data.title for title in PROFESSION_DONE_TITLES):
            logger.info(f"Profession finish ({data.title})")
            self.bot.controller.refresh_timer("prof")
            self._log_profession_gains(data)
            return True

        # Profession started
        if data.title in PROFESSION_START_TITLES:
            logger.info(f"Profession start ({data.title})")
            self.bot.controller.refresh_timer("prof")
            return True

        # Already in profession
        if ALREADY_REGEX.search(data.content):
            logger.info("Already in profession, attempting to leave...")

            async def leave_profession() -> dict:
                try:
                    if message.components:
                        await message.components[0].children[0].click()
                except Exception as e:
                    logger.error(f"Leave profession failed: {e}")
                return {}

            task = Task(
                func=leave_profession,
                expire_at=time.time() * 1000 + 30000,
                info="leave profession",
                tag=TaskType.NP,
                rank=get_default_rank(TaskType.NP),
            )
            self.bot.controller.add_task(task, "prof")
            return True

        return False

    def _log_profession_gains(self, data) -> None:
        """Log any item gains from profession.

        Args:
            data: Extracted embed data.
        """
        for field in data.fields:
            logger.info(f"Gain: {field.get('name', '')} - {field.get('value', '')}")


async def setup(bot: "ISeKaiZBot") -> None:
    """Setup function for loading the cog.

    Args:
        bot: The bot instance.
    """
    await bot.add_cog(Profession(bot))
