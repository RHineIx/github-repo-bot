"""  
Utility functions for the Telegram bot.  
"""  
import asyncio  
from typing import Optional, Callable, Any  
from telebot.async_telebot import AsyncTeleBot  
  
  
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
            await bot.send_chat_action(chat_id, 'typing')  
        except Exception as e:  
            print(f"Failed to send typing action: {e}")  
      
    @staticmethod  
    async def safe_edit_message(  
        bot: AsyncTeleBot,   
        chat_id: int,   
        message_id: int,   
        text: str,   
        **kwargs  
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
                text,   
                chat_id=chat_id,   
                message_id=message_id,  
                **kwargs  
            )  
            return True  
        except Exception as e:  
            print(f"Failed to edit message: {e}")  
            return False  
      
    @staticmethod  
    async def safe_reply(  
        bot: AsyncTeleBot,   
        message: Any,   
        text: str,   
        **kwargs  
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
            print(f"Failed to reply to message: {e}")  
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
        parts = command_text.split(' ', 1)  
        if len(parts) < min_args + 1:  
            return None  
        return parts[1].strip() if len(parts) > 1 else ""  
      
    @staticmethod  
    async def with_retry(  
        func: Callable,   
        max_retries: int = 3,   
        delay: float = 1.0,  
        *args,   
        **kwargs  
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
                    print(f"Function failed after {max_retries} retries: {e}")  
                    return None  
                print(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")  
                await asyncio.sleep(delay)  
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
        "❌ Please specify a username.\n\n"  
        "💡 Example: <code>/user torvalds</code>"  
    )  
      
    API_ERROR = "❌ An error occurred while fetching data. Please try again later."  
      
    RATE_LIMIT_EXCEEDED = (  
        "⚠️ Rate limit exceeded. Please wait a moment before trying again."  
    )  
  
  
class LoadingMessages:  
    """Loading messages for different operations."""  
      
    FETCHING_REPO = "🔍 Fetching repository information..."  
    FETCHING_USER = "🔍 Fetching user information..."  
    PROCESSING = "⏳ Processing your request..."