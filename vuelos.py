import os
import datetime
import requests

# Forzamos HTTP porque el plan gratuito de Aviationstack bloquea solicitudes HTTPS nativas
AVIATIONSTACK_URL = "http://aviationstack.com"
API_KEY = os.environ.get("FLIGHTAWARE_API_KEY")

def obtener_vuelos_del_dia():
    if not API_KEY:
        print("Error: No se encontró la credencial en GitHub Secrets.")
        return None

    # Parámetros directos para jalar los arribos hacia La Serena (LSC)
    params = {
        "access_key": API_KEY,
        "arr_iata": "LSC",
        "limit": 100
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
        for f in lista_vuelos:
            vuelo_num = f.get("flight", {}).get("iata") or f.get("flight", {}).get("number") or "N/A"
            aerolinea = f.get("airline", {}).get("name") or "Desconocida"
            origen = f.get("departure", {}).get("iata") or "N/A"
            
            # Capturar horas de vuelo crudas de forma segura
            salida_raw = f.get("departure", {}).get("scheduled") or "N/A"
            llegada_raw = f.get("arrival", {}).get("actual") or f.get("arrival", {}).get("scheduled") or "N/A"
            
            # Limpieza visual segura (corta las primeras 16 letras: "AAAA-MM-DD HH:MM")
            salida = salida_raw.replace("T", " ")[:16] if salida_raw != "N/A" else "N/A"
            llegada = llegada_raw.replace("T", " ")[:16] if llegada_raw != "N/A" else "N/A"
            
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
            
    contenido += f"\n\n*Datos automatizados de la jornada a través de la API de [Aviationstack](https://aviationstack.com/).*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    print("Reporte actualizado con éxito sin restricciones de zona horaria.")

if __name__ == "__main__":
    datos_vuelos = obtener_vuelos_del_dia()
    generar_reporte(datos_vuelos)
