"""El agente de logística alimentaria (lo escribe el equipo)."""

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel


def crear_agente(
    modelo: BaseChatModel | None = None, checkpointer: Any = None
) -> Any:
    """Arma el agente con sus herramientas, su respuesta estructurada y la
    pausa en que Pilar elige el proveedor antes de enviar la solicitud a compras.

    Se completa por etapas: en la etapa 1 con la herramienta de reservas; en la
    2 se suma la de políticas; en la 3, la de proveedores, y en la 4, el envío de
    la solicitud de compra con la pausa en que Pilar elige el proveedor. Con `modelo=None` usa el
    modelo del `.env`, y sin `checkpointer` usa `crear_checkpointer()`.
    """
    raise NotImplementedError(
        "Completen crear_agente antes de ejecutar esta celda."
    )
