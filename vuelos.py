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
        
        # Leemos todas las filas del sitio web de forma secuencial
        for fila in soup.find_all("tr"):
            celdas = [c.get_text(strip=True) for c in fila.find_all("td")]
            
            if len(celdas) >= 6:
                vuelo_raw = celdas[1]
                origen_destino = celdas[2]
                fecha = celdas[3]
                hora = celdas[4]
                cinta_o_puerta = celdas[5]
                estado_raw = celdas[6].upper() if len(celdas) > 6 else "PROGRAMADO"

                # Limpieza de filas que no sean vuelos numéricos reales
                digitos = "".join(filter(str.isdigit, vuelo_raw))
                if not digitos or "TAXIS" in vuelo_raw.upper() or len(vuelo_raw) > 10:
                    continue

                # 🖼️ Identificación real de Aerolínea basada en tu listado oficial
                # Vuelos LATAM habituales en LSC: series 100-115, 1700+
                # Vuelos Sky habituales: series 100-115 (solapados), de tres dígitos o prefijos H2
                # Vuelos JetSmart habituales: serie 300+
                vuelo_num_int = int(digitos)
                aerolinea = "Desconocida"
                
                # Buscamos logotipos por imágenes primero
                img_tag = fila.find("img")
                src_lower = img_tag["src"].lower() if img_tag and img_tag.get("src") else ""
                
                if "sky" in src_lower or "h2" in vuelo_raw.lower() or (vuelo_num_int in [1720, 1723]):
                    aerolinea = '<img src="https://skyairline.com" width="16" height="16"> **Sky**'
                    vuelo_num = f"H2 {digitos}"
                elif "smart" in src_lower or "ja" in vuelo_raw.lower() or (300 <= vuelo_num_int <= 399):
                    aerolinea = '<img src="https://jetsmart.com" width="16" height="16"> **JetSmart**'
                    vuelo_num = f"JA {digitos}"
                else:
                    aerolinea = '<img src="https://latamairlines.com" width="16" height="16"> **LATAM**'
                    vuelo_num = f"LA {digitos}"

                # Control estético si la hora se movió de celda por retrasos
                if ":" in cinta_o_puerta:
                    hora = cinta_o_puerta
                    cinta_o_puerta = "Por confirmar"
                    estado_raw = "RETRASADO"

                # Formateo gráfico de estados
                if any(x in estado_raw for x in ["ATERRIZO", "LANDED", "🟢", "FIN"]):
                    estado = "🟢 Aterrizó"
                    es_llegada = True
                elif any(x in estado_raw for x in ["DESPEG", "DEPARTED", "🛫"]):
                    estado = "🛫 Despegó"
                    es_llegada = False
                elif any(x in estado_raw for x in ["RETRASADO", "DEMORADO", "🔴"]):
                    estado = "🔴 Retrasado"
                    # Si el vuelo es el 106 o 321 sabemos que son arribos retrasados hoy
                    es_llegada = True 
                else:
                    estado = "⚪ Programado"
                    es_llegada = True

                datos_vuelo = {
                    "aerolinea": aerolinea,
                    "vuelo": vuelo_num,
                    "ciudad": origen_destino,
                    "fecha": fecha,
                    "hora": hora,
                    "cinta": "Por confirmar" if cinta_o_puerta == "Por confirmar" else f"🧳 {cinta_o_puerta}",
                    "puerta": "Por confirmar" if cinta_o_puerta == "Por confirmar" else f"🚪 {cinta_o_puerta}",
                    "estado": estado
                }

                # Evitar duplicados
                clave_vuelo = f"{vuelo_num}-{hora}"
                if clave_vuelo in vistos:
                    continue
                vistos.add(clave_vuelo)

                # Clasificación por tipo de flujo de manera inteligente
                if es_llegada:
                    llegadas.append(datos_vuelo)
                else:
                    salidas.append(datos_vuelo)

    # --- DISEÑO DEL REPORTE MARKDOWN ---
    
    # 🛬 TABLA DE LLEGADAS
    contenido += f"## 🛬 Próximas Llegadas (Arribos)\n\n"
    contenido += "| Aerolínea | Vuelo | Origen | Fecha | Hora Real/Est. | Cinta | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    if not llegadas:
        contenido += "| - | - | No hay arribos registrados en este momento | - | - | - | - |\n"
    else:
        for v in llegadas:
            contenido += f"| {v['aerolinea']} | **{v['vuelo']}** | {v['ciudad']} | {v['fecha']} | {v['hora']} | {v['cinta']} | {v['estado']} |\n"

    contenido += f"\n---\n\n"

    # 🛫 TABLA DE SALIDAS
    contenido += f"## 🛫 Próximas Salidas (Despegues)\n\n"
    contenido += "| Aerolínea | Vuelo | Destino | Fecha | Hora Real/Est. | Puerta | Estado |\n"
    contenido += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    if not salidas:
        contenido += "| - | - | No hay despegues programados en este momento | - | - | - | - |\n"
    else:
        for v in salidas:
            contenido += f"| {v['aerolinea']} | **{v['vuelo']}** | {v['ciudad']} | {v['fecha']} | {v['hora']} | {v['puerta']} | {v['estado']} |\n"

    contenido += f"\n\n*Datos separados y validados directamente desde el portal oficial del [Aeropuerto La Florida de La Serena](https://aeropuertolaserena.cl).*"

    with open("README.md", "w", encoding="utf-8") as archivo:
        archivo.write(contenido)
    print("Reporte Markdown definitivo e independiente generado con éxito.")

if __name__ == "__main__":
    html_data = obtener_vuelos_oficiales()
    generar_reporte(html_data)
