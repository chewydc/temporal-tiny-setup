# Script para desplegar workers después de que Temporal esté corriendo

Write-Host "🔧 Configurando Docker para Minikube..." -ForegroundColor Yellow
minikube docker-env | Invoke-Expression

Write-Host "🏗️ Building worker image..." -ForegroundColor Yellow
docker build -t lifecycle-worker:v1.0.0 --build-arg VERSION=v1.0.0 .

Write-Host "🚀 Desplegando workers v1..." -ForegroundColor Yellow
kubectl apply -f k8s/04-workers-v1.yaml

Write-Host "⏳ Esperando que workers estén listos..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=lifecycle-workers -n workers --timeout=300s

Write-Host "✅ Workers desplegados exitosamente!" -ForegroundColor Green
kubectl get pods -n workers

Write-Host "🌐 Para acceder a Temporal Web UI:" -ForegroundColor Cyan
Write-Host "kubectl port-forward service/temporal-web 8080:8080 -n temporal" -ForegroundColor White

Write-Host "🔌 Para conectar cliente Python:" -ForegroundColor Cyan
Write-Host "kubectl port-forward service/temporal-frontend-lb 7233:7233 -n temporal" -ForegroundColor White