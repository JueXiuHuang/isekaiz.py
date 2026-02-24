"""Tests for bot/player.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bot.player import Player, PlayerState, UserData


class TestPlayerState:
    """Tests for PlayerState enum."""

    def test_all_states_exist(self):
        """Test that all expected states exist."""
        states = [s.value for s in PlayerState]
        assert "init" in states
        assert "running" in states
        assert "defeated" in states
        assert "blocked" in states
        assert "banned" in states
        assert "stopped" in states


class TestUserData:
    """Tests for UserData class."""

    def test_default_values(self):
        """Test default user data values."""
        user_data = UserData()
        assert user_data.last_eat_at == 0
        assert user_data.zone_index == 0

    def test_load_from_file(self, tmp_path: Path):
        """Test loading user data from file."""
        data_path = tmp_path / "user_data.json"
        data_path.write_text(json.dumps({"last_eat_at": 12345, "zone_index": 3}))

        user_data = UserData.load(data_path)

        assert user_data.last_eat_at == 12345
        assert user_data.zone_index == 3

    def test_load_missing_file(self, tmp_path: Path):
        """Test loading from non-existent file returns defaults."""
        user_data = UserData.load(tmp_path / "nonexistent.json")

        assert user_data.last_eat_at == 0
        assert user_data.zone_index == 0

    def test_load_invalid_json(self, tmp_path: Path):
        """Test loading invalid JSON returns defaults."""
        data_path = tmp_path / "bad_data.json"
        data_path.write_text("not valid json")

        user_data = UserData.load(data_path)

        assert user_data.last_eat_at == 0
        assert user_data.zone_index == 0

    def test_save(self, tmp_path: Path):
        """Test saving user data."""
        user_data = UserData(last_eat_at=99999, zone_index=5)
        data_path = tmp_path / "user_data.json"

        user_data.save(data_path)

        assert data_path.exists()
        loaded = json.loads(data_path.read_text())
        assert loaded["last_eat_at"] == 99999
        assert loaded["zone_index"] == 5

    def test_to_dict(self):
        """Test converting to dictionary."""
        user_data = UserData(last_eat_at=123, zone_index=2)
        data = user_data.to_dict()

        assert data["last_eat_at"] == 123
        assert data["zone_index"] == 2


class TestPlayer:
    """Tests for Player class."""

    def test_create(self):
        """Test creating a new player."""
        player = Player.create(channel_id="123456")

        assert player.channel_id == "123456"
        assert player.state == PlayerState.STOPPED
        assert player.channel is None
        assert player.battle_msg is None
        assert player.auto_level is False

    def test_is_stopped_when_stopped(self):
        """Test is_stopped returns True for STOPPED state."""
        player = Player()
        player.state = PlayerState.STOPPED

        assert player.is_stopped() is True

    def test_is_stopped_when_defeated(self):
        """Test is_stopped returns True for DEFEATED state."""
        player = Player()
        player.state = PlayerState.DEFEATED

        assert player.is_stopped() is True

    def test_is_stopped_when_banned(self):
        """Test is_stopped returns True for BANNED state."""
        player = Player()
        player.state = PlayerState.BANNED

        assert player.is_stopped() is True

    def test_is_stopped_when_running(self):
        """Test is_stopped returns False for RUNNING state."""
        player = Player()
        player.state = PlayerState.RUNNING

        assert player.is_stopped() is False

    def test_is_stopped_when_blocked(self):
        """Test is_stopped returns False for BLOCKED state."""
        player = Player()
        player.state = PlayerState.BLOCKED

        assert player.is_stopped() is False

    def test_reset(self):
        """Test resetting player state."""
        player = Player()
        player.battle_msg = "some_message"
        player.prof_msg = "some_prof_message"
        player.verify_img = "some_image"
        player.sell = 5

        player.reset()

        assert player.battle_msg is None
        assert player.prof_msg is None
        assert player.verify_img is None
        assert player.sell == 0
