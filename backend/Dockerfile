FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/pyproject.toml backend/README.md ./
COPY backend/api_compass ./api_compass

RUN pip install --upgrade pip \
    && pip install -e .[dev]

EXPOSE 8000

CMD ["uvicorn", "api_compass.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
