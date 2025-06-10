import aiohttp
import asyncio
import time
import logging
from typing import Optional, Dict, Any, List
from config import config

logger = logging.getLogger(__name__)

class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"GitHub API Error {status_code}: {message}")

class GitHubAPI:
    """Asynchronous GitHub API client with a shared cache and per-user token support."""

    # 1. The cache is now a class variable, shared across all instances.
    _cache: Dict[str, Any] = {}

    def __init__(
        self,
        token: Optional[str] = "USE_FALLBACK",  # Use a sentinel value
        user_id: Optional[int] = None,
        token_manager=None,
    ):
        self.token_manager = token_manager
        self.user_id = user_id

        # New logic: Only fall back to the global token if no token is explicitly passed.
        if token == "USE_FALLBACK":
            self.token = config.GITHUB_TOKEN
        else:
            self.token = token # Respect the passed value, even if it's None

        # --- The missing lines that caused the error ---
        self.base_url = config.GITHUB_API_BASE
        self.cache_ttl = config.CACHE_TTL_SECONDS
        # --- End of missing lines ---

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
        """Checks if a valid (non-expired) entry exists in the shared cache."""
        # 3. Accessing the cache via the class name GitHubAPI._cache
        if key in GitHubAPI._cache:
            cached_time, cached_data = GitHubAPI._cache[key]
            if time.time() - cached_time < self.cache_ttl:
                logger.info(f"Shared cache hit for key: {key}")
                return cached_data
        logger.info(f"Shared cache miss for key: {key}")
        return None

    def _update_cache(self, key: str, data: Any):
        """Updates the shared cache with new data."""
        # 3. Accessing the cache via the class name GitHubAPI._cache
        GitHubAPI._cache[key] = (time.time(), data)

    async def _make_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make an HTTP request to GitHub API with smart rate limit handling."""
        await self._setup_headers()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        while True: # Loop to allow for retries
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT)
            ) as session:
                try:
                    async with session.get(url, headers=self.headers) as response:
                        # Success case
                        if response.status == 200:
                            return await response.json()
                        
                        # Rate limit handling case
                        elif response.status == 403 and 'X-RateLimit-Reset' in response.headers:
                            reset_timestamp = int(response.headers['X-RateLimit-Reset'])
                            current_time = int(time.time())
                            wait_duration = max(reset_timestamp - current_time, 0) + 2 # Add 2s buffer
                            
                            logger.warning(
                                f"Rate limit exceeded. Waiting for {wait_duration} seconds before retrying."
                            )
                            await asyncio.sleep(wait_duration)
                            continue # Retry the request by restarting the loop

                        # Other error cases - THIS IS THE MODIFIED PART
                        else:
                            error_text = await response.text()
                            logger.error(f"GitHub API error: {response.status} - {error_text} for URL {url}")
                            # Raise our custom exception instead of returning None
                            raise GitHubAPIError(response.status, error_text)
                            
                except asyncio.TimeoutError as e:
                    logger.error(f"Request timeout for: {url}")
                    raise GitHubAPIError(408, str(e)) # Raise custom exception for timeout
                except Exception as e:
                    # Re-raise other exceptions as our custom type for consistent handling
                    if not isinstance(e, GitHubAPIError):
                         logger.error(f"Request error for {url}: {e}")
                         raise GitHubAPIError(500, str(e))
                    else:
                        raise e

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
    
    async def download_asset(self, asset_url: str, asset_size: int) -> Optional[bytes]:
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