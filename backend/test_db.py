import asyncio
from sqlalchemy import text
from app.database import engine


async def test_connection():
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            print("DATABASE CONNECTION SUCCESS:", result.scalar())
    except Exception as e:
        print("DATABASE CONNECTION FAILED:")
        print(e)
    finally:
        await engine.dispose()


asyncio.run(test_connection())