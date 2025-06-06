"""  
Message handlers for the GitHub Repository Preview Bot.  
"""  
import asyncio  
from typing import Optional  
from telebot.async_telebot import AsyncTeleBot  
from telebot.types import Message  
  
from github import GitHubAPI, RepoFormatter, UserFormatter  
from github.formatter import URLParser  
from .utils import MessageUtils, ErrorMessages, LoadingMessages  
from config import config  
  
  
class BotHandlers:  
    """Contains all message handlers for the bot."""  
      
    def __init__(self, bot: AsyncTeleBot):  
        """  
        Initialize bot handlers.  
          
        Args:  
            bot: AsyncTeleBot instance  
        """  
        self.bot = bot  
        self.github_api = GitHubAPI()  
        self.register_handlers()  
      
    def register_handlers(self) -> None:  
        """Register all message handlers with the bot."""  
        self.bot.message_handler(commands=['start'])(self.handle_start)  
        self.bot.message_handler(commands=['help'])(self.handle_help)  
        self.bot.message_handler(commands=['repo'])(self.handle_repo)  
        self.bot.message_handler(commands=['user'])(self.handle_user)  
      
    async def handle_start(self, message: Message) -> None:  
        """  
        Handle /start command.  
          
        Args:  
            message: Telegram message object  
        """  
        welcome_text = """  
🤖 <b>Welcome to GitHub Repository Preview Bot!</b>  
  
📋 <b>Available Commands:</b>  
• <code>/repo &lt;repository URL or owner/repo&gt;</code> - Get repository preview  
• <code>/user &lt;username&gt;</code> - Get GitHub user information  
• <code>/help</code> - Show help message  
  
💡 <b>Examples:</b>  
• <code>/repo https://github.com/microsoft/vscode</code>  
• <code>/repo microsoft/vscode</code>  
• <code>/user torvalds</code>  
  
🚀 Start by sending a command to try the bot!  
"""  
        await MessageUtils.safe_reply(self.bot, message, welcome_text)  
      
    async def handle_help(self, message: Message) -> None:  
        """  
        Handle /help command.  
          
        Args:  
            message: Telegram message object  
        """  
        help_text = """  
📖 <b>Bot Usage Guide</b>  
  
🔍 <b>/repo command:</b>  
You can use this command in several ways:  
• <code>/repo https://github.com/owner/repo</code>  
• <code>/repo owner/repo</code>  
  
👤 <b>/user command:</b>  
• <code>/user username</code>  
  
📊 <b>Repository Information Displayed:</b>  
• Repository name and description  
• Stars and forks count  
• Open issues count  
• Latest release available  
• Programming languages with percentages  
• Top 3 repository topics  
• Repository URL  
  
❓ If you encounter any issues, make sure the repository URL or name is correct.  
"""  
        await MessageUtils.safe_reply(self.bot, message, help_text)  
      
    async def handle_repo(self, message: Message) -> None:  
        """  
        Handle /repo command.  
          
        Args:  
            message: Telegram message object  
        """  
        try:  
            # Extract repository input  
            repo_input = MessageUtils.validate_command_args(message.text)  
            if not repo_input:  
                await MessageUtils.safe_reply(self.bot, message, ErrorMessages.MISSING_REPO_ARG)  
                return  
              
            # Parse repository URL or name  
            parsed = URLParser.parse_repo_input(repo_input)  
            if not parsed:  
                await MessageUtils.safe_reply(self.bot, message, ErrorMessages.INVALID_REPO_FORMAT)  
                return  
              
            owner, repo = parsed  
              
            # Send typing action and loading message  
            await MessageUtils.send_typing_action(self.bot, message.chat.id)  
            wait_msg = await MessageUtils.safe_reply(self.bot, message, LoadingMessages.FETCHING_REPO)  
              
            if not wait_msg:  
                return  
              
            # Fetch repository data  
            repo_data = await self.github_api.get_repository(owner, repo)  
            if not repo_data:  
                await MessageUtils.safe_edit_message(  
                    self.bot,   
                    message.chat.id,   
                    wait_msg.message_id,   
                    ErrorMessages.REPO_NOT_FOUND  
                )  
                return  
              
            # Fetch additional data concurrently  
            languages_task = self.github_api.get_repository_languages(owner, repo)  
            release_task = self.github_api.get_latest_release(owner, repo)  
              
            languages, latest_release = await asyncio.gather(  
                languages_task,   
                release_task,   
                return_exceptions=True  
            )  
              
            # Handle exceptions from concurrent requests  
            if isinstance(languages, Exception):  
                languages = None  
            if isinstance(latest_release, Exception):  
                latest_release = None  
              
            # Format and send repository preview  
            preview = RepoFormatter.format_repository_preview(repo_data, languages, latest_release)  
              
            await MessageUtils.safe_edit_message(  
                self.bot,  
                message.chat.id,  
                wait_msg.message_id,  
                preview,  
                disable_web_page_preview=False  
            )  
              
        except Exception as e:  
            print(f"Error in handle_repo: {e}")  
            await MessageUtils.safe_reply(self.bot, message, ErrorMessages.API_ERROR)  
      
    async def handle_user(self, message: Message) -> None:  
        """  
        Handle /user command.  
          
        Args:  
            message: Telegram message object  
        """  
        try:  
            # Extract username  
            username = MessageUtils.validate_command_args(message.text)  
            if not username:  
                await MessageUtils.safe_reply(self.bot, message, ErrorMessages.MISSING_USER_ARG)  
                return  
              
            # Send typing action and loading message  
            await MessageUtils.send_typing_action(self.bot, message.chat.id)  
            wait_msg = await MessageUtils.safe_reply(self.bot, message, LoadingMessages.FETCHING_USER)  
              
            if not wait_msg:  
                return  
              
            # Fetch user data  
            user_data = await self.github_api.get_user(username)  
            if not user_data:  
                await MessageUtils.safe_edit_message(  
                    self.bot,  
                    message.chat.id,  
                    wait_msg.message_id,  
                    ErrorMessages.USER_NOT_FOUND  
                )  
                return  
              
            # Format and send user information  
            user_info = UserFormatter.format_user_info(user_data)  
              
            await MessageUtils.safe_edit_message(  
                self.bot,  
                message.chat.id,  
                wait_msg.message_id,  
                user_info  
            )  
              
        except Exception as e:  
            print(f"Error in handle_user: {e}")  
            await MessageUtils.safe_reply(self.bot, message, ErrorMessages.API_ERROR)