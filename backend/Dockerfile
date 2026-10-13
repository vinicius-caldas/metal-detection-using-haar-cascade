FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# opencv-python-headless dispensa libGL; libglib2.0 ainda é exigida em runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY training ./training

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/storage /app/models \
    && chown -R appuser:appuser /app
USER appuser

ENV STORAGE_DIR=/app/storage \
    CASCADE_PATH=/app/models/cascade.xml

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# 1 worker uvicorn: o paralelismo de CPU vem do ThreadPoolExecutor interno
# (OpenCV libera o GIL), mantendo um único processo dono do SQLite.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
