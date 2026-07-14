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

# URL CORRECTA: Con el subdominio 'api.' y la ruta '/v1/flights' bien separada de los parámetros
url = f"http://aviationstack.com{API_KEY}&dep_iata={AIRPORT_IATA}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        
        # Obtener la ruta exacta de la carpeta actual del proyecto para asegurar el guardado
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'vuelos_la_serena.json')
        
        # Guardar los datos en el archivo JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print("Datos de vuelos actualizados y guardados con éxito.")
    else:
        print(f"Error en la API: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Ocurrió un error inesperado: {e}")
