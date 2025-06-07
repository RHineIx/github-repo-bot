"""  
GitHub API client for fetching repository and user information.  
"""  
import aiohttp  
import asyncio  
from typing import Optional, Dict, Any, List  
from config import config  
  
  
class GitHubAPI:  
    """Asynchronous GitHub API client with per-user token support."""  
      
    def __init__(self, token: Optional[str] = None, user_id: Optional[int] = None, token_manager=None):  
            self.token_manager = token_manager  
            self.user_id = user_id  
            self.token = token or config.GITHUB_TOKEN  
            self.base_url = config.GITHUB_API_BASE  
              
            # Set up basic headers synchronously  
            self.headers = {  
                'Accept': 'application/vnd.github.v3+json',  
                'User-Agent': 'GitHub-Repo-Preview-Bot/1.0'  
            }  
            if self.token:  
                self.headers['Authorization'] = f'token {self.token}'

    async def _setup_headers(self):  
        """Setup headers for authenticated requests."""  
        if self.token_manager and self.user_id:  
            user_token = await self.token_manager.get_token(self.user_id)  
            if user_token:  
                self.token = user_token  
                self.headers['Authorization'] = f'token {self.token}'  
        elif self.token:  
            self.headers['Authorization'] = f'token {self.token}'
      
    async def _make_request(self, endpoint: str) -> Optional[Dict[str, Any]]:  
        """  
        Make an HTTP request to GitHub API.  
          
        Args:  
            endpoint: API endpoint path  
              
        Returns:  
            JSON response data or None if request failed  
        """  
        url = f"{self.base_url}/{endpoint.lstrip('/')}"  
          
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT)) as session:  
            try:  
                async with session.get(url, headers=self.headers) as response:  
                    if response.status == 200:  
                        return await response.json()  
                    elif response.status == 404:  
                        return None  
                    else:  
                        print(f"GitHub API error: {response.status} - {await response.text()}")  
                        return None  
            except asyncio.TimeoutError:  
                print(f"Request timeout for: {url}")  
                return None  
            except Exception as e:  
                print(f"Request error for {url}: {e}")  
                return None  
      
    async def get_repository(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:  
        """  
        Get repository information.  
          
        Args:  
            owner: Repository owner username  
            repo: Repository name  
              
        Returns:  
            Repository data or None if not found  
        """  
        return await self._make_request(f"repos/{owner}/{repo}")  
      
    async def get_repository_languages(self, owner: str, repo: str) -> Optional[Dict[str, int]]:  
        """  
        Get repository programming languages with byte counts.  
          
        Args:  
            owner: Repository owner username  
            repo: Repository name  
              
        Returns:  
            Language data with byte counts or None if not found  
        """  
        return await self._make_request(f"repos/{owner}/{repo}/languages")  
      
    async def get_latest_release(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:  
        """  
        Get latest release information.  
          
        Args:  
            owner: Repository owner username  
            repo: Repository name  
              
        Returns:  
            Latest release data or None if no releases  
        """  
        return await self._make_request(f"repos/{owner}/{repo}/releases/latest")  
      
    async def get_repository_tags(self, owner: str, repo: str, page: int = 1, per_page: int = None) -> Optional[List[Dict[str, Any]]]:  
        """  
        Get repository tags with pagination.  
          
        Args:  
            owner: Repository owner username  
            repo: Repository name  
            page: Page number (1-based)  
            per_page: Number of items per page  
              
        Returns:  
            List of tag data or None if not found  
        """  
        per_page = per_page or config.ITEMS_PER_PAGE  
        return await self._make_request(f"repos/{owner}/{repo}/tags?page={page}&per_page={per_page}")  
      
    async def get_repository_releases(self, owner: str, repo: str, page: int = 1, per_page: int = None) -> Optional[List[Dict[str, Any]]]:  
        """  
        Get repository releases with pagination.  
          
        Args:  
            owner: Repository owner username  
            repo: Repository name  
            page: Page number (1-based)  
            per_page: Number of items per page  
              
        Returns:  
            List of release data or None if not found  
        """  
        per_page = per_page or config.ITEMS_PER_PAGE  
        return await self._make_request(f"repos/{owner}/{repo}/releases?page={page}&per_page={per_page}")  
      
    async def get_release_assets(self, owner: str, repo: str, release_id: int) -> Optional[List[Dict[str, Any]]]:  
        """  
        Get assets for a specific release.  
          
        Args:  
            owner: Repository owner username  
            repo: Repository name  
            release_id: Release ID  
              
        Returns:  
            List of asset data or None if not found  
        """  
        return await self._make_request(f"repos/{owner}/{repo}/releases/{release_id}/assets")  
      
    async def get_repository_contributors(self, owner: str, repo: str, page: int = 1, per_page: int = None) -> Optional[List[Dict[str, Any]]]:  
        """  
        Get repository contributors with pagination.  
          
        Args:  
            owner: Repository owner username  
            repo: Repository name  
            page: Page number (1-based)  
            per_page: Number of items per page  
              
        Returns:  
            List of contributor data or None if not found  
        """  
        per_page = per_page or config.ITEMS_PER_PAGE  
        return await self._make_request(f"repos/{owner}/{repo}/contributors?page={page}&per_page={per_page}")  
      
    async def download_asset(self, asset_url: str, asset_size: int) -> Optional[bytes]:  
        """  
        Download a release asset if it's within size limits.  
        
        Args:  
            asset_url: Direct download URL for the asset  
            asset_size: Size of the asset in bytes  
            
        Returns:  
            Asset data as bytes or None if download failed or too large  
        """  
        # Check size limit  
        max_size_bytes = config.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024  
        if asset_size > max_size_bytes:  
            print(f"Asset too large: {asset_size} bytes > {max_size_bytes} bytes")  
            return None  
        
        # Use longer timeout for large files  
        timeout = max(config.REQUEST_TIMEOUT, asset_size // (1024 * 1024) * 10)  # 10 seconds per MB  
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:  
            try:  
                async with session.get(asset_url, headers=self.headers) as response:  
                    if response.status == 200:  
                        # Read the file in chunks to handle large files better  
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
            
    async def get_asset_download_url(self, asset_id: int) -> Optional[Dict[str, Any]]:  
        """  
        Get asset download information by ID.  
        
        Args:  
            asset_id: GitHub asset ID  
            
        Returns:  
            Asset data including download URL or None if not found  
        """  
        return await self._make_request(f"releases/assets/{asset_id}")
    
    async def get_repository_issues(self, owner: str, repo: str, state: str = "open", per_page: int = 1) -> Optional[List[Dict[str, Any]]]:  
        """  
        Get repository issues.  
          
        Args:  
            owner: Repository owner username  
            repo: Repository name  
            state: Issue state (open, closed, all)  
            per_page: Number of items per page  
              
        Returns:  
            List of issue data or None if not found  
        """  
        return await self._make_request(f"repos/{owner}/{repo}/issues?state={state}&per_page={per_page}&sort=created&direction=desc")
      
    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:  
        """  
        Get user information.  
          
        Args:  
            username: GitHub username  
              
        Returns:  
            User data or None if not found  
        """  
        return await self._make_request(f"users/{username}")
    
    async def get_authenticated_user_starred_repos(self, page: int = 1, per_page: int = 30) -> Optional[List[Dict[str, Any]]]:  
        """  
        Get authenticated user's starred repositories.  
            
        Args:  
            page: Page number (1-based)  
            per_page: Number of items per page  
                
        Returns:  
            List of starred repository data or None if not found  
        """  
        return await self._make_request(f"user/starred?page={page}&per_page={per_page}&sort=created&direction=desc")

    async def get_authenticated_user(self) -> Optional[Dict[str, Any]]:  
        """  
        Get information about the authenticated user (token owner).  
          
        Returns:  
            User data of the token owner or None if request failed  
        """  
        return await self._make_request("user")