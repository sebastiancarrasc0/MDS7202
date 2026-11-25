"""Etapa 0: la herramienta de reservas consulta la API y devuelve modelos."""

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.reposicion import servicios
from src.reposicion.contratos import ErrorHerramienta, ReservasProducto
from src.reposicion.herramienta_reservas import consultar_reservas

from .conftest import ejecutar

pytestmark = pytest.mark.etapa0


def test_consultar_un_producto_en_todas_las_bodegas(
    api_en_servicios: TestClient,
):
    resultado = ejecutar(consultar_reservas, producto="merluza")
    assert isinstance(resultado, ReservasProducto)
    assert resultado.producto == "Merluza austral"
    assert {r.bodega for r in resultado.reservas} == {
        "Lo Espejo",
        "Placilla",
        "Coronel",
        "Alerce",
    }


def test_consultar_una_bodega_trae_solo_esa_bodega(
    api_en_servicios: TestClient,
):
    resultado = ejecutar(
        consultar_reservas, producto="merluza", bodega="coronel"
    )
    assert isinstance(resultado, ReservasProducto)
    assert [r.bodega for r in resultado.reservas] == ["Coronel"]
    assert resultado.reservas[0].dias_cobertura == pytest.approx(1.5)


def test_un_producto_desconocido_es_un_error_legible(
    api_en_servicios: TestClient,
):
    resultado = ejecutar(consultar_reservas, producto="caviar")
    assert isinstance(resultado, ErrorHerramienta)
    assert resultado.tipo == "no_encontrado"
    assert "caviar" in resultado.mensaje


def test_el_contenido_que_lee_el_modelo_es_json(api_en_servicios: TestClient):
    mensaje = consultar_reservas.invoke(
        {
            "name": "consultar_reservas",
            "args": {"producto": "salmon"},
            "id": "t1",
            "type": "tool_call",
        }
    )
    assert ReservasProducto.model_validate_json(mensaje.content).reservas


def test_una_api_caida_devuelve_un_error_tipado_y_no_una_excepcion():
    def caida(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin conexión")

    servicios.configurar(
        cliente_api=httpx.Client(
            base_url="http://bodegas.test", transport=httpx.MockTransport(caida)
        )
    )
    resultado = ejecutar(consultar_reservas, producto="merluza")
    assert isinstance(resultado, ErrorHerramienta)
    assert resultado.tipo == "servicio_no_disponible"


def test_un_estado_de_error_de_la_api_se_informa():
    servicios.configurar(
        cliente_api=httpx.Client(
            base_url="http://bodegas.test",
            transport=httpx.MockTransport(lambda p: httpx.Response(500)),
        )
    )
    resultado = ejecutar(consultar_reservas, producto="merluza")
    assert isinstance(resultado, ErrorHerramienta)
    assert "500" in resultado.mensaje


def test_si_la_api_no_trae_datos_no_se_inventan():
    servicios.configurar(
        cliente_api=httpx.Client(
            base_url="http://bodegas.test",
            transport=httpx.MockTransport(
                lambda p: httpx.Response(200, json=[])
            ),
        )
    )
    resultado = ejecutar(consultar_reservas, producto="merluza")
    assert isinstance(resultado, ErrorHerramienta)
    assert resultado.tipo == "sin_resultados"


@pytest.mark.parametrize("texto", ["../ordenes", "merluza?x=1", "a", "x" * 41])
def test_la_entrada_se_limita_con_tipos_y_limites(
    api_en_servicios: TestClient, texto: str
):
    with pytest.raises(ValidationError):
        ejecutar(consultar_reservas, producto=texto)
