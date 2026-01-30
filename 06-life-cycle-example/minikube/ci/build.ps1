# Build script para Windows PowerShell
param(
    [Parameter(Mandatory=$true)]
    [string]$Version
)

Write-Host "🔧 Building Temporal Worker v$Version" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Verificar que estamos en el directorio correcto
if (!(Test-Path "Dockerfile")) {
    Write-Host "❌ Dockerfile not found. Run from minikube directory." -ForegroundColor Red
    exit 1
}

# Setup registry port forward si no está corriendo
$registryProcess = Get-Process | Where-Object {$_.ProcessName -eq "kubectl" -and $_.CommandLine -like "*port-forward*registry*"}
if (!$registryProcess) {
    Write-Host "🔧 Starting registry port-forward..." -ForegroundColor Yellow
    Start-Process -FilePath "kubectl" -ArgumentList "port-forward --namespace kube-system service/registry 5000:80" -WindowStyle Hidden
    Start-Sleep 5
}

# Build imagen
Write-Host "🏗️ Building Docker image..." -ForegroundColor Yellow
$env:DOCKER_BUILDKIT = "1"
docker build -t "localhost:5000/lifecycle-worker:$Version" --build-arg "VERSION=$Version" .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker build failed" -ForegroundColor Red
    exit 1
}

# Push imagen
Write-Host "📦 Pushing to local registry..." -ForegroundColor Yellow
docker push "localhost:5000/lifecycle-worker:$Version"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker push failed" -ForegroundColor Red
    exit 1
}

# Determinar qué manifest usar
$manifestFile = ""
if ($Version -like "v1.*") {
    $manifestFile = "k8s/04-workers-v1.yaml"
} elseif ($Version -like "v2.*") {
    $manifestFile = "k8s/05-workers-v2.yaml"
} else {
    Write-Host "⚠️ Unknown version pattern. Using v2 manifest." -ForegroundColor Yellow
    $manifestFile = "k8s/05-workers-v2.yaml"
}

# Deploy workers
Write-Host "🚀 Deploying workers..." -ForegroundColor Yellow
kubectl apply -f $manifestFile

# Esperar deployment
Write-Host "⏳ Waiting for deployment..." -ForegroundColor Yellow
$deploymentName = if ($Version -like "v1.*") { "lifecycle-workers-v1" } else { "lifecycle-workers-v2" }
kubectl rollout status deployment/$deploymentName -n workers --timeout=300s

# Verificar pods
Write-Host "📋 Checking deployment status..." -ForegroundColor Cyan
kubectl get pods -n workers -l version=$Version

Write-Host "✅ Build and deployment completed successfully!" -ForegroundColor Green
Write-Host "🎯 Version $Version is now running" -ForegroundColor Green