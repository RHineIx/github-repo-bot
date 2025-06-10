import asyncio
import logging
from typing import List, Dict, Any, Optional
from .database import RepositoryTracker
from .token_manager import TokenManager
from github.api import GitHubAPI, GitHubAPIError 
from github.formatter import RepoFormatter

logger = logging.getLogger(__name__)

#constant for the failure threshold
FAILURE_THRESHOLD = 5

class RepositoryMonitor:
    """Monitors tracked repositories for changes."""

    def __init__(self, github_api: GitHubAPI, tracker: RepositoryTracker, token_manager: TokenManager, bot):
        self.github_api = github_api
        self.tracker = tracker
        self.token_manager = token_manager
        self.bot = bot
        self.monitoring = False

    async def start_monitoring(self, interval: int = 300):
        """Start monitoring repositories every interval seconds."""
        self.monitoring = True
        logger.info("Repository monitoring started")

        while self.monitoring:
            try:
                await self._check_all_repositories()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)

    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.monitoring = False
        logger.info("Repository monitoring stopped")

    async def _check_all_repositories(self):
        """Check all tracked repositories for updates."""
        tracked_items = await self.tracker.get_all_tracked_repos()

        for item_data in tracked_items:
            item_key = item_data.get('item_key')
            try:
                await self._check_repository_updates(item_data)
                # If the check was successful, reset the failure count
                if item_key:
                    await self.tracker.reset_failure_count(item_key)
            except GitHubAPIError as e:
                # Handle API errors, specifically 404
                if e.status_code == 404:
                    logger.warning(f"Repo check failed for {item_key} with 404 Not Found.")
                    new_failure_count = await self.tracker.increment_failure_count(item_key)
                    
                    if new_failure_count >= FAILURE_THRESHOLD:
                        logger.error(f"Item {item_key} reached failure threshold. Removing and notifying users.")
                        await self._send_untrack_notification(item_data)
                        await self.tracker.remove_item_by_key(item_key)
                else:
                    logger.error(f"Error checking {item_key}: {e}")
            except Exception as e:
                logger.error(f"A non-API error occurred while checking {item_key}: {e}")

    async def _check_repository_updates(self, repo_data: Dict):
        """Check a single repository for updates based on tracking type."""
        item_type = repo_data.get("item_type")
        if item_type == "stars":
            await self._check_stars_updates(repo_data)
        elif item_type == "repo":
            if "owner" not in repo_data or "repo" not in repo_data:
                logger.error(f"Invalid repo data structure: {repo_data}")
                return

            track_type = repo_data.get("track_type", "releases")
            if track_type == "releases":
                await self._check_releases(repo_data)
            elif track_type == "issues":
                await self._check_issues(repo_data)

    async def _get_api_client_for_repo(self, repo_data: Dict) -> Optional[GitHubAPI]:
        """
        Gets an authenticated API client ONLY if a subscribed user has a token.
        Returns None if no token is found, effectively disabling fallback to global token.
        """
        all_user_subscribers = repo_data.get("user_subscribers", set())

        for user_id in all_user_subscribers:
            user_token = await self.token_manager.get_token(user_id)
            if user_token:
                owner = repo_data.get("owner", "N/A")
                repo = repo_data.get("repo", "N/A")
                logger.info(f"Using token from user {user_id} to check {owner}/{repo}")
                return GitHubAPI(token=user_token)  # Return new client immediately

        # If the loop finishes, no subscribed user had a token.
        return None

    async def _check_releases(self, repo_data: Dict):
        """Check for new releases, REQUIRES a user-specific token."""
        owner, repo = repo_data["owner"], repo_data["repo"]
        api_client = await self._get_api_client_for_repo(repo_data)

        if not api_client:
            logger.warning(f"Skipping release check for {owner}/{repo}: No subscribed user has provided a token.")
            return  # STOP if no specific token is found

        last_release_id = repo_data.get("last_release_id")
        latest_release = await api_client.get_latest_release(owner, repo)

        if latest_release:
            current_release_id = str(latest_release.get("id"))
            if last_release_id != current_release_id:
                await self.tracker.update_last_release(owner, repo, current_release_id)
                if last_release_id is not None:
                    await self._send_release_notifications(repo_data, latest_release)

    async def _check_issues(self, repo_data: Dict):
        """Check for new issues, REQUIRES a user-specific token."""
        owner, repo = repo_data["owner"], repo_data["repo"]
        api_client = await self._get_api_client_for_repo(repo_data)

        if not api_client:
            logger.warning(f"Skipping issue check for {owner}/{repo}: No subscribed user has provided a token.")
            return  # STOP if no specific token is found

        last_issue_id = repo_data.get("last_issue_id")
        latest_issues = await api_client.get_repository_issues(owner, repo, state="open", per_page=1)

        if latest_issues:
            latest_issue = latest_issues[0]
            current_issue_id = str(latest_issue.get("id"))
            if last_issue_id != current_issue_id:
                await self.tracker.update_last_issue(owner, repo, current_issue_id)
                if last_issue_id is not None:
                    await self._send_issue_notifications(repo_data, latest_issue)

    async def _check_stars_updates(self, repo_data: Dict):
        """Checks for new starred repos on a PER-USER basis using their personal token."""
        github_username_tracked = repo_data.get("github_username")
        subscribers = repo_data.get("subscribers", set())
        last_known_ids_for_group = repo_data.get("last_starred_repo_ids")
        
        valid_api_client = None
        
        for user_id in subscribers:
            try:
                client = GitHubAPI(user_id=user_id, token_manager=self.token_manager)
                auth_user_data = await client.get_authenticated_user()
                if auth_user_data and auth_user_data.get('login') == github_username_tracked:
                    valid_api_client = client
                    break
            except Exception:
                continue

        if not valid_api_client:
            logger.warning(f"No valid token found for any subscriber of {github_username_tracked}. Skipping star check.")
            return

        current_page_repos = await valid_api_client.get_authenticated_user_starred_repos(page=1, per_page=30)
        
        if not current_page_repos:
            return

        current_page_ids = {str(repo.get("id")) for repo in current_page_repos}

        if last_known_ids_for_group is None:
            await self.tracker.update_last_starred_repo_ids(github_username_tracked, current_page_ids)
            logger.info(f"Established baseline for {github_username_tracked} with {len(current_page_ids)} repos.")
            return
            
        truly_new_repos = []
        for repo in current_page_repos:
            if str(repo.get("id")) not in last_known_ids_for_group:
                truly_new_repos.append(repo)
            else:
                break
        
        if truly_new_repos:
            truly_new_repos.reverse()
            logger.info(f"Found {len(truly_new_repos)} new star(s) for {github_username_tracked}.")
            for new_repo in truly_new_repos:
                await self._send_starred_repo_notification(repo_data, new_repo)

        await self.tracker.update_last_starred_repo_ids(github_username_tracked, current_page_ids)

    async def _send_notifications_to_all_subscribers(self, repo_data: Dict, message_text: str):
        """Helper function to broadcast a message to all subscriber types."""
        # Combine all subscriber types into one loop
        subscribers_to_notify = {
            ('user', uid) for uid in repo_data.get("user_subscribers", set())
        }
        subscribers_to_notify.update(
            ('user', uid) for uid in repo_data.get("subscribers", set())
        )
        subscribers_to_notify.update(
            ('channel', cid) for cid in repo_data.get("channel_subscribers", set())
        )
        subscribers_to_notify.update(
            ('topic', tid) for tid in repo_data.get("topic_subscribers", set())
        )

        for sub_type, sub_id in subscribers_to_notify:
            try:
                if sub_type == 'user' or sub_type == 'channel':
                    await self.bot.send_message(sub_id, message_text, parse_mode="HTML", disable_web_page_preview=False)
                elif sub_type == 'topic':
                    chat_id, thread_id = sub_id.split(':')
                    await self.bot.send_message(int(chat_id), message_text, message_thread_id=int(thread_id), parse_mode="HTML", disable_web_page_preview=False)
            except Exception as e:
                logger.error(f"Failed to send notification to {sub_type} {sub_id}: {e}")

    async def _send_release_notifications(self, repo_data: Dict, release_data: Dict):
        """Send notifications for new releases with original formatting."""
        owner = repo_data["owner"]
        repo = repo_data["repo"]
        notification_text = self._format_release_notification(owner, repo, release_data)
        await self._send_notifications_to_all_subscribers(repo_data, notification_text)

    async def _send_issue_notifications(self, repo_data: Dict, issue_data: Dict):
        """Send notifications for new issues with original formatting."""
        owner = repo_data["owner"]
        repo = repo_data["repo"]
        notification_text = self._format_issue_notification(owner, repo, issue_data)
        await self._send_notifications_to_all_subscribers(repo_data, notification_text)
    
    async def _send_starred_repo_notification(self, repo_data: Dict, starred_repo: Dict):
        """Send notification for a newly starred repository."""
        owner = starred_repo.get("owner", {}).get("login", "Unknown")
        repo_name = starred_repo.get("name", "Unknown")
        
        # To get the full preview, we need more data
        repo_data_full = await self.github_api.get_repository(owner, repo_name)
        languages = await self.github_api.get_repository_languages(owner, repo_name)
        latest_release = await self.github_api.get_latest_release(owner, repo_name)
        
        if repo_data_full:
            preview_text = RepoFormatter.format_repository_preview(
                repo_data_full, languages, latest_release
            )
            await self._send_notifications_to_all_subscribers(repo_data, preview_text)

    def _format_release_notification(self, owner: str, repo: str, release_data: Dict) -> str:
        """Formats release notification message with more details."""
        tag_name = release_data.get("tag_name", "Unknown")
        html_url = release_data.get("html_url", "")
        published_at = release_data.get("published_at", "")
        release_name = release_data.get("name") or tag_name
        author = release_data.get("author", {})
        author_login = author.get("login", "N/A")
        author_url = author.get("html_url", "")
        is_prerelease = release_data.get("prerelease", False)
        assets_count = len(release_data.get("assets", []))
        body = release_data.get("body", "No description provided.")

        # Truncate body
        if len(body) > 500:
            body = body[:500] + "..."
        elif not body:
            body = "No release notes provided."

        date_str = f"🗓️ <b>Date:</b> {published_at.split('T')[0]}" if published_at else ""
        prerelease_badge = "⚠️ <b>Status:</b> Pre-release\n" if is_prerelease else ""

        message = f"""🔔 <b>New Release: {release_name}</b>
in 📦 <a href="https://github.com/{owner}/{repo}">{owner}/{repo}</a>

<blockquote expandable>{body}</blockquote>

{prerelease_badge}👤 <b>Published by:</b> <a href="{author_url}">{author_login}</a>
✅ <b>Version:</b> <code>{tag_name}</code>
📄 <b>Assets:</b> {assets_count} downloadable file(s)
{date_str}

🔗 <a href="{html_url}">View Full Release & Download</a>"""
        return message.strip()

    def _format_issue_notification(  
        self, owner: str, repo: str, issue_data: Dict  
    ) -> str:  
        """Format issue notification message with improved layout."""  
        title = issue_data.get("title", "Unknown")  
        number = issue_data.get("number", "Unknown")  
        user = issue_data.get("user", {})  
        author = user.get("login", "Unknown") if user else "Unknown"  
        author_url = user.get("html_url", "") if user else ""  
        html_url = issue_data.get("html_url", "")  
        body = issue_data.get("body", "No description provided.")  
  
        # Truncate body if too long  
        if len(body) > 500:  
            body = body[:500] + "..."  
  
        # Format the message according to your specification  
        message = f"""🪲 <a href="{author_url}">{author}</a> opened issue <code>{repo}#{number}</code>  

    <blockquote expandable>Title: {title}  
{body}</blockquote>
  
🔗 <a href="{html_url}">View Issue</a>  
#openedissue"""  
        return message.strip()
    
    async def _send_untrack_notification(self, repo_data: Dict):
        """Sends a notification that a repository is no longer being tracked due to errors."""
        owner = repo_data.get("owner", "N/A")
        repo = repo_data.get("repo", "N/A")
        item_key = repo_data.get("item_key", "N/A")
        
        message_text = (
            f"🔔 **Tracking Stopped**\n\n"
            f"Tracking for <code>{owner}/{repo}</code> has been automatically stopped "
            f"because the repository could not be found after multiple attempts.\n\n"
            f"It may have been deleted, made private, or renamed."
        )
        
        await self._send_notifications_to_all_subscribers(repo_data, message_text)