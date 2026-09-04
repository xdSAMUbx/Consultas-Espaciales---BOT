from pathlib import Path
from typing import Any
import yaml, os
from dotenv import dotenv_values

class Config:

    YAML_DIALOGOS = Path(__file__).parent.parent / 'dialogos.yml'
    TOKEN_PATH = Path(__file__).parent.parent.parent
    ENV_FILE = TOKEN_PATH / '.env'
    _datos: dict | None = None
    _env: dict[str, str | None] | None = None

    def __init__(self, path_env: Path | None = None):
        self.env_path = path_env if path_env is not None else self.ENV_FILE
        self._load_env()

    def _load_env(self):
        if self.env_path.exists():
            Config._env = dict(dotenv_values(self.env_path))
        else:
            Config._env = {}

    def env(self, clave: str, default: str | None = None) -> str | None:
        if Config._env is None:
            Config._env = {}
        # primero el .env (desarrollo local), luego el entorno (contenedor)
        valor = Config._env.get(clave) or os.getenv(clave) or default
        if valor is None:
            raise RuntimeError(f"Falta la variable '{clave}'")
        return valor

    @classmethod
    def _asegurar_carga(cls, path_yaml: Path | None = None):
        if cls._datos is None:
            ruta = path_yaml or cls.YAML_DIALOGOS
            with open(ruta, encoding="utf-8") as f:
                cls._datos = yaml.safe_load(f)

    @classmethod
    def get(cls, clave: str, **kwargs) -> str:
        cls._asegurar_carga()
        if cls._datos is None:
            raise RuntimeError("No se cargaron los datos.")

        valor: Any = cls._datos
        for parte in clave.split("."):
            valor = valor[parte]

        if not isinstance(valor, str):
            raise TypeError(f"La clave '{clave}' no apunta a un texto, apunta a: {type(valor)}")

        return valor.format(**kwargs) if kwargs else valor