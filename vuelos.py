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

    datos_comprimidos = []
    for v in llegadas:
        # Asignación limpia y directa de texto y logotipos para Google Sheets sin usar split()
        if "Sky" in v["aerolinea_raw_text"] or "H2" in v["vuelo"]:
            logo_url = "https://skyairline.com"
            linea_txt = "Sky Airline"
        elif "JetSmart" in v["aerolinea_raw_text"] or "JA" in v["vuelo"]:
            logo_url = "https://jetsmart.com"
            linea_txt = "JetSmart"
        else:
            logo_url = "https://latamairlines.com"
            linea_txt = "LATAM Airlines"

        datos_comprimidos.append({
            "logo_formula": f'=IMAGE("{logo_url}")',
            "aerolinea_texto": linea_txt,
            "vuelo": v["vuelo"],
            "origen": v["origen"],
            "fecha": v["fecha"],
            "hora": v["hora"],
            "cinta": v["cinta"].replace("🧳 ", ""),
            "estado": v["estado"],
            "actualizado": ahora_local
        })

    try:
        # Transmisión segura mediante método POST
        response = requests.post(google_url, json=datos_comprimidos, timeout=15)
        if response.status_code == 200:
            print("¡Datos estructurados volcados con éxito en Google Sheets!")
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
    vistos = set()

    if html:
        soup = BeautifulSoup(html, "html.parser")
        
        for fila in soup.find_all("tr"):
            celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
            
            if len(celdas) >= 6:
                vuelo_raw = celdas
                origen = celdas.upper()
                fecha = celdas
                hora = celdas
                cinta_raw = celdas
                estado_raw = celdas.upper() if len(celdas) > 6 else "PROGRAMADO"

                digitos = "".join(filter(str.isdigit, vuelo_raw))
                if not digitos or "TAXIS" in vuelo_raw.upper() or len(vuelo_raw) > 10:
                    continue

                vuelo_num_int = int(digitos)

                # Filtro definitivo contra despegues (salidas)
                if ":" in cinta_raw:
                    continue

                img_tag = fila.find("img")
                src_lower = img_tag["src"].lower() if img_tag and img_tag.get("src") else ""
                
                is_sky = "sky" in src_lower or "h2" in vuelo_raw.lower()
                is_jetsmart = "smart" in src_lower or "ja" in vuelo_raw.lower() or (300 <= vuelo_num_int <= 399)
                
                # Resguardamos una marca de texto cruda limpia para la función de Google Sheets
                aerolinea_raw_text = "LATAM"
                if is_sky:
                    if vuelo_num_int % 2 == 0: continue
                    aerolinea = '<img src="https://skyairline.com" width="16" height="16"> **Sky**'
                    vuelo_num = f"H2 {digitos}"
                    aerolinea_raw_text = "Sky"
                elif is_jetsmart:
                    if vuelo_num_int % 2 != 0: continue
                    aerolinea = '<img src="https://jetsmart.com" width="16" height="16"> **JetSmart**'
                    vuelo_num = f"JA {digitos}"
                    aerolinea_raw_text = "JetSmart"
                else:
                    if vuelo_num_int % 2 != 0: continue
                    aerolinea = '<img src="https://latamairlines.com" width="16" height="16"> **LATAM**'
                    vuelo_num = f"LA {digitos}"
                    aerolinea_raw_text = "LATAM"

                cinta = f"🧳 {cinta_raw}" if (cinta_raw and cinta_raw != "-") else "Por confirmar"

                if any(x in estado_raw for x in ["ATERRIZO", "LANDED", "🟢", "FIN"]):
                    estado = "🟢 Aterrizó"
                elif any(x in estado_raw for x in ["RETRASADO", "DEMORADO", "🔴"]):
                    estado = "🔴 Retrasado"
                else:
                    estado = "⚪ Programado"

                datos_vuelo = {
                    "aerolinea": aerolinea,
                    "aerolinea_raw_text": aerolinea_raw_text, # Pasamos la marca limpia
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
        
    # Desparramamos los datos ordenados limpios a Google
    enviar_a_google_sheets(llegadas_ordenadas, ahora_local)

if __name__ == "__main__":
    html_data = obtener_vuelos_oficiales()
    generar_reporte(html_data)
