"""  
Message handlers for the GitHub Repository Preview Bot.  
"""  
import asyncio  
from typing import Optional  
from telebot.async_telebot import AsyncTeleBot  
from telebot.types import Message, CallbackQuery  
  
from github import GitHubAPI, RepoFormatter, UserFormatter  
from github.formatter import URLParser  
from .utils import MessageUtils, ErrorMessages, LoadingMessages, CallbackDataManager
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
          
        #callback query handlers  
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('repo_'))(self.handle_repo_callback)  
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('tag_'))(self.handle_repo_callback)  
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('rel_'))(self.handle_repo_callback)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith('dl_'))(self.handle_download_callback)
      
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
        try:  
            await self.bot.answer_callback_query(call.id)  
              
            # إضافة تشخيص مؤقت  
            print(f"Callback data received: {call.data}")  
              
            parts = call.data.split(':')  
            action = parts[0]  
              
            if action in ['repo_tags', 'repo_contributors', 'repo_home', 'tag_releases', 'rel_assets']:  
                data_hash = parts[1]  
                print(f"Looking for hash: {data_hash}")  # للتشخيص  
                data = CallbackDataManager.get_callback_data(data_hash)  
                print(f"Retrieved data: {data}")  # للتشخيص  
                  
                if not data:  
                    await self.bot.answer_callback_query(call.id, "Session expired. Please try again.")  
                    return  
                      
                if action == 'repo_home':  
                    await self._show_repo_main(call, data['owner'], data['repo'])  
                elif action == 'repo_tags':  
                    await self._show_tags(call, data['owner'], data['repo'], data.get('page', 1))  
                elif action == 'repo_contributors':  
                    await self._show_contributors(call, data['owner'], data['repo'], data.get('page', 1))  
                elif action == 'tag_releases':  
                    await self._show_tag_releases(call, data['owner'], data['repo'], data['tag_name'])  
                elif action == 'rel_assets':  
                    print(f"Calling _show_release_assets with: {data}")  # للتشخيص  
                    await self._show_release_assets(call, data['owner'], data['repo'], data['release_id'])  
            else:  
                # إضافة معالجة للأزرار التي لا تستخدم نظام hash  
                print(f"Unhandled action: {action}")  
                await self.bot.answer_callback_query(call.id, f"Unknown action: {action}")  
                  
        except Exception as e:  
            print(f"Error in handle_repo_callback: {e}")  
            import traceback  
            traceback.print_exc()  # طباعة تفاصيل الخطأ الكاملة  
            await self.bot.answer_callback_query(call.id, "An error occurred.")
      
    async def handle_download_callback(self, call: CallbackQuery) -> None:  
        """Handle download callbacks with compressed data."""  
        try:  
            await self.bot.answer_callback_query(call.id, "Starting download...")  
              
            parts = call.data.split(':')  
            if parts[0] == 'dl_direct':  
                data_hash = parts[1]  
                data = CallbackDataManager.get_callback_data(data_hash)  
                  
                if not data:  
                    await self.bot.answer_callback_query(call.id, "Session expired.")  
                    return  
                  
                # Extract data  
                asset_url = data['url']  
                asset_size = data['size']  
                asset_name = data['name']  
                owner = data['owner']  
                repo = data['repo']
                
                # Check size limit  
                max_size_bytes = config.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024  
                if asset_size > max_size_bytes:  
                    await self.bot.answer_callback_query(call.id, f"File too large...")  
                    return  
                
                # Send NEW downloading message  
                download_msg = await self.bot.send_message(  
                    call.message.chat.id,  
                    f"📥 Downloading {asset_name}... Please wait."  
                )  
                
                # Download the file directly  
                file_data = await self.github_api.download_asset(asset_url, asset_size)  
                
                if file_data:  
                    await MessageUtils.send_document_from_bytes(  
                        self.bot,  
                        call.message.chat.id,  
                        file_data,  
                        asset_name,  
                        f"Downloaded from {owner}/{repo}"  
                    )  
                    await self.bot.delete_message(call.message.chat.id, download_msg.message_id)  
                    await self.bot.answer_callback_query(call.id, "✅ File downloaded successfully!")  
                else:  
                    await self.bot.edit_message_text(  
                        "❌ Download failed. Please try again.",  
                        call.message.chat.id,  
                        download_msg.message_id  
                    )  
                
        except Exception as e:  
            print(f"Error in handle_download_callback: {e}")  
            # Try to update the download message if it exists  
            try:  
                await self.bot.edit_message_text(  
                    f"❌ Download failed: {str(e)}",  
                    call.message.chat.id,  
                    download_msg.message_id  
                )  
            except:  
                pass  
            await self.bot.answer_callback_query(call.id, "❌ Download failed.")
      
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
          
        # Create tags keyboard with clickable tag buttons  
        keyboard = RepoFormatter.create_tags_keyboard(tags, owner, repo, page)  
          
        await MessageUtils.safe_edit_message(  
            self.bot,  
            call.message.chat.id,  
            call.message.message_id,  
            message_text,  
            reply_markup=keyboard  
        )  
      
    async def _show_tag_releases(self, call: CallbackQuery, owner: str, repo: str, tag_name: str) -> None:  
        """Show releases for a specific tag."""  
        # Get all releases for this repository  
        releases = await self.github_api.get_repository_releases(owner, repo)  
        if releases:  
            # Filter releases that match this tag  
            tag_releases = [r for r in releases if r.get('tag_name') == tag_name]  
        else:  
            tag_releases = []  
          
        # Format and display  
        message_text = RepoFormatter.format_tag_releases(tag_name, tag_releases, owner, repo)  
        keyboard = RepoFormatter.create_tag_releases_keyboard(tag_releases, owner, repo, tag_name)  
          
        await MessageUtils.safe_edit_message(  
            self.bot,  
            call.message.chat.id,  
            call.message.message_id,  
            message_text,  
            reply_markup=keyboard  
        )

    async def _show_release_assets(self, call: CallbackQuery, owner: str, repo: str, release_id: int) -> None:  
        """Show release assets for download."""  
        # Get release data  
        releases = await self.github_api.get_repository_releases(owner, repo)  
        release = None  
        for r in releases:  
            if r.get('id') == release_id:  
                release = r  
                break  
          
        if not release:  
            await self.bot.answer_callback_query(call.id, "Release not found.")  
            return  
          
        # Get assets for this release  
        assets = await self.github_api.get_release_assets(owner, repo, release_id)  
        if not assets:  
            await self.bot.answer_callback_query(call.id, "No assets found for this release.")  
            return  
          
        # Get tag name for back navigation  
        tag_name = release.get('tag_name', 'Unknown')  
          
        # Format and display  
        message_text = RepoFormatter.format_release_assets(release, assets, owner, repo)  
        keyboard = RepoFormatter.create_release_assets_keyboard(assets, owner, repo, release_id, tag_name)  
          
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