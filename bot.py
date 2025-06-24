import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from game_manager import GameManager
from flask import Flask
from threading import Thread

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
ENV = os.getenv("ENV", "DEV")
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")
DEV_GUILD = discord.Object(id=int(DEV_GUILD_ID))

# Keep-alive HTTP endpoint
app = Flask('')
@app.route('/')
def home():
    return "Bot is running."

def run():
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

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
    no_vote_timer="No timer for voting? (default: false)"
)
async def startgame(interaction: discord.Interaction, rounds: int = 4, timer: int = 90, no_vote_timer: bool = False):
    guild_id = interaction.guild_id
    
    # Validate parameters
    if rounds < 1 or rounds > 20:
        await interaction.response.send_message("Rounds must be between 1 and 20.", ephemeral=True)
        return
    if timer < 10 or timer > 600:
        await interaction.response.send_message("Timer must be between 10 and 600 seconds.", ephemeral=True)
        return
    
    # Check if game already exists
    if guild_id in games and games[guild_id].active:
        await interaction.response.send_message("A game is already active in this server.", ephemeral=True)
        return
    
    # Check bot permissions
    if not interaction.channel.permissions_for(interaction.guild.me).send_messages:
        await interaction.response.send_message("I don't have permission to send messages in this channel.", ephemeral=True)
        return
    
    # Check if host can receive DMs
    try:
        await interaction.user.send("Game creation test - you can safely ignore this message.")
    except Exception:
        await interaction.response.send_message("I can't DM you. Please enable DMs from server members to host a game.", ephemeral=True)
        return

    game = GameManager(guild=interaction.guild, host=interaction.user, rounds=rounds, timer=timer, anonymous=None, no_vote_timer=no_vote_timer)
    games[guild_id] = game
    
    # Set up cleanup callback
    async def cleanup_callback():
        if guild_id in games:
            del games[guild_id]
    game._cleanup_callback = cleanup_callback
    
    await game.start_lobby(interaction)

@tree.command(name="join", description="Join the game session")
async def join(interaction: discord.Interaction):
    game = games.get(interaction.guild_id)
    if not game:
        await interaction.response.send_message("No game has been started. Use /startgame first.", ephemeral=True)
        return
    if not game.active:
        await interaction.response.send_message("This game has ended. Start a new game with /startgame.", ephemeral=True)
        return
    await game.add_player(interaction)

@tree.command(name="start", description="Start the actual game after players join")
async def start(interaction: discord.Interaction):
    game = games.get(interaction.guild_id)
    if not game:
        await interaction.response.send_message("No game session found.", ephemeral=True)
        return
    if not game.active:
        await interaction.response.send_message("This game has ended. Start a new game with /startgame.", ephemeral=True)
        return
    if game.current_round > 0:
        await interaction.response.send_message("The game has already started.", ephemeral=True)
        return
    await game.begin_game(interaction)

@tree.command(name="answer", description="Submit your answer")
@app_commands.describe(text="Your answer to the question")
async def answer(interaction: discord.Interaction, text: str):
    game = games.get(interaction.guild_id)
    if not game:
        await interaction.response.send_message("No game in progress.", ephemeral=True)
        return
    if not game.active:
        await interaction.response.send_message("This game has ended.", ephemeral=True)
        return
    
    # Validate answer
    if not text.strip():
        await interaction.response.send_message("Please provide a non-empty answer.", ephemeral=True)
        return
    if len(text) > 500:
        await interaction.response.send_message("Answer must be 500 characters or less.", ephemeral=True)
        return
        
    await game.submit_answer(interaction, text.strip())

@tree.command(name="vote", description="Vote who you think is the imposter")
@app_commands.describe(user="Mention the player you vote for")
async def vote(interaction: discord.Interaction, user: discord.Member):
    game = games.get(interaction.guild_id)
    if not game:
        await interaction.response.send_message("No game in progress.", ephemeral=True)
        return
    if not game.active:
        await interaction.response.send_message("This game has ended.", ephemeral=True)
        return
    
    # Check if target user is still in server
    if not discord.utils.get(interaction.guild.members, id=user.id):
        await interaction.response.send_message("That user is no longer in the server.", ephemeral=True)
        return
        
    await game.submit_vote(interaction, user)

@tree.command(name="scoreboard", description="Show the current leaderboard")
async def scoreboard(interaction: discord.Interaction):
    game = games.get(interaction.guild_id)
    if not game:
        await interaction.response.send_message("No game in progress.", ephemeral=True)
        return
    if not game.active:
        await interaction.response.send_message("This game has ended.", ephemeral=True)
        return
    if game.current_round == 0:
        await interaction.response.send_message("The game hasn't started yet.", ephemeral=True)
        return
    await game.show_scoreboard(interaction)

@tree.command(name="endgame", description="Force end the current game")
async def endgame(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    game = games.get(guild_id)
    if not game:
        await interaction.response.send_message("No game is currently running.", ephemeral=True)
        return
    if not game.active:
        await interaction.response.send_message("The game has already ended.", ephemeral=True)
        return
    
    # Check if user is host or if host left server
    host_in_server = discord.utils.get(interaction.guild.members, id=game.host.id)
    if interaction.user != game.host and host_in_server:
        await interaction.response.send_message("Only the host can end the game.", ephemeral=True)
        return
      # If host left, allow any player to end
    if not host_in_server and not any(p.id == interaction.user.id for p in game.players):
        await interaction.response.send_message("Only players in the game can end it.", ephemeral=True)
        return
    
    await game.force_end()
    if guild_id in games:
        del games[guild_id]
    await interaction.response.send_message("The game has been forcefully ended.")

@tree.command(name="endround", description="Force end the current round and optionally remove a player")
@app_commands.describe(user="Mention a player to remove from the game (optional)")
async def endround(interaction: discord.Interaction, user: discord.Member = None):
    game = games.get(interaction.guild_id)
    if not game:
        await interaction.response.send_message("No game in progress.", ephemeral=True)
        return
    if not game.active:
        await interaction.response.send_message("The game has already ended.", ephemeral=True)
        return
    if game.current_round == 0:
        await interaction.response.send_message("The game hasn't started yet.", ephemeral=True)
        return
    
    # Check if user is host or if host left server
    host_in_server = discord.utils.get(interaction.guild.members, id=game.host.id)
    if interaction.user != game.host and host_in_server:
        await interaction.response.send_message("Only the host can end the round.", ephemeral=True)
        return
    
    # If host left, allow any player to end
    if not host_in_server and not any(p.id == interaction.user.id for p in game.players):
        await interaction.response.send_message("Only players in the game can end the round.", ephemeral=True)
        return
    
    if user:
        if not any(p.id == user.id for p in game.players):
            await interaction.response.send_message("That user is not in the game.", ephemeral=True)
            return
        await game.remove_player(user)
        await interaction.response.send_message(f"{user.mention} has been removed from the game.")
        if len(game.players) < 3:
            await game.force_end()
            if interaction.guild_id in games:
                del games[interaction.guild_id]
            await interaction.followup.send("Not enough players to continue. The game has ended.")
            return
    else:
        await interaction.response.send_message("The round has been forcefully ended. Proceeding to results.")
    
    game.voting_open = False
    if game.votes_done_event:
        game.votes_done_event.set()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    if ENV == "DEV":
        synced = await tree.sync(guild=DEV_GUILD)
        print(f"[DEV] Synced {len(synced)} commands to guild {DEV_GUILD_ID}")
    else:
        synced = await tree.sync()
        print(f"[PROD] Synced {len(synced)} global commands")

@bot.event
async def on_member_remove(member):
    """Handle when a member leaves the server during a game"""
    guild_id = member.guild.id
    if guild_id not in games:
        return
    
    game = games[guild_id]
    if not game.active:
        return
    
    # Check if the leaving member was in the game
    if any(p.id == member.id for p in game.players):
        await game.remove_player(member)
        await game.channel.send(f"⚠️ {member.mention} left the server and was removed from the game.")
        
        # End game if not enough players
        if len(game.players) < 3 and game.current_round > 0:
            await game.force_end()
            if guild_id in games:
                del games[guild_id]

if __name__ == "__main__":
    bot.run(TOKEN)
