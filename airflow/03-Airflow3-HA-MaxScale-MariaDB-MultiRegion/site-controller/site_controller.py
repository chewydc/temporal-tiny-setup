#!/usr/bin/env python3
"""
==============================================================================
 SITE CONTROLLER — Actuador para Airflow Active/Passive HA
==============================================================================

 Microservicio STATEFUL que consume el healthcheck y toma acciones:

 1. SEGUIR a la DB: si la DB local es primary → scheduler ON
 2. FORZAR FAILOVER: si un check crítico falla (ej: Airflow cae) pero la DB
    sigue local → forzar switchover de MaxScale para que la otra región
    tome el control completo.

 SEPARACIÓN DE RESPONSABILIDADES:
 ────────────────────────────────
   Healthcheck (otro servicio)  →  OBSERVA y REPORTA
   Site Controller (este)       →  DECIDE y ACTÚA

 El site-controller NO ejecuta checks directamente.
 Consume GET /ready del healthcheck, que retorna:
   {
     "critical_healthy": true/false,
     "needs_failover": true/false,
     "checks": { ... }
   }

 LÓGICA DE DECISIÓN:
 ───────────────────
   Caso 1: DB primary local + critical checks OK
     → ACTIVE: scheduler ON, HAProxy 200

   Caso 2: DB primary local + critical check FALLA (ej: Airflow muerto)
     → FORZAR SWITCHOVER: mover DB primary a la otra región via MaxScale
     → Esto causa que el site-controller de la otra región se promueva

   Caso 3: DB NO es primary local
     → PASSIVE: scheduler OFF, HAProxy 503

 ¿POR QUÉ FORZAR SWITCHOVER?
 ────────────────────────────
 Si Airflow cae en la región activa pero la DB sigue ahí, la otra región
 nunca se va a promover (su DB es replica). Es un deadlock.
 La única forma de resolverlo automáticamente es mover la DB.

 CONFIGURACIÓN:
 ──────────────
 Todo via variables de entorno (compatible con ConfigMap en OpenShift):

   HEALTHCHECK_URL     → URL del healthcheck local (GET /ready)
   MAXSCALE_URL        → URL de MaxScale para forzar switchover
   SCHEDULER_CONTAINER → Container a pausar/despausar
   FORCE_SWITCHOVER    → true/false: habilitar switchover forzado
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

# --- Conexión al healthcheck local ---
HEALTHCHECK_URL = os.getenv('HEALTHCHECK_URL', 'http://healthcheck-hornos:8000')

# --- MaxScale (para consultar DB primary y forzar switchover) ---
MAXSCALE_URL = os.getenv('MAXSCALE_URL', 'http://maxscale-hornos:8989')
MAXSCALE_USER = os.getenv('MAXSCALE_USER', 'admin')
MAXSCALE_PASS = os.getenv('MAXSCALE_PASS', 'mariadb')
LOCAL_DB_SERVER = os.getenv('LOCAL_DB_SERVER', 'HORNOS')
MAXSCALE_MONITOR = os.getenv('MAXSCALE_MONITOR', 'Replication-Monitor')

# --- Containers a controlar ---
SCHEDULER_CONTAINER = os.getenv('SCHEDULER_CONTAINER', 'airflow-scheduler-hornos')
DAG_PROCESSOR_CONTAINER = os.getenv('DAG_PROCESSOR_CONTAINER', 'airflow-dag-processor-hornos')

# --- Switchover forzado ---
# Si está habilitado, cuando un check crítico falla pero la DB sigue local,
# el controller fuerza un switchover de MaxScale para mover la DB a la otra región.
# Deshabilitarlo para entornos donde se prefiere intervención manual.
FORCE_SWITCHOVER = os.getenv('FORCE_SWITCHOVER', 'true').lower() == 'true'

# --- Threshold para forzar switchover ---
# Cuántos checks consecutivos con needs_failover=true antes de forzar switchover.
# Debe ser >= FAILURE_THRESHOLD del healthcheck para no actuar antes de que
# el healthcheck confirme el fallo.
SWITCHOVER_THRESHOLD = int(os.getenv('SWITCHOVER_THRESHOLD', '5'))

# --- Hysteresis para promote/demote ---
FAILOVER_THRESHOLD = int(os.getenv('FAILOVER_THRESHOLD', '3'))
RECOVERY_THRESHOLD = int(os.getenv('RECOVERY_THRESHOLD', '2'))


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
    "db_is_primary": False,
    "critical_healthy": False,
    "needs_failover": False,
    "scheduler_running": False,

    "consecutive_primary": 0,
    "consecutive_not_primary": 0,
    "consecutive_failover_needed": 0,

    "last_check": None,
    "last_transition": None,
    "transition_reason": None,
    "last_switchover_forced": None,
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
        logger.info(f"  Healthcheck URL:   {HEALTHCHECK_URL}")
        logger.info(f"  MaxScale URL:      {MAXSCALE_URL}")
        logger.info(f"  Local DB Server:   {LOCAL_DB_SERVER}")
        logger.info(f"  Scheduler:         {SCHEDULER_CONTAINER}")
        logger.info(f"  Force Switchover:  {'✅ habilitado' if FORCE_SWITCHOVER else '⛔ deshabilitado'}")
        logger.info(f"  Switchover After:  {SWITCHOVER_THRESHOLD} checks")
        logger.info(f"  Docker Socket:     {'✅' if self._docker_available else '⚠️ dry-run'}")
        logger.info("=" * 70)

    async def stop(self):
        if self.session:
            await self.session.close()

    # =========================================================================
    # CONSULTAS
    # =========================================================================

    async def get_healthcheck_status(self) -> dict:
        """Consulta GET /ready del healthcheck local."""
        try:
            url = f"{HEALTHCHECK_URL}/ready"
            async with self.session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                # El healthcheck retorna 200 siempre en /ready
                return {"critical_healthy": False, "needs_failover": True}
        except Exception as e:
            logger.warning(f"No se pudo consultar healthcheck: {e}")
            return {"critical_healthy": False, "needs_failover": False, "error": str(e)}

    async def check_db_is_primary(self) -> bool:
        """Consulta MaxScale directamente para saber si la DB local es primary."""
        try:
            url = f"{MAXSCALE_URL}/v1/servers/{LOCAL_DB_SERVER}"
            auth = aiohttp.BasicAuth(MAXSCALE_USER, MAXSCALE_PASS)
            async with self.session.get(url, auth=auth) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    state = data.get("data", {}).get("attributes", {}).get("state", "")
                    return "Master" in state and "Running" in state
                return False
        except Exception:
            return False

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
    # ACCIÓN: FORZAR SWITCHOVER DE DB
    # =========================================================================

    async def force_db_switchover(self) -> bool:
        """
        Fuerza un switchover en MaxScale para mover el primary a otra región.

        MaxScale API:
          POST /v1/maxscale/modules/mariadbmon/{monitor}/switchover

        Esto promueve la réplica con mejor posición GTID a primary.
        El primary actual pasa a ser réplica.

        IMPORTANTE: Esto es una operación PESADA. Solo se ejecuta cuando:
        1. FORCE_SWITCHOVER está habilitado
        2. La DB es primary local
        3. Un check crítico falló (needs_failover=true)
        4. Se superó SWITCHOVER_THRESHOLD checks consecutivos

        Retorna True si el switchover fue exitoso.
        """
        logger.info("=" * 70)
        logger.info("  ⚠️  FORZANDO SWITCHOVER DE DB VIA MAXSCALE")
        logger.info(f"  Razón: check crítico fallando con DB primary local")
        logger.info(f"  Monitor: {MAXSCALE_MONITOR}")
        logger.info("=" * 70)

        try:
            url = f"{MAXSCALE_URL}/v1/maxscale/modules/mariadbmon/{MAXSCALE_MONITOR}/switchover"
            auth = aiohttp.BasicAuth(MAXSCALE_USER, MAXSCALE_PASS)

            async with self.session.post(url, auth=auth) as resp:
                if resp.status == 204:
                    logger.info("✅ Switchover ejecutado exitosamente")
                    site_state["last_switchover_forced"] = datetime.now().isoformat()
                    return True
                else:
                    body = await resp.text()
                    logger.error(f"❌ Switchover falló: HTTP {resp.status} — {body}")
                    return False

        except Exception as e:
            logger.error(f"❌ Error al forzar switchover: {e}")
            return False

    # =========================================================================
    # LOOP PRINCIPAL
    # =========================================================================

    async def control_loop(self):
        """
        Loop principal:

        1. Consultar healthcheck local (GET /ready)
        2. Consultar MaxScale (¿DB es primary?)
        3. Decidir:
           a) DB primary + critical OK → ACTIVE (scheduler ON)
           b) DB primary + critical FAIL → FORZAR SWITCHOVER
           c) DB no primary → PASSIVE (scheduler OFF)
        4. Safety checks
        """
        logger.info(f"Iniciando control loop (intervalo={CHECK_INTERVAL}s)")

        while True:
            try:
                # ─── 1. CONSULTAR ───
                hc_status, db_primary = await asyncio.gather(
                    self.get_healthcheck_status(),
                    self.check_db_is_primary(),
                )

                critical_healthy = hc_status.get("critical_healthy", False)
                needs_failover = hc_status.get("needs_failover", False)

                site_state["db_is_primary"] = db_primary
                site_state["critical_healthy"] = critical_healthy
                site_state["needs_failover"] = needs_failover
                site_state["last_check"] = datetime.now().isoformat()

                # ─── 2. CONTADORES ───
                if db_primary:
                    site_state["consecutive_primary"] += 1
                    site_state["consecutive_not_primary"] = 0
                else:
                    site_state["consecutive_not_primary"] += 1
                    site_state["consecutive_primary"] = 0

                if needs_failover and db_primary:
                    site_state["consecutive_failover_needed"] += 1
                else:
                    site_state["consecutive_failover_needed"] = 0

                current_role = site_state["role"]

                # ─── 3. DECIDIR ───

                # Caso A: DB primary + todo OK → PROMOTE a active
                if current_role == "passive" and db_primary and critical_healthy:
                    if site_state["consecutive_primary"] >= RECOVERY_THRESHOLD:
                        logger.info("=" * 70)
                        logger.info(f"  ✅ PROMOTE: {REGION_NAME} → ACTIVE")
                        logger.info("=" * 70)
                        await self.start_scheduler()
                        site_state["role"] = "active"
                        site_state["last_transition"] = datetime.now().isoformat()
                        site_state["transition_reason"] = "db_primary_local_and_healthy"

                # Caso B: DB primary + check crítico falla → FORZAR SWITCHOVER
                elif db_primary and needs_failover:
                    if site_state["consecutive_failover_needed"] >= SWITCHOVER_THRESHOLD:
                        if FORCE_SWITCHOVER:
                            logger.info("=" * 70)
                            logger.info(f"  ⚠️  FORCED SWITCHOVER: {REGION_NAME}")
                            logger.info(f"  DB es primary local pero checks críticos fallan")
                            logger.info(f"  Forzando switchover para mover DB a otra región")
                            logger.info("=" * 70)

                            # Primero parar scheduler local
                            await self.stop_scheduler()
                            site_state["role"] = "passive"
                            site_state["last_transition"] = datetime.now().isoformat()
                            site_state["transition_reason"] = "forced_switchover_critical_failure"

                            # Forzar switchover de DB
                            await self.force_db_switchover()

                            # Reset counter para no re-ejecutar inmediatamente
                            site_state["consecutive_failover_needed"] = 0
                        else:
                            logger.warning(
                                f"Switchover necesario pero FORCE_SWITCHOVER=false. "
                                f"Intervención manual requerida."
                            )

                # Caso C: DB no es primary → DEMOTE a passive
                elif current_role == "active" and not db_primary:
                    if site_state["consecutive_not_primary"] >= FAILOVER_THRESHOLD:
                        logger.info("=" * 70)
                        logger.info(f"  ⛔ DEMOTE: {REGION_NAME} → PASSIVE")
                        logger.info("=" * 70)
                        await self.stop_scheduler()
                        site_state["role"] = "passive"
                        site_state["last_transition"] = datetime.now().isoformat()
                        site_state["transition_reason"] = "db_primary_moved"

                # ─── 4. SAFETY CHECKS ───
                if site_state["role"] == "active" and not site_state["scheduler_running"]:
                    paused = await self.is_container_paused(SCHEDULER_CONTAINER)
                    if paused is True:
                        logger.warning("[SAFETY] Active pero scheduler pausado → corrigiendo")
                        await self.start_scheduler()

                if site_state["role"] == "passive" and site_state["scheduler_running"]:
                    logger.warning("[SAFETY] Passive pero scheduler corriendo → corrigiendo")
                    await self.stop_scheduler()

                # ─── LOG ───
                logger.info(
                    f"[{REGION_NAME}] "
                    f"role={site_state['role']} | "
                    f"db={db_primary} | "
                    f"critical={critical_healthy} | "
                    f"failover_needed={needs_failover} | "
                    f"scheduler={'ON' if site_state['scheduler_running'] else 'OFF'} | "
                    f"sw_count={site_state['consecutive_failover_needed']}"
                )

            except Exception as e:
                logger.error(f"Error en control loop: {e}", exc_info=True)

            await asyncio.sleep(CHECK_INTERVAL)


# =============================================================================
# ENDPOINTS HTTP
# =============================================================================

async def handle_health(request):
    """GET /health — Estado detallado del controller."""
    return web.json_response({
        "region": REGION_NAME,
        "timestamp": datetime.now().isoformat(),
        "state": site_state,
        "config": {
            "force_switchover": FORCE_SWITCHOVER,
            "switchover_threshold": SWITCHOVER_THRESHOLD,
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
    """GET /role — Solo el rol."""
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
