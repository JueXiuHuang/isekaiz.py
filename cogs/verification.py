"""Verification handler cog (emoji and image captcha)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from bot.event_manager import BotState
from bot.task_manager import Task, TaskType, get_default_rank
from utils.helpers import message_extractor, is_from_isekaid, is_in_channel
from utils.logging import get_logger

if TYPE_CHECKING:
    from main import ISeKaiZBot

logger = get_logger(__name__)

# Emoji IDs for verification
X_EMOJI_ID = "1284730320133951592"
EMOJI_MAP = {
    "1285099666912055359": "Mine",
    "1284729698701541458": "Fish",
    "1285094197271199774": "Forage",
    "1285436059227783238": "Battle",
}


class Verification(commands.Cog):
    """Cog for handling verification messages.

    Handles emoji verification and image captcha challenges.
    """

    def __init__(self, bot: "ISeKaiZBot") -> None:
        """Initialize the Verification cog.

        Args:
            bot: The bot instance.
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages for verification.

        Args:
            message: The received message.
        """
        if not is_from_isekaid(message):
            return
        if not is_in_channel(message, self.bot.config.channel_id):
            return

        data = message_extractor(message)
        await self._handle_verification(message, data)

    async def _handle_verification(
        self,
        message: discord.Message,
        data,
    ) -> bool:
        """Process verification messages.

        Args:
            message: The Discord message.
            data: Extracted embed data.

        Returns:
            True if the message was handled.
        """
        # Emoji Verification
        if "Choose the correct option..." in data.desc:
            await self._handle_emoji_verification(message)
            return True

        # Skip if not addressed to us
        if data.emb_ref != self.bot.player.username:
            return False

        # Clear battle/profession messages during verification
        self.bot.player.battle_msg = None
        self.bot.player.prof_msg = None

        # Manual verification required
        if "Please complete the captcha" in data.desc:
            logger.warning(">>>BOT BLOCKED - Manual Verification Required<<<")
            self.bot.controller.update_state(BotState.BLOCKED)
            return True

        # Verification failed, retry
        if "Please Try doing $verify again." in data.desc:
            logger.info("Verification failed, trying again...")
            await self.bot.controller._verify_recursion()
            return True

        # Image captcha
        if "Please enter the captcha code from the image to verify." in data.desc:
            logger.warning(">>>BOT BLOCKED - Image Captcha<<<")
            await self._handle_image_captcha(message)
            return True

        # Verification successful
        if "Successfully Verified." in data.desc:
            logger.info(">>>VERIFICATION SUCCESSFUL - Resuming Bot<<<")
            self.bot.player.channel = message.channel
            self.bot.controller.update_state(BotState.INIT)
            return True

        return False

    async def _handle_emoji_verification(self, message: discord.Message) -> None:
        """Handle emoji verification challenge.

        Args:
            message: The verification message.
        """
        # Find the correct answer (button without X emoji)
        answer_index = 0
        emoji_type = "Unknown"

        if message.components:
            buttons = message.components[0].children
            for idx, button in enumerate(buttons):
                if hasattr(button, "emoji") and button.emoji:
                    emoji_id = str(button.emoji.id)
                    if emoji_id != X_EMOJI_ID:
                        answer_index = idx
                        emoji_type = EMOJI_MAP.get(emoji_id, "Unknown")
                        break

        # Determine task type and timer
        if emoji_type == "Battle":
            task_type = TaskType.EVB
            timer_key = "map"
        else:
            task_type = TaskType.EVP
            timer_key = "prof"

        logger.info(f"Emoji verification detected: {emoji_type}")

        # Create click task
        async def click_task() -> dict:
            try:
                await message.components[0].children[answer_index].click()
            except Exception as e:
                logger.error(f"Emoji verification click failed: {e}")
            return {}

        task = Task(
            func=click_task,
            expire_at=time.time() * 1000 + 30000,
            info=f"emoji verify: {emoji_type}",
            tag=task_type,
            rank=get_default_rank(task_type),
        )
        self.bot.controller.add_task(task, timer_key)

    async def _handle_image_captcha(self, message: discord.Message) -> None:
        """Handle image captcha challenge.

        Args:
            message: The captcha message.
        """
        # Store captcha image reference
        if message.embeds and message.embeds[0].image:
            self.bot.player.verify_img = message.embeds[0].image.url

        self.bot.controller.update_state(BotState.BLOCKED)

        # Check if captcha AI is available
        if not self.bot.captcha_ai:
            logger.error("Captcha AI not available - manual verification required")
            return

        # Create captcha solving task
        async def solve_captcha() -> dict:
            if not self.bot.player.verify_img:
                return {}

            result = await self.bot.captcha_ai.predict(self.bot.player.verify_img)
            logger.info(f"Captcha AI Result: {result}")

            if result and self.bot.player.channel:
                await self.bot.player.channel.send(result)

            return {}

        task = Task(
            func=solve_captcha,
            expire_at=time.time() * 1000 + 60000,
            info="send verify result",
            tag=TaskType.VERIFY,
            rank=get_default_rank(TaskType.VERIFY),
        )
        self.bot.controller.add_task(task, "verify")


async def setup(bot: "ISeKaiZBot") -> None:
    """Setup function for loading the cog.

    Args:
        bot: The bot instance.
    """
    await bot.add_cog(Verification(bot))
