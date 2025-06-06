"""  
Response formatting utilities for GitHub data.  
"""  
import re  
from typing import Dict, Any, Optional, List  
from telebot import types  
from telebot.util import quick_markup  
  
  
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
  
⭐ Stars: <b>{stars}</b> | 🍴 Forks: <b>{forks}</b>  
🪲 Open Issues: <b>{issues}</b>  
  
🚀 <b>Latest Release:</b> {release_info}  
  
💻 <b>Lang's:</b> {languages_text}  
  
🔗 <a href='{html_url}'>View Repo</a>  
  
{topics_text}"""  
          
        return message.strip()  
      
    @staticmethod  
    def create_repo_main_keyboard(owner: str, repo: str) -> types.InlineKeyboardMarkup:  
        """  
        Create main repository keyboard with 4 action buttons.  
          
        Args:  
            owner: Repository owner  
            repo: Repository name  
              
        Returns:  
            InlineKeyboardMarkup with repository action buttons  
        """  
        return quick_markup({  
            '🏷️ Tags': {'callback_data': f'repo_tags:{owner}/{repo}:1'},  
            '🚀 Releases': {'callback_data': f'repo_releases:{owner}/{repo}:1'},  
            '👥 Contributors': {'callback_data': f'repo_contributors:{owner}/{repo}:1'},  
            '📁 Files': {'callback_data': f'repo_files:{owner}/{repo}'}  
        }, row_width=2)  
      
    @staticmethod  
    def format_tags_list(tags: List[Dict[str, Any]], owner: str, repo: str, page: int) -> str:  
        """  
        Format tags list message.  
          
        Args:  
            tags: List of tag data from GitHub API  
            owner: Repository owner  
            repo: Repository name  
            page: Current page number  
              
        Returns:  
            Formatted message string  
        """  
        if not tags:  
            return f"📦 <b>{owner}/{repo}</b>\n\n🏷️ <b>Tags</b>\n\nNo tags found."  
          
        message = f"📦 <b>{owner}/{repo}</b>\n\n🏷️ <b>Tags (Page {page})</b>\n\n"  
          
        for i, tag in enumerate(tags, 1):  
            tag_name = tag.get('name', 'Unknown')  
            commit_sha = tag.get('commit', {}).get('sha', '')[:7]  
            message += f"{i}. <code>{tag_name}</code> ({commit_sha})\n"  
          
        return message.strip()  
      
    @staticmethod  
    def format_releases_list(releases: List[Dict[str, Any]], owner: str, repo: str, page: int) -> str:  
        """  
        Format releases list message.  
          
        Args:  
            releases: List of release data from GitHub API  
            owner: Repository owner  
            repo: Repository name  
            page: Current page number  
              
        Returns:  
            Formatted message string  
        """  
        if not releases:  
            return f"📦 <b>{owner}/{repo}</b>\n\n🚀 <b>Releases</b>\n\nNo releases found."  
          
        message = f"📦 <b>{owner}/{repo}</b>\n\n🚀 <b>Releases (Page {page})</b>\n\n"  
          
        for i, release in enumerate(releases, 1):  
            tag_name = release.get('tag_name', 'Unknown')  
            name = release.get('name', tag_name)  
            published_at = release.get('published_at', '')  
            if published_at:  
                date = published_at.split('T')[0]  
                message += f"{i}. <b>{name}</b> (<code>{tag_name}</code>) - {date}\n"  
            else:  
                message += f"{i}. <b>{name}</b> (<code>{tag_name}</code>)\n"  
          
        return message.strip()  
      
    @staticmethod  
    def format_contributors_list(contributors: List[Dict[str, Any]], owner: str, repo: str, page: int) -> str:  
        """  
        Format contributors list message.  
          
        Args:  
            contributors: List of contributor data from GitHub API  
            owner: Repository owner  
            repo: Repository name  
            page: Current page number  
              
        Returns:  
            Formatted message string  
        """  
        if not contributors:  
            return f"📦 <b>{owner}/{repo}</b>\n\n👥 <b>Contributors</b>\n\nNo contributors found."  
          
        message = f"📦 <b>{owner}/{repo}</b>\n\n👥 <b>Contributors (Page {page})</b>\n\n"  
          
        for i, contributor in enumerate(contributors, 1):  
            login = contributor.get('login', 'Unknown')  
            contributions = contributor.get('contributions', 0)  
            html_url = contributor.get('html_url', '')  
            message += f"{i}. <a href='{html_url}'>@{login}</a> ({contributions} contributions)\n"  
          
        return message.strip()  
      
    @staticmethod  
    def create_navigation_keyboard(  
        owner: str,   
        repo: str,   
        current_page: int,   
        action_type: str,  
        has_next: bool = True  
    ) -> types.InlineKeyboardMarkup:  
        """  
        Create navigation keyboard for paginated content.  
          
        Args:  
            owner: Repository owner  
            repo: Repository name  
            current_page: Current page number  
            action_type: Type of action (tags, releases, contributors)  
            has_next: Whether there's a next page available  
              
        Returns:  
            InlineKeyboardMarkup with navigation buttons  
        """  
        buttons = {}  
          
        # Previous page button  
        if current_page > 1:  
            buttons['⬅️ Previous'] = {  
                'callback_data': f'repo_{action_type}:{owner}/{repo}:{current_page - 1}'  
            }  
          
        # Next page button  
        if has_next:  
            buttons['Next ➡️'] = {  
                'callback_data': f'repo_{action_type}:{owner}/{repo}:{current_page + 1}'  
            }  
          
        # Home button  
        buttons['🏠 Back to Repo'] = {  
            'callback_data': f'repo_home:{owner}/{repo}'  
        }  
          
        return quick_markup(buttons, row_width=2)  
      
    @staticmethod  
    def create_release_assets_keyboard(  
        assets: List[Dict[str, Any]],   
        owner: str,   
        repo: str,  
        release_id: int  
    ) -> types.InlineKeyboardMarkup:  
        """  
        Create keyboard for release assets download.  
          
        Args:  
            assets: List of release assets  
            owner: Repository owner  
            repo: Repository name  
            release_id: Release ID  
              
        Returns:  
            InlineKeyboardMarkup with download buttons  
        """  
        buttons = {}  
          
        for asset in assets:  
            asset_name = asset.get('name', 'Unknown')  
            asset_id = asset.get('id')  
            asset_size = asset.get('size', 0)  
              
            # Format size for display  
            size_mb = asset_size / (1024 * 1024)  
            size_text = f" ({size_mb:.1f}MB)" if size_mb >= 1 else f" ({asset_size}B)"  
              
            buttons[f"📥 {asset_name}{size_text}"] = {  
                'callback_data': f'download_asset:{asset_id}:{asset_size}'  
            }  
          
        # Back button  
        buttons['⬅️ Back to Releases'] = {  
            'callback_data': f'repo_releases:{owner}/{repo}:1'  
        }  
          
        return quick_markup(buttons, row_width=1)  
  
  
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
  
📊 <b>Statistics:</b>  
👥 Followers: <b>{followers}</b>  
👤 Following: <b>{following}</b>  
📁 Public Repositories: <b>{public_repos}</b>  
  
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
