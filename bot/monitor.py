"""  
Repository monitoring system for tracking changes.  
"""  
  
import asyncio  
import logging  
from typing import List, Dict, Any  
from github import GitHubAPI  
from .database import RepositoryTracker  
  
logger = logging.getLogger(__name__)  
  
  
class RepositoryMonitor:  
    """Monitors tracked repositories for changes."""  
  
    def __init__(self, github_api: GitHubAPI, tracker: RepositoryTracker, bot):  
        self.github_api = github_api  
        self.tracker = tracker  
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
                await asyncio.sleep(60)  # Wait 1 minute on error  
  
    def stop_monitoring(self):  
        """Stop the monitoring loop."""  
        self.monitoring = False  
        logger.info("Repository monitoring stopped")  
  
    async def _check_all_repositories(self):  
        """Check all tracked repositories for updates."""  
        tracked_repos = await self.tracker.get_all_tracked_repos()  
  
        for repo_data in tracked_repos:  
            try:  
                await self._check_repository_updates(repo_data)  
            except Exception as e:  
                # Handle different data structures for error logging  
                if repo_data.get("type") == "stars":  
                    identifier = f"stars:{repo_data.get('github_username', 'unknown')}"  
                else:  
                    owner = repo_data.get("owner", "unknown")  
                    repo = repo_data.get("repo", "unknown")  
                    identifier = f"{owner}/{repo}"  
  
                logger.error(f"Error checking {identifier}: {e}")  
  
    async def _check_repository_updates(self, repo_data: Dict):  
        """Check a single repository for updates based on tracking type."""  
        # Check if this is stars tracking  
        if repo_data.get("type") == "stars":  
            await self._check_stars_updates(repo_data)  
        else:  
            # Regular repository tracking - ensure required keys exist  
            if "owner" not in repo_data or "repo" not in repo_data:  
                logger.error(f"Invalid repo data structure: {repo_data}")  
                return  
  
            owner = repo_data["owner"]  
            repo = repo_data["repo"]  
            track_type = repo_data.get("track_type", "releases")  
  
            if track_type == "releases":  
                await self._check_releases(repo_data)  
            elif track_type == "issues":  
                await self._check_issues(repo_data)  
  
    async def _check_releases(self, repo_data: Dict):  
        """Check for new releases."""  
        owner = repo_data["owner"]  
        repo = repo_data["repo"]  
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
        owner = repo_data["owner"]  
        repo = repo_data["repo"]  
        last_issue_id = repo_data.get("last_issue_id")  
  
        latest_issues = await self.github_api.get_repository_issues(  
            owner, repo, state="open", per_page=1  
        )  
  
        if latest_issues and len(latest_issues) > 0:  
            latest_issue = latest_issues[0]  
            current_issue_id = str(latest_issue.get("id"))  
  
            if last_issue_id != current_issue_id:  
                await self.tracker.update_last_issue(owner, repo, current_issue_id)  
  
                if last_issue_id is not None:  
                    await self._send_issue_notifications(repo_data, latest_issue)  
  
    async def _send_release_notifications(self, repo_data: Dict, release_data: Dict):  
        """Send notifications to all subscribers of a repository for new releases."""  
        owner = repo_data["owner"]  
        repo = repo_data["repo"]  
          
        notification_text = self._format_release_notification(owner, repo, release_data)  
          
        # Handle legacy format with single 'subscribers' field  
        legacy_subscribers = repo_data.get("subscribers", set())  
        if legacy_subscribers:  
            for user_id in legacy_subscribers:  
                try:  
                    await self.bot.send_message(user_id, notification_text)  
                    logger.info(f"Sent release notification to user {user_id} for {owner}/{repo}")  
                except Exception as e:  
                    logger.error(f"Failed to send notification to user {user_id}: {e}")  
          
        # Handle new format with separate subscriber types  
        user_subscribers = repo_data.get("user_subscribers", set())  
        for user_id in user_subscribers:  
            try:  
                await self.bot.send_message(user_id, notification_text)  
                logger.info(f"Sent release notification to user {user_id} for {owner}/{repo}")  
            except Exception as e:  
                logger.error(f"Failed to send notification to user {user_id}: {e}")  
          
        # Send to channel subscribers  
        channel_subscribers = repo_data.get("channel_subscribers", set())  
        for chat_id in channel_subscribers:  
            try:  
                await self.bot.send_message(chat_id, notification_text)  
                logger.info(f"Sent release notification to channel {chat_id} for {owner}/{repo}")  
            except Exception as e:  
                logger.error(f"Failed to send notification to channel {chat_id}: {e}")  
          
        # Send to topic subscribers  
        topic_subscribers = repo_data.get("topic_subscribers", set())  
        for topic_key in topic_subscribers:  
            try:  
                chat_id, thread_id = topic_key.split(':')  
                await self.bot.send_message(  
                    int(chat_id),   
                    notification_text,   
                    message_thread_id=int(thread_id)  
                )  
                logger.info(f"Sent release notification to topic {topic_key} for {owner}/{repo}")  
            except Exception as e:  
                logger.error(f"Failed to send notification to topic {topic_key}: {e}")  
  
    async def _send_issue_notifications(self, repo_data: Dict, issue_data: Dict):  
        """Send notifications to all subscribers of a repository for new issues."""  
        owner = repo_data["owner"]  
        repo = repo_data["repo"]  
          
        notification_text = self._format_issue_notification(owner, repo, issue_data)  
          
        # Handle legacy format with single 'subscribers' field  
        legacy_subscribers = repo_data.get("subscribers", set())  
        if legacy_subscribers:  
            for user_id in legacy_subscribers:  
                try:  
                    await self.bot.send_message(user_id, notification_text)  
                    logger.info(f"Sent issue notification to user {user_id} for {owner}/{repo}")  
                except Exception as e:  
                    logger.error(f"Failed to send notification to user {user_id}: {e}")  
          
        # Handle new format with separate subscriber types  
        user_subscribers = repo_data.get("user_subscribers", set())  
        for user_id in user_subscribers:  
            try:  
                await self.bot.send_message(user_id, notification_text)  
                logger.info(f"Sent issue notification to user {user_id} for {owner}/{repo}")  
            except Exception as e:  
                logger.error(f"Failed to send notification to user {user_id}: {e}")  
          
        # Send to channel subscribers  
        channel_subscribers = repo_data.get("channel_subscribers", set())  
        for chat_id in channel_subscribers:  
            try:  
                await self.bot.send_message(chat_id, notification_text)  
                logger.info(f"Sent issue notification to channel {chat_id} for {owner}/{repo}")  
            except Exception as e:  
                logger.error(f"Failed to send notification to channel {chat_id}: {e}")  
          
        # Send to topic subscribers  
        topic_subscribers = repo_data.get("topic_subscribers", set())  
        for topic_key in topic_subscribers:  
            try:  
                chat_id, thread_id = topic_key.split(':')  
                await self.bot.send_message(  
                    int(chat_id),   
                    notification_text,   
                    message_thread_id=int(thread_id)  
                )  
                logger.info(f"Sent issue notification to topic {topic_key} for {owner}/{repo}")  
            except Exception as e:  
                logger.error(f"Failed to send notification to topic {topic_key}: {e}")  
  
    def _format_release_notification(  
        self, owner: str, repo: str, release_data: Dict  
    ) -> str:  
        """Format release notification message."""  
        tag_name = release_data.get("tag_name", "Unknown")  
        name = release_data.get("name", tag_name)  
        published_at = release_data.get("published_at", "")  
        html_url = release_data.get("html_url", "")  
  
        date_str = ""  
        if published_at:  
            date_str = f"📅 Published: {published_at.split('T')[0]}\n"  
  
        return f"""🚀 <b>New Release Available!</b>  
  
📦 Repository: <b>{owner}/{repo}</b>  
🏷️ Version: <b>{tag_name}</b>  
{date_str}  
<a href="{html_url}">View Release</a>"""  
  
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
        if len(body) > 300:  
            body = body[:300] + "..."  
  
        # Format the message according to your specification  
        message = f"""🪲 <a href="{author_url}">{author}</a> opened issue <code>{repo}#{number}</code>  

    <blockquote expandable>Title: {title}  
{body}</blockquote>
  
🔗 <a href="{html_url}">View Issue</a>  
#openedissue"""  
  
        return message  
  
    async def _check_stars_updates(self, repo_data: Dict):
        """
        Check for new starred repositories using a robust ID-based comparison.
        This method is resistant to false positives when repositories are unstarred.
        """
        github_username = repo_data.get("github_username")
        if not github_username:
            logger.warning(f"Stars tracking data is missing github_username: {repo_data}")
            return

        # Get the set of repo IDs from the last successful check.
        last_known_ids = repo_data.get("last_starred_repo_ids")

        try:
            # Fetch the current list of most recently starred repositories.
            current_page_repos = await self.github_api.get_authenticated_user_starred_repos(
                page=1, per_page=30
            )
        except Exception as e:
            logger.error(f"Failed to fetch starred repos for {github_username}: {e}")
            return

        if not current_page_repos:
            # If the user has no stars, we clear our stored state.
            if last_known_ids is not None:
                await self.tracker.update_last_starred_repo_ids(github_username, set())
            return

        current_page_ids = {str(repo.get("id")) for repo in current_page_repos}

        # If this is the first time checking, we just establish a baseline.
        if last_known_ids is None:
            await self.tracker.update_last_starred_repo_ids(github_username, current_page_ids)
            logger.info(f"Initialized star tracking for {github_username}. Baseline set with {len(current_page_ids)} repos.")
            return

        # --- Core Logic ---
        # We iterate through the new list (from newest to oldest) and collect
        # any repos that were not in our last known set of IDs.
        truly_new_repos = []
        for repo in current_page_repos:
            repo_id = str(repo.get("id"))
            if repo_id not in last_known_ids:
                # This ID is not in the last set we saw, so it's a new star.
                truly_new_repos.append(repo)
            else:
                # We found a repo that we already knew about. Since the list is
                # sorted by newness, we can be sure that everything after this
                # point is also old. We can stop looking.
                break

        # If we found any new repos, notify the user.
        if truly_new_repos:
            # Reverse the list to send notifications in chronological order.
            truly_new_repos.reverse()
            for new_repo in truly_new_repos:
                logger.info(f"Detected new star for {github_username}: {new_repo.get('full_name')}")
                await self._send_starred_repo_notification(repo_data, new_repo)

        # After every check, update the state to the latest set of IDs. This is crucial.
        await self.tracker.update_last_starred_repo_ids(github_username, current_page_ids)

    async def _send_starred_repo_notification(  
            self, repo_data: Dict, starred_repo: Dict  
        ):  
            """Send notification for newly starred repository using /repo format."""  
            # Handle legacy format with single 'subscribers' field  
            legacy_subscribers = repo_data.get("subscribers", set())  
            user_subscribers = repo_data.get("user_subscribers", set())  
            channel_subscribers = repo_data.get("channel_subscribers", set())  
            topic_subscribers = repo_data.get("topic_subscribers", set())  
      
            # Get additional repo data to match /repo format exactly  
            owner = starred_repo.get("owner", {}).get("login", "Unknown")  
            repo_name = starred_repo.get("name", "Unknown")  
      
            # Fetch complete repo data, languages, and latest release  
            repo_data_full = await self.github_api.get_repository(owner, repo_name)  
            languages = await self.github_api.get_repository_languages(owner, repo_name)  
            latest_release = await self.github_api.get_latest_release(owner, repo_name)  
      
            if repo_data_full:  
                # Use the exact same formatting as /repo command  
                from github.formatter import RepoFormatter  
      
                preview = RepoFormatter.format_repository_preview(  
                    repo_data_full, languages, latest_release  
                )  
      
                notification_text = f"{preview}"  
      
                # Send to legacy subscribers  
                for user_id in legacy_subscribers:  
                    try:  
                        await self.bot.send_message(user_id, notification_text)  
                        logger.info(  
                            f"Sent starred repo notification to user {user_id} for {owner}/{repo_name}"  
                        )  
                    except Exception as e:  
                        logger.error(  
                            f"Failed to send starred repo notification to user {user_id}: {e}"  
                        )  
      
                # Send to user subscribers  
                for user_id in user_subscribers:  
                    try:  
                        await self.bot.send_message(user_id, notification_text)  
                        logger.info(  
                            f"Sent starred repo notification to user {user_id} for {owner}/{repo_name}"  
                        )  
                    except Exception as e:  
                        logger.error(  
                            f"Failed to send starred repo notification to user {user_id}: {e}"  
                        )  
      
                # Send to channel subscribers  
                for chat_id in channel_subscribers:  
                    try:  
                        await self.bot.send_message(chat_id, notification_text)  
                        logger.info(  
                            f"Sent starred repo notification to channel {chat_id} for {owner}/{repo_name}"  
                        )  
                    except Exception as e:  
                        logger.error(  
                            f"Failed to send starred repo notification to channel {chat_id}: {e}"  
                        )  
      
                # Send to topic subscribers  
                for topic_key in topic_subscribers:  
                    try:  
                        chat_id, thread_id = topic_key.split(':')  
                        await self.bot.send_message(  
                            int(chat_id),   
                            notification_text,   
                            message_thread_id=int(thread_id)  
                        )  
                        logger.info(  
                            f"Sent starred repo notification to topic {topic_key} for {owner}/{repo_name}"  
                        )  
                    except Exception as e:  
                        logger.error(  
                            f"Failed to send starred repo notification to topic {topic_key}: {e}"  
                        )