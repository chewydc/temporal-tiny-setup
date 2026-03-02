# 🚀 INICIO RÁPIDO - 3 Pasos

## Paso 1: Instalar MCP

```bash
cd C:/Users/u603924/PycharmProjects/Automation/temporal-tiny-setup/07-airflow-to-temporal-mcp-example
pip install -e .
```

## Paso 2: Configurar Kiro

1. Abrir archivo: `.kiro/settings/mcp.json` (en la raíz de tu workspace)

2. Copiar este contenido (o agregar al existente):

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

3. Guardar archivo

4. Reconectar MCP:
   - `Ctrl+Shift+P`
   - Buscar: `MCP: Reconnect All Servers`
   - Esperar confirmación

## Paso 3: Probar

En el chat de Kiro, escribir:

```
Lista las herramientas disponibles del MCP airflow-to-temporal
```

Deberías ver 6 tools:
- analyze_dag
- generate_workflow
- generate_activities
- generate_worker
- validate_migration
- list_centralized_activities

---

## 🎯 Usar en el Demo

### Opción A: Con Kiro (Recomendado)

En el chat:

```
Analiza este DAG usando airflow-to-temporal
```

Adjuntar: `input_real_dag_chogar/chogar_despertar_tr.py`

Luego:

```
Genera el código en fase HYBRID y guárdalo en output_mcp_server/
```

### Opción B: Script Python (Backup)

Si el MCP falla:

```bash
cd examples/02-RealDag
python demo_without_ai.py
```

---

## ❓ Troubleshooting

### MCP no aparece

1. Verificar instalación:
```bash
python -c "import airflow_to_temporal_mcp; print('OK')"
```

2. Ver logs:
   - En Kiro: View → Output → "MCP Servers"

3. Verificar ruta en mcp.json (debe ser absoluta)

### Kiro no usa el MCP

Ser explícito en el prompt:

```
Usa el MCP airflow-to-temporal para analizar este DAG
```

---

## 📖 Más Info

Ver: `DEMO_SCRIPT.md` para guía completa del demo
