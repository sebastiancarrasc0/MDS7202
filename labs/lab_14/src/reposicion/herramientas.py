"""Decorador de herramientas con resultado tipado (material provisto)."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel


def herramienta_tipada(funcion: Callable[..., BaseModel]) -> BaseTool:
    """Convierte una función que devuelve un modelo de Pydantic en una herramienta.

    Funciona como `@tool`, con una diferencia que importa: LangChain convertiría
    el modelo en un texto como `producto='merluza' cantidad=3.5`, difícil de leer
    para el modelo de lenguaje. Este decorador le entrega el **JSON** del modelo
    y conserva el objeto tipado como *artefacto* del mensaje de la herramienta,
    que es lo que lee la interfaz.
    """

    @wraps(funcion)
    def envoltura(*args: Any, **kwargs: Any) -> tuple[str, BaseModel]:
        resultado = funcion(*args, **kwargs)
        return resultado.model_dump_json(), resultado

    return tool(response_format="content_and_artifact")(envoltura)
