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
                logger.error(f"Error checking {repo_data['owner']}/{repo_data['repo']}: {e}")  
                  
    async def _check_repository_updates(self, repo_data: Dict):  
        """Check a single repository for updates."""  
        owner = repo_data['owner']  
        repo = repo_data['repo']  
        last_release_id = repo_data.get('last_release_id')  
          
        # Get latest release  
        latest_release = await self.github_api.get_latest_release(owner, repo)  
          
        if latest_release:  
            current_release_id = str(latest_release.get('id'))  
              
            # Check if this is a new release  
            if last_release_id != current_release_id:  
                # Update stored release ID  
                await self.tracker.update_last_release(owner, repo, current_release_id)  
                  
                # Send notifications to subscribers (only if we had a previous release)  
                if last_release_id is not None:  
                    await self._send_release_notifications(repo_data, latest_release)  
                      
    async def _send_release_notifications(self, repo_data: Dict, release_data: Dict):  
        """Send notifications to all subscribers of a repository."""  
        owner = repo_data['owner']  
        repo = repo_data['repo']  
        subscribers = repo_data['subscribers']  
          
        notification_text = self._format_release_notification(owner, repo, release_data)  
          
        for user_id in subscribers:  
            try:  
                await self.bot.send_message(user_id, notification_text)  
                logger.info(f"Sent release notification to user {user_id} for {owner}/{repo}")  
            except Exception as e:  
                logger.error(f"Failed to send notification to user {user_id}: {e}")  
                  
    def _format_release_notification(self, owner: str, repo: str, release_data: Dict) -> str:  
        """Format release notification message."""  
        tag_name = release_data.get('tag_name', 'Unknown')  
        name = release_data.get('name', tag_name)  
        published_at = release_data.get('published_at', '')  
        html_url = release_data.get('html_url', '')  
          
        date_str = ""  
        if published_at:  
            date_str = f"📅 Published: {published_at.split('T')[0]}\n"  
              
        return f"""🚀 <b>New Release Available!</b>  
  
📦 Repository: <b>{owner}/{repo}</b>  
🏷️ Version: <b>{tag_name}</b>  
{date_str}  
<a href="{html_url}">View Release</a>"""