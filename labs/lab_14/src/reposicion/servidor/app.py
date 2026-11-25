"""Servidor FastAPI de las bodegas de Mar y Huerta (material provisto).

Para levantarlo, desde la raíz del laboratorio:

    uv run uvicorn src.reposicion.servidor.app:app --port 8100

Es ficticio: los datos viven en memoria y no necesita internet ni credenciales.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.reposicion.servidor.datos import (
    BODEGAS,
    PRODUCTOS,
    filas_de_stock,
    normalizar,
)


class NuevaOrden(BaseModel):
    producto: str = Field(min_length=1)
    bodega: str = Field(min_length=1)
    proveedor: str = Field(min_length=1)
    cantidad: float = Field(gt=0)
    precio_unitario_clp: float | None = Field(default=None, ge=0)


def _producto_o_404(texto: str) -> str:
    clave = normalizar(texto)
    if clave not in PRODUCTOS:
        validos = ", ".join(PRODUCTOS)
        raise HTTPException(
            status_code=404,
            detail=f"El producto «{texto}» no existe. Productos válidos: {validos}.",
        )
    return clave


def _bodega_o_404(texto: str) -> str:
    clave = normalizar(texto)
    if clave not in BODEGAS:
        validas = ", ".join(BODEGAS)
        raise HTTPException(
            status_code=404,
            detail=f"La bodega «{texto}» no existe. Bodegas válidas: {validas}.",
        )
    return clave


def crear_app() -> FastAPI:
    """Crea una aplicación con las órdenes vacías (cada prueba usa la suya)."""
    app = FastAPI(title="Bodegas de Mar y Huerta")
    ordenes: list[dict] = []

    @app.get("/salud")
    def salud() -> dict:
        return {"estado": "ok"}

    @app.get("/bodegas")
    def bodegas() -> list[dict]:
        return [{"id": id_, **datos} for id_, datos in BODEGAS.items()]

    @app.get("/productos")
    def productos() -> list[dict]:
        return [
            {"id": id_, "nombre": p["nombre"], "unidad": p["unidad"]}
            for id_, p in PRODUCTOS.items()
        ]

    @app.get("/bodegas/{bodega}/stock")
    def stock_de_bodega(bodega: str) -> list[dict]:
        clave = _bodega_o_404(bodega)
        return [f for f in filas_de_stock() if f["bodega_id"] == clave]

    @app.get("/productos/{producto}/stock")
    def stock_de_producto(
        producto: str, bodega: str | None = None
    ) -> list[dict]:
        clave = _producto_o_404(producto)
        filas = [f for f in filas_de_stock() if f["producto_id"] == clave]
        if bodega is not None:
            clave_bodega = _bodega_o_404(bodega)
            filas = [f for f in filas if f["bodega_id"] == clave_bodega]
        return filas

    @app.post("/ordenes", status_code=201)
    def registrar_orden(orden: NuevaOrden) -> dict:
        producto = _producto_o_404(orden.producto)
        bodega = _bodega_o_404(orden.bodega)
        registro = {
            "orden_id": f"OC-{len(ordenes) + 1:04d}",
            **orden.model_dump(),
            "producto": producto,
            "bodega": bodega,
        }
        ordenes.append(registro)
        return registro

    @app.get("/ordenes")
    def listar_ordenes() -> list[dict]:
        return list(ordenes)

    return app


app = crear_app()
