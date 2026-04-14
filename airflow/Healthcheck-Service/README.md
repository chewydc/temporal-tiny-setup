# Healthcheck Service + Site Controller

## Overview

This directory contains standalone versions of the healthcheck and site-controller components for Airflow HA setup. These components work together to provide automatic failover capabilities.

## Components

### 1. Healthcheck Service
- **Purpose**: Observes and reports system health status
- **Type**: Stateless sensor
- **Responsibilities**: 
  - Monitor Airflow API health
  - Monitor Redis connectivity
  - Monitor DB primary status via MaxScale
  - Report critical health status and failover needs

### 2. Site Controller
- **Purpose**: Acts on health status to control scheduler and DB failover
- **Type**: Stateful actuator
- **Responsibilities**:
  - Follow DB primary (scheduler ON when DB is local)
  - Control Airflow scheduler containers (pause/unpause)
  - Force DB switchover when needed

## Recent Bug Fixes

### ✅ Fixed Ping-Pong Switchover Issue

**Problem**: Site controllers were creating an unstable ping-pong effect, rapidly switching DB primary between regions.

**Root Cause**: Incorrect switchover logic was triggering switchovers when a region already had the DB locally but had critical check failures.

**Solution**: Fixed switchover logic to only trigger when:
- `db_primary=False` (region doesn't have DB locally)
- `needs_failover=True` (region needs DB access)

**Before (incorrect)**:
```python
# Triggered switchover when already had DB locally
elif db_primary and needs_failover:
```

**After (correct)**:
```python
# Only triggers switchover when DB is needed but not local
elif not db_primary and needs_failover:
```

### ✅ Multi-MaxScale Failover Support

**Enhancement**: Added support for multiple MaxScale URLs with automatic failover.

**Configuration**:
```yaml
environment:
  - MAXSCALE_URLS=http://maxscale-hornos:8989,http://maxscale-sanlorenzo:8990
```

**Behavior**: 
- Tries primary MaxScale first
- Automatically fails over to backup MaxScale if primary is unavailable
- Uses correct switchover API endpoint: `/v1/maxscale/modules/mariadbmon/switchover?{monitor}`

## Configuration

### Environment Variables

#### Healthcheck Service
```yaml
environment:
  - REGION_NAME=hornos                    # Region identifier
  - AIRFLOW_URL=http://airflow:8080       # Airflow API endpoint
  - MAXSCALE_URL=http://maxscale:8989     # MaxScale API endpoint
  - MAXSCALE_USER=admin                   # MaxScale credentials
  - MAXSCALE_PASS=mariadb
  - LOCAL_DB_SERVER=HORNOS                # Local DB server name in MaxScale
  - REDIS_HOST=redis-hornos               # Redis connection
  - REDIS_PORT=6379
  - CHECKS=airflow,redis,db_primary       # Health checks to perform
  - CRITICAL_CHECKS=airflow,db_primary    # Critical checks for failover
  - CHECK_INTERVAL=10                     # Check frequency (seconds)
  - FAILURE_THRESHOLD=2                   # Failures before marking unhealthy
  - RECOVERY_THRESHOLD=1                  # Successes before marking healthy
```

#### Site Controller
```yaml
environment:
  - REGION_NAME=hornos                              # Region identifier
  - HEALTHCHECK_URL=http://healthcheck:8000         # Local healthcheck URL
  - MAXSCALE_URLS=http://maxscale1:8989,http://maxscale2:8990  # Multiple MaxScale URLs
  - MAXSCALE_USER=admin                             # MaxScale credentials
  - MAXSCALE_PASS=mariadb
  - LOCAL_DB_SERVER=HORNOS                          # Local DB server name
  - MAXSCALE_MONITOR=Replication-Monitor            # MaxScale monitor name
  - SCHEDULER_CONTAINER=airflow-scheduler-hornos    # Scheduler container name
  - DAG_PROCESSOR_CONTAINER=airflow-dag-processor-hornos  # DAG processor container
  - FORCE_SWITCHOVER=true                           # Enable automatic switchover
  - SWITCHOVER_THRESHOLD=3                          # Checks before switchover
  - FAILOVER_THRESHOLD=2                            # Checks before demote
  - RECOVERY_THRESHOLD=1                            # Checks before promote
  - CHECK_INTERVAL=10                               # Check frequency (seconds)
```

## Decision Logic

### Site Controller States

1. **ACTIVE**: 
   - Conditions: `db_primary=True` AND `critical_healthy=True`
   - Actions: Scheduler ON, HAProxy returns 200

2. **PASSIVE**: 
   - Conditions: `db_primary=False` OR `critical_healthy=False`
   - Actions: Scheduler OFF, HAProxy returns 503

3. **SWITCHOVER**: 
   - Conditions: `db_primary=False` AND `needs_failover=True` for `SWITCHOVER_THRESHOLD` consecutive checks
   - Actions: Force DB switchover via MaxScale API

### Correct Failover Scenario

1. **Initial State**: Hornos ACTIVE (has DB), San Lorenzo PASSIVE
2. **MaxScale Hornos goes down**: Hornos loses DB access
3. **Hornos detects**: `db_primary=False` and `needs_failover=True`
4. **Hornos executes switchover**: DB moves to San Lorenzo
5. **San Lorenzo detects**: `db_primary=True` and `critical_healthy=True`
6. **San Lorenzo promotes**: Becomes ACTIVE
7. **Stable**: San Lorenzo ACTIVE, Hornos PASSIVE - no more switchovers

## API Endpoints

### Healthcheck Service
- `GET /health` - Detailed health status
- `GET /ready` - Ready status for site-controller consumption

### Site Controller
- `GET /health` - Detailed controller state
- `GET /region-health` - HAProxy health check (200/503)
- `GET /role` - Current role (active/passive)

## Usage

### Standalone Deployment
```bash
cd C:\Users\u603924\PycharmProjects\Automation\temporal-tiny-setup\airflow\Healthcheck-Service
docker-compose up -d
```

### Integration with Full HA Setup
Copy the corrected configuration to your main deployment:
- Use `MAXSCALE_URLS` instead of `MAXSCALE_URL`
- Ensure site_controller.py has the fixed switchover logic

## Monitoring

### Health Check URLs
- Hornos Healthcheck: http://localhost:8001/health
- San Lorenzo Healthcheck: http://localhost:8002/health
- Hornos Site Controller: http://localhost:8011/health
- San Lorenzo Site Controller: http://localhost:8012/health

### Log Monitoring
```bash
# Watch site controller logs
docker logs -f site-controller-hornos
docker logs -f site-controller-sanlorenzo

# Watch healthcheck logs
docker logs -f healthcheck-hornos
docker logs -f healthcheck-sanlorenzo
```

## Troubleshooting

### Common Issues

1. **Ping-pong behavior**: Ensure you're using the fixed switchover logic
2. **MaxScale connection failures**: Check MAXSCALE_URLS configuration
3. **Docker socket permissions**: Ensure site-controller can access `/var/run/docker.sock`
4. **Switchover API errors**: Verify MaxScale monitor name and API endpoint format

### Debug Commands
```bash
# Check MaxScale server status
curl -u admin:mariadb http://localhost:8989/v1/servers/HORNOS

# Force manual switchover
curl -u admin:mariadb -X POST http://localhost:8989/v1/maxscale/modules/mariadbmon/switchover?Replication-Monitor

# Check site controller state
curl http://localhost:8011/health
```