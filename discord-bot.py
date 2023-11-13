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

    async def setup_hook(self):
        # sync to a specific guild
        self.tree.copy_global_to(guild=guild)

        # sync to all servers if no specification
        await self.tree.sync()


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
