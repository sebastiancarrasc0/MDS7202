"""Trazabilidad con Arize Phoenix.

`registrar_trazas` es la pieza que el equipo escribe en la etapa 0. El resto es
material provisto: avisa si Phoenix no está encendido en vez de fallar.
"""

import httpx

from src.reposicion.config import Settings


def registrar_trazas(proyecto: str, endpoint: str):
    """Conecta LangChain con Phoenix: cada llamada queda como una traza."""
    raise NotImplementedError(
        "Completen registrar_trazas antes de ejecutar esta celda."
    )


def phoenix_activo(url: str) -> bool:
    """Indica si el servidor de Phoenix responde en `url`."""
    try:
        return httpx.get(url, timeout=1.5).status_code < 500
    except httpx.HTTPError:
        return False


def activar_trazas(settings: Settings, proyecto: str = "lab14") -> str | None:
    """Enciende las trazas. Devuelve un aviso si no pudo, o `None` si todo bien.

    Una falla de la trazabilidad no debe impedir que el agente responda.
    """
    if not phoenix_activo(settings.url_phoenix):
        return (
            "Phoenix no está en ejecución: las trazas no se están registrando. "
            "Enciéndanlo con `uv run phoenix serve` en otra terminal."
        )
    try:
        registrar_trazas(proyecto, settings.endpoint_phoenix)
    except Exception as error:
        return f"No se pudieron registrar las trazas ({error})."
    return None
