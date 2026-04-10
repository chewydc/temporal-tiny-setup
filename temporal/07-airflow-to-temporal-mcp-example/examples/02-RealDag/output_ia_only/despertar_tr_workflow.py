"""
Workflow para Despertar TR
Migración del DAG chogar_despertar_tr de Airflow a Temporal
"""
from datetime import timedelta, datetime
from typing import List
import asyncio
import pytz
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from despertar_tr_activities import (
        nombrar_csv_activity,
        obtener_equipos_bigquery_activity,
        verificar_reproceso_mongodb_activity,
        reiniciar_tr_haas_activity,
        verificar_status_haas_activity,
        escribir_log_csv_activity,
        cargar_logs_mongodb_activity,
        cargar_logs_bigquery_activity,
        enviar_email_activity,
        EquipoTR,
        ResultadoEjecucion
    )


@workflow.defn
class DespertarTRWorkflow:
    """
    Workflow que reinicia agentes TR en equipos que no reportan información
    Excluye casos por reproceso y escribe logs en BigQuery y MongoDB
    """

    @workflow.run
    async def run(self, config: dict) -> dict:
        """
        Args:
            config: {
                'path': '/io/cel_chogar/per/confiabilidad/despertar_tr',
                'project_id': 'teco-dev-cdh-e926',
                'dataset_id': 'scripts_tambo',
                'table_id': 'despertar_tr',
                'mongo_uri': 'mongodb://...',
                'mongo_database': 'chogar_prod',
                'mongo_collection': 'logs_despertar_tr',
                'destinatarios_email': ['yairfernandez@teco.com.ar'],
                'max_workers': 10,
                'max_results': 1000
            }
        """
        zona_horaria = pytz.timezone('America/Argentina/Buenos_Aires')
        tiempo = datetime.now(zona_horaria)
        fecha = tiempo.strftime("%Y-%m-%d")
        
        workflow.logger.info(f"Iniciando workflow Despertar TR para fecha {fecha}")
        
        # Configuración de retry para activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=10),
            maximum_attempts=3
        )
        
        # 1. Nombrar archivo CSV
        nombre_archivo = await workflow.execute_activity(
            nombrar_csv_activity,
            args=[config['path'], fecha],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy
        )
        
        # 2. Obtener equipos desde BigQuery
        equipos = await workflow.execute_activity(
            obtener_equipos_bigquery_activity,
            args=[
                config['project_id'],
                config['dataset_id'],
                config['table_id'],
                config.get('max_results', 1000)
            ],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy
        )
        
        workflow.logger.info(f"Obtenidos {len(equipos)} equipos para procesar")
        
        # 3. Procesar equipos en paralelo (con límite de concurrencia)
        max_workers = config.get('max_workers', 10)
        resultados = []
        
        # Dividir en lotes para controlar concurrencia
        for i in range(0, len(equipos), max_workers):
            lote = equipos[i:i+max_workers]
            tareas = [
                self._procesar_equipo(
                    equipo,
                    fecha,
                    tiempo.isoformat(),
                    nombre_archivo,
                    config,
                    retry_policy
                )
                for equipo in lote
            ]
            resultados_lote = await asyncio.gather(*tareas)
            resultados.extend(resultados_lote)
        
        # 4. Enviar email con resultados
        await workflow.execute_activity(
            enviar_email_activity,
            args=[
                nombre_archivo,
                config['destinatarios_email'],
                fecha
            ],
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy
        )
        
        # 5. Cargar logs a MongoDB
        await workflow.execute_activity(
            cargar_logs_mongodb_activity,
            args=[
                nombre_archivo,
                config['mongo_uri'],
                config['mongo_database'],
                config['mongo_collection']
            ],
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy
        )
        
        # 6. Cargar logs a BigQuery
        await workflow.execute_activity(
            cargar_logs_bigquery_activity,
            args=[
                nombre_archivo,
                config['project_id'],
                'logs',
                'despertar_tr',
                500
            ],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=retry_policy
        )
        
        # Resumen de resultados
        exitosos = sum(1 for r in resultados if r['accionado'] == 'si')
        fallidos = sum(1 for r in resultados if r['accionado'] == 'no')
        
        workflow.logger.info(
            f"Workflow completado: {exitosos} exitosos, {fallidos} fallidos de {len(equipos)} equipos"
        )
        
        return {
            'total_equipos': len(equipos),
            'exitosos': exitosos,
            'fallidos': fallidos,
            'archivo_log': nombre_archivo,
            'fecha': fecha
        }

    async def _procesar_equipo(
        self,
        equipo: EquipoTR,
        fecha: str,
        tiempo: str,
        nombre_archivo: str,
        config: dict,
        retry_policy: RetryPolicy
    ) -> dict:
        """Procesa un equipo individual: verifica reproceso y ejecuta reinicio TR"""
        
        # Verificar si ya fue procesado
        count, exitos, errores = await workflow.execute_activity(
            verificar_reproceso_mongodb_activity,
            args=[
                equipo.mac,
                fecha,
                config['mongo_uri'],
                config['mongo_database'],
                config['mongo_collection']
            ],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy
        )
        
        # Lógica de reproceso: si ya tuvo éxito o más de 2 fallos, excluir
        if exitos >= 1 or errores > 2:
            resultado = ResultadoEjecucion(
                serial=equipo.serial,
                mac=equipo.mac,
                modem=equipo.modem,
                fecha=fecha,
                tiempo=tiempo,
                accionado='no',
                comment='excluido por filtro de reproceso'
            )
        else:
            # Intentar reiniciar TR
            try:
                resultado_tr = await workflow.execute_activity(
                    reiniciar_tr_haas_activity,
                    args=[equipo.mac],
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=retry_policy
                )
                
                if resultado_tr.get('result') == 'success':
                    accionado = 'si'
                    comment = 'reinicio ok'
                else:
                    # Verificar status para entender el fallo
                    resultado_status = await workflow.execute_activity(
                        verificar_status_haas_activity,
                        args=[equipo.mac],
                        start_to_close_timeout=timedelta(seconds=30),
                        retry_policy=retry_policy
                    )
                    
                    if resultado_status.get('result') == 'success':
                        comment = 'error al reiniciar TR con equipo online'
                    else:
                        comment = 'error al reiniciar TR por equipo offline'
                    
                    accionado = 'no'
                
                resultado = ResultadoEjecucion(
                    serial=equipo.serial,
                    mac=equipo.mac,
                    modem=equipo.modem,
                    fecha=fecha,
                    tiempo=tiempo,
                    accionado=accionado,
                    comment=comment
                )
                
            except Exception as e:
                workflow.logger.error(f"Error procesando {equipo.mac}: {e}")
                resultado = ResultadoEjecucion(
                    serial=equipo.serial,
                    mac=equipo.mac,
                    modem=equipo.modem,
                    fecha=fecha,
                    tiempo=tiempo,
                    accionado='no',
                    comment='fallo script'
                )
        
        # Escribir log en CSV
        await workflow.execute_activity(
            escribir_log_csv_activity,
            args=[nombre_archivo, resultado],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy
        )
        
        return {
            'mac': equipo.mac,
            'accionado': resultado.accionado,
            'comment': resultado.comment
        }
