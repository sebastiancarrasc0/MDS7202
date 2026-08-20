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
        # Su código aquí
        raise NotImplementedError(
            "Completen flip antes de ejecutar el programa."
        )

    def set_saturation(self, img_in: Imagen, C: float) -> Imagen:
        # Su código aquí
        raise NotImplementedError(
            "Completen set_saturation antes de ejecutar el programa."
        )

    def set_contrast(self, img_in: Imagen, C: float) -> Imagen:
        # Su código aquí
        raise NotImplementedError(
            "Completen set_contrast antes de ejecutar el programa."
        )

    def conv_channel(self, img_in: Imagen, kernel: np.ndarray) -> Imagen:
        """Por documentar (esto es parte del trabajo de la Etapa 6)."""
        # El cuerpo de este método lo entrega el curso.
        img = img_in.imagen
        img_out = []
        for i in range(img.shape[-1]):
            img_channel = convolve2d(
                img[:, :, i], kernel, mode="same", boundary="symm"
            )
            img_out.append(img_channel)
        new_image = np.stack(img_out, axis=2)
        new_image[new_image > 255], new_image[new_image < 0] = 255, 0
        return Imagen(new_image.astype(int))
