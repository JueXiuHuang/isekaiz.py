"""Tests for cogs/verification.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestVerificationCog:
    """Tests for Verification cog."""

    @pytest.fixture
    def mock_bot(self, config, player, controller):
        """Create a mock bot instance."""
        bot = MagicMock()
        bot.config = config
        bot.player = player
        bot.controller = controller
        bot.captcha_ai = MagicMock()
        bot.captcha_ai.predict = AsyncMock(return_value="1234")
        return bot

    @pytest.fixture
    def verification_cog(self, mock_bot):
        """Create Verification cog instance."""
        from cogs.verification import Verification

        return Verification(mock_bot)

    @pytest.mark.asyncio
    async def test_emoji_verification_detects_correct_trigger(
        self, verification_cog, mock_message
    ):
        """Test that emoji verification is triggered correctly."""
        from utils.helpers import EmbedData

        data = EmbedData(
            desc="Choose the correct option...",
        )

        # Set up mock components with buttons
        button = MagicMock()
        button.emoji = MagicMock()
        button.emoji.id = "1285099666912055359"  # Mine emoji
        button.click = AsyncMock()

        mock_message.components = [MagicMock()]
        mock_message.components[0].children = [button]

        verification_cog.bot.controller.add_task = MagicMock(return_value=True)

        result = await verification_cog._handle_verification(mock_message, data)

        assert result is True

    @pytest.mark.asyncio
    async def test_image_captcha_triggers_ai(self, verification_cog, mock_message):
        """Test that image captcha triggers AI prediction."""
        from bot.player import PlayerState
        from utils.helpers import EmbedData

        verification_cog.bot.player.username = "TestUser"

        data = EmbedData(
            desc="Please enter the captcha code from the image to verify.",
            emb_ref="TestUser",
        )

        # Set up mock image
        mock_embed = MagicMock()
        mock_embed.image = MagicMock()
        mock_embed.image.url = "http://example.com/captcha.png"
        mock_message.embeds = [mock_embed]

        verification_cog.bot.controller.update_state = MagicMock()
        verification_cog.bot.controller.add_task = MagicMock(return_value=True)

        result = await verification_cog._handle_verification(mock_message, data)

        assert result is True

    @pytest.mark.asyncio
    async def test_verification_success_triggers_init(
        self, verification_cog, mock_message
    ):
        """Test that successful verification triggers INIT state."""
        from bot.event_manager import BotState
        from utils.helpers import EmbedData

        verification_cog.bot.player.username = "TestUser"

        data = EmbedData(
            desc="Successfully Verified.",
            emb_ref="TestUser",
        )

        verification_cog.bot.controller.update_state = MagicMock()

        result = await verification_cog._handle_verification(mock_message, data)

        assert result is True
        verification_cog.bot.controller.update_state.assert_called_with(BotState.INIT)

    @pytest.mark.asyncio
    async def test_manual_verification_blocks(self, verification_cog, mock_message):
        """Test that manual verification triggers BLOCKED state."""
        from bot.event_manager import BotState
        from utils.helpers import EmbedData

        verification_cog.bot.player.username = "TestUser"

        data = EmbedData(
            desc="Please complete the captcha",
            emb_ref="TestUser",
        )

        verification_cog.bot.controller.update_state = MagicMock()

        result = await verification_cog._handle_verification(mock_message, data)

        assert result is True
        verification_cog.bot.controller.update_state.assert_called_with(BotState.BLOCKED)

    @pytest.mark.asyncio
    async def test_ignores_other_user_messages(self, verification_cog, mock_message):
        """Test that messages for other users are ignored."""
        from utils.helpers import EmbedData

        verification_cog.bot.player.username = "TestUser"

        data = EmbedData(
            desc="Please complete the captcha",
            emb_ref="OtherUser",  # Not for us
        )

        result = await verification_cog._handle_verification(mock_message, data)

        assert result is False
