#!/usr/bin/env python3
"""
==============================================================================
 HEALTHCHECK SERVICE — Sensor de salud para Airflow HA (Caso 04)
==============================================================================

 Microservicio STATELESS que evalúa la salud de los componentes de una región
 y expone el resultado via HTTP.

 NO toma acciones. Solo OBSERVA y REPORTA.

 CAMBIO CLAVE vs Caso 03:
 ─────────────────────────
   Caso 03: check "db_primary" → ¿mi DB local es Master?
   Caso 04: check "maxscale_healthy" → ¿mi MaxScale responde Y ve un Master?

   Esto permite que la DB esté cruzada (Master en otra región) sin que
   se dispare un failover. Lo importante es que MaxScale pueda rutear.

 ANTI SPLIT-BRAIN:
 ─────────────────
   MaxScale con cooperative_monitoring_locks=majority_of_running garantiza
   que solo el MaxScale con mayoría de nodos visibles puede operar.
   Si se corta la red, el MaxScale aislado pierde el lock y no ve Master.
   → El site-controller de esa región se pone PASSIVE automáticamente.

 CHECKS DISPONIBLES:
 ───────────────────
   airflow          → Airflow API Server responde en /api/v2/monitor/health
   redis            → Redis responde a PING
   maxscale_healthy → MaxScale responde Y ve al menos un Master Running

 ENDPOINTS:
 ──────────
   GET /health         → Estado detallado de todos los checks
   GET /region-health  → Para HAProxy (200 si critical checks OK, 503 si no)
   GET /ready          → Para el site-controller (incluye needs_failover)
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Optional

import aiohttp
from aiohttp import web
import aiohttp.web_runner


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

REGION_NAME = os.getenv('REGION_NAME', 'unknown')
LISTEN_PORT = int(os.getenv('LISTEN_PORT', '8000'))
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '10'))

ENABLED_CHECKS = [c.strip() for c in os.getenv('CHECKS', 'airflow,redis,maxscale_healthy').split(',') if c.strip()]
CRITICAL_CHECKS = [c.strip() for c in os.getenv('CRITICAL_CHECKS', 'airflow,maxscale_healthy').split(',') if c.strip()]

FAILURE_THRESHOLD = int(os.getenv('FAILURE_THRESHOLD', '2'))
RECOVERY_THRESHOLD = int(os.getenv('RECOVERY_THRESHOLD', '1'))

# --- Airflow ---
AIRFLOW_URL = os.getenv('AIRFLOW_URL', 'http://localhost:8080')

# --- Redis ---
REDIS_HOST = os.getenv('REDIS_HOST', 'redis-hornos')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

# --- MaxScale ---
MAXSCALE_URL = os.getenv('MAXSCALE_URL', 'http://maxscale-hornos:8989')
MAXSCALE_USER = os.getenv('MAXSCALE_USER', 'admin')
MAXSCALE_PASS = os.getenv('MAXSCALE_PASS', 'mariadb')

# --- Custom HTTP checks ---
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
failure_counters: Dict[str, int] = {}
region_status = {
    "healthy": False,
    "critical_healthy": False,
    "needs_failover": False,
    "last_check": None,
}


# =============================================================================
# CHECK IMPLEMENTATIONS
# =============================================================================

class HealthChecks:

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
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

    async def check_airflow(self) -> Dict:
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

    async def check_redis(self) -> Dict:
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

    async def check_maxscale_healthy(self) -> Dict:
        """
        Verifica que MaxScale local responda Y vea al menos un Master Running.
        
        Esto es la clave del anti split-brain:
        - Si MaxScale perdió el cooperative lock (red cortada), no verá Master
        - Si MaxScale está caído, no responde
        - En ambos casos → unhealthy → site se pone PASSIVE
        
        NO importa si el Master es local o remoto (DB cruzada OK).
        """
        try:
            auth = aiohttp.BasicAuth(MAXSCALE_USER, MAXSCALE_PASS)
            url = f"{MAXSCALE_URL}/v1/servers"
            async with self.session.get(url, auth=auth) as resp:
                if resp.status != 200:
                    return {"status": "unhealthy", "detail": f"maxscale_http_{resp.status}"}

                data = await resp.json()
                servers = data.get("data", [])

                master_found = False
                master_server = None
                server_states = {}

                for server in servers:
                    name = server.get("id", "unknown")
                    state = server.get("attributes", {}).get("state", "")
                    server_states[name] = state
                    if "Master" in state and "Running" in state:
                        master_found = True
                        master_server = name

                if master_found:
                    return {
                        "status": "healthy",
                        "detail": f"master={master_server}",
                        "master_server": master_server,
                        "server_states": server_states,
                    }
                return {
                    "status": "unhealthy",
                    "detail": "no_master_visible",
                    "server_states": server_states,
                }
        except asyncio.TimeoutError:
            return {"status": "unhealthy", "detail": "maxscale_timeout"}
        except Exception as e:
            return {"status": "unhealthy", "detail": str(e)}

    async def check_custom(self, name: str, url: str) -> Dict:
        try:
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return {"status": "healthy", "detail": "http_200"}
                return {"status": "unhealthy", "detail": f"http_{resp.status}"}
        except Exception as e:
            return {"status": "unhealthy", "detail": str(e)}

    async def run_check(self, name: str) -> Dict:
        if name == "airflow":
            return await self.check_airflow()
        elif name == "redis":
            return await self.check_redis()
        elif name == "maxscale_healthy":
            return await self.check_maxscale_healthy()
        elif name in self.custom_checks:
            return await self.check_custom(name, self.custom_checks[name])
        else:
            return {"status": "unknown", "detail": f"check '{name}' not implemented"}


# =============================================================================
# EVALUACIÓN CON HYSTERESIS
# =============================================================================

def update_with_hysteresis(check_name: str, result: Dict) -> Dict:
    if check_name not in failure_counters:
        failure_counters[check_name] = 0

    if result["status"] == "healthy":
        failure_counters[check_name] = max(0, failure_counters[check_name] - 1)
    else:
        failure_counters[check_name] += 1

    count = failure_counters[check_name]

    if count == 0:
        effective = "healthy"
    elif count >= FAILURE_THRESHOLD:
        effective = "unhealthy"
    else:
        effective = "degraded"

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
    logger.info(f"Checks habilitados: {ENABLED_CHECKS}")
    logger.info(f"Checks críticos:    {CRITICAL_CHECKS}")
    logger.info(f"Thresholds:         FAILURE={FAILURE_THRESHOLD}, RECOVERY={RECOVERY_THRESHOLD}")
    if checker.custom_checks:
        logger.info(f"Custom checks:      {list(checker.custom_checks.keys())}")

    while True:
        try:
            tasks = {name: checker.run_check(name) for name in ENABLED_CHECKS}
            results = {}
            for name, coro in tasks.items():
                results[name] = await coro

            for name, result in results.items():
                check_results[name] = update_with_hysteresis(name, result)

            all_healthy = all(
                r.get("effective_status") == "healthy"
                for r in check_results.values()
            )
            critical_healthy = all(
                r.get("effective_status") == "healthy"
                for name, r in check_results.items()
                if name in CRITICAL_CHECKS
            )
            needs_failover = any(
                r.get("effective_status") == "unhealthy"
                for name, r in check_results.items()
                if name in CRITICAL_CHECKS
            )

            region_status["healthy"] = all_healthy
            region_status["critical_healthy"] = critical_healthy
            region_status["needs_failover"] = needs_failover
            region_status["last_check"] = datetime.now().isoformat()

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

    logger.info(f"Healthcheck service escuchando en :{LISTEN_PORT}")
    logger.info("  GET /health        → Estado detallado (monitoreo)")
    logger.info("  GET /region-health → Para HAProxy (200/503)")
    logger.info("  GET /ready         → Para site-controller (includes needs_failover)")

    try:
        await loop_task
    except KeyboardInterrupt:
        pass
    finally:
        await checker.stop()
        await runner.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
