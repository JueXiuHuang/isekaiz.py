"""Custom error classes for ISeKaiZ bot."""

from __future__ import annotations

from typing import List, Optional


class BotError(Exception):
    """Base exception for bot-related errors."""

    def __init__(self, message: str, recoverable: bool = True) -> None:
        """Initialize BotError.

        Args:
            message: Error message.
            recoverable: Whether the bot can recover from this error.
        """
        super().__init__(message)
        self.recoverable = recoverable


class TaskExpiredError(BotError):
    """Raised when a task has expired before execution."""

    def __init__(self, task_info: str = "") -> None:
        """Initialize TaskExpiredError.

        Args:
            task_info: Information about the expired task.
        """
        super().__init__(f"Task expired: {task_info}", recoverable=True)
        self.task_info = task_info


class VerificationError(BotError):
    """Raised when verification fails."""

    def __init__(
        self,
        message: str = "Verification failed",
        verification_type: str = "unknown",
    ) -> None:
        """Initialize VerificationError.

        Args:
            message: Error message.
            verification_type: Type of verification that failed.
        """
        super().__init__(message, recoverable=True)
        self.verification_type = verification_type


class CaptchaError(BotError):
    """Raised when captcha solving fails."""

    def __init__(self, message: str = "Captcha solving failed") -> None:
        """Initialize CaptchaError.

        Args:
            message: Error message.
        """
        super().__init__(message, recoverable=True)


class ConfigError(BotError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str) -> None:
        """Initialize ConfigError.

        Args:
            message: Error message.
        """
        super().__init__(message, recoverable=False)


class ChannelError(BotError):
    """Raised when channel operations fail."""

    def __init__(self, message: str, channel_id: Optional[str] = None) -> None:
        """Initialize ChannelError.

        Args:
            message: Error message.
            channel_id: The channel ID that caused the error.
        """
        super().__init__(message, recoverable=True)
        self.channel_id = channel_id


# Error skip list - errors matching these patterns will be silently ignored
SKIP_PATTERNS: List[str] = [
    "Unknown Message",
    "Missing Access",
    "Missing Permissions",
]


def should_skip_error(error: Exception) -> bool:
    """Check if an error should be skipped (not logged/raised).

    Args:
        error: The exception to check.

    Returns:
        True if the error should be skipped.
    """
    error_str = str(error)
    return any(pattern in error_str for pattern in SKIP_PATTERNS)


def handle_error(error: Exception, context: str = "") -> bool:
    """Handle an error with appropriate logging.

    Args:
        error: The exception to handle.
        context: Additional context about where the error occurred.

    Returns:
        True if the error was handled (recoverable), False otherwise.
    """
    from utils.logging import get_logger

    logger = get_logger("errors")

    if should_skip_error(error):
        return True

    if isinstance(error, BotError):
        if error.recoverable:
            logger.warning(f"{context}: {error}")
            return True
        else:
            logger.error(f"{context}: {error}")
            return False

    # Unknown error
    logger.exception(f"Unexpected error in {context}: {error}")
    return False
