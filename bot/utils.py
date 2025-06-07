"""
Utility functions for the Telegram bot.
"""

import asyncio
import hashlib
import json
from typing import Optional, Callable, Any, Dict
from telebot.async_telebot import AsyncTeleBot
import logging

logger = logging.getLogger(__name__)


class MessageUtils:
    """Utility functions for message handling."""

    @staticmethod
    async def send_typing_action(bot: AsyncTeleBot, chat_id: int) -> None:
        """
        Send typing action to show bot is processing.

        Args:
            bot: AsyncTeleBot instance
            chat_id: Chat ID to send typing action to
        """
        try:
            await bot.send_chat_action(chat_id, "typing")
        except Exception as e:
            logger.error(f"Failed to send typing action: {e}")

    @staticmethod
    async def safe_edit_message(
        bot: AsyncTeleBot, chat_id: int, message_id: int, text: str, **kwargs
    ) -> bool:
        """
        Safely edit a message with error handling.

        Args:
            bot: AsyncTeleBot instance
            chat_id: Chat ID
            message_id: Message ID to edit
            text: New message text
            **kwargs: Additional parameters for edit_message_text

        Returns:
            True if successful, False otherwise
        """
        try:
            await bot.edit_message_text(
                text, chat_id=chat_id, message_id=message_id, **kwargs
            )
            return True
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
            return False

    @staticmethod
    async def safe_reply(
        bot: AsyncTeleBot, message: Any, text: str, **kwargs
    ) -> Optional[Any]:
        """
        Safely reply to a message with error handling.

        Args:
            bot: AsyncTeleBot instance
            message: Original message object
            text: Reply text
            **kwargs: Additional parameters for reply_to

        Returns:
            Sent message object or None if failed
        """
        try:
            return await bot.reply_to(message, text, **kwargs)
        except Exception as e:
            logger.error(f"Failed to reply to message: {e}")
            return None

    @staticmethod
    def validate_command_args(command_text: str, min_args: int = 1) -> Optional[str]:
        """
        Validate and extract arguments from command text.

        Args:
            command_text: Full command text
            min_args: Minimum number of arguments required

        Returns:
            Arguments string or None if validation failed
        """
        parts = command_text.split(" ", 1)
        if len(parts) < min_args + 1:
            return None
        return parts[1].strip() if len(parts) > 1 else ""

    @staticmethod
    async def with_retry(
        func: Callable, max_retries: int = 3, delay: float = 1.0, *args, **kwargs
    ) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: Function to execute
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result or None if all retries failed
        """
        for attempt in range(max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Function failed after {max_retries} retries: {e}")
                    return None
                logger.error(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
        return None

    @staticmethod
    async def send_document_from_bytes(
        bot: AsyncTeleBot,
        chat_id: int,
        file_data: bytes,
        filename: str,
        caption: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Send a document from bytes data.

        Args:
            bot: AsyncTeleBot instance
            chat_id: Chat ID to send document to
            file_data: File data as bytes
            filename: Name for the file
            caption: Optional caption for the document

        Returns:
            Sent message object or None if failed
        """
        try:
            from io import BytesIO

            file_obj = BytesIO(file_data)
            file_obj.name = filename

            return await bot.send_document(
                chat_id=chat_id, document=file_obj, caption=caption
            )
        except Exception as e:
            logger.error(f"Failed to send document: {e}")
            return None


class ErrorMessages:
    """Standard error messages for the bot."""

    INVALID_REPO_FORMAT = (
        "❌ Invalid format. Please use:\n"
        "• <code>owner/repo</code>\n"
        "• <code>https://github.com/owner/repo</code>"
    )

    REPO_NOT_FOUND = "❌ Repository not found. Please check the repository name."

    USER_NOT_FOUND = "❌ User not found. Please check the username."

    MISSING_REPO_ARG = (
        "❌ Please specify a repository.\n\n"
        "💡 Example: <code>/repo microsoft/vscode</code>"
    )

    MISSING_USER_ARG = (
        "❌ Please specify a username.\n\n" "💡 Example: <code>/user torvalds</code>"
    )

    API_ERROR = "❌ An error occurred while fetching data. Please try again later."

    RATE_LIMIT_EXCEEDED = (
        "⚠️ Rate limit exceeded. Please wait a moment before trying again."
    )

    DOWNLOAD_FAILED = "❌ Download failed. Please try again later."

    FILE_TOO_LARGE = "❌ File is too large for direct download."


class LoadingMessages:
    """Loading messages for different operations."""

    FETCHING_REPO = "🔍 Fetching repository information..."
    FETCHING_USER = "🔍 Fetching user information..."
    PROCESSING = "⏳ Processing your request..."
    DOWNLOADING = "📥 Downloading file..."
    PREPARING_DOWNLOAD = "⏳ Preparing download..."


class CallbackDataManager:
    """Manages callback data with hash compression for Telegram's 64-byte limit."""

    _data_store: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def create_short_callback(cls, action: str, data: Dict[str, Any]) -> str:
        """Create a short callback data string using hash."""
        # Create a unique hash for the data
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.md5(data_str.encode()).hexdigest()[:8]

        # Store the full data
        cls._data_store[data_hash] = data

        # Return short callback format
        return f"{action}:{data_hash}"

    @classmethod
    def get_callback_data(cls, data_hash: str) -> Dict[str, Any]:
        """Retrieve full data from hash."""
        return cls._data_store.get(data_hash, {})

    @staticmethod
    def parse_repo_callback(callback_data: str) -> Optional[dict]:
        """
        Parse repository-related callback data.

        Args:
            callback_data: Callback data string

        Returns:
            Parsed data dictionary or None if parsing failed
        """
        try:
            parts = callback_data.split(":")
            if len(parts) < 2:
                return None

            action = parts[0]

            if action == "repo_home":
                owner, repo = parts[1].split("/")
                return {"action": "home", "owner": owner, "repo": repo}

            elif action in ["repo_tags", "repo_releases", "repo_contributors"]:
                owner, repo = parts[1].split("/")
                page = int(parts[2]) if len(parts) > 2 else 1
                return {
                    "action": action.replace("repo_", ""),
                    "owner": owner,
                    "repo": repo,
                    "page": page,
                }

            elif action == "repo_files":
                owner, repo = parts[1].split("/")
                return {"action": "files", "owner": owner, "repo": repo}

            return None

        except Exception as e:
            logger.error(f"Error parsing callback data: {e}")
            return None

    @staticmethod
    def parse_download_callback(callback_data: str) -> Optional[dict]:
        """
        Parse download-related callback data.

        Args:
            callback_data: Callback data string

        Returns:
            Parsed data dictionary or None if parsing failed
        """
        try:
            parts = callback_data.split(":")
            if len(parts) < 3 or parts[0] != "download_asset":
                return None

            return {
                "action": "download",
                "asset_id": parts[1],
                "asset_size": int(parts[2]),
            }

        except Exception as e:
            logger.error(f"Error parsing download callback data: {e}")
            return None
