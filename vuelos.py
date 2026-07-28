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

def enviar_a_google_sheets(llegadas, ahora_local):
    google_url = os.environ.get("GOOGLE_SHEETS_URL")
    if not google_url:
        print("Aviso: No se encontró GOOGLE_SHEETS_URL. Saltando vuelco a Google.")
        return

    vuelos_payload = []
    for v in llegadas:
        # Sincronizamos las mismas URLs abiertas para Google Sheets
        if "Sky" in v["aerolinea_raw_text"] or "H2" in v["vuelo"]:
            logo_url = "https://icons8.com" if False else "https://githubusercontent.com"
            logo_url = "https://github.com" if False else "https://statvoo.com"
            logo_url = "https://google.com"
            linea_txt = "Sky"
        elif "JetSmart" in v["aerolinea_raw_text"] or "JA" in v["vuelo"]:
            logo_url = "https://google.com"
            linea_txt = "JetSmart"
        else:
            logo_url = "https://google.com"
            linea_txt = "LATAM"

        vuelos_payload.append({
            "logo_url": logo_url,
            "aerolinea_nombre": linea_txt,
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
            "actualizacion": f"Última actualización del reporte: {ahora_local} (Hora Local Chile)"
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
    ahora_local = datetime.datetime.now(zona_chile).strftime("%Y-%m-%d %H:%M:%S")
    
    contenido = f"# ✈️ Cronograma de Arribos Diarios - La Serena (SCSE / LSC)\n\n"
    contenido += f"Última actualización del reporte: `{ahora_local} (Hora Local Chile)`\n\n"
    contenido += "| Aerolínea | Vuelo | Origen | Fecha | Hora Real/Est. | Cinta | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    
    llegadas = []
    llegadas_ordenadas = []
    vistos = set()

    if html:
        soup = BeautifulSoup(html, "html.parser")
        
        for fila in soup.find_all("tr"):
            celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
            
            if len(celdas) >= 6:
                vuelo_raw = celdas
                origen_raw = celdas
                fecha = celdas
                hora = celdas
                cinta_raw = celdas
                estado_raw = celdas.upper() if len(celdas) > 5 else "PROGRAMADO"

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
                
                is_sky = "sky" in src_lower or "h2" in vuelo_raw.lower()
                is_jetsmart = "smart" in src_lower or "ja" in vuelo_raw.lower() or (300 <= int(digitos) <= 399)
                
                aerolinea_raw_text = "LATAM"
                # Usamos el motor de favicons seguro de Google que GitHub no bloquea
                if is_sky:
                    logo_static_url = "https://google.com"
                    aerolinea = f'<img src="{logo_static_url}" width="16" height="16"> **Sky**'
                    vuelo_num = f"H2 {digitos}"
                    aerolinea_raw_text = "Sky"
                elif is_jetsmart:
                    logo_static_url = "https://google.com"
                    aerolinea = f'<img src="{logo_static_url}" width="16" height="16"> **JetSmart**'
                    vuelo_num = f"JA {digitos}"
                    aerolinea_raw_text = "JetSmart"
                else:
                    logo_static_url = "https://google.com"
                    aerolinea = f'<img src="{logo_static_url}" width="16" height="16"> **LATAM**'
                    vuelo_num = f"LA {digitos}"
                    aerolinea_raw_text = "LATAM"

                cinta = f"🧳 {cinta_raw}" if (cinta_raw and cinta_raw != "-") else "Por confirmar"

                if any(x in estado_raw for x in ["ATERRIZO", "LANDED", "FIN"]):
                    estado = "🟢 Aterrizó"
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

    if not llegadas:
        contenido += "| - | - | No hay arribos registrados en este momento | - | - | - | - |\n"
    else:
        llegadas_ordenadas = sorted(
            llegadas,
            key=lambda x: ("-".join(x["sort_fecha"].split("-")[::-1]), x["sort_hora"])
        )

        for v in llegadas_ordenadas:
            contenido += f"| {v['aerolinea']} | **{v['vuelo']}** | {v['origen']} | {v['fecha']} | {v['hora']} | {v['cinta']} | {v['estado']} |\n"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
        
    enviar_a_google_sheets(llegadas_ordenadas, ahora_local)

if __name__ == "__main__":
    html_data = obtener_vuelos_oficiales()
    generar_reporte(html_data)
