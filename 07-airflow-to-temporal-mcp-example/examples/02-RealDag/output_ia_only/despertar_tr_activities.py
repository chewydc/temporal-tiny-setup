"""
Activities para el workflow de Despertar TR
"""
import os
import csv
import glob
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass
import pytz
import pandas as pd
from temporalio import activity
from pymongo import MongoClient
from google.cloud import bigquery


@dataclass
class EquipoTR:
    serial: str
    mac: str
    modem: str


@dataclass
class ResultadoEjecucion:
    serial: str
    mac: str
    modem: str
    fecha: str
    tiempo: str
    accionado: str
    comment: str


@activity.defn
async def nombrar_csv_activity(path: str, fecha: str) -> str:
    """Genera el nombre del archivo CSV con numeración incremental"""
    patron = os.path.join(path, f"despertar_{fecha}-*.csv")
    archivos = glob.glob(patron)

    if not archivos:
        nuevo_nombre = f"despertar_{fecha}-1.csv"
    else:
        archivos.sort(key=lambda x: int(x.split('-')[-1].split('.')[0]))
        ultimo_archivo = archivos[-1]
        numero = int(ultimo_archivo.split('-')[-1].split('.')[0])
        nuevo_numero = numero + 1
        nuevo_nombre = f"despertar_{fecha}-{nuevo_numero}.csv"

    nombre_completo = os.path.join(path, nuevo_nombre)
    activity.logger.info(f"Archivo CSV generado: {nombre_completo}")
    return nombre_completo


@activity.defn
async def obtener_equipos_bigquery_activity(
    project_id: str,
    dataset_id: str,
    table_id: str,
    max_results: int = 1000
) -> List[EquipoTR]:
    """Obtiene equipos desde BigQuery que no reportan TR"""
    client = bigquery.Client(project=project_id)
    query = f"""
        SELECT SerialNumber, MAC, modem
        FROM `{project_id}.{dataset_id}.{table_id}`
        LIMIT {max_results}
    """
    
    results = client.query(query).result()
    equipos = [
        EquipoTR(serial=row['SerialNumber'], mac=row['MAC'], modem=row['modem'])
        for row in results
    ]
    
    activity.logger.info(f"Obtenidos {len(equipos)} equipos desde BigQuery")
    return equipos


@activity.defn
async def verificar_reproceso_mongodb_activity(
    mac: str,
    fecha: str,
    mongo_uri: str,
    database: str,
    collection: str
) -> Tuple[int, int, int]:
    """Verifica en MongoDB si el equipo ya fue procesado"""
    client = MongoClient(mongo_uri)
    db = client[database]
    coll = db[collection]
    
    registros = coll.find({"mac": mac, "fecha": fecha})
    
    count_register = 0
    procesados_exito = 0
    procesados_error = 0
    
    for registro in registros:
        if registro.get("comment") != "excluido por filtro de reproceso":
            count_register += 1
            if registro.get("accionado") == "si":
                procesados_exito += 1
            elif registro.get("accionado") == "no":
                procesados_error += 1
    
    client.close()
    return count_register, procesados_exito, procesados_error


@activity.defn
async def reiniciar_tr_haas_activity(mac: str) -> Dict:
    """Reinicia el agente TR mediante HaaS"""
    # Importar la función de HaaS (ajustar según tu implementación)
    from cel_chogar.lib.chogar_libreria_haas_3scale import haas_reset_tr
    
    resultado = haas_reset_tr(mac, None)
    activity.logger.info(f"Reinicio TR para {mac}: {resultado}")
    return resultado


@activity.defn
async def verificar_status_haas_activity(mac: str) -> Dict:
    """Verifica el status del equipo en HaaS"""
    from cel_chogar.lib.chogar_libreria_haas_3scale import haas_status
    
    resultado = haas_status(mac, None)
    activity.logger.info(f"Status para {mac}: {resultado}")
    return resultado


@activity.defn
async def escribir_log_csv_activity(
    nombre_archivo: str,
    resultado: ResultadoEjecucion
) -> None:
    """Escribe el resultado en el archivo CSV"""
    with open(nombre_archivo, 'a', encoding='latin1') as csvfile:
        columnas = ['serial', 'mac', 'modem', 'fecha', 'tiempo', 'accionado', 'comment']
        writer = csv.DictWriter(csvfile, fieldnames=columnas, delimiter='|', lineterminator='\n')
        
        if csvfile.tell() == 0:
            writer.writeheader()
        
        writer.writerow({
            'serial': resultado.serial,
            'mac': resultado.mac,
            'modem': resultado.modem,
            'fecha': resultado.fecha,
            'tiempo': resultado.tiempo,
            'accionado': resultado.accionado,
            'comment': resultado.comment
        })
    
    activity.logger.info(f"Log escrito para {resultado.mac}")


@activity.defn
async def cargar_logs_mongodb_activity(
    nombre_archivo: str,
    mongo_uri: str,
    database: str,
    collection: str
) -> None:
    """Carga los logs del CSV a MongoDB"""
    df = pd.read_csv(nombre_archivo, sep='|')
    data = df.to_dict(orient='records')
    
    client = MongoClient(mongo_uri)
    db = client[database]
    coll = db[collection]
    coll.insert_many(data)
    client.close()
    
    activity.logger.info(f"Cargados {len(data)} registros en MongoDB")


@activity.defn
async def cargar_logs_bigquery_activity(
    nombre_archivo: str,
    project_id: str,
    dataset_id: str,
    table_id: str,
    batch_size: int = 500
) -> None:
    """Carga los logs del CSV a BigQuery"""
    df = pd.read_csv(nombre_archivo, sep='|')
    client = bigquery.Client(project=project_id)
    
    for i in range(0, len(df), batch_size):
        batch = df[i:i+batch_size]
        values = []
        
        for _, row in batch.iterrows():
            value = (
                f"'{row['serial']}', '{row['mac']}', '{row['modem']}', "
                f"'{row['fecha']}', '{row['tiempo']}', '{row['accionado']}', '{row['comment']}'"
            )
            values.append(f"({value})")
        
        values_sql = ', '.join(values)
        query = f"""
            INSERT INTO `{project_id}.{dataset_id}.{table_id}`
            VALUES {values_sql}
        """
        
        client.query(query).result()
    
    activity.logger.info(f"Cargados {len(df)} registros en BigQuery")


@activity.defn
async def enviar_email_activity(
    nombre_archivo: str,
    destinatarios: List[str],
    fecha: str
) -> None:
    """Envía email con el resultado del proceso"""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    
    zona_horaria = pytz.timezone('America/Argentina/Buenos_Aires')
    tiempo = datetime.now(zona_horaria)
    
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    nombre_dia = dias_semana[tiempo.weekday()]
    
    nombres_meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    nombre_mes = nombres_meses[tiempo.month]
    
    msg = MIMEMultipart()
    msg['From'] = 'automation@teco.com.ar'
    msg['To'] = ', '.join(destinatarios)
    msg['Subject'] = f'Despertar TR resultado {fecha}'
    
    body = f'Adjunto encontrarás el resultado de la implementación correspondiente al <b>{nombre_dia} {tiempo.day} de {nombre_mes} de {tiempo.year}.</b>'
    msg.attach(MIMEText(body, 'html'))
    
    if os.path.exists(nombre_archivo):
        with open(nombre_archivo, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(nombre_archivo)}')
            msg.attach(part)
    
    activity.logger.info(f"Email enviado a {destinatarios}")
