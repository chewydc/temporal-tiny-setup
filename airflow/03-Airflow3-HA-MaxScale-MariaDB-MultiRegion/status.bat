@echo off
echo ============================================================================
echo ESTADO DEL CLUSTER MULTI-REGION AIRFLOW 3.x HA
echo ============================================================================

echo.
echo === MAXSCALE HORNOS - ESTADO DE SERVIDORES ===
docker-compose exec maxscale-hornos maxctrl list servers

echo.
echo === MAXSCALE SAN LORENZO - ESTADO DE SERVIDORES ===
docker exec maxscale-sanlorenzo maxctrl --hosts=127.0.0.1:8990 list servers

echo ============================================================================
echo Accesos:
echo - HAProxy Stats: http://localhost:8404/stats
echo - Airflow UI: http://localhost:8080
echo   - Hornos directo: http://localhost:8081
echo   - San Lorenzo directo: http://localhost:8082
echo ============================================================================
