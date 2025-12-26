import asyncio
import os
import sys

# Add src to path so we can import database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import init_db, DB_PATH
import aiosqlite

async def test_db_structure():
    print("Running DB Init...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    await init_db()

    print("Verifying tables...")
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
            tables = [row[0] for row in await cursor.fetchall()]

        required_tables = ['users', 'inventory', 'market', 'items']
        for table in required_tables:
            if table in tables:
                print(f"[PASS] Table '{table}' exists.")
            else:
                print(f"[FAIL] Table '{table}' MISSING.")

        # Verify market init
        async with db.execute("SELECT * FROM market WHERE id=1") as cursor:
            market = await cursor.fetchone()
            if market:
                print(f"[PASS] Market initialized: Rate={market[1]}, Tax={market[3]}%")
            else:
                print("[FAIL] Market row missing.")

if __name__ == "__main__":
    asyncio.run(test_db_structure())
