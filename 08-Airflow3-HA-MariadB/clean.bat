@echo off
echo Deteniendo y limpiando Airflow 3 HA PoC...
docker-compose down -v --remove-orphans
docker system prune -f
echo Limpieza completa.