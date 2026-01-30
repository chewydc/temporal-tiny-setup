# ============================================
# DEMO 1: SIN VERSIONING (Flexible)
# ============================================

Write-Host "`n=== DEMO 1: SIN VERSIONING ===" -ForegroundColor Cyan

# Deshabilitar versioning
kubectl set env deployment/lifecycle-workers-v1 -n workers USE_VERSIONING=false
kubectl set env deployment/lifecycle-workers-v2 -n workers USE_VERSIONING=false

# Esperar restart
Write-Host "Esperando restart de workers..." -ForegroundColor Yellow
kubectl rollout status deployment/lifecycle-workers-v1 -n workers
kubectl rollout status deployment/lifecycle-workers-v2 -n workers

# Obtener pod
$POD = (kubectl get pods -n workers -o jsonpath='{.items[0].metadata.name}')
Write-Host "Usando pod: $POD" -ForegroundColor Green

# Copiar cliente
kubectl cp client_k8s.py "workers/${POD}:/tmp/"

Write-Host "`nEjecutando workflow SIN versioning..." -ForegroundColor Yellow
Write-Host "Observa los logs: activities se distribuyen entre v1 y v2`n" -ForegroundColor Yellow

# Ejecutar workflow
kubectl exec -it -n workers $POD -- python /tmp/client_k8s.py lifecycle

Write-Host "`n=== FIN DEMO 1 ===`n" -ForegroundColor Cyan


# ============================================
# DEMO 2: CON VERSIONING (Estricto)
# ============================================

Write-Host "`n=== DEMO 2: CON VERSIONING ===" -ForegroundColor Cyan

# Habilitar versioning
kubectl set env deployment/lifecycle-workers-v1 -n workers USE_VERSIONING=true
kubectl set env deployment/lifecycle-workers-v2 -n workers USE_VERSIONING=true

# Esperar restart
Write-Host "Esperando restart de workers..." -ForegroundColor Yellow
kubectl rollout status deployment/lifecycle-workers-v1 -n workers
kubectl rollout status deployment/lifecycle-workers-v2 -n workers

# Obtener pod
$POD = (kubectl get pods -n workers -o jsonpath='{.items[0].metadata.name}')
Write-Host "Usando pod: $POD" -ForegroundColor Green

# Copiar cliente
kubectl cp client_k8s.py "workers/${POD}:/tmp/"

Write-Host "`nEjecutando workflow bloqueado a v1.0.0..." -ForegroundColor Yellow
Write-Host "Observa los logs: SOLO v1 ejecuta activities`n" -ForegroundColor Yellow

# Ejecutar workflow bloqueado a v1.0.0
kubectl exec -it -n workers $POD -- python /tmp/client_k8s.py lifecycle v1.0.0

Write-Host "`nEjecutando workflow bloqueado a v2.0.0..." -ForegroundColor Yellow
Write-Host "Observa los logs: SOLO v2 ejecuta activities`n" -ForegroundColor Yellow

# Ejecutar workflow bloqueado a v2.0.0
kubectl exec -it -n workers $POD -- python /tmp/client_k8s.py lifecycle v2.0.0

Write-Host "`n=== FIN DEMO 2 ===`n" -ForegroundColor Cyan
