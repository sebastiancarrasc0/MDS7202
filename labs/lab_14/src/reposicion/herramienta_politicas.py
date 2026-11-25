"""Herramienta que consulta las políticas internas (la escribe el equipo)."""

from typing import Annotated

from pydantic import Field

from src.reposicion.contratos import (
    ErrorHerramienta,
    RespuestaPoliticas,
)
from src.reposicion.herramientas import herramienta_tipada

# Su código aquí: agreguen a `Field` el largo mínimo (3) y máximo (200).
Consulta = Annotated[str, Field(description="Texto de la consulta.")]


@herramienta_tipada  # Ya viene decorada: no la quiten.
def buscar_politicas(
    consultas: Annotated[list[Consulta], Field(min_length=1, max_length=5)],
) -> RespuestaPoliticas | ErrorHerramienta:
    # Su código aquí: reescriban este docstring. Es lo que el modelo lee para
    # decidir cuándo usar la herramienta y con qué argumentos.
    """Busca políticas."""
    raise NotImplementedError(
        "Completen buscar_politicas antes de ejecutar esta celda."
    )
