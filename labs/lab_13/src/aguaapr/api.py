"""Rutas de inferencia: información del modelo, vida y predicción."""

from fastapi import APIRouter, Depends

from .artifacts import a_tabla, predecir
from .constants import FEATURES, OPCIONALES, RANGOS
from .contracts import RespuestaPrediccion, Servicios
from .deps import crear_dependencia_clave
from .validation import MedicionAgua


def crear_router_inferencia(servicios: Servicios) -> APIRouter:
    """Construye el router con tres rutas.

    - `GET /`: describe el modelo. Responde las métricas de validación de la
      metadata, la entrada (cada columna con su rango) y la
      salida.
    - `GET /health`: ruta de vida, pública. Responde
      `{"estado": "ok"}`.
    - `POST /predict`: recibe una `MedicionAgua` en el cuerpo y responde una
      `RespuestaPrediccion` con la predicción y su probabilidad. Exige la
      clave de API con `crear_dependencia_clave`.
    """
    router = APIRouter()
    exigir_clave = crear_dependencia_clave(servicios)

    @router.get("/")
    def describir_modelo():
        return {
            "metricas_validacion": servicios.metadata["metricas_validacion"],
            "entrada": {
                columna: {
                    "minimo": RANGOS[columna][0],
                    "maximo": RANGOS[columna][1],
                    "opcional": columna in OPCIONALES,
                }
                for columna in FEATURES
            },
            "salida": {
                "prediccion": "1 si el agua es potable, 0 si no es potable",
                "probabilidad": "probabilidad estimada de que el agua sea potable",
            },
        }

    @router.get("/health")
    def health():
        return {"estado": "ok"}

    @router.post("/predict", response_model=RespuestaPrediccion)
    def predict(medicion: MedicionAgua, _: None = Depends(exigir_clave)):
        tabla = a_tabla([medicion])
        clases, probabilidades = predecir(servicios.modelo, tabla)
        return RespuestaPrediccion(
            prediccion=int(clases[0]), probabilidad=float(probabilidades[0])
        )

    return router
