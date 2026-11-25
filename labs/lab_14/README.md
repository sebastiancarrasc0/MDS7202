# Laboratorio 14 — Agentes de logística alimentaria

Desde la raíz del laboratorio, instalen las dependencias **antes de la sesión**; es lo único que hay que preparar de antemano. La instalación descarga cerca de 1 GB:

```bash
uv sync --locked --all-groups
```

Este laboratorio necesita dos cuentas gratuitas por pareja, que el notebook pide crear en la etapa que las usa: una de **OpenRouter** (da acceso a los modelos de lenguaje), en la etapa 0, y una de **Tavily** (el buscador web del agente), en la etapa 3. Las llaves van en un archivo `.env`, que se crea copiando `.env.example`; ese archivo no se sube a Git.

Durante la sesión trabajan con tres terminales abiertas (el notebook indica cuándo encender cada una) en esta carpeta, además del notebook:

```bash
uv run uvicorn src.reposicion.servidor.app:app --port 8100   # API de bodegas
uv run phoenix serve                                        # trazas, en http://localhost:6006
uv run streamlit run src/reposicion/ui/app.py               # interfaz, en http://localhost:8501
```

El trabajo se hace en `notebooks/Lab14_Enunciado.ipynb` y en los módulos de `src/reposicion/` marcados como pendientes; el resto de `src/reposicion/` viene hecho, incluida la interfaz. Después de completar cada etapa, ejecuten sus pruebas:

```bash
uv run pytest -m etapa0
uv run pytest -m etapa1
uv run pytest -m etapa2
uv run pytest -m etapa3
uv run pytest -m etapa4   # bonus: no suma al puntaje
```

Ninguna prueba usa red, llaves ni cuota. Lo que solo se comprueba con el modelo real (una respuesta del agente, una traza en Phoenix) se verifica a mano, según indica cada recuadro de comprobación del notebook. Una cuenta gratuita de OpenRouter permite 50 solicitudes por día; si la agotan, agreguen `REPOSICION_MODO=simulado` al `.env` para seguir con un modelo de reglas que no gasta cuota.

Los datos y las políticas, ficticios, están descritos en `data/raw/README.md`.
