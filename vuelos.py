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

def procesar_bloque_tabla(soup, selector_id):
    vuelos_lista = []
    vistos = set()
    
    # Intentamos buscar el contenedor por ID o por clase CSS específica de la sección
    contenedor = soup.find(id=selector_id) or soup.find(class_=f"{selector_id}-table") or soup.find(class_=selector_id)
    
    # Si no lo encuentra directamente, buscamos los subtítulos "Llegadas" o "Salidas" para enganchar la tabla correspondiente
    if not contenedor:
        for h in soup.find_all(["h2", "h3", "h4", "div"]):
            if selector_id.upper() in h.get_text().upper():
                contenedor = h.find_next("table") or h.find_next("div", class_="table-responsive") or h.find_next("div")
                break

    if not contenedor:
        return vuelos_lista

    # Buscamos las filas de datos reales (tr) dentro de ese contenedor aislado
    for fila in contenedor.find_all("tr"):
        celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
        
        if len(celdas) >= 6:
            vuelo_raw = celdas[1] if len(celdas) > 1 else ""
            ciudad = celdas[2] if len(celdas) > 2 else ""
            fecha = celdas[3] if len(celdas) > 3 else ""
            hora = celdas[4] if len(celdas) > 4 else ""
            cinta_o_puerta = celdas[5] if len(celdas) > 5 else "Por confirmar"
            estado_raw = celdas[6].upper() if len(celdas) > 6 else "PROGRAMADO"

            # 🛡️ FILTRO DE SEGURIDAD: Validar que sea un número de vuelo real (no texto basura de menús)
            # Extraemos los dígitos numéricos del código de vuelo
            digitos_vuelo = "".join(filter(str.isdigit, vuelo_raw))
            if not digitos_vuelo or len(vuelo_raw) > 12 or "TAXIS" in vuelo_raw.upper():
                continue

            # 🖼️ Identificación infalible analizando la etiqueta de imagen de la fila
            aerolinea = "Desconocida"
            img_tag = fila.find("img")
            src_lower = img_tag["src"].lower() if img_tag and img_tag.get("src") else ""
            
            if "sky" in src_lower or "h2" in vuelo_raw.lower():
                aerolinea = '<img src="https://skyairline.com" width="16" height="16"> **Sky**'
                vuelo_num = f"H2 {digitos_vuelo}"
            elif "smart" in src_lower or "ja" in vuelo_raw.lower():
                aerolinea = '<img src="https://jetsmart.com" width="16" height="16"> **JetSmart**'
                vuelo_num = f"JA {digitos_vuelo}"
            else:
                aerolinea = '<img src="https://latamairlines.com" width="16" height="16"> **LATAM**'
                vuelo_num = f"LA {digitos_vuelo}"

            # Parche de seguridad por si la hora se movió de columna debido a retrasos
            if ":" in cinta_o_puerta:
                hora = cinta_o_puerta
                cinta_o_puerta = "Por confirmar"
                if "RETRASADO" not in estado_raw: estado_raw = "RETRASADO"

            cinta_formateada = f"🧳 {cinta_o_puerta}" if selector_id == "llegadas" else f"🚪 {cinta_o_puerta}"
            if cinta_o_puerta == "Por confirmar":
                cinta_formateada = "Por confirmar"

            # Formateo iconográfico del estado real
            if any(x in estado_raw for x in ["ATERRIZO", "LANDED", "FIN"]):
                estado = "🟢 Aterrizó"
            elif any(x in estado_raw for x in ["DESPEG", "DEPARTED"]):
                estado = "🛫 Despegó"
            elif any(x in estado_raw for x in ["RUTA", "VUELO"]):
                estado = "🔵 En Ruta"
            elif any(x in estado_raw for x in ["RETRASADO", "DEMORADO"]):
                estado = "🔴 Retrasado"
            else:
                estado = "⚪ Programado"

            # Evitar registros duplicados dentro de la misma tabla
            clave_vuelo = f"{vuelo_num}-{hora}"
            if clave_vuelo in vistos:
                continue
            vistos.add(clave_vuelo)

            vuelos_lista.append({
                "aerolinea": aerolinea,
                "vuelo": vuelo_num,
                "ciudad": ciudad,
                "fecha": fecha,
                "hora": hora,
                "cinta_o_puerta": cinta_formateada,
                "estado": estado
            })
            
    return vuelos_lista

def generar_reporte(html):
    zona_chile = datetime.timezone(datetime.timedelta(hours=-4))
    ahora_local = datetime.datetime.now(zona_chile).strftime("%Y-%m-%d %H:%M:%S")
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Procesamos las dos secciones de forma 100% aislada usando selectores nativos
    llegadas = procesar_bloque_tabla(soup, "llegadas")
    salidas = procesar_bloque_tabla(soup, "salidas")

    contenido = f"# ✈️ Estado de Vuelos en Tiempo Real - La Serena (SCSE / LSC)\n\n"
    contenido += f"Última actualización: `{ahora_local} (Hora Local Chile)`\n\n"
    
    # --- TABLA DE LLEGADAS ---
    contenido += f"## 🛬 Próximas Llegadas (Arribos)\n\n"
    contenido += "| Aerolínea | Vuelo | Origen | Fecha | Hora Real/Est. | Cinta | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    if not llegadas:
        contenido += "| - | - | No hay arribos registrados en este momento | - | - | - | - |\n"
    else:
        for v in llegadas:
            contenido += f"| {v['aerolinea']} | **{v['vuelo']}** | {v['ciudad']} | {v['fecha']} | {v['hora']} | {v['cinta_o_puerta']} | {v['estado']} |\n"

    contenido += f"\n---\n\n"

    # --- TABLA DE SALIDAS ---
    contenido += f"## 🛫 Próximas Salidas (Despegues)\n\n"
    contenido += "| Aerolínea | Vuelo | Destino | Fecha | Hora Real/Est. | Puerta | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    if not salidas:
        contenido += "| - | - | No hay despegues programados en este momento | - | - | - | - |\n"
    else:
        for v in salidas:
            contenido += f"| {v['aerolinea']} | **{v['vuelo']}** | {v['ciudad']} | {v['fecha']} | {v['hora']} | {v['cinta_o_puerta']} | {v['estado']} |\n"

    contenido += f"\n\n*Datos separados y validados directamente desde el portal oficial del [Aeropuerto La Florida de La Serena](https://aeropuertolaserena.cl).*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    print("Reporte final estructurado y libre de basura generado con éxito.")

if __name__ == "__main__":
    html_data = obtener_vuelos_oficiales()
    if html_data:
        generar_reporte(html_data)
