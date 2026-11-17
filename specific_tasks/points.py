# main python file
import discord
from discord import reaction
from discord.ext import commands
from discord import app_commands
import os
import logging
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('DISCORD_BOT_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class MyBot(commands.Bot):
    async def on_ready(self):
        print(f'Logged in as {self.user}!')
        
        try:
            guild = discord.Object(id=1554889207321993306)
            sync = await self.tree.sync(guild=guild)
            print(f'Synced {len(sync)} commands to guild {guild.id}.')
            
        except Exception as e:
            print(f'Error syncing commands: {e}')
            
        
    async def on_message(self,message):
        if message.author == self.user:
            return
        
        if message.content.startswith('!'):
            await message.channel.send('Hello! I am a bot that responds to commands starting with "!".')

    async def on_reaction_add(self, reaction, user):
        await reaction.message.channel.send('A reaction was added!')
        

client = MyBot(command_prefix='!', intents=intents)

guild_ID = discord.Object(id=1554889207321993306)

@client.tree.command(name="points", description="View your points", guild=guild_ID)
async def points(interaction: discord.Interaction):
    await interaction.response.send_message("You have 100 points!")
client.run(token)