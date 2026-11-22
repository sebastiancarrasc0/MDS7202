"""Contrato de entrada: las nueve mediciones de una muestra de agua."""

from pydantic import BaseModel, Field


class MedicionAgua(BaseModel):
    """Una muestra de agua: nueve mediciones químicas, cada una con su rango.

    Los rangos son los de la tabla del enunciado, con los límites incluidos.
    `ph`, `Sulfate` y `Trihalomethanes` pueden faltar (`None`) y su valor por
    defecto es `None`; las otras seis son obligatorias. Un valor fuera de su
    rango, o `nan`, se rechaza con un `ValidationError` que nombra el campo.
    """

    ph: float | None = Field(default=None, ge=0, le=14)
    Hardness: float = Field(ge=0, le=500)
    Solids: float = Field(ge=0, le=100_000)
    Chloramines: float = Field(ge=0, le=15)
    Sulfate: float | None = Field(default=None, ge=0, le=600)
    Conductivity: float = Field(ge=0, le=1_000)
    Organic_carbon: float = Field(ge=0, le=50)
    Trihalomethanes: float | None = Field(default=None, ge=0, le=200)
    Turbidity: float = Field(ge=0, le=10)
