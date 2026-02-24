"""Tests for cogs/commands.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestCommandsCog:
    """Tests for Commands cog."""

    @pytest.fixture
    def mock_bot(self, config, player, controller):
        """Create a mock bot instance."""
        bot = MagicMock()
        bot.config = config
        bot.player = player
        bot.controller = controller
        bot.user = MagicMock()
        bot.user.id = 123456789
        return bot

    @pytest.fixture
    def commands_cog(self, mock_bot):
        """Create Commands cog instance."""
        from cogs.commands import Commands

        return Commands(mock_bot)

    @pytest.fixture
    def mock_ctx(self, mock_bot):
        """Create a mock command context."""
        ctx = MagicMock()
        ctx.author = MagicMock()
        ctx.author.id = mock_bot.user.id  # Same as bot user
        ctx.channel = MagicMock()
        ctx.reply = AsyncMock()
        return ctx

    @pytest.mark.asyncio
    async def test_start_command_sets_channel(self, commands_cog, mock_ctx):
        """Test that !start sets the channel."""
        commands_cog.bot.controller.update_state = MagicMock()

        await commands_cog.start_bot.callback(commands_cog, mock_ctx)

        assert commands_cog.bot.player.channel == mock_ctx.channel

    @pytest.mark.asyncio
    async def test_start_command_triggers_init(self, commands_cog, mock_ctx):
        """Test that !start triggers INIT state."""
        from bot.event_manager import BotState

        commands_cog.bot.controller.update_state = MagicMock()

        await commands_cog.start_bot.callback(commands_cog, mock_ctx)

        commands_cog.bot.controller.update_state.assert_called_with(BotState.INIT)

    @pytest.mark.asyncio
    async def test_start_ignores_other_users(self, commands_cog, mock_ctx):
        """Test that !start ignores other users."""
        mock_ctx.author.id = 999999  # Different user

        commands_cog.bot.controller.update_state = MagicMock()

        await commands_cog.start_bot.callback(commands_cog, mock_ctx)

        commands_cog.bot.controller.update_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_command_triggers_stopped(self, commands_cog, mock_ctx):
        """Test that !stop triggers STOPPED state."""
        from bot.event_manager import BotState

        commands_cog.bot.controller.update_state = MagicMock()

        await commands_cog.stop_bot.callback(commands_cog, mock_ctx)

        commands_cog.bot.controller.update_state.assert_called_with(BotState.STOPPED)

    @pytest.mark.asyncio
    async def test_autolevel_toggles_on(self, commands_cog, mock_ctx):
        """Test that !autolevel toggles auto_level on."""
        commands_cog.bot.player.auto_level = False

        await commands_cog.toggle_autolevel.callback(commands_cog, mock_ctx)

        assert commands_cog.bot.player.auto_level is True
        mock_ctx.reply.assert_called_once()

    @pytest.mark.asyncio
    async def test_autolevel_toggles_off(self, commands_cog, mock_ctx):
        """Test that !autolevel toggles auto_level off."""
        commands_cog.bot.player.auto_level = True

        await commands_cog.toggle_autolevel.callback(commands_cog, mock_ctx)

        assert commands_cog.bot.player.auto_level is False
        mock_ctx.reply.assert_called_once()

    @pytest.mark.asyncio
    async def test_battle_toggles_on(self, commands_cog, mock_ctx):
        """Test that !battle toggles enable_battle on."""
        commands_cog.bot.player.enable_battle = False

        await commands_cog.toggle_battle.callback(commands_cog, mock_ctx)

        assert commands_cog.bot.player.enable_battle is True
        mock_ctx.reply.assert_called_once()

    @pytest.mark.asyncio
    async def test_battle_toggles_off(self, commands_cog, mock_ctx):
        """Test that !battle toggles enable_battle off."""
        commands_cog.bot.player.enable_battle = True

        await commands_cog.toggle_battle.callback(commands_cog, mock_ctx)

        assert commands_cog.bot.player.enable_battle is False
        mock_ctx.reply.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_command_replies(self, commands_cog, mock_ctx):
        """Test that !status replies with status."""
        commands_cog.bot.controller.task_manager = MagicMock()
        commands_cog.bot.controller.task_manager.queue_size = 5

        await commands_cog.show_status.callback(commands_cog, mock_ctx)

        mock_ctx.reply.assert_called_once()
        # Check that reply contains status info
        call_args = mock_ctx.reply.call_args[0][0]
        assert "State:" in call_args
