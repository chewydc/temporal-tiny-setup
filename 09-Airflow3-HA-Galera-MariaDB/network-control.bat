@echo off
REM ============================================================================
REM CONTROL DE CONECTIVIDAD ENTRE REGIONES
REM ============================================================================
REM Permite simular fallos de red desconectando regiones específicas
REM ============================================================================

echo.
echo ============================================================================
echo GALERA CLUSTER - CONTROL DE CONECTIVIDAD
echo ============================================================================
echo Regiones: Hornos (172.20.0.0/24) - SanLorenzo (172.21.0.0/24) - Tucuman (172.22.0.0/24)
echo.

if "%1"=="" goto :show_help
if "%1"=="status" goto :show_status
if "%1"=="disconnect" goto :disconnect_region
if "%1"=="reconnect" goto :reconnect_all
if "%1"=="test" goto :test_connectivity
goto :show_help

:show_status
echo === ESTADO ACTUAL DEL CLUSTER ===
echo.
echo --- Galera Cluster Status ---
docker exec cluster-monitor mysql -h galera-hornos -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_cluster_size'" 2>nul
docker exec cluster-monitor mysql -h galera-hornos -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_ready'" 2>nul
echo.
echo --- Reglas de Firewall Activas ---
docker exec vrouter iptables -L FORWARD -n
echo.
goto :end

:disconnect_region
if "%2"=="" (
    echo ERROR: Especifica la region a desconectar: hornos, sanlorenzo, tucuman
    goto :end
)

if "%2"=="hornos" (
    echo Desconectando HORNOS del cluster...
    docker exec vrouter iptables -A FORWARD -s 172.20.0.0/24 -j DROP
    docker exec vrouter iptables -A FORWARD -d 172.20.0.0/24 -j DROP
    echo HORNOS desconectado. Galera deberia mantener quorum con SanLorenzo + Tucuman
)

if "%2"=="sanlorenzo" (
    echo Desconectando SAN LORENZO del cluster...
    docker exec vrouter iptables -A FORWARD -s 172.21.0.0/24 -j DROP
    docker exec vrouter iptables -A FORWARD -d 172.21.0.0/24 -j DROP
    echo SAN LORENZO desconectado. Galera deberia mantener quorum con Hornos + Tucuman
)

if "%2"=="tucuman" (
    echo Desconectando TUCUMAN del cluster...
    docker exec vrouter iptables -A FORWARD -s 172.22.0.0/24 -j DROP
    docker exec vrouter iptables -A FORWARD -d 172.22.0.0/24 -j DROP
    echo TUCUMAN desconectado. Galera deberia mantener quorum con Hornos + SanLorenzo
)

echo.
echo Esperando 10 segundos para que Galera detecte el cambio...
timeout /t 10 /nobreak >nul
call :show_status
goto :end

:reconnect_all
echo Reconectando todas las regiones...
docker exec vrouter iptables -F FORWARD
echo.
echo Todas las regiones reconectadas. Galera deberia sincronizar automaticamente.
echo.
echo Esperando 15 segundos para sincronizacion...
timeout /t 15 /nobreak >nul
call :show_status
goto :end

:test_connectivity
echo === TEST DE CONECTIVIDAD ===
echo.
echo Hornos -> SanLorenzo:
docker exec galera-hornos ping -c 2 galera-sanlorenzo 2>nul || echo "  FALLO"
echo.
echo SanLorenzo -> Hornos:
docker exec galera-sanlorenzo ping -c 2 galera-hornos 2>nul || echo "  FALLO"
echo.
echo Arbitrator -> Hornos:
docker exec galera-arbitrator ping -c 2 galera-hornos 2>nul || echo "  FALLO"
echo.
echo Arbitrator -> SanLorenzo:
docker exec galera-arbitrator ping -c 2 galera-sanlorenzo 2>nul || echo "  FALLO"
echo.
goto :end

:show_help
echo.
echo USO: network-control.bat [comando] [parametros]
echo.
echo COMANDOS:
echo   status                    - Mostrar estado del cluster y reglas de red
echo   disconnect [region]       - Desconectar una region (hornos/sanlorenzo/tucuman)
echo   reconnect                 - Reconectar todas las regiones
echo   test                      - Probar conectividad entre nodos
echo.
echo EJEMPLOS:
echo   network-control.bat status
echo   network-control.bat disconnect hornos
echo   network-control.bat disconnect sanlorenzo
echo   network-control.bat reconnect
echo   network-control.bat test
echo.
echo ESCENARIOS DE PRUEBA:
echo   1. Desconectar Hornos: SanLorenzo + Tucuman mantienen quorum
echo   2. Desconectar SanLorenzo: Hornos + Tucuman mantienen quorum
echo   3. Desconectar Tucuman: Hornos + SanLorenzo mantienen quorum
echo   4. Desconectar 2 regiones: Cluster se pone en modo no-primary
echo.

:end
echo.