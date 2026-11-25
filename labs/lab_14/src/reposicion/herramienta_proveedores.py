"""Herramienta que busca proveedores en la web con Tavily (la escribe el equipo)."""

from typing import Annotated

from pydantic import Field

from src.reposicion.contratos import (
    ErrorHerramienta,
    ResultadoBusqueda,
)
from src.reposicion.herramientas import herramienta_tipada

# Su código aquí: agreguen a `Field` el largo mínimo (2) y máximo (60) y el patrón.
Texto = Annotated[str, Field(description="Sin símbolos.")]


@herramienta_tipada  # Ya viene decorada: no la quiten.
def buscar_proveedores(
    producto: Texto, region: Texto
) -> ResultadoBusqueda | ErrorHerramienta:
    # Su código aquí: reescriban este docstring. Es lo que el modelo lee para
    # decidir cuándo usar la herramienta y con qué argumentos.
    """Busca proveedores."""
    raise NotImplementedError(
        "Completen buscar_proveedores antes de ejecutar esta celda."
    )
