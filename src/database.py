import aiosqlite
import os

DB_PATH = "data/rpg_bot.db"

# We export DB_PATH so Cogs can use aiosqlite.connect(DB_PATH) directly
# This prevents the "RuntimeError: threads can only be started once" caused by reusing connection objects incorrectly.

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Table: Users
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                role TEXT,
                xp INTEGER DEFAULT 0,
                point INTEGER DEFAULT 0,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                str INTEGER DEFAULT 1,
                agi INTEGER DEFAULT 1,
                intel INTEGER DEFAULT 1,
                luck INTEGER DEFAULT 1,
                criminal_skill INTEGER DEFAULT 0,
                job_stage TEXT DEFAULT 'idle',
                job_data TEXT DEFAULT '{}',
                last_job_time TIMESTAMP
            )
        """)

        # Table: Inventory
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                item_type TEXT,
                current_durability INTEGER,
                max_durability INTEGER,
                stats_mod REAL DEFAULT 1.0,
                is_equipped BOOLEAN DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        # Table: Market (Singleton for Exchange Rate)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS market (
                id INTEGER PRIMARY KEY,
                exchange_rate REAL DEFAULT 1.0,
                is_dynamic BOOLEAN DEFAULT 1,
                tax_rate INTEGER DEFAULT 5,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Initialize market row if not exists
        async with db.execute("SELECT id FROM market WHERE id = 1") as cursor:
            if not await cursor.fetchone():
                await db.execute("INSERT INTO market (id, exchange_rate, is_dynamic, tax_rate) VALUES (1, 1.0, 1, 5)")

        # Table: Items (Catalog)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                type TEXT,
                description TEXT,
                price INTEGER,
                base_str INTEGER DEFAULT 0,
                base_agi INTEGER DEFAULT 0,
                base_int INTEGER DEFAULT 0,
                base_luck INTEGER DEFAULT 0,
                base_durability INTEGER DEFAULT 100
            )
        """)

        # Seed some basic items if empty
        async with db.execute("SELECT id FROM items") as cursor:
            if not await cursor.fetchone():
                items_data = [
                    # Tools
                    ("Cangkul", "tool", "Alat untuk petani mengolah tanah.", 50, 0, 0, 0, 0, 50),
                    ("Panci", "tool", "Alat masak koki.", 50, 0, 0, 0, 0, 50),
                    ("Pedang Kayu", "weapon", "Senjata latihan.", 100, 5, 0, 0, 0, 100),
                    ("Lockpick", "criminal", "Alat pembobol kunci.", 200, 0, 2, 0, 5, 20),
                    # Consumables / Seeds
                    ("Bibit Padi", "seed", "Bibit untuk ditanam petani.", 10, 0, 0, 0, 0, 1),
                    ("Bahan Masakan", "ingredient", "Bahan mentah untuk koki.", 10, 0, 0, 0, 0, 1),
                    # Luxury
                    ("Brankas Kecil", "storage", "Menyimpan item aman di rumah.", 1000, 0, 0, 0, 0, 9999),
                ]
                await db.executemany("""
                    INSERT INTO items (name, type, description, price, base_str, base_agi, base_int, base_luck, base_durability)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, items_data)

        await db.commit()
        print("Database initialized successfully.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
