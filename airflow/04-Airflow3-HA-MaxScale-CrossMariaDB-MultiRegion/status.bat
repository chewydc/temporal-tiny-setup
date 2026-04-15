@echo off
echo ============================================================
echo  SITE STATUS
echo ============================================================
echo.

echo --- Healthcheck Hornos (sensor) ---
curl -s http://localhost:8001/health 2>nul | python -m json.tool 2>nul || echo   (not reachable)
echo.

echo --- Healthcheck SanLorenzo (sensor) ---
curl -s http://localhost:8002/health 2>nul | python -m json.tool 2>nul || echo   (not reachable)
echo.

echo --- Site Controller Hornos (actuator) ---
curl -s http://localhost:8011/health 2>nul | python -m json.tool 2>nul || echo   (not reachable)
echo.

echo --- Site Controller SanLorenzo (actuator) ---
curl -s http://localhost:8012/health 2>nul | python -m json.tool 2>nul || echo   (not reachable)
echo.

echo --- MaxScale Hornos (DB states) ---
curl -s -u admin:mariadb http://localhost:8989/v1/servers 2>nul | python -c "import sys,json; [print(f'  {s[\"id\"]}: {s[\"attributes\"][\"state\"]}') for s in json.load(sys.stdin)['data']]" 2>nul || echo   (not reachable)
echo.

echo --- Scheduler Container States ---
for %%c in (airflow-scheduler-hornos airflow-scheduler-sanlorenzo airflow-dag-processor-hornos airflow-dag-processor-sanlorenzo) do (
    for /f "tokens=*" %%s in ('docker inspect -f "{{.State.Status}} (paused={{.State.Paused}})" %%c 2^>nul') do echo   %%c: %%s
)
echo.

echo --- HAProxy ---
echo   http://localhost:8404/stats
echo.
