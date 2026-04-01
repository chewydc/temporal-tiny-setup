@echo off
echo ============================================================
echo ESTADO DE SERVICIOS - Airflow 3 HA + 3 Regiones
echo ============================================================

echo === SERVICIOS CLAVE ===
echo Verificando Airflow Web...
curl -s -o nul -w "Airflow Web: HTTP %%{http_code}" http://localhost:8080 2>nul || echo "Airflow Web: No disponible"
echo.
echo Verificando MaxScale Hornos...
curl -s -o nul -w "MaxScale Hornos: HTTP %%{http_code}" http://localhost:8989 2>nul || echo "MaxScale Hornos: No disponible"
echo.
echo Verificando MaxScale San Lorenzo...
curl -s -o nul -w "MaxScale San Lorenzo: HTTP %%{http_code}" http://localhost:8990 2>nul || echo "MaxScale San Lorenzo: No disponible"

echo.
echo === MAXSCALE SERVERS ===
echo --- MaxScale Hornos ---
docker exec maxscale-hornos maxctrl list servers 2>nul || echo "MaxScale Hornos no disponible"
echo.
echo --- MaxScale San Lorenzo ---
docker exec maxscale-sanlorenzo maxctrl list servers 2>nul || echo "MaxScale San Lorenzo no disponible"

echo.
echo ============================================================
echo ACCESOS:
echo - Airflow Web UI: http://localhost:8080
echo - MaxScale Hornos: http://localhost:8989 (puerto 4006)
echo - MaxScale San Lorenzo: http://localhost:8990 (puerto 4007)
echo.
echo Para logs en tiempo real: docker compose logs -f airflow-apiserver
echo ============================================================