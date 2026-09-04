from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

class MotorConsultas:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._pool: AsyncConnectionPool | None = None

    async def conectar(self):
        self._pool = AsyncConnectionPool(self.dsn, min_size=1, max_size=10, open=False)
        await self._pool.open(wait=True)

    async def cerrar(self):
        if self._pool:
            await self._pool.close()

    async def ejecutar(self, sql: str) -> list[dict]:
        if self._pool is None:
            raise RuntimeError("El pool no está inicializado")
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql)
                return await cur.fetchall()