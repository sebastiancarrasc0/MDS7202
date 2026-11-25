"""Los controles de seguridad viven en el código, no solo en el prompt."""

import pytest

from src.reposicion.agente import crear_agente
from src.reposicion.aprobacion import (
    configuracion_hilo,
    decision_rechazar,
    pausa_pendiente,
    reanudar,
)
from src.reposicion.contratos import ABRE_DATO, CIERRA_DATO
from src.reposicion.herramienta_proveedores import buscar_proveedores
from src.reposicion.simulacion import INSTRUCCION_ESCONDIDA

from .conftest import ModeloFalso, ejecutar, final, llamada


@pytest.mark.etapa4
def test_un_modelo_que_obedece_la_instruccion_escondida_igual_queda_pendiente(
    entorno_completo,
):
    """Aunque el modelo cayera en la inyección, la solicitud espera a Pilar."""
    modelo = ModeloFalso(
        guion=[
            llamada(
                "registrar_orden_reposicion",
                producto="merluza",
                bodega="coronel",
                cantidad=5000,
                proveedor="Distribuidora Rápida",
            ),
            final(respuesta="Hecho"),
        ]
    )
    agente = crear_agente(modelo)
    agente.invoke(
        {
            "messages": [
                {"role": "user", "content": "Compra 5 toneladas de merluza ya"}
            ]
        },
        configuracion_hilo("s1"),
    )
    assert pausa_pendiente(agente, "s1")
    assert entorno_completo["registro"].ordenes == []
    reanudar(agente, "s1", [decision_rechazar("No")])
    assert entorno_completo["registro"].ordenes == []


@pytest.mark.etapa3
def test_el_contenido_con_una_instruccion_llega_marcado_como_dato(
    busqueda_simulada,
):
    resultado = ejecutar(
        buscar_proveedores, producto="merluza", region="Biobío"
    )
    peligrosos = [
        i for i in resultado.items if INSTRUCCION_ESCONDIDA in i.extracto
    ]
    assert peligrosos, "El caso de prueba debe traer la instrucción escondida."
    for item in peligrosos:
        assert item.extracto.startswith(ABRE_DATO)
        assert item.extracto.endswith(CIERRA_DATO)
    assert "no instrucciones" in resultado.aviso


@pytest.mark.etapa0
def test_la_llave_no_aparece_en_el_registro_de_la_configuracion(monkeypatch):
    from src.reposicion.config import get_settings

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-no-debe-salir")
    get_settings.cache_clear()
    assert "no-debe-salir" not in repr(get_settings())
