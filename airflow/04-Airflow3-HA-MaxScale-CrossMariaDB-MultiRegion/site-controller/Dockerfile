FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY site_controller.py .
EXPOSE 8100
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8100/health || exit 1

# NOTA: Requiere montar docker.sock para controlar containers:
#   volumes:
#     - /var/run/docker.sock:/var/run/docker.sock:ro
CMD ["python", "site_controller.py"]
