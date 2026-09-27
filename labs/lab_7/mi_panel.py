"""Andamiaje del panel de la Parte 2. Renómbrenlo si quieren.

MATERIAL PROVISTO. Lo que ya está escrito acá —los imports, la configuración
de la página y el cargador de datos— es infraestructura y no se evalúa: son
las mismas líneas para cualquier panel sobre este dataset. Lo que sí se evalúa
son las cuatro secciones de más abajo.

Las secciones están en un orden que funciona, pero no es obligatorio:
reordenarlas o renombrarlas no descuenta. Lo que se corrige es que las cuatro
cosas estén y que cada gráfico explique por qué está ahí.

Para trabajar:

    uv run streamlit run mi_panel.py

Streamlit reejecuta el archivo completo cada vez que alguien mueve un control,
así que el navegador se actualiza solo al guardar.
"""

from pathlib import Path

import plotly.express as px
import polars as pl
import streamlit as st

RUTA_DATOS = Path(__file__).parent / "data" / "raw" / "penguins.csv"

st.set_page_config(
    page_title="Pingüinos de Palmer", page_icon="🐧", layout="wide"
)
st.title("🐧 Pingüinos del archipiélago de Palmer")


@st.cache_data
def cargar_datos() -> pl.DataFrame:
    """Lee el CSV sin modificarlo.

    `null_values=["NA"]` es necesario: el archivo viene de R, donde `NA` marca
    los faltantes. Sin ese argumento, polars lee las columnas numéricas como
    texto. Con él, los nulos quedan adentro — que es lo que queremos, porque
    este laboratorio no limpia nada.
    """
    return pl.read_csv(RUTA_DATOS, null_values=["NA"])


df = cargar_datos()


# --- 1) La tabla interactiva -----------------------------------------------
#
# Una tabla con el dataset que el lector pueda ordenar por cualquier columna y
# filtrar con al menos dos controles: uno categórico y uno de rango numérico.
# Esos mismos filtros deben afectar también a los cuatro gráficos. Los
# registros sin valor en la columna del filtro numérico quedan fuera de la
# selección filtrada. Si ningún registro cumple los filtros, muestren un aviso.
#
# Ordenar y buscar los trae `st.dataframe` de fábrica, sin programar nada.
# Filtrar no: los controles devuelven la selección y ustedes filtran el
# DataFrame antes de pasárselo a la tabla. Denle formato a las columnas, que
# `flipper_length_mm` no es un encabezado para mostrarle a un cliente.
#
#   https://docs.streamlit.io/develop/api-reference/data/st.dataframe
#   https://docs.streamlit.io/develop/api-reference/data/st.column_config
#   https://docs.streamlit.io/develop/api-reference/widgets/st.multiselect
#   https://docs.streamlit.io/develop/api-reference/widgets/st.slider

st.subheader("Explorando los datos")

col_filtro_1, col_filtro_2 = st.columns(2)

with col_filtro_1:
    especies_elegidas = st.multiselect(
        "Especie",
        options=sorted(df["species"].unique()),
        default=sorted(df["species"].unique()),
    )

with col_filtro_2:
    masa_min = int(df["body_mass_g"].min())
    masa_max = int(df["body_mass_g"].max())
    rango_masa = st.slider(
        "Masa corporal (g)",
        min_value=masa_min,
        max_value=masa_max,
        value=(masa_min, masa_max),
    )

df_filtrado = df.filter(
    pl.col("species").is_in(especies_elegidas)
    & pl.col("body_mass_g").is_between(rango_masa[0], rango_masa[1])
)

if df_filtrado.height == 0:
    st.warning("Ningún pingüino cumple con los filtros seleccionados.")
else:
    st.dataframe(
        df_filtrado,
        column_config={
            "species": "Especie",
            "island": "Isla",
            "sex": "Sexo",
            "culmen_length_mm": st.column_config.NumberColumn(
                "Largo de pico", format="%.1f mm"
            ),
            "culmen_depth_mm": st.column_config.NumberColumn(
                "Profundidad de pico", format="%.1f mm"
            ),
            "flipper_length_mm": st.column_config.NumberColumn(
                "Largo de aleta", format="%d mm"
            ),
            "body_mass_g": st.column_config.NumberColumn(
                "Masa corporal", format="%d g"
            ),
        },
        hide_index=True,
    )


# --- 2) La calidad de los datos --------------------------------------------
#
# Un informe visible en la página, calculado sobre el CSV completo aunque se
# apliquen filtros: qué columnas tienen nulos y cuántos, cuál es el valor
# inesperado de `sex` y cómo pueden afectar esos problemas los recuentos,
# filtros o gráficos del panel.
#
# Las cifras se calculan desde `df`, no se escriben a mano: si el
# archivo cambiara, un número escrito a mano queda mintiendo.
#
#   https://docs.streamlit.io/develop/api-reference/status/st.warning

st.subheader("Calidad de los datos")

nulos_por_columna = (
    df.null_count()
    .transpose(
        include_header=True, header_name="columna", column_names=["nulos"]
    )
    .filter(pl.col("nulos") > 0)
)

cantidad_punto = df.filter(pl.col("sex") == ".").height

col_calidad_1, col_calidad_2 = st.columns(2)

with col_calidad_1:
    st.caption(
        "Valores nulos por columna (sobre las "
        f"{df.height} filas del dataset completo, sin filtrar):"
    )
    st.dataframe(nulos_por_columna, hide_index=True)

with col_calidad_2:
    st.warning(
        f"La columna `sex` tiene {cantidad_punto} registro(s) con el valor "
        '"." en vez de MALE/FEMALE, y esto no se corrige en este panel.'
    )
    st.caption(
        "Estos problemas afectan al resto del panel: filas con nulos en la "
        "columna del filtro numérico quedan fuera de la tabla y de los "
        'gráficos de forma automática; y el valor "." en sex aparece como '
        "una tercera categoría más en cualquier gráfico que agrupe por sexo, "
        "en vez de tratarse como dato faltante."
    )


# --- 3) Los cuatro gráficos ------------------------------------------------
#
# Cuatro gráficos a elección, de al menos dos tipos distintos. Pueden reusar
# los de la Parte 1 o construir otros. Van a necesitar `plotly.express`:
# impórtenlo arriba, con el resto.
#
# Cada gráfico lleva, JUNTO A ÉL Y VISIBLE EN LA PÁGINA, por qué esa
# información es útil y por qué eligieron esa visualización. Un comentario en
# el código no cuenta: quien abre el panel no lee el código.
#
#   https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart
#   https://docs.streamlit.io/develop/api-reference/text/st.caption
#   https://docs.streamlit.io/develop/api-reference/layout/st.columns

st.subheader("Gráficos")

if df_filtrado.height == 0:
    st.info("Ajusta los filtros de arriba para ver los gráficos.")
else:
    fila_1_col_1, fila_1_col_2 = st.columns(2)
    fila_2_col_1, fila_2_col_2 = st.columns(2)

    with fila_1_col_1:
        fig_scatter = px.scatter(
            df_filtrado,
            x="flipper_length_mm",
            y="body_mass_g",
            color="species",
            labels={
                "flipper_length_mm": "Largo de aleta (mm)",
                "body_mass_g": "Masa corporal (g)",
                "species": "Especie",
            },
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.caption(
            "Scatter: relación entre tamaño de aleta y masa corporal. "
            "Sirve para ver si el tamaño de un pingüino se puede predecir a "
            "partir de una sola medida externa, y si esa relación cambia "
            "entre especies."
        )

    with fila_1_col_2:
        fig_hist = px.histogram(
            df_filtrado,
            x="body_mass_g",
            color="species",
            barmode="overlay",
            opacity=0.6,
            marginal="violin",
            labels={"body_mass_g": "Masa corporal (g)", "species": "Especie"},
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        st.caption(
            "Histograma con violín: muestra la forma completa de la "
            "distribución de masa por especie, no solo el promedio. Esto "
            "revela si hay superposición entre especies o si están bien "
            "separadas."
        )

    with fila_2_col_1:
        fig_caja = px.box(
            df_filtrado,
            x="species",
            y="body_mass_g",
            color="species",
            labels={"body_mass_g": "Masa corporal (g)", "species": "Especie"},
        )
        st.plotly_chart(fig_caja, use_container_width=True)
        st.caption(
            "Caja: mediana, cuartiles y outliers de masa por especie. Complementa al "
            "histograma cuando lo que importa es un número preciso y no la "
            "forma de la curva."
        )

    with fila_2_col_2:
        masa_por_especie_filtrada = (
            df_filtrado.group_by("species")
            .agg(pl.col("body_mass_g").mean().alias("masa_promedio"))
            .sort("species")
        )
        fig_barras = px.bar(
            masa_por_especie_filtrada,
            x="species",
            y="masa_promedio",
            labels={
                "masa_promedio": "Masa corporal promedio (g)",
                "species": "Especie",
            },
        )
        st.plotly_chart(fig_barras, use_container_width=True)
        st.caption(
            "Barras: resumen de un solo número por especie. Es "
            "útil para una comparación rápida cuando no hace falta ver toda "
            "la distribución, solo cuál especie pesa más en promedio."
        )


# --- 4) El tema --------------------------------------------------------------
#
# Este no se programa acá: vive en `.streamlit/config.toml`, al lado de este
# archivo. Ya existe, con las claves comentadas — descoméntenlas y decidan sus
# colores.
#
# Para comprobar que el suyo está haciendo algo: renombren el archivo,
# reinicien el panel y vean si cambia. Si no cambia, no lo configuraron.
#
#   https://docs.streamlit.io/develop/concepts/configuration/theming
