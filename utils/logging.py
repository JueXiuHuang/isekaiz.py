from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Default log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Color codes for terminal output
COLORS = {
    "DEBUG": "\033[36m",     # Cyan
    "INFO": "\033[32m",      # Green
    "WARNING": "\033[33m",   # Yellow
    "ERROR": "\033[31m",     # Red
    "CRITICAL": "\033[35m",  # Magenta
    "RESET": "\033[0m",
}


class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors to log levels for terminal output."""

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        if levelname in COLORS:
            record.levelname = f"{COLORS[levelname]}{levelname}{COLORS['RESET']}"
        return super().format(record)


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str | Path] = None,
    use_colors: bool = True,
) -> None:
    """Configure logging for the bot.

    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO).
        log_file: Optional path to a log file.
        use_colors: Whether to use colored output in terminal.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if use_colors and sys.stdout.isatty():
        console_formatter = ColoredFormatter(LOG_FORMAT, DATE_FORMAT)
    else:
        console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (usually __name__).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


class ItemLogger:
    """Logger for tracking item gains and statistics."""

    def __init__(self) -> None:
        self._logger = get_logger("items")
        self._gains: dict[str, int] = {}
        self._start_time: datetime = datetime.now()

    def log_gain(self, item_name: str, quantity: int = 1) -> None:
        """Log an item gain.

        Args:
            item_name: Name of the item gained.
            quantity: Number of items gained.
        """
        self._gains[item_name] = self._gains.get(item_name, 0) + quantity
        self._logger.info(f"+{quantity} {item_name}")

    def get_summary(self) -> dict[str, int]:
        """Get a summary of all item gains.

        Returns:
            Dictionary mapping item names to total quantities.
        """
        return self._gains.copy()

    def reset(self) -> None:
        """Reset the item tracking."""
        self._gains.clear()
        self._start_time = datetime.now()

    @property
    def runtime(self) -> float:
        """Get runtime in seconds since tracking started."""
        return (datetime.now() - self._start_time).total_seconds()
