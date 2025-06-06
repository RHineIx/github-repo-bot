"""  
Message handlers for the GitHub Repository Preview Bot.  
"""  
import asyncio  
from typing import Optional  
from telebot.async_telebot import AsyncTeleBot  
from telebot.types import Message, CallbackQuery  
  
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
          
        # Register callback query handlers  
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('repo_'))(self.handle_repo_callback)  
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('download_'))(self.handle_download_callback)  
      
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
  
🔧 <b>Interactive Features:</b>  
• Browse repository tags and releases  
• View contributors  
• Download release assets directly  
• Navigate through paginated results  
  
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
              
            # Format repository preview and create keyboard  
            preview = RepoFormatter.format_repository_preview(repo_data, languages, latest_release)  
            keyboard = RepoFormatter.create_repo_main_keyboard(owner, repo)  
              
            await MessageUtils.safe_edit_message(  
                self.bot,  
                message.chat.id,  
                wait_msg.message_id,  
                preview,  
                disable_web_page_preview=False,  
                reply_markup=keyboard  
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
      
    async def handle_repo_callback(self, call: CallbackQuery) -> None:  
        """  
        Handle repository-related callback queries.  
          
        Args:  
            call: Callback query object  
        """  
        try:  
            await self.bot.answer_callback_query(call.id)  
              
            # Parse callback data  
            parts = call.data.split(':')  
            action = parts[0]  
              
            if action == 'repo_home':  
                # Return to main repository view  
                owner, repo = parts[1].split('/')  
                await self._show_repo_main(call, owner, repo)  
                  
            elif action in ['repo_tags', 'repo_releases', 'repo_contributors']:  
                # Handle paginated content  
                owner, repo = parts[1].split('/')  
                page = int(parts[2]) if len(parts) > 2 else 1  
                  
                if action == 'repo_tags':  
                    await self._show_tags(call, owner, repo, page)  
                elif action == 'repo_releases':  
                    await self._show_releases(call, owner, repo, page)  
                elif action == 'repo_contributors':  
                    await self._show_contributors(call, owner, repo, page)  
                      
            elif action == 'repo_files':  
                # Show file browser (placeholder for now)  
                owner, repo = parts[1].split('/')  
                await self._show_files(call, owner, repo)  
                  
        except Exception as e:  
            print(f"Error in handle_repo_callback: {e}")  
            await self.bot.answer_callback_query(call.id, "An error occurred. Please try again.")  
      
    async def handle_download_callback(self, call: CallbackQuery) -> None:  
        """  
        Handle download-related callback queries.  
          
        Args:  
            call: Callback query object  
        """  
        try:  
            await self.bot.answer_callback_query(call.id, "Starting download...")  
              
            # Parse callback data  
            parts = call.data.split(':')  
            asset_id = parts[1]  
            asset_size = int(parts[2])  
              
            # Check size limit  
            max_size_bytes = config.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024  
            if asset_size > max_size_bytes:  
                await self.bot.answer_callback_query(  
                    call.id,   
                    f"File too large ({asset_size / (1024*1024):.1f}MB). Max size: {config.MAX_DOWNLOAD_SIZE_MB}MB",  
                    show_alert=True  
                )  
                return  
              
            # TODO: Implement actual download functionality  
            # This would require getting the asset download URL and using the download_asset method  
            await self.bot.answer_callback_query(call.id, "Download feature coming soon!")  
              
        except Exception as e:  
            print(f"Error in handle_download_callback: {e}")  
            await self.bot.answer_callback_query(call.id, "Download failed. Please try again.")  
      
    async def _show_repo_main(self, call: CallbackQuery, owner: str, repo: str) -> None:  
        """Show main repository view."""  
        # Fetch repository data  
        repo_data = await self.github_api.get_repository(owner, repo)  
        if not repo_data:  
            await self.bot.answer_callback_query(call.id, "Repository not found.")  
            return  
          
        # Fetch additional data  
        languages_task = self.github_api.get_repository_languages(owner, repo)  
        release_task = self.github_api.get_latest_release(owner, repo)  
          
        languages, latest_release = await asyncio.gather(  
            languages_task, release_task, return_exceptions=True  
        )  
          
        if isinstance(languages, Exception):  
            languages = None  
        if isinstance(latest_release, Exception):  
            latest_release = None  
          
        # Format and update message  
        preview = RepoFormatter.format_repository_preview(repo_data, languages, latest_release)  
        keyboard = RepoFormatter.create_repo_main_keyboard(owner, repo)  
          
        await MessageUtils.safe_edit_message(  
            self.bot,  
            call.message.chat.id,  
            call.message.message_id,  
            preview,  
            reply_markup=keyboard  
        )  
      
    async def _show_tags(self, call: CallbackQuery, owner: str, repo: str, page: int) -> None:  
        """Show repository tags."""  
        tags = await self.github_api.get_repository_tags(owner, repo, page)  
        if not tags:  
            await self.bot.answer_callback_query(call.id, "No tags found.")  
            return  
          
        # Format tags list  
        message_text = RepoFormatter.format_tags_list(tags, owner, repo, page)  
          
        # Create navigation keyboard  
        has_next = len(tags) == config.ITEMS_PER_PAGE  
        keyboard = RepoFormatter.create_navigation_keyboard(owner, repo, page, 'tags', has_next)  
          
        await MessageUtils.safe_edit_message(  
            self.bot,  
            call.message.chat.id,  
            call.message.message_id,  
            message_text,  
            reply_markup=keyboard  
        )  
      
    async def _show_releases(self, call: CallbackQuery, owner: str, repo: str, page: int) -> None:  
        """Show repository releases."""  
        releases = await self.github_api.get_repository_releases(owner, repo, page)  
        if not releases:  
            await self.bot.answer_callback_query(call.id, "No releases found.")  
            return  
          
        # Format releases list  
        message_text = RepoFormatter.format_releases_list(releases, owner, repo, page)  
          
        # Create navigation keyboard  
        has_next = len(releases) == config.ITEMS_PER_PAGE  
        keyboard = RepoFormatter.create_navigation_keyboard(owner, repo, page, 'releases', has_next)  
          
        await MessageUtils.safe_edit_message(  
            self.bot,  
            call.message.chat.id,  
            call.message.message_id,  
            message_text,  
            reply_markup=keyboard  
        )  
      
    async def _show_contributors(self, call: CallbackQuery, owner: str, repo: str, page: int) -> None:  
        """Show repository contributors."""  
        contributors = await self.github_api.get_repository_contributors(owner, repo, page)  
        if not contributors:  
            await self.bot.answer_callback_query(call.id, "No contributors found.")  
            return  
          
        # Format contributors list  
        message_text = RepoFormatter.format_contributors_list(contributors, owner, repo, page)  
          
        # Create navigation keyboard  
        has_next = len(contributors) == config.ITEMS_PER_PAGE  
        keyboard = RepoFormatter.create_navigation_keyboard(owner, repo, page, 'contributors', has_next)  
          
        await MessageUtils.safe_edit_message(  
            self.bot,  
            call.message.chat.id,  
            call.message.message_id,  
            message_text,  
            reply_markup=keyboard  
        )  
      
    async def _show_files(self, call: CallbackQuery, owner: str, repo: str) -> None:  
        """Show repository files (placeholder)."""  
        await self.bot.answer_callback_query(call.id, "File browser feature coming soon!")