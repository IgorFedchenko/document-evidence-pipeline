FROM node:22-bookworm-slim AS frontend
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci --no-fund --no-audit
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY --from=ghcr.io/astral-sh/uv:0.9.2 /uv /usr/local/bin/uv
RUN uv sync --frozen --no-dev
COPY backend/ ./backend/
COPY --from=frontend /ui/dist ./static/
RUN useradd --create-home --uid 10001 app && mkdir -p /app/data /home/app/.cache \
    && chown -R app:app /app /home/app/.cache
USER app
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app/backend DATA_DIR=/app/data \
    OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
EXPOSE 8016
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8016", "--no-access-log"]
