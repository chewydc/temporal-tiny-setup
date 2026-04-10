# Dockerfile para Lifecycle Worker
FROM python:3.11-slim

# Metadata
LABEL maintainer="temporal-lifecycle-demo"
LABEL version="1.0.0"

# Argumentos de build
ARG WORKER_VERSION=v1.0.0
ARG BUILD_TIME
ARG GIT_COMMIT

# Variables de entorno
ENV WORKER_VERSION=${WORKER_VERSION}
ENV BUILD_TIME=${BUILD_TIME}
ENV GIT_COMMIT=${GIT_COMMIT}
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY workflows/ ./workflows/
COPY activities/ ./activities/
COPY worker/ ./worker/

# Crear usuario no-root
RUN useradd --create-home --shell /bin/bash worker
RUN chown -R worker:worker /app
USER worker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import asyncio; from worker.lifecycle_worker import LifecycleWorker; \
    worker = LifecycleWorker(); \
    result = asyncio.run(worker.health_check()); \
    exit(0 if result else 1)"

# Exponer puerto para métricas (opcional)
EXPOSE 8080

# Comando por defecto
CMD ["python", "worker/lifecycle_worker.py"]