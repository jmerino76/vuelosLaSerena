import os
import datetime
import requests

# Forzamos HTTP plano porque el plan gratuito de Aviationstack bloquea solicitudes HTTPS nativas
AVIATIONSTACK_URL = "http://aviationstack.com"
API_KEY = os.environ.get("FLIGHTAWARE_API_KEY")

def obtener_vuelos_del_dia():
    if not API_KEY:
        print("Error: No se encontró la credencial en GitHub Secrets.")
        return None

    # Parámetros directos para jalar los movimientos hacia La Serena (LSC)
    params = {
        "access_key": API_KEY,
        "arr_iata": "LSC",
        "limit": 50
    }
    
    try:
        response = requests.get(AVIATIONSTACK_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con la API de Aviationstack: {e}")
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
        contenido += "| - | - | No se encontraron vuelos disponibles en los servidores | - | - | - |\n"
    else:
        # Ordenar cronológicamente por hora de arribo programado
        vuelos_ordenados = sorted(
            lista_vuelos,
            key=lambda x: x.get("arrival", {}).get("scheduled") or ""
        )

        for f in vuelos_ordenados:
            vuelo_num = f.get("flight", {}).get("iata") or f.get("flight", {}).get("number") or "N/A"
            aerolinea = f.get("airline", {}).get("name") or "Desconocida"
            origen = f.get("departure", {}).get("iata") or "N/A"
            
            # Capturar horas de vuelo
            salida_t = f.get("departure", {}).get("scheduled") or "N/A"
            llegada_t = f.get("arrival", {}).get("actual") or f.get("arrival", {}).get("scheduled") or "N/A"
            
            # Limpiar el formato ISO separando la fecha y la hora
            salida = salida_t.replace("T", " ").split("+")[0][:16]
            llegada = llegada_t.replace("T", " ").split("+")[0][:16]
            
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
            
    contenido += f"\n\n*Datos automatizados de la jornada a través de la API de [Aviationstack](https://aviationstack.com/).*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    print("Reporte actualizado con éxito sin restricciones de zona horaria.")

if __name__ == "__main__":
    datos_vuelos = obtener_vuelos_del_dia()
    generar_reporte(datos_vuelos)
