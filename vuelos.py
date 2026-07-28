import os
import datetime
import requests
from bs4 import BeautifulSoup

def obtener_vuelos_scraping():
    # Consultamos la vista de arribos públicos de Flightera para el aeropuerto SCSE
    url = "https://flightera.net"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con la fuente de vuelos: {e}")
        return None

def generar_reporte(html):
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    ahora_local = datetime.datetime.now(zona_chile).strftime("%Y-%m-%d %H:%M:%S")
    
    contenido = f"# ✈️ Cronograma de Arribos Diarios - La Serena (SCSE / LSC)\n\n"
    contenido += f"Última actualización del reporte: `{ahora_local} (Hora Local Chile)`\n\n"
    contenido += "| Horario | Vuelo | Origen | Aerolínea / Avión | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- |\n"

    if not html:
        contenido += "| - | - | No se pudo descargar la información de vuelos | - | - |\n"
    else:
        soup = BeautifulSoup(html, "html.parser")
        # Localizamos la tabla principal de vuelos dentro del HTML público
        tabla = soup.find("table")
        
        if not tabla:
            contenido += "| - | - | No se encontraron registros de vuelos en este bloque horario | - | - |\n"
        else:
            filas = tabla.find_all("tr")[1:] # Omitimos el encabezado de la tabla original
            vuelos_encontrados = 0
            
            for fila in filas:
                celdas = fila.find_all("td")
                if len(celdas) >= 5:
                    # Extracción limpia de columnas basada en la estructura del radar
                    horario = celdas[0].get_text(strip=True)[:16]
                    vuelo = celdas[1].get_text(strip=True)
                    origen = celdas[2].get_text(strip=True)
                    aerolinea = celdas[3].get_text(strip=True)
                    estado_raw = celdas[4].get_text(strip=True)
                    
                    # Formatear iconos amigables para el usuario
                    if "Aterrizó" in estado_raw or "Landed" in estado_raw or "early" in estado_raw or "late" in estado_raw:
                        estado = "🟢 Aterrizó / A tiempo"
                    elif "En Ruta" in estado_raw or "En curso" in estado_raw:
                        estado = "🔵 En Ruta"
                    elif "Cancelado" in estado_raw or "Delayed" in estado_raw:
                        estado = "🔴 Demorado / Cancelado"
                    else:
                        estado = f"⚪ {estado_raw}"
                        
                    contenido += f"| {horario} | **{vuelo}** | {origen} | {aerolinea} | {estado} |\n"
                    vuelos_encontrados += 1
            
            if vuelos_encontrados == 0:
                contenido += "| - | - | No hay vuelos programados para las próximas horas | - | - |\n"
                
    contenido += f"\n\n*Datos en tiempo real extraídos automáticamente de radares de navegación aérea abiertos.*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    print("Reporte Markdown generado con éxito vía Web Scraping.")

if __name__ == "__main__":
    html_data = obtener_vuelos_scraping()
    generar_reporte(html_data)
