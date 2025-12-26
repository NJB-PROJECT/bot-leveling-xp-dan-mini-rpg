import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
from database import DB_PATH

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="start", description="Pilih peran karakter Anda untuk memulai petualangan!")
    @app_commands.describe(role="Pilih peran yang Anda inginkan")
    @app_commands.choices(role=[
        app_commands.Choice(name="Petani (Pertanian)", value="Petani"),
        app_commands.Choice(name="Koki (Memasak)", value="Koki"),
        app_commands.Choice(name="Pelatih (Olahraga)", value="Pelatih"),
        app_commands.Choice(name="Pangeran (Premium)", value="Pangeran"),
        app_commands.Choice(name="Putri (Premium)", value="Putri")
    ])
    async def start(self, interaction: discord.Interaction, role: app_commands.Choice[str]):
        user_id = interaction.user.id
        selected_role = role.value

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT role FROM users WHERE id = ?", (user_id,))
            user = await cursor.fetchone()

            if user and user['role'] != "Belum Ada Role" and user['role'] is not None:
                await interaction.response.send_message(f"Anda sudah memiliki peran sebagai **{user['role']}**. Tidak bisa ganti peran sembarangan!", ephemeral=True)
                return

            # Initial Stats based on Role
            stats = {
                "Petani": {"str": 5, "agi": 3, "int": 2, "luck": 3},
                "Koki": {"str": 2, "agi": 4, "int": 3, "luck": 4},
                "Pelatih": {"str": 6, "agi": 5, "int": 2, "luck": 2},
                "Pangeran": {"str": 7, "agi": 6, "int": 8, "luck": 5}, # OP Role
                "Putri": {"str": 2, "agi": 4, "int": 8, "luck": 10}   # OP Role
            }

            s = stats.get(selected_role, {"str":1, "agi":1, "int":1, "luck":1})

            # Check if user exists to update, or insert new
            if user:
                 await db.execute("""
                    UPDATE users
                    SET role = ?, str = ?, agi = ?, intel = ?, luck = ?
                    WHERE id = ?
                """, (selected_role, s['str'], s['agi'], s['int'], s['luck'], user_id))
            else:
                await db.execute("""
                    INSERT INTO users (id, role, xp, point, str, agi, intel, luck)
                    VALUES (?, ?, 0, 0, ?, ?, ?, ?)
                """, (user_id, selected_role, s['str'], s['agi'], s['int'], s['luck']))

            await db.commit()

        await interaction.response.send_message(f"Selamat datang di Dunia RPG! Anda sekarang adalah seorang **{selected_role}**.\nStats Awal: Str {s['str']}, Agi {s['agi']}, Int {s['int']}, Luck {s['luck']}")

    @app_commands.command(name="status", description="Lihat status karakter Anda")
    async def status(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = await cursor.fetchone()

            if not user:
                await interaction.response.send_message("Anda belum terdaftar! Gunakan `/start` dulu.", ephemeral=True)
                return

            # Inventory summary
            inv_cursor = await db.execute("SELECT item_name, is_equipped FROM inventory WHERE user_id = ?", (user_id,))
            items = await inv_cursor.fetchall()
            equipped = [i['item_name'] for i in items if i['is_equipped']]
            bag_count = len(items)

            level = (user['xp'] // 100) + 1

            embed = discord.Embed(title=f"Status: {interaction.user.name}", color=discord.Color.blue())
            embed.add_field(name="Peran", value=user['role'] or "Pengangguran", inline=True)
            embed.add_field(name="Level", value=str(level), inline=True)
            embed.add_field(name="XP", value=f"{user['xp']} XP", inline=True)
            embed.add_field(name="Point (Uang)", value=f"{user['point']}", inline=True)

            embed.add_field(name="Stats", value=f"""
💪 Strength: {user['str']}
🏃 Agility: {user['agi']}
🧠 Intellect: {user['intel']}
🍀 Luck: {user['luck']}
🕵️ Criminal: {user['criminal_skill']}
            """, inline=False)

            embed.add_field(name="Equipment", value=", ".join(equipped) if equipped else "Kosong", inline=False)
            embed.set_footer(text=f"Items di tas: {bag_count}")

            await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Profile(bot))
