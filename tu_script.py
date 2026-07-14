import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# URL pública de FlightAware para La Serena
url_scrapie = "https://flightaware.com"

# Cabeceras de simulación de navegador para evitar bloqueos
cabeceras = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
}

try:
    print("Iniciando extracción limpia en tiempo real desde FlightAware...")
    respuesta = requests.get(url_scrapie, headers=cabeceras, timeout=20)
    
    vuelos_reales_detectados = []
    hoy = datetime.now().strftime('%Y-%m-%d')

    if respuesta.status_code == 200:
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        
        # Buscamos todas las tablas de datos en el HTML
        tablas = soup.find_all('table')
        
        for tabla in tablas:
            filas = tabla.find_all('tr')
            for fila in filas:
                celdas = fila.find_all('td')
                
                # Procesamos solo las filas con estructura de vuelos válida
                if len(celdas) >= 5:
                    ident = celdas[0].text.strip()       # Número de vuelo (ej: LAN100)
                    procedencia = celdas[2].text.strip() # Origen / Destino (ej: Santiago SCL)
                    hora_raw = celdas[4].text.strip()    # Hora informada en la grilla
                    
                    # Filtramos códigos aeronáuticos chilenos válidos (LATAM, Sky, JetSMART)
                    if ident and any(char.isdigit() for char in ident) and len(ident) < 10:
                        if ident.startswith(('LAN', 'LA', 'LXP', 'SKU', 'H2', 'JAT', 'JA', 'BON')):
                            
                            # Limpieza de la hora eliminando caracteres de demora o zonas horarias
                            hora_limpia = hora_raw.split(' ')[0].replace('*', '').strip()
                            
                            # Mapear aerolínea real
                            aerolinea = 'Comercial / Chárter'
                            if ident.startswith(('LAN', 'LA', 'LXP')): aerolinea = 'LATAM Airlines'
                            elif ident.startswith(('SKU', 'H2')): aerolinea = 'Sky Airline'
                            elif ident.startswith(('JAT', 'JA')): aerolinea = 'JetSMART'
                            elif ident.startswith('BON'): aerolinea = 'Skyline / Bonus'

                            # Detectar estado de retraso por el asterisco (*) nativo de FlightAware
                            estado = 'PROGRAMADO'
                            if '*' in hora_raw:
                                estado = 'ATRASADO / ESTIMADO'
                            elif 'p' in hora_raw.lower() or 'a' in hora_raw.lower():
                                estado = 'EN RUTA'

                            # Evitar duplicar registros en el bucle
                            if not any(v['vuelo_numero'] == ident for v in vuelos_reales_detectados):
                                vuelos_reales_detectados.append({
                                    'vuelo_numero': ident,
                                    'aerolinea': aerolinea,
                                    'tipo': 'Vuelo en Vivo',
                                    'origen': procedencia.replace('Int\'l', '').replace('Airport', '').strip(),
                                    'destino': 'La Serena (LSC)',
                                    'fecha': hoy,
                                    'hora_programada': hora_limpia,
                                    'estado': estado
                                })

        # Estructura del JSON final de producción libre de grillas fijas
        json_salida = {
            'status': 'exito' if len(vuelos_reales_detectados) > 0 else 'vacio',
            'proveedor': 'FlightAware Live HTML Stream',
            'aeropuerto': {'nombre': 'Aeropuerto La Florida', 'iata': 'LSC', 'icao': 'SCSE'},
            'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S CLST'),
            'vuelos_programados': vuelos_reales_detectados
        }

        with open('vuelos_la_serena.json', 'w', encoding='utf-8') as f:
            json.dump(json_salida, f, ensure_ascii=False, indent=4)
            
        print(f"Sincronización completada. Se guardaron {len(vuelos_reales_detectados)} vuelos reales.")
        
    else:
        print(f"Error de red con FlightAware: HTTP {respuesta.status_code}")
        exit(1)

except Exception as e:
    print(f"Falla crítica en el raspado web: {e}")
    exit(1)
