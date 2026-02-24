"""Bot control commands cog (!start, !stop, !autolevel)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from bot.event_manager import BotState
from utils.logging import get_logger

if TYPE_CHECKING:
    from main import ISeKaiZBot

logger = get_logger(__name__)


class Commands(commands.Cog):
    """Cog for handling bot control commands.

    Handles !start, !stop, and !autolevel commands from the user.
    """

    def __init__(self, bot: "ISeKaiZBot") -> None:
        """Initialize the Commands cog.

        Args:
            bot: The bot instance.
        """
        self.bot = bot

    @commands.command(name="start")
    async def start_bot(self, ctx: commands.Context) -> None:
        """Start the bot automation.

        Args:
            ctx: Command context.
        """
        # Only respond to our own commands
        if ctx.author.id != self.bot.user.id:
            return

        logger.info(">>>BOT START<<<")

        # Set the channel
        self.bot.player.channel = ctx.channel

        # Trigger init state
        self.bot.controller.update_state(BotState.INIT)

    @commands.command(name="stop")
    async def stop_bot(self, ctx: commands.Context) -> None:
        """Stop the bot automation.

        Args:
            ctx: Command context.
        """
        if ctx.author.id != self.bot.user.id:
            return

        logger.info(">>>BOT STOP<<<")
        self.bot.controller.update_state(BotState.STOPPED)

    @commands.command(name="autolevel")
    async def toggle_autolevel(self, ctx: commands.Context) -> None:
        """Toggle auto-level mode.

        Args:
            ctx: Command context.
        """
        if ctx.author.id != self.bot.user.id:
            return

        self.bot.player.auto_level = not self.bot.player.auto_level
        status = "ON" if self.bot.player.auto_level else "OFF"
        logger.info(f"Auto level is now {status}")

        await ctx.reply(f"Auto level is now {status}")

    @commands.command(name="status")
    async def show_status(self, ctx: commands.Context) -> None:
        """Show current bot status.

        Args:
            ctx: Command context.
        """
        if ctx.author.id != self.bot.user.id:
            return

        player = self.bot.player
        controller = self.bot.controller

        status_msg = (
            f"**State:** {player.state.value}\n"
            f"**Auto Level:** {'ON' if player.auto_level else 'OFF'}\n"
            f"**Zone Index:** {player.user_data.zone_index}\n"
            f"**Task Queue:** {controller.task_manager.queue_size} tasks\n"
        )

        await ctx.reply(status_msg)


async def setup(bot: "ISeKaiZBot") -> None:
    """Setup function for loading the cog.

    Args:
        bot: The bot instance.
    """
    await bot.add_cog(Commands(bot))
