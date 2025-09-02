import os
import time

import requests
import json
import base64
from PIL import Image
import io

# Carga la clave de API desde una variable de entorno o un archivo de configuración
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError(
        "No se encontró la clave de API de Gemini. Asegúrate de configurar la variable de entorno GEMINI_API_KEY.")

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"

PROMPT_TEXT = """
Eres un asistente de clasificación de basura inteligente y amigable.
Recibirás imágenes de objetos para decidir a qué categoría de residuos pertenece.
Debes responder SIEMPRE en formato JSON válido siguiendo las siguientes reglas estrictas:

## Reglas de Clasificación:
1. Solo puedes clasificar en uno de estos 3 materiales: "plástico", "orgánico", "metal".
2. Si detectas varios materiales en el objeto, elige el que tenga mayor peso visual/probabilidad y clasifica solo en uno.
3. Si no logras identificar el material con certeza, responde con "material": "null".
4. Siempre incluye una lista de objetos detectados con sus descripciones, aunque sea un solo objeto.

## Manejo de Errores:
- Si la imagen está borrosa, vacía o no contiene basura, devuelve "material": "null".
- Nunca rompas el formato JSON.

## Salida:
Tu salida DEBE ser un JSON único, válido y ejecutable en Python.

```json
{
  "material": "plástico|orgánico|metal|null",
  "objeto_s": [
    {
      "nombre": "ejemplo: botella de gaseosa",
      "confianza": 0.92
    }
  ],
  "respuesta_hablada": "Tu respuesta conversacional y amigable aquí."
}
```
Estilo de respuesta hablada:
Siempre en tono amistoso y educativo.
Ejemplo: "¡Genial! Detecté una botella de plástico. Recuerda que puedes reciclarla para ayudar al planeta."
"""


def classify_image(image_bytes, retries=1):
    print("Enviando imagen a Gemini para clasificación...")
    base64_image = base64.b64encode(image_bytes).decode('utf-8')

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT_TEXT},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64_image
                        }
                    }
                ]
            }
        ]
    }

    headers = {"Content-Type": "application/json"}

    for attempt in range(retries + 1):
        try:
            # <<< LÍNEA MODIFICADA >>>
            # Se ha añadido un timeout de 30 segundos. Si no hay respuesta, fallará.
            response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()  # Lanza un error si la respuesta es 4xx o 5xx

            response_json = response.json()

            # Extraer el contenido JSON del texto
            json_str = response_json['candidates'][0]['content']['parts'][0]['text']
            # Limpiar el string en caso de que venga con formato markdown
            if json_str.startswith("```json"):
                json_str = json_str.strip("```json\n").strip("`")

            return json.loads(json_str)

        except requests.exceptions.Timeout:
            print(f"Error: La solicitud a Gemini superó el tiempo de espera de 30 segundos.")
            if attempt < retries:
                print("Reintentando...")
            else:
                return {"error": "Timeout", "message": "La API no respondió a tiempo."}

        except requests.exceptions.RequestException as e:
            print(f"Error inesperado al contactar con la API de Gemini: {e}")
            if attempt < retries:
                print(f"Intento {attempt + 1} de clasificación falló. Reintentando...")
                time.sleep(2)  # Espera 2 segundos antes de reintentar
            else:
                return {"error": "API Connection Error", "message": str(e)}
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Error al procesar la respuesta de Gemini: {e}")
            return {"error": "Invalid Response", "message": "La respuesta de la API no tuvo el formato esperado."}

    return None


# Ejemplo de uso (para pruebas)
if __name__ == '__main__':
    # Carga una imagen de ejemplo llamada 'test_image.jpg'
    try:
        with open("test_image.jpg", "rb") as f:
            image_data = f.read()
            classification_result = classify_image(image_data)
            if classification_result:
                print("\n--- Resultado de la Clasificación ---")
                print(f"Material: {classification_result.get('material')}")
                print(f"Respuesta Hablada: {classification_result.get('respuesta_hablada')}")
                print("------------------------------------")
    except FileNotFoundError:
        print("Para probar, crea un archivo 'test_image.jpg' en este directorio.")
