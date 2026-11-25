"""Etapa 0: el servidor de bodegas entrega datos reproducibles y errores claros."""

import pytest
from fastapi.testclient import TestClient

from src.reposicion.servidor.datos import PRODUCTOS, filas_de_stock

pytestmark = pytest.mark.etapa0


def test_los_datos_son_identicos_entre_dos_lecturas():
    assert filas_de_stock() == filas_de_stock()


def test_hay_al_menos_cuatro_bodegas_y_ocho_productos(
    cliente_api: TestClient,
):
    assert len(cliente_api.get("/bodegas").json()) >= 4
    assert len(cliente_api.get("/productos").json()) >= 8


def test_el_stock_de_un_producto_lista_cada_bodega_que_lo_tiene(
    cliente_api: TestClient,
):
    filas = cliente_api.get("/productos/merluza/stock").json()
    assert {f["bodega_id"] for f in filas} == {
        "lo_espejo",
        "placilla",
        "coronel",
        "alerce",
    }
    for fila in filas:
        assert {
            "cantidad",
            "unidad",
            "consumo_diario",
            "dias_cobertura",
        } <= set(fila)


def test_la_cobertura_es_el_stock_dividido_por_el_consumo(
    cliente_api: TestClient,
):
    fila = cliente_api.get("/productos/merluza/stock?bodega=coronel").json()[0]
    assert fila["dias_cobertura"] == pytest.approx(
        fila["cantidad"] / fila["consumo_diario"], abs=0.01
    )


def test_el_stock_de_una_bodega_trae_sus_productos(cliente_api: TestClient):
    filas = cliente_api.get("/bodegas/alerce/stock").json()
    assert filas
    assert {f["bodega_id"] for f in filas} == {"alerce"}


def test_los_nombres_se_normalizan(cliente_api: TestClient):
    assert cliente_api.get("/productos/Salmón/stock").status_code == 200
    assert cliente_api.get("/bodegas/Lo Espejo/stock").status_code == 200


@pytest.mark.parametrize(
    ("ruta", "nombre"),
    [
        ("/bodegas/antofagasta/stock", "antofagasta"),
        ("/productos/caviar/stock", "caviar"),
    ],
)
def test_una_entidad_inexistente_responde_404_con_su_nombre(
    cliente_api: TestClient, ruta: str, nombre: str
):
    respuesta = cliente_api.get(ruta)
    assert respuesta.status_code == 404
    assert nombre in respuesta.json()["detail"]


def test_los_datos_producen_un_caso_por_escenario():
    """Una reposición necesaria, una al límite y un producto sin necesidad."""
    cobertura = {
        (f["producto_id"], f["bodega_id"]): f["dias_cobertura"]
        for f in filas_de_stock()
    }
    assert cobertura[("merluza", "coronel")] < PRODUCTOS["merluza"]["minima"]
    assert cobertura[("tomate", "placilla")] == PRODUCTOS["tomate"]["minima"]
    assert all(
        d >= PRODUCTOS["leche"]["minima"]
        for (producto, _), d in cobertura.items()
        if producto == "leche"
    )


def test_registrar_una_orden_la_deja_en_la_lista(cliente_api: TestClient):
    cuerpo = {
        "producto": "merluza",
        "bodega": "coronel",
        "proveedor": "Pesquera Austral",
        "cantidad": 300,
        "precio_unitario_clp": 4200,
    }
    respuesta = cliente_api.post("/ordenes", json=cuerpo)
    assert respuesta.status_code == 201
    assert respuesta.json()["orden_id"] == "OC-0001"
    assert (
        cliente_api.get("/ordenes").json()[0]["proveedor"] == "Pesquera Austral"
    )


@pytest.mark.parametrize(
    ("cambio", "estado"),
    [
        ({"cantidad": -5}, 422),
        ({"proveedor": ""}, 422),
        ({"producto": "caviar"}, 404),
        ({"bodega": "antofagasta"}, 404),
    ],
)
def test_una_orden_invalida_no_se_registra(
    cliente_api: TestClient, cambio: dict, estado: int
):
    cuerpo = {
        "producto": "merluza",
        "bodega": "coronel",
        "proveedor": "Pesquera Austral",
        "cantidad": 300,
    } | cambio
    assert cliente_api.post("/ordenes", json=cuerpo).status_code == estado
    assert cliente_api.get("/ordenes").json() == []
