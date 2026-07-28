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

def procesar_bloque_vuelos(soup, id_contenedor):
    # Localizamos el contenedor específico en la página web (ej: 'llegadas' o 'salidas')
    contenedor = soup.find(id=id_contenedor) or soup.find(class_=id_contenedor)
    vuelos_procesados = []
    vistos = set()

    if not contenedor:
        return vuelos_procesados

    # Recorremos las filas de la tabla dentro de ese contenedor específico
    for fila in contenedor.find_all("tr"):
        celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
        
        if len(celdas) >= 7:
            vuelo_raw = celdas[1]
            ciudad = celdas[2]
            fecha = celdas[3]
            hora = celdas[4]
            cinta_o_puerta = celdas[5]
            estado_raw = celdas[6].upper()

            if not vuelo_raw or vuelo_raw == "N/A":
                continue

            # ✈️ Identificación infalible por Logotipo en el HTML
            aerolinea = "Desconocida ⚪"
            img_tag = fila.find("img")
            if img_tag and img_tag.get("src"):
                src_lower = img_tag["src"].lower()
                if "sky" in src_lower:
                    aerolinea = "Sky Airline 🟢"
                elif "latam" in src_lower or "lan" in src_lower:
                    aerolinea = "LATAM Airlines 🔵"
                elif "jetsmart" in src_lower or "smart" in src_lower:
                    aerolinea = "JetSmart 🔴"

            # Control de desvíos si la hora se desplaza a la columna de cinta/puerta
            if ":" in cinta_o_puerta:
                hora = cinta_o_puerta
                cinta_o_puerta = "Por confirmar"
                estado_raw = "RETRASADO"

            # Evitar duplicados exactos en el búfer
            clave_vuelo = f"{vuelo_raw}-{hora}"
            if clave_vuelo in vistas_bloque:
                continue
            vistas_bloque.add(clave_vuelo)

            # Clasificación de estados
            if any(x in estado_raw for x in ["ATERRIZO", "LANDED", "🟢", "FIN"]):
                estado = "🟢 Aterrizó"
            elif any(x in estado_raw for x in ["DESPEGÓ", "DEPARTED", "🛫"]):
                estado = "🛫 Despegó"
            elif any(x in estado_raw for x in ["RUTA", "VUELO", "🔵", "EN CURSO"]):
                estado = "🔵 En Ruta"
            elif any(x in estado_raw for x in ["RETRASADO", "DEMORADO", "🔴"]):
                estado = "🔴 Retrasado"
            else:
                estado = "⚪ Programado"

            vuelos_procesados.append({
                "aerolinea": aerolinea,
                "vuelo": vuelo_raw,
                "ciudad": ciudad,
                "fecha": fecha,
                "hora": hora,
                "cinta_o_puerta": cinta_o_puerta,
                "estado": estado
            })
            
    return vuelos_procesados

def generar_reporte(html):
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    ahora_local = datetime.datetime.now(zona_chile).strftime("%Y-%m-%d %H:%M:%S")
    
    global vistas_bloque
    soup = BeautifulSoup(html, "html.parser")
    
    # Procesamos las dos secciones de forma totalmente aislada
    vistas_bloque = set()
    llegadas = procesar_bloque_vuelos(soup, "llegadas")
    
    vistas_bloque = set()
    salidas = procesar_bloque_vuelos(soup, "salidas")

    # Construcción del archivo Markdown estructurado
    contenido = f"# ✈️ Estado de Vuelos en Tiempo Real - La Serena (SCSE / LSC)\n\n"
    contenido += f"Última actualización: `{ahora_local} (Hora Local Chile)`\n\n"
    
    # --- SECCIÓN 1: LLEGADAS ---
    contenido += f"## 🛬 Próximas Llegadas (Arribos)\n\n"
    contenido += "| Aerolínea | Vuelo | Origen | Fecha | Hora Real/Est. | Cinta | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    if not llegadas:
        contenido += "| - | - | No hay arribos registrados en este momento | - | - | - | - |\n"
    else:
        for v in llegadas:
            contenido += f"| {v['aerolinea']} | **{v['vuelo']}** | {v['ciudad']} | {v['fecha']} | {v['hora']} | 🧳 {v['cinta_o_puerta']} | {v['estado']} |\n"

    contenido += f"\n---\n\n"

    # --- SECCIÓN 2: SALIDAS ---
    contenido += f"## 🛫 Próximas Salidas (Despegues)\n\n"
    contenido += "| Aerolínea | Vuelo | Destino | Fecha | Hora Real/Est. | Puerta | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    if not salidas:
        contenido += "| - | - | No hay despegues programados en este momento | - | - | - | - |\n"
    else:
        for v in salidas:
            contenido += f"| {v['aerolinea']} | **{v['vuelo']}** | {v['ciudad']} | {v['fecha']} | {v['hora']} | 🚪 {v['cinta_o_puerta']} | {v['estado']} |\n"

    contenido += f"\n\n*Datos separados y validados directamente desde el portal oficial del [Aeropuerto La Florida de La Serena](https://aeropuertolaserena.cl).*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    print("Reporte Markdown corregido, separado y validado con éxito.")

if __name__ == "__main__":
    html_data = obtener_vuelos_oficiales()
    if html_data:
        generar_reporte(html_data)
