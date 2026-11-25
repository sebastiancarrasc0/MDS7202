"""Dónde se obtienen los servicios que usan las herramientas (material provisto).

Las herramientas piden aquí el cliente de la API, la base vectorial, la búsqueda
y el registro de órdenes. Así una prueba puede reemplazarlos por versiones
simuladas con `configurar(...)` sin cambiar el código del equipo.
"""

from functools import lru_cache
from typing import Any

import httpx

from src.reposicion.config import get_settings

_REEMPLAZOS: dict[str, Any] = {}


def configurar(**reemplazos: Any) -> None:
    """Reemplaza servicios: `cliente_api`, `coleccion`, `busqueda`, `registro`."""
    _REEMPLAZOS.update(reemplazos)


def reiniciar() -> None:
    """Quita los reemplazos y olvida lo que se había creado."""
    _REEMPLAZOS.clear()
    _cliente_api.cache_clear()
    _coleccion.cache_clear()
    _busqueda.cache_clear()


@lru_cache
def _cliente_api() -> httpx.Client:
    return httpx.Client(base_url=get_settings().url_api_bodegas, timeout=5)


@lru_cache
def _coleccion() -> Any:
    from src.reposicion.modelos_llm import crear_embeddings
    from src.reposicion.rag import abrir_coleccion

    return abrir_coleccion(get_settings(), crear_embeddings())


@lru_cache
def _busqueda() -> Any:
    settings = get_settings()
    if settings.modo == "simulado":
        from src.reposicion.simulacion import BusquedaSimulada

        return BusquedaSimulada()
    from langchain_tavily import TavilySearch

    llave = settings.tavily_api_key
    return TavilySearch(
        max_results=5,
        tavily_api_key=llave.get_secret_value() if llave else None,
    )


def obtener_cliente_api() -> httpx.Client:
    return _REEMPLAZOS.get("cliente_api") or _cliente_api()


def obtener_coleccion() -> Any:
    return _REEMPLAZOS.get("coleccion") or _coleccion()


def obtener_cliente_busqueda() -> Any:
    return _REEMPLAZOS.get("busqueda") or _busqueda()


def obtener_registro_ordenes() -> Any | None:
    """Registro simulado de órdenes, o `None` para escribir en la API real."""
    return _REEMPLAZOS.get("registro")
