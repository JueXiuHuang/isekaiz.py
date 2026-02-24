"""Tests for bot/config.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bot.config import Config, BATTLE_ZONES


class TestConfig:
    """Tests for Config class."""

    def test_load_from_json(self, sample_config_file: Path):
        """Test loading config from JSON file."""
        config = Config.from_json(sample_config_file)

        assert config.token == "test-token-12345"
        assert config.channel_id == "1234567890"
        assert config.profession == "mine"
        assert config.task_gap == 2000
        assert config.task_bias == 3000
        assert config.retry_count == 2
        assert config.sell_equip == ["F", "E", "D"]

    def test_missing_token_raises(self, tmp_path: Path):
        """Test that missing token raises ValueError."""
        config_path = tmp_path / "bad_config.json"
        config_path.write_text(json.dumps({"channelId": "123"}))

        with pytest.raises(ValueError, match="token"):
            Config.from_json(config_path)

    def test_missing_channel_id_raises(self, tmp_path: Path):
        """Test that missing channelId raises ValueError."""
        config_path = tmp_path / "bad_config.json"
        config_path.write_text(json.dumps({"token": "abc123"}))

        with pytest.raises(ValueError, match="channelId"):
            Config.from_json(config_path)

    def test_default_values(self, tmp_path: Path):
        """Test that default values are applied."""
        config_path = tmp_path / "minimal_config.json"
        config_path.write_text(
            json.dumps({"token": "abc123", "channelId": "123456"})
        )

        config = Config.from_json(config_path)

        assert config.profession == "none"
        assert config.task_gap == 2000
        assert config.task_bias == 3000
        assert config.retry_count == 2
        assert config.treasure_hunter is False
        assert config.exp_food == "sushi-roll"

    def test_to_dict(self, config: Config):
        """Test converting config to dictionary."""
        data = config.to_dict()

        assert data["token"] == config.token
        assert data["channelId"] == config.channel_id
        assert data["profession"] == config.profession
        assert data["taskGap"] == config.task_gap

    def test_save_config(self, config: Config, tmp_path: Path):
        """Test saving config to file."""
        save_path = tmp_path / "saved_config.json"
        config.save(save_path)

        assert save_path.exists()

        loaded = Config.from_json(save_path)
        assert loaded.token == config.token
        assert loaded.channel_id == config.channel_id

    def test_file_not_found(self, tmp_path: Path):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            Config.from_json(tmp_path / "nonexistent.json")

    def test_invalid_json(self, tmp_path: Path):
        """Test that JSONDecodeError is raised for invalid JSON."""
        config_path = tmp_path / "invalid.json"
        config_path.write_text("not valid json {")

        with pytest.raises(json.JSONDecodeError):
            Config.from_json(config_path)


class TestBattleZones:
    """Tests for BATTLE_ZONES constant."""

    def test_battle_zones_not_empty(self):
        """Test that battle zones list is not empty."""
        assert len(BATTLE_ZONES) > 0

    def test_battle_zones_contains_start_zone(self):
        """Test that Start Zone is first."""
        assert BATTLE_ZONES[0] == "Start Zone"

    def test_battle_zones_count(self):
        """Test expected number of battle zones."""
        assert len(BATTLE_ZONES) == 13
