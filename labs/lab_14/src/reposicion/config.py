"""Configuración del laboratorio: variables de entorno y archivo `.env`.

Material provisto. Las llaves son `SecretStr`: no salen al imprimir el objeto.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def raiz_del_laboratorio() -> Path:
    """La carpeta del proyecto, la que tiene `.env` y `data/`.

    No depende de desde dónde se ejecute. `REPOSICION_RAIZ` la reemplaza; las
    pruebas la usan para no leer el `.env` de quien las ejecuta.
    """
    return Path(
        os.environ.get("REPOSICION_RAIZ") or Path(__file__).resolve().parents[2]
    )


class ErrorConfiguracion(RuntimeError):
    """Falta una llave o una variable que el modo real necesita."""


class Settings(BaseSettings):
    """Todo lo que cambia entre un computador y otro, con valores por defecto.

    Se lee del entorno y del archivo `.env` de la raíz del laboratorio (el entorno
    manda). Una variable vacía cuenta como ausente. Las carpetas por omisión
    también cuelgan de la raíz: así el notebook, que corre desde `notebooks/`, y
    la interfaz, que corre desde la raíz, comparten la misma base y el mismo caché.
    """

    model_config = SettingsConfigDict(
        env_ignore_empty=True,
        extra="ignore",
        populate_by_name=True,
    )

    openrouter_api_key: SecretStr | None = None
    tavily_api_key: SecretStr | None = None
    modelo_chat: str = "google/gemma-4-31b-it:free"
    modelo_embeddings: str = "nvidia/nemotron-3.5-embed-1b:free"
    url_openrouter: str = "https://openrouter.ai/api/v1"
    url_api_bodegas: str = "http://127.0.0.1:8100"
    url_phoenix: str = "http://localhost:6006"
    directorio_politicas: Path = Field(
        default_factory=lambda: raiz_del_laboratorio() / "data/raw/politicas"
    )
    directorio_chroma: Path = Field(
        default_factory=lambda: raiz_del_laboratorio() / "data/processed/chroma"
    )
    directorio_cache: Path = Field(
        default_factory=lambda: raiz_del_laboratorio() / ".cache"
    )
    usar_cache: bool = True
    # Distancia coseno máxima para considerar relevante un fragmento.
    distancia_maxima: float = 0.75
    modo: Literal["real", "simulado"] = Field(
        default="real", validation_alias="REPOSICION_MODO"
    )

    @property
    def endpoint_phoenix(self) -> str:
        return f"{self.url_phoenix.rstrip('/')}/v1/traces"


@lru_cache
def get_settings() -> Settings:
    """Lee la configuración una sola vez y la reutiliza."""
    return Settings(_env_file=raiz_del_laboratorio() / ".env")  # pyright: ignore[reportCallIssue]


def llaves_faltantes(settings: Settings) -> list[str]:
    """Nombres de las variables de llave que faltan para el modo real."""
    faltan = []
    if settings.openrouter_api_key is None:
        faltan.append("OPENROUTER_API_KEY")
    if settings.tavily_api_key is None:
        faltan.append("TAVILY_API_KEY")
    return faltan
