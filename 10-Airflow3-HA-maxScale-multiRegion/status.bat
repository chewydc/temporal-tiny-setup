@echo off
echo ============================================================================
echo ESTADO DEL CLUSTER HA
echo ============================================================================

echo.
echo === MAXSCALE HORNOS - ESTADO DE SERVIDORES ===
docker-compose exec maxscale-hornos maxctrl list servers

echo.
echo === MAXSCALE SAN LORENZO - ESTADO DE SERVIDORES ===
docker exec maxscale-sanlorenzo maxctrl --hosts=127.0.0.1:8990 list servers

echo.
echo === REPLICACION MARIADB HORNOS ===
docker-compose exec mariadb-hornos mysql -u root -proot_pass -e "SELECT 'IO_Running:', IF(@@read_only=1,'Slave','Master') as Role; SHOW SLAVE STATUS\G" 2>nul | findstr /C:"Slave_IO_Running" /C:"Slave_SQL_Running" /C:"Master_Host" /C:"Seconds_Behind_Master" /C:"IO_Running"

echo.
echo === REPLICACION MARIADB SAN LORENZO ===
docker-compose exec mariadb-sanlorenzo mysql -u root -proot_pass -e "SELECT 'IO_Running:', IF(@@read_only=1,'Slave','Master') as Role; SHOW SLAVE STATUS\G" 2>nul | findstr /C:"Slave_IO_Running" /C:"Slave_SQL_Running" /C:"Master_Host" /C:"Seconds_Behind_Master" /C:"IO_Running"

echo.
echo === REPLICACION MARIADB TUCUMAN ===
docker-compose exec mariadb-tucuman mysql -u root -proot_pass -e "SELECT 'IO_Running:', IF(@@read_only=1,'Slave','Master') as Role; SHOW SLAVE STATUS\G" 2>nul | findstr /C:"Slave_IO_Running" /C:"Slave_SQL_Running" /C:"Master_Host" /C:"Seconds_Behind_Master" /C:"IO_Running"
