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
        Create main repository keyboard with 2 action buttons.  
          
        Args:  
            owner: Repository owner  
            repo: Repository name  
              
        Returns:  
            InlineKeyboardMarkup with repository action buttons  
        """  
        return quick_markup({  
            '🏷️ Tags': {'callback_data': f'repo_tags:{owner}/{repo}:1'},  
            '👥 Contributors': {'callback_data': f'repo_contributors:{owner}/{repo}:1'}  
        }, row_width=2)  
      
    @staticmethod  
    def format_tags_list(tags: List[Dict[str, Any]], owner: str, repo: str, page: int) -> str:  
        """  
        Format tags list message with clickable tags.  
          
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
          
        message = f"📦 <b>{owner}/{repo}</b>\n\n🏷️ <b>Tags (Page {page})</b>\n\nClick on any tag to view its releases:\n"  
        
        return message.strip()  
      
    @staticmethod  
    def create_tags_keyboard(tags: List[Dict[str, Any]], owner: str, repo: str, page: int) -> types.InlineKeyboardMarkup:  
        """  
        Create keyboard for tags with clickable tag buttons.  
          
        Args:  
            tags: List of tag data  
            owner: Repository owner  
            repo: Repository name  
            page: Current page  
              
        Returns:  
            InlineKeyboardMarkup with tag buttons  
        """  
        buttons = {}  
          
        # Add clickable tag buttons  
        for tag in tags:  
            tag_name = tag.get('name', 'Unknown')  
            buttons[f"🏷️ {tag_name}"] = {  
                'callback_data': f'tag_releases:{owner}/{repo}:{tag_name}'  
            }  
          
        # Add navigation buttons  
        nav_buttons = {}  
        if page > 1:  
            nav_buttons['⬅️ Previous'] = {  
                'callback_data': f'repo_tags:{owner}/{repo}:{page - 1}'  
            }  
          
        if len(tags) == 5:  # Assuming ITEMS_PER_PAGE = 5  
            nav_buttons['Next ➡️'] = {  
                'callback_data': f'repo_tags:{owner}/{repo}:{page + 1}'  
            }  
          
        nav_buttons['🏠 Back to Repo'] = {  
            'callback_data': f'repo_home:{owner}/{repo}'  
        }  
          
        # Create markup with tags first, then navigation  
        markup = types.InlineKeyboardMarkup(row_width=1)  
          
        # Add tag buttons (one per row)  
        for text, data in buttons.items():  
            markup.add(types.InlineKeyboardButton(text=text, **data))  
          
        # Add navigation buttons (in a row)  
        nav_btns = [types.InlineKeyboardButton(text=text, **data) for text, data in nav_buttons.items()]  
        markup.row(*nav_btns)  
          
        return markup  
      
    @staticmethod  
    def format_tag_releases(tag_name: str, releases: List[Dict[str, Any]], owner: str, repo: str) -> str:  
        """  
        Format releases for a specific tag.  
          
        Args:  
            tag_name: Tag name  
            releases: List of release data  
            owner: Repository owner  
            repo: Repository name  
              
        Returns:  
            Formatted message string  
        """  
        if not releases:  
            return f"📦 <b>{owner}/{repo}</b>\n\n🏷️ <b>Tag: {tag_name}</b>\n\nNo releases found for this tag."  
          
        message = f"📦 <b>{owner}/{repo}</b>\n\n🏷️ <b>Tag: {tag_name}</b>\n\n🚀 <b>Available Releases:</b>\n\n"  
          
        for i, release in enumerate(releases, 1):  
            release_name = release.get('name', tag_name)  
            published_at = release.get('published_at', '')  
            assets_count = len(release.get('assets', []))  
              
            if published_at:  
                date = published_at.split('T')[0]  
                message += f"{i}. <b>{release_name}</b> - {date} ({assets_count} files)\n"  
            else:  
                message += f"{i}. <b>{release_name}</b> ({assets_count} files)\n"  
          
        return message.strip()  
      
    @staticmethod  
    def create_tag_releases_keyboard(  
        releases: List[Dict[str, Any]],   
        owner: str,   
        repo: str,   
        tag_name: str  
    ) -> types.InlineKeyboardMarkup:  
        """  
        Create keyboard for tag releases with download options.  
          
        Args:  
            releases: List of release data  
            owner: Repository owner  
            repo: Repository name  
            tag_name: Tag name  
              
        Returns:  
            InlineKeyboardMarkup with release buttons  
        """  
        buttons = {}  
          
        # Add release buttons  
        for release in releases:  
            release_name = release.get('name', release.get('tag_name', 'Unknown'))  
            release_id = release.get('id')  
            assets_count = len(release.get('assets', []))  
              
            if assets_count > 0:  
                buttons[f"📥 {release_name} ({assets_count} files)"] = {  
                    'callback_data': f'release_assets:{owner}/{repo}:{release_id}'  
                }  
            else:  
                buttons[f"📄 {release_name} (No files)"] = {  
                    'callback_data': f'release_info:{owner}/{repo}:{release_id}'  
                }  
          
        # Add back button  
        buttons['⬅️ Back to Tags'] = {  
            'callback_data': f'repo_tags:{owner}/{repo}:1'  
        }  
          
        return quick_markup(buttons, row_width=1)  
      
    @staticmethod  
    def format_release_assets(  
        release: Dict[str, Any],   
        assets: List[Dict[str, Any]],   
        owner: str,   
        repo: str  
    ) -> str:  
        """  
        Format release assets for download.  
          
        Args:  
            release: Release data  
            assets: List of asset data  
            owner: Repository owner  
            repo: Repository name  
              
        Returns:  
            Formatted message string  
        """  
        release_name = release.get('name', release.get('tag_name', 'Unknown'))  
          
        if not assets:  
            return f"📦 <b>{owner}/{repo}</b>\n\n🚀 <b>Release: {release_name}</b>\n\nNo downloadable files found."  
          
        message = f"📦 <b>{owner}/{repo}</b>\n\n🚀 <b>Release: {release_name}</b>\n\n📥 <b>Available Downloads:</b>\n\n"  
          
        for i, asset in enumerate(assets, 1):  
            asset_name = asset.get('name', 'Unknown')  
            asset_size = asset.get('size', 0)  
            download_count = asset.get('download_count', 0)  
              
            # Format size  
            size_mb = asset_size / (1024 * 1024)  
            if size_mb >= 1:  
                size_text = f"{size_mb:.1f}MB"  
            else:  
                size_text = f"{asset_size}B"  
              
            message += f"{i}. <b>{asset_name}</b>\n"  
            message += f"   Size: {size_text} | Downloads: {download_count}\n\n"  
          
        return message.strip()  
      
    @staticmethod  
    def create_release_assets_keyboard(  
        assets: List[Dict[str, Any]],   
        owner: str,   
        repo: str,  
        release_id: int,  
        tag_name: str  
    ) -> types.InlineKeyboardMarkup:  
        """  
        Create keyboard for release assets download.  
          
        Args:  
            assets: List of release assets  
            owner: Repository owner  
            repo: Repository name  
            release_id: Release ID  
            tag_name: Tag name for back navigation  
              
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
            if size_mb >= 1:  
                size_text = f" ({size_mb:.1f}MB)"  
            else:  
                size_text = f" ({asset_size}B)"  
              
            # Check if file is within download limit  
            max_size_mb = 50  # This should come from config  
            if asset_size <= max_size_mb * 1024 * 1024:  
                buttons[f"📥 {asset_name}{size_text}"] = {  
                    'callback_data': f'download_asset:{asset_id}:{asset_size}:{owner}/{repo}'  
                }  
            else:  
                buttons[f"❌ {asset_name}{size_text} (Too large)"] = {  
                    'callback_data': f'file_too_large:{asset_id}'  
                }  
          
        # Back button  
        buttons['⬅️ Back to Releases'] = {  
            'callback_data': f'tag_releases:{owner}/{repo}:{tag_name}'  
        }  
          
        return quick_markup(buttons, row_width=1)  
      
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
            action_type: Type of action (tags, contributors)  
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