@echo off
REM ============================================================================
REM CONTROL DE ENLACES - 3 REGIONES (IPTABLES EN VROUTER)
REM ============================================================================

echo.
echo ============================================================================
echo CONTROL DE ENLACES - 3 REGIONES
echo ============================================================================
echo TOPOLOGIA:
echo   Hornos (172.20.0.0/24) -- San Lorenzo (172.21.0.0/24)
echo   Hornos (172.20.0.0/24) -- Tucuman (172.22.0.0/24)
echo   San Lorenzo (172.21.0.0/24) -- Tucuman (172.22.0.0/24)
echo.

if "%1"=="" goto :show_help
if "%1"=="status" goto :show_status
if "%1"=="cut" goto :cut_link
if "%1"=="restore" goto :restore_all
if "%1"=="test" goto :test_connectivity
if "%1"=="failover" goto :test_failover
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
goto :end

:cut_link
if "%2"=="" (
    echo ERROR: Especifica el enlace a cortar:
    echo   hornos-sanlorenzo    - Corta entre Hornos y San Lorenzo
    echo   hornos-tucuman       - Corta entre Hornos y Tucuman
    echo   sanlorenzo-tucuman   - Corta entre San Lorenzo y Tucuman
    goto :end
)

if "%2"=="hornos-sanlorenzo" (
    echo Cortando enlace HORNOS -- SAN LORENZO...
    echo.
    echo Bloqueando puerto 3306 entre 172.20.0.0/24 y 172.21.0.0/24
    docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -d 172.21.0.0/24 -p tcp --dport 3306 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -d 172.20.0.0/24 -p tcp --dport 3306 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -d 172.21.0.0/24 -p tcp --sport 3306 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -d 172.20.0.0/24 -p tcp --sport 3306 -j DROP
    echo.
    echo ENLACE HORNOS-SANLORENZO CORTADO
    echo Puerto 3306 bloqueado entre Primary y Replica
    echo MaxScale deberia detectar fallo de conexion
    echo.
    echo Ejecuta: network-control.bat status
)

if "%2"=="hornos-tucuman" (
    echo Cortando enlace HORNOS -- TUCUMAN...
    echo.
    echo Bloqueando puerto 3306 entre 172.20.0.0/24 y 172.22.0.0/24
    docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -d 172.22.0.0/24 -p tcp --dport 3306 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -d 172.20.0.0/24 -p tcp --dport 3306 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -d 172.22.0.0/24 -p tcp --sport 3306 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -d 172.20.0.0/24 -p tcp --sport 3306 -j DROP
    echo.
    echo ENLACE HORNOS-TUCUMAN CORTADO
    echo Puerto 3306 bloqueado - Primary pierde Arbitrator
    echo.
    echo Ejecuta: network-control.bat status
)

if "%2"=="sanlorenzo-tucuman" (
    echo Cortando enlace SAN LORENZO -- TUCUMAN...
    echo.
    echo Bloqueando puerto 3306 entre 172.21.0.0/24 y 172.22.0.0/24
    docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -d 172.22.0.0/24 -p tcp --dport 3306 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -d 172.21.0.0/24 -p tcp --dport 3306 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -d 172.22.0.0/24 -p tcp --sport 3306 -j DROP
    docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -d 172.21.0.0/24 -p tcp --sport 3306 -j DROP
    echo.
    echo ENLACE SANLORENZO-TUCUMAN CORTADO
    echo Puerto 3306 bloqueado - Replica pierde Arbitrator
    echo.
    echo Ejecuta: network-control.bat status
)

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
echo Ejecuta: network-control.bat status
goto :end

:test_connectivity
echo === TEST DE CONECTIVIDAD ENTRE REGIONES ===
echo.

echo|set /p="Hornos -- San Lorenzo: "
docker exec vrouter ping -c 1 -W 2 mariadb-replica >nul 2>&1
if %errorlevel%==0 (echo OK) else (echo CORTADO)

echo|set /p="Hornos -- Tucuman: "
docker exec vrouter ping -c 1 -W 2 mariadb-arbitrator >nul 2>&1
if %errorlevel%==0 (echo OK) else (echo CORTADO)

echo|set /p="San Lorenzo -- Hornos: "
docker exec vrouter ping -c 1 -W 2 mariadb-primary >nul 2>&1
if %errorlevel%==0 (echo OK) else (echo CORTADO)

echo|set /p="San Lorenzo -- Tucuman: "
docker exec vrouter ping -c 1 -W 2 mariadb-arbitrator >nul 2>&1
if %errorlevel%==0 (echo OK) else (echo CORTADO)

echo|set /p="Tucuman -- Hornos: "
docker exec vrouter ping -c 1 -W 2 mariadb-primary >nul 2>&1
if %errorlevel%==0 (echo OK) else (echo CORTADO)

echo|set /p="Tucuman -- San Lorenzo: "
docker exec vrouter ping -c 1 -W 2 mariadb-replica >nul 2>&1
if %errorlevel%==0 (echo OK) else (echo CORTADO)

echo.
goto :end

:test_failover
echo === PRUEBA DE FAILOVER - SPLIT BRAIN ===
echo.
echo 1. Cortando enlace Primary-Replica...
call :cut_link cut hornos-sanlorenzo
echo.
echo 2. Ejecuta: network-control.bat status
echo 3. Ejecuta: network-control.bat restore
echo.
goto :end

:show_help
echo.
echo USO: network-control.bat [comando] [parametros]
echo.
echo COMANDOS:
echo   status                     - Mostrar estado de enlaces y MaxScale
echo   cut [enlace]              - Cortar enlace especifico
echo   restore                   - Restaurar todos los enlaces
echo   test                      - Probar conectividad entre regiones
echo   failover                  - Prueba automatica de split-brain
echo.
echo ENLACES DISPONIBLES:
echo   hornos-sanlorenzo         - Corta Primary -- Replica
echo   hornos-tucuman            - Corta Primary -- Arbitrator
echo   sanlorenzo-tucuman        - Corta Replica -- Arbitrator
echo.

:end
echo.