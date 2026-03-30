@echo off
echo ============================================================
echo Airflow 3 HA PoC - MariaDB + MaxScale
echo ============================================================

if not exist airflow.cfg (
    echo Creando airflow.cfg desde ejemplo...
    copy airflow.cfg.example airflow.cfg > nul
)
if not exist .env (
    echo Creando .env desde ejemplo...
    copy .env.example .env > nul
)

echo Limpiando containers anteriores...
docker compose down -v --remove-orphans > nul 2>&1

echo Iniciando stack completo...
docker compose up -d

echo Esperando que Airflow este completamente listo...
ping -n 45 127.0.0.1 > nul

echo ============================================================
echo STACK INICIADO EXITOSAMENTE
echo ============================================================
echo Accesos disponibles:
echo - Airflow Web UI: http://localhost:8080
echo - MaxScale GUI:   http://localhost:8989
echo ============================================================

echo Estado final de containers:
docker compose ps

echo ============================================================
echo Para monitorear: docker compose logs -f airflow-apiserver
echo Para verificar estado: status.bat
echo ============================================================
