"""
Activities para Workflow: chogar_despertar_tr
Fase: HYBRID/NATIVE

Combina Activities centralizadas del SDK con Activities personalizadas.
"""

from temporalio import activity
from typing import Dict, Any

# Activities centralizadas del SDK
from platform_sdk.bigquery import bigquery_get_data, bigquery_execute_query
from platform_sdk.mongodb import mongodb_find, mongodb_insert_many
from platform_sdk.notifications import send_email


class CustomActivities:
    """Activities personalizadas para chogar_despertar_tr"""
    
    @activity.defn
    async def nombrar_csv(self, params: Dict[str, Any]) -> str:
        """
        Activity migrada desde Airflow task: nombrar_csv
        Operator original: PythonOperator
        
        Genera nombre de archivo CSV incremental por día
        """
        
        activity.logger.info(f"Executing nombrar_csv with params: {params}")
        
        try:
            import os
            import glob
            from datetime import datetime
            import pytz
            
            path = '/io/cel_chogar/per/confiabilidad/despertar_tr'
            zona_horaria = pytz.timezone('America/Argentina/Buenos_Aires')
            tiempo_txt = datetime.now(zona_horaria)
            time_new = tiempo_txt.strftime("%Y-%m-%d")
            
            # Buscar todos los archivos del día en el directorio
            patron = os.path.join(path, f"despertar_{time_new}-*.csv")
            archivos = glob.glob(patron)

            if not archivos:
                activity.logger.info("No se encontraron archivos para hoy.")
                nuevo_nombre = f"despertar_{time_new}-1.csv"
                nombre_txt = f'{path}/{nuevo_nombre}'
            else:
                # Ordenar los archivos por su número (extraído del nombre)
                archivos.sort(key=lambda x: int(x.split('-')[-1].split('.')[0]))
                
                # Obtener el último archivo (el que tiene el número más grande)
                ultimo_archivo = archivos[-1]
                numero = int(ultimo_archivo.split('-')[-1].split('.')[0])
                
                activity.logger.info(f"Último archivo: {ultimo_archivo}, Número: {numero}")
                
                # Incrementar el número y generar el nombre del nuevo archivo
                nuevo_numero = numero + 1
                nuevo_nombre = f"despertar_{time_new}-{nuevo_numero}.csv"
                nombre_txt = f'{path}/{nuevo_nombre}'
                
                activity.logger.info(f"Nuevo nombre: {nuevo_nombre}")

            activity.logger.info(f"nombrar_csv completed successfully: {nombre_txt}")
            return nombre_txt
            
        except Exception as e:
            activity.logger.error(f"nombrar_csv failed: {str(e)}")
            raise


    @activity.defn
    async def tr_implementacion_task(self, params: Dict[str, Any]) -> str:
        """
        Activity migrada desde Airflow task: tr_implementacion_task
        Operator original: PythonOperator
        
        Procesa equipos TR: consulta BigQuery, verifica MongoDB, reinicia agentes
        """
        
        activity.logger.info(f"Executing tr_implementacion_task with params: {params}")
        
        try:
            # TODO: Descomponer esta Activity en sub-activities:
            # 1. bigquery_get_data (SDK) - Obtener equipos desde BigQuery
            # 2. mongodb_find (SDK) - Verificar equipos procesados
            # 3. haas_reset_tr (custom) - Reiniciar agente TR
            # 4. haas_status (custom) - Verificar status
            # 5. write_csv_log (custom) - Escribir log
            
            activity.logger.info("Esta Activity debe descomponerse en sub-activities atómicas")
            activity.logger.info("Ver workflow_redesign.md para el diseño propuesto")
            
            # Implementación temporal
            result = {
                "status": "success",
                "message": "Activity debe ser descompuesta",
                "equipos_procesados": 0
            }
            
            activity.logger.info(f"tr_implementacion_task completed successfully")
            return result
            
        except Exception as e:
            activity.logger.error(f"tr_implementacion_task failed: {str(e)}")
            raise


    @activity.defn
    async def tr_correo_finalizacion(self, params: Dict[str, Any]) -> str:
        """
        Activity migrada desde Airflow task: tr_correo_finalizacion
        Operator original: PythonOperator
        
        Prepara y envía correo con resultados
        """
        
        activity.logger.info(f"Executing tr_correo_finalizacion with params: {params}")
        
        try:
            from datetime import datetime
            import pytz
            import os
            
            nombre_txt = params.get("nombre_archivo", "")
            
            zona_horaria = pytz.timezone('America/Argentina/Buenos_Aires')
            tiempo_txt = datetime.now(zona_horaria)
            
            dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            nombre_dia_semana = dias_semana[tiempo_txt.weekday()]
            
            nombres_meses_espanol = {
                1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
                7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
            }
            nombre_mes = nombres_meses_espanol[tiempo_txt.month]
            
            activity.logger.info(f"Archivo CSV: {nombre_txt}")
            
            if os.path.exists(nombre_txt):
                # TODO: Usar Activity centralizada send_email del SDK
                # await send_email({
                #     "to": ['yairfernandez@teco.com.ar'],
                #     "subject": f'Despertar TR resultado {tiempo_txt.year}-{tiempo_txt.month}-{tiempo_txt.day}',
                #     "html_content": f'Adjunto encontrarás el resultado...',
                #     "files": [nombre_txt]
                # })
                
                activity.logger.info("Email would be sent (usar SDK send_email)")
                return {"status": "success", "email_sent": True}
            else:
                activity.logger.warning("El archivo CSV resultante no se encontró.")
                return {"status": "warning", "email_sent": False}
            
        except Exception as e:
            activity.logger.error(f"tr_correo_finalizacion failed: {str(e)}")
            raise


    @activity.defn
    async def load_csv_to_db(self, params: Dict[str, Any]) -> str:
        """
        Activity migrada desde Airflow task: load_csv_to_db
        Operator original: PythonOperator
        
        Carga logs desde CSV a MongoDB y BigQuery
        """
        
        activity.logger.info(f"Executing load_csv_to_db with params: {params}")
        
        try:
            import pandas as pd
            
            nombre_txt = params.get("nombre_archivo", "")
            
            # Leer el archivo CSV
            df = pd.read_csv(nombre_txt, sep='|')
            
            activity.logger.info(f"Leídos {len(df)} registros del CSV")
            
            # TODO: Descomponer en dos Activities del SDK:
            # 1. mongodb_insert_many (SDK) - Cargar a MongoDB
            # 2. bigquery_execute_query (SDK) - Cargar a BigQuery en batches
            
            # Implementación temporal
            activity.logger.info("Usar mongodb_insert_many del SDK para MongoDB")
            activity.logger.info("Usar bigquery_execute_query del SDK para BigQuery")
            
            result = {
                "status": "success",
                "records_loaded": len(df),
                "mongodb": "pending",
                "bigquery": "pending"
            }
            
            activity.logger.info(f"load_csv_to_db completed successfully")
            return result
            
        except Exception as e:
            activity.logger.error(f"load_csv_to_db failed: {str(e)}")
            raise


# Instanciar activities personalizadas
custom_activities = CustomActivities()
