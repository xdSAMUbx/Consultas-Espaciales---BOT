from pathlib import Path

class Prompts:
    DIR = Path(__file__).parent.parent.parent / "prompts"
    _cache: dict[str, str] = {}

    @classmethod
    def cargar(cls, nombre:str) -> str:
        if nombre not in cls._cache:
            ruta = cls.DIR / f"{nombre}.md"
            cls._cache[nombre] = ruta.read_text(encoding="utf-8")
        return cls._cache[nombre]

    @classmethod
    def sistema(cls, esquema_nombre: str = "esquema_nyc") -> str:
        plantilla = cls.cargar("sistema")
        esquema = cls.cargar(esquema_nombre)
        return plantilla.format(esquema=esquema)