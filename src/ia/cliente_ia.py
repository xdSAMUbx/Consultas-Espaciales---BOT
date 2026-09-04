import logging
from openai import AsyncOpenAI
from .prompts import Prompts

logger = logging.getLogger(__name__)

class ClienteIA:
    def __init__(self, api_key: str, modelo: str, base_url: str | None = None,
                 esquema: str = "esquema_nyc"):
        self.modelo = modelo
        self.esquema = esquema
        self.cliente = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generar_sql(self, pregunta: str) -> str:
        respuesta = await self.cliente.chat.completions.create(
            model=self.modelo,
            messages=[
                {"role": "system", "content": Prompts.sistema(self.esquema)},
                {"role": "user", "content": pregunta},
            ],
            temperature=0,
        )
        contenido = respuesta.choices[0].message.content
        if not contenido:
            raise RuntimeError("El modelo no devolvió respuesta")
        return self._limpiar(contenido)

    @staticmethod
    def _limpiar(texto: str) -> str:
        texto = texto.strip()
        if texto.startswith("```"):
            lineas = [l for l in texto.split("\n") if not l.strip().startswith("```")]
            texto = "\n".join(lineas)
        return texto.strip().rstrip(";").strip()

    async def redactar_respuesta(self, pregunta: str, filas: list[dict]) -> str:
        import json
        datos = json.dumps(filas[:30], ensure_ascii=False, default=str)
        respuesta = await self.cliente.chat.completions.create(
            model=self.modelo,
            messages=[
                {"role": "system", "content": (
                    "Redactas respuestas breves en español a partir de resultados de una consulta.\n"
                    "- Máximo 3 frases. Responde la pregunta directamente.\n"
                    "- Menciona las cifras relevantes, no listes todo.\n"
                    "- Sin markdown, sin saludos, sin ofrecer más ayuda."
                )},
                {"role": "user", "content": f"Pregunta: {pregunta}\n\nResultados: {datos}"},
            ],
            temperature=0.3,
        )
        return (respuesta.choices[0].message.content or "").strip()