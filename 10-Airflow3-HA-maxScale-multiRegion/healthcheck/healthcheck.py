#!/usr/bin/env python3
"""
Health Check Microservice for Airflow Multi-Site HA
Evaluates Airflow health status and provides simple endpoints for HAProxy/GSLB
Configurable per region via environment variables
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import aiohttp
from aiohttp import web
import aiohttp.web_runner

# Configuration from environment variables
REGION_NAME = os.getenv('REGION_NAME', 'unknown')
AIRFLOW_URL = os.getenv('AIRFLOW_URL', 'http://localhost:8080')
HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', '30'))  # seconds
HEALTH_CHECK_TIMEOUT = int(os.getenv('HEALTH_CHECK_TIMEOUT', '10'))   # seconds
FAILURE_THRESHOLD = int(os.getenv('FAILURE_THRESHOLD', '3'))       # consecutive failures
RECOVERY_THRESHOLD = int(os.getenv('RECOVERY_THRESHOLD', '2'))      # consecutive successes
LISTEN_PORT = int(os.getenv('LISTEN_PORT', '8000'))

# Global state
region_health = {}
failure_count = 0

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HealthChecker:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Initialize HTTP session"""
        timeout = aiohttp.ClientTimeout(total=HEALTH_CHECK_TIMEOUT)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info(f"Health checker started for region: {REGION_NAME}")
        logger.info(f"Monitoring Airflow at: {AIRFLOW_URL}")
        
    async def stop(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()
            
    async def check_airflow_health(self) -> Dict:
        """Check health of the configured Airflow instance"""
        try:
            url = f"{AIRFLOW_URL}/api/v2/monitor/health"
            async with self.session.get(url) as response:
                if response.status == 200:
                    health_data = await response.json()
                    return self.evaluate_health(health_data)
                else:
                    logger.warning(f"Region {REGION_NAME}: HTTP {response.status}")
                    return {"status": "unhealthy", "reason": f"HTTP {response.status}"}
                    
        except asyncio.TimeoutError:
            logger.warning(f"Region {REGION_NAME}: Timeout")
            return {"status": "unhealthy", "reason": "timeout"}
        except Exception as e:
            logger.warning(f"Region {REGION_NAME}: {str(e)}")
            return {"status": "unhealthy", "reason": str(e)}
            
    def evaluate_health(self, health_data: Dict) -> Dict:
        """Evaluate Airflow health data according to business rules"""
        try:
            # Critical components that must be healthy
            metadatabase = health_data.get("metadatabase", {}).get("status")
            scheduler = health_data.get("scheduler", {}).get("status") 
            dag_processor = health_data.get("dag_processor", {}).get("status")
            
            # Check critical components
            if metadatabase != "healthy":
                return {"status": "unhealthy", "reason": "database_unhealthy"}
                
            if scheduler != "healthy":
                return {"status": "unhealthy", "reason": "scheduler_unhealthy"}
                
            if dag_processor != "healthy":
                return {"status": "unhealthy", "reason": "dag_processor_unhealthy"}
                
            # Check scheduler heartbeat (should be recent)
            scheduler_heartbeat = health_data.get("scheduler", {}).get("latest_scheduler_heartbeat")
            if scheduler_heartbeat:
                try:
                    heartbeat_time = datetime.fromisoformat(scheduler_heartbeat.replace('Z', '+00:00'))
                    if datetime.now(heartbeat_time.tzinfo) - heartbeat_time > timedelta(minutes=2):
                        return {"status": "unhealthy", "reason": "scheduler_heartbeat_stale"}
                except Exception:
                    pass  # If we can't parse heartbeat, continue with other checks
                    
            return {"status": "healthy", "reason": "all_components_healthy"}
            
        except Exception as e:
            logger.error(f"Error evaluating health for {REGION_NAME}: {e}")
            return {"status": "unhealthy", "reason": "evaluation_error"}
            
    async def update_region_health(self, health_result: Dict):
        """Update region health with failure counting and hysteresis"""
        global failure_count
        current_status = health_result["status"]
        
        if current_status == "healthy":
            failure_count = max(0, failure_count - 1)
            
            # Mark as healthy if we've had enough consecutive successes
            if failure_count == 0:
                region_health[REGION_NAME] = {
                    "status": "healthy",
                    "reason": health_result["reason"],
                    "last_check": datetime.now().isoformat(),
                    "failure_count": 0,
                    "airflow_url": AIRFLOW_URL
                }
        else:
            failure_count += 1
            
            # Mark as unhealthy if we've exceeded failure threshold
            if failure_count >= FAILURE_THRESHOLD:
                region_health[REGION_NAME] = {
                    "status": "unhealthy", 
                    "reason": health_result["reason"],
                    "last_check": datetime.now().isoformat(),
                    "failure_count": failure_count,
                    "airflow_url": AIRFLOW_URL
                }
            else:
                # Still in grace period, keep previous status if exists
                if REGION_NAME not in region_health:
                    region_health[REGION_NAME] = {
                        "status": "degraded",
                        "reason": f"failing_{failure_count}_of_{FAILURE_THRESHOLD}",
                        "last_check": datetime.now().isoformat(),
                        "failure_count": failure_count,
                        "airflow_url": AIRFLOW_URL
                    }
                    
    async def health_check_loop(self):
        """Main health check loop"""
        logger.info(f"Starting health check loop for region: {REGION_NAME}")
        
        while True:
            try:
                health_result = await self.check_airflow_health()
                await self.update_region_health(health_result)
                
                logger.info(f"Region {REGION_NAME}: {health_result['status']} - {health_result['reason']}")
                    
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)  # Short sleep on error


# HTTP API endpoints
async def health_status(request):
    """Return detailed health status of this region"""
    return web.json_response({
        "region": REGION_NAME,
        "timestamp": datetime.now().isoformat(),
        "health": region_health.get(REGION_NAME, {"status": "unknown"}),
        "config": {
            "airflow_url": AIRFLOW_URL,
            "check_interval": HEALTH_CHECK_INTERVAL,
            "failure_threshold": FAILURE_THRESHOLD,
            "recovery_threshold": RECOVERY_THRESHOLD
        }
    })

async def region_health_endpoint(request):
    """HAProxy-friendly endpoint - returns 200 if region is healthy"""
    region_status = region_health.get(REGION_NAME, {"status": "unknown"})
    
    if region_status.get("status") == "healthy":
        return web.json_response({
            "region": REGION_NAME,
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        })
    else:
        return web.json_response({
            "region": REGION_NAME,
            "status": region_status.get("status", "unknown"),
            "reason": region_status.get("reason", "no_data"),
            "timestamp": datetime.now().isoformat()
        }, status=503)

async def init_app():
    """Initialize the web application"""
    app = web.Application()
    
    # Routes
    app.router.add_get('/health', health_status)
    app.router.add_get('/region-health', region_health_endpoint)  # For HAProxy
    
    return app

async def main():
    """Main application entry point"""
    # Initialize health checker
    health_checker = HealthChecker()
    await health_checker.start()
    
    # Start health check loop
    health_check_task = asyncio.create_task(health_checker.health_check_loop())
    
    # Initialize web app
    app = await init_app()
    
    # Start web server
    runner = aiohttp.web_runner.AppRunner(app)
    await runner.setup()
    
    site = aiohttp.web_runner.TCPSite(runner, '0.0.0.0', LISTEN_PORT)
    await site.start()
    
    logger.info(f"Health check service started for region: {REGION_NAME}")
    logger.info(f"Listening on port: {LISTEN_PORT}")
    logger.info("Endpoints:")
    logger.info("  GET /health - Detailed health status")
    logger.info("  GET /region-health - HAProxy-friendly endpoint")
    
    try:
        # Keep running
        await health_check_task
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await health_checker.stop()
        await runner.cleanup()

if __name__ == '__main__':
    asyncio.run(main())