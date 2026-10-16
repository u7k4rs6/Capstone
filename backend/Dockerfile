FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser

COPY requirements.txt .
# pip is only needed at build time. Removing it drops its vendored libs from the Trivy scan.
RUN pip install -r requirements.txt && pip uninstall -y pip

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

USER 10001
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
