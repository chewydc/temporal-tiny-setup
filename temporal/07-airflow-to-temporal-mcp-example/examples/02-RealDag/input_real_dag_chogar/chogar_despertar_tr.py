"""
DAG chogar_despertar_tr
===========================================
**Codigo:** chogar_despertar_tr
**Referentes:** Fernandez Yair

Descripcion
-----------
Trae equipos desde BigQuery que no están reportando información TR y reinicia el agente interno de CM
Excluye los casos por reproceso
Escribe logs en BigQuery
"""

import os, json, csv, time, re, pytz
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.http_operator import SimpleHttpOperator
from airflow.operators.email_operator import EmailOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.models import TaskInstance
from airflow.exceptions import AirflowException

#Para ir cargando de datos el dataframe
import threading

#xcom
from lib.teco_data_management import push_data
from lib.teco_events import *
import glob

#Para MongoDB
from pymongo import MongoClient
from airflow.providers.mongo.hooks.mongo import MongoHook

#BigQuery
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryValueCheckOperator,
    BigQueryGetDatasetTablesOperator,
    BigQueryExecuteQueryOperator,
    BigQueryGetDatasetOperator,
    BigQueryGetDataOperator,
    BigQueryInsertJobOperator,
    BigQueryDeleteTableOperator
)

#Para uso de HaaS
from cel_chogar.lib.chogar_libreria_haas_3scale import *

os.environ["https_proxy"] = "http://URL_PLACEHOLDER:8080" #Se deshabilita proxy para poder hacer consultas a BQ
DAG_ID = os.path.basename(__file__).replace(".pyc", "").replace(".py", "")
#arg
default_args = {
    'owner': 'chogar',
    'depends_on_past': False,
    'start_date': datetime(2024, 8, 27),
    'email': ['xxx@teco.com.ar'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
    'provide_context': True,
    'dag_type': 'custom'
}

dag = DAG (
    dag_id = DAG_ID,
    #schedule_interval = None, #scheduler para repetir la tarea
    schedule_interval = '50 * * * *', #None, 
    catchup = False, #intenta si falla
    description = "DAG Automatización Despertar TR", 
    tags = ["chogar"],
    default_args = default_args,
)

def doc_sphinx():
    #función para habilitar el código del DAG en Sphinx
    pass

####INICIALIZAR ARCHIVO RESULTADOS .csv
path = '/io/cel_chogar/per/confiabilidad/despertar_tr'
zona_horaria = pytz.timezone('America/Argentina/Buenos_Aires')
tiempo_txt = datetime.now(zona_horaria)
time_new = tiempo_txt.strftime("%Y-%m-%d")

#nombre_txt = f'{path}/despertar_{time_new}.csv'




####FUNCIONES
def nombrar_csv(ti):
    # Buscar todos los archivos del día en el directorio
    patron = os.path.join(path, f"despertar_{time_new}-*.csv")
    archivos = glob.glob(patron)

    if not archivos:
        print("No se encontraron archivos para hoy.")
        nuevo_nombre = f"despertar_{time_new}-1.csv"
        nombre_txt = f'{path}/{nuevo_nombre}'

        ti.xcom_push(key='nombre_archivo', value=nombre_txt)
        return nombre_txt
    
    # Ordenar los archivos por su número (extraído del nombre)
    archivos.sort(key=lambda x: int(x.split('-')[-1].split('.')[0]))

    # Obtener el último archivo (el que tiene el número más grande)
    ultimo_archivo = archivos[-1]
    numero = int(ultimo_archivo.split('-')[-1].split('.')[0])


    if ultimo_archivo is not None:
        print("Último archivo:", ultimo_archivo)
        print("Número del archivo:", numero)
        # Aquí puedes incrementar el número y generar el nombre del nuevo archivo
        nuevo_numero = numero + 1
        nuevo_nombre = f"despertar_{time_new}-{nuevo_numero}.csv"
        print("Nuevo nombre:", nuevo_nombre)
        nombre_txt=f'{path}/{nuevo_nombre}'
    else:
        print("No se encontraron archivos para hoy.")
        nuevo_nombre = f"despertar_{time_new}-1.csv"
        nombre_txt = f'{path}/{nuevo_nombre}'

    #ti = kwargs['ti']
    # Almacenar el nombre del archivo en XCom
    ti.xcom_push(key='nombre_archivo', value=nombre_txt)

    return nombre_txt

nombrar_csv_task = PythonOperator(
    task_id="nombrar_csv", #identificación de la tarea
    python_callable = nombrar_csv, #llamo la función definida
    dag=dag
)


# Función encargada de escribir en un csv el log del evento de a uno
def logs_csv(serial, mac, modem, accionado, comment, ti):
    tiempo = datetime.now(zona_horaria)
    fecha = tiempo.strftime("%Y-%m-%d")
    #print(f'serial {serial} listo para escribir csv') ###debug
    #ti = kwargs['ti']
    nombre_txt=ti.xcom_pull(task_ids="nombrar_csv", key="nombre_archivo")
    with open(nombre_txt, 'a', encoding='latin1') as csvfile:
        columnas = ['serial','mac','modem','fecha', 'tiempo','accionado', 'comment']
        writer = csv.DictWriter(csvfile, fieldnames=columnas, delimiter ='|',  lineterminator='\n')
        if csvfile.tell() == 0:
            writer.writeheader()
        writer.writerow({'serial': serial, 'mac': mac,'modem': modem, 'fecha': fecha, 'tiempo': tiempo, 'accionado': accionado, 'comment': comment})
        #print(f'serial {serial} se escribió en el csv') ###debug

# Especifico la conexión y las variables para MongoDB y debajo la función para conectarse
mongo_conn = 'AntoFi_Mongodb'
mongo_db = 'chogar_prod'
mongo_collection = 'logs_despertar_tr'

def connecter( mongo, database, collection ):
    hook = MongoHook( mongo )
    client = hook.get_conn()
    db = client[ database ]
    return db[ collection ]

# Verificación para excluir el dispositivo del proceso si fuera necesario
def check_mongodb(mac_ver,**kwargs):
    # Obtener la conexión a MongoDB
    collection = connecter( mongo_conn, mongo_db, mongo_collection )

    # Buscar los registros con el serial number especificado
    registros = collection.find({"mac": mac_ver, "fecha": time_new})

    # Inicializar contadores
    count_register = 0
    procesados_exito = 0
    procesados_error = 0

    # Recorrer los registros y contar las veces que aparece y su estado de procesamiento
    for registro in registros:
        if registro.get("comment") != "excluido por filtro de reproceso":
            count_register += 1
            if registro.get("accionado") == "si":
                procesados_exito += 1
            elif registro.get("accionado") == "no":
                procesados_error += 1

    return count_register,procesados_exito,procesados_error

# Define una función que realiza la llamada HTTP y extrae la respuesta
def main_tr(ti,**kwargs):
    #Consulta a tabla calculada mediante consulta programada dentro de BigQuery
    bq = BigQueryGetDataOperator(
        task_id="get_bq_data",   
        dataset_id="scripts_tambo",
        table_id="despertar_tr",
        max_results=1000, #cantidad de resultados a traer de la tablañ
        use_legacy_sql=False,
        as_dict=True,
        gcp_conn_id = "cdh_gcp" #el conector del proyecto
    ).execute(kwargs)

    results = list(bq)
    mac_list = [row['MAC'] for row in results]
    serial_list = [row['SerialNumber'] for row in results]
    modem_list = [row['modem'] for row in results]

    #print(mac_list)

    # Función encargada de la lógica de ejecución
    def ejecucion(serial, mac, modem,**kwargs):
        #se verifica si este equipo ya fue procesado, ya sea de forma exitosa o no
        check = check_mongodb(mac)

        q_try = check[0]
        q_success = check[1]
        q_fail = check[2]

        if q_success < 1 and q_fail <= 2:
            try:
                print(f'Se le reiniciará la interface TR a {mac}')
                resultado_json_tr=haas_reset_tr(mac,dag)                            #Ejecución del reinicio del agente TR
                respuesta_tr = resultado_json_tr['result']

                if respuesta_tr=='success':
                    accionado='si'
                    comment='reinicio ok'
                else:
                    accionado='no'
                    resultado_json_status=haas_status(mac,dag)                      #Verificación de status para entender porque falló
                    respuesta_status = resultado_json_status['result']
                    if respuesta_status=='success':
                        comment='error al reiniciar TR con equipo online'
                    else:
                        comment='error al reiniciar TR por equipo offline'

                logs_csv(serial, mac, modem, accionado, comment,ti)                 #Escritura de logs en csv
                    
            except Exception as e:
                print(f'dentro del segundo except, el error es{e}')
                print(f'{mac}: fallo procesamiento')
                accionado='no'
                comment='fallo script'
                logs_csv(serial, mac, modem, accionado, comment,ti)                 #Escritura de logs en csv

        else:
            print(f'El equipo {mac} ya fue procesado con anterioridad, se lo excluirá.') 
            accionado = 'no'
            comment = 'excluido por filtro de reproceso'

            logs_csv(serial, mac, modem, accionado, comment,ti)                     #Escritura de logs en csv

    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(ejecucion,serial_list,mac_list,modem_list)

# Define una tarea que realiza la llamada HTTP y captura los datos del gateway

tr_implementacion_task = PythonOperator(
    task_id=f'tr_implementacion_task',
    python_callable=main_tr,
    dag=dag,
)

def enviar_correo(ti,**kwargs):
    nombre_txt=ti.xcom_pull(task_ids="nombrar_csv", key="nombre_archivo")
    print(f'Este es el nombre del archivo {nombre_txt}')
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    nombre_dia_semana = dias_semana[tiempo_txt.weekday()]   # Obtener el nombre del día de la semana
    nombre_mes = tiempo_txt.strftime('%B')  # Nombre completo del mes
    numero_dia = tiempo_txt.day # Obtener el número del día, mes y año
    nombres_meses_espanol = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    nombre_mes = nombres_meses_espanol[tiempo_txt.month]
    anio = tiempo_txt.year
    # Obtener la ruta del archivo CSV resultante
    if os.path.exists(nombre_txt):
        email_task = EmailOperator(
            task_id='tr_enviar_correo',
            #to=['yairfernandez@teco.com.ar'],
            to=['xxx@teco.com.ar'],
            subject=f'Despertar TR resultado {str(tiempo_txt.year)}-{str(tiempo_txt.month)}-{str(tiempo_txt.day)}',
            html_content=f'Adjunto encontrarás el resultado de la implementación correspondiente al <b>{str(nombre_dia_semana)} {str(tiempo_txt.day)} de {str(nombre_mes)} de {str(tiempo_txt.year)}.</b> .',
            files=[nombre_txt],  # Ruta al archivo CSV resultante  
            dag=kwargs['dag'],
        )
        email_task.execute(context=kwargs)
    else:
        print("El archivo CSV resultante no se encontró.")

# Crear una tarea PythonOperator para enviar el correo electrónico al finalizar todas las tareas
correo_finalizacion_task = PythonOperator(
    task_id='tr_correo_finalizacion',
    python_callable=enviar_correo,
    trigger_rule = 'all_done',
    provide_context=True,  # Proporcionar el contexto para acceder al DAG
    dag=dag,
)

def load_csv_to_db(ti,**kwargs):
    ##### INICIO Escribir los registros en MongoDB #####
    # Obtener la conexión a MongoDB
    collection = connecter( mongo_conn, mongo_db, mongo_collection )

    #ti = kwargs['ti']
    # Nombre del csv a leer
    #ti = kwargs['ti']
    nombre_txt=ti.xcom_pull(task_ids="nombrar_csv", key="nombre_archivo")

    # Leer el archivo CSV
    df = pd.read_csv(nombre_txt, sep='|')

    # Convertir DataFrame a un diccionario y cargarlo en MongoDB
    data = df.to_dict(orient='records')
    collection.insert_many(data)

    print('Se han cargado los registros en MongoDB')
    ##### FIN Escribir los registros en MongoDB #####

    ##### INICIO Escribir los registros en BigQuery #####
    # Construir la consulta INSERT INTO para BigQuery el lotes para que corra la query
    batch_size = 500 #cantidad de registros a concatenar para insertar
    for i in range(0, len(df), batch_size):
        batch = df[i:i+batch_size]
        values = []
        for _, row in batch.iterrows():
            # Convierte la fecha al formato "yyyy-mm-dd"
            # fecha_obj = datetime.strptime(row['fecha'], "%d-%m-%Y")
            # fecha_formateada = fecha_obj.strftime("%Y-%m-%d")
            
            # Construir la cadena de valores
            value = (
                f"'{row['serial']}',"
                f"'{row['mac']}',"
                f"'{row['modem']}',"
                f"'{row['fecha']}',"
                f"'{row['tiempo']}',"
                f"'{row['accionado']}',"
                f"'{row['comment']}'"
            )
            values.append(f"({value})")

        # Unir todos los valores en una sola cadena SQL
        values_sql = ', '.join(values)

        # Construir la consulta completa
        insert_select_query = f"""
        INSERT INTO `xxx.logs.despertar_tr`
        VALUES {values_sql}
        """

        bq = BigQueryExecuteQueryOperator(
            task_id=f"insert_batch_{i}",   
            sql=insert_select_query,
            use_legacy_sql=False,
            write_disposition='WRITE_APPEND',
            gcp_conn_id = "cdh_gcp" #el conector del proyecto
        ).execute(kwargs)
        print('Se han cargado los registros en BigQuery')
    ##### FIN Escribir los registros en BigQuery #####

load_logs_task = PythonOperator(
    task_id="load_csv_to_db", #identificación de la tarea
    python_callable = load_csv_to_db, #llamo la función definida
    dag=dag
)

# Establecer dependencia entre todas las tareas y la tarea de envío de correo electrónico
nombrar_csv_task >> tr_implementacion_task >> correo_finalizacion_task >> load_logs_task


