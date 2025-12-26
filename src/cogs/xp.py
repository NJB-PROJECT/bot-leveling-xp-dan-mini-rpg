import discord
from discord.ext import commands, tasks
import random
import time
import asyncio
import aiosqlite
from database import DB_PATH

class XPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Only start the loop if we have an event loop running (avoids error during tests)
        try:
            asyncio.get_running_loop()
            self.voice_xp_loop.start()
        except RuntimeError:
            pass # Testing environment
        self.voice_users = {} # {user_id: timestamp_joined}

    def calculate_level(self, xp):
        # User defined: <100 XP = Lv 1. 120 XP = Lv 2.
        # Formula: Level = (XP // 100) + 1
        if xp < 0: return 1
        return (xp // 100) + 1

    async def add_xp(self, user_id, amount):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            # Check if user exists, if not create basic entry
            cursor = await db.execute("SELECT xp, role FROM users WHERE id = ?", (user_id,))
            user = await cursor.fetchone()

            if not user:
                # Default entry
                await db.execute("INSERT INTO users (id, xp, role) VALUES (?, ?, ?)", (user_id, amount, "Belum Ada Role"))
                new_xp = amount
            else:
                new_xp = user['xp'] + amount
                await db.execute("UPDATE users SET xp = ? WHERE id = ?", (new_xp, user_id))

            await db.commit()
            return new_xp

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Simple cooldown or random chance to prevent spam XP
        # Giving 1-3 XP per message
        xp_gain = random.randint(1, 3)
        new_xp = await self.add_xp(message.author.id, xp_gain)

        # Optional: Check level up?
        # Since Level is calculated dynamically from XP, we don't store "Level" in DB usually,
        # but the prompt implies visual feedback might be good.
        # For now, we just store XP.

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return

        # User joins voice
        if before.channel is None and after.channel is not None:
            self.voice_users[member.id] = time.time()

        # User leaves voice
        elif before.channel is not None and after.channel is None:
            if member.id in self.voice_users:
                del self.voice_users[member.id]

    @tasks.loop(minutes=1)
    async def voice_xp_loop(self):
        # Give XP every minute to users in voice
        current_time = time.time()
        for user_id, join_time in list(self.voice_users.items()):
            # Check if user is still in a valid channel (double check handled by dict logic usually)
            # Give 5 XP per minute
            await self.add_xp(user_id, 5)

async def setup(bot):
    await bot.add_cog(XPSystem(bot))
