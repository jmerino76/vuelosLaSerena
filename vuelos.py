import os
import datetime
import requests
from bs4 import BeautifulSoup

def obtener_vuelos_oficiales():
    url = "https://aeropuertolaserena.cl"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con el Aeropuerto de La Serena: {e}")
        return None

def generar_reporte(html):
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    ahora_local = datetime.datetime.now(zona_chile).strftime("%Y-%m-%d %H:%M:%S")
    
    contenido = f"# ✈️ Cronograma de Arribos Diarios - La Serena (SCSE / LSC)\n\n"
    contenido += f"Última actualización del reporte: `{ahora_local} (Hora Local Chile)`\n\n"
    contenido += "| Aerolínea | Vuelo | Origen | Fecha / Hora | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- |\n"

    if not html:
        contenido += "| - | - | No se pudo descargar la información desde el terminal oficial | - | - |\n"
    else:
        soup = BeautifulSoup(html, "html.parser")
        filas_vuelos = []
        
        for fila in soup.find_all("tr"):
            texto_fila = fila.get_text()
            if any(origen in texto_fila.upper() for origen in ["SANTIAGO", "ANTOFAGASTA", "IQUIQUE", "CALAMA"]):
                filas_vuelos.append(fila)

        if not filas_vuelos:
            contenido += "| - | - | No hay arribos comerciales registrados para las próximas horas | - | - |\n"
        else:
            vistos = set()
            for fila in filas_vuelos:
                celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
                
                # Sincronizamos las variables con los índices reales de la tabla web
                if len(celdas) >= 4:
                    vuelo_raw = celdas[1] if len(celdas) > 1 else "N/A"
                    origen = celdas[2] if len(celdas) > 2 else "N/A"
                    fecha_hora = celdas[3] if len(celdas) > 3 else "N/A"
                    estado_raw = celdas[4].upper() if len(celdas) > 4 else "PROGRAMADO"
                    
                    if not vuelo_raw or vuelo_raw == "N/A":
                        continue

                    # Identificamos la aerolínea según el número de vuelo detectado
                    if vuelo_raw.startswith("H2") or len(vuelo_raw) == 3:
                        aerolinea = "Sky Airline 🟢"
                        vuelo = f"H2 {vuelo_raw}" if not vuelo_raw.startswith("H2") else vuelo_raw
                    elif vuelo_raw.startswith("JA") or (vuelo_raw.isdigit() and 300 <= int(vuelo_raw) <= 399):
                        aerolinea = "JetSmart 🔴"
                        vuelo = f"JA {vuelo_raw}" if not vuelo_raw.startswith("JA") else vuelo_raw
                    else:
                        aerolinea = "LATAM Airlines 🔵"
                        vuelo = f"LA {vuelo_raw}" if not vuelo_raw.startswith("LA") else vuelo_raw

                    # Evitamos duplicados en la tabla Markdown
                    clave_vuelo = f"{vuelo}-{fecha_hora}"
                    if clave_vuelo in vistos:
                        continue
                    vistos.add(clave_vuelo)

                    # Clasificamos el estado visual
                    if any(x in estado_raw for x in ["ATERRIZO", "LANDED", "🟢", "FIN"]):
                        estado = "🟢 Aterrizó"
                    elif any(x in estado_raw for x in ["RUTA", "VUELO", "🔵"]):
                        estado = "🔵 En Ruta"
                    elif any(x in estado_raw for x in ["RETRASADO", "DEMORADO", "🔴"]):
                        estado = "🔴 Retrasado"
                    elif ":" in estado_raw or len(estado_raw) <= 2:
                        estado = f"⚪ Programado (Est: {estado_raw})" if ":" in estado_raw else "⚪ Programado"
                    else:
                        estado = f"⚪ {estado_raw.capitalize()}"

                    contenido += f"| {aerolinea} | **{vuelo}** | {origen} | {fecha_hora} | {estado} |\n"

    contenido += f"\n\n*Datos obtenidos directamente desde el portal oficial del [Aeropuerto La Florida de La Serena](https://aeropuertolaserena.cl).*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    print("Reporte Markdown alineado con éxito.")

if __name__ == "__main__":
    html_data = obtener_vuelos_oficiales()
    generar_reporte(html_data)
