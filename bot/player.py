"""Player state management for ISeKaiZ bot."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import discord

from utils.logging import get_logger

logger = get_logger(__name__)


class PlayerState(str, Enum):
    """Bot player states."""

    INIT = "init"
    RUNNING = "running"
    DEFEATED = "defeated"
    BLOCKED = "blocked"
    BANNED = "banned"
    STOPPED = "stopped"


@dataclass
class UserData:
    """Persistent user data stored on disk."""

    last_eat_at: int = 0
    zone_index: int = 0

    @classmethod
    def load(cls, path: str | Path = "user_data.json") -> "UserData":
        """Load user data from file.

        Args:
            path: Path to the user data JSON file.

        Returns:
            UserData instance with loaded values.
        """
        path = Path(path)
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(
                    last_eat_at=data.get("last_eat_at", 0),
                    zone_index=data.get("zone_index", 0),
                )
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"User data not found or invalid, creating default. Reason: {e}")

        return cls()

    def save(self, path: str | Path = "user_data.json") -> None:
        """Save user data to file.

        Args:
            path: Path to save the user data JSON file.
        """
        path = Path(path)
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
        except OSError as e:
            logger.error(f"Error saving user data: {e}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "last_eat_at": self.last_eat_at,
            "zone_index": self.zone_index,
        }


@dataclass
class Player:
    """Player state container.

    Holds all runtime state for the bot including message references,
    channel info, and persistent user data.
    """

    state: PlayerState = PlayerState.STOPPED
    channel: Optional["discord.TextChannel"] = None
    channel_id: str = ""
    username: str = ""

    # Message references for current activities
    battle_msg: Optional["discord.Message"] = None
    prof_msg: Optional["discord.Message"] = None
    verify_img: Optional[str] = None

    # Counters and flags
    sell: int = 0
    auto_level: bool = False

    # Persistent data
    user_data: UserData = field(default_factory=UserData.load)

    def is_stopped(self) -> bool:
        """Check if the player is in a stopped state.

        Returns:
            True if state is BANNED, DEFEATED, or STOPPED.
        """
        return self.state in (
            PlayerState.BANNED,
            PlayerState.DEFEATED,
            PlayerState.STOPPED,
        )

    def reset(self) -> None:
        """Reset transient state (messages, counters) but keep user_data."""
        self.battle_msg = None
        self.prof_msg = None
        self.verify_img = None
        self.sell = 0

    def save_user_data(self, path: str | Path = "user_data.json") -> None:
        """Save persistent user data to disk.

        Args:
            path: Path to save the user data JSON file.
        """
        self.user_data.save(path)

    @classmethod
    def create(cls, channel_id: str = "") -> "Player":
        """Create a new Player instance with loaded user data.

        Args:
            channel_id: Discord channel ID for the bot to operate in.

        Returns:
            New Player instance.
        """
        return cls(
            channel_id=channel_id,
            user_data=UserData.load(),
        )
