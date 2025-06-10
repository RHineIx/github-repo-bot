import aiosqlite
import json
import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

class RepositoryTracker:
    """
    Manages tracked repositories and user subscriptions using a persistent SQLite database.
    """

    def __init__(self, db_path: str = "tracking.db"):
        self.db_path = db_path
        self._db_initialized = False

    async def init_db(self):
        """
        Initializes the database and creates tables if they don't exist.
        """
        if self._db_initialized:
            return

        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # Main table for tracked items (repos, stars)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS tracked_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_key TEXT UNIQUE NOT NULL, -- e.g., 'owner/repo:releases' or 'stars:username'
                        item_type TEXT NOT NULL, -- 'repo' or 'stars'
                        owner TEXT,
                        repo TEXT,
                        github_username TEXT,
                        track_type TEXT, -- 'releases', 'issues', or null for stars
                        last_release_id TEXT,
                        last_issue_id TEXT,
                        last_starred_repo_ids_json TEXT -- Storing set as JSON
                    )
                """)

                # Table for subscriptions (linking users/channels to items)
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        item_id INTEGER NOT NULL,
                        subscriber_id TEXT NOT NULL, -- user_id, channel_id, or topic_key
                        subscriber_type TEXT NOT NULL, -- 'user', 'channel', 'topic'
                        FOREIGN KEY (item_id) REFERENCES tracked_items (id) ON DELETE CASCADE
                    )
                """)
                await conn.commit()
            self._db_initialized = True
            logger.info("Tracking database initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing tracking database: {e}")
            raise

    def _get_item_key(self, **kwargs) -> str:
        """Generates a unique key for a trackable item."""
        if kwargs.get('type') == 'stars':
            return f"stars:{kwargs['github_username']}"
        else:
            return f"{kwargs['owner']}/{kwargs['repo']}:{kwargs['track_type']}"

    async def add_tracked_repo_with_destination(
        self,
        user_id: int,
        owner: str,
        repo: str,
        track_types: List[str],
        chat_id: Optional[int] = None,
        thread_id: Optional[int] = None,
    ) -> bool:
        """Adds repository tracking with optional destination to the database."""
        async with aiosqlite.connect(self.db_path) as conn:
            for track_type in track_types:
                item_key = self._get_item_key(owner=owner, repo=repo, track_type=track_type)

                # 1. Find or create the tracked_item
                cursor = await conn.execute("SELECT id FROM tracked_items WHERE item_key = ?", (item_key,))
                item = await cursor.fetchone()

                if not item:
                    await conn.execute(
                        "INSERT INTO tracked_items (item_key, item_type, owner, repo, track_type) VALUES (?, ?, ?, ?, ?)",
                        (item_key, 'repo', owner, repo, track_type)
                    )
                    await conn.commit()
                    cursor = await conn.execute("SELECT id FROM tracked_items WHERE item_key = ?", (item_key,))
                    item = await cursor.fetchone()
                
                item_id = item[0]

                # 2. Determine subscriber type and ID
                if chat_id and thread_id:
                    subscriber_type = 'topic'
                    subscriber_id = f"{chat_id}:{thread_id}"
                elif chat_id:
                    subscriber_type = 'channel'
                    subscriber_id = str(chat_id)
                else:
                    subscriber_type = 'user'
                    subscriber_id = str(user_id)
                
                # 3. Add subscription if it doesn't exist
                await conn.execute(
                    "INSERT OR IGNORE INTO subscriptions (item_id, subscriber_id, subscriber_type) VALUES (?, ?, ?)",
                    (item_id, subscriber_id, subscriber_type)
                )
                await conn.commit()
        return True

    async def add_user_stars_tracking(self, user_id: int, github_username: str) -> bool:
        """Adds user's GitHub stars tracking to the database."""
        item_key = self._get_item_key(type='stars', github_username=github_username)
        async with aiosqlite.connect(self.db_path) as conn:
            # 1. Find or create the tracked_item for stars
            cursor = await conn.execute("SELECT id FROM tracked_items WHERE item_key = ?", (item_key,))
            item = await cursor.fetchone()

            if not item:
                await conn.execute(
                    "INSERT INTO tracked_items (item_key, item_type, github_username, last_starred_repo_ids_json) VALUES (?, ?, ?, ?)",
                    (item_key, 'stars', github_username, json.dumps(None)) # Initialize with null
                )
                await conn.commit()
                cursor = await conn.execute("SELECT id FROM tracked_items WHERE item_key = ?", (item_key,))
                item = await cursor.fetchone()

            item_id = item[0]

            # 2. Add user subscription
            await conn.execute(
                "INSERT OR IGNORE INTO subscriptions (item_id, subscriber_id, subscriber_type) VALUES (?, ?, ?)",
                (item_id, str(user_id), 'user')
            )
            await conn.commit()
        return True

    async def remove_tracked_repo(self, user_id: int, owner: str, repo: str) -> bool:
        """Removes a user's subscription to all track types for a repo."""
        async with aiosqlite.connect(self.db_path) as conn:
            # We only remove the user's subscription, not the tracked item itself,
            # as others might still be tracking it.
            for track_type in ["releases", "issues"]:
                item_key = self._get_item_key(owner=owner, repo=repo, track_type=track_type)
                await conn.execute("""
                    DELETE FROM subscriptions
                    WHERE subscriber_id = ? AND subscriber_type = 'user' AND item_id = (
                        SELECT id FROM tracked_items WHERE item_key = ?
                    )
                """, (str(user_id), item_key))
            await conn.commit()
        # We can add a cleanup task later to remove tracked_items with no subscriptions.
        return True

    async def get_user_tracked_repos(self, user_id: int) -> List[Dict[str, str]]:
        """Gets list of repositories tracked by a specific user from the database."""
        repos = []
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT ti.owner, ti.repo, ti.track_type
                FROM tracked_items ti
                JOIN subscriptions s ON ti.id = s.item_id
                WHERE s.subscriber_id = ? AND s.subscriber_type = 'user' AND ti.item_type = 'repo'
            """, (str(user_id),))
            rows = await cursor.fetchall()
            unique_repos = {}
            for row in rows:
                repo_key = f"{row['owner']}/{row['repo']}"
                if repo_key not in unique_repos:
                    unique_repos[repo_key] = {"owner": row["owner"], "repo": row["repo"]}
            repos = list(unique_repos.values())
        return repos

    async def get_all_tracked_repos(self) -> List[Dict]:
        """Gets all tracked items and their subscribers for the monitor."""
        all_items = []
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            # 1. Get all tracked items
            items_cursor = await conn.execute("SELECT * FROM tracked_items")
            items_rows = await items_cursor.fetchall()
            
            # 2. For each item, get its subscribers
            for item_row in items_rows:
                item_dict = dict(item_row)
                
                # Initialize subscriber sets
                item_dict["user_subscribers"] = set()
                item_dict["channel_subscribers"] = set()
                item_dict["topic_subscribers"] = set()
                # For stars tracking, it uses a generic 'subscribers' key. We'll populate that too.
                item_dict["subscribers"] = set()
                
                subs_cursor = await conn.execute("SELECT subscriber_id, subscriber_type FROM subscriptions WHERE item_id = ?", (item_dict['id'],))
                subs_rows = await subs_cursor.fetchall()
                
                for sub_row in subs_rows:
                    sub_type = sub_row['subscriber_type']
                    sub_id = sub_row['subscriber_id']
                    
                    if sub_type == 'user':
                        user_id = int(sub_id)
                        item_dict["user_subscribers"].add(user_id)
                        item_dict["subscribers"].add(user_id) # For stars tracking
                    elif sub_type == 'channel':
                        item_dict["channel_subscribers"].add(int(sub_id))
                    elif sub_type == 'topic':
                        item_dict["topic_subscribers"].add(sub_id)

                # Decode the JSON field for starred repos
                if item_dict.get('last_starred_repo_ids_json'):
                    ids_json = item_dict.pop('last_starred_repo_ids_json')
                    # Set can't be JSON serialized, so they were stored as list. Convert back.
                    deserialized = json.loads(ids_json)
                    item_dict['last_starred_repo_ids'] = set(deserialized) if deserialized is not None else None


                all_items.append(item_dict)

        return all_items

    async def _update_field(self, item_key: str, field_name: str, value: any):
        """Generic helper to update a single field for a tracked item."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                f"UPDATE tracked_items SET {field_name} = ? WHERE item_key = ?",
                (value, item_key)
            )
            await conn.commit()

    async def update_last_release(self, owner: str, repo: str, release_id: str):
        item_key = self._get_item_key(owner=owner, repo=repo, track_type='releases')
        await self._update_field(item_key, "last_release_id", release_id)

    async def update_last_issue(self, owner: str, repo: str, issue_id: str):
        item_key = self._get_item_key(owner=owner, repo=repo, track_type='issues')
        await self._update_field(item_key, "last_issue_id", issue_id)

    async def update_last_starred_repo_ids(self, github_username: str, starred_repo_ids: set):
        item_key = self._get_item_key(type='stars', github_username=github_username)
        # We must serialize the set to a JSON string (as a list) to store it.
        value_to_store = json.dumps(list(starred_repo_ids))
        await self._update_field(item_key, "last_starred_repo_ids_json", value_to_store)
    
    async def count_user_subscriptions(self, user_id: int) -> int:
        """Counts how many items a specific user is subscribed to."""
        async with aiosqlite.connect(self.db_path) as conn:
            # We count distinct tracked items to avoid counting 'releases' and 'issues' for the same repo twice.
            cursor = await conn.execute("""
                SELECT COUNT(DISTINCT ti.id)
                FROM tracked_items ti
                JOIN subscriptions s ON ti.id = s.item_id
                WHERE s.subscriber_id = ? AND s.subscriber_type = 'user'
            """, (str(user_id),))
            result = await cursor.fetchone()
            return result[0] if result else 0
        
    async def cleanup_orphaned_items(self) -> int:
        """
        Removes items from tracked_items that have no subscribers.
        This prevents the monitor from checking unused repositories.
        Returns the number of cleaned items.
        """
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # This query selects the IDs of all tracked_items that do not
                # have a corresponding entry in the subscriptions table.
                cursor = await conn.execute("""
                    DELETE FROM tracked_items
                    WHERE id IN (
                        SELECT ti.id
                        FROM tracked_items ti
                        LEFT JOIN subscriptions s ON ti.id = s.item_id
                        WHERE s.id IS NULL
                    )
                """)
                await conn.commit()
                
                cleaned_count = cursor.rowcount
                if cleaned_count > 0:
                    logger.info(f"Database cleanup: Removed {cleaned_count} orphaned tracked items.")
                else:
                    logger.info("Database cleanup: No orphaned items to remove.")
                
                return cleaned_count
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            return 0