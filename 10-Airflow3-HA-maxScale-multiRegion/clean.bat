@echo off
echo ============================================================================
echo LIMPIEZA COMPLETA DEL ENTORNO HA
echo ============================================================================

echo Deteniendo y eliminando contenedores...
docker-compose down -v

echo.
echo Eliminando imagenes no utilizadas...
docker image prune -f

echo.
echo Eliminando volumenes huerfanos...
docker volume prune -f

echo.
echo Limpieza completada.
echo ============================================================================