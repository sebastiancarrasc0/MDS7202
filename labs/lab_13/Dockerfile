FROM python:3.13-slim

# uv desde su imagen oficial
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /usr/local/bin/uv

# Sin caché de uv en la capa
ENV UV_NO_CACHE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencias (solo el grupo "servicio")
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --only-group servicio --no-install-project

# Dependencias del proyecto (la app como tal)
COPY src ./src

# Usuario sin privilegios
RUN useradd --system --create-home appuser
USER appuser

EXPOSE 8000 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["bash", "-c", "uvicorn src.aguaapr.main:app --host 0.0.0.0 --port 8000 & streamlit run src/aguaapr/ui.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false & wait -n"]
