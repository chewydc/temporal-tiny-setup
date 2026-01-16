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
    
    for tenant in tenants:
        namespace = f"tenant-{tenant}"
        print(f"📦 Creando namespace: {namespace}")
        
        try:
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
            print(f"   ❌ Error: {e}")
            print(f"   💡 Asegurate de tener Temporal CLI instalado")
            print(f"      O usa docker: docker exec temporal-admin-tools tctl namespace register {namespace}")
    
    print()
    print("="*60)
    print("CONFIGURACIÓN COMPLETADA")
    print("="*60)
    print()
    print("Namespaces creados:")
    for tenant in tenants:
        print(f"  - tenant-{tenant}")
    print()
    print("Ahora podés ejecutar:")
    print("  1. python secure_multitenant_demo.py")
    print()
    print("Para verificar en UI:")
    print("  http://localhost:8233")
    print("  (Cambiar namespace en dropdown superior)")
    print()

if __name__ == "__main__":
    asyncio.run(setup_namespaces())
