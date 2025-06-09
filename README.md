# GitHub Repository Preview Bot

🤖 A comprehensive Telegram bot for GitHub repository exploration, monitoring, and multi-destination notifications.

## Features

### 🔍 Repository Information

- Comprehensive repository details (stars, forks, open issues)
- Programming languages with percentages
- Latest release information with direct links
- Repository topics and description
- Interactive browsing with inline keyboards

### 👤 User Profiles

- Complete GitHub user profiles
- Follower/following statistics
- Public repository counts
- Developer activity insights

### 🚀 Interactive Navigation

- Browse repository tags and releases with pagination
- View project contributors
- Download release assets directly (up to 50MB)
- Paginated results navigation
- Compressed callback data for complex interactions

### 🔔 Advanced Tracking System

- Multi-destination notifications: Send alerts to DMs, channels, groups, or forum topics
- Flexible tracking options: Monitor releases, issues, or both
- Real-time monitoring: Automatic checks every 5 minutes
- Starred repository tracking: Get notified when you star new repos
- Encrypted token storage: Secure per-user GitHub token management

## Available Commands

### Basic Commands

```bash
/start    - Start using the bot with welcome message  
/help     - Show comprehensive usage guide  
/repo     - Get detailed repository information  
/user     - Get GitHub user profile information  
```

### Enhanced Tracking Commands

```bash
# Track to your DM  
/track owner/repo [releases,issues]  
  
# Track to channel/group  
/track owner/repo [releases] > chat_id  
  
# Track to forum topic  
/track owner/repo [issues] > chat_id/thread_id  
  
# Management commands  
/tracked  - View your tracked repositories  
/untrack  - Stop tracking a repository  
```

### Token Management

```bash
/settoken    - Connect your GitHub account for higher rate limits  
/removetoken - Remove stored token  
/trackme     - Track your starred repositories  
```

## Usage Examples

### Repository Information

```bash
/repo microsoft/vscode  
/repo https://github.com/torvalds/linux  
/user torvalds  
```

### Advanced Tracking

```bash
# Track releases to your DM  
/track microsoft/vscode [releases]  
  
# Track both releases and issues to a channel  
/track torvalds/linux [releases,issues] > -1001234567890  
  
# Track issues to a specific forum topic  
/track facebook/react [issues] > -1001234567890/123  
```

## Installation & Setup

### Requirements

- Python 3.9+ (tested with Python 3.9-3.13)
- Telegram Bot Token from @BotFather
- GitHub Personal Access Token (optional, for higher rate limits)

### Dependencies

```bash
# Core dependencies  
aiohttp>=3.8.0  
python-dotenv>=0.19.0  
cryptography>=3.4.0  
aiosqlite>=0.17.0  
  
# Telegram Bot API  
pyTelegramBotAPI>=4.0.0  
```

### Installation

```bash
git clone https://github.com/RHineIx/github-repo-bot  
cd github-repo-bot  
pip install -r requirements.txt  
```

### Configuration

Create a `.env` file in the project root:

```env
# Required  
BOT_TOKEN=your_telegram_bot_token  
  
# Optional (for higher rate limits and private repos)  
GITHUB_TOKEN=your_github_personal_access_token  
```

### Running

```bash
python main.py  
```

The bot will start with:

- Asynchronous polling for messages
- Background repository monitoring
- Encrypted token storage initialization

## Technical Architecture

### Core Components

- AsyncTeleBot: Main bot instance with asynchronous message handling  
- BotHandlers: Command processing and user interaction management  
- GitHubAPI: Asynchronous GitHub REST API client with per-user token support  
- RepoFormatter: Rich message formatting with HTML and inline keyboards  
- RepositoryMonitor: Background monitoring system for tracked repositories  
- RepositoryTracker: In-memory tracking database with multi-destination support  
- TokenManager: Encrypted SQLite storage for user GitHub tokens  
- MessageUtils: Safe message operations with error handling  

### Advanced Features

- Asynchronous Architecture: Full async/await implementation using AsyncTeleBot  
- Callback Data Compression: Custom hash-based system to handle Telegram's 64-byte limit  
- Multi-destination Notifications: Support for DMs, channels, groups, and forum topics  
- Encrypted Token Storage: Fernet encryption for secure GitHub token management  
- Rate Limiting Awareness: Intelligent handling of GitHub API rate limits  
- Error Recovery: Comprehensive error handling with retry mechanisms  
- Memory Management: Efficient in-memory storage with optional persistence  

## Monitoring System

- Real-time Tracking: Monitors repositories every 5 minutes  
- Multiple Track Types: Releases, issues, and starred repositories  
- Notification Delivery: Supports message_thread_id for forum topics  
- Legacy Compatibility: Handles both old and new data formats  
- Scalable Design: Per-repository isolation prevents cascade failures  

## API Integration

### GitHub API Support

- Repository Information: Full repository metadata and statistics  
- User Profiles: Complete user information and activity  
- Releases & Tags: Paginated browsing with download capabilities  
- Contributors: Repository contributor listings  
- Issues Tracking: Real-time issue monitoring  
- Starred Repositories: Authenticated user starred repo tracking  

### Rate Limiting

- Without Token: 60 requests per hour  
- With Token: 5,000 requests per hour  
- Per-user Tokens: Individual rate limits for authenticated users  

## Security Features

- Token Encryption: All GitHub tokens encrypted using Fernet symmetric encryption  
- Secure Storage: SQLite database with encrypted token fields  
- Permission Validation: Bot validates channel/topic permissions before tracking  
- Safe Downloads: File size limits and secure download handling  

## Contributing

This bot is built with the pyTelegramBotAPI library and follows modern Python async patterns. Contributions are welcome!

---

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/RHineIx/github-repo-bot)
