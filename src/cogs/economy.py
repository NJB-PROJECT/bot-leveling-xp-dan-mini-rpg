import discord
from discord import app_commands
from discord.ext import commands
from database import get_db_connection

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Lihat daftar barang yang dijual.")
    async def shop(self, interaction: discord.Interaction):
        async with await get_db_connection() as db:
            cursor = await db.execute("SELECT * FROM items")
            items = await cursor.fetchall()

            embed = discord.Embed(title="🛒 Toko Barang", color=discord.Color.gold())

            for item in items:
                desc = f"Harga: {item['price']} Point\n{item['description']}\nDurability: {item['base_durability']}"
                if item['base_str']: desc += f"\nStr +{item['base_str']}"
                if item['base_agi']: desc += f" | Agi +{item['base_agi']}"
                if item['base_int']: desc += f" | Int +{item['base_int']}"

                embed.add_field(name=f"{item['name']} ({item['type']})", value=desc, inline=False)

            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Beli barang dari toko.")
    @app_commands.describe(item_name="Nama barang yang mau dibeli")
    async def buy(self, interaction: discord.Interaction, item_name: str):
        user_id = interaction.user.id

        async with await get_db_connection() as db:
            # Check Item
            cursor = await db.execute("SELECT * FROM items WHERE name = ?", (item_name,))
            item = await cursor.fetchone()

            if not item:
                await interaction.response.send_message("Barang tidak ditemukan!", ephemeral=True)
                return

            # Check Money
            cursor = await db.execute("SELECT point FROM users WHERE id = ?", (user_id,))
            user = await cursor.fetchone()

            if not user or user['point'] < item['price']:
                await interaction.response.send_message("Uang (Point) tidak cukup!", ephemeral=True)
                return

            # Transaction
            new_point = user['point'] - item['price']
            await db.execute("UPDATE users SET point = ? WHERE id = ?", (new_point, user_id))

            # Add to Inventory
            await db.execute("""
                INSERT INTO inventory (user_id, item_name, item_type, current_durability, max_durability)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, item['name'], item['type'], item['base_durability'], item['base_durability']))

            await db.commit()

        await interaction.response.send_message(f"✅ Kamu berhasil membeli **{item_name}**!")

    @app_commands.command(name="inventory", description="Lihat tas dan kondisi barang.")
    async def inventory(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        async with await get_db_connection() as db:
            cursor = await db.execute("SELECT * FROM inventory WHERE user_id = ?", (user_id,))
            items = await cursor.fetchall()

            if not items:
                await interaction.response.send_message("Tas kamu kosong!", ephemeral=True)
                return

            embed = discord.Embed(title="🎒 Tas Penyimpanan", color=discord.Color.green())

            for item in items:
                # Progress Bar for Durability
                dur_percent = int((item['current_durability'] / item['max_durability']) * 10)
                bar = "🟩" * dur_percent + "🟥" * (10 - dur_percent)

                status = "Terpakai" if item['is_equipped'] else "Disimpan"
                quality = int(item['stats_mod'] * 100)

                embed.add_field(
                    name=f"{item['item_name']} ({status})",
                    value=f"Durability: {item['current_durability']}/{item['max_durability']}\n{bar}\nKualitas: {quality}%",
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="equip", description="Pakai senjata/alat.")
    @app_commands.describe(item_name="Nama barang")
    async def equip(self, interaction: discord.Interaction, item_name: str):
        user_id = interaction.user.id
        async with await get_db_connection() as db:
            # Check if user has item
            cursor = await db.execute("SELECT id, item_type FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
            item = await cursor.fetchone()

            if not item:
                await interaction.response.send_message("Barang tidak ada di tas!", ephemeral=True)
                return

            # Unequip same type
            await db.execute("UPDATE inventory SET is_equipped = 0 WHERE user_id = ? AND item_type = ?", (user_id, item['item_type']))

            # Equip new
            await db.execute("UPDATE inventory SET is_equipped = 1 WHERE id = ?", (item['id'],))
            await db.commit()

        await interaction.response.send_message(f"⚔️ Kamu memasang **{item_name}**.")

    @app_commands.command(name="refurbish", description="Perbaiki barang rusak (Menurunkan kualitas maksimal).")
    @app_commands.describe(item_name="Nama barang yang mau diperbaiki")
    async def refurbish(self, interaction: discord.Interaction, item_name: str):
        user_id = interaction.user.id

        async with await get_db_connection() as db:
            cursor = await db.execute("SELECT * FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item_name))
            item = await cursor.fetchone()

            if not item:
                await interaction.response.send_message("Barang tidak ditemukan!", ephemeral=True)
                return

            if item['current_durability'] >= item['max_durability']:
                await interaction.response.send_message("Barang masih bagus, tidak perlu diperbaiki.", ephemeral=True)
                return

            cost = 50 # Flat cost for now

            # Check Money
            cursor = await db.execute("SELECT point FROM users WHERE id = ?", (user_id,))
            user = await cursor.fetchone()

            if user['point'] < cost:
                await interaction.response.send_message(f"Butuh {cost} Point untuk perbaikan!", ephemeral=True)
                return

            # Logic: Restore Durability to Full, BUT Reduce Max Durability/Stats by 10%
            new_stats_mod = item['stats_mod'] * 0.90
            new_max_durability = int(item['max_durability'] * 0.95) # Degrade max durability too

            if new_max_durability < 10:
                await interaction.response.send_message("Barang ini sudah terlalu hancur untuk diperbaiki!", ephemeral=True)
                return

            await db.execute("UPDATE users SET point = point - ? WHERE id = ?", (cost, user_id))
            await db.execute("""
                UPDATE inventory
                SET current_durability = ?, max_durability = ?, stats_mod = ?
                WHERE id = ?
            """, (new_max_durability, new_max_durability, new_stats_mod, item['id']))

            await db.commit()

        await interaction.response.send_message(f"🔧 **{item_name}** berhasil di-refurbish!\nKondisi fisik pulih, tapi material terkikis.\nMax Durability baru: {new_max_durability}\nKualitas Stats: {int(new_stats_mod*100)}%")

async def setup(bot):
    await bot.add_cog(Economy(bot))
