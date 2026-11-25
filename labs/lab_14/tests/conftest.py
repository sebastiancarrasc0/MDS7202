"""Fixtures compartidos de las pruebas del Lab14.

Ninguna prueba necesita red, llaves ni cuota: usan un servidor de bodegas en
memoria, embeddings deterministas y un modelo falso que llama herramientas.
Cada prueba trata una carpeta temporal como la raíz del laboratorio, para no leer el `.env` de quien la
ejecuta ni escribir cachés o bases en el laboratorio.
"""

import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from src.reposicion import servicios
from src.reposicion.config import get_settings
from src.reposicion.rag import abrir_coleccion, ingestar_politicas
from src.reposicion.servidor.app import crear_app
from src.reposicion.simulacion import BusquedaSimulada, RegistroOrdenesSimulado

RAIZ = Path(__file__).resolve().parent.parent
POLITICAS = RAIZ / "data" / "raw" / "politicas"

VARIABLES = (
    "OPENROUTER_API_KEY",
    "TAVILY_API_KEY",
    "MODELO_CHAT",
    "MODELO_EMBEDDINGS",
    "URL_API_BODEGAS",
    "URL_PHOENIX",
    "REPOSICION_MODO",
    "USAR_CACHE",
)


@pytest.fixture(autouse=True)
def entorno_de_prueba(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Un entorno conocido: sin llaves, sin `.env` y con los servicios limpios."""
    for nombre in VARIABLES:
        monkeypatch.delenv(nombre, raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("REPOSICION_RAIZ", str(tmp_path))
    monkeypatch.setenv("DIRECTORIO_POLITICAS", str(POLITICAS))
    get_settings.cache_clear()
    servicios.reiniciar()
    yield
    get_settings.cache_clear()
    servicios.reiniciar()


def llamada(nombre: str, **argumentos: Any) -> AIMessage:
    """Un mensaje del modelo que pide usar una herramienta."""
    return AIMessage(
        content="",
        tool_calls=[
            {"name": nombre, "args": argumentos, "id": uuid.uuid4().hex[:8]}
        ],
    )


def final(**campos: Any) -> AIMessage:
    """El mensaje final del agente: la respuesta estructurada."""
    return llamada("RespuestaAgente", **campos)


class ModeloFalso(BaseChatModel):
    """Modelo que responde un guion fijo y soporta herramientas.

    Registra cada lista de mensajes que recibió, para comprobar qué vio.
    """

    guion: list[AIMessage]
    paso: int = 0
    vistos: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "modelo-falso"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ModeloFalso":
        return self

    def _generate(
        self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs
    ) -> ChatResult:
        self.vistos.append(list(messages))
        mensaje = self.guion[min(self.paso, len(self.guion) - 1)]
        self.paso += 1
        return ChatResult(generations=[ChatGeneration(message=mensaje)])


@pytest.fixture
def cliente_api() -> TestClient:
    """Cliente HTTP del servidor de bodegas, con las órdenes vacías."""
    return TestClient(crear_app())


def ejecutar(herramienta: Any, **argumentos: Any) -> Any:
    """Ejecuta una herramienta como lo hace el agente y devuelve su resultado tipado."""
    mensaje = herramienta.invoke(
        {
            "name": herramienta.name,
            "args": argumentos,
            "id": "t1",
            "type": "tool_call",
        }
    )
    return mensaje.artifact


@pytest.fixture
def api_en_servicios(cliente_api: TestClient) -> TestClient:
    """Las herramientas consultan el servidor de bodegas en memoria."""
    servicios.configurar(cliente_api=cliente_api)
    return cliente_api


@pytest.fixture
def coleccion_ingerida(monkeypatch: pytest.MonkeyPatch):
    """Base de políticas ya ingerida, con embeddings deterministas.

    Con embeddings falsos la relevancia es arbitraria, así que se acepta cualquier
    distancia: estas pruebas verifican el cableado, no la calidad de la búsqueda.
    """
    monkeypatch.setenv("DISTANCIA_MAXIMA", "2.0")
    get_settings.cache_clear()
    settings = get_settings()
    coleccion = abrir_coleccion(settings, DeterministicFakeEmbedding(size=64))
    ingestar_politicas(settings.directorio_politicas, coleccion)
    servicios.configurar(coleccion=coleccion)
    return coleccion


@pytest.fixture
def busqueda_simulada() -> BusquedaSimulada:
    cliente = BusquedaSimulada()
    servicios.configurar(busqueda=cliente)
    return cliente


@pytest.fixture
def registro_simulado() -> RegistroOrdenesSimulado:
    registro = RegistroOrdenesSimulado()
    servicios.configurar(registro=registro)
    return registro


@pytest.fixture
def entorno_sin_politicas(
    api_en_servicios, busqueda_simulada, registro_simulado
):
    """API, búsqueda y registro de órdenes simulados, sin la base de políticas."""
    return {
        "api": api_en_servicios,
        "busqueda": busqueda_simulada,
        "registro": registro_simulado,
    }


@pytest.fixture
def entorno_completo(entorno_sin_politicas, coleccion_ingerida):
    """Todo lo anterior y las políticas ya ingeridas."""
    return entorno_sin_politicas
