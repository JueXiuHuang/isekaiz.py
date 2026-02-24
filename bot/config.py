"""Configuration management for ISeKaiZ bot."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal

# Battle zones ordered by level progression
BATTLE_ZONES: List[str] = [
    "Start Zone",           # 1-10
    "Myrkwood",             # 20-95
    "The Wildlands",        # 95-160
    "The Abyssal Depths",   # 160-205
    "Scorching Earth",      # 205-275
    "The Iron Mountains",   # 275-370
    "The Underworld",       # 370-500
    "Celestial Isle",       # 500-650
    "Whispering Desolation",# 650-800
    "Sunstone Summit",      # 800-1000
    "Ancient Planet",       # 1000-1200
    "Unholy Battlefield",   # 1200-1400
    "The Purgatory",        # 1400-1700
]

ProfessionType = Literal["none", "mine", "fish", "forage"]
EquipGrade = Literal["F", "E", "D", "C", "B", "A"]


@dataclass
class Config:
    """Bot configuration loaded from config.json."""

    # Required fields
    token: str
    channel_id: str

    # Optional fields with defaults
    profession: ProfessionType = "none"
    check_delay: int = 60000  # milliseconds
    task_gap: int = 2000      # milliseconds between tasks
    task_bias: int = 3000     # random bias added to task gap
    retry_count: int = 2
    treasure_hunter: bool = False
    treasure_guild: str = ""
    exp_food: str = "sushi-roll"
    captcha_model: str = "./model/captcha.onnx"
    sell_equip: List[EquipGrade] = field(default_factory=lambda: ["F", "E", "D"])
    trust_usr: List[str] = field(default_factory=list)
    craft_channel_id: str = ""
    craft_material: str = "Platinum"

    @classmethod
    def from_json(cls, path: str | Path = "config.json") -> "Config":
        """Load configuration from a JSON file.

        Args:
            path: Path to the JSON configuration file.

        Returns:
            Config instance with loaded values.

        Raises:
            FileNotFoundError: If the config file doesn't exist.
            json.JSONDecodeError: If the JSON is malformed.
            ValueError: If required fields are missing.
        """
        path = Path(path)
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate required fields
        if not data.get("token"):
            raise ValueError("'token' is required in config.json")
        if not data.get("channelId"):
            raise ValueError("'channelId' is required in config.json")

        # Map camelCase JSON keys to snake_case Python attributes
        return cls(
            token=data["token"],
            channel_id=data["channelId"],
            profession=data.get("profession", "none"),
            check_delay=data.get("checkDelay", 60000),
            task_gap=data.get("taskGap", 2000),
            task_bias=data.get("taskBias", 3000),
            retry_count=data.get("retryCount", 2),
            treasure_hunter=data.get("treasureHunter", False),
            treasure_guild=data.get("treasureGuild", ""),
            exp_food=data.get("expFood", "sushi-roll"),
            captcha_model=data.get("captchaModel", "./model/captcha.onnx"),
            sell_equip=data.get("sellEquip", ["F", "E", "D"]),
            trust_usr=data.get("trustUsr", []),
            craft_channel_id=data.get("craftChannelId", ""),
            craft_material=data.get("craftMaterial", "Platinum"),
        )

    def to_dict(self) -> dict:
        """Convert config to dictionary with camelCase keys for JSON serialization."""
        return {
            "token": self.token,
            "channelId": self.channel_id,
            "profession": self.profession,
            "checkDelay": self.check_delay,
            "taskGap": self.task_gap,
            "taskBias": self.task_bias,
            "retryCount": self.retry_count,
            "treasureHunter": self.treasure_hunter,
            "treasureGuild": self.treasure_guild,
            "expFood": self.exp_food,
            "captchaModel": self.captcha_model,
            "sellEquip": self.sell_equip,
            "trustUsr": self.trust_usr,
            "craftChannelId": self.craft_channel_id,
            "craftMaterial": self.craft_material,
        }

    def save(self, path: str | Path = "config.json") -> None:
        """Save configuration to a JSON file.

        Args:
            path: Path to save the JSON configuration file.
        """
        path = Path(path)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
