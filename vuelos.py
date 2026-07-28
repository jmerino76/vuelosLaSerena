import os
import datetime
import requests

# Endpoint unificado de operaciones del aeropuerto
AEROAPI_URL = "https://flightaware.com"
API_KEY = os.environ.get("FLIGHTAWARE_API_KEY")

def obtener_vuelos_del_dia():
    if not API_KEY:
        print("Error: No se encontró la variable de entorno FLIGHTAWARE_API_KEY.")
        return None

    # Forzar el cálculo del día actual basándonos en la hora de Chile (UTC-4)
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    ahora_chile = datetime.datetime.now(zona_chile)
    
    # Crear los límites de inicio y fin del día en hora local chilena
    inicio_chile = ahora_chile.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_chile = ahora_chile.replace(hour=23, minute=59, second=59, microsecond=0)
    
    # Convertir esos límites exactos a su equivalente en UTC para enviárselos a FlightAware
    inicio_utc = inicio_chile.astimezone(datetime.timezone.utc)
    fin_utc = fin_chile.astimezone(datetime.timezone.utc)

    headers = {"x-apikey": API_KEY}
    params = {
        "start": inicio_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end": fin_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    ahora_local = datetime.datetime.now(zona_chile).strftime("%Y-%m-%d %H:%M:%S")
    
    contenido = f"# ✈️ Cronograma de Arribos Diarios - La Serena (SCSE)\n\n"
    contenido += f"Última actualización del reporte: `{ahora_local} (Hora Local Chile)`\n\n"
    contenido += "| Vuelo | Origen | Salida Estimada | Llegada Estimada/Real | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- |\n"

    lista_vuelos = []
    if datos:
        # Extraemos tanto los vuelos ya arribados como los que están programados para hoy
        if "arrivals" in datos and datos["arrivals"]:
            lista_vuelos.extend(datos["arrivals"])
        if "scheduled_arrivals" in datos and datos["scheduled_arrivals"]:
            lista_vuelos.extend(datos["scheduled_arrivals"])

    if not lista_vuelos:
        contenido += "| - | No se encontraron registros de vuelos para la jornada de hoy | - | - | - |\n"
    else:
        # Ordenamos los vuelos cronológicamente usando la fecha de llegada
        vuelos_ordenados = sorted(
            lista_vuelos, 
            key=lambda x: x.get("estimated_on") or x.get("scheduled_on") or ""
        )

        vistos = set()
        for vuelo in vuelos_ordenados:
            ident = vuelo.get("ident", "N/A")
            
            if ident in vistos and ident != "N/A":
                continue
            vistos.add(ident)
            
            origen = vuelo.get("origin", {}).get("code", "N/A")
            salida_t = vuelo.get("estimated_off") or vuelo.get("scheduled_off") or "N/A"
            llegada_t = vuelo.get("actual_on") or vuelo.get("estimated_on") or vuelo.get("scheduled_on") or "N/A"
            
            # Limpiar formatos de hora ISO y ajustar visualmente
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
    print("Reporte diario sincronizado con hora local generado con éxito.")

if __name__ == "__main__":
    datos_vuelos = obtener_vuelos_del_dia()
    generar_reporte(datos_vuelos)
