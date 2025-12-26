import discord
from discord import app_commands
from discord.ext import commands, tasks
import os
import random
import aiosqlite
from database import DB_PATH

class Exchange(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = int(os.getenv('OWNER_ID') or 0)
        self.rate_fluctuation.start()

    def get_owner_id(self):
        return self.owner_id

    @tasks.loop(hours=1)
    async def rate_fluctuation(self):
        """Randomly changes exchange rate if dynamic mode is on."""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT is_dynamic FROM market WHERE id = 1")
                market = await cursor.fetchone()

                if market and market['is_dynamic']:
                    # Rate fluctuates between 0.8 and 1.2
                    new_rate = round(random.uniform(0.8, 1.2), 2)
                    await db.execute("UPDATE market SET exchange_rate = ? WHERE id = 1", (new_rate,))
                    await db.commit()
        except Exception as e:
            print(f"Error in rate_fluctuation: {e}")

            if market and market['is_dynamic']:
                # Rate fluctuates between 0.8 and 1.2
                new_rate = round(random.uniform(0.8, 1.2), 2)
                await db.execute("UPDATE market SET exchange_rate = ? WHERE id = 1", (new_rate,))
                await db.commit()

    @app_commands.command(name="cek_kurs", description="Cek nilai tukar XP ke Point saat ini.")
    async def cek_kurs(self, interaction: discord.Interaction):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT exchange_rate, tax_rate FROM market WHERE id = 1")
            market = await cursor.fetchone()

            rate = market['exchange_rate']
            tax = market['tax_rate']

            await interaction.response.send_message(f"💰 **Kurs Saat Ini:**\n1 XP = {rate} Point\nPajak Transaksi: {tax}%")

    @app_commands.command(name="convert", description="Tukar XP menjadi Point (Uang).")
    @app_commands.describe(amount="Jumlah XP yang ingin ditukar")
    async def convert(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            await interaction.response.send_message("Jumlah XP harus positif!", ephemeral=True)
            return

        user_id = interaction.user.id

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            # Check Balance
            cursor = await db.execute("SELECT xp, point, role FROM users WHERE id = ?", (user_id,))
            user = await cursor.fetchone()

            if not user or user['xp'] < amount:
                await interaction.response.send_message(f"XP tidak cukup! Anda hanya punya {user['xp'] if user else 0} XP.", ephemeral=True)
                return

            # Get Market Info
            cursor = await db.execute("SELECT exchange_rate, tax_rate FROM market WHERE id = 1")
            market = await cursor.fetchone()
            rate = market['exchange_rate']
            tax_percent = market['tax_rate']

            # Calculation
            gross_points = int(amount * rate)
            tax_amount = int(gross_points * (tax_percent / 100))
            net_points = gross_points - tax_amount

            # Update User (Deduct XP, Add Net Points)
            new_xp = user['xp'] - amount
            new_points = user['point'] + net_points

            await db.execute("UPDATE users SET xp = ?, point = ? WHERE id = ?", (new_xp, new_points, user_id))

            # Pay Tax to Owner
            # We need to make sure Owner exists in DB
            owner_id = self.get_owner_id()
            if owner_id != 0:
                cursor = await db.execute("SELECT point FROM users WHERE id = ?", (owner_id,))
                owner = await cursor.fetchone()
                if owner:
                    await db.execute("UPDATE users SET point = point + ? WHERE id = ?", (tax_amount, owner_id))
                else:
                    # Create owner if not exists (Admin usually already has account, but for safety)
                    await db.execute("INSERT INTO users (id, point, role) VALUES (?, ?, 'Admin')", (owner_id, tax_amount))

                # Notify Owner (Silent update or DM)
                try:
                    owner_user = self.bot.get_user(owner_id)
                    if owner_user:
                        await owner_user.send(f"💸 **Pajak Masuk!**\nUser {interaction.user.name} menukar {amount} XP.\nAnda mendapatkan {tax_amount} Point (Pajak {tax_percent}%).")
                except:
                    pass # DM closed or bot can't see owner

            await db.commit()

        await interaction.response.send_message(f"✅ **Transaksi Berhasil!**\nAnda menukar {amount} XP.\nKurs: {rate}\nTotal: {gross_points} Point\nPajak: {tax_amount} Point\n**Diterima: {net_points} Point**")

    @app_commands.command(name="set_rate", description="Admin: Atur kurs dan mode dynamic.")
    @app_commands.describe(mode="Dynamic (Auto) atau Static (Manual)", rate="Nilai kurs (jika Static)", tax="Persen pajak")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Dynamic (Berubah-ubah)", value="dynamic"),
        app_commands.Choice(name="Static (Tetap)", value="static")
    ])
    async def set_rate(self, interaction: discord.Interaction, mode: str, rate: float = 1.0, tax: int = 5):
        if interaction.user.id != self.get_owner_id():
            await interaction.response.send_message("❌ Anda bukan pemilik bot ini!", ephemeral=True)
            return

        is_dynamic = 1 if mode == "dynamic" else 0

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("UPDATE market SET is_dynamic = ?, exchange_rate = ?, tax_rate = ? WHERE id = 1",
                             (is_dynamic, rate, tax))
            await db.commit()

        await interaction.response.send_message(f"⚙️ **Pengaturan Market Diubah:**\nMode: {mode}\nRate: {rate}\nPajak: {tax}%")

async def setup(bot):
    await bot.add_cog(Exchange(bot))
