from telegram.ext import ContextTypes
from enum import Enum, auto

class Estado(Enum):
    ESPERANDO_NOMBRE = auto()
    EN_MENU = auto()

class Sesion:
    def __init__(self, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data is None:
            raise RuntimeError("No se obtuvo el estado actual")
        self._data = context.user_data
        
    @property
    def estado(self) -> Estado | None:
        valor = self._data.get("estado")
        return Estado(valor) if valor is not None else None

    @estado.setter
    def estado(self, nuevo: Estado):
        self._data["estado"] = nuevo.value

    @property
    def nombre(self) -> str | None:
        return self._data.get("nombre")

    @nombre.setter
    def nombre(self, valor:str):
        self._data["nombre"] = valor

    def limpiar(self):
        self._data.clear()

    def cerrar_sesion(self):
        self._data.pop("estado", None)

    def olvidar(self):
        self._data.clear()

    @property
    def ultimo_sql(self) -> str | None:
        return self._data.get("ultimo_sql")

    @ultimo_sql.setter
    def ultimo_sql(self, valor: str):
        self._data["ultimo_sql"] = valor