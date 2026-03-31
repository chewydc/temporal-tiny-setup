@echo off
REM ============================================================================
REM AIRFLOW 3.x HA + GALERA CLUSTER - STARTUP
REM ============================================================================
REM Inicia el cluster Galera en 3 regiones con Airflow HA
REM ============================================================================

echo.
echo ============================================================================
echo AIRFLOW 3.x HA + GALERA CLUSTER (3 REGIONES)
echo ============================================================================
echo Hornos: Airflow + MariaDB Galera Node 1
echo SanLorenzo: Airflow + MariaDB Galera Node 2
echo Tucuman: Solo Galera Arbitrator
echo ============================================================================
echo.

REM Verificar que Docker esté corriendo
docker version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker no está corriendo o no está instalado
    pause
    exit /b 1
)

REM Limpiar contenedores previos si existen
echo Limpiando contenedores previos...
docker-compose down -v 2>nul

echo.
echo === FASE 1: Iniciando Router y Servicios Base ===
docker-compose up -d vrouter
timeout /t 5 /nobreak >nul

echo.
echo === FASE 2: Iniciando Galera Cluster ===
echo Iniciando nodo primario (Hornos)...
docker-compose up -d galera-hornos redis-hornos
timeout /t 30 /nobreak >nul

echo Iniciando nodo secundario (SanLorenzo)...
docker-compose up -d galera-sanlorenzo redis-sanlorenzo
timeout /t 45 /nobreak >nul

echo Iniciando arbitrator (Tucuman)...
docker-compose up -d galera-arbitrator
timeout /t 15 /nobreak >nul

echo.
echo === FASE 3: Verificando Cluster Galera ===
echo Esperando sincronización del cluster...
timeout /t 20 /nobreak >nul

docker-compose up -d cluster-monitor
timeout /t 5 /nobreak >nul

echo.
echo --- Estado del Cluster ---
docker exec cluster-monitor mysql -h galera-hornos -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_cluster_size'" 2>nul || echo "Esperando conexión..."
docker exec cluster-monitor mysql -h galera-hornos -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_ready'" 2>nul || echo "Esperando conexión..."

echo.
echo === FASE 4: Iniciando Airflow HA ===
echo Inicializando base de datos...
docker-compose up -d airflow-init-hornos
docker-compose up -d airflow-init-sanlorenzo

echo Esperando inicialización...
timeout /t 30 /nobreak >nul

echo Iniciando servicios de Airflow...
docker-compose up -d airflow-apiserver-hornos airflow-scheduler-hornos airflow-worker-hornos
docker-compose up -d airflow-apiserver-sanlorenzo airflow-scheduler-sanlorenzo airflow-worker-sanlorenzo

echo.
echo === VERIFICACIÓN FINAL ===
timeout /t 15 /nobreak >nul

echo.
echo --- Servicios Activos ---
docker-compose ps

echo.
echo ============================================================================
echo CLUSTER LISTO!
echo ============================================================================
echo.
echo ACCESOS:
echo   Airflow Hornos:     http://localhost:8080
echo   Airflow SanLorenzo: http://localhost:8081
echo   MariaDB Hornos:     localhost:3306
echo   MariaDB SanLorenzo: localhost:3307
echo.
echo COMANDOS ÚTILES:
echo   network-control.bat status              - Ver estado del cluster
echo   network-control.bat disconnect hornos   - Simular fallo de Hornos
echo   network-control.bat reconnect           - Reconectar todo
echo.
echo PRUEBAS DE FAILOVER:
echo   1. Ejecutar DAG 'failover_test' en cualquier Airflow
echo   2. Mientras corre, usar network-control.bat para desconectar regiones
echo   3. Verificar que el DAG completa sin errores
echo.
echo ============================================================================

pause