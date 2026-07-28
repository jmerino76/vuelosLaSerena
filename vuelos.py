import os
import datetime
import requests

# Endpoint unificado de operaciones del aeropuerto (Garantiza datos mixtos)
AEROAPI_URL = "https://flightaware.com"
API_KEY = os.environ.get("FLIGHTAWARE_API_KEY")

def obtener_vuelos_del_dia():
    if not API_KEY:
        print("Error: No se encontró la variable de entorno FLIGHTAWARE_API_KEY.")
        return None

    # 1. Definir la zona horaria de Chile (UTC-4)
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    ahora_chile = datetime.datetime.now(zona_chile)
    
    # 2. Creamos una ventana de 24 horas centrada en el momento actual
    # 12 horas en el pasado para capturar la mañana y 12 en el futuro para capturar la tarde
    inicio_chile = ahora_chile - datetime.timedelta(hours=12)
    fin_chile = ahora_chile + datetime.timedelta(hours=12)
    
    # 3. Convertir a formato UTC absoluto para FlightAware
    inicio_utc = inicio_chile.astimezone(datetime.timezone.utc)
    fin_utc = fin_chile.astimezone(datetime.timezone.utc)

    headers = {"x-apikey": API_KEY}
    
    # Parámetros oficiales validados para el endpoint de aeropuertos v4
    params = {
        "start": inicio_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": fin_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_pages": 2
    }
    
    try:
        response = requests.get(AEROAPI_URL, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con FlightAware: {e}")
        return None

def generar_reporte(datos):
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    ahora_local = datetime.datetime.now(zona_chile).strftime("%Y-%m-%d %H:%M:%S")
    
    contenido = f"# ✈️ Cronograma de Arribos de la Jornada - La Serena (SCSE)\n\n"
    contenido += f"Última actualización del reporte: `{ahora_local} (Hora Local Chile)`\n\n"
    contenido += "| Vuelo | Origen | Salida Estimada | Llegada Estimada/Real | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- |\n"

    lista_vuelos = []
    if datos:
        # Extraemos tanto los arribos completados (arrivals) como los programados (scheduled_arrivals)
        if "arrivals" in datos and datos["arrivals"]:
            lista_vuelos.extend(datos["arrivals"])
        if "scheduled_arrivals" in datos and datos["scheduled_arrivals"]:
            lista_vuelos.extend(datos["scheduled_arrivals"])

    if not lista_vuelos:
        contenido += "| - | No se encontraron registros de vuelos en la ventana de tiempo de hoy | - | - | - |\n"
    else:
        # Ordenamos los vuelos cronológicamente basándonos en la hora de llegada estimada
        vuelos_ordenados = sorted(
            lista_vuelos, 
            key=lambda x: x.get("estimated_on") or x.get("scheduled_on") or ""
        )

        vistos = set()
        for vuelo in vuelos_ordenados:
            ident = vuelo.get("ident", "N/A")
            
            # Evitar que vuelos repetidos aparezcan dos veces en el markdown
            if ident in vistos and ident != "N/A":
                continue
            vistos.add(ident)
            
            origen = vuelo.get("origin", {}).get("code", "N/A")
            salida_t = vuelo.get("estimated_off") or vuelo.get("scheduled_off") or "N/A"
            llegada_t = vuelo.get("actual_on") or vuelo.get("estimated_on") or vuelo.get("scheduled_on") or "N/A"
            
            # Limpieza visual de strings de fecha
            salida = salida_t.replace("T", " ").replace("Z", "")[:16]
            llegada = llegada_t.replace("T", " ").replace("Z", "")[:16]
            
            estado = vuelo.get("status", "Desconocido")
            
            # Normalización gráfica de estados aeronáuticos
            if "Arrived" in estado:
                estado = "🟢 Aterrizó"
            elif "En Route" in estado:
                estado = "🔵 En Ruta"
            elif "Scheduled" in estado:
                estado = "⚪ Programado"
                
            contenido += f"| **{ident}** | {origen} | {salida} | {llegada} | {estado} |\n"
            
    contenido += f"\n\n*Datos automatizados de la jornada a través de AeroAPI de [FlightAware](https://es.flightaware.com/).*"

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(contenido)
    print("Reporte de ventana diaria de 24h generado con éxito.")

if __name__ == "__main__":
    datos_vuelos = obtener_vuelos_del_dia()
    generar_reporte(datos_vuelos)
