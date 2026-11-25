"""El system prompt que escribe el equipo, comprobado por etapas.

Las pruebas solo revisan lo que se puede comprobar sin un modelo: que el texto
nombre a la empresa y cada herramienta y que incluya un ejemplo. Si las reglas
son claras se observa en la interfaz.
"""

import pytest

from src.reposicion.instrucciones import construir_instrucciones


@pytest.fixture
def instrucciones() -> str:
    return construir_instrucciones()


@pytest.mark.etapa1
def test_el_prompt_nombra_la_empresa_y_la_herramienta_de_reservas(
    instrucciones: str,
):
    assert isinstance(instrucciones, str)
    assert "Mar y Huerta" in instrucciones
    assert "consultar_reservas" in instrucciones


@pytest.mark.etapa1
def test_el_prompt_incluye_un_ejemplo(instrucciones: str):
    assert "ejemplo" in instrucciones.lower()


@pytest.mark.etapa2
def test_el_prompt_nombra_la_herramienta_de_politicas(instrucciones: str):
    assert "buscar_politicas" in instrucciones


@pytest.mark.etapa3
def test_el_prompt_nombra_la_herramienta_de_proveedores(instrucciones: str):
    assert "buscar_proveedores" in instrucciones


@pytest.mark.etapa4
def test_el_prompt_nombra_la_herramienta_que_envia_la_solicitud(
    instrucciones: str,
):
    assert "registrar_orden_reposicion" in instrucciones
