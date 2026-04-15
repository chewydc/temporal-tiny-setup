@echo off
echo ============================================================
echo  AIRFLOW MULTI-SITE ACTIVE/PASSIVE HA
echo ============================================================
echo.
echo  Hornos     = initial ACTIVE  (DB primary + scheduler ON)
echo  SanLorenzo = initial PASSIVE (DB replica + scheduler OFF)
echo.
echo  Services per region:
echo    - Healthcheck (sensor)       port 8000
echo    - Site Controller (actuator) port 8100
echo ============================================================

echo [1/4] Cleaning previous state...
docker-compose down -v --remove-orphans 2>nul

echo [2/4] Starting all services...
docker-compose up -d --build

echo [3/4] Waiting for schedulers to start (30s)...
timeout /t 30 /nobreak >nul

echo [4/4] Pausing PASSIVE region schedulers (San Lorenzo)...
docker pause airflow-scheduler-sanlorenzo
docker pause airflow-dag-processor-sanlorenzo

echo.
echo ============================================================
echo  READY
echo ============================================================
echo.
echo  Airflow UI (HAProxy):        http://localhost:8080
echo  HAProxy Stats:               http://localhost:8404/stats
echo.
echo  Healthcheck Hornos:          http://localhost:8001/health
echo  Healthcheck SanLorenzo:      http://localhost:8002/health
echo.
echo  Site Controller Hornos:      http://localhost:8011/health
echo  Site Controller SanLorenzo:  http://localhost:8012/health
echo.
echo  Direct Hornos:               http://localhost:8081
echo  Direct SanLorenzo:           http://localhost:8082
echo.
echo  To test failover (DB failure):
echo    docker pause mariadb-hornos
echo.
echo  To test failover (Airflow failure):
echo    docker stop airflow-apiserver-hornos
echo    (site-controller will force DB switchover after ~50s)
echo.
