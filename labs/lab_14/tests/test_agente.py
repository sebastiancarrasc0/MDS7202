"""Etapa 1: el agente mínimo usa la herramienta de reservas y responde tipado."""

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import SystemMessage, ToolMessage

from src.reposicion.agente import crear_agente
from src.reposicion.contratos import ErrorHerramienta, RespuestaAgente
from src.reposicion.instrucciones import construir_instrucciones

from .conftest import ModeloFalso, final, llamada

pytestmark = pytest.mark.etapa1

HILO = {"configurable": {"thread_id": "prueba"}}


def _preguntar(modelo: ModeloFalso, texto: str) -> dict:
    return crear_agente(modelo).invoke(
        {"messages": [{"role": "user", "content": texto}]}, HILO
    )


def test_una_pregunta_de_stock_usa_la_herramienta_y_responde_tipado(
    api_en_servicios: TestClient,
):
    modelo = ModeloFalso(
        guion=[
            llamada("consultar_reservas", producto="merluza", bodega="coronel"),
            final(respuesta="En Coronel quedan 90 kg de merluza."),
        ]
    )
    resultado = _preguntar(modelo, "¿Cuánta merluza hay en Coronel?")
    respuesta = resultado["structured_response"]
    assert isinstance(respuesta, RespuestaAgente)
    herramientas = [
        m for m in resultado["messages"] if isinstance(m, ToolMessage)
    ]
    assert herramientas[0].name == "consultar_reservas"
    assert "90" in herramientas[0].content


def test_las_instrucciones_del_equipo_llegan_al_modelo():
    modelo = ModeloFalso(guion=[final(respuesta="Hola")])
    _preguntar(modelo, "hola")
    sistema = modelo.vistos[0][0]
    assert isinstance(sistema, SystemMessage)
    assert str(sistema.content) == construir_instrucciones()


def test_un_producto_desconocido_le_llega_al_modelo_como_error_legible(
    api_en_servicios: TestClient,
):
    modelo = ModeloFalso(
        guion=[
            llamada("consultar_reservas", producto="caviar"),
            final(respuesta="No encuentro ese producto."),
        ]
    )
    _preguntar(modelo, "¿Cuánto caviar hay?")
    ultimo = modelo.vistos[1][-1]
    assert isinstance(ultimo, ToolMessage)
    error = ErrorHerramienta.model_validate_json(str(ultimo.content))
    assert error.tipo == "no_encontrado"
    assert "caviar" in error.mensaje
