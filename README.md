# 🤖 Guess the Imposter - Discord Bot

A social deduction Discord bot game built in Python using `discord.py`. Designed for 3+ players.

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
   - Server Members Intent
   - Message Content Intent
7. Go to **OAuth2 > URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Read Messages`, `Use Slash Commands`, `Manage Messages`, `View Channels`
   - Copy the generated link and open it to **invite the bot** to your server

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your values:
```env
DISCORD_TOKEN=your_discord_bot_token_here
ENV=DEV
DEV_GUILD_ID=your_guild_id_here
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the Bot
```bash
python bot.py
```

---

## 📘 Available Commands

| Command          | Description                                                     |
| ---------------- | --------------------------------------------------------------- |
| `/ping`          | Test if the bot is online                                       |
| `/startgame`     | Start a new game session (host only)                            |
| `/join`          | Join the lobby before the game starts                           |
| `/start`         | Host: Start the game after players join                         |
| `/answer`        | Submit your answer privately                                    |
| `/vote`          | Vote for the imposter                                           |
| `/scoreboard`    | Show current points                                             |
| `/endgame`       | Host: Force end the current game                                |
| `/endround`      | Host: Force end the round and optionally remove a player        |

---

## 📦 Project Structure

```
.
├── bot.py               # Discord bot setup and command handling
├── game_manager.py      # Main game logic and state management
├── questions_custom.py  # Custom question pairs for the game
├── .env                 # Secret token file (do not share)
├── .env.example         # Example environment variables
├── requirements.txt     # Dependencies
└── README.md            # This file
```

---

## 👥 Minimum Requirements

- At least 3 players to start a game
- Each round: 1 imposter, 1 fake question, players answer and vote

---

## 📝 How the Game Works

1. **Start a Game:** Use `/startgame` to create a lobby. Players join with `/join`.
2. **Begin:** Host uses `/start` to begin. Each player gets a question in DM—one player (the imposter) gets a slightly different question.
3. **Answer:** Players submit answers with `/answer`.
4. **Reveal:** Answers are shown (with player names), and the common question is revealed.
5. **Vote:** Players discuss and vote for the imposter using `/vote`.
6. **Scoring:** Points are awarded for catching or escaping as the imposter.
7. **Rounds:** The game continues for the chosen number of rounds. Use `/scoreboard` anytime to see scores.
8. **End:** The host can force end the game or round with `/endgame` or `/endround`.

---

## ✅ Features & Enhancements

- Custom question pairs in [`questions_custom.py`](questions_custom.py)
- Optional voting timer or manual vote end
- Host controls for ending rounds or removing players
- Scoreboard and final leaderboard

---

Happy deceiving! 🎭
