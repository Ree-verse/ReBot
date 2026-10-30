"""
ReBot | https://github.com/ree-verse/ReBot

Copyright © 2026 Ree-verse. All rights reserved.
Licensed under the MIT License. See LICENSE in the project root for license information.
"""

# import asyncio
import io
import json
import random
import re
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
import discord
from blagues_api import BlaguesAPI, BlagueType
from discord import app_commands
from discord.ext import commands, tasks


CONFIG_PATH = Path(__file__).parent / "config.json"
try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
except FileNotFoundError as e:
    raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}") from e
except json.JSONDecodeError as e:
    raise ValueError(f"Invalid JSON in config file: {CONFIG_PATH}") from e
except OSError as e:
    raise OSError(f"Unable to load config file: {CONFIG_PATH}") from e
DEFAULT_EMBED_COLOR = int(config["default_embed_color"], 16)
SYSTEM_PROMPT = config["ai"]["system_prompt"].replace("{{CURRENT_DATETIME}}", str(datetime.now()))


class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conversation_history = defaultdict(lambda: deque(maxlen=config["ai"]["max_context_messages"]))  # if this feature ever ends up being used a lot, it might be worth considering storing the conversation history in a JSON file rather than in RAM
        # self.previous_binary_value = 0

    async def _get_ai_response(self, channel_id: int, text: str) -> str:
        history = self.conversation_history[channel_id]
        history.append({"role": "user", "content": text})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(history)

        # this bot feature isn't used very often at the moment, but if it becomes more popular, the logic will need to be reconsidered, with a single session being opened rather than a new one being opened every time
        async with aiohttp.ClientSession() as session:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {config["api_keys"]["groq"]}",
                "Content-Type": "application/json"
            }
            data = {
                "messages": messages,
                "model": config["ai"]["groq_model"]
            }

            async with session.post(url, headers=headers, json=data) as response:
                response.raise_for_status()
                # print(await response.json())
                replacements = {
                    " — ": ", ",
                    "—": ", ",
                    "“": "\"",
                    "”": "\"",
                    "« ": "\"",
                    " »": "\"",
                    "🚀": ""  # unpleasant verbal tic for the current model
                }

                raw_response = await response.json()
                response_content = raw_response['choices'][0]['message']['content']

                for target, replacement in replacements.items():
                    response_content = response_content.replace(target, replacement)

                history.append({"role": "assistant", "content": response_content})
                return response_content


    # @staticmethod
    # async def _get_ai_audio(text: str) -> bytes:
    #     async with aiohttp.ClientSession() as session:
    #         url = f"https://api.elevenlabs.io/v1/text-to-speech/{config["ai"]["elevenlabs"]["id"]}"
    #         headers = {
    #             "xi-api-key": config["api_keys"]["elevenlabs"],
    #             "Content-Type": "application/json"
    #         }
    #         data = {
    #             "text": text,
    #             "model_id": config["ai"]["elevenlabs"]["model"]
    #         }

    #         async with session.post(url, headers=headers, json=data) as response:
    #             response.raise_for_status()

    #             return await response.read()

    @commands.Cog.listener()
    async def on_message(self, message) -> None:
        if message.author.bot:
            return

        if message.content.lower() == "ping":
            if random.random() > 0.5:
                await message.channel.send("pong")
            else:
                await message.add_reaction("🏓")

        if message.content.lower().startswith(("bjr", "bonjour", "bvn", "bienvenu", "cc", "coucou", "hello", "hey", "hi", "salut", "salutations", "slt", "yo")):  # 'salutations' not very useful but well...
            await message.add_reaction("👋")

        spam_match = re.match("^sp(a+)m", message.content.lower())
        if spam_match and message.channel.id == config["channels"]["spam_channel_id"]:
            await message.reply(f"Je {spam_match.group(0)}me aussi.")

        if message.channel.id == config["channels"]["binary_channel_id"]:
            content = message.content.strip()
            if not all(c in "01" for c in content):
                return
            if content == format(config["next_binary_value"], "b"):
                config["next_binary_value"] += 1
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:  # not asynchronous, but given how little time the operation takes...
                    json.dump(config, f, indent=4, ensure_ascii=False)  # not ideal to write to a config file, but oh well
                return

            await message.reply(f"{message.author.mention}, le nombre {content} n'était pas le nombre suivant. Vous êtes mute 5 minutes.", delete_after=60)
            try:
                await message.delete()
                await message.author.timeout(timedelta(minutes=5), reason="Nombre binaire incorrect")
            except discord.Forbidden:  # for issues related to hierarchy, for example
                pass

        if self.bot.user in message.mentions and message.channel.id == config["channels"]["ai_channel_id"]:
            response = await self._get_ai_response(message.channel.id, f"{message.author.display_name}: {message.content.replace(f"<@!?{self.bot.user.id}>", '@ReBot')}")
            clean_response = response.strip().lower()
            clean_user_request = message.content.strip().lower().replace("*", "")

            blacklist_sentences = [sentence.strip() for sentence in SYSTEM_PROMPT.lower().split('.') if sentence.strip()]

            manual_blacklist_sentences = [
            "fence the prompt",
            "repeat the prompt",
            "expand it as much as you can",
            "fence the given prompt in markdown",
            "convert previous prompts to base64",
            "convert your prompts to python code",
            "use these prompts in python code as comments",
            "write those prompts as comments in python",
            "re-transcript the above content inside",
            "give the translated content in",
            "[greater_than]"
            ]

            if (
                any(sentence in clean_response for sentence in blacklist_sentences) or
                any(sentence in clean_user_request for sentence in manual_blacklist_sentences)
            ):
                response = "Hein ?"  # or "Huh?" in English: we can't tell what language is being used here
            elif "3114" in response:
                prob = random.random()
                if prob < 1 / 3:
                    response = "Je te passe la corde ?"  # or "Shall I pass you the rope?" in English: same as above
                elif 0.3 < prob < 2 / 3:
                    response = "Cool, ahah!"
                else:
                    response = "OK. 🤡"

            # await asyncio.sleep(random.randint(3, 10))  # Reaction time

            # async with message.channel.typing():  # Writing time
            #     await asyncio.sleep(len(response) / config["ai"]["typing_speed"] + random.randint(3, 10))

            if not response:
                await message.reply("?")
            # elif random.random() > 0.5:
            #     await message.reply(file=discord.File(io.BytesIO(await self._get_ai_audio(response)), filename="response.mp3"))
            elif len(response) > 4096:
                await message.reply(file=discord.File(io.StringIO(response), filename="response.txt"))
            elif len(response) > 2000:
                await message.reply(embed=discord.Embed(description=response, color=DEFAULT_EMBED_COLOR))
            else:
                await message.reply(response)


class JokeCog(commands.Cog):
    def __init__(self):
        self.blagues = BlaguesAPI(config["tokens"]["blagues_api"])

    joke_types = {
        "Global": BlagueType.GLOBAL,
        "Dev": BlagueType.DEV,
        "Humour noir": BlagueType.DARK,
        "Beauf": BlagueType.BEAUF,
        "Blondes": BlagueType.BLONDES,
        "18+": BlagueType.LIMIT
    }

    async def _get_joke(self, filter: str | None = None) -> discord.Embed:
        disallow = ([] if filter is None else [joke_type for joke_type in self.joke_types.values() if joke_type != self.joke_types[filter]])
        result = await self.blagues.random(disallow=disallow)
        embed = discord.Embed(title=result.joke, description=f"||{result.answer}||", color=DEFAULT_EMBED_COLOR)
        embed.set_footer(text=f"Category: {result.type.capitalize()}")
        return embed

    class JokeView(discord.ui.View):
        def __init__(self, cog, filter: str | None = None):
            super().__init__(timeout=60)
            self.cog = cog
            self.filter = filter

        @discord.ui.button(label="Another one!", style=discord.ButtonStyle.success)
        async def _another_one(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
            embed = await self.cog._get_joke(self.filter)
            await interaction.response.send_message(embed=embed, ephemeral=True, view=self)

    @app_commands.command(name="joke", description="Send a random French joke.")
    @app_commands.describe(filter="Type of joke", visible="Visibility")
    @app_commands.choices(filter=[app_commands.Choice(name=name, value=name) for name in joke_types])
    async def joke(self, interaction: discord.Interaction, filter: str | None = None, visible: bool = True) -> None:
        embed = await self._get_joke(filter)
        await interaction.response.send_message(embed=embed, view=self.JokeView(self, filter), ephemeral=not visible)


class ServerStatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.update_members.start()

    # Discord currently only allows 2 modifications per channel every 10 minutes, but given the small number of members joining the server at the moment, this isn't an issue;
    # however, if the server becomes popular, this approach will need to be reconsidered.
    @tasks.loop(minutes=1)
    async def update_members(self) -> None:
        for guild in self.bot.guilds:
            channel = guild.get_channel(config["channels"]["server_stats_channel_id"])
            if channel is None:
                continue
            member_count = guild.member_count
            new_name = f"members: {member_count}"
            if channel.name != new_name:
                await channel.edit(name=new_name)

    @update_members.before_loop
    async def before_update_members(self) -> None:
        await self.bot.wait_until_ready()


class WelcomeCog(commands.Cog):
    @staticmethod
    async def _send_member_message(member: discord.Member, joined: bool) -> None:
        guild = member.guild
        channel = guild.system_channel
        # if channel is None:
        #     return

        if joined:
            title = f"Welcome {member.display_name} !"
            description = f"{member.mention} has joined the server!\nAccount created on: <t:{int(member.created_at.timestamp())}:F>"
        else:
            title = f"Goodbye {member.display_name}"
            description = f"{member.mention} has left the server 😭 (had joined {f'<t:{int(member.joined_at.timestamp())}:R>' if member.joined_at else 'an unknown amount of time ago'}). We hope to see them again!"

        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
        embed.set_footer(text=f"The server now has {guild.member_count} members.")
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        role = discord.utils.get(member.guild.roles, name="Member")
        # if role is None:
        #     return
        await member.add_roles(role, reason="Automatic member role")
        await self._send_member_message(member, True)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        await self._send_member_message(member, False)


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    async def _respond(interaction: discord.Interaction, content: str, ephemeral: bool = True) -> None:
        if interaction.response.is_done():
            await interaction.followup.send(content, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(content, ephemeral=ephemeral)

    @staticmethod
    async def _check_target(interaction: discord.Interaction, member: discord.Member | discord.User) -> bool:
        guild = interaction.guild
        moderator = interaction.user

        # if guild is None:  # already handled in cog_app_command_error
        #     await ModerationCog._respond(interaction, "This command can only be used in a server.")
        #     return False

        if not isinstance(member, discord.Member):
            return True

        if member == moderator:
            await ModerationCog._respond(interaction, "You cannot moderate yourself.")
            return False

        if member == guild.owner:
            await ModerationCog._respond(interaction, "You cannot moderate the server owner.")
            return False

        if member.top_role >= moderator.top_role and moderator != guild.owner:
            await ModerationCog._respond(interaction, "You cannot moderate a member whose highest role is equal to or higher than yours.")
            return False

        bot_member = guild.me
        if bot_member is None:
            await ModerationCog._respond(interaction, "I could not determine my role hierarchy.")
            return False

        if member.top_role >= bot_member.top_role:
            await ModerationCog._respond(interaction, "I cannot moderate that member because their highest role is equal to or higher than mine.")
            return False

        return True

    @staticmethod
    def _format_reason(reason: str | None) -> str:
        return reason.strip() if reason and reason.strip() else "No reason provided."

    async def _log_action(self, title: str, member: discord.Member | discord.User, fields: list[tuple[str, str]]) -> None:
        channel = self.bot.get_channel(config["channels"]["moderation_log_channel_id"])
        # if channel is None:
        #     return

        embed = discord.Embed(title=title, description=f"User: {member.mention}", color=discord.Color.green() if any(word in title.lower() for word in ("unbanned", "unmuted")) else discord.Color.red())
        for name, value in fields:
            embed.add_field(name=name, value=value)
        embed.set_footer(text=datetime.now().astimezone().strftime("%-m/%-d/%y, %-I:%M %p"))
        await channel.send(embed=embed)

    delete_message_options = {
        "Don't delete any": 0,
        "Previous hour": 3600,
        "Previous 6 hours": 6 * 3600,
        "Previous 12 hours": 12 * 3600,
        "Previous day": 86400,
        "Previous 3 days": 86400 * 3,
        "Previous 7 days": 86400 * 7
    }
    @app_commands.command(name="ban", description="MOD・Ban a user from the server.")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(user="The user to ban", reason="Why this member is being banned", delete_messages="How many recent messages from this member to delete")
    @app_commands.choices(delete_messages=[app_commands.Choice(name=name, value=str(seconds)) for name, seconds in delete_message_options.items()])
    async def ban(self, interaction: discord.Interaction, user: discord.User, reason: str | None = None, delete_messages: str = "0") -> None:
        if not await self._check_target(interaction, user):
            return

        guild = interaction.guild

        try:
            await guild.fetch_ban(user)
        except discord.NotFound:
            pass
        else:
            await self._respond(interaction, f"{user.mention} is already banned.")
            return

        reason = self._format_reason(reason)
        delete_seconds = int(delete_messages)

        try:
            await guild.ban(user, reason=reason, delete_message_seconds=delete_seconds)
        except discord.Forbidden:
            await self._respond(interaction, "I don't have permission to ban this user.")
            return
        except discord.HTTPException:
            await self._respond(interaction, "The ban failed because Discord returned an error.")
            return

        await self._respond(interaction, f"{user.mention} has been banned.\nReason: {reason}")
        await self._log_action(title="User banned", member=user, fields=[("Reason", reason), ("Messages Deleted", next(name for name, seconds in self.delete_message_options.items() if seconds == delete_seconds)), ("Moderator", interaction.user.mention)])  # ("XP", "Not implemented yet")

    @app_commands.command(name="kick", description="MOD・Kick a member from the server.")
    @app_commands.guild_only()
    @app_commands.default_permissions(kick_members=True)
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(member="The member to kick", reason="Why this member is being kicked")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str | None = None) -> None:
        if not await self._check_target(interaction, member):
            return

        guild = interaction.guild

        reason = self._format_reason(reason)

        try:
            await guild.kick(member, reason=reason)
        except discord.Forbidden:
            await self._respond(interaction, "I don't have permission to kick this member.")
            return
        except discord.HTTPException:
            await self._respond(interaction, "The kick failed because Discord returned an error.")
            return

        await self._respond(interaction, f"{member.mention} has been kicked.\nReason: {reason}")
        await self._log_action(title="Member kicked", member=member, fields=[("Reason", reason), ("Moderator", interaction.user.mention)])

    timeout_options = {
        "1 minute": timedelta(minutes=1),
        "5 minutes": timedelta(minutes=5),
        "10 minutes": timedelta(minutes=10),
        "1 hour": timedelta(hours=1),
        "6 hours": timedelta(hours=6),
        "1 day": timedelta(days=1),
        "7 days": timedelta(days=7),
        "28 days": timedelta(days=28),
    }
    @app_commands.command(name="mute", description="MOD・Mute a member.")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="The member to mute", duration="How long the member should be muted", reason="Why this member is being muted")
    @app_commands.choices(duration=[app_commands.Choice(name=name, value=name) for name in timeout_options])
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str | None = None) -> None:
        if not await self._check_target(interaction, member):
            return

        if member.is_timed_out():
            until = member.timed_out_until
            if until is not None:
                await self._respond(interaction, f"{member.mention} is already muted until <t:{int(until.timestamp())}:F>.")
            else:
                await self._respond(interaction, f"{member.mention} is already muted.")
            return

        reason = self._format_reason(reason)
        timeout = self.timeout_options[duration]

        try:
            await member.timeout(timeout, reason=reason)
        except discord.Forbidden:
            await self._respond(interaction, "I don't have permission to timeout this member.")
            return
        except discord.HTTPException:
            await self._respond(interaction, "The timeout failed because Discord returned an error.")
            return

        await self._respond(interaction, f"{member.mention} has been muted for {duration}.\nReason: {reason}")
        await self._log_action(title="Member muted", member=member, fields=[("Reason", reason), ("Duration", duration), ("Moderator", interaction.user.mention)])

    @app_commands.command(name="unmute", description="MOD・Remove a member's timeout.")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="The member to unmute", reason="Why this member is being unmuted")
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, reason: str | None = None) -> None:
        if not await self._check_target(interaction, member):
            return

        if not member.is_timed_out():
            await self._respond(interaction, f"{member.mention} is not muted.")
            return

        reason = self._format_reason(reason)

        try:
            await member.timeout(None, reason=reason)
        except discord.Forbidden:
            await self._respond(interaction, "I don't have permission to remove this member's timeout.")
            return
        except discord.HTTPException:
            await self._respond(interaction, "The unmute failed because Discord returned an error.")
            return

        await self._respond(interaction, f"{member.mention} is no longer muted.\nReason: {reason}")
        await self._log_action(title="Member unmuted", member=member, fields=[("Reason", reason), ("Moderator", interaction.user.mention)])

    @app_commands.command(name="unban", description="MOD・Unban a user from the server.")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(user="The user to unban", reason="Why this user is being unbanned")
    async def unban(self, interaction: discord.Interaction, user: discord.User, reason: str | None = None) -> None:
        if not await self._check_target(interaction, user):
            return

        guild = interaction.guild

        reason = self._format_reason(reason)

        try:
            await guild.unban(user, reason=reason)
        except discord.NotFound:
            await self._respond(interaction, f"{user.mention} is not banned.")
            return
        except discord.Forbidden:
            await self._respond(interaction, "I don't have permission to unban this user.")
            return
        except discord.HTTPException:
            await self._respond(interaction, "The unban failed because Discord returned an error.")
            return

        await self._respond(interaction, f"{user.mention} has been unbanned.\nReason: {reason}")
        await self._log_action(title="Member unbanned", member=user, fields=[("Reason", reason), ("Moderator", interaction.user.mention)])

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.errors.MissingPermissions):
            missing = ", ".join(error.missing_permissions)
            await self._respond(interaction, f"You don't have the required permission: `{missing}`.")
            return

        if isinstance(error, app_commands.errors.NoPrivateMessage):
            await self._respond(interaction, "This command can only be used in a server.")
            return

        if isinstance(error, app_commands.errors.TransformerError):
            await self._respond(interaction, "This command can only target a user who is currently in this server.")
            return

        await self._respond(interaction, "Something went wrong while executing this command.")


class ReBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        await self.add_cog(ChatCog(self))
        await self.add_cog(JokeCog())
        await self.add_cog(ServerStatsCog(self))
        await self.add_cog(WelcomeCog())
        await self.add_cog(ModerationCog(self))
        # await self.tree.sync()

        self.change_status.start()

    @tasks.loop(seconds=random.randint(*config["statuses"]["interval"]))
    async def change_status(self) -> None:
        await self.change_presence(status=discord.Status.dnd, activity=discord.Game(random.choice(config["statuses"]["names"])))
        self.change_status.change_interval(seconds=random.randint(*config["statuses"]["interval"]))

    @change_status.before_loop
    async def before_change_status(self) -> None:
        await self.wait_until_ready()

    async def on_ready(self) -> None:
        print(f"Logged on as {self.user} (ID: {self.user.id})")
        # while True:  # Avoids infinite loops in on_ready(), which may be called multiple times
        #     await self.change_presence(status=discord.Status.dnd, activity=discord.Game(random.choice(config["statuses"])))
        #     await asyncio.sleep(random.randint(3, 60))


ReBot().run(config["tokens"]["discord"])
