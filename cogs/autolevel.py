"""Auto-level handler cog."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot.config import BATTLE_ZONES
from bot.event_manager import BotState
from bot.task_manager import Task, TaskType, get_default_rank
from utils.helpers import message_extractor, is_from_isekaid, is_in_channel
from utils.logging import get_logger

if TYPE_CHECKING:
    from main import ISeKaiZBot

logger = get_logger(__name__)


class AutoLevel(commands.Cog):
    """Cog for handling auto-level progression.

    Automatically advances to next monster and changes zones when needed.
    """

    def __init__(self, bot: "ISeKaiZBot") -> None:
        """Initialize the AutoLevel cog.

        Args:
            bot: The bot instance.
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages for auto-leveling.

        Args:
            message: The received message.
        """
        # Only process if auto-level is enabled
        if not self.bot.player.auto_level:
            return
        if self.bot.player.is_stopped():
            return
        if not is_from_isekaid(message):
            return
        if not is_in_channel(message, self.bot.config.channel_id):
            return

        data = message_extractor(message)
        await self._handle_autolevel(message, data)

    async def _handle_autolevel(
        self,
        message: discord.Message,
        data,
    ) -> bool:
        """Process auto-level related messages.

        Args:
            message: The Discord message.
            data: Extracted embed data.

        Returns:
            True if the message was handled.
        """
        # After defeating a monster, advance to next
        if "You Defeated A" in data.title:
            async def next_monster() -> dict:
                try:
                    if self.bot.player.battle_msg and self.bot.player.battle_msg.components:
                        # Button index 3 is "Next Monster"
                        await self.bot.player.battle_msg.components[0].children[3].click()
                except Exception as e:
                    logger.error(f"Next monster failed: {e}")
                return {}

            task = Task(
                func=next_monster,
                expire_at=time.time() * 1000 + 30000,
                info="next monster",
                tag=TaskType.CMD,
                rank=get_default_rank(TaskType.CMD),
            )
            self.bot.controller.add_task(task, "map")
            return True

        # Final location reached, change zone
        if "You are already at the final location of this area." in data.content:
            logger.info("Final location reached, changing area...")

            # Increment zone index
            self.bot.player.user_data.zone_index += 1

            # Check if all zones completed
            if self.bot.player.user_data.zone_index >= len(BATTLE_ZONES):
                logger.info("All zones cleared, stopping bot.")
                self.bot.controller.update_state(BotState.STOPPED)
                return True

            # Save progress
            self.bot.player.save_user_data()

            next_zone = BATTLE_ZONES[self.bot.player.user_data.zone_index]

            async def change_zone() -> dict:
                try:
                    if self.bot.player.battle_msg and self.bot.player.battle_msg.components:
                        # Select menu index 2 for zone selection
                        select = self.bot.player.battle_msg.components[2].children[0]
                        # Find the option matching next_zone
                        for option in select.options:
                            if option.label == next_zone:
                                await select.choose(option)
                                logger.info(
                                    f"Changed area to: {next_zone} "
                                    f"#{self.bot.player.user_data.zone_index}"
                                )
                                break
                except Exception as e:
                    logger.error(f"Change zone to {next_zone} failed: {e}")
                return {}

            task = Task(
                func=change_zone,
                expire_at=time.time() * 1000 + 30000,
                info="change battle zone",
                tag=TaskType.CMD,
                rank=get_default_rank(TaskType.CMD),
            )
            self.bot.controller.add_task(task, "map")
            return True

        return False


async def setup(bot: "ISeKaiZBot") -> None:
    """Setup function for loading the cog.

    Args:
        bot: The bot instance.
    """
    await bot.add_cog(AutoLevel(bot))
