"""
Message handlers for the GitHub Repository Preview Bot.
"""

import asyncio
from typing import Optional
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message, CallbackQuery
from telebot import types

from github import GitHubAPI, RepoFormatter, UserFormatter
from github.formatter import URLParser
from bot.utils import MessageUtils, ErrorMessages, LoadingMessages, CallbackDataManager
from config import config

from bot.database import RepositoryTracker
from .monitor import RepositoryMonitor
from .token_manager import TokenManager

import logging  

logger = logging.getLogger(__name__)  

class BotHandlers:
    """Contains all message handlers for the bot."""

    def __init__(self, bot: AsyncTeleBot):
        """
        Initialize bot handlers.
        """
        self.bot = bot
        self.github_api = GitHubAPI()
        self.token_manager = TokenManager()
        self.tracker = RepositoryTracker()
        self.monitor = RepositoryMonitor(self.github_api, self.tracker, self.token_manager, self.bot)
        self.register_handlers()

    def register_handlers(self) -> None:
        """Register all message handlers with the bot."""
        self.bot.message_handler(commands=["start"])(self.handle_start)
        self.bot.message_handler(commands=["help"])(self.handle_help)
        self.bot.message_handler(commands=["repo"])(self.handle_repo)
        self.bot.message_handler(commands=["user"])(self.handle_user)
        # tracking handlers
        self.bot.message_handler(commands=['track'])(self.handle_track_command)  
        self.bot.message_handler(commands=["untrack"])(self.handle_untrack)
        self.bot.message_handler(commands=["tracked"])(self.handle_tracked)
        self.bot.message_handler(commands=["notifications"])(self.handle_notifications)
        self.bot.message_handler(commands=["trackme"])(self.handle_trackme)
        # Token manager handlers
        self.bot.message_handler(commands=["settoken"])(self.handle_set_token)
        self.bot.message_handler(commands=["removetoken"])(self.handle_remove_token)
        self.bot.message_handler(commands=["tokeninfo"])(self.handle_token_info)
        # inline query handler
        self.bot.inline_handler(lambda query: True)(self.handle_inline_query)

        # callback query handlers
        self.bot.callback_query_handler(
            func=lambda call: call.data.startswith("repo_")
        )(self.handle_repo_callback)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("tag_"))(
            self.handle_repo_callback
        )
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("rel_"))(
            self.handle_repo_callback
        )
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("dl_"))(
            self.handle_download_callback
        )

    async def handle_start(self, message: Message) -> None:
        """Handle /start command."""
        # Get info
        bot_info = await self.bot.get_me()
        bot_username = bot_info.username
        first_name = (
            message.from_user.first_name
            if message.from_user and message.from_user.first_name
            else "there"
        )

        welcome_text = f"""
👋 <b>hey {first_name}!</b>  
  
🔍 <b>Explore Repositories:</b>  
• <code>/repo microsoft/vscode</code> - Get repository preview  
• <code>/user torvalds</code> - Get developer information  
  
📊 <b>Track Updates:</b>  
• <code>/track owner/repo [releases,issues]</code> - Track to your DM  
• <code>/track owner/repo [releases] > chat_id</code> - Track to channel/group  
• <code>/track owner/repo [issues] > chat_id/thread_id</code> - Track to forum topic  
• /trackme - Track your starred repos (requires token)  
  
🔧 <b>Advanced Features:</b>  
• <code>/settoken your_github_token</code> - Connect your GitHub account  
• <code>/tracked</code> - View tracked repositories  
  
💡 <b>Tip:</b> Use inline mode by typing <code>@{bot_username} .repo owner/repo</code> in any chat!  
  
Type /help for detailed instructions 📖  
"""
        await MessageUtils.safe_reply(self.bot, message, welcome_text)

    async def handle_help(self, message: Message) -> None:
        """Handle /help command."""
        # Get bot info to use actual username
        bot_info = await self.bot.get_me()
        bot_username = bot_info.username

        help_text = f"""
📖 <b>Complete Usage Guide</b>  
  
🔍 <b>Repository Exploration:</b>  
• <code>/repo https://github.com/owner/repo</code>  
• <code>/repo owner/repo</code>  
• <code>/user username</code> - Developer information  
  
📊 <b>Enhanced Tracking System:</b>  
• <code>/track owner/repo [releases,issues]</code> - Track to your DM  
• <code>/track owner/repo [releases] > -1001234567890</code> - Track to channel/group  
• <code>/track owner/repo [issues] > -1001234567890/123</code> - Track to forum topic  
• <code>/untrack owner/repo</code> - Stop tracking  
• <code>/tracked</code> - View tracked list  
  
📝 <b>Tracking Options:</b>  
• <code>[releases]</code> - Get notified of new releases  
• <code>[issues]</code> - Get notified of new issues    
• <code>[releases,issues]</code> - Track both types  
  
🔧 <b>Advanced Settings:</b>  
• <code>/settoken your_github_token</code> - Connect account  
• /trackme - Track your new stars  
• <code>/tokeninfo</code> - Check token status  
• <code>/removetoken</code> - Remove token  
  
🌟 <b>Inline Mode:</b>  
In any chat, type:  
• <code>@{bot_username} .repo owner/repo</code>  
• <code>@{bot_username} .user username</code>  
  
🔔 <b>Multi-Destination Notifications:</b>  
• Send notifications to your DM, channels, groups, or forum topics  
• Automatic monitoring every 5 minutes  
• New starred repository alerts  
• Support for forum topic threads  
  
💡 <b>Tips:</b>  
• Use repository URLs or owner/repo format  
• Preferences must be enclosed in brackets [releases,issues]  
• Use > symbol to specify destination chat  
• For forum topics, use chat_id/thread_id format  
  
❓ <b>Issues?</b> Ensure repository name or URL is correct and bot has proper permissions for channels/topics  
"""
        await MessageUtils.safe_reply(self.bot, message, help_text)

    async def handle_set_token(self, message: Message) -> None:
        """Handle /settoken command to store user's GitHub token."""
        try:
            token = MessageUtils.validate_command_args(message.text)
            if not token:
                await MessageUtils.safe_reply(
                    self.bot,
                    message,
                    "❌ Please provide your GitHub token.\n\n💡 Example: <code>/settoken ghp_xxxxxxxxxxxx</code>\n\n⚠️ <b>Security Note:</b> Delete this message after setting the token!",
                )

                return

            # Test token validity
            test_api = GitHubAPI(token=token)
            user_data = await test_api.get_authenticated_user()

            if not user_data:
                await MessageUtils.safe_reply(
                    self.bot,
                    message,
                    "❌ Invalid token. Please check your GitHub token and try again.",
                )
                return

            # Additional GitHub token format validation
            if not token.startswith(("ghp_", "github_pat_")):
                await MessageUtils.safe_reply(
                    self.bot,
                    message,
                    "❌ Invalid GitHub token format. Please use a valid GitHub Personal Access Token.",
                )
                return

            # Test token validity
            test_api = GitHubAPI(token=token)
            user_data = await test_api.get_authenticated_user()

            if not user_data:
                await MessageUtils.safe_reply(
                    self.bot,
                    message,
                    "❌ Invalid token. Please check your GitHub token and try again.",
                )
                return

            # Store token
            success = await self.token_manager.store_token(message.from_user.id, token)

            if success:
                username = user_data.get("login", "Unknown")

                # Send success message
                success_msg = await MessageUtils.safe_reply(
                    self.bot,
                    message,
                    f"✅ <b>Token Set Successfully!</b>\n\n👤 Authenticated as: <b>@{username}</b>\n\nYou can now use advanced features like <code>/trackme</code>!",
                )

                # Delete the original /settoken message for security
                try:
                    await self.bot.delete_message(message.chat.id, message.message_id)
                except Exception as e:
                    print(f"Failed to delete settoken message: {e}")

            else:
                await MessageUtils.safe_reply(
                    self.bot, message, "❌ Failed to store token. Please try again."
                )

        except Exception as e:
            print(f"Error in handle_set_token: {e}")
            await MessageUtils.safe_reply(self.bot, message, ErrorMessages.API_ERROR)

    async def handle_remove_token(self, message: Message) -> None:
        """Handle /removetoken command to remove user's GitHub token."""
        try:
            success = await self.token_manager.remove_token(message.from_user.id)

            if success:
                await MessageUtils.safe_reply(
                    self.bot,
                    message,
                    "✅ <b>Token Removed Successfully!</b>\n\nYour GitHub token has been deleted from our system.",
                )
            else:
                await MessageUtils.safe_reply(
                    self.bot,
                    message,
                    "❌ Failed to remove token or no token was found.",
                )

        except Exception as e:
            print(f"Error in handle_remove_token: {e}")
            await MessageUtils.safe_reply(self.bot, message, ErrorMessages.API_ERROR)

    async def handle_token_info(self, message: Message) -> None:
        """Handle /tokeninfo command to show user's token status."""
        try:
            user_token = await self.token_manager.get_token(message.from_user.id)

            if user_token:
                # Test token validity
                test_api = GitHubAPI(token=user_token)
                user_data = await test_api.get_authenticated_user()

                if user_data:
                    username = user_data.get("login", "Unknown")
                    await MessageUtils.safe_reply(
                        self.bot,
                        message,
                        f"✅ <b>Token Status: Active</b>\n\n👤 Authenticated as: <b>@{username}</b>\n\nYour GitHub token is valid and working.",
                    )
                else:
                    await MessageUtils.safe_reply(
                        self.bot,
                        message,
                        "⚠️ <b>Token Status: Invalid</b>\n\nYour stored token appears to be invalid. Please set a new token with <code>/settoken</code>.",
                    )
            else:
                await MessageUtils.safe_reply(
                    self.bot,
                    message,
                    "❌ <b>No Token Set</b>\n\nYou haven't set a GitHub token yet. Use <code>/settoken your_github_token</code> to get started.",
                )

        except Exception as e:
            print(f"Error in handle_token_info: {e}")
            await MessageUtils.safe_reply(self.bot, message, ErrorMessages.API_ERROR)

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
                await MessageUtils.safe_reply(
                    self.bot, message, ErrorMessages.MISSING_REPO_ARG
                )
                return

            # Parse repository URL or name
            parsed = URLParser.parse_repo_input(repo_input)
            if not parsed:
                await MessageUtils.safe_reply(
                    self.bot, message, ErrorMessages.INVALID_REPO_FORMAT
                )
                return

            owner, repo = parsed

            # Send typing action and loading message
            await MessageUtils.send_typing_action(self.bot, message.chat.id)
            wait_msg = await MessageUtils.safe_reply(
                self.bot, message, LoadingMessages.FETCHING_REPO
            )

            if not wait_msg:
                return

            # Fetch repository data
            repo_data = await self.github_api.get_repository(owner, repo)
            if not repo_data:
                await MessageUtils.safe_edit_message(
                    self.bot,
                    message.chat.id,
                    wait_msg.message_id,
                    ErrorMessages.REPO_NOT_FOUND,
                )
                return

            # Fetch additional data concurrently
            languages_task = self.github_api.get_repository_languages(owner, repo)
            release_task = self.github_api.get_latest_release(owner, repo)

            languages, latest_release = await asyncio.gather(
                languages_task, release_task, return_exceptions=True
            )

            # Handle exceptions from concurrent requests
            if isinstance(languages, Exception):
                languages = None
            if isinstance(latest_release, Exception):
                latest_release = None

            # Format repository preview and create keyboard
            preview = RepoFormatter.format_repository_preview(
                repo_data, languages, latest_release
            )
            keyboard = RepoFormatter.create_repo_main_keyboard(owner, repo)

            await MessageUtils.safe_edit_message(
                self.bot,
                message.chat.id,
                wait_msg.message_id,
                preview,
                disable_web_page_preview=False,
                reply_markup=keyboard,
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
                await MessageUtils.safe_reply(
                    self.bot, message, ErrorMessages.MISSING_USER_ARG
                )
                return

            # Send typing action and loading message
            await MessageUtils.send_typing_action(self.bot, message.chat.id)
            wait_msg = await MessageUtils.safe_reply(
                self.bot, message, LoadingMessages.FETCHING_USER
            )

            if not wait_msg:
                return

            # Fetch user data
            user_data = await self.github_api.get_user(username)
            if not user_data:
                await MessageUtils.safe_edit_message(
                    self.bot,
                    message.chat.id,
                    wait_msg.message_id,
                    ErrorMessages.USER_NOT_FOUND,
                )
                return

            # Format and send user information
            user_info = UserFormatter.format_user_info(user_data)

            await MessageUtils.safe_edit_message(
                self.bot, message.chat.id, wait_msg.message_id, user_info
            )

        except Exception as e:
            print(f"Error in handle_user: {e}")
            await MessageUtils.safe_reply(self.bot, message, ErrorMessages.API_ERROR)

    async def handle_trackme(self, message: Message) -> None:
        """Handle /trackme command using user's personal token."""
        try:
            # Check if user has set a token
            user_token = await self.token_manager.get_token(message.from_user.id)
            if not user_token:
                await MessageUtils.safe_reply(
                    self.bot,
                    message,
                    "❌ <b>GitHub Token Required</b>\n\nTo use this feature, you need to set your personal GitHub token first.\n\nUse: <code>/settoken your_github_token</code>",
                )
                return

            # Use user's token for API calls
            user_api = GitHubAPI(
                user_id=message.from_user.id, token_manager=self.token_manager
            )

            # Send typing action and loading message
            await MessageUtils.send_typing_action(self.bot, message.chat.id)
            wait_msg = await MessageUtils.safe_reply(
                self.bot, message, "🔍 Setting up personal stars tracking..."
            )

            if not wait_msg:
                return

            # Get authenticated user info using the GitHub token
            user_data = await user_api.get_authenticated_user()
            if not user_data:
                await MessageUtils.safe_edit_message(
                    self.bot,
                    message.chat.id,
                    wait_msg.message_id,
                    "❌ Failed to authenticate with GitHub. Please check your GitHub token configuration.",
                )
                return

            github_username = user_data.get("login")
            if not github_username:
                await MessageUtils.safe_edit_message(
                    self.bot,
                    message.chat.id,
                    wait_msg.message_id,
                    "❌ Unable to retrieve your GitHub username from the token.",
                )
                return

            # Add to stars tracking
            await self.tracker.add_user_stars_tracking(
                message.from_user.id, github_username
            )

            await MessageUtils.safe_edit_message(
                self.bot,
                message.chat.id,
                wait_msg.message_id,
                f"✅ <b>Personal Stars Tracking Enabled!</b>\n\n⭐ Now tracking your stars for <b>@{github_username}</b>\nYou'll receive notifications when you star new repositories.",
            )

        except Exception as e:
            print(f"Error in handle_trackme: {e}")
            await MessageUtils.safe_reply(self.bot, message, ErrorMessages.API_ERROR)

    async def handle_repo_callback(self, call: CallbackQuery) -> None:
        try:
            await self.bot.answer_callback_query(call.id)

            parts = call.data.split(":")
            action = parts[0]

            if action in [
                "repo_tags",
                "repo_contributors",
                "repo_home",
                "tag_releases",
                "tag_releases_page",
                "rel_assets",
            ]:
                data_hash = parts[1]
                data = CallbackDataManager.get_callback_data(data_hash)

                if not data:
                    await self.bot.answer_callback_query(
                        call.id, "Session expired. Please try again."
                    )
                    return

                if action == "repo_home":
                    await self._show_repo_main(call, data["owner"], data["repo"])
                elif action == "repo_tags":
                    await self._show_tags(
                        call, data["owner"], data["repo"], data.get("page", 1)
                    )
                elif action == "repo_contributors":
                    await self._show_contributors(
                        call, data["owner"], data["repo"], data.get("page", 1)
                    )
                elif action == "tag_releases":
                    await self._show_tag_releases(
                        call, data["owner"], data["repo"], data["tag_name"], 1
                    )
                elif action == "tag_releases_page":
                    await self._show_tag_releases(
                        call,
                        data["owner"],
                        data["repo"],
                        data["tag_name"],
                        data["page"],
                    )
                elif action == "rel_assets":
                    await self._show_release_assets(
                        call, data["owner"], data["repo"], data["release_id"]
                    )

        except Exception as e:
            print(f"Error in handle_repo_callback: {e}")
            await self.bot.answer_callback_query(call.id, "An error occurred.")

    async def handle_download_callback(self, call: CallbackQuery) -> None:
        """Handle download callbacks with compressed data."""
        try:
            await self.bot.answer_callback_query(call.id, "Starting download...")

            parts = call.data.split(":")
            if parts[0] == "dl_direct":
                data_hash = parts[1]
                data = CallbackDataManager.get_callback_data(data_hash)

                if not data:
                    await self.bot.answer_callback_query(call.id, "Session expired.")
                    return

                # Extract data
                asset_url = data["url"]
                asset_size = data["size"]
                asset_name = data["name"]
                owner = data["owner"]
                repo = data["repo"]

                # Check size limit
                max_size_bytes = config.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024
                if asset_size > max_size_bytes:
                    await self.bot.answer_callback_query(call.id, f"File too large...")
                    return

                # Send NEW downloading message
                download_msg = await self.bot.send_message(
                    call.message.chat.id, f"📥 Downloading {asset_name}... Please wait."
                )

                # Download the file directly
                file_data = await self.github_api.download_asset(asset_url, asset_size)

                if file_data:
                    await MessageUtils.send_document_from_bytes(
                        self.bot,
                        call.message.chat.id,
                        file_data,
                        asset_name,
                        f"Downloaded from {owner}/{repo}",
                    )
                    await self.bot.delete_message(
                        call.message.chat.id, download_msg.message_id
                    )
                    await self.bot.answer_callback_query(
                        call.id, "✅ File downloaded successfully!"
                    )
                else:
                    await self.bot.edit_message_text(
                        "❌ Download failed. Please try again.",
                        call.message.chat.id,
                        download_msg.message_id,
                    )

        except Exception as e:
            print(f"Error in handle_download_callback: {e}")
            # Try to update the download message if it exists
            try:
                await self.bot.edit_message_text(
                    f"❌ Download failed: {str(e)}",
                    call.message.chat.id,
                    download_msg.message_id,
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
        preview = RepoFormatter.format_repository_preview(
            repo_data, languages, latest_release
        )
        keyboard = RepoFormatter.create_repo_main_keyboard(owner, repo)

        await MessageUtils.safe_edit_message(
            self.bot,
            call.message.chat.id,
            call.message.message_id,
            preview,
            reply_markup=keyboard,
        )

    async def _show_tags(
        self, call: CallbackQuery, owner: str, repo: str, page: int
    ) -> None:
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
            reply_markup=keyboard,
        )

    async def _show_tag_releases(
        self, call: CallbackQuery, owner: str, repo: str, tag_name: str, page: int = 1
    ) -> None:
        """Show releases for a specific tag with pagination."""
        # Get releases for this repository with pagination
        all_releases = await self.github_api.get_repository_releases(
            owner, repo, page, per_page=50
        )  # Get more to filter

        if all_releases:
            # Filter releases that match this tag
            tag_releases = [r for r in all_releases if r.get("tag_name") == tag_name]

            # Apply pagination to filtered results
            start_idx = (page - 1) * 5
            end_idx = start_idx + 5
            paginated_releases = tag_releases[start_idx:end_idx]
        else:
            paginated_releases = []

        # Format and display
        message_text = RepoFormatter.format_tag_releases(
            tag_name, paginated_releases, owner, repo, page
        )
        keyboard = RepoFormatter.create_tag_releases_keyboard(
            paginated_releases, owner, repo, tag_name, page
        )

        await MessageUtils.safe_edit_message(
            self.bot,
            call.message.chat.id,
            call.message.message_id,
            message_text,
            reply_markup=keyboard,
        )

    async def _show_release_assets(
        self, call: CallbackQuery, owner: str, repo: str, release_id: int
    ) -> None:
        """Show release assets for download."""
        # Get release data
        releases = await self.github_api.get_repository_releases(owner, repo)
        release = None
        for r in releases:
            if r.get("id") == release_id:
                release = r
                break

        if not release:
            await self.bot.answer_callback_query(call.id, "Release not found.")
            return

        # Get assets for this release
        assets = await self.github_api.get_release_assets(owner, repo, release_id)
        if not assets:
            await self.bot.answer_callback_query(
                call.id, "No assets found for this release."
            )
            return

        # Get tag name for back navigation
        tag_name = release.get("tag_name", "Unknown")

        # Format and display
        message_text = RepoFormatter.format_release_assets(release, assets, owner, repo)
        keyboard = RepoFormatter.create_release_assets_keyboard(
            assets, owner, repo, release_id, tag_name
        )

        await MessageUtils.safe_edit_message(
            self.bot,
            call.message.chat.id,
            call.message.message_id,
            message_text,
            reply_markup=keyboard,
        )

    async def _show_contributors(
        self, call: CallbackQuery, owner: str, repo: str, page: int
    ) -> None:
        """Show repository contributors."""
        contributors = await self.github_api.get_repository_contributors(
            owner, repo, page
        )
        if not contributors:
            await self.bot.answer_callback_query(call.id, "No contributors found.")
            return

        # Format contributors list
        message_text = RepoFormatter.format_contributors_list(
            contributors, owner, repo, page
        )

        # Create navigation keyboard
        has_next = len(contributors) == config.ITEMS_PER_PAGE
        keyboard = RepoFormatter.create_navigation_keyboard(
            owner, repo, page, "contributors", has_next
        )

        await MessageUtils.safe_edit_message(
            self.bot,
            call.message.chat.id,
            call.message.message_id,
            message_text,
            reply_markup=keyboard,
        )

    async def handle_track_command(self, message):
        """Handle the enhanced /track command with channel and topic support."""  
        try:  
            command_text = message.text.strip()  
              
            # Remove /track from the text  
            args = command_text.replace('/track', '').strip()  
              
            # Parse the new syntax using regex  
            import re  
            pattern = r'^([^/\s]+/[^/\s\[]+)\s*\[([^\]]+)\](?:\s*>\s*(.+))?$'  
            match = re.match(pattern, args)  
              
            if not match:  
                await self.bot.reply_to(message,   
                    "❌ Invalid format. Use:\n"  
                    "• <code>/track owner/repo [releases,issues]</code> - to your DM\n"  
                    "• <code>/track owner/repo [releases] > chat_id</code> - to channel\n"  
                    "• <code>/track owner/repo [issues] > chat_id/thread_id</code> - to topic",  
                    parse_mode='HTML'  
                )  
                return  
              
            repo_path, preferences_str, destination = match.groups()  
              
            # Parse repository  
            try:  
                owner, repo = repo_path.split('/')  
            except ValueError:  
                await self.bot.reply_to(message, "❌ Invalid repository format. Use: owner/repo")  
                return  
              
            # Parse preferences  
            preferences = [p.strip() for p in preferences_str.split(',')]  
            valid_preferences = ['releases', 'issues']  
            preferences = [p for p in preferences if p in valid_preferences]  
              
            if not preferences:  
                await self.bot.reply_to(message, "❌ Invalid preferences. Use: [releases], [issues], or [releases,issues]")  
                return  
              
            # Parse destination  
            chat_id = None  
            thread_id = None  
              
            if destination:  
                try:  
                    if '/' in destination:  
                        # Format: chat_id/thread_id  
                        dest_parts = destination.split('/')  
                        if len(dest_parts) == 2:  
                            chat_id = int(dest_parts[0])  
                            thread_id = int(dest_parts[1])  
                        else:  
                            await self.bot.reply_to(message, "❌ Invalid destination format. Use: chat_id or chat_id/thread_id")  
                            return  
                    else:  
                        # Format: chat_id only  
                        chat_id = int(destination)  
                except ValueError:  
                    await self.bot.reply_to(message, "❌ Invalid destination. Chat ID and thread ID must be numbers.")  
                    return  
              
            # Show typing action  
            await MessageUtils.send_typing_action(self.bot, message.chat.id)  
              
            # Validate repository exists using your GitHub API  
            github_api = GitHubAPI()  
            repo_data = await github_api.get_repository(owner, repo)  
              
            if not repo_data:  
                await self.bot.reply_to(message, f"❌ Repository {owner}/{repo} not found.")  
                return  
              
            # Validate permissions for channel/topic destinations  
            if chat_id:  
                try:  
                    # Check if bot can send messages to the destination  
                    if thread_id:  
                        # Test topic access  
                        test_msg = await self.bot.send_message(  
                            chat_id,   
                            "🔧 Testing permissions...",   
                            message_thread_id=thread_id  
                        )  
                        await self.bot.delete_message(chat_id, test_msg.message_id)  
                    else:  
                        # Test channel access  
                        test_msg = await self.bot.send_message(chat_id, "🔧 Testing permissions...")  
                        await self.bot.delete_message(chat_id, test_msg.message_id)  
                except Exception as e:  
                    logger.error(f"Permission test failed for destination {chat_id}/{thread_id}: {e}")  
                    await self.bot.reply_to(  
                        message,   
                        "❌ Cannot send messages to destination. Please ensure:\n"  
                        "• Bot is added to the channel/group\n"  
                        "• Bot has permission to send messages\n"  
                        "• For topics: Bot can post in the specific topic"  
                    )  
                    return  
              
            # Add tracking using your existing tracker  
            success = await self.tracker.add_tracked_repo_with_destination(  
                message.from_user.id,  
                owner,  
                repo,  
                preferences,  
                chat_id,  
                thread_id  
            )
              
            if success:  
                # Format success message  
                destination_text = "your DM"  
                if chat_id and thread_id:  
                    destination_text = f"topic {chat_id}/{thread_id}"  
                elif chat_id:  
                    destination_text = f"channel/group {chat_id}"  
                  
                preferences_text = ", ".join(preferences)  
                  
                success_message = (  
                    f"✅ Now tracking <b>{owner}/{repo}</b> for <code>{preferences_text}</code>\n"  
                    f"📍 Notifications will be sent to: {destination_text}\n\n"  
                    f"🔔 You'll receive notifications when new {preferences_text} are available."  
                )  
                  
                await self.bot.reply_to(message, success_message, parse_mode='HTML')  
                  
                # Log the tracking addition  
                logger.info(f"User {message.from_user.id} added tracking for {owner}/{repo} "  
                           f"({preferences_text}) to destination: {destination_text}")  
            else:  
                await self.bot.reply_to(message, "❌ Failed to add tracking. Please try again.")  
                  
        except Exception as e:  
            logger.error(f"Error in track command: {e}")  
            await self.bot.reply_to(message, "❌ An error occurred while processing your request. Please try again.")

    async def handle_untrack(self, message: Message) -> None:
        """Handle /untrack command to stop tracking a repository."""
        try:
            repo_input = MessageUtils.validate_command_args(message.text)
            if not repo_input:
                await MessageUtils.safe_reply(
                    self.bot,
                    message,
                    "❌ Please specify a repository.\n\n💡 Example: <code>/untrack microsoft/vscode</code>",
                )
                return

            parsed = URLParser.parse_repo_input(repo_input)
            if not parsed:
                await MessageUtils.safe_reply(
                    self.bot, message, ErrorMessages.INVALID_REPO_FORMAT
                )
                return

            owner, repo = parsed

            # Remove from tracking
            await self.tracker.remove_tracked_repo(message.from_user.id, owner, repo)

            await MessageUtils.safe_reply(
                self.bot,
                message,
                f"✅ <b>Repository Untracked!</b>\n\n📦 <b>{owner}/{repo}</b> has been removed from your tracking list.",
            )

        except Exception as e:
            print(f"Error in handle_untrack: {e}")
            await MessageUtils.safe_reply(self.bot, message, ErrorMessages.API_ERROR)

    async def handle_tracked(self, message: Message) -> None:
        """Handle /tracked command to show user's tracked repositories."""
        try:
            tracked_repos = await self.tracker.get_user_tracked_repos(
                message.from_user.id
            )

            if not tracked_repos:
                await MessageUtils.safe_reply(
                    self.bot,
                    message,
                    "📋 <b>No Tracked Repositories</b>\n\nYou're not tracking any repositories yet.\nUse <code>/track owner/repo</code> to start tracking.",
                )
                return

            message_text = "📋 <b>Your Tracked Repositories</b>\n\n"
            for i, repo in enumerate(tracked_repos, 1):
                message_text += f"{i}. <b>{repo['owner']}/{repo['repo']}</b>\n"

            message_text += f"\n📊 Total: <b>{len(tracked_repos)}</b> repositories"

            await MessageUtils.safe_reply(self.bot, message, message_text)

        except Exception as e:
            print(f"Error in handle_tracked: {e}")
            await MessageUtils.safe_reply(self.bot, message, ErrorMessages.API_ERROR)

    async def handle_notifications(self, message: Message) -> None:
        """Handle /notifications command to toggle notification settings."""
        try:
            # Extract argument (on/off)
            arg = MessageUtils.validate_command_args(message.text)
            if not arg or arg.lower() not in ["on", "off"]:
                await MessageUtils.safe_reply(
                    self.bot,
                    message,
                    "❌ Please specify 'on' or 'off'.\n\n💡 Example: <code>/notifications on</code>",
                )
                return

            # For now, just acknowledge the command
            # You can implement actual notification toggle logic later
            status = "enabled" if arg.lower() == "on" else "disabled"

            await MessageUtils.safe_reply(
                self.bot,
                message,
                f"🔔 <b>Notifications {status.title()}</b>\n\nNotifications have been {status} for your account.",
            )

        except Exception as e:
            print(f"Error in handle_notifications: {e}")
            await MessageUtils.safe_reply(self.bot, message, ErrorMessages.API_ERROR)

    async def handle_inline_query(self, inline_query) -> None:
        """Handle inline queries for repo and user previews."""
        try:
            query_text = inline_query.query.strip()

            if not query_text:
                # Show help when query is empty
                await self._show_inline_help(inline_query)
                return

            # Parse query for .repo or .user commands
            if query_text.startswith(".repo "):
                await self._handle_inline_repo(inline_query, query_text[6:])
            elif query_text.startswith(".user "):
                await self._handle_inline_user(inline_query, query_text[6:])
            else:
                await self._show_inline_help(inline_query)

        except Exception as e:
            print(f"Error in handle_inline_query: {e}")
            await self._show_inline_error(inline_query)

    async def _handle_inline_repo(self, inline_query, repo_input: str) -> None:
        """Handle inline repository queries."""
        try:
            # Parse repository URL or name
            parsed = URLParser.parse_repo_input(repo_input)
            if not parsed:
                await self._show_inline_error(inline_query, "Invalid repository format")
                return

            owner, repo = parsed

            # Fetch repository data
            repo_data = await self.github_api.get_repository(owner, repo)
            if not repo_data:
                await self._show_inline_error(inline_query, "Repository not found")
                return

            # Fetch additional data concurrently
            languages_task = self.github_api.get_repository_languages(owner, repo)
            release_task = self.github_api.get_latest_release(owner, repo)

            languages, latest_release = await asyncio.gather(
                languages_task, release_task, return_exceptions=True
            )

            if isinstance(languages, Exception):
                languages = None
            if isinstance(latest_release, Exception):
                latest_release = None

            # Format repository preview
            preview = RepoFormatter.format_repository_preview(
                repo_data, languages, latest_release
            )

            # Get owner's avatar URL from repository data
            owner_avatar_url = repo_data.get("owner", {}).get(
                "avatar_url",
                "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
            )

            # Create inline result
            result = types.InlineQueryResultArticle(
                id=f"repo_{owner}_{repo}",
                title=f"📦 {owner}/{repo}",
                description=repo_data.get("description", "No description available")[
                    :100
                ],
                input_message_content=types.InputTextMessageContent(
                    message_text=preview, parse_mode="HTML"
                ),
                thumbnail_url=owner_avatar_url,  # Use owner's avatar instead of GitHub logo
            )

            await self.bot.answer_inline_query(
                inline_query.id, [result], cache_time=300
            )

        except Exception as e:
            print(f"Error in _handle_inline_repo: {e}")
            await self._show_inline_error(inline_query)

    async def _handle_inline_user(self, inline_query, username: str) -> None:
        """Handle inline user queries."""
        try:
            # Fetch user data
            user_data = await self.github_api.get_user(username)
            if not user_data:
                await self._show_inline_error(inline_query, "User not found")
                return

            # Format user information
            user_info = UserFormatter.format_user_info(user_data)
            user_avatar_url = user_data.get(
                "avatar_url",
                "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
            )

            # Create inline result
            result = types.InlineQueryResultArticle(
                id=f"user_{username}",
                title=f"👤 {user_data.get('name', username)}",
                description=f"@{username} - {user_data.get('bio', 'No bio available')[:50]}",
                input_message_content=types.InputTextMessageContent(
                    message_text=user_info, parse_mode="HTML"
                ),
                thumbnail_url=user_avatar_url,  # Use user's avatar
            )

            await self.bot.answer_inline_query(
                inline_query.id, [result], cache_time=300
            )

        except Exception as e:
            print(f"Error in _handle_inline_user: {e}")
            await self._show_inline_error(inline_query)

    async def _show_inline_help(self, inline_query) -> None:
        """Show inline help message."""
        help_result = types.InlineQueryResultArticle(
            id="help",
            title="🤖 GitHub Bot - Help",
            description="Use .repo owner/repo or .user username",
            input_message_content=types.InputTextMessageContent(
                message_text="""
🤖 <b>GitHub Repository Preview Bot - Inline Mode</b>

📋 <b>Available Commands:</b>
• <code>.repo owner/repo</code> - Get repository preview
• <code>.repo https://github.com/owner/repo</code> - Get repository preview
• <code>.user username</code> - Get user information

💡 <b>Examples:</b>
• <code>.repo microsoft/vscode</code>
• <code>.user torvalds</code>""",
                parse_mode="HTML",
            ),
        )

        await self.bot.answer_inline_query(
            inline_query.id, [help_result], cache_time=60
        )

    async def _show_inline_error(
        self, inline_query, error_msg: str = "An error occurred"
    ) -> None:
        """Show inline error message."""
        error_result = types.InlineQueryResultArticle(
            id="error",
            title="❌ Error",
            description=error_msg,
            input_message_content=types.InputTextMessageContent(
                message_text=f"❌ <b>Error:</b> {error_msg}", parse_mode="HTML"
            ),
        )

        await self.bot.answer_inline_query(
            inline_query.id, [error_result], cache_time=10
        )