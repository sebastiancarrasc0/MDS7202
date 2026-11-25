"""Etapa 0: cada llamada al modelo y a una herramienta queda como un tramo."""

import pytest
from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from src.reposicion import observabilidad
from src.reposicion.config import Settings

from .conftest import ModeloFalso, llamada

pytestmark = pytest.mark.etapa0

LLAVE = "sk-or-que-no-debe-salir-en-las-trazas"


@tool
def consultar_stock(producto: str) -> str:
    """Devuelve el stock de un producto."""
    return f"{producto}: 3 kg"


def test_una_invocacion_con_herramienta_deja_tramos_de_modelo_y_de_herramienta():
    exportador = InMemorySpanExporter()
    proveedor = TracerProvider()
    proveedor.add_span_processor(SimpleSpanProcessor(exportador))
    instrumentador = LangChainInstrumentor()
    instrumentador.instrument(tracer_provider=proveedor)
    try:
        modelo = ModeloFalso(
            guion=[
                llamada("consultar_stock", producto="merluza"),
                AIMessage(content="Quedan 3 kg de merluza."),
            ]
        )
        agente = create_agent(model=modelo, tools=[consultar_stock])
        agente.invoke({"messages": [{"role": "user", "content": "¿merluza?"}]})
    finally:
        instrumentador.uninstrument()
    tipos = {
        str((tramo.attributes or {}).get("openinference.span.kind"))
        for tramo in exportador.get_finished_spans()
    }
    assert {"LLM", "TOOL"} <= tipos


def test_ningun_tramo_contiene_una_llave(monkeypatch: pytest.MonkeyPatch):
    exportador = InMemorySpanExporter()
    proveedor = TracerProvider()
    proveedor.add_span_processor(SimpleSpanProcessor(exportador))
    instrumentador = LangChainInstrumentor()
    instrumentador.instrument(tracer_provider=proveedor)
    monkeypatch.setenv("OPENROUTER_API_KEY", LLAVE)
    try:
        ModeloFalso(
            guion=[llamada("consultar_stock", producto="merluza")]
        ).invoke("¿cuánta merluza hay?")
    finally:
        instrumentador.uninstrument()
    for tramo in exportador.get_finished_spans():
        for valor in (tramo.attributes or {}).values():
            assert LLAVE not in str(valor)


def test_registrar_trazas_llama_a_register_con_el_proyecto_y_el_endpoint(
    monkeypatch: pytest.MonkeyPatch,
):
    recibido = {}

    def register(**kwargs):
        recibido.update(kwargs)

    monkeypatch.setattr("phoenix.otel.register", register)
    observabilidad.registrar_trazas(
        "mi-proyecto", "http://localhost:6006/v1/traces"
    )
    assert recibido == {
        "project_name": "mi-proyecto",
        "endpoint": "http://localhost:6006/v1/traces",
        "auto_instrument": True,
    }


def test_sin_phoenix_el_aviso_lo_dice_y_no_falla(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(observabilidad, "phoenix_activo", lambda url: False)
    aviso = observabilidad.activar_trazas(Settings(_env_file=None))  # pyright: ignore[reportCallIssue]
    assert aviso is not None
    assert "Phoenix no está en ejecución" in aviso


def test_con_phoenix_activo_se_registran_las_trazas(
    monkeypatch: pytest.MonkeyPatch,
):
    llamadas = []
    monkeypatch.setattr(observabilidad, "phoenix_activo", lambda url: True)
    monkeypatch.setattr(
        observabilidad, "registrar_trazas", lambda p, e: llamadas.append((p, e))
    )
    assert observabilidad.activar_trazas(Settings(_env_file=None)) is None  # pyright: ignore[reportCallIssue]
    assert llamadas == [("lab14", "http://localhost:6006/v1/traces")]
