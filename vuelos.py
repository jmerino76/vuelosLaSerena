import os
import datetime
import requests

# Cambiamos al endpoint general de vuelos del aeropuerto para permitir rangos de tiempo
AEROAPI_URL = "https://flightaware.com"
API_KEY = os.environ.get("FLIGHTAWARE_API_KEY")

def obtener_vuelos_del_dia():
    if not API_KEY:
        print("Error: No se encontró la variable de entorno FLIGHTAWARE_API_KEY.")
        return None

    # Calculamos el rango completo del día de hoy en UTC
    ahora_utc = datetime.datetime.now(datetime.timezone.utc)
    inicio_dia = ahora_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_dia = ahora_utc.replace(hour=23, minute=59, second=59, microsecond=0)

    headers = {"x-apikey": API_KEY}
    
    # Este endpoint sí procesa correctamente 'start' y 'end' para todo el día
    params = {
        "start": inicio_dia.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": fin_dia.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "max_pages": 1
    }
    
    try:
        response = requests.get(AEROAPI_URL, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con FlightAware: {e}")
        return None

def generar_reporte(datos):
    # Ajuste visual a la hora de Chile (UTC-4)
    ahora_local = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")
    
    contenido = f"# ✈️ Cronograma de Arribos Diarios - La Serena (SCSE)\n\n"
    contenido += f"Última actualización del reporte: `{ahora_local} (Hora Local Chile)`\n\n"
    contenido += "| Vuelo | Origen | Salida Estimada | Llegada Estimada/Real | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- |\n"

    # El endpoint unificado separa los vuelos en "arrivals" (ya aterrizados) y "scheduled_arrivals" (por llegar)
    lista_vuelos = []
    if datos:
        if "arrivals" in datos and datos["arrivals"]:
            lista_vuelos.extend(datos["arrivals"])
        if "scheduled_arrivals" in datos and datos["scheduled_arrivals"]:
            lista_vuelos.extend(datos["scheduled_arrivals"])

    if not lista_vuelos:
        contenido += "| - | No se registraron vuelos para el día de hoy | - | - | - |\n"
    else:
        # Ordenamos cronológicamente todos los arribos detectados
        vuelos_ordenados = sorted(
            lista_vuelos, 
            key=lambda x: x.get("estimated_on") or x.get("scheduled_on") or ""
        )

        # Usamos un set para evitar filas duplicadas si un vuelo aparece en ambas listas de la API
        vistos = set()

        for vuelo in vuelos_ordenados:
            ident = vuelo.get("ident", "N/A")
            
            # Si el vuelo ya se procesó, lo saltamos
            if ident in vistos and ident != "N/A":
                continue
            vistos.add(ident)
            
            origen = vuelo.get("origin", {}).get("code", "N/A")
            salida_t = vuelo.get("estimated_off") or vuelo.get("scheduled_off") or "N/A"
            llegada_t = vuelo.get("actual_on") or vuelo.get("estimated_on") or vuelo.get("scheduled_on") or "N/A"
            
            salida = salida_t.replace("T", " ").replace("Z", "")[:16]
            llegada = llegada_t.replace("T", " ").replace("Z", "")[:16]
            
            estado = vuelo.get("status", "Desconocido")
            
            if "Arrived" in estado:
                estado = "🟢 Aterrizó"
            elif "En Route" in estado:
                estado = "🔵 En Ruta"
            elif "Scheduled" in estado:
                estado = "⚪ Programado"
                
            contenido += f"| **{ident}** | {origen} | {salida} | {llegada} | {estado} |\n"
            
    contenido += f"\n\n*Datos diarios automatizados a través de AeroAPI de [FlightAware](https://es.flightaware.com/).*"

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(contenido)
    print("Reporte diario unificado generado con éxito.")

if __name__ == "__main__":
    datos_vuelos = obtener_vuelos_del_dia()
    generar_reporte(datos_vuelos)
