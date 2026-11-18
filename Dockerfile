FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        ffmpeg \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
ARG REQUIREMENTS_FILE=requirements/prod.txt
RUN pip install --upgrade pip && pip install -r ${REQUIREMENTS_FILE}

COPY . .

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/staticfiles /app/media /app/logs \
    && chmod +x docker/render/start-combined.sh \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Commande par défaut, utilisée par les hébergeurs à service unique (ex: Render) où web et worker
# Celery doivent partager le même conteneur/disque — voir docker/render/start-combined.sh.
# docker-compose.yml définit sa propre "command:" pour chaque service (web/celery_worker/celery_beat)
# et n'utilise donc jamais cette valeur par défaut.
CMD ["./docker/render/start-combined.sh"]
