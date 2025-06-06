"""  
GitHub API client for fetching repository and user information.  
"""  
import aiohttp  
import asyncio  
from typing import Optional, Dict, Any  
from config import config  
  
  
class GitHubAPI:  
    """Asynchronous GitHub API client."""  
      
    def __init__(self, token: Optional[str] = None):  
        """  
        Initialize GitHub API client.  
          
        Args:  
            token: GitHub personal access token (optional)  
        """  
        self.token = token or config.GITHUB_TOKEN  
        self.base_url = config.GITHUB_API_BASE  
        self.headers = {  
            'Accept': 'application/vnd.github.v3+json',  
            'User-Agent': 'GitHub-Repo-Preview-Bot/1.0'  
        }  
        if self.token:  
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
      
    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:  
        """  
        Get user information.  
          
        Args:  
            username: GitHub username  
              
        Returns:  
            User data or None if not found  
        """  
        return await self._make_request(f"users/{username}")