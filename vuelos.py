import os
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# La URL que descubriste con los arribos en camino hacia La Serena
url_enroute = "https://flightaware.com"

cabeceras = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-CL,es;q=0.9,en;q=0.8'
}

try:
    print("Iniciando conexión cruda en tiempo real a la grilla /enroute de FlightAware...")
    respuesta = requests.get(url_enroute, headers=cabeceras, timeout=20)
    
    vuelos_reales_detectados = []
    hoy = datetime.now().strftime('%Y-%m-%d')

    if respuesta.status_code == 200:
        # Analizamos el bloque script interno donde FlightAware inyecta la grilla de datos para el navegador
        # Esto nos permite extraer los datos reales saltándonos bloqueos visuales de etiquetas de diseño
        patron_datos = re.search(r'trackData\s*=\s*({.*?});', respuesta.text)
        
        if patron_datos:
            print("Datos de telemetría aérea interceptados en el código fuente.")
            datos_crudos = json.loads(patron_datos.group(1))
            
            # FlightAware organiza los vuelos en camino dentro de su objeto 'enroute' o 'flights'
            vuelos_api_interna = datos_crudos.get('enroute', {}).get('flights', [])
            
            for f in vuelos_api_interna:
                ident = f.get('ident', '').upper().replace(' ', '')
                
                # Sintonizar únicamente las aerolíneas comerciales que operan hoy hacia La Serena
                if ident.startswith(('LAN', 'LA', 'LXP', 'SKU', 'H2', 'JAT', 'JA', 'BON')):
                    
                    # Extraer la hora de arribo estimada calculada por el radar en formato HH:MM
                    llegada_estimada = f.get('estimated_arrival_time', f.get('scheduled_arrival_time', ''))
                    
                    if llegada_estimada:
                        hora_limpia = llegada_estimada.split(' ')[-1].replace('*', '').strip()[:5]
                        
                        aerolinea = 'Comercial / Chárter'
                        if ident.startswith(('LAN', 'LA', 'LXP')): aerolinea = 'LATAM Airlines'
                        elif ident.startswith(('SKU', 'H2')): aerolinea = 'Sky Airline'
                        elif ident.startswith(('JAT', 'JA')): aerolinea = 'JetSMART'

                        # Extraer estados de retraso directo desde los flags de la plataforma web
                        estado = 'EN RUTA'
                        if f.get('delayed') or f.get('delay_minutes', 0) > 0:
                            estado = 'ATRASADO / REPROGRAMADO'
                        elif f.get('cancelled'):
                            estado = 'CANCELADO'

                        vuelos_reales_detectados.append({
                            'vuelo_numero': ident,
                            'aerolinea': aerolinea,
                            'tipo': 'Arribo',
                            'origen': f.get('origin_city', f.get('origin_name', 'Origen')).split(',')[0].strip(),
                            'destino': 'La Serena (LSC)',
                            'fecha': hoy,
                            'hora_llegada_estimada': hora_limpia,
                            'estado': estado
                        })
        else:
            # Si no intercepta el objeto de datos directo, recorremos de forma estructurada las celdas de la tabla HTML
            soup = BeautifulSoup(respuesta.text, 'html.parser')
            filas = soup.select('table tr')
            
            for fila in filas:
                celdas = fila.find_all(['td', 'th'])
                if len(celdas) >= 5:
                    ident = celdas[0].get_text(strip=True).upper().replace(' ', '')
                    origen_raw = celdas[2].get_text(strip=True)
                    llegada_raw = celdas[4].get_text(strip=True)
                    
                    if ident.startswith(('LAN', 'LA', 'LXP', 'SKU', 'H2', 'JAT', 'JA', 'BON')) and any(c.isdigit() for c in ident):
                        hora_limpia = llegada_raw.split(' ')[0].replace('*', '').strip()
                        
                        aerolinea = 'Comercial / Chárter'
                        if ident.startswith(('LAN', 'LA', 'LXP')): aerolinea = 'LATAM Airlines'
                        elif ident.startswith(('SKU', 'H2')): aerolinea = 'Sky Airline'
                        elif ident.startswith(('JAT', 'JA')): aerolinea = 'JetSMART'

                        estado = 'PROGRAMADO'
                        if '*' in llegada_raw:
                            estado = 'ATRASADO / REPROGRAMADO'
                        elif 'P' in llegada_raw.upper() or 'A' in llegada_raw.upper():
                            estado = 'EN RUTA'

                        vuelos_reales_detectados.append({
                            'vuelo_numero': ident,
                            'aerolinea': aerolinea,
                            'tipo': 'Arribo',
                            'origen': origen_raw.split('(')[0].replace("Int'l", "").replace("Airport", "").strip(),
                            'destino': 'La Serena (LSC)',
                            'fecha': hoy,
                            'hora_llegada_estimada': hora_limpia,
                            'estado': estado
                        })

        # Estructura del JSON final de producción PURA sin grillas estáticas fijas de respaldo
        json_salida = {
            'status': 'exito' if len(vuelos_reales_detectados) > 0 else 'vacio',
            'proveedor': 'FlightAware Realtime Stream Engine',
            'aeropuerto': {'nombre': 'Aeropuerto La Florida', 'iata': 'LSC', 'icao': 'SCSE'},
            'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S CLST'),
            'vuelos_programados': vuelos_reales_detectados
        }

        with open('vuelos_la_serena.json', 'w', encoding='utf-8') as f:
            json.dump(json_salida, f, ensure_ascii=False, indent=4)
            
        print(f"Sincronización finalizada. Se procesaron {len(vuelos_reales_detectados)} arribos reales extraídos de la web.")
        
        # Forzamos código de salida de error si Cloudflare bloqueó la IP de GitHub y devolvió 0 vuelos
        # Esto sirve para que tú veas la alerta en Actions en lugar de recibir un JSON vacío
        if len(vuelos_reales_detectados) == 0:
            print("⚠️ Alerta: El servidor no devolvió vuelos reales en este ciclo debido a políticas de bloqueo perimetral.")
            exit(1)
        
    else:
        print(f"Error de red directo con FlightAware: HTTP {respuesta.status_code}")
        exit(1)

except Exception as e:
    print(f"Falla crítica en el raspado web directo: {e}")
    exit(1)
