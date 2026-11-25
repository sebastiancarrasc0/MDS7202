"""Ayudas para pausar y reanudar una aprobación humana (material provisto).

El middleware de aprobación detiene la ejecución antes de la acción sensible y
guarda el estado en el punto de control. Estas funciones leen la pausa y la
reanudan con la decisión de una persona; las usan la interfaz y las pruebas.
"""

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.types import Command
from pydantic import BaseModel


class AccionPendiente(BaseModel):
    """Una acción que espera la decisión de una persona."""

    nombre: str
    argumentos: dict[str, Any]
    descripcion: str = ""


def crear_checkpointer() -> InMemorySaver:
    """Punto de control en memoria que guarda el estado de cada conversación.

    Declara los modelos de Pydantic que se guardan en él (la respuesta final del
    agente), para que LangGraph no avise que lee un tipo no registrado.
    """
    serde = JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("src.reposicion.contratos", "RespuestaAgente")
        ]
    )
    return InMemorySaver(serde=serde)


def configuracion_hilo(thread_id: str) -> dict[str, Any]:
    """Configuración que identifica una conversación en el punto de control."""
    return {"configurable": {"thread_id": thread_id}}


def pausa_pendiente(agente: Any, thread_id: str) -> list[AccionPendiente]:
    """Acciones que esperan aprobación en esta conversación (vacía si no hay)."""
    estado = agente.get_state(configuracion_hilo(thread_id))
    interrupciones = getattr(estado, "interrupts", ())
    if not interrupciones:
        return []
    return [
        AccionPendiente(
            nombre=accion["name"],
            argumentos=accion["args"],
            descripcion=accion.get("description", ""),
        )
        for accion in interrupciones[0].value["action_requests"]
    ]


def decision_editar(nombre: str, argumentos: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "edit",
        "edited_action": {"name": nombre, "args": argumentos},
    }


def decision_rechazar(motivo: str) -> dict[str, Any]:
    return {"type": "reject", "message": motivo}


def validar_edicion(argumentos: dict[str, Any]) -> str | None:
    """Revisa una elección antes de reanudar: devuelve el error o `None` si sirve."""
    if not str(argumentos.get("proveedor") or "").strip():
        return "proveedor: elijan un proveedor."
    cantidad = argumentos.get("cantidad")
    if cantidad is None or cantidad <= 0:
        return "cantidad: debe ser mayor que cero."
    precio = argumentos.get("precio_unitario_clp")
    if precio is not None and precio < 0:
        return "precio_unitario_clp: no puede ser negativo."
    return None


def reanudar(
    agente: Any, thread_id: str, decisiones: list[dict[str, Any]]
) -> dict[str, Any]:
    """Reanuda la ejecución pausada con una decisión por cada acción pendiente."""
    return agente.invoke(
        Command(resume={"decisions": decisiones}),
        config=configuracion_hilo(thread_id),
    )
