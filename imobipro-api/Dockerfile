FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libpq para psycopg; as demais são dependências do WeasyPrint (PDFs a partir
# do Sprint 5) e do Pillow.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/

FROM base AS dev
RUN pip install -r requirements/dev.txt
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS prod
RUN pip install -r requirements/prod.txt
COPY . .
RUN adduser --disabled-password --gecos "" app && chown -R app /app
USER app
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", \
     "--workers", "3", "--worker-class", "gevent", "--timeout", "60"]
