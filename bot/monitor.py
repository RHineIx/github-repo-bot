# rhineix/github-repo-bot/github-repo-bot-353a356069cb9a7c65f342d5b42fee8862333925/bot/monitor.py
import asyncio
import logging
from typing import List, Dict, Any
from github import GitHubAPI
from .database import RepositoryTracker
from .token_manager import TokenManager
from github.formatter import RepoFormatter

logger = logging.getLogger(__name__)


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
            try:
                await self._check_repository_updates(item_data)
            except Exception as e:
                identifier = item_data.get('item_key', 'unknown item')
                logger.error(f"Error checking {identifier}: {e}")

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

    async def _check_releases(self, repo_data: Dict):
        """Check for new releases."""
        owner, repo = repo_data["owner"], repo_data["repo"]
        last_release_id = repo_data.get("last_release_id")
        latest_release = await self.github_api.get_latest_release(owner, repo)

        if latest_release:
            current_release_id = str(latest_release.get("id"))
            if last_release_id != current_release_id:
                await self.tracker.update_last_release(owner, repo, current_release_id)
                if last_release_id is not None:
                    await self._send_release_notifications(repo_data, latest_release)

    async def _check_issues(self, repo_data: Dict):
        """Check for new issues."""
        owner, repo = repo_data["owner"], repo_data["repo"]
        last_issue_id = repo_data.get("last_issue_id")
        latest_issues = await self.github_api.get_repository_issues(owner, repo, state="open", per_page=1)

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
        """Formats release notification message using the original style."""
        tag_name = release_data.get("tag_name", "Unknown")
        html_url = release_data.get("html_url", "")
        published_at = release_data.get("published_at", "")
        
        date_str = ""
        if published_at:
            date_str = f"🗓️ Published: {published_at.split('T')[0]}\n"

        return f"""
🔔 <b>New Release Available!</b>

📦 Repository: <b>{owner}/{repo}</b>
✅ Version: <b>{tag_name}</b>
{date_str}
<a href="{html_url}">View Release</a>
"""

    def _format_issue_notification(self, owner: str, repo: str, issue_data: Dict) -> str:
        """Formats issue notification message using the original style."""
        title = issue_data.get("title", "Unknown")
        number = issue_data.get("number", "Unknown")
        user = issue_data.get("user", {})
        author = user.get("login", "Unknown") if user else "Unknown"
        author_url = user.get("html_url", "") if user else ""
        html_url = issue_data.get("html_url", "")
        body = issue_data.get("body", "No description provided.")

        if len(body) > 300:
            body = body[:300] + "..."

        return f"""
🐞 <a href="{author_url}">{author}</a> opened issue <code>{repo}#{number}</code>

<blockquote expandable>Title: {title}
{body}</blockquote>

🔗 <a href="{html_url}">View Issue</a>
#openedissue
"""