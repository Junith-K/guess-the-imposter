import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from game_manager import GameManager

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
ENV = os.getenv("ENV", "DEV")
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")
# Optional: set your development guild ID
DEV_GUILD = discord.Object(id=DEV_GUILD_ID)

games = {}  # guild_id: GameManager

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

# Slash Commands
@tree.command(name="ping", description="Test command")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

@tree.command(name="startgame", description="Start a new game session")
@app_commands.describe(
    rounds="How many rounds to play (default: 4)",
    timer="Timer for discussion/voting in seconds (default: 90)",
    anonymous="Post answers anonymously? (default: false)",
    no_vote_timer="No timer for voting? (default: false)"
)
async def startgame(interaction: discord.Interaction, rounds: int = 4, timer: int = 90, anonymous: bool = False, no_vote_timer: bool = False):
    guild_id = interaction.guild_id
    if guild_id in games and games[guild_id].active:
        await interaction.response.send_message("A game is already active in this server.", ephemeral=True)
        return

    game = GameManager(guild=interaction.guild, host=interaction.user, rounds=rounds, timer=timer, anonymous=anonymous, no_vote_timer=no_vote_timer)
    games[guild_id] = game
    await game.start_lobby(interaction)

@tree.command(name="join", description="Join the game session")
async def join(interaction: discord.Interaction):
    game = games.get(interaction.guild_id)
    if not game:
        await interaction.response.send_message("No game has been started. Use /startgame first.", ephemeral=True)
        return
    await game.add_player(interaction)

@tree.command(name="start", description="Start the actual game after players join")
async def start(interaction: discord.Interaction):
    game = games.get(interaction.guild_id)
    if not game:
        await interaction.response.send_message("No game session found.", ephemeral=True)
        return
    await game.begin_game(interaction)

@tree.command(name="answer", description="Submit your answer")
@app_commands.describe(text="Your answer to the question")
async def answer(interaction: discord.Interaction, text: str):
    game = games.get(interaction.guild_id)
    if not game:
        await interaction.response.send_message("No game in progress.", ephemeral=True)
        return
    await game.submit_answer(interaction, text)

@tree.command(name="vote", description="Vote who you think is the imposter")
@app_commands.describe(user="Mention the player you vote for")
async def vote(interaction: discord.Interaction, user: discord.Member):
    game = games.get(interaction.guild_id)
    if not game:
        await interaction.response.send_message("No game in progress.", ephemeral=True)
        return
    await game.submit_vote(interaction, user)

@tree.command(name="scoreboard", description="Show the current leaderboard")
async def scoreboard(interaction: discord.Interaction):
    game = games.get(interaction.guild_id)
    if not game:
        await interaction.response.send_message("No game in progress.", ephemeral=True)
        return
    await game.show_scoreboard(interaction)

@tree.command(name="endgame", description="Force end the current game")
async def endgame(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    game = games.get(guild_id)
    if not game:
        await interaction.response.send_message("No game is currently running.", ephemeral=True)
        return
    if interaction.user != game.host:
        await interaction.response.send_message("Only the host can end the game.", ephemeral=True)
        return

    await game.force_end()
    del games[guild_id]
    await interaction.response.send_message("The game has been forcefully ended.")

@tree.command(name="endround", description="Force end the current round and optionally remove a player")
@app_commands.describe(user="Mention a player to remove from the game (optional)")
async def endround(interaction: discord.Interaction, user: discord.Member = None):
    game = games.get(interaction.guild_id)
    if not game:
        await interaction.response.send_message("No game in progress.", ephemeral=True)
        return
    if interaction.user != game.host:
        await interaction.response.send_message("Only the host can end the round.", ephemeral=True)
        return
    if user:
        # Remove the user from the game if present
        game.players = [p for p in game.players if p.id != user.id]
        await interaction.response.send_message(f"{user.mention} has been removed from the game.")
        if len(game.players) < 3:
            await game.force_end()
            del games[interaction.guild_id]
            await interaction.followup.send("Not enough players to continue. The game has ended.")
            return
    # End the round and proceed to the next if possible
    game.voting_open = False
    if game.votes_done_event:
        game.votes_done_event.set()
    await interaction.response.send_message("The round has been forcefully ended. Proceeding to results.")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    if ENV == "DEV":
        synced = await tree.sync(guild=DEV_GUILD)
        print(f"[DEV] Synced {len(synced)} commands to guild {DEV_GUILD_ID}")
    else:
        synced = await tree.sync()
        print(f"[PROD] Synced {len(synced)} global commands")

if __name__ == "__main__":
    bot.run(TOKEN)
