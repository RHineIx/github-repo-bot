"""  
Response formatting utilities for GitHub data.  
"""  
import re  
from typing import Dict, Any, Optional, List  
from telebot import types  
from telebot.util import quick_markup
from bot.utils import CallbackDataManager 

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
            languages_text = " ".join([f"#{lang}: (<code>{percent:.1f}%</code>)" for lang, percent in top_languages])  
          
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
      
    @staticmethod  
    def create_repo_main_keyboard(owner: str, repo: str) -> types.InlineKeyboardMarkup:  
        """  
        Create main repository keyboard with 2 action buttons using compressed callback data.  
        """  
        # Use CallbackDataManager for tags button  
        tags_callback = CallbackDataManager.create_short_callback(  
            'repo_tags',  
            {'owner': owner, 'repo': repo, 'page': 1}  
        )  
          
        # Use CallbackDataManager for contributors button  
        contributors_callback = CallbackDataManager.create_short_callback(  
            'repo_contributors',   
            {'owner': owner, 'repo': repo, 'page': 1}  
        )  
          
        return quick_markup({  
            '🏷️ Tags': {'callback_data': tags_callback},  
            '👥 Contributors': {'callback_data': contributors_callback}  
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
          
        message = f"📦 <b>{owner}/{repo}</b>\n\n🏷️ <b>Tags (Page {page})</b>\n\nClick on any tag to view its releases:\n\n"  
          
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
            callback_data = CallbackDataManager.create_short_callback(  
                'tag_releases',  
                {'owner': owner, 'repo': repo, 'tag_name': tag_name}  
            )  
            buttons[f"🏷️ {tag_name}"] = {'callback_data': callback_data}  
        
        # Navigation buttons  
        nav_buttons = {}  
        if page > 1:  
            prev_callback = CallbackDataManager.create_short_callback(  
                'repo_tags',  
                {'owner': owner, 'repo': repo, 'page': page - 1}  
            )  
            nav_buttons['⬅️ Previous'] = {'callback_data': prev_callback}  
        
        if len(tags) == 5:  
            next_callback = CallbackDataManager.create_short_callback(  
                'repo_tags',   
                {'owner': owner, 'repo': repo, 'page': page + 1}  
            )  
            nav_buttons['Next ➡️'] = {'callback_data': next_callback}  
        
        home_callback = CallbackDataManager.create_short_callback(  
            'repo_home',  
            {'owner': owner, 'repo': repo}  
        )  
        nav_buttons['🏠 Back to Repo'] = {'callback_data': home_callback}
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
    def format_tag_releases(tag_name: str, releases: List[Dict[str, Any]], owner: str, repo: str, page: int = 1) -> str:  
        """  
        Format releases for a specific tag with pagination support.  
          
        Args:  
            tag_name: Tag name  
            releases: List of release data (limited to page size)  
            owner: Repository owner  
            repo: Repository name  
            page: Current page number  
              
        Returns:  
            Formatted message string  
        """  
        if not releases:  
            return f"📦 <b>{owner}/{repo}</b>\n\n🏷️ <b>Tag: {tag_name}</b>\n\nNo releases found for this tag."  
          
        message = f"📦 <b>{owner}/{repo}</b>\n\n🏷️ <b>Tag: {tag_name} (Page {page})</b>\n\n🚀 <b>Available Releases:</b>\n\n"  
          
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
        tag_name: str,  
        page: int = 1  
    ) -> types.InlineKeyboardMarkup:  
        """Create keyboard for tag releases with pagination and download options."""  
        buttons = {}  
          
        # Add release buttons (limited to current page)  
        for release in releases:  
            release_name = release.get('name', release.get('tag_name', 'Unknown'))  
            release_id = release.get('id')  
            assets_count = len(release.get('assets', []))  
              
            if assets_count > 0:  
                callback_data = CallbackDataManager.create_short_callback(  
                    'rel_assets',  
                    {  
                        'owner': owner,  
                        'repo': repo,  
                        'release_id': release_id,  
                        'tag_name': tag_name  
                    }  
                )  
                buttons[f"📥 {release_name} ({assets_count} files)"] = {  
                    'callback_data': callback_data  
                }  
            else:  
                buttons[f"📄 {release_name} (No files)"] = {  
                    'callback_data': f'release_info:{owner}/{repo}:{release_id}'  
                }  
          
        # Add navigation buttons  
        nav_buttons = {}  
          
        # Previous page button  
        if page > 1:  
            prev_callback = CallbackDataManager.create_short_callback(  
                'tag_releases_page',  
                {'owner': owner, 'repo': repo, 'tag_name': tag_name, 'page': page - 1}  
            )  
            nav_buttons['⬅️ Previous'] = {'callback_data': prev_callback}  
          
        # Next page button (show if we have exactly 5 releases, indicating more might exist)  
        if len(releases) == 5:  # ITEMS_PER_PAGE  
            next_callback = CallbackDataManager.create_short_callback(  
                'tag_releases_page',  
                {'owner': owner, 'repo': repo, 'tag_name': tag_name, 'page': page + 1}  
            )  
            nav_buttons['Next ➡️'] = {'callback_data': next_callback}  
          
        # Back to tags button  
        back_callback = CallbackDataManager.create_short_callback(  
            'repo_tags',  
            {'owner': owner, 'repo': repo, 'page': 1}  
        )  
        nav_buttons['🏠 Back to Tags'] = {'callback_data': back_callback}  
          
        # Create markup with releases first, then navigation  
        markup = types.InlineKeyboardMarkup(row_width=1)  
          
        # Add release buttons  
        for text, data in buttons.items():  
            markup.add(types.InlineKeyboardButton(text=text, **data))  
          
        # Add navigation buttons in a row  
        if nav_buttons:  
            nav_btns = [types.InlineKeyboardButton(text=text, **data) for text, data in nav_buttons.items()]  
            markup.row(*nav_btns)  
          
        return markup
    
    @staticmethod    
    def create_release_assets_keyboard(    
        assets: List[Dict[str, Any]],     
        owner: str,     
        repo: str,    
        release_id: int,    
        tag_name: str    
    ) -> types.InlineKeyboardMarkup:    
        """Create keyboard for release assets with compressed callback data."""    
        buttons = {}    
           
        for asset in assets:    
            asset_name = asset.get('name', 'Unknown')    
            asset_url = asset.get('browser_download_url')    
            asset_size = asset.get('size', 0)    
              
            # Format size for display    
            size_mb = asset_size / (1024 * 1024)    
            size_text = f" ({size_mb:.1f}MB)" if size_mb >= 1 else f" ({asset_size}B)"    
              
            # Check size limit    
            max_size_mb = 50    
            if asset_size <= max_size_mb * 1024 * 1024:    
                callback_data = CallbackDataManager.create_short_callback(    
                    'dl_direct',    
                    {    
                        'url': asset_url,    
                        'size': asset_size,    
                        'name': asset_name,    
                        'owner': owner,    
                        'repo': repo    
                    }    
                )  
                buttons[f"📥 {asset_name}{size_text}"] = {'callback_data': callback_data}  
      
        back_callback = CallbackDataManager.create_short_callback(  
            'tag_releases',  
            {'owner': owner, 'repo': repo, 'tag_name': tag_name}  
        )  
        buttons['⬅️ Back'] = {'callback_data': back_callback}  
      
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
    def create_navigation_keyboard(owner: str, repo: str, current_page: int, action_type: str, has_next: bool = True) -> types.InlineKeyboardMarkup:  
        buttons = {}  
          
        if current_page > 1:  
            prev_callback = CallbackDataManager.create_short_callback(  
                f'repo_{action_type}',  
                {'owner': owner, 'repo': repo, 'page': current_page - 1}  
            )  
            buttons['⬅️ Previous'] = {'callback_data': prev_callback}  
          
        if has_next:  
            next_callback = CallbackDataManager.create_short_callback(  
                f'repo_{action_type}',  
                {'owner': owner, 'repo': repo, 'page': current_page + 1}  
            )  
            buttons['Next ➡️'] = {'callback_data': next_callback}  
          
        home_callback = CallbackDataManager.create_short_callback(  
            'repo_home',  
            {'owner': owner, 'repo': repo}  
        )  
        buttons['🏠 Back to Repo'] = {'callback_data': home_callback}  
          
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