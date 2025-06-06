"""  
Response formatting utilities for GitHub data.  
"""  
import re  
from typing import Dict, Any, Optional, List  
  
  
class RepoFormatter:  
    """Formats repository data for Telegram messages."""  
      
    @staticmethod  
    def format_number(num: int) -> str:  
        """  
        Format large numbers with K/M suffixes.  
          
        Args:  
            num: Number to format  
              
        Returns:  
            Formatted number string  
        """  
        if num >= 1000000:  
            return f"{num/1000000:.1f}M"  
        elif num >= 1000:  
            return f"{num/1000:.1f}K"  
        return str(num)  
      
    @staticmethod  
    def calculate_language_percentages(languages: Dict[str, int]) -> Dict[str, float]:  
        """  
        Calculate percentage distribution of programming languages.  
          
        Args:  
            languages: Dictionary of language names to byte counts  
              
        Returns:  
            Dictionary of language names to percentages  
        """  
        total = sum(languages.values())  
        if total == 0:  
            return {}  
        return {lang: (bytes_count / total) * 100 for lang, bytes_count in languages.items()}  
      
    @staticmethod  
    def format_repository_preview(  
        repo_data: Dict[str, Any],   
        languages: Optional[Dict[str, int]],   
        latest_release: Optional[Dict[str, Any]]  
    ) -> str:  
        """  
        Format complete repository preview message.  
        
        Args:  
            repo_data: Repository information from GitHub API  
            languages: Programming languages data  
            latest_release: Latest release information  
            
        Returns:  
            Formatted HTML message string  
        """  
        # Basic information  
        name = repo_data.get('name', 'Unknown')  
        full_name = repo_data.get('full_name', 'Unknown')  
        description = repo_data.get('description', 'No description available')  
        stars = RepoFormatter.format_number(repo_data.get('stargazers_count', 0))  
        forks = RepoFormatter.format_number(repo_data.get('forks_count', 0))  
        issues = repo_data.get('open_issues_count', 0)  
        html_url = repo_data.get('html_url', '')  
        topics = repo_data.get('topics', [])  
        
        # Latest release with URL  
        release_info = "No releases"  
        if latest_release:  
            release_name = latest_release.get('tag_name', 'Unknown')  
            release_url = latest_release.get('html_url', html_url)  
            release_info = f"<a href='{release_url}'>{release_name}</a>"  
        
        # Programming languages - only top 3  
        languages_text = "Not specified"  
        if languages:  
            lang_percentages = RepoFormatter.calculate_language_percentages(languages)  
            # Get top 3 languages only  
            top_languages = sorted(lang_percentages.items(), key=lambda x: x[1], reverse=True)[:3]  
            languages_text = " ".join([f"#{lang}: {percent:.1f}%" for lang, percent in top_languages])  
        
        # Top 3 topics  
        topics_text = ""  
        if topics:  
            top_topics = topics[:3]  
            topics_text = " ".join([f"#{topic}" for topic in top_topics])  
        
        # Format message with new layout  
        message = f"""📦 <a href='{html_url}'>{full_name}</a>  
    
📝 <b>Description:</b>  
{description} 

<blockquote>⭐ Stars: <b>{stars} </b> | 🍴 Forks: <b>{forks} </b> | 🪲 Open Issues: <b>{issues}</b></blockquote>  

🚀 <b>Latest Release:</b> {release_info}  
💻 <b>Lang's:</b> {languages_text}  

🔗 <a href='{html_url}'>View Repo</a>  

{topics_text}"""
        
        return message.strip()
  
  
class UserFormatter:  
    """Formats user data for Telegram messages."""  
      
    @staticmethod  
    def format_user_info(user_data: Dict[str, Any]) -> str:  
        """  
        Format user information message.  
          
        Args:  
            user_data: User information from GitHub API  
              
        Returns:  
            Formatted HTML message string  
        """  
        name = user_data.get('name', 'Not specified')  
        login = user_data.get('login', 'Unknown')  
        bio = user_data.get('bio', 'No bio available')  
        followers = RepoFormatter.format_number(user_data.get('followers', 0))  
        following = RepoFormatter.format_number(user_data.get('following', 0))  
        public_repos = user_data.get('public_repos', 0)  
        html_url = user_data.get('html_url', '')  
          
        message = f"""  
👤 <b>{name}</b>  
🔗 <code>@{login}</code>  
  
📝 <b>Bio:</b>  
{bio}

👥 Followers: <b>{followers}</b>  
👤 Following: <b>{following}</b>  
📦 Public Repositories: <b>{public_repos}</b>  
  
🔗 <b>Profile:</b>  
<a href="{html_url}">{html_url}</a>  
"""  
        return message.strip()  
  
  
class URLParser:  
    """Utility class for parsing GitHub URLs and repository names."""  
      
    @staticmethod  
    def parse_repo_input(text: str) -> Optional[tuple]:  
        """  
        Parse GitHub repository URL or owner/repo format.  
          
        Args:  
            text: Input text containing repository reference  
              
        Returns:  
            Tuple of (owner, repo) or None if parsing failed  
        """  
        # GitHub URL patterns  
        patterns = [  
            r'github\.com/([^/]+)/([^/\s]+)',  # Full GitHub URL  
            r'^([^/\s]+)/([^/\s]+)$'          # owner/repo format  
        ]  
          
        for pattern in patterns:  
            match = re.search(pattern, text.strip())  
            if match:  
                owner, repo = match.groups()  
                # Remove .git suffix if present  
                repo = repo.replace('.git', '')  
                return owner, repo  
        return None