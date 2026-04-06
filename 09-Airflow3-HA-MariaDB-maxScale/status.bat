@echo off
echo ============================================================================
echo ESTADO DEL CLUSTER HA
echo ============================================================================

echo.
echo === CONTENEDORES ===
docker-compose ps

echo.
echo === MAXSCALE HORNOS - ESTADO DE SERVIDORES ===
docker-compose exec maxscale-hornos maxctrl list servers

echo.
echo === MAXSCALE SAN LORENZO - ESTADO DE SERVIDORES ===
docker-compose exec maxscale-sanlorenzo maxctrl list servers

echo.
echo === REPLICACIÓN MARIADB SAN LORENZO ===
docker-compose exec mariadb-sanlorenzo mysql -u root -proot_pass -e "SHOW SLAVE STATUS\G" | findstr "Slave_IO_Running\|Slave_SQL_Running\|Master_Host\|Seconds_Behind_Master"

echo.
echo === REPLICACIÓN MARIADB TUCUMAN ===
docker-compose exec mariadb-tucuman mysql -u root -proot_pass -e "SHOW SLAVE STATUS\G" | findstr "Slave_IO_Running\|Slave_SQL_Running\|Master_Host\|Seconds_Behind_Master"

echo.
echo ============================================================================
echo PARA PROBAR FAILOVER MANUAL:
echo   docker-compose stop mariadb-hornos
echo   docker-compose start mariadb-hornos
echo ============================================================================

pause