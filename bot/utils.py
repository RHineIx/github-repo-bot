"""
Utility functions for the Telegram bot.
"""

import asyncio
import hashlib
import json
from typing import Optional, Callable, Any, Dict
from telebot.async_telebot import AsyncTeleBot
import logging
import re
import time # Add this import at the top of the file
from collections import OrderedDict # Add this import as well

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
    """Manages callback data with hash compression and automatic cleanup."""

    _data_store: Dict[str, tuple] = OrderedDict() # Use OrderedDict to easily remove old items
    _MAX_ITEMS = 1000  # Max items before forcing cleanup
    _TTL_SECONDS = 24 * 60 * 60  # Keep data for 24 hours

    @classmethod
    def _cleanup(cls):
        """Remove expired and excess items from the data store."""
        # Remove expired items
        now = time.time()
        expired_keys = [
            key for key, (timestamp, _) in cls._data_store.items()
            if now - timestamp > cls._TTL_SECONDS
        ]
        for key in expired_keys:
            del cls._data_store[key]

        # If store is still too large, remove the oldest items
        while len(cls._data_store) > cls._MAX_ITEMS:
            cls._data_store.popitem(last=False) # Removes the first (oldest) item

    @classmethod
    def create_short_callback(cls, action: str, data: Dict[str, Any]) -> str:
        """Create a short callback data string using hash."""
        # Perform cleanup periodically
        if len(cls._data_store) % 100 == 0:
            cls._cleanup()

        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.md5(data_str.encode()).hexdigest()[:8]

        # Store the full data with a timestamp
        cls._data_store[data_hash] = (time.time(), data)

        return f"{action}:{data_hash}"

    @classmethod
    def get_callback_data(cls, data_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve full data from hash."""
        stored = cls._data_store.get(data_hash)
        if stored:
            return stored[1] # Return the actual data dictionary
        return None
class TrackCommandParser:  
    """Parser for the enhanced /track command syntax."""  
      
    @staticmethod  
    def parse_track_command(command_text: str) -> Optional[dict]:  
        """  
        Parse the enhanced /track command syntax.  
          
        Examples:  
        - /track microsoft/vscode [releases,issues]  
        - /track microsoft/vscode [releases] > -1001234567890  
        - /track microsoft/vscode [issues] > -1001234567890/123  
          
        Returns:  
            Dict with parsed components or None if invalid  
        """  
        # Remove /track command prefix  
        args = command_text.replace('/track', '').strip()  
          
        # Pattern to match: owner/repo [preferences] [> destination]  
        pattern = r'^([^/\s]+/[^/\s\[]+)\s*\[([^\]]+)\](?:\s*>\s*(.+))?$'  
        match = re.match(pattern, args)  
          
        if not match:  
            return None  
              
        repo_path, preferences_str, destination = match.groups()  
          
        # Parse repository  
        repo_parts = repo_path.split('/')  
        if len(repo_parts) != 2:  
            return None  
        owner, repo = repo_parts  
          
        # Parse preferences  
        preferences = [p.strip() for p in preferences_str.split(',')]  
        valid_preferences = ['releases', 'issues']  
        preferences = [p for p in preferences if p in valid_preferences]  
          
        if not preferences:  
            return None  
              
        # Parse destination  
        chat_id = None  
        thread_id = None  
          
        if destination:  
            if '/' in destination:  
                # Format: chat_id/thread_id  
                dest_parts = destination.split('/')  
                if len(dest_parts) == 2:  
                    try:  
                        chat_id = int(dest_parts[0])  
                        thread_id = int(dest_parts[1])  
                    except ValueError:  
                        return None  
                else:  
                    return None  
            else:  
                # Format: chat_id only  
                try:  
                    chat_id = int(destination)  
                except ValueError:  
                    return None  
          
        return {  
            'owner': owner,  
            'repo': repo,  
            'preferences': preferences,  
            'chat_id': chat_id,  
            'thread_id': thread_id  
        }