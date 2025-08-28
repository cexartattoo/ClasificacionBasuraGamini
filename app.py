from flask import Flask, render_template, Response, jsonify, request
import time

# Importar nuestros módulos personalizados
import database
from camera import Camera
import gemini_client
import arduino_serial

# Inicializar la aplicación Flask
app = Flask(__name__)

# Inicializar la base de datos al arrancar
database.init_db()

# Intentar inicializar la conexión serial con Arduino
# La aplicación puede funcionar incluso si Arduino no está conectado al inicio.
arduino_serial.init_serial()

# Crear una instancia global de la cámara
try:
    cam = Camera()
except RuntimeError as e:
    print(f"Error crítico al iniciar la cámara: {e}")
    cam = None


@app.route('/')
def index():
    """
    Renderiza la página principal de la interfaz web.
    """
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """
    Ruta que proporciona el stream de video de la cámara.
    """
    if cam is None:
        return "Error: La cámara no está disponible.", 500

    return Response(cam.stream_generator(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/history')
def history():
    """
    API endpoint para obtener el historial de clasificaciones en formato JSON.
    """
    records = database.get_history()
    return jsonify(records)


@app.route('/capture', methods=['POST'])
def capture():
    """
    Captura una imagen, la clasifica, la guarda en la BD y envía el comando a Arduino.
    """
    if cam is None:
        return jsonify({"error": "La cámara no está disponible."}), 500

    print("Iniciando proceso de captura y clasificación...")

    # 1. Capturar la imagen
    frame_bytes = cam.get_frame()
    if not frame_bytes:
        return jsonify({"error": "No se pudo capturar la imagen."}), 500

    # 2. Enviar a Gemini para clasificación
    gemini_result = gemini_client.classify_image(frame_bytes)

    if not gemini_result or "material" not in gemini_result:
        # Opcional: Reintentar una vez si la clasificación falla
        print("Primer intento de clasificación falló. Reintentando...")
        time.sleep(1)
        gemini_result = gemini_client.classify_image(frame_bytes)
        if not gemini_result or "material" not in gemini_result:
            return jsonify({"error": "La clasificación de la imagen falló después de reintentar."}), 500

    # Extraer datos de la respuesta de Gemini
    material = gemini_result.get("material")
    objetos = gemini_result.get("objeto_s", [])
    respuesta_hablada = gemini_result.get("respuesta_hablada", "No se pudo generar una respuesta.")
    confianza = objetos[0].get('confianza', 0.0) if objetos else 0.0

    # 3. Guardar en la base de datos con estado 'PENDIENTE'
    record_id = database.add_record(material, objetos, confianza, 'PENDIENTE')
    if record_id is None:
        return jsonify({"error": "No se pudo guardar el registro en la base de datos."}), 500

    # 4. Enviar comando a Arduino si el material es válido
    estado_final = 'NO_ENVIADO'
    if material and material != "null":
        if arduino_serial.send_command(material):
            estado_final = 'ENVIADO'
            print(f"Comando '{material}' enviado correctamente a Arduino.")
        else:
            estado_final = 'ERROR_ARDUINO'
            print(f"Fallo al enviar comando '{material}' a Arduino.")
    else:
        print("Material nulo o no reconocido, no se enviará comando a Arduino.")
        estado_final = 'NO_REQUERIDO'

    # 5. Actualizar el estado en la base de datos
    database.update_record_status(record_id, estado_final)

    # 6. Devolver el resultado completo al frontend
    return jsonify({
        "status": "success",
        "classification": gemini_result,
        "arduino_status": estado_final
    })


if __name__ == '__main__':
    # Ejecutar la aplicación en modo de depuración
    # host='0.0.0.0' permite acceder desde otros dispositivos en la misma red
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)


# Asegurarse de cerrar la conexión serial al salir
@app.teardown_appcontext
def teardown_serial(exception=None):
    # Esta función se ejecuta al final de cada solicitud,
    # pero para cerrar al final de la app, es mejor manejarlo en otro lugar.
    # La limpieza final se puede manejar con 'atexit' si es necesario.
    pass


import atexit

atexit.register(arduino_serial.close_serial)
