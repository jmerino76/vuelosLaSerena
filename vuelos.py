import os
import datetime
import requests
from bs4 import BeautifulSoup

def obtener_vuelos_oficiales():
    # Conectamos directo con la base pública del terminal de La Serena
    url = "https://www.aeropuertolaserena.cl/"
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
        
        # El sitio oficial organiza los vuelos dentro de elementos de tipo lista o tablas estructuradas
        # Buscamos las filas correspondientes a "Próximas Llegadas"
        filas_vuelos = []
        
        # Buscamos todas las tablas o filas que tengan datos de aerolíneas
        for fila in soup.find_all("tr"):
            texto_fila = fila.get_text()
            # Filtramos solo las filas que contengan información relevante de llegadas
            if any(origen in texto_fila.upper() for origen in ["SANTIAGO", "ANTOFAGASTA", "IQUIQUE", "CALAMA"]):
                filas_vuelos.append(fila)

        if not filas_vuelos:
            contenido += "| - | - | No hay arribos comerciales registrados para las próximas horas | - | - |\n"
        else:
            vistos = set()
            for fila in filas_vuelos:
                celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
                
                if len(celdas) >= 5:
                    aerolinea = celdas[0]
                    vuelo = celdas[1]
                    origen = celdas[2]
                    fecha_hora = f"{celdas[3]} {celdas[4]}"
                    estado_raw = celdas[5] if len(celdas) > 5 else "PROGRAMADO"
                    
                    # Evitamos duplicaciones en la lectura de la página web
                    clave_vuelo = f"{vuelo}-{celdas[4]}"
                    if clave_vuelo in vistos:
                        continue
                    vistos.add(clave_vuelo)

                    # Iconografía amigable según estado real
                    if "LANDED" in estado_raw.upper() or "ATERRIZÓ" in estado_raw.upper():
                        estado = "🟢 Aterrizó"
                    elif "EN RUTA" in estado_raw.upper() or "EN VUELO" in estado_raw.upper():
                        estado = "🔵 En Ruta"
                    elif "RETRASADO" in estado_raw.upper() or "DEMORADO" in estado_raw.upper():
                        estado = "🔴 Retrasado"
                    else:
                        estado = f"⚪ {estado_raw.capitalize()}"

                    contenido += f"| {aerolinea} | **{vuelo}** | {origen} | {fecha_hora} | {estado} |\n"

    contenido += f"\n\n*Datos obtenidos directamente desde el portal oficial del [Aeropuerto La Florida de La Serena](https://www.aeropuertolaserena.cl/).*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    print("Reporte Markdown generado con éxito vía conexión oficial.")

if __name__ == "__main__":
    html_data = obtener_vuelos_oficiales()
    generar_reporte(html_data)
