# game_manager.py

import random
import asyncio
import discord
from questions_custom import QUESTION_PAIRS 

def validate_questions():
    """Validate that all question pairs are properly formatted"""
    for i, pair in enumerate(QUESTION_PAIRS):
        if not isinstance(pair, dict) or 'normal' not in pair or 'imposter' not in pair:
            raise ValueError(f"Invalid question pair at index {i}: {pair}")
        if not pair['normal'] or not pair['imposter']:
            raise ValueError(f"Empty question found at index {i}")
    return True

# Validate questions on import
validate_questions()

class GameManager:
    def __init__(self, guild, host, rounds, timer, anonymous, no_vote_timer=False):
        self.guild = guild
        self.host = host
        self.rounds_total = rounds
        self.timer = timer
        self.no_vote_timer = no_vote_timer
        self.players = []
        self.active = True
        self.game_started = False  # Track if /start was called
        self.current_round = 0
        self.imposter = None
        self.common_question = None
        self.imposter_question = None
        self.answers = {}
        self.votes = {}
        self.scores = {}  # user_id: points
        self.voting_open = False
        self.votes_done_event = None
        self.channel = None
        self._cleanup_callback = None  # Initialize cleanup callback

    async def start_lobby(self, interaction):
        self.channel = interaction.channel
        timer_info = f"Timer: {self.timer}s" if not self.no_vote_timer else "No timer (unlimited voting time)"
        await interaction.response.send_message(
            f"A new game of **Guess the Imposter** has started!\n"
            f"Type `/join` to participate.\n"
            f"Rounds: {self.rounds_total} | {timer_info}\n"
            f"The host must run `/start` to begin once enough players join."
        )

    async def add_player(self, interaction):
        try:
            if not self.active:
                await interaction.response.send_message("This game has ended.", ephemeral=True)
                return
            if self.game_started or self.current_round > 0:
                await interaction.response.send_message("You can't join after the game has started.", ephemeral=True)
                return
            if any(p.id == interaction.user.id for p in self.players):
                await interaction.response.send_message("You've already joined the game.", ephemeral=True)
                return
            # Check if user is still in the guild
            if not discord.utils.get(self.guild.members, id=interaction.user.id):
                await interaction.response.send_message("You must be a member of the server to join.", ephemeral=True)
                return
            # Check if bot can DM the user by sending a test message
            try:
                await interaction.user.send("✅ Test successful - you can receive DMs! You can safely ignore this message.")
                # If DM succeeds, add player and respond
                self.players.append(interaction.user)
                await interaction.response.send_message(f"{interaction.user.mention} joined the game! ({len(self.players)} players)")
            except Exception:
                await interaction.response.send_message("I can't DM you. Please enable DMs from server members to join.", ephemeral=True)
                return
        except Exception as e:
            # Catch-all to ensure a response is always sent
            try:
                await interaction.response.send_message(f"An unexpected error occurred: {str(e)}", ephemeral=True)
            except Exception:
                pass
            return

    async def remove_player(self, user):
        """Remove a player and clean up their data"""
        self.players = [p for p in self.players if p.id != user.id]
        
        # Clean up answers and votes
        if user in self.answers:
            del self.answers[user]
        if user in self.votes:
            del self.votes[user]
        
        # Remove votes for this user
        for voter in list(self.votes.keys()):
            if self.votes[voter].id == user.id:
                del self.votes[voter]
        
        # Handle imposter leaving during a round
        if self.imposter and self.imposter.id == user.id and self.current_round > 0:
            # If imposter leaves during active round, end the round
            if self.channel:
                await self.channel.send(f"⚠️ The imposter ({user.mention}) has left the game! Round ends automatically.")
                await self.channel.send(f"❓ The imposter's question was: \"{self.imposter_question}\"")
            # Close voting if it's open
            if self.voting_open:
                self.voting_open = False
                if self.votes_done_event:
                    self.votes_done_event.set()
        # If not enough players after removal
        if len(self.players) < 3:
            await self.end_game_with_results("Not enough players to continue (player left).")

    async def begin_game(self, interaction):
        # Check if host left server
        if not discord.utils.get(self.guild.members, id=self.host.id):
            await interaction.response.send_message("The host has left the server. Game ended.", ephemeral=True)
            self.active = False
            return
            
        if interaction.user != self.host:
            await interaction.response.send_message("Only the host can start the game.", ephemeral=True)
            return
        if len(self.players) < 3:
            await interaction.response.send_message("At least 3 players are required to start.", ephemeral=True)
            return
        if self.game_started:
            await interaction.response.send_message("The game has already been started.", ephemeral=True)
            return
            
        # Prevent starting if any player is no longer in the server
        removed = []
        for player in list(self.players):
            if not discord.utils.get(self.guild.members, id=player.id):
                removed.append(player)
                self.players.remove(player)
        if removed:
            await self.channel.send(", ".join(p.mention for p in removed) + " left the server and were removed from the game.")
        if len(self.players) < 3:
            await interaction.response.send_message("Not enough players to start after removing absent members.", ephemeral=True)
            return
        
        self.game_started = True
        await interaction.response.send_message("Starting game...")
        await self.next_round()

    async def next_round(self):
        self.current_round += 1
        self.answers.clear()
        self.votes.clear()
        # Check if we have questions available
        if not QUESTION_PAIRS:
            await self.end_game_with_results("No questions available.")
            return
        # Remove players who left the server
        removed = []
        for player in list(self.players):
            if not discord.utils.get(self.guild.members, id=player.id):
                removed.append(player)
                self.players.remove(player)
        if removed:
            await self.channel.send(", ".join(p.mention for p in removed) + " left the server and were removed from the game.")
        if not self.players or len(self.players) < 3:
            await self.end_game_with_results("Not enough players to continue.")
            return

        self.imposter = random.choice(self.players)
        q_pair = random.choice(QUESTION_PAIRS)
        self.common_question, self.imposter_question = q_pair["normal"], q_pair["imposter"]

        # Send questions via DM
        failed_dms = []
        for player in self.players:
            try:
                question = self.imposter_question if player.id == self.imposter.id else self.common_question
                await player.send(
                    f"**Round {self.current_round}/{self.rounds_total}**\n\n"
                    f"❓ **{question}**\n\n"
                    f"Reply with `/answer [your answer]` in the server channel."
                )
            except Exception:
                failed_dms.append(player)
                
        # Remove players who couldn't be DM'd
        for player in failed_dms:
            self.players.remove(player)
            await self.channel.send(f"{player.mention} could not be DM'd and was removed from the game.")
        if len(self.players) < 3:
            await self.end_game_with_results("Not enough players to continue (DM failure).")
            return

        await self.channel.send(
            f"**Round {self.current_round}/{self.rounds_total}** has started!\n"
            f"Everyone, answer your question using `/answer [your answer]`.\n"
            f"Please **don't reveal your question**!\n\n"
            f"Waiting for {len(self.players)} players to submit answers..."
        )

    async def submit_answer(self, interaction, text):
        if not self.active or self.current_round == 0:
            await interaction.response.send_message("No round is currently active.", ephemeral=True)
            return
        if not any(p.id == interaction.user.id for p in self.players):
            await interaction.response.send_message("You're not part of this game.", ephemeral=True)
            return
        if interaction.user in self.answers:
            await interaction.response.send_message("You've already submitted an answer.", ephemeral=True)
            return
          # Check if user still in server
        if not discord.utils.get(self.guild.members, id=interaction.user.id):
            await interaction.response.send_message("You are no longer in the server.", ephemeral=True)
            return
            
        self.answers[interaction.user] = text
        
        # Remove answers from players who left
        for user in list(self.answers.keys()):
            if not any(p.id == user.id for p in self.players):
                del self.answers[user]
          # Re-check if user is still in players list after cleanup
        if not any(p.id == interaction.user.id for p in self.players):
            await interaction.response.send_message("You are no longer in the game.", ephemeral=True)
            return
            
        await interaction.response.send_message("Answer submitted!", ephemeral=True)
                
        # Check if all answers are in
        if len(self.answers) == len(self.players):
            await self.reveal_answers()

    async def reveal_answers(self):
        if not self.answers:
            await self.channel.send("No answers to reveal. Moving to next round.")
            return
        
        msg = "\n📝 **All answers:**\n"
        for user, answer in self.answers.items():
            msg += f"• {user.mention}: {answer}\n"
        await self.channel.send(msg)
        await self.reveal_question()

    async def reveal_question(self):
        await self.channel.send(f"\n🧠 **Everyone's question:** {self.common_question}")
        
        voting_msg = f"\nYou have {self.timer} seconds to discuss and find the imposter! Voting is open during this time. Use `/vote @player`."
        if self.no_vote_timer:
            voting_msg = "\nNo timer for voting. Discuss and vote for who you think is the imposter using `/vote @player`."
        
        await self.channel.send(voting_msg)
        self.voting_open = True
        self.votes_done_event = asyncio.Event()
        
        if self.no_vote_timer:
            await self.channel.send("The round will continue until all votes are in.")
            while self.voting_open:
                await asyncio.sleep(2)
                if len(self.votes) == len(self.players):
                    self.voting_open = False
                    if self.votes_done_event:
                        self.votes_done_event.set()
        else:
            reminder_interval = 15 if self.timer > 30 else max(5, self.timer // 3)
            time_left = self.timer
            while time_left > 0 and self.voting_open:
                try:
                    await asyncio.wait_for(self.votes_done_event.wait(), timeout=min(reminder_interval, time_left))
                    # If event is set, all votes are in
                    break
                except asyncio.TimeoutError:
                    time_left -= reminder_interval
                    if time_left > 0 and self.voting_open:
                        await self.channel.send(f"⏳ {time_left} seconds left! Time is running out, please vote using `/vote @player`.")
            self.voting_open = False
            await self.channel.send("Time's up! Voting is now closed.")
        await self.reveal_results()

    async def submit_vote(self, interaction, target):
        # Double-check voting is still open (race condition protection)
        if not self.voting_open or not self.active:
            await interaction.response.send_message("Voting is currently closed. You can only vote during the discussion period.", ephemeral=True)
            return
        if not any(p.id == interaction.user.id for p in self.players) or not any(p.id == target.id for p in self.players):
            await interaction.response.send_message("Invalid vote.", ephemeral=True)
            return
        if interaction.user in self.votes:
            await interaction.response.send_message("You already voted.", ephemeral=True)
            return
        if interaction.user.id == target.id:
            await interaction.response.send_message("You cannot vote for yourself!", ephemeral=True)
            return
        
        # Check if both users still in server
        if not discord.utils.get(self.guild.members, id=interaction.user.id):
            await interaction.response.send_message("You are no longer in the server.", ephemeral=True)
            return
        if not discord.utils.get(self.guild.members, id=target.id):
            await interaction.response.send_message("That user is no longer in the server.", ephemeral=True)
            return
            
        self.votes[interaction.user] = target
        await interaction.response.send_message(f"Vote for {target.display_name} received!", ephemeral=True)
        
        # Remove votes from players who left
        for user in list(self.votes.keys()):
            if not any(p.id == user.id for p in self.players):
                del self.votes[user]
                  # Check if all votes are in (with race condition protection)
        if len(self.votes) == len(self.players) and self.voting_open:
            self.voting_open = False
            if self.votes_done_event:
                self.votes_done_event.set()

    async def reveal_results(self):
        try:
            if not self.votes:
                await self.channel.send("No votes were cast. The imposter escapes!")
                if self.imposter and any(p.id == self.imposter.id for p in self.players):
                    await self.channel.send(f"❗ The imposter was {self.imposter.mention}!")
                    if self.imposter_question:
                        await self.channel.send(f"❓ Their question was: \"{self.imposter_question}\"")
                    self.scores[self.imposter.id] = self.scores.get(self.imposter.id, 0) + 2
                elif self.imposter:
                    await self.channel.send("❗ The imposter left the game!")
                await asyncio.sleep(2)
                await self.continue_game()
                return
            
            vote_counts = {}
            for voter, voted in self.votes.items():
                vote_counts[voted] = vote_counts.get(voted, 0) + 1

            # Handle tie: imposter wins by default
            max_votes = max(vote_counts.values())
            top_voted = [user for user, count in vote_counts.items() if count == max_votes]
            
            if len(top_voted) > 1:
                await self.channel.send("It's a tie! The imposter escapes by default.")
                if self.imposter:
                    await self.channel.send(f"❗ The imposter was {self.imposter.mention}!")
                    if self.imposter_question:
                        await self.channel.send(f"❓ Their question was: \"{self.imposter_question}\"")
                    self.scores[self.imposter.id] = self.scores.get(self.imposter.id, 0) + 2
            else:
                top_voted = top_voted[0]
                await self.channel.send(f"❗ **The imposter was {self.imposter.mention}!**")
                await self.channel.send(f"❓ Their question was: \"{self.imposter_question}\"")

                if top_voted.id == self.imposter.id:
                    await self.channel.send("🎯 **The imposter was caught!**")
                    for voter, voted in self.votes.items():
                        if voted.id == self.imposter.id and voter.id != self.imposter.id:
                            self.scores[voter.id] = self.scores.get(voter.id, 0) + 1
                else:
                    await self.channel.send("😈 **The imposter got away!**")
                    # Only award points to imposter if they're still in the game
                    if any(p.id == self.imposter.id for p in self.players):
                        self.scores[self.imposter.id] = self.scores.get(self.imposter.id, 0) + 2

            await asyncio.sleep(2)
            await self.continue_game()
        except Exception as e:
            await self.channel.send(f"❗ An unexpected error occurred during results: {str(e)}. The game has ended.")
            self.active = False
            await self._cleanup_game()

    async def continue_game(self):
        try:
            # Show scorecard after every round except the last
            if self.current_round < self.rounds_total:
                msg = "🏅 **Current Scores:**\n"
                for player in self.players:
                    score = self.scores.get(player.id, 0)
                    msg += f"{player.mention}: {score} pts\n"
                await self.channel.send(msg)
                await self.channel.send(f"\n--- Starting round {self.current_round + 1} ---")
                await asyncio.sleep(3)
                await self.next_round()
            else:
                await self.final_scores()
        except Exception as e:
            await self.channel.send(f"❗ An unexpected error occurred during round progression: {str(e)}. The game has ended.")
            self.active = False
            await self._cleanup_game()

    async def final_scores(self):
        try:
            leaderboard = sorted([(player, self.scores.get(player.id, 0)) for player in self.players], key=lambda x: -x[1])
            msg = "\n🏆 **Final Scores:**\n"
            for i, (player, score) in enumerate(leaderboard):
                if i == 0:
                    emoji = "🥇"
                elif i == 1:
                    emoji = "🥈"
                elif i == 2:
                    emoji = "🥉"
                else:
                    emoji = "🏅"
                msg += f"{emoji} {player.mention} - {score} pts\n"
            await self.channel.send(msg)
            # Announce winner(s) or tie
            if leaderboard and leaderboard[0][1] > 0:
                top_score = leaderboard[0][1]
                winners = [player for player, score in leaderboard if score == top_score]
                if len(winners) == 1:
                    await self.channel.send(f"🎉 **{winners[0].mention} wins the game!** 🎉")
                else:
                    winner_mentions = ", ".join(w.mention for w in winners)
                    await self.channel.send(f"🤝 **It's a tie! Winners:** {winner_mentions} with {top_score} pts each!")
            self.active = False
            await self._cleanup_game()
        except Exception as e:
            await self.channel.send(f"❗ An unexpected error occurred during final scores: {str(e)}. The game has ended.")
            self.active = False
            await self._cleanup_game()

    def set_cleanup_callback(self, callback):
        """Set the cleanup callback function"""
        self._cleanup_callback = callback

    async def _cleanup_game(self):
        """Helper method to clean up game from bot's games dictionary"""
        if hasattr(self, '_cleanup_callback') and self._cleanup_callback:
            await self._cleanup_callback()

    async def show_scoreboard(self, interaction):
        if not self.scores:
            await interaction.response.send_message("No scores yet.", ephemeral=True)
            return
        
        # Sort by score descending
        sorted_scores = sorted(self.scores.items(), key=lambda x: -x[1])
        msg = "🏅 **Current Scores:**\n"
        for uid, score in sorted_scores:
            user = discord.utils.get(self.guild.members, id=uid)
            if user:
                msg += f"{user.display_name}: {score} pts\n"
            else:
                msg += f"Former player: {score} pts\n"
        await interaction.response.send_message(msg)

    async def end_game_with_results(self, reason):
        await self.channel.send(f"**Game ended early! Reason:** {reason}")
        # Reveal imposter/question if available
        if self.imposter:
            await self.channel.send(f"The imposter was {self.imposter.mention}!")
            if self.imposter_question:
                await self.channel.send(f"❓ The imposter's question was: \"{self.imposter_question}\"")
        else:
            await self.channel.send("Imposter data is not present.")
        # Show final scores
        leaderboard = sorted([(player, self.scores.get(player.id, 0)) for player in self.players], key=lambda x: -x[1])
        msg = "\n🏆 **Final Scores:**\n"
        for i, (player, score) in enumerate(leaderboard):
            if i == 0:
                emoji = "🥇"
            elif i == 1:
                emoji = "🥈"
            elif i == 2:
                emoji = "🥉"
            else:
                emoji = "🏅"
            msg += f"{emoji} {player.mention} - {score} pts\n"
        await self.channel.send(msg)
        if leaderboard and leaderboard[0][1] > 0:
            top_score = leaderboard[0][1]
            winners = [player for player, score in leaderboard if score == top_score]
            if len(winners) == 1:
                await self.channel.send(f"🎉 **{winners[0].mention} wins the game!** 🎉")
            else:
                winner_mentions = ", ".join(w.mention for w in winners)
                await self.channel.send(f"🤝 **It's a tie! Winners:** {winner_mentions} with {top_score} pts each!")
        self.active = False
        await self._cleanup_game()

    async def force_end(self):
        await self.end_game_with_results("Force ended by host or player.")
