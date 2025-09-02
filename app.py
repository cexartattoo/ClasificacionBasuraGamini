# -*- coding: utf-8 -*-
"""
Servidor Principal de Flask (app.py)

Este archivo es el corazón del sistema de clasificación de basura.
Orquesta la cámara, el modelo de IA (Gemini), y el control del Arduino.

Funcionalidades:
- Inicia y configura todos los módulos (base de datos, cámara, serial).
- Ejecuta un servidor web Flask para mostrar la interfaz de usuario.
- Proporciona un endpoint de streaming de video con las detecciones de la cámara.
- Proporciona un endpoint de API para obtener el historial de clasificaciones.
- Implementa una máquina de estados en un hilo separado para controlar el flujo
  de clasificación automática (detección -> estabilidad -> clasificación -> enfriamiento).
- Proporciona un endpoint para enviar mensajes de voz al frontend.
"""
import time
import threading
from datetime import datetime, timedelta
import atexit

from flask import Flask, render_template, Response, jsonify

# Importar nuestros módulos personalizados
import database
from camera import Camera
import gemini_client
import arduino_serial

# --- Inicialización de la Aplicación Flask ---
app = Flask(__name__)

# --- Configuración General de la Detección ---
FRAME_DELTA_THRESHOLD = 30
MIN_CONTOUR_AREA = 500

# --- Configuración de Estabilidad del Objeto ---
STABILITY_PIXEL_THRESHOLD = 1500
STABILITY_DURATION_SEC = 1.0
STABILITY_TIMEOUT_SEC = 10.0

# --- Configuración del Flujo de Clasificación ---
CLASSIFICATION_COOLDOWN_SEC = 10.0

# --- Cola de Mensajes para Hablar ---
MESSAGES_TO_SPEAK = []
messages_lock = threading.Lock()

# --- Inicialización de Módulos ---
print("Iniciando sistema de basura inteligente...")
database.init_db()
arduino_serial.init_serial()

atexit.register(arduino_serial.close_serial)

try:
    cam = Camera(
        frame_delta_thresh=FRAME_DELTA_THRESHOLD,
        min_contour_area=MIN_CONTOUR_AREA,
        stability_pixel_threshold=STABILITY_PIXEL_THRESHOLD,
        stability_duration_sec=STABILITY_DURATION_SEC
    )
except RuntimeError as e:
    print(f"--- ERROR CRÍTICO ---")
    print(f"No se pudo iniciar la cámara. Asegúrate de que esté conectada y no esté en uso.")
    print(f"Detalle: {e}")
    print("La aplicación se ejecutará sin la funcionalidad de cámara.")
    cam = None

# --- Máquina de Estados para el Control Automático ---
system_state = "ESPERANDO_OBJETO"
last_state_change = datetime.now()
is_classifying = threading.Lock()

def add_speech_message(message):
    """Añade un mensaje a la cola de voz de forma segura."""
    with messages_lock:
        MESSAGES_TO_SPEAK.append(message)

def classify_and_process():
    """
    Función central del proceso de clasificación.
    """
    global system_state, last_state_change

    if not is_classifying.acquire(blocking=False):
        print("Advertencia: Se intentó iniciar una clasificación mientras otra ya estaba en progreso.")
        return {"error": "Clasificación ya en progreso."}, 429

    print("\n--- INICIO DEL PROCESO DE CLASIFICACIÓN ---")
    try:
        frame_to_classify = cam.get_frame_bytes()
        if not frame_to_classify:
            print("Error: No se pudo capturar la imagen para clasificar.")
            return {"error": "No se pudo capturar imagen."}, 500

        print("1. Enviando imagen a Gemini para análisis...")
        add_speech_message("Analizando la imagen para clasificar el objeto.")
        gemini_result = gemini_client.classify_image(frame_to_classify)
        if not gemini_result or "material" not in gemini_result:
            print("Error: La respuesta de Gemini fue inválida o no contenía el material.")
            add_speech_message("Lo siento, no pude clasificar el objeto.")
            return {"error": "La clasificación de Gemini falló."}, 500

        material = gemini_result.get("material")
        objetos = gemini_result.get("objeto_s", [])
        confianza = objetos[0].get('confianza', 0.0) if objetos else 0.0
        respuesta_hablada = gemini_result.get("respuesta_hablada", "No se generó una respuesta.")

        print(f"2. Resultado de Gemini: Material='{material}', Respuesta='{respuesta_hablada}'")

        record_id = database.add_record(
            material,
            objetos,
            confianza,
            'PENDIENTE',
            respuesta_hablada
        )

        estado_final = 'NO_ENVIADO'
        if material and material != "null":
            print(f"3. Enviando comando '{material.upper()}' al Arduino...")
            add_speech_message(f"Moviendo los motores al compartimiento de {material}.")
            if arduino_serial.send_command(material):
                estado_final = 'ENVIADO'
                print("4. Arduino confirmó la recepción del comando.")
            else:
                estado_final = 'ERROR_ARDUINO'
                print("4. ERROR: Arduino no confirmó o hubo un error en la comunicación.")
            add_speech_message(respuesta_hablada)
        else:
            estado_final = 'NO_REQUERIDO'
            print("3. No se requiere acción del Arduino.")
            add_speech_message(respuesta_hablada)

        database.update_record_status(record_id, estado_final)
        print("--- PROCESO DE CLASIFICACIÓN COMPLETADO ---")

        system_state = "EN_ENFRIAMIENTO"
        last_state_change = datetime.now()
        print(f"\nSistema en modo ENFRIAMIENTO por {CLASSIFICATION_COOLDOWN_SEC} segundos.")

        return {"status": "success", "classification": gemini_result}, 200

    finally:
        is_classifying.release()

def automatic_classification_thread():
    """
    Hilo en segundo plano que opera la máquina de estados.
    """
    global system_state, last_state_change
    print("Iniciando hilo de clasificación automática...")

    while True:
        time.sleep(0.1)
        if not cam:
            continue

        if system_state == "ESPERANDO_OBJETO":
            if cam.detect_object_presence():
                system_state = "ESPERANDO_ESTABILIDAD"
                last_state_change = datetime.now()
                print("\n[Estado -> ESPERANDO_ESTABILIDAD] Objeto detectado. Esperando a que se detenga.")
                add_speech_message("Objeto en movimiento detectado.")

        elif system_state == "ESPERANDO_ESTABILIDAD":
            if cam.is_object_stable():
                print("[Estado -> CLASIFICANDO] Objeto estable. Iniciando clasificación...")
                with app.app_context():
                    classify_and_process()

            elif not cam.detect_object_presence():
                print("[Estado -> ESPERANDO_OBJETO] El objeto fue retirado antes de estabilizarse.")
                system_state = "ESPERANDO_OBJETO"

            elif (datetime.now() - last_state_change).total_seconds() > STABILITY_TIMEOUT_SEC:
                print(f"[Estado -> ESPERANDO_OBJETO] Timeout de {STABILITY_TIMEOUT_SEC}s. El objeto se movió demasiado tiempo.")
                system_state = "ESPERANDO_OBJETO"

        elif system_state == "EN_ENFRIAMIENTO":
            if (datetime.now() - last_state_change).total_seconds() > CLASSIFICATION_COOLDOWN_SEC:
                print("[Estado -> RECALIBRANDO] Enfriamiento finalizado. Actualizando fondo...")
                if cam:
                    cam.update_background()
                system_state = "ESPERANDO_OBJETO"
                print("[Estado -> ESPERANDO_OBJETO] Fondo actualizado. Listo para nueva detección.")


# --- Rutas de la Aplicación Web (Endpoints) ---

@app.route('/')
def index():
    """Sirve la página web principal (index.html)."""
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """Proporciona el streaming de video de la cámara."""
    if not cam:
        return "Error: La cámara no está disponible.", 503
    return Response(cam.stream_generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/history')
def history():
    """Endpoint de API que devuelve el historial de clasificaciones en formato JSON."""
    return jsonify(database.get_history())

@app.route('/get_messages')
def get_messages():
    """Devuelve y limpia la cola de mensajes de voz."""
    with messages_lock:
        messages = list(MESSAGES_TO_SPEAK)
        MESSAGES_TO_SPEAK.clear()
    return jsonify(messages)


# --- Bloque de Ejecución Principal ---
if __name__ == '__main__':
    classifier_thread = threading.Thread(target=automatic_classification_thread, daemon=True)
    classifier_thread.start()

    print("Servidor Flask iniciado en http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)