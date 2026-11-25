"""Interfaz de Streamlit del agente de Mar y Huerta (material provisto).

Se ejecuta desde la raíz del laboratorio, con el servidor de bodegas en marcha:

    uv run streamlit run src/reposicion/ui/app.py

Toda la interacción con el agente y con la base de conocimiento pasa por aquí.
"""

import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any

import streamlit as st

# Streamlit pone en el path la carpeta del script, no la raíz del proyecto.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.reposicion import servicios
from src.reposicion.agente import crear_agente
from src.reposicion.aprobacion import (
    configuracion_hilo,
    crear_checkpointer,
    decision_editar,
    decision_rechazar,
    pausa_pendiente,
    reanudar,
    validar_edicion,
)
from src.reposicion.config import get_settings, llaves_faltantes
from src.reposicion.contratos import ABRE_DATO, CIERRA_DATO
from src.reposicion.cuota import consultar_cuota, traducir_error
from src.reposicion.modelos_llm import activar_cache_llm, crear_embeddings
from src.reposicion.observabilidad import activar_trazas
from src.reposicion.rag import (
    ErrorEmbeddings,
    abrir_coleccion,
    borrar_coleccion,
    consultar_politicas,
    contar_fragmentos,
    ingestar_politicas,
)

PAGINAS = ("Conversación", "Base de conocimiento", "Órdenes")


@st.cache_resource
def obtener_agente() -> Any:
    activar_cache_llm(get_settings())
    return crear_agente(checkpointer=crear_checkpointer())


@st.cache_resource
def iniciar_trazas() -> str | None:
    return activar_trazas(get_settings())


def _pieza_pendiente(error: NotImplementedError) -> None:
    st.warning(
        f"Falta completar una pieza del laboratorio: {error} "
        "El notebook indica en qué archivo está."
    )


def barra_lateral() -> None:
    settings = get_settings()
    with st.sidebar:
        st.header("Estado")
        st.caption(f"Modo: **{settings.modo}**")
        if settings.modo == "real":
            cuota = consultar_cuota(settings)
            if cuota is None:
                st.caption("Cuota de OpenRouter: no disponible.")
            else:
                st.progress(cuota.restantes / max(cuota.limite, 1))
                st.caption(
                    f"Quedan **{cuota.restantes}** de {cuota.limite} solicitudes hoy."
                )
        aviso = iniciar_trazas()
        if aviso:
            st.warning(aviso)
        else:
            st.markdown(
                f"[Abrir las trazas en Phoenix]({settings.url_phoenix})"
            )


def _historial(agente: Any, hilo: str) -> list[tuple[str, str, list[str]]]:
    """Lee la conversación del punto de control: (rol, texto, herramientas)."""
    mensajes = agente.get_state(configuracion_hilo(hilo)).values.get(
        "messages", []
    )
    historial: list[tuple[str, str, list[str]]] = []
    usadas: list[str] = []
    for mensaje in mensajes:
        if mensaje.type == "human":
            historial.append(("user", str(mensaje.content), []))
            usadas = []
        elif mensaje.type == "ai":
            for llamada in getattr(mensaje, "tool_calls", None) or []:
                if llamada["name"] == "RespuestaAgente":
                    historial.append(
                        (
                            "assistant",
                            llamada["args"].get("respuesta", ""),
                            usadas,
                        )
                    )
                else:
                    usadas = [*usadas, llamada["name"]]
    return historial


_NUMERO = r"(\d{1,3}(?:[.,]\d{3})+|\d+)"
_UNIDAD = r"(?:kilos?|kilogramos?|kgs?|unidad(?:es)?|litros?|lts?)\b"
_POR = r"\s*(?:/|por|x|el|la|cada)?\s*"
_PRECIOS_POR_UNIDAD = (
    # `$4.200 por kilo`, `$4.200/kg`, `$ 4.200 el Kg`, `CLP 4.200 x kilo`
    re.compile(
        r"(?:\$|CLP)\s*" + _NUMERO + r"(?:\s*(?:CLP|pesos))?" + _POR + _UNIDAD,
        re.IGNORECASE,
    ),
    # `4.200 pesos por kilo`, `4.200 CLP/kg`
    re.compile(_NUMERO + r"\s*(?:CLP|pesos)" + _POR + _UNIDAD, re.IGNORECASE),
)


def _precio_del_extracto(texto: str) -> float | None:
    """El precio por unidad que publica la página, si lo dice.

    Entiende las formas habituales en Chile: `$4.200 por kilo`, `$4.200/kg`,
    `$ 4.200 el Kg`, `CLP 4.200 x kilo` y `4.200 pesos por kilo`.
    """
    for patron in _PRECIOS_POR_UNIDAD:
        encontrado = patron.search(texto)
        if encontrado:
            return float(re.sub(r"[.,]", "", encontrado.group(1)))
    return None


def _opciones_de_la_busqueda(agente: Any, hilo: str) -> list[dict[str, Any]]:
    """Los proveedores de la última búsqueda del agente, tal como los devolvió Tavily."""
    mensajes = agente.get_state(configuracion_hilo(hilo)).values.get(
        "messages", []
    )
    for mensaje in reversed(mensajes):
        if getattr(mensaje, "name", None) != "buscar_proveedores":
            continue
        try:
            items = json.loads(mensaje.content)["items"]
        except (ValueError, KeyError, TypeError):
            return []
        opciones = []
        for item in items[:3]:
            extracto = item["extracto"].replace(ABRE_DATO, "")
            extracto = extracto.replace(CIERRA_DATO, "")
            opciones.append(
                {
                    "proveedor": item["titulo"].split("|")[0].strip(),
                    "fuente": item["url"],
                    "precio": _precio_del_extracto(extracto),
                }
            )
        return opciones
    return []


def panel_de_aprobacion(agente: Any, hilo: str) -> bool:
    """Muestra las opciones pendientes. Devuelve `True` si hay una pausa."""
    acciones = pausa_pendiente(agente, hilo)
    if not acciones:
        return False
    accion = acciones[0]
    argumentos = accion.argumentos
    opciones = _opciones_de_la_busqueda(agente, hilo)
    st.subheader("Elijan un proveedor")
    st.markdown(
        f"**{argumentos.get('producto')}** para **{argumentos.get('bodega')}**: "
        f"cantidad a comprar, **{argumentos.get('cantidad'):g}**."
    )
    if not opciones:
        st.error("No encuentro los proveedores de la búsqueda.")
    st.table(
        [
            {
                "opción": n,
                "proveedor": o["proveedor"],
                "precio CLP": o["precio"],
                "fuente": o["fuente"],
            }
            for n, o in enumerate(opciones, 1)
        ]
    )
    with st.form("elegir"):
        numeros = list(range(1, len(opciones) + 1)) or [1]
        elegida = st.selectbox(
            "Proveedor elegido (opción)", numeros, key="opcion"
        )
        cantidad = st.number_input(
            "Cantidad a comprar",
            value=float(argumentos.get("cantidad") or 1),
            key="cantidad",
        )
        if st.form_submit_button("Enviar solicitud a compras", type="primary"):
            elegido = opciones[elegida - 1] if opciones else {}
            nuevos = {
                **argumentos,
                "proveedor": elegido.get("proveedor"),
                "cantidad": cantidad,
                "precio_unitario_clp": elegido.get("precio"),
            }
            error = validar_edicion(nuevos)
            if error:
                st.error(error)
            else:
                reanudar(agente, hilo, [decision_editar(accion.nombre, nuevos)])
                st.rerun()
    motivo = st.text_input("Motivo del rechazo", key="motivo")
    if st.button("Rechazar los proveedores", key="rechazar"):
        reanudar(
            agente, hilo, [decision_rechazar(motivo.strip() or "Rechazada.")]
        )
        st.rerun()
    return True


def _turno(agente: Any, hilo: str, texto: str) -> None:
    entrada = {"messages": [{"role": "user", "content": texto}]}
    with (
        st.chat_message("assistant"),
        st.status("Trabajando…", expanded=True) as estado,
    ):
        try:
            for fragmento in agente.stream(
                entrada, configuracion_hilo(hilo), stream_mode="updates"
            ):
                for nodo, cambio in fragmento.items():
                    if nodo == "__interrupt__" or not cambio:
                        continue
                    for mensaje in cambio.get("messages", []):
                        for llamada in (
                            getattr(mensaje, "tool_calls", None) or []
                        ):
                            if llamada["name"] != "RespuestaAgente":
                                estado.write(
                                    f"🔧 `{llamada['name']}` {llamada['args']}"
                                )
                        if mensaje.type == "tool":
                            estado.write(f"↳ {str(mensaje.content)[:300]}")
            estado.update(label="Listo", state="complete")
        except NotImplementedError as error:
            estado.update(label="Falta una pieza", state="error")
            _pieza_pendiente(error)
            return
        except Exception as error:
            estado.update(label="Falló", state="error")
            st.error(traducir_error(error))
            return
    st.rerun()


def pagina_conversacion() -> None:
    try:
        agente = obtener_agente()
    except NotImplementedError as error:
        _pieza_pendiente(error)
        return
    hilo = st.query_params.get("conv")
    if not hilo:
        hilo = uuid.uuid4().hex[:8]
        st.query_params["conv"] = hilo
    for rol, texto, usadas in _historial(agente, hilo):
        with st.chat_message(rol):
            st.write(texto)
            if usadas:
                st.caption("Herramientas usadas: " + ", ".join(usadas))
    if panel_de_aprobacion(agente, hilo):
        return
    if consulta := st.chat_input(
        "Pregunten por las reservas, las políticas o una reposición"
    ):
        with st.chat_message("user"):
            st.write(consulta)
        _turno(agente, hilo, consulta)


def pagina_base_de_conocimiento() -> None:
    settings = get_settings()
    st.write(
        f"Políticas en `{settings.directorio_politicas}`. Base vectorial en "
        f"`{settings.directorio_chroma}` (embeddings: `{settings.modelo_embeddings}`)."
    )
    try:
        coleccion = abrir_coleccion(settings, crear_embeddings(settings))
    except (ErrorEmbeddings, Exception) as error:
        st.error(str(error))
        return
    columna_a, columna_b = st.columns(2)
    if columna_a.button("Ingerir las políticas", key="ingerir"):
        try:
            resumen = ingestar_politicas(
                settings.directorio_politicas, coleccion
            )
        except NotImplementedError as error:
            _pieza_pendiente(error)
            return
        servicios.reiniciar()
        st.success(
            f"Ingeridos {resumen.archivos} documentos en {resumen.fragmentos} "
            f"fragmentos; la base tiene {resumen.total_en_coleccion}."
        )
    if columna_b.button("Borrar la base", key="borrar"):
        borrar_coleccion(settings)
        servicios.reiniciar()
        st.rerun()
    st.metric("Fragmentos en la base", contar_fragmentos(coleccion))
    consulta = st.text_input("Probar una consulta", key="consulta")
    if consulta:
        try:
            fragmentos = consultar_politicas(
                coleccion, consulta, distancia_maxima=settings.distancia_maxima
            )
        except NotImplementedError as error:
            _pieza_pendiente(error)
            return
        if not fragmentos:
            st.info("Sin política relevante para esa consulta.")
        for f in fragmentos:
            with st.expander(
                f"{f.archivo} · {f.ruta_seccion} (distancia {f.distancia:.2f})"
            ):
                st.write(f.texto)


def pagina_ordenes() -> None:
    try:
        ordenes = servicios.obtener_cliente_api().get("/ordenes").json()
    except Exception:
        st.error(
            "No se pudo consultar la API de bodegas. ¿Está en ejecución? "
            "`uv run uvicorn src.reposicion.servidor.app:app --port 8100`"
        )
        return
    if ordenes:
        st.table(
            [
                {
                    "id": o["orden_id"],
                    "producto": o["producto"],
                    "bodega": o["bodega"],
                    "proveedor": o["proveedor"],
                    "cantidad": o["cantidad"],
                    "precio CLP": o.get("precio_unitario_clp"),
                }
                for o in ordenes
            ]
        )
    else:
        st.info("Todavía no hay solicitudes de compra registradas.")


def principal() -> None:
    st.set_page_config(
        page_title="Mar y Huerta · Abastecimiento", page_icon="🐟"
    )
    st.title("🐟 Abastecimiento de Mar y Huerta")
    settings = get_settings()
    barra_lateral()
    if settings.modo == "real":
        faltan = llaves_faltantes(settings)
        if "OPENROUTER_API_KEY" in faltan:
            st.error(
                "Falta OPENROUTER_API_KEY. Defínanla en su archivo `.env` "
                "(hay un ejemplo en `.env.example`) y reinicien la interfaz."
            )
            return
        if "TAVILY_API_KEY" in faltan:
            st.sidebar.warning(
                "Falta TAVILY_API_KEY: la búsqueda de proveedores no funcionará."
            )
    pagina = st.sidebar.radio("Página", PAGINAS, key="pagina")
    {
        "Conversación": pagina_conversacion,
        "Base de conocimiento": pagina_base_de_conocimiento,
        "Órdenes": pagina_ordenes,
    }[pagina]()


principal()
