@echo off
REM ============================================================================
REM GALERA CLUSTER - LIMPIEZA COMPLETA
REM ============================================================================

echo.
echo ============================================================================
echo LIMPIANDO GALERA CLUSTER
echo ============================================================================
echo.

echo Deteniendo todos los servicios...
docker-compose down -v

echo.
echo Eliminando contenedores relacionados...
docker rm -f galera-hornos galera-sanlorenzo galera-arbitrator vrouter cluster-monitor 2>nul
docker rm -f airflow-apiserver-hornos airflow-scheduler-hornos airflow-worker-hornos 2>nul
docker rm -f airflow-apiserver-sanlorenzo airflow-scheduler-sanlorenzo airflow-worker-sanlorenzo 2>nul
docker rm -f airflow-init-hornos airflow-init-sanlorenzo 2>nul
docker rm -f redis-hornos redis-sanlorenzo 2>nul

echo.
echo Eliminando volúmenes...
docker volume rm -f 09-airflow3-ha-galera-mariadb_galera-hornos-data 2>nul
docker volume rm -f 09-airflow3-ha-galera-mariadb_galera-sanlorenzo-data 2>nul
docker volume rm -f 09-airflow3-ha-galera-mariadb_airflow-logs 2>nul

echo.
echo Eliminando redes...
docker network rm -f 09-airflow3-ha-galera-mariadb_net-hornos 2>nul
docker network rm -f 09-airflow3-ha-galera-mariadb_net-sanlorenzo 2>nul
docker network rm -f 09-airflow3-ha-galera-mariadb_net-tucuman 2>nul

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

pause