"""Operaciones de procesamiento de imágenes para completar."""

from __future__ import annotations

import numpy as np
from scipy.signal import convolve2d

from src.pixellab.imagen import Imagen


class LibImagen:
    """Filtros y transformaciones que reciben y retornan ``Imagen``."""

    def to_negative(self, img_in: Imagen) -> Imagen:
        res = 255 - np.copy(img_in.imagen)
        res[res > 255] = 255
        res[res < 0] = 0
        return Imagen(res.astype(int))

    def to_gray(self, img_in: Imagen) -> Imagen:
        img = np.copy(img_in.imagen)
        img_gray = (img @ np.array([0.299, 0.587, 0.114])).astype(int)
        img_gray = np.stack([img_gray, img_gray, img_gray], axis=2)
        return Imagen(img_gray)

    def get_channel(self, img_in: Imagen, channel: str) -> Imagen:
        if channel not in ["r", "g", "b"]:
            raise ValueError(
                "Canal 'x' no válido. Valores posibles: 'r', 'g' o 'b'."
            )
        zeros = np.zeros_like(img_in.imagen)
        idx = {"r": 0, "g": 1, "b": 2}[channel]
        zeros[:, :, idx] = np.copy(img_in.imagen[:, :, idx])
        return Imagen(zeros.astype(int))

    def flip(self, img_in: Imagen, axis: str) -> Imagen:
        if axis == "h":
            resultado = img_in.imagen[:, ::-1, :]
        elif axis == "v":
            resultado = img_in.imagen[::-1, :, :]
        else:
            raise ValueError(
                f"Eje '{axis}' no válido. Valores posibles: 'h' (horizontal) o 'v' (vertical)."
            )
        return Imagen(resultado.astype(int))

    def set_saturation(self, img_in: Imagen, C: float) -> Imagen:
        img = np.copy(img_in.imagen)
        gris = self.to_gray(img_in).imagen
        resultado = gris + C * (img - gris)
        resultado = resultado.astype(int)
        resultado[resultado > 255] = 255
        resultado[resultado < 0] = 0
        return Imagen(resultado)

    def set_contrast(self, img_in: Imagen, C: float) -> Imagen:
        img = np.copy(img_in.imagen)
        F = 259 * (C + 255) / (255 * (259 - C))
        resultado = F * (img - 128) + 128
        resultado = resultado.astype(int)
        resultado[resultado > 255] = 255
        resultado[resultado < 0] = 0
        return Imagen(resultado)

    def conv_channel(self, img_in: Imagen, kernel: np.ndarray) -> Imagen:
        """
        La convolución es una operación matemática. Consiste en aplicar un kernel
        (una matriz de números) a toda la imagen para obtener una nueva que puede tener
        diferentes efectos, como desenfoque, detección de bordes, etc.

        La convolución recorre cada píxel de la imagen y aplica el kernel a los vecinos y
        suma los resultados para obtener el nuevo valor del píxel. Aplicar esto
        a toda la imagen es lo que genera la nueva imagen transformada.

        """

        img = np.copy(img_in.imagen)
        img_out = []
        for i in range(img.shape[-1]):
            img_channel = convolve2d(
                img[:, :, i], kernel, mode="same", boundary="symm"
            )
            img_out.append(img_channel)
        new_image = np.stack(img_out, axis=2)
        new_image[new_image > 255], new_image[new_image < 0] = 255, 0
        return Imagen(new_image.astype(int))
