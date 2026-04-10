# 🎯 GUÍA DEMO EN VIVO - MCP Server

## 📋 PREPARACIÓN (Antes de la reunión)

### 1. Instalar el MCP Server

```bash
cd temporal-tiny-setup/07-airflow-to-temporal-mcp-example
pip install -e .
```

### 2. Configurar Kiro (tu IDE actual)

Crear/editar archivo: `.kiro/settings/mcp.json`

```json
{
  "mcpServers": {
    "airflow-to-temporal": {
      "command": "python",
      "args": ["-m", "airflow_to_temporal_mcp"],
      "env": {
        "PLATFORM_CONFIG": "C:/Users/u603924/PycharmProjects/Automation/temporal-tiny-setup/07-airflow-to-temporal-mcp-example/config/platform_config.yaml"
      }
    }
  }
}
```

**IMPORTANTE:** Usa la ruta COMPLETA a tu `platform_config.yaml`

### 3. Reconectar MCP en Kiro

- Presiona `Ctrl+Shift+P`
- Busca: `MCP: Reconnect All Servers`
- Verifica que aparezca "airflow-to-temporal" conectado

### 4. Verificar que funciona

En el chat de Kiro, escribe:

```
¿Qué herramientas tienes disponibles del MCP airflow-to-temporal?
```

Deberías ver 6 tools:
- analyze_dag
- generate_workflow
- generate_activities
- generate_worker
- validate_migration
- list_centralized_activities

---

## 🎬 SCRIPT DEL DEMO (5-7 minutos)

### PASO 1: Contexto (30 segundos)

**Tú dices:**

> "Tenemos 200+ DAGs en Airflow que queremos migrar a Temporal. Hacerlo manual toma 4-6 horas por DAG. Con este MCP, lo reducimos a minutos y garantizamos que todos usen el mismo estándar de plataforma."

### PASO 2: Mostrar el DAG Original (30 segundos)

**Abrir archivo:** `examples/02-RealDag/input_real_dag_chogar/chogar_despertar_tr.py`

**Tú dices:**

> "Este DAG real consulta BigQuery, llama APIs de HaaS (nuestra librería interna), guarda en MongoDB y envía email. Tiene 4 tasks con dependencias."

**Scrollear rápido mostrando:**
- Imports de HaaS (`haas_reset_tr`, `haas_status`)
- MongoDB Hook
- BigQuery operators
- ThreadPoolExecutor

### PASO 3: Analizar con MCP (2 minutos)

**En el chat de Kiro, escribir:**

```
Analiza este DAG usando el MCP airflow-to-temporal
```

**Adjuntar archivo:** `chogar_despertar_tr.py` (arrastrarlo al chat)

**Esperar respuesta del MCP...**

**Tú explicas mientras procesa:**

> "El MCP está leyendo el código con AST, identificando operators, dependencias, y lo más importante: detectando qué Activities ya existen en nuestro SDK centralizado."

**Cuando responda, señalar:**

✅ "Miren, detectó que `haas_reset_tr` y `haas_status` son de librería centralizada"  
✅ "MongoDB Hook también lo identifica como reutilizable"  
✅ "BigQuery es operator estándar"  
⚠️ "La lógica de ThreadPoolExecutor necesita Activity personalizada"

### PASO 4: Generar Código (2 minutos)

**En el chat, escribir:**

```
Genera el código en fase HYBRID y guárdalo en examples/02-RealDag/output_mcp_server/
```

**Esperar que genere los 3 archivos...**

**Tú explicas:**

> "Fase HYBRID significa que vamos migrando de a poco. Las Activities que ya existen en el SDK las importa directamente. Las nuevas las genera con TODOs para que completemos la lógica específica."

**Cuando termine, abrir los archivos generados:**

1. **workflows.py** - Mostrar:
   - Decorador `@workflow.defn`
   - Imports desde `platform_sdk` (centralizados)
   - Manejo de errores y compensación

2. **activities.py** - Mostrar:
   - Imports de Activities centralizadas: `from platform_sdk.haas import haas_reset_tr`
   - Activities personalizadas con TODOs
   - Decoradores `@activity.defn`

3. **run_worker.py** - Mostrar:
   - Configuración de worker
   - Task queue naming: `{tenant}-{workflow_type}`
   - Observabilidad incluida

### PASO 5: Destacar Beneficios (1 minuto)

**Tú dices:**

> "Esto que acaban de ver en 5 minutos, manualmente tomaría 4-6 horas. Pero lo más importante no es la velocidad, es la GOBERNANZA:"

**Señalar en pantalla:**

1. **No duplica código:** Usa Activities del SDK
2. **Naming estandarizado:** Sigue convenciones de plataforma
3. **Workers configurados:** Con observabilidad y recursos correctos
4. **Migración gradual:** Fase HYBRID permite validar antes de deprecar Airflow

### PASO 6: Mostrar Configuración (1 minuto)

**Abrir:** `config/platform_config.yaml`

**Tú dices:**

> "Toda la inteligencia del MCP viene de este archivo. Aquí definimos qué Activities son centralizadas, qué patrones detectar, naming conventions, etc."

**Scrollear mostrando:**

```yaml
centralized_activities:
  - name: "test_connectivity"
    triggers: ["ping", "connectivity"]
    
  - name: "deploy_router"
    triggers: ["ansible", "router", "deploy"]
```

**Tú dices:**

> "Cuando el MCP ve 'ansible' en un BashOperator, automáticamente sabe que debe usar `deploy_router` del SDK. No genera código nuevo."

### PASO 7: Cierre (30 segundos)

**Tú dices:**

> "En resumen: todos los devs van a usar IA para migrar código. Con este MCP, moldeamos esa respuesta para que se alinee a nuestra plataforma. Evitamos que cada uno reinvente la rueda y garantizamos calidad uniforme."

**Preguntar:**

> "¿Preguntas?"

---

## 🎯 TIPS PARA EL DEMO

### Si algo falla:

1. **MCP no responde:**
   - Verificar en Output → "MCP Servers" que esté conectado
   - Reconectar: `Ctrl+Shift+P` → `MCP: Reconnect`

2. **No encuentra platform_config.yaml:**
   - Usar ruta absoluta en mcp.json
   - Verificar que el archivo existe

3. **Kiro no usa el MCP:**
   - Ser explícito: "Usa el MCP airflow-to-temporal para..."
   - Mencionar el nombre del server

### Frases clave para tu jefe:

- "Reducimos tiempo de migración de 6 horas a 5 minutos"
- "Garantizamos que todos usen el SDK centralizado"
- "Evitamos duplicación de código y deuda técnica"
- "Gobernanza sin fricción - los devs usan IA, nosotros controlamos el output"

### Backup plan:

Si el MCP falla completamente, tienes el script Python:

```bash
cd examples/02-RealDag
python demo_without_ai.py
```

(Voy a crear este script ahora)

---

## ✅ CHECKLIST PRE-DEMO

- [ ] MCP instalado: `pip install -e .`
- [ ] mcp.json configurado con ruta absoluta
- [ ] MCP reconectado en Kiro
- [ ] Verificado que responde: "¿Qué tools tienes?"
- [ ] Archivos de ejemplo listos
- [ ] Output folder vacía (para mostrar generación limpia)
- [ ] Script de backup listo

---

## 🚀 DESPUÉS DEL DEMO

Si aprueban, próximos pasos:

1. Agregar más Activities centralizadas al `platform_config.yaml`
2. Migrar 2-3 DAGs piloto
3. Documentar learnings
4. Rollout gradual al equipo
