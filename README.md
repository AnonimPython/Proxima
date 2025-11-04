# Proxima Telegram Bot 🤖

A powerful Telegram bot built for Standoff 2 gaming community management, match organization, and player statistics tracking.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Aiogram](https://img.shields.io/badge/Aiogram-3.x-green.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🌟 Features

### 🎮 Gaming Features

- **Match Organization** - Create and manage gaming matches
- **Player Statistics** - Track player performance and rankings
- **Auto-matchmaking** - Find opponents based on skill level

### ⚡ Bot Capabilities

- **Multi-language Support** - Built-in localization system (ENG and RU)
- **Admin Panel** - Comprehensive moderation/admin tools
- **Real-time Notifications** - Instant match updates
- **Inline Keyboards** - Interactive user interface
- **Database Integration** - Persistent data storage

### 🛡️ Moderation

- **User Management** - Ban/unban system
- **Access Control** - Role-based permissions (User/Moderator/Admin)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Telegram Bot Token ([Get from @BotFather](https://t.me/BotFather))
- Docker (optional)

### Installation

#### Method 1: Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/AnonimPython/Proxima.git
cd Proxima

# Build the Docker image
docker build -t faceit-bot .

# Run the container
docker run proxima 
```

## ⚙️ Configuration

Open a `.env` file in the root directory:

**env**

```python
TELEGRAM_TOKEN="YOUR_TOKEN"
ADMIN_TELEGRAM_ID="YOUR_TELEGRAM_IT (need to take admin/moderator commands)"
```

## 🏗️ Project Structure

**text**

```
Proxima/
├── app/
│   ├── handlers/          # Telegram message handlers
│   │   ├── start.py       # Start command and main menu
│   │   ├── matches.py     # Match management
│   │   ├── clans.py       # Clan system (not work)
│   │   └── personal/      # Admin/moderation commands
│   ├── database/          # Database models and operations
│   │   ├── models.py      # Stucture of database (SQLite3)
│   ├── localization/      # Multi-language support (RU-ENG)
│   │   ├── en.json        # English localization of text
│   │   ├── ru.json        # Russian localization of text
│   ├── utils/             # Utility functions
│   ├── config.py          # Bot configuration
│   └── main.py            # Application entry point
├── middlewares/           # Middlewares functions
├── services/              # Services files
├── static/                # Static files (images, etc.)
├── utils/                 # Static files (images, etc.)
│   └── access_checker.py  # Acces chcker for admin/moderator commands
├── photo_matches/         # Match-related photos
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker configuration
├── README-RU.md           # Русская документация
└── README.md              # Documentation
```

## ✏️ Editing

If you need to rename project open ``config.py``

## 🐳 Docker Deployment

### Build and Run

**bash|zsh**

```bash
docker build -t proxima .
docker run -d --name proxima --env-file .env faceit-bot

--OR SIMPLE COMMANDS--

docker build -t proxima .
docker run proxima 
```

## 🎯 Usage

### Basic Commands

* `/start` - Initialize the bot and show main menu
* `/matches` - Browse and join available matches
* `/profile` - View your player statistics
* ~~``/clans``- Clan management system~~
* `/lobby` - Open lobby list
* `/match_register` - Register match after game
* `/help` - See all commands
* `/support` - Contact's of admin/owner/support
* `/stats` - View all stats of player
* `/top` - List of best playters on project
* `/history` - Check history matches
* `/project` - All info about project
* `/register` - Register a user profile

### Admin Commands

* `/make_me_admin` - Make you admin (ONLY FOR TEST)
* `/permaban` - Ban player forever
* `/admin_ban` - Tempary ban admin
* `/unban` - Unban user
* `/banlist` - Check list of banned users
* `/banhistory` - Show user ban history (10 )

### Admin Commands

* `/make_moderator` - Make you moderator (ONLY FOR TEST)
* `/mod_ban` - Temporary ban (max 7 days)
* `/mod_warn` - Send user warning message using bot
* `/mod_unban` - Unban user

## 🚀 Next Steps (Roadmap)

Future plans for improving the bot:

- [ ] **Clan System** 🏆
- [ ] **Make more Leagues** ⚔️
- [ ] **Star Payments** ⭐
- [ ] **Crypto Payments** **₿**
- [ ] **Phone Verification** **📱**

Future technology plans:

- [ ] **AI Helper 🧠**
- [ ] **Connect Postgress 📊**
- [ ] **MondgoDB for logging actives** 📝
- [ ] **Realize ClickHouse 🏠**


*If you want to suggest ideas, create an ***issue** in the repository!*

## 🤝 Contributing

Me welcome contributions! Please feel free to submit pull requests, report bugs, or suggest new features.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### 🤝 Support Author

TON - ``UQDXiwz__JqdI7UwuImKOMBE62gP8JkJkI1YLGIss94gVpaa``

USDT (TRC20) - ``TC4Qi3UKrb6YFkeimHC5wCDBB37ZMH5TYi``

BTC - ``bc1q26zdaa9uzudperm2m7e3qr04l5rackm6cee7xk``

## 📝 Русская документация

```
[Русская документация](app/README-RU.md "README-RU.md")
```

## 📄 License

This project is licensed under the MIT License - see the [MIT](https://license/) file for details.

<div align="center">**Made with ❤️ for the gaming community**

</div>
