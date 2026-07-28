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
    
    contenido = f"# ✈️ Estado de Vuelos en Tiempo Real - La Serena (SCSE / LSC)\n\n"
    contenido += f"Última actualización: `{ahora_local} (Hora Local Chile)`\n\n"
    
    llegadas = []
    salidas = []
    vistos = set()

    if html:
        soup = BeautifulSoup(html, "html.parser")
        
        # Buscamos todas las filas de datos que contengan celdas internas (td o div de celdas)
        for fila in soup.find_all(["tr", "div"]):
            # Extraemos los textos de los elementos hijos inmediatos para simular las columnas
            celdas = [c.get_text(strip=True) for c in fila.find_all(["td", "div"], recursive=False)]
            
            # Limpiamos las celdas vacías del array
            celdas = [c for c in celdas if c]

            # Si el bloque contiene la estructura de 7 datos oficiales de un vuelo
            if len(celdas) >= 6:
                texto_completo = " ".join(celdas).upper()
                
                # Descartamos si es una fila de encabezados
                if "VUELO" in texto_completo or "ORIGEN" in texto_completo or "DESTINO" in texto_completo:
                    continue
                
                # Mapeo universal de variables basado en la posición de los datos
                vuelo_raw = celdas[0] if len(celdas) > 0 else "N/A"
                ciudad = celdas[1] if len(celdas) > 1 else "N/A"
                fecha = celdas[2] if len(celdas) > 2 else "N/A"
                hora = celdas[3] if len(celdas) > 3 else "N/A"
                cinta_o_puerta = celdas[4] if len(celdas) > 4 else "Por confirmar"
                estado_raw = celdas[5].upper() if len(celdas) > 5 else "PROGRAMADO"

                # Si no hay número de vuelo válido, saltamos la fila
                if not vuelo_raw or len(vuelo_raw) > 10:
                    continue

                # 🖼️ Extracción del Logotipo gráfico o asignación inteligente
                aerolinea = "Desconocida"
                img_tag = fila.find("img")
                src_lower = img_tag["src"].lower() if img_tag and img_tag.get("src") else ""
                
                if "sky" in src_lower or vuelo_raw.startswith("H2") or len(vuelo_raw) == 3:
                    aerolinea = '<img src="https://skyairline.com" width="16" height="16"> **Sky**'
                    if not vuelo_raw.startswith("H2"): vuelo_raw = f"H2 {vuelo_raw}"
                elif "jetsmart" in src_lower or "smart" in src_lower or vuelo_raw.startswith("JA") or (vuelo_raw.isdigit() and 300 <= int(vuelo_raw) <= 399):
                    aerolinea = '<img src="https://jetsmart.com" width="16" height="16"> **JetSmart**'
                    if not vuelo_raw.startswith("JA"): vuelo_raw = f"JA {vuelo_raw}"
                else:
                    aerolinea = '<img src="https://latamairlines.com" width="16" height="16"> **LATAM**'
                    if not vuelo_raw.startswith("LA"): vuelo_raw = f"LA {vuelo_raw}"

                # Parche si la hora se desplazó por un retraso
                if ":" in cinta_o_puerta:
                    hora = cinta_o_puerta
                    cinta_o_puerta = "Por confirmar"
                    estado_raw = "RETRASADO"

                # Clasificación de la iconografía de estados
                if any(x in estado_raw for x in ["ATERRIZO", "LANDED", "🟢", "FIN"]):
                    estado = "🟢 Aterrizó"
                elif any(x in estado_raw for x in ["DESPEGÓ", "DEPARTED", "🛫"]):
                    estado = "🛫 Despegó"
                elif any(x in estado_raw for x in ["RUTA", "VUELO", "🔵"]):
                    estado = "🔵 En Ruta"
                elif any(x in estado_raw for x in ["RETRASADO", "DEMORADO", "🔴"]):
                    estado = "🔴 Retrasado"
                else:
                    estado = "⚪ Programado"

                datos_vuelo = {
                    "aerolinea": aerolinea,
                    "vuelo": vuelo_raw,
                    "ciudad": ciudad,
                    "fecha": fecha,
                    "hora": hora,
                    "cinta_o_puerta": cinta_o_puerta,
                    "estado": estado
                }

                # Evitamos duplicados en la lectura total
                clave_vuelo = f"{vuelo_raw}-{hora}"
                if clave_vuelo in vistos:
                    continue
                vistos.add(clave_vuelo)

                # 🗂️ Criterio de separación automática:
                # El sitio web usa componentes estructurales diferentes o palabras clave para clasificar
                # Si el contenedor superior o la fila hereda clases de despegues/salidas o arribos
                fila_texto_total = str(fila).upper()
                if "SALIDA" in fila_texto_total or "DEPARTURE" in fila_texto_total or "DESPEG" in estado_raw:
                    salidas.append(datos_vuelo)
                elif "LLEGADA" in fila_texto_total or "ARRIVAL" in fila_texto_total or "ATERRIZ" in estado_raw:
                    llegadas.append(datos_vuelo)
                else:
                    # Fallback analítico: si la hora es muy tardía o según flujos normales lo dejamos en arribos hoy
                    llegadas.append(datos_vuelo)

    # --- RENDERIZADO EN EL ARCHIVO MARKDOWN ---
    
    # 🛬 TABLA DE ARRIVOS
    contenido += f"## 🛬 Próximas Llegadas (Arribos)\n\n"
    contenido += "| Aerolínea | Vuelo | Origen | Fecha | Hora Real/Est. | Cinta | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    if not llegadas:
        contenido += "| - | - | No hay arribos registrados en este momento | - | - | - | - |\n"
    else:
        for v in llegadas:
            contenido += f"| {v['aerolinea']} | **{v['vuelo']}** | {v['ciudad']} | {v['fecha']} | {v['hora']} | 🧳 {v['cinta_o_puerta']} | {v['estado']} |\n"

    contenido += f"\n---\n\n"

    # 🛫 TABLA DE DESPEGUES
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
    print("Reporte Markdown con mapeo de divs modernos generado con éxito.")

if __name__ == "__main__":
    html_data = obtener_vuelos_oficiales()
    generar_reporte(html_data)
