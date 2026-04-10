# Script para abrir Web UI de Temporal
Write-Host "🌐 Abriendo Temporal Web UI..." -ForegroundColor Yellow
Write-Host "Presiona Ctrl+C para cerrar el port-forward" -ForegroundColor Cyan

# Abrir navegador automáticamente
Start-Process "http://localhost:8080"

# Port-forward Web UI
kubectl port-forward service/temporal-web 8080:8080 -n temporal