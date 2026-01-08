import asyncio
from datetime import timedelta
from temporalio import workflow
from models import NetworkDeploymentRequest, DeploymentResult

@workflow.defn
class NetworkDeploymentWithConnectivity:
    
    def __init__(self) -> None:
        self._continue_deployment = False
    
    @workflow.signal
    def enter(self) -> None:
        """Signal para continuar con el despliegue desde la web UI"""
        self._continue_deployment = True
    
    @workflow.run
    async def run(self, request: NetworkDeploymentRequest) -> DeploymentResult:
        """
        Workflow completo que demuestra conectividad cliente-servidor:
        1. Test inicial (sin conectividad esperada)
        2. Despliegue del router via Ansible (PING OK, HTTP BLOQUEADO)
        3. PAUSA - Espera signal desde Temporal Web UI
        4. Configuración via Airflow (habilita HTTP)
        5. Test final (conectividad completa)
        6. Reporte de resultados
        """
        
        try:
            # Step 1: Test inicial de conectividad (debe fallar)
            initial_test = await workflow.execute_activity(
                "test_client_server_connectivity",
                "initial_test",
                start_to_close_timeout=timedelta(minutes=5)
            )
            
            # Step 2: Provisionar router via Ansible Runner
            infra_result = await workflow.execute_activity(
                "provision_router_via_ansible_runner",
                request,
                start_to_close_timeout=timedelta(minutes=10)
            )
            
            # Step 3: PAUSA - Esperar signal desde Temporal Web UI
            workflow.logger.info("🔄 ROUTER DESPLEGADO - PING funciona, HTTP bloqueado")
            workflow.logger.info("📋 VERIFICACIÓN MANUAL:")
            workflow.logger.info("   docker exec test-client ping -c 1 192.168.200.10  # ✅ Debe funcionar")
            workflow.logger.info("   docker exec test-client wget -q -O - http://192.168.200.10  # ❌ Debe fallar")
            workflow.logger.info("🌐 Para continuar: Envía signal 'enter' desde Temporal Web UI")
            
            # Esperar hasta 30 minutos por el signal
            await workflow.wait_condition(
                lambda: self._continue_deployment,
                timeout=timedelta(minutes=30)
            )
            
            workflow.logger.info("✅ Signal recibido - Continuando con Airflow...")
            
            # Step 4: Configurar firewall via Airflow (habilitar HTTP)
            software_result = await workflow.execute_activity(
                "deploy_router_software",
                request,
                start_to_close_timeout=timedelta(minutes=15)
            )
            
            # Step 5: Test final de conectividad (debe funcionar)
            final_test = await workflow.execute_activity(
                "test_client_server_connectivity",
                "final_test",
                start_to_close_timeout=timedelta(minutes=5)
            )
            
            # Step 6: Generar reporte final
            report_data = {
                "request": {
                    "router_id": request.router_id,
                    "router_ip": request.router_ip,
                    "software_version": request.software_version
                },
                "initial_test": initial_test,
                "final_test": final_test
            }
            
            deployment_report = await workflow.execute_activity(
                "generate_deployment_report",
                report_data,
                start_to_close_timeout=timedelta(minutes=2)
            )
            
            return deployment_report
            
        except Exception as e:
            # Cleanup en caso de fallo
            await workflow.execute_activity(
                "cleanup_failed_deployment",
                request,
                start_to_close_timeout=timedelta(minutes=5)
            )
            raise