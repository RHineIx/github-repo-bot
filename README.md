# GitHub Repository Preview Bot

🤖 A Telegram bot for interactive GitHub repository and user information display.

---

## Features

### 🔍 Repository Information

- Comprehensive repository details (stars, forks, open issues)
- Programming languages with percentages
- Latest release information with direct links
- Repository topics and description

### 👤 User Profiles

- Complete GitHub user profiles
- Follower/following statistics
- Public repository counts

### 🚀 Interactive Navigation

- Browse repository tags and releases
- View project contributors
- Download release assets directly
- Paginated results navigation

---

## Available Commands

```bash
/start    - Start using the bot  
/help     - Show usage guide  
/repo     - Get repository information  
/user     - Get GitHub user information  
```

---

## Usage Examples

```bash
/repo microsoft/vscode  
/repo https://github.com/torvalds/linux  
/user torvalds  
```

---

## Installation & Setup

### Requirements

- Python 3.8+
- Telegram Bot Token
- GitHub Personal Access Token (optional)

### Installation

```bash
git clone https://github.com/RHineIx/github-repo-bot  
cd github-repo-bot  
pip install -r requirements.txt  
```

### Configuration

Create a `.env` file and add:

```env
BOT_TOKEN=your_telegram_bot_token  
GITHUB_TOKEN=your_github_token  # optional  
```

### Running

```bash
python main.py
```

---

## Technical Architecture

### Core Components

- `BotHandlers`: Command processing and user interactions  
- `GitHubAPI`: GitHub REST API communication  
- `RepoFormatter`: Data formatting and presentation  
- `MessageUtils`: Safe message operations  

### Technical Features

- Asynchronous request processing  
- Callback data compression for navigation  
- Comprehensive error handling  
- Safe download size limits
