#!/usr/bin/env python3
"""
==============================================================================
 SITE CONTROLLER — Actuador para Airflow HA (Caso 04: Cross-DB Multi-Region)
==============================================================================

 CAMBIO CLAVE vs Caso 03:
 ─────────────────────────
   Caso 03: "Sigo al DB Master" → si la DB se mueve, el site se mueve
   Caso 04: "Sigo al MaxScale funcional" → la DB puede estar cruzada, no importa

 Ya NO fuerza switchover de DB. MaxScale se encarga solo del ruteo.

 LÓGICA DE DECISIÓN:
 ───────────────────
   Para ser ACTIVE necesito:
     1. Mi MaxScale local responde Y ve un Master (donde sea)
     2. Mi Airflow local está OK
     3. Soy la región preferida, O la región preferida está caída

 ANTI SPLIT-BRAIN:
 ─────────────────
   MaxScale con cooperative_monitoring_locks=majority_of_running garantiza
   que si se corta la red, solo el MaxScale con mayoría opera.
   El MaxScale aislado no ve Master → healthcheck unhealthy → PASSIVE.

 REGIÓN PREFERIDA:
 ─────────────────
   Una región se configura como preferida (PREFERRED_REGION=true).
   Si ambas regiones están sanas, solo la preferida es ACTIVE.
   Si la preferida cae, la otra se promueve.
   Esto evita que ambas se activen simultáneamente.

 CONFIGURACIÓN:
 ──────────────
   HEALTHCHECK_URL      → URL del healthcheck local
   PEER_HEALTHCHECK_URL → URL del healthcheck de la otra región
   PREFERRED_REGION     → true/false: soy la región preferida
   SCHEDULER_CONTAINER  → Container a pausar/despausar
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

import aiohttp
from aiohttp import web
import aiohttp.web_runner


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

REGION_NAME = os.getenv('REGION_NAME', 'unknown')
LISTEN_PORT = int(os.getenv('LISTEN_PORT', '8100'))
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '10'))

# --- Healthcheck local y peer ---
HEALTHCHECK_URL = os.getenv('HEALTHCHECK_URL', 'http://healthcheck-hornos:8000')
PEER_HEALTHCHECK_URL = os.getenv('PEER_HEALTHCHECK_URL', '')

# --- Región preferida ---
PREFERRED_REGION = os.getenv('PREFERRED_REGION', 'false').lower() == 'true'

# --- Containers a controlar ---
SCHEDULER_CONTAINER = os.getenv('SCHEDULER_CONTAINER', 'airflow-scheduler-hornos')
DAG_PROCESSOR_CONTAINER = os.getenv('DAG_PROCESSOR_CONTAINER', 'airflow-dag-processor-hornos')

# --- Hysteresis ---
FAILOVER_THRESHOLD = int(os.getenv('FAILOVER_THRESHOLD', '2'))
RECOVERY_THRESHOLD = int(os.getenv('RECOVERY_THRESHOLD', '1'))


# =============================================================================
# LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [controller-%(name)s] %(message)s'
)
logger = logging.getLogger(REGION_NAME)


# =============================================================================
# ESTADO
# =============================================================================

site_state = {
    "role": "passive",
    "critical_healthy": False,
    "peer_healthy": True,
    "scheduler_running": False,

    "consecutive_should_active": 0,
    "consecutive_should_passive": 0,

    "last_check": None,
    "last_transition": None,
    "transition_reason": None,
}


# =============================================================================
# SITE CONTROLLER
# =============================================================================

class SiteController:

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._docker_available = os.path.exists('/var/run/docker.sock')

    async def start(self):
        timeout = aiohttp.ClientTimeout(total=8)
        self.session = aiohttp.ClientSession(timeout=timeout)

        logger.info("=" * 70)
        logger.info(f"  SITE CONTROLLER — Región: {REGION_NAME}")
        logger.info("=" * 70)
        logger.info(f"  Healthcheck URL:      {HEALTHCHECK_URL}")
        logger.info(f"  Peer Healthcheck URL: {PEER_HEALTHCHECK_URL or 'not configured'}")
        logger.info(f"  Preferred Region:     {'✅ SÍ' if PREFERRED_REGION else '⛔ NO'}")
        logger.info(f"  Scheduler:            {SCHEDULER_CONTAINER}")
        logger.info(f"  Docker Socket:        {'✅' if self._docker_available else '⚠️ dry-run'}")
        logger.info("=" * 70)

    async def stop(self):
        if self.session:
            await self.session.close()

    # =========================================================================
    # CONSULTAS
    # =========================================================================

    async def get_local_health(self) -> dict:
        """Consulta GET /ready del healthcheck local."""
        try:
            url = f"{HEALTHCHECK_URL}/ready"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"critical_healthy": False, "needs_failover": True}
        except Exception as e:
            logger.warning(f"No se pudo consultar healthcheck local: {e}")
            return {"critical_healthy": False, "needs_failover": False, "error": str(e)}

    async def get_peer_health(self) -> dict:
        """
        Consulta el healthcheck de la otra región.
        Si no está configurado o no responde, asumimos que el peer está caído.
        """
        if not PEER_HEALTHCHECK_URL:
            return {"critical_healthy": False, "reachable": False}
        try:
            url = f"{PEER_HEALTHCHECK_URL}/ready"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    data["reachable"] = True
                    return data
                return {"critical_healthy": False, "reachable": True}
        except Exception as e:
            logger.debug(f"Peer healthcheck no disponible: {e}")
            return {"critical_healthy": False, "reachable": False}

    # =========================================================================
    # ACCIONES: SCHEDULER
    # =========================================================================

    async def _docker_api(self, method: str, path: str) -> int:
        if not self._docker_available:
            logger.info(f"[DRY-RUN] {method} {path}")
            return 204
        try:
            conn = aiohttp.UnixConnector(path='/var/run/docker.sock')
            async with aiohttp.ClientSession(connector=conn) as docker:
                async with docker.request(method, f"http://localhost{path}") as resp:
                    if resp.status not in (204, 304):
                        body = await resp.text()
                        logger.warning(f"Docker {method} {path} → {resp.status}: {body}")
                    else:
                        logger.info(f"Docker {method} {path} → {resp.status}")
                    return resp.status
        except Exception as e:
            logger.error(f"Docker API error: {e}")
            return 500

    async def start_scheduler(self):
        logger.info("▶▶▶ ACTIVANDO scheduler + dag-processor")
        await self._docker_api("POST", f"/containers/{SCHEDULER_CONTAINER}/unpause")
        await self._docker_api("POST", f"/containers/{DAG_PROCESSOR_CONTAINER}/unpause")
        site_state["scheduler_running"] = True

    async def stop_scheduler(self):
        logger.info("⏸⏸⏸ DESACTIVANDO scheduler + dag-processor")
        await self._docker_api("POST", f"/containers/{SCHEDULER_CONTAINER}/pause")
        await self._docker_api("POST", f"/containers/{DAG_PROCESSOR_CONTAINER}/pause")
        site_state["scheduler_running"] = False

    async def is_container_paused(self, container: str) -> Optional[bool]:
        if not self._docker_available:
            return None
        try:
            conn = aiohttp.UnixConnector(path='/var/run/docker.sock')
            async with aiohttp.ClientSession(connector=conn) as docker:
                async with docker.get(f"http://localhost/containers/{container}/json") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("State", {}).get("Paused", False)
        except Exception:
            pass
        return None

    # =========================================================================
    # LOOP PRINCIPAL
    # =========================================================================

    async def control_loop(self):
        """
        Loop principal:

        1. Consultar healthcheck local (¿MaxScale OK + Airflow OK?)
        2. Consultar healthcheck peer (¿la otra región está sana?)
        3. Decidir:
           a) Yo sano + soy preferida → ACTIVE
           b) Yo sano + peer caído → ACTIVE (failover)
           c) Yo sano + peer sano + no soy preferida → PASSIVE
           d) Yo no sano → PASSIVE
        """
        logger.info(f"Iniciando control loop (intervalo={CHECK_INTERVAL}s)")

        while True:
            try:
                # ─── 1. CONSULTAR ───
                local_health, peer_health = await asyncio.gather(
                    self.get_local_health(),
                    self.get_peer_health(),
                )

                critical_healthy = local_health.get("critical_healthy", False)
                peer_critical_healthy = peer_health.get("critical_healthy", False)
                peer_reachable = peer_health.get("reachable", False)

                site_state["critical_healthy"] = critical_healthy
                site_state["peer_healthy"] = peer_critical_healthy
                site_state["last_check"] = datetime.now().isoformat()

                # ─── 2. DETERMINAR SI DEBO SER ACTIVE ───
                should_be_active = False

                if critical_healthy:
                    if PREFERRED_REGION:
                        # Soy preferida y estoy sana → ACTIVE (siempre)
                        should_be_active = True
                    elif not peer_critical_healthy:
                        # No soy preferida pero el peer está caído → ACTIVE
                        should_be_active = True
                    # else: no soy preferida y el peer está sano → PASSIVE
                    # (la preferida gana, esto no es "retorno automático"
                    #  sino resolución de quién manda cuando ambas están sanas)

                # ─── 3. CONTADORES CON HYSTERESIS ───
                if should_be_active:
                    site_state["consecutive_should_active"] += 1
                    site_state["consecutive_should_passive"] = 0
                else:
                    site_state["consecutive_should_passive"] += 1
                    site_state["consecutive_should_active"] = 0

                current_role = site_state["role"]

                # ─── 4. TRANSICIONES ───

                # PROMOTE: passive → active
                if current_role == "passive" and should_be_active:
                    if site_state["consecutive_should_active"] >= RECOVERY_THRESHOLD:
                        reason = "preferred_and_healthy" if PREFERRED_REGION else "peer_down_failover"
                        logger.info("=" * 70)
                        logger.info(f"  ✅ PROMOTE: {REGION_NAME} → ACTIVE ({reason})")
                        logger.info("=" * 70)
                        await self.start_scheduler()
                        site_state["role"] = "active"
                        site_state["last_transition"] = datetime.now().isoformat()
                        site_state["transition_reason"] = reason

                # DEMOTE: active → passive
                elif current_role == "active" and not should_be_active:
                    if site_state["consecutive_should_passive"] >= FAILOVER_THRESHOLD:
                        if not critical_healthy:
                            reason = "local_unhealthy"
                        else:
                            reason = "preferred_region_recovered"
                        logger.info("=" * 70)
                        logger.info(f"  ⛔ DEMOTE: {REGION_NAME} → PASSIVE ({reason})")
                        logger.info("=" * 70)
                        await self.stop_scheduler()
                        site_state["role"] = "passive"
                        site_state["last_transition"] = datetime.now().isoformat()
                        site_state["transition_reason"] = reason

                # ─── 5. SAFETY CHECKS (contra estado real del container) ───
                scheduler_paused = await self.is_container_paused(SCHEDULER_CONTAINER)

                if site_state["role"] == "active" and scheduler_paused is True:
                    logger.warning("[SAFETY] Active pero scheduler pausado → corrigiendo")
                    await self.start_scheduler()

                if site_state["role"] == "passive" and scheduler_paused is False:
                    logger.warning("[SAFETY] Passive pero scheduler corriendo → corrigiendo")
                    await self.stop_scheduler()

                # ─── LOG ───
                logger.info(
                    f"[{REGION_NAME}] "
                    f"role={site_state['role']} | "
                    f"healthy={critical_healthy} | "
                    f"peer_healthy={peer_critical_healthy} | "
                    f"peer_reachable={peer_reachable} | "
                    f"preferred={PREFERRED_REGION} | "
                    f"scheduler={'ON' if site_state['scheduler_running'] else 'OFF'}"
                )

            except Exception as e:
                logger.error(f"Error en control loop: {e}", exc_info=True)

            await asyncio.sleep(CHECK_INTERVAL)


# =============================================================================
# ENDPOINTS HTTP
# =============================================================================

async def handle_health(request):
    return web.json_response({
        "region": REGION_NAME,
        "timestamp": datetime.now().isoformat(),
        "state": site_state,
        "config": {
            "preferred_region": PREFERRED_REGION,
            "failover_threshold": FAILOVER_THRESHOLD,
            "recovery_threshold": RECOVERY_THRESHOLD,
        }
    })


async def handle_region_health(request):
    """
    GET /region-health — Para HAProxy.
    200 solo si ACTIVE + critical healthy + scheduler running.
    """
    is_ready = (
        site_state["role"] == "active"
        and site_state["critical_healthy"]
        and site_state["scheduler_running"]
    )

    if is_ready:
        return web.json_response({
            "region": REGION_NAME,
            "role": "active",
            "status": "healthy",
        })
    else:
        return web.json_response({
            "region": REGION_NAME,
            "role": site_state["role"],
            "status": "not_ready",
            "reason": site_state.get("transition_reason", "unknown"),
        }, status=503)


async def handle_role(request):
    return web.json_response({"region": REGION_NAME, "role": site_state["role"]})


# =============================================================================
# MAIN
# =============================================================================

async def main():
    controller = SiteController()
    await controller.start()

    loop_task = asyncio.create_task(controller.control_loop())

    app = web.Application()
    app.router.add_get('/health', handle_health)
    app.router.add_get('/region-health', handle_region_health)
    app.router.add_get('/role', handle_role)

    runner = aiohttp.web_runner.AppRunner(app)
    await runner.setup()
    site = aiohttp.web_runner.TCPSite(runner, '0.0.0.0', LISTEN_PORT)
    await site.start()

    logger.info(f"Site controller escuchando en :{LISTEN_PORT}")
    logger.info("  GET /health        → Estado detallado")
    logger.info("  GET /region-health → Para HAProxy (200/503)")
    logger.info("  GET /role          → Solo el rol")

    try:
        await loop_task
    except KeyboardInterrupt:
        pass
    finally:
        await controller.stop()
        await runner.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
