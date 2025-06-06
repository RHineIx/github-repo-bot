### Configuration
Required Environment Variables\
BOT_TOKEN: Your Telegram bot token from @BotFather
### Optional Environment Variables
GITHUB_TOKEN: GitHub Personal Access Token for higher rate limits\
Without token: 60 requests/hour\
With token: 5000 requests/hour

### Available Commands
> /start - Welcome message and bot introduction
> /repo <repository> - Get repository preview
> /user <username> - Get GitHub user information
> /help - Show help message
#### Examples
> /repo https://github.com/microsoft/vscode  
> /repo microsoft/vscode  
> /user torvalds  
---
# Development
### Requirements
Python 3.9+
pyTelegramBotAPI 4.27.0+
aiohttp for async HTTP requests
