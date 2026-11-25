"""Solicitud de compra al área de compras, la acción sensible (material provisto).

El agente no elige el proveedor: el middleware de aprobación humana detiene la
llamada y Pilar elige uno de los tres resultados de la búsqueda. Además valida en
código, sin confiar en el modelo.
"""

import httpx

from src.reposicion.contratos import ErrorHerramienta, OrdenRegistrada
from src.reposicion.herramienta_reservas import Nombre
from src.reposicion.herramientas import herramienta_tipada
from src.reposicion.servicios import (
    obtener_cliente_api,
    obtener_registro_ordenes,
)
from src.reposicion.servidor.datos import MONTO_VISACION_GERENCIA_CLP


@herramienta_tipada
def registrar_orden_reposicion(
    producto: Nombre,
    bodega: Nombre,
    cantidad: float,
    proveedor: str | None = None,
    precio_unitario_clp: float | None = None,
) -> OrdenRegistrada | ErrorHerramienta:
    """Genera la solicitud de compra al área de compras de Mar y Huerta.

    Úsala solo después de `buscar_proveedores`, pasando únicamente `producto` y
    `bodega` (por ejemplo `merluza` y `coronel`) y la `cantidad` que corresponde
    según la política. No elijas `proveedor` ni `precio_unitario_clp`: Pilar elige
    el proveedor entre los resultados de la búsqueda antes de que la solicitud se
    envíe, y el área de compras se pondrá en contacto con él.
    """
    if proveedor is None or not proveedor.strip():
        return ErrorHerramienta(
            tipo="entrada_invalida",
            mensaje="Falta que Pilar elija un proveedor.",
        )
    if cantidad <= 0:
        return ErrorHerramienta(
            tipo="entrada_invalida",
            mensaje="La cantidad debe ser mayor que cero.",
        )
    if precio_unitario_clp is not None:
        monto = cantidad * precio_unitario_clp
        if monto > MONTO_VISACION_GERENCIA_CLP:
            return ErrorHerramienta(
                tipo="entrada_invalida",
                mensaje=(
                    f"La solicitud suma ${monto:,.0f} y supera los "
                    f"${MONTO_VISACION_GERENCIA_CLP:,.0f} que se pueden enviar "
                    "sin la visación de la gerencia de abastecimiento."
                ).replace(",", "."),
            )
    cuerpo = {
        "producto": producto,
        "bodega": bodega,
        "proveedor": proveedor.strip(),
        "cantidad": cantidad,
        "precio_unitario_clp": precio_unitario_clp,
    }
    simulado = obtener_registro_ordenes()
    if simulado is not None:
        registro = simulado.registrar(cuerpo)
    else:
        try:
            respuesta = obtener_cliente_api().post("/ordenes", json=cuerpo)
        except httpx.HTTPError as error:
            return ErrorHerramienta(
                tipo="servicio_no_disponible",
                mensaje=f"No se pudo enviar la solicitud ({type(error).__name__}).",
            )
        if respuesta.status_code >= 400:
            detalle = respuesta.json().get("detail", respuesta.status_code)
            return ErrorHerramienta(
                tipo="entrada_invalida",
                mensaje=f"La API rechazó la solicitud: {detalle}",
            )
        registro = respuesta.json()
    return OrdenRegistrada(
        orden_id=registro["orden_id"],
        producto=registro["producto"],
        bodega=registro["bodega"],
        proveedor=cuerpo["proveedor"],
        cantidad=cantidad,
        precio_unitario_clp=precio_unitario_clp,
    )
