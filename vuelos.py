import os
import datetime
import requests

# Configuración de la API y Destino (La Serena - SCSE)
AEROAPI_URL = "https://flightaware.com"
API_KEY = os.environ.get("FLIGHTAWARE_API_KEY")

def obtener_vuelos():
    if not API_KEY:
        print("Error: No se encontró la variable de entorno FLIGHTAWARE_API_KEY.")
        return None

    headers = {"x-apikey": API_KEY}
    params = {"max_pages": 1, "cursor": None}
    
    try:
        response = requests.get(AEROAPI_URL, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con FlightAware: {e}")
        return None

def generar_reporte(datos):
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    contenido = f"# ✈️ Estado de Vuelos - Arribos a La Serena (SCSE)\n\n"
    contenido += f"Última actualización: `{ahora}`\n\n"
    contenido += "| Vuelo | Origen | Salida Estimada | Llegada Estimada | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- |\n"

    if not datos or "arrivals" not in datos or not datos["arrivals"]:
        contenido += "| - | No hay vuelos programados en este momento | - | - | - |\n"
    else:
        for vuelo in datos["arrivals"]:
            ident = vuelo.get("ident", "N/A")
            origen = vuelo.get("origin", {}).get("code", "N/A")
            
            # Formatear horas de llegada y salida
            salida_t = vuelo.get("estimated_off") or vuelo.get("scheduled_off") or "N/A"
            llegada_t = vuelo.get("estimated_on") or vuelo.get("scheduled_on") or "N/A"
            
            salida = salida_t.replace("T", " ").replace("Z", "")[:16]
            llegada = llegada_t.replace("T", " ").replace("Z", "")[:16]
            
            estado = vuelo.get("status", "Desconocido")
            contenido += f"| **{ident}** | {origen} | {salida} | {llegada} | {estado} |\n"
            
    contenido += f"\n\n*Datos automatizados a través de AeroAPI de [FlightAware](https://flightaware.com).*"

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(contenido)
    print("Reporte README.md generado correctamente.")

if __name__ == "__main__":
    datos_vuelos = obtener_vuelos()
    generar_reporte(datos_vuelos)
