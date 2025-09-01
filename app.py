from flask import Flask, render_template, Response, jsonify
import time
import threading
from datetime import datetime, timedelta

# Importar nuestros módulos personalizados
import database
from camera import Camera
import gemini_client
import arduino_serial

app = Flask(__name__)
database.init_db()
arduino_serial.init_serial()

# --- Configuración de Sensibilidad ---
# Puedes ajustar estos valores sin tocar camera.py
FRAME_DELTA_THRESHOLD = 30      # Umbral para detectar un objeto (vs. fondo). Más bajo = más sensible.
MIN_CONTOUR_AREA = 500          # Área mínima en píxeles para considerar un objeto.

# --- Nueva Configuración de Estabilidad ---
STABILITY_PIXEL_THRESHOLD = 1500 # Umbral de cambio de píxeles para detectar MOVIMIENTO. Más bajo = más sensible.
STABILITY_DURATION_SEC = 3.0     # Segundos que el objeto debe estar quieto para ser clasificado.

try:
    cam = Camera(
        frame_delta_thresh=FRAME_DELTA_THRESHOLD,
        min_contour_area=MIN_CONTOUR_AREA,
        stability_pixel_threshold=STABILITY_PIXEL_THRESHOLD,
        stability_duration_sec=STABILITY_DURATION_SEC
    )
except RuntimeError as e:
    print(f"Error crítico al iniciar la cámara: {e}")
    cam = None

# --- Máquina de Estados para el Control Automático ---
system_state = "ESPERANDO_OBJETO"
last_state_change = datetime.now()
is_classifying = threading.Lock()


def classify_and_process():
    """Función central que captura, clasifica y envía a Arduino."""
    global system_state, last_state_change

    if not is_classifying.acquire(blocking=False):
        return {"error": "Clasificación ya en progreso."}, 429

    print("--- INICIO DEL PROCESO DE CLASIFICACIÓN ---")
    try:
        frame_to_classify = cam.get_frame_bytes()
        if not frame_to_classify:
            return {"error": "No se pudo capturar imagen para clasificar."}, 500

        print("1. Enviando imagen a Gemini...")
        gemini_result = gemini_client.classify_image(frame_to_classify)
        if not gemini_result or "material" not in gemini_result:
            return {"error": "La clasificación de Gemini falló."}, 500

        material = gemini_result.get("material")
        objetos = gemini_result.get("objeto_s", [])
        confianza = objetos[0].get('confianza', 0.0) if objetos else 0.0

        print(f"2. Resultado de Gemini: {material}")
        record_id = database.add_record(material, objetos, confianza, 'PENDIENTE')

        estado_final = 'NO_ENVIADO'
        if material and material != "null":
            print("3. Enviando comando al Arduino...")
            if arduino_serial.send_command(material):
                estado_final = 'ENVIADO'
                print("4. Arduino confirmó la recepción.")
            else:
                estado_final = 'ERROR_ARDUINO'
                print("4. ERROR: Arduino no confirmó.")
        else:
            estado_final = 'NO_REQUERIDO'

        database.update_record_status(record_id, estado_final)
        print("--- PROCESO DE CLASIFICACIÓN COMPLETADO ---")

        # Iniciar enfriamiento para no reclasificar inmediatamente
        system_state = "EN_ENFRIAMIENTO"
        last_state_change = datetime.now()
        print(f"Sistema en ENFRIAMIENTO por 3 segundos.")

        return {"status": "success", "classification": gemini_result}, 200

    finally:
        is_classifying.release()


def automatic_classification_thread():
    """Hilo en segundo plano que opera la máquina de estados."""
    global system_state, last_state_change
    print("Iniciando hilo de clasificación automática...")

    while True:
        time.sleep(0.2)  # Pequeña pausa para no sobrecargar el CPU
        if not cam: continue

        # --- Lógica de la Máquina de Estados ---

        if system_state == "ESPERANDO_OBJETO":
            if cam.detect_object_presence():
                system_state = "ESPERANDO_ESTABILIDAD"
                last_state_change = datetime.now()
                print("Estado -> ESPERANDO_ESTABILIDAD (Objeto detectado)")

        elif system_state == "ESPERANDO_ESTABILIDAD":
            # Si el objeto se queda quieto, clasifícalo
            if cam.is_object_stable():
                print("Objeto ESTABLE. Iniciando clasificación...")
                with app.app_context():
                    classify_and_process()

            # Timeout: si el objeto se mueve por más de 10s, vuelve a esperar
            elif (datetime.now() - last_state_change).total_seconds() > 3:
                print("Timeout de estabilidad. Objeto se movió demasiado tiempo.")
                system_state = "ESPERANDO_OBJETO"

            # Si el objeto desaparece, vuelve al estado inicial
            elif not cam.detect_object_presence():
                print("El objeto fue removido antes de estabilizarse.")
                system_state = "ESPERANDO_OBJETO"

        elif system_state == "EN_ENFRIAMIENTO":
            if (datetime.now() - last_state_change).total_seconds() > 10:
                # Después de 10s, vuelve al estado inicial para el siguiente objeto
                print("Estado -> ESPERANDO_OBJETO (Enfriamiento finalizado)")
                system_state = "ESPERANDO_OBJETO"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    if not cam: return "Error: Cámara no disponible.", 500
    return Response(cam.stream_generator(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/history')
def history():
    return jsonify(database.get_history())


if __name__ == '__main__':
    classifier_thread = threading.Thread(target=automatic_classification_thread, daemon=True)
    classifier_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

import atexit

atexit.register(arduino_serial.close_serial)