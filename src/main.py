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
    # Note: Global sync can take up to 1 hour. Use !sync for instant updates in dev.
    # await bot.tree.sync()

@bot.command(name="sync", description="Sinkronisasi command ke server ini (Admin/Owner).")
async def sync(ctx):
    # Check if user is owner (optional, but good practice)
    # owner_id = os.getenv('OWNER_ID')
    # if str(ctx.author.id) != owner_id: return

    msg = await ctx.send("⏳ Sinkronisasi command...")
    try:
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await msg.edit(content=f"✅ Berhasil sinkronisasi {len(synced)} command ke server ini!")
    except Exception as e:
        await msg.edit(content=f"❌ Gagal: {e}")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env")
    else:
        bot.run(TOKEN)
