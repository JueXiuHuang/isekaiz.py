"""Retainer handler cog (hired material collection)."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot.task_manager import Task, TaskType, get_default_rank
from utils.helpers import message_extractor
from utils.logging import get_logger

if TYPE_CHECKING:
    from main import ISeKaiZBot

logger = get_logger(__name__)

# Pattern to match retainer elapsed time (handles newlines in embed)
ELAPSED_REGEX = re.compile(r"Time elapsed: (\d+) hours?\s+Materials produced:", re.DOTALL)


class Retainer(commands.Cog):
    """Cog for handling retainer (hired) messages.

    Handles collecting materials from hired helpers.
    """

    def __init__(self, bot: "ISeKaiZBot") -> None:
        """Initialize the Retainer cog.

        Args:
            bot: The bot instance.
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_isekaid_message(self, message: discord.Message) -> None:
        """Handle new messages for retainer collection.

        Args:
            message: The new message from Isekaid.
        """
        if self.bot.player.is_stopped():
            return

        data = message_extractor(message)
        logger.debug(f"Retainer checking new message: {data.desc[:100] if data.desc else 'No desc'}...")
        await self._handle_retainer_update(message, data)

    @commands.Cog.listener()
    async def on_isekaid_message_edit(self, message: discord.Message) -> None:
        """Handle message edits for retainer collection.

        Args:
            message: The edited message.
        """
        if self.bot.player.is_stopped():
            return

        data = message_extractor(message)
        logger.debug(f"Retainer checking edited message: {data.desc[:100] if data.desc else 'No desc'}...")
        await self._handle_retainer_update(message, data)

    async def _handle_retainer_update(
        self,
        message: discord.Message,
        data,
    ) -> bool:
        """Process retainer-related message updates.

        Args:
            message: The Discord message.
            data: Extracted embed data.

        Returns:
            True if the message was handled.
        """
        # Check for elapsed time pattern
        if not data.desc:
            logger.debug("Retainer: No embed description found")
            return False

        match = ELAPSED_REGEX.search(data.desc)
        if not match:
            logger.debug(f"Retainer: Regex didn't match desc: {data.desc[:150]!r}")
            return False

        elapsed_hours = match.group(1)
        logger.debug(f"Retainer: Matched elapsed hours = {elapsed_hours}")

        # If elapsed is not 0, collect materials
        if elapsed_hours != "0":
            logger.info(f"Retainer has items to collect ({elapsed_hours}h). Attempting to harvest.")

            async def collect_materials() -> dict:
                try:
                    if message.components:
                        logger.debug(f"Components found: {len(message.components)} rows")
                        if message.components[0].children and len(message.components[0].children) > 2:
                            # Button index 2 is "Collect"
                            await message.components[0].children[2].click()
                            logger.info("Harvest material success")
                        else:
                            logger.error(f"Expected 3+ buttons, found {len(message.components[0].children) if message.components[0].children else 0}")
                    else:
                        logger.error("No components found on message")
                except Exception as e:
                    logger.error(f"Collect retainer material failed: {e}")
                return {}

            task = Task(
                func=collect_materials,
                expire_at=time.time() * 1000 + 120000,
                info="$hired Collect",
                tag=TaskType.RETAINER,
                rank=get_default_rank(TaskType.RETAINER),
            )
            self.bot.controller.add_task(task)
            return True

        # No items ready, turn to next page
        logger.info("Retainer page has no items ready, turning to next page.")

        async def next_page() -> dict:
            try:
                if message.components:
                    logger.debug(f"Components found: {len(message.components)} rows")
                    if message.components[0].children and len(message.components[0].children) > 1:
                        # Button index 1 is "Next Page"
                        await message.components[0].children[1].click()
                        logger.info("Turn to next page success")
                    else:
                        logger.error(f"Expected 2+ buttons, found {len(message.components[0].children) if message.components[0].children else 0}")
                else:
                    logger.error("No components found on message")
            except Exception as e:
                logger.error(f"Turn to next page failed: {e}")
            return {}

        task = Task(
            func=next_page,
            expire_at=time.time() * 1000 + 120000,
            info="$hired Next Page",
            tag=TaskType.RETAINER,
            rank=get_default_rank(TaskType.RETAINER),
        )
        self.bot.controller.add_task(task)

        return True


async def setup(bot: "ISeKaiZBot") -> None:
    """Setup function for loading the cog.

    Args:
        bot: The bot instance.
    """
    await bot.add_cog(Retainer(bot))
