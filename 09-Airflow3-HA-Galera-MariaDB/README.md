# Airflow 3.x HA + Galera Cluster (3 Regiones)

## Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HORNOS        │    │  SAN LORENZO    │    │   TUCUMAN       │
│ (172.20.0.0/24) │    │ (172.21.0.0/24) │    │ (172.22.0.0/24) │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ Airflow API     │    │ Airflow API     │    │                 │
│ Airflow Sched   │    │ Airflow Sched   │    │                 │
│ Airflow Worker  │    │ Airflow Worker  │    │                 │
│ Redis           │    │ Redis           │    │                 │
│ Galera Node 1   │    │ Galera Node 2   │    │ Galera Arbitr.  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   VROUTER       │
                    │ (Conectividad)  │
                    └─────────────────┘
```

## Características

- **Galera Cluster Puro**: Sin MaxScale, conexión directa a nodos
- **3 Regiones Separadas**: Cada una en su propia red
- **Airflow HA**: Activo en Hornos y San Lorenzo
- **Arbitrator**: Solo en Tucumán para quorum
- **Simulación de Fallos**: Control de conectividad por región

## Componentes

### Región Hornos (172.20.0.0/24)
- Airflow completo (API, Scheduler, Worker)
- Redis local
- MariaDB Galera Node 1 (Inicializador)
- Puerto 8080 (Airflow UI)
- Puerto 3306 (MariaDB)

### Región San Lorenzo (172.21.0.0/24)
- Airflow completo (API, Scheduler, Worker)
- Redis local
- MariaDB Galera Node 2
- Puerto 8081 (Airflow UI)
- Puerto 3307 (MariaDB)

### Región Tucumán (172.22.0.0/24)
- Solo Galera Arbitrator (garbd)
- Sin datos, solo voto para quorum

### Router Central
- Conecta las 3 redes
- Permite desconectar regiones específicas
- Simula fallos de conectividad

## Inicio Rápido

```bash
# 1. Iniciar todo el cluster
start.bat

# 2. Verificar estado
status.bat

# 3. Probar conectividad
network-control.bat status
```

## Accesos

- **Airflow Hornos**: http://localhost:8080
- **Airflow San Lorenzo**: http://localhost:8081
- **MariaDB Hornos**: localhost:3306
- **MariaDB San Lorenzo**: localhost:3307

## Pruebas de Failover

### 1. Desconectar Hornos
```bash
network-control.bat disconnect hornos
```
- San Lorenzo + Tucumán mantienen quorum (2/3)
- Airflow sigue funcionando desde San Lorenzo
- Galera cluster operativo

### 2. Desconectar San Lorenzo
```bash
network-control.bat disconnect sanlorenzo
```
- Hornos + Tucumán mantienen quorum (2/3)
- Airflow sigue funcionando desde Hornos
- Galera cluster operativo

### 3. Desconectar Tucumán
```bash
network-control.bat disconnect tucuman
```
- Hornos + San Lorenzo mantienen quorum (2/2)
- Ambos Airflow funcionando
- Galera cluster operativo

### 4. Reconectar Todo
```bash
network-control.bat reconnect
```
- Todas las regiones vuelven online
- Galera sincroniza automáticamente
- Airflow HA completo

## Comandos Útiles

### Estado del Cluster
```bash
# Ver estado general
network-control.bat status

# Monitor en tiempo real
status.bat

# Test de conectividad
network-control.bat test
```

### Consultas Galera Directas
```bash
# Tamaño del cluster
docker exec cluster-monitor mysql -h galera-hornos -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_cluster_size'"

# Estado de sincronización
docker exec cluster-monitor mysql -h galera-hornos -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_ready'"

# Nodos en el cluster
docker exec cluster-monitor mysql -h galera-hornos -u root -proot_pass -e "SHOW STATUS LIKE 'wsrep_incoming_addresses'"
```

## Escenarios de Prueba

### Escenario 1: Fallo de Región Principal
1. Ejecutar DAG `failover_test`
2. `network-control.bat disconnect hornos`
3. Verificar que el DAG completa desde San Lorenzo

### Escenario 2: Split-Brain Prevention
1. `network-control.bat disconnect tucuman`
2. `network-control.bat disconnect hornos`
3. Solo San Lorenzo queda (1/3) → No-primary mode
4. Verificar que no acepta escrituras

### Escenario 3: Recuperación Automática
1. Desconectar cualquier región
2. Esperar 2 minutos
3. `network-control.bat reconnect`
4. Verificar sincronización automática

## Configuración Galera

### Quorum y Weights
- Cada nodo: `pc.weight=1`
- Quorum mínimo: 2/3 nodos
- Arbitrator cuenta como voto completo

### SST (State Snapshot Transfer)
- Método: `rsync`
- Usuario: `sst_user/sst_pass`
- Automático en join de nodos

### Networking
- Puerto Galera: 4567
- Puerto MySQL: 3306
- Bind: 0.0.0.0 (todas las interfaces)

## Troubleshooting

### Cluster No Inicia
```bash
# Verificar logs
docker-compose logs galera-hornos
docker-compose logs galera-sanlorenzo

# Reiniciar cluster completo
clean.bat
start.bat
```

### Split-Brain Recovery
```bash
# Si el cluster se divide, reiniciar desde Hornos
docker exec galera-hornos mysql -u root -proot_pass -e "SET GLOBAL wsrep_provider_options='pc.bootstrap=true'"
```

### Arbitrator No Conecta
```bash
# Verificar logs del arbitrator
docker-compose logs galera-arbitrator

# Reiniciar solo el arbitrator
docker-compose restart galera-arbitrator
```

## Archivos de Configuración

- `docker-compose.yml`: Definición completa del cluster
- `galera/hornos-init.sql`: Inicialización nodo Hornos
- `galera/sanlorenzo-init.sql`: Inicialización nodo San Lorenzo
- `network-control.bat`: Control de conectividad
- `start.bat`: Inicio secuencial del cluster
- `status.bat`: Monitor en tiempo real

## Ventajas de esta Arquitectura

1. **Sin MaxScale**: Menos complejidad, conexión directa
2. **Verdadero Multi-Master**: Escrituras en cualquier nodo
3. **Quorum Automático**: Prevención de split-brain
4. **Simulación Realista**: 3 regiones geográficas
5. **Failover Transparente**: Sin intervención manual
6. **Airflow HA**: Redundancia completa de servicios