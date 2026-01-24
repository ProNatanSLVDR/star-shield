"""
Custom logging formatters for the starshield project.
"""

import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages with structured display."""

    # ANSI color codes for log levels
    LEVEL_COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }

    # Short level names (max 5 chars)
    LEVEL_SHORT_NAMES = {
        "DEBUG": "DEBUG",
        "INFO": "INFO",
        "WARNING": "WARN",
        "ERROR": "ERROR",
        "CRITICAL": "CRIT",
    }

    # ANSI color codes for other components
    TIMESTAMP_COLOR = "\033[90m"  # Dim gray
    LOGGER_COLOR = "\033[94m"  # Bright blue
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        # Check if terminal supports colors
        use_colors = sys.stdout.isatty()

        # Format timestamp (use datefmt if set, otherwise default)
        datefmt = getattr(self, "datefmt", None)
        timestamp = self.formatTime(record, datefmt)

        # Get level name and color
        level_name = record.levelname
        level_display = self.LEVEL_SHORT_NAMES.get(level_name, level_name[:5])
        level_color = self.LEVEL_COLORS.get(level_name, "")

        # Get logger name
        logger_name = record.name.split(".")[-1]

        # Get message
        message = record.getMessage()

        # Build formatted output
        if use_colors:
            # Apply colors to each component
            timestamp_part = f"{self.TIMESTAMP_COLOR}[{timestamp}]{self.RESET}"
            level_part = f"{level_color}{self.BOLD}{level_display:5s}{self.RESET}"
            logger_part = f"{self.LOGGER_COLOR}{logger_name:14s}{self.RESET}"
            separator = f"{self.TIMESTAMP_COLOR} | {self.RESET}"

            formatted = f"{timestamp_part} {level_part}{separator}{logger_part}{separator}{message}"
        else:
            # No colors, just structured format
            formatted = f"[{timestamp}] {level_display:5s} | {logger_name} | {message}"

        # Handle exception info if present
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted
