@echo off
echo ============================================================
echo Airflow 3 HA + 3 Regiones - MariaDB + MaxScale
echo ============================================================

echo Limpiando containers anteriores...
docker compose down -v --remove-orphans > nul 2>&1

echo Iniciando stack completo...
docker compose up -d

echo Esperando que Airflow este completamente listo...
ping -n 30 127.0.0.1 > nul

echo ============================================================
echo STACK INICIADO EXITOSAMENTE
echo ============================================================
echo Accesos disponibles:
echo - Airflow Web UI: http://localhost:8080
echo - MaxScale Hornos: http://localhost:8989 (puerto 4006)
echo - MaxScale San Lorenzo: http://localhost:8990 (puerto 4007)
echo ============================================================

echo Estado final de containers:
docker compose ps

echo ============================================================
echo Para monitorear: docker compose logs -f airflow-apiserver
echo Para verificar estado: status.bat
echo Para control de red: network-control.bat
echo ============================================================