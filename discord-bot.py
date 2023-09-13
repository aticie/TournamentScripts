# This example requires the 'message_content' intent.
import io
import logging
import os

import ossapi
import discord
from discord.ext import tasks
from rosu_pp_py import Beatmap, Calculator

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

ch.setFormatter(formatter)
logger.addHandler(ch)


intents = discord.Intents.default()
intents.members = True

guild = discord.Object(id=1142002979277385829)  # replace with your guild id


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
        with open("players.txt") as f:
            self.players = f.read().splitlines()
        self.players = [player.casefold() for player in self.players]

    # In this basic example, we just synchronize the app commands to one guild.
    # Instead of specifying a guild to every command, we copy over our global commands instead.
    # By doing so, we don't have to wait up to an hour until they are shown to the end-user.
    async def setup_hook(self):
        self.update_user_role.start()

    @tasks.loop(minutes=60)
    async def update_user_role(self):
        logger.info("Running update_user_role task!")
        guild = await self.fetch_guild(1142002979277385829)
        logger.info(f"Found the guild {guild}!")
        ogrenci_role = guild.get_role(1142006050027995217)
        logger.info(f"Found the role: {ogrenci_role}")
        server_users_names = []
        server_users = []
        async for user in guild.fetch_members():
            server_users_names.append(str(user).casefold())
            server_users.append(user)
        leftovers = set(self.players).difference(set(server_users_names))
        logger.info("----LEFTOVERS----")
        for leftover in leftovers:
            logger.info(leftover)
        # for user in server_users:
        #     if str(user).casefold() in self.players:
        #         if ogrenci_role not in user.roles:
        #             logger.info(f"Adding role to {user.global_name}")
        #             await user.add_roles(ogrenci_role)
        #         else:
        #             logger.info(f"{user.global_name} already has the role.")
        #     else:
        #         logger.error(f"Could not find {user.global_name} in player list.")




client = MyClient(intents=intents)


@client.tree.command(name="sr", description="Calculates star rating for a map.")
async def some_command(interaction, file: discord.Attachment, mods: str):
    beatmap_name = file.filename
    map = io.BytesIO()
    await file.save(map)
    bmap = Beatmap(bytes=map.read())
    mods_value = ossapi.mod.Mod(mods.upper()).value

    calc = Calculator(mods=mods_value)
    perf = calc.performance(bmap)
    diff = calc.difficulty(bmap)

    embed = discord.Embed(title=f"Stats for {beatmap_name}")
    embed.add_field(name="Difficulty Attributes",
                    value=f"SR: {diff.stars:.2f}\n"
                          f"Speed: {diff.speed:.2f}\n"
                          f"Aim: {diff.aim:.2f}", inline=False)
    embed.add_field(name="Performance Attributes",
                    value=f"PP: {perf.pp:.2f}\n"
                          f"PP Speed: {perf.pp_speed:.2f}\n"
                          f"PP Aim: {perf.pp_aim:.2f}\n"
                          f"PP Acc: {perf.pp_acc:.2f}")
    await interaction.response.send_message(embeds=[embed])


client.run(os.getenv("DISCORD_TOKEN"))
