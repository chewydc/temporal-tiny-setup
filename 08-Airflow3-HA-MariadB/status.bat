@echo off
echo ============================================================
echo ESTADO DE SERVICIOS - Airflow 3 HA PoC
echo ============================================================

echo.
echo === CONTAINERS ===
docker-compose ps

echo.
echo === SERVICIOS CLAVE ===
echo Verificando Airflow Web...
curl -s -o nul -w "Airflow Web: HTTP %%{http_code}" http://localhost:8080 2>nul || echo "Airflow Web: No disponible"
echo.
echo Verificando MaxScale GUI...
curl -s -o nul -w "MaxScale GUI: HTTP %%{http_code}" http://localhost:8989 2>nul || echo "MaxScale GUI: No disponible"

echo.
echo === MAXSCALE SERVERS ===
docker exec maxscale maxctrl list servers 2>nul || echo "MaxScale no disponible"

echo.
echo === LOGS RECIENTES ===
echo.
echo --- MariaDB Primary ---
docker-compose logs --tail=3 mariadb-primary

echo.
echo --- MaxScale ---
docker-compose logs --tail=3 maxscale

echo.
echo --- Airflow API Server ---
docker-compose logs --tail=5 airflow-api-server

echo.
echo ============================================================
echo ACCESOS:
echo - Airflow Web UI: http://localhost:8080
echo - MaxScale GUI: http://localhost:8989
echo.
echo Para ver logs en tiempo real: docker-compose logs -f airflow-api-server
echo ============================================================