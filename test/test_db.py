import asyncio
import selectors
import psycopg
from src.core.config import Config

async def main():
    c = Config()
    dsn = c.env("DATABASE_URL")
    print("DSN:", dsn)
    async with await psycopg.AsyncConnection.connect(dsn) as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT count(*) FROM nyc_neighborhoods")
            fila = await cur.fetchone()
            print("Barrios:", fila[0])

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())