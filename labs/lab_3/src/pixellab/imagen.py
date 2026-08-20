"""Clase ``Imagen``: contenedor de imágenes sobre el que se opera con NumPy."""

from __future__ import annotations

import numpy as np


class Imagen:
    """Contenedor de imágenes RGB.

    Completen el constructor y los operadores de esta clase siguiendo el
    contrato del enunciado y los tests de ``tests/test_imagen.py``.
    """

    def __init__(self, img: np.ndarray) -> None:
        if not isinstance(img, np.ndarray):
            raise TypeError(
                "Debes entregar un arreglo de numpy como argumento del constructor de Imagen."
            )
        if img.ndim != 3 or img.shape[-1] != 3:
            raise ValueError("no calzan")
        self.imagen = img

    def __add__(self, other: int | float | np.ndarray | Imagen) -> Imagen:
        if (
            isinstance(other, np.ndarray) and other.shape != self.imagen.shape
        ) or (
            isinstance(other, Imagen)
            and other.imagen.shape != self.imagen.shape
        ):
            raise ValueError("no calzan")
        res = np.copy(
            self.imagen + (other.imagen if isinstance(other, Imagen) else other)
        )
        res[res > 255] = 255
        res[res < 0] = 0
        return Imagen(res.astype(int))

    def __radd__(self, other: int | float | np.ndarray | Imagen) -> Imagen:
        return self.__add__(other)

    def __sub__(self, other: int | float | np.ndarray | Imagen) -> Imagen:
        other_img = -1 * (other.imagen if isinstance(other, Imagen) else other)
        return self.__add__(other_img)

    def __rsub__(self, other: int | float | np.ndarray | Imagen) -> Imagen:
        if (
            isinstance(other, np.ndarray) and other.shape != self.imagen.shape
        ) or (
            isinstance(other, Imagen)
            and other.imagen.shape != self.imagen.shape
        ):
            raise ValueError("no calzan")
        res = np.copy(
            (other.imagen if isinstance(other, Imagen) else other) - self.imagen
        )
        res[res > 255] = 255
        res[res < 0] = 0
        return Imagen(res.astype(int))

    def __mul__(self, other: int | float | np.ndarray | Imagen) -> Imagen:
        if (
            isinstance(other, np.ndarray) and other.shape != self.imagen.shape
        ) or (
            isinstance(other, Imagen)
            and other.imagen.shape != self.imagen.shape
        ):
            raise ValueError("no calzan")
        res = np.copy(
            self.imagen * (other.imagen if isinstance(other, Imagen) else other)
        )
        res[res > 255] = 255
        res[res < 0] = 0
        return Imagen(res.astype(int))

    def __rmul__(self, other: int | float | np.ndarray | Imagen) -> Imagen:
        return self.__mul__(other)
