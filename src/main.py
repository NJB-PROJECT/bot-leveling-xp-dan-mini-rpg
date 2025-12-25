import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from database import init_db

# Load env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Setup Intent
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

class RPG_Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)

    async def setup_hook(self):
        # Load Cogs
        for filename in os.listdir('./src/cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')

        # Init DB on startup
        await init_db()
        print("Bot is ready and DB initialized!")

bot = RPG_Bot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    await bot.tree.sync()

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env")
    else:
        bot.run(TOKEN)
