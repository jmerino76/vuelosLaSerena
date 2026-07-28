import os
import datetime
import requests

# Cambiamos al endpoint oficial de arribos en tiempo real de Aviationstack
AVIATIONSTACK_URL = "https://aviationstack.com"
API_KEY = os.environ.get("FLIGHTAWARE_API_KEY") # Mantenemos el nombre de la variable de GitHub para no cambiar el archivo YML

def obtener_vuelos_del_dia():
    if not API_KEY:
        print("Error: No se encontró la credencial de la API en GitHub Secrets.")
        return None

    # Parámetros oficiales de Aviationstack estructurados para La Serena (LSC)
    params = {
        "access_key": API_KEY,
        "arr_iata": "LSC",      # Código IATA de La Serena
        "limit": 100            # Límite amplio para capturar todos los vuelos de la jornada
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

    lista_vuelos = datos.get("data", []) if datos else []

    if not lista_vuelos:
        contenido += "| - | - | No se encontraron vuelos programados para hoy | - | - | - |\n"
    else:
        # Filtrar para asegurarnos de que la API solo nos devuelva los vuelos del día de hoy
        fecha_hoy_chile = datetime.datetime.now(zona_chile).strftime("%Y-%m-%d")
        vuelos_hoy = [v for v in lista_vuelos if v.get("flight_date") == fecha_hoy_chile]

        if not vuelos_hoy:
            contenido += "| - | - | No hay operaciones comerciales registradas para la fecha de hoy | - | - | - |\n"
        else:
            # Ordenar los vuelos por la hora programada de aterrizaje
            vuelos_ordenados = sorted(
                vuelos_hoy,
                key=lambda x: x.get("arrival", {}).get("scheduled") or ""
            )

            for f in vuelos_ordenados:
                vuelo_num = f.get("flight", {}).get("iata") or f.get("flight", {}).get("number") or "N/A"
                aerolinea = f.get("airline", {}).get("name") or "Desconocida"
                origen = f.get("departure", {}).get("iata") or "N/A"
                
                # Extraer tiempos de salida y llegada
                salida_t = f.get("departure", {}).get("scheduled") or "N/A"
                llegada_t = f.get("arrival", {}).get("actual") or f.get("arrival", {}).get("scheduled") or "N/A"
                
                # Limpieza de cadenas de texto ISO (sacar desvíos de zona horaria)
                salida = salida_t.replace("T", " ").split("+")[0][:16]
                llegada = llegada_t.replace("T", " ").split("+")[0][:16]
                
                # Traducir los estados nativos de Aviationstack
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
                
    contenido += f"\n\n*Datos diarios automatizados a través de la API de [Aviationstack](https://aviationstack.com).*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    print("Reporte diario generado exitosamente mediante Aviationstack.")

if __name__ == "__main__":
    datos_vuelos = obtener_vuelos_del_dia()
    generar_reporte(datos_vuelos)
