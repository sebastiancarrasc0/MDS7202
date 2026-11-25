"""Etapa 3: ante merluza bajo la política, el agente busca proveedores y no envía nada."""

import pytest

from src.reposicion import servicios
from src.reposicion.agente import crear_agente
from src.reposicion.aprobacion import configuracion_hilo, pausa_pendiente
from src.reposicion.contratos import ResultadoBusqueda

from .conftest import ModeloFalso, final, llamada

pytestmark = pytest.mark.etapa3

HILO = "reposicion"


def _pedir(modelo: ModeloFalso, texto: str) -> dict:
    return crear_agente(modelo).invoke(
        {"messages": [{"role": "user", "content": texto}]},
        configuracion_hilo(HILO),
    )


def test_el_agente_consulta_reservas_y_politicas_antes_de_buscar_proveedores(
    entorno_completo,
):
    modelo = ModeloFalso(
        guion=[
            llamada("consultar_reservas", producto="merluza", bodega="coronel"),
            llamada(
                "buscar_politicas",
                consultas=["cobertura mínima de la merluza"],
            ),
            llamada("buscar_proveedores", producto="merluza", region="Biobío"),
            final(respuesta="Encontré tres proveedores."),
        ]
    )
    _pedir(modelo, "Necesito reponer merluza en Coronel")
    busqueda = ResultadoBusqueda.model_validate_json(
        str(modelo.vistos[3][-1].content)
    )
    assert len(busqueda.items) == 3
    assert entorno_completo["registro"].ordenes == []


def test_con_menos_de_tres_proveedores_la_herramienta_los_entrega_tal_cual(
    entorno_sin_politicas,
):
    class DosResultados:
        def invoke(self, entrada):
            return {
                "results": [
                    {
                        "title": f"P{n}",
                        "url": f"https://p{n}.example.com",
                        "content": "x",
                    }
                    for n in (1, 2)
                ]
            }

    servicios.configurar(busqueda=DosResultados())
    modelo = ModeloFalso(
        guion=[
            llamada("buscar_proveedores", producto="merluza", region="Biobío"),
            final(respuesta="Solo encontré 2 proveedores: ¿cómo seguimos?"),
        ]
    )
    resultado = _pedir(modelo, "Repongan merluza")
    busqueda = ResultadoBusqueda.model_validate_json(
        str(modelo.vistos[1][-1].content)
    )
    assert len(busqueda.items) == 2
    assert pausa_pendiente(crear_agente(modelo), HILO) == []
    assert "2" in resultado["structured_response"].respuesta
