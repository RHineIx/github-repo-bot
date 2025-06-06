"""  
Database management for repository tracking.  
"""  
import json  
import asyncio  
from typing import Dict, List, Optional, Set  
from telebot.asyncio_storage import StateMemoryStorage  
  
class RepositoryTracker:  
    """Manages tracked repositories and user subscriptions."""  
      
    def __init__(self):  
        self.storage = StateMemoryStorage()  
        self.tracked_repos: Dict[str, Dict] = {}  # repo_key -> repo_data  
        self.user_subscriptions: Dict[int, Set[str]] = {}  # user_id -> set of repo_keys  
          
    def _get_repo_key(self, owner: str, repo: str) -> str:  
        """Generate unique key for repository."""  
        return f"{owner}/{repo}"  
      
    async def add_tracked_repo(self, user_id: int, owner: str, repo: str) -> bool:  
        """Add repository to user's tracking list."""  
        repo_key = self._get_repo_key(owner, repo)  
          
        # Initialize user subscriptions if not exists  
        if user_id not in self.user_subscriptions:  
            self.user_subscriptions[user_id] = set()  
              
        # Add to user's subscriptions  
        self.user_subscriptions[user_id].add(repo_key)  
          
        # Initialize repo tracking data if not exists  
        if repo_key not in self.tracked_repos:  
            self.tracked_repos[repo_key] = {  
                'owner': owner,  
                'repo': repo,  
                'last_release_id': None,  
                'subscribers': set()  
            }  
              
        # Add user to repo subscribers  
        self.tracked_repos[repo_key]['subscribers'].add(user_id)  
        return True  
      
    async def remove_tracked_repo(self, user_id: int, owner: str, repo: str) -> bool:  
        """Remove repository from user's tracking list."""  
        repo_key = self._get_repo_key(owner, repo)  
          
        if user_id in self.user_subscriptions:  
            self.user_subscriptions[user_id].discard(repo_key)  
              
        if repo_key in self.tracked_repos:  
            self.tracked_repos[repo_key]['subscribers'].discard(user_id)  
              
            # Remove repo if no subscribers  
            if not self.tracked_repos[repo_key]['subscribers']:  
                del self.tracked_repos[repo_key]  
                  
        return True  
      
    async def get_user_tracked_repos(self, user_id: int) -> List[Dict[str, str]]:  
        """Get list of repositories tracked by user."""  
        if user_id not in self.user_subscriptions:  
            return []  
              
        repos = []  
        for repo_key in self.user_subscriptions[user_id]:  
            if repo_key in self.tracked_repos:  
                repo_data = self.tracked_repos[repo_key]  
                repos.append({  
                    'owner': repo_data['owner'],  
                    'repo': repo_data['repo'],  
                    'repo_key': repo_key  
                })  
        return repos  
      
    async def get_all_tracked_repos(self) -> List[Dict]:  
        """Get all tracked repositories for monitoring."""  
        return list(self.tracked_repos.values())  
      
    async def update_last_release(self, owner: str, repo: str, release_id: str):  
        """Update last known release ID for repository."""  
        repo_key = self._get_repo_key(owner, repo)  
        if repo_key in self.tracked_repos:  
            self.tracked_repos[repo_key]['last_release_id'] = release_id