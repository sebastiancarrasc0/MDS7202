"""Herramienta que consulta las reservas de las bodegas (material provisto).

Una reserva es lo que hay almacenado de un producto en una bodega: su cantidad, su
unidad, cuánto sale por día y para cuántos días alcanza.
"""

from typing import Annotated

import httpx
from pydantic import Field

from src.reposicion.contratos import (
    ErrorHerramienta,
    ReservaBodega,
    ReservasProducto,
)
from src.reposicion.herramientas import herramienta_tipada
from src.reposicion.servicios import obtener_cliente_api

Nombre = Annotated[
    str,
    Field(
        min_length=2,
        max_length=40,
        pattern=r"^[\w ]+$",
        description="Nombre sin símbolos.",
    ),
]


@herramienta_tipada
def consultar_reservas(
    producto: Nombre, bodega: Nombre | None = None
) -> ReservasProducto | ErrorHerramienta:
    """Consulta cuánto stock hay de un producto en las bodegas de Mar y Huerta.

    Úsala cuando la persona pregunte por reservas, stock o cobertura. `producto`
    es merluza, salmon, tomate, palta, lechuga, pollo, huevos o leche. `bodega`
    es opcional (lo_espejo, placilla, coronel o alerce): sin ella se consultan
    las cuatro. Devuelve la cantidad, la unidad y los días de cobertura de cada
    bodega. Es de solo lectura.
    """
    parametros = {"bodega": bodega} if bodega else {}
    try:
        respuesta = obtener_cliente_api().get(
            f"/productos/{producto}/stock", params=parametros
        )
    except httpx.HTTPError as error:
        return ErrorHerramienta(
            tipo="servicio_no_disponible",
            mensaje=f"No se pudo consultar la API de bodegas ({type(error).__name__}).",
        )
    if respuesta.status_code == 404:
        return ErrorHerramienta(
            tipo="no_encontrado", mensaje=respuesta.json()["detail"]
        )
    if respuesta.status_code >= 400:
        return ErrorHerramienta(
            tipo="servicio_no_disponible",
            mensaje=f"La API de bodegas respondió con el estado {respuesta.status_code}.",
        )
    filas = respuesta.json()
    if not filas:
        return ErrorHerramienta(
            tipo="sin_resultados", mensaje=f"Ninguna bodega tiene «{producto}»."
        )
    return ReservasProducto(
        producto=filas[0]["producto"],
        reservas=[ReservaBodega(**fila) for fila in filas],
    )
