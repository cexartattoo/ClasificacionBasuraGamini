import google.generativeai as genai
from PIL import Image
import io
import json

# --- CONFIGURACIÓN ---
# IMPORTANTE: Reemplaza "TU_API_KEY_AQUI" con tu clave de API de Google AI Studio.
# Se recomienda usar variables de entorno para mayor seguridad.
API_KEY = "TU_API_KEY_AQUI"

# Configura el cliente de Gemini
genai.configure(api_key=API_KEY)

# Define el prompt que se enviará a Gemini junto con la imagen.
# Este prompt instruye al modelo sobre cómo debe comportarse y qué formato de salida se espera.
GEMINI_PROMPT = """
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


def classify_image(image_bytes):
    """
    Envía una imagen a la API de Gemini para su clasificación.

    Args:
        image_bytes (bytes): La imagen en formato de bytes.

    Returns:
        dict: Un diccionario con el resultado de la clasificación, o None si hay un error.
    """
    print("Enviando imagen a Gemini para clasificación...")

    try:
        # Cargar la imagen desde los bytes
        img = Image.open(io.BytesIO(image_bytes))

        # Inicializar el modelo de Gemini Vision
        model = genai.GenerativeModel('gemini-pro-vision')

        # Enviar la imagen y el prompt al modelo
        response = model.generate_content([GEMINI_PROMPT, img])

        # Extraer y limpiar la respuesta JSON
        # A veces, el modelo envuelve el JSON en ```json ... ```, así que lo limpiamos.
        json_text = response.text.strip().replace("```json", "").replace("```", "").strip()

        # Parsear la cadena de texto a un diccionario de Python
        result = json.loads(json_text)
        print(f"Respuesta de Gemini recibida: {result}")

        return result

    except json.JSONDecodeError:
        print("Error: La respuesta de Gemini no es un JSON válido.")
        print(f"Texto recibido: {response.text}")
        return None
    except Exception as e:
        print(f"Error inesperado al contactar con la API de Gemini: {e}")
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

