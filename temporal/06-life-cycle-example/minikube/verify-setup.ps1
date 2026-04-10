# Script de verificación completa del setup

Write-Host "🔍 Verificando estado del cluster..." -ForegroundColor Yellow

Write-Host "`n📊 Estado de todos los pods:" -ForegroundColor Cyan
kubectl get pods --all-namespaces

Write-Host "`n🏗️ Estado de deployments:" -ForegroundColor Cyan
kubectl get deployments --all-namespaces

Write-Host "`n🌐 Estado de servicios:" -ForegroundColor Cyan
kubectl get services --all-namespaces

Write-Host "`n✅ Verificación de conectividad:" -ForegroundColor Green

# Test de conectividad a Temporal
Write-Host "Testing Temporal Server connectivity..." -ForegroundColor Yellow
$temporalPod = kubectl get pods -n temporal -l app=temporal-server -o jsonpath='{.items[0].metadata.name}'
if ($temporalPod) {
    Write-Host "✅ Temporal Server pod encontrado: $temporalPod" -ForegroundColor Green
} else {
    Write-Host "❌ No se encontró pod de Temporal Server" -ForegroundColor Red
}

# Test de workers
Write-Host "Testing Workers..." -ForegroundColor Yellow
$workerPods = kubectl get pods -n workers -l app=lifecycle-workers --no-headers 2>$null
if ($workerPods) {
    Write-Host "✅ Workers encontrados:" -ForegroundColor Green
    kubectl get pods -n workers
} else {
    Write-Host "⚠️ No se encontraron workers - ejecuta .\deploy-workers.ps1" -ForegroundColor Yellow
}

Write-Host "`n🚀 Para probar el sistema:" -ForegroundColor Cyan
Write-Host "1. Port-forward Temporal: kubectl port-forward service/temporal-frontend-lb 7233:7233 -n temporal" -ForegroundColor White
Write-Host "2. Port-forward Web UI: kubectl port-forward service/temporal-web 8080:8080 -n temporal" -ForegroundColor White
Write-Host "3. Ejecutar workflow: python client.py quick" -ForegroundColor White