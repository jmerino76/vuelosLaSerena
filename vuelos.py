import os
import datetime
import requests

# Endpoint oficial de itinerarios/schedules de AeroAPI v4
AEROAPI_URL = "https://flightaware.com"
API_KEY = os.environ.get("FLIGHTAWARE_API_KEY")

def obtener_itinerario_del_dia():
    if not API_KEY:
        print("Error: No se encontró la variable de entorno FLIGHTAWARE_API_KEY.")
        return None

    # Calcular la fecha de hoy basada estrictamente en la hora de Chile (UTC-4)
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    hoy_chile = datetime.datetime.now(zona_chile).date()
    
    # Formatear las fechas en formato AAAA-MM-DD requeridas por el endpoint de schedules
    fecha_str = hoy_chile.strftime("%Y-%m-%d")
    
    headers = {"x-apikey": API_KEY}
    
    # Filtramos los itinerarios que tengan como destino La Serena (SCSE)
    params = {
        "destination": "SCSE",
        "max_pages": 1
    }
    
    # La URL del endpoint de itinerarios requiere la fecha de inicio y fin en la ruta
    url_completa = f"{AEROAPI_URL}/{fecha_str}/{fecha_str}"
    
    try:
        response = requests.get(url_completa, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con los itinerarios de FlightAware: {e}")
        return None

def generar_reporte(datos):
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    ahora_local = datetime.datetime.now(zona_chile).strftime("%Y-%m-%d %H:%M:%S")
    
    contenido = f"# ✈️ Itinerario Completo de Arribos Diarios - La Serena (SCSE)\n\n"
    contenido += f"Última actualización del reporte: `{ahora_local} (Hora Local Chile)`\n\n"
    contenido += "| Vuelo | Origen | Salida Programada | Llegada Programada | Tipo de Avión |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- |\n"

    # El JSON devuelto por este endpoint agrupa los datos en la clave 'scheduled'
    lista_vuelos = datos.get("scheduled", []) if datos else []

    if not lista_vuelos:
        contenido += "| - | No se encontraron registros de itinerarios comerciales para hoy | - | - | - |\n"
    else:
        # Ordenamos los itinerarios cronológicamente por la hora de llegada programada
        vuelos_ordenados = sorted(
            lista_vuelos, 
            key=lambda x: x.get("scheduled_in") or ""
        )

        vistos = set()
        for vuelo in vuelos_ordenados:
            ident = vuelo.get("ident", "N/A")
            
            # Evitar duplicados visuales en la tabla
            if ident in vistos and ident != "N/A":
                continue
            vistos.add(ident)
            
            origen = vuelo.get("origin", "N/A")
            salida_t = vuelo.get("scheduled_out", "N/A")
            llegada_t = vuelo.get("scheduled_in", "N/A")
            aircraft = vuelo.get("aircraft_type", "N/A")
            
            # Limpiar formatos ISO para dejar solo horas legibles (Ej: 2026-07-28 08:30)
            salida = salida_t.replace("T", " ").replace("Z", "")[:16]
            llegada = llegada_t.replace("T", " ").replace("Z", "")[:16]
            
            contenido += f"| **{ident}** | {origen} | {salida} | {llegada} | {aircraft} |\n"
            
    contenido += f"\n\n*Datos diarios programados obtenidos a través de AeroAPI de [FlightAware](https://es.flightaware.com/).*"

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(contenido)
    print("Reporte de itinerarios diarios generado con éxito.")

if __name__ == "__main__":
    datos_vuelos = obtener_itinerario_del_dia()
    generar_reporte(datos_vuelos)
