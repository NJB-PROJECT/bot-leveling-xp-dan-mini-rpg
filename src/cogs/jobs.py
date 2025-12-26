import discord
from discord import app_commands
from discord.ext import commands
import json
import random
import time
from database import get_db_connection

class Jobs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_job_data(self, db, user_id):
        cursor = await db.execute("SELECT role, job_stage, job_data, last_job_time FROM users WHERE id = ?", (user_id,))
        return await cursor.fetchone()

    async def update_job_state(self, db, user_id, stage, data=None):
        if data is None:
            await db.execute("UPDATE users SET job_stage = ?, last_job_time = CURRENT_TIMESTAMP WHERE id = ?", (stage, user_id))
        else:
            await db.execute("UPDATE users SET job_stage = ?, job_data = ?, last_job_time = CURRENT_TIMESTAMP WHERE id = ?",
                             (stage, json.dumps(data), user_id))
        await db.commit()

    async def check_tool(self, db, user_id, tool_name):
        # Check if user has the tool and it has durability
        cursor = await db.execute("SELECT id, current_durability FROM inventory WHERE user_id = ? AND item_name = ? AND is_equipped = 1", (user_id, tool_name))
        tool = await cursor.fetchone()
        return tool

    async def degrade_tool(self, db, tool_id, amount=1):
        await db.execute("UPDATE inventory SET current_durability = current_durability - ? WHERE id = ?", (amount, tool_id))
        # If durability <= 0, delete or mark broken?
        # Plan says "Hancur" (Destroyed)
        await db.execute("DELETE FROM inventory WHERE id = ? AND current_durability <= 0", (tool_id,))

    # --- PETANI COMMANDS ---
    @app_commands.command(name="cangkul", description="[Petani] Menggemburkan tanah (Butuh Cangkul).")
    async def cangkul(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with await get_db_connection() as db:
            user = await self.get_user_job_data(db, user_id)
            if user['role'] != "Petani":
                return await interaction.response.send_message("Kamu bukan Petani!", ephemeral=True)

            tool = await self.check_tool(db, user_id, "Cangkul")
            if not tool:
                return await interaction.response.send_message("Kamu harus memegang **Cangkul**!", ephemeral=True)

            if user['job_stage'] != "idle":
                return await interaction.response.send_message(f"Tanah sedang dalam kondisi {user['job_stage']}, tidak perlu dicangkul lagi.", ephemeral=True)

            await self.degrade_tool(db, tool['id'], 5)
            await self.update_job_state(db, user_id, "ready_to_plant")
            await interaction.response.send_message("🌾 Tanah berhasil dicangkul! Siap ditanami.")

    @app_commands.command(name="tanam", description="[Petani] Menanam bibit (Butuh Bibit Padi).")
    async def tanam(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with await get_db_connection() as db:
            user = await self.get_user_job_data(db, user_id)
            if user['role'] != "Petani": return await interaction.response.send_message("Bukan Petani!", ephemeral=True)

            if user['job_stage'] != "ready_to_plant":
                return await interaction.response.send_message("Tanah belum siap! Cangkul dulu.", ephemeral=True)

            # Consume Seed
            cursor = await db.execute("SELECT id FROM inventory WHERE user_id = ? AND item_name = 'Bibit Padi'", (user_id,))
            seed = await cursor.fetchone()
            if not seed:
                return await interaction.response.send_message("Kamu tidak punya Bibit Padi!", ephemeral=True)

            await db.execute("DELETE FROM inventory WHERE id = ?", (seed['id'],))

            await self.update_job_state(db, user_id, "growing", {"planted_at": time.time()})
            await interaction.response.send_message("🌱 Bibit ditanam. Jangan lupa disiram!")

    @app_commands.command(name="siram", description="[Petani] Menyiram tanaman.")
    async def siram(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with await get_db_connection() as db:
            user = await self.get_user_job_data(db, user_id)
            if user['job_stage'] != "growing":
                return await interaction.response.send_message("Tidak ada yang perlu disiram.", ephemeral=True)

            data = json.loads(user['job_data'])
            if data.get('watered'):
                return await interaction.response.send_message("Tanaman sudah basah.", ephemeral=True)

            data['watered'] = True
            await self.update_job_state(db, user_id, "growing", data)
            await interaction.response.send_message("💧 Tanaman disiram. Tunggu panen!")

    @app_commands.command(name="panen", description="[Petani] Memanen hasil.")
    async def panen(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with await get_db_connection() as db:
            user = await self.get_user_job_data(db, user_id)
            if user['job_stage'] != "growing":
                return await interaction.response.send_message("Belum ada tanaman.", ephemeral=True)

            data = json.loads(user['job_data'])
            if not data.get('watered'):
                await self.update_job_state(db, user_id, "idle")
                return await interaction.response.send_message("Tanaman mati karena tidak disiram! Cangkul ulang.", ephemeral=True)

            # Check time (e.g., 10 seconds for demo, real life would be hours)
            if time.time() - data['planted_at'] < 10:
                return await interaction.response.send_message("Tanaman belum matang! Tunggu sebentar.", ephemeral=True)

            # Reward
            xp = 50
            point = 100
            await db.execute("UPDATE users SET xp = xp + ?, point = point + ? WHERE id = ?", (xp, point, user_id))
            await self.update_job_state(db, user_id, "idle")

            await interaction.response.send_message(f"🚜 Panen Berhasil! Kamu dapat {xp} XP dan {point} Point.")

    # --- KOKI COMMANDS ---
    @app_commands.command(name="masak", description="[Koki] Mulai memasak (Butuh Panci & Bahan).")
    async def masak(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with await get_db_connection() as db:
            user = await self.get_user_job_data(db, user_id)
            if user['role'] != "Koki": return await interaction.response.send_message("Bukan Koki!", ephemeral=True)

            tool = await self.check_tool(db, user_id, "Panci")
            if not tool: return await interaction.response.send_message("Butuh Panci!", ephemeral=True)

            # Consume Ingredient
            cursor = await db.execute("SELECT id FROM inventory WHERE user_id = ? AND item_name = 'Bahan Masakan'", (user_id,))
            ing = await cursor.fetchone()
            if not ing: return await interaction.response.send_message("Butuh Bahan Masakan!", ephemeral=True)
            await db.execute("DELETE FROM inventory WHERE id = ?", (ing['id'],))

            await self.degrade_tool(db, tool['id'], 2)
            await self.update_job_state(db, user_id, "cooking", {"start_time": time.time()})
            await interaction.response.send_message("🍳 Mulai memasak... Tunggu matang!")

    @app_commands.command(name="hidangkan", description="[Koki] Hidangkan masakan.")
    async def hidangkan(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with await get_db_connection() as db:
            user = await self.get_user_job_data(db, user_id)
            if user['job_stage'] != "cooking": return await interaction.response.send_message("Kamu belum memasak.", ephemeral=True)

            data = json.loads(user['job_data'])
            elapsed = time.time() - data['start_time']

            if elapsed < 5:
                return await interaction.response.send_message("Masakan belum matang!", ephemeral=True)
            if elapsed > 60:
                 await self.update_job_state(db, user_id, "idle")
                 return await interaction.response.send_message("🔥 Masakan GOSONG! Kamu gagal.", ephemeral=True)

            xp, point = 40, 120
            await db.execute("UPDATE users SET xp = xp + ?, point = point + ? WHERE id = ?", (xp, point, user_id))
            await self.update_job_state(db, user_id, "idle")
            await interaction.response.send_message(f"🍲 Masakan Lezat! Terjual seharga {point} Point.")

    # --- PELATIH COMMANDS ---
    @app_commands.command(name="latih", description="[Pelatih] Melatih murid (Butuh waktu).")
    async def latih(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with await get_db_connection() as db:
            user = await self.get_user_job_data(db, user_id)
            if user['role'] != "Pelatih": return await interaction.response.send_message("Bukan Pelatih!", ephemeral=True)

            if user['job_stage'] != "idle":
                # Check completion
                data = json.loads(user['job_data'])
                if time.time() - data.get('start_time', 0) > 60: # 1 minute training
                    xp, point = 60, 150
                    await db.execute("UPDATE users SET xp = xp + ?, point = point + ? WHERE id = ?", (xp, point, user_id))
                    await self.update_job_state(db, user_id, "idle")
                    return await interaction.response.send_message(f"🏋️ Latihan Selesai! Murid berkembang pesat. (+{point} Point)")
                else:
                    return await interaction.response.send_message("Sedang melatih... Jangan diganggu.", ephemeral=True)

            await self.update_job_state(db, user_id, "training", {"start_time": time.time()})
            await interaction.response.send_message("🏋️ Mulai sesi latihan 1 menit...")

    # --- PANGERAN/PUTRI COMMANDS (ROYAL) ---
    @app_commands.command(name="pajak_rakyat", description="[Pangeran] Menarik upeti dari rakyat.")
    async def pajak_rakyat(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with await get_db_connection() as db:
            user = await self.get_user_job_data(db, user_id)
            if user['role'] != "Pangeran": return await interaction.response.send_message("Hanya Pangeran!", ephemeral=True)

            # Cooldown logic (store in job_data 'last_tax')
            data = json.loads(user['job_data'])
            last_tax = data.get('last_tax', 0)
            if time.time() - last_tax < 300: # 5 mins cooldown
                return await interaction.response.send_message("Rakyat masih miskin, tunggu sebentar lagi.", ephemeral=True)

            income = random.randint(500, 1000)
            data['last_tax'] = time.time()
            await db.execute("UPDATE users SET point = point + ? WHERE id = ?", (income, user_id))
            await self.update_job_state(db, user_id, "idle", data)

            await interaction.response.send_message(f"👑 Upeti ditarik! Kas kerajaan bertambah {income} Point.")

    @app_commands.command(name="diplomasi", description="[Putri] Melakukan diplomasi antar kerajaan.")
    async def diplomasi(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with await get_db_connection() as db:
            user = await self.get_user_job_data(db, user_id)
            if user['role'] != "Putri": return await interaction.response.send_message("Hanya Putri!", ephemeral=True)

            result = random.choice(["Sukses", "Gagal"])
            if result == "Sukses":
                reward = 300
                await db.execute("UPDATE users SET point = point + ?, xp = xp + 100 WHERE id = ?", (reward, user_id))
                await interaction.response.send_message(f"🕊️ Diplomasi Berhasil! Hubungan membaik. (+{reward} Point)")
            else:
                await interaction.response.send_message("💀 Diplomasi Gagal! Perang hampir terjadi.")

async def setup(bot):
    await bot.add_cog(Jobs(bot))
