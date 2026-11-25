"""Etapa 2: la herramienta de políticas acepta una o varias consultas."""

import pytest
from pydantic import ValidationError

from src.reposicion.config import get_settings
from src.reposicion.contratos import ErrorHerramienta, RespuestaPoliticas
from src.reposicion.herramienta_politicas import buscar_politicas

from .conftest import ModeloFalso, ejecutar, final, llamada

pytestmark = pytest.mark.etapa2


def test_una_consulta_devuelve_fragmentos_con_su_fuente(coleccion_ingerida):
    resultado = ejecutar(
        buscar_politicas, consultas=["cobertura mínima de la merluza"]
    )
    assert isinstance(resultado, RespuestaPoliticas)
    assert len(resultado.resultados) == 1
    assert resultado.resultados[0].fragmentos
    assert resultado.resultados[0].fragmentos[0].archivo.endswith(".md")


def test_varias_consultas_en_una_llamada_vienen_separadas(coleccion_ingerida):
    resultado = ejecutar(
        buscar_politicas,
        consultas=["cobertura mínima de la merluza", "sustitución del tomate"],
    )
    assert isinstance(resultado, RespuestaPoliticas)
    assert [r.consulta for r in resultado.resultados] == [
        "cobertura mínima de la merluza",
        "sustitución del tomate",
    ]


def test_sin_politica_relevante_lo_dice_y_pide_no_inventar(
    coleccion_ingerida, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DISTANCIA_MAXIMA", "0.0")
    get_settings.cache_clear()
    resultado = ejecutar(buscar_politicas, consultas=["tema que nadie trata"])
    assert isinstance(resultado, RespuestaPoliticas)
    assert resultado.resultados[0].fragmentos == []
    assert "Sin política relevante" in resultado.mensaje
    assert "No inventen" in resultado.mensaje


def test_una_base_vacia_es_un_error_que_pide_ingerir(
    monkeypatch: pytest.MonkeyPatch,
):
    from langchain_core.embeddings import DeterministicFakeEmbedding

    from src.reposicion import servicios
    from src.reposicion.rag import abrir_coleccion

    servicios.configurar(
        coleccion=abrir_coleccion(
            get_settings(), DeterministicFakeEmbedding(size=32)
        )
    )
    resultado = ejecutar(buscar_politicas, consultas=["merluza"])
    assert isinstance(resultado, ErrorHerramienta)
    assert "ingerir" in resultado.mensaje


@pytest.mark.parametrize("consultas", [[], ["x"], ["una consulta"] * 6])
def test_la_entrada_se_limita(coleccion_ingerida, consultas):
    with pytest.raises(ValidationError):
        ejecutar(buscar_politicas, consultas=consultas)


def test_el_agente_recibe_las_politicas_como_json(coleccion_ingerida):
    from src.reposicion.agente import crear_agente

    modelo = ModeloFalso(
        guion=[
            llamada("buscar_politicas", consultas=["pescado", "tomate"]),
            final(respuesta="Listo", politicas_citadas=["pescado.md"]),
        ]
    )
    resultado = crear_agente(modelo).invoke(
        {"messages": [{"role": "user", "content": "políticas"}]},
        {"configurable": {"thread_id": "p"}},
    )
    contenido = RespuestaPoliticas.model_validate_json(
        str(modelo.vistos[1][-1].content)
    )
    assert len(contenido.resultados) == 2
    assert resultado["structured_response"].politicas_citadas == ["pescado.md"]
