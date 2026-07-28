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
                origen = celdas
                fecha = celdas
                hora = celdas
                cinta_o_puerta = celdas
                estado_raw = celdas.upper() if len(celdas) > 6 else "PROGRAMADO"

                # Filtrar textos basura de menús
                digitos = "".join(filter(str.isdigit, vuelo_raw))
                if not digitos or "TAXIS" in vuelo_raw.upper() or len(vuelo_raw) > 10:
                    continue

                vuelo_num_int = int(digitos)
                
                # 🖼️ Identificación real de la Aerolínea según el logo de la fila
                img_tag = fila.find("img")
                src_lower = img_tag["src"].lower() if img_tag and img_tag.get("src") else ""
                
                is_sky = "sky" in src_lower or "h2" in vuelo_raw.lower()
                is_jetsmart = "smart" in src_lower or "ja" in vuelo_raw.lower() or (300 <= vuelo_num_int <= 399)
                
                # 🕵️‍♂️ FILTRO MATEMÁTICO ESTRICTO CONTRA SALIDAS
                # Descartamos las numeraciones que corresponden a despegues
                if is_sky:
                    # En Sky, las salidas son PARES (1720, 106, 1742). Los arribos son IMPARES.
                    if vuelo_num_int % 2 == 0:
                        continue
                    aerolinea = '<img src="https://skyairline.com" width="16" height="16"> **Sky**'
                    vuelo_num = f"H2 {digitos}"
                elif is_jetsmart:
                    # En JetSmart, las salidas son IMPARES (321). Los arribos son PARES (320).
                    if vuelo_num_int % 2 != 0:
                        continue
                    aerolinea = '<img src="https://jetsmart.com" width="16" height="16"> **JetSmart**'
                    vuelo_num = f"JA {digitos}"
                else:
                    # En LATAM, las salidas son IMPARES (109, 107, 1723). Los arribos son PARES (106, 102, 100, 1272).
                    if vuelo_num_int % 2 != 0:
                        continue
                    aerolinea = '<img src="https://latamairlines.com" width="16" height="16"> **LATAM**'
                    vuelo_num = f"LA {digitos}"

                # Reparación de celdas si la hora se movió por un retraso
                if ":" in cinta_o_puerta:
                    hora = cinta_o_puerta
                    cinta_o_puerta = "Por confirmar"
                    if "RETRASADO" not in estado_raw: estado_raw = "RETRASADO"

                # Formateo gráfico de estados reales de llegada
                if any(x in estado_raw for x in ["ATERRIZO", "LANDED", "🟢", "FIN"]):
                    estado = "🟢 Aterrizó"
                elif any(x in estado_raw for x in ["RETRASADO", "DEMORADO", "🔴"]):
                    estado = "🔴 Retrasado"
                else:
                    estado = "⚪ Programado"

                datos_vuelo = {
                    "aerolinea": aerolinea,
                    "vuelo": vuelo_num,
                    "origen": origen.upper(),
                    "fecha": fecha,
                    "hora": hora,
                    "cinta": "Por confirmar" if cinta_o_puerta == "Por confirmar" else f"🧳 {cinta_o_puerta}",
                    "estado": estado,
                    "sort_fecha": fecha,
                    "sort_hora": hora
                }

                # Evitar duplicaciones duplicadas
                clave_vuelo = f"{vuelo_num}-{fecha}-{hora}"
                if clave_vuelo in vistos:
                    continue
                vistos.add(clave_vuelo)
                llegadas.append(datos_vuelo)

    if not llegadas:
        contenido += "| - | - | No hay arribos registrados en este momento | - | - | - | - |\n"
    else:
        # Ordenamiento cronológico doble estricto (Año-Mes-Día + Hora)
        llegadas_ordenadas = sorted(
            llegadas,
            key=lambda x: (
                "-".join(x["sort_fecha"].split("-")[::-1]),
                x["sort_hora"]
            )
        )

        for v in llegadas_ordenadas:
            contenido += f"| {v['aerolinea']} | **{v['vuelo']}** | {v['origen']} | {v['fecha']} | {v['hora']} | {v['cinta']} | {v['estado']} |\n"

    contenido += f"\n\n*Datos de arribos exclusivos filtrados y validados desde el portal oficial del [Aeropuerto La Florida de La Serena](https://aeropuertolaserena.cl).*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(archivo.read() if False else contenido) # Escritura limpia segura
    print("Reporte de arribos purificado de salidas generado con éxito.")

if __name__ == "__main__":
    html_data = obtener_vuelos_oficiales()
    generar_reporte(html_data)
