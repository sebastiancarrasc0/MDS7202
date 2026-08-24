"""Kernels de convolución que deben definir para la Etapa 6."""

import numpy as np

KERNELS: list[tuple[str, np.ndarray]] = [
    # Identidad: el centro pesa 1 y el resto 0.
    # La imagen queda igual
    (
        "identidad",
        np.array(
            [
                [0, 0, 0],
                [0, 1, 0],
                [0, 0, 0],
            ]
        ),
    ),
    # Laplaciano: mide la diferencia entre un pixel y los vecinos.
    # Sirve para detectar bordes y cambios de intensidad.
    (
        "laplaciano",
        np.array(
            [
                [0, 1, 0],
                [1, -4, 1],
                [0, 1, 0],
            ]
        ),
    ),
    # Enfoque: acentúa los bordes que detecta el laplaciano,
    # sin perder la información de la imagen orginal
    (
        "enfoque",
        np.array(
            [
                [0, -1, 0],
                [-1, 5, -1],
                [0, -1, 0],
            ]
        ),
    ),
    # Desenfoque: promedio simple de los vecinos.
    # Suaviza la imagen y reduce el ruido.
    (
        "desenfoque",
        np.array(
            [
                [1 / 9, 1 / 9, 1 / 9],
                [1 / 9, 1 / 9, 1 / 9],
                [1 / 9, 1 / 9, 1 / 9],
            ]
        ),
    ),
    # Relieve: esos antisimétricos en diagonal; resalta bordes
    # en esa dirección y da apariencia de relieve/grabado en gris.
    (
        "relieve",
        np.array(
            [
                [-1, -1, 0],
                [-1, 0, 1],
                [0, 1, 1],
            ]
        ),
    ),
]
