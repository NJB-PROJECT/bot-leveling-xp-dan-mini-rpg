import discord
from discord import app_commands
from discord.ext import commands
import random
from database import get_db_connection

class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="serang", description="Serang user lain (PvP).")
    async def serang(self, interaction: discord.Interaction, target: discord.Member):
        if target.id == interaction.user.id:
            return await interaction.response.send_message("Jangan serang diri sendiri!", ephemeral=True)

        async with await get_db_connection() as db:
            # Get Attacker
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (interaction.user.id,))
            attacker = await cursor.fetchone()

            if not attacker:
                return await interaction.response.send_message("Kamu belum main! Ketik `/start` dulu.", ephemeral=True)

            # Get Defender
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (target.id,))
            defender = await cursor.fetchone()

            if not defender:
                return await interaction.response.send_message("Target belum main game ini!", ephemeral=True)

            # Calculate Power
            # However, simpler approach: we didn't duplicate stats into inventory, only durability.
            # We need to join inventory -> items.

            # Attacker Weapons
            cursor = await db.execute("""
                SELECT i.base_str, i.base_agi, i.base_int, i.base_luck, inv.id, inv.stats_mod
                FROM inventory inv
                JOIN items i ON inv.item_name = i.name
                WHERE inv.user_id = ? AND inv.is_equipped = 1 AND i.type = 'weapon'
            """, (attacker['id'],))
            att_weapons = await cursor.fetchall()

            weapon_bonus = 0
            for w in att_weapons:
                # Apply stats_mod (quality from refurbish)
                weapon_bonus += int(w['base_str'] * w['stats_mod'])
                # Reduce durability
                await db.execute("UPDATE inventory SET current_durability = current_durability - 2 WHERE id = ?", (w['id'],))

            # Defender Armor (assuming we had armor, but for now we check any equipped item providing stats)
            cursor = await db.execute("""
                SELECT i.base_str, i.base_agi, i.base_int, i.base_luck, inv.id, inv.stats_mod
                FROM inventory inv
                JOIN items i ON inv.item_name = i.name
                WHERE inv.user_id = ? AND inv.is_equipped = 1
            """, (defender['id'],))
            def_items = await cursor.fetchall()

            armor_bonus = 0
            for d in def_items:
                armor_bonus += int(d['base_agi'] * d['stats_mod'])
                # Reduce durability
                await db.execute("UPDATE inventory SET current_durability = current_durability - 1 WHERE id = ?", (d['id'],))

            # Cleanup broken items
            await db.execute("DELETE FROM inventory WHERE current_durability <= 0")

            att_power = attacker['str'] + weapon_bonus + random.randint(1, 10)
            def_power = defender['agi'] + defender['luck'] + armor_bonus + random.randint(1, 10)

            embed = discord.Embed(title="⚔️ PvP Battle", color=discord.Color.red())
            embed.add_field(name=f"{interaction.user.name}", value=f"Power: {att_power}\n(Weapon Bonus: +{weapon_bonus})", inline=True)
            embed.add_field(name=f"{target.name}", value=f"Defense: {def_power}\n(Armor Bonus: +{armor_bonus})", inline=True)

            if att_power > def_power:
                winnings = 20
                await db.execute("UPDATE users SET xp = xp + ? WHERE id = ?", (winnings, attacker['id']))
                embed.description = f"🏆 **{interaction.user.name} Menang!**\nMendapat {winnings} XP."
            else:
                embed.description = f"🛡️ **{target.name} Menahan Serangan!**\nPenyerang gagal."

            await db.commit()
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rampok", description="Rampok user lain (Butuh Lockpick & Skill).")
    async def rampok(self, interaction: discord.Interaction, target: discord.Member):
        if target.id == interaction.user.id:
            return await interaction.response.send_message("Gila ya?", ephemeral=True)

        async with await get_db_connection() as db:
            # Check Tool
            cursor = await db.execute("SELECT * FROM inventory WHERE user_id = ? AND item_name = 'Lockpick'", (interaction.user.id,))
            tool = await cursor.fetchone()

            if not tool:
                return await interaction.response.send_message("Kamu butuh **Lockpick** untuk merampok!", ephemeral=True)

            # Get Stats
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (interaction.user.id,))
            thief = await cursor.fetchone()
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (target.id,))
            victim = await cursor.fetchone()

            if not victim: return await interaction.response.send_message("Target miskin (belum main).", ephemeral=True)

            # Logic: (Crime Skill * 2) + Luck + Tool vs Victim Luck * 2 + Security (Safe)
            # Check if victim has Safe
            cursor = await db.execute("SELECT * FROM inventory WHERE user_id = ? AND item_name = 'Brankas Kecil'", (target.id,))
            safe = await cursor.fetchone()
            security = 50 if safe else 0

            crime_score = (thief['criminal_skill'] * 2) + thief['luck'] + random.randint(1, 20)
            defense_score = (victim['luck'] * 2) + security + random.randint(1, 20)

            # Tool usage
            await db.execute("UPDATE inventory SET current_durability = current_durability - 1 WHERE id = ?", (tool['id'],))
            await db.execute("DELETE FROM inventory WHERE id = ? AND current_durability <= 0", (tool['id'],))

            if crime_score > defense_score:
                stolen = int(victim['point'] * 0.10) # Steal 10%
                if stolen <= 0: stolen = 1

                await db.execute("UPDATE users SET point = point + ? WHERE id = ?", (stolen, thief['id']))
                await db.execute("UPDATE users SET point = point - ? WHERE id = ?", (stolen, victim['id']))
                await db.execute("UPDATE users SET criminal_skill = criminal_skill + 1 WHERE id = ?", (thief['id'],))

                await interaction.response.send_message(f"🕵️ **Perampokan Sukses!**\nKamu mencuri {stolen} Point dari {target.name}.\nSkill Kriminal naik!")
            else:
                fine = 50
                await db.execute("UPDATE users SET point = point - ? WHERE id = ?", (fine, thief['id']))
                await interaction.response.send_message(f"🚓 **Gagal! Polisi Datang!**\nKamu didenda {fine} Point.\nLockpick rusak sedikit.")

            await db.commit()

async def setup(bot):
    await bot.add_cog(Combat(bot))
