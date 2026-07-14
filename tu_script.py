import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# La URL de los vuelos en camino hacia La Serena
url_enroute = "https://flightaware.com"

cabeceras = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
}

try:
    print("Conectando a la grilla /enroute de FlightAware...")
    respuesta = requests.get(url_enroute, headers=cabeceras, timeout=20)
    
    vuelos_reales_detectados = []
    hoy = datetime.now().strftime('%Y-%m-%d')

    if respuesta.status_code == 200:
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        filas = soup.select('table tr')
        
        for fila in filas:
            celdas = fila.find_all('td')
            
            # Validamos que la fila contenga al menos las 5 columnas requeridas
            if len(celdas) >= 5:
                ident = celdas[0].get_text(strip=True).upper().replace(' ', '')
                origen_raw = celdas[2].get_text(strip=True)
                llegada_raw = celdas[4].get_text(strip=True) # Columna 4: Hora de llegada estimada con telemetría

                # Validamos que corresponda a una aerolínea comercial chilena válida
                if ident.startswith(('LAN', 'LA', 'LXP', 'SKU', 'H2', 'JAT', 'JA', 'BON')) and any(char.isdigit() for char in ident):
                    
                    # Limpiamos la hora de llegada removiendo asteriscos (*) y zonas horarias (ej: -04)
                    hora_limpia = llegada_raw.split(' ')[0].replace('*', '').strip()
                    
                    # Clasificación de aerolíneas nacionales
                    aerolinea = 'Comercial / Chárter'
                    if ident.startswith(('LAN', 'LA', 'LXP')): aerolinea = 'LATAM Airlines'
                    elif ident.startswith(('SKU', 'H2')): aerolinea = 'Sky Airline'
                    elif ident.startswith(('JAT', 'JA')): aerolinea = 'JetSMART'
                    elif ident.startswith('BON'): aerolinea = 'Skyline / Bonus'

                    # Detección automática de estados de retraso por asterisco (*)
                    estado = 'PROGRAMADO'
                    if '*' in llegada_raw:
                        estado = 'ATRASADO / REPROGRAMADO'
                    elif 'p' in llegada_raw.lower() or 'a' in llegada_raw.lower():
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
                            'hora_llegada_estimada': hora_limpia, # Solo guardamos la llegada
                            'estado': estado
                        })

        json_salida = {
            'status': 'exito' if len(vuelos_reales_detectados) > 0 else 'vacio',
            'proveedor': 'FlightAware EnRoute HTML Stream',
            'aeropuerto': {'nombre': 'Aeropuerto La Florida', 'iata': 'LSC', 'icao': 'SCSE'},
            'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S CLST'),
            'vuelos_programados': vuelos_reales_detectados
        }

        with open('vuelos_la_serena.json', 'w', encoding='utf-8') as f:
            json.dump(json_salida, f, ensure_ascii=False, indent=4)
            
        print(f"Sincronización completada. Se extrajeron {len(vuelos_reales_detectados)} arribos reales.")
        
    else:
        print(f"Error de red con FlightAware: HTTP {respuesta.status_code}")
        exit(1)

except Exception as e:
    print(f"Falla crítica en el raspado: {e}")
    exit(1)
