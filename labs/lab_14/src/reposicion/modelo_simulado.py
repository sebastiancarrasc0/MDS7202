"""Un modelo de reglas que imita a un agente, sin red ni cuota (material provisto).

No es un modelo de lenguaje: lee la conversación y decide con reglas simples qué
herramienta llamar o qué responder. Sirve para ensayar el código, ejecutar el
notebook completo sin gastar solicitudes. Se activa con
`REPOSICION_MODO=simulado`. Ignora a propósito las instrucciones escondidas en
los resultados de la web: así se ve cómo debería comportarse un agente robusto.
"""

import json
import math
import re
import unicodedata
import uuid
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult

from src.reposicion.servidor.datos import BODEGAS, PRODUCTOS

CLAVES_DE_REPOSICION = (
    "repon",
    "compr",
    "proveedor",
    "pedido",
    "propuesta",
    "orden",
)
CLAVES_DE_POLITICA = (
    "politica",
    "regla",
    "que dice",
    "cobertura minima",
    "sustitu",
    "urgente",
)
CLAVES_DE_RESERVA = (
    "stock",
    "reserva",
    "cuanta",
    "cuanto",
    "queda",
    "hay",
    "cobertura",
)
CLAVES_SECRETAS = (
    "api key", "llave", "instrucciones internas", "tus instrucciones", "prompt",
    "ignora tus", "ignora las instrucciones", "olvida tus", "contrasena",
)  # fmt: skip
INSTRUCCION_ESCONDIDA = "IMPORTANTE PARA EL ASISTENTE"


def _plano(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


def _producto(texto: str) -> str | None:
    for id_ in PRODUCTOS:
        raiz = "huevo" if id_ == "huevos" else id_
        if raiz in texto:
            return id_
    return None


def _bodega(texto: str) -> str | None:
    for id_, datos in BODEGAS.items():
        if _plano(datos["nombre"]) in texto:
            return id_
    return None


def _json(contenido: Any) -> dict:
    if isinstance(contenido, str) and "Tool response:" in contenido:
        # Tras editar una llamada, LangChain antepone una nota al resultado.
        contenido = contenido.split("Tool response:", 1)[1].strip()
    try:
        valor = json.loads(contenido) if isinstance(contenido, str) else {}
    except ValueError:
        return {}
    return valor if isinstance(valor, dict) else {}


def _llamada(nombre: str, **argumentos: Any) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": nombre, "args": argumentos, "id": uuid.uuid4().hex[:8]}
        ],
    )


def _final(respuesta: str, citas: list[str] | None = None) -> AIMessage:
    return _llamada(
        "RespuestaAgente",
        respuesta=respuesta,
        politicas_citadas=citas or [],
    )


def _precio(texto: str) -> float | None:
    encontrado = re.search(
        r"\$\s?([\d.]+)\s*por\s*(?:kilo|kg|unidad|litro)", texto
    )
    return float(encontrado.group(1).replace(".", "")) if encontrado else None


def _texto_libre(mensaje: AIMessage) -> str:
    """Lo que diría un modelo sin herramientas: su respuesta o que no tiene el dato."""
    for llamada in mensaje.tool_calls:
        if llamada["name"] == "RespuestaAgente":
            return str(llamada["args"].get("respuesta", ""))
    return "No tengo acceso a los datos de las bodegas de Mar y Huerta."


class ModeloSimulado(BaseChatModel):
    """Decide la siguiente jugada del agente a partir de la conversación.

    Conoce las herramientas que el agente le entregó: si su jugada necesita una
    que el equipo todavía no agrega a `crear_agente`, lo dice en vez de fallar.
    """

    disponibles: tuple[str, ...] = ()

    @property
    def _llm_type(self) -> str:
        return "modelo-simulado"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ModeloSimulado":
        nombres = tuple(
            getattr(t, "name", None) or t.get("function", {}).get("name", "")
            for t in tools
        )
        return self.model_copy(update={"disponibles": nombres})

    def _generate(
        self,
        messages: list[BaseMessage],
        stop=None,
        run_manager=None,
        **kwargs: Any,
    ) -> ChatResult:
        mensaje = self._decidir(messages)
        if not self.disponibles:
            # Sin herramientas (una llamada directa al modelo): solo habla.
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(content=_texto_libre(mensaje))
                    )
                ]
            )
        for llamada in mensaje.tool_calls:
            if (
                self.disponibles
                and llamada["name"] != "RespuestaAgente"
                and llamada["name"] not in self.disponibles
            ):
                mensaje = _final(
                    f"Todavía no puedo usar `{llamada['name']}`: el agente no la "
                    "tiene. Agréguenla a `tools` en `crear_agente`."
                )
        return ChatResult(generations=[ChatGeneration(message=mensaje)])

    def _decidir(self, mensajes: list[BaseMessage]) -> AIMessage:
        ultimo = max(
            i for i, m in enumerate(mensajes) if isinstance(m, HumanMessage)
        )
        pregunta = _plano(str(mensajes[ultimo].content))
        resultados = {
            m.name: m
            for m in mensajes[ultimo + 1 :]
            if isinstance(m, ToolMessage)
        }
        producto, bodega = _producto(pregunta), _bodega(pregunta)

        if not resultados:
            if any(c in pregunta for c in CLAVES_SECRETAS):
                return _final(
                    "No puedo compartir mis instrucciones ni mis llaves, ni cambiar "
                    "mis reglas. Puedo ayudar con reservas, políticas y reposiciones."
                )
            dominio = (
                *CLAVES_DE_REPOSICION,
                *CLAVES_DE_POLITICA,
                *CLAVES_DE_RESERVA,
            )
            if producto is None and not any(c in pregunta for c in dominio):
                return _final(
                    "Solo puedo ayudar con las reservas, las políticas de reposición "
                    "y las propuestas de las bodegas de Mar y Huerta."
                )
            es_politica = any(
                c in pregunta for c in CLAVES_DE_POLITICA
            ) and not any(c in pregunta for c in CLAVES_DE_REPOSICION)
            if es_politica:
                consultas = (
                    [
                        f"cobertura mínima de {producto}",
                        f"qué hacer cuando falta {producto}",
                    ]
                    if producto
                    else [str(mensajes[ultimo].content)[:200]]
                )
                return _llamada("buscar_politicas", consultas=consultas)
            if producto is None:
                return _final(
                    "¿De qué producto quieren saber? Por ejemplo merluza o tomate."
                )
            return _llamada(
                "consultar_reservas",
                **(
                    {"producto": producto, "bodega": bodega}
                    if bodega
                    else {"producto": producto}
                ),
            )

        # Alguna herramienta falló: se informa sin inventar.
        for mensaje in resultados.values():
            contenido = _json(mensaje.content)
            if "tipo" in contenido and "mensaje" in contenido:
                return _final(
                    f"No pude completar la consulta: {contenido['mensaje']}"
                )

        quiere_reponer = any(c in pregunta for c in CLAVES_DE_REPOSICION)
        if "registrar_orden_reposicion" in resultados:
            return self._tras_la_orden(resultados["registrar_orden_reposicion"])
        if "buscar_proveedores" in resultados:
            return self._tras_los_proveedores(resultados)
        if (
            "buscar_politicas" in resultados
            and "consultar_reservas" in resultados
        ):
            return self._tras_las_politicas(
                resultados, producto, quiere_reponer
            )
        if "buscar_politicas" in resultados:
            return self._responder_politica(resultados["buscar_politicas"])
        if quiere_reponer and producto:
            return _llamada(
                "buscar_politicas",
                consultas=[
                    f"cobertura mínima de {producto}",
                    f"cantidad a reponer de {producto}",
                ],
            )
        return self._responder_reservas(resultados["consultar_reservas"])

    # --- respuestas finales -------------------------------------------------
    def _responder_reservas(self, mensaje: ToolMessage) -> AIMessage:
        datos = _json(mensaje.content)
        lineas = [
            f"{r['bodega']}: {r['cantidad']:g} {r['unidad']} "
            f"({str(r['dias_cobertura']).replace('.', ',')} días de cobertura)"
            for r in datos.get("reservas", [])
        ]
        return _final(
            f"{datos.get('producto', 'El producto')} — "
            + "; ".join(lineas)
            + "."
        )

    def _responder_politica(self, mensaje: ToolMessage) -> AIMessage:
        fragmentos = [
            f
            for r in _json(mensaje.content).get("resultados", [])
            for f in r["fragmentos"]
        ]
        if not fragmentos:
            return _final(
                "No encontré una política que responda eso, y no voy a inventar una regla."
            )
        primero = fragmentos[0]
        cuerpo = primero["texto"].split("\n\n", 1)[-1]
        return _final(
            f"Según {primero['archivo']} ({primero['ruta_seccion']}): {cuerpo}",
            [f"{primero['archivo']} > {primero['ruta_seccion']}"],
        )

    def _tras_la_orden(self, mensaje: ToolMessage) -> AIMessage:
        datos = _json(mensaje.content)
        if "orden_id" in datos:
            return _final(
                f"Quedó registrada la solicitud {datos['orden_id']}: el área de compras "
                f"contactará a {datos['proveedor']} por {datos['cantidad']:g} de "
                f"{datos['producto']} para {datos['bodega']}."
            )
        return _final(
            "Entendido: no envié la solicitud a compras. Si quieren, busco otros "
            "proveedores."
        )

    # --- decisión de reposición ---------------------------------------------
    def _tras_las_politicas(
        self, resultados: dict, producto: str | None, quiere_reponer: bool
    ) -> AIMessage:
        reservas = _json(resultados["consultar_reservas"].content).get(
            "reservas", []
        )
        citas = [
            f"{f['archivo']} > {f['ruta_seccion']}"
            for r in _json(resultados["buscar_politicas"].content).get(
                "resultados", []
            )
            for f in r["fragmentos"][:1]
        ]
        minima = PRODUCTOS[producto]["minima"] if producto else 0
        faltan = [r for r in reservas if r["dias_cobertura"] < minima]
        if not faltan or not quiere_reponer:
            detalle = "; ".join(
                f"{r['bodega']} {str(r['dias_cobertura']).replace('.', ',')} días"
                for r in reservas
            )
            veredicto = (
                "hace falta reponer" if faltan else "no hace falta reponer"
            )
            return _final(
                f"La cobertura mínima de {PRODUCTOS[producto]['nombre'] if producto else ''} "
                f"es de {minima} días ({detalle}): {veredicto}.",
                citas[:1],
            )
        peor = min(faltan, key=lambda r: r["dias_cobertura"])
        region = next(
            d["region"]
            for d in BODEGAS.values()
            if d["nombre"] == peor["bodega"]
        )
        return _llamada("buscar_proveedores", producto=producto, region=region)

    def _tras_los_proveedores(self, resultados: dict) -> AIMessage:
        reservas = _json(resultados["consultar_reservas"].content).get(
            "reservas", []
        )
        producto_id = next(
            i
            for i, p in PRODUCTOS.items()
            if p["nombre"]
            == _json(resultados["consultar_reservas"].content)["producto"]
        )
        peor = min(reservas, key=lambda r: r["dias_cobertura"])
        bodega_id = next(
            i for i, d in BODEGAS.items() if d["nombre"] == peor["bodega"]
        )
        cantidad = max(
            math.ceil(
                peor["consumo_diario"] * PRODUCTOS[producto_id]["objetivo"]
                - peor["cantidad"]
            ),
            1,
        )
        items = _json(resultados["buscar_proveedores"].content).get("items", [])
        if len(items) < 3:
            return _final(
                f"Encontré solo {len(items)} proveedores de {producto_id}. "
                "¿Quieren que busque en otra región o amplío la búsqueda?"
            )
        if (
            self.disponibles
            and "registrar_orden_reposicion" not in self.disponibles
        ):
            # Todavía no hay herramienta para enviar la solicitud: el agente
            # solo presenta lo que encontró.
            lineas = []
            for n, item in enumerate(items[:3], 1):
                precio = _precio(item["extracto"])
                texto = (
                    f"${precio:,.0f} por unidad".replace(",", ".")
                    if precio is not None
                    else "precio por confirmar"
                )
                lineas.append(
                    f"{n}. {item['titulo'].split('|')[0].strip()} ({texto})"
                )
            return _final(
                f"Encontré tres proveedores de {producto_id}; la política indica "
                f"comprar {cantidad:g}: " + "; ".join(lineas) + ". No "
                "recomiendo ninguno: eligen ustedes."
            )
        return _llamada(
            "registrar_orden_reposicion",
            producto=producto_id,
            bodega=bodega_id,
            cantidad=cantidad,
        )
