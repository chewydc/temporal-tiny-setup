@echo off
REM ============================================================================
REM AIRFLOW 3.x HA + MAXSCALE - LIMPIEZA COMPLETA
REM ============================================================================

echo.
echo ============================================================================
echo LIMPIANDO AIRFLOW 3.x HA + MAXSCALE
echo ============================================================================
echo.

echo Deteniendo todos los servicios...
docker compose down -v --remove-orphans

echo.
echo Eliminando contenedores relacionados...
docker rm -f mariadb-primary mariadb-replica mariadb-arbitrator 2>nul
docker rm -f maxscale-hornos maxscale-sanlorenzo 2>nul
docker rm -f airflow-apiserver airflow-scheduler airflow-dag-processor 2>nul
docker rm -f airflow-worker-hornos airflow-worker-sanlorenzo airflow-init redis 2>nul
docker rm -f vrouter cluster-monitor 2>nul

echo.
echo Eliminando volúmenes...
docker volume rm -f 09-airflow3-ha-mariadb-maxscaleconarbitro_mariadb-primary-data 2>nul
docker volume rm -f 09-airflow3-ha-mariadb-maxscaleconarbitro_mariadb-replica-data 2>nul
docker volume rm -f 09-airflow3-ha-mariadb-maxscaleconarbitro_mariadb-arbitrator-data 2>nul
docker volume rm -f 09-airflow3-ha-mariadb-maxscaleconarbitro_airflow-logs 2>nul

echo.
echo Eliminando redes...
docker network rm -f 09-airflow3-ha-mariadb-maxscaleconarbitro_net-hornos 2>nul
docker network rm -f 09-airflow3-ha-mariadb-maxscaleconarbitro_net-sanlorenzo 2>nul
docker network rm -f 09-airflow3-ha-mariadb-maxscaleconarbitro_net-tucuman 2>nul

echo.
echo Limpiando imágenes no utilizadas...
docker image prune -f

echo.
echo ============================================================================
echo LIMPIEZA COMPLETA
echo ============================================================================
echo.
echo El cluster ha sido completamente eliminado.
echo Para reiniciar, ejecuta: start.bat
echo.
