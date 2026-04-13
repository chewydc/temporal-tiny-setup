#!/usr/bin/env python3
"""
==============================================================================
 HEALTHCHECK SERVICE — Sensor de salud configurable para Airflow HA
==============================================================================

 Microservicio STATELESS que evalúa la salud de los componentes de una región
 y expone el resultado via HTTP.

 NO toma acciones. Solo OBSERVA y REPORTA.

 CONFIGURACIÓN DE CHECKS:
 ────────────────────────
 Cada check se configura via variables de entorno:

   CHECKS=airflow,redis,db_primary        ← checks habilitados (lista separada por coma)
   CRITICAL_CHECKS=airflow,db_primary     ← checks que disparan failover si fallan
                                             (los demás son informativos)

 Esto permite que en producción, via ConfigMap, se ajuste qué componentes
 se evalúan y cuáles son críticos sin tocar código.

 Ejemplo:
   - CHECKS=airflow,redis,db_primary,custom_api
   - CRITICAL_CHECKS=airflow,db_primary
   → Si redis cae: se reporta pero NO dispara failover
   → Si airflow cae: se reporta Y dispara failover

 CHECKS DISPONIBLES:
 ───────────────────
   airflow     → Airflow API Server responde en /api/v2/monitor/health
   redis       → Redis responde a PING
   db_primary  → La DB local es Master en MaxScale (via REST API)

 MEJORAS v2.0:
 ─────────────
   - Reset automático de contadores cuando cambia el primary de DB
   - Reset inteligente: detecta failovers exitosos sin depender de estado previo
   - Thresholds reducidos para failover más rápido (FAILURE=2, RECOVERY=1)
   - Detección inteligente de cambios de topología
   - Funciona sin intervención humana, incluso después de reinicios

 ENDPOINTS:
 ──────────
   GET /health         → Estado detallado de todos los checks
   GET /region-health  → Para HAProxy (200 si critical checks OK, 503 si no)
   GET /ready          → Para el site-controller (incluye flag de failover)
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
from aiohttp import web
import aiohttp.web_runner


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

REGION_NAME = os.getenv('REGION_NAME', 'unknown')
LISTEN_PORT = int(os.getenv('LISTEN_PORT', '8000'))
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '10'))

# --- Checks habilitados y cuáles son críticos ---
# Formato: lista separada por comas, sin espacios
# CHECKS: todos los que se ejecutan
# CRITICAL_CHECKS: los que, si fallan, indican que la región no puede servir
ENABLED_CHECKS = [c.strip() for c in os.getenv('CHECKS', 'airflow,redis,db_primary').split(',') if c.strip()]
CRITICAL_CHECKS = [c.strip() for c in os.getenv('CRITICAL_CHECKS', 'airflow,db_primary').split(',') if c.strip()]

# --- Hysteresis (v2.0: thresholds reducidos para failover más rápido) ---
FAILURE_THRESHOLD = int(os.getenv('FAILURE_THRESHOLD', '2'))  # era 3
RECOVERY_THRESHOLD = int(os.getenv('RECOVERY_THRESHOLD', '1'))  # era 2

# --- Airflow ---
AIRFLOW_URL = os.getenv('AIRFLOW_URL', 'http://localhost:8080')

# --- Redis ---
REDIS_HOST = os.getenv('REDIS_HOST', 'redis-hornos')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

# --- MaxScale (para db_primary check) ---
MAXSCALE_URL = os.getenv('MAXSCALE_URL', 'http://maxscale-hornos:8989')
MAXSCALE_USER = os.getenv('MAXSCALE_USER', 'admin')
MAXSCALE_PASS = os.getenv('MAXSCALE_PASS', 'mariadb')
LOCAL_DB_SERVER = os.getenv('LOCAL_DB_SERVER', 'HORNOS')

# --- Custom HTTP checks (extensible) ---
# Formato: nombre:url,nombre:url
# Ejemplo: CUSTOM_CHECKS=vault:http://vault:8200/v1/sys/health,kafka:http://kafka:8083/health
CUSTOM_CHECKS_RAW = os.getenv('CUSTOM_CHECKS', '')


# =============================================================================
# LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [healthcheck-%(name)s] %(message)s'
)
logger = logging.getLogger(REGION_NAME)


# =============================================================================
# ESTADO
# =============================================================================

check_results: Dict[str, Dict] = {}
# Contadores de hysteresis por check
failure_counters: Dict[str, int] = {}
# Estado consolidado
region_status = {
    "healthy": False,
    "critical_healthy": False,
    "needs_failover": False,
    "last_check": None,
}
# Tracking para detectar cambios de primary
last_primary_server: Optional[str] = None


# =============================================================================
# CHECK IMPLEMENTATIONS
# =============================================================================

class HealthChecks:
    """
    Implementaciones de cada tipo de check.

    Para agregar un check nuevo:
    1. Agregar un método async check_<nombre>(self) -> Dict
    2. Registrarlo en REGISTRY
    3. Configurar via env: CHECKS=...,<nombre>  CRITICAL_CHECKS=...,<nombre>
    """

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        # Parsear custom checks
        self.custom_checks = {}
        if CUSTOM_CHECKS_RAW:
            for entry in CUSTOM_CHECKS_RAW.split(','):
                if ':' in entry:
                    name, url = entry.split(':', 1)
                    self.custom_checks[name.strip()] = url.strip()

    async def start(self):
        timeout = aiohttp.ClientTimeout(total=8)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def stop(self):
        if self.session:
            await self.session.close()

    # --- Airflow ---
    async def check_airflow(self) -> Dict:
        """Verifica que Airflow API Server responda."""
        try:
            url = f"{AIRFLOW_URL}/api/v2/monitor/health"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return {"status": "healthy", "detail": "api_server_responding"}
                return {"status": "unhealthy", "detail": f"http_{resp.status}"}
        except asyncio.TimeoutError:
            return {"status": "unhealthy", "detail": "timeout"}
        except Exception as e:
            return {"status": "unhealthy", "detail": str(e)}

    # --- Redis ---
    async def check_redis(self) -> Dict:
        """Verifica que Redis responda a PING."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(REDIS_HOST, REDIS_PORT), timeout=3
            )
            writer.write(b"PING\r\n")
            await writer.drain()
            data = await asyncio.wait_for(reader.read(64), timeout=3)
            writer.close()
            await writer.wait_closed()
            if b"PONG" in data:
                return {"status": "healthy", "detail": "pong"}
            return {"status": "unhealthy", "detail": "no_pong"}
        except Exception as e:
            return {"status": "unhealthy", "detail": str(e)}

    # --- DB Primary (via MaxScale) ---
    async def check_db_primary(self) -> Dict:
        """Consulta MaxScale para saber si la DB local es Master."""
        global last_primary_server
        
        try:
            url = f"{MAXSCALE_URL}/v1/servers/{LOCAL_DB_SERVER}"
            auth = aiohttp.BasicAuth(MAXSCALE_USER, MAXSCALE_PASS)
            async with self.session.get(url, auth=auth) as resp:
                if resp.status != 200:
                    return {"status": "unhealthy", "detail": f"maxscale_http_{resp.status}"}
                data = await resp.json()
                state = data.get("data", {}).get("attributes", {}).get("state", "")
                
                # Detectar quién es actualmente el primary en el cluster
                current_primary = None
                local_is_master = "Master" in state and "Running" in state
                
                try:
                    servers_url = f"{MAXSCALE_URL}/v1/servers"
                    async with self.session.get(servers_url, auth=auth) as servers_resp:
                        if servers_resp.status == 200:
                            servers_data = await servers_resp.json()
                            for server in servers_data.get("data", []):
                                server_state = server.get("attributes", {}).get("state", "")
                                if "Master" in server_state and "Running" in server_state:
                                    current_primary = server.get("id")
                                    break
                except Exception:
                    # Si falla la consulta general, usar solo el estado local
                    if local_is_master:
                        current_primary = LOCAL_DB_SERVER
                
                # LÓGICA DE RESET INTELIGENTE:
                # Si tenemos contadores de fallo acumulados para db_primary,
                # pero el servidor local ahora ES el primary, significa que
                # hubo un failover y los contadores son obsoletos.
                current_failure_count = failure_counters.get("db_primary", 0)
                if current_failure_count > 0 and local_is_master:
                    logger.info(f"🔄 RESET AUTOMÁTICO: {LOCAL_DB_SERVER} ahora es primary pero tenía {current_failure_count} fallos acumulados")
                    logger.info(f"🔄 Esto indica un failover exitoso → reseteando contadores")
                    failure_counters["db_primary"] = 0
                
                # También detectar cambios explícitos de primary (para logging)
                if last_primary_server is not None and current_primary != last_primary_server:
                    logger.info(f"🔄 DB primary cambió: {last_primary_server} → {current_primary}")
                
                last_primary_server = current_primary
                
                if local_is_master:
                    return {"status": "healthy", "detail": f"state={state}"}
                return {"status": "unhealthy", "detail": f"state={state}"}
        except Exception as e:
            return {"status": "unhealthy", "detail": str(e)}

    # --- Custom HTTP check (genérico) ---
    async def check_custom(self, name: str, url: str) -> Dict:
        """Check genérico: HTTP GET, espera 200."""
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return {"status": "healthy", "detail": "http_200"}
                return {"status": "unhealthy", "detail": f"http_{resp.status}"}
        except Exception as e:
            return {"status": "unhealthy", "detail": str(e)}

    async def run_check(self, name: str) -> Dict:
        """Ejecuta un check por nombre. Retorna resultado estandarizado."""
        # Built-in checks
        if name == "airflow":
            return await self.check_airflow()
        elif name == "redis":
            return await self.check_redis()
        elif name == "db_primary":
            return await self.check_db_primary()
        # Custom checks
        elif name in self.custom_checks:
            return await self.check_custom(name, self.custom_checks[name])
        else:
            return {"status": "unknown", "detail": f"check '{name}' not implemented"}


# =============================================================================
# EVALUACIÓN CON HYSTERESIS
# =============================================================================

def update_with_hysteresis(check_name: str, result: Dict) -> Dict:
    """
    Aplica hysteresis al resultado de un check.

    No cambiamos el estado reportado hasta que se acumulen N fallos
    o N éxitos consecutivos. Esto evita flapping.

    Retorna el resultado enriquecido con:
      - effective_status: el estado después de aplicar hysteresis
      - failure_count: fallos consecutivos actuales
    """
    if check_name not in failure_counters:
        failure_counters[check_name] = 0

    if result["status"] == "healthy":
        failure_counters[check_name] = max(0, failure_counters[check_name] - 1)
    else:
        failure_counters[check_name] += 1

    count = failure_counters[check_name]

    # Determinar estado efectivo con hysteresis
    if count == 0:
        effective = "healthy"
    elif count >= FAILURE_THRESHOLD:
        effective = "unhealthy"
    else:
        effective = "degraded"  # en período de gracia

    return {
        **result,
        "effective_status": effective,
        "failure_count": count,
        "is_critical": check_name in CRITICAL_CHECKS,
    }


# =============================================================================
# LOOP PRINCIPAL
# =============================================================================

async def check_loop(checker: HealthChecks):
    """Ejecuta todos los checks habilitados periódicamente."""
    logger.info(f"Checks habilitados: {ENABLED_CHECKS}")
    logger.info(f"Checks críticos:    {CRITICAL_CHECKS}")
    logger.info(f"Thresholds v2.0:    FAILURE={FAILURE_THRESHOLD}, RECOVERY={RECOVERY_THRESHOLD}")
    if checker.custom_checks:
        logger.info(f"Custom checks:      {list(checker.custom_checks.keys())}")

    while True:
        try:
            # Ejecutar todos los checks en paralelo
            tasks = {name: checker.run_check(name) for name in ENABLED_CHECKS}
            results = {}
            for name, coro in tasks.items():
                results[name] = await coro

            # Aplicar hysteresis y guardar
            for name, result in results.items():
                check_results[name] = update_with_hysteresis(name, result)

            # Evaluar estado consolidado
            all_healthy = all(
                r.get("effective_status") == "healthy"
                for r in check_results.values()
            )
            critical_healthy = all(
                r.get("effective_status") == "healthy"
                for name, r in check_results.items()
                if name in CRITICAL_CHECKS
            )
            # needs_failover: algún check CRÍTICO está unhealthy (no degraded, sino confirmado)
            needs_failover = any(
                r.get("effective_status") == "unhealthy"
                for name, r in check_results.items()
                if name in CRITICAL_CHECKS
            )

            region_status["healthy"] = all_healthy
            region_status["critical_healthy"] = critical_healthy
            region_status["needs_failover"] = needs_failover
            region_status["last_check"] = datetime.now().isoformat()

            # Log
            status_str = " | ".join(
                f"{name}={r.get('effective_status', '?')}"
                f"{'*' if name in CRITICAL_CHECKS else ''}"
                for name, r in check_results.items()
            )
            logger.info(f"[{REGION_NAME}] {status_str} | failover_needed={needs_failover}")

        except Exception as e:
            logger.error(f"Error en check loop: {e}", exc_info=True)

        await asyncio.sleep(CHECK_INTERVAL)


# =============================================================================
# ENDPOINTS HTTP
# =============================================================================

async def handle_health(request):
    """
    GET /health — Estado detallado de todos los checks.
    Siempre retorna 200. Para monitoreo y debugging.
    """
    return web.json_response({
        "region": REGION_NAME,
        "timestamp": datetime.now().isoformat(),
        "status": region_status,
        "checks": check_results,
        "config": {
            "enabled_checks": ENABLED_CHECKS,
            "critical_checks": CRITICAL_CHECKS,
            "check_interval": CHECK_INTERVAL,
            "failure_threshold": FAILURE_THRESHOLD,
            "recovery_threshold": RECOVERY_THRESHOLD,
        }
    })


async def handle_region_health(request):
    """
    GET /region-health — Para HAProxy.
    200 si todos los checks críticos están healthy. 503 si no.
    """
    if region_status.get("critical_healthy"):
        return web.json_response({
            "region": REGION_NAME,
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
        })
    else:
        failed = [
            name for name, r in check_results.items()
            if name in CRITICAL_CHECKS and r.get("effective_status") != "healthy"
        ]
        return web.json_response({
            "region": REGION_NAME,
            "status": "unhealthy",
            "failed_critical_checks": failed,
            "timestamp": datetime.now().isoformat(),
        }, status=503)


async def handle_ready(request):
    """
    GET /ready — Para el site-controller.

    Retorna el estado completo incluyendo el flag needs_failover,
    que el site-controller usa para decidir si forzar un switchover de DB.

    Ejemplo:
    {
      "region": "hornos",
      "critical_healthy": false,
      "needs_failover": true,
      "checks": {
        "airflow": {"effective_status": "unhealthy", "is_critical": true, ...},
        "db_primary": {"effective_status": "healthy", "is_critical": true, ...},
        "redis": {"effective_status": "healthy", "is_critical": false, ...}
      }
    }
    """
    return web.json_response({
        "region": REGION_NAME,
        "timestamp": datetime.now().isoformat(),
        "critical_healthy": region_status.get("critical_healthy", False),
        "needs_failover": region_status.get("needs_failover", False),
        "checks": check_results,
    })


# =============================================================================
# MAIN
# =============================================================================

async def main():
    checker = HealthChecks()
    await checker.start()

    loop_task = asyncio.create_task(check_loop(checker))

    app = web.Application()
    app.router.add_get('/health', handle_health)
    app.router.add_get('/region-health', handle_region_health)
    app.router.add_get('/ready', handle_ready)

    runner = aiohttp.web_runner.AppRunner(app)
    await runner.setup()
    site = aiohttp.web_runner.TCPSite(runner, '0.0.0.0', LISTEN_PORT)
    await site.start()

    logger.info(f"Healthcheck service v2.0 escuchando en :{LISTEN_PORT}")
    logger.info("  GET /health        → Estado detallado (monitoreo)")
    logger.info("  GET /region-health → Para HAProxy (200/503)")
    logger.info("  GET /ready         → Para site-controller (incluye needs_failover)")

    try:
        await loop_task
    except KeyboardInterrupt:
        pass
    finally:
        await checker.stop()
        await runner.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
