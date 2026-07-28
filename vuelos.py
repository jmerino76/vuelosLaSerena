import os
import datetime
import requests

# Volvemos al endpoint específico de llegadas de AeroAPI
AEROAPI_URL = "https://flightaware.com"
API_KEY = os.environ.get("FLIGHTAWARE_API_KEY")

def obtener_vuelos_del_dia():
    if not API_KEY:
        print("Error: No se encontró la variable de entorno FLIGHTAWARE_API_KEY.")
        return None

    # Calculamos cuántas horas han pasado en Chile desde la medianoche (00:00)
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    ahora_chile = datetime.datetime.now(zona_chile)
    
    # Para capturar todo el día, forzamos un inicio temprano en formato ISO absoluto o relativo
    # Calculamos los minutos transcurridos desde las 00:00 hasta la hora actual
    minutos_desde_medianoche = (ahora_chile.hour * 60) + ahora_chile.minute
    
    headers = {"x-apikey": API_KEY}
    
    # Parámetros oficiales: 'start' le dice a la API el momento inicial relativo o absoluto
    # Usamos una ventana de tiempo amplia para capturar los vuelos que llegaron temprano hoy
    params = {
        "start": f"-{minutos_desde_medianoche} minutes", 
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

    if not datos or "arrivals" not in datos or not datos["arrivals"]:
        contenido += "| - | No se encontraron registros de vuelos para la jornada de hoy | - | - | - |\n"
    else:
        # Ordenamos cronológicamente por hora de llegada estimada en pista
        vuelos_ordenados = sorted(
            datos["arrivals"], 
            key=lambda x: x.get("estimated_on") or x.get("scheduled_on") or ""
        )

        for vuelo in vuelos_ordenados:
            ident = vuelo.get("ident", "N/A")
            origen = vuelo.get("origin", {}).get("code", "N/A")
            
            salida_t = vuelo.get("estimated_off") or vuelo.get("scheduled_off") or "N/A"
            llegada_t = vuelo.get("actual_on") or vuelo.get("estimated_on") or vuelo.get("scheduled_on") or "N/A"
            
            # Limpiar formatos y cortar strings ISO
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
    print("Reporte diario regenerado de forma exitosa.")

if __name__ == "__main__":
    datos_vuelos = obtener_vuelos_del_dia()
    generar_reporte(datos_vuelos)
