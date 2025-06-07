"""
Configuration settings for the GitHub Repository Preview Bot.
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot configuration class."""

    # Bot settings
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # GitHub API settings
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    GITHUB_API_BASE: str = "https://api.github.com"

    # Bot settings
    PARSE_MODE: str = "HTML"

    # Rate limiting
    GITHUB_RATE_LIMIT_WITHOUT_TOKEN: int = 60  # requests per hour
    GITHUB_RATE_LIMIT_WITH_TOKEN: int = 5000  # requests per hour

    # Request timeout
    REQUEST_TIMEOUT: int = 30

    # Download settings
    MAX_DOWNLOAD_SIZE_MB: int = 50  # Maximum file size for direct download
    ITEMS_PER_PAGE: int = 5  # Number of items to show per page

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        return True


# Global config instance
config = Config()
