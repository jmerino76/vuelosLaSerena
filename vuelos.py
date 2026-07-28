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
                origen_raw = celdas
                fecha = celdas
                hora = celdas
                cinta_o_puerta = celdas
                estado_raw = celdas.upper() if len(celdas) > 6 else "PROGRAMADO"

                # Filtrar textos basura o menús comerciales del aeropuerto
                digitos = "".join(filter(str.isdigit, vuelo_raw))
                if not digitos or "TAXIS" in vuelo_raw.upper() or len(vuelo_raw) > 10:
                    continue

                # 🕵️‍♂️ FILTRO GEOGRÁFICO ESTRICTO:
                # Si el origen es "LA SERENA", significa que el vuelo está saliendo.
                # Solo aceptamos ciudades que apunten a un arribo hacia LSC.
                origen = origen_raw.upper()
                if "LA SERENA" in origen or "SERENA" in origen:
                    continue
                
                # Forzar origen correcto si la celda venía vacía o con texto erróneo
                if not any(x in origen for x in ["SANTIAGO", "ANTOFAGASTA", "IQUIQUE", "CALAMA"]):
                    continue

                # 🖼️ Identificación real de Aerolínea basada en las imágenes de la fila
                img_tag = fila.find("img")
                src_lower = img_tag["src"].lower() if img_tag and img_tag.get("src") else ""
                
                if "sky" in src_lower or "h2" in vuelo_raw.lower():
                    aerolinea = '<img src="https://skyairline.com" width="16" height="16"> **Sky**'
                    vuelo_num = f"H2 {digitos}"
                elif "smart" in src_lower or "ja" in vuelo_raw.lower():
                    aerolinea = '<img src="https://jetsmart.com" width="16" height="16"> **JetSmart**'
                    vuelo_num = f"JA {digitos}"
                else:
                    aerolinea = '<img src="https://latamairlines.com" width="16" height="16"> **LATAM**'
                    vuelo_num = f"LA {digitos}"

                # Reparación de celdas si la hora se desplazó por un retraso en la pantalla
                if ":" in cinta_o_puerta:
                    hora = cinta_o_puerta
                    cinta_o_puerta = "Por confirmar"
                    if "RETRASADO" not in estado_raw: estado_raw = "RETRASADO"

                # Formateo gráfico de los estados de llegada
                if any(x in estado_raw for x in ["ATERRIZO", "LANDED", "🟢", "FIN"]):
                    estado = "🟢 Aterrizó"
                elif any(x in estado_raw for x in ["RETRASADO", "DEMORADO", "🔴"]):
                    estado = "🔴 Retrasado"
                else:
                    estado = "⚪ Programado"

                datos_vuelo = {
                    "aerolinea": aerolinea,
                    "vuelo": vuelo_num,
                    "origen": origen,
                    "fecha": fecha,
                    "hora": hora,
                    "cinta": "Por confirmar" if cinta_o_puerta == "Por confirmar" else f"🧳 {cinta_o_puerta}",
                    "estado": estado,
                    "sort_fecha": fecha,
                    "sort_hora": hora
                }

                # Evitar registros duplicados exactos en el Markdown
                clave_vuelo = f"{vuelo_num}-{fecha}-{hora}"
                if clave_vuelo in vistos:
                    continue
                vistos.add(clave_vuelo)
                llegadas.append(datos_vuelo)

    if not llegadas:
        contenido += "| - | - | No hay arribos registrados en este momento | - | - | - | - |\n"
    else:
        # Ordenamiento cronológico doble estricto (Año-Mes-Día + Hora de menor a mayor)
        llegadas_ordenadas = sorted(
            llegadas,
            key=lambda x: (
                "-".join(x["sort_fecha"].split("-")[::-1]),
                x["sort_hora"]
            )
        )

        for v in llegadas_ordenadas:
            contenido += f"| {v['aerolinea']} | **{v['vuelo']}** | {v['origen']} | {v['fecha']} | {v['hora']} | {v['cinta']} | {v['estado']} |\n"

    contenido += f"\n\n*Datos de arribos exclusivos ordenados cronológicamente y validados desde el portal oficial del [Aeropuerto La Florida de La Serena](https://aeropuertolaserena.cl).*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    print("Reporte de arribos purificado de salidas generado con éxito.")

if __name__ == "__main__":
    html_data = obtener_vuelos_oficiales()
    generar_reporte(html_data)
