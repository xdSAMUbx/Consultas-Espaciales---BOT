import html
import logging
from .cliente_ia import ClienteIA
from ..sql.motor_sql import MotorConsultas
from ..sql.validador import validar_sql, ConsultaInsegura
from dataclasses import dataclass


logger = logging.getLogger(__name__)

MAX_FILAS_MOSTRADAS = 15

@dataclass
class Resultado:
    texto: str
    sql: str | None = None

class ServicioConsultas:
    def __init__(self, cliente_ia: ClienteIA, motor_sql: MotorConsultas):
        self.cliente_ia = cliente_ia
        self.motor_sql = motor_sql

    async def responder(self, pregunta: str) -> str:
        sql_generado = await self.cliente_ia.generar_sql(pregunta)
        logger.info("Pregunta: %s | SQL: %s", pregunta, sql_generado)

        if "CONSULTA_NO_SOPORTADA" in sql_generado:
            return "Esa pregunta no la puedo responder con los datos que tengo disponibles."

        try:
            sql_seguro = validar_sql(sql_generado)
        except ConsultaInsegura as e:
            logger.warning("Consulta rechazada: %s", e)
            return "No puedo ejecutar esa consulta de forma segura."

        try:
            filas = await self.motor_sql.ejecutar(sql_seguro)
        except Exception as e:
            logger.warning("Error ejecutando SQL: %s", e)
            return (
                "La consulta generada no se pudo ejecutar. Intenta reformular la pregunta.\n\n"
                f"<pre>{html.escape(sql_seguro)}</pre>"
            )

        return self._formatear(filas, sql_seguro)

    def _formatear(self, filas: list[dict]) -> str:
        if not filas:
            return "No encontré resultados."

        columnas = list(filas[0].keys())
        mostradas = filas[:MAX_FILAS_MOSTRADAS]

        if len(columnas) == 1:
            col = columnas[0]
            cuerpo = "\n".join(
                f"{i}. {html.escape(str(f[col]))}" for i, f in enumerate(mostradas, 1)
            )
        else:
            encabezado = " · ".join(f"<b>{html.escape(c)}</b>" for c in columnas)
            lineas = [
                f"{i}. " + " · ".join(html.escape(str(f[c])) for c in columnas)
                for i, f in enumerate(mostradas, 1)
            ]
            cuerpo = encabezado + "\n" + "\n".join(lineas)

        if len(filas) > MAX_FILAS_MOSTRADAS:
            cuerpo += f"\n\n<i>Mostrando {MAX_FILAS_MOSTRADAS} de {len(filas)} filas.</i>"

        return cuerpo

    async def responder(self, pregunta: str) -> Resultado:
        sql_generado = await self.cliente_ia.generar_sql(pregunta)
        logger.info("Pregunta: %s | SQL: %s", pregunta, sql_generado)

        if "CONSULTA_NO_SOPORTADA" in sql_generado:
            return Resultado("Esa pregunta no la puedo responder con los datos que tengo.")

        try:
            sql_seguro = validar_sql(sql_generado)
        except ConsultaInsegura as e:
            logger.warning("Consulta rechazada: %s", e)
            return Resultado("No puedo ejecutar esa consulta de forma segura.")

        try:
            filas = await self.motor_sql.ejecutar(sql_seguro)
        except Exception as e:
            logger.warning("Error ejecutando SQL: %s", e)
            return Resultado(
                "La consulta generada no se pudo ejecutar. Intenta reformular la pregunta.",
                sql_seguro,
            )

        tabla = self._formatear(filas)

        if not filas:
            return Resultado(tabla, sql_seguro)

        try:
            resumen = await self.cliente_ia.redactar_respuesta(pregunta, filas)
            texto = f"{resumen}\n\n{tabla}" if resumen else tabla
        except Exception:
            logger.warning("No se pudo redactar el resumen", exc_info=True)
            texto = tabla

        return Resultado(texto, sql_seguro)