# 🖥️ UI con Control de Acceso - Opciones

## ❌ Temporal UI Nativa (Self-Hosted)

**Limitaciones:**
- No tiene autenticación de usuarios
- No tiene autorización por namespace
- Todos ven todos los namespaces
- No hay RBAC

**Conclusión:** No sirve para control de acceso granular.

---

## ✅ Opción 1: Custom UI (Recomendado)

Construyes tu propia interfaz web que:

### Características:
- ✅ Login de usuarios
- ✅ Permisos por namespace
- ✅ Un usuario puede ver N namespaces
- ✅ Control total de la experiencia

### Arquitectura:

```
Usuario → Tu UI (FastAPI/React) → Temporal API
          ↓
       Valida permisos
       Filtra namespaces
```

### Ejemplo:
```python
# Usuario "manager" tiene acceso a 2 namespaces
user_permissions = {
    "email": "manager@empresa.com",
    "namespaces": ["tenant-chogar", "tenant-amovil"]
}

# Tu UI consulta solo esos namespaces
for ns in user_permissions["namespaces"]:
    client = await Client.connect("temporal:7233", namespace=ns)
    workflows = await client.list_workflows()
```

### Demo Incluido:
`custom_ui_example.py` - UI completa con:
- Login de usuarios
- 3 roles diferentes (admin, manager, operator)
- Filtrado automático por permisos
- Dashboard HTML simple

**Ejecutar:**
```bash
pip install fastapi uvicorn pyjwt
python custom_ui_example.py
# Abrir: http://localhost:8000
```

---

## ✅ Opción 2: Temporal Cloud (Pago)

**Características:**
- ✅ RBAC nativo
- ✅ SSO (SAML, OAuth)
- ✅ Permisos granulares por namespace
- ✅ Auditoría completa
- ✅ mTLS automático

**Costo:** ~$200-500/mes según uso

**Cuándo usar:** Producción enterprise con presupuesto.

---

## ✅ Opción 3: Proxy con Autenticación

Pones un proxy (Nginx, Envoy) delante de Temporal UI:

```
Usuario → Proxy (Auth) → Temporal UI
          ↓
       Valida JWT
       Permite/Bloquea
```

**Limitaciones:**
- Solo controla acceso ON/OFF
- No filtra por namespace dentro de la UI
- Usuario ve todos los namespaces si tiene acceso

---

## 📊 Comparación

| Opción | Control Granular | Complejidad | Costo | Recomendado |
|--------|------------------|-------------|-------|-------------|
| Temporal UI Nativa | ❌ No | Baja | Gratis | No |
| Custom UI | ✅ Total | Media | Gratis | ✅ Sí |
| Temporal Cloud | ✅ Total | Baja | Alto | Enterprise |
| Proxy + Auth | ⚠️ Limitado | Media | Gratis | Casos simples |

---

## 🎯 Recomendación para Tu Caso

**Escenario:** Usuario puede acceder a N namespaces

### Solución: Custom UI

```python
# Base de datos de permisos
users = {
    "admin@empresa.com": {
        "namespaces": ["tenant-chogar", "tenant-amovil", "tenant-afijo"]
    },
    "manager@empresa.com": {
        "namespaces": ["tenant-chogar", "tenant-amovil"]  # Solo 2
    },
    "operator@empresa.com": {
        "namespaces": ["tenant-chogar"]  # Solo 1
    }
}

# Tu UI consulta solo namespaces permitidos
@app.get("/workflows")
async def list_workflows(user: User):
    workflows = []
    for ns in user.allowed_namespaces:
        client = await Client.connect("temporal:7233", namespace=ns)
        workflows.extend(await client.list_workflows())
    return workflows
```

---

## 🚀 Próximos Pasos

1. **Probar demo:** `python custom_ui_example.py`
2. **Adaptar a tu stack:** React, Vue, Angular, etc.
3. **Integrar con tu auth:** OAuth, LDAP, etc.
4. **Agregar features:** Filtros, búsqueda, gráficos

---

## 💡 Bonus: API Gateway Pattern

```python
# Tu API expone endpoints seguros
@app.get("/api/workflows")
async def get_workflows(current_user: User = Depends(get_current_user)):
    # Valida permisos
    # Consulta Temporal
    # Retorna solo lo permitido
    pass

# Frontend consume tu API (no Temporal directamente)
fetch("/api/workflows", {
    headers: { "Authorization": `Bearer ${token}` }
})
```

**Ventaja:** Frontend nunca habla directamente con Temporal.
