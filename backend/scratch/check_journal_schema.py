import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')
url = os.getenv('DATABASE_URL', '').replace('postgresql+asyncpg://', 'postgresql://')

async def main():
    conn = await asyncpg.connect(url)
    cols = await conn.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'journal_entries' ORDER BY ordinal_position")
    for c in cols:
        print(f"{c['column_name']}: {c['data_type']}")
    await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
