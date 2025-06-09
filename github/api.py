# rhineix/github-repo-bot/github-repo-bot-353a356069cb9a7c65f342d5b42fee8862333925/github/api.py
import aiohttp
import asyncio
import time
import logging
from typing import Optional, Dict, Any, List
from config import config

logger = logging.getLogger(__name__)

class GitHubAPI:
    """Asynchronous GitHub API client with per-user token support and caching."""

    def __init__(
        self,
        token: Optional[str] = None,
        user_id: Optional[int] = None,
        token_manager=None,
    ):
        self.token_manager = token_manager
        self.user_id = user_id
        self.token = token or config.GITHUB_TOKEN
        self.base_url = config.GITHUB_API_BASE

        # Caching mechanism
        self._cache = {}
        self.cache_ttl = config.CACHE_TTL_SECONDS

        # Set up basic headers synchronously
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Repo-Preview-Bot/1.0",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    async def _setup_headers(self):
        """Setup headers for authenticated requests."""
        if self.token_manager and self.user_id:
            user_token = await self.token_manager.get_token(self.user_id)
            if user_token:
                self.token = user_token
                self.headers["Authorization"] = f"token {self.token}"
        elif self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def _check_cache(self, key: str) -> Optional[Any]:
        """Checks if a valid (non-expired) entry exists in the cache."""
        if key in self._cache:
            cached_time, cached_data = self._cache[key]
            if time.time() - cached_time < self.cache_ttl:
                logger.info(f"Cache hit for key: {key}")
                return cached_data
        logger.info(f"Cache miss for key: {key}")
        return None

    def _update_cache(self, key: str, data: Any):
        """Updates the cache with new data."""
        self._cache[key] = (time.time(), data)

    async def _make_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make an HTTP request to GitHub API."""
        await self._setup_headers()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT)
        ) as session:
            try:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"GitHub API error: {response.status} - {await response.text()} for URL {url}")
                        return None
            except asyncio.TimeoutError:
                logger.error(f"Request timeout for: {url}")
                return None
            except Exception as e:
                logger.error(f"Request error for {url}: {e}")
                return None

    async def get_repository(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get repository information, with caching."""
        cache_key = f"repo:{owner}/{repo}"
        cached_data = self._check_cache(cache_key)
        if cached_data:
            return cached_data
        
        live_data = await self._make_request(f"repos/{owner}/{repo}")
        if live_data:
            self._update_cache(cache_key, live_data)
        return live_data

    async def get_repository_languages(self, owner: str, repo: str) -> Optional[Dict[str, int]]:
        """Get repository programming languages, with caching."""
        cache_key = f"languages:{owner}/{repo}"
        cached_data = self._check_cache(cache_key)
        if cached_data:
            return cached_data

        live_data = await self._make_request(f"repos/{owner}/{repo}/languages")
        if live_data:
            self._update_cache(cache_key, live_data)
        return live_data

    async def get_latest_release(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Get latest release information. We don't cache this heavily to keep it fresh."""
        # A shorter TTL can be used here if needed, but for simplicity we use the global TTL.
        cache_key = f"latest_release:{owner}/{repo}"
        cached_data = self._check_cache(cache_key)
        if cached_data:
            return cached_data
        
        live_data = await self._make_request(f"repos/{owner}/{repo}/releases/latest")
        if live_data:
            self._update_cache(cache_key, live_data)
        return live_data

    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information, with caching."""
        cache_key = f"user:{username}"
        cached_data = self._check_cache(cache_key)
        if cached_data:
            return cached_data

        live_data = await self._make_request(f"users/{username}")
        if live_data:
            self._update_cache(cache_key, live_data)
        return live_data

    async def get_rate_limit(self) -> Optional[Dict[str, Any]]:
        """Gets the current rate limit status. This is NOT cached."""
        return await self._make_request("rate_limit")

    # --- Methods below are generally not cached as they are user-specific or paginated ---

    async def get_repository_tags(self, owner: str, repo: str, page: int = 1, per_page: int = None) -> Optional[List[Dict[str, Any]]]:
        per_page = per_page or config.ITEMS_PER_PAGE
        return await self._make_request(f"repos/{owner}/{repo}/tags?page={page}&per_page={per_page}")

    async def get_repository_releases(self, owner: str, repo: str, page: int = 1, per_page: int = None) -> Optional[List[Dict[str, Any]]]:
        per_page = per_page or config.ITEMS_PER_PAGE
        return await self._make_request(f"repos/{owner}/{repo}/releases?page={page}&per_page={per_page}")

    async def get_release_assets(self, owner: str, repo: str, release_id: int) -> Optional[List[Dict[str, Any]]]:
        return await self._make_request(f"repos/{owner}/{repo}/releases/{release_id}/assets")

    async def get_repository_contributors(self, owner: str, repo: str, page: int = 1, per_page: int = None) -> Optional[List[Dict[str, Any]]]:
        per_page = per_page or config.ITEMS_PER_PAGE
        return await self._make_request(f"repos/{owner}/{repo}/contributors?page={page}&per_page={per_page}")
    
    # ... (rest of the file remains the same) ...

    async def download_asset(self, asset_url: str, asset_size: int) -> Optional[bytes]:
        # Download logic remains the same, no caching needed here.
        max_size_bytes = config.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024
        if asset_size > max_size_bytes:
            print(f"Asset too large: {asset_size} bytes > {max_size_bytes} bytes")
            return None

        timeout = max(
            config.REQUEST_TIMEOUT, asset_size // (1024 * 1024) * 10
        )

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as session:
            try:
                async with session.get(asset_url, headers=self.headers) as response:
                    if response.status == 200:
                        data = bytearray()
                        async for chunk in response.content.iter_chunked(8192):
                            data.extend(chunk)
                        return bytes(data)
                    else:
                        print(f"Download failed: {response.status}")
                        return None
            except asyncio.TimeoutError:
                print(f"Download timeout for asset: {asset_url}")
                return None
            except Exception as e:
                print(f"Download error: {e}")
                return None

    async def get_repository_issues( self, owner: str, repo: str, state: str = "open", per_page: int = 1) -> Optional[List[Dict[str, Any]]]:
        return await self._make_request(f"repos/{owner}/{repo}/issues?state={state}&per_page={per_page}&sort=created&direction=desc")

    async def get_authenticated_user_starred_repos(self, page: int = 1, per_page: int = 30) -> Optional[List[Dict[str, Any]]]:
        return await self._make_request(f"user/starred?page={page}&per_page={per_page}&sort=created&direction=desc")

    async def get_authenticated_user(self) -> Optional[Dict[str, Any]]:
        return await self._make_request("user")