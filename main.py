from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import discord
from discord.ext import commands

from bot import Config, Controller, Player
from services import CaptchaAI
from utils import get_logger, setup_logging

# Setup logging
setup_logging()
logger = get_logger(__name__)

# ASCII art welcome banner
WELCOME_BANNER = """
 _       __     __                        
 | |     / /__  / /________  ____ ___  ___ 
 | | /| / / _ \\/ / ___/ __ \\/ __ `__ \\/ _ \\
 | |/ |/ /  __/ / /__/ /_/ / / / / / /  __/
 |__/|__/\\___/_/\\___/\\____/_/ /_/ /_/\\___/ 
"""


class ISeKaiZBot(commands.Bot):
    """Main bot class for ISeKaiZ.

    Extends discord.py-self's Bot class with game-specific functionality.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the bot.

        Args:
            config: Bot configuration.
        """
        super().__init__(command_prefix="!", self_bot=True)

        self.config = config
        self.player: Player = Player.create(config.channel_id)
        self.player.enable_battle = config.enable_battle
        self.controller: Controller = Controller(self.player, config)
        self.captcha_ai: CaptchaAI | None = None

        # Store channel reference
        self._target_channel: discord.TextChannel | None = None

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        # Load captcha AI model
        try:
            self.captcha_ai = await CaptchaAI.create(self.config.captcha_model)
            logger.info("Captcha AI model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Captcha AI model: {e}")
            logger.warning("Bot will run without captcha solving capability")

        # Load cogs
        await self._load_cogs()

        # Start controller
        await self.controller.start()

    async def _load_cogs(self) -> None:
        """Load all cog extensions."""
        cogs = [
            "cogs.commands",
            "cogs.system",
            "cogs.verification",
            "cogs.battle",
            "cogs.autolevel",
            "cogs.profession",
            "cogs.inventory",
            "cogs.retainer",
            "cogs.treasure",
        ]

        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.debug(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")

        # Load routines
        try:
            await self.load_extension("routines.scheduler")
            logger.debug("Loaded routines scheduler")
        except Exception as e:
            logger.error(f"Failed to load routines: {e}")

    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        print(WELCOME_BANNER)
        logger.info(f"Logged in as {self.user.name}")

        # Store username in player
        self.player.username = self.user.name

        # Get target channel
        self._target_channel = self.get_channel(int(self.config.channel_id))
        if self._target_channel:
            self.player.channel = self._target_channel
            logger.info(f"Target channel: {self._target_channel.name}")

            # Auto-start (same as original JS behavior)
            # Use --no-auto-start flag to disable
            if "--no-auto-start" not in sys.argv:
                logger.info("Auto-starting bot...")
                await self._target_channel.send("!start")
        else:
            logger.warning(f"Could not find channel: {self.config.channel_id}")

    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages.

        Args:
            message: The received message.
        """
        # Process commands first (for our own commands)
        await self.process_commands(message)

        # Dispatch custom event for Isekaid messages in our channel
        if str(message.channel.id) == self.config.channel_id:
            if message.author and message.author.name == "Isekaid":
                logger.debug("Isekaid new message detected, dispatching event")
                self.dispatch("isekaid_message", message)

    async def on_message_edit(
        self,
        before: discord.Message,
        after: discord.Message,
    ) -> None:
        """Handle message edits.

        Args:
            before: Message before edit.
            after: Message after edit.
        """
        # Filter to only our channel and Isekaid messages
        if str(after.channel.id) != self.config.channel_id:
            return
        if not after.author or after.author.name != "Isekaid":
            return

        logger.debug(f"Isekaid message edit detected, dispatching event")
        # Dispatch custom event for cogs to handle
        self.dispatch("isekaid_message_edit", after)

    async def close(self) -> None:
        """Clean up when bot is closing."""
        logger.info("Bot shutting down...")
        await self.controller.stop()
        await super().close()


async def main() -> None:
    """Main entry point."""
    # Load config
    config_path = Path("config.json")
    if not config_path.exists():
        logger.error("config.json not found. Please create it from sample_config.json")
        sys.exit(1)

    try:
        config = Config.from_json(config_path)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        sys.exit(1)

    # Create and run bot
    bot = ISeKaiZBot(config)

    try:
        await bot.start(config.token)
    except discord.LoginFailure as e:
        logger.error(f"Failed to login: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
