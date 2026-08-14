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

def enviar_a_google_sheets(llegadas, ahora_local, total_hoy):
    google_url = os.environ.get("GOOGLE_SHEETS_URL")
    if not google_url:
        print("Aviso: No se encontró GOOGLE_SHEETS_URL. Saltando vuelco a Google.")
        return

    vuelos_payload = []
    for v in llegadas:
        vuelos_payload.append({
            "logo_url": "https://google.com",
            "aerolinea_nombre": v["aerolinea_raw_text"],
            "vuelo": v["vuelo"],
            "origen": v["origen"],
            "fecha": v["fecha"],
            "hora": v["hora"],
            "cinta": v["cinta"].replace("🧳 ", ""),
            "estado": v["estado"]
        })

    paquete_completo = {
        "metadata": {
            "titulo": "✈️ Cronograma de Arribos Diarios - La Serena (SCSE / LSC)",
            "actualizacion": f"Última actualización del reporte: {ahora_local} (Hora Local Chile)",
            "total_vuelos_hoy": total_hoy
        },
        "vuelos": vuelos_payload
    }

    try:
        response = requests.post(google_url, json=paquete_completo, timeout=15)
        if response.status_code == 200:
            print("¡Formato espejo del README volcado con éxito en Google Sheets!")
        else:
            print(f"Google Apps Script respondió con código {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error al enviar datos a Google Sheets: {e}")

def generar_reporte(html):
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    ahora_dt = datetime.datetime.now(zona_chile)
    ahora_local = ahora_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    hora_actual_cl = ahora_dt.hour
    fecha_hoy_cl = ahora_dt.strftime("%d-%m-%Y")
    
    contenido = f"# ✈️ Cronograma de Arribos Diarios - La Serena (SCSE / LSC)\n\n"
    
    llegadas = []
    llegadas_ordenadas = []
    vistos = set()

    if html:
        soup = BeautifulSoup(html, "html.parser")
        
        for tabla in soup.find_all("table"):
            encabezado_texto = tabla.get_text().upper()
            if "EMBARQUE" in encabezado_texto or "PUERTA" in encabezado_texto:
                continue
                
            for fila in tabla.find_all("tr"):
                celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
                
                if len(celdas) >= 6:
                    vuelo_raw = celdas[1]
                    origen_raw = celdas[2]
                    fecha = celdas[3]
                    hora = celdas[4]
                    cinta_raw = celdas[5]
                    estado_raw = celdas[-1].upper() if len(celdas) >= 6 else "PROGRAMADO"

                    digitos = "".join(filter(str.isdigit, vuelo_raw))
                    if not digitos or "TAXIS" in vuelo_raw.upper() or len(vuelo_raw) > 10:
                        continue

                    if ":" in cinta_raw:
                        continue

                    origen = origen_raw.upper()
                    if "SERENA" in origen:
                        continue

                    img_tag = fila.find("img")
                    src_lower = img_tag["src"].lower() if img_tag and img_tag.get("src") else ""
                    alt_text = img_tag["alt"].strip() if img_tag and img_tag.get("alt") else ""
                    
                    is_sky = "sky" in src_lower or "h2" in vuelo_raw.lower() or digitos in ["1720", "1723", "1742"]
                    is_jetsmart = "smart" in src_lower or "ja" in vuelo_raw.lower() or digitos == "321"
                    is_latam = "atam" in src_lower or "la" in vuelo_raw.lower()
                    
                    if is_sky:
                        aerolinea = '<img src="SKY.jpg" width="70" alt="Sky">'
                        vuelo_num = f"H2 {digitos}"
                        aerolinea_raw_text = "Sky"
                    elif is_jetsmart:
                        aerolinea = '<img src="JetSmart.jpg" width="70" alt="JetSmart">'
                        vuelo_num = f"JA {digitos}"
                        aerolinea_raw_text = "JetSmart"
                    elif is_latam:
                        aerolinea = '<img src="LATAM.jpg" width="70" alt="LATAM">'
                        vuelo_num = f"LA {digitos}"
                        aerolinea_raw_text = "LATAM"
                    else:
                        aerolinea_nombre = alt_text if alt_text else "Otra Aerolínea"
                        aerolinea = f"**{aerolinea_nombre}**"
                        vuelo_num = vuelo_raw.upper()
                        aerolinea_raw_text = aerolinea_nombre

                    cinta = f"🧳 {cinta_raw}" if (cinta_raw and cinta_raw != "-") else "Por confirmar"

                    if any(x in estado_raw for x in ["ATERRIZO", "LANDED", "FIN"]):
                        estado = "🟢 Aterrizó"
                    elif any(x in estado_raw for x in ["CANCELADO", "CANCEL", "🔴 CANCELADO"]):
                        estado = "❌ Cancelado"
                    elif any(x in estado_raw for x in ["RETRASADO", "DEMORADO", "🔴"]):
                        estado = "🔴 Retrasado"
                    else:
                        estado = "⚪ Programado"

                    datos_vuelo = {
                        "aerolinea": aerolinea,
                        "aerolinea_raw_text": aerolinea_raw_text,
                        "vuelo": vuelo_num,
                        "origen": origen,
                        "fecha": fecha,
                        "hora": hora,
                        "cinta": cinta,
                        "estado": estado,
                        "sort_fecha": fecha,
                        "sort_hora": hora
                    }

                    clave_vuelo = f"{vuelo_num}-{fecha}-{hora}"
                    if clave_vuelo in vistos: continue
                    vistos.add(clave_vuelo)
                    llegadas.append(datos_vuelo)

    # 📊 FILTRO Y CONTADOR CRONOLÓGICO CONDICIONAL (05:00 a 08:59 AM Chile)
    if 5 <= hora_actual_cl <= 8:
        vuelos_hoy = [v for v in llegadas if v["fecha"] == fecha_hoy_cl]
        total_vuelos_hoy = len(vuelos_hoy)
        resumen_estadistico = f"### 📊 Resumen Estadístico Diario:\n* **Vuelos totales programados para hoy ({fecha_hoy_cl}):** `{total_vuelos_hoy}`\n\n"
    else:
        total_vuelos_hoy = "No disponible fuera de horario"
        resumen_estadistico = ""

    contenido += resumen_estadistico  
    contenido += f"Última actualización del reporte: `{ahora_local} (Hora Local Chile)`\n\n"
    contenido += "| Aerolínea | Vuelo | Origen | Fecha | Hora Real/Est. | Cinta | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    
    if not llegadas:
        contenido += "| - | - | No hay arribos registrados en este momento | - | - | - | - |\n"
    else:
        llegadas_ordenadas = sorted(
            llegadas,
            key=lambda x: ("-".join(x["sort_fecha"].split("-")[::-1]), x["sort_hora"])
        )

        for v in llegadas_ordenadas:
            contenido += f"| {v['aerolinea']} | **{v['vuelo']}** | {v['origen']} | {v['fecha']} | {v['hora']} | {v['cinta']} | {v['estado']} |\n"

    contenido += f"\n\n*Datos de arribos exclusivos ordenados cronológicamente y validados desde el portal oficial del [Aeropuerto La Florida de La Serena](https://aeropuertolaserena.cl).*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
        
    os.makedirs("historial", exist_ok=True)
    nombre_historial = ahora_dt.strftime("historial/arribos_%Y-%m-%d_%H-%M.md")
    with open(nombre_historial, "w", encoding="utf-8") as archivo_historial:
        archivo_historial.write(contenido)
    print(f"Copia histórica guardada en: {nombre_historial}")
        
    enviar_a_google_sheets(llegadas_ordenadas, ahora_local, total_vuelos_hoy)

if __name__ == "__main__":
    html_data = obtener_vuelos_oficiales()
    generar_reporte(html_data)
