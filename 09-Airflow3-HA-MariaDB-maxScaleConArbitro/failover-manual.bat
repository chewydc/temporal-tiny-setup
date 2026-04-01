@echo off
echo ============================================================
echo MANUAL FAILOVER SCRIPT - CASO 09
echo ============================================================

echo.
echo Detectando estado actual de MaxScale...
docker exec maxscale-hornos maxctrl list servers

echo.
echo ¿Deseas ejecutar failover manual? (S/N)
set /p choice=

if /i "%choice%"=="S" (
    echo.
    echo Ejecutando failover manual...
    
    echo 1. Deteniendo mariadb-hornos si está corriendo...
    docker stop mariadb-hornos 2>nul
    
    echo 2. Promoviendo mariadb-sanlorenzo a Master...
    docker exec mariadb-sanlorenzo mysql -u root -proot_pass -e "STOP SLAVE; RESET SLAVE ALL; SET GLOBAL read_only = OFF;"
    
    echo 3. Configurando mariadb-tucuman para replicar desde sanlorenzo...
    docker exec mariadb-tucuman mysql -u root -proot_pass -e "STOP SLAVE; RESET SLAVE; CHANGE MASTER TO MASTER_HOST='172.21.0.20', MASTER_PORT=3306, MASTER_USER='repl_user', MASTER_PASSWORD='repl_pass', MASTER_USE_GTID=slave_pos; START SLAVE;"
    
    echo 4. Esperando sincronización...
    timeout /t 10 /nobreak > nul
    
    echo 5. Verificando nuevo estado...
    docker exec maxscale-hornos maxctrl list servers
    
    echo.
    echo Failover completado!
) else (
    echo Operación cancelada.
)

echo.
pause