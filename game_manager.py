# game_manager.py

import random
import asyncio
import discord
from questions_custom import QUESTION_PAIRS 

class GameManager:
    def __init__(self, guild, host, rounds, timer, anonymous, no_vote_timer=False):
        self.guild = guild
        self.host = host
        self.rounds_total = rounds
        self.timer = timer
        self.anonymous = anonymous
        self.no_vote_timer = no_vote_timer
        self.players = []
        self.active = True

        self.current_round = 0
        self.imposter = None
        self.common_question = None
        self.imposter_question = None
        self.answers = {}
        self.votes = {}
        self.scores = {}  # user_id: points
        self.voting_open = False
        self.votes_done_event = None

    async def start_lobby(self, interaction):
        self.channel = interaction.channel
        await interaction.response.send_message(
            f"A new game of **Guess the Imposter** has started!\n"
            f"Type `/join` to participate.\n"
            f"Rounds: {self.rounds_total} | Timer: {self.timer}s | Anonymous answers: {self.anonymous}\n"
            f"The host must run `/start` to begin once enough players join."
        )

    async def add_player(self, interaction):
        if any(p.id == interaction.user.id for p in self.players):
            await interaction.response.send_message("You've already joined the game.", ephemeral=True)
            return
        self.players.append(interaction.user)
        await interaction.response.send_message(f"{interaction.user.mention} joined the game!")

    async def begin_game(self, interaction):
        if interaction.user != self.host:
            await interaction.response.send_message("Only the host can start the game.", ephemeral=True)
            return
        if len(self.players) < 3:
            await interaction.response.send_message("At least 3 players are required to start.", ephemeral=True)
            return

        await interaction.response.send_message("Starting game...")
        await self.next_round()

    async def next_round(self):
        self.current_round += 1
        self.answers.clear()
        self.votes.clear()
        if not self.players or len(self.players) < 3:
            await self.channel.send("Not enough players to continue. Game ended.")
            self.active = False
            return

        self.imposter = random.choice(self.players)
        q_pair = random.choice(QUESTION_PAIRS)
        self.common_question, self.imposter_question = q_pair["normal"], q_pair["imposter"]

        failed_dms = []
        for player in self.players:
            try:
                question = self.imposter_question if player.id == self.imposter.id else self.common_question
                await player.send(
                    f"Here's your question:\n\n"
                    f"❓ **{question}**"
                )
            except Exception:
                failed_dms.append(player)
        for player in failed_dms:
            self.players.remove(player)
            await self.channel.send(f"{player.mention} could not be DM'd and was removed from the game.")

        if len(self.players) < 3:
            await self.channel.send("Not enough players to continue. Game ended.")
            self.active = False
            return

        await self.channel.send(
            "Everyone, answer your question using `/answer [your answer]`.\nPlease **don’t reveal your question**!"
        )

    async def submit_answer(self, interaction, text):
        if not any(p.id == interaction.user.id for p in self.players):
            await interaction.response.send_message("You're not part of this game.", ephemeral=True)
            return
        if interaction.user in self.answers:
            await interaction.response.send_message("You've already submitted an answer.", ephemeral=True)
            return

        self.answers[interaction.user] = text
        await interaction.response.send_message("Answer submitted!", ephemeral=True)

        if len(self.answers) == len(self.players):
            await self.reveal_answers()

    async def reveal_answers(self):
        msg = "\n📝 All answers:\n"
        for user, answer in self.answers.items():
            if not self.anonymous:
                msg += f"{user.mention}: {answer}\n"
            else:
                msg += f"Answer: {answer}\n"
        await self.channel.send(msg)
        await self.reveal_question()

    async def reveal_question(self):
        await self.channel.send(f"\n🧠 Everyone's question: **{self.common_question}**")
        await self.channel.send(f"\nYou have {self.timer} seconds to discuss and find the imposter! Voting is open during this time. Use `/vote @player`.")
        self.voting_open = True
        self.votes_done_event = asyncio.Event()
        if self.no_vote_timer:
            await self.channel.send("No timer for voting. The round will continue until all votes are in.")
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
        if not self.voting_open:
            await interaction.response.send_message("Voting is currently closed. You can only vote during the discussion period.", ephemeral=True)
            return
        if not any(p.id == interaction.user.id for p in self.players) or not any(p.id == target.id for p in self.players):
            await interaction.response.send_message("Invalid vote.", ephemeral=True)
            return
        if interaction.user in self.votes:
            await interaction.response.send_message("You already voted.", ephemeral=True)
            return

        self.votes[interaction.user] = target
        await interaction.response.send_message(f"Vote for {target.display_name} received!", ephemeral=True)

        if len(self.votes) == len(self.players):
            self.voting_open = False
            if self.votes_done_event:
                self.votes_done_event.set()

    async def reveal_results(self):
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
            await self.channel.send(f"❗ Imposter: {self.imposter.mention} was the imposter!")
            await self.channel.send(f"❓ Their question was: \"{self.imposter_question}\"")

            if top_voted.id == self.imposter.id:
                await self.channel.send("🎯 The imposter was caught!")
                for voter, voted in self.votes.items():
                    if voted.id == self.imposter.id and voter.id != self.imposter.id:
                        self.scores[voter.id] = self.scores.get(voter.id, 0) + 1
            else:
                await self.channel.send("😈 The imposter got away!")
                self.scores[self.imposter.id] = self.scores.get(self.imposter.id, 0) + 2

        await asyncio.sleep(2)

        # Show scorecard after every round except the last
        if self.current_round < self.rounds_total:
            msg = "🏅 Current Scores:\n"
            for player in self.players:
                score = self.scores.get(player.id, 0)
                msg += f"{player.mention}: {score} pts\n"
            await self.channel.send(msg)
            await self.channel.send(f"\n--- Starting round {self.current_round + 1} ---")
            await asyncio.sleep(3)
            await self.next_round()
        else:
            await self.final_scores()

    async def final_scores(self):
        leaderboard = sorted([(player, self.scores.get(player.id, 0)) for player in self.players], key=lambda x: -x[1])
        msg = "\n🏆 Final Scores:\n"
        for player, score in leaderboard:
            msg += f"{player.mention} - {score} pts\n"
        await self.channel.send(msg)
        self.active = False

    async def show_scoreboard(self, interaction):
        if not self.scores:
            await interaction.response.send_message("No scores yet.", ephemeral=True)
            return
        msg = "🏅 Current Scores:\n"
        for uid, score in self.scores.items():
            user = discord.utils.get(self.guild.members, id=uid)
            if user:
                msg += f"{user.display_name}: {score} pts\n"
            else:
                msg += f"User({uid}): {score} pts\n"
        await interaction.response.send_message(msg)

    async def force_end(self):
        # Show questions
        if self.common_question and self.imposter_question:
            await self.channel.send(f"Game ended early!\n\nNormal question: **{self.common_question}**\nImposter question: **{self.imposter_question}**")
        else:
            await self.channel.send("Game ended early! Question data is not present.")
        # Show final scores
        if self.players:
            leaderboard = sorted([(player, self.scores.get(player.id, 0)) for player in self.players], key=lambda x: -x[1])
            msg = "\n🏆 Final Scores:\n"
            for player, score in leaderboard:
                msg += f"{player.mention} - {score} pts\n"
            await self.channel.send(msg)
        else:
            await self.channel.send("No players or score data is present.")
        # Tag imposter
        if self.imposter:
            await self.channel.send(f"The imposter was {self.imposter.mention}!")
        else:
            await self.channel.send("Imposter data is not present.")
        self.active = False
