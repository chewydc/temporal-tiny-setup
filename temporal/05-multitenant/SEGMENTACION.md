# 🔐 Segmentación Real con Namespaces

## Problema
Con task queues, todos los tenants comparten el mismo namespace → todos ven todos los workflows en Temporal UI.

## Solución: Namespaces Separados

Cada tenant tiene su **namespace dedicado** = aislamiento total.

```
tenant-chogar  → Solo workflows de chogar
tenant-amovil  → Solo workflows de amovil  
tenant-afijo   → Solo workflows de afijo
```

## 🚀 Cómo Ejecutar

### 1. Crear namespaces
```bash
python setup_namespaces.py
```

### 2. Ejecutar demo seguro
```bash
python secure_multitenant_demo.py
```

### 3. Verificar en UI
1. Abrir: http://localhost:8233
2. Cambiar namespace en dropdown superior
3. Cada namespace solo muestra workflows de ese tenant

## 🏭 En Producción

### Opción A: API Gateway con Autenticación

```python
# Tu API valida JWT y conecta al namespace correcto
@app.post("/workflows/start")
async def start_workflow(request, token: str):
    user = validate_jwt(token)  # Obtiene tenant_id
    
    # Conectar al namespace del tenant
    client = await Client.connect(
        "temporal.prod:7233",
        namespace=f"tenant-{user.tenant_id}"
    )
    
    # Usuario solo puede iniciar workflows en su namespace
    await client.start_workflow(...)
```

### Opción B: Temporal Cloud + mTLS

- Cada tenant tiene certificados únicos
- RBAC integrado
- Autenticación automática

## 📊 Comparación

| Estrategia | Aislamiento | Complejidad | Costo |
|------------|-------------|-------------|-------|
| Task Queues | Bajo | Baja | Bajo |
| Namespaces | Alto | Media | Medio |
| Temporal Cloud | Total | Baja | Alto |

## 💡 Recomendación

- **Dev/Testing**: Task queues (actual)
- **Producción**: Namespaces + API Gateway
- **Enterprise**: Temporal Cloud + mTLS
