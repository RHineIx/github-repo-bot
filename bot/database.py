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
        # New: Channel and topic subscriptions  
        self.channel_subscriptions: Dict[int, Set[str]] = {}  # chat_id -> repo_keys  
        self.topic_subscriptions: Dict[str, Set[str]] = {}    # "chat_id:topic_id" -> repo_keys  

    def _get_destination_key(self, chat_id: Optional[int], thread_id: Optional[int]) -> str:  
            """Generate key for destination (channel or topic)."""  
            if chat_id and thread_id:  
                return f"topic:{chat_id}:{thread_id}"  
            elif chat_id:  
                return f"channel:{chat_id}"  
            else:  
                return "user"  
      
    async def add_tracked_repo_with_destination(  
        self,   
        user_id: int,   
        owner: str,   
        repo: str,   
        track_types: List[str],  
        chat_id: Optional[int] = None,  
        thread_id: Optional[int] = None  
    ) -> bool:  
        """Add repository tracking with optional destination."""  
            
        for track_type in track_types:  
            repo_key = self._get_repo_key(owner, repo, track_type)  
            destination_key = self._get_destination_key(chat_id, thread_id)  
                
            # Initialize repo tracking data if not exists  
            if repo_key not in self.tracked_repos:  
                self.tracked_repos[repo_key] = {  
                    "owner": owner,  
                    "repo": repo,  
                    "track_type": track_type,  
                    "last_release_id": None if track_type == "releases" else None,  
                    "last_issue_id": None if track_type == "issues" else None,  
                    "user_subscribers": set(),  
                    "channel_subscribers": set(),  
                    "topic_subscribers": set(),  
                }  
                
            # Add subscriber based on destination type  
            if chat_id and thread_id:  
                # Topic subscription  
                topic_key = f"{chat_id}:{thread_id}"  
                if topic_key not in self.topic_subscriptions:  
                    self.topic_subscriptions[topic_key] = set()  
                self.topic_subscriptions[topic_key].add(repo_key)  
                self.tracked_repos[repo_key]["topic_subscribers"].add(topic_key)  
                    
            elif chat_id:  
                # Channel subscription  
                if chat_id not in self.channel_subscriptions:  
                    self.channel_subscriptions[chat_id] = set()  
                self.channel_subscriptions[chat_id].add(repo_key)  
                self.tracked_repos[repo_key]["channel_subscribers"].add(chat_id)  
                    
            else:  
                # User subscription (default behavior)  
                if user_id not in self.user_subscriptions:  
                    self.user_subscriptions[user_id] = set()  
                self.user_subscriptions[user_id].add(repo_key)  
                self.tracked_repos[repo_key]["user_subscribers"].add(user_id)  
            
        return True
    
    async def migrate_legacy_data(self):  
        """Migrate legacy repository data to new format."""  
        for repo_key, repo_data in self.tracked_repos.items():  
            # Check if this is legacy format  
            if "subscribers" in repo_data and "user_subscribers" not in repo_data:  
                # Migrate to new format  
                legacy_subscribers = repo_data.pop("subscribers", set())  
                repo_data["user_subscribers"] = legacy_subscribers  
                repo_data["channel_subscribers"] = set()  
                repo_data["topic_subscribers"] = set()  
                  
                print(f"Migrated legacy data for {repo_key}")

    async def add_user_stars_tracking(self, user_id: int, github_username: str) -> bool:
        """Add user's GitHub stars tracking."""
        tracking_key = f"stars:{github_username}"

        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()

        self.user_subscriptions[user_id].add(tracking_key)

        if tracking_key not in self.tracked_repos:
            self.tracked_repos[tracking_key] = {
                "type": "stars",
                "github_username": github_username,
                "last_starred_repo_ids": None,  # Initialize as None for the first run
                "subscribers": {user_id},
            }
        else:
            self.tracked_repos[tracking_key]["subscribers"].add(user_id)

        return True

    def _get_repo_key(self, owner: str, repo: str, track_type: str) -> str:
        """Generate unique key for repository with tracking type."""
        return f"{owner}/{repo}:{track_type}"

    async def add_tracked_repo(
        self, user_id: int, owner: str, repo: str, track_types: List[str]
    ) -> bool:
        """Add repository to user's tracking list with specified types."""
        for track_type in track_types:
            repo_key = self._get_repo_key(owner, repo, track_type)

            # Initialize user subscriptions if not exists
            if user_id not in self.user_subscriptions:
                self.user_subscriptions[user_id] = set()

            # Add to user's subscriptions
            self.user_subscriptions[user_id].add(repo_key)

            # Initialize repo tracking data if not exists
            if repo_key not in self.tracked_repos:
                self.tracked_repos[repo_key] = {
                    "owner": owner,
                    "repo": repo,
                    "track_type": track_type,
                    "last_release_id": None if track_type == "releases" else None,
                    "last_issue_id": None if track_type == "issues" else None,
                    "subscribers": set(),
                }

            # Add user to repo subscribers
            self.tracked_repos[repo_key]["subscribers"].add(user_id)
        return True

    async def remove_tracked_repo(self, user_id: int, owner: str, repo: str) -> bool:
        """Remove repository from user's tracking list."""

        track_types = ["releases", "issues"]

        for track_type in track_types:
            repo_key = self._get_repo_key(owner, repo, track_type)

            if user_id in self.user_subscriptions:
                self.user_subscriptions[user_id].discard(repo_key)

            if repo_key in self.tracked_repos:
                self.tracked_repos[repo_key]["subscribers"].discard(user_id)

                # Remove repo if no subscribers
                if not self.tracked_repos[repo_key]["subscribers"]:
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

                if repo_data.get("type") == "stars":
                    continue

                repos.append(
                    {
                        "owner": repo_data.get("owner", "Unknown"),
                        "repo": repo_data.get("repo", "Unknown"),
                        "repo_key": repo_key,
                        "track_type": repo_data.get("track_type", "Unknown"),
                    }
                )
        return repos

    async def get_all_tracked_repos(self) -> List[Dict]:
        """Get all tracked repositories for monitoring."""
        return list(self.tracked_repos.values())

    async def update_last_release(self, owner: str, repo: str, release_id: str):
        """Update last known release ID for repository."""
        # Find the repo key for releases tracking
        repo_key = f"{owner}/{repo}:releases"
        if repo_key in self.tracked_repos:
            self.tracked_repos[repo_key]["last_release_id"] = release_id

    async def update_last_issue(self, owner: str, repo: str, issue_id: str):
        """Update last known issue ID for repository."""
        # Find the repo key for issues tracking
        repo_key = f"{owner}/{repo}:issues"
        if repo_key in self.tracked_repos:
            self.tracked_repos[repo_key]["last_issue_id"] = issue_id

    async def update_last_starred_repo_ids(self, github_username: str, starred_repo_ids: set):
        """Update the last known set of starred repository IDs for a user."""
        tracking_key = f"stars:{github_username}"
        if tracking_key in self.tracked_repos:
            self.tracked_repos[tracking_key]["last_starred_repo_ids"] = starred_repo_ids
