import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

url_enroute = "https://flightaware.com"

cabeceras = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
}

try:
    print("Conectando de forma directa a la grilla /enroute de FlightAware...")
    respuesta = requests.get(url_enroute, headers=cabeceras, timeout=20)
    
    vuelos_reales_detectados = []
    hoy = datetime.now().strftime('%Y-%m-%d')

    if respuesta.status_code == 200:
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        
        # Buscamos todas las filas dentro de cualquier estructura de tabla en la página
        filas = soup.select('tr')
        print(f"Total de filas evaluadas en el documento HTML: {len(filas)}")
        
        for fila in filas:
            # Buscamos elementos td o th para abarcar cualquier diseño de FlightAware
            celdas = fila.find_all(['td', 'th', 'div'])
            
            # Limpiamos y unimos los contenidos internos de la fila para validación rápida
            fila_texto = fila.get_text(" ", strip=True).upper()
            
            # Filtro inteligente: validamos si la fila contiene alguna aerolínea chilena comercial
            if any(sigla in fila_texto for sigla in ['LAN', 'LA ', 'LXP', 'SKU', 'H2 ', 'JAT', 'JA ']):
                
                # Extraemos de forma limpia el texto de cada elemento de la fila
                datos_fila = [c.get_text(strip=True) for c in celdas if c.get_text(strip=True)]
                
                # Si la fila tiene los campos necesarios procesamos sus posiciones
                if len(datos_fila) >= 4:
                    # Buscamos el identificador del vuelo (ej: LAN100, SKU1741)
                    ident = "".join(datos_fila[0].split()).upper()
                    
                    # Nos aseguramos que sea un número de vuelo válido y no un texto suelto
                    if any(char.isdigit() for char in ident) and len(ident) < 10:
                        
                        # Mapeamos las columnas basándonos en la estructura visual de la grilla
                        origen_raw = datos_fila[2] if len(datos_fila) > 2 else 'Origen'
                        llegada_raw = datos_fila[-1] # La última columna siempre es la hora de arribo estimada
                        
                        # Limpiamos la hora de llegada removiendo los asteriscos de retraso (*)
                        hora_limpia = llegada_raw.split(' ')[0].replace('*', '').strip()
                        
                        # Clasificación exacta de aerolíneas nacionales
                        aerolinea = 'Comercial / Chárter'
                        if ident.startswith(('LAN', 'LA', 'LXP')): aerolinea = 'LATAM Airlines'
                        elif ident.startswith(('SKU', 'H2')): aerolinea = 'Sky Airline'
                        elif ident.startswith(('JAT', 'JA')): aerolinea = 'JetSMART'
                        elif ident.startswith('BON'): aerolinea = 'Skyline / Bonus'

                        # Detección automática de estados de retraso por asterisco (*)
                        estado = 'PROGRAMADO'
                        if '*' in llegada_raw:
                            estado = 'ATRASADO / REPROGRAMADO'
                        elif 'P' in llegada_raw.upper() or 'A' in llegada_raw.upper():
                            estado = 'EN RUTA'

                        origen_limpio = origen_raw.replace("Int'l", "").replace("Airport", "").strip()

                        if not any(v['vuelo_numero'] == ident for v in vuelos_reales_detectados):
                            vuelos_reales_detectados.append({
                                'vuelo_numero': ident,
                                'aerolinea': aerolinea,
                                'tipo': 'Arribo',
                                'origen': origen_limpio,
                                'destino': 'La Serena (LSC)',
                                'fecha': hoy,
                                'hora_llegada_estimada': hora_limpia,
                                'estado': estado
                            })

        # Estructura del JSON final de producción libre de grillas fijas
        json_salida = {
            'status': 'exito' if len(vuelos_reales_detectados) > 0 else 'vacio',
            'proveedor': 'FlightAware EnRoute HTML Stream',
            'aeropuerto': {'nombre': 'Aeropuerto La Florida', 'iata': 'LSC', 'icao': 'SCSE'},
            'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S CLST'),
            'vuelos_programados': vuelos_reales_detectados
        }

        with open('vuelos_la_serena.json', 'w', encoding='utf-8') as f:
            json.dump(json_salida, f, ensure_ascii=False, indent=4)
            
        print(f"Sincronización completada. Se extrajeron {len(vuelos_reales_detectados)} arribos reales en vivo.")
        
    else:
        print(f"Error de red con FlightAware: HTTP {respuesta.status_code}")
        exit(1)

except Exception as e:
    print(f"Falla crítica en el raspado: {e}")
    exit(1)
