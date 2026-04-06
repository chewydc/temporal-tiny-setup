@echo off
REM ============================================================================
REM CONTROL DE ENLACES - 3 REGIONES (MEJORADO)
REM ============================================================================

echo.
echo ============================================================================
echo CONTROL DE ENLACES - 3 REGIONES (MEJORADO)
echo ============================================================================
echo TOPOLOGIA:
echo   Hornos (172.20.0.0/24) -- San Lorenzo (172.21.0.0/24)
echo   Hornos (172.20.0.0/24) -- Tucuman (172.22.0.0/24)
echo   San Lorenzo (172.21.0.0/24) -- Tucuman (172.22.0.0/24)
echo.
echo SERVICIOS POR REGION:
echo   Hornos: MariaDB Primary (3306), MaxScale (4006), Redis (6379), Airflow
echo   San Lorenzo: MariaDB Replica (3306), MaxScale (4006), Redis (6379), Worker
echo   Tucuman: MariaDB Arbitrator (3306)
echo.

if "%1"=="" goto :show_help
if "%1"=="status" goto :show_status
if "%1"=="cut" goto :cut_link
if "%1"=="restore" goto :restore_all
if "%1"=="test" goto :test_connectivity
if "%1"=="failover" goto :test_failover
if "%1"=="isolate" goto :isolate_region
goto :show_help

:show_status
echo === ESTADO DE ENLACES ===
echo.
docker exec vrouter iptables -L FORWARD -n 2>nul | findstr DROP >nul && (
    echo ENLACES CORTADOS:
    docker exec vrouter iptables -L FORWARD -n | findstr DROP
    echo.
) || echo TODOS LOS ENLACES ACTIVOS

echo === ESTADO DE MAXSCALE ===
echo.
echo --- MaxScale Hornos ---
docker exec maxscale-hornos maxctrl list servers 2>nul || echo "MaxScale Hornos no disponible"
echo.
echo --- MaxScale San Lorenzo ---
docker exec maxscale-sanlorenzo maxctrl list servers 2>nul || echo "MaxScale San Lorenzo no disponible"
echo.

echo === ESTADO DE SERVICIOS ===
echo.
echo|set /p="MariaDB Primary: "
docker exec mariadb-primary mysql -u root -proot_pass -e "SELECT 1" >nul 2>&1 && echo OK || echo ERROR

echo|set /p="MariaDB Replica: "
docker exec mariadb-replica mysql -u root -proot_pass -e "SELECT 1" >nul 2>&1 && echo OK || echo ERROR

echo|set /p="MariaDB Arbitrator: "
docker exec mariadb-arbitrator mysql -u root -proot_pass -e "SELECT 1" >nul 2>&1 && echo OK || echo ERROR

echo|set /p="Redis Hornos: "
docker exec redis-hornos redis-cli ping >nul 2>&1 && echo OK || echo ERROR

echo|set /p="Redis San Lorenzo: "
docker exec redis-sanlorenzo redis-cli ping >nul 2>&1 && echo OK || echo ERROR

echo|set /p="Airflow API: "
curl -s http://localhost:8080/health >nul 2>&1 && echo OK || echo ERROR

echo.
goto :end

:cut_link
if "%2"=="" (
    echo ERROR: Especifica el enlace a cortar:
    echo   hornos-sanlorenzo    - Corta entre Hornos y San Lorenzo
    echo   hornos-tucuman       - Corta entre Hornos y Tucuman  
    echo   sanlorenzo-tucuman   - Corta entre San Lorenzo y Tucuman
    echo   db-only              - Solo corta puertos de base de datos
    echo   all-ports            - Corta todos los puertos
    goto :end
)

if "%2"=="hornos-sanlorenzo" (
    echo Cortando enlace HORNOS -- SAN LORENZO...
    echo.
    if "%3"=="db-only" (
        echo Bloqueando solo puerto 3306...
        docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -d 172.21.0.0/24 -p tcp --dport 3306 -j DROP
        docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -d 172.20.0.0/24 -p tcp --dport 3306 -j DROP
    ) else (
        echo Bloqueando todos los puertos...
        docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -d 172.21.0.0/24 -j DROP
        docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -d 172.20.0.0/24 -j DROP
    )
    echo ENLACE HORNOS-SANLORENZO CORTADO
)

if "%2"=="hornos-tucuman" (
    echo Cortando enlace HORNOS -- TUCUMAN...
    echo.
    if "%3"=="db-only" (
        echo Bloqueando solo puerto 3306...
        docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -d 172.22.0.0/24 -p tcp --dport 3306 -j DROP
        docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -d 172.20.0.0/24 -p tcp --dport 3306 -j DROP
    ) else (
        echo Bloqueando todos los puertos...
        docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -d 172.22.0.0/24 -j DROP
        docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -d 172.20.0.0/24 -j DROP
    )
    echo ENLACE HORNOS-TUCUMAN CORTADO
)

if "%2"=="sanlorenzo-tucuman" (
    echo Cortando enlace SAN LORENZO -- TUCUMAN...
    echo.
    if "%3"=="db-only" (
        echo Bloqueando solo puerto 3306...
        docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -d 172.22.0.0/24 -p tcp --dport 3306 -j DROP
        docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -d 172.21.0.0/24 -p tcp --dport 3306 -j DROP
    ) else (
        echo Bloqueando todos los puertos...
        docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -d 172.22.0.0/24 -j DROP
        docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -d 172.21.0.0/24 -j DROP
    )
    echo ENLACE SANLORENZO-TUCUMAN CORTADO
)

echo.
echo Ejecuta: network-control-enhanced.bat status
goto :end

:isolate_region
if "%2"=="" (
    echo ERROR: Especifica la region a aislar:
    echo   hornos       - Aisla region Hornos
    echo   sanlorenzo   - Aisla region San Lorenzo
    echo   tucuman      - Aisla region Tucuman
    goto :end
)

if "%2"=="hornos" (
    echo Aislando region HORNOS...
    docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -d 172.21.0.0/24 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -d 172.22.0.0/24 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -d 172.20.0.0/24 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -d 172.20.0.0/24 -j DROP
    echo REGION HORNOS AISLADA - Primary sin acceso a Replica/Arbitrator
)

if "%2"=="sanlorenzo" (
    echo Aislando region SAN LORENZO...
    docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -d 172.20.0.0/24 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -d 172.22.0.0/24 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -d 172.21.0.0/24 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -d 172.21.0.0/24 -j DROP
    echo REGION SAN LORENZO AISLADA - Replica sin acceso a Primary/Arbitrator
)

if "%2"=="tucuman" (
    echo Aislando region TUCUMAN...
    docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -d 172.20.0.0/24 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -d 172.21.0.0/24 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -d 172.22.0.0/24 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -d 172.22.0.0/24 -j DROP
    echo REGION TUCUMAN AISLADA - Arbitrator sin acceso a Primary/Replica
)

echo.
echo Ejecuta: network-control-enhanced.bat status
goto :end

:restore_all
echo Restaurando todos los enlaces...
echo.
echo Limpiando reglas de firewall...
docker exec vrouter iptables -F FORWARD
echo.
echo TODOS LOS ENLACES RESTAURADOS
echo MaxScale deberia reconfigurar automaticamente
echo.
echo Ejecuta: network-control-enhanced.bat status
goto :end

:test_connectivity
echo === TEST DE CONECTIVIDAD COMPLETO ===
echo.

echo --- Conectividad de Red ---
echo|set /p="Hornos -- San Lorenzo: "
docker exec vrouter ping -c 1 -W 2 172.21.0.10 >nul 2>&1 && echo OK || echo CORTADO

echo|set /p="Hornos -- Tucuman: "
docker exec vrouter ping -c 1 -W 2 172.22.0.10 >nul 2>&1 && echo OK || echo CORTADO

echo|set /p="San Lorenzo -- Tucuman: "
docker exec vrouter ping -c 1 -W 2 172.22.0.10 >nul 2>&1 && echo OK || echo CORTADO

echo.
echo --- Conectividad de Servicios ---
echo|set /p="Primary -- Replica (3306): "
docker exec mariadb-primary mysql -h 172.21.0.20 -u root -proot_pass -e "SELECT 1" >nul 2>&1 && echo OK || echo ERROR

echo|set /p="Primary -- Arbitrator (3306): "
docker exec mariadb-primary mysql -h 172.22.0.20 -u root -proot_pass -e "SELECT 1" >nul 2>&1 && echo OK || echo ERROR

echo|set /p="MaxScale Hornos -- Replica: "
docker exec maxscale-hornos maxctrl call command mariadbmon ping MariaDB-Monitor mariadb-replica >nul 2>&1 && echo OK || echo ERROR

echo|set /p="MaxScale San Lorenzo -- Primary: "
docker exec maxscale-sanlorenzo maxctrl call command mariadbmon ping MariaDB-Monitor mariadb-primary >nul 2>&1 && echo OK || echo ERROR

echo.
goto :end

:test_failover
echo === PRUEBA DE FAILOVER AUTOMATICO ===
echo.
echo 1. Estado inicial...
call :show_status
echo.
echo 2. Cortando enlace Primary-Replica...
call :cut_link cut hornos-sanlorenzo
echo.
echo 3. Esperando deteccion de fallo (30 segundos)...
timeout /t 30 >nul
echo.
echo 4. Estado despues del corte...
call :show_status
echo.
echo 5. Restaurando enlaces...
call :restore_all
echo.
echo 6. Estado final...
call :show_status
echo.
goto :end

:show_help
echo.
echo USO: network-control-enhanced.bat [comando] [parametros]
echo.
echo COMANDOS:
echo   status                     - Estado completo del sistema
echo   cut [enlace] [tipo]       - Cortar enlace especifico
echo   isolate [region]          - Aislar region completamente
echo   restore                   - Restaurar todos los enlaces
echo   test                      - Test completo de conectividad
echo   failover                  - Prueba automatica de failover
echo.
echo ENLACES:
echo   hornos-sanlorenzo         - Primary -- Replica
echo   hornos-tucuman            - Primary -- Arbitrator  
echo   sanlorenzo-tucuman        - Replica -- Arbitrator
echo.
echo TIPOS DE CORTE:
echo   db-only                   - Solo puerto 3306 (MariaDB)
echo   (sin parametro)           - Todos los puertos
echo.
echo REGIONES:
echo   hornos, sanlorenzo, tucuman
echo.

:end
echo.