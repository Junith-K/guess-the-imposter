# 🤖 Guess the Imposter - Discord Bot

A social deduction Discord bot game built in Python using `discord.py`. Players try to identify the imposter based on their answers to slightly different questions. Designed for 3+ players with robust multiplayer handling.

## 🎮 Game Overview

In this social deduction game, players receive questions via DM - but one player (the imposter) gets a slightly different question! After everyone answers, players must discuss and vote to find the imposter. Points are awarded for successfully catching or escaping as the imposter.

**Key Features:**
- 🎯 **Social Deduction**: Find the imposter through clever questioning and deduction
- 🤖 **Automated Game Management**: Handles player joining/leaving, scoring, and round progression  
- 💬 **Private Questions**: Questions sent via DM to prevent spoilers
- ⏰ **Flexible Timing**: Configurable discussion/voting timers or manual progression
- 🏆 **Scoring System**: Points for catching imposters or successfully deceiving
- 🛡️ **Robust Error Handling**: Gracefully handles disconnections and edge cases

## 🛠 Setup Instructions

### 1. Clone the Repo
```bash
git clone https://github.com/yourname/guess-the-imposter-bot.git
cd guess-the-imposter-bot
```

### 2. Create a Discord Bot Token
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Name your app (e.g., "Guess The Imposter")
4. In the left sidebar, click **"Bot" > "Add Bot"**
5. Under **Token**, click **"Copy"** — you'll paste this in `.env`
6. Enable these **Privileged Gateway Intents**:
   - **Server Members Intent** (required for member leave detection)
   - **Message Content Intent** (required for bot functionality)
7. Go to **OAuth2 > URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Read Messages`, `Use Slash Commands`, `Send Messages in Threads`, `Create Private Threads`, `View Channels`
   - Copy the generated link and open it to **invite the bot** to your server

### 3. Get Your Guild ID (for Development)
1. Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
2. Right-click your server name and select "Copy Server ID"
3. Use this as your `DEV_GUILD_ID` in the `.env` file

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```env
DISCORD_TOKEN=your_discord_bot_token_here
ENV=DEV
DEV_GUILD_ID=your_guild_id_here
```

**Environment Variables Explained:**
- `DISCORD_TOKEN`: Your bot's secret token from the Discord Developer Portal
- `ENV`: Set to `DEV` for development (commands sync to specific guild) or `PROD` for production (global commands)
- `DEV_GUILD_ID`: Your Discord server ID (only required for development mode)

### 5. Install Dependencies
```bash
pip install -r requirements.txt
```

**Dependencies included:**
- `discord.py` - Discord API wrapper
- `python-dotenv` - Environment variable loading
- `Flask` - Keep-alive HTTP server for hosting platforms

### 6. Run the Bot
```bash
python bot.py
```

The bot will automatically:
- Validate question pairs on startup
- Sync slash commands (dev: specific guild, prod: globally)
- Start a keep-alive HTTP server on port 8000
- Log connection status and command sync results

---

## 📘 Available Commands

| Command | Parameters | Description |
|---------|------------|-------------|
| `/ping` | - | Test if the bot is online |
| `/startgame` | `rounds` (1-20, default: 4)<br>`timer` (10-600s, default: 90)<br>`no_vote_timer` (boolean, default: false) | Start a new game session (host only) |
| `/join` | - | Join the lobby before the game starts |
| `/start` | - | Begin the game after players join (host only) |
| `/answer` | `text` (max 500 chars) | Submit your answer to the question |
| `/vote` | `user` (mention player) | Vote for who you think is the imposter |
| `/scoreboard` | - | Show current points during the game |
| `/endgame` | - | Force end the current game (host or players if host left) |
| `/endround` | `user` (optional mention) | Force end current round, optionally remove a player |

### 🔧 Command Details

**`/startgame` Parameters:**
- `rounds`: Number of rounds to play (1-20, default: 4)
- `timer`: Discussion/voting time in seconds (10-600, default: 90)  
- `no_vote_timer`: If true, rounds continue until all votes are cast (default: false)

**Host Controls:**
- Only the game host can use `/start`, `/endgame`, and `/endround`
- If the host leaves the server, any remaining player can force end the game
- Host can remove problematic players using `/endround @player`

**Player Requirements:**
- Must be able to receive DMs from the bot (checked when joining)
- Must remain in the Discord server throughout the game
- Minimum 3 players required to start/continue

---

## 📦 Project Structure

```
guess-the-imposter/
├── bot.py                   # Discord bot setup, slash commands, and event handlers
├── game_manager.py          # Core game logic, state management, and player handling  
├── questions_custom.py      # Question pairs database (normal + imposter variants)
├── requirements.txt         # Python dependencies (discord.py, flask, python-dotenv)
├── .env                     # Environment variables (add to .gitignore)
├── README.md               # Documentation (this file)
└── __pycache__/            # Python bytecode cache (auto-generated)
```

### 📁 File Descriptions

**`bot.py`** (250 lines)
- Discord bot initialization and configuration
- All slash command definitions and handlers  
- Member leave event handling
- Environment-based command syncing (dev/prod)
- Keep-alive HTTP server for hosting platforms

**`game_manager.py`** (440+ lines)
- `GameManager` class handling all game logic
- Player management (join, leave, validation)
- Round progression and state management
- Question distribution via DMs
- Voting system with timer/manual control
- Scoring and leaderboard functionality
- Comprehensive error handling and edge cases

**`questions_custom.py`** (300+ lines)
- 100+ carefully crafted question pairs
- Format: `{"normal": "question", "imposter": "similar_question"}`
- Questions designed to be subtly different but related
- Covers various topics: lifestyle, preferences, habits, etc.

---

## 👥 Player Requirements & Limitations

- **Minimum Players:** 3 players required to start and continue the game
- **Maximum Players:** No hard limit, but optimal experience with 4-8 players
- **DM Permissions:** Players must allow DMs from server members (validated when joining)
- **Server Membership:** Players must remain in the Discord server throughout the game
- **Answer Limits:** Answers must be 1-500 characters, cannot be empty
- **Voting Rules:** Cannot vote for yourself, one vote per player per round

## 🛡️ Error Handling & Edge Cases

The bot gracefully handles various scenarios:

### Player Management
- **Players Leaving:** Automatic removal from game when members leave the server
- **DM Failures:** Players unable to receive DMs are automatically removed
- **Host Departure:** If host leaves, remaining players can force end the game
- **Insufficient Players:** Game automatically ends if fewer than 3 players remain

### Game Integrity
- **Imposter Leaves:** Round ends immediately, imposter's question is revealed
- **Duplicate Votes:** Players cannot vote multiple times or vote for themselves
- **Server Validation:** Continuous validation that players remain in the server
- **Race Conditions:** Protected against simultaneous timer expiry and vote completion

### Technical Resilience
- **Question Validation:** All question pairs validated on startup
- **Memory Management:** Proper cleanup of game data when games end
- **Event Coordination:** Robust async event handling for vote synchronization
- **Graceful Degradation:** Game continues smoothly when players disconnect

---

## 📝 How the Game Works

### Game Flow
1. **🏁 Start a Game:** Host uses `/startgame` with optional parameters (rounds, timer, etc.)
2. **👥 Join Lobby:** Players use `/join` - bot validates DM permissions and server membership
3. **▶️ Begin:** Host uses `/start` when ready (minimum 3 players required)
4. **❓ Question Phase:** Each player receives a question via DM:
   - Regular players get the "normal" question
   - One random player (imposter) gets the "imposter" question (slightly different)
5. **✍️ Answer Phase:** Players submit answers using `/answer` in the server channel
6. **📋 Reveal Answers:** All answers are displayed with player names
7. **🧠 Reveal Question:** The normal question is revealed (imposter's question stays secret)
8. **💬 Discussion Phase:** Players discuss for the set timer duration (or until all votes cast if no timer)
9. **🗳️ Voting Phase:** Players vote for who they think is the imposter using `/vote @player`
10. **🏆 Results:** Points awarded, imposter revealed, scores updated
11. **🔄 Next Round:** Process repeats for the configured number of rounds
12. **👑 Final Scores:** Leaderboard displayed, winner announced

### Scoring System
- **🎯 Catch the Imposter:** +1 point for each player who correctly votes for the imposter
- **😈 Imposter Escapes:** +2 points for the imposter if they avoid being caught
- **🤝 Tie Votes:** Imposter wins by default and gets +2 points
- **🚫 No Votes:** Imposter gets +2 points

### Game Mechanics
- **Random Selection:** Imposter and questions are randomly chosen each round
- **Question Validation:** All question pairs are validated on bot startup
- **Real-time Updates:** Players can check `/scoreboard` anytime during the game
- **Flexible Timing:** Use timer-based voting or wait for all votes with `no_vote_timer=true`
- **Progress Tracking:** Clear round indicators and remaining time announcements

---

## ✅ Features & Technical Highlights

### 🎮 Game Features
- **📝 300+ Question Pairs:** Diverse, carefully crafted questions with subtle imposter variants
- **⏰ Flexible Timing:** Configurable discussion timers with countdown reminders or manual progression
- **🏆 Comprehensive Scoring:** Points for catching imposters, escaping detection, with tie-breaking rules
- **👑 Host Controls:** Game management, player removal, force ending capabilities
- **📊 Live Scoreboard:** Real-time score tracking accessible during gameplay
- **🔄 Multi-Round Support:** 1-20 configurable rounds with automatic progression

### 🛠️ Technical Features
- **🤖 Robust Async Design:** Proper asyncio usage with event coordination and race condition protection
- **🔒 Comprehensive Validation:** Input validation, permission checks, and server membership verification
- **🛡️ Error Resilience:** Graceful handling of player disconnections, DM failures, and edge cases
- **💾 Clean Memory Management:** Automatic cleanup with callback system preventing memory leaks
- **📱 Modern Discord Integration:** Slash commands, ephemeral responses, and proper interaction handling
- **🌐 Hosting Ready:** Built-in keep-alive server for platforms like Replit, Heroku, etc.

### 🔧 Developer Features
- **🐛 Development Mode:** Guild-specific command syncing for faster testing
- **📋 Comprehensive Logging:** Detailed startup and runtime logging for debugging
- **🧪 Question Validation:** Automatic validation of question format and content on startup
- **♻️ Modular Design:** Clean separation between bot commands and game logic
- **📚 Well-Documented:** Extensive inline documentation and error messages

---

## 🚀 Deployment Options

### Local Development
```bash
git clone <repository>
cd guess-the-imposter
pip install -r requirements.txt
# Configure .env file
python bot.py
```

### Cloud Hosting
The bot includes a Flask keep-alive server making it suitable for:
- **Replit:** Ready to deploy with automatic wake-up
- **Heroku:** Compatible with buildpacks and dyno management  
- **Railway:** Simple deployment with environment variables
- **DigitalOcean Apps:** Container-ready application
- **AWS/GCP:** Can be containerized or run on compute instances

### Environment Configuration
- Set `ENV=DEV` for development (faster command sync to specific guild)
- Set `ENV=PROD` for production (global command deployment)
- Ensure `DISCORD_TOKEN` is kept secure and never committed to version control

---

## 🤝 Contributing

Feel free to contribute by:
- Adding new question pairs to `questions_custom.py`
- Improving game mechanics or user experience
- Enhancing error handling or edge case coverage
- Optimizing performance or code organization
- Adding new features like custom game modes

---

## 📄 License

This project is open source. Feel free to use, modify, and distribute as needed.

---

**Happy deceiving! 🎭**

*Built with ❤️ using Python and discord.py*
