# -*- coding: utf-8 -*-
"""
Cliente para la API de Gemini (gemini_client.py)

Este módulo gestiona toda la comunicación con la API de Google Gemini.
Su principal responsabilidad es tomar los bytes de una imagen, enviarlos
a un modelo de Gemini y procesar la respuesta para extraer la
clasificación del material en un formato JSON estructurado.

Implementa una estrategia de resiliencia con rotación de claves de API y modelos
para manejar errores de "Too Many Requests" (429).
"""
import os
import time
import requests
import json
import base64

# --- Configuración de la API de Gemini ---

# Lista de claves de API de Gemini.
API_KEYS = [

]

if not API_KEYS:
    raise ValueError(
        "CRÍTICO: No se encontraron claves de API de Gemini. "
    )

# Lista de modelos de Gemini para alternar en caso de sobrecarga.
GEMINI_MODELS = [
    "gemini-1.5-flash-latest",
    "gemini-pro"
]

# --- Prompt del Sistema ---
PROMPT_TEXT = """
Eres la IA de un sistema de clasificación de basura. Un humano ha colocado un objeto para que lo analices. Tu tarea es identificar el material principal del objeto en la imagen y responder en formato JSON.

## Contexto del Sistema:
- Después de tu clasificación, un sistema mecánico moverá el objeto al contenedor correcto.
- Tu respuesta hablada debe ser corta, creativa y reflejar que eres parte de este sistema físico.

## Reglas de Clasificación:
1.  Clasifica el material principal en una de estas 3 categorías: "plástico", "orgánico", "metal".
2.  Si no puedes identificar el material, responde con "material": "null".
3.  Incluye siempre una lista de los objetos que ves.

## Reglas para la `respuesta_hablada`:
1.  **Comienza mencionando el objeto que has identificado.** Por ejemplo, "Veo una botella de agua..." o "Parece una cáscara de plátano...".
2.  **Luego, anuncia el material y la acción que tomarás.**
3.  Sé creativo y variado en tus respuestas.

## Formato de Salida Estricto (JSON):
```json
{
  "material": "plástico|orgánico|metal|null",
  "objeto_s": [
    {
      "nombre": "ejemplo: lata de aluminio",
      "confianza": 0.95
    }
  ],
  "respuesta_hablada": "Una respuesta que primero nombra el objeto y luego el material."
}
```

## Ejemplos de `respuesta_hablada`:
- Para una botella de plástico: "¡Es una botella de plástico! La clasificaré como plástico y la enviaré a reciclar."
- Para una cáscara de banana: "Parece una cáscara de banana. Es material orgánico, así que va para el compost."
- Para una lata de metal: "Detecté una lata de aluminio. El metal es muy valioso. Procedo a clasificarlo."
- Si no estás seguro: "No estoy muy seguro de qué es esto. Por favor, retíralo para que pueda intentarlo de nuevo."
"""

def classify_image(image_bytes, timeout=30):
    """
    Envía una imagen a la API de Gemini para su clasificación, con rotación de claves y modelos.

    Args:
        image_bytes (bytes): La imagen a clasificar, en formato de bytes (ej. JPEG).
        timeout (int): El tiempo de espera en segundos para la respuesta de la API.

    Returns:
        dict: Un diccionario con el resultado de la clasificación si fue exitoso.
              Devuelve un diccionario con una clave 'error' si la clasificación falla.
    """
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

    # --- Lógica de Rotación de Claves y Modelos ---
    for api_key_index, api_key in enumerate(API_KEYS):
        for model_index, model_name in enumerate(GEMINI_MODELS):
            
            gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            
            print(f"Intentando con API Key #{api_key_index + 1} y Modelo '{model_name}'...")

            try:
                response = requests.post(gemini_api_url, headers=headers, json=payload, timeout=timeout)
                
                if response.status_code == 429:
                    print(f"Error 429: Demasiadas solicitudes. Rotando al siguiente modelo/clave.")
                    continue 

                response.raise_for_status()

                response_json = response.json()
                json_str = response_json['candidates'][0]['content']['parts'][0]['text']
                
                if json_str.startswith("```json"):
                    json_str = json_str.strip("```json\n").strip("`")

                return json.loads(json_str)

            except requests.exceptions.Timeout:
                print(f"Error: Timeout de {timeout}s. Considera reintentar más tarde.")
                return {"error": "Timeout", "message": "La API no respondió a tiempo."}

            except requests.exceptions.RequestException as e:
                print(f"Error de conexión con API de Gemini: {e}")
                return {"error": "API Connection Error", "message": str(e)}
            
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"Error al procesar la respuesta de Gemini. Formato inesperado. Detalle: {e}")
                return {"error": "Invalid Response", "message": "La respuesta de la API no tuvo el formato esperado."}

    print("Todas las claves de API y modelos están sobrecargados. Inténtalo de nuevo más tarde.")
    return {"error": "API Overload", "message": "Todas las claves y modelos disponibles han fallado por exceso de solicitudes."}


# --- Bloque de Ejecución para Pruebas ---
if __name__ == '__main__':
    print("--- Ejecutando prueba del cliente de Gemini ---")
    try:
        with open("test_image.jpg", "rb") as f:
            image_data = f.read()
            classification_result = classify_image(image_data)
            
            print("\n--- Resultado de la Clasificación ---")
            if classification_result and 'error' not in classification_result:
                print(json.dumps(classification_result, indent=2, ensure_ascii=False))
            else:
                print("La clasificación falló.")
                print(classification_result)
            print("------------------------------------")

    except FileNotFoundError:
        print("\nERROR: Para probar este módulo, crea un archivo 'test_image.jpg' en este directorio.")
