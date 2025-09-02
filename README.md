# ♻️ Sistema de Clasificación de Basura Inteligente v2.0

¡Un sistema autónomo que ve, entiende y clasifica la basura por ti! Este proyecto utiliza visión por computadora y la potencia de la IA de Google Gemini para identificar si un objeto es **plástico, orgánico o metal**, y luego interactúa con un Arduino para su posible clasificación física.

La interfaz web proporciona una visualización en tiempo real, un historial de clasificación y respuestas audibles del asistente de IA.

![GIF del proyecto en acción](https://i.imgur.com/YOUR_GIF_URL.gif)
*(Nota: Reemplaza la URL de arriba con un GIF que muestre tu proyecto funcionando)*

---

## ✨ Características Principales

- **Clasificación Automática:** No requiere intervención manual. El sistema detecta automáticamente cuándo un objeto se coloca frente a la cámara.
- **Detección de Estabilidad:** Espera a que el objeto esté quieto antes de analizarlo para asegurar una alta precisión.
- **Feedback Visual en Tiempo Real:** La transmisión de video muestra contornos para depuración:
    - **Verde:** Objeto detectado contra el fondo.
    - **Rojo:** Movimiento detectado.
- **Historial Interactivo:** La interfaz web muestra un historial de todas las clasificaciones.
- **Notificaciones con Voz y Animación:** Cada nueva clasificación se anuncia con una respuesta de voz del asistente y un efecto visual en la lista del historial.
- **Altamente Configurable:** Ajusta fácilmente la sensibilidad de la detección, los tiempos y los puertos desde los archivos de configuración.
- **Arquitectura Robusta:** El sistema utiliza hilos para separar la lógica de la cámara del servidor web, asegurando que la interfaz siempre sea fluida.

---

## 🛠️ Stack Tecnológico

- **Backend:** Python, Flask
- **Visión por Computadora:** OpenCV
- **Inteligencia Artificial:** Google Gemini 1.5 Flash
- **Hardware:** Arduino (o compatible)
- **Frontend:** HTML5, CSS3, JavaScript (puro)
- **Base de Datos:** SQLite

---

## ⚙️ ¿Cómo Funciona? (Flujo de Trabajo)

1.  **Detección de Presencia:** Un hilo dedicado en `camera.py` analiza constantemente el video. Cuando un objeto entra en el campo de visión, lo detecta comparándolo con una imagen de fondo de referencia (contornos verdes).
2.  **Espera de Estabilidad:** Una vez que se detecta un objeto, el sistema espera a que deje de moverse. Compara el fotograma actual con el anterior para detectar cambios (contornos rojos). Si no hay cambios significativos durante un tiempo configurable (`STABILITY_DURATION_SEC`), el objeto se considera estable.
3.  **Clasificación con IA:** Cuando un objeto está estable, `app.py` captura un fotograma **limpio** (sin contornos) y lo envía a la API de Gemini a través de `gemini_client.py`.
4.  **Respuesta de Gemini:** Gemini devuelve un objeto JSON con el `material` detectado, los `objetos` encontrados y una `respuesta_hablada`.
5.  **Registro y Comunicación:**
    - El resultado completo se guarda en la base de datos SQLite (`historial.db`).
    - Si el material es válido (plástico, orgánico o metal), se envía un comando por puerto serial al Arduino (ej. `PLASTICO\n`) a través de `arduino_serial.py`.
6.  **Feedback al Usuario:**
    - El frontend, al detectar un nuevo registro en la base de datos, lo añade a la lista del historial con una animación.
    - Simultáneamente, utiliza la API de voz del navegador para leer la `respuesta_hablada`.
7.  **Enfriamiento:** El sistema entra en un breve estado de "enfriamiento" para evitar clasificar el mismo objeto varias veces.

---

## 📂 Estructura del Proyecto

```
.
├── app.py                  # Servidor Flask principal, orquesta todo el sistema.
├── camera.py               # Lógica de OpenCV, detección de objetos y estabilidad.
├── gemini_client.py        # Cliente para la comunicación con la API de Gemini.
├── arduino_serial.py       # Maneja la comunicación serial con el Arduino.
├── database.py             # Gestiona la base de datos SQLite.
├── requirements.txt        # Dependencias de Python.
├── historial.db            # Archivo de la base de datos (se crea automáticamente).
├── README.md               # Esta documentación.
├── static/
│   └── style.css           # Hoja de estilos para la interfaz web.
└── templates/
    └── index.html          # Estructura HTML y JavaScript del frontend.
```

---

## 🚀 Instalación y Ejecución

#### **Paso 1: Requisitos Previos**
- Python 3.8 o superior.
- Una cámara web conectada.
- Un Arduino con un sketch simple cargado que pueda leer comandos seriales (ver `arduino_serial.py` para el protocolo).

#### **Paso 2: Clonar y Preparar el Entorno**
1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/tu-usuario/tu-repositorio.git
    cd tu-repositorio
    ```
2.  **Crea un entorno virtual (recomendado):**
    ```bash
    python -m venv .venv
    # En Windows
    .venv\Scripts\activate
    # En macOS/Linux
    source .venv/bin/activate
    ```
3.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

#### **Paso 3: Configuración**
¡Esta es la parte más importante! Abre los siguientes archivos y ajusta los parámetros según tu hardware y preferencias.

**1. `gemini_client.py`**
   - **API Key de Gemini:** Crea una variable de entorno llamada `GEMINI_API_KEY` con tu clave de API de Google AI Studio.
     ```bash
     # En Windows (temporal)
     set GEMINI_API_KEY="TU_API_KEY_AQUI"
     # En macOS/Linux (temporal)
     export GEMINI_API_KEY="TU_API_KEY_AQUI"
     ```
     *Para una configuración permanente, busca cómo añadir variables de entorno en tu sistema operativo.*

**2. `arduino_serial.py`**
   - `ARDUINO_PORT`: Cambia `'COM3'` por el puerto donde está conectado tu Arduino (ej. `'COM4'`, `'/dev/ttyUSB0'`).

**3. `app.py` (Ajustes de Sensibilidad)**
   - `FRAME_DELTA_THRESHOLD`: Sensibilidad para detectar la **presencia** de un objeto. Más bajo = más sensible.
   - `MIN_CONTOUR_AREA`: El tamaño mínimo en píxeles para que algo sea considerado un objeto. Auméntalo si detecta "ruido" pequeño.
   - `STABILITY_PIXEL_THRESHOLD`: Sensibilidad para detectar **movimiento**. Más bajo = más sensible al movimiento.
   - `STABILITY_DURATION_SEC`: Cuántos segundos debe estar quieto un objeto para ser clasificado.
   - `STABILITY_TIMEOUT_SEC`: Tiempo máximo de espera para que un objeto se estabilice antes de rendirse.
   - `CLASSIFICATION_COOLDOWN_SEC`: Tiempo de enfriamiento después de una clasificación.

**4. `camera.py` (Índice de la Cámara)**
   - En la línea `self.video = cv2.VideoCapture(1)`, el `1` se refiere a la segunda cámara del sistema. Si solo tienes una (la integrada), **cámbialo a `0`**.

#### **Paso 4: ¡Ejecutar!**
1.  Asegúrate de que tu Arduino esté conectado.
2.  Ejecuta el servidor Flask:
    ```bash
    python app.py
    ```
3.  Abre tu navegador y ve a `http://127.0.0.1:5000`.

¡Ahora deberías ver el video en vivo con los contornos de detección y escuchar al asistente cuando clasifique un objeto!