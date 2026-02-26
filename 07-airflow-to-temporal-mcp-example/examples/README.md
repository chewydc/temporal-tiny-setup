# Ejemplos de Uso

## sample_dag.py

DAG de ejemplo de Airflow que configura un router de red.

**Características:**
- 4 tasks con dependencias
- Mix de PythonOperator y BashOperator
- Integración con Ansible y firewall

**Para probar:**
```
En Kiro: "Analiza este DAG"
[Adjuntar: sample_dag.py]
```

## migrate_example.py

Script de demostración del flujo de migración.

**Ejecutar:**
```bash
python examples/migrate_example.py
```

**Muestra:**
- Análisis del DAG
- Recomendación de fase
- Estructura de archivos generados
