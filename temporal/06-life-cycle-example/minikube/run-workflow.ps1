# Script simple para ejecutar workflows desde el cluster
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("quick", "lifecycle")]
    [string]$WorkflowType
)

$script = @"
import asyncio
from temporalio.client import Client
from workflows.lifecycle_workflows import QuickTestWorkflow, LifecycleWorkflow

async def run():
    client = await Client.connect('temporal-frontend-lb.temporal.svc.cluster.local:7233')
    
    if '$WorkflowType' == 'quick':
        print('🚀 Ejecutando QuickTestWorkflow...')
        result = await client.execute_workflow(
            QuickTestWorkflow.run,
            'test-data',
            id='quick-' + str(int(asyncio.get_event_loop().time())),
            task_queue='lifecycle-queue'
        )
    else:
        print('🚀 Ejecutando LifecycleWorkflow (5 minutos)...')
        result = await client.execute_workflow(
            LifecycleWorkflow.run,
            'lifecycle-data',
            id='lifecycle-' + str(int(asyncio.get_event_loop().time())),
            task_queue='lifecycle-queue'
        )
    
    print(f'✅ Workflow completado: {result}')

asyncio.run(run())
"@

Write-Host "🚀 Ejecutando workflow '$WorkflowType'..." -ForegroundColor Yellow
kubectl exec -it deployment/lifecycle-workers-v1 -n workers -- python -c $script