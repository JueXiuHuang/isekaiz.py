"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_config_data() -> Dict[str, Any]:
    """Return sample configuration data."""
    return {
        "token": "test-token-12345",
        "channelId": "1234567890",
        "profession": "mine",
        "checkDelay": 60000,
        "taskGap": 2000,
        "taskBias": 3000,
        "retryCount": 2,
        "treasureHunter": False,
        "treasureGuild": "",
        "expFood": "sushi-roll",
        "captchaModel": "./model/captcha.onnx",
        "sellEquip": ["F", "E", "D"],
        "trustUsr": ["405340108846530571"],
        "craftChannelId": "",
        "craftMaterial": "Platinum",
    }


@pytest.fixture
def sample_config_file(tmp_path: Path, sample_config_data: Dict[str, Any]) -> Path:
    """Create a temporary config file."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(sample_config_data))
    return config_path


@pytest.fixture
def config(sample_config_file: Path):
    """Return a loaded Config instance."""
    from bot.config import Config

    return Config.from_json(sample_config_file)


@pytest.fixture
def player():
    """Return a fresh Player instance."""
    from bot.player import Player

    return Player.create(channel_id="1234567890")


@pytest.fixture
def event_manager():
    """Return a fresh BotEventManager instance."""
    from bot.event_manager import BotEventManager

    return BotEventManager()


@pytest.fixture
def task_manager():
    """Return a fresh TaskManager instance."""
    from bot.task_manager import TaskManager

    return TaskManager()


@pytest.fixture
def controller(player, config):
    """Return a fresh Controller instance."""
    from bot.controller import Controller

    return Controller(player, config)


@pytest.fixture
def mock_message() -> MagicMock:
    """Return a mock Discord message."""
    message = MagicMock()
    message.id = 123456789
    message.content = ""
    message.channel = MagicMock()
    message.channel.id = 1234567890
    message.channel.send = AsyncMock()
    message.author = MagicMock()
    message.author.id = 999999999
    message.author.name = "Isekaid"
    message.embeds = []
    message.components = []
    message.mentions = []
    message.reply = AsyncMock()
    return message


@pytest.fixture
def mock_embed() -> MagicMock:
    """Return a mock Discord embed."""
    embed = MagicMock()
    embed.title = ""
    embed.description = ""
    embed.author = MagicMock()
    embed.author.name = ""
    embed.fields = []
    embed.image = None
    return embed


@pytest.fixture
def mock_button() -> MagicMock:
    """Return a mock Discord button."""
    button = MagicMock()
    button.click = AsyncMock()
    button.emoji = MagicMock()
    button.emoji.id = "12345"
    return button


@pytest.fixture
def sample_embed_data() -> Dict[str, Any]:
    """Return sample embed data for various scenarios."""
    return {
        "battle_window": {
            "title": "Current Floor: 5",
            "description": "Select your action",
        },
        "battle_victory": {
            "title": "You Defeated A Goblin!",
            "description": "You gained 100 EXP",
            "fields": [
                {"name": "EXP", "value": "+100", "inline": True},
                {"name": "Gold", "value": "+50", "inline": True},
            ],
        },
        "battle_defeat": {
            "title": "Better Luck Next Time!",
            "description": "You were defeated",
        },
        "verification_emoji": {
            "title": "Verification",
            "description": "Choose the correct option...",
        },
        "verification_captcha": {
            "title": "Verification",
            "description": "Please enter the captcha code from the image to verify.",
        },
        "verification_success": {
            "title": "Verification",
            "description": "Successfully Verified.",
        },
        "profession_mining": {
            "title": "Mining",
            "description": "Select a mining action",
        },
        "profession_complete": {
            "title": "Mining Complete!",
            "description": "You found Iron Ore",
        },
        "equipment_sold": {
            "title": "Equipment Sold",
            "description": "You gained 5,000 Gold",
        },
        "retainer_ready": {
            "title": "Hired Workers",
            "description": "Time elapsed: 3 hours\nMaterials produced: 10",
        },
        "treasure_spawn": {
            "title": "Chest Spawned!",
            "description": "A treasure chest has appeared!",
        },
        "no_energy": {
            "title": "",
            "description": "You don't have enough energy to battle!",
        },
        "suspended": {
            "title": "Suspended",
            "description": "Your account has been suspended",
        },
    }


def create_message_with_embed(embed_data: Dict[str, Any], mock_message: MagicMock) -> MagicMock:
    """Helper to create a message with embed data.

    Args:
        embed_data: Dictionary with title, description, fields.
        mock_message: Base mock message to modify.

    Returns:
        Modified mock message with embed.
    """
    embed = MagicMock()
    embed.title = embed_data.get("title", "")
    embed.description = embed_data.get("description", "")
    embed.author = MagicMock()
    embed.author.name = embed_data.get("author_name", "")
    embed.fields = [
        MagicMock(name=f["name"], value=f["value"], inline=f.get("inline", False))
        for f in embed_data.get("fields", [])
    ]
    embed.image = embed_data.get("image")

    mock_message.embeds = [embed]
    return mock_message
