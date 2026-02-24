"""Tests for cogs/battle.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBattleCog:
    """Tests for Battle cog."""

    @pytest.fixture
    def mock_bot(self, config, player, controller):
        """Create a mock bot instance."""
        bot = MagicMock()
        bot.config = config
        bot.player = player
        bot.controller = controller
        return bot

    @pytest.fixture
    def battle_cog(self, mock_bot):
        """Create Battle cog instance."""
        from cogs.battle import Battle

        return Battle(mock_bot)

    def test_ignores_stopped_player(self, battle_cog, mock_message):
        """Test that stopped players are ignored."""
        battle_cog.bot.player.state = MagicMock()
        battle_cog.bot.player.is_stopped = MagicMock(return_value=True)

    def test_ignores_non_isekaid_messages(self, battle_cog, mock_message):
        """Test that non-Isekaid messages are ignored."""
        mock_message.author.name = "SomeUser"

    @pytest.mark.asyncio
    async def test_battle_window_creates_task(self, battle_cog, mock_message, mock_embed):
        """Test that battle window message creates a task."""
        from bot.player import PlayerState

        mock_embed.title = "Current Floor: 5"
        mock_embed.description = "Select action"
        mock_message.embeds = [mock_embed]
        mock_message.author.name = "Isekaid"

        battle_cog.bot.player.state = PlayerState.RUNNING
        battle_cog.bot.player.is_stopped = MagicMock(return_value=False)
        battle_cog.bot.controller.add_task = MagicMock(return_value=True)

        # Simulate extracting data
        from utils.helpers import EmbedData

        data = EmbedData(
            title="Current Floor: 5",
            desc="Select action",
        )

        # The handler should add a task
        result = await battle_cog._handle_battle_message(mock_message, data)

        assert result is True
        battle_cog.bot.controller.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_battle_victory_refreshes_timer(self, battle_cog, mock_message):
        """Test that victory message refreshes timer."""
        from utils.helpers import EmbedData

        data = EmbedData(
            title="You Defeated A Goblin!",
            desc="Victory!",
            fields=[{"name": "EXP", "value": "+100", "inline": True}],
        )

        battle_cog.bot.controller.refresh_timer = MagicMock()

        result = await battle_cog._handle_battle_message(mock_message, data)

        assert result is True
        battle_cog.bot.controller.refresh_timer.assert_called_with("map")

    @pytest.mark.asyncio
    async def test_battle_defeat_updates_state(self, battle_cog, mock_message):
        """Test that defeat message updates state."""
        from bot.event_manager import BotState
        from utils.helpers import EmbedData

        data = EmbedData(
            title="Better Luck Next Time!",
            desc="You died",
        )

        battle_cog.bot.controller.update_state = MagicMock()

        result = await battle_cog._handle_battle_message(mock_message, data)

        assert result is True
        battle_cog.bot.controller.update_state.assert_called_with(BotState.DEFEATED)

    @pytest.mark.asyncio
    async def test_already_in_battle_creates_leave_task(self, battle_cog, mock_message):
        """Test that 'already in battle' message creates leave task."""
        from utils.helpers import EmbedData

        data = EmbedData(
            content="You are already in a battle",
        )

        mock_message.components = [MagicMock()]
        mock_message.components[0].children = [MagicMock()]
        battle_cog.bot.controller.add_task = MagicMock(return_value=True)

        result = await battle_cog._handle_battle_message(mock_message, data)

        assert result is True
        battle_cog.bot.controller.add_task.assert_called_once()
