"""La interfaz guía al equipo y no deja pasar una orden sin aprobación.

Se prueba por etapas: lo que no necesita al agente es de la etapa 0; cada
página o función que sí lo necesita pertenece a la etapa que la completa.
"""

import pytest
import streamlit as st
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from src.reposicion.config import get_settings

from .conftest import RAIZ

UI = str(RAIZ / "src" / "reposicion" / "ui" / "app.py")


@pytest.fixture(autouse=True)
def limpiar_recursos():
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


@pytest.fixture
def simulado_sin_politicas(
    monkeypatch: pytest.MonkeyPatch, entorno_sin_politicas
):
    monkeypatch.setenv("REPOSICION_MODO", "simulado")
    get_settings.cache_clear()
    return entorno_sin_politicas


@pytest.fixture
def simulado(monkeypatch: pytest.MonkeyPatch, entorno_completo):
    monkeypatch.setenv("REPOSICION_MODO", "simulado")
    get_settings.cache_clear()
    return entorno_completo


def _abrir(conv: str | None = None) -> AppTest:
    app = AppTest.from_file(UI, default_timeout=60)
    if conv:
        app.query_params["conv"] = conv
    return app.run()


def _preguntar(app: AppTest, texto: str) -> AppTest:
    app.chat_input[0].set_value(texto).run()
    return app


def _textos(app: AppTest) -> str:
    return " ".join(
        str(e.value)
        for e in (
            *app.markdown,
            *app.caption,
            *app.error,
            *app.warning,
            *app.success,
            *app.info,
        )
    )


@pytest.mark.etapa0
def test_sin_llave_la_interfaz_dice_cual_falta_y_no_muestra_un_traceback():
    app = _abrir()
    assert not app.exception
    assert any("OPENROUTER_API_KEY" in e.value for e in app.error)


@pytest.mark.etapa0
def test_con_llave_ninguna_pagina_la_muestra(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-no-debe-salir-nunca")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-no-debe-salir-nunca")
    get_settings.cache_clear()
    app = _abrir()
    for pagina in ("Conversación", "Base de conocimiento", "Órdenes"):
        app.sidebar.radio(key="pagina").set_value(pagina).run()
        assert "no-debe-salir" not in _textos(app)


@pytest.mark.etapa1
def test_una_pregunta_de_stock_se_responde_y_muestra_la_herramienta(
    simulado_sin_politicas,
):
    app = _preguntar(_abrir(), "¿Cuánta merluza hay en Coronel?")
    assert not app.exception
    assert "90 kg" in _textos(app)
    assert any("consultar_reservas" in c.value for c in app.caption)


def _enviar(app: AppTest) -> AppTest:
    boton = next(
        b for b in app.button if "solicitud a compras" in (b.label or "")
    )
    return boton.click().run()


@pytest.mark.etapa4
def test_una_reposicion_muestra_tres_opciones_sin_plazo_ni_recomendacion(
    simulado,
):
    app = _preguntar(_abrir(), "Necesito reponer merluza en Coronel")
    assert app.button(key="rechazar")
    assert len(app.chat_input) == 0
    assert simulado["registro"].ordenes == []
    tabla = app.table[0].value
    assert list(tabla["opción"]) == [1, 2, 3]
    assert not any("plazo" in c.lower() for c in tabla.columns)
    assert "recomienda" not in _textos(app)


@pytest.mark.etapa4
def test_elegir_un_proveedor_envia_la_solicitud_a_compras(simulado):
    app = _preguntar(_abrir(), "Necesito reponer merluza en Coronel")
    app.selectbox(key="opcion").set_value(2)
    app = _enviar(app)
    orden = simulado["registro"].ordenes[0]
    assert orden["proveedor"] == "Mar del Sur SpA"
    assert "Quedó registrada" in _textos(app)
    assert len(app.chat_input) == 1


@pytest.mark.etapa4
def test_rechazar_con_motivo_no_registra_nada(simulado):
    app = _preguntar(_abrir(), "Necesito reponer merluza en Coronel")
    app.text_input(key="motivo").set_value("Muy caro")
    app.button(key="rechazar").click().run()
    assert simulado["registro"].ordenes == []
    assert "no envié la solicitud" in _textos(app)


@pytest.mark.etapa4
def test_una_cantidad_invalida_muestra_el_error_del_campo(simulado):
    app = _preguntar(_abrir(), "Necesito reponer merluza en Coronel")
    app.number_input(key="cantidad").set_value(-5.0)
    app = _enviar(app)
    assert any("cantidad" in e.value for e in app.error)
    assert simulado["registro"].ordenes == []


@pytest.mark.etapa4
def test_la_pausa_sobrevive_a_una_recarga_con_el_mismo_hilo(simulado):
    primera = _preguntar(_abrir(), "Necesito reponer merluza en Coronel")
    hilo = primera.query_params["conv"]
    recargada = _abrir(conv=hilo)
    assert recargada.button(key="rechazar")
    assert len(recargada.chat_input) == 0


@pytest.mark.etapa2
def test_la_base_de_conocimiento_se_ingiere_desde_la_interfaz(simulado):
    app = _abrir()
    app.sidebar.radio(key="pagina").set_value("Base de conocimiento").run()
    app.button(key="ingerir").click().run()
    assert any("Ingeridos 10 documentos" in s.value for s in app.success)
    app.text_input(key="consulta").set_value(
        "cobertura mínima de la merluza"
    ).run()
    assert app.expander


@pytest.mark.etapa0
def test_las_ordenes_registradas_se_listan(
    simulado_sin_politicas: dict, cliente_api: TestClient
):
    app = _abrir()
    app.sidebar.radio(key="pagina").set_value("Órdenes").run()
    assert any("Todavía no hay solicitudes" in i.value for i in app.info)


@pytest.mark.etapa0
def test_una_pieza_pendiente_se_nombra_en_vez_de_mostrar_un_traceback(
    simulado_sin_politicas, monkeypatch: pytest.MonkeyPatch
):
    def pendiente(*args, **kwargs):
        raise NotImplementedError("Completen crear_agente antes de continuar.")

    monkeypatch.setattr("src.reposicion.agente.crear_agente", pendiente)
    app = _abrir()
    assert not app.exception
    assert any("crear_agente" in w.value for w in app.warning)


@pytest.mark.etapa4
@pytest.mark.parametrize(
    ("extracto", "esperado"),
    [
        ("Merluza a $4.200 por kilo puesto en Coronel", 4200.0),
        ("Merluza fresca $4.990/kg, retiro en planta", 4990.0),
        ("Precio mayorista: $ 3.900 el Kg, mínimo 50 kg", 3900.0),
        ("Merluza austral CLP 5.100 x kilo", 5100.0),
        ("Se vende a 4.500 pesos por kilo en cajas", 4500.0),
        ("Merluza desde $6,500 KG en pescadería", 6500.0),
        ("Cotización por correo, sin precio publicado.", None),
        ("Caja de 18 kg a $12.000", None),
    ],
)
def test_el_precio_se_lee_de_las_formas_habituales_de_publicarlo(
    extracto: str, esperado: float | None
):
    from src.reposicion.ui.app import _precio_del_extracto

    assert _precio_del_extracto(extracto) == esperado
