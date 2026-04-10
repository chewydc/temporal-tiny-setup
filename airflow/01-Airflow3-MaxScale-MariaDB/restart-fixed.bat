@echo off
echo ============================================================================
echo REINICIANDO AIRFLOW 3.x + MAXSCALE + MARIADB - CORREGIDO
echo ============================================================================

echo Deteniendo contenedores...
docker-compose down -v

echo Eliminando volúmenes...
docker volume prune -f

echo Eliminando imágenes huérfanas...
docker image prune -f

echo Iniciando servicios corregidos...
docker-compose up -d

echo ============================================================================
echo SERVICIOS INICIADOS - ESPERANDO INICIALIZACIÓN...
echo ============================================================================
echo Airflow Web UI: http://localhost:8080
echo MaxScale Admin: http://localhost:8989
echo ============================================================================