"""
Custom UI con Control de Acceso - Demo
========================================

Ejemplo de cómo construir tu propia UI que:
1. Autentica usuarios
2. Muestra solo workflows de namespaces permitidos
3. Permite acceso a múltiples namespaces por usuario
"""

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from temporalio.client import Client
import jwt
from typing import List

app = FastAPI()

# Simula base de datos de usuarios y permisos
USERS_DB = {
    "admin@empresa.com": {
        "password": "admin123",
        "namespaces": ["chogar", "amovil", "afijo"],  # Ve todos los tenants
        "role": "admin"
    },
    "operator_chogar@empresa.com": {
        "password": "chogar123",
        "namespaces": ["chogar"],  # Solo chogar
        "role": "operator"
    },
    "manager@empresa.com": {
        "password": "manager123",
        "namespaces": ["chogar", "amovil"],  # Ve chogar y amovil
        "role": "manager"
    }
}

SECRET_KEY = "tu-secret-key-aqui"

# ============================================================================
# AUTENTICACIÓN
# ============================================================================

def create_token(email: str) -> str:
    """Crea JWT con info del usuario"""
    user = USERS_DB[email]
    return jwt.encode({
        "email": email,
        "namespaces": user["namespaces"],
        "role": user["role"]
    }, SECRET_KEY, algorithm="HS256")

def get_current_user(token: str):
    """Valida token y retorna info del usuario"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except:
        raise HTTPException(401, "Token inválido")

# ============================================================================
# ENDPOINTS DE AUTENTICACIÓN
# ============================================================================

@app.post("/login")
async def login(email: str, password: str):
    """Login de usuario"""
    user = USERS_DB.get(email)
    
    if not user or user["password"] != password:
        raise HTTPException(401, "Credenciales inválidas")
    
    token = create_token(email)
    
    return {
        "token": token,
        "email": email,
        "namespaces": user["namespaces"],
        "role": user["role"]
    }

# ============================================================================
# ENDPOINTS DE WORKFLOWS (Con Control de Acceso)
# ============================================================================

@app.get("/workflows")
async def list_workflows(token: str, namespace: str = None):
    """
    Lista workflows de los namespaces permitidos para el usuario.
    
    Si especifica namespace, valida que tenga permiso.
    """
    user = get_current_user(token)
    allowed_namespaces = user["namespaces"]
    
    # Si pide un namespace específico, validar permiso
    if namespace:
        if namespace not in allowed_namespaces:
            raise HTTPException(403, f"No tienes acceso a {namespace}")
        namespaces_to_query = [namespace]
    else:
        # Listar de todos sus namespaces permitidos
        namespaces_to_query = allowed_namespaces
    
    # Consultar workflows de cada namespace permitido
    all_workflows = []
    
    for ns in namespaces_to_query:
        try:
            print(f"[DEBUG] Consultando namespace: {ns}")
            client = await Client.connect("localhost:7233", namespace=ns)
            
            count = 0
            async for workflow in client.list_workflows():
                all_workflows.append({
                    "namespace": ns,
                    "workflow_id": workflow.id,
                    "status": workflow.status.name,
                    "workflow_type": workflow.workflow_type,
                    "start_time": workflow.start_time.isoformat() if workflow.start_time else None
                })
                count += 1
                if count >= 10:  # Limitar por namespace
                    break
            
            print(f"[DEBUG] Encontrados {count} workflows en {ns}")
                    
        except Exception as e:
            print(f"[ERROR] Error consultando {ns}: {e}")
    
    return {
        "user": user["email"],
        "allowed_namespaces": allowed_namespaces,
        "workflows": all_workflows,
        "total": len(all_workflows)
    }

@app.get("/workflows/{workflow_id}")
async def get_workflow_detail(workflow_id: str, namespace: str, token: str):
    """
    Obtiene detalle de un workflow específico.
    Valida que el usuario tenga acceso al namespace.
    """
    user = get_current_user(token)
    
    # Validar acceso al namespace
    if namespace not in user["namespaces"]:
        raise HTTPException(403, f"No tienes acceso a {namespace}")
    
    # Consultar workflow
    client = await Client.connect("localhost:7233", namespace=namespace)
    handle = client.get_workflow_handle(workflow_id)
    desc = await handle.describe()
    
    return {
        "workflow_id": workflow_id,
        "namespace": namespace,
        "status": desc.status.name,
        "workflow_type": desc.workflow_type,
        "start_time": desc.start_time.isoformat() if desc.start_time else None,
        "history_length": desc.history_length
    }

# ============================================================================
# UI HTML SIMPLE
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Dashboard HTML simple con login"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Temporal Custom UI</title>
        <style>
            body { font-family: Arial; margin: 40px; }
            .login-box { max-width: 400px; }
            .workflows { display: none; }
            table { border-collapse: collapse; width: 100%; margin-top: 20px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #4CAF50; color: white; }
            .namespace-badge { 
                background: #2196F3; 
                color: white; 
                padding: 4px 8px; 
                border-radius: 4px;
                font-size: 12px;
            }
        </style>
    </head>
    <body>
        <h1>🔐 Temporal Custom UI - Control de Acceso</h1>
        
        <!-- Login Form -->
        <div class="login-box" id="loginBox">
            <h2>Login</h2>
            <input type="email" id="email" placeholder="Email" style="width: 100%; padding: 8px; margin: 5px 0;">
            <input type="password" id="password" placeholder="Password" style="width: 100%; padding: 8px; margin: 5px 0;">
            <button onclick="login()" style="padding: 10px 20px; margin-top: 10px;">Login</button>
            
            <div style="margin-top: 20px; font-size: 12px; color: #666;">
                <b>Usuarios de prueba:</b><br>
                • admin@empresa.com / admin123 (ve todos)<br>
                • operator_chogar@empresa.com / chogar123 (solo chogar)<br>
                • manager@empresa.com / manager123 (chogar + amovil)
            </div>
        </div>
        
        <!-- Workflows Dashboard -->
        <div class="workflows" id="workflowsBox">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2>Mis Workflows</h2>
                    <p>Usuario: <span id="userEmail"></span></p>
                    <p>Namespaces permitidos: <span id="allowedNamespaces"></span></p>
                </div>
                <button onclick="logout()">Logout</button>
            </div>
            
            <button onclick="loadWorkflows()" style="padding: 8px 16px;">🔄 Refrescar</button>
            
            <table>
                <thead>
                    <tr>
                        <th>Namespace</th>
                        <th>Workflow ID</th>
                        <th>Status</th>
                        <th>Type</th>
                        <th>Start Time</th>
                    </tr>
                </thead>
                <tbody id="workflowsTable"></tbody>
            </table>
        </div>
        
        <script>
            let token = null;
            
            async function login() {
                const email = document.getElementById('email').value;
                const password = document.getElementById('password').value;
                
                const response = await fetch(`/login?email=${email}&password=${password}`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    const data = await response.json();
                    token = data.token;
                    
                    document.getElementById('loginBox').style.display = 'none';
                    document.getElementById('workflowsBox').style.display = 'block';
                    document.getElementById('userEmail').textContent = data.email;
                    document.getElementById('allowedNamespaces').textContent = data.namespaces.join(', ');
                    
                    loadWorkflows();
                } else {
                    alert('Login fallido');
                }
            }
            
            async function loadWorkflows() {
                const response = await fetch(`/workflows?token=${token}`);
                const data = await response.json();
                
                const tbody = document.getElementById('workflowsTable');
                tbody.innerHTML = '';
                
                data.workflows.forEach(wf => {
                    const row = tbody.insertRow();
                    row.innerHTML = `
                        <td><span class="namespace-badge">${wf.namespace}</span></td>
                        <td>${wf.workflow_id}</td>
                        <td>${wf.status}</td>
                        <td>${wf.workflow_type}</td>
                        <td>${wf.start_time || 'N/A'}</td>
                    `;
                });
            }
            
            function logout() {
                token = null;
                document.getElementById('loginBox').style.display = 'block';
                document.getElementById('workflowsBox').style.display = 'none';
            }
        </script>
    </body>
    </html>
    """

# ============================================================================
# EJECUTAR
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("CUSTOM UI CON CONTROL DE ACCESO")
    print("="*60)
    print("\n🌐 Abriendo en: http://localhost:8000")
    print("\n👥 Usuarios de prueba:")
    print("  • admin@empresa.com / admin123 (ve todos)")
    print("  • operator_chogar@empresa.com / chogar123 (solo chogar)")
    print("  • manager@empresa.com / manager123 (chogar + amovil)")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
