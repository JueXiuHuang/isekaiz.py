"""Helper utilities for ISeKaiZ bot."""

from __future__ import annotations

import asyncio
import random
import string
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import discord

from utils.logging import get_logger

logger = get_logger(__name__)

# Isekaid bot user ID (for message filtering)
ISEKAID_BOT_NAME = "Isekaid"


@dataclass
class EmbedData:
    """Extracted data from a Discord message embed."""

    id: str = ""
    author: str = ""
    ref: Optional[Any] = None  # mentions
    title: str = ""
    desc: str = ""
    emb_ref: str = ""  # embed author name
    content: str = ""
    fields: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.fields is None:
            self.fields = []


def message_extractor(message: "discord.Message") -> EmbedData:
    """Extract relevant data from a Discord message.

    Args:
        message: The Discord message to extract from.

    Returns:
        EmbedData containing extracted fields.
    """
    embed = message.embeds[0] if message.embeds else None

    return EmbedData(
        id=str(message.id) if message.id else "",
        author=str(message.author.id) if message.author else "",
        ref=message.mentions,
        title=embed.title if embed and embed.title else "",
        desc=embed.description if embed and embed.description else "",
        emb_ref=embed.author.name if embed and embed.author else "",
        content=message.content or "",
        fields=[
            {"name": f.name, "value": f.value, "inline": f.inline}
            for f in (embed.fields if embed else [])
        ],
    )


def parse_embed(message: "discord.Message") -> Optional[EmbedData]:
    """Parse a message and return embed data if it has an embed.

    Args:
        message: The Discord message to parse.

    Returns:
        EmbedData if message has an embed, None otherwise.
    """
    if not message.embeds:
        return None
    return message_extractor(message)


async def delayer(
    min_delay_ms: int,
    max_delay_ms: int,
    detail: str = "",
) -> None:
    """Apply a random delay between min and max milliseconds.

    Args:
        min_delay_ms: Minimum delay in milliseconds.
        max_delay_ms: Maximum delay in milliseconds.
        detail: Optional detail string for logging.
    """
    delay_ms = random.randint(min_delay_ms, max_delay_ms)
    logger.debug(f"Delay: {delay_ms}ms {detail}")
    await asyncio.sleep(delay_ms / 1000)


def make_hash(length: int = 5) -> str:
    """Generate a random alphanumeric hash string.

    Args:
        length: Length of the hash string.

    Returns:
        Random alphanumeric string.
    """
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def is_from_isekaid(message: "discord.Message") -> bool:
    """Check if a message is from the Isekaid bot.

    Args:
        message: The Discord message to check.

    Returns:
        True if the message is from Isekaid.
    """
    if not message.author:
        return False
    return message.author.name == ISEKAID_BOT_NAME


def is_in_channel(message: "discord.Message", channel_id: str) -> bool:
    """Check if a message is in the specified channel.

    Args:
        message: The Discord message to check.
        channel_id: The channel ID to match.

    Returns:
        True if the message is in the specified channel.
    """
    return str(message.channel.id) == channel_id


def mentions_user(message: "discord.Message", user_id: str) -> bool:
    """Check if a message mentions a specific user.

    Args:
        message: The Discord message to check.
        user_id: The user ID to look for.

    Returns:
        True if the user is mentioned in the message or embed.
    """
    # Check direct mentions
    for mention in message.mentions:
        if str(mention.id) == user_id:
            return True

    # Check embed author
    if message.embeds:
        embed = message.embeds[0]
        if embed.author and embed.author.name:
            # Could contain username
            return user_id in str(embed.author)

    return False


def get_embed_field_value(
    message: "discord.Message",
    field_name: str,
) -> Optional[str]:
    """Get the value of a specific embed field by name.

    Args:
        message: The Discord message to search.
        field_name: The name of the field to find.

    Returns:
        The field value if found, None otherwise.
    """
    if not message.embeds:
        return None

    embed = message.embeds[0]
    for field in embed.fields:
        if field.name == field_name:
            return field.value

    return None


def contains_keywords(text: str, keywords: List[str]) -> bool:
    """Check if text contains any of the specified keywords.

    Args:
        text: The text to search in.
        keywords: List of keywords to look for.

    Returns:
        True if any keyword is found.
    """
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)
