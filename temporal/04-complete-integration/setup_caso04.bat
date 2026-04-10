@echo off
echo ===================================
echo CASO 04: CONECTIVIDAD CLIENTE-SERVIDOR
echo ===================================
echo.
echo Este caso demuestra:
echo   - Cliente (192.168.100.10) aislado
echo   - Servidor (192.168.200.10) aislado  
echo   - Router virtual que los conecta
echo   - Temporal + Ansible para orquestacion
echo.

REM Verificar Docker
echo [1/4] Verificando Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo Docker no esta disponible
    pause
    exit /b 1
)
echo Docker OK

REM Levantar infraestructura
echo.
echo [2/4] Levantando infraestructura...
docker-compose up -d
if errorlevel 1 (
    echo Error con docker-compose
    pause
    exit /b 1
)
echo Infraestructura levantada

REM Esperar servicios
echo.
echo [3/4] Esperando servicios (30s)...
timeout /t 30 /nobreak >nul

REM Verificar estado inicial
echo.
echo [4/4] Verificando estado inicial...
echo    Probando conectividad cliente -^> servidor...

docker exec test-client ping -c 1 -W 2 192.168.200.10 >nul 2>&1
if errorlevel 1 (
    echo PERFECTO: Sin conectividad inicial (como esperado)
) else (
    echo Hay conectividad inicial (inesperado)
)

echo.
echo ===================================
echo SETUP COMPLETADO
echo ===================================
echo.
echo Servicios disponibles:
echo    - Servidor web: http://localhost:8080
echo    - Airflow UI: http://localhost:8081 (admin/admin)
echo.
echo Proximos pasos:
echo    1. Abrir nueva terminal
echo    2. Ejecutar: python run_worker.py
echo    3. En otra terminal: python run_deployment.py
echo.
echo Test manual de conectividad:
echo    docker exec test-client ping 192.168.200.10
echo.
echo ESTADO ACTUAL: Sin conectividad cliente-servidor
echo    (Perfecto para demostrar el valor del workflow)
echo.

pause