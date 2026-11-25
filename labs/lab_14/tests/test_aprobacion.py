"""Etapa 4: ninguna solicitud de compra se envía sin que Pilar elija un proveedor."""

import pytest

from src.reposicion.agente import crear_agente
from src.reposicion.aprobacion import (
    configuracion_hilo,
    decision_editar,
    decision_rechazar,
    pausa_pendiente,
    reanudar,
    validar_edicion,
)
from src.reposicion.herramienta_orden import registrar_orden_reposicion

from .conftest import ModeloFalso, ejecutar, final, llamada

pytestmark = pytest.mark.etapa4

HILO = "hilo-1"
PEDIDO = {"producto": "merluza", "bodega": "coronel", "cantidad": 330}


def _guion():
    return [
        llamada("buscar_proveedores", producto="merluza", region="Biobío"),
        llamada("registrar_orden_reposicion", **PEDIDO),
        final(respuesta="Listo"),
    ]


def _agente_pausado(entorno_completo):
    modelo = ModeloFalso(guion=_guion())
    agente = crear_agente(modelo)
    agente.invoke(
        {
            "messages": [
                {"role": "user", "content": "Repongan merluza en Coronel"}
            ]
        },
        configuracion_hilo(HILO),
    )
    return agente, modelo


def _elegir(agente, **cambios):
    pendiente = pausa_pendiente(agente, HILO)[0]
    elegida = {
        **pendiente.argumentos,
        "proveedor": "Pesquera Austral Ltda.",
        "precio_unitario_clp": 4200.0,
        **cambios,
    }
    return reanudar(
        agente, HILO, [decision_editar("registrar_orden_reposicion", elegida)]
    )


def test_la_ejecucion_se_detiene_antes_de_enviar_y_no_hay_solicitudes(
    entorno_completo,
):
    agente, _ = _agente_pausado(entorno_completo)
    pendientes = pausa_pendiente(agente, HILO)
    assert [p.nombre for p in pendientes] == ["registrar_orden_reposicion"]
    assert "proveedor" not in pendientes[0].argumentos
    assert entorno_completo["registro"].ordenes == []
    assert entorno_completo["api"].get("/ordenes").json() == []


def test_el_agente_no_elige_proveedor_y_pilar_si(entorno_completo):
    agente, _ = _agente_pausado(entorno_completo)
    resultado = _elegir(agente)
    orden = entorno_completo["registro"].ordenes[0]
    assert orden["proveedor"] == "Pesquera Austral Ltda."
    assert orden["precio_unitario_clp"] == 4200
    assert (orden["producto"], orden["bodega"], orden["cantidad"]) == (
        "merluza",
        "coronel",
        330,
    )
    assert resultado["structured_response"].respuesta == "Listo"
    assert pausa_pendiente(agente, HILO) == []


def test_pilar_puede_cambiar_la_cantidad_a_comprar(entorno_completo):
    agente, _ = _agente_pausado(entorno_completo)
    _elegir(agente, cantidad=100.0)
    assert entorno_completo["registro"].ordenes[0]["cantidad"] == 100.0


def test_un_precio_no_publicado_queda_sin_precio(entorno_completo):
    agente, _ = _agente_pausado(entorno_completo)
    _elegir(agente, proveedor="Mar del Sur SpA", precio_unitario_clp=None)
    orden = entorno_completo["registro"].ordenes[0]
    assert orden["proveedor"] == "Mar del Sur SpA"
    assert orden["precio_unitario_clp"] is None


def test_rechazar_no_envia_nada_y_el_agente_recibe_el_motivo(entorno_completo):
    agente, modelo = _agente_pausado(entorno_completo)
    reanudar(agente, HILO, [decision_rechazar("Ninguno me convence")])
    assert entorno_completo["registro"].ordenes == []
    ultimo = modelo.vistos[-1][-1]
    assert "Ninguno me convence" in str(ultimo.content)


def test_las_dos_decisiones_usan_el_mismo_hilo_y_cierran_la_pausa(
    entorno_completo,
):
    agente, _ = _agente_pausado(entorno_completo)
    assert pausa_pendiente(agente, "otro-hilo") == []
    assert pausa_pendiente(agente, HILO)
    reanudar(agente, HILO, [decision_rechazar("No")])
    assert pausa_pendiente(agente, HILO) == []


@pytest.mark.parametrize(
    ("argumentos", "campo"),
    [
        ({"proveedor": "X", "cantidad": -5}, "cantidad"),
        ({"proveedor": "", "cantidad": 10}, "proveedor"),
        ({"cantidad": 10}, "proveedor"),
        (
            {"proveedor": "X", "cantidad": 10, "precio_unitario_clp": -1},
            "precio",
        ),
    ],
)
def test_una_eleccion_invalida_se_rechaza_nombrando_el_campo(argumentos, campo):
    assert campo in (validar_edicion(argumentos) or "")


def test_una_eleccion_valida_no_tiene_error():
    assert (
        validar_edicion(
            {"proveedor": "X", "cantidad": 50, "precio_unitario_clp": 100.0}
        )
        is None
    )


def test_el_monto_sobre_la_visacion_no_se_envia_aunque_pilar_lo_elija(
    entorno_completo,
):
    # 1.000 kg a $4.200 son $4.200.000: sobre los $3.000.000 sin visación.
    agente, _ = _agente_pausado(entorno_completo)
    _elegir(agente, cantidad=1000.0)
    assert entorno_completo["registro"].ordenes == []


def test_sin_proveedor_la_solicitud_no_se_envia(entorno_completo):
    resultado = ejecutar(registrar_orden_reposicion, **PEDIDO)
    assert resultado.tipo == "entrada_invalida"
    assert "proveedor" in resultado.mensaje
    assert entorno_completo["registro"].ordenes == []
