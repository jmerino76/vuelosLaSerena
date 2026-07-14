import os
import json
import requests
from dotenv import load_dotenv

# Cargar variables de entorno locales (si existen)
load_dotenv()

API_KEY = os.getenv('AVIATIONSTACK_KEY')
AIRPORT_IATA = 'LSC'

if not API_KEY:
    print("Error: No se encontró la API Key en las variables de entorno.")
    exit(1)

# URL CORRECTA: Incluye ://aviationstack.com
url = f"http://://aviationstack.com?access_key={API_KEY}&dep_iata={AIRPORT_IATA}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        
        # Guardar los datos en un archivo JSON bien formateado
        with open('vuelos_la_serena.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print("Datos de vuelos actualizados y guardados con éxito.")
    else:
        print(f"Error en la API: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Ocurrió un error inesperado: {e}")
