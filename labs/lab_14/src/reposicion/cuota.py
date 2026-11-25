"""Cuota diaria de OpenRouter y mensajes de error claros (material provisto)."""

import httpx
from pydantic import BaseModel, Field

from src.reposicion.config import Settings


class Cuota(BaseModel):
    """Solicitudes a modelos gratuitos del día (UTC), según OpenRouter."""

    usadas: int = Field(ge=0)
    limite: int = Field(ge=0)

    @property
    def restantes(self) -> int:
        return max(self.limite - self.usadas, 0)


def _extraer(cuerpo: dict) -> Cuota | None:
    datos = cuerpo.get("data", cuerpo)
    diario = datos.get("free_model_daily_requests")
    if not isinstance(diario, dict):
        return None
    usadas, limite = diario.get("used"), diario.get("limit")
    if usadas is None or limite is None:
        return None
    return Cuota(usadas=int(usadas), limite=int(limite))


def consultar_cuota(
    settings: Settings, cliente: httpx.Client | None = None
) -> Cuota | None:
    """Pide a OpenRouter cuántas solicitudes gratuitas se usaron hoy.

    Devuelve `None` si no hay llave, si falla la red o si la respuesta no trae
    el dato: la cuota es una ayuda y nunca debe romper la interfaz.
    """
    if settings.openrouter_api_key is None:
        return None
    llave = settings.openrouter_api_key.get_secret_value()
    propio = cliente is None
    cliente = cliente or httpx.Client(timeout=5)
    try:
        respuesta = cliente.get(
            f"{settings.url_openrouter.rstrip('/')}/key",
            headers={"Authorization": f"Bearer {llave}"},
        )
        respuesta.raise_for_status()
        return _extraer(respuesta.json())
    except (httpx.HTTPError, ValueError):
        return None
    finally:
        if propio:
            cliente.close()


def traducir_error(error: Exception) -> str:
    """Convierte un error del proveedor en un mensaje que el equipo entienda."""
    estado = getattr(error, "status_code", None)
    if estado == 429 and "Provider returned error" in str(error):
        return (
            "El proveedor del modelo gratuito, no OpenRouter, rechazó la "
            "solicitud porque el modelo está saturado: es un límite del modelo, "
            "compartido con todos sus usuarios, y no de su cuenta. Reintenten en "
            "un minuto o cambien MODELO_CHAT en su archivo .env por otro modelo "
            "gratuito."
        )
    if estado == 429:
        return (
            "OpenRouter rechazó la solicitud por el límite de uso: los modelos "
            "gratuitos permiten 20 solicitudes por minuto y 50 por día por cuenta. "
            "Esperen un minuto; si ya se agotó el día, la cuota se renueva a "
            "medianoche UTC (21:00 hora de Chile en verano). Mientras tanto "
            "pueden seguir en modo simulado."
        )
    if estado in (401, 403):
        return (
            "OpenRouter no aceptó la llave. Revisen OPENROUTER_API_KEY en su "
            "archivo .env."
        )
    return f"No se pudo consultar el modelo ({type(error).__name__}): {error}"
