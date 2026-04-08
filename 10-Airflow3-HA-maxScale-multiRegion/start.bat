@echo off
echo ============================================================================
echo AIRFLOW 3 HA - MARIADB + MAXSCALE + MULTI REGION
echo ============================================================================

echo Limpiando containers anteriores...
docker compose down -v --remove-orphans > nul 2>&1

echo Iniciando servicios...
docker compose up -d

echo.
echo Esperando que los servicios esten listos...
timeout /t 25 /nobreak

echo.
echo Estado de los servicios:
docker compose ps

echo.
echo ============================================================================
echo ACCESOS:
echo ============================================================================
echo Airflow Web UI: http://localhost:8080 (admin/admin)
echo MaxScale Hornos: http://localhost:8989 (admin/mariadb)
echo MaxScale San Lorenzo: http://localhost:8990 (admin/mariadb)
echo.
echo MariaDB Hornos (Primary): localhost:3306
echo MariaDB San Lorenzo (Replica): localhost:3307  
echo MariaDB Tucuman (Arbitrator): localhost:3308
echo.
echo MaxScale Hornos: localhost:4006
echo MaxScale San Lorenzo: localhost:4007
echo ============================================================================