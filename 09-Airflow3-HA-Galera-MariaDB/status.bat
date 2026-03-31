@echo off
REM ============================================================================
REM GALERA CLUSTER - MONITOR DE ESTADO
REM ============================================================================

echo.
echo ============================================================================
echo GALERA CLUSTER - ESTADO DETALLADO
echo ============================================================================

:loop
cls
echo.
echo === TIMESTAMP: %date% %time% ===
echo.

echo --- CONTENEDORES ACTIVOS ---
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo.

echo --- GALERA CLUSTER STATUS ---
echo.
echo [HORNOS] Cluster Size:
docker exec cluster-monitor mysql -h galera-hornos -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_cluster_size'" 2>nul || echo "  DESCONECTADO"

echo [HORNOS] Ready Status:
docker exec cluster-monitor mysql -h galera-hornos -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_ready'" 2>nul || echo "  DESCONECTADO"

echo [HORNOS] Local State:
docker exec cluster-monitor mysql -h galera-hornos -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_local_state_comment'" 2>nul || echo "  DESCONECTADO"

echo.
echo [SAN LORENZO] Cluster Size:
docker exec cluster-monitor mysql -h galera-sanlorenzo -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_cluster_size'" 2>nul || echo "  DESCONECTADO"

echo [SAN LORENZO] Ready Status:
docker exec cluster-monitor mysql -h galera-sanlorenzo -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_ready'" 2>nul || echo "  DESCONECTADO"

echo [SAN LORENZO] Local State:
docker exec cluster-monitor mysql -h galera-sanlorenzo -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_local_state_comment'" 2>nul || echo "  DESCONECTADO"

echo.
echo --- CONECTIVIDAD DE RED ---
echo Hornos -> SanLorenzo:
docker exec galera-hornos ping -c 1 -W 2 galera-sanlorenzo >nul 2>&1 && echo "  OK" || echo "  FALLO"

echo SanLorenzo -> Hornos:
docker exec galera-sanlorenzo ping -c 1 -W 2 galera-hornos >nul 2>&1 && echo "  OK" || echo "  FALLO"

echo Arbitrator -> Hornos:
docker exec galera-arbitrator ping -c 1 -W 2 galera-hornos >nul 2>&1 && echo "  OK" || echo "  FALLO"

echo Arbitrator -> SanLorenzo:
docker exec galera-arbitrator ping -c 1 -W 2 galera-sanlorenzo >nul 2>&1 && echo "  OK" || echo "  FALLO"

echo.
echo --- REGLAS DE FIREWALL ---
docker exec vrouter iptables -L FORWARD -n | findstr DROP >nul 2>&1 && (
    echo "REGIONES DESCONECTADAS:"
    docker exec vrouter iptables -L FORWARD -n | findstr DROP
) || echo "TODAS LAS REGIONES CONECTADAS"

echo.
echo --- AIRFLOW STATUS ---
echo Hornos WebServer:
curl -s -o nul -w "%%{http_code}" http://localhost:8080/health 2>nul | findstr 200 >nul && echo "  OK (200)" || echo "  FALLO"

echo SanLorenzo WebServer:
curl -s -o nul -w "%%{http_code}" http://localhost:8081/health 2>nul | findstr 200 >nul && echo "  OK (200)" || echo "  FALLO"

echo.
echo ============================================================================
echo Presiona Ctrl+C para salir, o cualquier tecla para actualizar...
echo ============================================================================

timeout /t 10 /nobreak >nul
goto :loop