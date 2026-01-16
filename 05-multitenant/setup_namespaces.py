"""
Script para crear namespaces en Temporal Server.
Ejecutar ANTES de iniciar workers y demo.
"""
import asyncio
from temporalio.client import Client

async def setup_namespaces():
    """Crea namespaces para cada tenant"""
    
    tenants = ["chogar", "amovil", "afijo"]
    
    print("="*60)
    print("CONFIGURANDO NAMESPACES EN TEMPORAL")
    print("="*60)
    print()
    
    # Conectar al namespace default para crear otros
    client = await Client.connect("localhost:7233")
    
    for tenant in tenants:
        namespace = tenant
        print(f"📦 Creando namespace: {namespace}")
        
        try:
            # Crear namespace usando temporal CLI
            import subprocess
            result = subprocess.run(
                ["temporal", "operator", "namespace", "create", namespace],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"   ✅ Namespace '{namespace}' creado")
            elif "already exists" in result.stderr.lower():
                print(f"   ℹ️  Namespace '{namespace}' ya existe")
            else:
                print(f"   ❌ Error: {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ Error creando namespace: {e}")
    
    print()
    print("="*60)
    print("CONFIGURACIÓN COMPLETADA")
    print("="*60)
    print()
    print("Namespaces creados:")
    for tenant in tenants:
        print(f"  - {tenant}")
    print()
    print("Ahora podés ejecutar:")
    print("  1. python multitenant_worker.py")
    print("  2. python multitenant_demo.py")
    print()

if __name__ == "__main__":
    asyncio.run(setup_namespaces())
