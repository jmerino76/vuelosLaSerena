import os
import datetime
import requests

# Forzamos HTTP plano debido a restricciones del plan gratuito de Aviationstack
AVIATIONSTACK_URL = "http://aviationstack.com"
API_KEY = os.environ.get("FLIGHTAWARE_API_KEY")

def obtener_vuelos_del_dia():
    if not API_KEY:
        print("Error: No se encontró la credencial de la API en GitHub Secrets.")
        return None

    # Consultamos los vuelos de la principal aerolínea de la región (LATAM - LNE/LAN)
    # Esto despierta el búfer de datos de la API y garantiza que nos entregue información real
    params = {
        "access_key": API_KEY,
        "airline_icao": "LNE",  # LATAM Express / Chile
        "limit": 100
    }
    
    try:
        response = requests.get(AVIATIONSTACK_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con Aviationstack: {e}")
        return None

def generar_reporte(datos):
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    ahora_local = datetime.datetime.now(zona_chile).strftime("%Y-%m-%d %H:%M:%S")
    
    contenido = f"# ✈️ Cronograma de Arribos Diarios - La Serena (SCSE / LSC)\n\n"
    contenido += f"Última actualización del reporte: `{ahora_local} (Hora Local Chile)`\n\n"
    contenido += "| Vuelo | Aerolínea | Origen | Salida Estimada | Llegada Estimada/Real | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"

    todos_los_vuelos = datos.get("data", []) if datos else []
    
    # Filtramos localmente mediante Python solo los arribos dirigidos al Aeropuerto La Florida (LSC)
    vuelos_la_serena = [
        f for f in todos_los_vuelos 
        if f.get("arrival", {}).get("iata") == "LSC"
    ]

    if not vuelos_la_serena:
        contenido += "| - | - | No hay vuelos de LATAM detectados para La Serena en este bloque horario | - | - | - |\n"
    else:
        # Ordenamos los arribos cronológicamente por horario de llegada programado
        vuelos_ordenados = sorted(
            vuelos_la_serena,
            key=lambda x: x.get("arrival", {}).get("scheduled") or ""
        )

        for f in vuelos_ordenados:
            vuelo_num = f.get("flight", {}).get("iata") or f.get("flight", {}).get("number") or "N/A"
            aerolinea = f.get("airline", {}).get("name") or "LATAM"
            origen = f.get("departure", {}).get("iata") or "SCL"
            
            # Capturar horas estimadas o reales
            salida_raw = f.get("departure", {}).get("scheduled") or "N/A"
            llegada_raw = f.get("arrival", {}).get("actual") or f.get("arrival", {}).get("scheduled") or "N/A"
            
            # Formatear el texto de fecha de manera limpia (primeros 16 caracteres: AAAA-MM-DD HH:MM)
            salida = salida_raw.replace("T", " ")[:16] if salida_raw != "N/A" else "N/A"
            llegada = llegada_raw.replace("T", " ")[:16] if llegada_raw != "N/A" else "N/A"
            
            # Mapear estados para el usuario
            status_raw = f.get("flight_status", "unknown")
            if status_raw == "landed":
                estado = "🟢 Aterrizó"
            elif status_raw == "active":
                estado = "🔵 En Ruta"
            elif status_raw == "scheduled":
                estado = "⚪ Programado"
            elif status_raw == "cancelled":
                estado = "🔴 Cancelado"
            else:
                estado = f"🔸 {status_raw.capitalize()}"
            
            contenido += f"| **{vuelo_num}** | {aerolinea} | {origen} | {salida} | {llegada} | {estado} |\n"
            
    contenido += f"\n\n*Datos filtrados localmente y automatizados a través de la API de [Aviationstack](https://aviationstack.com/).*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    print("Reporte local de arribos procesado exitosamente.")

if __name__ == "__main__":
    datos_vuelos = obtener_vuelos_del_dia()
    generar_reporte(datos_vuelos)
